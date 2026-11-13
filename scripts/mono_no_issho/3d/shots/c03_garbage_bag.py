"""C03 / カット4-1: 朝の住宅街のごみ集積所。色とりどりの服が詰まった透明なごみ袋が置かれる。5秒。

- ブロック塀の前、道路わきの集積所。左にカラスよけネットをかぶせた白い袋が数個
- 1〜34f: 画面上から透明な袋が下りてきて(手は画面外)、34f で手を離れて少し落ち、つぶれて落ち着く
- カメラはゆっくり寄る。看板・地名・ロゴなし
透明素材は袋1つだけ(Transparent と光沢の Mix。屈折なし、BLENDED なので低サンプルでも粒が出にくい。DOF は使わない)。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import bmesh
from mathutils import Vector, noise
import common as C
import props as P
import factory_parts as F
import fuku_parts as FK

FRAMES = 120
LAND = 36
BAG_POS = (30.0, -18.0)


# ------------------------------------------------------------------ マテリアル
def mat_asphalt(name="Asphalt"):
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    vo = n.new("ShaderNodeTexNoise"); vo.inputs["Scale"].default_value = 1.5; vo.inputs["Detail"].default_value = 2
    C.link(nt, tc.outputs["Object"], vo.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.02; nz.inputs["Detail"].default_value = 6
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.07, 0.07, 0.075, 1); cr.color_ramp.elements[1].color = (0.17, 0.165, 0.16, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.85
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.5; b.inputs["Distance"].default_value = 0.2
    C.link(nt, vo.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def mat_blocks(name="Blocks"):
    """コンクリートブロック塀(39x19cm、XZ 面)。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (math.radians(-90), 0, 0)
    C.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    br = n.new("ShaderNodeTexBrick"); br.offset = 0.5
    br.inputs["Scale"].default_value = 1.0; br.inputs["Mortar Size"].default_value = 1.0
    br.inputs["Brick Width"].default_value = 40.0; br.inputs["Row Height"].default_value = 20.0
    br.inputs["Color1"].default_value = (0.5, 0.49, 0.46, 1); br.inputs["Color2"].default_value = (0.44, 0.43, 0.41, 1)
    br.inputs["Mortar"].default_value = (0.6, 0.59, 0.56, 1)
    C.link(nt, mp.outputs["Vector"], br.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.5; nz.inputs["Detail"].default_value = 4
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs["Factor"].default_value = 0.35
    C.link(nt, br.outputs["Color"], mx.inputs["A"]); C.link(nt, nz.outputs["Color"], mx.inputs["B"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.9
    C.link(nt, mx.outputs["Result"], p.inputs["Base Color"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.5; b.invert = True
    C.link(nt, br.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def mat_bag(name, tint=(0.94, 0.96, 0.97), a_min=0.12, a_max=0.7, rough=0.18, method="DITHERED"):
    """ポリ袋。正面は透け、ふちは白く光る(フレネル風)。a_min を 1 近くにすると不透明な乳白の袋。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.25; nz.inputs["Detail"].default_value = 6
    nz.inputs["Distortion"].default_value = 1.5
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    p = n.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*tint, 1); p.inputs["Roughness"].default_value = rough
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.35; b.inputs["Distance"].default_value = 0.4
    C.link(nt, nz.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    C.link(nt, b.outputs["Normal"], lw.inputs["Normal"])
    mr = n.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = a_min; mr.inputs["To Max"].default_value = a_max
    C.link(nt, lw.outputs["Facing"], mr.inputs["Value"])
    tr = n.new("ShaderNodeBsdfTransparent")
    mx = n.new("ShaderNodeMixShader")
    C.link(nt, mr.outputs["Result"], mx.inputs["Fac"])
    C.link(nt, tr.outputs["BSDF"], mx.inputs[1]); C.link(nt, p.outputs["BSDF"], mx.inputs[2])
    C.link(nt, mx.outputs["Shader"], out.inputs["Surface"])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = method
    return m


# ------------------------------------------------------------------ 袋
def bag_mesh(name, size=(40.0, 34.0, 44.0), seed=0, mat=None, squash=0.0):
    """口をしばったごみ袋(原点=底の中心)。size=(幅, 奥行, 高さ)。"""
    rx, ry, h = size
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=1.0)
    off = Vector((seed * 3.1, seed * 1.7, seed * 0.3))
    for v in bm.verts:
        x, y, z = v.co
        if z < -0.35:                           # 底は平ら
            z = -0.35 + (z + 0.35) * 0.25
        k = 1.0
        if z > 0.45:                            # 口に向かってすぼまる
            t = (z - 0.45) / 0.55
            k = 1.0 - 0.88 * t ** 0.8
            z = 0.45 + (z - 0.45) * 1.25
        bulge = 1.0 + 0.08 * noise.noise(Vector((x, y, z)) * 1.6 + off)
        v.co = Vector((x * k * bulge * rx / 2 * (1 + squash), y * k * bulge * ry / 2 * (1 + squash),
                       (z + 0.4) * h / 1.78 * (1 - squash)))
        # しわ
        d = noise.noise(v.co * 0.18 + off) * 0.9
        v.co += Vector((x, y, 0)).normalized() * d if (x or y) else Vector()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = FK.mesh_object(name, me)
    for poly in o.data.polygons:
        poly.use_smooth = True
    sub = o.modifiers.new("sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 1
    if mat:
        o.data.materials.append(mat)
    # 結び目の耳(2枚)
    top = max(v.co.z for v in o.data.vertices)
    for s in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1.0, location=(s * 3.0, 0, top + 2.5))
        e = bpy.context.object; e.name = f"{name}_Ear{s}"
        e.scale = (4.2, 1.2, 2.6); e.rotation_euler = (0, math.radians(s * 35), 0)
        bpy.ops.object.shade_smooth()
        if mat:
            e.data.materials.append(mat)
        e.parent = o
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=1.6, location=(0, 0, top + 0.6))
    kn = bpy.context.object; kn.name = f"{name}_Knot"; bpy.ops.object.shade_smooth()
    if mat:
        kn.data.materials.append(mat)
    kn.parent = o
    return o


def build(sc):
    rnd = random.Random(7)
    P.world_studio((0.12, 0.11, 0.1), (0.5, 0.55, 0.62), (0.45, 0.6, 0.85), 0.7, camera_color=(0.62, 0.7, 0.8))
    P.plane("Road", (1600, 900), (0, -300, 0), mat=mat_asphalt())
    P.box("WhiteLine", (1600, 14, 0.3), (0, -150, 0.15), mat=C.principled("LineM", (0.85, 0.85, 0.82), rough=0.7))
    # 塀の足元の側溝ふた(コンクリート)
    gut = F.mat_concrete("GutterM", (0.5, 0.49, 0.46), rough=0.85, scale=0.05)
    for i in range(-8, 9):
        P.box(f"Gutter{i}", (49.5, 34, 3), (i * 50, 36, 1.5), mat=gut, bevel=0.4)
    P.box("Wall", (1600, 15, 160), (0, 60.5, 80), mat=mat_blocks())
    P.box("WallCap", (1600, 17, 5), (0, 60.5, 162.5), mat=F.mat_concrete("CapM", (0.55, 0.54, 0.51)))
    # 塀の上の生け垣
    leaf = C.principled("HedgeM", (0.12, 0.26, 0.09), rough=0.7, bump=0.6, bump_scale=0.4)
    for i in range(14):
        x = -520 + i * 80 + rnd.uniform(-15, 15)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0, location=(x, 80, 175 + rnd.uniform(0, 10)))
        h = bpy.context.object; h.scale = (rnd.uniform(48, 62), 30, rnd.uniform(28, 40))
        bpy.ops.object.shade_smooth(); h.data.materials.append(leaf)

    # ---- 先に出されている袋(乳白・不透明)
    m_white = mat_bag("WhiteBag", tint=(0.86, 0.87, 0.86), a_min=0.94, a_max=1.0, rough=0.3)
    others = [((-70, 18), (46, 38, 50), 0), ((-25, 26), (40, 34, 44), 1), ((-95, -22), (36, 32, 38), 2),
              ((-45, -18), (42, 36, 40), 3)]
    domes = []
    for (x, y), size, sd in others:
        b = bag_mesh(f"Bag{sd}", size, seed=sd + 10, mat=m_white, squash=0.08)
        b.location = (x, y, 0); b.rotation_euler = (math.radians(rnd.uniform(-5, 5)), math.radians(rnd.uniform(-5, 5)),
                                                    rnd.uniform(0, math.tau))
        domes.append((x, y, size[0] / 2 * 1.08, size[1] / 2 * 1.08, size[2] * 0.95))
    # ---- カラスよけネット(格子をワイヤーフレーム化。袋の上にかぶせる)
    nx, ny, pitch = 64, 46, 2.6
    x0, y0 = -150.0, -60.0
    bm = bmesh.new()
    grid = [[None] * (ny + 1) for _ in range(nx + 1)]
    H = [[0.0] * (ny + 1) for _ in range(nx + 1)]
    for i in range(nx + 1):
        for j in range(ny + 1):
            x, y = x0 + i * pitch, y0 + j * pitch
            z = 0.4
            for cx, cy, ax, ay, hz in domes:
                q = 1 - ((x - cx) / ax) ** 2 - ((y - cy) / ay) ** 2
                if q > 0:
                    z = max(z, hz * math.sqrt(q) ** 0.7 + 1.0)
            H[i][j] = z
    for _ in range(6):     # すき間でたるむ
        H2 = [row[:] for row in H]
        for i in range(1, nx):
            for j in range(1, ny):
                avg = (H[i - 1][j] + H[i + 1][j] + H[i][j - 1] + H[i][j + 1]) / 4
                H2[i][j] = max(0.4, min(H[i][j], avg) if avg < H[i][j] - 2 else (H[i][j] + avg) / 2)
        H = H2
    for i in range(nx + 1):
        for j in range(ny + 1):
            x, y = x0 + i * pitch, y0 + j * pitch
            grid[i][j] = bm.verts.new((x + 0.6 * math.sin(j * 0.7), y, H[i][j]))
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    me = bpy.data.meshes.new("Net"); bm.to_mesh(me); bm.free()
    net = FK.mesh_object("Net", me)
    wf = net.modifiers.new("wf", "WIREFRAME"); wf.thickness = 0.35; wf.use_even_offset = True
    net.data.materials.append(C.principled("NetM", (0.08, 0.32, 0.55), rough=0.6))
    # ---- 主役: 服が詰まった透明な袋
    piv = bpy.data.objects.new("BagPivot", None); bpy.context.collection.objects.link(piv)
    m_clear = mat_bag("ClearBag", tint=(0.95, 0.97, 0.98), a_min=0.16, a_max=0.7, rough=0.12, method="BLENDED")
    size = (54.0, 46.0, 56.0)
    bag = bag_mesh("ClearBag", size, seed=4, mat=m_clear)
    bag.parent = piv
    colors = [((0.85, 0.12, 0.12), None, None), ((0.95, 0.75, 0.1), None, None), ((0.1, 0.55, 0.55), None, None),
              ((0.92, 0.45, 0.6), None, None), ((0.12, 0.18, 0.38), None, None), ((0.95, 0.95, 0.93), (0.15, 0.3, 0.7), "stripe"),
              ((0.35, 0.65, 0.25), None, None), ((0.95, 0.5, 0.15), None, None), ((0.6, 0.4, 0.75), None, None),
              ((0.93, 0.9, 0.85), (0.8, 0.2, 0.2), "check"), ((0.3, 0.6, 0.9), None, None), ((0.78, 0.66, 0.5), None, None)]
    mats = [FK.mat_cloth(f"Wad{i}", c, c2, pt, scale=0.5, sheen=0.4) for i, (c, c2, pt) in enumerate(colors)]
    # 袋の内側: 布のかたまりを詰め、前面近くに小さく縮めたTシャツ・シャツを押しつける
    k = 0
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2]
    for iz in range(5):
        for ix in range(-2, 3):
            for iy in range(-2, 3):
                p = Vector((ix * 8.5 + rnd.uniform(-2, 2), iy * 8.0 + rnd.uniform(-2, 2), 6 + iz * 8.5 + rnd.uniform(-1.5, 1.5)))
                zf = p.z / hz
                prof = 1.0 if zf < 0.5 else max(0.2, 1.0 - (zf - 0.5) * 2.0)
                if (p.x / (hx * 0.68 * prof)) ** 2 + (p.y / (hy * 0.68 * prof)) ** 2 > 1.0:
                    continue
                w = FK.cloth_wad(f"Wad{k}", (rnd.uniform(9, 11), rnd.uniform(7, 9), rnd.uniform(2.8, 4)), rnd, mats[k % len(mats)])
                w.location = p
                w.rotation_euler = (rnd.uniform(-0.9, 0.9), rnd.uniform(-0.9, 0.9), rnd.uniform(0, math.tau))
                w.parent = piv
                k += 1
    for k, (kind, mi, loc, rot) in enumerate((("tee", 0, (-7, -16.5, 36), (8, 0, -6)), ("tee", 5, (9, -16.5, 30), (-4, 0, 10)),
                                              ("tee", 10, (0, -17.0, 22), (-75, 0, 80)), ("tee", 1, (4, -12.0, 44), (14, 0, -40)))):
        g, _ = FK.garment(f"BagTee{k}", kind, mats[mi], seed=k + 20, collar=(kind == "shirt"), buttons=False)
        g.scale = (0.36, 0.36, 0.36)
        g.location = loc
        g.rotation_euler = tuple(math.radians(v) for v in rot)
        g.parent = piv
    # 下ろす → 手を離れて少し落ちる → つぶれて落ち着く
    bx, by = BAG_POS
    P.key_seq(piv, "location", [(1, (bx - 6, by + 4, 95)), (LAND - 8, (bx - 1, by + 1, 14)), (LAND - 4, (bx, by, 10)),
                                (LAND, (bx, by, 0)), (FRAMES, (bx, by, 0))])
    F.set_interp(piv, "LINEAR", path="location")
    fc = [c for c in F.fcurves(piv) if c.data_path == "location"]
    for c in fc:     # 下ろす部分だけなめらかに
        for kp in c.keyframe_points[:2]:
            kp.interpolation = "BEZIER"
    P.key_seq(piv, "rotation_euler", [(1, (math.radians(4), math.radians(-7), math.radians(-20))),
                                      (LAND - 6, (math.radians(-2), math.radians(3), math.radians(-14))),
                                      (LAND + 6, (math.radians(1.5), math.radians(-1.5), math.radians(-12))),
                                      (LAND + 20, (0, 0, math.radians(-12)))])
    for f, s in ((1, (1, 1, 1)), (LAND - 1, (0.97, 0.97, 1.04)), (LAND + 3, (1.07, 1.07, 0.86)), (LAND + 9, (0.98, 0.98, 1.02)),
                 (LAND + 16, (1.02, 1.02, 0.96)), (LAND + 26, (1.01, 1.01, 0.97))):
        piv.scale = s; piv.keyframe_insert("scale", frame=f)

    # ---- 照明: 朝の日差し(左奥から、影は手前右へ)+ 空の補助光
    bpy.ops.object.light_add(type="SUN")
    sun = bpy.context.object; sun.name = "Sun"
    sun.data.energy = 3.2; sun.data.angle = math.radians(3.0); sun.data.color = (1.0, 0.9, 0.76)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    fill = C.area_light((120, -300, 220), (0, 0, 0), 300, 2.0e5, (0.8, 0.88, 1.0), "SkyFill")
    C.light_look_at(fill, (0, 0, 30))
    fill.data.use_shadow = False
    # 描画を軽く: 金属がないので反射プローブなし、袋は透過影を計算しない、影の最小解像度を粗く(1BU=1cm)
    for L in bpy.data.lights:
        L.shadow_maximum_resolution = 0.2
    m_clear.use_transparent_shadow = False

    # ---- カメラ: 道路側の低い位置から、ゆっくり寄る
    cam, tgt = C.camera((110, -240, 95), (0, 0, 30), lens=35)
    P.key_seq(cam, "location", [(1, (105, -245, 100)), (FRAMES, (80, -185, 78))])
    P.key_seq(tgt, "location", [(1, (-5, 5, 34)), (FRAMES, (12, 0, 28))])
    sc.view_settings.exposure = -0.2


if __name__ == "__main__":
    C.EPISODE = "ep04"
    C.run_shot("c03_garbage_bag", build, FRAMES)
