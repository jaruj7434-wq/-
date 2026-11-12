"""H01 / カット1-1(6-1 流用): 財布(箱型小銭入れ)に硬貨がジャラッと落ちるマクロ。5秒。

- 0〜18f: 開いた小銭入れの中に数枚の硬貨。カメラはゆっくり寄る。
- 18〜44f: 上から硬貨(ほぼ1円玉)が次々に落ち、跳ねて重なる(物理・0.5倍スロー)。
- 60f〜: 落ち着いた小銭の山。最後に1円玉1枚が遅れて落ちる(~78f)。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P

FRAMES = 120

# 小銭入れ内寸 (cm)
W, D, H = 9.0, 6.5, 2.6
WALL = 0.28


def build(sc):
    C.world((0.05, 0.042, 0.035))
    P.physics(sc, FRAMES, time_scale=0.5, substeps=40)

    # 木の机
    desk = P.plane("Desk", 200, (0, 0, 0), mat=P.mat_wood("Wood", (0.36, 0.22, 0.12), (0.18, 0.10, 0.05), 0.6))
    C.rigid(desk, False, "BOX", friction=0.6)

    leather = P.mat_leather("Leather", (0.035, 0.010, 0.005), grain=4.0, rough=0.42)
    inner = P.mat_leather("Suede", (0.05, 0.03, 0.022), grain=9.0, rough=0.85)

    # 箱型小銭入れ本体(外側) + 内張り
    body = P.open_box("Purse", (W + 2 * WALL, D + 2 * WALL, H), (0, 0, H / 2), wall=WALL, mat=leather, bevel=0.12)
    body.data.materials.append(inner)
    body.modifiers["solidify"].material_offset = 1
    P.passive_mesh(body, friction=0.7, bounce=0.05, margin=0.02)
    # 床(内張り)
    floor = P.box("PurseFloor", (W, D, 0.25), (0, 0, 0.125 + WALL * 0.2), mat=inner, bevel=0.05)
    C.rigid(floor, False, "BOX", friction=0.7, bounce=0.05)

    # 開いたフタ(奥側の縁でヒンジ、外側に倒れている)
    flap = P.box("Flap", (W + 2 * WALL, D + 1.8, 0.3), (0, (D + 1.8) / 2, 0), mat=leather, bevel=0.14)
    bpy.ops.object.empty_add(location=(0, D / 2 + WALL, H))
    hinge = bpy.context.object; hinge.name = "Hinge"
    flap.parent = hinge
    hinge.rotation_euler = (math.radians(62), 0, 0)
    # フタ先端のスナップボタン
    P.cyl("Snap", 0.55, 0.15, (0, D + 1.0, 0.2), mat=C.principled("Nickel", (0.75, 0.74, 0.72), metallic=1, rough=0.22)).parent = hinge
    # 縁のステッチ(小さな糸目を配列)
    thread = C.principled("Thread", (0.75, 0.62, 0.42), rough=0.7)
    for side, (y, n) in {"F": (-(D / 2 + WALL * 0.55), 30), "B": (D / 2 + WALL * 0.55, 30)}.items():
        st = P.box(f"Stitch{side}", (0.18, 0.06, 0.04), (-W / 2 + 0.1, y, H - 0.35), mat=thread)
        P.add_mod(st, "ARRAY", count=n, relative_offset_displace=(0, 0, 0), use_relative_offset=False,
                  use_constant_offset=True, constant_offset_displace=(W / (n - 1) - 0.0, 0, 0))
        st.rotation_euler = (math.radians(90), 0, 0)

    # 最初から入っている硬貨(すぐ落ち着く)
    rnd = random.Random(7)
    pre = []
    for i, k in enumerate(["10", "1", "100", "1", "5", "1"]):
        loc = (rnd.uniform(-3, 3), rnd.uniform(-2, 1.8), 0.5 + i * 0.25)
        c = P.make_any_coin(k, f"Pre{i}", loc, (rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), rnd.uniform(0, 6)))
        s = P.COINS[k]; C.rigid(c, True, "CYLINDER", mass=s["r"] ** 2 * s["t"], friction=0.5, bounce=0.1)
        pre.append(c)

    # 落ちてくる硬貨: カメラ上方で保持 → 順に解放
    kinds = ["1"] * 20 + ["10", "5", "1", "100", "1", "1"]
    rnd.shuffle(kinds)
    for i, k in enumerate(kinds):
        slot = i % 8
        a = slot * math.pi / 4 + rnd.uniform(-0.1, 0.1)
        loc = (2.8 * math.cos(a) + 0.3, 2.0 * math.sin(a) - 0.4, (22.0 if slot % 2 == 0 else 25.0) + rnd.uniform(0, 0.4))
        rot = (rnd.uniform(-1.2, 1.2), rnd.uniform(-1.2, 1.2), rnd.uniform(0, 6.28))
        c = P.make_any_coin(k, f"Drop{i}", loc, rot)
        s = P.COINS[k]
        C.rigid(c, True, "CYLINDER", mass=s["r"] ** 2 * s["t"], friction=0.45, bounce=0.25)
        P.hold_then_release(c, 16 + i, park=(200 + i * 4, 200, 0))
    late = P.make_any_coin("1", "Late", (0.4, -0.6, 22.0), (0.9, 0.3, 0))
    C.rigid(late, True, "CYLINDER", mass=0.15, friction=0.45, bounce=0.3)
    P.hold_then_release(late, 70, park=(300, 300, 0))

    # 背景: ボケる鍵と硬貨
    steel = C.principled("Steel", (0.7, 0.7, 0.72), metallic=1, rough=0.25)
    P.box("Key", (6, 1.2, 0.2), (-14, 18, 0.1), (0, 0, 0.4), mat=steel, bevel=0.1)
    P.cyl("KeyRing", 1.6, 0.25, (-18, 16, 0.15), mat=steel)
    P.scatter_mixed(6, center=(12, 16, 0), radius=4, seed=11, prefix="Bg")

    # 照明: 暖色キー(窓)、クールなリム、反射用ライトカード
    C.area_light((-25, -20, 35), (45, 0, -50), 25, 60000, (1.0, 0.86, 0.7), "Key")
    C.area_light((25, 30, 18), (65, 0, 140), 15, 20000, (0.65, 0.78, 1.0), "Rim")
    C.area_light((0, -30, 10), (80, 0, 0), 20, 8000, (1.0, 0.95, 0.9), "Fill")
    P.light_card("Card", (30, 15), (0, -8, 40), (0, 0, 0), strength=3.0, color=(1.0, 0.95, 0.88))
    P.light_card("CardBack", (40, 20), (5, -45, 30), (0, 0, 2), strength=2.0, color=(1.0, 0.93, 0.85))
    P.light_card("CardSide", (20, 20), (-30, 0, 15), (0, 0, 2), strength=1.5, color=(0.8, 0.88, 1.0))

    cam, tgt = C.camera((0, -24, 20), (0, -0.3, 1.0), lens=70, fstop=1.4)
    P.key_seq(cam, "location", [(1, (2.0, -26.0, 20.5)), (FRAMES, (-0.5, -21.0, 17.0))])
    sc.view_settings.exposure = 0.0


if __name__ == "__main__":
    C.run_shot("h01_wallet", build, FRAMES)
