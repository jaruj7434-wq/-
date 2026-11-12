"""H05 / カット2-5: 圧穿(ブランキング)プレス。アルミ帯板が1ピッチずつ送られ、上からパンチ(ラム)が打ち下ろされ、
無地の円盤(ブランク)が3枚ずつ下へ抜け落ちてトレーの山に加わる。右へ出ていく帯板には丸い穴が並ぶ。5秒。

キー: 打ち抜き 12 / 36 / 60 / 84 / 108 フレーム(各回3枚落下)。送りは各打撃の +4〜+14 フレーム。
構造メモ: パンチ左は静止した無地の板、右は穴あき帯板(打撃の瞬間に1ピッチ戻して周期的に見せる)。
          継ぎ目はストリッパー(上)とダイ(下)の中に隠れる。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy, bmesh
import common as C
import props as P
import factory_parts as F

FRAMES = 120
STRIKES = (12, 36, 60, 84, 108)
PITCH = 2.4
ROWS_Y = (-2.4, 0.0, 2.4)
T = 0.15                 # 板厚
WID = 9.0                # 板幅
SEAM = -1.4


def mat_strip(name, coord_obj):
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord"); tc.object = coord_obj
    mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.05, 4, 4)
    C.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    hl = n.new("ShaderNodeTexNoise"); hl.inputs["Scale"].default_value = 3; hl.inputs["Detail"].default_value = 10
    C.link(nt, mp.outputs["Vector"], hl.inputs["Vector"])
    st = n.new("ShaderNodeTexNoise"); st.inputs["Scale"].default_value = 0.3; st.inputs["Detail"].default_value = 5
    C.link(nt, tc.outputs["Object"], st.inputs["Vector"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Metallic"].default_value = 1.0
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.62, 0.62, 0.61, 1); cr.color_ramp.elements[1].color = (0.88, 0.88, 0.87, 1)
    C.link(nt, st.outputs["Fac"], cr.inputs["Fac"]); C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.12; rr.inputs["To Max"].default_value = 0.3
    C.link(nt, hl.outputs["Fac"], rr.inputs["Value"]); C.link(nt, rr.outputs["Result"], p.inputs["Roughness"])
    env = F.fake_env(nt, strength=0.5, rows=1.2, duty=0.2, sky=(0.35, 0.35, 0.36), lamp=(1.6, 1.5, 1.4),
                     along_x=0.5, lamp_len=0.85)
    add = n.new("ShaderNodeAddShader")
    C.link(nt, p.outputs["BSDF"], add.inputs[0]); C.link(nt, env.outputs["Emission"], add.inputs[1])
    C.link(nt, add.outputs["Shader"], out.inputs["Surface"])
    return m


def plate(name, x0, x1, mat):
    o = P.box(name, (x1 - x0, WID, T), ((x0 + x1) / 2, 0, 0), mat=mat)
    return o


def holed_strip(mat, x0=SEAM, x1=60.0):
    """穴あき帯板(ローカル原点=パンチ中心)。穴は x=0, PITCH, 2*PITCH, ... に3列。"""
    o = P.box("HoledStrip", (x1 - x0, WID, T), ((x0 + x1) / 2, 0, 0))
    cutters = []
    k = 0
    x = 0.0
    while x < x1 + 1:
        for y in ROWS_Y:
            bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=1.0, depth=1.0, location=(x, y, 0))
            cutters.append(bpy.context.object)
        x += PITCH; k += 1
    for c in cutters:
        c.select_set(True)
    bpy.context.view_layer.objects.active = cutters[0]
    bpy.ops.object.join()
    cut = bpy.context.object
    b = o.modifiers.new("holes", "BOOLEAN"); b.object = cut; b.operation = "DIFFERENCE"; b.solver = "EXACT"
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="holes")
    bpy.data.objects.remove(cut)
    o.data.materials.append(mat)
    return o


def keyed(obj, path, keys, interp_at=None):
    """keys=[(frame, value)], interp_at={frame: 'CONSTANT'|...}"""
    for f, v in keys:
        C.key(obj, path, f, v)
    for fc in F.fcurves(obj):
        if fc.data_path == path:
            for kp in fc.keyframe_points:
                kp.interpolation = (interp_at or {}).get(int(round(kp.co.x)), "BEZIER")


def build(sc):
    sc.gravity = (0, 0, -981.0)
    F.world_gradient(top=(0.35, 0.34, 0.33), horizon=(0.06, 0.06, 0.065), bottom=(0.015, 0.015, 0.015),
                     strength=0.6, strips=3.0, strip_color=(2.5, 2.4, 2.2), camera_color=(0.012, 0.012, 0.014))
    frame_m = F.mat_painted("PressFrame", (0.16, 0.24, 0.22), rough=0.45, wear=0.25, scale=0.3)
    tool_m, _ = F.mat_steel("ToolSteel", (0.55, 0.56, 0.58), rough=0.18, streak_axis="Z")
    dark_m = F.mat_painted("Dark", (0.05, 0.05, 0.055), rough=0.5, wear=0.5, scale=0.4)
    blank_m = C.mat_coin("Blank", stamped=False)

    # --- 帯板
    bpy.ops.object.empty_add(location=(0, 0, 0)); flow = bpy.context.object; flow.name = "Flow"
    smat = mat_strip("StripM", flow)
    plate("PlainPlate", -70, 1.2, smat)
    hs = holed_strip(smat)
    hs.location.z = 0.002
    hs_keys = [(1, (PITCH, 0, 0.002))]
    fl_keys = [(1, (0, 0, 0))]
    interp = {}
    for i, s in enumerate(STRIKES):
        hs_keys += [(s - 1, (PITCH, 0, 0.002)), (s, (0, 0, 0.002)), (s + 4, (0, 0, 0.002)), (s + 14, (PITCH, 0, 0.002))]
        fl_keys += [(s + 4, (i * PITCH, 0, 0)), (s + 14, ((i + 1) * PITCH, 0, 0))]
        interp[s - 1] = "CONSTANT"
    keyed(hs, "location", hs_keys, interp)
    keyed(flow, "location", fl_keys)

    # --- 金型: ダイ(下)とストリッパー(上)、パンチ+ラム
    P.box("Die", (7.0, 11.0, 3.0), (0, 0, -1.5 - T / 2 - 0.01), mat=tool_m, bevel=0.08)
    P.box("Stripper", (6.4, 11.0, 1.2), (0, 0, 0.6 + T / 2 + 0.01), mat=tool_m, bevel=0.08)
    for s in (-1, 1):
        P.box(f"DieSupport{s}", (3.0, 6.0, 13.9), (s * 6.2, 4.0, -10.05), mat=dark_m, bevel=0.1)
        P.box(f"Guide{s}", (2.6, 14.0, 1.0), (s * 5.0, 0, -3.6), mat=dark_m, bevel=0.05)
    bpy.ops.object.empty_add(location=(0, 0, 0)); ram = bpy.context.object; ram.name = "RamRig"
    for y in ROWS_Y:
        pn = P.cyl(f"Punch{y}", 0.98, 6.0, (0, y, 4.2), mat=tool_m, verts=48, bevel=0.03)
        pn.parent = ram
    hold = P.box("PunchHolder", (6.4, 11.0, 2.4), (0, 0, 8.2), mat=tool_m, bevel=0.1); hold.parent = ram
    ramb = P.box("Ram", (14.0, 14.0, 7.0), (0, 0, 12.8), mat=frame_m, bevel=0.2); ramb.parent = ram
    up, down = 3.0, 0.0     # パンチ先端はストリッパー内(上死点)→板を貫通(下死点)
    rk = [(1, (0, 0, up))]
    for s in STRIKES:
        rk += [(s - 9, (0, 0, up)), (s, (0, 0, down)), (s + 7, (0, 0, up))]
    keyed(ram, "location", rk)
    for fc in F.fcurves(ram):
        for kp in fc.keyframe_points:
            if int(round(kp.co.x)) in [s - 9 for s in STRIKES]:
                kp.interpolation = "QUAD"; kp.easing = "EASE_IN"
    # プレス本体(ストレートサイド)
    for s in (-1, 1):
        P.box(f"Column{s}", (6.0, 8.0, 46.0), (s * 14.0, 9.0, 4.0), mat=frame_m, bevel=0.3)
    P.box("Crown", (36.0, 12.0, 9.0), (0, 8.0, 29.0), mat=frame_m, bevel=0.3)
    P.box("Bolster", (34.0, 20.0, 3.0), (0, 0, -18.5), mat=frame_m, bevel=0.2)
    P.box("Bed", (40.0, 26.0, 20.0), (0, 0, -30.0), mat=frame_m, bevel=0.3)
    # 送りロール(左)
    for z, sgn in ((1.2, -1), (-1.2, 1)):
        r = P.cyl(f"Feed{z}", 1.05, 12.0, (-12.0, 0, z), (math.radians(90), 0, 0), tool_m, verts=48)
        keys = [(1, tuple(r.rotation_euler))]
        ang = 0.0
        for s in STRIKES:
            keys += [(s + 4, (r.rotation_euler.x, 0, ang))]
            ang += sgn * PITCH / 1.05
            keys += [(s + 14, (r.rotation_euler.x, 0, ang))]
        keyed(r, "rotation_euler", keys)
    P.box("FeedFrame", (4, 3, 7), (-12.0, -7.6, 0), mat=frame_m, bevel=0.15)
    P.box("FeedFrame2", (4, 3, 7), (-12.0, 7.6, 0), mat=frame_m, bevel=0.15)
    # 出側の帯板受け
    P.box("ExitGuide", (30, 12, 0.8), (22, 0, -0.6), mat=dark_m, bevel=0.05)

    # --- 受けトレーとブランクの山
    tray = P.open_box("Tray", (9.0, 14.0, 4.0), (0, 0, -15.0), wall=0.3, mat=dark_m, bevel=0.05)
    P.passive_mesh(tray, friction=0.5, bounce=0.1, margin=0.02)
    rnd = random.Random(5)
    pile = []
    for i in range(70):
        x = rnd.uniform(-3.4, 3.4); y = rnd.uniform(-5.6, 5.6)
        h = 0.9 * max(0.0, 1 - (x / 4.5) ** 2 - (y / 7.5) ** 2)
        z = -16.7 + 0.075 + rnd.uniform(0, h)
        c = C.make_coin(f"Pile{i}", blank_m, (x, y, z),
                        (rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), rnd.uniform(0, 6.3)), verts=40)
        C.rigid(c, active=False, shape="CYLINDER", friction=0.5, bounce=0.15, margin=0.004)
        pile.append(c)
    # 打ち抜かれて落ちるブランク(打撃まではダイの中に隠れて保持→物理へ)
    for i, s in enumerate(STRIKES):
        for j, y in enumerate(ROWS_Y):
            c = C.make_coin(f"Blank{i}_{j}", blank_m, (0, y, -0.4), (0, 0, rnd.uniform(0, 6.3)), verts=40)
            C.rigid(c, active=True, shape="CYLINDER", mass=0.0005, friction=0.5, bounce=0.2, margin=0.004)
            tilt = (rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), c.rotation_euler.z)
            C.key(c, "rotation_euler", 1, tuple(c.rotation_euler))
            C.key(c, "location", 1, (0, y, -0.4))
            C.key(c, "location", s, (0, y, -0.4))
            C.key(c, "location", s + 2, (rnd.uniform(-0.1, 0.1), y + rnd.uniform(-0.1, 0.1), -2.6))
            C.key(c, "rotation_euler", s + 2, tilt)
            rb = c.rigid_body
            rb.kinematic = True; rb.keyframe_insert("kinematic", frame=1)
            rb.keyframe_insert("kinematic", frame=s + 2)
            rb.kinematic = False; rb.keyframe_insert("kinematic", frame=s + 3)
            F.set_interp(c, "LINEAR", "location")
            for fc in F.fcurves(c):
                if "kinematic" in fc.data_path:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "CONSTANT"
    rw = C.rigid_world(sc, FRAMES, substeps=30)
    rw.solver_iterations = 30

    # --- 背景(工場の奥)
    F.factory_hall(size=(1200, 900, 400), floor_mat=F.mat_concrete("Concrete", (0.22, 0.21, 0.2)),
                   lamp_rows=[(100, 5), (300, 5)], lamp_strength=18, lamp_temp=4000, center=(0, 250, -40))
    for k, x in enumerate((-150, -60, 90, 180)):
        P.box(f"BgPress{k}", (40, 40, 110 + 20 * (k % 2)), (x, 260, 15), mat=frame_m, bevel=1)

    # --- 照明
    C.area_light((10, -30, 35), (45, 0, 18), 25, 2.2e4, (1.0, 0.93, 0.84), "Key")
    C.area_light((-30, 20, 20), (60, 0, -125), 20, 1.2e4, (0.65, 0.75, 1.0), "Rim")
    F.spot((20, -25, -8), (0, 0, -12), 1.2e4, (1.0, 0.85, 0.7), size_deg=35, name="TraySpot")

    # --- カメラ
    cam, tgt = C.camera((26, -50, 9), (2.0, 0, -3.5), lens=34, fstop=4.0)
    C.key(cam, "location", 1, (28, -52, 10)); C.key(cam, "location", FRAMES, (22, -45, 7))
    sc.view_settings.exposure = 0.0


if __name__ == "__main__":
    C.run_shot("h05_blanking", build, FRAMES)
