"""K04 / カット4-1: 駅の忘れ物保管庫(無名・文字なし)。スチールラックのパイプに、
紙タグを付けた閉じた傘が何十本も手元で吊るされ、日付ごとに無地の仕切り札で区切られている。
蛍光灯の下、カメラは通路をゆっくりドリー。5秒。
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
AISLE = 70.0          # 通路の半幅(ラック前面の y)
RACK_D = 45.0         # ラックの奥行き
X0, X1 = -420.0, 400.0
BARS_Z = (196.0, 102.0)   # 吊りパイプの高さ(上段・下段)
CEIL = 270.0


def variants(rnd):
    """傘のバリエーション(メッシュ元)。カメラの外に置いて複製元にする。"""
    specs = []
    for i in range(10):
        specs.append(dict(kind="vinyl", color=None, handle=rnd.choice(["white", "white", "clear", "black"]),
                          loose=rnd.uniform(0.0, 0.35)))
    for c in ((0.75, 0.85, 0.95), (0.95, 0.9, 0.75), (0.85, 0.95, 0.85)):
        specs.append(dict(kind="vinyl", color=c, handle="white", loose=rnd.uniform(0, 0.3)))
    for c in ("navy", "black", "charcoal", "burgundy", "beige", "green", "navy", "black", "olive"):
        specs.append(dict(kind="cloth", color=c, handle=rnd.choice(["black", "black", "wood"]), loose=rnd.uniform(0.1, 0.5)))
    roots = []
    for i, s in enumerate(specs):
        r = K.make_umbrella(f"V{i:02d}", (0, 0, -2000 - i * 100), state="closed", kind=s["kind"], color=s["color"],
                            tag=True, handle=s["handle"], loose=s["loose"], seed=100 + i)
        K.hide_tree(r)
        roots.append(r)
    return roots, specs


def rack(name, x0, x1, side, steel, shelf_m):
    """片側のスチールラック: 支柱・吊りパイプ2段・最下段の棚板。side=+1/-1(通路の左右)。"""
    yf = side * AISLE
    yb = side * (AISLE + RACK_D)
    n = int((x1 - x0) // 120)
    for i in range(n + 1):
        x = x0 + i * (x1 - x0) / n
        for y in (yf, yb):
            P.box(f"{name}Post{i}_{y}", (3.5, 3.5, 230), (x, y, 115), mat=steel)
        for z in (12, 228):
            P.box(f"{name}Tie{i}_{z}", (3, RACK_D, 3), (x, (yf + yb) / 2, z), mat=steel)
    for z in BARS_Z:
        for y in (yf + side * 14, ):
            P.cyl(f"{name}Bar{z}", 1.2, x1 - x0, ((x0 + x1) / 2, y, z), rot=(0, math.radians(90), 0), mat=steel, verts=12)
    # 上の棚板(箱が載る)と最下段の棚板
    P.box(f"{name}TopShelf", (x1 - x0, RACK_D, 2), ((x0 + x1) / 2, (yf + yb) / 2, 229), mat=shelf_m)
    P.box(f"{name}LowShelf", (x1 - x0, RACK_D, 2), ((x0 + x1) / 2, (yf + yb) / 2, 10), mat=shelf_m)
    for y in (yf, yb):
        for z in (10, 229):
            P.box(f"{name}Rail{y}_{z}", (x1 - x0, 3.5, 4), ((x0 + x1) / 2, y, z), mat=steel)
    return side * 14 + yf


def build(sc):
    P.world_studio((0.02, 0.02, 0.02), (0.08, 0.08, 0.075), (0.2, 0.2, 0.19), 1.0, camera_color=(0.01, 0.01, 0.01))
    rnd = random.Random(4)
    steel = F.mat_painted("RackSteel", (0.42, 0.45, 0.44), rough=0.45, wear=0.1, scale=0.05)
    shelf_m = F.mat_painted("ShelfM", (0.5, 0.52, 0.5), rough=0.5, wear=0.15, scale=0.05)

    # 部屋
    floor = F.mat_concrete("StoreFloor", (0.36, 0.37, 0.36), rough=0.4, scale=0.05)
    P.plane("Floor", (2400, 800), (50, 0, 0), mat=floor)
    wall = C.principled("StoreWall", (0.62, 0.64, 0.6), rough=0.8, bump=0.05, bump_scale=100)
    for s in (-1, 1):
        P.plane(f"Wall{s}", (2400, CEIL), (50, s * 140, CEIL / 2), rot=(90, 0, 0), mat=wall)
    P.plane("EndWall", (300, CEIL), (X1 + 140, 0, CEIL / 2), rot=(90, 0, 90), mat=wall)
    P.plane("Ceiling", (2400, 300), (50, 0, CEIL), rot=(180, 0, 0), mat=C.principled("Ceil", (0.7, 0.7, 0.68), rough=0.8, emission=(0.6, 0.62, 0.6), emission_strength=0.08))
    # 突き当たりの扉(無地の鉄扉)
    P.box("EndDoor", (4, 90, 200), (X1 + 137, 0, 100), mat=F.mat_painted("DoorM", (0.35, 0.4, 0.42), rough=0.5, wear=0.1))
    P.box("EndDoorKnob", (6, 3, 3), (X1 + 133, 35, 100), mat=C.principled("Knob", (0.7, 0.7, 0.72), metallic=1, rough=0.3))

    # 蛍光灯(通路の上に1列+ラック上)
    for i, x in enumerate(range(int(X0), int(X1) + 120, 160)):
        K.fluorescent(f"Fl{i}", (x, 0, CEIL - 6), length=120, axis="X", strength=14, temp=5000)
    for i, x in enumerate((-260, 60, 380)):
        L = C.area_light((x, 0, CEIL - 12), (0, 0, 0), 1, 9e4, (0.93, 0.97, 1.0), f"Fluo{i}").data
        L.shape = "RECTANGLE"; L.size = 300; L.size_y = 30
        U = C.area_light((x, 0, CEIL - 20), (180, 0, 0), 1, 1.5e4, (0.93, 0.97, 1.0), f"FluoUp{i}").data
        U.shape = "RECTANGLE"; U.size = 300; U.size_y = 60

    # ラックと傘
    vroots, specs = variants(rnd)
    divider_m = C.principled("Divider", (0.9, 0.9, 0.86), rough=0.6)
    clip_cols = [C.principled(f"Clip{i}", c, rough=0.4) for i, c in
                 enumerate([(0.7, 0.1, 0.08), (0.08, 0.25, 0.6), (0.1, 0.45, 0.15), (0.8, 0.6, 0.05)])]
    count = 0
    for side in (-1, 1):
        bar_y = rack(f"R{side}", X0, X1, side, steel, shelf_m)
        for z in BARS_Z:
            x = X0 + 6
            group = 0
            while x < X1 - 6:
                # 日付ごとの区切り(無地の札+色クリップ)
                if rnd.random() < 0.07:
                    P.box(f"Div{side}_{z}_{int(x)}", (0.3, 12, 16), (x, bar_y, z - 10), mat=divider_m)
                    P.box(f"DivClip{side}_{z}_{int(x)}", (1.5, 3, 3), (x, bar_y, z - 1), mat=clip_cols[group % 4])
                    group += 1
                    x += 5
                if rnd.random() < 0.05:      # ところどころ空き
                    x += rnd.uniform(8, 20); continue
                v = rnd.randrange(len(vroots))
                hx, hy, hz = K.HOOK_INNER
                # 手元のフックが通路と直交する向き(-Y 側へ曲がる)になるよう Z=90°。フック内側がパイプに載る
                yaw = 90 if side > 0 else -90
                tip = (x, bar_y + (-hx if yaw > 0 else hx), z - 1.2 - hz)   # Z回転後もフック内側がパイプ上
                r = K.clone(vroots[v], f"U{count}", tip, (rnd.uniform(-2, 2), rnd.uniform(-2, 2), yaw + rnd.uniform(-6, 6)))
                count += 1
                x += rnd.uniform(7.5, 10.5) if specs[v]["kind"] == "vinyl" else rnd.uniform(8.5, 11)
        # 最下段の棚: 立てて詰めた傘のケース(段ボール箱に挿してある)
        box_m = C.principled("Cardboard", (0.45, 0.32, 0.18), rough=0.85, bump=0.1, bump_scale=30)
        for i, x in enumerate(range(int(X0) + 60, int(X1) - 60, 160)):
            if rnd.random() < 0.4:
                continue
            P.open_box(f"Box{side}_{i}", (55, 35, 22), (x, side * (AISLE + RACK_D / 2), 22), wall=0.5, mat=box_m, bevel=0.2)
        # 上の棚の段ボール
        for i, x in enumerate(range(int(X0) + 40, int(X1) - 40, 90)):
            if rnd.random() < 0.5:
                P.box(f"TopBox{side}_{i}", (rnd.uniform(40, 70), 38, rnd.uniform(18, 30)), (x, side * (AISLE + RACK_D / 2), 245),
                      mat=box_m, bevel=0.3)
    print("umbrellas:", count)

    P.reflection_probe((0, 0, 140), radius=500)
    # カメラ: 通路の中をゆっくり前進(少し右の棚を向く)
    cam, tgt = C.camera((X0 - 60, -10, 145), (X0 + 300, 45, 125), lens=28, fstop=0.035)
    P.key_seq(cam, "location", [(1, (X0 - 70, -12, 146)), (FRAMES, (X0 + 70, -8, 142))])
    P.key_seq(tgt, "location", [(1, (X0 + 230, 48, 125)), (FRAMES, (X0 + 380, 42, 120))])
    F.set_interp(cam, "LINEAR"); F.set_interp(tgt, "LINEAR")
    sc.view_settings.exposure = 0.6
    sc.view_settings.look = "AgX - Medium High Contrast"


if __name__ == "__main__":
    K.set_episode("ep02")
    C.run_shot("k04_lost_storage", build, FRAMES)
