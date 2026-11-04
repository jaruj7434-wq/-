"""Higgs Field で作った動物の3Dモデル(GLB)を軽くして大きさをそろえる。
各モデルを1つのメッシュにまとめ、ポリゴンを減らし(描画を速くする)、中心を原点・いちばん長い辺を1にして保存する。

    python prep_models.py   # assets/source/race3d/*.glb → assets/source/race3d/prep/*.glb
"""
import os
import sys

import bpy
import mathutils

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "source", "race3d")
NAMES = ["hamster", "rabbit", "penguin", "shiba", "pig", "gorilla"]
TARGET_FACES = 60000

os.makedirs(os.path.join(SRC, "prep"), exist_ok=True)
for n in NAMES:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, n + ".glb"))
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in bpy.data.objects:
        o.select_set(o.type == 'MESH')
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    if len(meshes) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    faces = len(o.data.polygons)
    if faces > TARGET_FACES:
        m = o.modifiers.new("dec", 'DECIMATE')
        m.ratio = TARGET_FACES / faces
        bpy.ops.object.modifier_apply(modifier="dec")
    pts = [mathutils.Vector(c) for c in o.bound_box]
    mn = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    size = max(mx - mn)
    o.data.transform(mathutils.Matrix.Scale(1 / size, 4) @ mathutils.Matrix.Translation(-(mn + mx) / 2))
    for x in list(bpy.data.objects):
        if x is not o:
            bpy.data.objects.remove(x)
    bpy.ops.export_scene.gltf(filepath=os.path.join(SRC, "prep", n + ".glb"), use_selection=False)
    print(n, faces, "->", len(o.data.polygons), "size", [round(v / size, 2) for v in (mx - mn)])
