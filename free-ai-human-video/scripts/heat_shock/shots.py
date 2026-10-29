"""12カットの 3D シーン。湯気は sims.py の結果(アトラス画像)をボリュームとして描画する。

使い方: python shots.py <カット名> <timings.json> <sims フォルダ> <出力フォルダ> [--preview]
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tempura_fire"))
sys.path.insert(0, str(HERE.parent / "elevator_quake"))
sys.path.insert(0, str(HERE))

import bpy  # noqa: E402

from house import BACK_Y, DRESS, LIVING, bathroom, dressing, exterior, living, thermo_overlay  # noqa: E402
from kit import (assign, box, camera, curve_tube, cyl, glow, glow_socket, key, key_socket, light, metal,  # noqa: E402
                 principled, render, reset_scene, smooth, text)
from plan import STEAM_SHOTS, TUB_RIM, TUB_X, TUB_Y, WATER_Z, windows  # noqa: E402
from volume import SCALES, atlas, domain_box, volume_material  # noqa: E402

RED_X = (1.0, 0.04, 0.03)


def steam(sims, k=32.0):
    """湯気(白く光を散らす煙)。k は濃さ(カメラが湯気ごしに見るアップでは薄くする)。"""
    d = Path(sims) / "steam"
    grid = json.loads((d / "grid.json").read_text())
    info = atlas(d, Path(sims) / "steam_atlas")
    first = sorted((Path(sims) / "steam_atlas").glob("f_*.png"))[0]
    mat = volume_material("Steam", first, info, smoke_k=k, flame_k=0.0, smoke_color=(0.95, 0.96, 0.98), scales=SCALES,
                          absorption=(0.97, 0.97, 0.97))
    domain_box("Steam", tuple(grid["shape"]), grid["h"], tuple(grid["origin"]), mat)


def pop(obj, start, size=1.0):
    key(obj, "scale", 1, (0, 0, 0), "CONSTANT")
    key(obj, "scale", start, (0.01, 0.01, 0.01))
    key(obj, "scale", start + 6, (size * 1.15,) * 3)
    key(obj, "scale", start + 10, (size,) * 3)


def red_x(scene, loc, size, start, rot=(math.radians(90), 0, 0)):
    mat = glow("RedX", RED_X, 10.0)
    root = bpy.data.objects.new("XRoot", None)
    root.location, root.rotation_euler = loc, rot
    scene.collection.objects.link(root)
    for a in (45, -45):
        bar = box(f"X{a}", (size, size * 0.13, 0.01), (0, 0, 0), mat, bevel=size * 0.03)
        bar.rotation_euler = (0, 0, math.radians(a))
        bar.parent = root
    pop(root, start)
    return root


def dark_stage(scene):
    w = scene.world.node_tree.nodes["Background"]
    w.inputs["Color"].default_value = (0.01, 0.012, 0.02, 1)
    w.inputs["Strength"].default_value = 1.0


def bp_graph(scene, frames):
    """光る血圧のグラフ:居間 → 脱衣所(急上昇)→ 湯船(急降下)→ 立ち上がる(さらに低下)と描かれていく。"""
    dark_stage(scene)
    grid_mat = principled("Grid", (0.1, 0.12, 0.16), rough=0.6, emission=0.4, emission_color=(0.2, 0.3, 0.5))
    for i in range(7):
        box(f"GridH{i}", (6.0, 0.005, 0.008), (0, 0, -1.2 + i * 0.4), grid_mat)
    for i in range(9):
        box(f"GridV{i}", (0.008, 0.005, 2.4), (-3.0 + i * 0.75, 0, 0), grid_mat)
    danger = principled("Danger", (0.8, 0.05, 0.05), rough=0.6, emission=0.6, emission_color=(1.0, 0.1, 0.1), alpha=0.35)
    box("DangerHigh", (6.0, 0.004, 0.35), (0, 0.01, 1.0), danger)
    box("DangerLow", (6.0, 0.004, 0.35), (0, 0.01, -1.0), danger)
    pts = [(-3.0, 0, -0.1), (-2.2, 0, -0.05), (-1.6, 0, 0.0), (-1.1, 0, 0.95), (-0.7, 0, 0.9),
           (-0.2, 0, 0.75), (0.3, 0, -0.95), (0.8, 0, -0.85), (1.3, 0, -0.7), (1.8, 0, -1.05), (2.4, 0, -0.4),
           (3.0, 0, -0.2)]
    line_mat = glow("BPLine", (1.0, 0.25, 0.2), 12.0)
    line, sp = curve_tube(scene, "BP", pts, 0.025, line_mat, order=3, resolution=32)
    cu = line.data
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    cu.bevel_factor_end = 0.0
    cu.keyframe_insert("bevel_factor_end", frame=6)
    cu.bevel_factor_end = 1.0
    cu.keyframe_insert("bevel_factor_end", frame=int(frames * 0.85))
    ink = glow("Labels", (0.85, 0.9, 1.0), 2.5)
    for label, x in (("居間", -2.4), ("脱衣所", -1.0), ("湯船", 0.6), ("立ち上がる", 1.9)):
        text(scene, label, 0.3, ink, (x, 0, -1.65), (math.radians(90), 0, 0))
    text(scene, "血圧", 0.34, ink, (-2.7, 0, 1.45), (math.radians(90), 0, 0))
    head = bpy.data.objects.new("PenHead", None)  # 線の先端を追うカメラ用の目印
    scene.collection.objects.link(head)
    cam, tgt = camera(scene, "Cam", (-1.6, -5.2, 0.1), (-1.0, 0, 0.0), lens=24)
    key(cam, "location", 1, (-2.0, -5.0, 0.2))
    key(cam, "location", frames, (0.9, -5.6, 0.0))
    key(tgt, "location", 1, (-1.6, 0, 0.0))
    key(tgt, "location", frames, (0.8, 0, -0.1))
    light(scene, "AREA", "Fill", (0, -3, 2), 40, (0.6, 0.7, 1.0), size=4)


def build(name, timings, sims):
    win = windows(timings)
    frames = win[name][1]
    scene = reset_scene(frames)

    if name in ("exterior", "exterior_end"):
        exterior(scene, frames)
        cam, tgt = camera(scene, "Cam", (-3.0, -14.0, 1.6), (0.0, 3.0, 2.8), lens=30)
        if name == "exterior":
            key(cam, "location", 1, (-3.5, -15.0, 1.7))
            key(cam, "location", frames, (-0.8, -7.5, 1.8))
        else:
            key(cam, "location", 1, (-0.8, -8.0, 1.8))
            key(cam, "location", frames, (-3.5, -15.5, 2.2))
        return scene

    if name == "pressure":
        bp_graph(scene, frames)
        return scene

    if name == "five":
        dark_stage(scene)
        five = text(scene, "5", 1.6, glow("Five", (1.0, 0.82, 0.25), 8.0), (0, 0, 0.1), (math.radians(90), 0, 0), extrude=0.12, jp=False)
        pop(five, 4)
        for i in range(5):
            dot = cyl(f"Dot{i}", 0.09, 0.03, ((i - 2) * 0.35, 0, -1.05), glow(f"Dot{i}", (1.0, 0.82, 0.25), 5.0),
                      rot=(math.radians(90), 0, 0))
            pop(dot, 10 + i * 4)
        camera(scene, "Cam", (0, -5.0, 0.0), (0, 0, -0.1), lens=35)
        return scene

    if name == "food":
        w = scene.world.node_tree.nodes["Background"]
        w.inputs["Color"].default_value = (0.25, 0.2, 0.16, 1)
        w.inputs["Strength"].default_value = 0.3
        table = principled("DiningTable", (0.45, 0.3, 0.18), rough=0.35, coat=0.3)
        box("DiningTable", (1.4, 0.9, 0.04), (0, 0, 0.7), table)
        box("Wall", (4, 0.05, 3), (0, 0.8, 1.5), principled("Wall", (0.9, 0.87, 0.8), rough=0.7))
        beer = principled("Beer", (0.95, 0.6, 0.1), rough=0.03, transmission=0.9, ior=1.35)
        cyl("Beer", 0.04, 0.15, (-0.15, 0.0, 0.795), beer, bevel=0.003)
        foam = principled("Foam", (0.98, 0.96, 0.9), rough=0.8, sss=0.6, sss_scale=0.01)
        cyl("Foam", 0.04, 0.035, (-0.15, 0.0, 0.888), foam, bevel=0.01)
        bowl_mat = principled("RiceBowl", (0.2, 0.25, 0.4), rough=0.25, coat=0.6)
        cyl("Bowl", 0.07, 0.06, (0.12, 0.05, 0.75), bowl_mat, bevel=0.015)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.065, location=(0.12, 0.05, 0.78))
        rice = bpy.context.active_object
        rice.scale.z = 0.5
        smooth(rice)
        assign(rice, principled("Rice", (0.97, 0.96, 0.92), rough=0.6, sss=0.4, sss_scale=0.01))
        cyl("Plate", 0.12, 0.012, (0.05, -0.18, 0.727), principled("Plate", (0.95, 0.95, 0.93), rough=0.2, coat=0.6))
        cyl("Chopsticks", 0.004, 0.22, (0.28, -0.1, 0.725), principled("Hashi", (0.45, 0.2, 0.1), rough=0.4),
            rot=(0, math.radians(90), math.radians(15)), verts=12)
        light(scene, "AREA", "Pendant", (0, -0.1, 1.6), 60, (1.0, 0.8, 0.55), size=0.4)
        red_x(scene, (0.0, -0.25, 0.85), 0.45, 30)
        cam, tgt = camera(scene, "Cam", (0.0, -0.95, 1.05), (0.0, 0.0, 0.8), lens=40, fstop=4.0)
        key(cam, "location", 1, (0.05, -1.0, 1.08))
        key(cam, "location", frames, (-0.05, -0.85, 1.0))
        return scene

    # ---- ここから家の中のカット ----
    rails = bathroom(scene)
    w = scene.world.node_tree.nodes["Background"]
    w.inputs["Color"].default_value = (0.03, 0.035, 0.05, 1)
    w.inputs["Strength"].default_value = 0.5
    if name in STEAM_SHOTS:
        steam(sims, k=9.0 if name == "temp_timer" else 32.0)

    if name == "bath":
        bpy.data.objects["BathLamp"].data.energy = 22
        cam, tgt = camera(scene, "Cam", (0.25, -2.5, 1.3), (0.0, 0.0, 0.65), lens=28, fstop=5.0)
        key(cam, "location", 1, (0.35, -2.7, 1.35))
        key(cam, "location", frames, (0.1, -2.0, 1.15))
    elif name == "heatshock":
        bpy.data.objects["BathLamp"].data.energy = 3
        # 左の壁を赤(熱い)、右の壁を青(寒い)に照らし分ける
        red = light(scene, "SPOT", "Red", (-0.3, -1.6, 1.6), 0, (1.0, 0.08, 0.04), size=0.1, look_at=(-0.95, 0.2, 1.0))
        blue = light(scene, "SPOT", "Blue", (0.3, -1.6, 1.6), 0, (0.08, 0.3, 1.0), size=0.1, look_at=(0.95, 0.2, 1.0))
        for l_ in (red, blue):
            l_.data.spot_size = math.radians(55)
            l_.data.spot_blend = 0.5
            key(l_.data, "energy", 1, 0.0)
            key(l_.data, "energy", 12, 220.0)
        cam, tgt = camera(scene, "Cam", (0.0, -2.6, 1.2), (0, 0, 0.7), lens=26)
        key(cam, "location", 1, (0.0, -2.8, 1.25))
        key(cam, "location", frames, (0.0, -2.3, 1.15))
    elif name == "thermo":
        dressing(scene)
        living(scene)
        thermo_overlay(scene, 6)
        cam, tgt = camera(scene, "Cam", (-4.9, -6.5, 1.6), (-4.9, 0, 1.0), lens=24)
        key(cam, "location", 1, (-5.0, -6.5, 1.6))
        key(cam, "location", frames, (-0.4, -5.6, 1.5))
        key(tgt, "location", 1, (-5.0, 0, 1.0))
        key(tgt, "location", frames, (-0.6, 0, 0.8))
    elif name == "heater":
        grill, heater_light, (hx, hy) = dressing(scene)
        on = int(frames * 0.22)
        gs = glow_socket(grill)
        key_socket(gs, 1, 0.0, "CONSTANT")
        key_socket(gs, on, 0.0)
        key_socket(gs, on + 8, 7.0)
        key(heater_light.data, "energy", 1, 0.0, "CONSTANT")
        key(heater_light.data, "energy", on, 0.0)
        key(heater_light.data, "energy", on + 8, 25.0)
        warm = light(scene, "AREA", "RoomWarm", ((DRESS[0] + DRESS[1]) / 2, BACK_Y - 1.2, 1.2), 0.0, (1.0, 0.55, 0.25), size=2.0)
        key(warm.data, "energy", on, 0.0)
        key(warm.data, "energy", frames - 10, 140.0)
        cold = bpy.data.objects["DressLamp"]
        cold.data.color = (0.55, 0.7, 1.0)
        key(cold.data, "energy", on, 30.0)
        key(cold.data, "energy", frames - 10, 12.0)
        # 壁の温度計:10℃ → 20℃
        panel = box("ThermoPanel", (0.28, 0.02, 0.14), (DRESS[0] + 1.3, BACK_Y - 0.01, 1.6), principled("Panel", (0.05, 0.05, 0.06), rough=0.3))
        for label, col, show in (("10℃", (0.3, 0.6, 1.0), (1, int(frames * 0.6))), ("20℃", (1.0, 0.6, 0.2), (int(frames * 0.6), frames + 1))):
            t = text(scene, label, 0.08, glow(f"T{label}", col, 6.0), (DRESS[0] + 1.3, BACK_Y - 0.025, 1.6), (math.radians(90), 0, 0), jp=True)
            t.hide_render = True
            t.keyframe_insert("hide_render", frame=0)
            t.hide_render = False
            t.keyframe_insert("hide_render", frame=show[0])
            t.hide_render = True
            t.keyframe_insert("hide_render", frame=show[1])
        cam, tgt = camera(scene, "Cam", (hx + 0.5, hy - 1.9, 1.1), (hx - 0.2, BACK_Y - 0.6, 0.7), lens=26)
        key(cam, "location", 1, (hx + 0.6, hy - 2.0, 1.15))
        key(cam, "location", frames, (hx + 0.3, hy - 1.6, 1.0))
    elif name == "temp_timer":
        # 浮かぶ湯温計(41℃)と、ふちに置いたタイマー(10:00)
        body = principled("Floater", (0.95, 0.95, 0.95), rough=0.3, coat=0.6)
        fl = cyl("Floater", 0.1, 0.035, (-0.15, -0.05, WATER_Z + 0.01), body, bevel=0.01)
        lcd = principled("LCD", (0.6, 0.7, 0.62), rough=0.3)
        lcd_o = cyl("FloaterLCD", 0.075, 0.005, (-0.15, -0.05, WATER_Z + 0.03), lcd)
        t41 = text(scene, "41℃", 0.06, principled("LCDInk", (0.03, 0.03, 0.03), rough=0.5), (-0.15, -0.05, WATER_Z + 0.034), (0, 0, 0))
        for o in (lcd_o, t41):
            o.parent = fl
            o.location = (o.location.x + 0.15, o.location.y + 0.05, o.location.z - WATER_Z - 0.01)
        tm = box("Timer", (0.11, 0.05, 0.08), (0.2, -TUB_Y - 0.06, TUB_RIM + 0.04), principled("TimerBody", (0.95, 0.85, 0.2), rough=0.35), bevel=0.01)
        box("TimerLCD", (0.085, 0.004, 0.04), (0.2, -TUB_Y - 0.087, TUB_RIM + 0.045), lcd)
        text(scene, "10:00", 0.028, principled("LCDInk2", (0.03, 0.03, 0.03), rough=0.5), (0.2, -TUB_Y - 0.09, TUB_RIM + 0.045),
             (math.radians(90), 0, 0), jp=False)
        key(fl, "location", 1, (-0.15, -0.05, WATER_Z + 0.01))
        key(fl, "location", frames, (-0.1, -0.08, WATER_Z + 0.01))
        cam, tgt = camera(scene, "Cam", (0.0, -0.8, 0.95), (-0.02, -0.12, WATER_Z + 0.03), lens=34, fstop=4.0)
        key(cam, "location", 1, (0.05, -0.85, 0.98))
        key(cam, "location", frames, (-0.02, -0.72, 0.9))
    elif name == "handrail":
        arrow_mat = glow("Arrow", (0.3, 0.9, 1.0), 6.0)
        root = bpy.data.objects.new("Arrow", None)
        scene.collection.objects.link(root)
        box("ArrowShaft", (0.04, 0.01, 0.35), (0, 0, 0), arrow_mat).parent = root
        bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.09, depth=0.12, location=(0, 0, 0.22),
                                        rotation=(math.radians(90), 0, math.radians(90)))
        head = bpy.context.active_object
        assign(head, arrow_mat)
        head.rotation_euler = (math.radians(-90), 0, 0)
        head.parent = root
        key(root, "location", 1, (-0.3, -0.2, 0.55), "LINEAR")
        key(root, "location", frames, (-0.3, -0.2, 0.95), "LINEAR")  # ゆっくり上がる
        glow_rail = glow("RailGlow", (0.3, 0.9, 1.0), 0.0)
        for r in rails:  # 手すりをうっすら光らせて強調
            r.data.materials.append(glow_rail)
            for p in r.data.polygons:
                p.material_index = 1
        key_socket(glow_socket(glow_rail), 8, 0.0)
        key_socket(glow_socket(glow_rail), 20, 2.0)
        cam, tgt = camera(scene, "Cam", (0.6, -1.7, 1.1), (0.0, 0.1, 0.75), lens=30, fstop=5.0)
        key(cam, "location", 1, (0.7, -1.8, 1.15))
        key(cam, "location", frames, (0.5, -1.55, 1.05))
    elif name == "one_word":
        dressing(scene)
        bubble_mat = principled("Bubble", (0.98, 0.98, 0.98), rough=0.35, emission=0.6, emission_color=(1, 1, 1))
        root = bpy.data.objects.new("Speech", None)
        root.location = (DRESS[1] - 0.45, BACK_Y - 1.5, 1.55)
        scene.collection.objects.link(root)
        b = box("SpeechBox", (0.95, 0.06, 0.32), (0, 0, 0), bubble_mat, bevel=0.12)
        b.parent = root
        bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.08, depth=0.05, location=(0.25, 0, -0.2),
                                        rotation=(math.radians(90), 0, math.radians(180)))
        tail = bpy.context.active_object
        assign(tail, bubble_mat)
        tail.parent = root
        t = text(scene, "お風呂入るね", 0.12, principled("BubbleInk", (0.1, 0.1, 0.12), rough=0.5), (0, -0.035, 0), (math.radians(90), 0, 0))
        t.parent = root
        pop(root, 14)
        cam, tgt = camera(scene, "Cam", (DRESS[1] - 0.2, BACK_Y - 3.6, 1.4), (DRESS[1] - 0.4, BACK_Y - 1.2, 1.2), lens=30)
        key(cam, "location", 1, (DRESS[1] - 0.1, BACK_Y - 3.8, 1.45))
        key(cam, "location", frames, (DRESS[1] - 0.3, BACK_Y - 3.3, 1.35))
    return scene


if __name__ == "__main__":
    name, timings, sims, out = sys.argv[1:5]
    scene = build(name, timings, sims)
    frames = scene.frame_end
    glass = name in ("food", "bath", "temp_timer", "handrail", "heatshock")
    vb = 3 if name in STEAM_SHOTS else 0
    if "--preview" in sys.argv:
        render(scene, out, samples=12, scale=30, preview_frames=sorted({max(1, frames // 6), frames // 2, frames - 3}),
               bounces=10 if glass else None, volume_bounces=vb)
    else:
        render(scene, out, bounces=10 if glass else None, volume_bounces=vb)
