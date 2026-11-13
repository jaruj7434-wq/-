"""第4話(服)の C 系ショット用の補助。単位 1BU=1cm。

- 布マテリアル `mat_cloth`(無地/ストライプ/ギンガム/ニットのリブ。織り目バンプ+シーン)
- 吊るした服 `garment`(シャツ/コート/Tシャツ)。身頃と袖の板をボクセルリメッシュで一体化し、
  縦じわを頂点で足す(物理なし)。ローカル: X=幅, -Z=下, -Y=前。原点=首の付け根の上
- ハンガー `hanger`(木の肩+針金フック)。原点=パイプとの接点。子に服を付ける
- 値札 `price_tag`(無地の紙+糸。文字なし)
- クローゼット一式 `build_closet`(扉を開けたワードローブ、パイプ、ハンガーの服、棚のたたんだニット、
  下の収納ボックス、部屋の床と壁)。C01(値札付きシャツ)と C08(空のハンガーが揺れる)で共用
- 揺れ `swing`(パイプ回りの減衰振動)
"""
import math, random

import bmesh
import bpy
from mathutils import Vector

import common as C
import props as P
import factory_parts as F
import pet_parts2 as PP2


# ------------------------------------------------------------------ 布マテリアル
def mat_cloth(name, color, color2=None, pattern=None, scale=1.0, rough=0.82, sheen=0.35, coord=None,
              weave=0.15, vary=0.12):
    """布。pattern: None(無地)/"stripe"(縦じま、color2)/"check"(ギンガム、color2)/"rib"(ニットの縦うね)。
    scale はしま・格子の 1cm あたりの本数。coord を渡すとその Object の座標で模様を貼る(切り抜きで模様を合わせる用)。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    if coord is not None:
        tc.object = coord
    vec = tc.outputs["Object"]
    sep = n.new("ShaderNodeSeparateXYZ"); C.link(nt, vec, sep.inputs["Vector"])
    p = n.new("ShaderNodeBsdfPrincipled")
    p.inputs["Roughness"].default_value = rough
    p.inputs["Sheen Weight"].default_value = sheen; p.inputs["Sheen Roughness"].default_value = 0.45
    # 色ムラ
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.05; nz.inputs["Detail"].default_value = 3
    C.link(nt, vec, nz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (color[0] * (1 - vary), color[1] * (1 - vary), color[2] * (1 - vary), 1)
    cr.color_ramp.elements[1].color = (*color, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    col = cr.outputs["Color"]

    def bands(axis_out, s):
        """軸方向の 0/1 の帯(fract(x*s) < 0.5)。"""
        mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = s
        C.link(nt, axis_out, mul.inputs[0])
        fr = n.new("ShaderNodeMath"); fr.operation = "FRACT"; C.link(nt, mul.outputs[0], fr.inputs[0])
        lt = n.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = 0.5
        C.link(nt, fr.outputs[0], lt.inputs[0])
        return lt.outputs[0]

    if pattern in ("stripe", "check") and color2 is not None:
        fx = bands(sep.outputs["X"], scale)
        fac = fx
        if pattern == "stripe":
            thin = n.new("ShaderNodeMath"); thin.operation = "MULTIPLY"; thin.inputs[1].default_value = 1.0
            C.link(nt, fx, thin.inputs[0]); fac = thin.outputs[0]
        else:
            fz = bands(sep.outputs["Z"], scale)
            fy = bands(sep.outputs["Y"], scale)
            # 平置き(XY)でも吊り(XZ)でも格子になるよう Z と Y の両方を足す
            add = n.new("ShaderNodeMath"); add.operation = "ADD"
            C.link(nt, fx, add.inputs[0]); C.link(nt, fz, add.inputs[1])
            add2 = n.new("ShaderNodeMath"); add2.operation = "ADD"
            C.link(nt, add.outputs[0], add2.inputs[0]); C.link(nt, fy, add2.inputs[1])
            half = n.new("ShaderNodeMath"); half.operation = "MULTIPLY"; half.inputs[1].default_value = 0.5
            C.link(nt, add2.outputs[0], half.inputs[0])
            mn = n.new("ShaderNodeMath"); mn.operation = "MINIMUM"; mn.inputs[1].default_value = 1.0
            C.link(nt, half.outputs[0], mn.inputs[0]); fac = mn.outputs[0]
        mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"
        C.link(nt, fac, mx.inputs["Factor"])
        C.link(nt, col, mx.inputs["A"]); mx.inputs["B"].default_value = (*color2, 1)
        col = mx.outputs["Result"]
    C.link(nt, col, p.inputs["Base Color"])
    # 織り目(縦横の細かい波)/ニットのうね
    if pattern == "rib":
        wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"
        wv.inputs["Scale"].default_value = scale; wv.inputs["Distortion"].default_value = 0.6
        C.link(nt, vec, wv.inputs["Vector"])
        b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.6; b.inputs["Distance"].default_value = 0.3
        C.link(nt, wv.outputs["Fac"], b.inputs["Height"])
    else:
        w1 = n.new("ShaderNodeTexWave"); w1.wave_type = "BANDS"; w1.bands_direction = "X"
        w1.inputs["Scale"].default_value = 40; C.link(nt, vec, w1.inputs["Vector"])
        w2 = n.new("ShaderNodeTexWave"); w2.wave_type = "BANDS"; w2.bands_direction = "Z"
        w2.inputs["Scale"].default_value = 40; C.link(nt, vec, w2.inputs["Vector"])
        mw = n.new("ShaderNodeMath"); mw.operation = "MULTIPLY"
        C.link(nt, w1.outputs["Fac"], mw.inputs[0]); C.link(nt, w2.outputs["Fac"], mw.inputs[1])
        b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = weave; b.inputs["Distance"].default_value = 0.05
        C.link(nt, mw.outputs[0], b.inputs["Height"])
    C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


# ------------------------------------------------------------------ メッシュ補助
def _prism(bm, poly_xz, y0, y1):
    """XZ 平面の多角形を Y 方向に押し出した柱を bm に追加。"""
    vf = [bm.verts.new((x, y0, z)) for x, z in poly_xz]
    vb = [bm.verts.new((x, y1, z)) for x, z in poly_xz]
    k = len(poly_xz)
    bm.faces.new(vf[::-1]); bm.faces.new(vb)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((vf[i], vf[j], vb[j], vb[i]))


def _quad_along(p0, d, length, w0, w1):
    """p0 から方向 d(XZ 単位ベクトル)へ length 伸びる台形(根元幅 w0, 先幅 w1)。"""
    nx, nz = -d[1], d[0]
    e = (p0[0] + d[0] * length, p0[1] + d[1] * length)
    return [(p0[0] + nx * w0 / 2, p0[1] + nz * w0 / 2), (e[0] + nx * w1 / 2, e[1] + nz * w1 / 2),
            (e[0] - nx * w1 / 2, e[1] - nz * w1 / 2), (p0[0] - nx * w0 / 2, p0[1] - nz * w0 / 2)], e


def mesh_object(name, me):
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return o


def bake_modifiers(o):
    """モディファイアを適用した新しいメッシュに差し替える(静止物の評価を軽く)。"""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    old = o.data
    o.modifiers.clear()
    o.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return o


GARMENTS = {
    # half_w(肩), half_w(すそ), 丈, 厚み, 袖丈, 袖幅(根元, 先), 袖の角度(水平から下向き°)
    "shirt": dict(sh=21.0, hem=25.0, chest=24.0, length=74.0, thick=3.2, sleeve=58.0, sw=(16.0, 10.0), sdeg=74.0),
    "coat": dict(sh=24.0, hem=31.0, chest=27.0, length=102.0, thick=6.0, sleeve=62.0, sw=(19.0, 14.0), sdeg=78.0),
    "tee": dict(sh=22.0, hem=25.0, chest=25.0, length=68.0, thick=2.6, sleeve=20.0, sw=(18.0, 15.0), sdeg=55.0),
    "knit": dict(sh=23.0, hem=24.0, chest=26.0, length=64.0, thick=4.0, sleeve=56.0, sw=(17.0, 10.0), sdeg=76.0),
}


def fold_offset(x, z, length, seed=0.0, amp=0.9):
    """吊るした服の縦じわ(Y方向のずれ)。肩で0、すそほど大きい。"""
    t = min(1.0, max(0.0, -z / length))
    a = amp * (0.15 + 0.85 * t)
    return a * (math.sin(x * 0.42 + seed + 0.9 * math.sin(z * 0.06 + seed * 1.7))
                + 0.45 * math.sin(x * 0.95 - seed * 2.3 + z * 0.03))


def garment(name, kind="shirt", mat=None, seed=0, collar=True, buttons=True, trim_mat=None, sleeve_deg=None,
            voxel=1.0):
    """吊るした服(身頃+袖をリメッシュで一体化)。戻り値 (obj, anchors)。
    anchors: "cuff_l"/"cuff_r"(袖口の中心), "front_y"(前面の y), "hem_z"。"""
    g = dict(GARMENTS[kind])
    sh, hem, chest, L, t = g["sh"], g["hem"], g["chest"], g["length"], g["thick"]
    sdeg = g["sdeg"] if sleeve_deg is None else sleeve_deg
    bm = bmesh.new()
    body = [(-7.5, -0.5), (-sh, -5.5), (-chest, -20.0), (-hem, -L), (hem, -L), (chest, -20.0), (sh, -5.5), (7.5, -0.5),
            (0.0, -2.0)]
    _prism(bm, body, -t / 2, t / 2)
    anchors = {}
    for s, nm in ((-1, "cuff_l"), (1, "cuff_r")):
        a = math.radians(sdeg)
        d = (s * math.cos(a), -math.sin(a))
        p0 = (s * (sh - 2.5), -5.5 - g["sw"][0] * 0.35)
        quad, e = _quad_along(p0, d, g["sleeve"], g["sw"][0], g["sw"][1])
        # 袖は身頃の前側に少し重ねる
        _prism(bm, quad, -t / 2 - 0.6, t / 2 - 0.2)
        anchors[nm] = Vector((e[0], -t / 2 - 0.2, e[1]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = mesh_object(name, me)
    rm = o.modifiers.new("rm", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = voxel; rm.use_smooth_shade = True
    bake_modifiers(o)
    # 縦じわ・すその広がり
    sd = seed * 1.37
    for v in o.data.vertices:
        x, y, z = v.co
        v.co.y = y + fold_offset(x, z, L, sd)
        tt = min(1.0, max(0.0, -z / L))
        v.co.x = x * (1.0 + 0.03 * tt)
    for nm in ("cuff_l", "cuff_r"):
        c = anchors[nm]; c.y += fold_offset(c.x, c.z, L, sd)
    sm = o.modifiers.new("sm", "SMOOTH"); sm.factor = 0.5; sm.iterations = 2
    bake_modifiers(o)
    for poly in o.data.polygons:
        poly.use_smooth = True
    if mat:
        o.data.materials.append(mat)
    tm = trim_mat or mat
    front = lambda x, z: -t / 2 + fold_offset(x, z, L, sd) - 0.05
    anchors["front_y"] = front(0, -30)
    anchors["hem_z"] = -L
    anchors["chest"] = Vector((0.6, front(0.6, -19.0) - 0.9, -19.0))   # 3つ目のボタンあたり(値札の糸を通す)
    if collar and kind in ("shirt", "coat", "knit"):
        bpy.ops.mesh.primitive_torus_add(major_radius=7.6, minor_radius=1.3 if kind != "coat" else 2.0,
                                         major_segments=32, minor_segments=8, location=(0, 0, -1.2))
        cl = bpy.context.object; cl.name = name + "_Collar"
        cl.scale = (1.0, (t / 2 + 1.2) / 7.6, 1.6 if kind == "coat" else 1.0)
        bpy.ops.object.shade_smooth()
        cl.data.materials.append(tm)
        cl.parent = o
        if kind in ("shirt", "coat"):
            # 前の襟先(三角)/コートは下襟
            for s in (-1, 1):
                if kind == "shirt":
                    tri = [(s * 1.0, -2.5), (s * 8.0, -2.0), (s * 4.0, -9.0)]
                else:
                    tri = [(s * 1.5, -3.0), (s * 11.0, -3.5), (s * 9.0, -20.0), (s * 2.5, -30.0)]
                bm = bmesh.new()
                fy = front(s * 4, -6)
                _prism(bm, tri, fy - 0.8, fy + 0.1)
                me2 = bpy.data.meshes.new(name + f"_Lapel{s}"); bm.to_mesh(me2); bm.free()
                lp = mesh_object(name + f"_Lapel{s}", me2); lp.parent = o
                bv = lp.modifiers.new("bv", "BEVEL"); bv.width = 0.35; bv.segments = 2
                lp.data.materials.append(tm)
    if kind == "shirt":
        # 前立て(ボタンの帯)と胸ポケット: 前面のしわに沿う薄い板
        def strip(nm, x0, x1, z0, z1, nz=14):
            bm = bmesh.new()
            rows = []
            for i in range(nz + 1):
                z = z0 + (z1 - z0) * i / nz
                rows.append([bm.verts.new((x, front(x, z) - 0.12, z)) for x in (x0, x1)])
            for i in range(nz):
                bm.faces.new((rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]))
            me3 = bpy.data.meshes.new(nm); bm.to_mesh(me3); bm.free()
            so = mesh_object(nm, me3); so.parent = o
            sl = so.modifiers.new("sol", "SOLIDIFY"); sl.thickness = 0.25; sl.offset = 1.0
            bv = so.modifiers.new("bv", "BEVEL"); bv.width = 0.1; bv.segments = 1
            so.data.materials.append(tm)
            for p_ in so.data.polygons:
                p_.use_smooth = True
            return so
        strip(name + "_Placket", -1.6, 1.6, -3.0, -L + 1.0, 18)
        strip(name + "_Pocket", -15.0, -6.0, -16.0, -26.5, 4)
    if buttons and kind in ("shirt", "coat"):
        bmat = bpy.data.materials.get("ButtonM") or C.principled("ButtonM", (0.92, 0.9, 0.86), rough=0.3)
        n_b = 6 if kind == "shirt" else 3
        z0, z1 = (-8.0, -L + 8.0) if kind == "shirt" else (-34.0, -70.0)
        r = 0.55 if kind == "shirt" else 1.3
        for i in range(n_b):
            z = z0 + (z1 - z0) * i / max(1, n_b - 1)
            x = 0.0 if kind == "shirt" else 3.5
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=r, depth=0.3,
                                                location=(x, front(x, z) - 0.5, z), rotation=(math.pi / 2, 0, 0))
            b = bpy.context.object; b.name = name + f"_Btn{i}"; b.parent = o
            b.data.materials.append(bmat if kind == "shirt" else tm)
    return o, anchors


# ------------------------------------------------------------------ ハンガー
_HANGER_CACHE = {}


def _curve(name, pts, bevel, mat, closed=False):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"
    cu.bevel_depth = bevel; cu.bevel_resolution = 3; cu.use_fill_caps = True
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1.0)
    sp.use_smooth = True; sp.use_cyclic_u = closed
    cu.materials.append(mat)
    return cu


def hanger(name, wood=True, rod_r=1.3):
    """ハンガー(XZ 平面、原点=パイプの中心)。戻り値は根の Object(フック)。肩のバーは z≈-9〜-16。"""
    if "data" not in _HANGER_CACHE:
        mw = (P.mat_wood("HangerWood", base=(0.55, 0.36, 0.2), dark=(0.36, 0.22, 0.11), scale=0.3, rough=0.35)
              if wood else C.principled("HangerPlastic", (0.9, 0.9, 0.9), rough=0.4))
        mm = F.mat_steel("HangerWire", (0.75, 0.75, 0.76), rough=0.2)[0]
        hr = rod_r + 0.35
        hook = []
        for i in range(25):
            a = math.radians(200 - i * (260 / 24))     # 先端(左下)→上→右→右下
            hook.append((hr * math.cos(a), 0.0, hr * math.sin(a)))
        hook += [(0.9, 0, -2.6), (0.0, 0, -4.2), (0.0, 0, -9.0)]
        bar = []
        for i in range(33):
            u = -1 + 2 * i / 32
            x = 21.5 * u
            z = -9.6 - 6.8 * abs(u) ** 1.35
            bar.append((x, 0.0, z))
        _HANGER_CACHE["data"] = (_curve("HookC", hook, 0.17, mm), _curve("BarC", bar, 0.75, mw))
    hook_c, bar_c = _HANGER_CACHE["data"]
    root = bpy.data.objects.new(name, hook_c); bpy.context.collection.objects.link(root)
    bar = bpy.data.objects.new(name + "_Bar", bar_c); bpy.context.collection.objects.link(bar)
    bar.parent = root
    bar.scale = (1, 1.9, 1)       # 木の肩は少し厚く
    root.rotation_mode = "ZXY"    # Z(向き)→ X(パイプ回りの揺れ)
    return root


def swing(obj, start, amp_deg, period=34.0, decay=55.0, end=None, axis=0, base=None):
    """パイプ回り(rotation_mode ZXY の X)の減衰振動を毎フレームキー。base=静止角(度)。"""
    end = end or bpy.context.scene.frame_end
    b = obj.rotation_euler[axis] if base is None else math.radians(base)
    for f in range(start, end + 1):
        t = f - start
        obj.rotation_euler[axis] = b + math.radians(amp_deg) * math.exp(-t / decay) * math.sin(math.tau * t / period)
        obj.keyframe_insert("rotation_euler", index=axis, frame=f)
    F.set_interp(obj, "LINEAR", path="rotation_euler")


# ------------------------------------------------------------------ 値札
def price_tag(name, attach, drop=6.0, size=(4.2, 6.6), color=(0.93, 0.9, 0.82), parent=None):
    """糸で吊るした無地の紙の値札(文字・ロゴなし)。戻り値 pivot(attach の位置の Empty。回すと揺れる)。"""
    pv = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(pv)
    pv.empty_display_size = 1.0
    if parent:
        pv.parent = parent
    pv.location = attach
    pm = bpy.data.materials.get("TagPaperM") or C.principled("TagPaperM", color, rough=0.75, bump=0.04, bump_scale=30)
    sm = bpy.data.materials.get("TagStringM") or C.principled("TagStringM", (0.85, 0.82, 0.76), rough=0.9)
    w, h = size
    # 角を落とした紙(上辺の角を斜めに切った荷札形)
    poly = [(-w / 2, -drop - h), (w / 2, -drop - h), (w / 2, -drop - 1.0), (w / 2 - 1.0, -drop),
            (-w / 2 + 1.0, -drop), (-w / 2, -drop - 1.0)]
    bm = bmesh.new(); _prism(bm, poly, -0.03, 0.03)
    me = bpy.data.meshes.new(name + "_Paper"); bm.to_mesh(me); bm.free()
    paper = mesh_object(name + "_Paper", me); paper.parent = pv
    paper.data.materials.append(pm)
    # 穴の補強リング(少し濃い紙色)
    rm = bpy.data.materials.get("TagRingM") or C.principled("TagRingM", (0.72, 0.62, 0.45), rough=0.6)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.42, minor_radius=0.14, major_segments=16, minor_segments=6,
                                     location=(0, -0.06, -drop - 1.0), rotation=(math.pi / 2, 0, 0))
    ring = bpy.context.object; ring.name = name + "_Ring"; ring.parent = pv
    ring.data.materials.append(rm)
    # 糸(輪になって垂れる)
    pts = [(0, 0, 0), (0.5, -0.1, -drop * 0.35), (0.25, -0.1, -drop * 0.75), (0, -0.06, -drop - 1.0)]
    st = bpy.data.objects.new(name + "_String", _curve(name + "_StringC", pts, 0.05, sm))
    bpy.context.collection.objects.link(st); st.parent = pv
    return pv


# ------------------------------------------------------------------ クローゼット
DEFAULT_LAYOUT = [
    # (種類, 色, 2色目/None, 模様, 向きの補正°)。"empty" は服なしのハンガー
    ("coat", (0.52, 0.36, 0.2), None, None, 0),
    ("coat", (0.12, 0.13, 0.15), None, None, 4),
    ("knit", (0.62, 0.18, 0.14), None, "rib", -3),
    ("shirt", (0.12, 0.18, 0.32), None, None, 5),
    ("shirt", (0.9, 0.9, 0.88), (0.25, 0.42, 0.7), "stripe", -4),
    ("shirt", (0.78, 0.68, 0.5), None, None, 3),
    ("empty", None, None, None, 0),
    ("shirt", (0.55, 0.68, 0.82), None, None, -2),
    ("shirt", (0.92, 0.92, 0.9), (0.22, 0.5, 0.36), "check", 6),
    ("tag", (0.9, 0.68, 0.66), None, None, 0),        # 値札付きの淡いピンクのシャツ(手前に向ける)
]
SPACING = {"coat": 11.0, "knit": 9.0, "shirt": 7.5, "tee": 7.0, "empty": 5.0, "tag": 16.0}


def build_room(width=600.0, wall_y=70.0, wall_h=270.0, floor_color=(0.42, 0.27, 0.15), wall_color=(0.86, 0.83, 0.78)):
    """部屋の床(フローリング)・奥の壁・幅木。原点=クローゼット前面の床中央。"""
    floor_m = P.mat_wood("FloorWood", base=floor_color, dark=(floor_color[0] * 0.6, floor_color[1] * 0.6, floor_color[2] * 0.6),
                         scale=0.06, rough=0.35)
    fl = P.plane("Floor", (width, 900), (0, -380, 0), mat=floor_m)
    wall_m = C.principled("WallM", wall_color, rough=0.85, bump=0.03, bump_scale=2)
    wl = P.plane("Wall", (width, wall_h), (0, wall_y, wall_h / 2), rot=(90, 0, 0), mat=wall_m)
    P.box("Baseboard", (width, 1.5, 8), (0, wall_y - 0.75, 4), mat=C.principled("BaseboardM", (0.92, 0.9, 0.86), rough=0.5))
    return fl, wl


def _drop_collar(parts):
    """PP2.tshirt の襟(上から見ると取っ手に見える)を外して、たたんだニットにする。"""
    for o in parts:
        if o.name.endswith(("_Collar", "_Neck")):
            bpy.data.objects.remove(o, do_unlink=True)


def build_closet(origin=(0.0, 0.0, 0.0), width=170.0, depth=62.0, height=210.0, layout=None, door_deg=105.0,
                 room=True, seed=3, shelf_items=True, bottom_items=True, wood_color=(0.62, 0.45, 0.28)):
    """扉を開けたワードローブと中の服。原点=前面下の中央、奥が +Y。
    戻り値 dict: root(Empty), hangers(根 Object の list), garments(服 Object または None の list), slots(各スロットの種類),
    tag(値札の pivot か None), rod=(y, z), inner=(x0, x1, y0, y1, z0, z1), doors=(左, 右), knits(list)。
    C08 では layout に "empty" を入れ、空のハンガーを swing() で揺らす。"""
    rnd = random.Random(seed)
    ox, oy, oz = origin
    root = bpy.data.objects.new("Closet", None); bpy.context.collection.objects.link(root)
    if room:
        build_room(wall_y=oy + depth + 4.0)
    wood = P.mat_wood("ClosetWood", base=wood_color, dark=(wood_color[0] * 0.7, wood_color[1] * 0.68, wood_color[2] * 0.62),
                      scale=0.12, rough=0.4)
    inner_m = C.principled("ClosetInner", (0.88, 0.84, 0.76), rough=0.7)
    T = 2.0
    W, D, H = width, depth, height
    parts = []
    parts.append(P.box("ClSideL", (T, D, H), (-W / 2 + T / 2, D / 2, H / 2), mat=wood, bevel=0.2))
    parts.append(P.box("ClSideR", (T, D, H), (W / 2 - T / 2, D / 2, H / 2), mat=wood, bevel=0.2))
    parts.append(P.box("ClTop", (W, D, T), (0, D / 2, H - T / 2), mat=wood, bevel=0.2))
    parts.append(P.box("ClBottom", (W - 2 * T, D, T), (0, D / 2, 8 + T / 2), mat=wood, bevel=0.2))
    parts.append(P.box("ClPlinth", (W - 2 * T, T, 8), (0, 3, 4), mat=wood))
    parts.append(P.box("ClBack", (W - 2 * T, 1.0, H - T), (0, D - 0.5, (H - T) / 2), mat=inner_m))
    shelf_z = H - 30.0
    parts.append(P.box("ClShelf", (W - 2 * T, D - 4, T), (0, D / 2 + 1, shelf_z), mat=wood, bevel=0.2))
    rod_y, rod_z = D / 2 + 2, shelf_z - 12.0
    steel = F.mat_steel("RodSteel", (0.8, 0.8, 0.82), rough=0.15)[0]
    parts.append(P.cyl("ClRod", 1.3, W - 2 * T, (0, rod_y, rod_z), (0, math.pi / 2, 0), mat=steel, verts=24))
    for s in (-1, 1):
        parts.append(P.cyl(f"ClRodCup{s}", 2.0, 1.0, (s * (W / 2 - T - 0.5), rod_y, rod_z), (0, math.pi / 2, 0), mat=steel, verts=24))
    # 扉(外へ開く。蝶番は側板の前端)
    doors = []
    for s in (-1, 1):
        pv = bpy.data.objects.new(f"ClDoorHinge{s}", None); bpy.context.collection.objects.link(pv)
        pv.location = (s * W / 2, -0.2, 0)
        dw = W / 2
        dr = P.box(f"ClDoor{s}", (dw, T, H - 1), (-s * dw / 2, -T / 2, H / 2), mat=wood, bevel=0.3)
        dr.parent = pv
        # 鏡板(枠の内側を少し凹ませた見え)
        pn = P.box(f"ClDoorPanel{s}", (dw - 14, 0.6, H - 30), (-s * dw / 2, -T - 0.1, H / 2), mat=wood, bevel=0.6)
        pn.parent = pv
        kn = P.cyl(f"ClKnob{s}", 1.4, 3.0, (-s * (dw - 5), -T - 1.5, H * 0.5), (math.pi / 2, 0, 0), mat=steel, verts=24)
        kn.parent = pv
        pv.rotation_euler = (0, 0, math.radians(s * door_deg))
        doors.append(pv)
    for o in parts:
        o.parent = root

    # ---- ハンガーの服
    layout = DEFAULT_LAYOUT if layout is None else layout
    total = sum(SPACING[k[0]] for k in layout)
    x = -W / 2 + T + 8.0
    left_room = (W - 2 * T - 16.0) - total
    x += max(0.0, left_room * 0.15)
    hangers, garments, slots = [], [], []
    tag_pv = None
    for i, (kind, color, color2, pattern, rot) in enumerate(layout):
        sp = SPACING[kind]
        x += sp / 2
        hg = hanger(f"Hanger{i}")
        hg.parent = root
        face = 90.0 + rot + rnd.uniform(-4, 4)
        if kind == "tag":
            face = 28.0 + rot
            x += 6.0
        hg.location = (x, rod_y, rod_z)
        hg.rotation_euler = (math.radians(rnd.uniform(-1.5, 1.5)), 0, math.radians(face))
        g = None
        if kind != "empty":
            gk = "shirt" if kind == "tag" else kind
            mat = mat_cloth(f"Cloth{i}", color, color2, pattern,
                            scale={"stripe": 1.2, "check": 0.55, "rib": 2.5}.get(pattern, 1.0),
                            sheen=0.5 if gk == "knit" else 0.3)
            g, anc = garment(f"Garment{i}", gk, mat, seed=i + seed)
            g.parent = hg
            g.location = (0, 0, -9.3)
            if kind == "tag":
                tag_pv = price_tag("PriceTag", anc["chest"], drop=4.5, size=(5.0, 8.0), parent=g)
        hangers.append(hg); garments.append(g); slots.append(kind)
        x += sp / 2

    # ---- 棚の上: たたんだニット(2〜3山)
    knits = []
    if shelf_items:
        kcol = [(0.88, 0.84, 0.74), (0.72, 0.56, 0.2), (0.42, 0.48, 0.4), (0.6, 0.62, 0.66), (0.78, 0.5, 0.45),
                (0.25, 0.3, 0.42)]
        k = 0
        for sx in (-W * 0.3, -W * 0.02, W * 0.27):
            zz = shelf_z + T / 2
            for j in range(3 if sx < W * 0.2 else 2):
                c = kcol[(k * 2 + 1) % len(kcol)]
                m = mat_cloth(f"KnitM{k}", c, pattern="rib", scale=2.2, sheen=0.55, weave=0.0)
                body, kp = PP2.tshirt(f"Knit{k}", m, size=(34.0, 27.0, 4.4))
                _drop_collar(kp)
                body.rotation_euler = (0, 0, math.radians(180 + rnd.uniform(-4, 4)))   # 折り山(襟の反対側)を手前に
                body.location = (sx + rnd.uniform(-2, 2), D / 2 + 2 + rnd.uniform(-1.5, 1.5), zz + 2.2)
                body.parent = root
                zz += 4.6
                knits.append(body)
                k += 1
    # ---- 下: 布の収納ボックス(ふたなし)と、たたんだ服
    if bottom_items:
        bm_ = F.mat_canvas("BinCanvas", (0.6, 0.55, 0.47), weave=3.0)
        for j, bx in enumerate((W * 0.08, W * 0.3)):
            P.open_box(f"Bin{j}", (36, 40, 26), (bx, D / 2 + 2, 10 + 13), wall=0.8, mat=bm_, bevel=0.3).parent = root
            c = [(0.3, 0.42, 0.55), (0.82, 0.78, 0.7)][j]
            m = mat_cloth(f"BinClothM{j}", c, pattern="rib", scale=1.5, sheen=0.4, weave=0.0)
            tb, kp = PP2.tshirt(f"BinTee{j}", m, size=(30.0, 32.0, 4.0))
            _drop_collar(kp)
            tb.location = (bx, D / 2 + 2, 10 + 24.5); tb.rotation_euler = (0, 0, math.radians(rnd.uniform(-6, 6)))
            tb.parent = root
    root.location = (ox, oy, oz)
    return dict(root=root, hangers=hangers, garments=garments, slots=slots, tag=tag_pv, rod=(rod_y + oy, rod_z + oz),
                inner=(ox - W / 2 + T, ox + W / 2 - T, oy, oy + D, oz + 10, oz + shelf_z), doors=doors, knits=knits,
                shelf_z=shelf_z + oz)


def closet_lights(target=(0, 30, 120), key_energy=6e5, warm=(1.0, 0.9, 0.78)):
    """部屋の照明: 左の窓(暖かいキー)+ 右手前のフィル + クローゼット内の柔らかい上からの光。"""
    key = C.area_light((-260, -170, 210), (0, 0, 0), 160, key_energy, warm, "WindowKey")
    C.light_look_at(key, target)
    fill = C.area_light((230, -260, 170), (0, 0, 0), 200, key_energy * 0.3, (0.88, 0.92, 1.0), "Fill")
    C.light_look_at(fill, target)
    inner = C.area_light((0, -40, 205), (0, 0, 0), 140, key_energy * 0.18, (1.0, 0.93, 0.84), "InnerTop")
    C.light_look_at(inner, (0, 40, 110))
    P.reflection_probe((0, -60, 120), radius=400, clip_start=1)
    return key, fill, inner
