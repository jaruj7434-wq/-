"""台所のセット(作業台・ガスコンロ・天ぷら鍋・タイル壁・吊り戸棚・小物)。

座標:コンロの天板の上面が z=0、鍋の中心が (0, 0)。単位は m。手前が -y。
"""
import math
import random

import bmesh
import bpy

from kit import add_bump, assign, box, color_variation, cyl, light, metal, principled, smooth

POT_R, POT_H = 0.12, 0.09     # 天ぷら鍋(直径24cm・深さ9cm)
OIL_Z = 0.065                 # 油面の高さ
CEIL = 1.55                   # 天井(コンロ天板から)
ROOM_LIGHT = 9               # 部屋の照明(W)。炎がいちばんの光源になるよう暗め


def lathe(name, profile, mat, segments=96):
    """断面 [(r, z), ...] を回転させて器の形を作る(内側の面も含めて閉じた形)。"""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        ring = [bm.verts.new((r * math.cos(a), r * math.sin(a), z))
                for a in (i * math.tau / segments for i in range(segments))]
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new([a[i], a[j], b[j], b[i]])
    # 回転軸上(r=0)の点が重なったままだと面の向きが決まらず、ガラスなどが黒く写るので1点にまとめる
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for p in me.polygons:
        p.use_smooth = True
    assign(obj, mat)
    return obj


def pot(scene):
    """鉄の天ぷら鍋(外側・縁・内側・底)と2つの持ち手、油面。"""
    iron = principled("Iron", (0.035, 0.034, 0.036), rough=0.42)
    iron.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0
    add_bump(iron, scale=60, strength=0.25)
    R, H, t = POT_R, POT_H, 0.004
    prof = [(0.0, 0.003), (R - 0.02, 0.0), (R - 0.004, 0.006), (R, 0.03), (R + 0.004, H - 0.006),
            (R + 0.018, H), (R + 0.018, H + 0.003), (R + 0.001, H + 0.002), (R - t, H - 0.006),
            (R - t - 0.004, 0.03), (R - t - 0.016, t + 0.002), (0.0, t)]
    body = lathe("Pot", prof, iron)
    for side in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.025, minor_radius=0.005,
                                         location=(side * (R + 0.03), 0, H - 0.012), rotation=(0, math.radians(90), 0))
        handle = bpy.context.active_object
        smooth(handle)
        assign(handle, iron)
    oil = principled("Oil", (0.72, 0.45, 0.1), rough=0.03, transmission=0.35, ior=1.47)
    add_bump(oil, scale=18, strength=0.08)
    surface = cyl("OilSurface", R - t - 0.005, 0.002, (0, 0, OIL_Z), oil, verts=96)
    return body, surface


def burner(scene, x, y, flame_on=False):
    """五徳・バーナー。flame_on で青いガスの炎(発光リング)を付ける。"""
    cast = principled("CastIron", (0.02, 0.02, 0.02), rough=0.55)
    cyl("BurnerBase", 0.05, 0.02, (x, y, 0.01), metal("BurnerMetal", (0.4, 0.4, 0.42), rough=0.4, brushed=False))
    cyl("BurnerCap", 0.035, 0.008, (x, y, 0.024), cast)
    for k in range(5):  # 五徳
        a = k * math.tau / 5
        arm = box(f"Trivet{k}", (0.1, 0.012, 0.012), (x + 0.11 * math.cos(a), y + 0.11 * math.sin(a), 0.03), cast, bevel=0.003)
        arm.rotation_euler.z = a
    gas = None
    if flame_on:
        gas = principled("GasFlame", (0.2, 0.45, 1.0), emission=8.0, emission_color=(0.25, 0.5, 1.0), alpha=0.6)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.042, minor_radius=0.006, location=(x, y, 0.028))
        ring = bpy.context.active_object
        assign(ring, gas)
    return gas


def kitchen(scene, gas_on=True, props=True, with_burner=True):
    random.seed(9)
    worktop = principled("Worktop", (0.82, 0.8, 0.77), rough=0.25, coat=0.3)
    color_variation(worktop, (0.78, 0.76, 0.73), (0.88, 0.86, 0.83), scale=30, detail=8)
    glass_top = principled("HobGlass", (0.015, 0.015, 0.017), rough=0.08, coat=1.0)
    box("Worktop", (3.0, 0.65, 0.04), (0, 0.0, -0.025), worktop)
    box("Hob", (0.6, 0.5, 0.008), (0, 0.0, -0.001), glass_top, bevel=0.003)
    box("CabinetFront", (3.0, 0.02, 0.85), (0, -0.33, -0.47), principled("Cabinet", (0.92, 0.9, 0.86), rough=0.4))
    box("Floor", (6, 6, 0.02), (0, 0, -0.86), principled("FloorWood", (0.45, 0.32, 0.2), rough=0.5))
    # 壁(白いタイル)
    tile = principled("Tile", (0.8, 0.8, 0.78), rough=0.15, coat=0.6)
    n, l = tile.node_tree.nodes, tile.node_tree.links
    tc = n.new("ShaderNodeTexCoord")
    brick = n.new("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 9.0
    brick.inputs["Mortar Size"].default_value = 0.012
    brick.inputs["Color1"].default_value = (0.8, 0.8, 0.77, 1)
    brick.inputs["Color2"].default_value = (0.76, 0.76, 0.73, 1)
    brick.inputs["Mortar"].default_value = (0.6, 0.6, 0.58, 1)
    mapping = n.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
    l.new(tc.outputs["Object"], mapping.inputs["Vector"])
    l.new(mapping.outputs["Vector"], brick.inputs["Vector"])
    l.new(brick.outputs["Color"], n["Principled BSDF"].inputs["Base Color"])
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    l.new(brick.outputs["Fac"], bump.inputs["Height"])
    l.new(bump.outputs["Normal"], n["Principled BSDF"].inputs["Normal"])
    box("BackWall", (3.0, 0.03, CEIL + 0.9), (0, 0.33, CEIL / 2 - 0.45), tile)
    box("Ceiling", (3.0, 2.5, 0.03), (0, -0.9, CEIL + 0.015), principled("CeilingPaint", (0.9, 0.9, 0.88), rough=0.8))
    wood = principled("CabWood", (0.6, 0.45, 0.3), rough=0.45)
    color_variation(wood, (0.52, 0.38, 0.24), (0.68, 0.52, 0.36), scale=4, detail=10)
    for side in (-1, 1):  # 吊り戸棚(コンロの真上は空ける)
        box(f"Upper{side}", (0.9, 0.33, 0.6), (side * 1.0, 0.15, CEIL - 0.3), wood, bevel=0.005)
    if props:
        board = principled("Board", (0.75, 0.6, 0.42), rough=0.5)
        color_variation(board, (0.7, 0.55, 0.38), (0.82, 0.68, 0.5), scale=8, detail=10)
        box("CuttingBoard", (0.36, 0.22, 0.02), (-0.62, -0.02, 0.01), board, bevel=0.004)
        ceramic = principled("Ceramic", (0.9, 0.88, 0.82), rough=0.2, coat=0.6)
        batter = principled("Batter", (0.95, 0.9, 0.75), rough=0.4, sss=0.4, sss_scale=0.02)
        bowl = lathe("Bowl", [(0.0, 0.0), (0.05, 0.0), (0.085, 0.05), (0.08, 0.05), (0.045, 0.006), (0.0, 0.006)], ceramic)
        bowl.location = (0.55, 0.05, 0.0)
        cyl("BatterIn", 0.072, 0.004, (0.55, 0.05, 0.038), batter)
        chop = principled("Chopsticks", (0.55, 0.35, 0.18), rough=0.4)
        for k in (-1, 1):
            c = cyl(f"Chopstick{k}", 0.003, 0.28, (0.42 + k * 0.008, -0.12, 0.004), chop, rot=(0, math.radians(90), math.radians(12)), verts=12)
    gas = burner(scene, 0, 0, flame_on=gas_on) if with_burner else None
    # 照明:天井の照明+窓からの柔らかい光
    light(scene, "AREA", "CeilingLight", (0.0, -0.5, CEIL - 0.02), ROOM_LIGHT, (1.0, 0.9, 0.78), size=0.8)
    light(scene, "AREA", "Window", (-1.6, -0.6, 0.8), ROOM_LIGHT * 1.2, (0.75, 0.85, 1.0), size=1.2, look_at=(0, 0, 0.3))
    world = scene.world.node_tree.nodes["Background"]
    world.inputs["Color"].default_value = (0.25, 0.24, 0.23, 1)
    world.inputs["Strength"].default_value = 0.04
    return gas


def fire_light(scene, loc, flames, strength=120):
    """炎の明るさに合わせて揺らめく点光源(周りを照らす)。flames: フレームごとの炎の強さ(0〜1)。"""
    l = light(scene, "POINT", "FireGlow", loc, 0.0, (1.0, 0.55, 0.2), size=0.12)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    for fr, f in enumerate(flames, start=1):
        l.data.energy = strength * f
        l.data.keyframe_insert("energy", frame=fr)
    return l
