"""C02: 布のロールから服の形が切り出される。5秒。手は出さない(自動裁断機)。

- 裁断台(緑のカッティングマット)の奥に布のロール。広げた布(ギンガム)の上を、門型の自動裁断機が動く
- 12〜62f: 刃のヘッドがシャツの形をなぞり、濃い切り線が伸びる
- 62〜76f: 門型が奥へ退く。72f〜: シャツ形の布が持ち上がり、布にシャツ形の穴が残る
- 84〜108f: 布がこちらへ起き上がり、襟・前立て・ボタン・ポケット・袖口が順に付いて「平置きのシャツ」になる
透明素材なし。布と切り抜きは同じ模様(切り抜きの模様は自分の座標、布は最初の位置に置いた Empty の座標)。
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import bmesh
from mathutils import Vector
import common as C
import props as P
import factory_parts as F
import fuku_parts as FK

FRAMES = 120
CUT0, CUT1 = 12, 62
LIFT = 72
SHEET_Z = 0.3            # マット上面
TH = 0.25                # 布の厚み
FAB = (0.16, 0.32, 0.62)  # 青のギンガム
FAB2 = (0.93, 0.94, 0.95)


def shirt_outline():
    """平置きシャツ(半袖)の外形。XY、襟が +Y。"""
    half = [(0.0, 31.0), (4.5, 32.8), (8.0, 35.0), (19.0, 32.0), (33.0, 21.0), (27.0, 12.5), (21.5, 17.5),
            (22.0, 0.0), (23.0, -30.0), (19.0, -33.0), (10.0, -34.5), (0.0, -35.0)]
    return half + [(-x, y) for x, y in reversed(half[1:-1])]


def resample(poly, n):
    pts = [Vector((x, y)) for x, y in poly] + [Vector(poly[0])]
    seg = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(seg)
    out = []
    for k in range(n):
        d = total * k / n
        i = 0
        while d > seg[i]:
            d -= seg[i]; i += 1
        out.append(pts[i].lerp(pts[i + 1], d / seg[i]))
    return out


def prism_obj(name, poly, z0, z1, mat=None):
    bm = bmesh.new()
    vb = [bm.verts.new((x, y, z0)) for x, y in poly]
    vt = [bm.verts.new((x, y, z1)) for x, y in poly]
    bm.faces.new(vb[::-1]); bm.faces.new(vt)
    for i in range(len(poly)):
        j = (i + 1) % len(poly)
        bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = FK.mesh_object(name, me)
    if mat:
        o.data.materials.append(mat)
    return o


def mat_mat(name="CutMat"):
    """緑のカッティングマット(細かい方眼。文字なし)。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    br = n.new("ShaderNodeTexBrick"); br.offset = 0.0
    br.inputs["Scale"].default_value = 1.0; br.inputs["Mortar Size"].default_value = 0.12
    br.inputs["Brick Width"].default_value = 5.0; br.inputs["Row Height"].default_value = 5.0
    br.inputs["Color1"].default_value = (0.08, 0.26, 0.17, 1); br.inputs["Color2"].default_value = (0.08, 0.25, 0.16, 1)
    br.inputs["Mortar"].default_value = (0.35, 0.55, 0.42, 1)
    C.link(nt, tc.outputs["Object"], br.inputs["Vector"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.55
    C.link(nt, br.outputs["Color"], p.inputs["Base Color"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def build(sc):
    P.world_studio((0.1, 0.09, 0.08), (0.35, 0.33, 0.3), (0.6, 0.58, 0.55), 0.6, camera_color=(0.2, 0.19, 0.18))
    # 部屋(縫製工場の明るい床と奥の壁)
    P.plane("Floor", (1200, 1200), (0, 0, -90), mat=F.mat_concrete("FloorC", (0.45, 0.43, 0.4), rough=0.6))
    P.plane("BackWall", (1200, 400), (0, 260, 110), rot=(90, 0, 0), mat=C.principled("WallM", (0.78, 0.76, 0.72), rough=0.85))
    # 裁断台
    wood = P.mat_wood("TableWood", base=(0.6, 0.45, 0.3), scale=0.1)
    P.box("TableTop", (220, 170, 4), (0, 15, -2), mat=wood, bevel=0.4)
    leg = F.mat_painted("LegM", (0.25, 0.27, 0.3), rough=0.5, wear=0.1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box(f"Leg{sx}{sy}", (6, 6, 86), (sx * 100, 15 + sy * 75, -47), mat=leg)
    P.box("Mat", (190, 150, SHEET_Z), (0, 10, SHEET_Z / 2), mat=mat_mat())

    # ---- 布の模様の基準: シャツ片の最初の位置
    piece_c = Vector((0, 4, SHEET_Z))
    coord = bpy.data.objects.new("FabricCoord", None); bpy.context.collection.objects.link(coord)
    coord.location = piece_c
    m_sheet = FK.mat_cloth("FabricSheet", FAB2, FAB, "check", scale=0.26, coord=coord, check_axis="Y", weave=0.2)

    # ---- ロール(奥)と広げた布
    R = 9.0
    roll_y = 72.0
    roll = P.cyl("Roll", R, 160, (0, roll_y, SHEET_Z + R), (0, math.pi / 2, 0), mat=m_sheet, verts=64)
    core_m = C.principled("CoreM", (0.55, 0.42, 0.28), rough=0.8)
    P.cyl("RollCore", 3.0, 166, (0, roll_y, SHEET_Z + R), (0, math.pi / 2, 0), mat=core_m, verts=32)
    ring_m = C.principled("RollRingM", (0.3, 0.42, 0.58), rough=0.8)
    for s in (-1, 1):
        for k, r in enumerate((4.5, 6.0, 7.5)):
            bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.1, major_segments=48, minor_segments=4,
                                             location=(s * 80.02, roll_y, SHEET_Z + R), rotation=(0, math.pi / 2, 0))
            bpy.context.object.data.materials.append(ring_m)
    outline = shirt_outline()
    sheet = P.box("Sheet", (156, roll_y - (-58), TH), (0, (roll_y - 58) / 2, SHEET_Z + TH / 2), mat=m_sheet)
    hole = prism_obj("HoleCutter", [(x + piece_c.x, y + piece_c.y) for x, y in outline], -5, 5)
    bo = sheet.modifiers.new("hole", "BOOLEAN"); bo.object = hole; bo.operation = "DIFFERENCE"; bo.solver = "EXACT"
    FK.bake_modifiers(sheet)
    bpy.data.objects.remove(hole, do_unlink=True)

    # ---- シャツ片(原点=中心)。模様は自分の座標
    m_piece = FK.mat_cloth("FabricPiece", FAB2, FAB, "check", scale=0.26, check_axis="Y", weave=0.2)
    piece = prism_obj("Piece", outline, 0, TH, m_piece)
    m_piece.node_tree.nodes["Texture Coordinate"].object = piece
    pivot = bpy.data.objects.new("PiecePivot", None); bpy.context.collection.objects.link(pivot)
    pivot.location = piece_c
    piece.parent = pivot
    bv = piece.modifiers.new("bv", "BEVEL"); bv.width = 0.08; bv.segments = 1

    # ---- 仕立て(後から現れる部品。ピースの子、上面 z=TH)
    trim = FK.mat_cloth("Trim", FAB2, FAB, "check", scale=0.26, check_axis="Y", weave=0.2)
    trim.node_tree.nodes["Texture Coordinate"].object = piece
    white = C.principled("BtnM", (0.95, 0.94, 0.9), rough=0.3)
    details = []
    for s in (-1, 1):   # 襟先
        c = prism_obj(f"Collar{s}", [(s * 0.6, 32.0), (s * 9.0, 34.6), (s * 5.5, 25.5)], TH, TH + 0.35, trim)
        details.append((c, 88))
    band = prism_obj("CollarBand", [(-8.5, 34.4), (8.5, 34.4), (7.5, 36.0), (-7.5, 36.0)], TH, TH + 0.3, trim)
    details.append((band, 86))
    plk = prism_obj("Placket", [(-1.6, 31.0), (1.6, 31.0), (1.6, -34.5), (-1.6, -34.5)], TH, TH + 0.2, trim)
    details.append((plk, 92))
    for i in range(6):
        y = 27.0 - i * 11.0
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.75, depth=0.25, location=(0, y, TH + 0.35))
        b = bpy.context.object; b.name = f"Btn{i}"; b.data.materials.append(white)
        details.append((b, 95 + i * 2))
    pk = prism_obj("Pocket", [(-17.0, 18.0), (-7.0, 18.0), (-7.0, 7.0), (-12.0, 5.5), (-17.0, 7.0)], TH, TH + 0.25, trim)
    details.append((pk, 98))
    for s in (-1, 1):   # 袖口の折り返し
        a = Vector((s * 33.0, 21.0)); b2 = Vector((s * 27.0, 12.5))
        d = (b2 - a).normalized(); nrm = Vector((-d.y, d.x)) * (-s)
        poly = [a, b2, b2 - nrm * 3.2, a - nrm * 3.2]
        cf = prism_obj(f"Cuff{s}", [(p.x, p.y) for p in poly], TH, TH + 0.3, trim)
        details.append((cf, 100))
    for o, f in details:
        o.parent = piece
        bm_ = o.modifiers.new("bv", "BEVEL"); bm_.width = 0.08; bm_.segments = 1
        o.scale = (0.001, 0.001, 0.001)
        o.keyframe_insert("scale", frame=f)
        o.scale = (1.12, 1.12, 1.12); o.keyframe_insert("scale", frame=f + 5)
        o.scale = (1, 1, 1); o.keyframe_insert("scale", frame=f + 8)
    # 部品の拡大の中心を各部品の中心にする
    for o, f in details:
        if o.type == "MESH" and not o.name.startswith("Btn"):
            cen = sum((v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
            for v in o.data.vertices:
                v.co -= cen
            o.location = cen

    # ---- 切り線(暗い溝)。ヘッドの後を伸びる
    pts = resample(outline, 240)
    cu = bpy.data.curves.new("CutLineC", "CURVE"); cu.dimensions = "3D"
    cu.bevel_depth = 0.22; cu.bevel_resolution = 2
    sp = cu.splines.new("POLY"); sp.points.add(len(pts))
    for p_, q in zip(sp.points, pts + [pts[0]]):
        p_.co = (q.x + piece_c.x, q.y + piece_c.y, SHEET_Z + TH + 0.02, 1)
    cu.bevel_factor_mapping_end = "SPLINE"
    cu.materials.append(C.principled("CutLineM", (0.03, 0.05, 0.09), rough=0.7))
    line = bpy.data.objects.new("CutLine", cu); bpy.context.collection.objects.link(line)
    cu.bevel_factor_end = 0.0; cu.keyframe_insert("bevel_factor_end", frame=CUT0)
    cu.bevel_factor_end = 1.0; cu.keyframe_insert("bevel_factor_end", frame=CUT1)
    F.set_interp(cu, "LINEAR")
    for o_, f, v in ((line, 1, True), (line, CUT0 + 1, False), (line, LIFT + 1, True)):
        o_.hide_render = v; o_.keyframe_insert("hide_render", frame=f)
    F.set_interp(line, "CONSTANT", path="hide_render")

    # ---- 門型の自動裁断機(ロゴなし)
    gm = F.mat_painted("GantryM", (0.86, 0.86, 0.84), rough=0.4, wear=0.05)
    acc = F.mat_painted("AccentM", (0.92, 0.5, 0.15), rough=0.4, wear=0.05)
    steel = F.mat_steel("RailSteel", (0.7, 0.7, 0.72), rough=0.2)[0]
    for s in (-1, 1):
        P.box(f"Rail{s}", (4, 160, 3), (s * 104, 15, 1.5), mat=steel)
    gantry = bpy.data.objects.new("Gantry", None); bpy.context.collection.objects.link(gantry)
    parts = [P.box("Beam", (216, 9, 7), (0, 0, 24), mat=gm, bevel=0.6)]
    for s in (-1, 1):
        parts.append(P.box(f"Post{s}", (8, 12, 26), (s * 104, 0, 13), mat=acc, bevel=0.6))
    for o in parts:
        o.parent = gantry
    carriage = bpy.data.objects.new("Carriage", None); bpy.context.collection.objects.link(carriage)
    carriage.parent = gantry
    hp = [P.box("HeadBox", (11, 14, 10), (0, -9, 23), mat=acc, bevel=0.8),
          P.cyl("HeadTube", 2.2, 14, (0, -9, 12), mat=gm, verts=24),
          P.cyl("HeadFoot", 3.2, 1.2, (0, -9, 5.5), mat=steel, verts=24),
          P.box("Blade", (0.15, 1.6, 5.0), (0, -9, 2.6), mat=steel)]
    for o in hp:
        o.parent = carriage
    # ヘッド(-9 オフセット)がアウトラインをなぞる
    def head_at(f):
        u = min(1.0, max(0.0, (f - CUT0) / (CUT1 - CUT0)))
        q = pts[min(len(pts) - 1, int(u * len(pts)))] if u < 1 else pts[0]
        return q.x + piece_c.x, q.y + piece_c.y + 9.0
    start = head_at(CUT0)
    for f in range(1, FRAMES + 1):
        if f <= CUT0:
            k = (f - 1) / (CUT0 - 1)
            k = k * k * (3 - 2 * k)
            gx, gy = 60 + (start[0] - 60) * k, 95 + (start[1] - 95) * k
        elif f <= CUT1:
            gx, gy = head_at(f)
        else:
            k = min(1.0, (f - CUT1) / 14.0); k = k * k * (3 - 2 * k)
            gx, gy = start[0] + (40 - start[0]) * k, start[1] + (92 - start[1]) * k
        gantry.location = (0, gy, 0); gantry.keyframe_insert("location", frame=f)
        carriage.location = (gx, 0, 0); carriage.keyframe_insert("location", frame=f)
    # 刃は切っている間だけ下がる
    for f, z in ((1, 3.0), (CUT0 - 2, 3.0), (CUT0, 0.0), (CUT1, 0.0), (CUT1 + 3, 3.0)):
        hp[3].location.z = 2.6 + z; hp[3].keyframe_insert("location", index=2, frame=f)

    # ---- シャツ片: 持ち上がり、こちらへ起き上がって仕立てられる
    up = [(1, piece_c), (LIFT, piece_c), (LIFT + 12, piece_c + Vector((0, 0, 12))),
          (104, Vector((34, -32, 30))), (FRAMES, Vector((35, -33, 31.5)))]
    P.key_seq(pivot, "location", [(f, tuple(v)) for f, v in up])
    P.key_seq(pivot, "rotation_euler", [(1, (0, 0, 0)), (LIFT + 8, (0, 0, 0)), (104, (math.radians(58), 0, math.radians(-8))),
                                        (FRAMES, (math.radians(60), 0, math.radians(-8)))])
    # 少しふくらむ(平らな布 → 縫ったシャツの厚み)
    P.key_seq(piece, "scale", [(1, (1, 1, 1)), (88, (1, 1, 1)), (104, (1, 1, 3.0))])

    # ---- 照明: 天井の大きな柔らかい光 + 左からのキー + 右奥のリム
    top = C.area_light((0, 10, 260), (0, 0, 0), 300, 1.0e6, (1.0, 0.97, 0.92), "Top")
    key = C.area_light((-200, -150, 180), (0, 0, 0), 150, 6e5, (1.0, 0.9, 0.78), "Key"); C.light_look_at(key, (0, 0, 10))
    rim = C.area_light((180, 200, 140), (0, 0, 0), 150, 4e5, (0.85, 0.9, 1.0), "Rim"); C.light_look_at(rim, (0, 0, 20))
    P.reflection_probe((0, 0, 60), radius=300, clip_start=1)

    # ---- カメラ: 手前上から見下ろし、終盤は起き上がったシャツへ少し寄る
    cam, tgt = C.camera((0, -165, 150), (0, 8, 6), lens=40)
    P.key_seq(cam, "location", [(1, (-14, -150, 175)), (70, (-6, -150, 165)), (FRAMES, (10, -175, 140))])
    P.key_seq(tgt, "location", [(1, (0, 6, 0)), (70, (0, 4, 2)), (FRAMES, (16, -6, 12))])
    sc.view_settings.exposure = 0.0


if __name__ == "__main__":
    C.EPISODE = "ep04"
    C.run_shot("c02_fabric_cut", build, FRAMES)
