"""K05 / カット4-3: 紐で束ねた忘れ物の傘が平台車に積まれ、駅の裏の通路を運び出される(人物なし)。
カメラは台車を押す人の目線(POV)。手前に台車のハンドル、その先に傘の束。通路の突き当たりの
開いた鉄扉から曇天の外光。台車ごとゆっくり扉へ進む。5秒。
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
CW = 200.0            # 通路の幅
DOOR_X = 760.0        # 突き当たりの扉
CEIL = 260.0
TRAVEL = 340.0        # 台車の移動量(約 0.8m/s 相当より少し遅い)


def hand_truck(name):
    """平台車(90x60cm、樹脂の天板、キャスター4つ、後ろに折りたたみハンドル)。原点=天板中心の床位置。"""
    root = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(root)
    deck_m = C.principled("TruckDeck", (0.08, 0.2, 0.42), rough=0.45, bump=0.15, bump_scale=6)
    rub = C.principled("TruckRubber", (0.03, 0.03, 0.032), rough=0.65)
    steel = C.principled("TruckSteel", (0.72, 0.73, 0.75), metallic=1, rough=0.3, noise_rough=(0.2, 0.45))
    grip = C.principled("TruckGrip", (0.05, 0.05, 0.055), rough=0.7)
    z_deck = 16.0
    parts = [P.box(name + "Deck", (90, 60, 4), (0, 0, z_deck), mat=deck_m, bevel=1.5),
             P.box(name + "Bumper", (92, 62, 1.8), (0, 0, z_deck - 1), mat=rub, bevel=0.8)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 36, sy * 22
            parts.append(P.box(f"{name}Fork{sx}{sy}", (6, 6, 3), (x, y, z_deck - 3.5), mat=steel, bevel=0.3))
            parts.append(P.box(f"{name}ForkL{sx}{sy}", (1, 5, 6), (x, y, z_deck - 7), mat=steel))
            parts.append(P.cyl(f"{name}Wheel{sx}{sy}", 5.0, 3.0, (x - 1.5, y, 5.0), rot=(math.radians(90), 0, 0), mat=rub, verts=24, bevel=0.6))
            parts.append(P.cyl(f"{name}Hub{sx}{sy}", 2.0, 3.4, (x - 1.5, y, 5.0), rot=(math.radians(90), 0, 0), mat=steel, verts=16))
    # ハンドル(後ろ端・U字パイプ)
    hx = -43.0
    pts = []
    for sy in (-1, 1):
        parts.append(P.cyl(f"{name}Post{sy}", 1.3, 70, (hx, sy * 24, z_deck + 2 + 35), mat=steel, verts=16))
        parts.append(P.box(f"{name}Hinge{sy}", (5, 5, 5), (hx, sy * 24, z_deck + 3), mat=steel, bevel=0.5))
    parts.append(P.cyl(name + "Top", 1.3, 48, (hx, 0, z_deck + 72), rot=(math.radians(90), 0, 0), mat=steel, verts=16))
    parts.append(P.cyl(name + "Grip", 1.9, 30, (hx, 0, z_deck + 72), rot=(math.radians(90), 0, 0), mat=grip, verts=16, bevel=0.4))
    for sy in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=3, minor_radius=1.3, location=(hx, sy * 21, z_deck + 69),
                                         rotation=(math.radians(90), 0, 0))
        b = bpy.context.object; b.name = f"{name}Bend{sy}"; b.data.materials.append(steel); bpy.ops.object.shade_smooth()
        parts.append(b)
    for p in parts:
        p.parent = root
    return root, z_deck + 2


def bundle(name, vroots, center, n, rnd, axis_deg=0.0):
    """n本の閉じた傘を紐で2か所束ねた束(横倒し、+X 方向に手元)。center は束の中心(石突きと手元の中間)。"""
    root = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(root)
    root.location = center; root.rotation_euler = (0, 0, math.radians(axis_deg))
    # 断面の並び: 中心1+周り(六方)
    offs = [(0, 0)] + [(5.2 * math.cos(a), 5.2 * math.sin(a)) for a in (math.tau * k / 6 for k in range(6))]
    offs += [(10.0 * math.cos(a), 10.0 * math.sin(a)) for a in (math.tau * (k + 0.5) / 6 for k in range(6))]
    for i in range(n):
        oy, oz = offs[i]
        v = rnd.randrange(len(vroots))
        flip = rnd.random() < 0.25          # たまに逆向き
        L = 86.0
        x = -L / 2 + rnd.uniform(-4, 4) if not flip else L / 2 + rnd.uniform(-4, 4)
        rot = (rnd.uniform(0, 360), 90 if not flip else -90, 0)
        u = K.clone(vroots[v], f"{name}_{i}", (x, oy, oz), (0, 0, 0))
        u.rotation_mode = "ZYX"             # 自分の軸回りの回転(Z)を先に、次に横倒し(Y)
        u.rotation_euler = (0, math.radians(rot[1]), math.radians(rot[0]))
        u.parent = root
    r_out = 6.0 if n <= 7 else 11.0
    for k, tx in enumerate((-14, 18)):
        t = K.tie(f"{name}Tie{k}", (0, 0, 0), r_out * 0.92, rot=(0, 90, 0), thick=0.28)
        t.location = (tx, 0, 0); t.scale = (1, 1.05, 0.95)
        t.parent = root
        # 結び目
        kn = P.cyl(f"{name}Knot{k}", 0.7, 1.4, (tx, 0, r_out * 0.92 + 0.4), mat=K.string_mat(), verts=8)
        kn.parent = root
    return root


def build(sc):
    P.world_studio((0.25, 0.25, 0.25), (0.8, 0.82, 0.85), (1.3, 1.33, 1.38), 1.0)
    rnd = random.Random(5)

    # ---- 裏の通路(コンクリート床・塗装壁・配管)
    floor = F.mat_concrete("CorFloor", (0.34, 0.34, 0.33), rough=0.45, scale=0.04)
    P.plane("Floor", (1200, CW), (DOOR_X - 600, 0, 0), mat=floor)
    P.box("FloorLine", (1100, 6, 0.3), (DOOR_X - 600, -CW / 2 + 22, 0.15), mat=C.principled("YLine", (0.8, 0.6, 0.05), rough=0.5))
    wall = C.principled("CorWall", (0.66, 0.67, 0.64), rough=0.75, noise_rough=(0.6, 0.85), bump=0.01, bump_scale=3)
    wains = C.principled("CorWains", (0.32, 0.36, 0.37), rough=0.45, noise_rough=(0.3, 0.6), bump=0.03, bump_scale=30, coat=0.2)
    for s in (-1, 1):
        P.box(f"Wall{s}", (1200, 10, CEIL), (DOOR_X - 600, s * (CW / 2 + 5), CEIL / 2), mat=wall)
        P.box(f"Wains{s}", (1200, 1, 90), (DOOR_X - 600, s * (CW / 2 - 0.5), 45), mat=wains)
        P.box(f"Skirt{s}", (1200, 2, 8), (DOOR_X - 600, s * (CW / 2 - 1), 4), mat=C.principled("Skirt", (0.08, 0.08, 0.08), rough=0.6))
    P.box("Ceiling", (1200, CW + 20, 10), (DOOR_X - 600, 0, CEIL + 5), mat=C.principled("CorCeil", (0.55, 0.55, 0.53), rough=0.8))
    pipe = F.mat_painted("Pipe", (0.6, 0.6, 0.58), rough=0.5, wear=0.1)
    for k, (y, z, r) in enumerate(((CW / 2 - 12, CEIL - 20, 5), (CW / 2 - 26, CEIL - 16, 3), (-CW / 2 + 10, CEIL - 25, 7))):
        P.cyl(f"Pipe{k}", r, 1200, (DOOR_X - 600, y, z), rot=(0, math.radians(90), 0), mat=pipe, verts=20)
    # 天井灯
    for i, x in enumerate(range(int(DOOR_X) - 520, int(DOOR_X) - 40, 180)):
        K.fluorescent(f"CFl{i}", (x, 0, CEIL - 5), length=110, axis="X", strength=10, temp=4600)
        L = C.area_light((x, 0, CEIL - 10), (0, 0, 0), 1, 2.2e4, (1.0, 0.95, 0.88), f"CorL{i}").data
        L.shape = "RECTANGLE"; L.size = 110; L.size_y = 15
    # 側面の扉(無地)と消火設備風の赤い箱(文字なし)
    P.box("SideDoor", (90, 3, 200), (DOOR_X - 330, CW / 2 - 1.5, 100), mat=C.principled("SideDoorM", (0.5, 0.52, 0.5), rough=0.45, coat=0.2))
    P.box("RedBox", (45, 14, 60), (DOOR_X - 170, -CW / 2 + 7, 120), mat=C.principled("RedBoxM", (0.35, 0.03, 0.025), rough=0.35, coat=0.4), bevel=1.0)
    # 壁際の台車・コンテナ
    P.box("Crate", (60, 40, 30), (DOOR_X - 120, CW / 2 - 24, 15), mat=C.principled("CrateM", (0.15, 0.3, 0.55), rough=0.5), bevel=1.0)
    P.box("Crate2", (60, 40, 30), (DOOR_X - 120, CW / 2 - 24, 46), mat=C.principled("CrateM2", (0.15, 0.3, 0.55), rough=0.5), bevel=1.0)

    # ---- 突き当たりの両開き鉄扉(外へ開いている)と外
    endw = C.principled("EndWall", (0.6, 0.61, 0.59), rough=0.75, noise_rough=(0.6, 0.85), bump=0.01, bump_scale=3)
    door_w = 140
    P.box("EndWallL", (10, (CW - door_w) / 2, CEIL), (DOOR_X + 5, -(door_w + (CW - door_w) / 2) / 2 - 0.0 - (CW - door_w) / 4 + (CW - door_w) / 4, CEIL / 2), mat=endw)
    P.box("EndWallR", (10, (CW - door_w) / 2, CEIL), (DOOR_X + 5, (door_w / 2 + CW / 2) / 2, CEIL / 2), mat=endw)
    bpy.data.objects["EndWallL"].location.y = -(door_w / 2 + CW / 2) / 2
    P.box("EndWallTop", (10, door_w, CEIL - 210), (DOOR_X + 5, 0, 210 + (CEIL - 210) / 2), mat=endw)
    leaf = C.principled("Leaf", (0.38, 0.42, 0.44), rough=0.4, noise_rough=(0.3, 0.55), coat=0.2)
    for s in (-1, 1):
        lf = P.box(f"Leaf{s}", (door_w / 2, 4, 205), (door_w / 4, 0, 102.5), mat=leaf, bevel=0.4)
        piv = bpy.data.objects.new(f"LeafPiv{s}", None); bpy.context.collection.objects.link(piv)
        piv.location = (DOOR_X + 10, s * door_w / 2, 0)
        lf.location = (door_w / 4, 0, 102.5) if False else (0, -s * door_w / 4, 102.5)
        lf.parent = piv
        piv.rotation_euler = (0, 0, math.radians(s * 100))   # 外側へ開く
    P.box("Threshold", (14, door_w, 1), (DOOR_X + 5, 0, 0.5), mat=C.principled("ThrSteel", (0.6, 0.6, 0.62), metallic=1, rough=0.35))
    # 外: 濡れたアスファルトの搬出口、向かいの塀、植え込み(曇天)
    P.plane("OutGround", (1500, 1500), (DOOR_X + 760, 0, -0.5), mat=C.principled("OutAsph", (0.1, 0.1, 0.1), rough=0.3, noise_rough=(0.05, 0.6), bump=0.1, bump_scale=200))
    P.box("OutFence", (20, 1500, 220), (DOOR_X + 700, 0, 110), mat=F.mat_concrete("FenceC", (0.55, 0.55, 0.53), rough=0.8))
    bol = C.principled("Bollard", (0.75, 0.6, 0.08), rough=0.4, coat=0.3)
    for i, y in enumerate((-160, 0, 160)):
        P.cyl(f"Bollard{i}", 6, 80, (DOOR_X + 330, y, 40), mat=bol, verts=20, bevel=1.0)
    P.box("OutCurb", (30, 1500, 12), (DOOR_X + 520, 0, 6), mat=F.mat_concrete("CurbC", (0.5, 0.5, 0.48)))
    sun = C.area_light((DOOR_X + 400, 0, 500), (0, 0, 0), 800, 6e5, (0.88, 0.93, 1.0), "Overcast")
    C.light_look_at(sun, (DOOR_X, 0, 0))
    spill = C.area_light((DOOR_X + 30, 0, 110), (0, -90, 0), 1, 6e4, (0.9, 0.94, 1.0), "DoorSpill").data
    spill.shape = "RECTANGLE"; spill.size = 140; spill.size_y = 200

    # ---- 台車と傘の束
    truck, deck_top = hand_truck("Truck")
    vroots = []
    for i in range(8):
        kind = "vinyl" if i < 6 else "cloth"
        r = K.make_umbrella(f"BV{i}", (0, 0, -3000 - i * 100), state="closed", kind=kind,
                            color=None if kind == "vinyl" else ("navy", "black")[i - 6],
                            handle="white" if kind == "vinyl" else "black", seed=300 + i, loose=0.1 + 0.05 * (i % 3))
        K.hide_tree(r); vroots.append(r)
    layout = [((2, -19, deck_top + 7.5), 7), ((0, 0, deck_top + 7.5), 7), ((-2, 19, deck_top + 7.5), 7),
              ((1, -9.5, deck_top + 20.5), 7), ((-1, 9.5, deck_top + 20.5), 7), ((3, 0, deck_top + 33), 7)]
    for k, (c, n) in enumerate(layout):
        b = bundle(f"Bundle{k}", vroots, c, n, rnd, axis_deg=rnd.uniform(-4, 4))
        b.parent = truck
    # 移動(ゆっくり出発→一定速度)。少しだけ横ぶれ
    x0 = DOOR_X - 520
    truck.location = (x0, 8, 0)
    P.key_seq(truck, "location", [(1, (x0, 8, 0)), (30, (x0 + TRAVEL * 0.18, 6, 0)), (FRAMES, (x0 + TRAVEL, 0, 0))])
    P.key_seq(truck, "rotation_euler", [(1, (0, 0, math.radians(1.5))), (FRAMES, (0, 0, math.radians(-0.5)))])

    P.reflection_probe((DOOR_X - 300, 0, 120), radius=500)
    # POV カメラ: 押す人の目線(台車の後ろ)。台車と一緒に進み、歩行の揺れを少し
    cam, tgt = C.camera((0, 0, 0), (0, 0, 0), lens=24, fstop=0.04)
    cam.parent = None
    pts = []
    for f in range(1, FRAMES + 1, 6):
        bpy.context.scene.frame_set(f)
        tx = truck.location.x
        bob = 1.2 * math.sin(f / 24 * math.tau * 1.7)
        pts.append((f, tx - 98, truck.location.y + 10, 140 + bob))
    for f, x, y, z in pts:
        C.key(cam, "location", f, (x, y, z))
        C.key(tgt, "location", f, (x + 270, y - 6, 18))
    F.set_interp(cam, "BEZIER")
    focus = bpy.data.objects.new("Focus", None); bpy.context.collection.objects.link(focus)
    focus.parent = truck; focus.location = (5, 0, deck_top + 20)
    cam.data.dof.focus_object = focus
    sc.view_settings.exposure = -0.2
    sc.view_settings.look = "AgX - Medium High Contrast"


if __name__ == "__main__":
    K.set_episode("ep02")
    C.run_shot("k05_cart_out", build, FRAMES)
