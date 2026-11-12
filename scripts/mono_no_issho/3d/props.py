"""モノの一生 3Dショット用の追加部品(小道具・他の硬貨・形状ユーティリティ)。

common.py には手を入れず、ここに追加の補助関数を置く。単位は common と同じ 1BU=1cm。
"""
import math, random

import bmesh
import bpy
from mathutils import Vector

import common as C

# 日本の硬貨: 半径cm, 厚さcm, 穴半径cm, 色, 粗さ
COINS = {
    "1":   dict(r=1.000, t=0.15, hole=0.0,  color=None),
    "5":   dict(r=1.100, t=0.15, hole=0.25, color=(0.80, 0.58, 0.26), rough=0.32),   # 黄銅
    "10":  dict(r=1.175, t=0.15, hole=0.0,  color=(0.62, 0.33, 0.20), rough=0.40),   # 青銅
    "50":  dict(r=1.050, t=0.17, hole=0.20, color=(0.80, 0.79, 0.76), rough=0.28),   # 白銅
    "100": dict(r=1.130, t=0.17, hole=0.0,  color=(0.80, 0.79, 0.76), rough=0.26),   # 白銅
    "500": dict(r=1.300, t=0.18, hole=0.0,  color=(0.82, 0.74, 0.52), rough=0.28),   # ニッケル黄銅
}


def mat_alloy(name, color, rough=0.3, tarnish=0.25):
    """硬貨用の金属マテリアル(模様なし・面に微細な凹凸と粗さムラ、縁は少し明るい)。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    p = n.new("ShaderNodeBsdfPrincipled")
    p.inputs["Metallic"].default_value = 1.0
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 40; nz.inputs["Detail"].default_value = 10
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    rr = n.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough * 0.6; rr.inputs["To Max"].default_value = rough * 1.5
    C.link(nt, nz.outputs["Fac"], rr.inputs["Value"]); C.link(nt, rr.outputs["Result"], p.inputs["Roughness"])
    dz = n.new("ShaderNodeTexNoise"); dz.inputs["Scale"].default_value = 3; dz.inputs["Detail"].default_value = 5
    C.link(nt, tc.outputs["Object"], dz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.4; cr.color_ramp.elements[0].color = (*color, 1)
    d = 1 - tarnish
    cr.color_ramp.elements[1].position = 0.8
    cr.color_ramp.elements[1].color = (color[0] * d, color[1] * d * 0.95, color[2] * d * 0.9, 1)
    C.link(nt, dz.outputs["Fac"], cr.inputs["Fac"]); C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    # 面の浮き彫り感(ランダムな凹凸を薄く)
    vz = n.new("ShaderNodeTexNoise"); vz.inputs["Scale"].default_value = 5; vz.inputs["Detail"].default_value = 3
    C.link(nt, tc.outputs["Object"], vz.inputs["Vector"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.12; b.inputs["Distance"].default_value = 0.01
    C.link(nt, vz.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


_MATS = {}


def coin_mat(kind):
    if kind == "1":
        return bpy.data.materials.get("CoinShared") or C.mat_coin("CoinShared")
    if kind not in _MATS or _MATS[kind].name not in bpy.data.materials:
        s = COINS[kind]
        _MATS[kind] = mat_alloy(f"Coin{kind}", s["color"], s["rough"])
    return _MATS[kind]


def make_any_coin(kind="1", name=None, location=(0, 0, 0), rotation=(0, 0, 0), verts=40):
    """任意の硬貨(1/5/10/50/100/500)。穴あき硬貨はブーリアンで穴を開ける(物理は円柱のまま)。"""
    s = COINS[kind]
    name = name or f"Coin{kind}"
    if kind == "1":
        return C.make_coin(name, coin_mat("1"), location, rotation, verts=verts)
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=s["r"], depth=s["t"], location=location, rotation=rotation)
    c = bpy.context.object; c.name = name
    # 縁(リム)を少し盛り上げる: 上下面を内側にインセットして凹ませる
    bm = bmesh.new(); bm.from_mesh(c.data)
    caps = [f for f in bm.faces if abs(f.normal.z) > 0.9]
    bmesh.ops.inset_individual(bm, faces=caps, thickness=0.09, use_even_offset=True)
    for f in caps:
        for v in f.verts:
            v.co.z -= 0.012 * (1 if v.co.z > 0 else -1)
    bm.to_mesh(c.data); bm.free()
    if s["hole"]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=s["hole"], depth=1, location=location, rotation=rotation)
        h = bpy.context.object
        bo = c.modifiers.new("hole", "BOOLEAN"); bo.object = h; bo.operation = "DIFFERENCE"; bo.solver = "EXACT"
        bpy.context.view_layer.objects.active = c
        bpy.ops.object.modifier_apply(modifier="hole")
        bpy.data.objects.remove(h, do_unlink=True)
    bev = c.modifiers.new("bev", "BEVEL"); bev.width = 0.02; bev.segments = 2; bev.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = c
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    c.data.materials.clear()
    c.data.materials.append(coin_mat(kind))
    for poly in c.data.polygons:
        poly.material_index = 0
    return c


def scatter_mixed(n, center=(0, 0, 0), radius=4.0, seed=1, weights=None, tilt=0.15, prefix="S", verts=40,
                  exclude=None):
    """混在硬貨を平面にばらまく(静的)。weights={"1":5,"10":2,...}。exclude(x,y)->True で除外。"""
    rnd = random.Random(seed)
    weights = weights or {"1": 5, "5": 1, "10": 2, "50": 1, "100": 2}
    kinds = list(weights); w = [weights[k] for k in kinds]
    out = []
    tries = 0
    while len(out) < n and tries < n * 20:
        tries += 1
        r = radius * math.sqrt(rnd.random()); a = rnd.uniform(0, math.tau)
        x, y = center[0] + r * math.cos(a), center[1] + r * math.sin(a)
        if exclude and exclude(x, y):
            continue
        k = rnd.choices(kinds, w)[0]
        rot = (rnd.uniform(-tilt, tilt), rnd.uniform(-tilt, tilt), rnd.uniform(0, math.tau))
        if rnd.random() < 0.5:
            rot = (rot[0] + math.pi, rot[1], rot[2])
        z = center[2] + COINS[k]["t"] / 2 + 0.02 + len(out) * 0.004
        out.append(make_any_coin(k, f"{prefix}{len(out)}", (x, y, z), rot, verts=verts))
    return out


# ------------------------------------------------------------------ 形状
def add_mod(obj, kind, **kw):
    m = obj.modifiers.new(kind.lower(), kind)
    for k, v in kw.items():
        setattr(m, k, v)
    return m


def box(name, size, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, bevel=0.0, segments=3):
    """直方体(size=(x,y,z) フルサイズ)。bevel>0 で角を丸める。"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        add_mod(o, "BEVEL", width=bevel, segments=segments, limit_method="ANGLE")
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    if mat:
        o.data.materials.append(mat)
    return o


def cyl(name, r, depth, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, verts=48, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    if bevel:
        add_mod(o, "BEVEL", width=bevel, segments=3, limit_method="ANGLE")
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    if mat:
        o.data.materials.append(mat)
    return o


def open_box(name, size, loc=(0, 0, 0), wall=0.3, mat=None, bevel=0.1, rot=(0, 0, 0), remove="top"):
    """上面の無い箱(トレー・引き出し・小銭入れ)。size は外寸。"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bm = bmesh.new(); bm.from_mesh(o.data)
    ax = {"top": (2, 1), "front": (1, -1)}[remove]
    dead = [f for f in bm.faces if f.normal[ax[0]] * ax[1] > 0.9]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(o.data); bm.free()
    add_mod(o, "SOLIDIFY", thickness=wall, offset=-1, use_even_offset=True)
    if bevel:
        add_mod(o, "BEVEL", width=bevel, segments=3, limit_method="ANGLE")
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    if mat:
        o.data.materials.append(mat)
    return o


def plane(name, size, loc=(0, 0, 0), rot=(0, 0, 0), mat=None):
    """size: スカラーまたは (x, y)。rot は度。"""
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=tuple(math.radians(a) for a in rot))
    o = bpy.context.object; o.name = name
    if isinstance(size, (int, float)):
        size = (size, size)
    o.scale = (size[0], size[1], 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        o.data.materials.append(mat)
    return o


def light_card(name, size, loc, target, strength=5.0, color=(1, 1, 1), visible_camera=False):
    """反射用の発光板(金属に映り込む明るい面)。カメラには映さない。"""
    o = plane(name, size, loc, mat=C.emissive(name + "M", color, strength=strength))
    d = Vector(target) - Vector(loc)
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.visible_camera = visible_camera
    o.visible_shadow = False
    return o


def mat_wood(name, base=(0.30, 0.18, 0.09), dark=(0.16, 0.09, 0.04), scale=0.15, rough=0.45):
    """木目(引き伸ばしたノイズの縞)。scale は 1cm あたりの縞の細かさ。木目は X 方向に流れる。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale * 0.04, scale, scale)
    C.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 12; nz.inputs["Distortion"].default_value = 0.6
    C.link(nt, mp.outputs["Vector"], nz.inputs["Vector"])
    wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "Y"
    wv.inputs["Scale"].default_value = 1.2; wv.inputs["Distortion"].default_value = 8
    wv.inputs["Detail"].default_value = 3
    C.link(nt, mp.outputs["Vector"], wv.inputs["Vector"])
    mx = n.new("ShaderNodeMix"); mx.data_type = "FLOAT"; mx.inputs["Factor"].default_value = 0.35
    C.link(nt, nz.outputs["Fac"], mx.inputs["A"]); C.link(nt, wv.outputs["Fac"], mx.inputs["B"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.3; cr.color_ramp.elements[0].color = (*dark, 1)
    cr.color_ramp.elements[1].position = 0.7; cr.color_ramp.elements[1].color = (*base, 1)
    C.link(nt, mx.outputs["Result"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled")
    rr = n.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough * 0.8; rr.inputs["To Max"].default_value = rough * 1.2
    C.link(nt, mx.outputs["Result"], rr.inputs["Value"]); C.link(nt, rr.outputs["Result"], p.inputs["Roughness"])
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.05
    C.link(nt, mx.outputs["Result"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def mat_leather(name, color=(0.20, 0.09, 0.04), grain=3.0, rough=0.45):
    """シボのある革。grain は 1cm あたりのシボの数。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    vz = n.new("ShaderNodeTexVoronoi"); vz.inputs["Scale"].default_value = grain
    C.link(nt, tc.outputs["Object"], vz.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6; nz.inputs["Detail"].default_value = 4
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (color[0] * 0.6, color[1] * 0.6, color[2] * 0.6, 1)
    cr.color_ramp.elements[1].color = (color[0] * 1.3, color[1] * 1.25, color[2] * 1.2, 1)
    C.link(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled")
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = rough * 0.7; rr.inputs["To Max"].default_value = rough * 1.3
    C.link(nt, vz.outputs["Distance"], rr.inputs["Value"]); C.link(nt, rr.outputs["Result"], p.inputs["Roughness"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.35; b.inputs["Distance"].default_value = 0.03
    C.link(nt, vz.outputs["Distance"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def key_seq(obj, path, frames_values, interp="BEZIER"):
    for f, v in frames_values:
        C.key(obj, path, f, v)
    C.ease_all(obj, interp)


def drop_coins(kinds, center, spread, z0, z_step, seed=1, verts=40, prefix="D", friction=0.5, bounce=0.15,
               vel_xy=(0.0, 0.0), start_frame=None, stagger=0):
    """落下させる硬貨(リジッドボディ・アクティブ)を生成。stagger>0 なら start_frame から順にアニメ→物理へ切替。"""
    rnd = random.Random(seed)
    out = []
    for i, k in enumerate(kinds):
        loc = (center[0] + rnd.uniform(-spread, spread), center[1] + rnd.uniform(-spread, spread), z0 + i * z_step)
        rot = (rnd.uniform(0, math.tau), rnd.uniform(0, math.tau), rnd.uniform(0, math.tau))
        c = make_any_coin(k, f"{prefix}{i}", loc, rot, verts=verts)
        s = COINS[k]
        C.rigid(c, True, "CYLINDER", mass=s["r"] ** 2 * s["t"], friction=friction, bounce=bounce)
        out.append(c)
    return out


# ------------------------------------------------------------------ 物理
def physics(sc, frames, time_scale=1.0, substeps=40, iterations=30):
    """1BU=1cm なので重力を 981 BU/s^2 にする(既定の 9.81 だと 1/100 G でふわふわ落ちる)。"""
    rw = C.rigid_world(sc, frames, substeps)
    rw.solver_iterations = iterations
    rw.time_scale = time_scale
    sc.use_gravity = True
    sc.gravity = (0, 0, -981.0)
    return rw


def passive_mesh(obj, friction=0.6, bounce=0.1, margin=0.01):
    """モディファイア適用後の形状(FINAL)をメッシュ衝突に使う静的コライダー。"""
    rb = C.rigid(obj, False, "MESH", friction=friction, bounce=bounce, margin=margin)
    rb.mesh_source = "FINAL"
    return rb


def hold_then_release(obj, release_frame, path_keys=None, park=None):
    """release_frame まではアニメ(kinematic)で保持、以降は物理に任せる。
    path_keys=[(frame, location), ...] で保持中に動かすことも可(手から滑り落ちる等)。"""
    rb = obj.rigid_body
    if park is not None:  # 解放直前まで画面外に待機させ、解放1フレーム前に出現位置へ瞬間移動
        spawn = tuple(obj.location)
        # 瞬間移動の速度を物理に持ち込まないよう、出現後3フレーム静止してから解放
        path_keys = [(1, park), (release_frame - 4, park), (release_frame - 3, spawn), (release_frame, spawn)]
    if path_keys:
        for f, loc in path_keys:
            C.key(obj, "location", f, loc)
    else:
        obj.keyframe_insert("location", frame=1)
    obj.keyframe_insert("rotation_euler", frame=1)
    rb.kinematic = True; rb.keyframe_insert("kinematic", frame=1)
    rb.kinematic = True; rb.keyframe_insert("kinematic", frame=release_frame - 1)
    rb.kinematic = False; rb.keyframe_insert("kinematic", frame=release_frame)
    for fc in _fcurves(obj):
        if "kinematic" in fc.data_path or (park is not None and fc.data_path == "location"):
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


def _fcurves(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return []
    try:
        return list(ad.action.fcurves)
    except AttributeError:
        return [fc for layer in ad.action.layers for strip in layer.strips
                for bag in strip.channelbags for fc in bag.fcurves]


def settle(sc, frames=60, time_scale=1.0):
    """今あるリジッドボディを frames まで計算し、その姿勢で静止オブジェクトとして固定する
    (自然に積み重なった静物用)。物理ワールドは削除するので run_shot では焼かれない。"""
    physics(sc, max(frames, 2), time_scale=time_scale)
    bpy.ops.ptcache.bake_all(bake=True)
    sc.frame_set(frames)
    rb_objs = [o for o in sc.objects if o.rigid_body]
    mats = {o.name: o.matrix_world.copy() for o in rb_objs}
    bpy.ops.ptcache.free_bake_all()
    sc.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    for o in rb_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rb_objs[0] if rb_objs else None
    if rb_objs:
        bpy.ops.rigidbody.objects_remove()
    bpy.ops.rigidbody.world_remove()
    for o in rb_objs:
        o.matrix_world = mats[o.name]
        o.select_set(False)


def drop_pile(kinds, center, spread, z0, seed=1, verts=40, prefix="P", friction=0.5):
    """settle() 用: 重ならないよう縦に間隔を空けて硬貨を配置(リジッドボディ付き)。"""
    rnd = random.Random(seed)
    out = []
    for i, k in enumerate(kinds):
        loc = (center[0] + rnd.uniform(-spread, spread), center[1] + rnd.uniform(-spread, spread), z0 + i * 1.3)
        rot = (rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), rnd.uniform(0, math.tau))
        c = make_any_coin(k, f"{prefix}{i}", loc, rot, verts=verts)
        s = COINS[k]
        C.rigid(c, True, "CYLINDER", mass=s["r"] ** 2 * s["t"], friction=friction, bounce=0.1)
        out.append(c)
    return out


def reflection_probe(loc, radius=100.0, clip_start=0.5):
    """EEVEE の球面反射プローブ。金属の映り込みに周囲の物体・ライトカードを入れるため必須級
    (無いとスクリーン外は world しか映らず、硬貨が黒く見える)。"""
    bpy.ops.object.lightprobe_add(type="SPHERE", location=loc)
    o = bpy.context.object; o.name = "ReflProbe"
    o.data.influence_distance = radius
    o.data.clip_start = clip_start
    return o


def world_studio(bottom=(0.02, 0.02, 0.02), horizon=(0.08, 0.08, 0.08), top=(0.5, 0.5, 0.5), strength=1.0,
                 camera_color=None):
    """上方向が明るいグラデーションの world(部屋・空の映り込み代わり)。
    camera_color を渡すと、カメラから直接見える背景だけその色にする。"""
    w = bpy.data.worlds.new("WorldStudio")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree; n = nt.nodes; n.clear()
    out = n.new("ShaderNodeOutputWorld")
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ"); C.link(nt, tc.outputs["Generated"], sep.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    e = cr.color_ramp.elements
    e[0].position = 0.35; e[0].color = (*bottom, 1)
    e[1].position = 0.85; e[1].color = (*top, 1)
    mid = e.new(0.52); mid.color = (*horizon, 1)
    mr = n.new("ShaderNodeMapRange")  # Generated の Z は -1..1 → 0..1
    mr.inputs["From Min"].default_value = -1; mr.inputs["From Max"].default_value = 1
    C.link(nt, sep.outputs["Z"], mr.inputs["Value"]); C.link(nt, mr.outputs["Result"], cr.inputs["Fac"])
    bg = n.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = strength
    C.link(nt, cr.outputs["Color"], bg.inputs["Color"])
    final = bg.outputs["Background"]
    if camera_color is not None:
        lp = n.new("ShaderNodeLightPath")
        bg2 = n.new("ShaderNodeBackground"); bg2.inputs["Color"].default_value = (*camera_color, 1)
        mx = n.new("ShaderNodeMixShader")
        C.link(nt, lp.outputs["Is Camera Ray"], mx.inputs["Fac"])
        C.link(nt, final, mx.inputs[1]); C.link(nt, bg2.outputs["Background"], mx.inputs[2])
        final = mx.outputs["Shader"]
    C.link(nt, final, out.inputs["Surface"])
    return w
