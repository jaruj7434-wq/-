"""造幣工程ショット(H03〜H07, H11)用の工場部品・マテリアル。

common.py / props.py には手を入れず、ここに工場系の補助を置く。単位 1BU=1cm。
"""
import math, random

import bpy
from mathutils import Vector

import common as C
import props as P


# ------------------------------------------------------------------ アニメ補助
def fcurves(idblock):
    ad = getattr(idblock, "animation_data", None)
    if not ad or not ad.action:
        return []
    try:
        return list(ad.action.fcurves)
    except AttributeError:
        return [fc for layer in ad.action.layers for strip in layer.strips
                for bag in strip.channelbags for fc in bag.fcurves]


def set_interp(idblock, interp="LINEAR", path=None):
    for fc in fcurves(idblock):
        if path is None or path in fc.data_path:
            for kp in fc.keyframe_points:
                kp.interpolation = interp


def key_socket(sock, frame, value):
    """ノード入力/出力ソケットの default_value をキーフレーム。"""
    sock.default_value = value
    sock.keyframe_insert("default_value", frame=frame)


def dup(src, name, loc, rot=(0, 0, 0), scale=None):
    """メッシュを共有した複製(大量配置用・軽量)。"""
    o = src.copy(); o.name = name
    bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    if scale:
        o.scale = scale
    return o


def shake(cam, frame, amp=0.08, decay=6, seed=0, axis_scale=(1, 1, 0.6)):
    """カメラ位置に衝撃の揺れを足す(既存キーの間に差し込む)。"""
    rnd = random.Random(seed)
    base = cam.location.copy()
    cam.keyframe_insert("location", frame=frame - 1)
    for i in range(decay):
        a = amp * (1 - i / decay)
        off = Vector((rnd.uniform(-a, a) * axis_scale[0], rnd.uniform(-a, a) * axis_scale[1],
                      rnd.uniform(-a, a) * axis_scale[2]))
        cam.location = base + off
        cam.keyframe_insert("location", frame=frame + i)
    cam.location = base
    cam.keyframe_insert("location", frame=frame + decay)


# ------------------------------------------------------------------ マテリアル
def mat_painted(name, color, rough=0.45, wear=0.25, scale=0.08):
    """塗装鋼(機械のフレーム)。ノイズで汚れ・塗装ハゲの金属地を混ぜる。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale * 10
    nz.inputs["Detail"].default_value = 10; nz.inputs["Roughness"].default_value = 0.65
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.3
    cr.color_ramp.elements[0].color = (color[0] * 0.55, color[1] * 0.55, color[2] * 0.55, 1)
    cr.color_ramp.elements[1].position = 0.7; cr.color_ramp.elements[1].color = (*color, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled")
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    # 角や擦れ: 細かいノイズで金属地
    nz2 = n.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = scale * 60; nz2.inputs["Detail"].default_value = 6
    C.link(nt, tc.outputs["Object"], nz2.inputs["Vector"])
    cr2 = n.new("ShaderNodeValToRGB")
    cr2.color_ramp.elements[0].position = 1 - wear * 0.6; cr2.color_ramp.elements[1].position = 1 - wear * 0.5
    C.link(nt, nz2.outputs["Fac"], cr2.inputs["Fac"])
    C.link(nt, cr2.outputs["Color"], p.inputs["Metallic"])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = rough * 0.8; mr.inputs["To Max"].default_value = rough * 1.3
    C.link(nt, nz.outputs["Fac"], mr.inputs["Value"]); C.link(nt, mr.outputs["Result"], p.inputs["Roughness"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.08
    C.link(nt, nz2.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def mat_steel(name, color=(0.62, 0.63, 0.65), rough=0.12, aniso=0.0, streak_axis="X", coord_obj=None):
    """研磨鋼・アルミ板。streak でヘアライン(研磨目)。coord_obj を渡すとその物体基準のテクスチャ(流れる板用)。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    if coord_obj is not None:
        tc.object = coord_obj
    mp = n.new("ShaderNodeMapping")
    s = {"X": (0.02, 3.0, 3.0), "Y": (3.0, 0.02, 3.0), "Z": (3.0, 3.0, 0.02)}[streak_axis]
    mp.inputs["Scale"].default_value = s
    C.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 6; nz.inputs["Detail"].default_value = 12
    C.link(nt, mp.outputs["Vector"], nz.inputs["Vector"])
    big = n.new("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 0.12; big.inputs["Detail"].default_value = 4
    C.link(nt, tc.outputs["Object"], big.inputs["Vector"])
    p = n.new("ShaderNodeBsdfPrincipled")
    p.inputs["Metallic"].default_value = 1.0
    if aniso and "Anisotropic" in p.inputs:
        p.inputs["Anisotropic"].default_value = aniso
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (color[0] * 0.8, color[1] * 0.8, color[2] * 0.8, 1)
    cr.color_ramp.elements[1].color = (*color, 1)
    C.link(nt, big.outputs["Fac"], cr.inputs["Fac"]); C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = rough * 0.6; mr.inputs["To Max"].default_value = rough * 1.8
    C.link(nt, nz.outputs["Fac"], mr.inputs["Value"])
    mr2 = n.new("ShaderNodeMath"); mr2.operation = "ADD"
    bigr = n.new("ShaderNodeMapRange"); bigr.inputs["To Min"].default_value = 0; bigr.inputs["To Max"].default_value = rough * 0.8
    C.link(nt, big.outputs["Fac"], bigr.inputs["Value"])
    C.link(nt, mr.outputs["Result"], mr2.inputs[0]); C.link(nt, bigr.outputs["Result"], mr2.inputs[1])
    C.link(nt, mr2.outputs[0], p.inputs["Roughness"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.04
    C.link(nt, nz.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m, mp


def mat_concrete(name, color=(0.32, 0.31, 0.29), rough=0.8, scale=0.02):
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale * 10; nz.inputs["Detail"].default_value = 12
    nz.inputs["Roughness"].default_value = 0.7
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (color[0] * 0.6, color[1] * 0.6, color[2] * 0.6, 1)
    cr.color_ramp.elements[1].color = (color[0] * 1.15, color[1] * 1.15, color[2] * 1.15, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled")
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = rough * 0.55; mr.inputs["To Max"].default_value = rough
    C.link(nt, nz.outputs["Fac"], mr.inputs["Value"]); C.link(nt, mr.outputs["Result"], p.inputs["Roughness"])
    fine = n.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = scale * 400
    C.link(nt, tc.outputs["Object"], fine.inputs["Vector"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.15
    C.link(nt, fine.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def mat_canvas(name, color=(0.55, 0.47, 0.34), weave=3.0, rough=0.9):
    """麻・帆布(織り目のバンプ+色ムラ)。weave は 1cm あたりの糸本数。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = rough
    if "Sheen Weight" in p.inputs:
        p.inputs["Sheen Weight"].default_value = 0.4
    w1 = n.new("ShaderNodeTexWave"); w1.wave_type = "BANDS"; w1.bands_direction = "X"
    w1.inputs["Scale"].default_value = weave; w1.inputs["Distortion"].default_value = 0.5
    w2 = n.new("ShaderNodeTexWave"); w2.wave_type = "BANDS"; w2.bands_direction = "Z"
    w2.inputs["Scale"].default_value = weave; w2.inputs["Distortion"].default_value = 0.5
    for w in (w1, w2):
        C.link(nt, tc.outputs["Object"], w.inputs["Vector"])
    mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    C.link(nt, w1.outputs["Fac"], mul.inputs[0]); C.link(nt, w2.outputs["Fac"], mul.inputs[1])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.2; nz.inputs["Detail"].default_value = 6
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (color[0] * 0.65, color[1] * 0.62, color[2] * 0.58, 1)
    cr.color_ramp.elements[1].color = (color[0] * 1.1, color[1] * 1.1, color[2] * 1.05, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.35; b.inputs["Distance"].default_value = 0.05
    C.link(nt, mul.outputs[0], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def mat_rubber(name, color=(0.035, 0.035, 0.037), rough=0.7, coord_obj=None, scale=0.6):
    """コンベアベルトなどのゴム。coord_obj 基準でテクスチャが流れる。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    if coord_obj is not None:
        tc.object = coord_obj
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 8
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*color, 1)
    cr.color_ramp.elements[1].color = (color[0] * 2.5, color[1] * 2.5, color[2] * 2.5, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled")
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = rough * 0.7; mr.inputs["To Max"].default_value = rough
    C.link(nt, nz.outputs["Fac"], mr.inputs["Value"]); C.link(nt, mr.outputs["Result"], p.inputs["Roughness"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def mat_blackbody_emit(name, temp, strength):
    return C.emissive(name, temp=temp, strength=strength)


# ------------------------------------------------------------------ 形状
def ring(name, r_out, r_in, depth, loc=(0, 0, 0), mat=None, verts=96, bevel=0.0, rot=(0, 0, 0)):
    """中空円筒(ドーナツ状の板・炉の縁など)。"""
    outer = P.cyl(name, r_out, depth, loc, rot, None, verts)
    inner = P.cyl(name + "_cut", r_in, depth * 3, loc, rot, None, verts)
    b = outer.modifiers.new("cut", "BOOLEAN"); b.object = inner; b.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = outer
    bpy.ops.object.modifier_apply(modifier="cut")
    bpy.data.objects.remove(inner)
    if bevel:
        P.add_mod(outer, "BEVEL", width=bevel, segments=3, limit_method="ANGLE")
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    if mat:
        outer.data.materials.append(mat)
    return outer


def haze(size, loc, density=0.0015, color=(0.9, 0.8, 0.7), anisotropy=0.3):
    """もや(EEVEEのボリューム)。光源の光筋が少し見える程度の薄さで。"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = "Haze"
    o.scale = size
    m, nt, out = C.node_mat("HazeM")
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = density
    v.inputs["Color"].default_value = (*color, 1)
    v.inputs["Anisotropy"].default_value = anisotropy
    C.link(nt, v.outputs["Volume"], out.inputs["Volume"])
    o.data.materials.append(m)
    o.visible_shadow = False
    return o


def spot(loc, target, energy, color=(1, 0.85, 0.65), size_deg=45, blend=0.4, radius=2.0, name="Spot"):
    bpy.ops.object.light_add(type="SPOT", location=loc)
    l = bpy.context.object; l.name = name
    l.data.energy = energy; l.data.color = color
    l.data.spot_size = math.radians(size_deg); l.data.spot_blend = blend
    l.data.shadow_soft_size = radius
    C.light_look_at(l, target)
    return l


def factory_hall(size=(4000, 3000, 900), floor_mat=None, wall_color=(0.22, 0.23, 0.24), lamp_rows=None,
                 lamp_strength=40.0, lamp_temp=3600, center=(0, 0, 0)):
    """背景用の工場建屋: 床・奥壁・柱・天井の照明列(発光板)。"""
    cx, cy, cz = center
    sx, sy, sz = size
    floor = P.plane("Floor", (sx, sy), (cx, cy, cz), mat=floor_mat or mat_concrete("Concrete"))
    wall_m = mat_painted("WallM", wall_color, rough=0.7, wear=0.05, scale=0.01)
    P.plane("BackWall", (sx, sz), (cx, cy + sy / 2, cz + sz / 2), rot=(90, 0, 0), mat=wall_m)
    P.plane("Ceiling", (sx, sy), (cx, cy, cz + sz), rot=(180, 0, 0), mat=wall_m)
    col_m = mat_painted("ColumnM", (0.30, 0.32, 0.30), rough=0.55, wear=0.15, scale=0.02)
    for i in range(-4, 5):
        P.box(f"Col{i}", (40, 40, sz), (cx + i * sx / 9, cy + sy / 2 - 40, cz + sz / 2), mat=col_m)
    lamp_m = C.emissive("LampM", temp=lamp_temp, strength=lamp_strength)
    lamps = []
    for (y, n) in (lamp_rows or [(cy, 8)]):
        for i in range(n):
            x = cx - sx / 2 + (i + 0.5) * sx / n
            l = P.box(f"Lamp{y}_{i}", (120, 30, 6), (x, y, cz + sz - 60), mat=lamp_m)
            lamps.append(l)
    return floor, lamps
