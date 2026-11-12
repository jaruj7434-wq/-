"""H12 / カット4-7(コミカル): 客がガラス瓶いっぱいの1円玉をレジのカルトンにぶちまける。
カルトンから溢れて山盛りに。カウンターの向こうに店員のエプロン(胸元から下だけ・顔なし)。5秒。

- 1〜14f: 1円玉がぎっしり詰まった瓶(画面上から手持ちの想定)。
- 14〜56f: 瓶が傾き、1円玉がジャラジャラと流れ出てカルトンに山を作る(約150枚・物理)。
- 56〜120f: 溢れた山が落ち着く。店員の体がわずかに引く(困惑)。カメラはゆっくり寄る。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import bmesh
import common as C
import props as P
from h08_register import mat_tray

FRAMES = 120
JAR_R, JAR_H = 5.2, 15.0
JAR_POS = (-12.0, -1.0, 9.0)      # 瓶の底の中心(初期)


def jar():
    """口の開いたガラス瓶(衝突用メッシュ兼用)。底中心が原点。"""
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=JAR_R, depth=JAR_H, location=(0, 0, JAR_H / 2))
    o = bpy.context.object; o.name = "Jar"
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.9], context="FACES")
    bm.to_mesh(o.data); bm.free()
    P.add_mod(o, "SOLIDIFY", thickness=0.35, offset=1)
    P.add_mod(o, "BEVEL", width=0.12, segments=2, limit_method="ANGLE")
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    o.data.materials.append(C.principled("JarGlass", (0.85, 0.95, 0.92), rough=0.04, alpha=0.18, coat=1.0))
    # 口のねじ山(リング)
    bpy.ops.mesh.primitive_torus_add(major_radius=JAR_R + 0.1, minor_radius=0.25, location=(0, 0, JAR_H - 1.0))
    t = bpy.context.object; t.name = "JarThread"; t.data.materials.append(bpy.data.materials["JarGlass"])
    t.parent = o
    return o


def build(sc):
    P.world_studio((0.03, 0.03, 0.032), (0.12, 0.12, 0.12), (0.55, 0.57, 0.6), 1.0)
    P.physics(sc, FRAMES, time_scale=0.8, substeps=30, iterations=20)
    rnd = random.Random(12)

    top = P.box("Counter", (180, 60, 3), (0, 8, -1.5),
                mat=C.principled("Laminate", (0.55, 0.42, 0.3), rough=0.35, noise_rough=(0.25, 0.45), bump=0.02, bump_scale=200))
    C.rigid(top, False, "BOX", friction=0.5)
    tray = P.open_box("Tray", (22, 15, 1.4), (0, 0, 0.7), wall=0.35, mat=mat_tray(), bevel=0.3)
    P.passive_mesh(tray, friction=0.45, bounce=0.1, margin=0.02)
    tf = P.box("TrayFloor", (21.2, 14.2, 0.2), (0, 0, 0.1), mat=bpy.data.materials["Tray"])
    C.rigid(tf, False, "BOX", friction=0.45, bounce=0.1)

    # 瓶(キネマティックに傾ける)+ 中の1円玉
    j = jar()
    j.location = JAR_POS
    C.rigid(j, False, "MESH", friction=0.08, bounce=0.05, margin=0.03)
    j.rigid_body.mesh_source = "FINAL"; j.rigid_body.kinematic = True
    P.key_seq(j, "location", [(1, JAR_POS), (14, (JAR_POS[0] + 0.5, JAR_POS[1], JAR_POS[2] + 1)),
                              (40, (JAR_POS[0] - 1, JAR_POS[1], JAR_POS[2] + 5)), (70, (JAR_POS[0] - 2, JAR_POS[1], JAR_POS[2] + 7)),
                              (FRAMES, (JAR_POS[0] - 3, JAR_POS[1], JAR_POS[2] + 8))])
    P.key_seq(j, "rotation_euler", [(1, (0, 0, 0)), (14, (0, math.radians(-8), 0)), (40, (0, math.radians(115), 0)),
                                    (56, (0, math.radians(140), 0)), (70, (0, math.radians(150), 0)), (FRAMES, (0, math.radians(150), 0))])
    mat1 = P.coin_mat("1")
    ring = [(0, 0)] + [(2.6 * math.cos(a * math.pi / 3), 2.6 * math.sin(a * math.pi / 3)) for a in range(6)]
    n = 0; layer = 0
    while n < 150:
        off = layer * 0.6
        for (x, y) in ring:
            if n >= 150:
                break
            ca, sa = math.cos(off), math.sin(off)
            px, py = x * ca - y * sa, x * sa + y * ca
            c = C.make_coin(f"Y{n}", mat1, (JAR_POS[0] + px, JAR_POS[1] + py, JAR_POS[2] + 0.55 + layer * 0.2),
                            (rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), rnd.uniform(0, 6.28)), verts=32)
            C.rigid(c, True, "CYLINDER", mass=0.15, friction=0.7, bounce=0.1, margin=0.006)
            n += 1
        layer += 1
    # 背景: レジ・募金箱(無地)・店員のエプロン(胸から下)
    reg = P.box("Register", (34, 26, 12), (40, 30, 6), mat=C.principled("RegBody", (0.12, 0.12, 0.13), rough=0.4), bevel=1.0)
    P.box("RegScreen", (26, 2, 18), (40, 38, 21), (math.radians(-12), 0, 0),
          mat=C.principled("RegScr", (0.02, 0.02, 0.03), rough=0.15, emission=(0.35, 0.55, 0.85), emission_strength=0.8), bevel=0.5)
    shirt = C.principled("Shirt", (0.85, 0.85, 0.83), rough=0.8, bump=0.2, bump_scale=40)
    apron = C.principled("Apron", (0.03, 0.12, 0.08), rough=0.9, bump=0.3, bump_scale=60)
    torso = P.box("Torso", (44, 24, 60), (-4, 58, 30), mat=shirt, bevel=9)
    ap = P.box("ApronPanel", (38, 2, 58), (-4, 45.5, 28), mat=apron)
    P.add_mod(ap, "SUBSURF", levels=3, render_levels=3, subdivision_type="SIMPLE")
    tx = bpy.data.textures.new("Folds", "CLOUDS"); tx.noise_scale = 0.4
    P.add_mod(ap, "DISPLACE", texture=tx, strength=1.6, direction="Y")
    bpy.ops.object.shade_smooth()
    for s in (-1, 1):
        P.box(f"Strap{s}", (4, 1.6, 30), (-4 + s * 13, 46.5, 62), mat=apron)
        P.cyl(f"Arm{s}", 6.5, 50, (-4 + s * 27, 56, 34), (math.radians(8), math.radians(-s * 6), 0), mat=shirt, bevel=2)
    P.box("Pocket", (16, 1.0, 10), (-8, 44.3, 34), mat=apron, bevel=0.5)
    P.box("NameTag", (7, 0.5, 2.5), (6, 44.2, 46), mat=C.principled("Tag", (0.9, 0.9, 0.88), rough=0.4))  # 無地
    # 店員がわずかに後ずさる(困惑)
    for obn in ("Torso", "ApronPanel", "Strap-1", "Strap1", "Arm-1", "Arm1", "Pocket", "NameTag"):
        o = bpy.data.objects[obn]
        y0 = o.location.y
        P.key_seq(o, "location", [(60, (o.location.x, y0, o.location.z)), (80, (o.location.x, y0 + 6, o.location.z + 0.5)),
                                  (FRAMES, (o.location.x, y0 + 6.5, o.location.z + 0.5))])
    # 奥の棚(ボケ)
    cols = [(0.8, 0.1, 0.1), (0.95, 0.75, 0.1), (0.1, 0.35, 0.75), (0.9, 0.9, 0.9), (0.1, 0.55, 0.25), (0.9, 0.45, 0.1)]
    pm = [C.principled(f"Pk{i}", c, rough=0.4) for i, c in enumerate(cols)]
    for row in range(5):
        z = 10 + row * 30
        x = -160
        while x < 160:
            w = rnd.uniform(5, 12); h = rnd.uniform(10, 24)
            P.box(f"Pk{row}_{int(x)}", (w, 8, h), (x + w / 2, 160, z + h / 2), mat=rnd.choice(pm), bevel=0.3, segments=1)
            x += w + rnd.uniform(0.5, 2.5)
    P.box("BackWall", (400, 2, 250), (0, 175, 100), mat=C.principled("Wall", (0.8, 0.82, 0.83), rough=0.7))

    # 照明(店内の蛍光灯)
    tube = C.emissive("Tube", (0.9, 0.95, 1.0), strength=10)
    for i in range(3):
        P.box(f"Tube{i}", (200, 6, 1.5), (0, -20 + i * 70, 170), mat=tube)
        L = C.area_light((0, -20 + i * 70, 168), (0, 0, 0), 1, 120000, (0.9, 0.95, 1.0), f"Ceil{i}").data
        L.shape = "RECTANGLE"; L.size = 180; L.size_y = 12
    C.area_light((-30, -70, 70), (55, 0, -20), 50, 50000, (1.0, 0.97, 0.92), "Front")

    cam, tgt = C.camera((6, -62, 36), (-3, 2, 8), lens=35, fstop=0.028)  # 実効 F2.8
    P.key_seq(cam, "location", [(1, (8, -66, 38)), (FRAMES, (2, -44, 25))])
    P.key_seq(tgt, "location", [(1, (-4, 2, 11)), (60, (-1, 1, 4)), (FRAMES, (0, 1, 2))])


if __name__ == "__main__":
    C.run_shot("h12_counter_pile", build, FRAMES)
