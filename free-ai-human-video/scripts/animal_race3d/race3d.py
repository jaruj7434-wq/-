"""「40秒以内に6匹全員ゴールできる?」3Dの動物マーブルレース(Blender の剛体物理 + Cycles で描画)。

縦長の木のマーブルコースの塔。ガラス玉(中に動物)が6個、上のスタートから同時に転がり出す。
ジグザグの坂 → 回る風車 → ジャンプ台 → じょうご → 最後の坂とゴール。物理は Blender(Bullet)のまま、ねらい・補正なし。
制限時間内に6個すべてゴールすれば成功(天使)、間に合わなければ失敗(幽霊)。

使い方(Blender の Python モジュール bpy を入れた Python で実行):
    python race3d.py sim --seed N          # 物理だけ計算して結果を表示
    python race3d.py search -n 50          # たくさん計算して成功率を見る
    python race3d.py still --seed N --frame F   # 1コマだけ描画(確認用)
"""

import argparse
import json
import math
import os
import sys

import bpy
import numpy as np

FPS = 30
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 40.0))
N_BALLS = 6
# 選手:名前, 玉の半径(m)。大きさに差をつける(極小のハムスター〜特大のゴリラ)
RACERS = [("ハムスター", "hamster", 0.04), ("ウサギ", "rabbit", 0.08), ("ペンギン", "penguin", 0.11),
          ("柴犬", "shiba", 0.13), ("ブタ", "pig", 0.17), ("ゴリラ", "gorilla", 0.275)]
BALL_R = 0.13
LANE_W = 0.64          # 通路の内幅
WALL_H = 0.40
RAMP_L = 4.2
LEVEL_H = 1.5
DROP_GAP = 0.80        # 段の端の落ちる口の幅(いちばん大きい玉より広く)
SLOPE = math.radians(float(os.environ.get("SLOPE_DEG", 5.0)))
WINDMILLS = [(1, 0.55, 0.8), (2, 0.5, 1.0), (3, 0.4, 1.2)]   # (段, 段の中の位置, 速さの倍率)
BUMPS = [0.3, 0.5, 0.7]
COLORS = [(1, .55, .2), (.95, .95, .95), (.2, .2, .2), (1, .7, .8), (.2, .4, .9), (1, .6, .6)]

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "output", "race3d")


def box(name, loc, size, rot=(0, 0, 0), passive=True, mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if passive:
        bpy.ops.rigidbody.object_add()
        o.rigid_body.type = 'PASSIVE'
        o.rigid_body.collision_shape = 'BOX'
        o.rigid_body.friction = 0.6
        o.rigid_body.restitution = 0.2
        o.rigid_body.collision_margin = 0.002
    if mat:
        o.data.materials.append(mat)
    return o


def trough(name, x0, x1, z_hi, direction, mat, open_low=True):
    """x0→x1 の向きに下る通路(床と両側の壁)。direction=+1 なら右へ下る。"""
    L = abs(x1 - x0)
    cx = (x0 + x1) / 2
    ang = direction * SLOPE       # Y軸まわりの傾き(正の回転で +X 側が下がる)
    cz = z_hi - math.tan(SLOPE) * L / 2
    rot = (0, ang, 0)
    parts = [box(name + "_floor", (cx, 0, cz - 0.02), (L, LANE_W + 0.08, 0.04), rot, mat=mat)]
    # 奥は木のかべ。手前は低い木のふちだけ見せる(当たり判定の高いかべはカメラに写さない)
    parts.append(box(name + "_wall1", (cx, LANE_W / 2 + 0.02, cz + WALL_H / 2 - 0.02), (L, 0.04, WALL_H), rot, mat=mat))
    fw = box(name + "_wall-1", (cx, -(LANE_W / 2 + 0.02), cz + WALL_H / 2 - 0.02), (L, 0.04, WALL_H), rot)
    fw.visible_camera = False
    fw.visible_shadow = False
    parts.append(fw)
    lip = box(name + "_lip", (cx, -(LANE_W / 2 + 0.02), cz + 0.03), (L, 0.04, 0.07), rot, passive=False, mat=mat)
    parts.append(lip)
    return parts, cz


ACRYL = [None]


def wood_material():
    """木目のある木(手続きテクスチャ)。"""
    m = bpy.data.materials.new("wood")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.3, 1.5, 6.0)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Z'
    wave.inputs["Scale"].default_value = 3.0
    wave.inputs["Distortion"].default_value = 2.0
    wave.inputs["Detail"].default_value = 3.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.42, 0.24, 0.11, 1)
    ramp.color_ramp.elements[1].color = (0.72, 0.48, 0.26, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    return m


def acrylic_material():
    m = bpy.data.materials.new("acrylic")
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Transmission Weight"].default_value = 1.0
    p.inputs["Roughness"].default_value = 0.0
    p.inputs["IOR"].default_value = 1.2
    p.inputs["Base Color"].default_value = (0.95, 0.98, 1.0, 1)
    return m


def build(seed):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ACRYL[0] = acrylic_material()
    sc = bpy.context.scene
    sc.render.fps = FPS
    bpy.ops.rigidbody.world_add()
    rw = sc.rigidbody_world
    rw.substeps_per_frame = 20
    rw.solver_iterations = 30
    rng = np.random.default_rng(seed)

    wood = wood_material()

    info = {"levels": []}
    xl_list, xr_list = [], []
    z = 6.0
    xl, xr = -RAMP_L / 2, RAMP_L / 2
    n_levels = 5
    for i in range(n_levels):
        d = 1 if i % 2 == 0 else -1
        xl_list.append(xl)
        xr_list.append(xr)
        x0, x1 = (xl, xr) if d == 1 else (xr, xl)
        parts, cz = trough(f"ramp{i}", x0, x1, z, d, wood)
        # 高い方の端の壁(はね返り用)と、低い方の端の先の止め板
        box(f"back{i}", (x0 - d * 0.02, 0, z + 0.05), (0.04, LANE_W + 0.08, 0.3), mat=wood)
        z_low = z - math.tan(SLOPE) * RAMP_L
        # 落ちる所を囲う(止め板+両側のかべ。次の段の床まで)
        drop_h = LEVEL_H + 0.6
        box(f"stop{i}", (x1 + d * DROP_GAP, 0, z_low + 0.3 - drop_h / 2), (0.04, LANE_W + 0.08, drop_h), mat=wood)
        for sy in (-1, 1):
            box(f"drop{i}_{sy}", (x1 + d * DROP_GAP / 2, sy * (LANE_W / 2 + 0.02), z_low + 0.3 - drop_h / 2),
                (DROP_GAP + 0.1, 0.04, drop_h), mat=wood)
        info["levels"].append({"z_hi": z, "z_low": z_low, "dir": d})
        if i < n_levels - 1:
            z = z_low - LEVEL_H + 0.0
            # 次の段は少し外側から始める(落ちてきた玉を受ける)
            xl2, xr2 = (xl, xr + DROP_GAP) if d == 1 else (xl - DROP_GAP, xr)
            xl, xr = xl2, xr2
    # 風車:Y軸まわりに回る4枚の羽根(キネマティック)。段ごとに位置・向き・速さを変える
    import mathutils
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'   # 一定の速さで回す
    wind_speed = float(os.environ.get("WIND_DEG_S", 60))
    for wi, (lvl, fx, spd) in enumerate(WINDMILLS):
        lv = info["levels"][lvl]
        x_hi = xl_list[lvl] if lv["dir"] == 1 else xr_list[lvl]
        wx = x_hi + lv["dir"] * fx * RAMP_L
        wz = lv["z_hi"] - math.tan(SLOPE) * fx * RAMP_L + 0.66
        bpy.ops.object.empty_add(location=(wx, 0, wz))
        hub = bpy.context.object
        hub.name = f"windmill{wi}"
        for k in range(4):
            bl = box(f"blade{wi}_{k}", (0, 0, 0), (0.05, LANE_W - 0.06, 0.62), passive=False, mat=wood)
            bl.data.transform(mathutils.Matrix.Translation((0, 0, 0.31)))
            bl.rotation_euler = (0, k * math.pi / 2, 0)
            bpy.context.view_layer.objects.active = bl
            bpy.ops.rigidbody.object_add()
            bl.rigid_body.type = 'PASSIVE'
            bl.rigid_body.kinematic = True
            bl.rigid_body.collision_shape = 'MESH'
            bl.rigid_body.restitution = 0.4
            bl.parent = hub
            bl.location = (0, 0, 0)
        # 羽根は玉の進む向きと逆に回る(玉を押し戻す)
        sgn = -lv["dir"]
        ph = rng.uniform(0, math.pi / 2)
        hub.rotation_euler = (0, ph, 0)
        hub.keyframe_insert("rotation_euler", frame=1)
        hub.rotation_euler = (0, ph + sgn * math.radians(wind_speed * spd) * 60, 0)
        hub.keyframe_insert("rotation_euler", frame=1 + 60 * FPS)
    # でこぼこ(最後の段):低い横木を越えるたびに少し遅くなる
    lv = info["levels"][-1]
    x_hi = xl_list[-1] if lv["dir"] == 1 else xr_list[-1]
    for j, fx in enumerate(BUMPS):
        bx = x_hi + lv["dir"] * fx * RAMP_L
        bz = lv["z_hi"] - math.tan(SLOPE) * fx * RAMP_L + 0.02
        bz = lv["z_hi"] - math.tan(SLOPE) * fx * RAMP_L
        bpy.ops.mesh.primitive_cylinder_add(radius=0.022, depth=LANE_W, location=(bx, 0, bz),
                                            rotation=(math.radians(90), 0, 0), vertices=16)
        cyl = bpy.context.object
        cyl.name = f"bump{j}"
        bpy.ops.rigidbody.object_add()
        cyl.rigid_body.type = 'PASSIVE'
        cyl.rigid_body.collision_shape = 'CONVEX_HULL'
        cyl.rigid_body.friction = 0.6
        cyl.rigid_body.restitution = 0.2
        cyl.data.materials.append(wood)
    # ゴールの受け皿(最後の段の落ちる所の真下)
    last = info["levels"][-1]
    x_end = xr if last["dir"] == 1 else xl
    gx = x_end + last["dir"] * DROP_GAP / 2
    gz = last["z_low"] - 0.9
    box("goal_floor", (gx, 0, gz), (DROP_GAP + 0.6, LANE_W + 0.08, 0.06), mat=wood)
    info["goal"] = (gx - DROP_GAP / 2 - 0.3, gx + DROP_GAP / 2 + 0.3, gz)
    # 塔全体を前後の透明な板ではさむ(カメラには写らないが、玉は外に飛び出せない)
    zmin, zmax = gz - 0.3, info["levels"][0]["z_hi"] + 1.2
    cxmin, cxmax = min(xl_list) - DROP_GAP - 0.1, max(xr_list) + DROP_GAP + 0.1
    info["xrange"] = (cxmin, cxmax)
    for sy in (-1, 1):
        g = box(f"case{sy}", ((cxmin + cxmax) / 2, sy * (LANE_W / 2 + 0.05), (zmin + zmax) / 2),
                (cxmax - cxmin + 0.2, 0.02, zmax - zmin))
        g.visible_camera = False
        g.visible_shadow = False
    for sx, nm in ((cxmin - 0.04, "caseL"), (cxmax + 0.04, "caseR")):
        box(nm, (sx, 0, (zmin + zmax) / 2), (0.08, LANE_W + 0.12, zmax - zmin), mat=wood)
    # 玉
    def glass_mat(col):
        g = bpy.data.materials.new("glass")
        g.use_nodes = True
        p = g.node_tree.nodes["Principled BSDF"]
        p.inputs["Transmission Weight"].default_value = 1.0
        p.inputs["Roughness"].default_value = 0.02
        p.inputs["IOR"].default_value = 1.45
        p.inputs["Base Color"].default_value = (*col, 1)
        return g
    lv0 = info["levels"][0]
    balls = []
    order = rng.permutation(N_BALLS)   # スタートの並び順はシードごとにランダム
    xs = -RAMP_L / 2 + 0.1
    for k in order:
        rad = RACERS[k][2]
        x = xs + rad + rng.uniform(0, 0.03)
        xs = x + rad + 0.03
        zz = lv0["z_hi"] - math.tan(SLOPE) * (x + RAMP_L / 2) + rad + 0.03 + rng.uniform(0, 0.03)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rad, location=(x, rng.uniform(-0.05, 0.05), zz),
                                             segments=32, ring_count=16)
        o = bpy.context.object
        o.name = f"ball{k}"
        bpy.ops.object.shade_smooth()
        bpy.ops.rigidbody.object_add()
        o.rigid_body.collision_shape = 'SPHERE'
        o.rigid_body.mass = 0.3 * (rad / 0.13) ** 3   # 同じ密度:大きい玉ほど重い
        o.rigid_body.friction = 0.5
        o.rigid_body.restitution = 0.25
        o.rigid_body.angular_damping = 0.05
        o.rigid_body.linear_damping = 0.02
        o.rigid_body.use_deactivation = False
        o.data.materials.append(glass_mat(COLORS[k]))
        balls.append((k, o))
    balls = [o for _, o in sorted(balls, key=lambda t: t[0])]
    sc.frame_start = 1
    sc.frame_end = int((TIME_LIMIT + 6) * FPS)
    rw.point_cache.frame_end = sc.frame_end
    return info, balls


def simulate(seed):
    info, balls = build(seed)
    sc = bpy.context.scene
    track = []
    finish = [None] * N_BALLS
    for f in range(1, sc.frame_end + 1):
        sc.frame_set(f)
        pos = [tuple(b.matrix_world.translation) for b in balls]
        track.append(pos)
        t = (f - 1) / FPS
        for k, (x, y, z) in enumerate(pos):
            gx0, gx1, gz = info["goal"]
            if finish[k] is None and gx0 - 0.1 < x < gx1 + 0.1 and z < gz + 0.4:   # ゴールの受け皿に入った
                finish[k] = t
        if all(v is not None for v in finish):
            break
    ok = all(v is not None and v <= TIME_LIMIT for v in finish)
    return {"finish": finish, "success": ok, "track": track, "info": info}


def setup_look(info, res=(720, 1280), samples=24):
    """カメラ・光・背景(床と壁)を置く。"""
    sc = bpy.context.scene
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    cam.data.lens = 50
    cam.data.sensor_fit = 'VERTICAL'
    cam.location = (0.25, -26.0, 7.2)
    cam.rotation_euler = (math.radians(82), 0, 0)   # 少し上から見下ろす
    sc.camera = cam
    # 背景:明るいスタジオの床と奥のかべ
    floor_m = bpy.data.materials.new("studio")
    floor_m.use_nodes = True
    floor_m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.82, 0.86, 0.92, 1)
    floor_m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
    gz = info["goal"][2]
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, gz - 0.35))
    bpy.context.object.data.materials.append(floor_m)
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 4, 10), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(floor_m)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN'))
    sun.data.energy = 3.5
    sun.data.angle = math.radians(8)
    sun.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-20))
    sc.collection.objects.link(sun)
    area = bpy.data.objects.new("key", bpy.data.lights.new("key", 'AREA'))
    area.data.energy = 2500
    area.data.size = 8
    area.location = (-3, -8, 9)
    area.rotation_euler = (math.radians(45), 0, math.radians(-20))
    sc.collection.objects.link(area)
    sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.75, 0.82, 0.95, 1)
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.transmission_bounces = 6
    sc.cycles.glossy_bounces = 3
    sc.cycles.diffuse_bounces = 2
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = 'AgX'


PREP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "source", "race3d", "prep")


def add_animals():
    """玉の中に入れる動物(Higgs Field で作った3Dモデル)を読み込む。玉と一緒には回らず、いつも立ったまま。"""
    import mathutils
    animals = []
    for name_jp, key, rad in RACERS:
        bpy.ops.import_scene.gltf(filepath=os.path.join(PREP, key + ".glb"))
        o = [x for x in bpy.context.selected_objects if x.type == 'MESH'][0]
        o.rotation_mode = 'XYZ'
        s_ = 2 * rad * 0.78           # 玉の中にちょうど収まる大きさ
        o.scale = (s_, s_, s_)
        animals.append(o)
    return animals


def place_animals(balls, animals, prev=None):
    """動物を玉の中心に置く。顔はカメラの方へ向け、進む向きに少しだけ顔をふる。"""
    for k, (b, a) in enumerate(zip(balls, animals)):
        p = b.matrix_world.translation
        rad = RACERS[k][2]
        a.location = (p.x, p.y, p.z - rad * 0.05)
        vx = 0.0 if prev is None else (p.x - prev[k][0]) * FPS
        yaw = -math.pi / 2 + max(-0.6, min(0.6, vx * 0.25))   # 正面(−Y)を向き、進む方へ少し向く
        a.rotation_euler = (0, 0, yaw)


def still(seed, frame, path):
    info, balls = build(seed)
    setup_look(info)
    animals = add_animals()
    sc = bpy.context.scene
    prev = None
    for f in range(1, frame + 1):
        sc.frame_set(f)
        place_animals(balls, animals, prev)
        prev = [tuple(b.matrix_world.translation) for b in balls]
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("-n", type=int, default=20)
    ap.add_argument("--frame", type=int, default=1)
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
    if a.mode == "sim":
        r = simulate(a.seed)
        print(json.dumps({"finish": [None if v is None else round(v, 2) for v in r["finish"]], "success": r["success"]}))
    elif a.mode == "closeup":   # 動物の見え方の確認用:玉の近くにカメラを寄せる
        os.makedirs(OUT, exist_ok=True)
        info, balls = build(a.seed)
        setup_look(info)
        animals = add_animals()
        sc = bpy.context.scene
        prev = None
        for f in range(1, a.frame + 1):
            sc.frame_set(f)
            place_animals(balls, animals, prev)
            prev = [tuple(b.matrix_world.translation) for b in balls]
        zs = [b.matrix_world.translation for b in balls]
        c = sum((v for v in zs), __import__("mathutils").Vector()) / len(zs)
        sc.camera.location = (c.x, -6.5, c.z + 0.6)
        sc.camera.rotation_euler = (math.radians(84), 0, 0)
        import time
        t0 = time.time()
        sc.render.filepath = os.path.join(OUT, f"closeup_{a.seed}_{a.frame}.png")
        bpy.ops.render.render(write_still=True)
        print("描画", round(time.time() - t0, 1), "秒")
    elif a.mode == "still":
        os.makedirs(OUT, exist_ok=True)
        still(a.seed, a.frame, os.path.join(OUT, f"still_{a.seed}_{a.frame}.png"))
