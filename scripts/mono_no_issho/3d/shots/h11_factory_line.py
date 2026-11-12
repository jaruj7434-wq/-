"""H11 / カット4-6: 再び動き出す硬貨の製造ライン(ワイド)。天井の水銀灯が順に点き、表示灯が点灯、
コンベアが動き出して大量の硬貨が流れ、プレス機が上下を繰り返す。暖色の工場照明+薄いもや。ゆっくりドリー。5秒。

キー: 1〜30 天井灯が奥から順に点灯(少しちらつく) / 8〜40 各機械の表示灯が点灯
      / 20〜50 コンベアが加速して定速へ / 30〜 プレス機のラムが周期運動を開始。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P
import factory_parts as F

FRAMES = 120
LINES_Y = (0.0, 260.0)       # 2本のライン
BELT_W = 34.0
BELT_Z = 85.0
X0, X1 = -900.0, 900.0
SPEED = 45.0                 # 定速時の搬送速度 cm/s
PRESS_X = (-780.0, -250.0, 300.0, 820.0)


def belt_travel(f):
    """フレーム f までの移動量(20〜50 で加速→定速)。"""
    t0, t1 = 20, 50
    if f <= t0:
        return 0.0
    v = SPEED / 24.0
    if f <= t1:
        u = (f - t0) / (t1 - t0)
        return v * (t1 - t0) * (u ** 2) / 2
    return v * (t1 - t0) / 2 + v * (f - t1)


def key_travel(obj, axis_vals, base):
    for f in range(1, FRAMES + 1, 4):
        loc = list(base); loc[0] += belt_travel(f)
        C.key(obj, "location", f, tuple(loc))
    loc = list(base); loc[0] += belt_travel(FRAMES); C.key(obj, "location", FRAMES, tuple(loc))
    F.set_interp(obj, "LINEAR")


def press_unit(name, x, y, body_m, steel_m, beacon_on, cycle_start, period, phase):
    P.box(name + "Base", (170, 150, 40), (x, y, 20), mat=body_m, bevel=2)
    for s in (-1, 1):
        P.box(name + f"Col{s}", (130, 34, 230), (x, y + s * 62, 155), mat=body_m, bevel=2)
    P.box(name + "Crown", (180, 140, 70), (x, y, 300), mat=body_m, bevel=3)
    ram = P.box(name + "Ram", (88, 100, 60), (x, y, 200), mat=steel_m, bevel=1.5)
    # ラムの周期運動
    C.key(ram, "location", 1, (x, y, 200)); C.key(ram, "location", cycle_start, (x, y, 200))
    f = cycle_start + phase
    while f < FRAMES + period:
        C.key(ram, "location", f, (x, y, 200))
        C.key(ram, "location", f + period * 0.45, (x, y, 135))
        C.key(ram, "location", f + period * 0.6, (x, y, 135))
        f += period
    # 制御盤と表示灯(文字・ロゴなし)
    P.box(name + "Panel", (50, 20, 70), (x + 110, y - 70, 120), mat=body_m, bevel=1)
    lamp_m = C.emissive(name + "BeaconM", color=(1.0, 0.55, 0.1), strength=0.0)
    em = lamp_m.node_tree.nodes["Emission"].inputs["Strength"]
    F.key_socket(em, 1, 0.0); F.key_socket(em, beacon_on, 0.0); F.key_socket(em, beacon_on + 1, 40.0)
    F.set_interp(lamp_m.node_tree, "CONSTANT")
    P.cyl(name + "Beacon", 7, 14, (x + 70, y - 40, 342), mat=lamp_m, verts=24)
    P.cyl(name + "BeaconBase", 8, 4, (x + 70, y - 40, 333), mat=steel_m, verts=24)
    g = C.emissive(name + "GreenM", color=(0.2, 1.0, 0.35), strength=0.0)
    gs = g.node_tree.nodes["Emission"].inputs["Strength"]
    F.key_socket(gs, 1, 0.0); F.key_socket(gs, beacon_on + 6, 0.0); F.key_socket(gs, beacon_on + 7, 25.0)
    F.set_interp(g.node_tree, "CONSTANT")
    P.cyl(name + "Ind", 2.5, 2, (x + 100, y - 81, 135), (math.radians(90), 0, 0), g, verts=16)
    P.cyl(name + "Ind2", 2.5, 2, (x + 120, y - 81, 135), (math.radians(90), 0, 0), lamp_m, verts=16)


def build(sc):
    rnd = random.Random(4)
    C.world((0.02, 0.018, 0.016))
    body_m = F.mat_painted("MachineGreen", (0.17, 0.27, 0.25), rough=0.45, wear=0.2, scale=0.01)
    grey_m = F.mat_painted("MachineGrey", (0.32, 0.33, 0.34), rough=0.45, wear=0.2, scale=0.01)
    steel_m, _ = F.mat_steel("Steel", (0.6, 0.6, 0.62), rough=0.2, streak_axis="Z")
    frame_m = F.mat_painted("ConvFrame", (0.08, 0.08, 0.085), rough=0.5, wear=0.4, scale=0.02)
    yel = F.mat_painted("Yellow", (0.62, 0.43, 0.04), rough=0.5, wear=0.3, scale=0.02)
    coin_m = C.mat_coin("CoinShared")
    # 粗さ控えめ・映り込みを足して遠目でもキラッと光る硬貨
    coin_far = C.principled("CoinFar", (0.86, 0.87, 0.88), metallic=1.0, rough=0.22)

    # --- 建屋(床・壁・柱・天井トラス)
    floor_m = F.mat_concrete("Floor", (0.28, 0.27, 0.25), rough=0.6, scale=0.005)
    P.plane("Floor", (6000, 4000), (0, 600, 0), mat=floor_m)
    wall_m = F.mat_painted("Wall", (0.3, 0.31, 0.3), rough=0.7, wear=0.05, scale=0.003)
    P.plane("BackWall", (6000, 1400), (0, 1400, 700), rot=(90, 0, 0), mat=wall_m)
    P.plane("Ceiling", (6000, 4000), (0, 600, 1100), rot=(180, 0, 0), mat=C.principled("CeilM", (0.05, 0.05, 0.05), rough=0.8))
    for i in range(-6, 7):
        P.box(f"Col{i}", (50, 50, 1100), (i * 450, 1300, 550), mat=grey_m)
        P.box(f"Truss{i}", (25, 2400, 60), (i * 450, 300, 1040), mat=grey_m)
    # 床の通路ライン(黄色・文字なし)
    for y in (-150, 420):
        P.box(f"Walkway{y}", (5000, 8, 0.4), (0, y, 0.2), mat=yel)

    # --- 天井灯: 奥から順に点灯(ちらつき)
    lamps = []
    for row, y in enumerate((-100, 350, 800)):
        for i in range(8):
            x = -1400 + i * 400
            on = 2 + int((x + 1400) / 400) * 3 + row * 2 + rnd.randint(0, 2)
            m = C.emissive(f"LampM{row}{i}", temp=3300, strength=0.0)
            s = m.node_tree.nodes["Emission"].inputs["Strength"]
            F.key_socket(s, 1, 0.0); F.key_socket(s, on, 0.0)
            F.key_socket(s, on + 1, 30.0); F.key_socket(s, on + 2, 6.0); F.key_socket(s, on + 3, 40.0)
            F.key_socket(s, on + 8, 60.0)
            F.set_interp(m.node_tree, "LINEAR")
            P.cyl(f"Lamp{row}{i}", 28, 10, (x, y, 960), mat=m, verts=32)
            P.cyl(f"LampHood{row}{i}", 32, 18, (x, y, 975), mat=grey_m, verts=32)
            l = C.point_light((x, y, 930), 0.0, (1.0, 0.78, 0.52), radius=25, name=f"LampL{row}{i}")
            l.data.energy = 0; l.data.keyframe_insert("energy", frame=on)
            l.data.energy = 2.5e6; l.data.keyframe_insert("energy", frame=on + 3)
            l.data.energy = 4.0e6; l.data.keyframe_insert("energy", frame=on + 8)
            lamps.append(l)

    # --- コンベア+硬貨
    belt_src = None
    for li, y in enumerate(LINES_Y):
        bpy.ops.object.empty_add(location=(0, y, 0)); flow = bpy.context.object; flow.name = f"Flow{li}"
        key_travel(flow, None, (0, y, 0))
        belt_m = F.mat_rubber(f"Belt{li}", coord_obj=flow, scale=0.08)
        P.box(f"Belt{li}", (X1 - X0, BELT_W, 4), ((X0 + X1) / 2, y, BELT_Z - 2), mat=belt_m)
        for s in (-1, 1):
            P.box(f"Side{li}{s}", (X1 - X0, 4, 10), ((X0 + X1) / 2, y + s * (BELT_W / 2 + 2), BELT_Z + 1), mat=steel_m, bevel=0.5)
        P.box(f"Under{li}", (X1 - X0, BELT_W + 8, 14), ((X0 + X1) / 2, y, BELT_Z - 11), mat=frame_m)
        for k in range(int((X1 - X0) / 150) + 1):
            x = X0 + k * 150
            for s in (-1, 1):
                P.box(f"Leg{li}{k}{s}", (5, 5, BELT_Z - 18), (x, y + s * (BELT_W / 2 - 2), (BELT_Z - 18) / 2), mat=frame_m)
        # 硬貨(メッシュ共有の複製)。手前の区間は実物の1円玉、奥は軽量版。
        src_near = C.make_coin(f"CoinSrcN{li}", coin_m, (0, 0, -500), verts=32)
        src_far = C.make_coin(f"CoinSrcF{li}", coin_far, (0, 0, -500), verts=16)
        travel = belt_travel(FRAMES)
        n = 0
        x = X0 - travel - 50
        while x < X1:
            for _ in range(rnd.randint(2, 4)):
                cx = x + rnd.uniform(-2, 2)
                cy = rnd.uniform(-BELT_W / 2 + 3, BELT_W / 2 - 3)
                src = src_near if cx < -100 else src_far
                c = F.dup(src, f"BC{li}_{n}", (cx, cy, BELT_Z + 0.08 + rnd.uniform(0, 0.15)),
                          (rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12), rnd.uniform(0, 6.3)))
                c.parent = flow
                c.location = (cx, cy, BELT_Z + 0.08 + rnd.uniform(0, 0.15))
                c.location.y -= 0  # flow の y は既にライン位置
                n += 1
            x += rnd.uniform(3.0, 5.5)
        # flow は y=ライン位置 にあるので子の y はローカル

    # --- プレス機(各ライン4台)。ライン上に跨がる
    for li, y in enumerate(LINES_Y):
        for k, x in enumerate(PRESS_X):
            press_unit(f"P{li}{k}", x, y, body_m if (k + li) % 2 == 0 else grey_m, steel_m,
                       beacon_on=8 + k * 6 + li * 3, cycle_start=30 + k * 3, period=26 + li * 2, phase=k * 5)
    # 奥のライン(シルエット)
    for k in range(6):
        P.box(f"BgMach{k}", (220, 160, 260 + 60 * (k % 3)), (-1200 + k * 480, 900, 130 + 30 * (k % 3)), mat=grey_m, bevel=3)
    # 手前の安全柵
    for k in range(14):
        P.cyl(f"Fence{k}", 3, 110, (-1300 + k * 200, -260, 55), mat=yel, verts=12)
    P.cyl("FenceBar", 3, 2700, (0, -260, 105), (0, math.radians(90), 0), yel, verts=12)
    P.cyl("FenceBar2", 3, 2700, (0, -260, 60), (0, math.radians(90), 0), yel, verts=12)

    # --- もや(体積)と補助光
    F.haze((5200, 3000, 1100), (0, 500, 550), density=0.00008, color=(0.95, 0.85, 0.72), anisotropy=0.5)
    C.area_light((-1800, -900, 600), (60, 0, -60), 600, 4e6, (0.55, 0.65, 0.9), "WindowFill")

    # --- カメラ: 斜め上からのワイド、ゆっくりドリー
    cam, tgt = C.camera((-1250, -150, 270), (300, 140, 60), lens=26, fstop=5.6)
    C.key(cam, "location", 1, (-1290, -170, 280)); C.key(cam, "location", FRAMES, (-1110, -120, 255))
    C.key(tgt, "location", 1, (300, 150, 70)); C.key(tgt, "location", FRAMES, (360, 130, 60))
    foc = bpy.data.objects.new("Focus", None); bpy.context.collection.objects.link(foc)
    foc.location = (-500, 0, BELT_Z); cam.data.dof.focus_object = foc
    F.set_interp(cam, "BEZIER")
    sc.view_settings.exposure = 0.0


if __name__ == "__main__":
    C.run_shot("h11_factory_line", build, FRAMES)
