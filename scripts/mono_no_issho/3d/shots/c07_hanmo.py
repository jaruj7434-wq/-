"""C07 / カット 5-4: 反毛(はんもう)。宙に浮いた1枚のTシャツが、上から順にほどけて、ふわふわの短い繊維
(くるっと曲がった糸くず)になって舞い上がり、綿雲のように渦を巻く。やがて繊維が下へ集まって押し固められ、
台の上で平らなフェルトの板(防音材)になる。スタジオ・明るく暖かいトーン。5秒。

仕組み: 繊維 7000 本は 1 つの点群(GN)で、点ごとに「服の上 A → 綿雲 B → 板の中 C」の 3 位置と
開始・終了フレームを属性で持ち、シーン時間で補間する(キーフレーム・物理なし)。
Tシャツは add_reveal のディゾルブで上から消え、消えた所の繊維から順に飛び出す。板は下から現れて厚みが締まる。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import bmesh
import numpy as np
from mathutils import Vector
import common as C
import props as P
import factory_parts as F
import pet_parts2 as Q
import fuku_parts2 as K

FRAMES = 120
N_FIB = 9000
SHIRT_Z = 58.0                 # Tシャツの中心の高さ
BOARD = (64.0, 42.0, 2.6)      # 板(x, y, 厚さ)
BOARD_Z = 3.0                  # 台の上面
SHIRT_COLOR = (0.13, 0.36, 0.52)
D0, D1 = 14, 52                # Tシャツが消えていく区間(上端 → 下端)


def shirt_outline():
    """Tシャツの輪郭(XZ 平面、正面 -Y 向き)。中心原点、幅 ~52cm、高さ ~62cm。"""
    pts = [(-9, 31), (-6.5, 27.5), (-3, 26), (0, 25.6), (3, 26), (6.5, 27.5), (9, 31),
           (17, 29), (26, 22), (21, 13), (16, 16), (16, -31), (-16, -31), (-16, 16), (-21, 13), (-26, 22), (-17, 29)]
    return pts


def inside(poly, x, y):
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]; xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
            c = not c
        j = i
    return c


def shirt_mesh(name, mat):
    """輪郭の多角形を三角分割 → 細分化 → 厚み・しわ。原点=中心、XZ 平面。"""
    poly = shirt_outline()
    bm = bmesh.new()
    vs = [bm.verts.new((x, 0, z)) for x, z in poly]
    bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    for _ in range(4):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    for v in bm.verts:
        x, _, z = v.co
        v.co.y = 0.5 * math.sin(0.25 * x + 0.3 * z) + 0.35 * math.cos(0.5 * z - 0.2 * x) + 0.0012 * x * x
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    me.materials.append(mat)
    P.add_mod(o, "SOLIDIFY", thickness=0.35, offset=0)
    return o, poly


def mat_felt(name, base=(0.30, 0.33, 0.36), fleck=(0.13, 0.36, 0.52)):
    """反毛フェルト(防音材): 灰色がかった地に、元の服の色がまだらに混ざる。細かい繊維の筋と毛羽のバンプ。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.35; nz.inputs["Detail"].default_value = 4
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[0].color = (*fleck, 1)
    cr.color_ramp.elements[1].position = 0.65; cr.color_ramp.elements[1].color = (*base, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    # 繊維の筋: 細かいノイズを方向を変えて2つ
    fibers = []
    for k, sc_ in enumerate(((9, 1.2, 9), (1.2, 9, 9))):
        mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = sc_
        mp.inputs["Rotation"].default_value = (0, 0, 0.6 * k)
        C.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
        fz = n.new("ShaderNodeTexNoise"); fz.inputs["Scale"].default_value = 1.5; fz.inputs["Detail"].default_value = 6
        C.link(nt, mp.outputs["Vector"], fz.inputs["Vector"])
        fibers.append(fz)
    fm = n.new("ShaderNodeMath"); fm.operation = "MAXIMUM"
    C.link(nt, fibers[0].outputs["Fac"], fm.inputs[0]); C.link(nt, fibers[1].outputs["Fac"], fm.inputs[1])
    fr = n.new("ShaderNodeMapRange"); fr.inputs["From Min"].default_value = 0.4; fr.inputs["From Max"].default_value = 0.8
    fr.inputs["To Min"].default_value = 0.7; fr.inputs["To Max"].default_value = 1.25
    C.link(nt, fm.outputs[0], fr.inputs["Value"])
    mul = n.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
    C.link(nt, cr.outputs["Color"], mul.inputs["A"]); C.link(nt, fr.outputs["Result"], mul.inputs["B"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.95
    p.inputs["Sheen Weight"].default_value = 0.35; p.inputs["Sheen Roughness"].default_value = 0.5
    C.link(nt, mul.outputs["Result"], p.inputs["Base Color"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.5; b.inputs["Distance"].default_value = 0.1
    C.link(nt, fm.outputs[0], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def build(sc):
    rnd = random.Random(7)
    nrng = np.random.default_rng(7)
    P.world_studio((0.10, 0.09, 0.08), (0.42, 0.38, 0.33), (0.95, 0.9, 0.84), 1.0, camera_color=(0.50, 0.45, 0.39))
    # --- スタジオの床(ゆるいホリゾント)と台
    floor_m = C.principled("StudioFloor", (0.52, 0.46, 0.40), rough=0.6)
    bpy.ops.mesh.primitive_plane_add(size=1)
    fl = bpy.context.object; fl.name = "Cyc"
    bm = bmesh.new(); bm.from_mesh(fl.data); bm.clear()
    rows = []
    for k in range(25):
        t = k / 24
        a = t * math.pi / 2
        y = -400 + 600 * min(t * 2, 1) if t < 0.5 else 200 + 120 * math.sin(a * 2 - math.pi / 2 + math.pi / 2) * 0 + 120 * math.sin((t - 0.5) * math.pi)
        z = 0 if t < 0.5 else 120 * (1 - math.cos((t - 0.5) * math.pi))
        rows.append((y, z))
    rows.append((320, 400))
    vs = [[bm.verts.new((x, y, z)) for x in (-600, 600)] for y, z in rows]
    for i in range(len(vs) - 1):
        bm.faces.new((vs[i][0], vs[i][1], vs[i + 1][1], vs[i + 1][0]))
    bm.to_mesh(fl.data); bm.free()
    fl.data.materials.append(floor_m)
    for p_ in fl.data.polygons:
        p_.use_smooth = True
    ped_m = C.principled("Pedestal", (0.50, 0.45, 0.40), rough=0.6)
    P.box("Pedestal", (90, 64, BOARD_Z), (0, 0, BOARD_Z / 2), mat=ped_m, bevel=0.5)

    # --- Tシャツ
    jer = Q.mat_jersey("Jersey", SHIRT_COLOR, scale=6.0)
    shirt, poly = shirt_mesh("Shirt", jer)
    shirt.location = (0, 0, SHIRT_Z)
    shirt.rotation_euler = (math.radians(-8), 0, 0)
    rv = Q.add_reveal(jer, "Z", noise_amt=0.5, edge_color=(1.0, 0.92, 0.8), edge_strength=2.5, edge_width=0.8, coord_obj=shirt)
    # Reveal は Z(cm) の上限: 上端 34 → 下端 -36 へ下げると上から消える
    F.key_socket(rv, 1, 40.0); F.key_socket(rv, D0, 34.0); F.key_socket(rv, D1, -38.0)
    F.set_interp(jer.node_tree, "LINEAR")
    P.key_seq(shirt, "location", [(1, (0, 0, SHIRT_Z - 1.5)), (D1, (0, 0, SHIRT_Z + 1.5))])
    P.key_seq(shirt, "rotation_euler", [(1, (math.radians(-8), 0, math.radians(-4))), (D1, (math.radians(-4), 0, math.radians(5)))])

    # --- 繊維の部品(色5種 × 形4種)
    cols = [SHIRT_COLOR, (0.30, 0.55, 0.70), (0.55, 0.72, 0.82), (0.86, 0.88, 0.88), (0.20, 0.45, 0.60)]
    cw = np.array([2.5, 4, 3.5, 2.0, 2.5]); cw = cw / cw.sum()
    fmats = [K.mat_fiber(f"Fib{i}", c) for i, c in enumerate(cols)]
    meshes = []
    for i in range(20):
        me = K.fiber_mesh(f"FibMesh{i}", rnd, length=rnd.uniform(1.6, 2.6), radius=0.06, curl=rnd.uniform(0.3, 0.55))
        me.materials.append(fmats[i % len(fmats)] if i >= 5 else fmats[0])
        meshes.append(me)
    coll = Q.instance_collection("FibParts", meshes, fmats)
    # 色の重み: 部品 index ごとに色が決まるので、点の var を色の重みで選ぶ
    var_col = np.array([0 if i < 5 else i % len(fmats) for i in range(20)])

    # --- 点: A = Tシャツの上(輪郭内に一様)、B = 綿雲(楕円体)、C = 板の中
    A = []; zA = []
    while len(A) < N_FIB:
        x, z = nrng.uniform(-27, 27), nrng.uniform(-32, 32)
        if inside(poly, x, z):
            A.append((x, nrng.uniform(-0.3, 0.3), z)); zA.append(z)
    A = np.array(A); zA = np.array(zA)
    from mathutils import Euler, Matrix
    mw = Matrix.Translation((0, 0, SHIRT_Z)) @ Euler((math.radians(-6), 0, 0)).to_matrix().to_4x4()
    # Tシャツの動き(平均)に合わせ、中間の姿勢でワールドへ
    Aw = np.array([tuple(mw @ Vector(p)) for p in A])
    # 消える時刻(上から): Reveal が z を通過するフレーム + ノイズ
    t_dis = D0 + (34.0 - zA) / (34.0 + 38.0) * (D1 - D0) + nrng.uniform(-2, 4, N_FIB)
    a0 = t_dis - 1.0; a1 = a0 + nrng.uniform(20, 32, N_FIB)
    # 綿雲: 上に膨らむ楕円体(中心 0,0,52)
    cen = np.array([0.0, 0.0, 46.0])
    # 綿のかたまり(房)の集まり: 半分は 60 個の房のまわり、残りは全体に薄く
    rad = np.array([44.0, 26.0, 26.0])

    def in_ellipsoid(n, power):
        u = nrng.normal(size=(n, 3)); u /= np.linalg.norm(u, axis=1)[:, None]
        return u * (nrng.random(n) ** power)[:, None] * rad
    tufts = in_ellipsoid(60, 0.6)
    k = N_FIB // 2
    B = np.empty((N_FIB, 3))
    B[:k] = tufts[nrng.integers(0, 60, k)] + nrng.normal(0, 4.5, (k, 3))
    B[k:] = in_ellipsoid(N_FIB - k, 0.5)
    B += cen
    # 下にあった繊維ほど下へ
    B[:, 2] += (Aw[:, 2] - SHIRT_Z) * 0.35
    # 板: 上の方の繊維ほど板の上面に(積み重なる感じ)
    order = np.argsort(np.argsort(B[:, 2]))
    Cz = BOARD_Z + 0.25 + (order / N_FIB) * (BOARD[2] - 0.6)
    Cc = np.column_stack([nrng.uniform(-BOARD[0] / 2 + 1, BOARD[0] / 2 - 1, N_FIB),
                          nrng.uniform(-BOARD[1] / 2 + 1, BOARD[1] / 2 - 1, N_FIB), Cz])
    # 集まる順: 雲の下の方から(下に降りていく)
    b0 = 64 + (B[:, 2] - B[:, 2].min()) / (np.ptp(B[:, 2]) + 1e-6) * 22 + nrng.uniform(-3, 3, N_FIB)
    b0 = np.maximum(b0, a1 + 2)
    b1 = np.minimum(b0 + nrng.uniform(14, 20, N_FIB), 110)
    b0 = np.minimum(b0, b1 - 6)
    sA = nrng.uniform(0.6, 0.9, N_FIB)         # 出番(a0)までは GN 側で隠す
    sB = nrng.uniform(0.9, 1.35, N_FIB)
    # 板に入ったら縮んで消える(板の表面が代わりに見える)。表面の 1 割だけ毛羽として残す
    sC = np.where(order > N_FIB * 0.9, nrng.uniform(0.35, 0.55, N_FIB), 0.0)
    Cc[:, 2] = np.where(order > N_FIB * 0.9, BOARD_Z + BOARD[2] + 0.05, Cc[:, 2])
    # var: 色の重みで選ぶ
    col_pick = nrng.choice(len(fmats), N_FIB, p=cw)
    groups = [np.where(var_col == c)[0] for c in range(len(fmats))]
    var = np.array([g[nrng.integers(len(g))] for g in (groups[c] for c in col_pick)])
    rot = nrng.uniform(-math.pi, math.pi, (N_FIB, 3))
    spin = nrng.normal(0, 0.05, (N_FIB, 3))
    K.fluff_object("Fluff", coll, Aw, B, Cc, np.column_stack([a0, a1]), np.column_stack([b0, b1]), sA, sB, sC, rot, spin, var,
                   center=tuple(cen), omega=0.012, drift=5.0, drift_scale=0.05)

    # --- 板(反毛フェルト): 下から現れて、厚みがきゅっと締まる
    felt = mat_felt("Felt", fleck=SHIRT_COLOR)
    board = P.box("Board", (BOARD[0], BOARD[1], BOARD[2]), (0, 0, BOARD[2] / 2), mat=felt, bevel=0.5, segments=3)
    me = board.data
    for v in me.vertices:
        v.co.z += BOARD[2] / 2
    board.location = (0, 0, BOARD_Z)
    P.add_mod(board, "SUBSURF", levels=1, render_levels=1)
    tex = bpy.data.textures.new("FeltBump", "CLOUDS"); tex.noise_scale = 3.0
    P.add_mod(board, "DISPLACE", texture=tex, strength=0.25, texture_coords="LOCAL")
    brv = Q.add_reveal(felt, "X", noise_amt=1.5, edge_color=(1.0, 0.9, 0.75), edge_strength=1.5, edge_width=1.5, coord_obj=board)
    F.key_socket(brv, 1, -60.0); F.key_socket(brv, 78, -40.0); F.key_socket(brv, 108, 42.0)
    P.key_seq(board, "scale", [(76, (1.0, 1.0, 2.2)), (104, (1.0, 1.0, 1.6)), (113, (1.0, 1.0, 0.92)), (119, (1.0, 1.0, 1.0))])

    # --- 照明: 左上のやわらかいキー(暖色)、右奥のリム(繊維のふち)、正面の弱い補助
    key = C.area_light((-120, -110, 170), (0, 0, 0), 160, 1.8e5, (1.0, 0.9, 0.78), "Key"); C.light_look_at(key, (0, 0, 30))
    rim = C.area_light((110, 140, 120), (0, 0, 0), 120, 1.2e5, (0.9, 0.95, 1.0), "Rim"); C.light_look_at(rim, (0, 0, 40))
    fill = C.area_light((80, -200, 60), (0, 0, 0), 200, 4e4, (0.95, 0.95, 1.0), "Fill"); C.light_look_at(fill, (0, 0, 30))

    cam, tgt = C.camera((0, -205, 88), (0, 0, 34), lens=40, fstop=4.0)
    P.key_seq(cam, "location", [(1, (-14, -215, 92)), (FRAMES, (10, -180, 72))])
    P.key_seq(tgt, "location", [(1, (0, 0, 44)), (60, (0, 0, 40)), (FRAMES, (0, 0, 14))])
    cam.data.dof.focus_object = tgt
    sc.view_settings.exposure = 0.2
    sc.view_settings.look = "AgX - Medium High Contrast"


if __name__ == "__main__":
    C.EPISODE = "ep04"
    C.run_shot("c07_hanmo", build, FRAMES)
