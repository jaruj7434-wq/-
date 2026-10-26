"""「もしも地球が1秒止まったら?」の3DCGシーンを Blender(bpy・無料)で組み立て、連番PNGに書き出す。

使い方: python scene.py <timings.json> <出力フォルダ> [--preview]
  --preview を付けると、各カットの代表フレームだけを低画質で書き出す(確認用)。
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy

FPS = 30
RES = (720, 1280)  # 書き出し後に FFmpeg で 1080x1920 へ拡大する
GROUND_X = 1000.0  # 地上シーンを地球から離して置く位置

random.seed(7)


# ---------- 汎用ヘルパー ----------
def key(obj, path, frame, value, interp="LINEAR"):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    setattr(obj, path, value)
    obj.keyframe_insert(data_path=path, frame=frame)


def visible(obj, ranges, last_frame):
    """ranges: [(start, end)] のフレーム区間だけレンダリングに表示する。"""
    obj.hide_render = True
    obj.keyframe_insert("hide_render", frame=0)
    for s, e in ranges:
        obj.hide_render = False
        obj.keyframe_insert("hide_render", frame=s)
        obj.hide_render = True
        obj.keyframe_insert("hide_render", frame=e)
    obj.hide_render = True if ranges else False


def new_material(name):
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    return mat, mat.node_tree.nodes, mat.node_tree.links


def flat_material(name, color, rough=0.6, emission=0.0):
    mat, nodes, _ = new_material(name)
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def smooth(obj, levels=0):
    for p in obj.data.polygons:
        p.use_smooth = True
    if levels:
        m = obj.modifiers.new("subsurf", "SUBSURF")
        m.levels = m.render_levels = levels


# ---------- 素材 ----------
def make_world():
    world = bpy.data.worlds.new("Space")
    bpy.context.scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    nodes, links = world.node_tree.nodes, world.node_tree.links
    bg = nodes["Background"]
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 450.0
    noise.inputs["Detail"].default_value = 0.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.72
    ramp.color_ramp.elements[0].color = (0.002, 0.003, 0.01, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0


def earth_material():
    mat, nodes, links = new_material("Earth")
    bsdf = nodes["Principled BSDF"]
    coord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.6
    noise.inputs["Detail"].default_value = 10.0
    noise.inputs["Roughness"].default_value = 0.6
    links.new(coord.outputs["Object"], noise.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.50, (0.01, 0.06, 0.25, 1)  # 海
    els[1].position, els[1].color = 0.70, (0.45, 0.38, 0.22, 1)  # 山地
    e = els.new(0.53)
    e.color = (0.08, 0.30, 0.08, 1)  # 陸
    e = els.new(0.515)
    e.color = (0.03, 0.12, 0.35, 1)  # 浅瀬
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.55
    return mat


def cloud_material():
    mat, nodes, links = new_material("Clouds")
    out = nodes["Material Output"]
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
    transp = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    coord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 8.0
    links.new(coord.outputs["Object"], noise.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.52
    ramp.color_ramp.elements[1].position = 0.70
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], mix.inputs["Fac"])
    links.new(transp.outputs[0], mix.inputs[1])
    links.new(bsdf.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def glow_material(name, color, strength):
    """縁だけ光るシェル(大気・炎)。"""
    mat, nodes, links = new_material(name)
    out = nodes["Material Output"]
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*color, 1)
    emit.inputs["Strength"].default_value = strength
    transp = nodes.new("ShaderNodeBsdfTransparent")
    lw = nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    mix = nodes.new("ShaderNodeMixShader")
    links.new(lw.outputs["Facing"], mix.inputs["Fac"])
    links.new(transp.outputs[0], mix.inputs[1])
    links.new(emit.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def sphere(name, radius, mat, parent=None, loc=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=radius, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    smooth(obj)
    assign(obj, mat)
    if parent:
        obj.parent = parent
    return obj


# ---------- シーン構築 ----------
def build(t):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    lines = t["lines"]
    f = lambda sec: int(round(sec * FPS)) + 1
    L = [(f(l["start"]), f(l["end"])) for l in lines]
    end = f(t["total"] + 0.6)
    scene.frame_start, scene.frame_end = 1, end
    scene.render.fps = FPS

    make_world()

    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 4.5
    sun.data.angle = math.radians(2)
    sun.rotation_euler = (math.radians(50), math.radians(-35), math.radians(-40))
    scene.collection.objects.link(sun)

    # --- 地球 ---
    tilt = bpy.data.objects.new("Tilt", None)
    tilt.rotation_euler = (math.radians(23.4), math.radians(-10), 0)
    scene.collection.objects.link(tilt)

    earth = sphere("Earth", 1.0, earth_material(), tilt)
    clouds = sphere("Clouds", 1.025, cloud_material(), tilt)
    sphere("Atmosphere", 1.07, glow_material("Atmo", (0.25, 0.55, 1.0), 2.5), tilt)
    fire = sphere("Fire", 1.04, glow_material("FireMat", (1.0, 0.25, 0.03), 6.0), tilt)
    visible(fire, [(L[4][0], end + 1)], end)

    stop = L[2][0] + int(0.4 * FPS)  # 地球が止まるフレーム
    spin = 0.9 / FPS  # 1フレームあたりの回転(誇張)
    key(earth, "rotation_euler", 1, (0, 0, 0))
    key(earth, "rotation_euler", stop, (0, 0, spin * stop), "CONSTANT")
    key(earth, "rotation_euler", end, (0, 0, spin * stop))
    # 雲(大気)は止まれずに回り続け、むしろ加速する
    key(clouds, "rotation_euler", 1, (0, 0, 0))
    key(clouds, "rotation_euler", stop, (0, 0, spin * stop * 1.1))
    key(clouds, "rotation_euler", L[3][0], (0, 0, spin * stop * 1.1 + 2.8))

    # --- 赤道の矢印リング(セリフ2〜3) ---
    ring_root = bpy.data.objects.new("RingRoot", None)
    ring_root.parent = tilt
    scene.collection.objects.link(ring_root)
    ring_mat = flat_material("Ring", (1.0, 0.55, 0.05), emission=6.0)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.22, minor_radius=0.012, major_segments=128)
    ring = bpy.context.active_object
    assign(ring, ring_mat)
    ring.parent = ring_root
    for i in range(6):
        a = i * math.tau / 6
        bpy.ops.mesh.primitive_cone_add(radius1=0.05, depth=0.14, location=(1.22 * math.cos(a), 1.22 * math.sin(a), 0))
        cone = bpy.context.active_object
        cone.rotation_euler = (math.radians(-90), 0, a)  # 進行方向(反時計回り)へ向ける
        assign(cone, ring_mat)
        cone.parent = ring_root
    for obj in [ring, *[c for c in ring_root.children if c != ring]]:
        visible(obj, [(L[1][0], stop)], end)
    key(ring_root, "rotation_euler", L[1][0], (0, 0, 0))
    key(ring_root, "rotation_euler", stop, (0, 0, 4.0))
    key(ring_root, "scale", L[1][0], (0.6, 0.6, 0.6), "BEZIER")
    key(ring_root, "scale", L[1][0] + 8, (1, 1, 1))

    # --- 宇宙カメラ ---
    cam_space = bpy.data.objects.new("CamSpace", bpy.data.cameras.new("CamSpace"))
    cam_space.data.lens = 50
    scene.collection.objects.link(cam_space)
    cam_space.rotation_euler = (math.radians(90), 0, 0)
    key(cam_space, "location", 1, (0, -7.0, 0.0), "BEZIER")
    key(cam_space, "location", L[1][0], (0, -5.6, 0.0))
    key(cam_space, "location", stop, (0, -5.3, 0.0))
    for fr in range(stop, L[3][0], 2):  # 停止時の揺れ(徐々に弱まる)
        k = 1 - (fr - stop) / max(1, L[3][0] - stop)
        key(cam_space, "location", fr, (random.uniform(-1, 1) * 0.12 * k, -5.3, random.uniform(-1, 1) * 0.12 * k))
    key(cam_space, "location", L[4][0], (0, -5.0, 0.0), "BEZIER")
    key(cam_space, "location", end, (0, -6.5, 0.0))

    # --- 地上シーン(セリフ4) ---
    build_ground(scene, L, end)

    cam_ground = bpy.data.objects.new("CamGround", bpy.data.cameras.new("CamGround"))
    cam_ground.data.lens = 22
    scene.collection.objects.link(cam_ground)
    cam_ground.rotation_euler = (math.radians(84), 0, 0)
    gs = L[3][0]
    for fr in range(gs, L[4][0] + 1, 2):
        k = 0.0 if fr < gs + 10 else 0.25
        key(cam_ground, "location", fr, (GROUND_X + random.uniform(-1, 1) * k, -16 + random.uniform(-1, 1) * k * 0.3, 2.2 + random.uniform(-1, 1) * k))

    # --- カット割り(マーカーでカメラを切り替える) ---
    for name, frame, cam in [("s1", 1, cam_space), ("ground", L[3][0], cam_ground), ("end", L[4][0], cam_space)]:
        m = scene.timeline_markers.new(name, frame=frame)
        m.camera = cam
    scene.camera = cam_space
    return scene, L, stop, end


def build_ground(scene, L, end):
    gs, ge = L[3][0], L[4][0]
    blast = gs + 10  # 吹き飛び開始
    show = [(gs, ge)]

    sky_mat, nodes, links = new_material("Sky")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (0.45, 0.65, 0.95, 1)
    emit.inputs["Strength"].default_value = 1.0
    links.new(emit.outputs[0], nodes["Material Output"].inputs["Surface"])
    sky = sphere("Sky", 150, sky_mat, loc=(GROUND_X, 0, 0))
    visible(sky, show, end)

    bpy.ops.mesh.primitive_plane_add(size=300, location=(GROUND_X, 60, 0))
    ground = bpy.context.active_object
    assign(ground, flat_material("Grass", (0.12, 0.35, 0.08), rough=0.9))
    visible(ground, show, end)

    pastel = [(0.9, 0.85, 0.75), (0.85, 0.6, 0.5), (0.7, 0.8, 0.9), (0.95, 0.9, 0.6), (0.8, 0.75, 0.85)]
    roof = flat_material("Roof", (0.55, 0.12, 0.08))
    trunk = flat_material("Trunk", (0.3, 0.18, 0.08))
    leaf = flat_material("Leaf", (0.1, 0.45, 0.12))
    people = [flat_material(f"Person{i}", c) for i, c in enumerate([(0.95, 0.4, 0.1), (0.1, 0.4, 0.9), (0.9, 0.85, 0.2)])]
    skin = flat_material("Skin", (0.85, 0.65, 0.5))
    walls = [flat_material(f"Wall{i}", c) for i, c in enumerate(pastel)]

    def group(parts, x, y):
        root = bpy.data.objects.new("Obj", None)
        root.location = (x, y, 0)
        scene.collection.objects.link(root)
        for p in parts:
            p.parent = root
            p.location.x -= x
            p.location.y -= y
            visible(p, show, end)
        return root

    objs = []
    for _ in range(14):  # 家
        x, y = GROUND_X + random.uniform(-14, 14), random.uniform(4, 30)
        s = random.uniform(1.2, 2.0)
        bpy.ops.mesh.primitive_cube_add(size=s, location=(x, y, s / 2))
        wall = bpy.context.active_object
        assign(wall, random.choice(walls))
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=s * 0.8, depth=s * 0.6, location=(x, y, s + s * 0.3))
        r = bpy.context.active_object
        r.rotation_euler.z = math.radians(45)
        assign(r, roof)
        objs.append(group([wall, r], x, y))
    for _ in range(18):  # 木
        x, y = GROUND_X + random.uniform(-16, 16), random.uniform(-2, 30)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=1.0, location=(x, y, 0.5))
        tr = bpy.context.active_object
        assign(tr, trunk)
        bpy.ops.mesh.primitive_cone_add(radius1=0.7, depth=1.8, location=(x, y, 1.8))
        lf = bpy.context.active_object
        assign(lf, leaf)
        objs.append(group([tr, lf], x, y))
    for _ in range(12):  # 人
        x, y = GROUND_X + random.uniform(-8, 8), random.uniform(-6, 2)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.9, location=(x, y, 0.45))
        body = bpy.context.active_object
        assign(body, random.choice(people))
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.17, location=(x, y, 1.08))
        head = bpy.context.active_object
        smooth(head)
        assign(head, skin)
        objs.append(group([body, head], x, y))

    # 東(画面右)へ吹き飛ばす。手前(カメラに近い)ものほど先に飛ぶ
    for o in objs:
        start = blast + int((o.location.y + 6) * 0.35) + random.randint(0, 3)
        dist = random.uniform(35, 60)
        lift = random.uniform(2, 9)
        spinv = [random.uniform(-6, 6) for _ in range(3)]
        x0, y0 = o.location.x, o.location.y
        key(o, "location", start, (x0, y0, 0), "BEZIER")
        key(o, "rotation_euler", start, (0, 0, 0), "BEZIER")
        key(o, "location", start + 18, (x0 + dist, y0 + random.uniform(-3, 3), lift))
        key(o, "rotation_euler", start + 18, spinv)

    # 風の筋
    streak_mat = flat_material("Streak", (1, 1, 1), emission=3.0)
    for i in range(70):
        y, z = random.uniform(-6, 25), random.uniform(0.3, 6)
        st = blast - 6 + random.randint(0, ge - blast)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=random.uniform(3, 7), location=(GROUND_X - 30, y, z))
        s = bpy.context.active_object
        s.rotation_euler = (0, math.radians(90), 0)
        assign(s, streak_mat)
        visible(s, [(max(gs, st), min(ge, st + 9))], end)
        key(s, "location", st, (GROUND_X - 30, y, z))
        key(s, "location", st + 9, (GROUND_X + 30, y, z))


def render(scene, out_dir, frames=None, samples=24, scale=100):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.render.use_persistent_data = True
    scene.render.resolution_x, scene.render.resolution_y = RES
    scene.render.resolution_percentage = scale
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if frames is None:
        scene.render.filepath = str(out / "f_")
        bpy.ops.render.render(animation=True)
    else:
        for fr in frames:
            scene.frame_set(fr)
            scene.render.filepath = str(out / f"preview_{fr:04d}.png")
            bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    timings = json.loads(Path(sys.argv[1]).read_text())
    scene, L, stop, end = build(timings)
    if "--preview" in sys.argv:
        frames = [L[0][0] + 20, L[1][0] + 25, stop + 8, L[3][0] + 22, L[4][0] + 15]
        render(scene, sys.argv[2], frames, samples=12, scale=50)
    else:
        render(scene, sys.argv[2])
