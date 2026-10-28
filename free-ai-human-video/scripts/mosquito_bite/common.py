"""Blender(bpy)の共通ヘルパー。各カットのスクリプトから使う。"""
import math
import os
from pathlib import Path

import bpy  # bmesh より先に読み込む必要がある
import bmesh

FPS = 24
RES = (1080, 1920)


# ---------- シーン ----------
def reset_scene(frames):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, frames
    scene.render.fps = FPS
    world = bpy.data.worlds.new("World")
    scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0, 0, 0, 1)
    return scene


def key(obj, path, frame, value, interp="BEZIER", index=-1):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    setattr(obj, path, value)
    obj.keyframe_insert(data_path=path, frame=frame, index=index)


def key_point(point, frame, co, interp="BEZIER"):
    """NURBS/ポリラインの制御点を動かす。co は (x, y, z)。"""
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    point.co = (*co, 1.0)
    point.keyframe_insert("co", frame=frame)


def camera(scene, name, loc, look_at, lens=50, fstop=None, focus=None):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.data.lens = lens
    cam.data.sensor_width = 36
    target = bpy.data.objects.new(name + "_target", None)
    target.location = look_at
    scene.collection.objects.link(target)
    c = cam.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    if fstop:
        cam.data.dof.use_dof = True
        cam.data.dof.aperture_fstop = fstop
        cam.data.dof.focus_object = focus or target
    scene.camera = cam
    return cam, target


def light(scene, kind, name, loc, energy, color=(1, 1, 1), size=1.0, look_at=None):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if kind == "AREA":
        data.size = size
    elif kind in ("POINT", "SPOT"):
        data.shadow_soft_size = size
    elif kind == "SUN":
        data.angle = size
    obj = bpy.data.objects.new(name, data)
    obj.location = loc
    scene.collection.objects.link(obj)
    if look_at is not None:
        t = bpy.data.objects.new(name + "_t", None)
        t.location = look_at
        scene.collection.objects.link(t)
        c = obj.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = t, "TRACK_NEGATIVE_Z", "UP_Y"
    return obj


# ---------- マテリアル ----------
def material(name):
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    return mat, mat.node_tree.nodes, mat.node_tree.links


def principled(name, color, rough=0.5, sss=0.0, sss_radius=(1.0, 0.3, 0.15), sss_scale=0.1,
               coat=0.0, emission=0.0, emission_color=None, alpha=1.0, transmission=0.0, ior=1.45):
    mat, nodes, links = material(name)
    b = nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = ior
    if sss:
        b.subsurface_method = "BURLEY"  # ランダムウォークより大幅に速い
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = sss_radius
        b.inputs["Subsurface Scale"].default_value = sss_scale
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.15
    if emission:
        b.inputs["Emission Color"].default_value = (*(emission_color or color), 1)
        b.inputs["Emission Strength"].default_value = emission
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return mat


def add_bump(mat, scale, strength, distance=0.02, kind="noise", detail=6.0, coord="Object", voronoi_feature="F1"):
    """マテリアルに凹凸(バンプ)を足す。"""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    b = nodes["Principled BSDF"]
    tc = nodes.new("ShaderNodeTexCoord")
    if kind == "noise":
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Detail"].default_value = detail
        out = tex.outputs["Fac"]
    elif kind == "voronoi":
        tex = nodes.new("ShaderNodeTexVoronoi")
        tex.feature = voronoi_feature
        out = tex.outputs["Distance"]
    else:  # wave(繊維)
        tex = nodes.new("ShaderNodeTexWave")
        tex.inputs["Distortion"].default_value = 6.0
        tex.inputs["Detail"].default_value = detail
        out = tex.outputs["Fac"]
    tex.inputs["Scale"].default_value = scale
    links.new(tc.outputs[coord], tex.inputs["Vector"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    old = b.inputs["Normal"].links[0].from_socket if b.inputs["Normal"].is_linked else None
    if old:
        links.new(old, bump.inputs["Normal"])
    links.new(out, bump.inputs["Height"])
    links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return tex


def color_variation(mat, color_a, color_b, scale, detail=4.0):
    """ベースカラーにノイズで色ムラを付ける。"""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    b = nodes["Principled BSDF"]
    tc = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = detail
    links.new(tc.outputs["Object"], noise.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*color_a, 1)
    ramp.color_ramp.elements[1].color = (*color_b, 1)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.65
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return ramp


def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def smooth(obj, levels=0):
    for p in obj.data.polygons:
        p.use_smooth = True
    if levels:
        m = obj.modifiers.new("subsurf", "SUBSURF")
        m.levels = m.render_levels = levels


# ---------- 形状 ----------
def curve_tube(scene, name, points, radius, mat, order=4, resolution=24, taper=None):
    """制御点を通るチューブ(NURBS)。points: [(x,y,z), ...]"""
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = radius
    data.bevel_resolution = 6
    data.resolution_u = resolution
    data.use_fill_caps = True
    sp = data.splines.new("NURBS")
    sp.points.add(len(points) - 1)
    for p, co in zip(sp.points, points):
        p.co = (*co, 1.0)
    sp.order_u = min(order, len(points))
    sp.use_endpoint_u = True
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    if taper is not None:
        sp.points[-1].radius = taper
    obj.data.materials.append(mat)
    return obj, sp


def red_blood_cell_mesh(name, R=1.0, segments=48, rings=24):
    """赤血球(両凹円盤)のメッシュ。Evans & Fung の式で断面を作って回転させる。"""
    c0, c2, c4 = 0.207, 2.003, -1.123
    bm = bmesh.new()
    rows = []
    for i in range(rings + 1):
        t = i / rings  # 0(中心)→1(縁)
        x = math.sin(t * math.pi / 2)
        z = 0.5 * R * math.sqrt(max(0.0, 1 - x * x)) * (c0 + c2 * x * x + c4 * x ** 4)
        rows.append((x * R, z))
    top, bottom = [], []
    for side, store in ((1, top), (-1, bottom)):
        for r, z in rows:
            ring = []
            for j in range(segments):
                a = j / segments * math.tau
                ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), side * z)))
            store.append(ring)
    for store, flip in ((top, False), (bottom, True)):
        for i in range(rings):
            for j in range(segments):
                q = [store[i][j], store[i][(j + 1) % segments], store[i + 1][(j + 1) % segments], store[i + 1][j]]
                bm.faces.new(q[::-1] if flip else q)
    for j in range(segments):  # 縁をつなぐ
        q = [top[-1][j], top[-1][(j + 1) % segments], bottom[-1][(j + 1) % segments], bottom[-1][j]]
        bm.faces.new(q[::-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


# ---------- レンダリング ----------
def render(scene, out_dir, samples=None, scale=None, motion_blur=False, preview_frames=None, bounces=None):
    samples = samples or int(os.environ.get("SAMPLES", 12))
    scale = scale or int(os.environ.get("SCALE", 67))
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.cycles.transmission_bounces = 4
    scene.cycles.volume_bounces = 0
    scene.cycles.transparent_max_bounces = 8
    if bounces:  # ガラス越しの水など、透過が重なる場面用
        scene.cycles.max_bounces = bounces
        scene.cycles.transmission_bounces = bounces
    scene.render.use_persistent_data = True
    scene.render.resolution_x, scene.render.resolution_y = RES
    scene.render.resolution_percentage = scale
    scene.render.use_motion_blur = motion_blur
    scene.render.motion_blur_shutter = 0.5
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    frames_env = os.environ.get("FRAMES")
    if preview_frames is not None:
        for fr in preview_frames:
            scene.frame_set(fr)
            scene.render.filepath = str(out / f"preview_{fr:04d}.png")
            bpy.ops.render.render(write_still=True)
        return
    if frames_env:
        scene.frame_start, scene.frame_end = map(int, frames_env.split("-"))
    scene.render.filepath = str(out / "f_")
    scene.render.use_overwrite = False  # 途中で止まっても、書き出し済みのフレームは飛ばして再開できる
    bpy.ops.render.render(animation=True)
