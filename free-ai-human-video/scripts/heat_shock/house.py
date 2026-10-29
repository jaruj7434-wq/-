"""家のセット:浴室・脱衣所・居間・雪の夜の外観。床が z=0。浴槽の中心が原点(plan.py の寸法)。

手前(-y 側)の壁はなく、断面のように中が見える。部屋は x 方向に 居間 → 脱衣所 → 浴室 と並ぶ。
"""
import math
import random

import bpy

from kit import add_bump, assign, box, color_variation, cyl, glow, light, metal, principled, smooth, text
from plan import TUB_RIM, TUB_X, TUB_Y, WATER_Z

H = 2.3                       # 天井の高さ
BATH = (-0.95, 0.95)          # 浴室の x 範囲
DRESS = (-2.75, -1.0)         # 脱衣所の x 範囲
LIVING = (-7.0, -2.8)         # 居間の x 範囲
BACK_Y = TUB_Y + 0.12         # 奥の壁の y


def tiles(name, color, scale, mortar=(0.55, 0.56, 0.58), rot=(math.radians(90), 0, 0)):
    """タイル張りの素材(目地付き)。"""
    mat = principled(name, color, rough=0.18, coat=0.5)
    n, l = mat.node_tree.nodes, mat.node_tree.links
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = rot
    brick = n.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = scale
    brick.inputs["Mortar Size"].default_value = 0.015
    brick.inputs["Brick Width"].default_value = 0.5
    brick.inputs["Row Height"].default_value = 0.5
    brick.inputs["Color1"].default_value = (*color, 1)
    brick.inputs["Color2"].default_value = tuple(c * 0.96 for c in color) + (1,)
    brick.inputs["Mortar"].default_value = (*mortar, 1)
    l.new(tc.outputs["Object"], mp.inputs["Vector"])
    l.new(mp.outputs["Vector"], brick.inputs["Vector"])
    l.new(brick.outputs["Color"], n["Principled BSDF"].inputs["Base Color"])
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    l.new(brick.outputs["Fac"], bump.inputs["Height"])
    l.new(bump.outputs["Normal"], n["Principled BSDF"].inputs["Normal"])
    return mat


def bathroom(scene, lamp=True):
    wall = tiles("BathTile", (0.82, 0.86, 0.88), 6.0)
    floor = tiles("BathFloor", (0.6, 0.63, 0.66), 8.0, rot=(0, 0, 0))
    x0, x1 = BATH
    box("BathBack", (x1 - x0, 0.06, H), ((x0 + x1) / 2, BACK_Y + 0.03, H / 2), wall)
    box("BathRight", (0.06, 2.0, H), (x1 + 0.03, BACK_Y - 1.0, H / 2), wall)
    box("BathLeftWall", (0.06, 0.6, H), (x0 - 0.03, BACK_Y - 0.3, H / 2), wall)
    box("BathFloor", (x1 - x0, 2.0, 0.04), ((x0 + x1) / 2, BACK_Y - 1.0, -0.02), floor)
    box("BathCeil", (x1 - x0, 2.0, 0.04), ((x0 + x1) / 2, BACK_Y - 1.0, H + 0.02), principled("BathCeiling", (0.85, 0.86, 0.86), rough=0.5))
    # 浴槽(外枠からくり抜く)
    acrylic = principled("Tub", (0.9, 0.88, 0.84), rough=0.12, coat=0.8)
    tub = box("Tub", (2 * TUB_X + 0.16, 2 * TUB_Y + 0.16, TUB_RIM), (0, 0, TUB_RIM / 2), acrylic, bevel=0.03)
    cutter = box("TubCut", (2 * TUB_X, 2 * TUB_Y, TUB_RIM), (0, 0, TUB_RIM / 2 + 0.06), acrylic, bevel=0.06)
    cutter.hide_render = True
    m = tub.modifiers.new("hollow", "BOOLEAN")
    m.object, m.operation = cutter, "DIFFERENCE"
    water = principled("BathWater", (0.75, 0.9, 0.92), rough=0.03, transmission=1.0, ior=1.33)
    add_bump(water, scale=4, strength=0.15)
    box("Water", (2 * TUB_X - 0.01, 2 * TUB_Y - 0.01, WATER_Z - 0.08), (0, 0, 0.08 + (WATER_Z - 0.08) / 2), water)
    # 水栓・シャワー・手すり(クロム)
    chrome = metal("Chrome", (0.85, 0.85, 0.87), rough=0.08, brushed=False)
    cyl("FaucetBody", 0.03, 0.22, (x1 - 0.03, -0.2, 0.75), chrome, rot=(math.radians(90), 0, 0))
    cyl("Spout", 0.015, 0.16, (x1 - 0.1, -0.2, 0.72), chrome, rot=(0, math.radians(90), 0))
    cyl("ShowerBar", 0.012, 0.9, (x1 - 0.04, -0.55, 1.45), chrome)
    cyl("ShowerHead", 0.05, 0.03, (x1 - 0.08, -0.55, 1.85), chrome, rot=(0, math.radians(70), 0))
    rails = [cyl("RailBack", 0.017, 0.8, (0.0, BACK_Y - 0.05, 0.85), chrome, rot=(0, math.radians(90), 0)),
             cyl("RailSide", 0.017, 0.6, (x1 - 0.05, TUB_Y - 0.1, 0.95), chrome)]
    for x in (-0.4, 0.4):
        cyl(f"RailMount{x}", 0.025, 0.06, (x, BACK_Y - 0.02, 0.85), chrome, rot=(math.radians(90), 0, 0))
    # 風呂椅子と桶
    resin = principled("Resin", (0.85, 0.8, 0.7), rough=0.3)
    box("Stool", (0.32, 0.24, 0.04), (0.55, -0.75, 0.3), resin, bevel=0.015)
    for dx in (-0.12, 0.12):
        box(f"StoolLeg{dx}", (0.04, 0.22, 0.28), (0.55 + dx, -0.75, 0.14), resin, bevel=0.01)
    cyl("Bucket", 0.12, 0.13, (0.15, -0.75, 0.065), resin, bevel=0.01)
    if lamp:
        light(scene, "AREA", "BathLamp", (0.0, -0.3, H - 0.05), 45, (1.0, 0.9, 0.75), size=0.5)
    return rails


def dressing(scene, heater_on=False):
    """脱衣所:洗面台・鏡・洗濯機・マット・タオル・小型の暖房(セラミックヒーター)。"""
    x0, x1 = DRESS
    floor = principled("DressFloor", (0.75, 0.72, 0.66), rough=0.35)
    color_variation(floor, (0.7, 0.67, 0.6), (0.8, 0.77, 0.7), scale=6)
    wallp = principled("DressWall", (0.9, 0.9, 0.88), rough=0.6)
    box("DressBack", (x1 - x0, 0.06, H), ((x0 + x1) / 2, BACK_Y + 0.03, H / 2), wallp)
    box("DressFloor", (x1 - x0 + 0.1, 2.0, 0.04), ((x0 + x1) / 2, BACK_Y - 1.0, -0.02), floor)
    box("DressCeil", (x1 - x0, 2.0, 0.04), ((x0 + x1) / 2, BACK_Y - 1.0, H + 0.02), principled("DressCeiling", (0.88, 0.88, 0.86), rough=0.6))
    # 浴室との間の折れ戸(半透明)
    frosted = principled("Frosted", (0.9, 0.92, 0.95), rough=0.4, transmission=0.9)
    box("BathDoor", (0.04, 0.7, 1.9), (x1 + 0.02, BACK_Y - 1.25, 0.95), frosted)
    vanity = principled("Vanity", (0.95, 0.95, 0.93), rough=0.25, coat=0.4)
    box("Vanity", (0.75, 0.5, 0.8), (x0 + 0.5, BACK_Y - 0.25, 0.4), vanity, bevel=0.02)
    box("Basin", (0.6, 0.38, 0.06), (x0 + 0.5, BACK_Y - 0.27, 0.82), vanity, bevel=0.03)
    mirror = metal("Mirror", (0.9, 0.9, 0.92), rough=0.02, brushed=False)
    box("Mirror", (0.6, 0.02, 0.75), (x0 + 0.5, BACK_Y - 0.01, 1.4), mirror)
    washer = principled("Washer", (0.92, 0.92, 0.92), rough=0.3, coat=0.5)
    box("Washer", (0.6, 0.55, 0.9), (x1 - 0.45, BACK_Y - 0.3, 0.45), washer, bevel=0.04)
    cyl("WasherDoor", 0.18, 0.02, (x1 - 0.45, BACK_Y - 0.58, 0.5), principled("WasherGlass", (0.2, 0.25, 0.3), rough=0.05, coat=1.0),
        rot=(math.radians(90), 0, 0))
    box("Mat", (0.6, 0.4, 0.015), (x1 - 0.4, BACK_Y - 1.3, 0.008), principled("BathMat", (0.35, 0.55, 0.65), rough=0.9))
    towel = principled("Towel", (0.95, 0.85, 0.75), rough=0.95)
    add_bump(towel, scale=80, strength=0.6)
    box("Towel", (0.4, 0.04, 0.5), (x0 + 1.1, BACK_Y - 0.03, 1.25), towel, bevel=0.015)
    # 小型の暖房(正面に発熱部)
    body = principled("HeaterBody", (0.93, 0.93, 0.9), rough=0.35)
    hx, hy = (x0 + x1) / 2 - 0.1, BACK_Y - 1.0
    box("Heater", (0.28, 0.16, 0.38), (hx, hy, 0.19), body, bevel=0.03)
    grill = glow("HeaterGlow", (1.0, 0.35, 0.05), 6.0 if heater_on else 0.0)
    grill_obj = box("HeaterGrill", (0.2, 0.01, 0.2), (hx, hy - 0.081, 0.2), grill)
    heater_light = light(scene, "POINT", "HeaterLight", (hx, hy - 0.3, 0.25), 20.0 if heater_on else 0.0, (1.0, 0.5, 0.2), size=0.15)
    light(scene, "AREA", "DressLamp", ((x0 + x1) / 2, BACK_Y - 0.8, H - 0.05), 25, (0.85, 0.9, 1.0), size=0.5)
    return grill, heater_light, (hx, hy)


def living(scene):
    """居間:ソファ・ローテーブル・テレビ・暖かいスタンドライト・エアコン。"""
    x0, x1 = LIVING
    wood = principled("LivingFloor", (0.5, 0.33, 0.2), rough=0.4, coat=0.3)
    color_variation(wood, (0.42, 0.27, 0.16), (0.58, 0.4, 0.25), scale=3, detail=10)
    wallp = principled("LivingWall", (0.93, 0.9, 0.84), rough=0.7)
    box("LivingBack", (x1 - x0, 0.06, H), ((x0 + x1) / 2, BACK_Y + 0.03, H / 2), wallp)
    box("LivingFloor", (x1 - x0, 2.6, 0.04), ((x0 + x1) / 2, BACK_Y - 1.3, -0.02), wood)
    box("LivingCeil", (x1 - x0, 2.6, 0.04), ((x0 + x1) / 2, BACK_Y - 1.3, H + 0.02), principled("LivingCeiling", (0.9, 0.88, 0.85), rough=0.7))
    box("DividerWall", (0.12, 2.6, H), (x1 + 0.06, BACK_Y - 1.3, H / 2), wallp)
    sofa = principled("Sofa", (0.55, 0.42, 0.32), rough=0.8)
    cx = (x0 + x1) / 2
    box("SofaSeat", (2.0, 0.8, 0.42), (cx, BACK_Y - 0.5, 0.21), sofa, bevel=0.06)
    box("SofaBack", (2.0, 0.2, 0.5), (cx, BACK_Y - 0.12, 0.6), sofa, bevel=0.06)
    for s in (-1, 1):
        box(f"SofaArm{s}", (0.18, 0.8, 0.6), (cx + s * 1.0, BACK_Y - 0.5, 0.3), sofa, bevel=0.06)
    box("Table", (1.0, 0.55, 0.05), (cx, BACK_Y - 1.5, 0.38), principled("TableWood", (0.35, 0.22, 0.13), rough=0.35), bevel=0.01)
    box("Rug", (2.4, 1.6, 0.01), (cx, BACK_Y - 1.2, 0.005), principled("Rug", (0.75, 0.6, 0.45), rough=1.0))
    cyl("LampPole", 0.015, 1.4, (x0 + 0.4, BACK_Y - 0.35, 0.7), metal("LampMetal", (0.2, 0.2, 0.2), rough=0.3, brushed=False))
    cyl("LampShade", 0.2, 0.3, (x0 + 0.4, BACK_Y - 0.35, 1.45), glow("LampShade", (1.0, 0.75, 0.45), 4.0))
    light(scene, "POINT", "LivingWarm", (x0 + 0.4, BACK_Y - 0.4, 1.4), 120, (1.0, 0.7, 0.4), size=0.2)
    box("AC", (0.8, 0.25, 0.28), (cx, BACK_Y - 0.15, H - 0.3), principled("ACWhite", (0.95, 0.95, 0.95), rough=0.3), bevel=0.04)


def thermo_overlay(scene, start):
    """サーモグラフィー風に、各部屋を温度の色で染める(半透明の発光する霧)。"""
    zones = [("居間 22℃", LIVING, (1.0, 0.5, 0.1)), ("脱衣所 10℃", DRESS, (0.1, 0.35, 1.0)),
             ("お湯 42℃", (-TUB_X, TUB_X), (1.0, 0.08, 0.04))]
    objs = []
    for label, (x0, x1), col in zones:
        mat = bpy.data.materials.new(f"Thermo{label}")
        try:
            mat.use_nodes = True
        except AttributeError:
            pass
        n, l = mat.node_tree.nodes, mat.node_tree.links
        n.remove(n["Principled BSDF"])
        vol = n.new("ShaderNodeVolumePrincipled")
        vol.inputs["Density"].default_value = 0.0
        vol.inputs["Emission Color"].default_value = (*col, 1)
        vol.inputs["Emission Strength"].default_value = 0.0
        l.new(vol.outputs[0], n["Material Output"].inputs["Volume"])
        z1 = WATER_Z if "お湯" in label else H
        o = box(f"Zone{label}", (x1 - x0 - 0.05, 1.6 if "お湯" not in label else 2 * TUB_Y, z1 - 0.02),
                ((x0 + x1) / 2, BACK_Y - 0.85 if "お湯" not in label else 0, z1 / 2), mat)
        es = vol.inputs["Emission Strength"]
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
        es.default_value = 0.0
        es.keyframe_insert("default_value", frame=start)
        es.default_value = 0.35
        es.keyframe_insert("default_value", frame=start + 10)
        lab = text(scene, label, 0.36, glow(f"Label{label}", (1, 1, 1), 4.0), ((x0 + x1) / 2, BACK_Y - 2.0, 1.95),
                   (math.radians(90), 0, 0))
        objs.append((o, lab))
        start += 14
    return objs


def gable(scene, name, length, depth, base_z, rise, mat, center_y=6.0):
    """切妻の三角柱(x 方向に長い)。"""
    import bmesh
    bm = bmesh.new()
    hx, hy = length / 2, depth / 2
    pts = [(-hx, center_y - hy, base_z), (-hx, center_y + hy, base_z), (-hx, center_y, base_z + rise),
           (hx, center_y - hy, base_z), (hx, center_y + hy, base_z), (hx, center_y, base_z + rise)]
    v = [bm.verts.new(p) for p in pts]
    for f in ([0, 1, 2], [3, 5, 4], [0, 3, 4, 1], [1, 4, 5, 2], [2, 5, 3, 0]):
        bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    scene.collection.objects.link(obj)
    assign(obj, mat)
    return obj


def exterior(scene, frames):
    """雪の夜の家:2階建て・切妻屋根・暖かい窓・雪の地面と木・降る雪。"""
    world = scene.world.node_tree.nodes["Background"]
    world.inputs["Color"].default_value = (0.02, 0.03, 0.07, 1)
    world.inputs["Strength"].default_value = 1.0
    snow = principled("Snow", (0.92, 0.94, 0.98), rough=0.6, sss=0.6, sss_radius=(0.8, 0.9, 1.0), sss_scale=0.05)
    add_bump(snow, scale=3, strength=0.4)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=120, y_subdivisions=120, size=60)
    ground = bpy.context.active_object
    tex = bpy.data.textures.new("SnowDrift", "CLOUDS")
    tex.noise_scale = 3.0
    d = ground.modifiers.new("drift", "DISPLACE")
    d.texture, d.strength = tex, 0.25
    smooth(ground)
    assign(ground, snow)
    plaster = principled("Plaster", (0.82, 0.78, 0.7), rough=0.7)
    add_bump(plaster, scale=20, strength=0.2)
    box("HouseBody", (8.0, 6.0, 5.6), (0, 6.0, 2.8), plaster)
    roof = principled("Roof", (0.2, 0.22, 0.26), rough=0.5)
    gable(scene, "Roof", 8.6, 6.8, 5.6, 1.9, roof)            # 切妻屋根
    gable(scene, "RoofSnow", 8.7, 6.9, 5.68, 1.9, snow)       # 屋根に積もった雪
    gable(scene, "Gable", 8.0, 6.0, 5.6, 1.65, plaster)      # 妻壁(三角の壁)
    warm = glow("WindowWarm", (1.0, 0.68, 0.35), 6.0)
    frame_mat = principled("WindowFrame", (0.15, 0.13, 0.12), rough=0.5)
    windows = [(-2.6, 1.6), (-0.4, 1.6), (3.0, 1.6), (-2.4, 4.2), (0.9, 4.2)]
    for i, (x, z) in enumerate(windows):
        box(f"WinFrame{i}", (1.5, 0.08, 1.2), (x, 2.97, z), frame_mat)
        box(f"Win{i}", (1.36, 0.06, 1.06), (x, 2.95, z), warm)
        box(f"WinBar{i}", (0.05, 0.05, 1.06), (x, 2.93, z), frame_mat)
        light(scene, "AREA", f"WinLight{i}", (x, 2.6, z), 70, (1.0, 0.65, 0.35), size=1.2, look_at=(x, -2, 0))
    box("Door", (1.0, 0.1, 2.1), (1.3, 2.96, 1.05), principled("DoorWood", (0.35, 0.22, 0.13), rough=0.45))
    rnd = random.Random(4)
    pine = principled("Pine", (0.05, 0.18, 0.1), rough=0.7)
    for i in range(9):  # 雪をかぶった木
        x = rnd.choice([-1, 1]) * rnd.uniform(5.5, 12)
        y = rnd.uniform(1, 12)
        hgt = rnd.uniform(3, 6)
        bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=hgt * 0.32, depth=hgt, location=(x, y, hgt / 2))
        assign(bpy.context.active_object, pine)
        bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=hgt * 0.22, depth=hgt * 0.45, location=(x, y, hgt * 0.8))
        assign(bpy.context.active_object, snow)
    moon = light(scene, "SUN", "Moon", (10, -10, 20), 0.6, (0.6, 0.7, 1.0), size=math.radians(1), look_at=(0, 5, 0))
    # 降る雪:小さな粒を4000個まとめた1つの物体を、ゆっくり下へ流す(高さ方向に十分長く敷き詰めておく)
    import bmesh
    bm = bmesh.new()
    for i in range(4000):
        c = (rnd.uniform(-12, 12), rnd.uniform(-16, 4), rnd.uniform(0, 30))
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rnd.uniform(0.015, 0.035),
                                   matrix=__import__("mathutils").Matrix.Translation(c))
    me = bpy.data.meshes.new("Snowfall")
    bm.to_mesh(me)
    bm.free()
    flakes = bpy.data.objects.new("Snowfall", me)
    scene.collection.objects.link(flakes)
    assign(flakes, principled("Flake", (1, 1, 1), rough=0.5, emission=0.8, emission_color=(0.9, 0.95, 1.0)))
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    flakes.location = (0, 0, 0)
    flakes.keyframe_insert("location", frame=1)
    flakes.location = (0.6, 0, -0.9 * frames / 24)
    flakes.keyframe_insert("location", frame=frames)
    return moon
