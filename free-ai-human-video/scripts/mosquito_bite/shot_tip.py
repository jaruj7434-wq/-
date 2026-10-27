"""カット3:6本の針の束が、ギザギザの2本で皮膚の組織を切り開きながら潜っていくクローズアップ。"""
import math
import random

import bpy

from common import add_bump, assign, camera, curve_tube, key, light, principled, reset_scene, smooth

DEPTH = 18.0  # 針先が進む距離


def bundle(scene):
    """針の束(先端が原点、上方向へ伸びる)。マキシラ(ギザギザの刃)2本を返す。"""
    root = bpy.data.objects.new("Bundle", None)
    scene.collection.objects.link(root)
    amber = principled("Stylet", (0.62, 0.38, 0.14), rough=0.18, sss=0.6, sss_radius=(1, 0.6, 0.3),
                       sss_scale=0.05, coat=1.0)
    add_bump(amber, scale=50, strength=0.1)
    dark = principled("StyletDark", (0.42, 0.24, 0.08), rough=0.22, coat=0.8)
    straight = lambda x, y, top=14: [(x, y, top), (x, y, top * 0.66), (x, y, top * 0.33), (x, y, 0.0)]
    parts = [
        ("Labrum", (0.0, 0.0), 0.15, amber, 0.0),       # 中心の太い管(血を吸う)
        ("Hypopharynx", (0.0, 0.2), 0.055, dark, 0.15),  # 唾液を出す管
        ("MandibleL", (-0.19, 0.13), 0.045, dark, 0.3),
        ("MandibleR", (0.19, 0.13), 0.045, dark, 0.3),
    ]
    for name, (x, y), r, mat, lift in parts:
        obj, sp = curve_tube(scene, name, straight(x, y, 14 + lift), r, mat)
        obj.location.z = lift
        sp.points[-1].radius = 0.15  # 先をとがらせる
        obj.parent = root
    blades = []
    for side in (-1, 1):
        blade_root = bpy.data.objects.new(f"Maxilla{side}", None)
        scene.collection.objects.link(blade_root)
        blade_root.parent = root
        obj, sp = curve_tube(scene, f"MaxillaBlade{side}", straight(side * 0.25, -0.06), 0.07, amber)
        sp.points[-1].radius = 0.1
        obj.scale = (1.0, 0.45, 1.0)
        obj.parent = blade_root
        for k in range(22):  # 外側のギザギザ(返し)
            z = 0.25 + k * 0.13
            bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.04, depth=0.14,
                                            location=(side * 0.29, -0.06, z),
                                            rotation=(0, math.radians(side * -60), 0))
            tooth = bpy.context.active_object
            assign(tooth, amber)
            tooth.parent = blade_root
        blades.append(blade_root)
    return root, blades


def tissue(scene):
    random.seed(21)
    fiber = principled("Collagen", (0.95, 0.72, 0.7), rough=0.35, sss=0.8, sss_radius=(1, 0.5, 0.4), sss_scale=0.1)
    add_bump(fiber, scale=12, strength=0.2, kind="wave")
    cell = principled("Keratinocyte", (0.88, 0.7, 0.58), rough=0.4, sss=0.9, sss_radius=(1, 0.6, 0.4), sss_scale=0.2)
    add_bump(cell, scale=6, strength=0.3)
    fibro = principled("Fibroblast", (0.8, 0.45, 0.55), rough=0.4, sss=0.8, sss_scale=0.1)
    # 表皮:細胞がぎっしり並ぶ
    for i in range(260):
        r = random.uniform(0.55, 4.5)
        a = random.uniform(0, math.tau)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=random.uniform(0.25, 0.4),
                                              location=(r * math.cos(a), r * math.sin(a) + 1.0, random.uniform(-3.2, -0.2)))
        o = bpy.context.active_object
        o.scale = (1.0, 1.0, random.uniform(0.45, 0.7))
        o.rotation_euler = [random.uniform(0, 1) for _ in range(3)]
        smooth(o)
        assign(o, cell)
    # 真皮:波打つ細いコラーゲン繊維の束と線維芽細胞(カメラと針の間は空ける)
    def seg_dist(px, py, bx=2.4, by=-3.2):
        t = max(0.0, min(1.0, (px * bx + py * by) / (bx * bx + by * by)))
        return math.hypot(px - t * bx, py - t * by)

    for i in range(520):
        z = random.uniform(-DEPTH - 4, -3.5)
        a = random.uniform(0, math.pi)
        cx, cy = random.uniform(-3.5, 3.5), random.uniform(-2.0, 5)
        dx, dy = math.cos(a), math.sin(a)
        amp, ph = random.uniform(0.1, 0.3), random.uniform(0, math.tau)
        pts = [(cx + dx * t, cy + dy * t, z + amp * math.sin(t * 1.6 + ph)) for t in (-5, -3, -1, 1, 3, 5)]
        if min(seg_dist(px, py) for px, py, _ in pts) < 0.7:
            continue
        if min(math.hypot(px, py) for px, py, _ in pts) < 0.4 and random.random() < 0.6:
            continue  # 針の通り道は少し空ける
        curve_tube(scene, f"Fiber{i}", pts, random.uniform(0.018, 0.05), fiber)
    for i in range(30):
        r = random.uniform(0.8, 3.5)
        a = random.uniform(0, math.tau)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25, location=(r * math.cos(a), r * math.sin(a) + 1, random.uniform(-DEPTH - 3, -4)))
        o = bpy.context.active_object
        o.scale = (2.4, 0.7, 0.6)
        o.rotation_euler = (0, 0, random.uniform(0, math.pi))
        smooth(o)
        assign(o, fibro)


def build(frames):
    scene = reset_scene(frames)
    w = scene.world.node_tree.nodes["Background"]
    w.inputs["Color"].default_value = (0.18, 0.04, 0.04, 1)
    w.inputs["Strength"].default_value = 0.6
    root, blades = bundle(scene)
    tissue(scene)

    # 針先が上から下へ進む(最初は表皮のすぐ上)
    key(root, "location", 1, (0, 0, 1.0), "BEZIER")
    key(root, "location", frames, (0, 0, -DEPTH), "BEZIER")
    # ギザギザの2本が交互に上下して切り進む
    for fr in range(1, frames + 1, 2):
        ph = 0.12 if (fr // 2) % 2 == 0 else -0.12
        key(blades[0], "location", fr, (0, 0, ph), "LINEAR")
        key(blades[1], "location", fr, (0, 0, -ph), "LINEAR")

    rig = bpy.data.objects.new("CamRig", None)
    scene.collection.objects.link(rig)
    key(rig, "location", 1, (0, 0, 1.0), "BEZIER")
    key(rig, "location", frames, (0, 0, -DEPTH + 0.6), "BEZIER")
    cam, target = camera(scene, "Cam", (2.4, -3.2, 1.2), (0, 0, 0.9), lens=40, fstop=1.8)
    cam.parent = rig
    target.parent = rig
    for name, loc, energy, color in [("Key", (2.0, -2.5, 3.0), 160, (1.0, 0.88, 0.78)),
                                     ("Rim", (-2.5, 2.5, 1.5), 140, (1.0, 0.55, 0.5))]:
        l = light(scene, "POINT", name, loc, energy, color, size=0.6)
        l.parent = rig
    return scene
