"""シミュレーション結果(.npz)を Blender で描画するための橋渡し。

1. atlas(): 各フレームの3D格子を、z方向の断面を並べた1枚の画像(アトラス)にする。
   R=煙、G=炎、B=温度、A=消火器の粉。8bit でも暗い部分がつぶれないよう、平方根で保存して描画時に2乗で戻す。
2. volume_material(): 箱の中で画像を3D的に読み直し(上下2枚の断面を線形補間)、
   黒体放射で光る炎と、光を遮る煙として描画するボリューム素材を作る。画像は連番として毎フレーム切り替わる。
"""
import math
from pathlib import Path

import numpy as np

SCALES = {"smoke": 2.0, "flame": 3.0, "temp": 8.0, "powder": 1.0}  # この値で割って 0〜1 に収める


def atlas(npz_dir, out_dir, scales=SCALES):
    """全フレームをアトラス PNG にして (nx, ny, nz, cols, rows, frames) を返す。"""
    from PIL import Image
    files = sorted(Path(npz_dir).glob("f_*.npz"))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    nx = ny = nz = cols = rows = 0
    for f in files:
        d = np.load(f)
        nx, ny, nz = d["smoke"].shape
        cols = math.ceil(math.sqrt(nz * ny / nx))
        rows = math.ceil(nz / cols)
        img = np.zeros((rows * ny, cols * nx, 4), np.float32)
        for c, name in enumerate(("smoke", "flame", "temp", "powder")):
            if name not in d.files:
                continue
            g = np.clip(d[name].astype(np.float32) / scales[name], 0, 1) ** 0.5
            for k in range(nz):
                col, row = k % cols, k // cols
                img[row * ny:(row + 1) * ny, col * nx:(col + 1) * nx, c] = g[:, :, k].T
        target = out / f.with_suffix(".png").name
        if not target.exists():
            Image.fromarray((np.flipud(img) * 255 + 0.5).astype(np.uint8)).save(target, compress_level=3)
    return nx, ny, nz, cols, rows, len(files)


def volume_material(name, first_png, info, smoke_k=40.0, flame_density=1.5, flame_k=260.0,
                    smoke_color=(0.025, 0.024, 0.023), detail=True, scales=SCALES):
    import bpy
    nx, ny, nz, cols, rows, frames = info
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    n, l = mat.node_tree.nodes, mat.node_tree.links
    n.remove(n["Principled BSDF"])

    def math_node(op, a=None, b=None):
        m = n.new("ShaderNodeMath")
        m.operation = op
        for idx, val in enumerate((a, b)):
            if val is None:
                continue
            if isinstance(val, (int, float)):
                m.inputs[idx].default_value = val
            else:
                l.new(val, m.inputs[idx])
        return m.outputs[0]

    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ")
    l.new(tc.outputs["Generated"], sep.inputs[0])
    gx, gy, gz = sep.outputs
    # 断面の番号 z0/z1 と補間係数 t
    zf = math_node("MULTIPLY", gz, nz - 1)
    z0 = math_node("FLOOR", zf)
    t = math_node("SUBTRACT", zf, z0)
    z1 = math_node("MINIMUM", math_node("ADD", z0, 1.0), nz - 1)
    # タイル内の位置(半ピクセル内側に寄せて隣のタイルがにじまないようにする)
    ux = math_node("DIVIDE", math_node("ADD", math_node("MULTIPLY", gx, nx - 1), 0.5), nx)
    vy = math_node("DIVIDE", math_node("ADD", math_node("MULTIPLY", gy, ny - 1), 0.5), ny)

    image = bpy.data.images.load(str(first_png))
    image.source = "SEQUENCE"
    image.colorspace_settings.name = "Non-Color"
    image.alpha_mode = "CHANNEL_PACKED"  # アルファ(粉)を色と独立したデータとして読む
    samples = []
    for zi in (z0, z1):
        col = math_node("FLOORED_MODULO", zi, cols)
        row = math_node("FLOOR", math_node("DIVIDE", zi, cols))
        U = math_node("DIVIDE", math_node("ADD", col, ux), cols)
        V = math_node("DIVIDE", math_node("ADD", row, vy), rows)
        comb = n.new("ShaderNodeCombineXYZ")
        l.new(U, comb.inputs[0])
        l.new(V, comb.inputs[1])
        tex = n.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Linear"
        tex.extension = "EXTEND"
        tex.image_user.frame_duration = frames
        tex.image_user.frame_start = 1
        tex.image_user.frame_offset = 0
        tex.image_user.use_auto_refresh = True
        l.new(comb.outputs[0], tex.inputs["Vector"])
        samples.append(tex.outputs["Color"])
    mix = n.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    l.new(t, mix.inputs["Factor"])
    l.new(samples[0], mix.inputs["A"])
    l.new(samples[1], mix.inputs["B"])
    rgb = n.new("ShaderNodeSeparateColor")
    l.new(mix.outputs["Result"], rgb.inputs[0])
    amix = n.new("ShaderNodeMix")  # アルファ(粉)も同じように補間
    amix.data_type = "FLOAT"
    l.new(t, amix.inputs["Factor"])
    l.new(n[samples[0].node.name].outputs["Alpha"], amix.inputs[2])
    l.new(n[samples[1].node.name].outputs["Alpha"], amix.inputs[3])
    powder = math_node("POWER", amix.outputs[0], 2.0)
    # atlas() と同じ scales で元の値の大きさに戻す(既定の SCALES のときは 0〜1 のまま)
    rel = {k: scales[k] / SCALES[k] for k in SCALES}
    smoke = math_node("MULTIPLY", math_node("POWER", rgb.outputs[0], 2.0), rel["smoke"])
    flame = math_node("MULTIPLY", math_node("POWER", rgb.outputs[1], 2.0), rel["flame"])
    temp = math_node("MULTIPLY", math_node("POWER", rgb.outputs[2], 2.0), rel["temp"])

    if detail:  # 格子より細かい揺らぎ(4Dノイズ、W をフレームで動かす)
        noise = n.new("ShaderNodeTexNoise")
        noise.noise_dimensions = "4D"
        noise.inputs["Scale"].default_value = 9.0
        noise.inputs["Detail"].default_value = 6.0
        noise.inputs["Roughness"].default_value = 0.6
        l.new(tc.outputs["Object"], noise.inputs["Vector"])
        w = noise.inputs["W"]
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
        w.default_value = 0.0
        w.keyframe_insert("default_value", frame=1)
        w.default_value = frames * 0.08
        w.keyframe_insert("default_value", frame=frames)
        fac = math_node("ADD", math_node("MULTIPLY", noise.outputs["Fac"], 1.4), 0.3)
        smoke = math_node("MULTIPLY", smoke, fac)
        flame = math_node("MULTIPLY", flame, math_node("ADD", math_node("MULTIPLY", fac, 0.6), 0.4))

    vol = n.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (*smoke_color, 1)
    vol.inputs["Absorption Color"].default_value = (0.02, 0.02, 0.02, 1)
    dens = math_node("ADD", math_node("MULTIPLY", smoke, smoke_k), math_node("MULTIPLY", flame, flame_density))
    # 粉は白く光を散らす。煙の色と粉の色を濃さの割合で混ぜる
    pdens = math_node("MULTIPLY", powder, 30.0)
    dens = math_node("ADD", dens, pdens)
    cmix = n.new("ShaderNodeMix")
    cmix.data_type = "RGBA"
    l.new(math_node("DIVIDE", pdens, math_node("ADD", dens, 1e-4)), cmix.inputs["Factor"])
    cmix.inputs["A"].default_value = (*smoke_color, 1)
    cmix.inputs["B"].default_value = (0.9, 0.9, 0.88, 1)
    l.new(cmix.outputs["Result"], vol.inputs["Color"])
    l.new(dens, vol.inputs["Density"])
    l.new(math_node("MULTIPLY", flame, flame_k), vol.inputs["Blackbody Intensity"])
    # 炎が強い(燃焼が激しい)ところほど白っぽく、弱いところは赤く(1100K〜2000K)
    heat = math_node("MINIMUM", math_node("ADD", math_node("MULTIPLY", flame, 2.5), math_node("MULTIPLY", temp, 0.3)), 1.0)
    temp_k = math_node("ADD", math_node("MULTIPLY", heat, 900.0), 1100.0)
    l.new(temp_k, vol.inputs["Temperature"])
    l.new(vol.outputs[0], n["Material Output"].inputs["Volume"])
    return mat


def domain_box(name, sim_shape, h, origin, mat):
    """シミュレーションの格子と同じ位置・大きさの箱を作り、ボリューム素材を割り当てる。"""
    import bpy
    nx, ny, nz = sim_shape
    size = (nx * h, ny * h, nz * h)
    center = tuple(o + s / 2 for o, s in zip(origin, size))
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    box = bpy.context.active_object
    box.name = name
    box.scale = size
    bpy.ops.object.transform_apply(scale=True)
    box.data.materials.append(mat)
    return box


def flame_curve(npz_dir):
    """フレームごとの炎の総量(最大を1にそろえる)。炎の光で周りを照らすライトの強さに使う。"""
    vals = [float(np.load(f)["flame"].astype(np.float32).sum()) for f in sorted(Path(npz_dir).glob("f_*.npz"))]
    top = max(vals) or 1.0
    return [v / top for v in vals]
