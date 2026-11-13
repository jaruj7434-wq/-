"""第4話(服)C05〜C08 用の補助。単位 1BU=1cm。

- 古着の圧縮梱包(ベール): 押しつぶされて横に重なった色とりどりの布の層+PPバンド
- 無地の海上コンテナ(波板の壁・観音開きの扉。ロゴ・文字なし)
- ウエス(四角く切った綿布)のメッシュ/柄、歯車、油汚れ→ふき取ると光る金属
- 反毛の繊維(くるっと曲がった短い糸)と、GN で「服 → 綿雲 → 板」に移動させる点群
(C01〜C04 用の fuku_parts.py は別エージェントの担当。こちらは C05〜C08 専用。)
"""
import math, random

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import common as C
import props as P
import factory_parts as F
import pet_parts as PP


# ------------------------------------------------------------------ アニメ補助
def key_multi(obj, keys):
    """keys = [(frame, loc, rot_deg or None, interp)]。interp はそのキーから次のキーまでの補間。"""
    for f, loc, rot, _ in keys:
        obj.location = loc; obj.keyframe_insert("location", frame=f)
        if rot is not None:
            obj.rotation_euler = tuple(math.radians(a) for a in rot); obj.keyframe_insert("rotation_euler", frame=f)
    table = {f: it for f, _, _, it in keys}
    for fc in F.fcurves(obj):
        for kp in fc.keyframe_points:
            kp.interpolation = table.get(int(round(kp.co.x)), "BEZIER")


# ------------------------------------------------------------------ 布の色
# 古着の色(デニム・白・黒・赤・からし・緑・ピンク・グレー・紺・ベージュ)
CLOTH_COLORS = [(0.10, 0.18, 0.34), (0.20, 0.30, 0.48), (0.80, 0.80, 0.76), (0.04, 0.04, 0.045),
                (0.55, 0.08, 0.07), (0.70, 0.50, 0.12), (0.14, 0.32, 0.18), (0.78, 0.42, 0.48),
                (0.38, 0.38, 0.38), (0.05, 0.08, 0.18), (0.62, 0.52, 0.38), (0.24, 0.52, 0.58)]


def _ramp(cr, colors, hard=True):
    """カラーランプを colors で等分に塗る(hard=True で段差)。"""
    cr.color_ramp.interpolation = "CONSTANT" if hard else "LINEAR"
    e = cr.color_ramp.elements
    k = len(colors)
    e[0].position = 0.0; e[0].color = (*colors[0], 1)
    e[1].position = 1.0 / k; e[1].color = (*colors[1], 1)
    for i in range(2, k):
        e.new(i / k).color = (*colors[i], 1)


def mat_cloth_bale(name="ClothBale", seed=0.0):
    """圧縮した古着: 上下に強くつぶしたボロノイのセル1つ=服1枚。セルごとに古着の色、
    セル内は布のしわ(筋状の明暗+バンプ)、セルの境目(服と服の隙間)は暗い。不透明で軽い。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping"); mp.inputs["Location"].default_value = (seed * 37.1, seed * 11.3, seed * 5.7)
    mp.inputs["Scale"].default_value = (0.7, 0.7, 6.5)      # 上下に押しつぶされて横に重なる層
    C.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    warp = n.new("ShaderNodeTexNoise"); warp.inputs["Scale"].default_value = 0.08; warp.inputs["Detail"].default_value = 3
    C.link(nt, mp.outputs["Vector"], warp.inputs["Vector"])
    wsub = n.new("ShaderNodeVectorMath"); wsub.operation = "SUBTRACT"; wsub.inputs[1].default_value = (0.5, 0.5, 0.5)
    C.link(nt, warp.outputs["Color"], wsub.inputs[0])
    wsc = n.new("ShaderNodeVectorMath"); wsc.operation = "SCALE"; wsc.inputs["Scale"].default_value = 22.0
    C.link(nt, wsub.outputs[0], wsc.inputs[0])
    wadd = n.new("ShaderNodeVectorMath"); wadd.operation = "ADD"
    C.link(nt, mp.outputs["Vector"], wadd.inputs[0]); C.link(nt, wsc.outputs[0], wadd.inputs[1])
    vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 0.06; vo.inputs["Randomness"].default_value = 1.0
    C.link(nt, wadd.outputs[0], vo.inputs["Vector"])
    ve = n.new("ShaderNodeTexVoronoi"); ve.feature = "DISTANCE_TO_EDGE"; ve.inputs["Scale"].default_value = 0.06
    C.link(nt, wadd.outputs[0], ve.inputs["Vector"])
    sepc = n.new("ShaderNodeSeparateColor"); C.link(nt, vo.outputs["Color"], sepc.inputs["Color"])
    cr = n.new("ShaderNodeValToRGB"); _ramp(cr, CLOTH_COLORS)
    C.link(nt, sepc.outputs["Red"], cr.inputs["Fac"])
    # 柄物(ボーダー)をまれに: セルの緑成分で選ぶ
    stripe = n.new("ShaderNodeTexWave"); stripe.wave_type = "BANDS"; stripe.bands_direction = "Z"
    stripe.inputs["Scale"].default_value = 0.6; stripe.inputs["Distortion"].default_value = 2.0
    C.link(nt, wadd.outputs[0], stripe.inputs["Vector"])
    sth = n.new("ShaderNodeMath"); sth.operation = "GREATER_THAN"; sth.inputs[1].default_value = 0.55
    C.link(nt, stripe.outputs["Fac"], sth.inputs[0])
    pick = n.new("ShaderNodeMath"); pick.operation = "GREATER_THAN"; pick.inputs[1].default_value = 0.8
    C.link(nt, sepc.outputs["Green"], pick.inputs[0])
    sm = n.new("ShaderNodeMath"); sm.operation = "MULTIPLY"
    C.link(nt, sth.outputs[0], sm.inputs[0]); C.link(nt, pick.outputs[0], sm.inputs[1])
    smix = n.new("ShaderNodeMix"); smix.data_type = "RGBA"
    C.link(nt, sm.outputs[0], smix.inputs["Factor"])
    C.link(nt, cr.outputs["Color"], smix.inputs["A"]); smix.inputs["B"].default_value = (0.85, 0.84, 0.8, 1)
    # しわ
    cm = n.new("ShaderNodeMapping"); cm.inputs["Scale"].default_value = (0.5, 0.5, 1.6)
    C.link(nt, wadd.outputs[0], cm.inputs["Vector"])
    wr = n.new("ShaderNodeTexNoise"); wr.inputs["Scale"].default_value = 0.7; wr.inputs["Detail"].default_value = 6
    wr.inputs["Roughness"].default_value = 0.6
    C.link(nt, cm.outputs["Vector"], wr.inputs["Vector"])
    crk = n.new("ShaderNodeValToRGB")
    crk.color_ramp.elements[0].position = 0.3; crk.color_ramp.elements[0].color = (0.5, 0.5, 0.5, 1)
    crk.color_ramp.elements[1].position = 0.7; crk.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    C.link(nt, wr.outputs["Fac"], crk.inputs["Fac"])
    mul = n.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
    C.link(nt, smix.outputs["Result"], mul.inputs["A"]); C.link(nt, crk.outputs["Color"], mul.inputs["B"])
    edge = n.new("ShaderNodeMapRange"); edge.inputs["From Min"].default_value = 0.0; edge.inputs["From Max"].default_value = 0.05
    C.link(nt, ve.outputs["Distance"], edge.inputs["Value"])
    dk = n.new("ShaderNodeMix"); dk.data_type = "RGBA"
    C.link(nt, edge.outputs["Result"], dk.inputs["Factor"])
    dk.inputs["A"].default_value = (0.02, 0.02, 0.02, 1); C.link(nt, mul.outputs["Result"], dk.inputs["B"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.85
    p.inputs["Sheen Weight"].default_value = 0.3; p.inputs["Sheen Roughness"].default_value = 0.4
    C.link(nt, dk.outputs["Result"], p.inputs["Base Color"])
    h = n.new("ShaderNodeMath"); h.operation = "MULTIPLY_ADD"; h.inputs[1].default_value = 0.5
    C.link(nt, wr.outputs["Fac"], h.inputs[0]); C.link(nt, edge.outputs["Result"], h.inputs[2])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.9; b.inputs["Distance"].default_value = 1.0
    C.link(nt, h.outputs[0], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def cloth_bale(name, size=(75, 55, 52), loc=(0, 0, 0), seed=0, mat=None, rot_z=0.0):
    """古着のベール(原点=底面中心)。PPバンド3本。pet_parts.bale の形をそのまま流用。"""
    sm = bpy.data.materials.get("PPBand") or C.principled("PPBand", (0.85, 0.82, 0.70), rough=0.35)
    root = PP.bale(name, size, loc, seed=seed, mat=mat, strap_mat=sm, straps=3)
    blk = bpy.data.objects[name + "_Blk"]
    blk.modifiers["sub"].levels = 3; blk.modifiers["sub"].render_levels = 3
    blk.modifiers["disp"].strength = 2.0
    blk.modifiers["disp2"].strength = 2.5
    root.rotation_euler.z = rot_z
    return root


# ------------------------------------------------------------------ コンテナ
def corrugated_panel(name, length, height, pitch=27.0, depth=3.5, mat=None):
    """台形の波板(X 方向に length、Z 方向に height、-Y 側へ山)。原点=左下手前。"""
    prof = []
    k = int(length / pitch)
    pitch = length / k
    for i in range(k):
        x0 = i * pitch
        prof += [(x0, 0.0), (x0 + pitch * 0.15, -depth), (x0 + pitch * 0.5, -depth), (x0 + pitch * 0.65, 0.0)]
    prof.append((length, 0.0))
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, 0)) for x, y in prof]
    hi = [bm.verts.new((x, y, height)) for x, y in prof]
    for i in range(len(prof) - 1):
        bm.faces.new((lo[i], lo[i + 1], hi[i + 1], hi[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    P.add_mod(o, "SOLIDIFY", thickness=0.4, offset=1)
    if mat:
        me.materials.append(mat)
    return o


def mat_container(name, color, rough=0.5, ribs=True):
    """コンテナの塗装: 色ムラは控えめ、縦の波(リブ)をバンプで(扉・平らな面用)、うっすら汚れ。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.02; nz.inputs["Detail"].default_value = 6
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.3; cr.color_ramp.elements[0].color = tuple(c * 0.82 for c in color) + (1,)
    cr.color_ramp.elements[1].position = 0.7; cr.color_ramp.elements[1].color = (*color, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    # 下の方ほど少し汚れる(縦筋)
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = rough
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    if ribs:
        wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"
        wv.inputs["Scale"].default_value = 0.037 * 100 / 100; wv.inputs["Distortion"].default_value = 0
        wv.wave_profile = "TRI"
        C.link(nt, tc.outputs["Object"], wv.inputs["Vector"])
        b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.6; b.inputs["Distance"].default_value = 2.0
        C.link(nt, wv.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def container(name, color=(0.10, 0.30, 0.36), loc=(0, 0, 0), length=606.0, width=244.0, height=259.0,
              door_deg=105.0, interior=True, floor_mat=None):
    """20ft 風の海上コンテナ(無地)。扉は -Y 側の端(y=0)、奥へ +Y。原点=扉側の床下中央。
    door_deg で観音扉を外へ開く。interior=False なら外形だけ(遠景用・軽い)。"""
    root = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(root)
    root.location = loc
    paint = mat_container(name + "Paint", color)
    frame_m = mat_container(name + "Frame", tuple(c * 0.75 for c in color), rough=0.45)
    W, L, H = width, length, height
    parts = []

    def add(o):
        o.parent = root; parts.append(o); return o
    if not interior:
        add(P.box(name + "_Box", (W, L, H - 10), (0, L / 2, 10 + (H - 10) / 2), mat=paint))
        # 側面の波板(外形を少し凸凹に)
        for s in (-1, 1):
            cp = corrugated_panel(name + f"_Side{s}", L - 20, H - 26, mat=paint)
            cp.rotation_euler = (0, 0, math.radians(90 if s > 0 else -90))
            cp.location = (s * (W / 2 + 0.2), 10 if s > 0 else L - 10, 18)
            add(cp)
        return root
    # 床・天井
    add(P.box(name + "_Floor", (W, L, 15), (0, L / 2, 7.5), mat=floor_mat or paint))
    add(P.box(name + "_Roof", (W, L, 6), (0, L / 2, H - 3), mat=paint))
    # 側壁(波板)と内側の暗い面
    for s in (-1, 1):
        cp = corrugated_panel(name + f"_Side{s}", L - 16, H - 30, mat=paint)
        if s < 0:
            cp.rotation_euler = (0, 0, math.radians(-90)); cp.location = (-W / 2 + 2, L - 8, 15)
        else:
            cp.rotation_euler = (0, 0, math.radians(90)); cp.location = (W / 2 - 2, 8, 15)
        add(cp)
    add(P.box(name + "_Back", (W, 6, H), (0, L - 3, H / 2), mat=paint))
    # 四隅の柱と上下のレール
    for sx in (-1, 1):
        for y in (0, L):
            add(P.box(name + f"_Post{sx}{int(y)}", (12, 14, H), (sx * (W / 2 - 6), y + (7 if y == 0 else -7), H / 2), mat=frame_m, bevel=0.6))
        add(P.box(name + f"_RailB{sx}", (10, L, 15), (sx * (W / 2 - 5), L / 2, 7.5), mat=frame_m, bevel=0.5))
        add(P.box(name + f"_RailT{sx}", (10, L, 12), (sx * (W / 2 - 5), L / 2, H - 6), mat=frame_m, bevel=0.5))
    add(P.box(name + "_Header", (W, 14, 22), (0, 7, H - 11), mat=frame_m, bevel=0.6))
    add(P.box(name + "_Sill", (W, 14, 15), (0, 7, 7.5), mat=frame_m, bevel=0.6))
    # 観音扉: 1枚 = W/2、ヒンジは外側の柱。縦の波板+錠の縦棒
    rod_m = C.principled(name + "Rod", (0.35, 0.36, 0.37), metallic=1.0, rough=0.35)
    for s in (-1, 1):
        hinge = bpy.data.objects.new(name + f"_Hinge{s}", None); bpy.context.collection.objects.link(hinge)
        add(hinge); hinge.location = (s * (W / 2 - 1), -1, 0)
        dw = W / 2 - 4
        door = P.box(name + f"_Door{s}", (dw, 4, H - 24), (-s * dw / 2, -2, H / 2), mat=paint, bevel=0.6)
        door.parent = hinge
        # 扉の外面の縦リブ
        for i in range(4):
            rb = P.box(name + f"_DRib{s}{i}", (7, 3, H - 60), (-s * (14 + i * (dw - 28) / 3), -5, H / 2), mat=paint, bevel=0.8)
            rb.parent = hinge
        for i in range(2):
            rx = -s * (dw * (0.3 + 0.45 * i))
            r = P.cyl(name + f"_Rod{s}{i}", 1.6, H - 20, (rx, -8.5, H / 2), mat=rod_m, verts=12)
            r.parent = hinge
            for zz in (60, H - 60):
                g = P.box(name + f"_RodG{s}{i}{zz}", (8, 5, 4), (rx, -7, zz), mat=rod_m)
                g.parent = hinge
        hinge.rotation_euler.z = math.radians(s * door_deg)
    return root


def mat_plank(name):
    """コンテナの床(合板の板目)。"""
    return P.mat_wood(name, base=(0.36, 0.24, 0.14), dark=(0.20, 0.12, 0.06), scale=0.05, rough=0.6)


# ------------------------------------------------------------------ ウエス・歯車
def mat_cotton(name, color, pattern=None, color2=(0.9, 0.9, 0.88), scale=0.5, rough=0.9):
    """綿の布(ウエス): 平織りの細かいバンプ+色ムラ。pattern: None / "stripe" / "check" / "dot"。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    base = n.new("ShaderNodeMix"); base.data_type = "RGBA"
    base.inputs["A"].default_value = (*color, 1); base.inputs["B"].default_value = (*color2, 1)
    if pattern == "stripe":
        wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "Y"
        wv.inputs["Scale"].default_value = scale; wv.inputs["Distortion"].default_value = 0
        C.link(nt, tc.outputs["Object"], wv.inputs["Vector"])
        th = n.new("ShaderNodeMath"); th.operation = "GREATER_THAN"; th.inputs[1].default_value = 0.6
        C.link(nt, wv.outputs["Fac"], th.inputs[0]); C.link(nt, th.outputs[0], base.inputs["Factor"])
    elif pattern == "check":
        ck = n.new("ShaderNodeTexChecker"); ck.inputs["Scale"].default_value = scale
        ck.inputs["Color1"].default_value = (1, 1, 1, 1); ck.inputs["Color2"].default_value = (0, 0, 0, 1)
        C.link(nt, tc.outputs["Object"], ck.inputs["Vector"])
        mr = n.new("ShaderNodeMapRange"); mr.inputs["To Max"].default_value = 0.75
        C.link(nt, ck.outputs["Fac"], mr.inputs["Value"]); C.link(nt, mr.outputs["Result"], base.inputs["Factor"])
    elif pattern == "dot":
        vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = scale; vo.inputs["Randomness"].default_value = 0
        C.link(nt, tc.outputs["Object"], vo.inputs["Vector"])
        th = n.new("ShaderNodeMath"); th.operation = "LESS_THAN"; th.inputs[1].default_value = 0.22
        C.link(nt, vo.outputs["Distance"], th.inputs[0]); C.link(nt, th.outputs[0], base.inputs["Factor"])
    else:
        base.inputs["Factor"].default_value = 0.0
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.3; nz.inputs["Detail"].default_value = 3
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    shade = n.new("ShaderNodeMapRange"); shade.inputs["To Min"].default_value = 0.8; shade.inputs["To Max"].default_value = 1.05
    C.link(nt, nz.outputs["Fac"], shade.inputs["Value"])
    mul = n.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
    C.link(nt, base.outputs["Result"], mul.inputs["A"]); C.link(nt, shade.outputs["Result"], mul.inputs["B"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = rough
    p.inputs["Sheen Weight"].default_value = 0.35; p.inputs["Sheen Roughness"].default_value = 0.35
    C.link(nt, mul.outputs["Result"], p.inputs["Base Color"])
    # 平織り(縦横の細い波)
    w1 = n.new("ShaderNodeTexWave"); w1.wave_type = "BANDS"; w1.bands_direction = "X"; w1.inputs["Scale"].default_value = 30
    w2 = n.new("ShaderNodeTexWave"); w2.wave_type = "BANDS"; w2.bands_direction = "Y"; w2.inputs["Scale"].default_value = 30
    for w in (w1, w2):
        w.inputs["Distortion"].default_value = 0.5
        C.link(nt, tc.outputs["Object"], w.inputs["Vector"])
    ad = n.new("ShaderNodeMath"); ad.operation = "ADD"
    C.link(nt, w1.outputs["Fac"], ad.inputs[0]); C.link(nt, w2.outputs["Fac"], ad.inputs[1])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.25; b.inputs["Distance"].default_value = 0.03
    C.link(nt, ad.outputs[0], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def rag_mesh(name, rnd, size=30.0, res=20, crumple=0.6, fray=0.6):
    """四角いウエス(格子メッシュ)。縁は少しガタガタ(切りっぱなし)、面はゆるいしわ。原点=中心。"""
    bm = bmesh.new()
    vs = []
    ph = [rnd.uniform(0, math.tau) for _ in range(6)]
    for j in range(res + 1):
        row = []
        for i in range(res + 1):
            u, v = i / res - 0.5, j / res - 0.5
            x, y = u * size, v * size
            edge = (i in (0, res)) or (j in (0, res))
            if edge:   # 切りっぱなしの縁
                x += rnd.uniform(-fray, fray) * 0.5; y += rnd.uniform(-fray, fray) * 0.5
            z = crumple * (math.sin(0.35 * x + ph[0]) * math.cos(0.3 * y + ph[1]) + 0.5 * math.sin(0.7 * (x - y) + ph[2]))
            row.append(bm.verts.new((x, y, z)))
        vs.append(row)
    for j in range(res):
        for i in range(res):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def gear_mesh(name, teeth=24, r_root=10.0, r_tip=11.6, width=4.0, r_hub=4.0, r_bore=1.6, hub_h=2.0, spokes=0):
    """平歯車(Z 軸、下面 z=0)。台形の歯+中央のハブ+軸穴。"""
    bm = bmesh.new()
    prof = []
    for k in range(teeth):
        a0 = k * math.tau / teeth
        da = math.tau / teeth
        for t, r in ((0.0, r_root), (0.18, r_root), (0.32, r_tip), (0.55, r_tip), (0.69, r_root)):
            prof.append((a0 + t * da, r))
    pts = [(r * math.cos(a), r * math.sin(a)) for a, r in prof]
    inner = [(r_bore * math.cos(a), r_bore * math.sin(a)) for a, _ in prof]
    for z in (0.0, width):
        pass
    lo = [bm.verts.new((x, y, 0)) for x, y in pts]
    hi = [bm.verts.new((x, y, width)) for x, y in pts]
    ilo = [bm.verts.new((x, y, 0)) for x, y in inner]
    ihi = [bm.verts.new((x, y, width + hub_h)) for x, y in inner]
    N = len(pts)
    for i in range(N):
        j = (i + 1) % N
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))           # 外周
        bm.faces.new((ilo[j], ilo[i], ihi[i], ihi[j]))       # 軸穴
        bm.faces.new((lo[j], lo[i], ilo[i], ilo[j]))         # 下面
    # 上面: 歯の面 → ハブ(段差)
    hub_lo = [bm.verts.new((r_hub * math.cos(a), r_hub * math.sin(a), width)) for a, _ in prof]
    hub_hi = [bm.verts.new((r_hub * math.cos(a), r_hub * math.sin(a), width + hub_h)) for a, _ in prof]
    for i in range(N):
        j = (i + 1) % N
        bm.faces.new((hi[i], hi[j], hub_lo[j], hub_lo[i]))
        bm.faces.new((hub_lo[i], hub_lo[j], hub_hi[j], hub_hi[i]))
        bm.faces.new((hub_hi[i], hub_hi[j], ihi[j], ihi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return me


def mat_oily_metal(name, coord_obj=None, axis="X", wipe_dir=1.0):
    """油で汚れた金属 → ふいたところだけ光る鋼。"Wipe" 値ノード(オブジェクト座標 cm)をキーフレームすると、
    axis 方向に Wipe の位置までが「ふき取り済み」になる(wipe_dir=-1 で逆向き)。境目は少しにじむ。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    if coord_obj is not None:
        tc.object = coord_obj
    sep = n.new("ShaderNodeSeparateXYZ"); C.link(nt, tc.outputs["Object"], sep.inputs["Vector"])
    # 汚れ側: 黒茶の油膜(ムラ・垂れ)+ところどころ鈍い金属
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.25; nz.inputs["Detail"].default_value = 8
    nz.inputs["Roughness"].default_value = 0.65
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    crd = n.new("ShaderNodeValToRGB")
    e = crd.color_ramp.elements
    e[0].position = 0.4; e[0].color = (0.012, 0.009, 0.005, 1)
    e[1].position = 0.75; e[1].color = (0.09, 0.06, 0.03, 1)
    C.link(nt, nz.outputs["Fac"], crd.inputs["Fac"])
    dirty = n.new("ShaderNodeBsdfPrincipled")
    dirty.inputs["Metallic"].default_value = 0.2; dirty.inputs["Roughness"].default_value = 0.4
    dirty.inputs["Coat Weight"].default_value = 0.8; dirty.inputs["Coat Roughness"].default_value = 0.12
    C.link(nt, crd.outputs["Color"], dirty.inputs["Base Color"])
    gb = n.new("ShaderNodeBump"); gb.inputs["Strength"].default_value = 0.35; gb.inputs["Distance"].default_value = 0.3
    C.link(nt, nz.outputs["Fac"], gb.inputs["Height"]); C.link(nt, gb.outputs["Normal"], dirty.inputs["Normal"])
    # きれい側: 研磨鋼(細かいヘアライン)
    clean = n.new("ShaderNodeBsdfPrincipled")
    clean.inputs["Base Color"].default_value = (0.42, 0.42, 0.43, 1)
    clean.inputs["Metallic"].default_value = 1.0
    fz = n.new("ShaderNodeTexNoise"); fz.inputs["Scale"].default_value = 3.0; fz.inputs["Detail"].default_value = 6
    C.link(nt, tc.outputs["Object"], fz.inputs["Vector"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.05; rr.inputs["To Max"].default_value = 0.14
    C.link(nt, fz.outputs["Fac"], rr.inputs["Value"]); C.link(nt, rr.outputs["Result"], clean.inputs["Roughness"])
    # マスク
    wp = n.new("ShaderNodeValue"); wp.name = "Wipe"; wp.outputs[0].default_value = -1000.0
    jit = n.new("ShaderNodeTexNoise"); jit.inputs["Scale"].default_value = 0.6; jit.inputs["Detail"].default_value = 3
    C.link(nt, tc.outputs["Object"], jit.inputs["Vector"])
    pos = n.new("ShaderNodeMath"); pos.operation = "MULTIPLY"; pos.inputs[1].default_value = wipe_dir
    C.link(nt, sep.outputs[axis], pos.inputs[0])
    pj = n.new("ShaderNodeMath"); pj.operation = "MULTIPLY_ADD"; pj.inputs[1].default_value = 3.0
    C.link(nt, jit.outputs["Fac"], pj.inputs[0]); C.link(nt, pos.outputs[0], pj.inputs[2])
    d = n.new("ShaderNodeMath"); d.operation = "SUBTRACT"
    C.link(nt, wp.outputs[0], d.inputs[0]); C.link(nt, pj.outputs[0], d.inputs[1])
    mk = n.new("ShaderNodeMapRange"); mk.inputs["From Min"].default_value = 0.0; mk.inputs["From Max"].default_value = 1.2
    mk.interpolation_type = "SMOOTHSTEP"
    C.link(nt, d.outputs[0], mk.inputs["Value"])
    # 磨いた面の映り込み(EEVEE は画面外を映せないので、反射ベクトルから天井の照明列を描く)
    env = F.fake_env(nt, strength=0.6, rows=1.6, duty=0.14, sky=(0.16, 0.15, 0.14), floor=(0.02, 0.02, 0.02),
                     lamp=(3.0, 2.8, 2.5), along_x=0.8, structure=0.7)
    cadd = n.new("ShaderNodeAddShader")
    C.link(nt, clean.outputs["BSDF"], cadd.inputs[0]); C.link(nt, env.outputs["Emission"], cadd.inputs[1])
    mx = n.new("ShaderNodeMixShader")
    C.link(nt, mk.outputs["Result"], mx.inputs["Fac"])
    C.link(nt, dirty.outputs["BSDF"], mx.inputs[1]); C.link(nt, cadd.outputs["Shader"], mx.inputs[2])
    C.link(nt, mx.outputs["Shader"], out.inputs["Surface"])
    return m, wp.outputs[0]


# ------------------------------------------------------------------ 反毛の繊維
def fiber_mesh(name, rnd, length=2.4, radius=0.035, curl=0.35, segs=14, sides=4):
    """くるっと曲がった短い繊維(細い管)。原点=中心。"""
    pts = []
    a0 = rnd.uniform(0, math.tau)
    w = rnd.uniform(2.5, 5.0)
    for i in range(segs + 1):
        t = i / segs - 0.5
        x = t * length
        y = curl * math.sin(w * t * math.pi + a0)
        z = curl * math.cos(w * t * math.pi * 0.7 + a0) * 0.8
        pts.append(Vector((x, y, z)))
    bm = bmesh.new()
    rings = []
    for i, p in enumerate(pts):
        tng = (pts[min(i + 1, segs)] - pts[max(i - 1, 0)]).normalized()
        ax = tng.orthogonal().normalized(); ay = tng.cross(ax)
        rr = radius * (0.5 if i in (0, segs) else 1.0)
        rings.append([bm.verts.new(p + rr * (math.cos(k * math.tau / sides) * ax + math.sin(k * math.tau / sides) * ay))
                      for k in range(sides)])
    for i in range(segs):
        for k in range(sides):
            k2 = (k + 1) % sides
            bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def mat_fiber(name, color, rough=0.7):
    """繊維: 細いので明るめ+裏から光が抜ける(Translucent を少し)。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Sheen Weight"].default_value = 0.6; p.inputs["Sheen Roughness"].default_value = 0.3
    tr = n.new("ShaderNodeBsdfTranslucent"); tr.inputs["Color"].default_value = (*color, 1)
    mx = n.new("ShaderNodeMixShader"); mx.inputs["Fac"].default_value = 0.3
    C.link(nt, p.outputs["BSDF"], mx.inputs[1]); C.link(nt, tr.outputs["BSDF"], mx.inputs[2])
    C.link(nt, mx.outputs["Shader"], out.inputs["Surface"])
    return m


def fluff_object(name, coll, A, B, Cc, a01, b01, sA, sB, sC, rot, spin, var, center=(0, 0, 0), omega=0.02,
                 drift=6.0, drift_scale=0.04):
    """反毛の繊維群。点ごとに 3 つの位置 A(服の上)→ B(ふわふわの綿雲)→ Cc(板の中) を、
    点ごとのフレーム区間 a01=[(a0,a1)], b01=[(b0,b1)] でなめらかに移動させる(GN + シーン時間、キー不要)。
    綿雲の間は center を軸に Z 回転(omega rad/フレーム)+ノイズで漂い、繊維自身もくるくる回る(spin)。
    スケールは sA→sB→sC。"""
    n = len(A)
    me = bpy.data.meshes.new(name + "Pts")
    me.vertices.add(n)
    me.vertices.foreach_set("co", np.asarray(A, dtype=np.float32).ravel())

    def put(nm, dt, data):
        a = me.attributes.new(nm, dt, "POINT")
        if dt == "FLOAT_VECTOR":
            a.data.foreach_set("vector", np.asarray(data, dtype=np.float32).ravel())
        else:
            a.data.foreach_set("value", np.asarray(data, dtype=np.int32 if dt == "INT" else np.float32))
    put("pB", "FLOAT_VECTOR", B); put("pC", "FLOAT_VECTOR", Cc)
    a01 = np.asarray(a01, dtype=np.float32); b01 = np.asarray(b01, dtype=np.float32)
    put("a0", "FLOAT", a01[:, 0]); put("a1", "FLOAT", a01[:, 1]); put("b0", "FLOAT", b01[:, 0]); put("b1", "FLOAT", b01[:, 1])
    put("sA", "FLOAT", sA); put("sB", "FLOAT", sB); put("sC", "FLOAT", sC)
    put("rot", "FLOAT_VECTOR", rot); put("spin", "FLOAT_VECTOR", spin); put("var", "INT", var)
    me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)

    ng = bpy.data.node_groups.new(name + "GN", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nd = ng.nodes; L = ng.links.new
    gi = nd.new("NodeGroupInput"); go = nd.new("NodeGroupOutput")

    def attr(nm, dt="FLOAT"):
        x = nd.new("GeometryNodeInputNamedAttribute"); x.data_type = dt; x.inputs["Name"].default_value = nm
        return x.outputs["Attribute"]

    def math_(op, a, b):
        x = nd.new("ShaderNodeMath"); x.operation = op
        for k, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                x.inputs[k].default_value = v
            else:
                L(v, x.inputs[k])
        return x.outputs[0]

    def vmath(op, a, b=None, scale=None):
        x = nd.new("ShaderNodeVectorMath"); x.operation = op
        L(a, x.inputs[0])
        if b is not None:
            if isinstance(b, tuple):
                x.inputs[1].default_value = b
            else:
                L(b, x.inputs[1])
        if scale is not None:
            if isinstance(scale, (int, float)):
                x.inputs["Scale"].default_value = scale
            else:
                L(scale, x.inputs["Scale"])
        return x.outputs[0]

    def lerp_v(a, b, t):
        return vmath("ADD", a, vmath("SCALE", vmath("SUBTRACT", b, a), scale=t))

    def lerp_f(a, b, t):
        return math_("ADD", a, math_("MULTIPLY", math_("SUBTRACT", b, a), t))

    def ramp(t, lo, hi):
        x = nd.new("ShaderNodeMapRange"); x.interpolation_type = "SMOOTHSTEP"; x.clamp = True
        L(t, x.inputs["Value"]); L(lo, x.inputs["From Min"]); L(hi, x.inputs["From Max"])
        return x.outputs["Result"]
    time = nd.new("GeometryNodeInputSceneTime").outputs["Frame"]
    pos0 = nd.new("GeometryNodeInputPosition").outputs["Position"]
    u = ramp(time, attr("a0"), attr("a1"))
    v = ramp(time, attr("b0"), attr("b1"))
    w = math_("MULTIPLY", u, math_("SUBTRACT", 1.0, v))
    # 綿雲: center 軸で回転+ノイズで漂う
    rotn = nd.new("ShaderNodeVectorRotate"); rotn.rotation_type = "Z_AXIS"
    rotn.inputs["Center"].default_value = center
    L(attr("pB", "FLOAT_VECTOR"), rotn.inputs["Vector"]); L(math_("MULTIPLY", time, omega), rotn.inputs["Angle"])
    nz = nd.new("ShaderNodeTexNoise"); nz.inputs["Detail"].default_value = 1.0; nz.inputs["Scale"].default_value = 1.0
    nzv = vmath("ADD", vmath("SCALE", attr("pB", "FLOAT_VECTOR"), scale=drift_scale),
                vmath("SCALE", _const_vec(nd, (0.0, 0.0, 1.0)), scale=math_("MULTIPLY", time, 0.012)))
    L(nzv, nz.inputs["Vector"])
    dv = vmath("SCALE", vmath("SUBTRACT", nz.outputs["Color"], (0.5, 0.5, 0.5)), scale=drift * 2)
    Bt = vmath("ADD", rotn.outputs["Vector"], dv)
    pos = lerp_v(pos0, Bt, u)
    pos = lerp_v(pos, attr("pC", "FLOAT_VECTOR"), v)
    sp = nd.new("GeometryNodeSetPosition")
    L(gi.outputs[0], sp.inputs["Geometry"]); L(pos, sp.inputs["Position"])
    s = lerp_f(attr("sA"), attr("sB"), u)
    s = lerp_f(s, attr("sC"), v)
    r = vmath("ADD", attr("rot", "FLOAT_VECTOR"), vmath("SCALE", attr("spin", "FLOAT_VECTOR"), scale=math_("MULTIPLY", time, w)))
    e2r = nd.new("FunctionNodeEulerToRotation"); L(r, e2r.inputs["Euler"])
    sel = math_("MULTIPLY", math_("GREATER_THAN", s, 0.02), math_("GREATER_THAN", time, attr("a0")))   # 出番前は隠す
    ci = nd.new("GeometryNodeCollectionInfo"); ci.inputs["Collection"].default_value = coll
    ci.inputs["Separate Children"].default_value = True; ci.inputs["Reset Children"].default_value = True
    ci.transform_space = "ORIGINAL"
    iop = nd.new("GeometryNodeInstanceOnPoints")
    L(sp.outputs["Geometry"], iop.inputs["Points"]); L(sel, iop.inputs["Selection"])
    L(ci.outputs["Instances"], iop.inputs["Instance"]); iop.inputs["Pick Instance"].default_value = True
    L(attr("var", "INT"), iop.inputs["Instance Index"]); L(e2r.outputs["Rotation"], iop.inputs["Rotation"])
    L(s, iop.inputs["Scale"])
    L(iop.outputs["Instances"], go.inputs[0])
    mod = o.modifiers.new("Fluff", "NODES"); mod.node_group = ng
    return o


def _const_vec(nd, v):
    x = nd.new("FunctionNodeInputVector"); x.vector = v
    return x.outputs[0]
