"""10カットの3D シーン。炎・煙は sims.py の結果(アトラス画像)をボリュームとして描画する。

使い方: python shots.py <カット名> <timings.json> <sims フォルダ> <出力フォルダ> [--preview]
"""
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "elevator_quake"))
sys.path.insert(0, str(HERE))

import bpy  # noqa: E402

from kit import (add_bump, assign, box, camera, color_variation, cyl, glow, glow_socket, key, key_socket,  # noqa: E402
                 light, metal, principled, render, reset_scene, shake, smooth, text)
from kitchen import OIL_Z, POT_H, POT_R, fire_light, kitchen, lathe, pot  # noqa: E402
from plan import SIM_OF, events, lid_z, windows  # noqa: E402
from volume import SCALES, atlas, domain_box, flame_curve, volume_material  # noqa: E402

# 炎がとても強いシミュレーションは、アトラスで白飛びしないよう範囲を広げる
SIM_SCALES = {"erupt": {**SCALES, "flame": 12.0, "temp": 12.0}, "spray": {**SCALES, "flame": 6.0}}
SIM_FLAME_K = {"erupt": 110.0, "spray": 120.0}
# 熱した油から出る煙は白っぽい灰色で濃い(発火前の「煙が出ている」状態を見せる)
SIM_SMOKE = {"heat": dict(smoke_k=160.0, smoke_color=(0.32, 0.31, 0.3)),
             "erupt": dict(smoke_k=9.0)}  # 火柱のあとの大量のすすで画面が真っ黒にならないよう薄めに  # 火柱は明るすぎて白飛びしやすいので、発光を抑えて炎の色を残す

RED_X = (1.0, 0.04, 0.03)


def add_fire(scene, sims, name, frames, light_k=14.0):
    """シミュレーション結果を読み込んで、炎・煙のボリュームと揺らめく光を置く。"""
    sim_dir = Path(sims) / name
    grid = json.loads((sim_dir / "grid.json").read_text())
    scales = SIM_SCALES.get(name, SCALES)
    info = atlas(sim_dir, Path(sims) / f"{name}_atlas", scales)
    first = sorted((Path(sims) / f"{name}_atlas").glob("f_*.png"))[0]
    mat = volume_material(f"Fire_{name}", first, info, scales=scales, flame_k=SIM_FLAME_K.get(name, 260.0),
                          **SIM_SMOKE.get(name, {}))
    domain_box(f"Fire_{name}", tuple(grid["shape"]), grid["h"], tuple(grid["origin"]), mat)
    curve = flame_curve(sim_dir)[:frames]
    fire_light(scene, (0, 0, 0.25), curve, light_k)
    return grid


def glass(scene):
    """水の入ったガラスのコップ。"""
    g = principled("Glass", (1, 1, 1), rough=0.02, transmission=1.0, ior=1.5)
    cup = lathe("Cup", [(0.0, 0.0), (0.032, 0.0), (0.036, 0.11), (0.033, 0.11), (0.029, 0.004), (0.0, 0.004)], g)
    water = principled("Water", (0.85, 0.95, 1.0), rough=0.02, transmission=1.0, ior=1.33)
    w = cyl("WaterIn", 0.03, 0.07, (0, 0, 0.04), water)
    w.parent = cup
    return cup, water


def red_x(scene, loc, size, start, rot=(math.radians(90), 0, 0)):
    mat = glow("RedX", RED_X, 10.0)
    root = bpy.data.objects.new("XRoot", None)
    root.location, root.rotation_euler = loc, rot
    scene.collection.objects.link(root)
    for a in (45, -45):
        bar = box(f"X{a}", (size, size * 0.13, 0.01), (0, 0, 0), mat, bevel=size * 0.03)
        bar.rotation_euler = (0, 0, math.radians(a))
        bar.parent = root
    key(root, "scale", 1, (0, 0, 0), "CONSTANT")
    key(root, "scale", start, (0.01, 0.01, 0.01))
    key(root, "scale", start + 6, (1.15, 1.15, 1.15))
    key(root, "scale", start + 10, (1, 1, 1))
    return root


def thermometer(scene, start_frame, end_frame):
    """鍋のふちに付けるダイヤル式の温度計。針が 180℃→370℃ に上がる。"""
    root = bpy.data.objects.new("Thermo", None)
    root.location = (-0.07, -POT_R - 0.02, POT_H + 0.06)
    root.rotation_euler = (math.radians(90), 0, math.radians(-12))
    scene.collection.objects.link(root)
    steel = metal("ThermoSteel", (0.75, 0.75, 0.77), rough=0.2, brushed=False)
    face = principled("DialFace", (0.95, 0.95, 0.93), rough=0.35)
    ink = principled("DialInk", (0.05, 0.05, 0.05), rough=0.4)
    redm = principled("DialRed", (0.8, 0.05, 0.04), rough=0.4)
    for o in (cyl("DialRim", 0.05, 0.016, (0, 0, 0), steel, bevel=0.003), cyl("DialFace", 0.045, 0.017, (0, 0, 0), face)):
        o.parent = root
    stem = cyl("Stem", 0.003, 0.16, (0, -0.08, -0.012), steel, rot=(math.radians(90), 0, 0), verts=16)
    stem.parent = root
    a0, a1 = math.radians(225), math.radians(-45)  # 0℃ と 400℃ の角度(時計回り)
    ang = lambda c: a0 + (a1 - a0) * c / 400.0
    for c in range(0, 401, 20):
        a = ang(c)
        long_tick = c % 100 == 0
        t = box(f"Tick{c}", (0.0025, 0.009 if long_tick else 0.005, 0.002),
                (0.037 * math.cos(a), 0.037 * math.sin(a), 0.0095), redm if c >= 300 else ink)
        t.rotation_euler.z = a - math.pi / 2
        t.parent = root
        if long_tick:
            lab = text(scene, str(c), 0.009, ink, (0.026 * math.cos(a), 0.026 * math.sin(a), 0.0096), (0, 0, 0), jp=False)
            lab.parent = root
    lab = text(scene, "℃", 0.01, ink, (0, -0.016, 0.0096), (0, 0, 0))
    lab.parent = root
    pivot = bpy.data.objects.new("NeedlePivot", None)
    scene.collection.objects.link(pivot)
    pivot.parent = root
    pivot.location = (0, 0, 0.011)
    needle = box("Needle", (0.034, 0.0025, 0.0015), (0.015, 0, 0), redm)
    needle.parent = pivot
    cyl("Hub", 0.004, 0.003, (0, 0, 0.011), ink).parent = root
    key(pivot, "rotation_euler", 1, (0, 0, ang(180)), "BEZIER")
    key(pivot, "rotation_euler", end_frame, (0, 0, ang(372)), "BEZIER")
    return root


def extinguisher(scene, nozzle, aim_at):
    """赤い粉末消火器(ラベルに 普通・油・電気 の丸いマーク)。本体は作業台の上、ホースの先をノズルの位置に。"""
    red = principled("ExtRed", (0.7, 0.02, 0.02), rough=0.25, coat=0.8)
    black = principled("ExtBlack", (0.02, 0.02, 0.02), rough=0.5)
    brass = metal("ExtValve", (0.3, 0.3, 0.32), rough=0.3, brushed=False)
    base = (0.52, -0.12, 0.0)
    body = lathe("ExtBody", [(0.0, 0.0), (0.065, 0.0), (0.07, 0.012), (0.07, 0.3), (0.058, 0.34), (0.022, 0.355),
                             (0.0, 0.355)], red)
    body.location = base
    cyl("Valve", 0.018, 0.04, (base[0], base[1], 0.375), brass)
    lever = box("Lever", (0.09, 0.02, 0.008), (base[0] - 0.02, base[1], 0.4), black, bevel=0.003)
    lever.rotation_euler.y = math.radians(12)
    # ラベル(白地に3つの丸:白=普通火災、黄=油火災、青=電気火災)
    white = principled("LabelWhite", (0.92, 0.92, 0.9), rough=0.5)
    lab_root = bpy.data.objects.new("Label", None)
    scene.collection.objects.link(lab_root)
    lab_root.location = (base[0], base[1] - 0.071, 0.17)
    lab_root.rotation_euler = (math.radians(90), 0, 0)
    box("LabelBase", (0.1, 0.16, 0.002), (0, 0, 0), white).parent = lab_root
    ink = principled("LabelInk", (0.05, 0.05, 0.05), rough=0.5)
    t = text(scene, "消火器", 0.022, principled("LabelRed", (0.75, 0.03, 0.03), rough=0.5), (0, 0.055, 0.0015), (0, 0, 0))
    t.parent = lab_root
    marks = [("普通", (0.97, 0.97, 0.95)), ("油", (1.0, 0.8, 0.0)), ("電気", (0.1, 0.35, 0.85))]
    for i, (label, col) in enumerate(marks):
        x = (i - 1) * 0.032
        cyl(f"Mark{i}", 0.014, 0.002, (x, 0.005, 0.0015), principled(f"Mark{label}", col, rough=0.4),
            rot=(0, 0, 0)).parent = lab_root
        cyl(f"MarkRim{i}", 0.0155, 0.0015, (x, 0.005, 0.0008), ink).parent = lab_root
        tt = text(scene, label, 0.009 if len(label) > 1 else 0.012, ink, (x, 0.005, 0.0032), (0, 0, 0))
        tt.parent = lab_root
    t2 = text(scene, "油火災に使えます", 0.009, ink, (0, -0.03, 0.0015), (0, 0, 0))
    t2.parent = lab_root
    # ホース(バルブからノズルへ)
    import mathutils
    d = mathutils.Vector(aim_at) - mathutils.Vector(nozzle)
    d.normalize()
    from kit import curve_tube
    start = (base[0] + 0.015, base[1], 0.375)
    back = tuple(n - 0.1 * c for n, c in zip(nozzle, d))
    curve_tube(scene, "Hose", [start, (base[0] + 0.05, base[1] - 0.12, 0.2), (back[0] + 0.05, back[1] - 0.05, back[2] - 0.12), back,
                               nozzle], 0.009, black)
    tip = cyl("Nozzle", 0.013, 0.07, nozzle, black)
    tip.rotation_mode = "QUATERNION"
    tip.rotation_quaternion = mathutils.Vector((0, 0, 1)).rotation_difference(d)
    return lab_root


def lid_obj(scene):
    alu = metal("LidAlu", (0.8, 0.8, 0.82), rough=0.25, brushed=False)
    lid = lathe("Lid", [(0.0, 0.03), (0.06, 0.026), (0.12, 0.01), (POT_R + 0.016, 0.0), (POT_R + 0.016, 0.004),
                        (0.12, 0.014), (0.06, 0.03), (0.0, 0.034)], alu)
    knob = cyl("LidKnob", 0.018, 0.022, (0, 0, 0.045), principled("Bakelite", (0.03, 0.03, 0.03), rough=0.4), bevel=0.004)
    knob.parent = lid
    return lid


def stove_knob(scene):
    k = cyl("StoveKnob", 0.022, 0.02, (0.2, -0.235, 0.012), principled("KnobBlack", (0.03, 0.03, 0.03), rough=0.35),
            rot=(math.radians(90), 0, 0), bevel=0.004)
    mark = box("KnobMark", (0.004, 0.003, 0.016), (0.2, -0.247, 0.02), principled("KnobMarkWhite", (0.9, 0.9, 0.9)))
    mark.parent = k
    mark.location = (0, 0.008, -0.012)
    return k


def mayo_bottle(scene, loc):
    """マヨネーズの容器(やわらかいボトル+赤いキャップ)。"""
    body_mat = principled("MayoBottle", (1.0, 0.92, 0.6), rough=0.3, transmission=0.2, sss=0.6, sss_scale=0.02)
    body = lathe("Mayo", [(0.0, 0.0), (0.03, 0.0), (0.034, 0.02), (0.036, 0.13), (0.03, 0.16), (0.012, 0.175),
                          (0.0, 0.175)], body_mat)
    body.location = loc
    cap = cyl("MayoCap", 0.014, 0.03, (loc[0], loc[1], loc[2] + 0.19), principled("MayoCap", (0.8, 0.05, 0.05), rough=0.35))
    cyl("MayoTip", 0.006, 0.02, (loc[0], loc[1], loc[2] + 0.212), principled("MayoCap2", (0.8, 0.05, 0.05), rough=0.35))
    lab = box("MayoLabel", (0.07, 0.002, 0.05), (loc[0], loc[1] - 0.036, loc[2] + 0.08),
              principled("MayoLabelPaper", (0.95, 0.95, 0.93), rough=0.5))
    t = text(scene, "マヨネーズ", 0.011, principled("MayoInk", (0.75, 0.05, 0.05), rough=0.5),
             (loc[0], loc[1] - 0.038, loc[2] + 0.08), (math.radians(90), 0, 0))
    return body


def shrimp(scene, loc, rot_z):
    """えび天:曲がった体に衣のでこぼこ、赤いしっぽ。"""
    batter = principled("TempuraBatter", (0.9, 0.58, 0.18), rough=0.55, sss=0.3, sss_scale=0.01)
    add_bump(batter, scale=60, strength=0.9)  # 衣のでこぼこ
    add_bump(batter, scale=200, strength=0.5)
    from kit import curve_tube
    pts = [(-0.06, 0.0, 0.0), (-0.02, 0.012, 0.004), (0.03, 0.006, 0.006), (0.06, -0.012, 0.002)]
    body, sp = curve_tube(scene, "Shrimp", pts, 0.018, batter)
    sp.points[0].radius = 0.6
    tail = bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.012, depth=0.02, location=(0.072, -0.016, 0.004),
                                           rotation=(0, math.radians(90), 0))
    t = bpy.context.active_object
    assign(t, principled("ShrimpTail", (0.85, 0.2, 0.08), rough=0.4))
    t.scale.y = 0.4
    root = bpy.data.objects.new("ShrimpRoot", None)
    scene.collection.objects.link(root)
    body.parent = root
    t.parent = root
    root.location = loc
    root.rotation_euler.z = rot_z
    return root


def bubbles(scene, frames, count=60, region=0.09):
    """揚げ油の細かい泡(下から湧いて油面ではじける)。"""
    rnd = random.Random(3)
    mat = principled("Bubble", (1, 0.95, 0.8), rough=0.05, transmission=1.0, ior=1.2)
    for i in range(count):
        a, r = rnd.uniform(0, math.tau), region * math.sqrt(rnd.random())
        x, y = r * math.cos(a), r * math.sin(a)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rnd.uniform(0.002, 0.005), location=(x, y, OIL_Z), segments=12, ring_count=8)
        b = bpy.context.active_object
        assign(b, mat)
        period = rnd.randint(8, 18)
        off = rnd.randint(0, period)
        for fr in range(1, frames + 1, 2):
            ph = ((fr + off) % period) / period
            b.scale = (1, 1, 1) if ph < 0.85 else (0.01, 0.01, 0.01)
            b.keyframe_insert("scale", frame=fr)
            b.location = (x + 0.004 * math.sin(fr * 0.7 + i), y, OIL_Z + 0.001 + 0.003 * ph)
            b.keyframe_insert("location", frame=fr)


def cutaway(scene, frames):
    """断面:半分に切った鍋と油。水滴が沈み、一気に水蒸気の泡になって油を押しのける。"""
    body, oil = pot(scene)
    oil.hide_render = True
    cutter = box("Cutter", (0.6, 0.3, 0.6), (0, -0.15, 0.05), principled("CutterMat", (1, 1, 1)))
    cutter.hide_render = True
    m = body.modifiers.new("cut", "BOOLEAN")
    m.object, m.operation = cutter, "DIFFERENCE"
    # 油(断面が見える半円柱)
    oil_mat = principled("HotOil", (0.85, 0.5, 0.08), rough=0.05, transmission=0.6, ior=1.47, sss=0.5,
                         sss_radius=(1.0, 0.6, 0.2), sss_scale=0.05, emission=0.15, emission_color=(1.0, 0.5, 0.1))
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=POT_R - 0.006, depth=OIL_Z - 0.006, location=(0, 0, (OIL_Z + 0.006) / 2))
    oil_vol = bpy.context.active_object
    m2 = oil_vol.modifiers.new("cut", "BOOLEAN")
    m2.object, m2.operation = cutter, "DIFFERENCE"
    assign(oil_vol, oil_mat)
    light(scene, "AREA", "Key", (-0.4, -0.6, 0.5), 25, (1.0, 0.9, 0.8), size=0.5, look_at=(0, 0, 0.04))
    light(scene, "AREA", "Rim", (0.4, 0.4, 0.4), 18, (1.0, 0.6, 0.3), size=0.4, look_at=(0, 0, 0.05))
    # 水滴 → 水蒸気の泡
    water = principled("Drop", (0.7, 0.85, 1.0), rough=0.02, transmission=1.0, ior=1.33)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.006, location=(0.01, -0.005, 0.2))
    drop = bpy.context.active_object
    smooth(drop)
    assign(drop, water)
    t_in, t_bottom, t_boom = 8, 30, 46
    key(drop, "location", 1, (0.01, -0.005, 0.2), "LINEAR")
    key(drop, "location", t_in, (0.01, -0.005, OIL_Z), "BEZIER")
    key(drop, "location", t_bottom, (0.01, -0.005, 0.012), "BEZIER")
    key(drop, "scale", t_boom - 1, (1, 1, 1), "CONSTANT")
    key(drop, "scale", t_boom, (0, 0, 0), "CONSTANT")
    steam = principled("Steam", (1, 1, 1), rough=0.05, transmission=0.85, ior=1.0, alpha=0.6)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.006, location=(0.01, -0.005, 0.012), segments=48, ring_count=24)
    bub = bpy.context.active_object
    smooth(bub)
    assign(bub, steam)
    key(bub, "scale", 1, (0, 0, 0), "CONSTANT")
    key(bub, "scale", t_boom, (1, 1, 1), "BEZIER")
    key(bub, "location", t_boom, (0.01, -0.005, 0.012), "BEZIER")
    key(bub, "scale", t_boom + 12, (8, 8, 8), "BEZIER")  # 一気にふくらむ(実際の体積は約1700倍)
    key(bub, "location", t_boom + 12, (0.0, -0.005, 0.045), "BEZIER")
    key(bub, "scale", t_boom + 20, (10, 10, 10), "BEZIER")
    key(bub, "location", t_boom + 20, (0.0, -0.005, 0.085), "BEZIER")  # 油面を突き破る
    key(bub, "scale", t_boom + 26, (0, 0, 0), "BEZIER")
    # 押しのけられて飛び散る油
    rnd = random.Random(5)
    drop_mat = principled("OilDrop", (0.9, 0.55, 0.1), rough=0.05, transmission=0.5, ior=1.47, emission=0.5,
                          emission_color=(1.0, 0.5, 0.1))
    for i in range(70):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rnd.uniform(0.002, 0.006), location=(0, 0, OIL_Z), segments=12, ring_count=8)
        d = bpy.context.active_object
        smooth(d)
        assign(d, drop_mat)
        a = rnd.uniform(0, math.pi)  # 手前(断面側)には飛ばさない
        sp = rnd.uniform(0.3, 0.9)
        t0 = t_boom + rnd.randint(4, 12)
        x0 = rnd.uniform(-0.08, 0.08)
        key(d, "scale", 1, (0, 0, 0), "CONSTANT")
        key(d, "scale", t0, (1, 1, 1), "CONSTANT")
        key(d, "location", t0, (x0, 0.02, OIL_Z), "LINEAR")
        dur = (frames - t0) / 24 * 0.5
        for k in range(1, 6):
            tt = dur * k / 5
            key(d, "location", t0 + int((frames - t0) * k / 5),
                (x0 + sp * math.cos(a) * tt, 0.02 + sp * math.sin(a) * tt * 0.5, OIL_Z + 1.6 * sp * tt - 4.9 * tt * tt), "LINEAR")
    return drop, bub


def build(name, timings, sims):
    win = windows(timings)
    frames = win[name][1]
    ev = events({k: v[1] for k, v in win.items()})
    scene = reset_scene(frames)
    import os
    scene.cycles.volume_step_rate = float(os.environ.get("VOLUME_STEP", 1.0))  # 大きいほど速いが粗い

    if name == "section":
        kitchen(scene, with_burner=False)  # 断面の鍋の中にバーナーが見えないように
        cutaway(scene, frames)
        cam, tgt = camera(scene, "Cam", (0.0, -0.5, 0.1), (0, 0, 0.06), lens=60, fstop=5.0)
        key(cam, "location", 1, (0.02, -0.55, 0.11))
        key(cam, "location", frames, (-0.01, -0.45, 0.09))
        return scene

    gas = kitchen(scene, gas_on=name not in ("outro",) or True)
    body, oil = pot(scene)
    if name in SIM_OF:
        add_fire(scene, sims, SIM_OF[name], frames)

    if name == "hook":
        cup, _ = glass(scene)
        cup.rotation_euler = (0, math.radians(-10), 0)
        key(cup, "location", 1, (0.62, -0.12, 0.42))
        key(cup, "location", frames, (0.26, -0.06, 0.36))
        key(cup, "rotation_euler", 1, (0, math.radians(-5), 0))
        key(cup, "rotation_euler", frames, (0, math.radians(-35), 0))
        cam, tgt = camera(scene, "Cam", (0.45, -1.15, 0.45), (0.05, 0, 0.3), lens=32, fstop=5.0)
        key(cam, "location", 1, (0.5, -1.25, 0.5))
        key(cam, "location", frames, (0.3, -0.95, 0.4))
    elif name == "erupt":
        cup, _ = glass(scene)
        cup.location = (0.2, -0.05, 0.3)
        key(cup, "rotation_euler", 1, (0, math.radians(-35), 0))
        key(cup, "rotation_euler", ev["erupt_pour"], (0, math.radians(-110), 0))
        key(cup, "location", ev["erupt_burst"] + 2, (0.2, -0.05, 0.3))
        key(cup, "location", ev["erupt_burst"] + 14, (0.75, -0.3, 0.6))  # 爆発で吹き飛ばされる
        water = principled("PourWater", (0.85, 0.95, 1.0), rough=0.02, transmission=1.0, ior=1.33)
        rnd = random.Random(2)
        for i in range(24):  # 注がれた水の粒
            bpy.ops.mesh.primitive_uv_sphere_add(radius=rnd.uniform(0.004, 0.009), location=(0.14, -0.05, 0.27))
            d = bpy.context.active_object
            smooth(d)
            assign(d, water)
            t0 = ev["erupt_pour"] + i * 0.25
            key(d, "scale", 1, (0, 0, 0), "CONSTANT")
            key(d, "scale", int(t0), (1, 1, 1), "CONSTANT")
            key(d, "location", int(t0), (0.14 + rnd.uniform(-0.01, 0.01), -0.05, 0.27), "LINEAR")
            key(d, "location", int(t0) + 5, (0.05 + rnd.uniform(-0.02, 0.02), -0.03, OIL_Z), "LINEAR")
            key(d, "scale", int(t0) + 6, (0, 0, 0), "CONSTANT")
        cam, tgt = camera(scene, "Cam", (0.25, -2.0, 0.55), (0, 0, 0.72), lens=26)
        shake(cam, ev["erupt_burst"] + 1, frames, 0.03, (0.25, -2.0, 0.55), every=2, decay=True, seed=2)
    elif name == "spray":
        sim_dir = Path(sims) / "spray"
        track = json.loads((sim_dir / "droplets.json").read_text())
        mat = principled("BurningDrop", (1.0, 0.6, 0.15), rough=0.1, emission=6.0, emission_color=(1.0, 0.55, 0.15))
        objs, last = {}, {}
        for fr_s, items in track.items():
            for i, x, y, z, r in items:
                if i not in objs:
                    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=16, ring_count=8)
                    o = bpy.context.active_object
                    smooth(o)
                    assign(o, mat)
                    o.scale = (0, 0, 0)
                    o.keyframe_insert("scale", frame=1)
                    objs[i] = o
                o = objs[i]
                o.location = (x, y, z)
                o.keyframe_insert("location", frame=int(fr_s))
                o.scale = (1, 1, 1)
                o.keyframe_insert("scale", frame=int(fr_s))
                last[i] = max(last.get(i, 0), int(fr_s))
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "CONSTANT"
        for i, fr_last in last.items():  # 着地したら(最後に記録されたフレームの次から)消す
            objs[i].scale = (0, 0, 0)
            objs[i].keyframe_insert("scale", frame=fr_last + 1)
        cam, tgt = camera(scene, "Cam", (0.35, -1.3, 0.4), (0, 0, 0.32), lens=28)
        key(cam, "location", 1, (0.4, -1.35, 0.42))
        key(cam, "location", frames, (0.2, -1.1, 0.36))
    elif name == "heat":
        thermometer(scene, 1, ev["heat_ignite"])
        cam, tgt = camera(scene, "Cam", (0.18, -0.62, 0.3), (-0.04, -0.06, 0.14), lens=42, fstop=3.5)
        key(cam, "location", 1, (0.2, -0.66, 0.3))
        key(cam, "location", frames, (0.25, -0.75, 0.36))
    elif name == "unattended":
        box("Phone", (0.075, 0.155, 0.008), (-0.75, -0.12, 0.004), principled("PhoneBlack", (0.02, 0.02, 0.025), rough=0.1, coat=1.0), bevel=0.006)
        cam, tgt = camera(scene, "Cam", (-0.75, -2.1, 0.8), (0, 0, 0.45), lens=24)
        key(cam, "location", 1, (-0.8, -2.2, 0.85))
        key(cam, "location", frames, (-0.6, -1.9, 0.75))
    elif name == "extinguisher":
        nozzle = (0.36, -0.3, 0.36)
        label = extinguisher(scene, nozzle, (0, 0, 0.1))
        cam, tgt = camera(scene, "Cam", (0.5, -0.38, 0.19), (0.52, -0.19, 0.17), lens=50, fstop=2.8)
        sp = ev["ext_spray"]
        key(cam, "location", 1, (0.52, -0.42, 0.18))
        key(cam, "location", sp - 10, (0.52, -0.4, 0.18))
        key(tgt, "location", sp - 10, (0.52, -0.19, 0.17))
        key(cam, "location", sp + 6, (0.3, -1.25, 0.45))
        key(tgt, "location", sp + 6, (0.12, -0.1, 0.25))
        key(cam, "location", frames, (0.25, -1.15, 0.42))
    elif name == "lid":
        knob = stove_knob(scene)
        key(knob, "rotation_euler", ev["lid_knob"], (math.radians(90), 0, 0))
        key(knob, "rotation_euler", ev["lid_knob"] + 6, (math.radians(90), math.radians(-90), 0))
        if gas is not None:
            key_socket(glow_socket(gas), ev["lid_knob"] + 3, 8.0, "CONSTANT")
            key_socket(glow_socket(gas), ev["lid_knob"] + 4, 0.0, "CONSTANT")
        lid = lid_obj(scene)
        for fr in range(1, frames + 1):
            lid.location = (0, 0, lid_z(fr, ev))
            lid.keyframe_insert("location", frame=fr)
        cam, tgt = camera(scene, "Cam", (0.38, -0.95, 0.38), (0.04, 0, 0.16), lens=34, fstop=5.0)
        key(cam, "location", 1, (0.42, -1.0, 0.4))
        key(cam, "location", frames, (0.3, -0.85, 0.32))
    elif name == "mayo":
        bottle = mayo_bottle(scene, (-0.32, -0.12, 0.0))
        red_x(scene, (-0.32, -0.2, 0.1), 0.2, 22)
        cam, tgt = camera(scene, "Cam", (-0.42, -0.9, 0.32), (-0.18, 0, 0.18), lens=34, fstop=4.0)
        key(cam, "location", 1, (-0.45, -0.95, 0.34))
        key(cam, "location", frames, (-0.38, -0.82, 0.3))
    elif name == "outro":
        for l in ("CeilingLight", "Window"):  # 落ち着いた普段の台所の明るさ
            bpy.data.objects[l].data.energy *= 3.0
        for i, (x, y, rz) in enumerate([(-0.04, 0.03, 0.4), (0.04, -0.03, -0.3), (0.0, 0.05, 2.6)]):
            shrimp(scene, (x, y, OIL_Z + 0.004), rz)
        bubbles(scene, frames)
        cam, tgt = camera(scene, "Cam", (0.3, -0.7, 0.42), (0, 0, 0.08), lens=40, fstop=3.0)
        key(cam, "location", 1, (0.38, -0.72, 0.45))
        key(cam, "location", frames, (0.15, -0.72, 0.4))
    return scene


if __name__ == "__main__":
    name, timings, sims, out = sys.argv[1:5]
    scene = build(name, timings, sims)
    frames = scene.frame_end
    if "--preview" in sys.argv:
        render(scene, out, samples=12, scale=30, preview_frames=sorted({max(1, frames // 6), frames // 2, frames - 3}),
               bounces=10)
    else:
        render(scene, out, bounces=10 if name in ("hook", "erupt", "section", "outro") else None)  # ガラス・水・油が重なる場面だけ
