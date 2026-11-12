"""H09b / カット3-5: 眠る小銭②「机の引き出し」。開けた引き出しの中、文房具やがらくたに
混じって小銭が散らばっている。デスクライトの暖色光。カメラはゆっくり横へスライド(静物)。5秒。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P

FRAMES = 120
DW, DD, DH = 36.0, 28.0, 8.0   # 引き出し外寸


def pencil(name, loc, rot_z, color, length=16):
    body = P.cyl(name, 0.38, length, loc, (0, math.radians(90), rot_z), C.principled(name + "M", color, rough=0.35, coat=0.4), verts=6)
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.38, depth=1.6, location=(0, 0, length / 2 + 0.8))
    tip = bpy.context.object; tip.name = name + "Tip"
    tip.data.materials.append(C.principled("Pine", (0.75, 0.55, 0.35), rough=0.7))
    tip.parent = body
    return body


def build(sc):
    P.world_studio((0.02, 0.018, 0.016), (0.1, 0.09, 0.08), (0.7, 0.65, 0.58), 1.0)
    rnd = random.Random(21)
    wood = P.mat_wood("Oak", (0.55, 0.38, 0.22), (0.35, 0.22, 0.12), 0.5)
    inner = P.mat_wood("Ply", (0.42, 0.32, 0.22), (0.30, 0.22, 0.14), 0.8, rough=0.6)

    # 引き出し(箱)+ 前板 + 机の天板・側板
    drawer = P.open_box("Drawer", (DW, DD, DH), (0, 0, DH / 2), wall=1.2, mat=inner, bevel=0.1)
    P.passive_mesh(drawer, friction=0.6)
    dfloor = P.box("DrawerFloor", (DW - 2.4, DD - 2.4, 0.4), (0, 0, 0.2), mat=inner)
    C.rigid(dfloor, False, "BOX", friction=0.6)
    P.box("Front", (DW + 4, 1.8, DH + 4), (0, -DD / 2 - 0.9, DH / 2 - 1), mat=wood, bevel=0.2)
    P.cyl("Knob", 1.2, 1.5, (0, -DD / 2 - 2.4, DH / 2 - 1), (math.radians(90), 0, 0),
          C.principled("Brass", (0.8, 0.6, 0.3), metallic=1, rough=0.25), bevel=0.3)
    P.box("DeskTop", (120, 70, 3), (0, DD / 2 + 32, DH + 3.5), mat=wood, bevel=0.3)
    P.box("Carcass", (DW + 6, 60, DH + 2), (0, DD / 2 + 32, DH / 2 + 0.5), mat=wood)
    P.plane("Floor", 400, (0, 0, -60), mat=C.principled("Floor", (0.25, 0.2, 0.16), rough=0.6))

    # がらくた
    pencil("PencilA", (-6, 5, 1.0), math.radians(12), (0.9, 0.7, 0.05))
    pencil("PencilB", (4, 7, 1.0), math.radians(-30), (0.1, 0.35, 0.18), 13)
    P.box("Eraser", (4.5, 2.2, 1.2), (10, -2, 1.0), (0, 0, math.radians(20)), C.principled("Eraser", (0.92, 0.92, 0.9), rough=0.8), bevel=0.15)
    P.box("EraserSleeve", (3.0, 2.3, 1.3), (9.3, -2.25, 1.0), (0, 0, math.radians(20)), C.principled("Sleeve", (0.1, 0.25, 0.65), rough=0.5))
    P.box("Sticky", (7.5, 7.5, 1.2), (-10, -6, 1.0), (0, 0, math.radians(-15)), C.principled("StickyM", (0.98, 0.85, 0.25), rough=0.8), bevel=0.05)
    chrome = C.principled("Chrome", (0.85, 0.85, 0.86), metallic=1, rough=0.15)
    for i in range(6):  # ゼムクリップ(細長いトーラス)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.9, minor_radius=0.07, location=(rnd.uniform(-13, 13), rnd.uniform(-10, 10), 0.5),
                                         rotation=(0, 0, rnd.uniform(0, 6.28)))
        cp = bpy.context.object; cp.name = f"Clip{i}"; cp.scale = (1.8, 0.6, 1); cp.data.materials.append(chrome)
    for i in range(3):  # 輪ゴム
        bpy.ops.mesh.primitive_torus_add(major_radius=1.8, minor_radius=0.12, location=(rnd.uniform(-12, 12), rnd.uniform(-9, 8), 0.55),
                                         rotation=(rnd.uniform(-0.1, 0.1), 0, rnd.uniform(0, 6.28)))
        rb = bpy.context.object; rb.name = f"Band{i}"; rb.scale = (1, rnd.uniform(0.5, 0.9), 1)
        rb.data.materials.append(C.principled("Rubber", (0.6, 0.35, 0.15), rough=0.6))
    for i in range(2):  # 乾電池
        bat = P.cyl(f"Battery{i}", 0.7, 5.0, (13 + i * 1.6, 8, 0.9), (math.radians(90), 0, math.radians(80)),
                    C.principled("BatM", (0.05, 0.05, 0.06), rough=0.3, coat=0.5))
    key = P.box("Key", (5.5, 1.3, 0.2), (2, -10, 0.6), (0, 0, math.radians(-35)), C.principled("KeyBrass", (0.75, 0.62, 0.35), metallic=1, rough=0.3), bevel=0.2)
    # 丸めたレシート(しわくちゃの紙玉)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=2.2, location=(-13, 7, 2.2))
    wad = bpy.context.object; wad.name = "PaperWad"
    P.add_mod(wad, "DISPLACE", strength=0.9, texture=bpy.data.textures.new("Crumple", "VORONOI"))
    P.add_mod(wad, "SUBSURF", levels=1, render_levels=1); bpy.ops.object.shade_smooth()
    wad.data.materials.append(C.principled("Paper", (0.9, 0.9, 0.86), rough=0.8))

    # 硬貨: 物理で自然に散らばらせて固定(がらくたはコライダー)
    for o in list(bpy.data.objects):
        if o.name.startswith(("Pencil", "Eraser", "Sticky", "Battery", "Key")) and "Tip" not in o.name:
            C.rigid(o, False, "CONVEX_HULL", friction=0.6)
    kinds = ["1"] * 16 + ["10", "10", "10", "5", "100", "50", "1", "1", "10", "1"]
    rnd.shuffle(kinds)
    P.drop_pile(kinds[:16], (-8, -4, 0), 4.5, 3.0, seed=22, friction=0.6, prefix="PA")   # 手前の隅に溜まった小銭
    P.drop_pile(kinds[16:], (2, 0, 0), 11, 3.0, seed=23, friction=0.6, prefix="PB")
    P.settle(sc, 50)

    # デスクライト(暖色・左上) + 部屋の環境光 + 反射カード
    C.area_light((-30, 10, 55), (0, -25, 0), 12, 60000, (1.0, 0.8, 0.55), "Lamp")
    C.light_look_at(bpy.data.objects["Lamp"], (0, 0, 0))
    C.area_light((40, -60, 50), (50, 0, 35), 50, 50000, (0.75, 0.82, 1.0), "Room")
    P.light_card("Card", (60, 30), (0, -50, 70), (0, 0, 0), strength=1.5, color=(1.0, 0.95, 0.88))
    P.light_card("CardBack", (70, 40), (0, 45, 40), (0, -5, 0), strength=2.5, color=(1.0, 0.93, 0.85), visible_camera=True)

    cam, tgt = C.camera((-10, -34, 38), (-3, -3, 0), lens=40, fstop=0.04)  # 実効 F4
    P.key_seq(cam, "location", [(1, (-16, -34, 42)), (FRAMES, (2, -27, 40))])
    P.key_seq(tgt, "location", [(1, (-6, -3, 0)), (FRAMES, (0, -4, 0))])
    P.reflection_probe((0, -2, 8), 80)
    sc.view_settings.exposure = -0.4


if __name__ == "__main__":
    C.run_shot("h09_drawer", build, FRAMES)
