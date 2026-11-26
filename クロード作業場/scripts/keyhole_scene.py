"""
鍵穴を通り抜ける金の球 — Blender シーン生成スクリプト

黒大理石のスラブに金の鍵穴プレート。上から金の球が落ち、
SOFT(柔らかさ)の値によって「弾かれる/詰まる/通り抜ける」が変わる。

使い方(Blender 4.2 以降 / 5.x で確認):
  blender -b -P keyhole_scene.py -- --soft 50 --render out/soft050/
  blender -b -P keyhole_scene.py -- --soft 100 --save soft100.blend   # 保存して GUI で開く
  blender -b -P keyhole_scene.py -- --soft 75 --still 90 --preview --render out/test_

オプション:
  --soft N        柔らかさ 0〜100(0 は剛体、それ以外は布+空気圧のソフトボディ)
  --frames N      フレーム数(既定 150 = 30fps で 5 秒)
  --preview       低解像度・低サンプル(確認用)
  --still F       フレーム F だけを静止画で書き出す
  --render PATH   連番 PNG を書き出す(PATH は接頭辞)
  --save PATH     .blend を保存する
  --report        シミュレーション結果(球の高さ)を表示する
"""
import sys
import math
import argparse

import bpy
import bmesh
from mathutils import Vector

# ----------------------------------------------------------------------------
# 引数
# ----------------------------------------------------------------------------
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("--soft", type=float, default=50)
ap.add_argument("--frames", type=int, default=150)
ap.add_argument("--preview", action="store_true")
ap.add_argument("--still", type=int, default=None)
ap.add_argument("--render", type=str, default=None)
ap.add_argument("--save", type=str, default=None)
ap.add_argument("--report", action="store_true")
ap.add_argument("--samples", type=int, default=None)
ap.add_argument("--res", type=str, default=None, help="解像度 例: 360x640")
ap.add_argument("--step", type=int, default=1, help="何フレームおきに書き出すか")
# 調整用(通常は不要)
ap.add_argument("--k", type=float, default=None, help="布の硬さを直接指定")
ap.add_argument("--press", type=float, default=None, help="空気圧を直接指定")
ap.add_argument("--internal", type=float, default=None, help="内部スプリングの硬さ(0 で無効)")
ap.add_argument("--friction", type=float, default=None)
args = ap.parse_args(argv)

SOFT = max(0.0, min(100.0, args.soft)) / 100.0

# ----------------------------------------------------------------------------
# 寸法(1 unit = 10cm くらいのイメージ)
# ----------------------------------------------------------------------------
SLAB_TOP = 1.60          # スラブ上面の高さ
SLAB_T = 0.24            # スラブの厚み
SLAB_W, SLAB_D = 2.6, 1.5
BALL_R = 0.30            # 球の半径
HOLE_R = 0.19            # 鍵穴の丸の半径(球より小さい)
HOLE_CY = 0.12           # 鍵穴の丸の中心(Y)
SLOT_LEN = 0.42          # 鍵穴の下の切れ込みの長さ
SLOT_W_TOP, SLOT_W_BOT = 0.10, 0.20
DROP_Z = SLAB_TOP + 0.85 # 球の初期高さ(中心)


def lerp(a, b, t):
    return a + (b - a) * t


def loglerp(a, b, t):
    return 10 ** lerp(math.log10(a), math.log10(b), t)


# ----------------------------------------------------------------------------
# リセット
# ----------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = args.frames
scene.render.fps = 30


def link(obj):
    scene.collection.objects.link(obj)
    return obj


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
    """2D 多角形を Z 方向に押し出した柱"""
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


def keyhole_cutters(z0, z1, grow=0.0):
    c = cylinder("cut_round", HOLE_R + grow, (z1 - z0), (0, HOLE_CY, (z0 + z1) / 2))
    y0 = HOLE_CY - 0.05
    y1 = HOLE_CY - SLOT_LEN - grow
    wt, wb = SLOT_W_TOP / 2 + grow, SLOT_W_BOT / 2 + grow
    s = prism("cut_slot", [(-wt, y0), (wt, y0), (wb, y1), (-wb, y1)], z0, z1)
    return [c, s]


def boolean_cut(target, cutters):
    for i, c in enumerate(cutters):
        m = target.modifiers.new(f"cut{i}", "BOOLEAN")
        m.operation = "DIFFERENCE"
        m.solver = "EXACT"
        m.object = c
        c.hide_render = True
        c.hide_viewport = True
    # 適用してメッシュを確定(コリジョンを安定させるため)
    bpy.context.view_layer.objects.active = target
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    target.modifiers.clear()
    old = target.data
    target.data = me
    bpy.data.meshes.remove(old)
    for c in cutters:
        bpy.data.objects.remove(c)


def smooth(o, angle=35):
    for p in o.data.polygons:
        p.use_smooth = True
    try:
        o.data.set_sharp_from_angle(angle=math.radians(angle))
    except Exception:
        pass


def bevel(o, w=0.012, segs=3):
    m = o.modifiers.new("Bevel", "BEVEL")
    m.width = w
    m.segments = segs
    m.limit_method = "ANGLE"
    m.harden_normals = False
    return m


# ----------------------------------------------------------------------------
# マテリアル
# ----------------------------------------------------------------------------
def principled(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    return mat, nt, bsdf


def mat_gold(name, rough):
    mat, nt, b = principled(name)
    b.inputs["Base Color"].default_value = (1.0, 0.72, 0.36, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rough
    return mat


def mat_black_marble():
    """ネロ・マルキーナ風の黒大理石(プロシージャル。外部素材不要)"""
    mat, nt, b = principled("BlackMarble")
    N = nt.nodes
    L = nt.links
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.9, 0.9, 0.9)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.6
    noise.inputs["Detail"].default_value = 12
    noise.inputs["Roughness"].default_value = 0.62
    L.new(mp.outputs["Vector"], noise.inputs["Vector"])
    mix = N.new("ShaderNodeMix")
    mix.data_type = "VECTOR"
    mix.inputs["Factor"].default_value = 0.55
    L.new(mp.outputs["Vector"], mix.inputs[4])
    L.new(noise.outputs["Color"], mix.inputs[5])
    wave = N.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 0.9
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 10
    wave.inputs["Detail Roughness"].default_value = 0.7
    L.new(mix.outputs[1], wave.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.62, 0.6, 0.57, 1)
    cr.elements[1].position = 0.018
    cr.elements[1].color = (0.012, 0.012, 0.014, 1)
    L.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.16
    b.inputs["Coat Weight"].default_value = 0.6
    b.inputs["Coat Roughness"].default_value = 0.04
    return mat


def mat_backdrop():
    mat, nt, b = principled("Backdrop")
    b.inputs["Base Color"].default_value = (0.11, 0.085, 0.07, 1)  # 深いモカ/トープ
    b.inputs["Roughness"].default_value = 0.85
    return mat


M_GOLD_BALL = mat_gold("GoldPolished", 0.07)
M_GOLD_PLATE = mat_gold("GoldBrushed", 0.28)
M_MARBLE = mat_black_marble()
M_BACK = mat_backdrop()


def assign(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)


# ----------------------------------------------------------------------------
# 背景(ホリゾント:床と壁がなめらかにつながる)
# ----------------------------------------------------------------------------
def backdrop():
    prof = []
    R = 3.0
    for i in range(0, 12):
        prof.append((-14 + i * 1.0 + 0.0, 0.0))  # 床 y=-14..-3
    prof = [(y, 0.0) for y in [-14, -10, -6, -4, -3]]
    for i in range(1, 25):
        a = (i / 24) * (math.pi / 2)
        prof.append((-3 + R * math.sin(a), R - R * math.cos(a)))
    prof += [(0.0, 6.0), (0.0, 14.0)]
    # 奥の壁を y=+3.5 に置く
    prof = [(y + 3.5, z) for y, z in prof]
    bm = bmesh.new()
    xs = (-14, 14)
    rows = []
    for x in xs:
        rows.append([bm.verts.new((x, y, z)) for y, z in prof])
    for i in range(len(prof) - 1):
        bm.faces.new((rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1]))
    o = mesh_obj("Backdrop", bm)
    for p in o.data.polygons:
        p.use_smooth = True
    assign(o, M_BACK)
    return o


backdrop()

# ----------------------------------------------------------------------------
# 大理石スラブ + 柱 + 金の鍵穴プレート + 受け皿
# ----------------------------------------------------------------------------
slab = box("Slab", SLAB_W, SLAB_D, SLAB_T, (0, 0, SLAB_TOP - SLAB_T / 2))
boolean_cut(slab, keyhole_cutters(SLAB_TOP - SLAB_T - 0.2, SLAB_TOP + 0.2, grow=0.0))
assign(slab, M_MARBLE)
smooth(slab)
bevel(slab, 0.01, 2)

for sx in (-1, 1):
    p = box(f"Pillar{sx}", 0.42, 0.9, SLAB_TOP - SLAB_T, (sx * 0.98, 0, (SLAB_TOP - SLAB_T) / 2))
    assign(p, M_MARBLE)
    bevel(p, 0.01, 2)

PLATE_T = 0.025
plate = box("KeyPlate", 0.62, 0.92, PLATE_T, (0, HOLE_CY - 0.16, SLAB_TOP + PLATE_T / 2))
boolean_cut(plate, keyhole_cutters(SLAB_TOP - 0.1, SLAB_TOP + 0.2, grow=0.0))
assign(plate, M_GOLD_PLATE)
smooth(plate)
bevel(plate, 0.008, 3)

# 受け皿(金のトレイ)
tray = cylinder("Tray", 0.62, 0.06, (0, HOLE_CY - 0.05, 0.03))
inner = cylinder("TrayIn", 0.56, 0.1, (0, HOLE_CY - 0.05, 0.08))
boolean_cut(tray, [inner])
assign(tray, M_GOLD_PLATE)
smooth(tray)
bevel(tray, 0.006, 2)

for o in (slab, plate, tray, bpy.data.objects["Pillar-1"], bpy.data.objects["Pillar1"],
          bpy.data.objects["Backdrop"]):
    o.modifiers.new("Collision", "COLLISION")
    o.collision.thickness_outer = 0.004
    o.collision.cloth_friction = args.friction if args.friction is not None else 1.0
    o.collision.use_culling = False

# ----------------------------------------------------------------------------
# 金の球
# ----------------------------------------------------------------------------
bm = bmesh.new()
bmesh.ops.create_icosphere(bm, subdivisions=4 if not args.preview else 4, radius=BALL_R)
ball = mesh_obj("Ball", bm)
ball.location = (0.03, HOLE_CY + 0.02, DROP_Z)
for p in ball.data.polygons:
    p.use_smooth = True
assign(ball, M_GOLD_BALL)

if SOFT <= 0.0:
    # 0% = 完全な剛体
    bpy.context.view_layer.objects.active = ball
    scene.rigidbody_world is None and bpy.ops.rigidbody.world_add()
    scene.rigidbody_world.point_cache.frame_end = args.frames
    scene.rigidbody_world.substeps_per_frame = 20
    bpy.ops.rigidbody.object_add()
    rb = ball.rigid_body
    rb.type = "ACTIVE"
    rb.collision_shape = "SPHERE"
    rb.mass = 2.0
    rb.restitution = 0.9
    rb.friction = 0.4
    for o in (slab, plate, tray, bpy.data.objects["Backdrop"]):
        bpy.context.view_layer.objects.active = o
        bpy.ops.rigidbody.object_add()
        o.rigid_body.type = "PASSIVE"
        o.rigid_body.collision_shape = "MESH"
        o.rigid_body.restitution = 0.9
        o.rigid_body.friction = 0.5
        o.rigid_body.collision_margin = 0.0
else:
    # 25〜100% = 布 + 空気圧(風船のようなソフトボディ。標準の Soft Body より安定)
    cl = ball.modifiers.new("Cloth", "CLOTH")
    s = cl.settings
    s.quality = 12
    s.mass = 0.25
    s.air_damping = 1.0
    # 検証済みの設定表(SOFT% → 布の硬さ k / 空気圧 p)。間の値は補間する。
    #   (SOFT%, 硬さ k, 空気圧 p, 曲げ b)
    #   25%: 鍵穴の上に乗って止まる / 50%: 少しめり込んで詰まる
    #   75%: じわじわ押し出され、約4.5秒後に落ちる / 100%: 約2秒ですり抜ける
    table = [(25, 8.0, 10.0, 1.0), (50, 3.0, 5.0, 0.1), (75, 3.0, 2.0, 0.02), (100, 1.0, 3.0, 0.02)]
    sp = SOFT * 100
    lo = max([t for t in table if t[0] <= sp] or [table[0]], key=lambda t: t[0])
    hi = min([t for t in table if t[0] >= sp] or [table[-1]], key=lambda t: t[0])
    t = 0.0 if hi[0] == lo[0] else (sp - lo[0]) / (hi[0] - lo[0])
    k = args.k if args.k is not None else loglerp(lo[1], hi[1], t)
    s.tension_stiffness = k
    s.compression_stiffness = k
    s.shear_stiffness = k
    s.bending_stiffness = loglerp(lo[3], hi[3], t)
    s.tension_damping = 8
    s.compression_damping = 8
    s.shear_damping = 8
    s.use_pressure = True
    s.uniform_pressure_force = args.press if args.press is not None else lerp(lo[2], hi[2], t)
    ik = args.internal if args.internal is not None else 0.0
    s.use_internal_springs = ik > 0
    s.internal_spring_max_length = BALL_R * 2.2
    s.internal_tension_stiffness = max(ik, 0.001)
    s.internal_compression_stiffness = max(ik, 0.001)
    c = cl.collision_settings
    c.collision_quality = 6
    c.distance_min = 0.006
    c.use_self_collision = True
    c.self_distance_min = 0.004
    cl.point_cache.frame_end = args.frames
    sub = ball.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 2

# ----------------------------------------------------------------------------
# ライト(大きなソフトボックス + リム + フィル + 反射用の白カード)
# ----------------------------------------------------------------------------
def area(name, size, energy, loc, rot, color=(1, 1, 1), sy=None):
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
    o.rotation_euler = rot
    return o


def aim(o, target):
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


k = area("Key", 3.0, 900, (-3.2, -2.2, 4.6), (0, 0, 0), (1.0, 0.93, 0.84), sy=1.6)
aim(k, (0, 0, 1.2))
r = area("Rim", 1.2, 650, (2.6, 2.6, 3.2), (0, 0, 0), (0.85, 0.9, 1.0), sy=4.0)
aim(r, (0, 0, 1.4))
f = area("Fill", 4.0, 120, (3.5, -3.5, 1.8), (0, 0, 0), (1.0, 0.96, 0.9))
aim(f, (0, 0, 1.0))
top = area("Top", 2.0, 260, (0, -0.4, 5.5), (0, 0, 0), (1, 0.97, 0.92), sy=0.5)
aim(top, (0, 0, 1.6))

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.05, 0.045, 0.04, 1)
bg.inputs["Strength"].default_value = 0.6

# ----------------------------------------------------------------------------
# カメラ(固定、やや見下ろし、浅い被写界深度)
# ----------------------------------------------------------------------------
cd = bpy.data.cameras.new("Cam")
cd.lens = 52
cd.sensor_fit = "VERTICAL"
cd.sensor_height = 36
cd.dof.use_dof = True
cd.dof.aperture_fstop = 5.6
cam = link(bpy.data.objects.new("Cam", cd))
cam.location = (0.55, -4.3, 4.6)
aim(cam, (0, -0.05, 1.05))
scene.camera = cam
focus = link(bpy.data.objects.new("Focus", None))
focus.location = (0, HOLE_CY, SLAB_TOP - 0.2)
cd.dof.focus_object = focus

# ----------------------------------------------------------------------------
# レンダー設定
# ----------------------------------------------------------------------------
rd = scene.render
rd.engine = "CYCLES"
scene.cycles.device = "CPU"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for t in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = t
            prefs.get_devices()
            if any(d.type == t for d in prefs.devices):
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
    scene.cycles.samples = args.samples or 192
rd.resolution_percentage = 100
if args.res:
    rd.resolution_x, rd.resolution_y = (int(v) for v in args.res.split("x"))
scene.frame_step = args.step
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 10
scene.cycles.glossy_bounces = 6
scene.view_settings.view_transform = "AgX"
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
rd.use_motion_blur = True
rd.motion_blur_shutter = 0.5
rd.image_settings.file_format = "PNG"
rd.film_transparent = False

# ----------------------------------------------------------------------------
# 実行
# ----------------------------------------------------------------------------
def ball_stats():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ball.evaluated_get(dg)
    zs = [(ev.matrix_world @ v.co).z for v in ev.data.vertices]
    return min(zs), max(zs), sum(zs) / len(zs)


if args.report or args.render or args.still is not None or args.save:
    # シミュレーションを先頭から順に進めてキャッシュする
    for fr in range(1, args.frames + 1):
        scene.frame_set(fr)
        if args.report and (fr % (2 if SOFT == 0 else 10) == 0 or fr == 1):
            mn, mx, av = ball_stats()
            print(f"[soft {args.soft:.0f}] f{fr:3d}  zmin={mn:5.2f} zmax={mx:5.2f} zavg={av:5.2f}")

if args.save:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(args.save))

if args.still is not None:
    scene.frame_set(args.still)
    rd.filepath = (args.render or "/tmp/keyhole_") + f"{args.still:04d}.png"
    bpy.ops.render.render(write_still=True)
elif args.render:
    rd.filepath = args.render
    bpy.ops.render.render(animation=True)
