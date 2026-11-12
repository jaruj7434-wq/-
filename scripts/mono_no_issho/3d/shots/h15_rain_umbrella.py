"""H15 / カット6-2(次回予告): 雨の夜の駅ホーム(無名・看板文字なし)。ベンチに立てかけられた
忘れ物のビニール傘。屋根の外は雨が降りしきり、濡れた床にホームの灯りが映る。
カメラは低い位置からゆっくり傘へ寄る。5秒。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import bmesh
from mathutils import Vector
import common as C
import props as P

FRAMES = 120
EDGE_Y = 250.0          # ホーム端(線路側)の y
ROOF_Y = 200.0          # 屋根の端の y(これより外に雨)


def umbrella(base=(0, 0, 0), lean_deg=18, yaw_deg=0):
    """閉じたビニール傘(全長約85cm)。石突きが base、手元が上。"""
    root = bpy.data.objects.new("Umbrella", None); bpy.context.collection.objects.link(root)
    root.location = base
    root.rotation_euler = (math.radians(lean_deg), 0, math.radians(yaw_deg))
    white = C.principled("UmbWhite", (0.9, 0.9, 0.88), rough=0.35, coat=0.3)
    chrome = C.principled("UmbChrome", (0.8, 0.8, 0.82), metallic=1, rough=0.2)
    vinyl = C.principled("Vinyl", (0.9, 0.95, 0.97), rough=0.06, alpha=0.32, coat=1.0)

    def add(o):
        o.parent = root
        return o
    add(P.cyl("Tip", 0.45, 3.0, (0, 0, 1.5), mat=white, verts=16, bevel=0.15))
    add(P.cyl("Shaft", 0.45, 62, (0, 0, 31), mat=chrome, verts=16))
    # 畳んだ生地: しわのある細長い円錐(下すぼまり)
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.6, radius2=3.4, depth=52, location=(0, 0, 3 + 26))
    cone = bpy.context.object; cone.name = "Canopy"
    bpy.context.view_layer.objects.active = cone
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.subdivide(number_cuts=8); bpy.ops.object.mode_set(mode="OBJECT")
    # ひだ: 円周方向に半径を交互に増減
    for v in cone.data.vertices:
        a = math.atan2(v.co.y, v.co.x)
        r = Vector((v.co.x, v.co.y)).length
        k = 1 + 0.22 * math.sin(a * 8) + 0.08 * math.sin(v.co.z * 0.6 + a * 3)
        v.co.x, v.co.y = math.cos(a) * r * k, math.sin(a) * r * k
    bpy.ops.object.shade_smooth()
    cone.data.materials.append(vinyl)
    add(cone)
    # 上部の丸め(生地の付け根)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=3.2, location=(0, 0, 55.5))
    cap = bpy.context.object; cap.scale = (1, 1, 0.5); cap.data.materials.append(vinyl); bpy.ops.object.shade_smooth(); add(cap)
    # 留めベルト(白いマジックテープ)
    add(P.cyl("Strap", 2.9, 2.2, (0, 0, 40), mat=white, verts=24))
    # 手元: 白いJ字ハンドル
    add(P.cyl("Grip", 1.3, 13, (0, 0, 65), mat=white, verts=20, bevel=0.4))
    bpy.ops.mesh.primitive_torus_add(major_radius=4.0, minor_radius=1.2, location=(-4.0, 0, 71.5), rotation=(math.radians(90), 0, 0))
    hook = bpy.context.object; hook.name = "Hook"
    bm = bmesh.new(); bm.from_mesh(hook.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > 0.3], context="VERTS")  # 半円だけ残す
    bm.to_mesh(hook.data); bm.free()
    bpy.ops.object.shade_smooth()
    hook.data.materials.append(white); add(hook)
    return root


def bench(x0=0.0, y0=0.0):
    """ホームの樹脂製ベンチ(4席連結)。"""
    frame = C.principled("BenchFrame", (0.35, 0.37, 0.4), metallic=0.8, rough=0.35)
    seatm = C.principled("SeatPlastic", (0.05, 0.22, 0.45), rough=0.3, coat=0.5)
    P.box("BenchBeam", (190, 6, 4), (x0, y0, 38), mat=frame, bevel=0.5)
    for s in (-1, 1):
        P.box(f"BenchLeg{s}", (5, 40, 4), (x0 + s * 80, y0, 2), mat=frame, bevel=0.5)
        P.box(f"BenchPost{s}", (5, 5, 38), (x0 + s * 80, y0, 20), mat=frame)
    for i in range(4):
        x = x0 - 70 + i * 46.7
        P.box(f"Seat{i}", (42, 40, 3), (x, y0 - 2, 43), (math.radians(-4), 0, 0), seatm, bevel=1.2)
        P.box(f"Back{i}", (42, 3, 36), (x, y0 + 19, 62), (math.radians(-12), 0, 0), seatm, bevel=1.2)


def rain(sc, x_range, y_range, top=420, count=40000):
    """雨: パーティクルで細長い筋(白く淡い)を落とす。"""
    P.plane("RainEmitter", 1, (sum(x_range) / 2, sum(y_range) / 2, top))
    em = bpy.context.object
    em.scale = (x_range[1] - x_range[0], y_range[1] - y_range[0], 1)
    bpy.ops.object.transform_apply(scale=True)
    # (エミッタを hide_render にするとパーティクルも消えるので show_instancer_for_render で隠す)
    # 雨粒の筋(縦に長い。速度方向回転は使わずワールド縦向きのまま落とす)
    streak = P.cyl("Streak", 0.14, 28, (0, 0, -500), verts=6)
    streak.data.materials.append(C.principled("RainM", (0.8, 0.85, 0.9), rough=0.1, emission=(0.6, 0.7, 0.85),
                                              emission_strength=1.0, alpha=0.35))
    m = em.modifiers.new("Rain", "PARTICLE_SYSTEM")
    ps = em.particle_systems[0]; ps.seed = 7
    st = ps.settings
    st.count = count; st.frame_start = -40; st.frame_end = FRAMES; st.lifetime = 14
    st.emit_from = "FACE"; st.use_emit_random = True
    st.normal_factor = 0; st.object_align_factor = (6, 0, -900)
    st.factor_random = 40
    st.render_type = "OBJECT"; st.instance_object = streak
    st.use_rotations = False
    st.particle_size = 1.0; st.size_random = 0.7
    st.effector_weights.gravity = 1.0
    st.use_rotation_instance = False
    em.show_instancer_for_render = False
    return em


def build(sc):
    P.world_studio((0.003, 0.004, 0.006), (0.02, 0.025, 0.035), (0.05, 0.06, 0.08), 1.0, camera_color=(0.004, 0.005, 0.008))
    sc.use_gravity = True; sc.gravity = (0, 0, -981.0)
    rnd = random.Random(15)

    # ホーム床(濡れたコンクリートタイル)、白線、点字ブロック(黄色)、線路側の段差
    wet = C.principled("WetConcrete", (0.09, 0.09, 0.095), rough=0.2, noise_rough=(0.02, 0.5), bump=0.02, bump_scale=60)
    P.box("Platform", (3000, 600, 100), (0, EDGE_Y - 300, -50), mat=wet)
    P.box("EdgeWhite", (3000, 25, 0.4), (0, EDGE_Y - 12.5, 0.2), mat=C.principled("EdgePaint", (0.75, 0.75, 0.72), rough=0.3))
    tact = C.principled("Tactile", (0.75, 0.55, 0.03), rough=0.35, bump=0.6, bump_scale=6000)
    P.box("TactileStrip", (3000, 30, 0.8), (0, EDGE_Y - 90, 0.4), mat=tact)
    P.box("TrackBed", (3000, 600, 10), (0, EDGE_Y + 300, -125), mat=C.principled("Ballast", (0.06, 0.06, 0.06), rough=0.9, bump=0.8, bump_scale=3000))
    steel = C.principled("Rail", (0.5, 0.5, 0.52), metallic=1, rough=0.35)
    for ry in (EDGE_Y + 150, EDGE_Y + 257):
        P.box(f"Rail{ry}", (3000, 6, 15), (0, ry, -112), mat=steel)
    # 屋根と柱、ライン照明
    P.box("Roof", (3000, 520, 8), (0, ROOF_Y - 240, 330), mat=C.principled("RoofM", (0.3, 0.31, 0.33), rough=0.6))
    P.box("Gutter", (3000, 10, 14), (0, ROOF_Y + 5, 322), mat=C.principled("GutterM", (0.35, 0.36, 0.38), metallic=0.6, rough=0.4))
    colm = C.principled("Column", (0.55, 0.56, 0.58), rough=0.5, coat=0.3)
    for x in range(-1200, 1300, 600):
        P.box(f"Col{x}", (25, 25, 330), (x - 150, 20, 165), mat=colm)
    tube = C.emissive("Tube", (0.9, 0.95, 1.0), strength=14)
    for i, x in enumerate(range(-1400, 1500, 220)):
        P.box(f"Lamp{i}", (160, 6, 3), (x, 120, 324), mat=tube)
        P.box(f"Lamp2_{i}", (160, 6, 3), (x, -100, 324), mat=tube)
    for i, x in enumerate((-660, 0, 660)):
        L = C.area_light((x, 120, 320), (0, 0, 0), 1, 1.2e6, (0.88, 0.94, 1.0), f"PlatLight{i}").data
        L.shape = "RECTANGLE"; L.size = 600; L.size_y = 60
    C.area_light((-40, -140, 300), (0, 0, 0), 120, 4e5, (0.88, 0.94, 1.0), "FrontLamp")
    C.light_look_at(bpy.data.objects["FrontLamp"], (-40, -20, 40))
    # 無地の案内表示(光る板・文字なし)
    P.box("SignBox", (140, 12, 40), (220, 140, 270), mat=C.principled("SignFrame", (0.1, 0.1, 0.11), rough=0.4))
    P.box("SignFace", (130, 1, 30), (220, 133.5, 270), mat=C.emissive("SignGlow", (0.85, 0.9, 1.0), strength=3))
    # 遠くの信号灯
    sig = C.emissive("Signal", (0.1, 1.0, 0.35), strength=40)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=6, location=(-1400, EDGE_Y + 200, 300)); bpy.context.object.data.materials.append(sig)
    # 向こう側の暗い建物(窓明かり少し)
    P.box("FarBuilding", (3000, 50, 900), (0, EDGE_Y + 900, 300), mat=C.principled("FarB", (0.02, 0.02, 0.025), rough=0.8))
    winm = C.emissive("FarWin", (1.0, 0.8, 0.55), strength=2.0)
    winc = C.emissive("FarWinCool", (0.7, 0.85, 1.0), strength=1.2)
    for i in range(90):
        P.box(f"FarWin{i}", (rnd.uniform(12, 30), 2, rnd.uniform(8, 16)), (rnd.uniform(-1600, 1600), EDGE_Y + 874, rnd.uniform(40, 600)),
              mat=winm if rnd.random() < 0.6 else winc)

    # ベンチと忘れ傘
    bench(0, 0)
    umbrella((-40, -36, 0.1), lean_deg=-17, yaw_deg=0)

    # 雨(屋根の外側)
    rain(sc, (-700, 700), (ROOF_Y + 10, ROOF_Y + 450), top=420, count=40000)
    # 屋根からの雨だれ(雨樋の線から落ちる細い筋)
    rain2 = rain(sc, (-700, 700), (ROOF_Y + 2, ROOF_Y + 12), top=318, count=3000)
    rain2.name = "DripEmitter"

    # カメラ: ローアングルからゆっくり傘へ
    cam, tgt = C.camera((-150, -330, 45), (-40, -25, 40), lens=50, fstop=0.028)  # 実効 F2.8
    P.key_seq(cam, "location", [(1, (-170, -360, 48)), (FRAMES, (-105, -250, 40))])
    P.key_seq(tgt, "location", [(1, (-42, -25, 42)), (FRAMES, (-40, -28, 38))])
    sc.view_settings.exposure = 0.2
    bpy.ops.ptcache.bake_all(bake=True)


if __name__ == "__main__":
    C.run_shot("h15_rain_umbrella", build, FRAMES)
