"""第1話 カット5-3 / 1-3「1円玉が炉の中で溶ける」— Blender(bpy) + Cycles で作る3Dショット。

使い方:
  python3 scripts/mono_no_issho/3d/shot_melt.py --still 70          # 1フレームだけ確認
  python3 scripts/mono_no_issho/3d/shot_melt.py --start 1 --end 120 # 連番PNGを書き出し
単位: 1 Blender単位 = 1cm(1円玉は直径2cm = 半径1.0)
"""
import argparse, math, random, sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/output/mono_no_issho/ep01/shot_melt"
TEX = ROOT / "assets/output/mono_no_issho/ep01/tex"
FPS = 24
FRAMES = 120  # 5秒


# ---------------------------------------------------------------- ユーティリティ
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def node_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def link(nt, a, b):
    nt.links.new(a, b)


# ---------------------------------------------------------------- マテリアル
def mat_coin(name):
    """アルミ(1円玉)。表裏ハイトマップでバンプ、Heat(0→1)で赤熱。"""
    m, nt, out = node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    # オブジェクト座標(-1..1)→UV(0..1)
    mp = n.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (0.5, 0.5, 0)
    mp.inputs["Scale"].default_value = (0.5, 0.5, 1)
    link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    imgs = []
    for side in ("front", "back"):
        t = n.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(str(TEX / f"coin_{side}.png"))
        t.image.colorspace_settings.name = "Non-Color"
        t.extension = "CLIP"
        link(nt, mp.outputs["Vector"], t.inputs["Vector"])
        imgs.append(t)
    # 裏面は左右反転して貼る
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ")
    link(nt, geo.outputs["Normal"], sep.inputs["Vector"])
    # 法線zの符号で表裏を選ぶ
    gt = n.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0
    link(nt, sep.outputs["Z"], gt.inputs[0])
    mix_h = n.new("ShaderNodeMix"); mix_h.data_type = "FLOAT"
    link(nt, gt.outputs[0], mix_h.inputs["Factor"])
    link(nt, imgs[1].outputs["Color"], mix_h.inputs["A"])
    link(nt, imgs[0].outputs["Color"], mix_h.inputs["B"])
    # 側面ではバンプを切る
    ab = n.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"
    link(nt, sep.outputs["Z"], ab.inputs[0])
    cap = n.new("ShaderNodeMath"); cap.operation = "GREATER_THAN"; cap.inputs[1].default_value = 0.9
    link(nt, ab.outputs[0], cap.inputs[0])
    hmul = n.new("ShaderNodeMath"); hmul.operation = "MULTIPLY"
    link(nt, mix_h.outputs["Result"], hmul.inputs[0]); link(nt, cap.outputs[0], hmul.inputs[1])
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.02
    link(nt, hmul.outputs[0], bump.inputs["Height"])
    # 使い込まれた細かな傷(粗さのムラ)
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 60; nz.inputs["Detail"].default_value = 8
    rr = n.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.18; rr.inputs["To Max"].default_value = 0.42
    link(nt, nz.outputs["Fac"], rr.inputs["Value"])
    metal = n.new("ShaderNodeBsdfPrincipled")
    metal.inputs["Base Color"].default_value = (0.86, 0.87, 0.88, 1)
    metal.inputs["Metallic"].default_value = 1.0
    link(nt, rr.outputs["Result"], metal.inputs["Roughness"])
    link(nt, bump.outputs["Normal"], metal.inputs["Normal"])
    # 赤熱
    bb = n.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = 1150
    em = n.new("ShaderNodeEmission")
    link(nt, bb.outputs["Color"], em.inputs["Color"])
    heat = n.new("ShaderNodeValue"); heat.name = "Heat"; heat.outputs[0].default_value = 0.0
    st = n.new("ShaderNodeMath"); st.operation = "MULTIPLY"; st.inputs[1].default_value = 6.0
    link(nt, heat.outputs[0], st.inputs[0]); link(nt, st.outputs[0], em.inputs["Strength"])
    add = n.new("ShaderNodeAddShader")
    link(nt, metal.outputs["BSDF"], add.inputs[0]); link(nt, em.outputs["Emission"], add.inputs[1])
    link(nt, add.outputs["Shader"], out.inputs["Surface"])
    return m


def mat_molten():
    """溶けたアルミ: 銀色の液体金属+薄い酸化膜(ドロス)+炉の熱で鈍く赤く光る。"""
    m, nt, out = node_mat("Molten")
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = 0.35; nz.inputs["Detail"].default_value = 6; nz.inputs["Roughness"].default_value = 0.6
    link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    w = nz.inputs["W"]
    w.default_value = 0
    # ドロス(灰色の膜)の分布
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.48; cr.color_ramp.elements[0].color = (0, 0, 0, 1)
    cr.color_ramp.elements[1].position = 0.62; cr.color_ramp.elements[1].color = (1, 1, 1, 1)
    link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    liquid = n.new("ShaderNodeBsdfPrincipled")
    liquid.inputs["Base Color"].default_value = (0.92, 0.9, 0.86, 1)
    liquid.inputs["Metallic"].default_value = 1.0
    liquid.inputs["Roughness"].default_value = 0.12
    dross = n.new("ShaderNodeBsdfPrincipled")
    dross.inputs["Base Color"].default_value = (0.16, 0.15, 0.14, 1)
    dross.inputs["Metallic"].default_value = 0.4
    dross.inputs["Roughness"].default_value = 0.7
    mix = n.new("ShaderNodeMixShader")
    link(nt, cr.outputs["Color"], mix.inputs["Fac"])
    link(nt, liquid.outputs["BSDF"], mix.inputs[1]); link(nt, dross.outputs["BSDF"], mix.inputs[2])
    bb = n.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = 1000
    em = n.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 0.15
    link(nt, bb.outputs["Color"], em.inputs["Color"])
    add = n.new("ShaderNodeAddShader")
    link(nt, mix.outputs["Shader"], add.inputs[0]); link(nt, em.outputs["Emission"], add.inputs[1])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15
    link(nt, nz.outputs["Fac"], bump.inputs["Height"])
    for b in (liquid, dross):
        link(nt, bump.outputs["Normal"], b.inputs["Normal"])
    link(nt, add.outputs["Shader"], out.inputs["Surface"])
    # 表面がゆっくり流れるようにWを動かす
    w.keyframe_insert("default_value", frame=1)
    w.default_value = 1.2
    w.keyframe_insert("default_value", frame=FRAMES)
    return m


def mat_crucible():
    """るつぼ: 黒鉛・耐火物の煤けた質感、縁は熱で赤い。"""
    m, nt, out = node_mat("Crucible")
    n = nt.nodes
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3; nz.inputs["Detail"].default_value = 10
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.035, 0.032, 0.03, 1)
    cr.color_ramp.elements[1].color = (0.16, 0.13, 0.11, 1)
    link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.85
    link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.5
    link(nt, nz.outputs["Fac"], bump.inputs["Height"]); link(nt, bump.outputs["Normal"], p.inputs["Normal"])
    # 高さ(Z)が高いほど=縁ほど熱く光る…ではなく内側上部が光るよう Object Z で
    tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ")
    link(nt, tc.outputs["Object"], sep.inputs["Vector"])
    mr = n.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 1.6; mr.inputs["From Max"].default_value = 4.0
    mr.inputs["To Min"].default_value = 0.18; mr.inputs["To Max"].default_value = 0.0
    # 外壁は光らせない(法線が外向き=るつぼ外側)
    geo = n.new("ShaderNodeNewGeometry"); dotn = n.new("ShaderNodeVectorMath"); dotn.operation = "DOT_PRODUCT"
    link(nt, geo.outputs["Normal"], dotn.inputs[0]); link(nt, geo.outputs["Position"], dotn.inputs[1])
    inward = n.new("ShaderNodeMath"); inward.operation = "LESS_THAN"; inward.inputs[1].default_value = 0
    link(nt, dotn.outputs["Value"], inward.inputs[0])
    mr2 = n.new("ShaderNodeMath"); mr2.operation = "MULTIPLY"
    link(nt, mr.outputs["Result"], mr2.inputs[0]); link(nt, inward.outputs[0], mr2.inputs[1])
    link(nt, sep.outputs["Z"], mr.inputs["Value"])
    bb = n.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = 1100
    em = n.new("ShaderNodeEmission")
    link(nt, bb.outputs["Color"], em.inputs["Color"]); link(nt, mr2.outputs[0], em.inputs["Strength"])
    add = n.new("ShaderNodeAddShader")
    link(nt, p.outputs["BSDF"], add.inputs[0]); link(nt, em.outputs["Emission"], add.inputs[1])
    link(nt, add.outputs["Shader"], out.inputs["Surface"])
    return m


def mat_emit(name, temp, strength):
    m, nt, out = node_mat(name)
    bb = nt.nodes.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = temp
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = strength
    link(nt, bb.outputs["Color"], em.inputs["Color"])
    link(nt, em.outputs["Emission"], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- オブジェクト
def make_coin(name, mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=160, radius=1.0, depth=0.15)
    c = bpy.context.object; c.name = name
    bev = c.modifiers.new("bev", "BEVEL"); bev.width = 0.02; bev.segments = 3; bev.limit_method = "ANGLE"
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    c.data.materials.append(mat)
    return c


def make_crucible():
    # 外側と内側の円柱をブーリアンで抜いて「器」にする
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=9.0, depth=8.0, location=(0, 0, -2.0))
    outer = bpy.context.object; outer.name = "Crucible"
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=8.0, depth=8.0, location=(0, 0, -1.2))
    inner = bpy.context.object
    b = outer.modifiers.new("cut", "BOOLEAN"); b.object = inner; b.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = outer
    bpy.ops.object.modifier_apply(modifier="cut")
    bpy.data.objects.remove(inner)
    bev = outer.modifiers.new("bev", "BEVEL"); bev.width = 0.25; bev.segments = 4
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    outer.data.materials.clear()
    outer.data.materials.append(mat_crucible())
    return outer


def make_pool(impacts):
    import bmesh
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=320, y_subdivisions=320, size=16.4, location=(0, 0, 0))
    p = bpy.context.object; p.name = "Pool"
    bm = bmesh.new(); bm.from_mesh(p.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.xy.length > 8.15], context="VERTS")
    bm.to_mesh(p.data); bm.free()
    # 落下点ごとに波紋(Waveモディファイア)
    for i, (x, y, f) in enumerate(impacts):
        w = p.modifiers.new(f"wave{i}", "WAVE")
        w.use_x = w.use_y = True
        w.start_position_x, w.start_position_y = x, y
        w.time_offset = f
        w.height = 0.035; w.width = 1.6; w.speed = 0.12; w.narrowness = 1.2
        w.use_normal = False
        w.damping_time = 40; w.falloff_radius = 6
        w.lifetime = 60
    bpy.ops.object.shade_smooth()
    p.data.materials.append(mat_molten())
    return p


def make_sparks(pool):
    """湯面から立ちのぼる小さな火花。"""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.025, location=(0, -50, 0))
    sp = bpy.context.object; sp.name = "SparkInst"
    sp.data.materials.append(mat_emit("Spark", 2200, 60))
    ps_mod = pool.modifiers.new("sparks", "PARTICLE_SYSTEM")
    ps = ps_mod.particle_system.settings
    ps.count = 260; ps.frame_start = 1; ps.frame_end = FRAMES; ps.lifetime = 30; ps.lifetime_random = 0.6
    ps.normal_factor = 3.5; ps.factor_random = 2.0; ps.effector_weights.gravity = 0.15
    ps.render_type = "OBJECT"; ps.instance_object = sp; ps.particle_size = 1.0; ps.size_random = 0.7
    ps.use_rotations = False
    # 粒子系はモディファイアの最後(波の後)だとメッシュが重いので順番を前へ
    return sp


# ---------------------------------------------------------------- シーン
def build(res=(1280, 720), samples=64):
    reset()
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, FRAMES
    sc.unit_settings.scale_length = 0.01

    random.seed(7)
    # 1円玉の落下スケジュール: (着水x, 着水y, 着水フレーム)
    impacts = []
    for i in range(max(9, (FRAMES - 60) // 9)):
        r = random.uniform(0.5, 4.5); a = random.uniform(0, math.tau)
        impacts.append((r * math.cos(a), r * math.sin(a), 14 + i * 9 + random.randint(-3, 3)))

    make_crucible()
    pool = make_pool(impacts)
    make_sparks(pool)

    # コインを落とす → 湯に沈みながら赤熱して消える
    for i, (x, y, f) in enumerate(impacts):
        mat = mat_coin(f"Coin{i}")
        c = make_coin(f"Coin{i}", mat)
        start = Vector((x * 0.4 - 2.0, y * 0.4 + 6.0, 12.0))
        rot0 = (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0, 6))
        fall = 12
        c.location = start; c.rotation_euler = rot0; c.scale = (1, 1, 1)
        c.keyframe_insert("location", frame=f - fall); c.keyframe_insert("rotation_euler", frame=f - fall)
        c.location = (x, y, 0.05)
        c.rotation_euler = (random.uniform(-.25, .25), random.uniform(-.25, .25), rot0[2] + random.uniform(1, 3))
        c.keyframe_insert("location", frame=f); c.keyframe_insert("rotation_euler", frame=f)
        # 着水後: 少し浮いたまま漂い、赤熱し、縁から溶けて縮みつつ沈む
        c.location = (x + random.uniform(-.4, .4), y + random.uniform(-.4, .4), -0.05)
        c.keyframe_insert("location", frame=f + 18)
        c.scale = (1, 1, 1); c.keyframe_insert("scale", frame=f + 6)
        c.location = (c.location.x, c.location.y, -0.35)
        c.scale = (0.35, 0.35, 0.6)
        c.keyframe_insert("location", frame=f + 48); c.keyframe_insert("scale", frame=f + 48)
        heat = mat.node_tree.nodes["Heat"].outputs[0]
        heat.default_value = 0; heat.keyframe_insert("default_value", frame=f)
        heat.default_value = 0.9; heat.keyframe_insert("default_value", frame=f + 30)
        # 落下はほぼ等加速度になるよう補間を調整
        for fc in (c.animation_data.action.fcurves if hasattr(c.animation_data.action, "fcurves") else []):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"

    # 照明: 炉内の熱源(上方の暖色エリアライト)+工場の冷たい環境光
    bpy.ops.object.light_add(type="AREA", location=(-6, 8, 20))
    key = bpy.context.object; key.data.size = 14; key.data.energy = 9000
    key.data.color = (1.0, 0.55, 0.25)
    key.rotation_euler = (math.radians(30), 0, math.radians(200))
    bpy.ops.object.light_add(type="AREA", location=(14, -10, 10))
    rim = bpy.context.object; rim.data.size = 6; rim.data.energy = 2500; rim.data.color = (0.55, 0.7, 1.0)
    rim.rotation_euler = (math.radians(60), 0, math.radians(55))
    # 湯面に映り込む「炉の口」= 暖色の発光板
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 14, 26))
    hood = bpy.context.object; hood.rotation_euler = (math.radians(120), 0, 0)
    hood.data.materials.append(mat_emit("FurnaceMouth", 1500, 0.5))
    hood.visible_camera = False

    world = bpy.data.worlds.new("World"); sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.012, 0.010, 0.010, 1); bg.inputs["Strength"].default_value = 1

    # カメラ: るつぼの縁越しのマクロ、ゆっくり寄る
    bpy.ops.object.camera_add(location=(0, -26, 17))
    cam = bpy.context.object; sc.camera = cam
    cam.data.lens = 55; cam.data.sensor_width = 36
    cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 2.0
    bpy.ops.object.empty_add(location=(0, 0, 0))
    target = bpy.context.object; target.name = "Focus"
    tr = cam.constraints.new("TRACK_TO"); tr.target = target
    cam.data.dof.focus_object = target
    cam.keyframe_insert("location", frame=1)
    cam.location = (1.5, -21.0, 13.5)
    cam.keyframe_insert("location", frame=FRAMES)

    # レンダリング設定
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = -1.0
    sc.view_settings.look = "AgX - Punchy" if "AgX - Punchy" in [l.identifier for l in bpy.types.ColorManagedViewSettings.bl_rna.properties["look"].enum_items] else "None"
    sc.render.image_settings.file_format = "PNG"
    return sc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=int)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=FRAMES)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--res", default="1280x720")
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
    w, h = map(int, a.res.split("x"))
    sc = build((w, h), a.samples)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.still:
        sc.frame_set(a.still)
        sc.render.filepath = str(OUT / f"still_{a.still:04d}.png")
        bpy.ops.render.render(write_still=True)
    else:
        sc.frame_start, sc.frame_end = a.start, a.end
        sc.render.filepath = str(OUT / "f_")
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
