"""H10 / カット3-6: 夜の自販機(無地・ロゴなし)。カメラが硬貨投入口へドリー。
1円玉が投入口に入るが、受け付けられず下の返却口にカランと落ちてくる。5秒。

- 1〜50f: 夜の路地に光る自販機のワイド → 投入口へゆっくりドリーイン。
- 50〜64f: 画面右(手・画面外)から1円玉が現れ、縦の投入口へ吸い込まれる(~62f で消える)。
- 68〜84f: カメラが少し下へティルトし、返却口を見る。
- 84f: 返却口に1円玉が落ちてきて跳ね、~100f で静止(物理)。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P

FRAMES = 120
MW, MD, MH = 100.0, 72.0, 183.0      # 自販機 幅・奥行・高さ (cm)
FY = -MD / 2                          # 前面の y
SLOT = (36.0, FY - 1.6, 98.0)         # 投入口(前面右側・ドア上)
RET = (36.0, FY - 3.0, 79.0)          # 返却口(カップ中心)


def can(name, loc, color, h=12.2, r=3.3):
    body = P.cyl(name, r, h, (loc[0], loc[1], loc[2] + h / 2), mat=C.principled(name + "M", color, metallic=0.3, rough=0.3, coat=0.5), verts=24)
    P.cyl(name + "Top", r * 0.92, 0.4, (loc[0], loc[1], loc[2] + h + 0.2), mat=bpy.data.materials.get("Alu") or
          C.principled("Alu", (0.8, 0.8, 0.82), metallic=1, rough=0.25), verts=24)
    return body


def bottle(name, loc, color, cap):
    h = 16.0
    P.cyl(name, 3.4, h, (loc[0], loc[1], loc[2] + h / 2), mat=bpy.data.materials.get("PET") or
          C.principled("PET", (0.85, 0.92, 0.95), rough=0.08, alpha=0.35), verts=24, bevel=0.6)
    P.cyl(name + "Label", 3.46, 6.0, (loc[0], loc[1], loc[2] + 7.0), mat=C.principled(name + "L", color, rough=0.35, coat=0.4), verts=24)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=3.4, radius2=1.3, depth=3.5, location=(loc[0], loc[1], loc[2] + h + 1.75))
    bpy.context.object.data.materials.append(bpy.data.materials["PET"])
    P.cyl(name + "Cap", 1.45, 1.6, (loc[0], loc[1], loc[2] + h + 4.2), mat=C.principled(name + "C", cap, rough=0.4), verts=16)


def build(sc):
    P.world_studio((0.004, 0.005, 0.008), (0.05, 0.055, 0.075), (0.3, 0.33, 0.4), 1.0, camera_color=(0.003, 0.004, 0.008))
    P.physics(sc, FRAMES, time_scale=1.0, substeps=60)
    rnd = random.Random(10)

    # 地面(濡れたアスファルト: 粗さムラで水たまり風) + ブロック塀
    ground = P.plane("Ground", 3000, (0, 0, 0), mat=C.principled("WetAsphalt", (0.035, 0.035, 0.038), rough=0.25,
                                                                  noise_rough=(0.03, 0.45), bump=0.1, bump_scale=300))
    curb = P.box("Curb", (3000, 15, 12), (0, -200, 6), mat=C.principled("Concrete", (0.25, 0.25, 0.24), rough=0.85, bump=0.2, bump_scale=200))
    wall = P.box("BlockWall", (3000, 15, 170), (0, MD / 2 + 12, 85),
                 mat=C.principled("Block", (0.28, 0.28, 0.27), rough=0.9, bump=0.3, bump_scale=600))
    # ブロックの目地(横線)
    for i in range(1, 9):
        P.box(f"Joint{i}", (3000, 0.6, 0.8), (0, MD / 2 + 4.4, i * 19.5), mat=C.principled("JointM", (0.12, 0.12, 0.12), rough=0.9))

    # ---- 自販機本体
    paint = C.principled("Paint", (0.6, 0.62, 0.65), rough=0.35, coat=0.6)
    accent = C.principled("Accent", (0.04, 0.12, 0.35), rough=0.3, coat=0.6)
    darkm = C.principled("DarkPlastic", (0.02, 0.02, 0.022), rough=0.4)
    steel = C.principled("Steel", (0.75, 0.76, 0.78), metallic=1, rough=0.38, noise_rough=(0.3, 0.45), bump=0.05, bump_scale=200)
    P.box("Body", (MW, MD, MH), (0, 0, MH / 2 + 4), mat=paint, bevel=1.0)
    P.box("Plinth", (MW - 4, MD - 4, 4), (0, 0, 2), mat=darkm)
    P.box("Header", (MW + 0.4, 2, 14), (0, FY - 0.6, MH - 6), mat=accent, bevel=0.5)   # 無地の帯(ロゴなし)
    # 商品ディスプレイ(ガラス窓の奥に3段)
    win_bottom, win_top = 108.0, MH - 16
    P.box("DisplayBack", (MW - 10, 2, win_top - win_bottom), (0, FY + 22, (win_top + win_bottom) / 2),
          mat=C.emissive("Backlight", (0.85, 0.92, 1.0), strength=1.2))
    P.box("Window", (MW - 8, 0.4, win_top - win_bottom), (0, FY - 0.4, (win_top + win_bottom) / 2),
          mat=C.principled("WinGlass", (0.9, 0.95, 1.0), rough=0.03, alpha=0.12))
    # 本体前面の窓部分を抜く(ブーリアン)
    body = bpy.data.objects["Body"]
    cut = P.box("WinCut", (MW - 8, 30, win_top - win_bottom), (0, FY + 10, (win_top + win_bottom) / 2))
    bo = body.modifiers.new("win", "BOOLEAN"); bo.object = cut; bo.solver = "EXACT"
    cut.hide_render = True; cut.hide_viewport = True

    cols = [(0.7, 0.05, 0.05), (0.05, 0.2, 0.6), (0.9, 0.6, 0.05), (0.05, 0.4, 0.15), (0.9, 0.9, 0.9),
            (0.4, 0.2, 0.05), (0.05, 0.05, 0.05), (0.85, 0.3, 0.05), (0.5, 0.75, 0.9)]
    rows = 3
    row_h = (win_top - win_bottom) / rows
    btn_on = C.emissive("BtnOn", (0.3, 1.0, 0.4), strength=6)
    btn_off = C.emissive("BtnOff", (1.0, 0.25, 0.15), strength=3)
    price = C.emissive("PriceTag", (0.95, 0.95, 0.9), strength=2.0)
    shelf = C.principled("ShelfM", (0.8, 0.8, 0.82), rough=0.4)
    for r in range(rows):
        z0 = win_bottom + r * row_h + 7
        P.box(f"Shelf{r}", (MW - 10, 18, 1.0), (0, FY + 10, z0 - 0.5), mat=shelf)
        for i in range(10):
            x = -MW / 2 + 9 + i * 9.2
            if (r + i) % 3 == 0:
                bottle(f"B{r}_{i}", (x, FY + 8, z0), rnd.choice(cols), rnd.choice(cols))
            else:
                can(f"K{r}_{i}", (x, FY + 8, z0), rnd.choice(cols))
            # 商品下の値札(読めない白い光の帯)とボタン
            P.box(f"Tag{r}_{i}", (6.5, 0.3, 1.6), (x, FY - 0.9, z0 - 3.2), mat=price)
            P.box(f"Btn{r}_{i}", (3.2, 0.8, 1.2), (x, FY - 1.0, z0 - 5.4), mat=btn_on if rnd.random() < 0.8 else btn_off, bevel=0.3)

    # ---- 下半分: 操作パネル(投入口・返却レバー・紙幣口)
    P.box("ControlPanel", (22, 2.0, 40), (SLOT[0], FY - 0.8, 92), mat=darkm, bevel=0.6)
    plate = P.box("SlotPlate", (7.5, 1.6, 9), (SLOT[0], SLOT[1] + 0.2, SLOT[2]), mat=steel, bevel=0.6)
    P.box("SlotSlit", (0.35, 0.4, 3.4), (SLOT[0], SLOT[1] - 0.45, SLOT[2]), mat=C.principled("Black", (0, 0, 0), rough=1))
    P.box("BillSlot", (8, 1.6, 3), (SLOT[0], SLOT[1] + 0.2, SLOT[2] + 11), mat=steel, bevel=0.4)
    P.box("BillSlit", (7, 0.3, 0.3), (SLOT[0], SLOT[1] - 0.65, SLOT[2] + 11), mat=C.emissive("BillGlow", (0.2, 0.6, 1.0), strength=4))
    P.cyl("ReturnLever", 1.6, 1.4, (SLOT[0] - 7, SLOT[1] - 0.2, SLOT[2]), (math.radians(90), 0, 0), steel, bevel=0.3)
    P.box("Display7segBg", (7, 0.6, 2.2), (SLOT[0], SLOT[1] - 0.3, SLOT[2] + 6.4), mat=C.principled("SegBg", (0.02, 0.0, 0.0), rough=0.1, coat=1.0))
    for d in range(3):  # 「000」風の小さな赤い表示(数字の形は作らない)
        P.box(f"Seg{d}", (1.1, 0.3, 1.4), (SLOT[0] + 1.2 + d * 1.6, SLOT[1] - 0.65, SLOT[2] + 6.4), mat=bpy.data.materials.get("SegM") or C.emissive("SegM", (1.0, 0.08, 0.02), strength=1.5))
    # 返却口(金属のカップ。上の黒い穴から硬貨が落ちてくる)
    cup = P.open_box("ReturnCup", (10, 6, 3), (RET[0], RET[1], RET[2]), wall=0.4, mat=steel, bevel=0.15)
    P.passive_mesh(cup, friction=0.4, bounce=0.35, margin=0.02)
    cupf = P.box("ReturnCupFloor", (9.2, 5.2, 0.4), (RET[0], RET[1], RET[2] - 1.3), mat=steel)
    C.rigid(cupf, False, "BOX", friction=0.4, bounce=0.35)
    P.box("ChuteHole", (6, 0.5, 5), (RET[0], FY - 0.3, RET[2] + 4.5), mat=C.principled("Black2", (0, 0, 0), rough=1))
    P.box("ReturnHood", (11, 4.4, 1.0), (RET[0], FY - 2.2, RET[2] + 7.5), mat=darkm, bevel=0.3)
    # 商品取出口
    P.box("Dispenser", (MW - 20, 3, 22), (0, FY - 1.0, 26), mat=darkm, bevel=0.8)
    P.box("DispFlap", (MW - 24, 0.6, 18), (0, FY - 2.6, 26), mat=C.principled("Smoke", (0.03, 0.03, 0.035), rough=0.1, coat=0.8), bevel=0.3)

    # ---- 1円玉(投入側): アニメーションのみ
    coin_in = P.make_any_coin("1", "CoinIn", (SLOT[0] + 12, SLOT[1] - 12, SLOT[2] + 4), (0, math.radians(90), 0))
    path = [(1, (SLOT[0] + 40, SLOT[1] - 30, SLOT[2] + 10)), (50, (SLOT[0] + 40, SLOT[1] - 30, SLOT[2] + 10)),
            (51, (SLOT[0] + 9, SLOT[1] - 10, SLOT[2] + 2)), (58, (SLOT[0], SLOT[1] - 2.6, SLOT[2] + 0.3)),
            (60, (SLOT[0], SLOT[1] - 1.6, SLOT[2])), (64, (SLOT[0], SLOT[1] + 2.5, SLOT[2]))]
    for f, loc in path:
        C.key(coin_in, "location", f, loc)
    C.key(coin_in, "rotation_euler", 51, (0, math.radians(90), math.radians(-35)))
    C.key(coin_in, "rotation_euler", 58, (0, math.radians(90), 0))
    for fc in P._fcurves(coin_in):
        for kp in fc.keyframe_points:
            if kp.co[0] in (50, 51):
                kp.interpolation = "CONSTANT"
    # 入りきったら隠す
    coin_in.hide_render = False; coin_in.keyframe_insert("hide_render", frame=64)
    coin_in.hide_render = True; coin_in.keyframe_insert("hide_render", frame=65)
    coin_in.hide_render = True; coin_in.keyframe_insert("hide_render", frame=1)
    coin_in.hide_render = False; coin_in.keyframe_insert("hide_render", frame=51)

    # ---- 1円玉(返却側): 物理で返却口に落ちる
    coin_out = P.make_any_coin("1", "CoinOut", (RET[0] + 0.5, FY - 3.0, RET[2] + 5.5), (math.radians(60), 0.3, 0))
    C.rigid(coin_out, True, "CYLINDER", mass=0.15, friction=0.35, bounce=0.45)
    P.hold_then_release(coin_out, 84, park=(500, 500, 0))

    # ---- 照明
    # 自販機の窓からの光(前方へ)+ 内部の照り返し
    C.area_light((0, FY - 4, (win_top + win_bottom) / 2), (-90, 0, 0), 1, 400000, (0.85, 0.92, 1.0), "MachineGlow")
    g = bpy.data.objects["MachineGlow"].data; g.shape = "RECTANGLE"; g.size = MW - 10; g.size_y = win_top - win_bottom
    C.area_light((0, FY - 45, 210), (-25, 0, 0), 80, 300000, (0.85, 0.92, 1.0), "Spill")
    # 遠くの街灯(白色LED)と、月明かり(青)
    C.point_light((-450, -350, 520), 1.2e6, (0.95, 0.9, 0.8), 15, "StreetLamp")
    C.area_light((300, -600, 800), (40, 0, 30), 600, 1.5e6, (0.4, 0.5, 0.9), "Moon")
    C.area_light((SLOT[0] + 10, FY - 70, SLOT[2] + 50), (0, 0, 0), 50, 30000, (0.8, 0.88, 1.0), "PanelFill")
    C.light_look_at(bpy.data.objects["PanelFill"], (SLOT[0], FY, SLOT[2] - 8))
    P.light_card("SlotCard", (40, 40), (SLOT[0] + 30, FY - 60, SLOT[2] + 20), SLOT, strength=1.2, color=(0.85, 0.92, 1.0))

    # ---- カメラ: ワイド → 投入口 → 返却口
    cam, tgt = C.camera((60, -420, 120), (0, 0, 100), lens=35, fstop=0.08)  # 実効 F8
    P.key_seq(cam, "location", [(1, (70, -430, 125)), (50, (46, -72, 106)), (70, (45, -68, 104)), (90, (41, -64, 108)), (FRAMES, (40, -60, 108))])
    P.key_seq(tgt, "location", [(1, (0, 0, 100)), (50, (SLOT[0], FY, SLOT[2])), (70, (SLOT[0], FY, SLOT[2] - 2)),
                                (90, (RET[0], FY, RET[2] + 3)), (FRAMES, (RET[0], FY, RET[2] + 1))])
    cam.data.lens = 35; cam.data.keyframe_insert("lens", frame=1)
    cam.data.lens = 50; cam.data.keyframe_insert("lens", frame=50)
    cam.data.lens = 50; cam.data.keyframe_insert("lens", frame=70)
    cam.data.lens = 65; cam.data.keyframe_insert("lens", frame=92)
    sc.view_settings.exposure = 0.3


if __name__ == "__main__":
    C.run_shot("h10_vending", build, FRAMES)
