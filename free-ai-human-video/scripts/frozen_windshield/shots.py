"""12カットの 3D シーン。霜は maps.py のマップ、湯気は sims.py の結果(アトラス画像)を使う。

使い方: python shots.py <カット名> <作業フォルダ> <出力フォルダ> [--preview]
  作業フォルダ: timings.json、maps/、sims/、hdri/(Poly Haven の HDRI・CC0)
"""
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tempura_fire"))
sys.path.insert(0, str(HERE.parent / "elevator_quake"))
sys.path.insert(0, str(HERE))

import bpy  # noqa: E402
import mathutils  # noqa: E402
import numpy as np  # noqa: E402

import car as C  # noqa: E402
from kit import add_bump, assign, box, camera, curve_tube, cyl, glow, key, light, metal, principled, render, reset_scene, smooth, text  # noqa: E402
from kitchen import lathe  # noqa: E402
from plan import IMPACT, SPOUT_TIP, stream_points, to_uv, windows, ws_normal, ws_point  # noqa: E402
from sims import KETTLE_SPOUT_MORNING  # noqa: E402
from volume import SCALES, atlas, domain_box, volume_material  # noqa: E402

WORK = None


def steam(name, k=30.0, start=1):
    d = WORK / "sims" / name
    if not (d / "grid.json").exists():   # 試し描きでシミュレーションがまだ無いとき
        print("no steam yet:", name)
        return
    grid = json.loads((d / "grid.json").read_text())
    info = atlas(d, WORK / "sims" / f"{name}_atlas")
    first = sorted((WORK / "sims" / f"{name}_atlas").glob("f_*.png"))[0]
    mat = volume_material(f"Steam{name}", first, info, smoke_k=k, flame_k=0.0, smoke_color=(0.95, 0.96, 0.98), scales=SCALES,
                          absorption=(0.97, 0.97, 0.97))
    box_ = domain_box(f"Steam{name}", tuple(grid["shape"]), grid["h"], tuple(grid["origin"]), mat)
    if start > 1:   # 途中から湯気を出す:連番の開始をずらし、それまでは隠す
        for nd in mat.node_tree.nodes:
            if nd.type == "TEX_IMAGE":
                nd.image_user.frame_start = start
        box_.hide_render = True
        box_.keyframe_insert("hide_render", frame=1)
        box_.hide_render = False
        box_.keyframe_insert("hide_render", frame=start)


def frost(melt=None, freeze=None, cover=1.0):
    mp = lambda n: WORK / "maps" / f"{n}.png" if n else None
    return C.frost_material("Frost", mp(melt), mp(freeze), cover=cover)


def outdoor(scene, sun_az=-60, strength=1.0, hdri="passendorf_snow", sun=3.0):
    lamp, bg, mix = C.world_hdri(scene, hdri, strength, sun_az=sun_az, sun=sun)
    C.snow_ground(scene)
    return lamp, bg, mix


# ---------------------------------------------------------------- 小物
def kettle(scene, tip_world, tilt_deg=40.0, yaw_deg=180.0):
    """ステンレスのやかん。注ぎ口の先が tip_world に来るように置く。"""
    steel = metal("KettleSteel", (0.86, 0.86, 0.88), rough=0.12, brushed=False)
    black = principled("KettleHandle", (0.02, 0.02, 0.02), rough=0.45)
    root = bpy.data.objects.new("Kettle", None)
    scene.collection.objects.link(root)
    prof = [(0.0, 0.0), (0.08, 0.0), (0.098, 0.012), (0.106, 0.06), (0.098, 0.12), (0.075, 0.155), (0.05, 0.168),
            (0.05, 0.172), (0.0, 0.172)]
    body = lathe("KettleBody", prof, steel)
    body.parent = root
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.016, location=(0, 0, 0.18))
    knob = bpy.context.active_object
    smooth(knob)
    assign(knob, black)
    knob.parent = root
    sp, _ = curve_tube(scene, "Spout", [(0.08, 0, 0.04), (0.13, 0, 0.08), (0.17, 0, 0.14), (0.2, 0, 0.17)], 0.016, steel,
                       order=3, taper=0.55)
    sp.parent = root
    hd, _ = curve_tube(scene, "Handle", [(-0.07, 0, 0.15), (-0.06, 0, 0.27), (0.04, 0, 0.27), (0.05, 0, 0.16)], 0.012, black,
                       order=3)
    hd.parent = root
    root.rotation_euler = (0, math.radians(tilt_deg), math.radians(yaw_deg))
    R = root.rotation_euler.to_matrix()
    tip_local = mathutils.Vector((0.203, 0, 0.172))
    root.location = mathutils.Vector(tip_world) - R @ tip_local
    return root


def droplets(scene, frames, n=36, seed=3):
    """お湯がガラスに当たって跳ねるしずく。"""
    rnd = random.Random(seed)
    mat = C.water_material("Drop")
    p0 = np.array(ws_point(*IMPACT))
    nrm = ws_normal(*IMPACT)
    g = np.array([0, 0, -9.8])
    for i in range(n):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rnd.uniform(0.0015, 0.004), segments=12, ring_count=8, location=p0)
        o = bpy.context.active_object
        smooth(o)
        assign(o, mat)
        life = rnd.uniform(6, 12)
        t0 = rnd.uniform(-life, frames)
        ang = rnd.uniform(0, math.tau)
        tang = np.array([math.cos(ang), math.sin(ang), 0.0])
        tang -= nrm * tang.dot(nrm)
        vel = tang * rnd.uniform(0.4, 1.1) + nrm * rnd.uniform(0.3, 0.9)
        for fr in range(1, frames + 1, 1):
            age = (fr - t0) % (life + 4)
            alive = age < life
            t = age / 24 * 0.8
            pos = p0 + vel * t + 0.5 * g * t * t
            key(o, "location", fr, tuple(pos), "LINEAR")
            key(o, "scale", fr, (1, 1, 1) if alive else (0, 0, 0), "CONSTANT")


def key_socket_val(sock, fr, val, interp="BEZIER"):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    sock.default_value = val
    sock.keyframe_insert("default_value", frame=fr)


def stopwatch(scene, loc, frames):
    """クロームのストップウォッチ。文字盤を上に向けて置き、針が1周(=1分)する。"""
    root = bpy.data.objects.new("Stopwatch", None)
    root.location = loc
    root.rotation_euler = (math.radians(4), 0, math.radians(8))
    scene.collection.objects.link(root)
    chrome = metal("SWChrome", (0.88, 0.88, 0.9), rough=0.08, brushed=False)
    face = principled("SWFace", (0.95, 0.95, 0.93), rough=0.35)
    ink = principled("SWInk", (0.02, 0.02, 0.025), rough=0.5)
    parts = [cyl("SWBody", 0.05, 0.018, (0, 0, 0), chrome, bevel=0.006),
             cyl("SWFace", 0.043, 0.002, (0, 0, 0.0095), face),
             cyl("SWGlass", 0.044, 0.003, (0, 0, 0.0115), principled("SWGlassM", (1, 1, 1), rough=0.0, transmission=1.0, ior=1.5)),
             cyl("SWStem", 0.006, 0.014, (0, 0.056, 0), chrome, rot=(math.radians(90), 0, 0)),
             cyl("SWCrown", 0.009, 0.006, (0, 0.066, 0), chrome, rot=(math.radians(90), 0, 0))]
    bpy.ops.mesh.primitive_torus_add(major_radius=0.013, minor_radius=0.0025, location=(0, 0.078, 0), rotation=(0, math.radians(90), 0))
    ring = bpy.context.active_object
    assign(ring, chrome)
    parts.append(ring)
    for i in range(60):
        a = i / 60 * math.tau
        big = i % 5 == 0
        r = 0.038
        t = box(f"Tick{i}", (0.0008 if not big else 0.0014, 0.004 if not big else 0.007, 0.0006),
                (r * math.sin(a), r * math.cos(a), 0.0108), ink)
        t.rotation_euler = (0, 0, -a)
        parts.append(t)
    for i in range(1, 13):
        a = i / 12 * math.tau
        parts.append(text(scene, str(i * 5), 0.0055, ink, (0.029 * math.sin(a), 0.029 * math.cos(a), 0.0108), jp=False))
    hand_root = bpy.data.objects.new("Hand", None)
    hand_root.location = (0, 0, 0.0112)
    scene.collection.objects.link(hand_root)
    hand = box("HandBar", (0.0011, 0.042, 0.0006), (0, 0.014, 0), principled("HandRed", (0.85, 0.05, 0.03), rough=0.4))
    hand.parent = hand_root
    cyl("HandCap", 0.002, 0.001, (0, 0, 0.0004), chrome).parent = hand_root
    parts.append(hand_root)
    for p in parts:
        p.parent = root
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
    hand_root.rotation_euler = (0, 0, 0)
    hand_root.keyframe_insert("rotation_euler", frame=8)
    hand_root.rotation_euler = (0, 0, -math.tau)
    hand_root.keyframe_insert("rotation_euler", frame=frames - 18)
    return root


def studio(scene):
    """暗い背景のスタジオ(ガラスの断面の説明用)。"""
    w = scene.world.node_tree.nodes["Background"]
    w.inputs["Color"].default_value = (0.02, 0.025, 0.035, 1)
    w.inputs["Strength"].default_value = 1.0
    floor = principled("StudioFloor", (0.03, 0.035, 0.045), rough=0.35)
    box("Floor", (6, 6, 0.01), (0, 0, -0.08), floor)
    light(scene, "AREA", "Key", (-0.5, -0.6, 0.8), 18, (1.0, 0.97, 0.92), size=0.8, look_at=(0, 0, 0))
    light(scene, "AREA", "Rim", (0.6, 0.6, 0.4), 25, (0.6, 0.8, 1.0), size=0.6, look_at=(0, 0, 0))
    light(scene, "AREA", "Under", (0, -0.4, -0.05), 6, (0.6, 0.8, 1.0), size=0.6, look_at=(0, 0, 0))


def glass_sample(scene, thermal, frames):
    """合わせガラスの切れ端(厚みは見やすいよう誇張):上のガラス・中間膜・下のガラス。"""
    glass_m = principled("SampleGlass", (0.82, 0.95, 0.9), rough=0.02, transmission=1.0, ior=1.52)
    pvb = principled("PVB", (0.85, 0.9, 0.92), rough=0.25, transmission=0.6, sss=0.4, sss_scale=0.01)
    L, Wd = 0.36, 0.22
    top = box("TopGlass", (L, Wd, 0.022), (0, 0, 0.0165), glass_m, bevel=0.002)
    mid = box("PVBLayer", (L, Wd, 0.011), (0, 0, 0.0), pvb, bevel=0.001)
    bot = box("BottomGlass", (L, Wd, 0.022), (0, 0, -0.0165), glass_m, bevel=0.002)
    for o in (top, mid, bot):
        sub = o.modifiers.new("sub", "SUBSURF")
        sub.levels = sub.render_levels = 4
        sub.subdivision_type = "SIMPLE"
    fm, ctrl = C.frost_material("SampleFrost", cover=0.9 if not thermal else 0.0)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=40, y_subdivisions=24, size=1, location=(0, 0, 0.0285))
    fr = bpy.context.active_object
    fr.scale = (L, Wd, 1)
    assign(fr, fm)
    if not thermal:
        return top, mid, bot
    # お湯 → 上のガラスの表面だけが熱くなる(赤い発光が上から少しだけしみ込む)
    tn = top.data.materials[0].copy()
    tn.name = "TopGlassHot"
    top.data.materials.clear()
    top.data.materials.append(tn)
    n, l = tn.node_tree.nodes, tn.node_tree.links
    b = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ")
    l.new(tc.outputs["Object"], sep.inputs["Vector"])
    depth = n.new("ShaderNodeMapRange")       # 上面(z=0.0275)からの深さを 0〜1 に
    depth.inputs["From Min"].default_value, depth.inputs["From Max"].default_value = 0.0275, 0.0055
    l.new(sep.outputs["Z"], depth.inputs["Value"])
    heat = n.new("ShaderNodeValue")
    heat.outputs[0].default_value = 0.0
    sub_ = n.new("ShaderNodeMath")
    sub_.operation, sub_.use_clamp = "SUBTRACT", True
    l.new(heat.outputs[0], sub_.inputs[0])
    l.new(depth.outputs["Result"], sub_.inputs[1])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].color = (1.0, 0.25, 0.05, 1)
    ramp.color_ramp.elements[1].position = 0.35
    l.new(sub_.outputs[0], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 3.0
    C.key_value(heat.outputs[0], 18, 0.0)
    C.key_value(heat.outputs[0], frames - 20, 0.75)
    cold = principled("BottomCold", (0.82, 0.95, 0.9), rough=0.02, transmission=1.0, ior=1.52, emission=0.6,
                      emission_color=(0.1, 0.35, 1.0))
    bot.data.materials.clear()
    bot.data.materials.append(cold)
    # 熱いお湯の筋
    water = C.water_material("SampleWater")
    st, _ = curve_tube(scene, "SampleStream", [(0.0, 0.0, 0.32), (0.0, 0.0, 0.15), (0.0, 0.0, 0.03)], 0.006, water, order=3, taper=0.8)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.04, location=(0, 0, 0.026))
    puddle = bpy.context.active_object
    puddle.scale = (1.8, 1.2, 0.04)
    assign(puddle, water)
    key(puddle, "scale", 6, (0.3, 0.3, 0.04))
    key(puddle, "scale", 40, (3.6, 2.4, 0.04))
    # 表面だけがふくらむ → 全体がそる(ゆがみ)。頂点を直接動かすシェイプキーで曲げる
    R = 0.36 / math.radians(22)
    for o, stretch in ((top, 1.04), (mid, 1.0), (bot, 1.0)):
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.modifier_apply(modifier="sub")
        o.shape_key_add(name="Basis")
        sk = o.shape_key_add(name="Bend")
        for v, kv in zip(o.data.vertices, sk.data):
            x, y, z = v.co
            th = x * stretch / R
            kv.co = ((R + z) * math.sin(th), y, (R + z) * math.cos(th) - R)
        sk.value = 0.0
        sk.keyframe_insert("value", frame=30)
        sk.value = 1.0
        sk.keyframe_insert("value", frame=frames - 15)
    arrow = glow("Expand", (1.0, 0.6, 0.15), 6.0)
    for s_ in (-1, 1):
        a = box(f"Arr{s_}", (0.05, 0.004, 0.004), (s_ * 0.215, -0.115, 0.03), arrow)
        bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.01, depth=0.016, location=(s_ * 0.245, -0.115, 0.03),
                                        rotation=(0, s_ * math.radians(90), 0))
        hd = bpy.context.active_object
        assign(hd, arrow)
        for o in (a, hd):
            key(o, "scale", 1, (0, 0, 0), "CONSTANT")
            key(o, "scale", 34, (0.01, 0.01, 0.01))
            key(o, "scale", 42, (1, 1, 1))
            key(o, "location", 42, tuple(o.location))
            key(o, "location", frames - 15, tuple(o.location + mathutils.Vector((s_ * 0.02, 0, 0.02))))
    return top, mid, bot


def spray_can(scene):
    """解氷スプレーの缶と、噴き出す霧(ボリューム)。can の -Z が噴射方向。"""
    root = bpy.data.objects.new("Can", None)
    scene.collection.objects.link(root)
    blue = principled("CanBlue", (0.05, 0.25, 0.75), rough=0.25, coat=0.8)
    blue.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.5
    white = principled("CanWhite", (0.92, 0.93, 0.95), rough=0.3, coat=0.6)
    body = cyl("CanBody", 0.033, 0.19, (0, 0.11, 0.0), blue, rot=(math.radians(90), 0, 0), bevel=0.004)
    band = cyl("CanBand", 0.0335, 0.07, (0, 0.11, 0.0), white, rot=(math.radians(90), 0, 0))
    lab = text(scene, "解氷", 0.03, principled("CanInk", (0.05, 0.25, 0.75), rough=0.4), (0, 0.11, 0.034), (0, 0, math.radians(90)))
    cap = cyl("CanCap", 0.024, 0.03, (0, 0.0, 0.0), white, rot=(math.radians(90), 0, 0))
    nozzle = cyl("Nozzle", 0.004, 0.012, (0, -0.005, -0.012), principled("NozzleBlack", (0.02, 0.02, 0.02), rough=0.5))
    for p in (body, band, lab, cap, nozzle):
        p.parent = root
    # 霧:先が広がる円すいに、ノイズで濃淡を付けたボリューム
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.08, radius2=0.004, depth=0.2, location=(0, 0, -0.11))
    mist = bpy.context.active_object
    mist.parent = root
    mat = bpy.data.materials.new("Mist")
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    n, l = mat.node_tree.nodes, mat.node_tree.links
    n.remove(n["Principled BSDF"])
    vol = n.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (0.95, 0.97, 1.0, 1)
    noise = n.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 40.0
    noise.inputs["Detail"].default_value = 6.0
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping")
    l.new(tc.outputs["Object"], mp.inputs["Vector"])
    l.new(mp.outputs["Vector"], noise.inputs["Vector"])
    mp.inputs["Location"].default_value = (0, 0, 0)
    mp.inputs["Location"].keyframe_insert("default_value", frame=1)
    mp.inputs["Location"].default_value = (0, 0, 3.0)
    mp.inputs["Location"].keyframe_insert("default_value", frame=120)
    mr = n.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.25, 0.7
    mr.inputs["To Max"].default_value = 160.0
    l.new(noise.outputs["Fac"], mr.inputs["Value"])
    l.new(mr.outputs["Result"], vol.inputs["Density"])
    l.new(vol.outputs[0], n["Material Output"].inputs["Volume"])
    assign(mist, mat)
    return root, mist


def cover_sheet(scene, lift_start, frames):
    """凍結防止カバー(銀色のシート)。夜のあいだに霜が付き、朝に持ち上げて外す。"""
    silver = principled("CoverSilver", (0.75, 0.77, 0.8), rough=0.45)
    silver.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.8
    add_bump(silver, scale=6, strength=0.6, distance=0.02)
    root = bpy.data.objects.new("Cover", None)
    scene.collection.objects.link(root)
    sheet = C.surface_mesh("CoverSheet", offset=0.006, u_range=(-1.14, 1.14), v_range=(-0.06, 1.04), nu=64, nv=32)
    assign(sheet, silver)
    fm, _ = C.frost_material("CoverFrost", cover=0.45, seed=2.0)
    fr = C.surface_mesh("CoverFrost", offset=0.008, u_range=(-1.14, 1.14), v_range=(-0.06, 1.04), nu=64, nv=32)
    assign(fr, fm)
    for o in (sheet, fr):
        o.parent = root
        w = o.modifiers.new("wrinkle", "DISPLACE")
        tx = bpy.data.textures.new("Wrinkle", "CLOUDS")
        tx.noise_scale = 0.15
        w.texture, w.strength = tx, 0.008
    key(root, "location", lift_start, (0, 0, 0))
    key(root, "rotation_euler", lift_start, (0, 0, 0))
    key(root, "location", lift_start + 18, (0.05, -0.1, 0.45))
    key(root, "rotation_euler", lift_start + 18, (math.radians(-25), 0, math.radians(6)))
    key(root, "location", min(frames, lift_start + 40), (0.9, 0.2, 1.4))
    key(root, "rotation_euler", min(frames, lift_start + 40), (math.radians(-60), 0, math.radians(20)))


def drive_scene(scene, frames):
    """運転席から見た、朝日に向かって走り出す景色(フロントガラスは透明)。"""
    lamp, bg, mix = C.world_hdri(scene, "passendorf_snow", 1.0, sun_az=-95, sun=3.0)
    C.car(scene, paint=C.car_paint(frost_top=0.5), frost_mat=None, side_frost=None)
    world = bpy.data.objects.new("World_", None)
    scene.collection.objects.link(world)
    g = C.snow_ground(scene, size=400)
    road = principled("Road", (0.06, 0.06, 0.065), rough=0.5)
    add_bump(road, scale=200, strength=0.3)
    r = box("Road", (4.5, 400, 0.02), (0.6, 0, 0.005), road)
    slush = principled("Slush", (0.75, 0.78, 0.82), rough=0.4)
    for x in (-1.7, 2.9):
        box(f"RoadEdge{x}", (0.6, 400, 0.05), (x, 0, 0.02), slush)
    rnd = random.Random(2)
    pine = principled("Pine", (0.04, 0.14, 0.08), rough=0.7)
    snow = principled("TreeSnow", (0.9, 0.93, 0.97), rough=0.6)
    objs = [g, r]
    for i in range(0):   # 円すいの木は作り物っぽく見えるので置かない(遠景は HDRI の山と林)
        x = rnd.choice([-1, 1]) * rnd.uniform(5, 30) + 0.6
        y = rnd.uniform(-180, 40)
        hgt = rnd.uniform(4, 9)
        bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=hgt * 0.28, depth=hgt, location=(x, y, hgt / 2))
        c1 = bpy.context.active_object
        assign(c1, pine)
        bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=hgt * 0.18, depth=hgt * 0.4, location=(x, y, hgt * 0.82))
        c2 = bpy.context.active_object
        assign(c2, snow)
        objs += [c1, c2]
    for i in range(30):   # 道路わきのポール
        y = -i * 12.0 + 10
        objs.append(cyl(f"Pole{i}", 0.03, 1.2, (-2.2, y, 0.6), principled("PoleRed", (0.8, 0.05, 0.04), rough=0.4)))
    for o in set(scene.objects) - {world}:
        if o in objs:
            o.parent = world
    # 車が前へ進む=景色が手前(+y)へ流れる(だんだん加速)
    for fr in range(1, frames + 1, 3):
        t = (fr - 1) / 24
        dist = 0.5 * 2.2 * t * t
        key(world, "location", fr, (0, dist, 0), "LINEAR")
    cam, tgt = camera(scene, "Cam", (-0.05, 0.3, 1.27), (-0.02, -3.0, 0.95), lens=20)
    for fr in range(1, frames + 1, 2):
        key(cam, "location", fr, (-0.05 + random.uniform(-0.002, 0.002), 0.3, 1.27 + random.uniform(-0.002, 0.002)), "LINEAR")


# ---------------------------------------------------------------- カット
def build(name):
    t = WORK / "timings.json"
    frames = windows(t)[name][1]
    scene = reset_scene(frames)

    if name == "hook":
        outdoor(scene, sun_az=-35, strength=1.0)
        fmat, ctrl = frost("hook_melt")
        C.key_value(ctrl["melt"], 1, 0.22, "LINEAR")
        C.key_value(ctrl["melt"], frames, 0.95, "LINEAR")
        C.car(scene, paint=C.car_paint(frost_top=0.8), frost_mat=fmat, side_frost=frost()[0])
        kettle(scene, SPOUT_TIP)
        water = C.water_material("Pour")
        pts = [tuple(p) for p in stream_points(10)]
        curve_tube(scene, "Stream", pts, 0.0065, water, order=4, resolution=32, taper=0.7)
        droplets(scene, frames)
        # 流れ落ちる筋(溶けた所に沿って下へ伸びる)
        x0 = IMPACT[0] * (0.72 - 0.08 * IMPACT[1])
        y0 = IMPACT[1] * 0.886
        for k, dx in enumerate((-0.015, 0.02, 0.05)):
            uvs = [to_uv(x0 + dx + 0.035 * math.sin(b * 13 + 1 + k), y0 - b) for b in np.linspace(0, 0.5, 12)]
            rv = C.surface_curve(scene, f"Rivulet{k}", uvs, 0.0035 - k * 0.0006, water, offset=0.0025)
            bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
            rv.data.bevel_factor_end = 0.15 + 0.1 * k
            rv.data.keyframe_insert("bevel_factor_end", frame=1)
            rv.data.bevel_factor_end = 1.0
            rv.data.keyframe_insert("bevel_factor_end", frame=frames)
        # パキッ:当たった所からヒビが一気に走る
        dirs = [math.radians(a) for a in (-100, -20, 160, 40, -150)]
        paths = C.crack_paths(11, (x0, y0), n_main=5, length=(0.3, 0.75), dirs=dirs, branch=0.06)
        C.crack_curves(scene, paths, start_frame=13, frames_total=26)
        steam("pour", k=45.0)
        cam, tgt = camera(scene, "Cam", (-0.5, -1.25, 1.5), (0.08, -0.12, 1.3), lens=30, fstop=6.0)
        key(cam, "location", 1, (-0.52, -1.3, 1.52))
        key(cam, "location", frames, (-0.36, -1.05, 1.46))
        return scene

    if name == "morning":
        outdoor(scene, sun_az=-30, strength=1.0)
        C.car(scene, paint=C.car_paint(frost_top=0.85), frost_mat=frost()[0], side_frost=frost()[0])
        kettle(scene, KETTLE_SPOUT_MORNING, tilt_deg=0, yaw_deg=0)
        steam("spout", k=130.0)
        cam, tgt = camera(scene, "Cam", (0.95, -2.25, 1.5), (0.2, -0.7, 1.12), lens=30, fstop=5.6)
        key(cam, "location", 1, (1.05, -2.45, 1.55))
        key(cam, "location", frames, (0.85, -2.0, 1.45))
        return scene

    if name == "stopwatch":
        outdoor(scene, sun_az=-40, strength=0.9)
        C.car(scene, paint=C.car_paint(frost_top=0.85), frost_mat=frost()[0], side_frost=frost()[0], interior=False)
        root = stopwatch(scene, (-0.15, -1.05, 0.0), frames)
        z = C.surface_z(-0.15, -1.05)
        root.location.z = z + 0.012
        cam, tgt = camera(scene, "Cam", (-0.12, -1.22, z + 0.3), (-0.15, -1.04, z + 0.0), lens=50, fstop=4.0)
        key(cam, "location", 1, (-0.08, -1.26, z + 0.33))
        key(cam, "location", frames, (-0.14, -1.19, z + 0.26))
        return scene

    if name in ("layers", "thermal"):
        studio(scene)
        parts = glass_sample(scene, name == "thermal", frames)
        if name == "layers":
            labels = [("ガラス", 0.026, 10), ("中間膜(樹脂)", 0.0, 26), ("ガラス", -0.026, 42)]
            ink = glow("LabelInk", (1, 1, 1), 3.0)
            line = glow("LabelLine", (0.9, 0.95, 1.0), 2.0)
            holder = bpy.data.objects.new("SampleTurn", None)   # 長い辺を奥へ向け、断面を正面に見せる
            scene.collection.objects.link(holder)
            for o in list(scene.objects):
                if o.parent is None and o.type == "MESH" and o.name != "Floor":
                    o.parent = holder
            holder.rotation_euler = (0, 0, math.radians(90))
            for txt, z, fr in labels:
                lab = text(scene, txt, 0.017, ink, (0.152, -0.185, z), (math.radians(90), 0, 0), align="LEFT")
                ln = box(f"Lead{fr}", (0.04, 0.001, 0.0012), (0.13, -0.185, z), line)
                for o in (lab, ln):
                    key(o, "scale", 1, (0, 0, 0), "CONSTANT")
                    key(o, "scale", fr, (0.01, 0.01, 0.01))
                    key(o, "scale", fr + 6, (1, 1, 1))
            cam, tgt = camera(scene, "Cam", (0.05, -0.75, 0.45), (0.06, 0, 0.0), lens=30, fstop=8.0)
            key(cam, "location", 1, (-0.12, -0.85, 0.42))
            key(cam, "location", frames, (0.08, -0.86, 0.08))
            key(tgt, "location", 1, (0.03, -0.1, 0.0))
            key(tgt, "location", frames, (0.08, -0.18, 0.0))
        else:
            cam, tgt = camera(scene, "Cam", (0.0, -0.95, 0.14), (0.0, 0, 0.0), lens=40, fstop=8.0)
            key(cam, "location", 1, (-0.05, -0.98, 0.18))
            key(cam, "location", frames, (0.03, -0.88, 0.1))
        return scene

    if name == "chip":
        outdoor(scene, sun_az=-35, strength=1.0)
        C.car(scene, paint=C.car_paint(frost_top=0.6), frost_mat=None, side_frost=None)
        x0 = IMPACT[0] * (0.72 - 0.08 * IMPACT[1])
        y0 = IMPACT[1] * 0.886
        p0 = np.array(ws_point(*IMPACT))
        nrm = ws_normal(*IMPACT)
        # 飛び石の小さな傷:星形の細かいヒビと、欠けた小さなくぼみ
        star = C.crack_paths(5, (x0, y0), n_main=7, length=(0.004, 0.011), step=0.0012, branch=0.0)
        C.crack_curves(scene, star, start_frame=-10, frames_total=5, radius=0.0003, offset=0.0008, name="Chip")
        pit = cyl("Pit", 0.0016, 0.0008, tuple(p0 + nrm * 0.0003), principled("PitMat", (0.9, 0.95, 1.0), rough=0.3, emission=0.2),
                  rot=tuple(mathutils.Vector(nrm).to_track_quat("Z", "Y").to_euler()))
        ring_mat = glow("Ring", (1.0, 0.85, 0.2), 6.0)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.018, minor_radius=0.0008, location=tuple(p0 + nrm * 0.003))
        ring = bpy.context.active_object
        ring.rotation_euler = mathutils.Vector(nrm).to_track_quat("Z", "Y").to_euler()
        assign(ring, ring_mat)
        ring.visible_glossy = ring.visible_transmission = False   # ガラスに映り込んで何重にも見えないように
        key(ring, "scale", 1, (0, 0, 0), "CONSTANT")
        key(ring, "scale", 8, (0.01, 0.01, 0.01))
        key(ring, "scale", 14, (1.2, 1.2, 1.2))
        key(ring, "scale", 18, (1, 1, 1))
        key(ring, "scale", 44, (1, 1, 1))
        key(ring, "scale", 50, (0, 0, 0))
        # お湯が当たる → 傷から一気にヒビが広がる
        water = C.water_material("Pour")
        st = curve_tube(scene, "Stream", [tuple(p) for p in stream_points(10)], 0.0065, water, order=4, resolution=32, taper=0.7)[0]
        key(st, "scale", 1, (0, 0, 0), "CONSTANT")
        key(st, "scale", 48, (1, 1, 1), "CONSTANT")
        kettle(scene, SPOUT_TIP)
        dirs = [math.radians(a) for a in (-95, -15, 165, 35, -150, 100)]
        paths = C.crack_paths(21, (x0, y0), n_main=6, length=(0.35, 0.8), dirs=dirs, branch=0.07)
        C.crack_curves(scene, paths, start_frame=56, frames_total=34, radius=0.0006)
        steam("pour", k=22.0, start=50)
        cam, tgt = camera(scene, "Cam", tuple(p0 + nrm * 0.22 + np.array((-0.08, -0.04, 0.03))), tuple(p0), lens=50, fstop=5.6)
        key(cam, "location", 1, tuple(p0 + nrm * 0.22 + np.array((-0.08, -0.04, 0.03))))
        key(cam, "location", 46, tuple(p0 + nrm * 0.18 + np.array((-0.06, -0.04, 0.03))))
        key(cam, "location", frames, (-0.42, -1.2, 1.58))
        key(cam.data, "lens", 46, 50.0)
        key(cam.data, "lens", frames, 32.0)
        return scene

    if name == "lukewarm":
        outdoor(scene, sun_az=-35, strength=0.95)
        fmat, ctrl = frost("lukewarm_melt", "lukewarm_freeze")
        C.key_value(ctrl["melt"], 1, 0.0, "LINEAR")
        C.key_value(ctrl["melt"], int(frames * 0.33), 0.36, "LINEAR")
        C.key_value(ctrl["freeze"], int(frames * 0.42), 0.4, "LINEAR")
        C.key_value(ctrl["freeze"], frames - 6, 0.97, "LINEAR")
        C.car(scene, paint=C.car_paint(frost_top=0.8), frost_mat=fmat, side_frost=frost()[0])
        water = C.water_material("Pour")
        tip = np.array(SPOUT_TIP) + np.array((-0.05, 0, 0))
        imp = np.array(ws_point(IMPACT[0] - 0.08, IMPACT[1]))
        sp = [tuple(tip + (imp - tip) * s_ + np.array((0, 0, (imp[2] - tip[2]) * (s_ * s_ - s_)))) for s_ in np.linspace(0, 1, 10)]
        st = curve_tube(scene, "Stream", sp, 0.006, water, order=4, resolution=32, taper=0.7)[0]
        key(st, "scale", 1, (1, 1, 1), "CONSTANT")
        key(st, "scale", int(frames * 0.3), (0, 0, 0), "CONSTANT")
        kt = kettle(scene, tuple(tip))
        key(kt, "location", int(frames * 0.3), tuple(kt.location))
        key(kt, "location", int(frames * 0.3) + 14, tuple(kt.location + mathutils.Vector((0.25, 0.1, 0.35))))
        cam, tgt = camera(scene, "Cam", (-0.45, -1.15, 1.55), (0.0, -0.12, 1.24), lens=34, fstop=5.6)
        key(cam, "location", 1, (-0.46, -1.18, 1.56))
        key(cam, "location", frames, (-0.3, -0.95, 1.48))
        return scene

    if name == "wiper":
        outdoor(scene, sun_az=-35, strength=0.95)
        parts = C.car(scene, paint=C.car_paint(frost_top=0.85), frost_mat=frost()[0], side_frost=frost()[0])
        swing, arm, blade, rubber = parts["wipers"][0]
        rubber.data.materials.clear()
        rubber.data.materials.append(principled("RubberIce", (0.05, 0.05, 0.06), rough=0.3))
        mw = rubber.matrix_world.copy()
        rubber.parent = None
        rubber.matrix_world = mw
        stuck = int(frames * 0.25)
        for k, fr in enumerate(range(stuck, stuck + 24, 3)):   # 動こうとしてガタガタ
            key(swing, "rotation_euler", fr, (0, 0, math.radians(1.2 if k % 2 else -0.4)), "LINEAR")
        lift = stuck + 26
        key(swing, "rotation_euler", lift, (0, 0, 0))
        key(swing, "rotation_euler", lift + 10, (0, 0, math.radians(16)))
        key(swing, "rotation_euler", frames, (0, 0, math.radians(19)))
        # ちぎれたゴム:ブレードからガラスへ伸びる細い切れ端
        flap_mat = principled("Flap", (0.03, 0.03, 0.035), rough=0.4)
        tear = box("Tear", (0.12, 0.006, 0.006), (0.0, 0.0, 0.0), flap_mat)
        tear.parent = swing
        tear.location = (C.WIPER_PIVOTS[0][1] * 0.75, 0.075, -0.02)
        tear.rotation_euler = (0, math.radians(25), math.radians(-8))
        key(tear, "scale", 1, (0, 0, 0), "CONSTANT")
        key(tear, "scale", lift + 6, (1, 1, 1), "CONSTANT")
        pu = C.WIPER_PIVOTS[0][0]
        target = np.array(ws_point(pu + 0.35, 0.12))
        cam, tgt = camera(scene, "Cam", tuple(target + np.array((-0.12, -0.38, 0.3))), tuple(target), lens=32, fstop=5.6)
        key(cam, "location", 1, tuple(target + np.array((-0.14, -0.4, 0.32))))
        key(cam, "location", frames, tuple(target + np.array((-0.1, -0.33, 0.27))))
        return scene

    if name == "defroster":
        outdoor(scene, sun_az=-70, strength=1.0)
        fmat, ctrl = frost("defrost_melt")
        C.key_value(ctrl["melt"], 6, 0.0, "LINEAR")
        C.key_value(ctrl["melt"], frames - 4, 1.0, "LINEAR")
        C.car(scene, paint=C.car_paint(frost_top=0.85), frost_mat=fmat, side_frost=frost()[0])
        vent = glow("Vent", (1.0, 0.45, 0.12), 0.0)
        for x in (-0.45, 0.45):
            box(f"Vent{x}", (0.4, 0.04, 0.006), (x, -0.36, 1.062), vent)
        from car import key_value
        es = vent.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
        key_value(es, 1, 0.0)
        key_value(es, 12, 4.0)
        warm = light(scene, "AREA", "WarmAir", (0, -0.35, 1.1), 0.0, (1.0, 0.5, 0.2), size=1.2, look_at=(0, -0.6, 1.4))
        key(warm.data, "energy", 1, 0.0)
        key(warm.data, "energy", 14, 25.0)
        cabin = light(scene, "AREA", "CabinFill", (-0.3, 0.6, 1.35), 6.0, (0.8, 0.85, 1.0), size=0.6, look_at=(-0.2, -0.3, 1.0))
        cam, tgt = camera(scene, "Cam", (-0.05, 0.42, 1.3), (-0.02, -0.6, 1.24), lens=20)
        key(cam, "location", 1, (-0.06, 0.45, 1.3))
        key(cam, "location", frames, (-0.04, 0.36, 1.28))
        return scene

    if name == "spray":
        outdoor(scene, sun_az=-35, strength=1.0)
        fmat, ctrl = frost("spray_melt")
        s0, s1 = 6, frames - 8
        C.key_value(ctrl["melt"], s0, 0.0, "LINEAR")
        C.key_value(ctrl["melt"], s1, 1.0, "LINEAR")
        C.car(scene, paint=C.car_paint(frost_top=0.8), frost_mat=fmat, side_frost=frost()[0])
        can, mist = spray_can(scene)
        # 缶はマップと同じ経路で動かす(τ=0〜0.55 のあいだ噴射)
        spray_end = s0 + int(0.55 * (s1 - s0))
        for fr in range(1, frames + 1, 2):
            tau = min(max((fr - s0) / (s1 - s0), 0.0), 0.55)
            ph = tau / 0.55
            cu, cv = 0.55 - 1.1 * ph, 0.68 - 0.36 * ph + 0.1 * math.sin(ph * 9)
            u, v = to_uv(cu * 0.68, cv * 0.886)
            pt = np.array(ws_point(u, v))
            n_ = ws_normal(u, v)
            pos = pt + n_ * 0.2 + np.array((0.0, -0.08, 0.0))
            if fr > spray_end:
                pos = pos + n_ * (fr - spray_end) * 0.012 + np.array((0.02, 0, 0.01)) * (fr - spray_end)
            key(can, "location", fr, tuple(pos), "LINEAR")
            d = mathutils.Vector(tuple(pt - pos)).normalized()
            key(can, "rotation_euler", fr, tuple(d.to_track_quat("-Z", "Y").to_euler()), "LINEAR")
        # 縮尺0の体積は OpenVDB が落ちるので、表示/非表示で切り替える
        for fr, hide in ((1, True), (s0, False), (spray_end, True)):
            mist.hide_render = hide
            mist.keyframe_insert("hide_render", frame=fr)
        cam, tgt = camera(scene, "Cam", (-0.25, -1.3, 1.6), (0.0, -0.15, 1.28), lens=24, fstop=8.0)
        key(cam, "location", 1, (-0.28, -1.34, 1.62))
        key(cam, "location", frames, (-0.2, -1.2, 1.56))
        return scene

    if name == "cover":
        sun, bg, mix = outdoor(scene, sun_az=-35, strength=1.0)
        night, dawn = int(frames * 0.3), int(frames * 0.48)
        key_socket_val(bg.inputs["Strength"], 1, 0.06)
        key_socket_val(bg.inputs["Strength"], night, 0.06)
        key_socket_val(bg.inputs["Strength"], dawn, 1.0)
        key(sun.data, "energy", 1, 0.0)
        key(sun.data, "energy", night, 0.0)
        key(sun.data, "energy", dawn, 3.0)
        moon = light(scene, "SUN", "Moon", (3, -6, 6), 0.0, (0.55, 0.65, 1.0), size=math.radians(1), look_at=(0, 0, 0))
        key(moon.data, "energy", 1, 0.35)
        key(moon.data, "energy", night, 0.35)
        key(moon.data, "energy", dawn, 0.0)
        C.car(scene, paint=C.car_paint(frost_top=0.85), frost_mat=None, side_frost=frost()[0])
        cover_sheet(scene, night + 8, frames)
        cam, tgt = camera(scene, "Cam", (-0.9, -2.3, 1.75), (0.0, -0.1, 1.15), lens=28)
        key(cam, "location", 1, (-1.0, -2.45, 1.8))
        key(cam, "location", frames, (-0.75, -2.05, 1.68))
        return scene

    if name == "drive":
        drive_scene(scene, frames)
        return scene

    raise SystemExit(f"unknown shot {name}")


if __name__ == "__main__":
    name, work, out = sys.argv[1:4]
    WORK = Path(work)
    C.HDRI_DIR = str(WORK / "hdri")
    scene = build(name)
    frames = scene.frame_end
    vb = 3 if name in ("hook", "morning", "chip") else (1 if name == "spray" else 0)
    if "--preview" in sys.argv:
        pf = [int(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")] if len(sys.argv) > 5 else \
            sorted({max(1, frames // 6), frames // 2, frames - 3})
        render(scene, out, samples=16, scale=40, preview_frames=pf, bounces=12, volume_bounces=vb)
    else:
        render(scene, out, bounces=8, volume_bounces=vb)
