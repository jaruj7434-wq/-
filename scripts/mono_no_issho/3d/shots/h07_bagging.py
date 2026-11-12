"""H07 / カット2-8: 計数・袋詰め。ステンレスのシュートを1円玉が流れ落ち、口を開けた帆布の袋に注ぎ込まれる
(リジッドボディ150枚)。奥には口を縛った満杯の袋がパレットに積まれている。5秒。

キー: 1 から硬貨の流れが続く(最初の約20枚はシュート上に並んだ状態から滑り出す)。
      ~100 フレームまで順次投入、以降は袋の中で落ち着く。カメラはゆっくり寄る。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from mathutils import Vector
import common as C
import props as P
import factory_parts as F

FRAMES = 120
N_STREAM = 150
SACK_R, SACK_H = 9.0, 30.0
FILL_Z = 24.0                        # 袋の中の硬貨の山の高さ
CH_TOP = Vector((-46, 0, 58))        # シュート上端(中心線)
CH_END = Vector((-6.0, 0, 39))       # シュート下端
CH_W = 7.0


def chute(mat):
    """U字断面のシュート。上端→下端に沿った箱を回転して置く。"""
    d = CH_END - CH_TOP
    L = d.length
    ang = math.atan2(-d.z, d.x)
    mid = (CH_TOP + CH_END) / 2
    bpy.ops.object.empty_add(location=mid); rig = bpy.context.object; rig.name = "ChuteRig"
    parts = [P.box("ChuteBed", (L, CH_W, 0.3), (0, 0, -0.15), mat=mat, bevel=0.05),
             P.box("ChuteWallL", (L, 0.3, 3.0), (0, -CH_W / 2 - 0.15, 1.2), mat=mat, bevel=0.05),
             P.box("ChuteWallR", (L, 0.3, 3.0), (0, CH_W / 2 + 0.15, 1.2), mat=mat, bevel=0.05)]
    for p in parts:
        p.parent = rig
    rig.rotation_euler = (0, ang, 0)
    bpy.context.view_layer.update()
    for p in parts:
        mw = p.matrix_world.copy(); p.parent = None; p.matrix_world = mw
        P.passive_mesh(p, friction=0.15, bounce=0.1, margin=0.01)
    return ang


def sack(mat):
    """口の開いた袋(見た目)+ 物理用の内側コライダー(不可視・厚みあり)。"""
    bpy.ops.mesh.primitive_cylinder_add(vertices=72, radius=SACK_R, depth=SACK_H, location=(0, 0, SACK_H / 2), end_fill_type="NGON")
    s = bpy.context.object; s.name = "Sack"
    import bmesh
    bm = bmesh.new(); bm.from_mesh(s.data)
    top = [f for f in bm.faces if f.normal.z > 0.9]
    bmesh.ops.delete(bm, geom=top, context="FACES_ONLY")
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1], cuts=24)
    # 下ぶくれ+口元のすぼまり
    for v in bm.verts:
        t = (v.co.z + SACK_H / 2) / SACK_H
        k = 1.0 + 0.10 * math.sin(math.pi * min(t * 1.3, 1.0)) - 0.06 * max(0, t - 0.85) / 0.15
        v.co.x *= k; v.co.y *= k
    bm.to_mesh(s.data); bm.free()
    P.add_mod(s, "SOLIDIFY", thickness=0.25, offset=1)
    tex = bpy.data.textures.new("SackWrinkle", "CLOUDS"); tex.noise_scale = 4.0
    d = s.modifiers.new("wrinkle", "DISPLACE"); d.texture = tex; d.strength = 0.9; d.texture_coords = "OBJECT"
    sub = s.modifiers.new("sub", "SUBSURF"); sub.levels = sub.render_levels = 1
    bpy.ops.object.shade_smooth()
    s.data.materials.append(mat)
    # 物理用コライダー(袋の内側・不可視)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=SACK_R - 0.3, depth=SACK_H, location=(0, 0, SACK_H / 2))
    col = bpy.context.object; col.name = "SackCollider"
    bm = bmesh.new(); bm.from_mesh(col.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.9], context="FACES_ONLY")
    bm.to_mesh(col.data); bm.free()
    P.add_mod(col, "SOLIDIFY", thickness=1.5, offset=1)
    col.hide_render = True
    P.passive_mesh(col, friction=0.5, bounce=0.05, margin=0.02)
    return s


def filled_sack(name, loc, mat, rnd, scale=1.0, tilt=0.0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=32, radius=1, location=loc)
    o = bpy.context.object; o.name = name
    o.scale = (11 * scale, 10 * scale, 13 * scale)
    o.rotation_euler = (tilt, rnd.uniform(-0.15, 0.15), rnd.uniform(0, 6.28))
    tex = bpy.data.textures.new(name + "T", "CLOUDS"); tex.noise_scale = 0.5
    d = o.modifiers.new("lump", "DISPLACE"); d.texture = tex; d.strength = 0.12; d.texture_coords = "OBJECT"
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    # 縛った口(すぼまった首+房)
    top = Vector(loc) + Vector((0, 0, 12.5 * scale))
    neck = P.cyl(name + "Neck", 1.4 * scale, 3.5 * scale, top, mat=mat, verts=24)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=1.2 * scale, radius2=3.2 * scale, depth=3.5 * scale,
                                    location=top + Vector((0, 0, 3.0 * scale)))
    tuft = bpy.context.object; tuft.data.materials.append(mat)
    d2 = tuft.modifiers.new("lump", "DISPLACE"); d2.texture = tex; d2.strength = 0.6
    bpy.ops.object.shade_smooth()
    tie = P.cyl(name + "Tie", 1.6 * scale, 0.6 * scale, top + Vector((0, 0, 0.8 * scale)),
                mat=C.principled("Tie", (0.55, 0.08, 0.05), rough=0.6), verts=24)
    return o


def build(sc):
    P.physics(sc, FRAMES, substeps=30, iterations=30)
    F.world_gradient(top=(0.35, 0.33, 0.3), horizon=(0.07, 0.065, 0.06), bottom=(0.03, 0.028, 0.025),
                     strength=0.7, strips=3.0, strip_color=(2.2, 2.0, 1.8), camera_color=(0.03, 0.028, 0.026))
    rnd = random.Random(11)
    steel_m, _ = F.mat_steel("Stainless", (0.66, 0.66, 0.67), rough=0.22, streak_axis="X")
    canvas = F.mat_canvas("Canvas", (0.58, 0.5, 0.36), weave=2.5)
    canvas2 = F.mat_canvas("Canvas2", (0.5, 0.43, 0.31), weave=2.5)
    frame_m = F.mat_painted("Frame", (0.15, 0.23, 0.21), rough=0.45, wear=0.3, scale=0.2)
    coin_m = C.mat_coin("CoinShared")

    # --- 床・計量台
    floor_m = F.mat_concrete("Concrete", (0.3, 0.29, 0.27))
    fl = P.plane("Floor", 2000, (0, 0, -6), mat=floor_m)
    P.box("Scale", (30, 30, 6), (0, 0, -3), mat=steel_m, bevel=0.3)
    P.box("ScaleBase", (34, 34, 1), (0, 0, -5.5), mat=frame_m, bevel=0.2)
    # --- 袋と保持リング
    sk = sack(canvas)
    ring = F.ring("HolderRing", SACK_R + 1.4, SACK_R + 0.3, 1.2, (0, 0, SACK_H - 0.6), steel_m, verts=96, bevel=0.15)
    for s in (1,):   # 支持は奥側だけ(手前を空けて袋口を見せる)
        P.cyl(f"Arm{s}", 0.6, 14, (0, s * (SACK_R + 6), SACK_H - 0.6), (math.radians(90), 0, 0), steel_m, verts=16)
        P.cyl(f"Post{s}", 0.9, SACK_H + 6, (0, s * (SACK_R + 12.5), SACK_H / 2 - 3), mat=frame_m, verts=16)
    # 袋の中の既にある山(静的な硬貨)
    k = 0
    for layer in range(3):
        for i in range(55):
            r = (SACK_R - 1.6) * math.sqrt(rnd.random()); a = rnd.uniform(0, math.tau)
            z = FILL_Z - 1.2 + layer * 0.5 + 1.6 * (1 - (r / SACK_R) ** 2) + rnd.uniform(-0.2, 0.2)
            c = C.make_coin(f"Fill{k}", coin_m, (r * math.cos(a), r * math.sin(a), z),
                            (rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), rnd.uniform(0, 6.3)), verts=32)
            if layer == 2:
                C.rigid(c, active=False, shape="CYLINDER", friction=0.5, bounce=0.1, margin=0.004)
            k += 1
    # 山の下支え(不可視の床)
    supp = P.cyl("FillSupport", SACK_R - 0.3, 1.0, (0, 0, FILL_Z - 1.0), verts=32)
    supp.hide_render = True
    C.rigid(supp, active=False, shape="CYLINDER", friction=0.6, bounce=0.05, margin=0.02)
    # 袋口の上の跳ね返し板(シュートから飛び出した硬貨を袋へ落とす)
    defl = P.box("Deflector", (0.4, 16, 22), (6.0, 0, 43), (0, math.radians(-8), 0), mat=steel_m, bevel=0.05)
    C.rigid(defl, active=False, shape="BOX", friction=0.3, bounce=0.05, margin=0.02)
    P.cyl("DeflArm", 0.5, 14, (6.5, 14.5, 53), (math.radians(90), 0, 0), steel_m, verts=12)
    P.cyl("DeflPost", 0.6, 62, (6.5, 21.5, 23), mat=frame_m, verts=12)

    # --- シュートと流れる硬貨
    ang = chute(steel_m)
    P.box("ChuteStand", (2, 2, 52), (-40, 8, 26), mat=frame_m, bevel=0.1)
    P.box("ChuteStand2", (2, 2, 52), (-40, -8, 26), mat=frame_m, bevel=0.1)
    P.box("Hopper", (16, 14, 12), (-52, 0, 66), mat=frame_m, bevel=0.3)
    d = (CH_END - CH_TOP).normalized()
    nrm = Vector((d.z * -1, 0, d.x)) if d.x > 0 else Vector((0, 0, 1))
    nrm = Vector((-d.z, 0, d.x)).normalized()
    if nrm.z < 0:
        nrm = -nrm
    rot_base = (0, ang, 0)
    v_ch = 70.0  # 投入時の初速(シュート方向 cm/s)
    for i in range(N_STREAM):
        lane = rnd.uniform(-CH_W / 2 + 1.2, CH_W / 2 - 1.2)
        if i < 22:
            # 最初からシュート上を流れている分
            t = 0.12 + 0.85 * (i / 22)
            p = CH_TOP + (CH_END - CH_TOP) * t + nrm * (0.25 + rnd.uniform(0, 0.4)) + Vector((0, lane, 0))
            c = C.make_coin(f"S{i}", coin_m, p, (rot_base[0] + rnd.uniform(-0.1, 0.1), ang + rnd.uniform(-0.1, 0.1), rnd.uniform(0, 6.3)), verts=32)
            C.rigid(c, active=True, shape="CYLINDER", mass=0.1, friction=0.3, bounce=0.2, margin=0.004)
            continue
        f = 2 + int((i - 22) * 84 / (N_STREAM - 22)) + rnd.randint(0, 1)
        p = CH_TOP + (CH_END - CH_TOP) * 0.06 + nrm * 0.6 + Vector((0, lane, 0))
        hidden = Vector((-80, lane, 90 + i * 0.5))
        c = C.make_coin(f"S{i}", coin_m, hidden, (0, ang, rnd.uniform(0, 6.3)), verts=32)
        C.rigid(c, active=True, shape="CYLINDER", mass=0.1, friction=0.3, bounce=0.2, margin=0.004)
        rb = c.rigid_body
        C.key(c, "location", 1, tuple(hidden)); C.key(c, "location", f - 3, tuple(hidden))
        C.key(c, "location", f - 2, tuple(p - d * (v_ch * 2 / 24)))
        C.key(c, "location", f, tuple(p))
        C.key(c, "rotation_euler", 1, tuple(c.rotation_euler))
        rb.kinematic = True; rb.keyframe_insert("kinematic", frame=1); rb.keyframe_insert("kinematic", frame=f)
        rb.kinematic = False; rb.keyframe_insert("kinematic", frame=f + 1)
        for fc in F.fcurves(c):
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT" if ("kinematic" in fc.data_path or int(round(kp.co.x)) == f - 3) else "LINEAR"

    # --- 奥: 満杯の袋の山(パレット)
    wood = P.mat_wood("Pallet") if hasattr(P, "mat_wood") else C.principled("Pallet", (0.35, 0.24, 0.13), rough=0.7)
    for px, py in ((-35, 70), (25, 75), (-5, 120)):
        P.box(f"Pallet{px}", (60, 48, 6), (px, py, -3), mat=wood, bevel=0.3)
        for ix in range(3):
            for iy in range(2):
                filled_sack(f"Bag{px}_{ix}{iy}", (px - 19 + ix * 19, py - 11 + iy * 22, 12.5), rnd.choice([canvas, canvas2]), rnd,
                            scale=0.95, tilt=rnd.uniform(-0.1, 0.1))
        for ix in range(2):
            filled_sack(f"BagT{px}_{ix}", (px - 9 + ix * 19, py, 37.5), rnd.choice([canvas, canvas2]), rnd, 0.95, rnd.uniform(-0.15, 0.15))
    F.factory_hall(size=(1600, 1000, 600), floor_mat=floor_m, lamp_rows=[(100, 5), (350, 5)], lamp_strength=20,
                   lamp_temp=3800, center=(0, 300, -6.1))

    # --- 照明
    C.area_light((40, -50, 90), (40, 0, 38), 50, 6.0e4, (1.0, 0.9, 0.78), "Key")
    C.area_light((-40, 60, 70), (55, 0, -145), 40, 3.0e4, (0.65, 0.75, 1.0), "Rim")
    F.spot((5, -10, 80), (0, 0, 20), 2.0e4, (1.0, 0.88, 0.7), size_deg=25, name="SackSpot")
    C.area_light((0, 160, 60), (80, 0, 180), 120, 8e4, (1.0, 0.85, 0.65), "BgFill")

    # --- カメラ
    cam, tgt = C.camera((8, -70, 76), (-6, 0, 33), lens=40, fstop=4.0)
    C.key(cam, "location", 1, (12, -74, 79)); C.key(cam, "location", FRAMES, (4, -62, 70))
    dof = bpy.data.objects.new("Focus", None); bpy.context.collection.objects.link(dof)
    dof.location = (0, 0, 30); cam.data.dof.focus_object = dof
    sc.view_settings.exposure = -0.4


if __name__ == "__main__":
    C.run_shot("h07_bagging", build, FRAMES)
