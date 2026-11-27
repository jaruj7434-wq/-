"""
らせん滑り台 — Blender シーン生成スクリプト(企画 #02)

黒大理石の柱に、白大理石のらせんスロープ(下に行くほどカーブがきつくなる)。
上から棒が滑り込み、SOFT が上がるほど素材が 鉄→鋼→真鍮→金→液体の金 に変わり、
曲がれる距離が伸びる。100% はゴールの金のカップにホールインワン。

使い方:
  blender -b -P spiral_slide.py -- --soft 50 --report
  blender -b -P spiral_slide.py -- --soft 50 --render render/s50/f_
"""
import sys
import math
import argparse

import bpy
import bmesh
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("--soft", type=float, default=50)
ap.add_argument("--frames", type=int, default=150)
ap.add_argument("--preview", action="store_true")
ap.add_argument("--res", type=str, default=None)
ap.add_argument("--samples", type=int, default=None)
ap.add_argument("--still", type=int, default=None)
ap.add_argument("--step", type=int, default=1)
ap.add_argument("--start", type=int, default=1, help="書き出し開始フレーム(シミュレーションは常に 1 から)")
ap.add_argument("--render", type=str, default=None)
ap.add_argument("--save", type=str, default=None)
ap.add_argument("--report", action="store_true")
# 調整用
ap.add_argument("--k", type=float, default=None)
ap.add_argument("--bend", type=float, default=None)
ap.add_argument("--fric", type=float, default=None)
ap.add_argument("--ch", type=float, default=None)
ap.add_argument("--rbot", type=float, default=None)
args = ap.parse_args(argv)
SOFT = max(0.0, min(100.0, args.soft)) / 100.0


def lerp(a, b, t):
    return a + (b - a) * t


def loglerp(a, b, t):
    return 10 ** lerp(math.log10(a), math.log10(b), t)


# ----------------------------------------------------------------------------
# らせんの形
# ----------------------------------------------------------------------------
TURNS = 1.75
Z_TOP, Z_BOT = 3.25, 0.85
END_ANGLE = math.radians(-65)   # 出口がカメラ手前右に来る角度
R_TOP, R_BOT = 0.78, (args.rbot or 0.34)      # 下に行くほど半径が小さい = カーブがきつい
CH_R = args.ch or 0.13         # 溝(U字)の半径
ROD_LEN, ROD_R = 0.66, 0.082   # 棒の長さ・太さ
N_PATH = 360


def helix(u):
    """u: 0(上)〜1(下)"""
    a = END_ANGLE - (1 - u) * TURNS * 2 * math.pi
    r = lerp(R_TOP, R_BOT, u)
    z = lerp(Z_TOP, Z_BOT, u)
    return Vector((r * math.cos(a), r * math.sin(a), z))


def frame(u, du=1e-4):
    p = helix(u)
    t = (helix(min(1, u + du)) - helix(max(0, u - du))).normalized()
    up = Vector((0, 0, 1))
    up = (up - t * up.dot(t)).normalized()
    side = t.cross(up).normalized()
    return p, t, up, side


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, args.frames
scene.render.fps = 30


def link(o):
    scene.collection.objects.link(o)
    return o


def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def cylinder(name, r, depth, loc, segs=96, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r,
                          radius2=r if r2 is None else r2, depth=depth)
    o = mesh_obj(name, bm)
    o.location = loc
    return o


def apply_mods(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    o.modifiers.clear()
    old = o.data
    o.data = me
    bpy.data.meshes.remove(old)


def shade_smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True


# ----------------------------------------------------------------------------
# マテリアル
# ----------------------------------------------------------------------------
def principled(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat, mat.node_tree, mat.node_tree.nodes.get("Principled BSDF")


def marble(name, base, vein, vein_w=0.012, rough=0.18):
    mat, nt, b = principled(name)
    N, L = nt.nodes, nt.links
    tc = N.new("ShaderNodeTexCoord")

    def layer(scale, dist, width, off):
        mp = N.new("ShaderNodeMapping")
        mp.inputs["Location"].default_value = (off, off * 0.7, off * 0.3)
        mp.inputs["Rotation"].default_value = (0.3, 0.2, 0.6 + off)
        L.new(tc.outputs["Object"], mp.inputs["Vector"])
        nz = N.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 1.3
        nz.inputs["Detail"].default_value = 14
        nz.inputs["Roughness"].default_value = 0.65
        L.new(mp.outputs["Vector"], nz.inputs["Vector"])
        mx = N.new("ShaderNodeMix")
        mx.data_type = "VECTOR"
        mx.inputs["Factor"].default_value = 0.5
        L.new(mp.outputs["Vector"], mx.inputs[4])
        L.new(nz.outputs["Color"], mx.inputs[5])
        wv = N.new("ShaderNodeTexWave")
        wv.inputs["Scale"].default_value = scale
        wv.inputs["Distortion"].default_value = dist
        wv.inputs["Detail"].default_value = 12
        wv.inputs["Detail Roughness"].default_value = 0.75
        L.new(mx.outputs[1], wv.inputs["Vector"])
        rp = N.new("ShaderNodeValToRGB")
        rp.color_ramp.interpolation = "EASE"
        rp.color_ramp.elements[0].color = (1, 1, 1, 1)
        rp.color_ramp.elements[1].position = width
        rp.color_ramp.elements[1].color = (0, 0, 0, 1)
        L.new(wv.outputs["Fac"], rp.inputs["Fac"])
        return rp

    v1 = layer(0.7, 7.0, vein_w, 0.0)
    v2 = layer(2.0, 10.0, vein_w * 0.5, 3.1)
    m2 = N.new("ShaderNodeMath")
    m2.operation = "MULTIPLY"
    m2.inputs[1].default_value = 0.45
    L.new(v2.outputs["Color"], m2.inputs[0])
    mxm = N.new("ShaderNodeMath")
    mxm.operation = "MAXIMUM"
    L.new(v1.outputs["Color"], mxm.inputs[0])
    L.new(m2.outputs[0], mxm.inputs[1])
    col = N.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs[6].default_value = (*base, 1)
    col.inputs[7].default_value = (*vein, 1)
    L.new(mxm.outputs[0], col.inputs["Factor"])
    L.new(col.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = 0.7
    b.inputs["Coat Roughness"].default_value = 0.04
    return mat


def metal(name, color, rough, coat=0.0):
    mat, nt, b = principled(name)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    return mat


def mat_object(soft):
    """SOFT に応じて 鉄 → 鋼 → 真鍮 → 金 → 液体の金"""
    keys = [  # (soft, 色, 粗さ)
        (0.00, (0.035, 0.035, 0.038), 0.55),   # 黒い鍛造鉄
        (0.25, (0.55, 0.56, 0.58), 0.22),   # 鋼
        (0.50, (0.80, 0.62, 0.33), 0.18),   # 真鍮
        (0.75, (1.00, 0.72, 0.36), 0.10),   # 金
        (1.00, (1.00, 0.70, 0.30), 0.03),   # 液体の金
    ]
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        if a[0] <= soft <= b[0]:
            t = (soft - a[0]) / (b[0] - a[0])
            col = tuple(lerp(x, y, t) for x, y in zip(a[1], b[1]))
            rough = lerp(a[2], b[2], t)
            break
    mat, nt, bs = principled("ObjectMetal")
    N, L = nt.nodes, nt.links
    bs.inputs["Base Color"].default_value = (*col, 1)
    bs.inputs["Metallic"].default_value = 1.0
    bs.inputs["Coat Weight"].default_value = 0.6 if soft >= 0.99 else 0.0
    # 鉄らしいムラ(硬い段階ほど強い)
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 40.0
    nz.inputs["Detail"].default_value = 10
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough * (1 - 0.5 * (1 - soft))
    mr.inputs["To Max"].default_value = rough * (1 + 0.6 * (1 - soft))
    L.new(nz.outputs["Fac"], mr.inputs["Value"])
    L.new(mr.outputs["Result"], bs.inputs["Roughness"])
    return mat


M_BLACK = marble("BlackMarble", (0.010, 0.010, 0.011), (0.70, 0.68, 0.64))
M_WHITE = marble("WhiteMarble", (0.80, 0.78, 0.75), (0.20, 0.19, 0.19), 0.02, 0.15)
M_GOLD = metal("GoldBrushed", (1.0, 0.72, 0.36), 0.25)
M_BACK = principled("Backdrop")[0]
M_BACK.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.10, 0.078, 0.064, 1)
M_BACK.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9


def assign(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)


# ----------------------------------------------------------------------------
# 背景
# ----------------------------------------------------------------------------
prof = [(y, 0.0) for y in [-14, -10, -6, -4, -3]]
for i in range(1, 25):
    a = (i / 24) * (math.pi / 2)
    prof.append((-3 + 3 * math.sin(a), 3 - 3 * math.cos(a)))
prof += [(0.0, 6.0), (0.0, 14.0)]
prof = [(y + 3.2, z) for y, z in prof]
bm = bmesh.new()
rows = [[bm.verts.new((x, y, z)) for y, z in prof] for x in (-14, 14)]
for i in range(len(prof) - 1):
    bm.faces.new((rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1]))
backdrop = mesh_obj("Backdrop", bm)
shade_smooth(backdrop)
assign(backdrop, M_BACK)

# ----------------------------------------------------------------------------
# 中心の柱(黒大理石)+ 台座
# ----------------------------------------------------------------------------
column = cylinder("Column", R_BOT - CH_R - 0.03, Z_TOP + 0.25, (0, 0, (Z_TOP + 0.25) / 2), 128)
assign(column, M_BLACK)
shade_smooth(column)
cap = cylinder("ColumnCap", R_BOT - CH_R + 0.0, 0.04, (0, 0, Z_TOP + 0.27), 128)
assign(cap, M_GOLD)
shade_smooth(cap)
base = cylinder("Base", 1.05, 0.12, (0, 0, 0.06), 128)
assign(base, M_BLACK)
shade_smooth(base)
bv = base.modifiers.new("Bevel", "BEVEL")
bv.width, bv.segments = 0.015, 3

# ----------------------------------------------------------------------------
# らせんスロープ(U 字の溝を押し出し)+ 金の縁
# ----------------------------------------------------------------------------
PROF_N = 24
bm = bmesh.new()
rings = []
for i in range(N_PATH + 1):
    u = i / N_PATH
    p, t, up, side = frame(u)
    ring = []
    for j in range(PROF_N + 1):
        a = math.pi * j / PROF_N  # 0..π(下半分の半円)
        q = p + CH_R * (math.cos(a) * side - math.sin(a) * up)
        ring.append(bm.verts.new(q))
    rings.append(ring)
for i in range(N_PATH):
    for j in range(PROF_N):
        bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][j + 1], rings[i][j + 1]))
chute = mesh_obj("Chute", bm)
sol = chute.modifiers.new("Solid", "SOLIDIFY")
sol.thickness = 0.035
sol.offset = 1.0
apply_mods(chute)
shade_smooth(chute)
assign(chute, M_WHITE)

# 縁の金のライン(両側)
for sgn, nm in ((1, "RimA"), (-1, "RimB")):
    cu = bpy.data.curves.new(nm, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(N_PATH // 2)
    for i in range(N_PATH // 2 + 1):
        u = i / (N_PATH // 2)
        p, t, up, side = frame(u)
        q = p + side * sgn * (CH_R + 0.017)
        sp.points[i].co = (*q, 1)
    cu.bevel_depth = 0.014
    cu.bevel_resolution = 4
    o = link(bpy.data.objects.new(nm, cu))
    o.data.materials.append(M_GOLD)

# ゴール: 出口の先(100% の着地点)に金の器
GOAL = Vector((0.50, -0.16))
CUP_R, CUP_H = 0.33, 0.2
cup = cylinder("Cup", CUP_R, CUP_H, (GOAL.x, GOAL.y, 0.12 + CUP_H / 2), 128)
inner = cylinder("CupIn", CUP_R - 0.03, CUP_H, (GOAL.x, GOAL.y, 0.12 + CUP_H / 2 + 0.03), 128)
m = cup.modifiers.new("b", "BOOLEAN")
m.operation, m.solver, m.object = "DIFFERENCE", "EXACT", inner
apply_mods(cup)
bpy.data.objects.remove(inner)
assign(cup, M_GOLD)
shade_smooth(cup)
bv = cup.modifiers.new("Bevel", "BEVEL")
bv.width, bv.segments = 0.008, 3

colliders = [chute, column, base, cup, backdrop]
for o in colliders:
    o.modifiers.new("Collision", "COLLISION")
    o.collision.thickness_outer = 0.006
    o.collision.cloth_friction = args.fric if args.fric is not None else 0.4
    o.collision.use_culling = False

# ----------------------------------------------------------------------------
# 棒(カプセル)
# ----------------------------------------------------------------------------
bm = bmesh.new()
seg_len = 24
ring_n = 20
L_half = ROD_LEN / 2 - ROD_R
verts_rows = []
# 半球キャップ + 円筒 を回転体で作る
prof_pts = []
for i in range(7):
    a = -math.pi / 2 + (math.pi / 2) * i / 6
    prof_pts.append((-L_half + ROD_R * math.sin(a), ROD_R * math.cos(a)))
for i in range(1, seg_len):
    prof_pts.append((-L_half + 2 * L_half * i / seg_len, ROD_R))
for i in range(7):
    a = (math.pi / 2) * i / 6
    prof_pts.append((L_half + ROD_R * math.sin(a), ROD_R * math.cos(a)))
tip0 = bm.verts.new((prof_pts[0][0], 0, 0))
tip1 = bm.verts.new((prof_pts[-1][0], 0, 0))
mid = []
for x, r in prof_pts[1:-1]:
    mid.append([bm.verts.new((x, r * math.cos(2 * math.pi * k / ring_n),
                              r * math.sin(2 * math.pi * k / ring_n))) for k in range(ring_n)])
for k in range(ring_n):
    k2 = (k + 1) % ring_n
    bm.faces.new((tip0, mid[0][k2], mid[0][k]))
    bm.faces.new((tip1, mid[-1][k], mid[-1][k2]))
for i in range(len(mid) - 1):
    for k in range(ring_n):
        k2 = (k + 1) % ring_n
        bm.faces.new((mid[i][k], mid[i][k2], mid[i + 1][k2], mid[i + 1][k]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
rod = mesh_obj("Rod", bm)
shade_smooth(rod)
assign(rod, mat_object(SOFT))

# スタート位置: らせんの入り口の少し上、溝の向きに合わせる
u0 = 0.035
p0, t0, up0, side0 = frame(u0)
rot = Matrix((t0, side0, up0)).transposed()  # ローカル X を接線方向へ
rod.matrix_world = Matrix.Translation(p0 + up0 * 0.12 - t0 * 0.05) @ rot.to_4x4()

if SOFT <= 0.0:
    bpy.context.view_layer.objects.active = rod
    bpy.ops.rigidbody.world_add()
    rw = scene.rigidbody_world
    rw.point_cache.frame_end = args.frames
    rw.substeps_per_frame = 40
    rw.solver_iterations = 30
    bpy.ops.rigidbody.object_add()
    rb = rod.rigid_body
    rb.collision_shape = "CONVEX_HULL"
    rb.mass = 4.0
    rb.restitution = 0.45
    rb.friction = 0.3
    rb.collision_margin = 0.001
    for o in (chute, column, base, cup, backdrop):
        bpy.context.view_layer.objects.active = o
        bpy.ops.rigidbody.object_add()
        o.rigid_body.type = "PASSIVE"
        o.rigid_body.collision_shape = "MESH"
        o.rigid_body.restitution = 0.5
        o.rigid_body.friction = 0.3
        o.rigid_body.collision_margin = 0.001
else:
    cl = rod.modifiers.new("Cloth", "CLOTH")
    s = cl.settings
    table = [  # (SOFT%, 硬さ k, 曲げ b) — 検証済み
        (25, 10.0, 2.0),    # 鋼: 0% より少し先まで進んでから飛び出す
        (50, 2.5, 0.3),     # 真鍮: 最後まで滑るが、勢い余って器を飛び越える
        (75, 2.2, 0.06),    # 金: 器の縁に引っかかって揺れ、ギリギリで入る(焦らし)
        (100, 1.5, 0.02),   # 液体の金: ホールインワン
    ]
    sp = SOFT * 100
    lo = max([t for t in table if t[0] <= sp] or [table[0]], key=lambda t: t[0])
    hi = min([t for t in table if t[0] >= sp] or [table[-1]], key=lambda t: t[0])
    tt = 0.0 if hi[0] == lo[0] else (sp - lo[0]) / (hi[0] - lo[0])
    k = args.k if args.k is not None else loglerp(lo[1], hi[1], tt)
    bend = args.bend if args.bend is not None else loglerp(lo[2], hi[2], tt)
    s.quality = 15
    s.mass = 0.3
    s.air_damping = 0.5
    s.tension_stiffness = s.compression_stiffness = s.shear_stiffness = k
    s.bending_stiffness = bend
    s.tension_damping = s.compression_damping = s.shear_damping = 5
    s.use_pressure = True
    s.uniform_pressure_force = 0.0
    bmv = bmesh.new()
    bmv.from_mesh(rod.data)
    s.use_pressure_volume = True
    s.target_volume = bmv.calc_volume()
    bmv.free()
    s.pressure_factor = 3.0
    s.use_internal_springs = True
    s.internal_spring_max_length = ROD_R * 2.5
    s.internal_tension_stiffness = k
    s.internal_compression_stiffness = k
    c = cl.collision_settings
    c.collision_quality = 6
    c.distance_min = 0.005
    c.use_self_collision = False
    cl.point_cache.frame_end = args.frames
    cs = rod.modifiers.new("Goo", "CORRECTIVE_SMOOTH")
    cs.rest_source = "ORCO"
    cs.factor = 0.8
    cs.iterations = int(lerp(1, 12, SOFT))
    sub = rod.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = sub.render_levels = 1

# ----------------------------------------------------------------------------
# ライト / カメラ
# ----------------------------------------------------------------------------
def area(name, size, energy, loc, target, color=(1, 1, 1), sy=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.color = energy, color
    if sy:
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = size, sy
    else:
        ld.size = size
    o = link(bpy.data.objects.new(name, ld))
    o.location = loc
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()


area("Key", 3.0, 1100, (-3.4, -2.6, 5.0), (0, 0, 1.8), (1.0, 0.92, 0.82), sy=1.8)
area("Rim", 1.2, 900, (2.8, 2.4, 3.8), (0, 0, 2.0), (0.85, 0.9, 1.0), sy=4.5)
area("Fill", 4.0, 160, (3.8, -3.6, 2.2), (0, 0, 1.5), (1.0, 0.96, 0.9))
area("Top", 2.0, 380, (0, -0.3, 6.5), (0, 0, 2.0), (1, 0.97, 0.92), sy=0.6)
area("Strip", 0.25, 260, (-1.8, 1.5, 3.4), (0, 0, 2.0), (1, 0.95, 0.88), sy=3.5)

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.045, 0.04, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

cd = bpy.data.cameras.new("Cam")
cd.lens = 58
cd.sensor_fit = "VERTICAL"
cd.sensor_height = 36
cd.dof.use_dof = True
cd.dof.aperture_fstop = 8
cam = link(bpy.data.objects.new("Cam", cd))
cam.location = (1.2, -6.4, 3.0)
cam.rotation_euler = (Vector((0.05, 0, 1.95)) - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam
focus = link(bpy.data.objects.new("Focus", None))
focus.location = (0, 0, 1.8)
cd.dof.focus_object = focus

# ----------------------------------------------------------------------------
# レンダー設定
# ----------------------------------------------------------------------------
rd = scene.render
rd.engine = "CYCLES"
scene.cycles.device = "CPU"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for tname in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = tname
            prefs.get_devices()
            if any(d.type == tname for d in prefs.devices):
                for d in prefs.devices:
                    d.use = True
                scene.cycles.device = "GPU"
                break
        except Exception:
            continue
except Exception:
    pass
if args.preview:
    rd.resolution_x, rd.resolution_y = 540, 960
    scene.cycles.samples = args.samples or 24
else:
    rd.resolution_x, rd.resolution_y = 1080, 1920
    scene.cycles.samples = args.samples or 16
if args.res:
    rd.resolution_x, rd.resolution_y = (int(v) for v in args.res.split("x"))
rd.resolution_percentage = 100
scene.frame_step = args.step
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.02
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.cycles.diffuse_bounces = 3
scene.cycles.glossy_bounces = 5
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
scene.cycles.blur_glossy = 1.0
scene.view_settings.view_transform = "AgX"
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
rd.use_motion_blur = True
rd.motion_blur_shutter = 0.5
rd.image_settings.file_format = "PNG"
# 途中で止まっても、書き出し済みのフレームを飛ばして再開できるようにする
rd.use_overwrite = False
rd.use_placeholder = True


# ----------------------------------------------------------------------------
# 実行
# ----------------------------------------------------------------------------
def progress():
    """棒の重心が、らせんのどこまで進んだか(0〜1)と、カップに入ったか"""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = rod.evaluated_get(dg)
    pts = [ev.matrix_world @ v.co for v in ev.data.vertices]
    c = sum(pts, Vector()) / len(pts)
    u = min(range(N_PATH + 1), key=lambda i: (helix(i / N_PATH) - c).length) / N_PATH
    d = (helix(u) - c).length
    in_cup = (Vector((c.x, c.y)) - GOAL).length < CUP_R - 0.03 and c.z < 0.12 + CUP_H
    return u, d, c.z, in_cup, c


if args.report or args.render or args.still is not None or args.save:
    for fr in range(1, args.frames + 1):
        scene.frame_set(fr)
        if args.report and (fr % 5 == 0 or fr == 1):
            u, d, z, inc, c = progress()
            print(f"REPORT f={fr} u={u:.2f} off={d:.2f} z={z:.2f} cup={int(inc)} x={c.x:.2f} y={c.y:.2f}")
scene.frame_start = max(1, args.start)
if args.save:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(args.save))
if args.still is not None:
    scene.frame_set(args.still)
    rd.filepath = (args.render or "/tmp/spiral_") + f"{args.still:04d}.png"
    bpy.ops.render.render(write_still=True)
elif args.render:
    rd.filepath = args.render
    bpy.ops.render.render(animation=True)
