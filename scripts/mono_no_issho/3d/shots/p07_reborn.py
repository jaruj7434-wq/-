"""P07 / カット(生まれ変わり): 無地のスタジオ。中央の白い台にペレットの山。そこから粒が渦を巻いて
舞い上がり、左に新しい透明ボトル、中央上に透明な卵パック、右にたたんだTシャツが、下から形になりながら
(光る境目のディゾルブ+拡大)浮かび上がる。分解図のように3つが山の上に並んで、ゆっくり回る。5秒。

キー: 8〜38 ボトル / 22〜52 卵パック / 36〜66 Tシャツ が山から上がって形になる。以降ゆっくり浮遊。
屈折するのはボトルと卵パックの2つだけ(軽い)。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from mathutils import Vector
import common as C
import props as P
import factory_parts as F
import pet_parts2 as Q

FRAMES = 120
RISE = 30
PILE_R = 15.0
PILE_K = 0.6
PILE_TOP = Vector((0, 0, 3.0 + PILE_K * PILE_R - 1.0))
TARGETS = {   # name: (開始フレーム, 最終位置, 最終回転(度), 現れる軸, 軸の範囲)
    "bottle": (8, Vector((-40, 2, 34)), (0, -6, 0), "Z", (-1.0, 22.5)),
    "carton": (22, Vector((0, 14, 51)), (40, 0, 16), "X", (-17.0, 17.0)),
    "shirt": (36, Vector((40, 2, 34)), (58, 0, -14), "Y", (-16.0, 16.0)),
}


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def ease_out(u):
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def rise_keys(obj, start, target, rot_deg, center_off, bob_phase, final_scale=1.0):
    """山の頂上から target へ弧を描いて上がり、拡大・回転。到着後はゆっくり浮遊。
    center_off: オブジェクト原点から見た見た目の中心(拡大の基準を中心に見せるため)。"""
    fr = list(range(1, FRAMES + 1))
    L, R, S = [], [], []
    for f in fr:
        u = (f - start) / RISE
        e = ease(u); s = (0.08 + 0.92 * ease_out(u)) * final_scale
        if u <= 0:
            s = 0.0
        pos = PILE_TOP.lerp(target, e) + Vector((0, 0, 12 * math.sin(math.pi * min(1, max(0, u)))))
        t_after = max(0.0, f - start - RISE)
        pos += Vector((0, 0, 1.2 * math.sin(0.09 * t_after + bob_phase) * min(1, t_after / 10)))
        spin = math.radians(-150) * (1 - ease_out(u)) + math.radians(0.35) * t_after
        rx, ry, rz = (math.radians(a) for a in rot_deg)
        # 見た目の中心が pos に来るよう、原点をずらす(回転は無視できる程度の近似)
        off = Vector(center_off) * s
        L.append(tuple(pos - off)); R.append((rx, ry, rz + spin)); S.append((s, s, s))
    Q.bake_keys(obj, "location", fr, L, "LINEAR")
    Q.bake_keys(obj, "rotation_euler", fr, R, "LINEAR")
    Q.bake_keys(obj, "scale", fr, S, "LINEAR")


def key_reveal(sock, start, lo, hi):
    fr = list(range(1, FRAMES + 1))
    vals = []
    for f in fr:
        u = (f - start - 4) / (RISE - 2)
        vals.append(lo - 3 + (hi - lo + 6) * ease(u))
    nt = sock.node.id_data
    for f, v in zip(fr, vals):
        sock.default_value = v
        sock.keyframe_insert("default_value", frame=f)
    F.set_interp(nt, "LINEAR")


def swarm(rnd, mesh_list, start, target, n=70, prefix="Sw"):
    """山の表面から target へ渦を巻いて飛び、小さくなって吸い込まれるペレット群。"""
    fr = list(range(1, FRAMES + 1))
    for i in range(n):
        th = rnd.uniform(0, math.tau); rho = PILE_R * math.sqrt(rnd.uniform(0.0, 0.7))
        p0 = Vector((rho * math.cos(th), rho * math.sin(th), 3.0 + PILE_K * (PILE_R - rho)))
        t0 = start - 4 + rnd.uniform(0, 18); dur = rnd.uniform(12, 20)
        swirl = rnd.uniform(4, 9); ph = rnd.uniform(0, math.tau); turns = rnd.uniform(0.8, 1.6)
        e0 = [rnd.uniform(0, 6) for _ in range(3)]; w = [rnd.uniform(-0.6, 0.6) for _ in range(3)]
        L, R, S = [], [], []
        for f in fr:
            u = (f - t0) / dur
            if u <= 0 or u >= 1:
                L.append(tuple(p0)); R.append(tuple(e0)); S.append((0, 0, 0) if u >= 1 else (1, 1, 1))
                continue
            e = ease(u)
            base = p0.lerp(target, e) + Vector((0, 0, 10 * math.sin(math.pi * u)))
            a = ph + turns * math.tau * u
            r = swirl * math.sin(math.pi * u)
            p = base + Vector((r * math.cos(a), r * math.sin(a), 0))
            s = 1.0 if u < 0.6 else max(0.0, 1 - (u - 0.6) / 0.4)
            L.append(tuple(p)); R.append(tuple(e0[k] + w[k] * (f - t0) for k in range(3))); S.append((s, s, s))
        o = Q.linked(mesh_list[i % len(mesh_list)], f"{prefix}{i:03d}")
        Q.bake_keys(o, "location", fr, L); Q.bake_keys(o, "rotation_euler", fr, R); Q.bake_keys(o, "scale", fr, S)


def build(sc):
    rnd = random.Random(7)
    P.world_studio((0.03, 0.035, 0.04), (0.14, 0.17, 0.19), (0.85, 0.9, 0.95), 1.0, camera_color=(0.05, 0.07, 0.08))

    # --- 台とペレットの山(静止)
    ped_m = C.principled("Pedestal", (0.3, 0.36, 0.38), rough=0.3, coat=0.5)
    P.cyl("Pedestal", 21, 3.0, (0, 0, 1.5), mat=ped_m, verts=96, bevel=0.6)
    P.cyl("PedestalBase", 23, 1.0, (0, 0, -0.5), mat=C.principled("PedBase", (0.1, 0.12, 0.13), rough=0.4), verts=96)
    pel_mats = [Q.mat_pellet(f"Pel{i}", t, translucent=0.35) for i, t in
                enumerate(((0.88, 0.93, 0.91), (0.80, 0.90, 0.93), (0.93, 0.95, 0.93)))]
    pm = []
    for i in range(6):
        me = Q.pellet_mesh(f"PelMesh{i}", r=0.36 * rnd.uniform(0.9, 1.1), length=0.55 * rnd.uniform(0.85, 1.15))
        me.materials.append(pel_mats[i % 3]); pm.append(me)
    coll = Q.instance_collection("PilePel", pm, pel_mats)
    core_m = Q.mat_pile_core("Core", (0.75, 0.8, 0.78), scale=4)
    Q.growing_pile("Pile", coll, len(pm), (0, 0, 3.0), lambda f: PILE_R + 0.02 * (f + 100), (-300, -100),
                   k=PILE_K, density=5.0, shell=1.2, seed=8, core_mat=core_m, r_core_in=1.2)

    # --- 3つの生まれ変わり先
    reveal = {}
    # ボトル(空・キャップ付き・ラベルなし)
    bm = Q.bottle_meshes()
    clear = Q.mat_clear_pet("BottlePET", rough=0.02)
    cap_m = C.principled("CapM", (0.92, 0.93, 0.94), rough=0.35)
    parts = Q.make_bottle("Bottle", (0, 0, 0), [clear], cap_mat=cap_m, meshes=bm)
    bottle = parts[0]
    reveal["bottle"] = [Q.add_reveal(clear, "Z", coord_obj=bottle), Q.add_reveal(cap_m, "Z", coord_obj=bottle)]
    # 卵パック
    egg_m = Q.mat_clear_pet("EggPET", tint=(0.95, 0.97, 1.0), rough=0.04, thickness=0.07)
    tray, lid = Q.egg_carton("Carton", egg_m)
    reveal["carton"] = [Q.add_reveal(egg_m, "X", noise_amt=0.8, coord_obj=tray)]
    # Tシャツ
    jer = Q.mat_jersey("Jersey", (0.05, 0.17, 0.36))
    neck_m = Q.mat_jersey("JerseyNeck", (0.015, 0.04, 0.08))
    shirt, sparts = Q.tshirt("Shirt", jer)
    sparts[-1].data.materials.append(neck_m)
    reveal["shirt"] = [Q.add_reveal(jer, "Y", noise_amt=0.8, coord_obj=shirt), Q.add_reveal(neck_m, "Y", noise_amt=0.8, coord_obj=shirt)]

    centers = {"bottle": (0, 0, 10.5), "carton": (0, 0, 0), "shirt": (0, 0, 0)}
    objs = {"bottle": bottle, "carton": tray, "shirt": shirt}
    for k, (st, tgt, rot, axis, rng) in TARGETS.items():
        rise_keys(objs[k], st, tgt, rot, centers[k], bob_phase=len(k), final_scale=1.3 if k == "bottle" else 1.0)
        for sock in reveal[k]:
            key_reveal(sock, st, *rng)
        swarm(rnd, pm, st, tgt, n=80, prefix=f"Sw{k}")

    # --- 分解図の引き出し線(山の頂上→各オブジェクト。上がるのに合わせて伸びる)
    line_m = C.emissive("LeaderM", (0.55, 0.85, 1.0), strength=0.5)
    for k, (st, tgt, rot, axis, rng) in TARGETS.items():
        d = tgt - PILE_TOP
        ln = P.cyl(f"Leader_{k}", 0.07, 1.0, (0, 0, 0.5), mat=line_m, verts=8)
        ln.data.transform(__import__("mathutils").Matrix.Translation((0, 0, 0.5)))
        ln.location = PILE_TOP + Vector((0, 0, 1)); ln.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        ln.visible_shadow = False
        L = d.length * 0.62
        fr = list(range(1, FRAMES + 1))
        Q.bake_keys(ln, "scale", fr, [(1, 1, max(0.0, L * ease((f - st - 6) / (RISE + 6))) ) for f in fr], "LINEAR")

    # --- 照明: 大きなキー(左上前)・左右後ろのリム(透明な縁を光らせる)・上
    k = C.area_light((-220, -260, 200), (0, 0, 0), 200, 1.1e6, (1.0, 0.98, 0.95), "Key"); C.light_look_at(k, (0, 0, 30))
    r1 = C.area_light((-240, 220, 120), (0, 0, 0), 120, 1.6e6, (0.8, 0.92, 1.0), "RimL"); C.light_look_at(r1, (-20, 0, 45))
    r2 = C.area_light((250, 200, 90), (0, 0, 0), 120, 1.6e6, (1.0, 0.95, 0.9), "RimR"); C.light_look_at(r2, (20, 0, 40))
    t = C.area_light((0, 0, 300), (0, 0, 0), 160, 2.5e5, (1, 1, 1), "Top"); C.light_look_at(t, (0, 0, 0))
    P.light_card("CardL", (260, 200), (-320, -60, 100), (0, 0, 40), strength=2.5)
    P.light_card("CardR", (200, 260), (300, -160, 140), (0, 0, 40), strength=1.5)
    P.reflection_probe((0, 0, 40), radius=400, clip_start=1)

    cam, tgt = C.camera((0, -210, 55), (0, 0, 32), lens=50, fstop=0.06)
    cam.data.dof.focus_object = None; cam.data.dof.focus_distance = 205
    P.key_seq(cam, "location", [(1, (10, -222, 58)), (FRAMES, (-6, -192, 50))])
    Q.backdrop(cam, top=(0.05, 0.13, 0.17), bottom=(0.01, 0.025, 0.035), glow=(0.10, 0.24, 0.30), glow_center=(0.5, 0.6),
               glow_radius=0.55)
    sc.view_settings.exposure = 0.0


if __name__ == "__main__":
    C.EPISODE = "ep03"
    C.run_shot("p07_reborn", build, FRAMES)
