"""車・フロントガラス・霜・ヒビ・雪の地面・HDRI の空。

座標と (u, v) の決まりは plan.py を参照。霜は「溶ける時刻のマップ」(maps.py で作る画像)と、
キーフレームで動かすしきい値を比べて、場所ごとに消えたり(溶ける)現れたり(再凍結)する。
"""
import math
import random

import bmesh
import bpy
import numpy as np

from kit import add_bump, assign, box, cyl, glow, light, metal, principled, smooth
from plan import to_uv, ws_normal, ws_point

HDRI_DIR = None   # shots.py が作業フォルダの hdri/ を設定する
NU, NV = 96, 48   # フロントガラスの分割数


# ---------------------------------------------------------------- 空と地面
def world_hdri(scene, name="passendorf_snow", strength=1.0, sun_az=0.0, tint=(1, 1, 1), sun=3.0):
    """HDRI(Poly Haven・CC0)で空と環境光を作り、太陽の向きに合わせた太陽光を足す。
    sun_az: 太陽を置きたい方位 [度](0=+x、90=+y、-90=手前 -y)。戻り値は (太陽光, 背景ノード, 色ミックス)。"""
    w = scene.world
    n, l = w.node_tree.nodes, w.node_tree.links
    img = bpy.data.images.load(f"{HDRI_DIR}/{name}_1k.exr", check_existing=True)
    tc, mp, env = n.new("ShaderNodeTexCoord"), n.new("ShaderNodeMapping"), n.new("ShaderNodeTexEnvironment")
    env.image = img
    mix = n.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs[7].default_value = (*tint, 1)
    l.new(tc.outputs["Generated"], mp.inputs["Vector"])
    l.new(mp.outputs["Vector"], env.inputs["Vector"])
    l.new(env.outputs["Color"], mix.inputs[6])
    bg = n["Background"]
    l.new(mix.outputs[2], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    # 画像のいちばん明るい点=太陽の向き
    w_, h_ = img.size
    px = np.empty(w_ * h_ * 4, np.float32)
    img.pixels.foreach_get(px)
    lum = px.reshape(h_, w_, 4)[..., :3].sum(-1)
    y, x = np.unravel_index(int(lum.argmax()), lum.shape)
    phi = ((x + 0.5) / w_ - 0.5) * math.tau   # Blender の正距円筒図法:u = atan2(y, -x) / 2π + 0.5
    el = ((y + 0.5) / h_ - 0.5) * math.pi
    di = (-math.cos(phi) * math.cos(el), math.sin(phi) * math.cos(el), math.sin(el))
    rot = math.atan2(di[1], di[0]) - math.radians(sun_az)   # 背景を回して太陽を望みの方位へ
    mp.inputs["Rotation"].default_value = (0, 0, rot)
    r = -rot
    d = (di[0] * math.cos(r) - di[1] * math.sin(r), di[0] * math.sin(r) + di[1] * math.cos(r), di[2])
    lamp = light(scene, "SUN", "Sun", (d[0] * 10, d[1] * 10, d[2] * 10), sun * strength, (1.0, 0.86, 0.7),
                 size=math.radians(1.5), look_at=(0, 0, 0))
    return lamp, bg, mix


def snow_ground(scene, size=240):
    snow = principled("Snow", (0.9, 0.93, 0.97), rough=0.55, sss=0.5, sss_radius=(0.8, 0.9, 1.0), sss_scale=0.03)
    add_bump(snow, scale=6, strength=0.35)
    add_bump(snow, scale=900, strength=0.25, distance=0.002)   # 粒のきらめき
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=200, y_subdivisions=200, size=size)
    g = bpy.context.active_object
    g.name = "Ground"
    tex = bpy.data.textures.new("Drift", "CLOUDS")
    tex.noise_scale = 4.0
    d = g.modifiers.new("drift", "DISPLACE")
    d.texture, d.strength, d.mid_level = tex, 0.18, 0.6
    smooth(g)
    assign(g, snow)
    return g


# ---------------------------------------------------------------- 霜
def _img(path):
    im = bpy.data.images.load(str(path), check_existing=True)
    im.colorspace_settings.name = "Non-Color"
    return im


def frost_material(name, melt_map=None, freeze_map=None, cover=1.0, uv_scale=(1.4, 0.88), seed=0.0):
    """霜(白い結晶)のマテリアル。返り値の dict の "melt" / "freeze" を keyframe するとしきい値が動く。

    melt_map: 霜が溶ける時刻(0〜1)の画像。しきい値 melt を超えた場所から透明になる。
    freeze_map: 溶けた場所が再び凍る時刻の画像。しきい値 freeze を超えた場所に厚い氷が現れる。
    cover: 全体の霜の量(0〜1)。
    """
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    n, l = mat.node_tree.nodes, mat.node_tree.links
    out = n["Material Output"]
    n.remove(n["Principled BSDF"])

    def node(kind, **inputs):
        x = n.new(kind)
        for k, v in inputs.items():
            x.inputs[k].default_value = v
        return x

    def math_(op, a, b=None, clamp=False):
        m = n.new("ShaderNodeMath")
        m.operation, m.use_clamp = op, clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                l.new(v, m.inputs[i])
        return m.outputs[0]

    uv = n.new("ShaderNodeUVMap")
    mp = node("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (*uv_scale, 1)
    mp.inputs["Location"].default_value = (seed * 3.7, seed * 1.3, seed)
    l.new(uv.outputs["UV"], mp.inputs["Vector"])
    # 座標をノイズでゆがませて、結晶の模様をタイル状でなく有機的にする
    warp = node("ShaderNodeTexNoise", Scale=9.0, Detail=6.0)
    l.new(mp.outputs["Vector"], warp.inputs["Vector"])
    wsub = n.new("ShaderNodeVectorMath")
    wsub.operation = "SUBTRACT"
    l.new(warp.outputs["Color"], wsub.inputs[0])
    wsub.inputs[1].default_value = (0.5, 0.5, 0.5)
    wsc = n.new("ShaderNodeVectorMath")
    wsc.operation = "MULTIPLY_ADD"
    l.new(wsub.outputs[0], wsc.inputs[0])
    wsc.inputs[1].default_value = (0.06, 0.06, 0.06)
    l.new(mp.outputs["Vector"], wsc.inputs[2])
    vec = wsc.outputs[0]
    # 結晶のすじ(ボロノイの境界)+ムラ(低周波ノイズ)+細かい粒(高周波ノイズ)
    vor = n.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 60.0
    vor.inputs["Randomness"].default_value = 1.0
    l.new(vec, vor.inputs["Vector"])
    vor2 = n.new("ShaderNodeTexVoronoi")
    vor2.feature = "DISTANCE_TO_EDGE"
    vor2.inputs["Scale"].default_value = 260.0
    l.new(vec, vor2.inputs["Vector"])
    patch = node("ShaderNodeTexNoise", Scale=5.0, Detail=8.0, Roughness=0.6)
    l.new(vec, patch.inputs["Vector"])
    grain = node("ShaderNodeTexNoise", Scale=600.0, Detail=2.0)
    l.new(vec, grain.inputs["Vector"])
    ridge = math_("SUBTRACT", 1.0, math_("MULTIPLY", vor.outputs["Distance"], 9.0), clamp=True)
    ridge2 = math_("SUBTRACT", 1.0, math_("MULTIPLY", vor2.outputs["Distance"], 6.0), clamp=True)
    dens = math_("ADD", math_("MULTIPLY", math_("SUBTRACT", patch.outputs["Fac"], 0.5), 1.1), 0.62)
    dens = math_("ADD", dens, math_("MULTIPLY", ridge, 0.14))
    dens = math_("ADD", dens, math_("MULTIPLY", ridge2, 0.12))
    dens = math_("ADD", dens, math_("MULTIPLY", math_("SUBTRACT", grain.outputs["Fac"], 0.5), 0.5), clamp=True)

    ctrl = {}
    cov = n.new("ShaderNodeValue")
    cov.outputs[0].default_value = cover
    ctrl["cover"] = cov.outputs[0]
    amount = math_("MULTIPLY", dens, cov.outputs[0])
    if melt_map is not None:
        tex = n.new("ShaderNodeTexImage")
        tex.image = _img(melt_map)
        tex.interpolation = "Cubic"
        l.new(uv.outputs["UV"], tex.inputs["Vector"])
        t = n.new("ShaderNodeValue")
        t.outputs[0].default_value = 0.0
        ctrl["melt"] = t.outputs[0]
        # 境目を少しギザギザにする
        edge_noise = node("ShaderNodeTexNoise", Scale=60.0, Detail=4.0)
        l.new(vec, edge_noise.inputs["Vector"])
        m = math_("ADD", tex.outputs["Color"], math_("MULTIPLY", math_("SUBTRACT", edge_noise.outputs["Fac"], 0.5), 0.04))
        keep = math_("MULTIPLY", math_("SUBTRACT", m, t.outputs[0]), 40.0)
        keep = math_("ADD", keep, 0.5, clamp=True)
        amount = math_("MULTIPLY", amount, keep)
    ice = None
    if freeze_map is not None:
        tex2 = n.new("ShaderNodeTexImage")
        tex2.image = _img(freeze_map)
        tex2.interpolation = "Cubic"
        l.new(uv.outputs["UV"], tex2.inputs["Vector"])
        t2 = n.new("ShaderNodeValue")
        t2.outputs[0].default_value = 0.0
        ctrl["freeze"] = t2.outputs[0]
        ice = math_("ADD", math_("MULTIPLY", math_("SUBTRACT", t2.outputs[0], tex2.outputs["Color"]), 30.0), 0.5, clamp=True)

    frost = n.new("ShaderNodeBsdfPrincipled")
    frost.inputs["Base Color"].default_value = (0.86, 0.9, 0.95, 1)
    frost.inputs["Roughness"].default_value = 0.5
    frost.inputs["Subsurface Weight"].default_value = 0.35
    frost.inputs["Subsurface Radius"].default_value = (0.8, 0.9, 1.0)
    frost.inputs["Subsurface Scale"].default_value = 0.002
    frost.inputs["Specular IOR Level"].default_value = 0.6
    bump = node("ShaderNodeBump", Strength=0.5, Distance=0.0005)
    l.new(math_("ADD", dens, math_("MULTIPLY", grain.outputs["Fac"], 0.5)), bump.inputs["Height"])
    l.new(bump.outputs["Normal"], frost.inputs["Normal"])
    clear = n.new("ShaderNodeBsdfTransparent")
    mix = n.new("ShaderNodeMixShader")
    l.new(amount, mix.inputs[0])
    l.new(clear.outputs[0], mix.inputs[1])
    l.new(frost.outputs[0], mix.inputs[2])
    shader = mix.outputs[0]
    if ice is not None:
        glaze = n.new("ShaderNodeBsdfPrincipled")   # 再凍結した厚い氷:白く濁った、でこぼこの透明な層
        glaze.inputs["Base Color"].default_value = (0.82, 0.88, 0.94, 1)
        glaze.inputs["Roughness"].default_value = 0.12
        glaze.inputs["Transmission Weight"].default_value = 0.55
        glaze.inputs["IOR"].default_value = 1.31
        lump = node("ShaderNodeTexNoise", Scale=30.0, Detail=10.0, Roughness=0.7)
        l.new(vec, lump.inputs["Vector"])
        b2 = node("ShaderNodeBump", Strength=0.9, Distance=0.003)
        l.new(lump.outputs["Fac"], b2.inputs["Height"])
        l.new(b2.outputs["Normal"], glaze.inputs["Normal"])
        cloudy = math_("ADD", math_("MULTIPLY", lump.outputs["Fac"], 0.6), 0.45, clamp=True)
        mix2 = n.new("ShaderNodeMixShader")
        l.new(math_("MULTIPLY", ice, cloudy), mix2.inputs[0])
        l.new(shader, mix2.inputs[1])
        l.new(glaze.outputs[0], mix2.inputs[2])
        shader = mix2.outputs[0]
    l.new(shader, out.inputs["Surface"])
    return mat, ctrl


def key_value(socket, frame, value, interp="BEZIER"):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    socket.default_value = value
    socket.keyframe_insert("default_value", frame=frame)


# ---------------------------------------------------------------- フロントガラス
def surface_mesh(name, offset=0.0, u_range=(-1, 1), v_range=(0, 1), nu=NU, nv=NV):
    """フロントガラス面(を法線方向に offset ずらした面)のメッシュ。UV は (u, v) を 0〜1 にしたもの。"""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    grid = []
    for j in range(nv + 1):
        v = v_range[0] + (v_range[1] - v_range[0]) * j / nv
        row = []
        for i in range(nu + 1):
            u = u_range[0] + (u_range[1] - u_range[0]) * i / nu
            p = np.array(ws_point(u, v)) + offset * ws_normal(u, v)
            row.append((bm.verts.new(p), ((u + 1) / 2, v)))
        grid.append(row)
    for j in range(nv):
        for i in range(nu):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            f = bm.faces.new([a for a, _ in q])
            for loop, (_, uv) in zip(f.loops, q):
                loop[uv_layer].uv = uv
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for p in me.polygons:
        p.use_smooth = True
    return obj


def glass_material(name="Glass", tint=(0.86, 0.95, 0.92)):
    """フロントガラス:わずかに緑がかった透明。周囲に黒いセラミックの帯(黒セラ)。"""
    mat = principled(name, tint, rough=0.0, transmission=1.0, ior=1.52)
    n, l = mat.node_tree.nodes, mat.node_tree.links
    b = n["Principled BSDF"]
    uv = n.new("ShaderNodeUVMap")
    sep = n.new("ShaderNodeSeparateXYZ")
    l.new(uv.outputs["UV"], sep.inputs["Vector"])
    edge = None
    for comp, lo in (("X", True), ("X", False), ("Y", True), ("Y", False)):
        m = n.new("ShaderNodeMath")
        m.operation = "SUBTRACT"
        if lo:
            l.new(sep.outputs[comp], m.inputs[0])
            m.inputs[1].default_value = 0.0
        else:
            m.inputs[0].default_value = 1.0
            l.new(sep.outputs[comp], m.inputs[1])
        w = 0.035 if comp == "X" else (0.07 if lo else 0.06)
        g = n.new("ShaderNodeMath")
        g.operation = "LESS_THAN"
        g.inputs[1].default_value = w
        l.new(m.outputs[0], g.inputs[0])
        if edge is None:
            edge = g.outputs[0]
        else:
            mx = n.new("ShaderNodeMath")
            mx.operation = "MAXIMUM"
            l.new(edge, mx.inputs[0])
            l.new(g.outputs[0], mx.inputs[1])
            edge = mx.outputs[0]
    black = n.new("ShaderNodeBsdfPrincipled")
    black.inputs["Base Color"].default_value = (0.01, 0.01, 0.012, 1)
    black.inputs["Roughness"].default_value = 0.08
    mix = n.new("ShaderNodeMixShader")
    l.new(edge, mix.inputs[0])
    l.new(b.outputs[0], mix.inputs[1])
    l.new(black.outputs[0], mix.inputs[2])
    l.new(mix.outputs[0], n["Material Output"].inputs["Surface"])
    return mat


def windshield(frost_mat=None):
    glass = surface_mesh("Windshield")
    s = glass.modifiers.new("thick", "SOLIDIFY")
    s.thickness, s.offset = 0.005, -1.0
    assign(glass, glass_material())
    frost = None
    if frost_mat is not None:
        frost = surface_mesh("Frost", offset=0.0015)
        assign(frost, frost_mat)
    return glass, frost


# ---------------------------------------------------------------- 車体
STATIONS = [  # (y, 半幅, 下端 z, 上端 z) 前から後ろへ
    (-2.32, 0.70, 0.36, 0.62), (-2.27, 0.80, 0.30, 0.70), (-2.18, 0.86, 0.27, 0.76), (-1.95, 0.89, 0.26, 0.81),
    (-1.60, 0.90, 0.25, 0.85), (-1.20, 0.90, 0.25, 0.89), (-0.85, 0.90, 0.25, 0.945),
    (-0.58, 0.90, 0.25, 0.985), (0.30, 0.91, 0.25, 1.0), (1.30, 0.91, 0.25, 1.02), (1.90, 0.89, 0.27, 1.03),
    (2.20, 0.84, 0.32, 0.99), (2.33, 0.72, 0.40, 0.90),
]
WHEELS = [(-1.38, 0.33), (1.42, 0.33)]   # (y, 半径)


def car_paint(color=(0.015, 0.04, 0.11), frost_top=0.0):
    """メタリック塗装+クリア層。frost_top>0 なら、上を向いた面(ボンネット・屋根)にうっすら霜。"""
    mat = principled("Paint", color, rough=0.32, coat=1.0)
    n, l = mat.node_tree.nodes, mat.node_tree.links
    b = n["Principled BSDF"]
    b.inputs["Metallic"].default_value = 0.65
    b.inputs["Coat Roughness"].default_value = 0.03
    flake = n.new("ShaderNodeTexNoise")
    flake.inputs["Scale"].default_value = 2500.0
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    l.new(flake.outputs["Fac"], bump.inputs["Height"])
    l.new(bump.outputs["Normal"], b.inputs["Normal"])
    if frost_top:
        geo = n.new("ShaderNodeNewGeometry")
        sep = n.new("ShaderNodeSeparateXYZ")
        l.new(geo.outputs["Normal"], sep.inputs["Vector"])
        up = n.new("ShaderNodeMapRange")
        up.inputs["From Min"].default_value, up.inputs["From Max"].default_value = 0.55, 0.85
        l.new(sep.outputs["Z"], up.inputs["Value"])
        noise = n.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 300.0
        noise2 = n.new("ShaderNodeTexNoise")
        noise2.inputs["Scale"].default_value = 3.0
        mul = n.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        l.new(up.outputs["Result"], mul.inputs[0])
        mul.inputs[1].default_value = frost_top
        mul2 = n.new("ShaderNodeMath")
        mul2.operation, mul2.use_clamp = "MULTIPLY_ADD", True
        l.new(noise.outputs["Fac"], mul2.inputs[0])
        mul2.inputs[1].default_value = 0.9
        l.new(noise2.outputs["Fac"], mul2.inputs[2])
        mul3 = n.new("ShaderNodeMath")
        mul3.operation, mul3.use_clamp = "MULTIPLY", True
        l.new(mul.outputs[0], mul3.inputs[0])
        l.new(mul2.outputs[0], mul3.inputs[1])
        rime = n.new("ShaderNodeBsdfPrincipled")
        rime.inputs["Base Color"].default_value = (0.85, 0.89, 0.94, 1)
        rime.inputs["Roughness"].default_value = 0.6
        mix = n.new("ShaderNodeMixShader")
        l.new(mul3.outputs[0], mix.inputs[0])
        l.new(b.outputs[0], mix.inputs[1])
        l.new(rime.outputs[0], mix.inputs[2])
        l.new(mix.outputs[0], n["Material Output"].inputs["Surface"])
    return mat


def _ring(W, zb, zt):
    half = [(W * 0.85, zb), (W, zb + 0.12), (W, zt - 0.22 * (zt - zb)), (W * 0.99, zt - 0.06), (W * 0.95, zt - 0.02),
            (W * 0.8, zt), (W * 0.4, zt + 0.012), (0.0, zt + 0.016)]
    full = [(0.0, zb)] + half + [(-x, z) for x, z in reversed(half[:-1])]
    return full


def body(paint):
    bm = bmesh.new()
    rings = []
    for y, W, zb, zt in STATIONS:
        rings.append([bm.verts.new((x, y, z)) for x, z in _ring(W, zb, zt)])
    n = len(rings[0])
    for a, b_ in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([a[i], a[j], b_[j], b_[i]])
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("Body")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("Body", me)
    bpy.context.scene.collection.objects.link(obj)
    sub = obj.modifiers.new("sub", "SUBSURF")
    sub.levels = sub.render_levels = 2
    smooth(obj)
    assign(obj, paint)
    for k, (wy, r) in enumerate(WHEELS):   # タイヤハウスをくり抜く
        cut = cyl(f"Arch{k}", r + 0.06, 2.4, (0, wy, r), paint, rot=(0, math.radians(90), 0))
        cut.hide_render = True
        cut.hide_viewport = True
        m = obj.modifiers.new(f"arch{k}", "BOOLEAN")
        m.object, m.operation = cut, "DIFFERENCE"
    return obj


def _quad_strip(name, a_pts, b_pts, mat, thick=0.02):
    bm = bmesh.new()
    A = [bm.verts.new(p) for p in a_pts]
    B = [bm.verts.new(p) for p in b_pts]
    for i in range(len(A) - 1):
        bm.faces.new([A[i], A[i + 1], B[i + 1], B[i]])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    if thick:
        s = obj.modifiers.new("t", "SOLIDIFY")
        s.thickness = thick
    smooth(obj)
    assign(obj, mat)
    return obj


def car(scene, paint=None, frost_mat=None, side_frost=None, interior=True, wipers=True):
    """車一式。戻り値: dict(glass, frost, body, wipers, root)。root を動かすと車ごと動く。"""
    paint = paint or car_paint()
    before = set(bpy.data.objects)
    parts = {}
    parts["body"] = body(paint)
    parts["glass"], parts["frost"] = windshield(frost_mat)
    tint = principled("SideGlass", (0.25, 0.28, 0.3), rough=0.0, transmission=0.85, ior=1.5)
    trim = principled("BlackTrim", (0.012, 0.012, 0.014), rough=0.35)
    # Aピラー(フロントガラスの横の柱):ガラスの縁と、側面の窓の前端を結ぶ帯
    for s in (-1, 1):
        vs = np.linspace(0, 1, 12)
        a = [np.array(ws_point(s * 1.0, v)) + 0.004 * ws_normal(s * 1.0, v) for v in vs]
        b = [(s * (0.9 - 0.24 * v), -0.47 + 0.85 * v, 0.995 + 0.39 * v) for v in vs]
        _quad_strip(f"APillar{s}", a, b, paint)
        # 側面の窓
        glass_pts = [(s * 0.895, -0.40, 1.0), (s * 0.895, 1.86, 1.03), (s * 0.67, 1.32, 1.395), (s * 0.67, 0.36, 1.385)]
        _quad_strip(f"SideWin{s}", glass_pts[:2], [glass_pts[3], glass_pts[2]], side_frost or tint, thick=0.004)
        cyl(f"BPillar{s}", 0.03, 0.42, (s * 0.79, 0.62, 1.2), trim, rot=(math.radians(-6), s * math.radians(-30), 0))
        cyl(f"CPillar{s}", 0.05, 0.72, (s * 0.77, 1.62, 1.22), paint, rot=(math.radians(-52), s * math.radians(-17), 0))
        # ドアミラー
        m = box(f"Mirror{s}", (0.2, 0.08, 0.12), (s * 1.0, -0.28, 1.1), paint, bevel=0.03)
        box(f"MirrorArm{s}", (0.1, 0.04, 0.03), (s * 0.92, -0.25, 1.04), trim)
    # カウル(ガラスの下の黒い樹脂の帯。ワイパーの根元がある)
    vs = np.linspace(-1, 1, 24)
    a = [np.array(ws_point(u, 0.0)) + np.array((0, 0, 0.004)) for u in vs]
    b = [(u * 0.74, -0.63, 0.985) for u in vs]
    _quad_strip("Cowl", a, b, principled("CowlPlastic", (0.02, 0.02, 0.022), rough=0.55), thick=0.004)
    roof = box("Roof", (1.36, 1.16, 0.05), (0, 0.79, 1.41), paint, bevel=0.03)
    _quad_strip("RearWin", [(-0.64, 1.33, 1.395), (0.64, 1.33, 1.395)], [(-0.86, 1.93, 1.03), (0.86, 1.93, 1.03)],
                side_frost or tint, thick=0.004)
    # 前後の灯火類・グリル・ナンバー
    lens = principled("HeadLens", (0.95, 0.97, 1.0), rough=0.02, transmission=0.9)
    for s in (-1, 1):
        box(f"Head{s}", (0.32, 0.06, 0.1), (s * 0.58, -2.22, 0.72), lens, bevel=0.02)
        box(f"HeadIn{s}", (0.28, 0.02, 0.07), (s * 0.58, -2.2, 0.72), metal(f"Reflector{s}", (0.9, 0.9, 0.9), rough=0.1, brushed=False))
        box(f"Tail{s}", (0.34, 0.05, 0.1), (s * 0.6, 2.28, 0.86), glow(f"TailGlow{s}", (0.9, 0.02, 0.01), 0.6), bevel=0.015)
    box("Grille", (0.7, 0.05, 0.18), (0, -2.25, 0.5), trim, bevel=0.02)
    plate = principled("Plate", (0.92, 0.92, 0.9), rough=0.4)
    box("PlateF", (0.34, 0.02, 0.17), (0, -2.33, 0.42), plate, bevel=0.01)
    box("PlateR", (0.34, 0.02, 0.17), (0, 2.36, 0.58), plate, bevel=0.01)
    # 車輪
    rubber = principled("Tire", (0.02, 0.02, 0.022), rough=0.75)
    add_bump(rubber, scale=40, strength=0.2)
    rim = metal("Rim", (0.75, 0.76, 0.78), rough=0.18, brushed=False)
    parts["wheels"] = []
    for wy, r in WHEELS:
        for s in (-1, 1):
            t = cyl(f"Tire{wy}{s}", r, 0.21, (s * 0.8, wy, r), rubber, rot=(0, math.radians(90), 0), bevel=0.05)
            rr = cyl(f"Rim{wy}{s}", r * 0.62, 0.02, (s * 0.905, wy, r), rim, rot=(0, math.radians(90), 0), bevel=0.01)
            parts["wheels"].append(t)
    if interior:
        dash = principled("Dash", (0.03, 0.03, 0.032), rough=0.6)
        add_bump(dash, scale=300, strength=0.15)
        box("Dashboard", (1.6, 0.5, 0.14), (0, -0.15, 0.99), dash, bevel=0.04)
        box("CabinFloor", (1.7, 2.1, 0.02), (0, 0.85, 1.035), principled("Carpet", (0.04, 0.04, 0.045), rough=0.9))
        seat = principled("Seat", (0.06, 0.06, 0.065), rough=0.7)
        for s in (-1, 1):
            box(f"SeatBack{s}", (0.5, 0.12, 0.3), (s * 0.4, 0.62, 1.15), seat, bevel=0.05)
            box(f"Headrest{s}", (0.24, 0.09, 0.12), (s * 0.4, 0.65, 1.33), seat, bevel=0.03)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.18, minor_radius=0.018, location=(-0.4, -0.02, 1.15),
                                         rotation=(math.radians(62), 0, 0))
        wheel = bpy.context.active_object
        smooth(wheel)
        assign(wheel, trim)
    parts["wipers"] = wiper_set(trim) if wipers else []
    root = bpy.data.objects.new("CarRoot", None)
    scene.collection.objects.link(root)
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root:
            o.parent = root
    parts["root"] = root
    return parts


# ---------------------------------------------------------------- ワイパー
WIPER_PIVOTS = [(-0.62, 0.62), (0.08, 0.64)]   # (根元の u, ブレードの長さ m)


def wiper(name, pivot_u, length, mat, rubber_mat=None, angle_deg=0.0):
    """ワイパー1本。root(根元の空)を法線まわりに回すと動く。ブレードはガラスに沿って u 方向に寝ている。"""
    piv = np.array(ws_point(pivot_u, -0.02)) + 0.016 * ws_normal(pivot_u, 0.02)
    n = ws_normal(pivot_u, 0.08)
    root = bpy.data.objects.new(name, None)
    root.location = piv
    bpy.context.scene.collection.objects.link(root)
    # ローカル座標:x=ガラスに沿って横、z=法線
    zx = np.array(n)
    xx = np.array([1.0, 0.0, 0.0])
    xx = xx - zx * xx.dot(zx)
    xx /= np.linalg.norm(xx)
    yx = np.cross(zx, xx)
    import mathutils
    root.rotation_euler = mathutils.Matrix([xx, yx, zx]).transposed().to_euler()
    swing = bpy.data.objects.new(name + "Swing", None)   # これを z 軸(ガラスの法線)まわりに回すとワイパーが動く
    bpy.context.scene.collection.objects.link(swing)
    swing.parent = root
    cap = cyl(name + "Cap", 0.022, 0.035, (0, 0, 0), mat)
    cap.parent = swing
    arm = box(name + "Arm", (length * 0.95, 0.014, 0.01), (length * 0.48, 0.07, 0.01), mat, bevel=0.003)
    arm.parent = swing
    blade = box(name + "Blade", (length, 0.016, 0.013), (length * 0.5, 0.08, 0.0), mat, bevel=0.004)
    blade.parent = swing
    rubber = box(name + "Rubber", (length * 0.98, 0.006, 0.009), (length * 0.5, 0.08, -0.01), rubber_mat or mat)
    rubber.parent = swing
    return swing, arm, blade, rubber


def wiper_set(mat):
    out = []
    for k, (pu, ln) in enumerate(WIPER_PIVOTS):
        out.append(wiper(f"Wiper{k}", pu, ln, mat))
    return out


def surface_z(x, y, z_from=3.0):
    """真上から光線を当てて、車体などの表面の高さを調べる(小物をボンネットに置くとき用)。"""
    import mathutils
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = scene.ray_cast(dg, mathutils.Vector((x, y, z_from)), mathutils.Vector((0, 0, -1)))
    return loc.z if hit else 0.0


# ---------------------------------------------------------------- ヒビ
def crack_paths(seed, origin_xy, n_main=4, length=(0.25, 0.6), step=0.008, branch=0.07, dirs=None):
    """ガラス面上(横 X・斜面方向 Y [m])に枝分かれするヒビ。戻り値: [(点の列, 始まる時刻, 終わる時刻), ...]、時刻は 0〜1。"""
    rnd = random.Random(seed)
    out = []

    def walk(p, ang, L, t0, depth):
        pts = [p]
        x, y = p
        steps = max(2, int(L / step))
        for k in range(steps):
            ang += rnd.gauss(0, 0.22)
            x += step * math.cos(ang)
            y += step * math.sin(ang)
            u, v = to_uv(x, y)
            if abs(u) > 0.97 or v < 0.03 or v > 0.97:
                break
            pts.append((x, y))
            if depth < 2 and rnd.random() < branch:
                walk((x, y), ang + rnd.choice([-1, 1]) * rnd.uniform(0.4, 1.0), L * rnd.uniform(0.15, 0.4),
                     t0 + (k / steps) * (L / length[1]) * 0.6, depth + 1)
        if len(pts) > 2:
            dur = (len(pts) * step / length[1]) * 0.6
            out.append((pts, t0, t0 + dur, depth))

    for i in range(n_main):
        ang = dirs[i] if dirs else rnd.uniform(0, math.tau)
        walk(origin_xy, ang, rnd.uniform(*length), 0.0, 0)
    return out


def crack_curves(scene, paths, start_frame, frames_total, radius=0.0009, offset=0.0026, name="Crack"):
    """ヒビをガラス面の上の細い線として作り、伸びていくようにキーフレームを打つ。"""
    mat = principled("CrackMat", (0.95, 0.97, 1.0), rough=0.15, emission=0.35, emission_color=(0.9, 0.95, 1.0))
    objs = []
    for k, (pts, t0, t1, depth) in enumerate(paths):
        data = bpy.data.curves.new(f"{name}{k}", "CURVE")
        data.dimensions = "3D"
        data.bevel_depth = radius * (1.0 if depth == 0 else 0.7 if depth == 1 else 0.5)
        data.bevel_resolution = 1
        data.bevel_factor_mapping_end = "SPLINE"
        sp = data.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p, (X, Y) in zip(sp.points, pts):
            u, v = to_uv(X, Y)
            q = np.array(ws_point(u, v)) + offset * ws_normal(u, v)
            p.co = (*q, 1.0)
        obj = bpy.data.objects.new(f"{name}{k}", data)
        scene.collection.objects.link(obj)
        obj.data.materials.append(mat)
        f0 = start_frame + t0 * frames_total
        f1 = start_frame + t1 * frames_total
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
        data.bevel_factor_end = 0.0
        data.keyframe_insert("bevel_factor_end", frame=max(0.0, f0))
        data.bevel_factor_end = 1.0
        data.keyframe_insert("bevel_factor_end", frame=max(f0 + 1, f1))
        objs.append(obj)
    return objs


def surface_curve(scene, name, uv_pts, radius, mat, offset=0.002, order=3):
    """ガラス面に沿うチューブ(水の筋など)。"""
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = radius
    data.bevel_resolution = 3
    data.bevel_factor_mapping_end = "SPLINE"
    sp = data.splines.new("NURBS")
    sp.points.add(len(uv_pts) - 1)
    for p, (u, v) in zip(sp.points, uv_pts):
        q = np.array(ws_point(u, v)) + offset * ws_normal(u, v)
        p.co = (*q, 1.0)
    sp.order_u = order
    sp.use_endpoint_u = True
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def water_material(name="Water"):
    mat = principled(name, (0.95, 0.98, 1.0), rough=0.02, transmission=1.0, ior=1.33)
    add_bump(mat, scale=25, strength=0.25)
    return mat
