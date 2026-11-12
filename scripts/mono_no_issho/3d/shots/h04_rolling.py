"""H04 / カット2-4: 圧延機。磨かれた大きな鋼ロール(4段: ワークロール+バックアップロール)が回り、
厚いアルミ板(スラブ)が噛み込まれて薄く長くなって出てくる。工場の背景、出側からの斜め3/4。5秒。

キー: 1 で薄くなった板の先端がロールから少し出ている → 120 までに約3m先へ伸びる(出側速度=入側の3倍)。
      ロール・テーブルロールは板速度に合わせて回転。カメラはゆっくり横に回り込む。
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy, bmesh
import common as C
import props as P
import factory_parts as F

FRAMES = 120
FPS = 24
T_IN, T_OUT = 12.0, 4.0           # 板厚(cm)
W = 120.0                         # 板幅
R_W, R_B = 25.0, 46.0             # ワーク/バックアップロール半径
L_ROLL = 170.0
V_OUT = 66.0                      # 出側速度 cm/s
V_IN = V_OUT * T_OUT / T_IN


def extrude_profile(name, loop, width, mat, bevel=0.5):
    """XZ 平面の閉じた輪郭 loop を Y 方向に width だけ押し出した柱状メッシュ。"""
    bm = bmesh.new()
    a = [bm.verts.new((x, -width / 2, z)) for x, z in loop]
    b = [bm.verts.new((x, width / 2, z)) for x, z in loop]
    nv = len(loop)
    for k in range(nv):
        bm.faces.new((a[k], a[(k + 1) % nv], b[(k + 1) % nv], b[k]))
    bm.faces.new(a[::-1]); bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    bpy.context.view_layer.objects.active = o
    for ob in bpy.context.selected_objects:
        ob.select_set(False)
    o.select_set(True)
    if bevel:
        P.add_mod(o, "BEVEL", width=bevel, segments=2, limit_method="ANGLE", angle_limit=math.radians(50))
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
    return o


def strip_in(mat):
    """入側スラブ: 厚さ T_IN → ロールの円弧に沿って T_OUT まで絞られる断面。"""
    xs = [-700.0] + [-(i / 24) * 20 for i in range(24, -1, -1)]
    prof = []
    for x in xs:
        dz = R_W - math.sqrt(max(R_W ** 2 - x ** 2, 0)) if abs(x) < R_W else 99
        prof.append((x, min(T_IN / 2, T_OUT / 2 + dz)))
    loop = [(x, h) for x, h in prof] + [(x, -h) for x, h in prof[::-1]]
    return extrude_profile("SlabIn", loop, W, mat)


def mat_alu_sheet(name, coord_obj, rough=0.18, dull=0.0):
    """圧延アルミ板: 圧延方向(X)のヘアライン+うっすら乳化液の汚れ。映り込みは fake_env。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord"); tc.object = coord_obj
    mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.004, 0.5, 0.5)
    C.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    hl = n.new("ShaderNodeTexNoise"); hl.inputs["Scale"].default_value = 4; hl.inputs["Detail"].default_value = 12
    C.link(nt, mp.outputs["Vector"], hl.inputs["Vector"])
    st = n.new("ShaderNodeTexNoise"); st.inputs["Scale"].default_value = 0.02; st.inputs["Detail"].default_value = 6
    C.link(nt, tc.outputs["Object"], st.inputs["Vector"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Metallic"].default_value = 1.0
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.55 - dull, 0.55 - dull, 0.54 - dull, 1)
    cr.color_ramp.elements[1].color = (0.9 - dull, 0.9 - dull, 0.89 - dull, 1)
    C.link(nt, st.outputs["Fac"], cr.inputs["Fac"]); C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = rough * 0.5; rr.inputs["To Max"].default_value = rough * 1.6
    C.link(nt, hl.outputs["Fac"], rr.inputs["Value"]); C.link(nt, rr.outputs["Result"], p.inputs["Roughness"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.01
    C.link(nt, hl.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    env = F.fake_env(nt, strength=0.7 * (1 - dull * 2), rows=0.9, duty=0.22, sky=(0.42, 0.42, 0.44), lamp=(1.3, 1.25, 1.15),
                     along_x=0.4, lamp_len=0.9, structure=0.7)
    # 粗いほど映り込みは弱く: 研磨目の粗さでマスク
    add = n.new("ShaderNodeAddShader")
    C.link(nt, p.outputs["BSDF"], add.inputs[0]); C.link(nt, env.outputs["Emission"], add.inputs[1])
    C.link(nt, add.outputs["Shader"], out.inputs["Surface"])
    return m


def mat_roll(name):
    """研磨された鋼ロール: ほぼ鏡面、円周方向の研削目と薄い油染み(回転が分かる程度のムラ)。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    st = n.new("ShaderNodeTexNoise"); st.inputs["Scale"].default_value = 0.05; st.inputs["Detail"].default_value = 8
    C.link(nt, tc.outputs["Object"], st.inputs["Vector"])
    mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.0, 0.02, 2.0)   # ロール軸=Y
    C.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    gr = n.new("ShaderNodeTexNoise"); gr.inputs["Scale"].default_value = 3; gr.inputs["Detail"].default_value = 10
    C.link(nt, mp.outputs["Vector"], gr.inputs["Vector"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Metallic"].default_value = 1.0
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[0].color = (0.32, 0.31, 0.3, 1)
    cr.color_ramp.elements[1].position = 0.7; cr.color_ramp.elements[1].color = (0.78, 0.78, 0.8, 1)
    C.link(nt, st.outputs["Fac"], cr.inputs["Fac"]); C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.05; rr.inputs["To Max"].default_value = 0.22
    C.link(nt, st.outputs["Fac"], rr.inputs["Value"]); C.link(nt, rr.outputs["Result"], p.inputs["Roughness"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.04
    C.link(nt, gr.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    env = F.fake_env(nt, strength=0.45, rows=1.4, duty=0.1, sky=(0.2, 0.2, 0.21), lamp=(2.6, 2.4, 2.1), structure=0.8)
    msk = n.new("ShaderNodeMapRange"); msk.inputs["To Min"].default_value = 0.4; msk.inputs["To Max"].default_value = 1.0
    C.link(nt, st.outputs["Fac"], msk.inputs["Value"])
    mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 0.45
    C.link(nt, msk.outputs["Result"], mul.inputs[0]); C.link(nt, mul.outputs[0], env.inputs["Strength"])
    add = n.new("ShaderNodeAddShader")
    C.link(nt, p.outputs["BSDF"], add.inputs[0]); C.link(nt, env.outputs["Emission"], add.inputs[1])
    C.link(nt, add.outputs["Shader"], out.inputs["Surface"])
    return m


def roll(name, r, z, mat, neck_mat, omega, length=L_ROLL):
    o = P.cyl(name, r, length, (0, 0, z), (math.radians(90), 0, 0), mat, verts=128, bevel=0.8)
    o.rotation_mode = "XYZ"
    # ネック(軸受け側の細い部分)
    for s in (-1, 1):
        nk = P.cyl(f"{name}Neck{s}", r * 0.55, 40, (0, s * (length / 2 + 20), z), (math.radians(90), 0, 0), neck_mat, verts=48)
        nk.parent = o; nk.matrix_parent_inverse = o.matrix_world.inverted()
    # 回転はワールドZ軸ではなくロール軸(ローカルZ=ワールドY)まわり → rotation_euler.y ではなく z を回す
    r0 = o.rotation_euler.copy()
    C.key(o, "rotation_euler", 1, tuple(r0))
    C.key(o, "rotation_euler", FRAMES, (r0.x, r0.y, r0.z + omega * (FRAMES - 1) / FPS))
    F.set_interp(o, "LINEAR", "rotation_euler")
    return o


def build(sc):
    C.world((0.03, 0.03, 0.032))
    housing_m = F.mat_painted("Housing", (0.10, 0.17, 0.20), rough=0.5, wear=0.3, scale=0.02)
    dark_m = F.mat_painted("DarkSteel", (0.08, 0.08, 0.085), rough=0.45, wear=0.5, scale=0.05)
    neck_m, _ = F.mat_steel("Neck", (0.45, 0.45, 0.46), rough=0.25, streak_axis="Y")
    roll_m = mat_roll("Roll")
    yel = F.mat_painted("Yellow", (0.6, 0.42, 0.04), rough=0.5, wear=0.35)

    # --- 板(テクスチャを板と一緒に流すための Empty)
    bpy.ops.object.empty_add(location=(0, 0, 0)); e_in = bpy.context.object; e_in.name = "FlowIn"
    bpy.ops.object.empty_add(location=(0, 0, 0)); e_out = bpy.context.object; e_out.name = "FlowOut"
    for e, v in ((e_in, V_IN), (e_out, V_OUT)):
        C.key(e, "location", 1, (0, 0, 0)); C.key(e, "location", FRAMES, (v * (FRAMES - 1) / FPS, 0, 0))
        F.set_interp(e, "LINEAR")
    strip_in(mat_alu_sheet("SlabInM", e_in, rough=0.35, dull=0.12))
    # 出側の薄板: 原点=ロール直下、X スケールで先端が伸びる
    out = extrude_profile("StripOut", [(0, T_OUT / 2), (1, T_OUT / 2), (1, -T_OUT / 2), (0, -T_OUT / 2)], W, None, bevel=0)
    out.data.materials.clear()
    out.data.materials.append(mat_alu_sheet("StripOutM", e_out, rough=0.14))
    head0 = 70.0
    C.key(out, "scale", 1, (head0, 1, 1)); C.key(out, "scale", FRAMES, (head0 + V_OUT * (FRAMES - 1) / FPS, 1, 1))
    F.set_interp(out, "LINEAR")
    # 先端はわずかに反って(圧延直後の板端らしく)

    # --- ロール(4段)
    zw = R_W + T_OUT / 2
    omega_w = V_OUT / R_W
    roll("WorkTop", R_W, zw, roll_m, neck_m, +omega_w)
    roll("WorkBot", R_W, -zw, roll_m, neck_m, -omega_w)
    zb = zw + R_W + R_B + 0.3
    roll("BackupTop", R_B, zb, roll_m, neck_m, -V_OUT / R_B, L_ROLL - 10)
    roll("BackupBot", R_B, -zb, roll_m, neck_m, +V_OUT / R_B, L_ROLL - 10)

    # --- ハウジング(左右の巨大な門型フレーム)とチョック
    y_h = L_ROLL / 2 + 60
    for s in (-1, 1):
        for dx in (-1, 1):
            P.box(f"Post{s}{dx}", (55, 60, 520), (dx * 105, s * y_h, 40), mat=housing_m, bevel=2)
        P.box(f"Top{s}", (265, 60, 70), (0, s * y_h, 300), mat=housing_m, bevel=2)
        P.box(f"Base{s}", (265, 60, 60), (0, s * y_h, -230), mat=housing_m, bevel=2)
        for z in (zw, -zw, zb, -zb):
            P.box(f"Chock{s}{z:.0f}", (150, 50, 2 * (R_W if abs(z) < zb else R_B) * 0.95), (0, s * y_h, z), mat=dark_m, bevel=1.5)
        # 圧下シリンダー(上)
        P.cyl(f"Screw{s}", 22, 90, (0, s * y_h, 380), mat=yel, verts=32, bevel=1)
    P.box("TopBeam", (80, 2 * y_h + 60, 50), (0, 0, 360), mat=housing_m, bevel=2)

    # --- テーブルロール(入側・出側)
    tr_m, _ = F.mat_steel("TableRoll", (0.5, 0.5, 0.5), rough=0.3, streak_axis="Y")
    tr_src = None
    i = 0
    for x in list(range(-640, -120, 52)) + list(range(110, 800, 52)):
        zt = (-T_IN / 2 if x < 0 else -T_OUT / 2) - 9.0
        r = P.cyl(f"TR{i}", 9, W + 30, (x, 0, zt), (math.radians(90), 0, 0), tr_m, verts=32)
        v = V_IN if x < 0 else V_OUT
        C.key(r, "rotation_euler", 1, tuple(r.rotation_euler))
        C.key(r, "rotation_euler", FRAMES, (r.rotation_euler.x, 0, r.rotation_euler.z - v / 9 * (FRAMES - 1) / FPS))
        F.set_interp(r, "LINEAR")
        i += 1
    for s in (-1, 1):
        P.box(f"TableRail{s}", (1500, 14, 30), (75, s * (W / 2 + 25), -T_IN / 2 - 22), mat=dark_m, bevel=1)
    P.box("TableBed", (1500, W + 60, 20), (75, 0, -70), mat=dark_m)

    # --- 建屋
    F.factory_hall(size=(4000, 3000, 1400), floor_mat=F.mat_concrete("Concrete", (0.25, 0.24, 0.22)),
                   lamp_rows=[(-300, 7), (500, 7), (1200, 7)], lamp_strength=30, lamp_temp=4200, center=(0, 300, -260))
    # 奥の別ライン(シルエット)
    for k, x in enumerate((-900, -500, 600, 1000)):
        P.box(f"BgMachine{k}", (220, 160, 300 + 80 * (k % 2)), (x, 900, -110), mat=housing_m, bevel=3)
    # 黄黒の安全柵(ロゴなし)
    for k, x in enumerate(range(-600, 900, 150)):
        P.cyl(f"Rail{k}", 3, 110, (x, -230, -205), mat=yel, verts=12)
    P.cyl("RailBar", 3, 1500, (150, -230, -150), (0, math.radians(90), 0), yel, verts=12)

    # --- 照明
    C.area_light((250, -350, 500), (45, 0, 35), 300, 3.5e6, (1.0, 0.9, 0.78), "Key")
    C.area_light((-500, 250, 300), (65, 0, -120), 200, 1.2e6, (0.6, 0.72, 1.0), "Rim")
    C.area_light((0, 0, 900), (0, 0, 0), 800, 2.5e6, (1.0, 0.95, 0.9), "Top")
    F.spot((500, -200, 80), (0, 0, 0), 3e5, (1.0, 0.85, 0.65), size_deg=30, name="Bite")

    # --- カメラ: 出側斜め3/4、ゆっくり回り込む
    cam, tgt = C.camera((620, -250, 190), (60, 0, 0), lens=40, fstop=5.6)
    C.key(cam, "location", 1, (660, -170, 205)); C.key(cam, "location", FRAMES, (590, -270, 165))
    C.key(tgt, "location", 1, (40, 0, 0)); C.key(tgt, "location", FRAMES, (30, 0, 0))
    sc.view_settings.exposure = 0.3
    sc.eevee.ray_tracing_options.resolution_scale = "1"   # 板の映り込みのザラつきを抑える


if __name__ == "__main__":
    C.run_shot("h04_rolling", build, FRAMES)
