"""第2話（脳汁・ドーパミン）の3Dシーンを Blender（無料, bpy）でレンダリングする。クレジット不使用。

  python3 scripts/science_0001/blender/ep02_scenes.py squishy   # 冒頭: スクイーズがむにゅっとつぶれて戻る
  python3 scripts/science_0001/blender/ep02_scenes.py nerve     # 光の信号が神経を通って脳へ
  python3 scripts/science_0001/blender/ep02_scenes.py reward    # 脳の前側の下(眼窩前頭皮質)が暖色に光る
  python3 scripts/science_0001/blender/ep02_scenes.py dopamine  # 脳の奥(中脳)から金色の粒(ドーパミン)が広がる
  オプション: --preview (数フレームだけ) --frames N
出力: assets/output/science_0001/ep02_blender/<scene>/####.png (540x960) → 編集時に 1080x1920 へ拡大
レンダラは Cycles(CPU)。EEVEE はこの環境に GPU/EGL がないため使えない。
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/output/science_0001/ep02_blender"
FPS = 15  # レンダリングは15fps。編集で30fpsに補間する(時間短縮)


# ------------------------------------------------------------------ 共通
def reset(frames):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 8
    sc.cycles.adaptive_threshold = 0.05
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 3
    sc.cycles.transmission_bounces = 3
    sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = 540, 960
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, frames
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.image_settings.file_format = "PNG"
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.012, 0.014, 0.025, 1)
    bg.inputs["Strength"].default_value = 1.0
    return sc


def glare(sc, size=7, threshold=0.6, mix=0.0):
    """光のにじみ。この環境ではコンポジタが GPU 初期化で落ちるため、編集側(PIL)でかける。ここでは何もしない。"""
    return
    sc.use_nodes = True
    tree = sc.compositing_node_group if hasattr(sc, "compositing_node_group") else None
    if tree is None:
        try:
            tree = bpy.data.node_groups.new("comp", "CompositorNodeTree")
            sc.compositing_node_group = tree
        except Exception:
            tree = sc.node_tree
    nodes, links = tree.nodes, tree.links
    for n in list(nodes):
        nodes.remove(n)
    rl = nodes.new("CompositorNodeRLayers")
    gl = nodes.new("CompositorNodeGlare")
    for attr, val in (("glare_type", "FOG_GLOW"), ("size", size), ("threshold", threshold), ("mix", mix)):
        try:
            setattr(gl, attr, val)
        except Exception:
            for inp in gl.inputs:
                if inp.name.lower().replace(" ", "_") == attr:
                    try:
                        inp.default_value = val
                    except Exception:
                        pass
    try:
        out = nodes.new("CompositorNodeComposite")
    except Exception:
        out = nodes.new("NodeGroupOutput")
        tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    links.new(rl.outputs["Image"], gl.inputs[0])
    links.new(gl.outputs[0], out.inputs[0])


def camera(loc, look_at, lens=50):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    cam.data.lens = lens
    d = Vector(look_at) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def area_light(loc, energy, size=3, color=(1, 1, 1), target=(0, 0, 0)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    lt = bpy.context.object
    lt.data.energy = energy
    lt.data.size = size
    lt.data.color = color
    d = Vector(target) - Vector(loc)
    lt.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return lt


def mat_principled(name, color, rough=0.5, sss=0.0, sheen=0.0, emission=None, estr=0.0, alpha=1.0, trans=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    for key, val in (("Subsurface Weight", sss), ("Sheen Weight", sheen), ("Alpha", alpha),
                     ("Transmission Weight", trans)):
        if key in b.inputs:
            b.inputs[key].default_value = val
    if sss and "Subsurface Radius" in b.inputs:
        b.inputs["Subsurface Radius"].default_value = (0.5, 0.3, 0.3)
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = estr
    return m


def mat_emit(name, color, strength):
    """発光(強さ0のときは透明になるので、光っていないときは見えない)。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    add = nt.nodes.new("ShaderNodeAddShader")
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(e.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], o.inputs[0])
    return m, e


def key(obj, path, frame, value, index=-1):
    setattr(obj, path, value) if index < 0 else None
    if index >= 0:
        getattr(obj, path)[index] = value
    obj.keyframe_insert(data_path=path, frame=frame, index=index)


def smooth_keys():
    for a in bpy.data.actions:
        try:
            curves = a.fcurves
        except AttributeError:
            curves = [fc for layer in a.layers for strip in layer.strips for bag in strip.channelbags
                      for fc in bag.fcurves]
        for fc in curves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.easing = "AUTO"


# ------------------------------------------------------------------ 脳(様式化)
def brain(glass=False):
    """左右の大脳半球(しわ=Marble テクスチャの凹凸) + 小脳(横じま) + 脳幹。"""
    gy = bpy.data.textures.new("gyri", type="MARBLE")
    gy.marble_type = "SHARP"
    gy.noise_basis_2 = "SIN"
    gy.noise_scale = 0.32
    gy.turbulence = 5.0
    gy.noise_depth = 2
    fol = bpy.data.textures.new("folia", type="WOOD")
    fol.wood_type = "BANDS"
    fol.noise_scale = 0.05
    fol.turbulence = 2.0
    m = mat_principled("brain", (0.86, 0.52, 0.58), rough=0.42, sss=0.0, sheen=0.3, alpha=0.3 if glass else 1.0)
    parts = []
    for side in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=96, radius=1, location=(0, side * 0.5, 0))
        h = bpy.context.object
        h.scale = (1.42, 0.56, 0.98)
        parts.append(h)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=64, radius=0.45, location=(-1.0, 0, -0.7))
    cb = bpy.context.object
    cb.scale = (0.95, 1.6, 0.62)
    parts.append(cb)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.17, depth=1.0, location=(-0.4, 0, -1.05))
    bs = bpy.context.object
    bs.rotation_euler = (0, math.radians(-18), 0)
    parts.append(bs)
    for i, p in enumerate(parts):
        bpy.context.view_layer.objects.active = p
        if i < 3:
            sub = p.modifiers.new("sub", "SUBSURF")
            sub.levels = sub.render_levels = 1
            mod = p.modifiers.new("disp", "DISPLACE")
            mod.texture = gy if i < 2 else fol
            mod.strength = 0.11 if i < 2 else 0.05
            mod.texture_coords = "LOCAL"
        bpy.ops.object.shade_smooth()
        p.data.materials.append(m)
    return parts, m


# ------------------------------------------------------------------ シーン
def scene_squishy(frames):
    sc = reset(frames)
    # 床
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    floor = bpy.context.object
    floor.data.materials.append(mat_principled("floor", (0.03, 0.03, 0.045), rough=0.7))
    # スクイーズ(ミント色のまんじゅう形)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=1, location=(0, 0, 0.82))
    sq = bpy.context.object
    sq.scale = (1, 1, 0.82)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.shade_smooth()
    sq.data.materials.append(mat_principled("squishy", (0.45, 0.88, 0.76), rough=0.62, sss=0.0, sheen=0.5))
    # つぶれ形のシェイプキー: 上を押し下げ、横にふくらむ
    sq.shape_key_add(name="Basis")
    sk = sq.shape_key_add(name="squash")
    for v, kv in zip(sq.data.vertices, sk.data):
        x, y, z = v.co
        h = (z - 0.0) / 1.64  # 0..1
        press = math.exp(-((x) ** 2 + (y) ** 2) / 0.35)  # 押す点(中央)ほど深く
        nz = z * (0.74 - 0.30 * press * h)
        bulge = 1 + 0.22 * math.sin(math.pi * min(max(h, 0), 1)) * (1 - 0.3 * press)
        kv.co = (x * bulge, y * bulge, max(nz, 0.0))
    # 指(上から伸びる丸い棒。先は画面の外へ)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.36, depth=4.0, location=(0, 0, 4.6))
    rod = bpy.context.object
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.36, location=(0, 0, 2.6))
    tip = bpy.context.object
    rod.parent = tip
    rod.location = (0, 0, 2.0)
    for o in (rod, tip):
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.shade_smooth()
        o.data.materials.append(mat_principled("finger", (0.98, 0.86, 0.80), rough=0.45, sss=0.0))
    fing = tip
    # アニメーション: 0.4秒で押す → 0.8秒キープ → ゆっくり戻る(〜4.8秒)
    f = lambda s: int(1 + s * FPS)
    for fr, val, z in ((f(0.0), 0.0, 2.9), (f(0.2), 0.0, 2.0), (f(0.6), 1.0, 1.25), (f(1.4), 1.0, 1.25),
                       (f(1.9), 0.8, 1.9), (f(4.6), 0.0, 3.4)):
        sk.value = val
        sk.keyframe_insert("value", frame=fr)
        fing.location.z = z
        fing.keyframe_insert("location", frame=fr, index=2)
    smooth_keys()
    # ライト・カメラ
    area_light((3, -3, 5), 900, size=4, color=(1.0, 0.95, 0.92), target=(0, 0, 0.8))
    area_light((-4, 2, 3), 400, size=5, color=(0.6, 0.75, 1.0), target=(0, 0, 0.8))
    area_light((0, 4, 2), 600, size=3, color=(1.0, 0.7, 0.85), target=(0, 0, 0.8))
    camera((0, -6.0, 1.7), (0, 0, 1.0), lens=55)
    glare(sc, size=6, threshold=0.9)
    return sc


def scene_nerve(frames):
    sc = reset(frames)
    parts, _ = brain()
    for p in parts:
        p.location.z += 1.2
    # 神経の管(下から脳の下へ)
    curve = bpy.data.curves.new("nerve", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.035
    curve.bevel_resolution = 4
    sp = curve.splines.new("BEZIER")
    pts = [(1.4, -0.2, -3.6), (0.6, 0.0, -1.6), (-0.2, 0.0, -0.4), (-0.45, 0.0, 0.35)]
    sp.bezier_points.add(len(pts) - 1)
    for bp, co in zip(sp.bezier_points, pts):
        bp.co = co
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    nerve = bpy.data.objects.new("nerve", curve)
    bpy.context.collection.objects.link(nerve)
    nerve.data.materials.append(mat_emit("nerve_m", (0.25, 0.45, 1.0), 1.2)[0])
    # 光の粒が管を通る
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.11, location=(0, 0, 0))
    pulse = bpy.context.object
    pulse.data.materials.append(mat_emit("pulse_m", (1.0, 0.85, 0.4), 40)[0])
    c = pulse.constraints.new("FOLLOW_PATH")
    c.target = nerve
    c.use_fixed_location = True
    c.offset_factor = 0.0
    c.keyframe_insert("offset_factor", frame=int(0.3 * FPS))
    c.offset_factor = 1.0
    c.keyframe_insert("offset_factor", frame=int(2.6 * FPS))
    bpy.ops.object.light_add(type="POINT", location=(0, 0, 0))
    pl = bpy.context.object
    pl.data.energy = 60
    pl.data.color = (1.0, 0.8, 0.4)
    pl.parent = pulse
    # 脳に届いた瞬間、脳の上部が光る
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(-0.1, 0, 2.15))
    hit = bpy.context.object
    hit.scale = (0.5, 1.2, 0.25)
    hm, he = mat_emit("hit_m", (1.0, 0.6, 0.25), 0.0)
    hit.data.materials.append(hm)
    for fr, s in ((int(2.5 * FPS), 0.0), (int(2.9 * FPS), 8.0), (int(4.8 * FPS), 3.0)):
        he.inputs["Strength"].default_value = s
        he.inputs["Strength"].keyframe_insert("default_value", frame=fr)
    area_light((3, -4, 4), 700, size=5, color=(1.0, 0.9, 0.95), target=(0, 0, 1.2))
    area_light((-4, 3, 2), 500, size=5, color=(0.5, 0.6, 1.0), target=(0, 0, 1.2))
    cam = camera((0.3, -11.0, 0.4), (0.0, 0, -0.3), lens=46)
    cam.location.z = 0.4
    cam.keyframe_insert("location", frame=1, index=2)
    cam.location.z = 0.9
    cam.keyframe_insert("location", frame=frames, index=2)
    glare(sc, size=7, threshold=0.7)
    return sc


def scene_reward(frames):
    sc = reset(frames)
    parts, _ = brain()
    for p in parts:
        p.location.z += 0.3
    # 眼窩前頭皮質(前側の下)の光
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.45, location=(1.15, -0.45, -0.3))
    ofc = bpy.context.object
    ofc.scale = (0.75, 0.9, 0.5)
    om, oe = mat_emit("ofc_m", (1.0, 0.45, 0.2), 0.0)
    ofc.data.materials.append(om)
    for fr, s in ((int(0.6 * FPS), 0.0), (int(1.6 * FPS), 10.0), (int(3.0 * FPS), 6.0), (frames, 9.0)):
        oe.inputs["Strength"].default_value = s
        oe.inputs["Strength"].keyframe_insert("default_value", frame=fr)
    bpy.ops.object.light_add(type="POINT", location=(1.35, -0.9, -0.45))
    pl = bpy.context.object
    pl.data.color = (1.0, 0.55, 0.3)
    pl.data.energy = 0
    pl.data.keyframe_insert("energy", frame=int(0.6 * FPS))
    pl.data.energy = 250
    pl.data.keyframe_insert("energy", frame=int(1.6 * FPS))
    area_light((3, -4, 4), 600, size=5, color=(1.0, 0.9, 0.95), target=(0, 0, 0.3))
    area_light((-4, 3, 2), 500, size=5, color=(0.5, 0.6, 1.0), target=(0, 0, 0.3))
    # ゆっくり回り込む
    bpy.ops.object.empty_add(location=(0, 0, 0.3))
    rig = bpy.context.object
    cam = camera((0, -9.6, 0.6), (0, 0, 0.3), lens=50)
    cam.parent = rig
    rig.rotation_euler.z = math.radians(-12)
    rig.keyframe_insert("rotation_euler", frame=1, index=2)
    rig.rotation_euler.z = math.radians(14)
    rig.keyframe_insert("rotation_euler", frame=frames, index=2)
    glare(sc, size=7, threshold=0.7)
    return sc


def scene_dopamine(frames):
    sc = reset(frames)
    parts, bm = brain(glass=True)
    for p in parts:
        p.location.z += 0.3
    # 脳を半透明に(中の粒が見えるように)
    b = bm.node_tree.nodes["Principled BSDF"]
    b.inputs["Alpha"].default_value = 0.28
    # 中脳(ドーパミンの出どころ)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(-0.25, 0, -0.35))
    src = bpy.context.object
    src.data.materials.append(mat_emit("src_m", (1.0, 0.75, 0.25), 25)[0])
    # 粒(ドーパミン)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.035, location=(0, 0, -50))
    drop = bpy.context.object
    drop.data.materials.append(mat_emit("drop_m", (1.0, 0.72, 0.18), 14)[0])
    ps = src.modifiers.new("ps", "PARTICLE_SYSTEM").particle_system
    st = ps.settings
    st.count = 900
    st.frame_start = int(0.5 * FPS)
    st.frame_end = int(4.0 * FPS)
    st.lifetime = int(1.5 * FPS)
    st.lifetime_random = 0.4
    st.emit_from = "VOLUME"
    st.normal_factor = 0.0
    st.object_align_factor = (0.35, 0.0, 0.55)
    st.factor_random = 0.35
    st.normal_factor = 0.0
    st.effector_weights.gravity = 0.0
    st.render_type = "OBJECT"
    st.instance_object = drop
    st.particle_size = 1.0
    st.size_random = 0.6
    st.use_rotations = False
    src.show_instancer_for_render = True
    area_light((3, -4, 4), 450, size=5, color=(1.0, 0.9, 0.95), target=(0, 0, 0.3))
    area_light((-4, 3, 2), 350, size=5, color=(0.5, 0.6, 1.0), target=(0, 0, 0.3))
    bpy.ops.object.empty_add(location=(0, 0, 0.2))
    rig = bpy.context.object
    cam = camera((0, -9.6, 0.4), (0, 0, 0.2), lens=50)
    cam.parent = rig
    rig.rotation_euler.z = math.radians(8)
    rig.keyframe_insert("rotation_euler", frame=1, index=2)
    rig.rotation_euler.z = math.radians(-10)
    rig.keyframe_insert("rotation_euler", frame=frames, index=2)
    glare(sc, size=8, threshold=0.6)
    return sc


SCENES = {"squishy": (scene_squishy, 5 * FPS), "nerve": (scene_nerve, 5 * FPS), "reward": (scene_reward, 4 * FPS),
          "dopamine": (scene_dopamine, 5 * FPS)}


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    name = args[0]
    fn, frames = SCENES[name]
    if "--frames" in args:
        frames = int(args[args.index("--frames") + 1])
    sc = fn(frames)
    out = OUT / name
    out.mkdir(parents=True, exist_ok=True)
    if "--preview" in args:
        for fr in (1, frames // 3, frames * 2 // 3, frames):
            sc.frame_set(fr)
            sc.render.filepath = str(out / f"preview_{fr:04d}.png")
            bpy.ops.render.render(write_still=True)
        return
    sc.render.filepath = str(out) + "/"
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
