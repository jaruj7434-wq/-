"""H09a / カット3-5: 眠る小銭①「貯金箱」。陶器の豚の貯金箱と、まわりに積まれた/散らばった小銭。
棚の上、夕方の窓明かり。カメラはゆっくり横移動しながら寄る(静物)。5秒。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from mathutils import Vector
import common as C
import props as P

FRAMES = 120


def sphere(name, loc, scale, mat, seg=48):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = scale
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    return o


def piggy(loc=(0, 0, 0)):
    """陶器の豚(長さ約16cm)。頭は -X 向き。"""
    glaze = C.principled("Glaze", (0.85, 0.42, 0.45), rough=0.12, coat=0.6)
    dark = C.principled("SlotDark", (0.01, 0.01, 0.01), rough=0.8)
    x, y, z = loc
    body = sphere("PigBody", (x, y, z + 7.2), (8.0, 6.2, 6.0), glaze)
    snout = P.cyl("Snout", 2.1, 2.4, (x - 8.4, y, z + 6.8), (0, math.radians(90), 0), glaze, bevel=0.5)
    for s in (-1, 1):
        sphere(f"Nostril{s}", (x - 9.62, y + s * 0.7, z + 6.8), (0.12, 0.38, 0.55), dark, seg=16)
        sphere(f"Eye{s}", (x - 6.3, y + s * 2.6, z + 9.6), (0.35, 0.35, 0.45), C.principled("EyeM", (0.02, 0.02, 0.02), rough=0.1), seg=16)
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=1.7, depth=2.4,
                                        location=(x - 4.4, y + s * 3.2, z + 12.4),
                                        rotation=(math.radians(-s * 25), math.radians(-25), 0))
        ear = bpy.context.object; ear.name = f"Ear{s}"; ear.scale = (1, 0.45, 1)
        P.add_mod(ear, "BEVEL", width=0.3, segments=3); bpy.ops.object.shade_smooth()
        ear.data.materials.append(glaze)
        for fx in (-1, 1):
            P.cyl(f"Leg{s}{fx}", 1.4, 2.4, (x + fx * 4.2, y + s * 3.0, z + 1.2), mat=glaze, bevel=0.4)
    # しっぽ(ねじれたトーラス)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.7, minor_radius=0.22, location=(x + 8.1, y, z + 8.2),
                                     rotation=(0, math.radians(90), 0))
    t = bpy.context.object; t.name = "Tail"; t.data.materials.append(glaze); bpy.ops.object.shade_smooth()
    # 背中の投入口: 少し盛り上がった縁 + 黒い穴
    P.box("SlotRim", (4.2, 0.9, 0.5), (x + 0.5, y, z + 13.05), mat=glaze, bevel=0.2)
    P.box("Slot", (3.4, 0.32, 0.3), (x + 0.5, y, z + 13.2), mat=dark)
    return body


def build(sc):
    C.world((0.05, 0.045, 0.04))
    rnd = random.Random(4)
    shelf = P.box("Shelf", (120, 40, 2.5), (0, 8, -1.25), mat=P.mat_wood("Wood", (0.5, 0.33, 0.18), (0.28, 0.16, 0.08), 0.6))
    C.rigid(shelf, False, "BOX", friction=0.7)
    P.box("Wall", (200, 2, 120), (0, 30, 40), mat=C.principled("Plaster", (0.75, 0.72, 0.66), rough=0.9, bump=0.05, bump_scale=0.3))

    piggy((0, 6, 0))
    # 本(背景・ボケ)
    for i, (c, w) in enumerate([((0.15, 0.25, 0.45), 3), ((0.55, 0.15, 0.12), 2.5), ((0.85, 0.8, 0.7), 4), ((0.2, 0.35, 0.25), 3)]):
        P.box(f"Book{i}", (w, 17, 24 - i * 1.5), (26 + i * 3.6, 16, (24 - i * 1.5) / 2),
              mat=C.principled(f"BookM{i}", c, rough=0.6), bevel=0.2)
    # 観葉植物の鉢(ボケ)
    P.cyl("Pot", 5, 10, (-30, 16, 5), mat=C.principled("Terracotta", (0.55, 0.25, 0.14), rough=0.8), bevel=0.5)
    sphere("Plant", (-30, 16, 15), (7, 7, 8), C.principled("Leaves", (0.08, 0.2, 0.06), rough=0.6, bump=0.8, bump_scale=6))

    # 豚の前の小銭: 積んだ山(タワー) + 自然にこぼれた硬貨(物理で落ち着かせて固定)
    for j, (cx, cy, n) in enumerate([(-10.5, -4.5, 9), (-7.5, -6.5, 5)]):
        for i in range(n):
            c = P.make_any_coin("1", f"Stack{j}_{i}", (cx + rnd.uniform(-0.08, 0.08), cy + rnd.uniform(-0.08, 0.08), 0.075 + i * 0.152),
                                (0, 0, rnd.uniform(0, 6.28)))
            C.rigid(c, False, "CYLINDER", friction=0.6)
    kinds = ["1"] * 14 + ["10", "10", "5", "100", "50"]
    rnd.shuffle(kinds)
    P.drop_pile(kinds, (-2, -6, 0), 5.0, 1.0, seed=5)
    P.settle(sc, 50)

    # 夕方の窓明かり(暖色)+ 室内の補助光 + 反射用カード
    C.area_light((-60, -40, 50), (60, 0, -55), 40, 120000, (1.0, 0.78, 0.55), "Window")
    C.area_light((40, -50, 30), (70, 0, 40), 30, 20000, (0.6, 0.7, 1.0), "Fill")
    P.light_card("Card", (40, 20), (-10, -40, 40), (-5, -3, 0), strength=3.0, color=(1.0, 0.95, 0.9))

    cam, tgt = C.camera((-14, -55, 24), (-3, 0, 5), lens=55, fstop=0.04)  # 実効 F4
    P.key_seq(cam, "location", [(1, (-26, -56, 25)), (FRAMES, (-8, -46, 20))])
    P.key_seq(tgt, "location", [(1, (-3, 1, 6)), (FRAMES, (-3, -2, 4))])


if __name__ == "__main__":
    C.run_shot("h09_piggy", build, FRAMES)
