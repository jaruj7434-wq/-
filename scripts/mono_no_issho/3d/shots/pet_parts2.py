"""第3話(ペットボトル)P05〜P08 用の補助。単位 1BU=1cm。

- 高速キーフレーム(foreach_set): 数百個のフレーク/ペレットを毎フレーム位置指定で動かす
- フレーク・ペレットのメッシュとマテリアル(不透明+Translucent の安い半透明。屈折ガラスは使わない)
- 「育つ山」: 点群(頂点)+ジオメトリノードで小粒を数千〜1万個インスタンス。
  各点に「現れるフレーム」を持たせ、山が円錐状に大きくなる様子を出す(物理ベイク不要)
- 新しいボトル(ラベルなし/無地ラベル)、背景板
(P01〜P04 用の pet_parts.py とは別ファイル)
"""
import math, random

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Vector

import common as C
import props as P
import factory_parts as F


# ------------------------------------------------------------------ キーフレーム
INTERP = {"CONSTANT": 0, "LINEAR": 1, "BEZIER": 2}


def bake_keys(obj, path, frames, values, interp="CONSTANT"):
    """obj.<path> に frames ごとの値(タプルの列)をまとめてキー。大量オブジェクト向け。"""
    ad = obj.animation_data_create()
    if ad.action is None:
        ad.action = bpy.data.actions.new(obj.name + "Act")
    vals = np.asarray(values, dtype=np.float32)
    if vals.ndim == 1:
        vals = vals[:, None]
    fr = np.asarray(frames, dtype=np.float32)
    for i in range(vals.shape[1]):
        fc = ad.action.fcurve_ensure_for_datablock(obj, path, index=i)
        kp = fc.keyframe_points
        kp.add(len(fr))
        kp.foreach_set("co", np.column_stack([fr, vals[:, i]]).ravel())
        kp.foreach_set("interpolation", [INTERP[interp]] * len(fr))
        fc.update()


def linked(src_mesh, name, mat=None, coll=None):
    o = bpy.data.objects.new(name, src_mesh)
    (coll or bpy.context.collection).objects.link(o)
    if mat is not None and not src_mesh.materials:
        src_mesh.materials.append(mat)
    return o


# ------------------------------------------------------------------ 小粒のメッシュ
def flake_mesh(name, rnd, size=1.2, thick=0.05):
    """不規則な多角形の薄片(ボトルの壁を砕いたフレーク)。少し反っている。"""
    k = rnd.randint(5, 8)
    ang = sorted(rnd.uniform(0, math.tau) for _ in range(k))
    sx, sy = size * rnd.uniform(0.35, 0.6), size * rnd.uniform(0.25, 0.45)
    curl = rnd.uniform(-0.12, 0.12)
    bm = bmesh.new()
    top = []
    for a in ang:
        r = rnd.uniform(0.6, 1.0)
        x, y = sx * r * math.cos(a), sy * r * math.sin(a)
        top.append(bm.verts.new((x, y, curl * x * x)))
    f = bm.faces.new(top)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    vs = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=vs, vec=(0, 0, -thick))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return me


def pellet_mesh(name, r=0.2, length=0.32, verts=8):
    """ペレット(短い円柱の角を丸めたもの)。低ポリ。"""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r, depth=length)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if len(e.link_faces) == 2 and
                              abs(e.link_faces[0].normal.z) != abs(e.link_faces[1].normal.z)],
                    offset=r * 0.35, segments=1, affect="EDGES")
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


# ------------------------------------------------------------------ マテリアル
def mat_flake(name, tint=(0.75, 0.88, 0.98), rough=0.12, translucent=0.45, alpha=1.0):
    """PETフレーク: 光沢(コート)+ Translucent(背面から光が透ける)の混合。屈折なしで安い。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    p = n.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*tint, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Coat Weight"].default_value = 1.0
    p.inputs["Coat Roughness"].default_value = 0.03
    p.inputs["Specular IOR Level"].default_value = 0.8
    tr = n.new("ShaderNodeBsdfTranslucent")
    tr.inputs["Color"].default_value = (min(1, tint[0] * 1.05), min(1, tint[1] * 1.05), min(1, tint[2] * 1.05), 1)
    mx = n.new("ShaderNodeMixShader"); mx.inputs["Fac"].default_value = translucent
    C.link(nt, p.outputs["BSDF"], mx.inputs[1]); C.link(nt, tr.outputs["BSDF"], mx.inputs[2])
    final = mx.outputs["Shader"]
    if alpha < 1.0:
        tp = n.new("ShaderNodeBsdfTransparent")
        mx2 = n.new("ShaderNodeMixShader"); mx2.inputs["Fac"].default_value = alpha
        C.link(nt, tp.outputs["BSDF"], mx2.inputs[1]); C.link(nt, final, mx2.inputs[2])
        final = mx2.outputs["Shader"]
        m.surface_render_method = "DITHERED"
    C.link(nt, final, out.inputs["Surface"])
    m.use_backface_culling = False
    return m


def mat_pellet(name, tint=(0.86, 0.92, 0.9), rough=0.22, translucent=0.35):
    """再生PETペレット: 乳白〜半透明。"""
    return mat_flake(name, tint, rough, translucent)


def mat_clear_pet(name, tint=(0.96, 0.98, 1.0), rough=0.02, ior=1.5, thickness=0.04, slab=True):
    """透明PET(屈折あり・薄肉)。数を絞って使う。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    p = n.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*tint, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Transmission Weight"].default_value = 1.0
    p.inputs["IOR"].default_value = ior
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    th = n.new("ShaderNodeValue"); th.outputs[0].default_value = thickness
    C.link(nt, th.outputs[0], out.inputs["Thickness"])
    m.thickness_mode = "SLAB" if slab else "SPHERE"
    if hasattr(m, "use_raytrace_refraction"):
        m.use_raytrace_refraction = True
    m.use_backface_culling = False
    return m


def mat_fake_clear(name, tint=(0.55, 0.62, 0.66), edge=(0.04, 0.05, 0.06), rough=0.05, glow=0.0):
    """遠景用の「透明っぽく見える」不透明マテリアル(屈折・半透明なしで安い)。
    正面は背景色寄りの明るさ、縁(フレネル)は暗く+強い映り込み。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*tint, 1); cr.color_ramp.elements[1].color = (*edge, 1)
    cr.color_ramp.elements[1].position = 0.8
    C.link(nt, lw.outputs["Facing"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled")
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    p.inputs["Coat Weight"].default_value = 1.0
    p.inputs["Coat Roughness"].default_value = 0.02
    if glow:
        p.inputs["Emission Strength"].default_value = glow
        C.link(nt, cr.outputs["Color"], p.inputs["Emission Color"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def add_reveal(mat, obj_axis="Z", noise_amt=0.6, edge_color=(0.35, 0.85, 1.0), edge_strength=8.0, edge_width=0.5,
               coord_obj=None):
    """マテリアルに「下から現れる」ディゾルブを足す。"Reveal" 値ノード(オブジェクト座標の高さ cm)をキーフレーム。
    境目は細く光る(ペレットから形ができていく感じ)。"""
    nt = mat.node_tree; n = nt.nodes
    out = [x for x in n if x.type == "OUTPUT_MATERIAL"][0]
    src = out.inputs["Surface"].links[0].from_socket
    tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ")
    if coord_obj is not None:      # 部品が複数でも、基準オブジェクトの座標でそろって現れる
        tc.object = coord_obj
    C.link(nt, tc.outputs["Object"], sep.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6; nz.inputs["Detail"].default_value = 4
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    h = n.new("ShaderNodeMath"); h.operation = "MULTIPLY_ADD"; h.inputs[1].default_value = noise_amt * 4
    C.link(nt, nz.outputs["Fac"], h.inputs[0]); C.link(nt, sep.outputs[obj_axis], h.inputs[2])
    rv = n.new("ShaderNodeValue"); rv.name = "Reveal"; rv.outputs[0].default_value = 1000.0
    d = n.new("ShaderNodeMath"); d.operation = "SUBTRACT"
    C.link(nt, rv.outputs[0], d.inputs[0]); C.link(nt, h.outputs[0], d.inputs[1])     # >0 なら見える
    vis = n.new("ShaderNodeMath"); vis.operation = "GREATER_THAN"; vis.inputs[1].default_value = 0.0
    C.link(nt, d.outputs[0], vis.inputs[0])
    band = n.new("ShaderNodeMath"); band.operation = "LESS_THAN"; band.inputs[1].default_value = edge_width
    C.link(nt, d.outputs[0], band.inputs[0])
    eb = n.new("ShaderNodeMath"); eb.operation = "MULTIPLY"
    C.link(nt, band.outputs[0], eb.inputs[0]); C.link(nt, vis.outputs[0], eb.inputs[1])
    em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*edge_color, 1)
    em.inputs["Strength"].default_value = edge_strength
    mxe = n.new("ShaderNodeMixShader")
    C.link(nt, eb.outputs[0], mxe.inputs["Fac"]); C.link(nt, src, mxe.inputs[1]); C.link(nt, em.outputs["Emission"], mxe.inputs[2])
    tp = n.new("ShaderNodeBsdfTransparent")
    mxv = n.new("ShaderNodeMixShader")
    C.link(nt, vis.outputs[0], mxv.inputs["Fac"]); C.link(nt, tp.outputs["BSDF"], mxv.inputs[1])
    C.link(nt, mxe.outputs["Shader"], mxv.inputs[2])
    C.link(nt, mxv.outputs["Shader"], out.inputs["Surface"])
    mat.surface_render_method = "DITHERED"
    return rv.outputs[0]


# ------------------------------------------------------------------ 育つ山(GN インスタンス)
def instance_collection(name, meshes, mats):
    """GN 用の部品コレクション(シーンには入れない)。meshes[i] に mats[i % len] を割当。"""
    coll = bpy.data.collections.new(name)
    for i, me in enumerate(meshes):
        if not me.materials:
            me.materials.append(mats[i % len(mats)])
        o = bpy.data.objects.new(f"{name}_{i:02d}", me)
        coll.objects.link(o)
    return coll


def _gn_pile_group(name, coll):
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    n = ng.nodes; L = ng.links.new
    gi = n.new("NodeGroupInput"); go = n.new("NodeGroupOutput")
    ci = n.new("GeometryNodeCollectionInfo"); ci.inputs["Collection"].default_value = coll
    ci.inputs["Separate Children"].default_value = True; ci.inputs["Reset Children"].default_value = True
    ci.transform_space = "ORIGINAL"

    def attr(nm, dt):
        a = n.new("GeometryNodeInputNamedAttribute"); a.data_type = dt; a.inputs["Name"].default_value = nm
        return a.outputs["Attribute"]
    st = n.new("GeometryNodeInputSceneTime")
    rev = attr("reveal", "FLOAT")
    c1 = n.new("FunctionNodeCompare"); c1.data_type = "FLOAT"; c1.operation = "LESS_EQUAL"
    L(rev, c1.inputs["A"]); L(st.outputs["Frame"], c1.inputs["B"])
    c2 = n.new("FunctionNodeCompare"); c2.data_type = "FLOAT"; c2.operation = "GREATER_THAN"
    L(attr("bury", "FLOAT"), c2.inputs["A"]); L(st.outputs["Frame"], c2.inputs["B"])
    an = n.new("FunctionNodeBooleanMath"); an.operation = "AND"
    L(c1.outputs["Result"], an.inputs[0]); L(c2.outputs["Result"], an.inputs[1])
    e2r = n.new("FunctionNodeEulerToRotation"); L(attr("rot", "FLOAT_VECTOR"), e2r.inputs["Euler"])
    iop = n.new("GeometryNodeInstanceOnPoints")
    L(gi.outputs[0], iop.inputs["Points"]); L(an.outputs["Boolean"], iop.inputs["Selection"])
    L(ci.outputs["Instances"], iop.inputs["Instance"]); iop.inputs["Pick Instance"].default_value = True
    L(attr("var", "INT"), iop.inputs["Instance Index"]); L(e2r.outputs["Rotation"], iop.inputs["Rotation"])
    L(attr("scl", "FLOAT"), iop.inputs["Scale"])
    L(iop.outputs["Instances"], go.inputs[0])
    return ng


def points_object(name, pts, reveal, rot, scl, var, bury=None):
    me = bpy.data.meshes.new(name + "Pts")
    me.vertices.add(len(pts))
    me.vertices.foreach_set("co", np.asarray(pts, dtype=np.float32).ravel())
    if bury is None:
        bury = np.full(len(pts), 1e9)
    for nm, dt, data in (("reveal", "FLOAT", reveal), ("bury", "FLOAT", bury), ("scl", "FLOAT", scl), ("var", "INT", var)):
        a = me.attributes.new(nm, dt, "POINT")
        a.data.foreach_set("value", np.asarray(data, dtype=np.int32 if dt == "INT" else np.float32))
    a = me.attributes.new("rot", "FLOAT_VECTOR", "POINT")
    a.data.foreach_set("vector", np.asarray(rot, dtype=np.float32).ravel())
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return o


def pile_height(x, y, k, seed=0, amp=0.35):
    """山の表面のでこぼこ(決定的なサイン和)。"""
    s = seed * 1.7
    return amp * (np.sin(0.45 * x + s) * np.cos(0.38 * y - s) + 0.6 * np.sin(0.9 * (x + y) + 2 * s)
                  + 0.4 * np.cos(1.3 * x - 0.7 * y + s))


def growing_pile(name, coll, n_var, center, r_of_frame, frames, k=0.6, density=6.0, shell=1.2, seed=1,
                 scale_range=(0.85, 1.15), flat=0.0, window=None, core_mat=None, r_core_in=0.8, clip=None):
    """円錐の山が r_of_frame(f) に従って大きくなる。各点は「表面がそこを通過したフレーム」に現れ、
    表面から shell cm より深く埋まったら消す(描画数を抑える)。
    density: 1cm^3 あたりの粒数。flat>0 で粒を表面に沿って寝かせる(フレーク)。clip(x,y)->bool で除外。
    core_mat を渡すと、内側を埋める円錐(隙間から下が透けないように)も作り、半径をキーする。"""
    rnd = np.random.default_rng(seed)
    f_lo, f_hi = frames
    r0 = r_of_frame(f_lo) - shell * 1.5
    r1 = r_of_frame(f_hi)
    vol = lambda r: math.pi * k * r ** 3 / 3
    n = int((vol(r1) - vol(max(r0, 0.0))) * density)
    # 体積内に一様に(r^3 で半径を引く)、角度と高さもランダム
    u = rnd.random(n)
    rr = (max(r0, 0) ** 3 + u * (r1 ** 3 - max(r0, 0) ** 3)) ** (1 / 3)      # 点が属する円錐の大きさ
    rho = rr * np.sqrt(rnd.random(n))                                       # 中心からの距離(底面内)
    th = rnd.uniform(0, math.tau, n)
    x = rho * np.cos(th); y = rho * np.sin(th)
    bump = pile_height(x, y, k, seed)
    z_surf = k * (rr - rho)
    z = z_surf + bump * np.clip((rr - rho) / 2.0, 0, 1)                    # 縁では凹凸を消す
    # 現れるフレーム: r_of_frame(f) >= rr となる最初の f
    fs = np.arange(f_lo - 200, f_hi + 1, dtype=np.float32)
    rf = np.array([r_of_frame(float(f)) for f in fs])
    reveal = np.interp(rr, rf, fs)
    keep = rr >= r0
    if clip is not None:
        keep &= ~clip(x + center[0], y + center[1])
    x, y, z, reveal, rr, rho, th = (a[keep] for a in (x, y, z, reveal, rr, rho, th))
    n = len(x)
    rot = rnd.uniform(-math.pi, math.pi, (n, 3))
    if flat:
        # 斜面に沿って寝かせる: Rz(方位) * Ry(斜面の傾き) * Rx(ゆらぎ) * Rz(自転)
        slope = math.atan(k)
        wob = rnd.normal(0, 0.35 * flat + (1 - flat) * 1.5, n)
        til = slope + rnd.normal(0, 0.3, n)
        spin = rnd.uniform(0, math.tau, n)
        out = np.empty((n, 3))
        for i in range(n):
            m = (Euler((wob[i], til[i], th[i]), "XYZ").to_matrix() @ Euler((0, 0, spin[i]), "XYZ").to_matrix())
            e = m.to_euler("XYZ"); out[i] = (e.x, e.y, e.z)
        rot = out
    scl = rnd.uniform(*scale_range, n)
    var = rnd.integers(0, n_var, n)
    pts = np.column_stack([x + center[0], y + center[1], z + center[2]])
    # 表面から shell cm 埋まったフレームで消す(window を指定したら reveal+window で消す)
    if window is None:
        bury = np.interp(rr + shell, rf, fs, right=1e9)
    else:
        bury = reveal + window
    o = points_object(name, pts, reveal, rot, scl, var, bury)
    mod = o.modifiers.new("Pile", "NODES")
    mod.node_group = _gn_pile_group(name + "GN", coll)
    f_mid = (f_lo + f_hi) // 2
    window = int(np.sum((reveal <= f_mid) & (bury > f_mid)))   # 参考: 中間フレームの表示数
    core = None
    if core_mat is not None:
        core = cone(name + "Core", 1.0, k, center, core_mat)
        fr = list(range(f_lo, f_hi + 1))
        sv = [max(0.01, r_of_frame(f) - r_core_in) for f in fr]
        bake_keys(core, "scale", fr, [(s, s, s) for s in sv], "LINEAR")
    return o, core, window


def cone(name, r, k, loc, mat=None, verts=48):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=0, depth=k * r, location=(loc[0], loc[1], loc[2] + k * r / 2))
    o = bpy.context.object; o.name = name
    # 原点を底面中心へ
    o.data.transform(__import__("mathutils").Matrix.Translation((0, 0, k * r / 2)))
    o.location = loc
    if mat:
        o.data.materials.append(mat)
    return o


def mat_pile_core(name, tint, rough=0.4, scale=3.0):
    """山の芯(粒の隙間から見える奥): 粒っぽいノイズの陰影付き。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = scale
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (tint[0] * 0.25, tint[1] * 0.25, tint[2] * 0.25, 1)
    cr.color_ramp.elements[1].color = (tint[0] * 0.7, tint[1] * 0.7, tint[2] * 0.7, 1)
    C.link(nt, vo.outputs["Distance"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = rough
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


# ------------------------------------------------------------------ 落下の軌道
def drag_fall(z0, vz0, t, vt=130.0, g=981.0):
    """空気抵抗(終端速度 vt)付きの落下。t 秒後の z と vz(下向き負)。"""
    tau = vt / g
    # v(t) = -vt + (vz0 + vt) e^{-t/tau}
    e = math.exp(-t / tau)
    v = -vt + (vz0 + vt) * e
    z = z0 - vt * t + (vz0 + vt) * tau * (1 - e)
    return z, v


# ------------------------------------------------------------------ ボトル
BOTTLE_PROFILE = [   # (r, z) 500ml 角のない丸ボトル。底は花形(ペタロイド)を角度で変調
    (0.0, 0.55), (0.9, 0.45), (1.8, 0.05), (2.7, 0.15), (3.15, 0.8), (3.28, 1.8), (3.3, 3.0),
    (3.3, 7.6), (3.12, 8.3), (3.12, 8.9), (3.3, 9.5), (3.3, 13.6), (3.18, 14.6), (2.85, 15.8),
    (2.25, 17.0), (1.62, 18.15), (1.38, 18.7), (1.36, 18.95), (1.62, 19.0), (1.62, 19.25), (1.3, 19.3),
    (1.3, 20.7)]


def bottle_mesh(name, segs=40, fill_z=None, profile=BOTTLE_PROFILE, feet=5):
    """回転体のボトル(片面・薄肉は SLAB で表現)。fill_z を与えると、それより下の面に
    マテリアル番号1(中身入り)を割り当てる。口は開いたまま(キャップで隠す)。"""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        ring = []
        for j in range(segs):
            a = math.tau * j / segs
            rr, zz = r, z
            if z < 2.2 and r > 0.5:      # 花形の底: 5つの足の間をへこませる
                petal = 0.5 + 0.5 * math.cos(feet * a)
                w = max(0.0, 1 - z / 2.2)
                rr = r * (1 - 0.1 * (1 - petal) * w)
                zz = z + 0.45 * (1 - petal) * w * (1 if r < 3.0 else 0.5)
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), zz)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for j in range(segs):
            a, b = rings[i][j], rings[i][(j + 1) % segs]
            c, d = rings[i + 1][(j + 1) % segs], rings[i + 1][j]
            if a == b:
                continue
            f = bm.faces.new((a, b, c, d))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
        if fill_z is not None:
            p.material_index = 1 if p.center.z < fill_z else 0
    return me


def cap_mesh(name, r=1.62, h=1.55, segs=48):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=h)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h / 2))
    # 側面の縦リブ: 偶数頂点を少し内へ
    for v in bm.verts:
        a = math.atan2(v.co.y, v.co.x)
        rr = math.hypot(v.co.x, v.co.y)
        if rr > r * 0.9:
            k = 1 - 0.025 * (0.5 + 0.5 * math.cos(segs * a))
            v.co.x *= k; v.co.y *= k
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if e.verts[0].co.z > h - 0.01 and e.verts[1].co.z > h - 0.01
                              and len(e.link_faces) == 2 and e.calc_face_angle(0) > 0.5],
                    offset=0.15, segments=2, affect="EDGES")
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def label_mesh(name, r=3.34, z0=9.6, z1=13.4, segs=40):
    bm = bmesh.new()
    lo = [bm.verts.new((r * math.cos(math.tau * j / segs), r * math.sin(math.tau * j / segs), z0)) for j in range(segs)]
    hi = [bm.verts.new((v.co.x, v.co.y, z1)) for v in lo]
    for j in range(segs):
        bm.faces.new((lo[j], lo[(j + 1) % segs], hi[(j + 1) % segs], hi[j]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def _part(name, me, parent, mat):
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.parent = parent
    if mat is not None:
        if not me.materials:
            me.materials.append(mat)
        elif me.materials[0] != mat:
            o.material_slots[0].link = "OBJECT"; o.material_slots[0].material = mat
    return o


def make_bottle(name, loc, body_mats, cap_mat=None, label_mat=None, meshes=None, rot_z=0.0, water=None):
    """meshes=bottle_meshes() を共有して複製する。body_mats=[空の部分, 中身部分]。
    戻り値 [本体, (キャップ), (ラベル), (水面)]。部品は本体の子。"""
    me = meshes["body"]
    body = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(body)
    body.location = loc; body.rotation_euler = (0, 0, rot_z)
    if not me.materials:
        for m in body_mats:
            me.materials.append(m)
    elif list(me.materials) != list(body_mats):
        for i, m in enumerate(body_mats):
            body.material_slots[i].link = "OBJECT"; body.material_slots[i].material = m
    parts = [body]
    if cap_mat is not None:
        c = _part(name + "_Cap", meshes["cap"], body, cap_mat); c.location = (0, 0, 19.35); parts.append(c)
    if label_mat is not None:
        parts.append(_part(name + "_Label", meshes["label"], body, label_mat))
    if water is not None and "water" in meshes:
        parts.append(_part(name + "_Water", meshes["water"], body, water))
    return parts


def bottle_meshes(fill_z=None, segs=40):
    d = {"body": bottle_mesh("BottleBody", segs, fill_z), "cap": cap_mesh("BottleCap"), "label": label_mesh("BottleLabel")}
    if fill_z is not None:
        # 水面(円板)
        r = np.interp(fill_z, [p[1] for p in BOTTLE_PROFILE[8:]], [p[0] for p in BOTTLE_PROFILE[8:]]) - 0.05
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=True, segments=segs, radius=float(r))
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, fill_z))
        me = bpy.data.meshes.new("BottleWater"); bm.to_mesh(me); bm.free()
        d["water"] = me
    return d


# ------------------------------------------------------------------ 背景
def backdrop(cam, dist=900.0, top=(0.10, 0.12, 0.15), bottom=(0.018, 0.022, 0.028), glow=(0.15, 0.17, 0.21),
             glow_center=(0.5, 0.5), glow_radius=0.45, strength=1.0):
    """カメラに固定した背景板(縦グラデーション+中央の光だまり)。K06 と同じ作り。"""
    w = 2 * dist * 18 / cam.data.lens * 1.15
    o = P.plane("Backdrop", (w, w * 9 / 16), (0, 0, -dist))
    o.parent = cam
    o.visible_shadow = False
    for attr in ("visible_glossy", "visible_diffuse", "visible_transmission"):
        if hasattr(o, attr):
            setattr(o, attr, False)
    m, nt, out = C.node_mat("BackdropM")
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ")
    C.link(nt, tc.outputs["Generated"], sep.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*bottom, 1); cr.color_ramp.elements[1].color = (*top, 1)
    C.link(nt, sep.outputs["Y"], cr.inputs["Fac"])
    vec = n.new("ShaderNodeVectorMath"); vec.operation = "SUBTRACT"
    vec.inputs[1].default_value = (*glow_center, 0)
    C.link(nt, tc.outputs["Generated"], vec.inputs[0])
    sc_ = n.new("ShaderNodeVectorMath"); sc_.operation = "MULTIPLY"; sc_.inputs[1].default_value = (1.0, 0.5625, 0)
    C.link(nt, vec.outputs[0], sc_.inputs[0])
    ln = n.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; C.link(nt, sc_.outputs[0], ln.inputs[0])
    gm = n.new("ShaderNodeMapRange"); gm.inputs["From Min"].default_value = 0.0; gm.inputs["From Max"].default_value = glow_radius
    gm.inputs["To Min"].default_value = 1.0; gm.inputs["To Max"].default_value = 0.0
    gm.interpolation_type = "SMOOTHSTEP"
    C.link(nt, ln.outputs["Value"], gm.inputs["Value"])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "SCREEN"
    C.link(nt, gm.outputs["Result"], mx.inputs["Factor"])
    C.link(nt, cr.outputs["Color"], mx.inputs["A"]); mx.inputs["B"].default_value = (*glow, 1)
    em = n.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = strength
    C.link(nt, mx.outputs["Result"], em.inputs["Color"]); C.link(nt, em.outputs["Emission"], out.inputs["Surface"])
    o.data.materials.append(m)
    return o


def frustum(name, top, bottom, z_top, z_bot, mat=None, wall=0.4):
    """角錐台(ホッパー)。top/bottom は (幅x, 幅y)。上下は開口。"""
    bm = bmesh.new()
    def sq(w, z):
        return [bm.verts.new((sx * w[0] / 2, sy * w[1] / 2, z)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    a = sq(top, z_top); b = sq(bottom, z_bot)
    for i in range(4):
        bm.faces.new((b[i], b[(i + 1) % 4], a[(i + 1) % 4], a[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    P.add_mod(o, "SOLIDIFY", thickness=wall, offset=1)
    P.add_mod(o, "BEVEL", width=0.3, segments=2, limit_method="ANGLE")
    if mat:
        me.materials.append(mat)
    return o


def plant_hall():
    """リサイクル工場の背景(床・奥壁・天井灯・サイロ・ダクト・奥のコンベア)。戻り値 (steel, grey, blue)。"""
    floor_m = F.mat_concrete("Floor", (0.12, 0.125, 0.13), rough=0.55, scale=0.006)
    P.plane("Floor", (6000, 4000), (0, 1000, -0.01), mat=floor_m)
    wall_m = F.mat_painted("Wall", (0.16, 0.18, 0.2), rough=0.7, wear=0.05, scale=0.003)
    P.plane("BackWall", (6000, 1400), (0, 1500, 700), rot=(90, 0, 0), mat=wall_m)
    P.plane("Ceiling", (6000, 4000), (0, 1000, 900), rot=(180, 0, 0), mat=C.principled("CeilM", (0.08, 0.08, 0.085), rough=0.8))
    lamp_m = C.emissive("LampM", temp=5600, strength=30)
    for row, y in enumerate((300, 800, 1300)):
        for i in range(7):
            P.box(f"Lamp{row}_{i}", (160, 30, 6), (-1500 + i * 500 + row * 120, y, 880), mat=lamp_m)
    grey = F.mat_painted("MachGrey", (0.55, 0.58, 0.6), rough=0.4, wear=0.08, scale=0.03)
    blue = F.mat_painted("MachBlue", (0.12, 0.3, 0.5), rough=0.4, wear=0.1, scale=0.03)
    steel, _ = F.mat_steel("Steel", (0.7, 0.71, 0.73), rough=0.18, streak_axis="Z")
    # 奥: サイロ・ダクト・コンベア(ボケて見える工場の気配)
    for i, x in enumerate((-520, -330, 420, 640)):
        P.cyl(f"Silo{i}", 85, 620, (x, 1050 + 60 * (i % 2), 310), mat=steel, verts=48)
        P.cyl(f"SiloCone{i}", 85, 10, (x, 1050 + 60 * (i % 2), 0), mat=steel, verts=48)
    P.box("Duct", (2400, 40, 40), (0, 1000, 700), mat=steel)
    for x in range(-900, 901, 300):
        P.box(f"DuctHang{x}", (6, 6, 180), (x, 1000, 810), mat=grey)
    P.box("ConvFar", (900, 60, 8), (-250, 650, 95), mat=C.principled("Belt", (0.03, 0.03, 0.035), rough=0.7))
    P.box("ConvFarFrame", (920, 70, 14), (-250, 650, 84), mat=blue)
    for x in range(-650, 160, 150):
        P.box(f"ConvLeg{x}", (8, 60, 80), (x, 650, 40), mat=blue)
    P.box("MachBox", (220, 160, 180), (430, 520, 90), mat=blue, bevel=2)
    P.box("MachBox2", (140, 120, 130), (-560, 420, 65), mat=grey, bevel=2)
    # 黄色い通路線(文字なし)
    yel = F.mat_painted("Yellow", (0.62, 0.45, 0.05), rough=0.5, wear=0.3, scale=0.02)
    P.box("Walk", (3000, 8, 0.3), (0, 160, 0.15), mat=yel)
    return steel, grey, blue


# ------------------------------------------------------------------ 生まれ変わり先(P07)
def _cup_sheet(name, cols, rows, pitch, depth, flange=1.2, res=0.25, sign=-1.0, cup_r=None):
    """卵パック1枚分(並んだくぼみ)。sign=-1 でくぼみが下(トレー)、+1 で上(フタのドーム)。"""
    cup_r = cup_r or pitch * 0.44
    w, h = cols * pitch + 2 * flange, rows * pitch + 2 * flange
    nx, ny = int(w / res), int(h / res)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=nx, y_subdivisions=ny, size=1)
    o = bpy.context.object; o.name = name
    o.scale = (w, h, 1); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    cx = [(-cols / 2 + i + 0.5) * pitch for i in range(cols)]
    cy = [(-rows / 2 + j + 0.5) * pitch for j in range(rows)]
    for v in o.data.vertices:
        x, y = v.co.x, v.co.y
        z = 0.0
        for a in cx:
            for b in cy:
                d = math.hypot(x - a, y - b) / cup_r
                if d < 1.0:
                    z = max(z, (1 - d * d) ** 0.6)
        # 外周の縁(少し立ち上がる)
        edge = min(w / 2 - abs(x), h / 2 - abs(y))
        lip = 0.25 if edge < 0.4 else 0.0
        v.co.z = sign * depth * z - sign * lip
    P.add_mod(o, "SOLIDIFY", thickness=0.07, offset=0)
    bpy.ops.object.shade_smooth()
    return o, w, h


def egg_carton(name, mat, cols=5, rows=2, pitch=5.4, depth=3.6, lid_open_deg=105.0):
    """透明な卵パック(2×5)。トレー(くぼみ下)+ヒンジで開いたフタ(ドーム上)。原点はトレー中心。"""
    tray, w, h = _cup_sheet(name, cols, rows, pitch, depth, sign=-1.0)
    lid, _, _ = _cup_sheet(name + "_Lid", cols, rows, pitch, depth * 0.75, sign=1.0)
    # フタ: ヒンジ(+Y 側の辺)回りに開く。ピボット用 Empty
    hinge = bpy.data.objects.new(name + "_Hinge", None); bpy.context.collection.objects.link(hinge)
    hinge.parent = tray; hinge.location = (0, h / 2, 0)
    lid.parent = hinge; lid.location = (0, h / 2, 0)
    # フタは開いて +Y 側に広がった状態を基準に、ヒンジ回りに起こす(180-lid_open_deg)
    hinge.rotation_euler = (math.radians(180.0 - lid_open_deg), 0, 0)
    for o in (tray, lid):
        o.data.materials.append(mat)
    return tray, lid


def tshirt(name, mat, size=(24.0, 28.0, 3.2)):
    """たたんだTシャツ(原点=中心、上面 +Z、襟は +Y 側)。"""
    sx, sy, sz = size
    body = P.box(name, size, (0, 0, 0), mat=mat, bevel=1.5, segments=5)
    P.add_mod(body, "SUBSURF", levels=1, render_levels=1)
    tex = bpy.data.textures.new(name + "Wrinkle", "CLOUDS"); tex.noise_scale = 6.0
    P.add_mod(body, "DISPLACE", texture=tex, strength=0.35, texture_coords="LOCAL")
    bpy.ops.object.shade_smooth()
    parts = [body]
    # 袖を内側に折った重なり(左右の帯)
    for s in (-1, 1):
        fold = P.box(name + f"_Fold{s}", (6.5, sy - 3.0, 0.7), (s * (sx / 2 - 3.6), -1.0, sz / 2 + 0.2), mat=mat, bevel=0.3, segments=3)
        fold.parent = body; parts.append(fold)
    # 襟(半分のリブ)
    bpy.ops.mesh.primitive_torus_add(major_radius=5.2, minor_radius=0.65, major_segments=40, minor_segments=10,
                                     location=(0, sy / 2 - 0.6, sz / 2 + 0.4))
    col = bpy.context.object; col.name = name + "_Collar"
    bm = bmesh.new(); bm.from_mesh(col.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > 0.3], context="VERTS")   # 下半分(U字の襟ぐり)
    bm.to_mesh(col.data); bm.free()
    col.scale = (1.0, 0.75, 1.0)
    bpy.ops.object.shade_smooth()
    col.data.materials.append(mat)
    col.parent = body; col.location = (0, sy / 2 - 0.6, sz / 2 + 0.4); parts.append(col)
    # 襟ぐりの影(内側の布が少し暗い)
    bm = bmesh.new()
    c0 = bm.verts.new((0, 0, 0))
    arc = [bm.verts.new((4.7 * math.cos(a), 4.7 * 0.72 * math.sin(a), 0)) for a in np.linspace(math.pi, math.tau, 25)]
    for i in range(len(arc) - 1):
        bm.faces.new((c0, arc[i + 1], arc[i]))
    me = bpy.data.meshes.new(name + "_Neck"); bm.to_mesh(me); bm.free()
    neck = bpy.data.objects.new(name + "_Neck", me); bpy.context.collection.objects.link(neck)
    neck.parent = body; neck.location = (0, sy / 2 - 0.6, sz / 2 + 0.3); parts.append(neck)
    return body, parts


def mat_jersey(name, color=(0.28, 0.48, 0.66), rough=0.85, scale=9.0):
    """綿/ポリエステルの天竺ニット: 細かい編み目のバンプ+色ムラ。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"
    wv.inputs["Scale"].default_value = scale; wv.inputs["Distortion"].default_value = 1.5
    wv.inputs["Detail"].default_value = 2
    C.link(nt, tc.outputs["Object"], wv.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.4; nz.inputs["Detail"].default_value = 3
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (color[0] * 0.85, color[1] * 0.85, color[2] * 0.85, 1)
    cr.color_ramp.elements[1].color = (*color, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = rough
    p.inputs["Sheen Weight"].default_value = 0.25; p.inputs["Sheen Roughness"].default_value = 0.4
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.25; b.inputs["Distance"].default_value = 0.05
    C.link(nt, wv.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m
