"""H03 / カット2-3: 工業用電気炉(誘導炉)で、アルミ地金(インゴット)が溶けた銀色の湯に沈んで溶ける。
炉壁の熱でにぶく赤く光る湯面、表面のドロス(酸化膜)、ときどき火花。ゆっくりプッシュイン。5秒。

キー: 1〜 手前のインゴットAが半分沈んだ状態から溶けて沈む / 26〜34 インゴットBが奥の縁から滑り込み着水(34)
      / 68〜76 インゴットCが右から着水(76) / カメラは全体を通してゆっくり寄る。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy, bmesh
from mathutils import Vector
import common as C
import props as P
import factory_parts as F

FRAMES = 120
R_IN = 45.0      # 炉の内半径(cm)


# ------------------------------------------------------------------ マテリアル
def mat_molten():
    """溶けたアルミ: 鏡のような銀色+灰色のドロス膜(壁際ほど厚い)+炉の熱でにぶく赤い。"""
    m, nt, out = C.node_mat("Molten")
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = 0.06; nz.inputs["Detail"].default_value = 8; nz.inputs["Roughness"].default_value = 0.62
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    F.key_socket(nz.inputs["W"], 1, 0.0); F.key_socket(nz.inputs["W"], FRAMES, 0.7)
    F.set_interp(nt, "LINEAR")
    # 壁際ほどドロスが多い(半径方向の勾配)
    sep = n.new("ShaderNodeSeparateXYZ"); C.link(nt, tc.outputs["Object"], sep.inputs["Vector"])
    ln = n.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; C.link(nt, tc.outputs["Object"], ln.inputs[0])
    rad = n.new("ShaderNodeMapRange"); rad.inputs["From Min"].default_value = R_IN * 0.55
    rad.inputs["From Max"].default_value = R_IN; rad.inputs["To Min"].default_value = 0.0; rad.inputs["To Max"].default_value = 0.35
    C.link(nt, ln.outputs["Value"], rad.inputs["Value"])
    addr = n.new("ShaderNodeMath"); addr.operation = "ADD"
    C.link(nt, nz.outputs["Fac"], addr.inputs[0]); C.link(nt, rad.outputs["Result"], addr.inputs[1])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.64; cr.color_ramp.elements[0].color = (0, 0, 0, 1)
    cr.color_ramp.elements[1].position = 0.72; cr.color_ramp.elements[1].color = (1, 1, 1, 1)
    C.link(nt, addr.outputs[0], cr.inputs["Fac"])
    liquid = n.new("ShaderNodeBsdfPrincipled")
    liquid.inputs["Base Color"].default_value = (0.93, 0.92, 0.9, 1)
    liquid.inputs["Metallic"].default_value = 1.0; liquid.inputs["Roughness"].default_value = 0.035
    dross = n.new("ShaderNodeBsdfPrincipled")
    dn = n.new("ShaderNodeTexNoise"); dn.inputs["Scale"].default_value = 0.8; dn.inputs["Detail"].default_value = 10
    C.link(nt, tc.outputs["Object"], dn.inputs["Vector"])
    dcr = n.new("ShaderNodeValToRGB")
    dcr.color_ramp.elements[0].color = (0.12, 0.12, 0.12, 1); dcr.color_ramp.elements[1].color = (0.42, 0.42, 0.41, 1)
    C.link(nt, dn.outputs["Fac"], dcr.inputs["Fac"]); C.link(nt, dcr.outputs["Color"], dross.inputs["Base Color"])
    dross.inputs["Metallic"].default_value = 0.5; dross.inputs["Roughness"].default_value = 0.75
    env = F.fake_env(nt, strength=1.5, rows=2.2, duty=0.1, sky=(0.2, 0.2, 0.2), floor=(0.05, 0.03, 0.02), structure=0.85, lamp=(3.2, 3.0, 2.7))
    liq = n.new("ShaderNodeAddShader")
    C.link(nt, liquid.outputs["BSDF"], liq.inputs[0]); C.link(nt, env.outputs["Emission"], liq.inputs[1])
    mix = n.new("ShaderNodeMixShader")
    C.link(nt, cr.outputs["Color"], mix.inputs["Fac"])
    C.link(nt, liq.outputs["Shader"], mix.inputs[1]); C.link(nt, dross.outputs["BSDF"], mix.inputs[2])
    # 熱の自己発光(にぶい赤橙、ドロスの割れ目=液面側をわずかに強く)
    bb = n.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = 1050
    em = n.new("ShaderNodeEmission")
    C.link(nt, bb.outputs["Color"], em.inputs["Color"])
    es = n.new("ShaderNodeMapRange"); es.inputs["To Min"].default_value = 0.012; es.inputs["To Max"].default_value = 0.006
    C.link(nt, cr.outputs["Color"], es.inputs["Value"]); C.link(nt, es.outputs["Result"], em.inputs["Strength"])
    add = n.new("ShaderNodeAddShader")
    C.link(nt, mix.outputs["Shader"], add.inputs[0]); C.link(nt, em.outputs["Emission"], add.inputs[1])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 0.6
    C.link(nt, nz.outputs["Fac"], bump.inputs["Height"])
    db = n.new("ShaderNodeBump"); db.inputs["Strength"].default_value = 0.5; db.inputs["Distance"].default_value = 0.3
    C.link(nt, dn.outputs["Fac"], db.inputs["Height"]); C.link(nt, bump.outputs["Normal"], db.inputs["Normal"])
    C.link(nt, bump.outputs["Normal"], liquid.inputs["Normal"]); C.link(nt, db.outputs["Normal"], dross.inputs["Normal"])
    C.link(nt, add.outputs["Shader"], out.inputs["Surface"])
    return m


def mat_refractory():
    """耐火物の内壁: 煤けた灰褐色、内側は湯面に近いほど赤く光る。外向き面は光らない。"""
    m, nt, out = C.node_mat("Refractory")
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.25; nz.inputs["Detail"].default_value = 12
    nz.inputs["Roughness"].default_value = 0.7
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.05, 0.045, 0.04, 1); cr.color_ramp.elements[1].color = (0.36, 0.31, 0.26, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.9
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.6
    C.link(nt, nz.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    sep = n.new("ShaderNodeSeparateXYZ")
    geo = n.new("ShaderNodeNewGeometry"); C.link(nt, geo.outputs["Position"], sep.inputs["Vector"])
    zr = n.new("ShaderNodeMapRange")
    zr.inputs["From Min"].default_value = 0.0; zr.inputs["From Max"].default_value = 15.0
    zr.inputs["To Min"].default_value = 0.6; zr.inputs["To Max"].default_value = 0.05
    C.link(nt, sep.outputs["Z"], zr.inputs["Value"])
    dotn = n.new("ShaderNodeVectorMath"); dotn.operation = "DOT_PRODUCT"
    C.link(nt, geo.outputs["Normal"], dotn.inputs[0]); C.link(nt, geo.outputs["Position"], dotn.inputs[1])
    inward = n.new("ShaderNodeMath"); inward.operation = "LESS_THAN"; inward.inputs[1].default_value = 0
    C.link(nt, dotn.outputs["Value"], inward.inputs[0])
    # ムラ(煤の筋)
    vn = n.new("ShaderNodeTexNoise"); vn.inputs["Scale"].default_value = 0.6; vn.inputs["Detail"].default_value = 4
    C.link(nt, tc.outputs["Object"], vn.inputs["Vector"])
    m1 = n.new("ShaderNodeMath"); m1.operation = "MULTIPLY"
    C.link(nt, zr.outputs["Result"], m1.inputs[0]); C.link(nt, inward.outputs[0], m1.inputs[1])
    m2 = n.new("ShaderNodeMath"); m2.operation = "MULTIPLY"
    C.link(nt, m1.outputs[0], m2.inputs[0]); C.link(nt, vn.outputs["Fac"], m2.inputs[1])
    bb = n.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = 1150
    em = n.new("ShaderNodeEmission")
    C.link(nt, bb.outputs["Color"], em.inputs["Color"]); C.link(nt, m2.outputs[0], em.inputs["Strength"])
    add = n.new("ShaderNodeAddShader")
    C.link(nt, p.outputs["BSDF"], add.inputs[0]); C.link(nt, em.outputs["Emission"], add.inputs[1])
    C.link(nt, add.outputs["Shader"], out.inputs["Surface"])
    return m


def mat_ingot(name):
    """アルミ地金: 鋳肌のにぶい銀色。Heat(0..1)で下から赤みがさす。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.4; nz.inputs["Detail"].default_value = 10
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    fine = n.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 6; fine.inputs["Detail"].default_value = 8
    C.link(nt, tc.outputs["Object"], fine.inputs["Vector"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Metallic"].default_value = 1.0
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.45, 0.44, 0.42, 1); cr.color_ramp.elements[1].color = (0.82, 0.82, 0.8, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"]); C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.28; rr.inputs["To Max"].default_value = 0.6
    C.link(nt, fine.outputs["Fac"], rr.inputs["Value"]); C.link(nt, rr.outputs["Result"], p.inputs["Roughness"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.3
    C.link(nt, fine.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    hv = n.new("ShaderNodeValue"); hv.name = "Heat"; hv.outputs[0].default_value = 0.0
    bb = n.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = 980
    em = n.new("ShaderNodeEmission"); C.link(nt, bb.outputs["Color"], em.inputs["Color"])
    st = n.new("ShaderNodeMath"); st.operation = "MULTIPLY"; st.inputs[1].default_value = 0.035
    C.link(nt, hv.outputs[0], st.inputs[0])
    st2 = n.new("ShaderNodeMath"); st2.operation = "MULTIPLY"
    C.link(nt, st.outputs[0], st2.inputs[0]); C.link(nt, nz.outputs["Fac"], st2.inputs[1])
    C.link(nt, st2.outputs[0], em.inputs["Strength"])
    add = n.new("ShaderNodeAddShader")
    C.link(nt, p.outputs["BSDF"], add.inputs[0]); C.link(nt, em.outputs["Emission"], add.inputs[1])
    C.link(nt, add.outputs["Shader"], out.inputs["Surface"])
    return m


def mat_checker_plate():
    """作業床の縞鋼板(暗い鉄、細かな凹凸)。"""
    m, nt, out = C.node_mat("CheckerPlate")
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    br = n.new("ShaderNodeTexBrick"); br.inputs["Scale"].default_value = 0.35
    br.inputs["Mortar Size"].default_value = 0.0; br.inputs["Brick Width"].default_value = 0.5; br.inputs["Row Height"].default_value = 0.5
    C.link(nt, tc.outputs["Object"], br.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.05; nz.inputs["Detail"].default_value = 8
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Metallic"].default_value = 0.8
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.05, 0.05, 0.05, 1); cr.color_ramp.elements[1].color = (0.25, 0.23, 0.21, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"]); C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.35; rr.inputs["To Max"].default_value = 0.8
    C.link(nt, nz.outputs["Fac"], rr.inputs["Value"]); C.link(nt, rr.outputs["Result"], p.inputs["Roughness"])
    # 縞(斜めの小突起)を Wave で
    wv = n.new("ShaderNodeTexWave"); wv.bands_direction = "DIAGONAL"; wv.inputs["Scale"].default_value = 0.9
    C.link(nt, tc.outputs["Object"], wv.inputs["Vector"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.35
    C.link(nt, wv.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


# ------------------------------------------------------------------ 形状
def make_ingot(name, mat, size=(52, 13, 9)):
    """台形断面のインゴット。溶ける表現のため細分化+Displace(強さをキー)。"""
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object; o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    bm = bmesh.new(); bm.from_mesh(o.data)
    for v in bm.verts:
        if v.co.z > 0:
            v.co.x *= 0.92; v.co.y *= 0.78
    bm.to_mesh(o.data); bm.free()
    P.add_mod(o, "BEVEL", width=1.2, segments=3, limit_method="ANGLE")
    sub = o.modifiers.new("sub", "SUBSURF"); sub.subdivision_type = "SIMPLE"; sub.levels = sub.render_levels = 3
    tex = bpy.data.textures.new(name + "Melt", "CLOUDS"); tex.noise_scale = 3.0
    d = o.modifiers.new("melt", "DISPLACE"); d.texture = tex; d.strength = 0.0; d.mid_level = 0.6
    d.texture_coords = "OBJECT"
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    return o, d


def add_wave(pool, x, y, frame, height=0.5, width=6.0, speed=0.9, life=70):
    w = pool.modifiers.new(f"wave{frame}", "WAVE")
    w.use_x = w.use_y = True
    w.start_position_x, w.start_position_y = x, y
    w.time_offset = frame
    w.height = height; w.width = width; w.speed = speed; w.narrowness = 1.5
    w.use_normal = False; w.damping_time = 30; w.falloff_radius = 40; w.lifetime = life
    return w


def build(sc):
    sc.gravity = (0, 0, -981.0)
    C.world((0.03, 0.027, 0.025))
    random.seed(3)

    # --- 炉
    refr = mat_refractory()
    F.ring("Wall", R_IN + 14, R_IN, 50, (0, 0, -11), refr, verts=128, bevel=0.8)
    shell = F.mat_painted("Shell", (0.12, 0.12, 0.13), rough=0.5, wear=0.4, scale=0.05)
    F.ring("Rim", R_IN + 26, R_IN + 13, 6, (0, 0, 14), shell, verts=128, bevel=0.6)
    # 縁にこびりついたドロス(耐火物の上面の黒い塊)
    crust = C.principled("Crust", (0.07, 0.065, 0.06), metallic=0.3, rough=0.85, bump=0.8, bump_scale=0.6)
    F.ring("Crust", R_IN + 4, R_IN - 1.5, 2.0, (0, 0, 0.4), crust, verts=128)
    # 注湯口(手前右)
    sp = P.box("Spout", (22, 18, 6), (R_IN + 18, -18, 13), mat=shell, bevel=0.6)
    sp.rotation_euler.z = math.radians(-35)
    # 作業床(縞鋼板)
    F.ring("Deck", 520, R_IN + 26, 3, (0, 0, 11), mat_checker_plate(), verts=128)
    # 奥: 炉蓋(跳ね上げ)と油圧シリンダー、手すり
    lid = P.cyl("Lid", R_IN + 22, 10, (0, R_IN + 70, 60), (math.radians(78), 0, 0), shell, verts=96, bevel=1.0)
    yel = F.mat_painted("Yellow", (0.55, 0.38, 0.05), rough=0.5, wear=0.35)
    for sx in (-1, 1):
        P.cyl(f"Hyd{sx}", 5, 60, (sx * 50, R_IN + 45, 35), (math.radians(-30), 0, 0), yel, verts=24)
        P.cyl(f"Post{sx}", 2.5, 110, (sx * 160, 140, 66), mat=yel, verts=16)
    P.cyl("Handrail", 2.5, 320, (0, 140, 120), (0, math.radians(90), 0), yel, verts=16)
    # 遠景の建屋
    F.factory_hall(size=(2400, 1600, 900), floor_mat=F.mat_concrete("Concrete2", (0.2, 0.19, 0.18)),
                   lamp_rows=[(300, 6), (650, 6)], lamp_strength=25, lamp_temp=3400, center=(0, 500, -2))
    # 遠景の別の炉の明かり(暖色のにじみ)
    P.cyl("FarGlow", 40, 4, (-420, 900, 30), mat=C.emissive("FarGlowM", temp=1400, strength=8), verts=32)

    # --- 湯面
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=220, y_subdivisions=220, size=2 * R_IN + 2, location=(0, 0, 0))
    pool = bpy.context.object; pool.name = "Pool"
    bm = bmesh.new(); bm.from_mesh(pool.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.xy.length > R_IN + 0.5], context="VERTS")
    bm.to_mesh(pool.data); bm.free()
    bpy.ops.object.shade_smooth()
    pool.data.materials.append(mat_molten())

    # --- インゴット
    # A: 手前、半分沈んだ状態から溶けて沈む
    ma = mat_ingot("IngotA"); a, da = make_ingot("IngotA", ma)
    hv = ma.node_tree.nodes["Heat"].outputs[0]
    C.key(a, "location", 1, (-6, -8, 2.6)); C.key(a, "rotation_euler", 1, (math.radians(4), math.radians(-6), math.radians(18)))
    C.key(a, "location", 100, (-5, -6, -4.0)); C.key(a, "rotation_euler", 100, (math.radians(6), math.radians(-8), math.radians(24)))
    C.key(a, "scale", 1, (1, 1, 1)); C.key(a, "scale", 100, (0.86, 0.8, 0.7))
    F.key_socket(hv, 1, 0.2); F.key_socket(hv, 100, 0.6)
    da.strength = 0.0; da.keyframe_insert("strength", frame=1); da.strength = 2.0; da.keyframe_insert("strength", frame=100)
    add_wave(pool, -6, -8, -40, height=0.18, width=5, speed=0.5, life=0)  # 常に揺らぐ溶け際
    # B: 奥の縁から滑り込む
    mb = mat_ingot("IngotB"); b, db = make_ingot("IngotB", mb)
    hb = mb.node_tree.nodes["Heat"].outputs[0]
    C.key(b, "location", 24, (14, 36, 13)); C.key(b, "rotation_euler", 24, (math.radians(-28), 0, math.radians(-12)))
    C.key(b, "location", 34, (10, 16, 1.5)); C.key(b, "rotation_euler", 34, (math.radians(-6), math.radians(3), math.radians(-20)))
    C.key(b, "location", 50, (9, 14, -0.5)); C.key(b, "rotation_euler", 50, (math.radians(3), math.radians(2), math.radians(-23)))
    C.key(b, "location", FRAMES, (8, 12, -2.8)); C.key(b, "rotation_euler", FRAMES, (math.radians(5), math.radians(4), math.radians(-28)))
    F.key_socket(hb, 34, 0.0); F.key_socket(hb, FRAMES, 0.5)
    db.strength = 0.0; db.keyframe_insert("strength", frame=34); db.strength = 1.2; db.keyframe_insert("strength", frame=FRAMES)
    add_wave(pool, 10, 16, 34, height=0.9, width=7, speed=0.8)
    # C: 右から着水
    mc = mat_ingot("IngotC"); c, dc = make_ingot("IngotC", mc)
    hc = mc.node_tree.nodes["Heat"].outputs[0]
    C.key(c, "location", 66, (44, -4, 15)); C.key(c, "rotation_euler", 66, (0, math.radians(30), math.radians(80)))
    C.key(c, "location", 76, (22, -10, 1.5)); C.key(c, "rotation_euler", 76, (0, math.radians(6), math.radians(72)))
    C.key(c, "location", 92, (21, -9, -0.3)); C.key(c, "rotation_euler", 92, (0, math.radians(-2), math.radians(70)))
    C.key(c, "location", FRAMES, (20.5, -8.5, -1.2)); C.key(c, "rotation_euler", FRAMES, (0, math.radians(-3), math.radians(69)))
    F.key_socket(hc, 76, 0.0); F.key_socket(hc, FRAMES, 0.3)
    add_wave(pool, 22, -10, 76, height=0.9, width=7, speed=0.8)
    # 落下は加速(入り EASE_IN)、着水後はゆっくり
    for o in (b, c):
        for fc in F.fcurves(o):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                if kp.co.x in (24, 66):
                    kp.easing = "EASE_IN"; kp.interpolation = "QUAD"

    # --- 火花(湯面からときどき跳ねる)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.12, location=(0, 0, -300))
    spark = bpy.context.object; spark.name = "SparkInst"
    spark.data.materials.append(C.emissive("SparkM", temp=2300, strength=80))
    ps = pool.modifiers.new("sparks", "PARTICLE_SYSTEM").particle_system.settings
    ps.count = 160; ps.frame_start = 1; ps.frame_end = FRAMES; ps.lifetime = 14; ps.lifetime_random = 0.6
    ps.normal_factor = 150; ps.factor_random = 45; ps.effector_weights.gravity = 1.0
    ps.render_type = "OBJECT"; ps.instance_object = spark; ps.particle_size = 1.0; ps.size_random = 0.8
    ps.use_rotations = False; ps.emit_from = "FACE"; ps.use_emit_random = True
    if hasattr(ps, "use_dynamic_rotation"):
        ps.use_dynamic_rotation = False
    # 着水の瞬間に火花を多めに: 別の小さな放出板
    for (x, y, f) in ((10, 16, 34), (22, -10, 76)):
        bpy.ops.mesh.primitive_plane_add(size=12, location=(x, y, 0.3))
        em = bpy.context.object; em.name = f"SplashEmit{f}"; em.hide_render = False
        em.visible_camera = False; em.visible_shadow = False
        em.data.materials.append(C.principled("Inv", (0, 0, 0), alpha=0.0))
        s2 = em.modifiers.new("sp", "PARTICLE_SYSTEM").particle_system.settings
        s2.count = 70; s2.frame_start = f; s2.frame_end = f + 3; s2.lifetime = 16; s2.lifetime_random = 0.5
        s2.normal_factor = 240; s2.factor_random = 70; s2.render_type = "OBJECT"; s2.instance_object = spark
        s2.particle_size = 0.8; s2.size_random = 0.7; s2.use_rotations = False
        em.show_instancer_for_render = False

    # --- 照明
    # 湯面から立ちのぼる熱の照り返し(炉内の暖色)
    gl = C.point_light((0, 0, 8), 1.0e4, (1.0, 0.5, 0.25), radius=30, name="PoolGlow")
    gl.data.specular_factor = 0.0  # 湯面(鏡面)に光源そのものを映さない
    # 天井の作業灯(湯面に映り込む冷たい白): 映り込み用の発光板+エリアライト
    P.light_card("ReflCard", (520, 300), (0, 230, 210), (0, 0, 0), strength=3.0, color=(0.95, 0.93, 0.9))
    C.area_light((-120, -60, 260), (20, -25, 0), 120, 2.0e5, (1.0, 0.92, 0.82), "Overhead")
    C.area_light((180, 120, 120), (60, 0, 125), 80, 3e4, (0.6, 0.7, 1.0), "Rim")

    # 湯面(鏡面)が画面外の作業灯・天井を映せるよう反射プローブを置く
    bpy.ops.object.lightprobe_add(type="SPHERE", location=(0, 0, 30))
    pr = bpy.context.object; pr.data.influence_distance = 120
    # --- カメラ: 炉の縁越しに見下ろし、ゆっくり寄る
    cam, tgt = C.camera((-18, -175, 128), (4, 4, 0), lens=45, fstop=4.0)
    C.key(cam, "location", 1, (-18, -175, 128)); C.key(cam, "location", FRAMES, (-8, -122, 88))
    C.key(tgt, "location", 1, (4, 4, 0)); C.key(tgt, "location", FRAMES, (6, 2, 0))
    F.set_interp(cam, "BEZIER")
    sc.view_settings.exposure = -0.5
    if hasattr(sc.render, "use_motion_blur"):
        sc.render.use_motion_blur = True


if __name__ == "__main__":
    C.run_shot("h03_furnace", build, FRAMES)
