"""エレベーターのかごの中(ボタン盤・扉・非常灯・防災キャビネット)。

mode: shake / buttons / doors_no / bell / blackout / clock / cabinet / outro
"""
import math

import bmesh
import bpy

from kit import (assign, box, camera, color_variation, add_bump, cyl, glow, glow_socket, key, key_socket, light,
                 metal, principled, reset_scene, shake, smooth, text)

W, D, H = 0.8, 0.7, 2.3  # かごの半幅・半奥行き・高さ(m)
FLOORS = [(9, 10), (7, 8), (5, 6), (3, 4), (1, 2)]
PANEL_X = 0.6
LAMP, LIGHT = 2.2, 50  # 天井照明の明るさ(発光の強さ、ライトのW)
FACE_IN = (math.radians(90), 0, math.radians(180))  # 前面の壁に貼り、かごの内側を向く


def car(scene):
    steel = metal("Steel", (0.62, 0.62, 0.64), rough=0.26)
    steel_dark = metal("SteelDark", (0.45, 0.45, 0.48), rough=0.3)
    seam = principled("Seam", (0.02, 0.02, 0.02), rough=0.6)
    floor_mat = principled("FloorStone", (0.12, 0.12, 0.13), rough=0.35, coat=0.3)
    color_variation(floor_mat, (0.08, 0.08, 0.09), (0.2, 0.2, 0.21), scale=12, detail=8)
    ceil = principled("Ceiling", (0.85, 0.85, 0.85), rough=0.6)
    # 壁(縦の継ぎ目で3枚ずつに分ける)
    for side in (-1, 1):
        for k in range(3):
            y0 = -D + k * (2 * D / 3)
            box(f"Side{side}{k}", (0.02, 2 * D / 3 - 0.008, H), (side * W, y0 + D / 3, H / 2), steel)
        box(f"Rail{side}", (0.03, 2 * D - 0.3, 0.03), (side * (W - 0.06), 0, 0.9), steel_dark, bevel=0.01)
    for k in range(3):
        x0 = -W + k * (2 * W / 3)
        box(f"Back{k}", (2 * W / 3 - 0.008, 0.02, H), (x0 + W / 3, D, H / 2), steel)
    box("BackSeam", (2 * W, 0.01, H), (0, D + 0.012, H / 2), seam)
    # 前面(扉の左右と上)
    box("FrontL", (W - 0.4, 0.03, H), (-(0.4 + W) / 2, -D, H / 2), steel_dark)
    box("FrontR", (W - 0.4, 0.03, H), ((0.4 + W) / 2, -D, H / 2), steel_dark)
    box("FrontTop", (0.8, 0.03, H - 2.1), (0, -D, 2.1 + (H - 2.1) / 2), steel_dark)
    doors = [box("DoorL", (0.4, 0.03, 2.1), (-0.2, -D - 0.03, 1.05), steel),
             box("DoorR", (0.4, 0.03, 2.1), (0.2, -D - 0.03, 1.05), steel)]
    box("DoorGap", (0.006, 0.035, 2.1), (0, -D - 0.03, 1.05), seam)
    box("Floor", (2 * W, 2 * D, 0.02), (0, 0, -0.01), floor_mat)
    box("Sill", (0.8, 0.12, 0.012), (0, -D - 0.02, 0.0), steel_dark)
    box("Ceiling", (2 * W, 2 * D, 0.02), (0, 0, H + 0.01), ceil)
    lamp = glow("CeilingLamp", (1.0, 0.97, 0.92), LAMP)
    box("LampPanel", (1.1, 0.8, 0.01), (0, 0.05, H - 0.005), lamp)
    emer = glow("EmergencyLamp", (1.0, 0.75, 0.4), 0.0)
    box("EmergencyLight", (0.16, 0.05, 0.04), (-0.55, -D + 0.04, H - 0.05), emer)
    key_light = light(scene, "AREA", "CeilingLight", (0, 0.05, H - 0.05), LIGHT, (1.0, 0.96, 0.9), size=1.0)
    key_light.rotation_euler = (0, 0, 0)
    emer_light = light(scene, "POINT", "EmergencyBulb", (-0.55, -D + 0.12, H - 0.12), 0.0, (1.0, 0.7, 0.35), size=0.05)
    return doors, lamp, key_light, emer, emer_light


def panel(scene):
    """ボタン盤。ボタンごとに光り方を動かせるよう、マテリアルを分ける。"""
    plate_mat = metal("Plate", (0.6, 0.6, 0.62), rough=0.18, brushed=True)
    ink = principled("Ink", (0.03, 0.03, 0.03), rough=0.5)
    y = -D + 0.03
    box("Plate", (0.22, 0.012, 0.86), (PANEL_X, y, 1.2), plate_mat, bevel=0.004)
    buttons = {}
    rim = metal("Rim", (0.85, 0.85, 0.87), rough=0.12, brushed=False)
    def button(label, x, z, color=(1.0, 0.4, 0.03), base=(0.55, 0.55, 0.55), jp=False):
        mat = principled(f"Btn{label}", base, rough=0.3)
        mat.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (*color, 1)  # 光ると橙色
        glow_socket(mat).default_value = 0.0
        cyl(f"Rim{label}", 0.031, 0.008, (x, y + 0.006, z), rim, rot=(math.radians(90), 0, 0))
        cyl(f"Btn{label}", 0.025, 0.012, (x, y + 0.011, z), mat, rot=(math.radians(90), 0, 0), bevel=0.003)
        text(scene, label, 0.026, ink, (x, y + 0.0185, z), FACE_IN, jp=jp)
        buttons[label] = mat
        return mat
    for row, (a, b) in enumerate(FLOORS):
        z = 1.5 - row * 0.085
        button(str(a), PANEL_X - 0.045, z)
        button(str(b), PANEL_X + 0.045, z)
    button("開", PANEL_X - 0.045, 1.0, jp=True)
    button("閉", PANEL_X + 0.045, 1.0, jp=True)
    bell = button("", PANEL_X, 0.88, color=(1.0, 0.8, 0.1), base=(0.95, 0.75, 0.1))
    buttons["bell"] = bell
    # ベルのマーク(簡単な形で作る)
    bell_ink = principled("BellInk", (0.05, 0.04, 0.0), rough=0.5)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.012, radius2=0.004, depth=0.016,
                                    location=(PANEL_X, y + 0.019, 0.883))
    b = bpy.context.active_object
    b.scale = (1, 1, 1)
    b.rotation_euler = (0, 0, 0)
    assign(b, bell_ink)
    b.scale.y = 0.15
    cyl("BellClapper", 0.003, 0.002, (PANEL_X, y + 0.019, 0.873), bell_ink, rot=(math.radians(90), 0, 0))
    # 階数表示(扉の上)
    box("Indicator", (0.26, 0.02, 0.1), (0, -D + 0.02, 2.2), principled("LCD", (0.01, 0.01, 0.01), rough=0.2))
    led = glow("LED", (1.0, 0.45, 0.05), 6.0)
    digits = {}
    for n in range(1, 11):
        digits[n] = text(scene, str(n), 0.07, led, (0.0, -D + 0.032, 2.2), FACE_IN, jp=False)
        digits[n].hide_render = True
    return buttons, digits


def cabinet(scene):
    """奥の隅の三角形の防災キャビネットと中身。扉(door)を回して開ける。"""
    steel = metal("CabSteel", (0.7, 0.7, 0.72), rough=0.25)
    x0, y0, s, h = -W + 0.02, D - 0.02, 0.42, 0.5
    bm = bmesh.new()
    pts = [(x0, y0), (x0 + s, y0), (x0, y0 - s)]
    bottom = [bm.verts.new((x, y, 0.0)) for x, y in pts]
    top = [bm.verts.new((x, y, h)) for x, y in pts]
    bm.faces.new(bottom[::-1])
    bm.faces.new(top)
    for i in range(3):
        j = (i + 1) % 3
        if i == 1:
            continue  # 正面は扉にする
        bm.faces.new([bottom[i], bottom[j], top[j], top[i]])
    me = bpy.data.meshes.new("Cabinet")
    bm.to_mesh(me)
    bm.free()
    body = bpy.data.objects.new("Cabinet", me)
    scene.collection.objects.link(body)
    m = body.modifiers.new("solid", "SOLIDIFY")
    m.thickness = 0.01
    assign(body, steel)
    # 扉:蝶番(左端)を軸に回す
    hinge = bpy.data.objects.new("Hinge", None)
    hinge.location = (x0, y0 - s, 0)
    scene.collection.objects.link(hinge)
    length = math.hypot(s, s)
    door = box("CabDoor", (length, 0.012, h), (length / 2, 0, h / 2), steel)
    door.parent = hinge
    hinge.rotation_euler = (0, 0, math.radians(45))
    green = principled("SafetyGreen", (0.05, 0.45, 0.2), rough=0.4)
    white = principled("LabelWhite", (0.95, 0.95, 0.95), rough=0.5)
    label = box("Label", (0.3, 0.004, 0.09), (length / 2, -0.008, 0.36), green)
    label.parent = hinge
    t = text(scene, "防災キャビネット", 0.034, white, (length / 2, -0.012, 0.36), (math.radians(90), 0, 0))
    t.parent = hinge
    # 中身:水・簡易トイレ・ライト
    water = principled("Water", (0.6, 0.85, 1.0), rough=0.05, transmission=1.0, ior=1.33)
    cap = principled("Cap", (0.1, 0.35, 0.9), rough=0.4)
    for i, (x, y) in enumerate([(x0 + 0.07, y0 - 0.07), (x0 + 0.15, y0 - 0.06), (x0 + 0.07, y0 - 0.15)]):
        cyl(f"Bottle{i}", 0.032, 0.2, (x, y, 0.11), water, bevel=0.01)
        cyl(f"Cap{i}", 0.014, 0.025, (x, y, 0.225), cap)
    pack = box("ToiletPack", (0.13, 0.05, 0.16), (x0 + 0.25, y0 - 0.06, 0.09), white, bevel=0.01)
    pack.rotation_euler.z = math.radians(-20)
    t2 = text(scene, "簡易トイレ", 0.022, principled("PackInk", (0.1, 0.3, 0.6), rough=0.5),
              (x0 + 0.24, y0 - 0.088, 0.1), (math.radians(90), 0, math.radians(-20)))
    yellow = principled("Torch", (0.95, 0.75, 0.05), rough=0.35)
    cyl("Torch", 0.022, 0.16, (x0 + 0.17, y0 - 0.16, 0.03), yellow, rot=(0, math.radians(90), math.radians(30)))
    return hinge


def build(mode, frames, cues=None):
    scene = reset_scene(frames)
    doors, lamp, ceil_light, emer, emer_light = car(scene)
    buttons, digits = panel(scene)
    hinge = cabinet(scene)
    lamp_s = glow_socket(lamp)
    emer_s = glow_socket(emer)
    digit = {"shake": 7, "buttons": 7, "doors_no": 4, "bell": 4, "blackout": 4, "clock": 4, "cabinet": 4,
             "outro": 1}[mode]
    digits[digit].hide_render = False

    rig = bpy.data.objects.new("CamRig", None)
    scene.collection.objects.link(rig)
    cam, target = camera(scene, "Cam", (0, 0, 0), (0, -1, 0), lens=24, fstop=None)
    cam.parent = rig
    target.parent = rig

    def place(loc, look, lens, fstop=None, focus=None):
        rig.location = loc
        target.location = tuple(l - c for l, c in zip(look, loc))
        cam.data.lens = lens
        if fstop:
            cam.data.dof.use_dof = True
            cam.data.dof.aperture_fstop = fstop
            cam.data.dof.focus_object = focus or target

    def light_all(start, step=2):
        order = [str(n) for n in range(1, 11)]
        for i, lab in enumerate(order):
            key_socket(glow_socket(buttons[lab]), 1, 0.0, "CONSTANT")
            key_socket(glow_socket(buttons[lab]), start + i * step, 0.0, "LINEAR")
            key_socket(glow_socket(buttons[lab]), start + i * step + 2, 9.0, "LINEAR")

    if mode == "shake":
        place((-0.05, 0.5, 1.5), (PANEL_X - 0.15, -D, 1.22), 22)
        key(rig, "location", 1, (-0.05, 0.5, 1.5))
        key(rig, "location", frames, (0.15, 0.1, 1.38))
        shake(cam, 6, frames, 0.035, (0, 0, 0), every=2, decay=False, seed=1)
        for fr in range(6, frames, 3):  # 照明がチカチカする
            v = LAMP if (fr // 3) % 4 else LAMP * 0.2
            key_socket(lamp_s, fr, v, "CONSTANT")
            ceil_light.data.energy = LIGHT * v / LAMP
            ceil_light.data.keyframe_insert("energy", frame=fr)
    elif mode in ("buttons", "outro"):
        place((PANEL_X - 0.05, -0.28, 1.28), (PANEL_X, -D, 1.22), 40, fstop=2.8)
        if mode == "buttons":
            key(rig, "location", 1, (PANEL_X - 0.08, -0.22, 1.3))
            key(rig, "location", frames, (PANEL_X - 0.03, -0.33, 1.25))
            light_all(4, step=2)
        else:
            for lab in [str(n) for n in range(1, 11)]:
                glow_socket(buttons[lab]).default_value = 9.0
            key(rig, "location", 1, (PANEL_X - 0.04, -0.33, 1.25))
            key(rig, "location", frames, (-0.05, 0.45, 1.48))  # 冒頭の構図に戻る(ループ)
            key(target, "location", 1, (0.04, -0.37, -0.03))
            key(target, "location", frames, (PANEL_X - 0.1, -D - 0.45, 1.22 - 1.48))
    elif mode == "doors_no":
        place((0.0, 0.55, 1.35), (0.0, -D, 1.15), 22)
        key(rig, "location", 1, (0.0, 0.6, 1.35))
        key(rig, "location", frames, (0.0, 0.25, 1.3))
        red = glow("RedX", (1.0, 0.05, 0.03), 8.0)
        xroot = bpy.data.objects.new("XRoot", None)
        xroot.location = (0, -D + 0.1, 1.2)
        scene.collection.objects.link(xroot)
        for a in (45, -45):
            bar = box(f"X{a}", (1.0, 0.03, 0.09), (0, 0, 0), red, bevel=0.02)
            bar.rotation_euler = (0, math.radians(a), 0)
            bar.parent = xroot
        key(xroot, "scale", 1, (0.0, 0.0, 0.0), "CONSTANT")
        key(xroot, "scale", 14, (0.01, 0.01, 0.01), "BEZIER")
        key(xroot, "scale", 20, (1.15, 1.15, 1.15), "BEZIER")
        key(xroot, "scale", 25, (1.0, 1.0, 1.0), "BEZIER")
    elif mode == "bell":
        place((PANEL_X - 0.02, -0.42, 0.95), (PANEL_X, -D, 0.89), 50, fstop=2.0)
        key(rig, "location", 1, (PANEL_X - 0.04, -0.38, 0.97))
        key(rig, "location", frames, (PANEL_X - 0.01, -0.47, 0.93))
        bell_s = glow_socket(buttons["bell"])
        key_socket(bell_s, 1, 0.0)
        key_socket(bell_s, 10, 6.0)
        ring_mat = glow("Ring", (1.0, 0.8, 0.2), 5.0)
        for i in range(4):  # 音の波
            bpy.ops.mesh.primitive_torus_add(major_radius=0.03, minor_radius=0.0025, location=(PANEL_X, -D + 0.05, 0.88),
                                             rotation=(math.radians(90), 0, 0))
            ring = bpy.context.active_object
            assign(ring, ring_mat)
            s0 = 12 + i * 14
            key(ring, "scale", 1, (0, 0, 0), "CONSTANT")
            key(ring, "scale", s0, (1, 1, 1), "LINEAR")
            key(ring, "scale", s0 + 26, (6, 6, 6), "LINEAR")
            key(ring, "location", s0, ring.location[:], "LINEAR")
            key(ring, "location", s0 + 26, (PANEL_X, -D + 0.12, 0.88), "LINEAR")
            key(ring, "scale", s0 + 27, (0, 0, 0), "CONSTANT")
    elif mode in ("blackout", "clock"):
        place((0.35, 0.55, 1.45), (-0.1, -D, 1.3), 20)
        off = int(frames * 0.22) if mode == "blackout" else 1
        on = int(frames * 0.45) if mode == "blackout" else 1
        key_socket(lamp_s, 1, LAMP if mode == "blackout" else 0.0, "CONSTANT")
        ceil_light.data.energy = LIGHT if mode == "blackout" else 0
        ceil_light.data.keyframe_insert("energy", frame=1)
        if mode == "blackout":
            for fr, v in [(off - 6, LAMP * 0.2), (off - 4, LAMP), (off - 2, LAMP * 0.1), (off, 0.0)]:
                key_socket(lamp_s, fr, v, "CONSTANT")
                ceil_light.data.energy = LIGHT * v / LAMP
                ceil_light.data.keyframe_insert("energy", frame=fr)
            key_socket(emer_s, 1, 0.0, "CONSTANT")
            key_socket(emer_s, on, 0.0, "BEZIER")
            emer_light.data.energy = 0
            emer_light.data.keyframe_insert("energy", frame=on)
        key_socket(emer_s, on + 8, 12.0)
        emer_light.data.energy = 9.0
        emer_light.data.keyframe_insert("energy", frame=on + 8)
        key(rig, "location", 1, (0.35, 0.55, 1.45))
        key(rig, "location", frames, (0.25, 0.35, 1.4))
        if mode == "clock":
            clock_root = bpy.data.objects.new("Clock", None)
            clock_root.location = (0.12, -0.15, 1.38)
            clock_root.rotation_euler = (math.radians(90), 0, math.radians(162))  # 文字盤をカメラへ向ける
            scene.collection.objects.link(clock_root)
            face = principled("ClockFace", (0.95, 0.94, 0.9), rough=0.4)
            frame_m = metal("ClockFrame", (0.2, 0.2, 0.22), rough=0.2, brushed=False)
            ink = principled("ClockInk", (0.03, 0.03, 0.03), rough=0.4)
            hand_red = principled("ClockRed", (0.8, 0.05, 0.03), rough=0.4, emission=1.0)
            for o in (cyl("ClockRim", 0.2, 0.04, (0, 0, 0), frame_m, bevel=0.01),
                      cyl("ClockFace", 0.185, 0.042, (0, 0, 0.0), face)):
                o.parent = clock_root
            for i in range(12):
                a = i * math.tau / 12
                t = box(f"Tick{i}", (0.012, 0.035 if i % 3 == 0 else 0.02, 0.006),
                        (0.155 * math.sin(a), 0.155 * math.cos(a), 0.023), ink)
                t.rotation_euler.z = -a
                t.parent = clock_root
            for name, length, width, mat, turns in [("Hour", 0.09, 0.014, ink, 1.5), ("Minute", 0.15, 0.009, ink, 18)]:
                pivot = bpy.data.objects.new(name + "Pivot", None)
                scene.collection.objects.link(pivot)
                pivot.parent = clock_root
                pivot.location = (0, 0, 0.026)
                hand = box(name, (width, length, 0.004), (0, length / 2 - 0.01, 0), mat)
                hand.parent = pivot
                key(pivot, "rotation_euler", 1, (0, 0, 0), "BEZIER")
                key(pivot, "rotation_euler", frames, (0, 0, -turns * math.tau), "BEZIER")
            key(clock_root, "scale", 1, (0.0, 0.0, 0.0), "BEZIER")
            key(clock_root, "scale", 10, (1.0, 1.0, 1.0), "BEZIER")
            emer_light.data.energy = 9.0
    elif mode == "cabinet":
        key_socket(lamp_s, 1, 0.0, "CONSTANT")
        ceil_light.data.energy = 0
        key_socket(emer_s, 1, 12.0, "CONSTANT")
        emer_light.data.energy = 9.0
        fill = light(scene, "POINT", "CabFill", (-0.25, 0.2, 0.75), 30, (1.0, 0.85, 0.65), size=0.3)
        place((0.35, -0.25, 1.25), (-0.64, 0.55, 0.18), 26, fstop=2.8)
        key(rig, "location", 1, (0.4, -0.3, 1.3))
        key(rig, "location", frames, (-0.12, 0.18, 0.8))
        key(hinge, "rotation_euler", int(frames * 0.25), (0, 0, math.radians(45)))
        key(hinge, "rotation_euler", int(frames * 0.55), (0, 0, math.radians(45 - 100)))
    return scene
