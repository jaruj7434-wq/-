"""C06 / カット 5-3: 工場の作業台。四角く切ったウエス(色・柄いろいろの綿布)が重なっていて、
いちばん上の1枚がふわりと浮き、油で黒く汚れた歯車の上をすーっとなでる。通ったところから
鋼の地肌が現れてピカッと光る(手は出さない・布がひとりでに動く)。5秒。

ふき取りはマテリアルの "Wipe" 値(歯車のオブジェクト座標 X)をウエスの位置に合わせてキー。
ウエスは格子メッシュに決定的なしわ(布シミュなし)。金属の映り込みは world グラデーション+反射プローブ+ライトカード。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from mathutils import Vector
import common as C
import props as P
import factory_parts as F
import fuku_parts2 as K

FRAMES = 120
GEAR_R = 11.6
GEAR_W = 3.2
HUB_H = 0.6
RAG = 19.0
STACK = Vector((-30.0, 6.0, 0.0))
RAGS = [((0.70, 0.12, 0.10), None, None), ((0.85, 0.85, 0.82), "stripe", (0.12, 0.22, 0.45)),
        ((0.15, 0.30, 0.55), None, None), ((0.92, 0.80, 0.30), "check", (0.85, 0.85, 0.80)),
        ((0.30, 0.55, 0.40), None, None), ((0.85, 0.50, 0.55), "dot", (0.95, 0.93, 0.90)),
        ((0.55, 0.55, 0.57), "stripe", (0.9, 0.9, 0.88)), ((0.20, 0.45, 0.70), "check", (0.92, 0.92, 0.9)),
        ((0.95, 0.94, 0.90), "stripe", (0.75, 0.15, 0.12))]


def build(sc):
    rnd = random.Random(6)
    F.world_gradient(top=(0.32, 0.29, 0.25), horizon=(0.12, 0.10, 0.085), bottom=(0.03, 0.028, 0.025),
                     strength=1.0, camera_color=(0.05, 0.045, 0.04), strips=0.0)
    # --- 作業台(鋼板の天板・使い込み)と奥の壁
    top_m = F.mat_painted("BenchTop", (0.16, 0.18, 0.17), rough=0.5, wear=0.35, scale=0.05)
    P.box("Bench", (160, 90, 4), (0, 10, -2), mat=top_m, bevel=0.3)
    P.box("BenchEdge", (160, 3, 6), (0, -36.5, -3), mat=F.mat_painted("BenchEdgeM", (0.35, 0.30, 0.18), rough=0.45, wear=0.3))
    P.box("Wall", (400, 4, 200), (0, 70, 60), mat=F.mat_painted("WallM", (0.10, 0.095, 0.09), rough=0.8, wear=0.0, scale=0.01))
    # --- 歯車(主役)と、奥のまだ汚れた部品
    gear_m, wipe = K.mat_oily_metal("GearOily")
    gme = K.gear_mesh("GearMesh", teeth=26, r_root=GEAR_R - 1.5, r_tip=GEAR_R, width=GEAR_W, r_hub=4.2, r_bore=1.6, hub_h=HUB_H)
    gear = bpy.data.objects.new("Gear", gme); bpy.context.collection.objects.link(gear)
    gme.materials.append(gear_m)
    P.add_mod(gear, "BEVEL", width=0.12, segments=2, limit_method="ANGLE")
    gear.location = (6, 0, 0); gear.rotation_euler.z = math.radians(4)
    dirty2, _ = K.mat_oily_metal("PartsOily")
    g2 = bpy.data.objects.new("Gear2", K.gear_mesh("Gear2Mesh", teeth=16, r_root=5.6, r_tip=6.8, width=2.6, r_hub=2.6, r_bore=1.0, hub_h=1.2))
    bpy.context.collection.objects.link(g2); g2.data.materials.append(dirty2)
    g2.location = (24, 30, 0); g2.rotation_euler = (0, 0, 0.3)
    sh = P.cyl("Shaft", 1.5, 34, (-4, 36, 1.5), rot=(0, math.radians(90), math.radians(-12)), mat=dirty2, verts=24)
    P.cyl("Bearing", 3.2, 2.4, (-4 + 15 * math.cos(math.radians(-12)), 36 + 15 * math.sin(math.radians(-12)), 3.2),
          rot=(0, math.radians(90), math.radians(-12)), mat=dirty2, verts=32)

    # --- ウエスの山
    mats = [K.mat_cotton(f"Rag{i}", c, pat, c2 or (0.9, 0.9, 0.88), scale=0.25 if pat != "dot" else 0.6)
            for i, (c, pat, c2) in enumerate(RAGS)]
    z = 0.0
    for i, m in enumerate(mats[:-1]):
        me = K.rag_mesh(f"RagMesh{i}", rnd, size=RAG * rnd.uniform(0.95, 1.05), crumple=0.12, fray=0.5)
        o = bpy.data.objects.new(f"RagS{i}", me); bpy.context.collection.objects.link(o)
        me.materials.append(m)
        P.add_mod(o, "SOLIDIFY", thickness=0.25, offset=0)
        z += 0.42
        o.location = (STACK.x + rnd.uniform(-1.2, 1.2), STACK.y + rnd.uniform(-1.2, 1.2), z)
        o.rotation_euler.z = math.radians(rnd.uniform(-9, 9))
    # 動く1枚(いちばん上): ふき取り中はくしゅっと丸まった形
    me = K.rag_mesh("RagMove", rnd, size=RAG, crumple=0.9, fray=0.5, res=24)
    rag = bpy.data.objects.new("RagMove", me); bpy.context.collection.objects.link(rag)
    me.materials.append(mats[-1])
    P.add_mod(rag, "SOLIDIFY", thickness=0.25, offset=0)
    P.add_mod(rag, "SUBSURF", levels=1, render_levels=1)
    # 平ら → 丸まった、のシェイプキー(持ち上がると布が少したわむ)
    rag.shape_key_add(name="Basis")
    sk = rag.shape_key_add(name="Bunch")
    for v, kv in zip(me.vertices, sk.data):
        x, y, zz = v.co
        r2 = min(1.0, (x * x + y * y) / (RAG / 2) ** 2)
        crum = 0.5 + 0.5 * math.sin(0.55 * x + 1.3) * math.cos(0.6 * y - 0.4) + 0.35 * math.sin(1.1 * (x + y))
        kv.co = (x * 0.62, y * 0.58, (1.0 - r2) * (1.6 + 1.6 * crum) + 0.5 * zz)   # くしゅっと丸めた小山
    flat = rag.shape_key_add(name="Flat")
    for v, kv in zip(me.vertices, flat.data):
        x, y, zz = v.co
        kv.co = (x, y, zz * 0.12)
    # 動き: 山の上(平ら)→ 浮く → 歯車の左端へ → 右へなでる(2往復目は少し奥)→ 浮いて去る
    top_z = z + 0.42
    gx, gy = gear.location.x, gear.location.y
    face = GEAR_W + HUB_H + 0.1
    xs, xe = gx - GEAR_R - 4, gx + GEAR_R + 5
    keys = [(1, (STACK.x, STACK.y, top_z), (0, 0, 2), "BEZIER"),
            (8, (STACK.x, STACK.y, top_z), (0, 0, 2), "BEZIER"),
            (22, (STACK.x + 8, STACK.y - 2, top_z + 9), (6, -4, 10), "BEZIER"),
            (34, (xs, gy + 1, face + 1.2), (0, 3, -6), "LINEAR"),
            (84, (xe, gy - 1, face + 0.2), (0, -3, 4), "BEZIER"),
            (102, (xe + 12, gy + 4, face + 10), (-6, 8, 16), "BEZIER"),
            (FRAMES, (xe + 30, gy + 14, face + 22), (-10, 10, 24), "BEZIER")]
    K.key_multi(rag, keys)
    # なでている間の小さな揺れ(手の圧を表す上下)
    for f in range(38, 84, 6):
        t = (f - 34) / 50
        x = xs + (xe - xs) * t
        rag.location = (x, gy + 1 - 2 * t + 0.6 * math.sin(f * 0.7), face + 1.2 - 1.0 * t - 0.25 * (f % 12 == 2))
        rag.keyframe_insert("location", frame=f)
    for fc in F.fcurves(rag):
        if fc.data_path == "location":
            for kp in fc.keyframe_points:
                if 34 <= kp.co.x < 84:
                    kp.interpolation = "BEZIER"
    for f, b, fl in ((1, 0.0, 1.0), (10, 0.0, 1.0), (24, 0.75, 0.0), (34, 1.0, 0.0), (84, 1.0, 0.0), (104, 0.6, 0.0)):
        sk.value = b; sk.keyframe_insert("value", frame=f)
        flat.value = fl; flat.keyframe_insert("value", frame=f)
    # ふき取り位置(歯車のローカル X)。ウエスの後ろ側の縁に合わせる
    lead = 4.0
    for f, x in ((1, -100.0), (33, xs - gx - 2), (84, xe - gx + lead), (FRAMES, xe - gx + lead)):
        F.key_socket(wipe, f, x)
    F.set_interp(gear_m.node_tree, "LINEAR")

    # --- 照明: 左上の暖かいキー、右奥のリム、きれいになった面に映る横長のライトカード(最後に光が走る)
    key = C.area_light((-60, -50, 90), (0, 0, 0), 60, 2.2e4, (1.0, 0.88, 0.72), "Key"); C.light_look_at(key, (0, 0, 0))
    rim = C.area_light((40, 70, 40), (0, 0, 0), 40, 9e3, (0.9, 0.93, 1.0), "Rim"); C.light_look_at(rim, (6, 0, 2))
    fill = C.area_light((60, -70, 50), (0, 0, 0), 80, 4e3, (0.85, 0.9, 1.0), "Fill"); C.light_look_at(fill, (0, 0, 0))
    card = P.light_card("Glint", (90, 14), (6, 40, 60), (6, 0, 0), strength=6.0, color=(1.0, 0.95, 0.88))
    P.key_seq(card, "location", [(80, (-40, 40, 55)), (FRAMES, (50, 30, 55))])
    P.key_seq(card, "rotation_euler", [(80, tuple(card.rotation_euler)), (FRAMES, tuple(card.rotation_euler))])
    P.reflection_probe((6, 0, 10), radius=120, clip_start=0.5)

    cam, tgt = C.camera((-8, -78, 54), (-4, 4, 2), lens=50, fstop=2.0)
    P.key_seq(cam, "location", [(1, (-12, -80, 56)), (FRAMES, (2, -70, 48))])
    P.key_seq(tgt, "location", [(1, (-8, 4, 2)), (FRAMES, (4, 2, 2))])
    cam.data.dof.focus_object = None
    cam.data.dof.focus_distance = 88
    sc.view_settings.exposure = 0.75
    sc.view_settings.look = "AgX - Medium High Contrast"


if __name__ == "__main__":
    C.EPISODE = "ep04"
    C.run_shot("c06_wiping_rag", build, FRAMES)
