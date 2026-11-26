"""
鍵穴が溶けていく — Blender シーン生成スクリプト(v2)

鍵穴の形をした金のオブジェが、黒大理石の台に落ちてくる。
台には小さな鍵穴の穴が開いており、SOFT(柔らかさ)が上がるほど
金のオブジェがスライムのように崩れ、穴から垂れて下のトレイに溜まる。

使い方(Blender 4.2 以降 / 5.x で確認):
  blender -b -P keyhole_slime.py -- --soft 60 --report               # 動きの数値確認
  blender -b -P keyhole_slime.py -- --soft 60 --save soft060.blend    # GUI で開く用
  blender -b -P keyhole_slime.py -- --soft 60 --render render/s60/f_  # 連番 PNG

オプション:
  --soft N      柔らかさ 0〜100(0 は剛体。それ以外は布+体積保持のソフトボディ)
  --frames N    フレーム数(既定 120 = 30fps で 4 秒)
  --preview     540x960・低サンプル
  --res WxH     解像度を直接指定
  --samples N   Cycles サンプル数(既定 64、ノイズ除去あり)
  --still F     フレーム F だけを書き出す
  --step N      N フレームおきに書き出す
"""
import sys
import math
import argparse

import bpy
import bmesh
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("--soft", type=float, default=50)
ap.add_argument("--frames", type=int, default=120)
ap.add_argument("--preview", action="store_true")
ap.add_argument("--res", type=str, default=None)
ap.add_argument("--samples", type=int, default=None)
ap.add_argument("--still", type=int, default=None)
ap.add_argument("--step", type=int, default=1)
ap.add_argument("--render", type=str, default=None)
ap.add_argument("--save", type=str, default=None)
ap.add_argument("--report", action="store_true")
ap.add_argument("--threads", type=int, default=0)
# 調整用
ap.add_argument("--k", type=float, default=None)
ap.add_argument("--bend", type=float, default=None)
ap.add_argument("--press", type=float, default=None)
ap.add_argument("--vol", type=float, default=None)
args = ap.parse_args(argv)

SOFT = max(0.0, min(100.0, args.soft)) / 100.0

# ----------------------------------------------------------------------------
# 寸法
# ----------------------------------------------------------------------------
SLAB_TOP = 1.60
SLAB_T = 0.24
SLAB_W, SLAB_D = 2.6, 1.6
# 落ちてくる鍵穴オブジェ(大)
KEY = dict(r=0.27, cy=0.16, slot_len=0.52, w_top=0.16, w_bot=0.34, thick=0.13)
# 台の穴(小さい鍵穴)
HOLE = dict(r=0.12, cy=0.10, slot_len=0.24, w_top=0.07, w_bot=0.15)
DROP_Z = SLAB_TOP + 0.75


def lerp(a, b, t):
    return a + (b - a) * t


def loglerp(a, b, t):
    return 10 ** lerp(math.log10(a), math.log10(b), t)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = args.frames
scene.render.fps = 30


def link(o):
    scene.collection.objects.link(o)
    return o


def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def box(name, sx, sy, sz, loc):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    o = mesh_obj(name, bm)
    o.location = loc
    return o


def cylinder(name, r, depth, loc, segs=96):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=depth)
    o = mesh_obj(name, bm)
    o.location = loc
    return o


def prism(name, pts2d, z0, z1):
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in pts2d]
    top = [bm.verts.new((x, y, z1)) for x, y in pts2d]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    n = len(pts2d)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm)


def keyhole_parts(spec, z0, z1, name="kh"):
    """鍵穴 = 円柱 + 台形の柱"""
    c = cylinder(name + "_round", spec["r"], z1 - z0, (0, spec["cy"], (z0 + z1) / 2))
    y0 = spec["cy"] - spec["r"] * 0.4
    y1 = spec["cy"] - spec["slot_len"]
    wt, wb = spec["w_top"] / 2, spec["w_bot"] / 2
    s = prism(name + "_slot", [(-wt, y0), (wt, y0), (wb, y1), (-wb, y1)], z0, z1)
    return [c, s]


def apply_mods(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    o.modifiers.clear()
    old = o.data
    o.data = me
    bpy.data.meshes.remove(old)


def boolean_cut(target, cutters):
    for i, c in enumerate(cutters):
        m = target.modifiers.new(f"cut{i}", "BOOLEAN")
        m.operation = "DIFFERENCE"
        m.solver = "EXACT"
        m.object = c
    apply_mods(target)
    for c in cutters:
        bpy.data.objects.remove(c)


def smooth(o, angle=35):
    for p in o.data.polygons:
        p.use_smooth = True
    try:
        o.data.set_sharp_from_angle(angle=math.radians(angle))
    except Exception:
        pass


def bevel(o, w=0.01, segs=3):
    m = o.modifiers.new("Bevel", "BEVEL")
    m.width = w
    m.segments = segs
    m.limit_method = "ANGLE"


# ----------------------------------------------------------------------------
# マテリアル
# ----------------------------------------------------------------------------
def principled(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat, mat.node_tree, mat.node_tree.nodes.get("Principled BSDF")


def mat_gold(name, rough):
    mat, nt, b = principled(name)
    b.inputs["Base Color"].default_value = (1.0, 0.71, 0.33, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rough
    return mat


def mat_black_marble():
    """ネロ・マルキーナ風の黒大理石。細い主脈 + 細かい副脈の 2 層"""
    mat, nt, b = principled("BlackMarble")
    N, L = nt.nodes, nt.links
    tc = N.new("ShaderNodeTexCoord")

    def vein(scale, dist, width, seed_off):
        mp = N.new("ShaderNodeMapping")
        mp.inputs["Location"].default_value = (seed_off, seed_off * 0.7, 0)
        mp.inputs["Rotation"].default_value = (0.3, 0.2, 0.6 + seed_off)
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
        rp.color_ramp.elements[0].position = 0.0
        rp.color_ramp.elements[0].color = (1, 1, 1, 1)
        rp.color_ramp.elements[1].position = width
        rp.color_ramp.elements[1].color = (0, 0, 0, 1)
        L.new(wv.outputs["Fac"], rp.inputs["Fac"])
        return rp

    v1 = vein(0.55, 7.0, 0.012, 0.0)
    v2 = vein(1.7, 10.0, 0.006, 3.1)
    add = N.new("ShaderNodeMath")
    add.operation = "MAXIMUM"
    add2 = N.new("ShaderNodeMath")
    add2.operation = "MULTIPLY"
    add2.inputs[1].default_value = 0.45
    L.new(v2.outputs["Color"], add2.inputs[0])
    L.new(v1.outputs["Color"], add.inputs[0])
    L.new(add2.outputs[0], add.inputs[1])
    col = N.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs[6].default_value = (0.010, 0.010, 0.011, 1)
    col.inputs[7].default_value = (0.70, 0.68, 0.64, 1)
    L.new(add.outputs[0], col.inputs["Factor"])
    L.new(col.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.2
    b.inputs["Coat Weight"].default_value = 0.8
    b.inputs["Coat Roughness"].default_value = 0.03
    return mat


def mat_backdrop():
    mat, nt, b = principled("Backdrop")
    b.inputs["Base Color"].default_value = (0.10, 0.078, 0.064, 1)
    b.inputs["Roughness"].default_value = 0.9
    return mat


M_GOLD = mat_gold("GoldPolished", 0.09)
M_GOLD_PLATE = mat_gold("GoldBrushed", 0.3)
M_MARBLE = mat_black_marble()
M_BACK = mat_backdrop()


def assign(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)


# ----------------------------------------------------------------------------
# 背景(ホリゾント)
# ----------------------------------------------------------------------------
prof = [(y, 0.0) for y in [-14, -10, -6, -4, -3]]
R = 3.0
for i in range(1, 25):
    a = (i / 24) * (math.pi / 2)
    prof.append((-3 + R * math.sin(a), R - R * math.cos(a)))
prof += [(0.0, 6.0), (0.0, 14.0)]
prof = [(y + 3.5, z) for y, z in prof]
bm = bmesh.new()
rows = [[bm.verts.new((x, y, z)) for y, z in prof] for x in (-14, 14)]
for i in range(len(prof) - 1):
    bm.faces.new((rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1]))
backdrop = mesh_obj("Backdrop", bm)
for p in backdrop.data.polygons:
    p.use_smooth = True
assign(backdrop, M_BACK)

# ----------------------------------------------------------------------------
# 大理石の台(小さい鍵穴の穴)+ 金の縁取り + 受けトレイ
# ----------------------------------------------------------------------------
slab = box("Slab", SLAB_W, SLAB_D, SLAB_T, (0, 0, SLAB_TOP - SLAB_T / 2))
boolean_cut(slab, keyhole_parts(HOLE, SLAB_TOP - SLAB_T - 0.2, SLAB_TOP + 0.2))
assign(slab, M_MARBLE)
smooth(slab)
bevel(slab, 0.01, 2)

pillars = []
for sx in (-1, 1):
    p = box(f"Pillar{sx}", 0.42, 1.0, SLAB_TOP - SLAB_T, (sx * 0.98, 0, (SLAB_TOP - SLAB_T) / 2))
    assign(p, M_MARBLE)
    bevel(p, 0.01, 2)
    pillars.append(p)

# 穴のまわりの金の縁(細いリング状の鍵穴フレーム)
RIM = 0.025
rim_outer = dict(HOLE)
rim_outer.update(r=HOLE["r"] + RIM, w_top=HOLE["w_top"] + RIM * 2,
                 w_bot=HOLE["w_bot"] + RIM * 2, slot_len=HOLE["slot_len"] + RIM)
rim_parts = keyhole_parts(rim_outer, SLAB_TOP, SLAB_TOP + 0.012, "rim")
rim = rim_parts[0]
m = rim.modifiers.new("u", "BOOLEAN")
m.operation = "UNION"
m.solver = "EXACT"
m.object = rim_parts[1]
apply_mods(rim)
bpy.data.objects.remove(rim_parts[1])
rim.name = "Rim"
boolean_cut(rim, keyhole_parts(HOLE, SLAB_TOP - 0.1, SLAB_TOP + 0.1, "rimcut"))
assign(rim, M_GOLD_PLATE)
smooth(rim)

tray = cylinder("Tray", 0.6, 0.06, (0, HOLE["cy"] - 0.08, 0.03))
boolean_cut(tray, [cylinder("TrayIn", 0.55, 0.1, (0, HOLE["cy"] - 0.08, 0.08))])
assign(tray, M_GOLD_PLATE)
smooth(tray)
bevel(tray, 0.006, 2)

colliders = [slab, rim, tray, backdrop] + pillars
for o in colliders:
    c = o.modifiers.new("Collision", "COLLISION")
    o.collision.thickness_outer = 0.005
    o.collision.cloth_friction = 2.0
    o.collision.use_culling = False

# ----------------------------------------------------------------------------
# 落ちてくる金の鍵穴(ボクセルリメッシュで一体化した閉じたメッシュ)
# ----------------------------------------------------------------------------
parts = keyhole_parts(KEY, -KEY["thick"] / 2, KEY["thick"] / 2, "key")
key = parts[0]
m = key.modifiers.new("u", "BOOLEAN")
m.operation = "UNION"
m.solver = "EXACT"
m.object = parts[1]
apply_mods(key)
bpy.data.objects.remove(parts[1])
rm = key.modifiers.new("Remesh", "REMESH")
rm.mode = "VOXEL"
rm.voxel_size = 0.022
rm.use_smooth_shade = True
apply_mods(key)
# 角を少し丸めて高級感のある面取りに
sm = key.modifiers.new("Smooth", "SMOOTH")
sm.factor = 0.5
sm.iterations = 3
apply_mods(key)
key.name = "GoldKey"
for p in key.data.polygons:
    p.use_smooth = True
assign(key, M_GOLD)
key.location = (0, 0.0, DROP_Z)
key.rotation_euler = (math.radians(7), math.radians(-4), 0)
# 鍵穴の形を台の穴と揃える(丸の中心を合わせる)
key.location.y = HOLE["cy"] - KEY["cy"] + 0.02

bm = bmesh.new()
bm.from_mesh(key.data)
KEY_VOLUME = bm.calc_volume()
bm.free()

if SOFT <= 0.0:
    bpy.context.view_layer.objects.active = key
    bpy.ops.rigidbody.world_add()
    scene.rigidbody_world.point_cache.frame_end = args.frames
    scene.rigidbody_world.substeps_per_frame = 30
    scene.rigidbody_world.solver_iterations = 20
    bpy.ops.rigidbody.object_add()
    rb = key.rigid_body
    rb.collision_shape = "CONVEX_HULL"
    rb.mass = 3.0
    rb.restitution = 0.5
    rb.friction = 0.5
    rb.collision_margin = 0.002
    for o in (slab, rim, tray, backdrop):
        bpy.context.view_layer.objects.active = o
        bpy.ops.rigidbody.object_add()
        o.rigid_body.type = "PASSIVE"
        o.rigid_body.collision_shape = "MESH"
        o.rigid_body.restitution = 0.6
        o.rigid_body.collision_margin = 0.001
else:
    cl = key.modifiers.new("Cloth", "CLOTH")
    s = cl.settings
    # 設定表: (SOFT%, 硬さ k, 曲げ b, 体積保持の圧力係数 v)
    table = [
        (20, 30.0, 60.0, 3.0),    # ほぼ硬い。着地でわずかにたわむ
        (40, 4.0, 2.0, 3.0),      # 角が少し垂れる
        (60, 0.6, 0.1, 1.8),      # 穴にじわじわ垂れ下がる(途中で止まる)
        (80, 0.4, 0.05, 1.5),     # 約3秒かけて穴を通り抜ける
        (100, 0.07, 0.003, 1.2),  # 液体の金のように一気に流れ落ちる
    ]
    sp = SOFT * 100
    lo = max([t for t in table if t[0] <= sp] or [table[0]], key=lambda t: t[0])
    hi = min([t for t in table if t[0] >= sp] or [table[-1]], key=lambda t: t[0])
    t = 0.0 if hi[0] == lo[0] else (sp - lo[0]) / (hi[0] - lo[0])
    k = args.k if args.k is not None else loglerp(lo[1], hi[1], t)
    bend = args.bend if args.bend is not None else loglerp(lo[2], hi[2], t)
    vol = args.vol if args.vol is not None else lerp(lo[3], hi[3], t)
    s.quality = 15
    s.mass = 0.15
    s.air_damping = 1.0
    s.tension_stiffness = s.compression_stiffness = s.shear_stiffness = k
    s.bending_stiffness = bend
    s.tension_damping = s.compression_damping = s.shear_damping = 10
    s.bending_damping = 1.0
    # 体積を保つ「圧力」でスライムらしい“重さ”を出す
    s.use_pressure = True
    s.uniform_pressure_force = args.press if args.press is not None else 0.0
    s.use_pressure_volume = True
    s.target_volume = KEY_VOLUME
    s.pressure_factor = vol
    c = cl.collision_settings
    c.collision_quality = 6
    c.distance_min = 0.006
    c.use_self_collision = True
    c.self_distance_min = 0.006
    c.self_friction = 3
    cl.point_cache.frame_end = args.frames
    # 細かいシワを消して、とろっとしたスライムの表面にする(柔らかいほど強く)
    cs = key.modifiers.new("Goo", "CORRECTIVE_SMOOTH")
    cs.rest_source = "ORCO"
    cs.smooth_type = "LENGTH_WEIGHTED"
    cs.factor = 0.9
    cs.iterations = int(lerp(2, 25, SOFT))
    cs.use_only_smooth = False
    sub = key.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1

# ----------------------------------------------------------------------------
# ライト / カメラ
# ----------------------------------------------------------------------------
def area(name, size, energy, loc, target, color=(1, 1, 1), sy=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = color
    if sy:
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = size, sy
    else:
        ld.size = size
    o = link(bpy.data.objects.new(name, ld))
    o.location = loc
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()
    return o


area("Key", 3.0, 850, (-3.2, -2.2, 4.6), (0, 0, 1.2), (1.0, 0.92, 0.82), sy=1.6)
area("Rim", 1.2, 700, (2.6, 2.6, 3.2), (0, 0, 1.4), (0.85, 0.9, 1.0), sy=4.0)
area("Fill", 4.0, 110, (3.5, -3.5, 1.8), (0, 0, 1.0), (1.0, 0.96, 0.9))
area("Top", 2.0, 300, (0, -0.4, 5.5), (0, 0, 1.6), (1, 0.97, 0.92), sy=0.5)
area("Strip", 0.25, 220, (-1.6, 1.4, 3.0), (0, 0, 1.6), (1, 0.95, 0.88), sy=3.0)

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.05, 0.045, 0.04, 1)
bg.inputs["Strength"].default_value = 0.6

cd = bpy.data.cameras.new("Cam")
cd.lens = 66
cd.sensor_fit = "VERTICAL"
cd.sensor_height = 36
cd.dof.use_dof = True
cd.dof.aperture_fstop = 5.6
cam = link(bpy.data.objects.new("Cam", cd))
cam.location = (0.55, -4.3, 4.6)
cam.rotation_euler = (Vector((0, -0.12, 1.12)) - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam
focus = link(bpy.data.objects.new("Focus", None))
focus.location = (0, HOLE["cy"], SLAB_TOP - 0.2)
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
    scene.cycles.samples = args.samples or 64
if args.res:
    rd.resolution_x, rd.resolution_y = (int(v) for v in args.res.split("x"))
rd.resolution_percentage = 100
if args.threads:
    rd.threads_mode = "FIXED"
    rd.threads = args.threads
scene.frame_step = args.step
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.02
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.cycles.diffuse_bounces = 3
scene.cycles.glossy_bounces = 5
scene.cycles.transmission_bounces = 2
scene.cycles.volume_bounces = 0
scene.cycles.transparent_max_bounces = 2
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
rd.image_settings.color_depth = "8"
rd.image_settings.compression = 30

# ----------------------------------------------------------------------------
# 実行
# ----------------------------------------------------------------------------
def stats():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = key.evaluated_get(dg)
    zs = [(ev.matrix_world @ v.co).z for v in ev.data.vertices]
    below = sum(1 for z in zs if z < SLAB_TOP - SLAB_T) / len(zs)
    return min(zs), max(zs), below


if args.report or args.render or args.still is not None or args.save:
    for fr in range(1, args.frames + 1):
        scene.frame_set(fr)
        if args.report and (fr % 10 == 0 or fr == 1):
            mn, mx, below = stats()
            print(f"REPORT soft={args.soft:.0f} f={fr} zmin={mn:.2f} zmax={mx:.2f} below={below:.2f}")

if args.save:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(args.save))

if args.still is not None:
    scene.frame_set(args.still)
    rd.filepath = (args.render or "/tmp/keyhole_") + f"{args.still:04d}.png"
    bpy.ops.render.render(write_still=True)
elif args.render:
    rd.filepath = args.render
    bpy.ops.render.render(animation=True)
