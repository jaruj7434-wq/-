"""カット1・2・8:皮膚表面の超マクロ。蚊(ヒトスジシマカ)の口が近づき、鞘が「く」の字に曲がり、最後は抜けていく。

mode: approach(近づいて触れる)/ bend(鞘が曲がり針が刺さる)/ withdraw(腫れた皮膚から抜ける)
"""
import math
import random

import bpy

from common import add_bump, assign, camera, color_variation, curve_tube, key, key_point, light, principled, reset_scene

CONTACT = (0.0, 0.0, 0.0)


def skin_material(redness_empty=None):
    mat = principled("Skin", (0.72, 0.45, 0.36), rough=0.5, sss=1.0, sss_radius=(1.0, 0.35, 0.2),
                     sss_scale=0.25, coat=0.05)
    ramp = color_variation(mat, (0.62, 0.38, 0.3), (0.8, 0.52, 0.42), scale=0.8)
    add_bump(mat, scale=1.7, strength=0.45, distance=0.06, kind="voronoi", voronoi_feature="DISTANCE_TO_EDGE")  # 皮溝
    add_bump(mat, scale=5.0, strength=0.5, distance=0.04, kind="voronoi", voronoi_feature="F1")  # 毛穴
    add_bump(mat, scale=40.0, strength=0.2, distance=0.01)
    if redness_empty is not None:  # 腫れた部分を赤くする
        n, l = mat.node_tree.nodes, mat.node_tree.links
        tc = n.new("ShaderNodeTexCoord")
        tc.object = redness_empty
        grad = n.new("ShaderNodeTexGradient")
        grad.gradient_type = "SPHERICAL"
        l.new(tc.outputs["Object"], grad.inputs["Vector"])
        mix = n.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["B"].default_value = (0.85, 0.28, 0.25, 1)
        l.new(grad.outputs["Fac"], mix.inputs["Factor"])
        l.new(ramp.outputs["Color"], mix.inputs["A"])
        l.new(mix.outputs["Result"], n["Principled BSDF"].inputs["Base Color"])
    return mat


def build_skin(scene, swell=None):
    """swell: (empty, displace_modifier) を返す。腫れを動かすときに使う。"""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=260, y_subdivisions=260, size=14)
    skin = bpy.context.active_object
    tex = bpy.data.textures.new("SkinUndulation", "CLOUDS")
    tex.noise_scale = 1.5
    d = skin.modifiers.new("undulation", "DISPLACE")
    d.texture, d.strength, d.mid_level = tex, 0.12, 0.5
    bump_empty = bpy.data.objects.new("SwellCenter", None)
    bump_empty.location = CONTACT
    bump_empty.scale = (2.2, 2.2, 2.2)
    scene.collection.objects.link(bump_empty)
    btex = bpy.data.textures.new("Swell", "BLEND")
    btex.progression = "SPHERICAL"
    sw = skin.modifiers.new("swell", "DISPLACE")
    sw.texture, sw.texture_coords, sw.texture_coords_object = btex, "OBJECT", bump_empty
    sw.mid_level, sw.strength, sw.direction = 0.0, 0.0, "Z"
    for p in skin.data.polygons:
        p.use_smooth = True
    assign(skin, skin_material(bump_empty if swell else None))

    # 産毛
    hair_mat = principled("Hair", (0.35, 0.22, 0.12), rough=0.3, sss=0.3, sss_scale=0.02)
    skin.data.materials.append(hair_mat)
    mod = skin.modifiers.new("hairs", "PARTICLE_SYSTEM")
    st = mod.particle_system.settings
    st.type = "HAIR"
    st.count = 45
    st.hair_length = 1.1
    st.use_advanced_hair = True
    st.normal_factor = 0.6
    st.factor_random = 0.6
    st.tangent_factor = 0.8
    st.material_slot = "Hair"
    st.root_radius, st.tip_radius, st.radius_scale = 1.0, 0.2, 0.014
    st.child_type = "NONE"
    mod.particle_system.seed = 3
    return skin, bump_empty, sw


def build_mosquito(scene):
    """口吻(鞘+針の束)と脚。root を動かすと全体が動く。"""
    root = bpy.data.objects.new("Mosquito", None)
    scene.collection.objects.link(root)
    labium_mat = principled("Labium", (0.05, 0.04, 0.035), rough=0.35, coat=0.3)
    add_bump(labium_mat, scale=30, strength=0.4)  # 鱗片
    stylet_mat = principled("Stylet", (0.55, 0.33, 0.12), rough=0.2, sss=0.5, sss_radius=(1, 0.6, 0.3),
                            sss_scale=0.03, coat=0.9)
    labium, lsp = curve_tube(scene, "Labium", [(0, 0.5, 7.0), (0, 0.3, 4.6), (0, 0.12, 2.2), (0, 0.0, 0.08)],
                             0.075, labium_mat)
    labium.parent = root
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(0, 0, 0.08))  # 先端の唇弁
    tip = bpy.context.active_object
    tip.scale = (1.0, 0.8, 0.7)
    for p in tip.data.polygons:
        p.use_smooth = True
    assign(tip, labium_mat)
    tip.parent = root
    stylet, ssp = curve_tube(scene, "Stylets", [(0, 0.5, 7.0), (0, 0.3, 4.6), (0, 0.12, 2.2), (0, 0.0, 0.0)],
                             0.032, stylet_mat)
    stylet.parent = root

    # 脚(白黒のしま模様)
    leg_mat = principled("Leg", (0.03, 0.03, 0.03), rough=0.4)
    n, l = leg_mat.node_tree.nodes, leg_mat.node_tree.links
    tc = n.new("ShaderNodeTexCoord")
    wave = n.new("ShaderNodeTexWave")
    wave.wave_type, wave.bands_direction = "BANDS", "Z"
    wave.wave_profile = "SAW"
    wave.inputs["Scale"].default_value = 0.9
    l.new(tc.outputs["Object"], wave.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = (0.02, 0.02, 0.02, 1)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = (0.9, 0.9, 0.88, 1)
    l.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], n["Principled BSDF"].inputs["Base Color"])
    random.seed(5)
    for i, ang in enumerate([165, 115, 65, 15]):  # 後ろ側の脚だけ見せる
        a = math.radians(ang)
        foot = (3.2 * math.cos(a), 3.2 * math.sin(a) + 1.2, 0.02)
        knee = (foot[0] * 0.9, foot[1] * 0.9 + 0.3, 2.6 + random.uniform(-0.3, 0.4))
        body = (foot[0] * 0.25, 0.9 + foot[1] * 0.15, 6.5)
        leg, _ = curve_tube(scene, f"Leg{i}", [body, knee, (foot[0] * 1.05, foot[1] * 1.05, 0.9), foot], 0.022, leg_mat, order=3)
        leg.parent = root
    return root, labium, lsp, tip, stylet, ssp


def build(mode, frames):
    scene = reset_scene(frames)
    w = scene.world.node_tree.nodes["Background"]
    w.inputs["Color"].default_value = (0.08, 0.04, 0.03, 1)
    w.inputs["Strength"].default_value = 0.4
    skin, swell_empty, swell = build_skin(scene, swell=(mode == "withdraw"))
    root, labium, lsp, tip, stylet, ssp = build_mosquito(scene)

    light(scene, "AREA", "Key", (-4, -3, 6), 260, (1.0, 0.92, 0.85), size=3, look_at=(0, 0, 0))
    light(scene, "AREA", "Rim", (2, 6, 2.5), 420, (1.0, 0.8, 0.65), size=2, look_at=(0, 0, 1))
    light(scene, "AREA", "Fill", (5, -5, 2), 50, (0.8, 0.85, 1.0), size=5, look_at=(0, 0, 0))

    focus = bpy.data.objects.new("Focus", None)
    scene.collection.objects.link(focus)
    focus.location = (0, 0, 0.3)
    cam, target = camera(scene, "Cam", (0, -4.0, 4.2), (0, 0, 0.6), lens=50, fstop=2.0, focus=focus)

    if mode == "approach":
        key(root, "location", 1, (0.4, 0.8, 2.2))
        key(root, "location", int(frames * 0.8), (0, 0, 0))
        key(cam, "location", 1, (0.4, -4.8, 5.2))
        key(cam, "location", frames, (0.0, -3.7, 3.8))
        key(target, "location", 1, (0, 0, 1.0))
        key(target, "location", frames, (0, 0, 0.5))
        key(focus, "location", 1, (0.4, 0.8, 2.4))
        key(focus, "location", int(frames * 0.8), (0, 0, 0.3))
    elif mode == "bend":
        target.location = (-0.3, 0, 1.0)
        key(cam, "location", 1, (-0.4, -4.0, 3.8))
        key(cam, "location", frames, (-0.2, -3.5, 3.3))
        start, end = int(frames * 0.15), int(frames * 0.85)
        # 鞘の中ほどを手前に押し出して「く」の字にする。先端は皮膚に触れたまま
        bent = [(0, 0.5, 7.0), (-0.7, 0.3, 4.4), (-1.25, 0.12, 1.7), (0, 0.0, 0.08)]  # 横(画面左)に曲げる
        straight = [(0, 0.5, 7.0), (0, 0.3, 4.6), (0, 0.12, 2.2), (0, 0.0, 0.08)]
        for p, a, b in zip(lsp.points, straight, bent):
            key_point(p, start, a)
            key_point(p, end, b)
        # 針の束は皮膚の中へ沈んでいく(皮膚より下は見えない)
        for p, (x, y, z) in zip(ssp.points, [(0, 0.5, 7.0), (0, 0.3, 4.6), (0, 0.12, 2.2), (0, 0.0, 0.0)]):
            key_point(p, start, (x, y, z))
            key_point(p, frames, (x * 0.5, y * 0.4, z - 1.2 if z < 1 else z - 0.6))
    else:  # withdraw:腫れて赤くなった皮膚から、口を抜いて飛び去る
        bent = [(0, 0.5, 7.0), (-0.7, 0.3, 4.4), (-1.25, 0.12, 1.7), (0, 0.0, 0.08)]
        for p, co in zip(lsp.points, bent):
            p.co = (*co, 1.0)
        key(swell, "strength", 1, 0.25)
        key(swell, "strength", frames, 0.55)
        key(root, "location", 1, (0, 0, 0.1))
        key(root, "location", int(frames * 0.35), (0, 0, 0.35))
        key(root, "location", frames, (1.5, 2.0, 7.5))
        key(cam, "location", 1, (0.0, -3.8, 3.8))
        key(cam, "location", frames, (0.0, -4.8, 5.0))
        target.location = (0, 0, 0.6)
        focus.location = (0, 0, 0.4)
    return scene
