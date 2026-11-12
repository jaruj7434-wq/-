"""H06 / カット2-7: 圧印プレスのマクロ。下型(臼)の上に無地の円盤。上型(杵)が一気に降りて打ち、上がると
円盤に図柄が現れている。打撃の瞬間にわずかなカメラの揺れ。次の円盤が送り込まれて2打目。5秒。

キー: 1打目 22→30(打撃=30)→44 上昇 / 46〜50 突き上げ / 52〜62 送り(打った硬貨は右へ、次の円盤が左から)
      / 62〜66 新しい円盤が臼に収まる / 2打目 78→86(打撃=86)→100 上昇。
台本の注記「硬貨の図柄は映さない/ボカす」に配慮し、低い角度+浅い被写界深度で図柄は読めない程度に留める
(SHOW_DESIGN=False で図柄を出さない版にもできる)。
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P
import factory_parts as F

FRAMES = 120
SHOW_DESIGN = True
HIT1, HIT2 = 30, 86
Z_IN, Z_PLATE = 0.075, 0.175       # 臼の中の硬貨中心高さ / 送り板の上
TOP = 3.2                          # 上型の待機高さ(下面)


def build(sc):
    F.world_gradient(top=(0.4, 0.39, 0.37), horizon=(0.07, 0.07, 0.075), bottom=(0.02, 0.02, 0.02),
                     strength=0.8, strips=4.0, strip_color=(3.0, 2.9, 2.7), camera_color=(0.02, 0.02, 0.022))
    die_m, _ = F.mat_steel("DieSteel", (0.62, 0.63, 0.65), rough=0.1, streak_axis="Z")
    plate_m, _ = F.mat_steel("PlateSteel", (0.5, 0.5, 0.52), rough=0.28, streak_axis="X")
    dark_m = F.mat_painted("Holder", (0.07, 0.075, 0.08), rough=0.4, wear=0.4, scale=1.0)
    green = F.mat_painted("Frame", (0.14, 0.22, 0.2), rough=0.45, wear=0.25, scale=0.6)

    # --- 下側: 送り板(臼の穴つき)と臼(下型)
    plate = P.box("DiePlate", (16, 7, 0.5), (0, 0, 0.1 - 0.25), mat=plate_m, bevel=0.03)
    cut = P.cyl("Hole", 1.03, 2, (0, 0, 0), verts=96)
    b = plate.modifiers.new("hole", "BOOLEAN"); b.object = cut; b.operation = "DIFFERENCE"; b.solver = "EXACT"
    bpy.context.view_layer.objects.active = plate
    bpy.ops.object.modifier_apply(modifier="hole"); bpy.data.objects.remove(cut)
    # 送りレール(手前と奥のガイド)
    P.box("RailBack", (16, 0.6, 0.3), (0, 1.4, 0.1 + 0.15), mat=plate_m, bevel=0.03)
    anvil = P.cyl("Anvil", 1.0, 3.0, (0, 0, -1.5), mat=die_m, verts=96, bevel=0.02)
    C.key(anvil, "location", 1, (0, 0, -1.5))
    C.key(anvil, "location", 46, (0, 0, -1.5)); C.key(anvil, "location", 50, (0, 0, -1.4))
    C.key(anvil, "location", 62, (0, 0, -1.4)); C.key(anvil, "location", 66, (0, 0, -1.5))
    P.box("LowerHolder", (18, 10, 3), (0, 0, -1.9), mat=dark_m, bevel=0.1)
    P.box("Bolster", (30, 18, 4), (0, 0, -5.4), mat=green, bevel=0.15)

    # --- 上型(杵)とホルダー
    bpy.ops.object.empty_add(location=(0, 0, TOP)); up = bpy.context.object; up.name = "UpperRig"
    P.cyl("Hammer", 1.0, 1.2, (0, 0, 0.6), mat=die_m, verts=96, bevel=0.02).parent = up
    bpy.ops.mesh.primitive_cone_add(vertices=96, radius1=1.0, radius2=1.7, depth=1.4, location=(0, 0, 1.9))
    cone = bpy.context.object; cone.name = "Shank"; cone.data.materials.append(die_m)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35)); cone.parent = up
    P.cyl("DieRing", 2.4, 1.5, (0, 0, 3.3), mat=dark_m, verts=64, bevel=0.06).parent = up
    P.box("UpperHolder", (14, 9, 4), (0, 0, 6.0), mat=dark_m, bevel=0.12).parent = up
    P.box("Ram", (22, 14, 10), (0, 0, 13.0), mat=green, bevel=0.2).parent = up
    for f, z in ((1, TOP), (22, TOP), (HIT1, 0.15), (HIT1 + 2, 0.15), (44, TOP),
                 (78, TOP), (HIT2, 0.15), (HIT2 + 2, 0.15), (100, TOP)):
        C.key(up, "location", f, (0, 0, z))
    for fc in F.fcurves(up):
        for kp in fc.keyframe_points:
            if int(round(kp.co.x)) in (22, 78):
                kp.interpolation = "QUAD"; kp.easing = "EASE_IN"      # 一気に落ちる
            elif int(round(kp.co.x)) in (HIT1, HIT2):
                kp.interpolation = "CONSTANT"
    # プレス柱(背景)
    for s in (-1, 1):
        P.box(f"Column{s}", (5, 6, 40), (s * 15, 8, 12), mat=green, bevel=0.2)

    # --- 硬貨
    def coin(name, keys, hit):
        m = C.mat_coin(name, stamped=False)
        c = C.make_coin(name, m, keys[0][1], verts=128)
        for f, loc in keys:
            C.key(c, "location", f, loc)
        st = m.node_tree.nodes["Stamp"].outputs[0]
        F.key_socket(st, 1, 0.0); F.key_socket(st, hit - 1, 0.0)
        F.key_socket(st, hit, 1.0 if SHOW_DESIGN else 0.0)
        F.set_interp(m.node_tree, "CONSTANT")
        return c
    c1 = coin("Coin1", [(1, (0, 0, Z_IN)), (46, (0, 0, Z_IN)), (50, (0, 0, Z_IN + 0.1)),
                        (52, (0, 0, Z_PLATE)), (62, (2.25, 0, Z_PLATE))], HIT1)
    c2 = coin("Coin2", [(1, (-2.25, 0, Z_PLATE)), (52, (-2.25, 0, Z_PLATE)), (62, (0, 0, Z_PLATE)),
                        (66, (0, 0, Z_IN))], HIT2)
    for c in (c1, c2):
        C.key(c, "rotation_euler", 1, (0, 0, 0.4))
    # 列で待つ次の円盤
    q = []
    for i in range(3):
        qc = C.make_coin(f"Queue{i}", C.mat_coin(f"Q{i}", stamped=False), (-4.5 - 2.25 * i, 0, Z_PLATE), (0, 0, i), verts=96)
        C.key(qc, "location", 52, (-4.5 - 2.25 * i, 0, Z_PLATE)); C.key(qc, "location", 62, (-2.25 - 2.25 * i, 0, Z_PLATE))
        q.append(qc)
    # 送り爪(奥側から伸びるフォーク)
    finger = P.box("Finger", (0.6, 2.0, 0.3), (-3.4, 0, Z_PLATE + 0.05), mat=plate_m, bevel=0.04)
    C.key(finger, "location", 1, (-3.4 - 2.25 * 3, 0, Z_PLATE + 0.05))
    C.key(finger, "location", 52, (-3.4 - 2.25 * 3, 0, Z_PLATE + 0.05))
    C.key(finger, "location", 62, (-1.15 - 2.25 * 3, 0, Z_PLATE + 0.05))
    # 打った硬貨の出口側に既に打たれた硬貨(シュートへ)
    for i in range(2):
        d = C.make_coin(f"Done{i}", C.mat_coin(f"D{i}", stamped=SHOW_DESIGN), (2.25 + 2.25 * i, 0, Z_PLATE), (0, 0, 1.3 * i), verts=96)
        C.key(d, "location", 52, (2.25 + 2.25 * i, 0, Z_PLATE)); C.key(d, "location", 62, (4.5 + 2.25 * i, 0, Z_PLATE))

    # --- 照明
    C.area_light((-6, -10, 9), (50, 0, -30), 6, 900, (1.0, 0.92, 0.82), "Key")
    C.area_light((5, 9, 4), (75, 0, 150), 5, 1400, (0.65, 0.78, 1.0), "Rim")
    C.area_light((8, -6, 2), (80, 0, 55), 3, 300, (1.0, 0.85, 0.7), "Kick")
    # 打撃の瞬間の作業灯のちらつき(衝撃で揺れる吊り灯)
    # 背景のボケ玉(遠くの機械の表示灯)
    for k, (x, y, z, t) in enumerate(((-14, 40, 1.5, 2600), (12, 45, -1.0, 4200), (28, 60, 4.0, 3000), (-30, 55, 0.0, 5000), (40, 70, -2.0, 2200))):
        P.cyl(f"Bokeh{k}", 1.5, 0.2, (x, y, z), (math.radians(90), 0, 0), C.emissive(f"BokehM{k}", temp=t, strength=250), verts=16)
    # 奥の機械群(暗くボケる)
    for k, (x, w, h) in enumerate(((-45, 30, 50), (-10, 20, 35), (25, 35, 60), (60, 25, 40))):
        P.box(f"BgMach{k}", (w, 15, h), (x, 85, -10 + h / 2), mat=green, bevel=0.5)
    C.area_light((0, 40, 40), (-50, 0, 0), 60, 6e4, (1.0, 0.85, 0.65), "BgLight")

    # --- カメラ(低い角度のマクロ)
    cam, tgt = C.camera((5.5, -12.0, 4.2), (0.2, 0.0, 1.0), lens=70, fstop=3.2)
    C.key(cam, "location", 1, (5.8, -12.6, 4.4)); C.key(cam, "location", FRAMES, (4.8, -11.0, 3.8))
    dof_t = bpy.data.objects.new("Focus", None); bpy.context.collection.objects.link(dof_t)
    dof_t.location = (0, -0.4, 0.15); cam.data.dof.focus_object = dof_t
    F.set_interp(cam, "LINEAR")
    F.shake(cam, HIT1, amp=0.07, decay=7, seed=1)
    F.shake(cam, HIT2, amp=0.07, decay=7, seed=2)
    sc.view_settings.exposure = 0.0


if __name__ == "__main__":
    C.run_shot("h06_press", build, FRAMES)
