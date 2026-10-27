"""カット5:血管の内部。赤血球が流れる中に針先が入り、唾液を注入し、血を吸い上げる。"""
import math
import random

import bpy  # bmesh より先に読み込む必要がある
import bmesh

from common import (add_bump, assign, camera, color_variation, curve_tube, key, light, principled,
                    red_blood_cell_mesh, reset_scene, smooth)

TUBE_R = 1.3
TIP = (0.1, 4.5, 0.3)  # 針先の位置


def seg_dist(p, a, b):
    """点 p と線分 ab の距離(2D)。"""
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay)))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def build(frames, saliva_at, suck_at):
    """saliva_at / suck_at: 唾液注入・吸い上げを始めるフレーム。"""
    random.seed(11)
    scene = reset_scene(frames)

    # --- 血管の壁 ---
    bpy.ops.mesh.primitive_cylinder_add(vertices=160, radius=TUBE_R, depth=36, location=(0, 15, 0),
                                        rotation=(math.radians(90), 0, 0), end_fill_type="NOTHING")
    wall = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(wall.data)
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1], cuts=120)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)  # 内側を表にする
    bm.to_mesh(wall.data)
    bm.free()
    smooth(wall)
    tex = bpy.data.textures.new("WallWobble", "CLOUDS")
    tex.noise_scale = 1.2
    d = wall.modifiers.new("wobble", "DISPLACE")
    d.texture, d.strength, d.mid_level = tex, 0.25, 0.5
    wall_mat = principled("Endothelium", (0.55, 0.10, 0.08), rough=0.35, sss=0.6,
                          sss_radius=(1.0, 0.25, 0.15), sss_scale=0.3, coat=0.6)
    color_variation(wall_mat, (0.45, 0.06, 0.05), (0.75, 0.22, 0.16), scale=1.5)
    add_bump(wall_mat, scale=7.0, strength=0.35, kind="voronoi", voronoi_feature="DISTANCE_TO_EDGE")
    add_bump(wall_mat, scale=25.0, strength=0.15)
    assign(wall, wall_mat)

    # --- 赤血球・血小板・白血球 ---
    rbc_mesh = red_blood_cell_mesh("RBC", R=0.26)
    rbc_mat = principled("RBC", (0.55, 0.03, 0.03), rough=0.3, sss=0.8, sss_radius=(1.0, 0.2, 0.1),
                         sss_scale=0.15, coat=0.4)
    add_bump(rbc_mat, scale=40, strength=0.05)
    rbc_mesh.materials.append(rbc_mat)
    cells = []
    for i in range(150):
        o = bpy.data.objects.new(f"rbc{i}", rbc_mesh)
        scene.collection.objects.link(o)
        r = TUBE_R * 0.8 * math.sqrt(random.random())
        a = random.uniform(0, math.tau)
        x, z = r * math.cos(a), r * math.sin(a)
        y0 = random.uniform(0.5, 30)
        if seg_dist((x, z), (0.0, -0.2), (TIP[0], TIP[2])) < 0.42:  # カメラと針先の間は空けておく
            continue
        speed = random.uniform(1.2, 1.8) * (1.1 - (r / TUBE_R) ** 2)  # 中心ほど速い
        rot0 = [random.uniform(0, math.tau) for _ in range(3)]
        spin = [random.uniform(-2.5, 2.5) for _ in range(3)]
        cells.append((o, x, y0, z, speed, rot0, spin))

    plt_mat = principled("Platelet", (0.85, 0.7, 0.55), rough=0.5, sss=0.5, sss_scale=0.05)
    wbc_mat = principled("WBC", (0.9, 0.85, 0.8), rough=0.45, sss=0.9, sss_radius=(1, 0.9, 0.8), sss_scale=0.2)
    add_bump(wbc_mat, scale=14, strength=0.6, detail=8)
    extras = []
    for i in range(25):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.07)
        o = bpy.context.active_object
        o.scale = (1, 1, 0.45)
        smooth(o)
        assign(o, plt_mat)
        extras.append(o)
    for i in range(2):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.42, segments=48, ring_count=24)
        o = bpy.context.active_object
        smooth(o)
        assign(o, wbc_mat)
        extras.append(o)
    for o in extras:
        r = TUBE_R * 0.7 * math.sqrt(random.random())
        a = random.uniform(0, math.tau)
        cells.append((o, r * math.cos(a), random.uniform(3, 30), r * math.sin(a), random.uniform(1.0, 1.4),
                      [random.uniform(0, math.tau) for _ in range(3)], [random.uniform(-1, 1) for _ in range(3)]))

    secs = frames / 24
    sucked = sorted(cells[:150], key=lambda c: (c[1] - TIP[0]) ** 2 + (c[2] - TIP[1] - 3) ** 2 + (c[3] - TIP[2]) ** 2)[:14]
    for o, x, y0, z, speed, rot0, spin in cells:
        if any(o is s[0] for s in sucked):
            continue
        key(o, "location", 1, (x, y0, z), "LINEAR")
        key(o, "location", frames, (x, y0 - speed * secs, z), "LINEAR")
        key(o, "rotation_euler", 1, rot0, "LINEAR")
        key(o, "rotation_euler", frames, [r + s * secs for r, s in zip(rot0, spin)], "LINEAR")

    # 吸い上げられる赤血球:流れに乗って近づき、吸い込み開始後に針先へ吸い寄せられて消える
    for k, (o, x, y0, z, speed, rot0, spin) in enumerate(sucked):
        y0 = TIP[1] + 1.5 + k * 0.45
        x, z = TIP[0] + random.uniform(-0.6, 0.6), TIP[2] + random.uniform(-0.6, 0.4)
        start = suck_at + k * 3
        y_start = y0 - speed * (start / 24)
        key(o, "location", 1, (x, y0, z), "LINEAR")
        key(o, "rotation_euler", 1, rot0, "LINEAR")
        key(o, "location", start, (x, y_start, z), "BEZIER")
        key(o, "rotation_euler", start, [r + s * start / 24 for r, s in zip(rot0, spin)], "BEZIER")
        key(o, "scale", start, (1, 1, 1), "BEZIER")
        key(o, "location", start + 16, (TIP[0] + 0.25, TIP[1] + 0.55, TIP[2] + 0.4), "BEZIER")
        key(o, "scale", start + 16, (0.0, 0.0, 0.0), "CONSTANT")

    # --- 針(上唇:血を吸う管)と下咽頭(唾液の管) ---
    chitin = principled("Chitin", (0.6, 0.36, 0.14), rough=0.22, sss=0.5, sss_radius=(1, 0.6, 0.3),
                        sss_scale=0.05, coat=0.8)
    add_bump(chitin, scale=60, strength=0.15)
    root = bpy.data.objects.new("NeedleRoot", None)
    scene.collection.objects.link(root)
    tip_dir = (0.25, 0.55, 0.4)  # 針の向き(先端→根元)
    pts = [(TIP[0] + tip_dir[0] * t * 6, TIP[1] + tip_dir[1] * t * 6, TIP[2] + tip_dir[2] * t * 6) for t in (0, 0.33, 0.66, 1)]
    labrum, _ = curve_tube(scene, "Labrum", pts, 0.16, chitin)
    labrum.data.use_fill_caps = False
    labrum.parent = root
    pts2 = [(p[0] - 0.2, p[1] + 0.08, p[2] + 0.02) for p in pts]
    hypo, _ = curve_tube(scene, "Hypopharynx", pts2, 0.06, chitin)
    hypo.parent = root
    # 壁の外から差し込まれる
    back = 1.6
    key(root, "location", 1, (tip_dir[0] * back, tip_dir[1] * back, tip_dir[2] * back), "BEZIER")
    key(root, "location", int(saliva_at * 0.6) + 1, (0, 0, 0), "BEZIER")

    # --- 唾液(緑の粒) ---
    sal_mat = principled("Saliva", (0.55, 1.0, 0.3), rough=0.2, emission=1.2, alpha=0.6)
    for i in range(140):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.008, 0.022),
                                              location=(TIP[0] - 0.2, TIP[1] + 0.08, TIP[2]))
        o = bpy.context.active_object
        smooth(o)
        assign(o, sal_mat)
        s = saliva_at + random.randint(0, 40)
        drift = (random.uniform(-0.7, 0.7), -random.uniform(0.2, 1.0), random.uniform(-0.6, 0.5))
        key(o, "scale", 1, (0, 0, 0), "CONSTANT")
        key(o, "scale", s, (0.01, 0.01, 0.01), "BEZIER")
        key(o, "location", s, o.location[:], "BEZIER")
        key(o, "scale", s + 10, (1, 1, 1), "BEZIER")
        key(o, "location", frames, (o.location.x + drift[0], o.location.y + drift[1] - 0.5 * (frames - s) / 24,
                                    o.location.z + drift[2]), "BEZIER")

    # --- カメラとライト ---
    cam, target = camera(scene, "Cam", (0.0, -1.2, -0.15), TIP, lens=26, fstop=1.4)
    target.location = TIP
    key(cam, "location", 1, (0.0, -1.6, -0.2), "BEZIER")
    key(cam, "location", frames, (-0.05, 2.2, -0.05), "BEZIER")
    light(scene, "POINT", "Endoscope", (0.3, -1.0, 0.5), 60, (1.0, 0.85, 0.75), size=0.3)
    key(bpy.data.objects["Endoscope"], "location", 1, (0.3, -1.4, 0.5), "BEZIER")
    key(bpy.data.objects["Endoscope"], "location", frames, (0.3, 2.4, 0.5), "BEZIER")
    light(scene, "POINT", "Deep", (0, 14, 0), 120, (1.0, 0.5, 0.35), size=1.0)
    light(scene, "POINT", "TipRim", (TIP[0] - 0.6, TIP[1] + 0.8, TIP[2] - 0.5), 10, (1.0, 0.9, 0.8), size=0.2)
    return scene
