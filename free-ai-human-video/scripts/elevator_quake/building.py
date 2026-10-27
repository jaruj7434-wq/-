"""ビルの断面(ミニチュア風)。エレベーターのかご・ロープ・つり合いおもり・巻上機・地震感知器。

mode: nearest(全階ボタンで近い階に止まって降りる)/ auto(揺れを感知して自動で最寄り階へ)/ stuck(古い機種は階の間で止まる)
"""
import math
import random

import bpy

from kit import (add_bump, assign, box, camera, color_variation, cyl, glow, glow_socket, key, key_socket, light,
                 metal, principled, reset_scene, shake, text)

FLOORS = 7
FH = 3.2       # 階の高さ
SLAB = 0.25
SHAFT = 1.25   # 昇降路の半幅
DEPTH = 6.0


def floor_z(n):
    """n 階の床の高さ(かごの床をここに合わせる)。"""
    return (n - 1) * FH + SLAB


def building(scene):
    random.seed(2)
    concrete = principled("Concrete", (0.72, 0.7, 0.66), rough=0.8)
    color_variation(concrete, (0.66, 0.64, 0.6), (0.78, 0.76, 0.72), scale=2)
    add_bump(concrete, scale=20, strength=0.15)
    shaft_mat = principled("ShaftWall", (0.16, 0.16, 0.18), rough=0.85)
    wall_colors = [(0.95, 0.78, 0.55), (0.55, 0.75, 0.9), (0.92, 0.6, 0.55), (0.6, 0.82, 0.6), (0.95, 0.9, 0.7)]
    sky = glow("Window", (0.45, 0.7, 1.0), 0.9)
    wood = principled("Wood", (0.55, 0.36, 0.2), rough=0.5)
    color_variation(wood, (0.48, 0.3, 0.16), (0.62, 0.42, 0.24), scale=6)
    green = principled("Plant", (0.15, 0.45, 0.15), rough=0.6)
    sofa = principled("Sofa", (0.25, 0.4, 0.6), rough=0.7)
    landing_door = metal("LandingDoor", (0.7, 0.7, 0.72), rough=0.25)
    label_mat = principled("Label", (0.15, 0.15, 0.17), rough=0.5)
    root = bpy.data.objects.new("Building", None)
    scene.collection.objects.link(root)
    parts = []
    for n in range(1, FLOORS + 2):
        z = (n - 1) * FH
        parts.append(box(f"Slab{n}", (12, DEPTH, SLAB), (0, DEPTH / 2, z + SLAB / 2), concrete))
        if n > FLOORS:
            continue
        for side in (-1, 1):  # 左右の部屋
            wall = principled(f"Wall{n}{side}", random.choice(wall_colors), rough=0.7)
            cx = side * (SHAFT + 0.15 + (6 - SHAFT - 0.15) / 2)
            w = 6 - SHAFT - 0.15
            parts.append(box(f"Back{n}{side}", (w, 0.2, FH - SLAB), (cx, DEPTH, z + SLAB + (FH - SLAB) / 2), wall))
            parts.append(box(f"Win{n}{side}", (w * 0.55, 0.05, 1.3), (cx, DEPTH - 0.11, z + SLAB + 1.5), sky))
            # 家具(大きさの手がかり)
            if random.random() < 0.6:
                parts.append(box(f"Desk{n}{side}", (1.2, 0.6, 0.05), (cx + random.uniform(-1, 1), 3.5, z + SLAB + 0.72), wood))
                for lx in (-0.55, 0.55):
                    parts.append(box(f"Leg{n}{side}{lx}", (0.04, 0.5, 0.7), (cx + lx, 3.5, z + SLAB + 0.35), wood))
            else:
                parts.append(box(f"Sofa{n}{side}", (1.6, 0.8, 0.45), (cx, 4.6, z + SLAB + 0.23), sofa, bevel=0.08))
            if random.random() < 0.5:
                parts.append(cyl(f"Pot{n}{side}", 0.2, 0.35, (cx + side * 1.6, 4.8, z + SLAB + 0.18), wood))
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.45, location=(cx + side * 1.6, 4.8, z + SLAB + 0.75))
                o = bpy.context.active_object
                assign(o, green)
                parts.append(o)
        # 乗り場の扉(昇降路の左側の壁)と階数表示
        parts.append(box(f"LDoor{n}", (0.06, 1.0, 2.1), (-SHAFT - 0.05, 1.1, z + SLAB + 1.05), landing_door))
        parts.append(text(scene, f"{n}F", 0.55, label_mat, (-5.3, 0.02, z + SLAB + 2.3), (math.radians(90), 0, 0), jp=False))
    # 昇降路
    parts.append(box("ShaftBack", (2 * SHAFT, 0.2, FLOORS * FH + 3), (0, 2.3, (FLOORS * FH + 3) / 2 - 1.5), shaft_mat))
    for side in (-1, 1):
        parts.append(box(f"ShaftSide{side}", (0.1, 2.3, FLOORS * FH + 3), (side * SHAFT, 1.15, (FLOORS * FH + 3) / 2 - 1.5), shaft_mat))
        parts.append(box(f"Rail{side}", (0.06, 0.1, FLOORS * FH + 2), (side * 0.95, 1.6, (FLOORS * FH + 2) / 2 - 1.0),
                         metal("Rail", (0.5, 0.5, 0.52), rough=0.3, brushed=False)))
    # 屋上の機械室(巻上機)
    top = FLOORS * FH + SLAB
    machine = metal("Machine", (0.25, 0.35, 0.5), rough=0.35, brushed=False)
    parts.append(box("MachineBase", (2.2, 1.6, 0.3), (0, 1.2, top + 0.15), concrete))
    parts.append(box("Motor", (1.0, 0.8, 0.7), (-0.4, 1.2, top + 0.65), machine, bevel=0.05))
    parts.append(cyl("Sheave", 0.45, 0.3, (0.35, 1.2, top + 0.75), metal("Sheave", rough=0.2, brushed=False),
                     rot=(math.radians(90), 0, 0)))
    for o in parts:
        o.parent = root
    return root


def ground(scene):
    soil = principled("Soil", (0.32, 0.22, 0.14), rough=0.9)
    color_variation(soil, (0.26, 0.18, 0.11), (0.4, 0.28, 0.18), scale=1.2, detail=8)
    add_bump(soil, scale=6, strength=0.3)
    grass = principled("Grass", (0.18, 0.4, 0.15), rough=0.8)
    box("Soil", (40, DEPTH, 14), (0, DEPTH / 2, -7.0), soil)
    box("GrassL", (14, DEPTH, 0.1), (-13, DEPTH / 2, 0.0), grass)
    box("GrassR", (14, DEPTH, 0.1), (13, DEPTH / 2, 0.0), grass)
    pit = principled("Pit", (0.3, 0.3, 0.31), rough=0.85)
    box("Pit", (2 * SHAFT, 2.3, 1.5), (0, 1.15, -0.75), pit)
    # 地震感知器(ピット内の箱)
    sensor_body = principled("SensorBody", (0.85, 0.85, 0.8), rough=0.5)
    box("Sensor", (0.4, 0.25, 0.3), (0.6, 0.6, 0.15), sensor_body, bevel=0.03)
    lamp = glow("SensorLamp", (1.0, 0.1, 0.05), 0.0)
    cyl("SensorLED", 0.05, 0.04, (0.6, 0.47, 0.2), lamp, rot=(math.radians(90), 0, 0))
    return lamp


def elevator(scene):
    """かご(手前を切り取って中が見える)・ロープ・つり合いおもり。"""
    steel = metal("CarSteel", (0.55, 0.56, 0.6), rough=0.3)
    frame = metal("CarFrame", (0.3, 0.3, 0.32), rough=0.4, brushed=False)
    inner = glow("CarLight", (1.0, 0.92, 0.8), 1.2)
    root = bpy.data.objects.new("Car", None)
    scene.collection.objects.link(root)
    parts = [box("CarFloor", (1.7, 1.8, 0.12), (0, 1.1, -0.06), frame),
             box("CarRoof", (1.7, 1.8, 0.12), (0, 1.1, 2.36), frame),
             box("CarBack", (1.7, 0.06, 2.3), (0, 2.0, 1.15), steel),
             box("CarRight", (0.06, 1.8, 2.3), (0.85, 1.1, 1.15), steel),
             box("CarLamp", (1.2, 1.2, 0.02), (0, 1.1, 2.29), inner),
             box("CarRail", (0.04, 1.4, 0.04), (0.8, 1.1, 0.9), frame)]
    doors = [box("CarDoorA", (0.06, 0.5, 2.1), (-0.88, 0.85, 1.05), steel),
             box("CarDoorB", (0.06, 0.5, 2.1), (-0.88, 1.35, 1.05), steel)]
    warn = glow("Warn", (1.0, 0.05, 0.02), 0.0)
    parts.append(cyl("WarnLamp", 0.2, 0.22, (0.3, 0.6, 2.55), warn))
    for o in parts + doors:
        o.parent = root
    light(scene, "POINT", "CarBulb", (0, 1.1, 2.0), 25, (1.0, 0.85, 0.65), size=0.5).parent = root
    rope_mat = metal("Rope", (0.35, 0.35, 0.36), rough=0.4, brushed=False)
    top = FLOORS * FH + SLAB + 0.75
    ropes = []
    for dx in (-0.08, 0.0, 0.08):
        r = cyl(f"Rope{dx}", 0.018, 1.0, (dx, 1.2, 0), rope_mat, verts=12)
        ropes.append(r)
    cw_root = bpy.data.objects.new("Counterweight", None)
    scene.collection.objects.link(cw_root)
    box("CW", (0.35, 0.5, 2.2), (1.05, 1.6, 0), metal("CW", (0.2, 0.2, 0.22), rough=0.5, brushed=False)).parent = cw_root
    cw_rope = cyl("CWRope", 0.018, 1.0, (1.05, 1.6, 0), rope_mat, verts=12)
    return root, doors, warn, ropes, cw_root, cw_rope, top


def set_car(fr, car, ropes, cw, cw_rope, top, z, interp="BEZIER"):
    """かごの高さ z に合わせて、ロープの長さとおもりの位置も動かす。"""
    key(car, "location", fr, (0, 0, z), interp)
    length = top - (z + 2.42)
    for r in ropes:
        key(r, "location", fr, (r.location.x, 1.2, z + 2.42 + length / 2), interp)
        key(r, "scale", fr, (1, 1, length), interp)
    cz = FLOORS * FH * 0.5 + (FLOORS * FH * 0.5 - z) * 0.9  # おもりは逆向きに動く
    key(cw, "location", fr, (0, 0, cz), interp)
    clen = top - (cz + 1.1)
    key(cw_rope, "location", fr, (1.05, 1.6, cz + 1.1 + clen / 2), interp)
    key(cw_rope, "scale", fr, (1, 1, clen), interp)


def open_doors(doors, start, length=10):
    for d, dy in zip(doors, (-0.45, 0.45)):
        key(d, "location", start, d.location[:])
        key(d, "location", start + length, (d.location.x, d.location.y + dy, d.location.z))


def build(mode, frames):
    scene = reset_scene(frames)
    w = scene.world.node_tree.nodes["Background"]
    w.inputs["Color"].default_value = (0.55, 0.68, 0.85, 1)
    w.inputs["Strength"].default_value = 0.35
    bld = building(scene)
    sensor_lamp = ground(scene)
    car, doors, warn, ropes, cw, cw_rope, top = elevator(scene)
    light(scene, "SUN", "Sun", (-12, -10, 25), 4.5, (1.0, 0.93, 0.82), size=math.radians(2), look_at=(0, 3, 8))
    light(scene, "AREA", "FrontFill", (6, -14, 10), 700, (0.85, 0.9, 1.0), size=10, look_at=(0, 2, 9))

    if mode == "nearest":
        cam, target = camera(scene, "Cam", (2.2, -9.5, floor_z(5) + 2.5), (0, 1.0, floor_z(5) + 1.2), lens=30)
        key(cam, "location", 1, (2.6, -10.5, floor_z(5) + 3.2))
        key(cam, "location", frames, (1.2, -8.0, floor_z(5) + 1.8))
        stop = int(frames * 0.5)
        set_car(1, car, ropes, cw, cw_rope, top, floor_z(6) + 1.2, "LINEAR")
        set_car(int(frames * 0.2), car, ropes, cw, cw_rope, top, floor_z(6) - 0.4)
        set_car(stop, car, ropes, cw, cw_rope, top, floor_z(5))
        open_doors(doors, int(frames * 0.66))
        shake(bld, 1, frames, 0.06, (0, 0, 0), every=2, decay=True, seed=3)
    elif mode == "auto":
        cam, target = camera(scene, "Cam", (4.0, -19.0, 5.0), (0, 1.5, 5.0), lens=32)
        key(cam, "location", 1, (4.5, -20.0, 3.5))
        key(cam, "location", frames, (2.5, -15.0, 9.0))
        key(target, "location", 1, (0, 1.5, 2.0))
        key(target, "location", frames, (0, 1.5, 10.0))
        wave = glow("Wave", (1.0, 0.45, 0.1), 3.0)
        hit = int(frames * 0.3)
        for i in range(4):  # 地震の波(地中から広がる)
            bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.06, location=(0, -0.05, -9),
                                             rotation=(math.radians(90), 0, 0))
            ring = bpy.context.active_object
            assign(ring, wave)
            s0 = 1 + i * 8
            key(ring, "scale", s0, (0.2, 0.2, 0.2), "LINEAR")
            key(ring, "scale", s0 + 40, (13, 13, 1), "LINEAR")
            key(ring, "scale", s0 + 41, (0, 0, 0), "CONSTANT")
        key_socket(glow_socket(sensor_lamp), 1, 0.0, "CONSTANT")
        key_socket(glow_socket(sensor_lamp), hit, 0.0)
        key_socket(glow_socket(sensor_lamp), hit + 4, 12.0)
        set_car(1, car, ropes, cw, cw_rope, top, floor_z(3) + 0.8, "LINEAR")
        set_car(hit, car, ropes, cw, cw_rope, top, floor_z(3) + 1.9)
        set_car(int(frames * 0.68), car, ropes, cw, cw_rope, top, floor_z(4))
        open_doors(doors, int(frames * 0.8))
        shake(bld, hit, frames, 0.08, (0, 0, 0), every=2, decay=True, seed=4)
    else:  # stuck
        z = floor_z(4) + FH * 0.5
        cam, target = camera(scene, "Cam", (2.0, -8.5, z + 2.0), (0, 1.0, z + 1.0), lens=30)
        key(cam, "location", 1, (2.4, -9.5, z + 2.4))
        key(cam, "location", frames, (1.2, -7.5, z + 1.5))
        set_car(1, car, ropes, cw, cw_rope, top, z + 0.6, "BEZIER")
        set_car(int(frames * 0.25), car, ropes, cw, cw_rope, top, z)
        for fr in range(int(frames * 0.25), frames, 6):  # 警告ランプの点滅
            key_socket(glow_socket(warn), fr, 15.0, "CONSTANT")
            key_socket(glow_socket(warn), fr + 3, 0.0, "CONSTANT")
        shake(bld, 1, int(frames * 0.6), 0.05, (0, 0, 0), every=2, decay=True, seed=5)
    return scene
