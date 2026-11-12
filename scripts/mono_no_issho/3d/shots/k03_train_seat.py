"""K03 / カット3-1: 通勤電車の車内(特定の車両ではない汎用デザイン・文字なし)。
ロングシートの端、袖仕切りに閉じたビニール傘が立てかけられたまま。
駅に停車中でドアの外はホーム。終盤ドアが閉まり、電車が動き出して窓の外の景色が流れ始める。5秒。

- 1〜70f: ゆっくりカメラが傘へ寄る(停車中)。
- 70〜92f: 両開きドアが閉まる。
- 96f〜: 発車。窓・ドアガラスの外(ホーム・街)が左へ流れ始め、吊り革が慣性で揺れる。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P
import factory_parts as F
import kasa_parts as K

FRAMES = 120
WALL_Y = 142.0          # ドア側の壁(車内側の面)
DOOR_X = (-65.0, 65.0)  # ドア開口
SEAT_X0 = 78.0          # ロングシート端(袖仕切りの位置)
CEIL = 228.0


def car_interior(rnd):
    wall = C.principled("CarWall", (0.80, 0.79, 0.75), rough=0.35, coat=0.2)
    panel = C.principled("CarPanel", (0.70, 0.71, 0.70), rough=0.4, coat=0.2)
    floor = F.mat_concrete("CarFloor", (0.24, 0.23, 0.21), rough=0.6, scale=0.3)
    steel = C.principled("Stainless", (0.78, 0.78, 0.8), metallic=1, rough=0.22, noise_rough=(0.15, 0.3))
    glass = C.principled("CarGlass", (0.85, 0.9, 0.9), rough=0.02, alpha=0.08, coat=1.0)
    rubber = C.principled("DoorRubber", (0.03, 0.03, 0.03), rough=0.6)

    # 床・天井(中央が少し高いカマボコ型を段で表現)
    P.box("Floor", (1400, 300, 4), (150, 0, -2), mat=floor)
    P.box("FloorStrip", (1400, 6, 0.4), (150, 0, 0.2), mat=C.principled("FloorLine", (0.2, 0.2, 0.2), rough=0.6))
    P.box("Ceiling", (1400, 210, 4), (150, 0, CEIL + 2), mat=wall)
    for s in (-1, 1):
        P.box(f"CeilSlope{s}", (1400, 50, 4), (150, s * 125, CEIL - 10), (s * math.radians(-28), 0, 0), mat=wall)
    # ドア側の壁(開口部を残して箱で組む)
    win_z = (95.0, 178.0)
    def wall_piece(name, x0, x1, z0, z1, y=WALL_Y + 4):
        P.box(name, (x1 - x0, 8, z1 - z0), ((x0 + x1) / 2, y, (z0 + z1) / 2), mat=wall)
    wall_piece("WallL", -560, DOOR_X[0] - 70, 0, 205)       # ドア左の戸袋
    wall_piece("WallLPocket", DOOR_X[0] - 70, DOOR_X[0], 0, 205)
    wall_piece("WallTopDoor", DOOR_X[0], DOOR_X[1], 190, 215)
    # 右側(座席側): 腰壁・窓・幕板
    wall_piece("WallRPocket", DOOR_X[1], DOOR_X[1] + 70, 0, 205)
    wall_piece("WallLow", DOOR_X[1] + 70, 760, 0, win_z[0])
    wall_piece("WallHigh", -560, 760, win_z[1], 215)
    # 窓(2枚、間に柱)
    xs = [DOOR_X[1] + 70, 290, 300, 520, 530, 760]
    for i in range(0, len(xs) - 1, 2):
        x0, x1 = xs[i], xs[i + 1]
        P.box(f"Win{i}", (x1 - x0, 0.6, win_z[1] - win_z[0]), ((x0 + x1) / 2, WALL_Y + 6, sum(win_z) / 2), mat=glass)
        for (zz, hh) in ((win_z[0], 3), (win_z[1], 3)):
            P.box(f"WinSill{i}_{zz}", (x1 - x0, 6, hh), ((x0 + x1) / 2, WALL_Y + 1, zz), mat=panel, bevel=0.5)
    for i in range(1, len(xs) - 1, 2):
        x0, x1 = xs[i], xs[i + 1]
        P.box(f"WinPost{i}", (x1 - x0, 8, win_z[1] - win_z[0]), ((x0 + x1) / 2, WALL_Y + 4, sum(win_z) / 2), mat=wall)
    # 窓のブラインド(上に巻き上げた状態の帯)
    for i, (x0, x1) in enumerate(((DOOR_X[1] + 70, 290), (300, 520))):
        P.box(f"Blind{i}", (x1 - x0 - 4, 5, 6), ((x0 + x1) / 2, WALL_Y - 1, win_z[1] - 4), mat=panel, bevel=1.0)
    # ドア枠(ステンレス)と床の敷居
    P.box("DoorSill", (DOOR_X[1] - DOOR_X[0], 30, 1.2), (0, WALL_Y + 6, 0.6), mat=steel)
    for x in DOOR_X:
        P.box(f"DoorJamb{x}", (4, 10, 190), (x, WALL_Y + 2, 95), mat=steel, bevel=0.6)
    P.box("DoorHead", (DOOR_X[1] - DOOR_X[0] + 8, 10, 4), (0, WALL_Y + 2, 190), mat=steel, bevel=0.6)
    # ドア上の案内表示(無地・暗い液晶)
    P.box("DoorDisplay", (70, 3, 16), (0, WALL_Y - 1, 203), mat=C.principled("LCD", (0.01, 0.012, 0.015), rough=0.08, coat=1))

    # 両開きドア(ステンレス+縦長の窓)
    doors = []
    leaf_w = (DOOR_X[1] - DOOR_X[0]) / 2
    for s in (-1, 1):
        root = bpy.data.objects.new(f"Door{s}", None); bpy.context.collection.objects.link(root)
        parts = [
            P.box(f"DoorLeafBot{s}", (leaf_w, 3, 92), (0, 0, 46), mat=steel, bevel=0.4),
            P.box(f"DoorLeafTop{s}", (leaf_w, 3, 18), (0, 0, 180), mat=steel, bevel=0.4),
            P.box(f"DoorLeafIn{s}", (8, 3, 80), (-s * (leaf_w / 2 - 4), 0, 132), mat=steel, bevel=0.4),
            P.box(f"DoorLeafOut{s}", (8, 3, 80), (s * (leaf_w / 2 - 4), 0, 132), mat=steel, bevel=0.4),
            P.box(f"DoorGlass{s}", (leaf_w - 16, 0.6, 80), (0, 0, 132), mat=glass),
            P.box(f"DoorEdge{s}", (2.5, 3.4, 189), (-s * leaf_w / 2, 0, 94.5), mat=rubber, bevel=0.6),
        ]
        for p in parts:
            p.parent = root
        doors.append(root)
    # 開いた位置(戸袋の中)→閉じた位置
    for s, d in zip((-1, 1), doors):
        open_x = s * (leaf_w / 2 + leaf_w + 2)
        shut_x = s * leaf_w / 2
        P.key_seq(d, "location", [(1, (open_x, WALL_Y + 9, 0)), (70, (open_x, WALL_Y + 9, 0)),
                                  (90, (shut_x + s * 1.5, WALL_Y + 9, 0)), (94, (shut_x, WALL_Y + 9, 0))])
    # 戸袋の内側カバー(開いたドアを隠す)は WallLPocket/WallRPocket が担当(ドアはその外側 y を走る)

    # ロングシート(座席側)
    moquette = F.mat_canvas("Moquette", (0.08, 0.14, 0.26), weave=2.2, rough=0.95)
    base = C.principled("SeatBase", (0.55, 0.56, 0.57), metallic=0.6, rough=0.35)
    seat_len = 470.0
    sx = SEAT_X0 + 4 + seat_len / 2
    P.box("SeatBase", (seat_len, 46, 34), (sx, WALL_Y - 26, 17), mat=base, bevel=1.0)
    P.box("SeatKick", (seat_len, 2, 26), (sx, WALL_Y - 50, 15), mat=C.principled("Kick", (0.12, 0.12, 0.13), rough=0.5))
    # 座面は1人分ずつ少し凹ませたクッション
    for i in range(7):
        x = SEAT_X0 + 6 + 33 + i * 66
        P.box(f"Cushion{i}", (64, 50, 10), (x, WALL_Y - 28, 39), mat=moquette, bevel=3.5, segments=4)
        P.box(f"Back{i}", (64, 10, 46), (x, WALL_Y - 5, 70), (math.radians(-8), 0, 0), mat=moquette, bevel=3.5, segments=4)
    # 袖仕切り(座席端の板)+スタンションポール
    P.box("SidePartition", (5, 58, 100), (SEAT_X0, WALL_Y - 29, 50), mat=panel, bevel=2.0, segments=4)
    P.box("SidePartTop", (7, 60, 5), (SEAT_X0, WALL_Y - 29, 101), mat=steel, bevel=2.0)
    P.cyl("Stanchion", 1.6, CEIL - 101, (SEAT_X0 - 1, WALL_Y - 60, 101 + (CEIL - 101) / 2), mat=steel, verts=20)

    # 網棚(座席の上)
    for y in (WALL_Y - 8, WALL_Y - 22, WALL_Y - 34):
        P.cyl(f"Rack{y}", 0.7, seat_len, (sx, y, 182), rot=(0, math.radians(90), 0), mat=steel, verts=10)
    for i in range(5):
        P.box(f"RackBracket{i}", (2, 34, 3), (SEAT_X0 + 30 + i * 110, WALL_Y - 18, 182), mat=steel)

    # 吊り革(座席前・ドア前)
    rail_y = WALL_Y - 62
    P.cyl("StrapRail", 1.4, 1200, (150, rail_y, 205), rot=(0, math.radians(90), 0), mat=steel, verts=16)
    strap_m = C.principled("Strap", (0.85, 0.85, 0.83), rough=0.5)
    ring_m = C.principled("RingM", (0.92, 0.92, 0.9), rough=0.3, coat=0.4)
    straps = []
    for i, x in enumerate(range(-420, 640, 36)):
        piv = bpy.data.objects.new(f"StrapPiv{i}", None); bpy.context.collection.objects.link(piv)
        piv.location = (x, rail_y, 204)
        st = P.box(f"StrapBelt{i}", (2.8, 0.6, 24), (0, 0, -12), mat=strap_m, bevel=0.2)
        bpy.ops.mesh.primitive_torus_add(major_radius=6.5, minor_radius=1.0, major_segments=32, minor_segments=8,
                                         location=(0, 0, -30), rotation=(0, math.radians(90), 0))
        rg = bpy.context.object; rg.name = f"StrapRing{i}"; rg.data.materials.append(ring_m); bpy.ops.object.shade_smooth()
        rg.scale = (1, 0.82, 1)
        st.parent = piv; rg.parent = piv
        straps.append(piv)
    # 発車の慣性で吊り革が揺れる(Y軸回り、少しずつ位相をずらす)
    for i, piv in enumerate(straps):
        ph = rnd.uniform(-1.5, 1.5)
        keys = [(1, 0.0), (96, 0.0)]
        for k, (df, ang) in enumerate(((7, 11), (15, 7), (23, 9.5), (31, 8))):
            keys.append((96 + df + int(ph), ang))
        P.key_seq(piv, "rotation_euler", [(f, (0, math.radians(a), 0)) for f, a in keys])

    # 天井照明(2列の連続した蛍光灯カバー)
    lampm = C.emissive("CarLamp", temp=5600, strength=9)
    for s in (-1, 1):
        P.box(f"LampCover{s}", (1300, 18, 2.5), (150, s * 68, CEIL - 1.5), mat=lampm)
        L = C.area_light((150, s * 68, CEIL - 6), (0, 0, 0), 1, 1.6e5, (0.95, 0.98, 1.0), f"CarLight{s}").data
        L.shape = "RECTANGLE"; L.size = 1200; L.size_y = 30
    # 空調ダクトの吹出口(中央の帯)
    P.box("Vent", (1300, 30, 2), (150, 0, CEIL - 1), mat=C.principled("VentM", (0.6, 0.6, 0.6), rough=0.5, bump=0.5, bump_scale=400))
    return doors


def outside(rnd):
    """ドア・窓の外: 屋根付きのホーム(無名・文字なし)と、その向こうの街。発車で -X 方向へ流れる。"""
    root = bpy.data.objects.new("Outside", None); bpy.context.collection.objects.link(root)
    objs = []
    wet = C.principled("PlatWet", (0.32, 0.32, 0.31), rough=0.3, noise_rough=(0.08, 0.6), bump=0.05, bump_scale=80)
    objs.append(P.box("Platform", (6000, 700, 20), (0, WALL_Y + 22 + 350, -10), mat=wet))
    objs.append(P.box("PlatEdge", (6000, 22, 0.5), (0, WALL_Y + 32, 0.3), mat=C.principled("PlatEdgeW", (0.85, 0.85, 0.82), rough=0.4)))
    objs.append(P.box("Tactile", (6000, 30, 0.8), (0, WALL_Y + 110, 0.4),
                      mat=C.principled("TactileY", (0.8, 0.6, 0.05), rough=0.4, bump=0.5, bump_scale=3000)))
    colm = C.principled("PlatCol", (0.62, 0.63, 0.64), rough=0.5)
    for x in range(-3000, 3000, 520):
        objs.append(P.box(f"PCol{x}", (30, 30, 380), (x, WALL_Y + 420, 190), mat=colm))
    objs.append(P.box("PlatRoof", (6000, 700, 10), (0, WALL_Y + 380, 390), mat=C.principled("PRoof", (0.42, 0.43, 0.45), rough=0.6)))
    tube = C.emissive("PlatTube", temp=6000, strength=12)
    for x in range(-3000, 3000, 260):
        objs.append(P.box(f"PLamp{x}", (150, 8, 3), (x, WALL_Y + 250, 383), mat=tube))
    # 無地の駅名板風(光る白い板・文字なし)
    for x in (-900, 700):
        objs.append(P.box(f"PSign{x}", (160, 6, 40), (x, WALL_Y + 400, 240), mat=C.emissive("PSignM", (0.9, 0.93, 0.95), strength=2)))
    # ベンチ(ホーム側)
    benchm = C.principled("PBench", (0.12, 0.35, 0.3), rough=0.35, coat=0.4)
    for x in (-500, 380):
        objs.append(P.box(f"PBench{x}", (180, 40, 6), (x, WALL_Y + 470, 44), mat=benchm, bevel=1))
        objs.append(P.box(f"PBenchB{x}", (180, 6, 40), (x, WALL_Y + 492, 70), mat=benchm, bevel=1))
    # 向こうの線路と、さらに向こうのビル群(曇天の昼)
    objs.append(P.box("FarGround", (8000, 3000, 10), (0, WALL_Y + 2200, -130), mat=C.principled("FarG", (0.18, 0.18, 0.17), rough=0.9)))
    bmats = [C.principled(f"Bld{i}", c, rough=0.7) for i, c in enumerate(
        [(0.55, 0.55, 0.53), (0.42, 0.43, 0.45), (0.65, 0.62, 0.57), (0.35, 0.37, 0.4), (0.7, 0.7, 0.68)])]
    winm = C.principled("BldWin", (0.15, 0.18, 0.22), rough=0.1, coat=1)
    x = -4000
    while x < 4000:
        w = rnd.uniform(250, 700); h = rnd.uniform(600, 2600); d = WALL_Y + rnd.uniform(1400, 2600)
        objs.append(P.box(f"Bld{int(x)}", (w, 400, h), (x + w / 2, d, h / 2 - 120), mat=rnd.choice(bmats)))
        # 窓の横帯
        for k in range(int(h // 320)):
            objs.append(P.box(f"BldW{int(x)}_{k}", (w * 0.92, 2, 90), (x + w / 2, d - 201, 140 + k * 320 - 120), mat=winm))
        x += w + rnd.uniform(40, 200)
    for o in objs:
        o.parent = root
    # 発車: 96f から加速しながら -X へ(最後の方で約 6m/s 相当)
    keys = [(1, 0.0), (96, 0.0)]
    for f in range(100, FRAMES + 1, 4):
        t = (f - 96) / 24.0
        keys.append((f, -0.5 * 260 * t * t))  # 加速度 2.6m/s^2
    P.key_seq(root, "location", [(f, (v, 0, 0)) for f, v in keys])
    F.set_interp(root, "LINEAR")
    return root


def build(sc):
    P.world_studio((0.2, 0.21, 0.22), (0.62, 0.65, 0.7), (0.9, 0.93, 0.98), 1.0)
    rnd = random.Random(3)
    car_interior(rnd)
    outside(rnd)
    # 外光(曇天・ホーム屋根の下)
    sun = C.area_light((0, WALL_Y + 600, 300), (0, 0, 0), 600, 3e5, (0.85, 0.9, 1.0), "SkyFill")
    C.light_look_at(sun, (60, 60, 60))
    # 忘れ物の傘: 石突きは床、手元を袖仕切りの上端に預ける
    K.make_umbrella("LostUmbrella", (SEAT_X0 + 17.5, WALL_Y - 66, 0.3), rotation_deg=(-3, -10, 0), state="closed", kind="vinyl")
    # 金属の映り込み用プローブ
    P.reflection_probe((40, 40, 110), radius=600)
    # カメラ: 向かいの座席前あたりから、袖仕切りと傘、ドアをとらえてゆっくり寄る
    cam, tgt = C.camera((-45, -60, 128), (70, 92, 76), lens=24, fstop=0.022)
    P.key_seq(cam, "location", [(1, (-58, -72, 130)), (FRAMES, (-28, -42, 124))])
    P.key_seq(tgt, "location", [(1, (66, 96, 80)), (FRAMES, (80, 90, 68))])
    focus = bpy.data.objects.new("Focus", None); bpy.context.collection.objects.link(focus)
    focus.location = (SEAT_X0 + 12, WALL_Y - 66, 50)
    cam.data.dof.focus_object = focus
    sc.view_settings.exposure = -0.7
    sc.view_settings.look = "AgX - Medium High Contrast"


if __name__ == "__main__":
    K.set_episode("ep02")
    C.run_shot("k03_train_seat", build, FRAMES)
