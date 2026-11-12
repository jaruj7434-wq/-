"""モノの一生 3Dショット共通部品(bpy 5.3 / EEVEE)。

単位: 1 Blender単位 = 1cm(1円玉=直径2cm=半径1.0)。
各ショットは build(sc) でシーンを組み、run_shot(name, build, frames) で書き出す。
"""
import argparse, math, random, sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = ROOT / "assets/output/mono_no_issho/ep01/3d"
TEX = ROOT / "assets/output/mono_no_issho/ep01/tex"
FPS = 24


# ------------------------------------------------------------------ シーン基本
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.unit_settings.scale_length = 0.01
    return sc


def world(color=(0.02, 0.02, 0.022), strength=1.0):
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength
    return w


def setup_render(sc, res=(960, 540), samples=8, engine="EEVEE", exposure=0.0):
    if engine == "CYCLES":
        sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
        sc.cycles.samples = samples; sc.cycles.use_denoising = True
    else:
        sc.render.engine = "BLENDER_EEVEE"
        sc.eevee.taa_render_samples = samples
        for attr, val in (("use_raytracing", True), ("use_shadows", True)):
            if hasattr(sc.eevee, attr):
                setattr(sc.eevee, attr, val)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = exposure
    sc.render.image_settings.file_format = "PNG"


# ------------------------------------------------------------------ ノード補助
def node_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def link(nt, a, b):
    nt.links.new(a, b)


def principled(name, color, metallic=0.0, rough=0.5, noise_rough=None, bump=0.0, bump_scale=20.0,
               emission=None, emission_strength=0.0, alpha=1.0, transmission=0.0, ior=1.45, coat=0.0):
    """汎用マテリアル。noise_rough=(min,max)で粗さムラ、bump>0で微細な凹凸。"""
    m, nt, out = node_mat(name)
    n = nt.nodes
    p = n.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, 1) if len(color) == 3 else color
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = rough
    p.inputs["Alpha"].default_value = alpha
    p.inputs["IOR"].default_value = ior
    if transmission:
        p.inputs["Transmission Weight"].default_value = transmission
    if coat:
        p.inputs["Coat Weight"].default_value = coat
    if noise_rough or bump:
        nz = n.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = bump_scale; nz.inputs["Detail"].default_value = 8
        if noise_rough:
            mr = n.new("ShaderNodeMapRange")
            mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = noise_rough
            link(nt, nz.outputs["Fac"], mr.inputs["Value"]); link(nt, mr.outputs["Result"], p.inputs["Roughness"])
        if bump:
            b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = bump
            link(nt, nz.outputs["Fac"], b.inputs["Height"]); link(nt, b.outputs["Normal"], p.inputs["Normal"])
    if emission is not None:
        p.inputs["Emission Color"].default_value = (*emission, 1)
        p.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0:
        m.surface_render_method = "BLENDED" if hasattr(m, "surface_render_method") else m.blend_method
    link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def emissive(name, color=None, temp=None, strength=5.0):
    m, nt, out = node_mat(name)
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = strength
    if temp:
        bb = nt.nodes.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = temp
        link(nt, bb.outputs["Color"], em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = (*color, 1)
    link(nt, em.outputs["Emission"], out.inputs["Surface"])
    return m


# ------------------------------------------------------------------ 1円玉
def mat_coin(name="Coin", stamped=True, worn=0.0, heat=False):
    """1円玉(アルミ)。stamped=False で模様なしの「円形(ブランク)」。
    worn(0..1)で使い古し(くすみ・傷・黒ずみ)。heat=True で "Heat" 値ノードにより赤熱。
    stamped を後から切り替えたい時は "Stamp" 値ノード(0/1)をキーフレーム。"""
    m, nt, out = node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (0.5, 0.5, 0)
    mp.inputs["Scale"].default_value = (0.5, 0.5, 1)
    link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    imgs = []
    for side in ("front", "back"):
        t = n.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(str(TEX / f"coin_{side}.png"), check_existing=True)
        t.image.colorspace_settings.name = "Non-Color"
        t.extension = "CLIP"
        link(nt, mp.outputs["Vector"], t.inputs["Vector"])
        imgs.append(t)
    geo = n.new("ShaderNodeNewGeometry"); sep = n.new("ShaderNodeSeparateXYZ")
    vt = n.new("ShaderNodeVectorTransform"); vt.convert_from = "WORLD"; vt.convert_to = "OBJECT"; vt.vector_type = "NORMAL"
    link(nt, geo.outputs["Normal"], vt.inputs["Vector"]); link(nt, vt.outputs["Vector"], sep.inputs["Vector"])
    gt = n.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0
    link(nt, sep.outputs["Z"], gt.inputs[0])
    mix_h = n.new("ShaderNodeMix"); mix_h.data_type = "FLOAT"
    link(nt, gt.outputs[0], mix_h.inputs["Factor"])
    link(nt, imgs[1].outputs["Color"], mix_h.inputs["A"]); link(nt, imgs[0].outputs["Color"], mix_h.inputs["B"])
    ab = n.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; link(nt, sep.outputs["Z"], ab.inputs[0])
    cap = n.new("ShaderNodeMath"); cap.operation = "GREATER_THAN"; cap.inputs[1].default_value = 0.9
    link(nt, ab.outputs[0], cap.inputs[0])
    stamp = n.new("ShaderNodeValue"); stamp.name = "Stamp"; stamp.outputs[0].default_value = 1.0 if stamped else 0.0
    h1 = n.new("ShaderNodeMath"); h1.operation = "MULTIPLY"
    link(nt, mix_h.outputs["Result"], h1.inputs[0]); link(nt, cap.outputs[0], h1.inputs[1])
    h2 = n.new("ShaderNodeMath"); h2.operation = "MULTIPLY"
    link(nt, h1.outputs[0], h2.inputs[0]); link(nt, stamp.outputs[0], h2.inputs[1])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.7 - 0.3 * worn
    bump.inputs["Distance"].default_value = 0.02
    link(nt, h2.outputs[0], bump.inputs["Height"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 60; nz.inputs["Detail"].default_value = 10
    link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    rr = n.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.16 + 0.2 * worn; rr.inputs["To Max"].default_value = 0.38 + 0.3 * worn
    link(nt, nz.outputs["Fac"], rr.inputs["Value"])
    metal = n.new("ShaderNodeBsdfPrincipled")
    metal.inputs["Metallic"].default_value = 1.0
    # 使い古し: 色をくすませ、黒ずみの斑を足す
    dirt = n.new("ShaderNodeTexNoise"); dirt.inputs["Scale"].default_value = 4; dirt.inputs["Detail"].default_value = 6
    link(nt, tc.outputs["Object"], dirt.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[0].color = (0.86, 0.87, 0.88, 1)
    cr.color_ramp.elements[1].position = 0.75
    g = 0.86 - 0.5 * worn
    cr.color_ramp.elements[1].color = (g * 0.95, g * 0.93, g * 0.88, 1)
    link(nt, dirt.outputs["Fac"], cr.inputs["Fac"])
    if worn <= 0:
        cr.color_ramp.elements[1].color = (0.86, 0.87, 0.88, 1)
    link(nt, cr.outputs["Color"], metal.inputs["Base Color"])
    link(nt, rr.outputs["Result"], metal.inputs["Roughness"])
    link(nt, bump.outputs["Normal"], metal.inputs["Normal"])
    final = metal.outputs["BSDF"]
    if heat:
        bb = n.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = 1150
        em = n.new("ShaderNodeEmission"); link(nt, bb.outputs["Color"], em.inputs["Color"])
        hv = n.new("ShaderNodeValue"); hv.name = "Heat"; hv.outputs[0].default_value = 0.0
        st = n.new("ShaderNodeMath"); st.operation = "MULTIPLY"; st.inputs[1].default_value = 6.0
        link(nt, hv.outputs[0], st.inputs[0]); link(nt, st.outputs[0], em.inputs["Strength"])
        add = n.new("ShaderNodeAddShader")
        link(nt, final, add.inputs[0]); link(nt, em.outputs["Emission"], add.inputs[1])
        final = add.outputs["Shader"]
    link(nt, final, out.inputs["Surface"])
    return m


def make_coin(name="Coin", mat=None, location=(0, 0, 0), rotation=(0, 0, 0), verts=96):
    """1円玉(直径2cm, 厚さ1.5mm)。mat省略時は新品の1円玉マテリアルを共有。"""
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=1.0, depth=0.15, location=location, rotation=rotation)
    c = bpy.context.object; c.name = name
    bev = c.modifiers.new("bev", "BEVEL"); bev.width = 0.025; bev.segments = 2; bev.limit_method = "ANGLE"
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    if mat is None:
        mat = bpy.data.materials.get("CoinShared") or mat_coin("CoinShared")
    c.data.materials.append(mat)
    return c


def scatter_coins(n, center=(0, 0, 0), radius=4.0, z_jitter=0.0, seed=1, mat=None, tilt=0.15):
    """平面にばらまいた1円玉(静的)。"""
    rnd = random.Random(seed)
    coins = []
    for i in range(n):
        r = radius * math.sqrt(rnd.random()); a = rnd.uniform(0, math.tau)
        loc = (center[0] + r * math.cos(a), center[1] + r * math.sin(a), center[2] + 0.075 + i * z_jitter)
        rot = (rnd.uniform(-tilt, tilt), rnd.uniform(-tilt, tilt), rnd.uniform(0, math.tau))
        if rnd.random() < 0.5:
            rot = (rot[0] + math.pi, rot[1], rot[2])
        coins.append(make_coin(f"C{i}", mat, loc, rot, verts=48))
    return coins


# ------------------------------------------------------------------ 物理(リジッドボディ)
def rigid_world(sc, frames, substeps=20):
    if sc.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    rw = sc.rigidbody_world
    rw.substeps_per_frame = substeps; rw.solver_iterations = 20
    rw.point_cache.frame_start = 1; rw.point_cache.frame_end = frames
    return rw


def rigid(obj, active=True, shape="CYLINDER", mass=0.001, friction=0.5, bounce=0.2, margin=0.004, kinematic=False):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.rigidbody.object_add(type="ACTIVE" if active else "PASSIVE")
    rb = obj.rigid_body
    rb.collision_shape = shape; rb.mass = mass; rb.friction = friction; rb.restitution = bounce
    rb.use_margin = True; rb.collision_margin = margin
    rb.kinematic = kinematic
    obj.select_set(False)
    return rb


def bake_rigid(sc):
    """物理を先に計算しておく(並列フレーム書き出しでも結果がぶれないように)。"""
    bpy.ops.ptcache.bake_all(bake=True)


# ------------------------------------------------------------------ 照明・カメラ
def area_light(loc, rot_deg, size, energy, color=(1, 1, 1), name="Area"):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.object; l.name = name
    l.data.size = size; l.data.energy = energy; l.data.color = color
    l.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    return l


def point_light(loc, energy, color=(1, 1, 1), radius=1.0, name="Point"):
    bpy.ops.object.light_add(type="POINT", location=loc)
    l = bpy.context.object; l.name = name
    l.data.energy = energy; l.data.color = color; l.data.shadow_soft_size = radius
    return l


def light_look_at(light, target):
    d = Vector(target) - light.location
    light.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(loc, target=(0, 0, 0), lens=50, fstop=None, focus=None):
    """カメラ+注視点Empty。fstop指定で被写界深度(focusはEmptyまたは座標)。戻り値 (cam, target_empty)。"""
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object; bpy.context.scene.camera = cam
    cam.data.lens = lens; cam.data.sensor_width = 36
    cam.data.clip_start = 0.05; cam.data.clip_end = 5000
    bpy.ops.object.empty_add(location=target)
    tgt = bpy.context.object; tgt.name = "CamTarget"
    tr = cam.constraints.new("TRACK_TO"); tr.target = tgt
    if fstop:
        cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = fstop
        cam.data.dof.focus_object = tgt
    return cam, tgt


def key(obj, path, frame, value, interp=None):
    """obj.path = value を frame にキーフレーム。"""
    setattr(obj, path, value)
    obj.keyframe_insert(path, frame=frame)


def ease_all(obj, interp="BEZIER"):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    try:
        curves = ad.action.fcurves
    except AttributeError:  # 5.x layered actions
        curves = [fc for layer in ad.action.layers for strip in layer.strips
                  for bag in strip.channelbags for fc in bag.fcurves]
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = interp


# ------------------------------------------------------------------ 実行
def run_shot(name, build, frames, default_res="960x540", default_samples=8):
    """CLI: --still N / --start --end / --res / --samples / --engine"""
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=int)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=frames)
    ap.add_argument("--samples", type=int, default=default_samples)
    ap.add_argument("--res", default=default_res)
    ap.add_argument("--engine", default="EEVEE")
    ap.add_argument("--step", type=int, default=1, help="2なら1フレームおきに書き出し(12fps相当の下書き)")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    a = ap.parse_args(argv)
    sc = reset()
    sc.frame_start, sc.frame_end = 1, frames
    build(sc)
    w, h = map(int, a.res.split("x"))
    setup_render(sc, (w, h), a.samples, a.engine, exposure=sc.view_settings.exposure)
    out = OUT_ROOT / name
    out.mkdir(parents=True, exist_ok=True)
    if sc.rigidbody_world is not None:
        bake_rigid(sc)
    if a.still:
        sc.frame_set(a.still)
        sc.render.filepath = str(out / f"still_{a.still:04d}.png")
        bpy.ops.render.render(write_still=True)
    else:
        sc.frame_start, sc.frame_end = a.start, a.end
        sc.frame_step = a.step
        sc.render.filepath = str(out / "f_")
        bpy.ops.render.render(animation=True)
