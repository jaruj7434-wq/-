"""第3話(ペットボトル)P01〜P04 用の補助。単位 1BU=1cm。

- ボトル(500ml 風、回転体)/プリフォーム: 同じ頂点構成で作れるので、シェイプキーで膨らませられる
- マテリアル: 透明PET(安い BLENDED フレネル)/架空ラベル(文字なし)/キャップ/ベール(圧縮ボトルの塊)
- 自販機(ロゴなし)とリサイクルボックス、コンベア

透明素材は描画が重いので、各ショットで数個までに絞る。ベールや背景は不透明マテリアル。
(P05〜P08 の補助は pet_parts2.py 側。こちらは他エージェントと共有しない。)
"""
import math, random

import bmesh
import bpy
from mathutils import Matrix, Vector

import common as C
import props as P
import factory_parts as F

# ------------------------------------------------------------------ 寸法(500ml 角なし丸ボトル風)
BOTTLE_R = 3.3          # 胴の半径
NECK_Z = 17.9           # サポートリングの下(ここから上の口部はプリフォームと共通)
TOP_Z = 20.3            # 口の上端
CAP_H = 1.8
LABEL_Z = (6.0, 12.6)   # ラベルの巻かれる範囲
SEG = 48                # 円周方向の分割


def _resample(pts, n):
    """折れ線 pts=[(r,z),...] を弧長で n 点に等間隔サンプリング。"""
    d = [0.0]
    for a, b in zip(pts, pts[1:]):
        d.append(d[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    out, j = [], 0
    for i in range(n):
        t = d[-1] * i / (n - 1)
        while j < len(d) - 2 and d[j + 1] < t:
            j += 1
        seg = d[j + 1] - d[j] or 1.0
        u = (t - d[j]) / seg
        a, b = pts[j], pts[j + 1]
        out.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
    return out


def _bottle_body():
    """胴部(底の中心 → サポートリングの下)の外形。"""
    R = BOTTLE_R
    pts = [(0.0, 0.55)]
    for i in range(1, 9):                       # 底の浅いドーム
        r = 2.4 * i / 8
        pts.append((r, 0.55 - 0.45 * (r / 2.4) ** 2))
    for i in range(0, 9):                       # 底の角R
        a = math.radians(-90 + 90 * i / 8)
        pts.append((R - 0.9 + 0.9 * math.cos(a), 0.9 + 0.9 * math.sin(a)))
    z = 1.0
    grooves = (4.6, 13.6)                       # ラベル上下の溝
    while z < 14.2:
        r = R
        for gz in grooves:
            r -= 0.22 * math.exp(-((z - gz) / 0.35) ** 2)
        pts.append((r, z)); z += 0.3
    for i in range(1, 21):                      # 肩(なだらかに首へ)
        t = i / 20
        s = 0.5 - 0.5 * math.cos(math.pi * t)
        pts.append((R + (1.25 - R) * s, 14.2 + (NECK_Z - 14.2) * t))
    return pts


def _preform_body(length=9.5, r=1.15):
    """プリフォーム(試験管形)の胴部。口部の下から長さ length。"""
    zb = NECK_Z - length
    pts = [(0.0, zb)]
    for i in range(1, 13):
        a = math.radians(-90 + 90 * i / 12)
        pts.append((r * math.cos(a), zb + r + r * math.sin(a)))
    pts.append((r, NECK_Z - 0.6))
    pts.append((1.25, NECK_Z))
    return pts


def _stretched_body():
    """延伸ロッドで下まで伸ばされた中間形(細長い)。"""
    return _preform_body(length=NECK_Z - 0.6, r=1.0)


def _finish():
    """口部(サポートリング+ねじ山)。ボトル・プリフォーム共通。"""
    return [(1.25, NECK_Z), (1.75, NECK_Z + 0.05), (1.78, NECK_Z + 0.25), (1.75, NECK_Z + 0.45), (1.3, NECK_Z + 0.5),
            (1.3, NECK_Z + 0.75), (1.42, NECK_Z + 0.85), (1.42, NECK_Z + 1.05), (1.3, NECK_Z + 1.15),
            (1.42, NECK_Z + 1.4), (1.42, NECK_Z + 1.6), (1.3, NECK_Z + 1.7), (1.32, TOP_Z - 0.1), (1.25, TOP_Z),
            (1.08, TOP_Z)]


N_BODY = 90


def profile(kind="bottle"):
    body = {"bottle": _bottle_body, "preform": _preform_body, "stretched": _stretched_body}[kind]()
    return _resample(body, N_BODY) + _finish()[1:]


def _petaloid(r, z, th, kind):
    """底の5本足(ペタロイド)風のふくらみ。ボトル形状のみ。"""
    if kind != "bottle" or z > 1.6:
        return r, z
    w = max(0.0, 1 - z / 1.6) * min(1.0, r / 1.6)
    lobe = 0.5 - 0.5 * math.cos(5 * th)
    return r * (1 - 0.06 * lobe * w), z + 0.45 * lobe * w * min(1.0, r / 2.4)


def lathe_coords(prof, kind="bottle", seg=SEG):
    co = []
    for r, z in prof:
        if r < 1e-4:
            co.append((0.0, 0.0, z))
            continue
        for k in range(seg):
            th = math.tau * k / seg
            rr, zz = _petaloid(r, z, th, kind)
            co.append((rr * math.cos(th), rr * math.sin(th), zz))
    return co


def lathe_mesh(name, prof, kind="bottle", seg=SEG):
    """回転体メッシュ(先頭点 r=0 は極、末尾は開口)。"""
    bm = bmesh.new()
    rings = []
    co = lathe_coords(prof, kind, seg)
    i = 0
    for r, z in prof:
        if r < 1e-4:
            rings.append([bm.verts.new(co[i])]); i += 1
        else:
            rings.append([bm.verts.new(co[i + k]) for k in range(seg)]); i += seg
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1:
            for k in range(seg):
                bm.faces.new((a[0], b[k], b[(k + 1) % seg]))
        else:
            for k in range(seg):
                bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return o


# ------------------------------------------------------------------ マテリアル
def _blended(m):
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    for attr, val in (("use_backface_culling", False), ("use_transparency_overlap", True), ("show_transparent_back", True)):
        if hasattr(m, attr):
            setattr(m, attr, val)


def mat_pet(name="PET", tint=(0.88, 0.95, 1.0), a_min=0.05, a_max=0.55, glow=0.0):
    """透明PET: 正面は透け、輪郭ほど白く光るフレネル・アルファ(屈折は計算しないので軽い)。
    glow>0 で白っぽい自己発光を少し足す(暗い背景で輪郭を読ませる)。"""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    p = n.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (tint[0] * 0.5, tint[1] * 0.5, tint[2] * 0.5, 1)
    p.inputs["Roughness"].default_value = 0.04
    p.inputs["IOR"].default_value = 1.57
    p.inputs["Coat Weight"].default_value = 0.3
    lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.25
    am = n.new("ShaderNodeMapRange"); am.inputs["To Min"].default_value = a_min; am.inputs["To Max"].default_value = a_max
    C.link(nt, lw.outputs["Facing"], am.inputs["Value"])
    sh = p.outputs["BSDF"]
    if glow:
        em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*tint, 1)
        em.inputs["Strength"].default_value = glow
        ad = n.new("ShaderNodeAddShader"); C.link(nt, sh, ad.inputs[0]); C.link(nt, em.outputs["Emission"], ad.inputs[1])
        sh = ad.outputs["Shader"]
    tr = n.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (*tint, 1)
    mix = n.new("ShaderNodeMixShader")
    C.link(nt, am.outputs["Result"], mix.inputs["Fac"])
    C.link(nt, tr.outputs["BSDF"], mix.inputs[1]); C.link(nt, sh, mix.inputs[2])
    C.link(nt, mix.outputs["Shader"], out.inputs["Surface"])
    _blended(m)
    return m


def mat_label(name="LabelM", base=(0.08, 0.36, 0.62), stripe=(0.95, 0.95, 0.92), accent=(0.95, 0.55, 0.1)):
    """架空のラベル(文字なし): 地色+白い帯+小さな水玉模様。UV 不要(オブジェクト座標の高さ・角度)。"""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ")
    C.link(nt, tc.outputs["Generated"], sep.inputs["Vector"])
    # 高さ方向の帯(Generated Z 0..1)
    cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = "CONSTANT"
    e = cr.color_ramp.elements
    e[0].position = 0.0; e[0].color = (*base, 1)
    e[1].position = 0.40; e[1].color = (*stripe, 1)
    e.new(0.62).color = (*base, 1)
    e.new(0.70).color = (*accent, 1)
    e.new(0.76).color = (*base, 1)
    C.link(nt, sep.outputs["Z"], cr.inputs["Fac"])
    # 白帯の中に「読めない」細い線(文字の代わり)
    wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "Z"
    wv.inputs["Scale"].default_value = 18; wv.inputs["Distortion"].default_value = 0
    C.link(nt, tc.outputs["Generated"], wv.inputs["Vector"])
    gate = n.new("ShaderNodeMapRange"); gate.inputs["From Min"].default_value = 0.47; gate.inputs["From Max"].default_value = 0.47
    gate2 = n.new("ShaderNodeMapRange"); gate2.inputs["From Min"].default_value = 0.56; gate2.inputs["From Max"].default_value = 0.56
    gate2.inputs["To Min"].default_value = 1; gate2.inputs["To Max"].default_value = 0
    C.link(nt, sep.outputs["Z"], gate.inputs["Value"]); C.link(nt, sep.outputs["Z"], gate2.inputs["Value"])
    band = n.new("ShaderNodeMath"); band.operation = "MULTIPLY"
    C.link(nt, gate.outputs["Result"], band.inputs[0]); C.link(nt, gate2.outputs["Result"], band.inputs[1])
    th = n.new("ShaderNodeMath"); th.operation = "GREATER_THAN"; th.inputs[1].default_value = 0.8
    C.link(nt, wv.outputs["Fac"], th.inputs[0])
    lines = n.new("ShaderNodeMath"); lines.operation = "MULTIPLY"
    C.link(nt, band.outputs[0], lines.inputs[0]); C.link(nt, th.outputs[0], lines.inputs[1])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"
    C.link(nt, lines.outputs[0], mx.inputs["Factor"])
    C.link(nt, cr.outputs["Color"], mx.inputs["A"]); mx.inputs["B"].default_value = (*base, 1)
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.28
    p.inputs["Coat Weight"].default_value = 0.4
    # 裏面は白(はがれた時に見える)
    geo = n.new("ShaderNodeNewGeometry")
    bk = n.new("ShaderNodeMix"); bk.data_type = "RGBA"
    C.link(nt, geo.outputs["Backfacing"], bk.inputs["Factor"])
    C.link(nt, mx.outputs["Result"], bk.inputs["A"]); bk.inputs["B"].default_value = (0.85, 0.86, 0.86, 1)
    C.link(nt, bk.outputs["Result"], p.inputs["Base Color"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    m.use_backface_culling = False
    return m


def mat_cap(name="CapM", color=(0.92, 0.92, 0.9)):
    m = bpy.data.materials.get(name)
    if m:
        return m
    return C.principled(name, color, rough=0.35, bump=0.15, bump_scale=6)


# ------------------------------------------------------------------ ボトル
def bottle(name, loc=(0, 0, 0), rot_deg=(0, 0, 0), mat=None, cap=True, label=True, cap_color=(0.92, 0.92, 0.9),
           label_mat=None):
    """ボトル一式。戻り値 dict(body, cap, label)。body が親(原点=底)。"""
    body = lathe_mesh(name, profile("bottle"), "bottle")
    body.data.materials.append(mat or mat_pet())
    body.location = loc
    body.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    res = {"body": body, "cap": None, "label": None}
    if cap:
        c = make_cap(name + "_Cap", cap_color)
        c.parent = body; c.location = (0, 0, TOP_Z - 1.45)
        res["cap"] = c
    if label:
        lb = make_label(name + "_Label", label_mat or mat_label())
        lb.parent = body
        res["label"] = lb
    return res


def make_cap(name, color=(0.92, 0.92, 0.9)):
    """キャップ(ギザ付き側面+天面)。原点=キャップ下端の中心。"""
    prof = [(0.0, CAP_H), (1.3, CAP_H), (1.55, CAP_H - 0.12), (1.6, CAP_H - 0.3), (1.6, 0.35), (1.66, 0.3),
            (1.66, 0.0), (1.4, 0.0)]
    seg = 60
    bm = bmesh.new()
    rings = []
    for r, z in prof:
        if r < 1e-4:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            ring = []
            for k in range(seg):
                th = math.tau * k / seg
                rr = r - (0.04 if (k % 2 and 0.4 < z < CAP_H - 0.35) else 0.0)
                ring.append(bm.verts.new((rr * math.cos(th), rr * math.sin(th), z)))
            rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1:
            for k in range(seg):
                bm.faces.new((a[0], b[(k + 1) % seg], b[k]))
        else:
            for k in range(seg):
                bm.faces.new((a[k], b[k], b[(k + 1) % seg], a[(k + 1) % seg]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.normal_update(); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.data.materials.append(mat_cap(f"CapM_{color[0]:.2f}_{color[1]:.2f}_{color[2]:.2f}", color))
    return o


def label_coords(p=0.0, curl=0.0, r=None, seg=72, rows=6):
    """ラベル(筒状の帯)の頂点。p(0..1)ははがれた割合: 継ぎ目の端から接線方向にほどけていく。"""
    r = r or (BOTTLE_R + 0.03)
    z0, z1 = LABEL_Z
    thc = math.tau * (1 - p)
    co = []
    for j in range(rows + 1):
        z = z0 + (z1 - z0) * j / rows
        for k in range(seg + 1):
            th = math.tau * k / seg
            if th <= thc:
                co.append((r * math.cos(th), r * math.sin(th), z))
            else:
                s = r * (th - thc)              # ほどけた長さ
                tx, ty = -math.sin(thc), math.cos(thc)
                ox, oy = math.cos(thc), math.sin(thc)
                bend = curl * s * s / 20.0       # 外側へ少し反る
                co.append(((r + bend) * ox + tx * s, (r + bend) * oy + ty * s, z - 0.02 * s * curl))
    return co


def make_label(name, mat, seg=72, rows=6):
    """ラベル(継ぎ目のある開いた筒)。Generated 座標が高さ方向で模様を決める。"""
    bm = bmesh.new()
    co = label_coords(0.0, seg=seg, rows=rows)
    vs = [bm.verts.new(c) for c in co]
    W = seg + 1
    for j in range(rows):
        for k in range(seg):
            bm.faces.new((vs[j * W + k], vs[j * W + k + 1], vs[(j + 1) * W + k + 1], vs[(j + 1) * W + k]))
    me = bpy.data.meshes.new(name); bm.normal_update(); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    return o   # 厚みなし(裏面は Backfacing で白くする)


# ------------------------------------------------------------------ シェイプキー補助
def add_shape(obj, key_name, coords, relative=None):
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    sk = obj.shape_key_add(name=key_name, from_mix=False)
    for v, c in zip(sk.data, coords):
        v.co = c
    if relative is not None:
        sk.relative_key = relative
    return sk


def key_shape(sk, frames_values, interp="BEZIER"):
    for f, v in frames_values:
        sk.value = v
        sk.keyframe_insert("value", frame=f)
    F.set_interp(sk.id_data, interp, path=f'key_blocks["{sk.name}"]')


def stage_keys(obj, coords_list, frames, prefix="S"):
    """coords_list[i] を frames[i] に通過する(隣どうしを線形に混ぜる)シェイプキー列。"""
    sks = [add_shape(obj, f"{prefix}{i}", c) for i, c in enumerate(coords_list)]
    for i, sk in enumerate(sks):
        seq = []
        if i > 0:
            seq.append((frames[i - 1], 0.0))
        seq.append((frames[i], 1.0))
        if i < len(sks) - 1:
            seq.append((frames[i + 1], 0.0))
        if i == 0:
            seq.insert(0, (1, 1.0 if frames[0] <= 1 else 0.0))
        key_shape(sk, seq, "LINEAR")
    return sks


# ------------------------------------------------------------------ ベール(圧縮ボトルの塊)
def mat_bale(name="BaleM", seed=0.0):
    """つぶれたボトルの塊: 横長にゆがめたボロノイのセル1つ=つぶれたボトル1本。
    セルごとに透明PET風の青白〜くもり・緑・まれに取り残しのラベル色、セル内はしわ(筋状の明暗+強いバンプ)。
    不透明なので軽い。"""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping"); mp.inputs["Location"].default_value = (seed * 37.1, seed * 11.3, seed * 5.7)
    mp.inputs["Scale"].default_value = (1.0, 1.0, 3.2)      # 上下に押しつぶされて横長
    C.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    warp = n.new("ShaderNodeTexNoise"); warp.inputs["Scale"].default_value = 0.12; warp.inputs["Detail"].default_value = 4
    C.link(nt, mp.outputs["Vector"], warp.inputs["Vector"])
    wsub = n.new("ShaderNodeVectorMath"); wsub.operation = "SUBTRACT"; wsub.inputs[1].default_value = (0.5, 0.5, 0.5)
    C.link(nt, warp.outputs["Color"], wsub.inputs[0])
    wsc = n.new("ShaderNodeVectorMath"); wsc.operation = "SCALE"; wsc.inputs["Scale"].default_value = 9.0
    C.link(nt, wsub.outputs[0], wsc.inputs[0])
    wadd = n.new("ShaderNodeVectorMath"); wadd.operation = "ADD"
    C.link(nt, mp.outputs["Vector"], wadd.inputs[0]); C.link(nt, wsc.outputs[0], wadd.inputs[1])
    vo = n.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 0.05; vo.inputs["Randomness"].default_value = 1.0
    C.link(nt, wadd.outputs[0], vo.inputs["Vector"])
    ve = n.new("ShaderNodeTexVoronoi"); ve.feature = "DISTANCE_TO_EDGE"; ve.inputs["Scale"].default_value = 0.05
    C.link(nt, wadd.outputs[0], ve.inputs["Vector"])
    # セルの色(1セル=1本)
    sepc = n.new("ShaderNodeSeparateColor"); C.link(nt, vo.outputs["Color"], sepc.inputs["Color"])
    cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = "LINEAR"
    e = cr.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0.30, 0.42, 0.50, 1)     # 透明PET(奥が透けて暗い青)
    e[1].position = 0.45; e[1].color = (0.52, 0.62, 0.68, 1)
    e.new(0.70).color = (0.70, 0.76, 0.80, 1)                    # くもったPET
    e.new(0.78).color = (0.70, 0.76, 0.80, 1)
    e.new(0.80).color = (0.25, 0.45, 0.32, 1)                    # 緑がかったボトル
    e.new(0.86).color = (0.30, 0.50, 0.38, 1)
    e.new(0.88).color = (0.62, 0.70, 0.76, 1)
    e.new(0.95).color = (0.62, 0.70, 0.76, 1)
    e.new(0.955).color = (0.62, 0.14, 0.08, 1)                   # 取り残しのラベル(まれ)
    e.new(0.975).color = (0.12, 0.25, 0.55, 1)
    e.new(0.99).color = (0.90, 0.90, 0.86, 1)                    # 白キャップ
    C.link(nt, sepc.outputs["Red"], cr.inputs["Fac"])
    # しわ: 細かい筋状ノイズで明るい反射の筋と暗い折り目
    cm = n.new("ShaderNodeMapping"); cm.inputs["Scale"].default_value = (0.6, 0.6, 2.5)
    C.link(nt, wadd.outputs[0], cm.inputs["Vector"])
    wr = n.new("ShaderNodeTexNoise"); wr.inputs["Scale"].default_value = 0.9; wr.inputs["Detail"].default_value = 8
    wr.inputs["Roughness"].default_value = 0.65
    C.link(nt, cm.outputs["Vector"], wr.inputs["Vector"])
    crk = n.new("ShaderNodeValToRGB")
    crk.color_ramp.elements[0].position = 0.35; crk.color_ramp.elements[0].color = (0.3, 0.3, 0.3, 1)
    crk.color_ramp.elements[1].position = 0.75; crk.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    C.link(nt, wr.outputs["Fac"], crk.inputs["Fac"])
    mul = n.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
    C.link(nt, cr.outputs["Color"], mul.inputs["A"]); C.link(nt, crk.outputs["Color"], mul.inputs["B"])
    # セルの境目(ボトルどうしの隙間)は暗く細く
    edge = n.new("ShaderNodeMapRange"); edge.inputs["From Min"].default_value = 0.0; edge.inputs["From Max"].default_value = 0.06
    C.link(nt, ve.outputs["Distance"], edge.inputs["Value"])
    dk = n.new("ShaderNodeMix"); dk.data_type = "RGBA"
    C.link(nt, edge.outputs["Result"], dk.inputs["Factor"])
    dk.inputs["A"].default_value = (0.04, 0.05, 0.06, 1); C.link(nt, mul.outputs["Result"], dk.inputs["B"])
    p = n.new("ShaderNodeBsdfPrincipled")
    C.link(nt, dk.outputs["Result"], p.inputs["Base Color"])
    p.inputs["Coat Weight"].default_value = 0.6; p.inputs["Coat Roughness"].default_value = 0.12
    rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.08; rr.inputs["To Max"].default_value = 0.35
    C.link(nt, wr.outputs["Fac"], rr.inputs["Value"]); C.link(nt, rr.outputs["Result"], p.inputs["Roughness"])
    h = n.new("ShaderNodeMath"); h.operation = "MULTIPLY_ADD"; h.inputs[1].default_value = 0.6
    C.link(nt, wr.outputs["Fac"], h.inputs[0]); C.link(nt, edge.outputs["Result"], h.inputs[2])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 1.0; b.inputs["Distance"].default_value = 1.2
    C.link(nt, h.outputs[0], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def mat_crushed_pet(name="CrushedPET"):
    """ベール表面に埋まった「つぶれたボトル」(不透明。暗い地+強い映り込み+縁が白く光るフレネル風)。"""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    oi = n.new("ShaderNodeObjectInfo")
    cr = n.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = "CONSTANT"
    e = cr.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0.30, 0.38, 0.44, 1)
    e[1].position = 0.5; e[1].color = (0.50, 0.56, 0.60, 1)
    e.new(0.8).color = (0.22, 0.40, 0.28, 1)
    e.new(0.92).color = (0.65, 0.68, 0.70, 1)
    C.link(nt, oi.outputs["Random"], cr.inputs["Fac"])
    lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.12
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"
    C.link(nt, lw.outputs["Facing"], mx.inputs["Factor"])
    C.link(nt, cr.outputs["Color"], mx.inputs["A"]); mx.inputs["B"].default_value = (0.62, 0.68, 0.72, 1)
    p = n.new("ShaderNodeBsdfPrincipled")
    C.link(nt, mx.outputs["Result"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.12; p.inputs["Coat Weight"].default_value = 1.0
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6; nz.inputs["Detail"].default_value = 6
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.7
    C.link(nt, nz.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, b.outputs["Normal"], lw.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def crushed_bottle_mesh():
    """つぶれたボトル用の低ポリ回転体(共有メッシュ)。"""
    me = bpy.data.meshes.get("CrushedBottleMesh")
    if me:
        return me
    o = lathe_mesh("CrushedBottleMesh", _resample(_bottle_body(), 22) + _finish()[1:3] + [(1.3, TOP_Z)], "flat", seg=14)
    me = o.data; me.name = "CrushedBottleMesh"
    tx = bpy.data.textures.get("CrushTx") or bpy.data.textures.new("CrushTx", "CLOUDS")
    tx.noise_scale = 2.0
    bpy.data.objects.remove(o)
    return me


def _surface_bottles(root, name, size, rnd, count, mat):
    """ベールの側面・上面に、つぶれたボトルを埋め込む(面の法線方向につぶす)。"""
    me = crushed_bottle_mesh()
    sx, sy, sz = size
    faces = [(Vector((0, -1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)), sy / 2, sx, sz, 1.0),   # 前
             (Vector((0, 1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)), sy / 2, sx, sz, 0.5),
             (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), sx / 2, sy, sz, 1.0),    # 右
             (Vector((-1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), sx / 2, sy, sz, 0.6),
             (Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0)), sz / 2, sx, sy, 0.8)]    # 上
    k = 0
    for nrm, u, v, half, lu, lv, w in faces:
        for i in range(int(count * w)):
            a = rnd.uniform(-0.45, 0.45) * lu; b = rnd.uniform(-0.44, 0.44) * lv
            phi = rnd.uniform(-0.5, 0.5) + (0.0 if nrm.z == 0 else rnd.uniform(0, math.pi))
            d = u * math.cos(phi) + v * math.sin(phi)
            x_ax = d.cross(nrm)
            rot = Matrix((x_ax, nrm, d)).transposed()          # ローカル x, y(=法線), z(=ボトル軸)
            scl = rnd.uniform(0.85, 1.1)
            mw = Matrix.Translation(Vector((0, 0, sz / 2)) + nrm * (half - 0.9) + u * a + v * b - d * 10 * scl) \
                @ rot.to_4x4() @ Matrix.Diagonal((scl * rnd.uniform(1.0, 1.35), scl * 0.2, scl, 1))
            o = bpy.data.objects.new(f"{name}_PB{k}", me); bpy.context.collection.objects.link(o)
            o.parent = root; o.matrix_parent_inverse = Matrix.Identity(4)
            o.matrix_basis = mw
            if not o.data.materials:
                o.data.materials.append(mat)
            k += 1


def bale(name, size=(110, 100, 80), loc=(0, 0, 0), seed=0, mat=None, strap_mat=None, straps=4, surface=0):
    """ベール1個(凸凹の直方体+針金バンド)。原点=底面中心。戻り値 root(Empty)。
    surface>0 で各面に約 surface 本の「つぶれたボトル」(不透明・共有メッシュ)を埋め込む。"""
    rnd = random.Random(seed)
    root = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(root)
    root.location = loc
    sx, sy, sz = size
    blk = P.box(name + "_Blk", (sx, sy, sz), (0, 0, sz / 2))
    blk.parent = root
    sub = blk.modifiers.new("sub", "SUBSURF"); sub.subdivision_type = "SIMPLE"; sub.levels = 4; sub.render_levels = 4
    tx = bpy.data.textures.new(name + "_Tx", "VORONOI"); tx.noise_scale = 9.0
    d = blk.modifiers.new("disp", "DISPLACE"); d.texture = tx; d.strength = 3.0; d.mid_level = 0.6
    tx2 = bpy.data.textures.new(name + "_Tx2", "CLOUDS"); tx2.noise_scale = 25.0
    d2 = blk.modifiers.new("disp2", "DISPLACE"); d2.texture = tx2; d2.strength = 3.0
    bev = blk.modifiers.new("bev", "BEVEL"); bev.width = 4; bev.segments = 2
    blk.modifiers.move(3, 0)  # bevel を先に
    blk.data.materials.append(mat or mat_bale())
    for poly in blk.data.polygons:
        poly.use_smooth = True
    if surface:
        _surface_bottles(root, name, size, rnd, surface, mat_crushed_pet())
    sm = strap_mat or bpy.data.materials.get("StrapM") or C.principled("StrapM", (0.32, 0.33, 0.35), metallic=1, rough=0.3)
    for i in range(straps):          # 針金バンド(X 方向に巻く)
        x = -sx / 2 + sx * (i + 0.5) / straps + rnd.uniform(-3, 3)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, sz / 2))
        s = bpy.context.object; s.name = f"{name}_Strap{i}"
        s.scale = (1.0, sy + 2.4, sz + 2.4)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bm = bmesh.new(); bm.from_mesh(s.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.x) > 0.9], context="FACES")
        bm.to_mesh(s.data); bm.free()
        so = s.modifiers.new("sol", "SOLIDIFY"); so.thickness = 0.6
        s.data.materials.append(sm)
        s.parent = root; s.location = (x, 0, sz / 2)
    return root


# ------------------------------------------------------------------ コンベア
def conveyor(name, length, width, height, loc=(0, 0, 0), belt_mat=None, frame_mat=None, roller_step=45.0):
    """X 方向のベルトコンベア(ベルト上面 z=height)。ベルトの流れはマテリアル側(座標をずらす)で表現。"""
    x0, y0, z0 = loc
    fm = frame_mat or F.mat_painted("ConvFrame", (0.18, 0.35, 0.55), rough=0.45, wear=0.3, scale=0.05)
    belt = P.box(name + "_Belt", (length, width, 2.0), (x0, y0, z0 + height - 1.0), mat=belt_mat, bevel=0.6)
    for s in (-1, 1):
        P.box(f"{name}_Side{s}", (length, 4, 14), (x0, y0 + s * (width / 2 + 2.5), z0 + height - 4), mat=fm, bevel=0.5)
    steel = bpy.data.materials.get("RollerSteel") or C.principled("RollerSteel", (0.6, 0.6, 0.62), metallic=1, rough=0.3)
    n = int(length // roller_step)
    for i in range(n + 1):
        x = x0 - length / 2 + i * length / n
        P.cyl(f"{name}_Roll{i}", 4.5, width + 2, (x, y0, z0 + height - 6.5), (math.radians(90), 0, 0), steel, verts=16)
    # 脚
    legs = max(2, int(length // 250) + 1)
    for i in range(legs):
        x = x0 - length / 2 + 20 + i * (length - 40) / (legs - 1)
        for s in (-1, 1):
            P.box(f"{name}_Leg{i}{s}", (6, 6, height - 10), (x, y0 + s * (width / 2 - 2), z0 + (height - 10) / 2), mat=fm)
        P.box(f"{name}_Brace{i}", (5, width, 5), (x, y0, z0 + 25), mat=fm)
    return belt


def mat_belt(name, coord_obj):
    """ゴムベルト(横筋入り)。coord_obj を動かすとベルトが流れる。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord"); tc.object = coord_obj
    wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"
    wv.inputs["Scale"].default_value = 0.06; wv.inputs["Distortion"].default_value = 0
    C.link(nt, tc.outputs["Object"], wv.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.4; nz.inputs["Detail"].default_value = 8
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.025, 0.025, 0.027, 1); cr.color_ramp.elements[1].color = (0.09, 0.09, 0.09, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.6
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    th = n.new("ShaderNodeMath"); th.operation = "GREATER_THAN"; th.inputs[1].default_value = 0.85
    C.link(nt, wv.outputs["Fac"], th.inputs[0])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.6
    C.link(nt, th.outputs[0], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


# ------------------------------------------------------------------ 自販機・リサイクルボックス
def _opaque_bottle_proxy(name, loc, color, cap):
    """自販機の陳列用(不透明・低ポリ)。"""
    body = lathe_mesh(name, _resample(_bottle_body(), 24) + _finish()[1:3] + [(1.3, TOP_Z)], "flat", seg=16)
    body.scale = (0.85, 0.85, 0.85)
    body.location = loc
    body.data.materials.append(bpy.data.materials.get("ProxyPET") or
                               C.principled("ProxyPET", (0.62, 0.72, 0.78), rough=0.08, coat=1.0))
    lb = P.cyl(name + "L", BOTTLE_R * 0.85 + 0.04, 5.5, (loc[0], loc[1], loc[2] + 8.0), mat=color, verts=16)
    P.cyl(name + "C", 1.4, 1.5, (loc[0], loc[1], loc[2] + TOP_Z * 0.85 + 0.3), mat=cap, verts=12)


def vending_machine(cx=0.0, cy=0.0, w=100.0, d=72.0, h=183.0, body_color=(0.82, 0.83, 0.85), accent=(0.1, 0.35, 0.6),
                    seed=3, glow=1.4):
    """無地の自販機(ロゴなし)。前面は -Y。陳列は不透明の簡易ボトル・缶。戻り値: 前面の y。"""
    rnd = random.Random(seed)
    fy = cy - d / 2
    paint = C.principled("VMPaint", body_color, rough=0.32, coat=0.6)
    acc = C.principled("VMAccent", accent, rough=0.3, coat=0.6)
    dark = C.principled("VMDark", (0.025, 0.025, 0.028), rough=0.4)
    steel = C.principled("VMSteel", (0.72, 0.73, 0.75), metallic=1, rough=0.32)
    body = P.box("VMBody", (w, d, h), (cx, cy, h / 2 + 4), mat=paint, bevel=1.0)
    P.box("VMPlinth", (w - 4, d - 4, 4), (cx, cy, 2), mat=dark)
    P.box("VMHeader", (w + 0.4, 2, 12), (cx, fy - 0.6, h - 5), mat=acc, bevel=0.5)     # 無地の帯
    wb, wt = 104.0, h - 14
    P.box("VMBack", (w - 10, 2, wt - wb), (cx, fy + 22, (wt + wb) / 2), mat=C.emissive("VMBacklight", (0.92, 0.96, 1.0), strength=glow))
    cut = P.box("VMWinCut", (w - 8, 30, wt - wb), (cx, fy + 10, (wt + wb) / 2))
    bo = body.modifiers.new("win", "BOOLEAN"); bo.object = cut; bo.solver = "EXACT"
    cut.hide_render = True; cut.hide_viewport = True
    P.box("VMWin", (w - 8, 0.3, wt - wb), (cx, fy - 0.3, (wt + wb) / 2),
          mat=C.principled("VMGlass", (0.9, 0.95, 1.0), rough=0.03, alpha=0.08))
    cols = [(0.75, 0.08, 0.06), (0.06, 0.25, 0.62), (0.95, 0.65, 0.08), (0.08, 0.45, 0.2), (0.92, 0.92, 0.9),
            (0.45, 0.22, 0.06), (0.9, 0.35, 0.08), (0.5, 0.75, 0.9)]
    cmats = [C.principled(f"VMProd{i}", c, rough=0.3, coat=0.5) for i, c in enumerate(cols)]
    alu = C.principled("VMAlu", (0.8, 0.8, 0.82), metallic=1, rough=0.25)
    price = C.emissive("VMPrice", (0.95, 0.95, 0.9), strength=1.5)
    btn = C.emissive("VMBtn", (0.35, 1.0, 0.45), strength=4)
    shelf = C.principled("VMShelf", (0.85, 0.85, 0.87), rough=0.4)
    rows = 3
    rh = (wt - wb) / rows
    for r in range(rows):
        z0 = wb + r * rh + 6
        P.box(f"VMShelf{r}", (w - 10, 18, 1.0), (cx, fy + 10, z0 - 0.5), mat=shelf)
        for i in range(8):
            x = cx - w / 2 + 11 + i * 11
            m = rnd.choice(cmats)
            if (r + i) % 2 == 0:
                _opaque_bottle_proxy(f"VMB{r}_{i}", (x, fy + 9, z0), m, rnd.choice(cmats))
            else:
                P.cyl(f"VMK{r}_{i}", 3.3, 12.2, (x, fy + 9, z0 + 6.1), mat=m, verts=20)
                P.cyl(f"VMK{r}_{i}T", 3.0, 0.4, (x, fy + 9, z0 + 12.4), mat=alu, verts=20)
            P.box(f"VMTag{r}_{i}", (7, 0.3, 1.6), (x, fy - 0.8, z0 - 3.0), mat=price)
            P.box(f"VMBtn{r}_{i}", (3.4, 0.8, 1.2), (x, fy - 0.9, z0 - 5.2), mat=btn, bevel=0.3)
    P.box("VMPanel", (22, 2, 38), (cx + 30, fy - 0.8, 88), mat=dark, bevel=0.6)
    P.box("VMSlot", (7, 1.6, 9), (cx + 30, fy - 1.6, 95), mat=steel, bevel=0.5)
    P.box("VMBill", (8, 1.6, 3), (cx + 30, fy - 1.6, 84), mat=steel, bevel=0.4)
    P.box("VMRet", (10, 6, 3), (cx + 30, fy - 3, 74), mat=steel, bevel=0.5)
    P.box("VMDisp", (w - 20, 3, 22), (cx, fy - 1.0, 26), mat=dark, bevel=0.8)
    P.box("VMFlap", (w - 24, 0.6, 18), (cx, fy - 2.6, 26), mat=C.principled("VMSmoke", (0.03, 0.03, 0.035), rough=0.1, coat=0.8), bevel=0.3)
    # 窓からの光
    C.area_light((cx, fy - 4, (wt + wb) / 2), (-90, 0, 0), 1, 1.5e5, (0.88, 0.94, 1.0), "VMGlow")
    g = bpy.data.objects["VMGlow"].data; g.shape = "RECTANGLE"; g.size = w - 10; g.size_y = wt - wb
    return fy


def recycle_box(cx, cy, w=46.0, d=40.0, h=88.0, color=(0.88, 0.89, 0.88), lid_color=(0.12, 0.42, 0.25), hole_r=5.2):
    """自販機横のボトル回収ボックス(ロゴ・文字なし)。上面の丸い投入口に入る。
    戻り値: 投入口の中心(ワールド座標)。前面は -Y。"""
    body_m = C.principled("RBBody", color, rough=0.45, bump=0.03, bump_scale=2)
    lid_m = C.principled("RBLid", lid_color, rough=0.35, coat=0.3)
    dark = C.principled("RBHole", (0.008, 0.008, 0.009), rough=0.9)
    P.box("RBBody", (w, d, h - 10), (cx, cy, (h - 10) / 2), mat=body_m, bevel=1.5)
    lid = P.box("RBLid", (w + 2, d + 2, 10), (cx, cy, h - 5), mat=lid_m, bevel=1.5)
    hole = (cx, cy - 4, h)
    cutter = P.cyl("RBHoleCut", hole_r, 60, (hole[0], hole[1], h - 20), verts=48)
    bo = lid.modifiers.new("hole", "BOOLEAN"); bo.object = cutter; bo.solver = "EXACT"
    lid.modifiers.move(len(lid.modifiers) - 1, 0)
    cutter.hide_render = True; cutter.hide_viewport = True
    bo2 = bpy.data.objects["RBBody"].modifiers.new("hole", "BOOLEAN"); bo2.object = cutter; bo2.solver = "EXACT"
    bpy.data.objects["RBBody"].modifiers.move(len(bpy.data.objects["RBBody"].modifiers) - 1, 0)
    # 穴の中(暗い筒)+ ゴムのフチ
    P.cyl("RBHoleIn", hole_r - 0.05, 40, (hole[0], hole[1], h - 20.5), mat=dark, verts=32)
    F.ring("RBHoleRim", hole_r + 0.8, hole_r - 0.2, 0.8, (hole[0], hole[1], h + 0.1), mat=C.principled("RBRim", (0.04, 0.04, 0.045), rough=0.6), verts=48, bevel=0.2)
    # 前面のピクトグラム(ボトルの形の白抜き・文字なし)+ 回収口の扉
    P.box("RBDoor", (w - 8, 0.8, h - 26), (cx, cy - d / 2 - 0.3, (h - 10) / 2), mat=C.principled("RBDoorM", (0.8, 0.81, 0.8), rough=0.5), bevel=0.4)
    plate = C.principled("RBPlate", lid_color, rough=0.35)
    P.cyl("RBPicto", 9.5, 0.5, (cx, cy - d / 2 - 0.9, h - 32), (math.radians(90), 0, 0), plate, verts=48)
    white = C.principled("RBWhite", (0.95, 0.95, 0.93), rough=0.4)
    P.box("RBPictoB", (4.2, 0.4, 8.0), (cx, cy - d / 2 - 1.2, h - 33.5), mat=white, bevel=0.6)
    P.box("RBPictoN", (1.8, 0.4, 3.2), (cx, cy - d / 2 - 1.2, h - 28), mat=white, bevel=0.3)
    P.box("RBHandle", (12, 2, 2), (cx, cy - d / 2 - 1.5, 22), mat=C.principled("RBHandleM", (0.3, 0.3, 0.32), rough=0.4), bevel=0.5)
    return hole
