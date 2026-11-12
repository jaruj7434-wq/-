"""傘の小道具(第2話「なくした傘」用)。単位 1BU=1cm。

    import umbrella as U
    root = U.make("U1", (0, 0, 0), rotation_deg=(8, 0, 30), state="closed", kind="vinyl", tag=True)

- state="closed": 畳んでベルトで留めた傘。原点=石突きの先端、手元(J字)が +Z(傘立てに立てた向き)。全長約86cm。
- state="open"  : 開いた傘。原点=手元(J字)の下端、生地が上(差している向き)。直径約100cm。
- kind="vinyl": 透明ビニール(少しくもった樹脂)。color を渡すと薄く色付き。手元は白(handle="black"/"clear"も可)。
  kind="cloth": 布傘。color は (r,g,b) か名前 "navy","charcoal","olive","burgundy","beige","black","green"。
- tag=True: 手元に紙の忘れ物タグ(ひも付き)。
- 戻り値 root(Empty)。子に3つのメッシュ: <name>_Canopy(生地+石突き先端), <name>_Frame(親骨・受骨・中棒・
  ろくろ・石突き), <name>_Handle(手元)、tag=True なら <name>_Tag。分解図(k06)ではこの3つを個別に動かす。
- 追加オプション(キーワード): seed(しわの乱数), loose(0..1 畳んだ生地のふくらみ。0=きっちり), handle, strap(bool)。
"""
import math, random

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

import common as C

LEN = 86.0            # 石突き先端〜手元の頂点(閉じた状態の全長)
NOTCH_Z = 5.0         # 上ろくろ(親骨の付け根)
SHAFT_END = 68.0      # 中棒の終わり(手元の付け根)
GRIP_LEN = 12.0
RIB_LEN = 58.0        # 親骨の長さ(閉じた時の到達点 NOTCH_Z+RIB_LEN)
R_OPEN = 50.0         # 開いた時の半径
H_OPEN = 21.0         # 開いた時の深さ

NAMED = {
    "navy": (0.025, 0.035, 0.08), "charcoal": (0.045, 0.045, 0.05), "olive": (0.13, 0.13, 0.06),
    "burgundy": (0.16, 0.025, 0.035), "beige": (0.42, 0.36, 0.27), "black": (0.012, 0.012, 0.014),
    "green": (0.03, 0.09, 0.06),
}


# ------------------------------------------------------------------ マテリアル
def _get(name, maker):
    m = bpy.data.materials.get(name)
    return m if m is not None else maker(name)


def _blended(m):
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    for attr, val in (("use_backface_culling", False), ("use_transparent_shadow", True),
                      ("use_transparency_overlap", True), ("show_transparent_back", True)):
        if hasattr(m, attr):
            setattr(m, attr, val)


def mat_vinyl(name="UmbVinyl", tint=(0.93, 0.96, 0.97), a_min=0.06, a_max=0.42, frost=0.12, diffuse=0.45, translucent=0.5):
    """透明ビニール: 正面は透けて、斜めほど白く光る(フレネルでアルファ)。粗さムラで少しくもる。"""
    def mk(nm):
        m, nt, out = C.node_mat(nm)
        n = nt.nodes
        tc = n.new("ShaderNodeTexCoord")
        p = n.new("ShaderNodeBsdfPrincipled")
        p.inputs["Base Color"].default_value = (tint[0] * diffuse, tint[1] * diffuse, tint[2] * diffuse, 1)
        p.inputs["IOR"].default_value = 1.5
        p.inputs["Coat Weight"].default_value = 0.25
        nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.08; nz.inputs["Detail"].default_value = 6
        C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
        rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = frost * 0.4
        rr.inputs["To Max"].default_value = frost * 1.6
        C.link(nt, nz.outputs["Fac"], rr.inputs["Value"]); C.link(nt, rr.outputs["Result"], p.inputs["Roughness"])
        # 細かいしわ(バンプ)
        wz = n.new("ShaderNodeTexNoise"); wz.inputs["Scale"].default_value = 0.35; wz.inputs["Detail"].default_value = 2
        C.link(nt, tc.outputs["Object"], wz.inputs["Vector"])
        b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.035; b.inputs["Distance"].default_value = 0.3
        C.link(nt, wz.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
        lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
        C.link(nt, b.outputs["Normal"], lw.inputs["Normal"])
        am = n.new("ShaderNodeMapRange"); am.inputs["To Min"].default_value = a_min; am.inputs["To Max"].default_value = a_max
        C.link(nt, lw.outputs["Facing"], am.inputs["Value"])
        # 逆光で白く透ける(拡散透過)+反射。アルファは透明BSDFとの混合で
        tl = n.new("ShaderNodeBsdfTranslucent")
        tl.inputs["Color"].default_value = (tint[0] * translucent, tint[1] * translucent, tint[2] * translucent, 1)
        C.link(nt, b.outputs["Normal"], tl.inputs["Normal"])
        add = n.new("ShaderNodeAddShader")
        C.link(nt, p.outputs["BSDF"], add.inputs[0]); C.link(nt, tl.outputs["BSDF"], add.inputs[1])
        tr = n.new("ShaderNodeBsdfTransparent")
        mix = n.new("ShaderNodeMixShader")
        C.link(nt, am.outputs["Result"], mix.inputs["Fac"])
        C.link(nt, tr.outputs["BSDF"], mix.inputs[1]); C.link(nt, add.outputs["Shader"], mix.inputs[2])
        C.link(nt, mix.outputs["Shader"], out.inputs["Surface"])
        _blended(m)
        return m
    return _get(name, mk)


def mat_cloth(name, color):
    """布傘のポリエステル生地(織り目バンプ・弱いシーン)。"""
    def mk(nm):
        m, nt, out = C.node_mat(nm)
        n = nt.nodes
        tc = n.new("ShaderNodeTexCoord")
        p = n.new("ShaderNodeBsdfPrincipled")
        p.inputs["Roughness"].default_value = 0.55
        if "Sheen Weight" in p.inputs:
            p.inputs["Sheen Weight"].default_value = 0.5
        nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.15; nz.inputs["Detail"].default_value = 5
        C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
        cr = n.new("ShaderNodeValToRGB")
        cr.color_ramp.elements[0].color = (color[0] * 0.8, color[1] * 0.8, color[2] * 0.8, 1)
        cr.color_ramp.elements[1].color = (color[0] * 1.15, color[1] * 1.15, color[2] * 1.15, 1)
        C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"]); C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
        w1 = n.new("ShaderNodeTexWave"); w1.wave_type = "BANDS"; w1.bands_direction = "X"; w1.inputs["Scale"].default_value = 160
        w2 = n.new("ShaderNodeTexWave"); w2.wave_type = "BANDS"; w2.bands_direction = "Y"; w2.inputs["Scale"].default_value = 160
        for w in (w1, w2):
            C.link(nt, tc.outputs["Object"], w.inputs["Vector"])
        mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
        C.link(nt, w1.outputs["Fac"], mul.inputs[0]); C.link(nt, w2.outputs["Fac"], mul.inputs[1])
        b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.05; b.inputs["Distance"].default_value = 0.01
        C.link(nt, mul.outputs[0], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
        C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
        return m
    return _get(name, mk)


def mat_metal(name="UmbSteel", color=(0.78, 0.78, 0.8), rough=0.22, metallic=1.0):
    return _get(name, lambda nm: C.principled(nm, color, metallic=metallic, rough=rough, noise_rough=(rough * 0.6, rough * 1.5),
                                              bump_scale=8))


def mat_plastic(name, color, rough=0.35):
    return _get(name, lambda nm: C.principled(nm, color, rough=rough, coat=0.2))


def mat_clear_plastic(name="UmbClearHandle"):
    return mat_vinyl(name, tint=(0.9, 0.93, 0.95), a_min=0.3, a_max=0.85, frost=0.3, diffuse=1.0, translucent=0.8)


def mat_paper(name="UmbTagPaper"):
    """忘れ物タグ: クリーム色の紙。上部に色帯、手書き風の線。"""
    def mk(nm):
        m, nt, out = C.node_mat(nm)
        n = nt.nodes
        tc = n.new("ShaderNodeTexCoord")
        sep = n.new("ShaderNodeSeparateXYZ"); C.link(nt, tc.outputs["Object"], sep.inputs["Vector"])
        p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.8
        # 上部の色帯(タグ座標: z=0..-8 で下へ)
        band = n.new("ShaderNodeMath"); band.operation = "GREATER_THAN"; band.inputs[1].default_value = -1.8
        C.link(nt, sep.outputs["Z"], band.inputs[0])
        # 手書き線: z 方向の縞 × ノイズで途切れ
        wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "Z"
        wv.inputs["Scale"].default_value = 0.11; wv.inputs["Distortion"].default_value = 1.5
        wv.inputs["Detail Scale"].default_value = 3
        C.link(nt, tc.outputs["Object"], wv.inputs["Vector"])
        ln = n.new("ShaderNodeMath"); ln.operation = "GREATER_THAN"; ln.inputs[1].default_value = 0.93
        C.link(nt, wv.outputs["Fac"], ln.inputs[0])
        nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.2
        C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
        nzm = n.new("ShaderNodeMath"); nzm.operation = "GREATER_THAN"; nzm.inputs[1].default_value = 0.45
        C.link(nt, nz.outputs["Fac"], nzm.inputs[0])
        lnm = n.new("ShaderNodeMath"); lnm.operation = "MULTIPLY"
        C.link(nt, ln.outputs[0], lnm.inputs[0]); C.link(nt, nzm.outputs[0], lnm.inputs[1])
        inside = n.new("ShaderNodeMath"); inside.operation = "LESS_THAN"; inside.inputs[1].default_value = -2.4
        C.link(nt, sep.outputs["Z"], inside.inputs[0])
        lnm2 = n.new("ShaderNodeMath"); lnm2.operation = "MULTIPLY"
        C.link(nt, lnm.outputs[0], lnm2.inputs[0]); C.link(nt, inside.outputs[0], lnm2.inputs[1])
        mx1 = n.new("ShaderNodeMix"); mx1.data_type = "RGBA"
        mx1.inputs["A"].default_value = (0.82, 0.78, 0.66, 1); mx1.inputs["B"].default_value = (0.7, 0.16, 0.1, 1)
        C.link(nt, band.outputs[0], mx1.inputs["Factor"])
        mx2 = n.new("ShaderNodeMix"); mx2.data_type = "RGBA"
        mx2.inputs["B"].default_value = (0.05, 0.06, 0.12, 1)
        C.link(nt, mx1.outputs["Result"], mx2.inputs["A"]); C.link(nt, lnm2.outputs[0], mx2.inputs["Factor"])
        C.link(nt, mx2.outputs["Result"], p.inputs["Base Color"])
        C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
        return m
    return _get(name, mk)


# ------------------------------------------------------------------ bmesh 形状
def _frames(pts):
    """折れ線の各点の (接線, 法線, 従法線)。平行移動フレーム。"""
    tans = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        tans.append((b - a).normalized())
    ref = Vector((0, 0, 1)) if abs(tans[0].z) < 0.9 else Vector((1, 0, 0))
    nrm = tans[0].cross(ref).normalized()
    out = []
    for t in tans:
        nrm = (nrm - t * nrm.dot(t)).normalized()
        out.append((t, nrm, t.cross(nrm)))
    return out


def tube(bm, pts, radii, sides=8, mat=0, cap=True, smooth=True):
    """折れ線に沿った管(半径は点ごと)。端は扇でふさぐ。"""
    pts = [Vector(p) for p in pts]
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * len(pts)
    rings = []
    for p, (t, nv, bv), r in zip(pts, _frames(pts), radii):
        ring = []
        for k in range(sides):
            a = math.tau * k / sides
            ring.append(bm.verts.new(p + (nv * math.cos(a) + bv * math.sin(a)) * r))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            f = bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
            f.material_index = mat; f.smooth = smooth
    if cap:
        for ring, p, flip in ((rings[0], pts[0], True), (rings[-1], pts[-1], False)):
            c = bm.verts.new(p)
            for k in range(sides):
                vs = (ring[k], ring[(k + 1) % sides], c)
                f = bm.faces.new(vs[::-1] if flip else vs)
                f.material_index = mat; f.smooth = smooth
    return rings


def rod(bm, z0, z1, r, sides=12, mat=0, x=0.0, y=0.0, round_ends=0.0):
    """Z軸に沿った円柱。round_ends>0 で端を丸める。"""
    if round_ends:
        pts, rads = [], []
        n = 4
        for i in range(n + 1):            # 下端の半球
            a = math.pi / 2 * (1 - i / n)
            pts.append((x, y, z0 + round_ends * (1 - math.sin(a))))
            rads.append(max(r * math.cos(a), r * 0.15))
        for i in range(n + 1):            # 上端の半球
            a = math.pi / 2 * i / n
            pts.append((x, y, z1 - round_ends + round_ends * math.sin(a)))
            rads.append(max(r * math.cos(a), r * 0.15))
        return tube(bm, pts, rads, sides, mat)
    return tube(bm, [(x, y, z0), (x, y, z1)], r, sides, mat)


def _new_obj(name, bm, mats, parent):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    o.parent = parent
    return o


# ------------------------------------------------------------------ 部品
def _rib_curve(s):
    """開いた親骨の (半径, z)。s=0 付け根 .. 1 先端。"""
    th = math.radians(68)
    rho = R_OPEN * math.sin(s * th) / math.sin(th)
    z = NOTCH_Z + H_OPEN * (1 - math.cos(s * th)) / (1 - math.cos(th))
    return rho, z


def _canopy_open(bm, rnd, nrib=8, sub=8, rings=26, scallop=3.2, wrinkle=0.25, mat=0):
    na = nrib * sub
    seed = rnd.random() * 100
    grid = []
    for i in range(rings + 1):
        s = 0.03 + 0.97 * i / rings
        rho, z = _rib_curve(s)
        row = []
        for j in range(na):
            a = math.tau * j / na
            d = ((a + math.pi / nrib) % (math.tau / nrib)) - math.pi / nrib   # 最寄りの骨からの角度
            u = d / (math.pi / nrib)
            chord = math.cos(math.pi / nrib) / math.cos(d)
            f = chord + (1 - chord) * 0.25            # 張った生地(弦)+少しのふくらみ
            w = max(0.0, (s - 0.75) / 0.25) ** 2
            dz = -scallop * (1 - u * u) * w           # 骨と骨の間の縁が石突き側へ反る
            r = rho * f * (1 - 0.02 * (1 - u * u) * w)
            p = Vector((r * math.cos(a), r * math.sin(a), z - 0.35 + dz))
            if wrinkle:
                p.z += wrinkle * noise.noise(Vector((p.x * 0.08, p.y * 0.08, seed))) * s
            row.append(bm.verts.new(p))
        grid.append(row)
    for r0, r1 in zip(grid, grid[1:]):
        for j in range(na):
            f = bm.faces.new((r0[j], r1[j], r1[(j + 1) % na], r0[(j + 1) % na]))
            f.material_index = mat; f.smooth = True
    # 頂点の穴をふさぐ
    c = bm.verts.new((0, 0, NOTCH_Z - 0.6))
    for j in range(na):
        f = bm.faces.new((grid[0][(j + 1) % na], grid[0][j], c)); f.material_index = mat; f.smooth = True
    # 縁の折り返し(ほんの少し厚み)
    edge = grid[-1]
    lower = [bm.verts.new(v.co + Vector((0, 0, 0.5)) - Vector((v.co.x, v.co.y, 0)).normalized() * 0.15) for v in edge]
    for j in range(na):
        f = bm.faces.new((edge[j], lower[j], lower[(j + 1) % na], edge[(j + 1) % na])); f.material_index = mat; f.smooth = True


def _closed_radius(t, rmax, pinch_t, pinch):
    if t < 0.82:
        r = 0.9 + (rmax - 0.9) * math.sin(min(t / 0.72, 1.0) * math.pi / 2) ** 1.3
    else:
        k = (t - 0.82) / 0.18
        r = rmax + (1.7 - rmax) * k ** 1.6
    if pinch_t is not None:
        r *= 1 - pinch * math.exp(-((t - pinch_t) / 0.045) ** 2)
    return r


def _canopy_closed(bm, rnd, loose=0.0, strap_t=0.62, nrib=8, rings=30, mat=0):
    na = nrib * 6
    rmax = 2.5 + 2.6 * loose
    twist = rnd.uniform(0.25, 0.6) * (1 - 0.6 * loose)
    seed = rnd.random() * 100
    z0, z1 = NOTCH_Z, NOTCH_Z + RIB_LEN
    grid = []
    for i in range(rings + 1):
        t = i / rings
        row = []
        for j in range(na):
            a = math.tau * j / na
            ph = a + twist * t * math.pi
            lobe = 0.5 - 0.5 * math.cos(nrib * ph)           # 0=骨の位置, 1=パネル中央
            r = _closed_radius(t, rmax, strap_t, 0.35 - 0.2 * loose) * (0.8 + 0.42 * lobe)
            z = z0 + (z1 - z0) * t
            if t > 0.9:
                z -= 2.8 * lobe * ((t - 0.9) / 0.1)               # 裾は骨の間が短い
            p = Vector((r * math.cos(a), r * math.sin(a), z))
            nn = noise.noise(Vector((math.cos(a) * 1.5, math.sin(a) * 1.5, z * 0.12 + seed)))
            p.x += nn * 0.35 * r / rmax; p.y += nn * 0.35 * r / rmax
            row.append(bm.verts.new(p))
        grid.append(row)
    for r0, r1 in zip(grid, grid[1:]):
        for j in range(na):
            f = bm.faces.new((r0[j], r0[(j + 1) % na], r1[(j + 1) % na], r1[j]))
            f.material_index = mat; f.smooth = True
    c = bm.verts.new((0, 0, z0 - 0.3))
    for j in range(na):
        f = bm.faces.new((grid[0][(j + 1) % na], grid[0][j], c)); f.material_index = mat; f.smooth = True
    return rmax, twist


def _hook(bm, z_base, r_grip, mat, open_dir=-1.0):
    """J字の手元(グリップ+半円のフック)。z_base から +Z へ。"""
    zt = z_base + GRIP_LEN
    pts = [(0, 0, z_base - 0.5), (0, 0, z_base), (0, 0, z_base + GRIP_LEN * 0.5), (0, 0, zt)]
    rads = [0.75, r_grip * 0.85, r_grip, r_grip * 0.96]
    R = 3.7
    for i in range(1, 15):
        a = math.pi * i / 14
        pts.append((open_dir * R * (1 - math.cos(a)), 0, zt + R * math.sin(a)))
        rads.append(r_grip * (0.96 - 0.08 * i / 14))
    end = Vector(pts[-1])
    pts.append((end.x, 0, end.z - 1.6)); rads.append(r_grip * 0.86)
    pts.append((end.x, 0, end.z - 2.1)); rads.append(r_grip * 0.6)
    tube(bm, pts, rads, 16, mat)
    # 中棒との継ぎ目の金具
    rod(bm, z_base - 0.9, z_base + 0.15, 0.85, 16, 1 if mat == 0 else 0)


def make(name, location, rotation_deg=(0, 0, 0), state="closed", kind="vinyl", color=None, tag=False, **kw):
    """傘を作って root(Empty)を返す。詳しくはモジュールの説明を参照。"""
    rnd = random.Random(kw.get("seed", hash(name) & 0xFFFF))
    loose = kw.get("loose", 0.0)
    strap = kw.get("strap", state == "closed" and loose < 0.6)

    root = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(root)
    root.empty_display_size = 10
    root.location = location
    root.rotation_euler = tuple(math.radians(a) for a in rotation_deg)
    body = bpy.data.objects.new(name + "_Body", None); bpy.context.collection.objects.link(body)
    body.parent = root
    if state == "open":   # 傘座標(石突き=0, 手元=+Z)を逆さにして手元を原点へ
        body.rotation_euler = (math.pi, 0, 0)
        body.location = (0, 0, LEN)

    # マテリアル
    if kind == "vinyl":
        canopy_m = mat_vinyl() if color is None else mat_vinyl(f"UmbVinyl_{color[0]:.2f}_{color[1]:.2f}_{color[2]:.2f}",
                                                               tint=tuple(color))
        metal = mat_metal()
        handle = kw.get("handle", "white")
    else:
        col = NAMED.get(color, None) if isinstance(color, str) else color
        col = col or NAMED["navy"]
        canopy_m = mat_cloth(f"UmbCloth_{col[0]:.3f}_{col[1]:.3f}_{col[2]:.3f}", col)
        metal = mat_metal("UmbBlackSteel", (0.03, 0.03, 0.032), rough=0.3, metallic=0.6)
        handle = kw.get("handle", "black")
    if handle == "black":
        handle_m = mat_plastic("UmbBlackPlastic", (0.015, 0.015, 0.017), 0.4)
    elif handle == "clear":
        handle_m = mat_clear_plastic()
    elif handle == "wood":
        import props as P
        handle_m = _get("UmbWood", lambda nm: P.mat_wood(nm, (0.32, 0.17, 0.08), (0.16, 0.08, 0.03), scale=0.6, rough=0.3))
    else:
        handle_m = mat_plastic("UmbWhitePlastic", (0.86, 0.86, 0.84), 0.33)
    tipcap_m = handle_m if handle != "clear" else mat_plastic("UmbWhitePlastic", (0.86, 0.86, 0.84), 0.33)

    # --- 生地(+骨先のキャップ)
    bm = bmesh.new()
    if state == "open":
        _canopy_open(bm, rnd, wrinkle=0.3 if kind == "vinyl" else 0.15)
    else:
        rmax, twist = _canopy_closed(bm, rnd, loose)
        if strap:
            zt = NOTCH_Z + RIB_LEN * 0.62
            rs = _closed_radius(0.62, rmax, 0.62, 0.35 - 0.2 * loose) * 1.02 + 0.12
            pts = [((rs + 0.02 * k) * math.cos(a), (rs + 0.02 * k) * math.sin(a), zt + 0.25 * math.sin(a * 2))
                   for k, a in enumerate(i * math.tau / 40 for i in range(43))]
            tube(bm, pts, 0.5, 4, 2, cap=True, smooth=False)
            rod(bm, zt - 0.4, zt + 0.4, 0.55, 12, 1, x=rs + 0.2, y=0)  # ボタン
    mats = [canopy_m, tipcap_m, handle_m if kind == "vinyl" and handle != "clear" else tipcap_m]
    if state == "closed" and kind == "vinyl":
        mats[2] = mat_vinyl("UmbStrapVinyl", tint=(0.9, 0.93, 0.95), a_min=0.45, a_max=0.9, frost=0.35, diffuse=1.0, translucent=0.8)
    elif state == "closed":
        mats[2] = canopy_m
    canopy = _new_obj(name + "_Canopy", bm, mats, body)

    # --- 骨・中棒(Frame)
    bm = bmesh.new()
    rod(bm, -0.2, NOTCH_Z + 0.5, 0.42, 12, 1, round_ends=0.35)           # 石突き(樹脂)
    rod(bm, NOTCH_Z - 1.0, NOTCH_Z + 1.2, 0.95, 16, 1)                   # 上ろくろ
    rod(bm, NOTCH_Z, SHAFT_END, 0.4, 12, 0)                              # 中棒
    if state == "open":
        runner_z = NOTCH_Z + 15.0
        for k in range(8):
            a = math.tau * k / 8
            ca, sa = math.cos(a), math.sin(a)
            pts = [(rho * ca + 0.9 * ca, rho * sa + 0.9 * sa, z) for rho, z in (_rib_curve(i / 20) for i in range(21))]
            tube(bm, pts, 0.17, 6, 0)
            rho, z = _rib_curve(0.48)
            tube(bm, [(1.0 * ca, 1.0 * sa, runner_z), ((rho + 0.6) * ca, (rho + 0.6) * sa, z + 0.3)], 0.14, 6, 0)
    else:
        runner_z = NOTCH_Z + RIB_LEN * 0.78
        for k in range(8):
            a = math.tau * k / 8
            ca, sa = math.cos(a), math.sin(a)
            a2 = a + twist * math.pi
            tube(bm, [(0.9 * ca, 0.9 * sa, NOTCH_Z + 1), (1.15 * math.cos(a2), 1.15 * math.sin(a2), NOTCH_Z + RIB_LEN)], 0.17, 6, 0)
    rod(bm, runner_z - 1.6, runner_z + 1.6, 0.85, 16, 1)                 # 下ろくろ
    for k in range(8):                                                   # 骨の先の樹脂キャップ(露先)
        if state == "open":
            a = math.tau * k / 8
            rho, z = _rib_curve(1.0)
            tube(bm, [((rho + 0.5) * math.cos(a), (rho + 0.5) * math.sin(a), z - 0.2),
                      ((rho + 1.7) * math.cos(a), (rho + 1.7) * math.sin(a), z + 0.6)], [0.32, 0.22], 8, 1)
        else:
            a = math.tau * k / 8 + twist * math.pi
            rr, z = 1.25, NOTCH_Z + RIB_LEN
            tube(bm, [(rr * math.cos(a), rr * math.sin(a), z - 0.8), (rr * 1.05 * math.cos(a), rr * 1.05 * math.sin(a), z + 1.0)],
                 [0.3, 0.2], 8, 1)
    frame_obj = _new_obj(name + "_Frame", bm, [metal, tipcap_m], body)

    # --- 手元
    bm = bmesh.new()
    _hook(bm, SHAFT_END, 1.35, 0)
    handle_obj = _new_obj(name + "_Handle", bm, [handle_m, metal], body)

    # --- 忘れ物タグ
    if tag:
        down = -1.0 if state == "closed" else 1.0
        bm = bmesh.new()
        gz = SHAFT_END + GRIP_LEN * 0.55
        top = Vector((4.2, 0.6, gz + down * 6.0))
        tube(bm, [(1.2, 0.3, gz), ((1.2 + top.x) / 2 + 0.3, 0.5, (gz + top.z) / 2), top], 0.06, 4, 1)
        tube(bm, [(1.2, 0.3, gz), (0.0, 1.45, gz + 0.3), (-1.45, 0.0, gz), (0.0, -1.45, gz - 0.3), (1.2, 0.3, gz)], 0.06, 4, 1)
        # 紙(4.5 x 8.5cm)。タグ物体の原点=穴の位置
        tb = bmesh.new()
        bmesh.ops.create_cube(tb, size=1.0)
        for v in tb.verts:
            v.co = Vector((v.co.x * 4.5, v.co.y * 0.04, (v.co.z - 0.5) * 8.5 + 0.6))
        tag_obj = _new_obj(name + "_Tag", tb, [mat_paper()], body)
        tag_obj.location = top
        tag_obj.rotation_euler = (math.radians(rnd.uniform(-8, 8)) + (0 if down < 0 else math.pi),
                                  math.radians(rnd.uniform(-10, 10)), math.radians(rnd.uniform(-35, 35)))
        sm = mat_plastic("UmbString", (0.85, 0.82, 0.75), 0.8)
        _new_obj(name + "_TagString", bm, [sm, sm], handle_obj)
    return root


def parts(root):
    """root の子孫から {"canopy","frame","handle","tag"} を返す(分解アニメ用)。"""
    out = {}
    for o in root.children_recursive:
        for key in ("Canopy", "Frame", "Handle", "Tag"):
            if o.name.endswith("_" + key):
                out[key.lower()] = o
    return out
