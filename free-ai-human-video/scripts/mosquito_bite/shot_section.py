"""カット4・7:皮膚の断面(表皮・真皮・皮下脂肪、毛細血管、毛包)。

mode: search(針がしなりながら血管を探し当てる)/ react(唾液に体が反応してヒスタミンが出て、皮膚が腫れる)
"""
import math
import random

import bpy

from common import (add_bump, assign, camera, color_variation, curve_tube, key, key_point, light, principled,
                    reset_scene, smooth)

FRONT = -3.0  # 断面(手前の切り口)の y 座標
VESSEL = (0.9, -1.45)  # 針が届く毛細血管の (x, z)


def layer_box(scene, name, z_top, z_bottom, mat, swell=None):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object
    o.name = name
    o.scale = (12, 6, z_top - z_bottom)
    o.location = (0, 0, (z_top + z_bottom) / 2)
    bpy.ops.object.transform_apply(scale=True)
    if swell is not None:  # 腫れで上面が盛り上がるように細かく分割してから変形させる
        m = o.modifiers.new("subdiv", "SUBSURF")
        m.subdivision_type = "SIMPLE"
        m.levels = m.render_levels = 6
        empty, tex = swell
        d = o.modifiers.new("swell", "DISPLACE")
        d.texture, d.texture_coords, d.texture_coords_object = tex, "OBJECT", empty
        d.mid_level, d.strength, d.direction = 0.0, 0.0, "Z"
    assign(o, mat)
    return o


def skin_block(scene, swell):
    epi = principled("Epidermis", (0.86, 0.66, 0.55), rough=0.5, sss=0.8, sss_radius=(1, 0.5, 0.3), sss_scale=0.15)
    color_variation(epi, (0.8, 0.6, 0.5), (0.92, 0.74, 0.62), scale=3)
    add_bump(epi, scale=9, strength=0.4, kind="voronoi", voronoi_feature="DISTANCE_TO_EDGE")  # 細胞の並び
    derm = principled("Dermis", (0.86, 0.5, 0.48), rough=0.45, sss=0.7, sss_radius=(1, 0.4, 0.3), sss_scale=0.2)
    color_variation(derm, (0.8, 0.42, 0.42), (0.95, 0.62, 0.58), scale=1.5)
    add_bump(derm, scale=3, strength=0.5, kind="wave", detail=8)  # 繊維
    fat_mat = principled("Fat", (0.95, 0.8, 0.35), rough=0.3, sss=0.9, sss_radius=(1, 0.8, 0.4), sss_scale=0.3, coat=0.4)
    horny = principled("StratumCorneum", (0.92, 0.8, 0.7), rough=0.7)
    add_bump(horny, scale=6, strength=0.6)

    blocks = [layer_box(scene, "Horny", 0.0, -0.12, horny, swell),
              layer_box(scene, "Epidermis", -0.12, -0.6, epi, swell),
              layer_box(scene, "Dermis", -0.6, -3.6, derm, swell),
              layer_box(scene, "FatBase", -3.6, -7.0, fat_mat)]
    random.seed(4)
    for i in range(70):  # 脂肪の粒(切り口から少し飛び出す)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(0.45, 0.7),
                                             location=(random.uniform(-6, 6), FRONT + random.uniform(0.0, 0.25),
                                                       random.uniform(-6.8, -3.9)))
        o = bpy.context.active_object
        smooth(o)
        assign(o, fat_mat)

    # 毛細血管(切り口に半分埋まった赤い管)と、真皮乳頭へ上がるループ
    blood = principled("Vessel", (0.6, 0.05, 0.05), rough=0.3, sss=0.6, sss_radius=(1, 0.2, 0.1), sss_scale=0.1, coat=0.6)
    vein = principled("Vein", (0.3, 0.08, 0.2), rough=0.3, sss=0.5, sss_scale=0.1, coat=0.5)
    y = FRONT + 0.02
    curve_tube(scene, "Plexus", [(-6, y, -1.6), (-2.5, y, -1.35), (VESSEL[0], y, VESSEL[1]), (3.5, y, -1.6), (6, y, -1.4)], 0.13, blood)
    curve_tube(scene, "DeepArtery", [(-6, y, -3.3), (-2, y, -3.1), (2, y, -3.35), (6, y, -3.2)], 0.24, blood)
    curve_tube(scene, "DeepVein", [(-6, y, -3.0), (-1.5, y, -2.8), (2.5, y, -3.0), (6, y, -2.85)], 0.2, vein)
    for x in (-4.6, -3.3, -1.9, -0.6, 2.2, 3.4, 4.7):
        curve_tube(scene, f"Loop{x}", [(x - 0.25, y, -1.5), (x - 0.2, y, -0.75), (x + 0.2, y, -0.75), (x + 0.25, y, -1.5)], 0.06, blood, order=3)
    # 毛包と毛
    sheath = principled("Follicle", (0.92, 0.75, 0.62), rough=0.5, sss=0.8, sss_scale=0.1)
    hair = principled("HairShaft", (0.12, 0.07, 0.04), rough=0.3)
    x = -3.9
    curve_tube(scene, "FollicleSheath", [(x, y, 0.0), (x - 0.15, y, -1.5), (x - 0.35, y, -2.9)], 0.22, sheath, order=3)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.38, location=(x - 0.38, y, -3.05))
    smooth(bpy.context.active_object)
    assign(bpy.context.active_object, sheath)
    curve_tube(scene, "HairShaft", [(x + 0.6, y - 0.3, 3.5), (x + 0.15, y, 0.6), (x - 0.15, y, -1.5), (x - 0.35, y, -2.8)], 0.08, hair, order=3)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(x + 0.4, y, -0.9))  # 皮脂腺
    o = bpy.context.active_object
    o.scale = (1.2, 0.6, 0.9)
    smooth(o)
    assign(o, fat_mat)
    return blocks


def proboscis(scene):
    """皮膚の上:く の字に曲がった鞘と、皮膚に入っていく針の束。"""
    labium_mat = principled("Labium", (0.05, 0.04, 0.035), rough=0.35, coat=0.3)
    stylet = principled("Stylet", (0.62, 0.38, 0.14), rough=0.2, sss=0.5, sss_scale=0.03, coat=0.9,
                        emission=0.4, emission_color=(1.0, 0.6, 0.2))
    y = FRONT - 0.05
    curve_tube(scene, "Labium", [(0.4, y, 6.5), (-0.9, y, 3.6), (-1.4, y, 1.4), (0.0, y, 0.1)], 0.13, labium_mat)
    bundle, sp = curve_tube(scene, "Bundle", [(0.4, y, 6.5), (0.25, y, 3.0), (0.0, y, 0.5), (0.0, y, 0.0),
                                              (0.0, y, -0.4), (0.0, y, -0.8)], 0.06, stylet)
    return sp


def build(mode, frames):
    scene = reset_scene(frames)
    w = scene.world.node_tree.nodes["Background"]
    w.inputs["Color"].default_value = (0.03, 0.025, 0.03, 1)
    swell_empty = bpy.data.objects.new("SwellCenter", None)
    swell_empty.location = (0.3, FRONT, 0.0)
    swell_empty.scale = (3.2, 3.2, 3.2)
    scene.collection.objects.link(swell_empty)
    tex = bpy.data.textures.new("Swell", "BLEND")
    tex.progression = "SPHERICAL"
    blocks = skin_block(scene, (swell_empty, tex))
    sp = proboscis(scene)
    y = FRONT - 0.05

    light(scene, "AREA", "Key", (-6, -9, 7), 1500, (1.0, 0.93, 0.86), size=6, look_at=(0, FRONT, -1.5))
    light(scene, "AREA", "Rim", (6, -4, 6), 600, (0.85, 0.9, 1.0), size=4, look_at=(0, FRONT, 0))
    cam, target = camera(scene, "Cam", (0.3, -15.0, -0.4), (0.3, FRONT, -1.2), lens=50, fstop=4.0)

    # 針先の通り道(しなりながら左右を探り、最後に血管に届く)
    path_search = [
        [(0.0, y, 0.0), (0.0, y, -0.4), (0.0, y, -0.8)],
        [(-0.1, y, -0.1), (-0.5, y, -0.6), (-0.9, y, -1.0)],
        [(0.05, y, -0.1), (0.2, y, -0.6), (0.1, y, -1.2)],
        [(0.05, y, -0.15), (0.45, y, -0.75), (VESSEL[0] - 0.1, y, VESSEL[1] + 0.05)],
    ]
    if mode == "search":
        key(cam, "location", 1, (0.3, -16.0, -0.2))
        key(cam, "location", frames, (0.6, -11.5, -1.0))
        key(target, "location", 1, (0.2, FRONT, -1.0))
        key(target, "location", frames, (0.6, FRONT, -1.3))
        marks = [1, int(frames * 0.35), int(frames * 0.62), int(frames * 0.9)]
        for fr, pts in zip(marks, path_search):
            for p, co in zip(sp.points[3:], pts):
                key_point(p, fr, co)
    else:  # react
        for p, co in zip(sp.points[3:], path_search[-1]):
            p.co = (*co, 1.0)
        key(cam, "location", 1, (0.5, -12.5, -0.6))
        key(cam, "location", frames, (0.3, -14.5, 0.0))
        target.location = (0.5, FRONT, -1.0)
        random.seed(8)
        saliva = principled("Saliva", (0.55, 1.0, 0.3), rough=0.3, emission=2.0, alpha=0.8)
        hist = principled("Histamine", (1.0, 0.85, 0.2), rough=0.3, emission=3.0)
        mast = principled("MastCell", (0.55, 0.3, 0.7), rough=0.4, sss=0.6, sss_scale=0.1)
        add_bump(mast, scale=10, strength=0.6)
        # 血管のまわりに残った唾液
        for i in range(60):
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.03, 0.07),
                                                  location=(VESSEL[0] + random.gauss(0, 0.35), y - 0.03,
                                                            VESSEL[1] + random.gauss(0, 0.3)))
            assign(bpy.context.active_object, saliva)
        # 肥満細胞が反応して、ヒスタミン(黄色い粒)を放出する
        for c, (mx, mz) in enumerate([(-0.4, -1.1), (1.9, -1.0), (0.4, -2.2), (2.2, -2.0), (-1.2, -1.9)]):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.28, location=(mx, y + 0.05, mz))
            cell = bpy.context.active_object
            smooth(cell)
            assign(cell, mast)
            t0 = int(frames * 0.12) + c * 6
            key(cell, "scale", t0, (1, 1, 1))
            key(cell, "scale", t0 + 8, (1.25, 1.25, 1.25))
            key(cell, "scale", t0 + 16, (0.85, 0.85, 0.85))
            for k in range(26):
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.03, 0.06), location=(mx, y - 0.05, mz))
                g = bpy.context.active_object
                assign(g, hist)
                a = random.uniform(0, math.tau)
                r = random.uniform(0.6, 2.0)
                key(g, "scale", 1, (0, 0, 0), "CONSTANT")
                key(g, "scale", t0 + 8, (1, 1, 1))
                key(g, "location", t0 + 8, (mx, y - 0.05, mz))
                key(g, "location", frames, (mx + r * math.cos(a), y - 0.05, mz + r * math.sin(a) * 0.7))
        # 皮膚がぷくっと腫れる
        for b in blocks[:3]:
            d = b.modifiers["swell"]
            key(d, "strength", int(frames * 0.3), 0.0)
            key(d, "strength", frames, 0.55)
    return scene
