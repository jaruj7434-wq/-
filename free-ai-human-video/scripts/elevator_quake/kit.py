"""エレベーター動画用のヘルパー。基本部分は mosquito_bite/common.py を使い回す。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mosquito_bite"))

import bpy  # noqa: E402

from common import (FPS, add_bump, assign, camera, color_variation, curve_tube, key, light, material,  # noqa: E402,F401
                    principled, render, reset_scene, smooth)

JP_FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"


def metal(name, color=(0.8, 0.8, 0.82), rough=0.22, brushed=True):
    """ステンレス(ヘアライン仕上げ)。"""
    mat = principled(name, color, rough=rough)
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Metallic"].default_value = 1.0
    if brushed:
        b.inputs["Anisotropic"].default_value = 0.7
        n, l = mat.node_tree.nodes, mat.node_tree.links
        tc = n.new("ShaderNodeTexCoord")
        mapping = n.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = (1.0, 400.0, 1.0)  # 横方向に細長いノイズ=ヘアライン
        noise = n.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 3.0
        l.new(tc.outputs["Object"], mapping.inputs["Vector"])
        l.new(mapping.outputs["Vector"], noise.inputs["Vector"])
        ramp = n.new("ShaderNodeMapRange")
        ramp.inputs["To Min"].default_value = rough * 0.6
        ramp.inputs["To Max"].default_value = rough * 1.5
        l.new(noise.outputs["Fac"], ramp.inputs["Value"])
        l.new(ramp.outputs["Result"], b.inputs["Roughness"])
    return mat


def glow(name, color, strength=5.0):
    """光る素材(ボタンのランプ・LED 表示など)。Emission Strength をキーフレームで動かせる。"""
    mat = principled(name, color, rough=0.3, emission=strength, emission_color=color)
    return mat


def glow_socket(mat):
    return mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]


def key_socket(socket, frame, value, interp="BEZIER"):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    socket.default_value = value
    socket.keyframe_insert("default_value", frame=frame)


def text(scene, body, size, mat, loc=(0, 0, 0), rot=(0, 0, 0), extrude=0.0, align="CENTER", jp=True):
    data = bpy.data.curves.new("txt", "FONT")
    data.body = body
    data.size = size
    data.extrude = extrude
    data.align_x = align
    data.align_y = "CENTER"
    if jp:
        data.font = bpy.data.fonts.load(JP_FONT, check_existing=True)
    obj = bpy.data.objects.new("Text_" + body[:6], data)
    obj.location, obj.rotation_euler = loc, rot
    scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def box(name, size, loc, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        m = o.modifiers.new("bevel", "BEVEL")
        m.width, m.segments = bevel, 3
        m.limit_method = "ANGLE"
    assign(o, mat)
    return o


def cyl(name, r, depth, loc, mat, rot=(0, 0, 0), verts=48, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    if bevel:
        m = o.modifiers.new("bevel", "BEVEL")
        m.width, m.segments = bevel, 3
        m.limit_method = "ANGLE"
    smooth(o)
    for p in o.data.polygons:  # 平らな面はフラットに戻す
        if abs(p.normal.z) > 0.9 and rot == (0, 0, 0):
            p.use_smooth = False
    assign(o, mat)
    return o


def shake(obj, start, end, amp, base, every=2, decay=True, seed=0):
    """start〜end の間、obj の位置を小刻みに揺らす(地震の揺れ)。"""
    import random
    rnd = random.Random(seed)
    key(obj, "location", start, base, "LINEAR")
    for fr in range(start + every, end, every):
        k = amp * ((1 - (fr - start) / max(1, end - start)) if decay else 1.0)
        key(obj, "location", fr, tuple(b + rnd.uniform(-k, k) for b in base), "LINEAR")
    key(obj, "location", end, base, "BEZIER")
