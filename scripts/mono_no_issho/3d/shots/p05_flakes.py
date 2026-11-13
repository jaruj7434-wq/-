"""P05 / カット(フレーク): リサイクル工場。ステンレスのホッパーの口から、砕いたPETフレーク
(透明・水色の不規則な薄片)がひらひら回りながら舞い落ち、下のトレーの山に積もっていく。5秒。

軽量化: 落ちるフレークは 260 個を使い回し(着地→斜面を少し滑って沈む→口の中へ戻る)、毎フレーム位置をキー。
山はジオメトリノードのインスタンス(約1万個)で、表面付近だけ表示しながら円錐が少しずつ大きくなる。
屈折ガラスは使わず、光沢+Translucent の不透明マテリアル。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P
import factory_parts as F
import pet_parts2 as Q

FRAMES = 120
LIP_Z = 50.0                 # ホッパー下の口(下端)
CHUTE = 16.0                 # 口の内寸
PILE_K = 0.62                # 山の傾き(高さ/半径)
PILE_Z = 1.2                 # トレー底
N_FALL = 520
FLAKE = 1.9                  # フレークの大きさ(cm)。実物より少し大きめにして読ませる
TINTS = [((0.78, 0.89, 0.98), 0.45), ((0.55, 0.78, 0.97), 0.45), ((0.35, 0.62, 0.92), 0.4),
         ((0.92, 0.96, 0.98), 0.5), ((0.50, 0.82, 0.62), 0.4)]
TINT_W = [5, 5, 3, 3, 1]


def r_pile(f):
    return 14.0 + 4.5 * (f - 1) / (FRAMES - 1)


def surf_z(x, y, f):
    return PILE_Z + max(0.0, PILE_K * (r_pile(f) - math.hypot(x, y)))


def flake_tracks(rnd, n, fps=24.0):
    """各フレークの毎フレームの (位置, 回転, 大きさ)。着地→滑って沈む→消えて口に戻る、を繰り返す。"""
    frames = list(range(1, FRAMES + 1))
    tracks = []
    for i in range(n):
        loc = {}; rot = {}; scl = {}
        t = rnd.uniform(-40, 0)                       # 最初の出現(プレロールで定常状態から始める)
        while t < FRAMES + 1:
            x0, y0 = rnd.uniform(-CHUTE / 2 + 1, CHUTE / 2 - 1), rnd.uniform(-CHUTE / 2 + 1, CHUTE / 2 - 1)
            z0 = LIP_Z + rnd.uniform(3, 9)
            ang = rnd.uniform(0, math.tau); spread = abs(rnd.gauss(0, 5.0))
            xl, yl = x0 * 1.3 + spread * math.cos(ang), y0 * 1.0 + spread * math.sin(ang) * 0.8
            vt = rnd.uniform(110, 170)
            e0 = [rnd.uniform(0, math.tau) for _ in range(3)]
            w = [rnd.uniform(-14, 14) for _ in range(3)]
            fl_a, fl_w, fl_p = rnd.uniform(0.6, 2.2), rnd.uniform(9, 16), rnd.uniform(0, math.tau)
            # 落下時間の見込み(山頂の高さまで)
            T = 0.0; z = z0
            while z > surf_z(xl, yl, t) and T < 2:
                T += 1 / fps; z, _ = Q.drag_fall(z0, -40.0, T, vt)
            T = max(T, 0.15)
            f = int(math.ceil(t)); landed = None
            while f < FRAMES + 1:
                te = (f - t) / fps
                if landed is None:
                    s = min(1.0, te / T)
                    z, _ = Q.drag_fall(z0, -40.0, te, vt)
                    fl = fl_a * s * math.sin(fl_w * te + fl_p)
                    x = x0 + (xl - x0) * s + fl * math.cos(ang + 1.3)
                    y = y0 + (yl - y0) * s + fl * math.sin(ang + 1.3)
                    zs = surf_z(x, y, f)
                    if z <= zs + 0.3:
                        landed = (f, x, y)
                        z = zs + 0.3
                    if 1 <= f <= FRAMES:
                        loc[f] = (x, y, z); rot[f] = tuple(e0[k] + w[k] * te for k in range(3)); scl[f] = 1.0
                else:
                    lf, lx, ly = landed
                    u = (f - lf) / 10.0
                    if u > 1:
                        break
                    rr = math.hypot(lx, ly) + 1e-3
                    d = 2.5 * u                                # 斜面を外へ少し滑る
                    x, y = lx + d * lx / rr, ly + d * ly / rr
                    z = surf_z(x, y, f) + 0.3 - 1.2 * u * u   # だんだん沈む
                    if 1 <= f <= FRAMES:
                        az = math.atan2(y, x)
                        loc[f] = (x, y, z); rot[f] = (0.3 * math.sin(i), math.atan(PILE_K), az); scl[f] = 1.0
                f += 1
            t = f + rnd.uniform(0, 3)
        L, R, S = [], [], []
        last_r = (0, 0, 0)
        for f in frames:
            if f in loc:
                L.append(loc[f]); R.append(rot[f]); S.append((1, 1, 1)); last_r = rot[f]
            else:
                L.append((0, 0, LIP_Z + 20)); R.append(last_r); S.append((0, 0, 0))
        tracks.append((frames, L, R, S))
    return tracks


def build(sc):
    rnd = random.Random(5)
    F.world_gradient(top=(0.55, 0.58, 0.62), horizon=(0.06, 0.065, 0.07), bottom=(0.03, 0.03, 0.03),
                     strength=1.0, camera_color=(0.03, 0.035, 0.04), strips=6.0)
    steel, grey, blue = Q.plant_hall()

    # --- ホッパー(角錐台)+口の短いダクト+フランジ、支柱
    Q.frustum("Hopper", (110, 110), (CHUTE + 0.8, CHUTE + 0.8), 150, LIP_Z + 16, mat=steel, wall=0.6)
    Q.frustum("Chute", (CHUTE + 0.8, CHUTE + 0.8), (CHUTE + 0.8, CHUTE + 0.8), LIP_Z + 16, LIP_Z, mat=steel, wall=0.6)
    P.box("Flange", (CHUTE + 5, CHUTE + 5, 1.2), (0, 0, LIP_Z + 16), mat=steel, bevel=0.3)
    P.box("LipBand", (CHUTE + 3, CHUTE + 3, 2.0), (0, 0, LIP_Z + 1.0), mat=steel, bevel=0.3)
    inner = C.principled("ChuteInner", (0.02, 0.02, 0.022), rough=0.6)
    P.box("ChuteDark", (CHUTE - 0.5, CHUTE - 0.5, 0.2), (0, 0, LIP_Z + 14), mat=inner)   # 口の奥を暗く
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box(f"Leg{sx}{sy}", (7, 7, 160), (sx * 95, sy * 62 + 35, 80), mat=blue, bevel=0.4)
    P.box("BeamF", (196, 6, 8), (0, -27, 148), mat=blue, bevel=0.4)
    P.box("BeamB", (196, 6, 8), (0, 97, 148), mat=blue, bevel=0.4)
    # --- 受けトレー
    P.open_box("Tray", (110, 90, 4.5), (0, 0, 2.25), wall=1.0, mat=F.mat_painted("TrayM", (0.2, 0.22, 0.24), rough=0.45, wear=0.15, scale=0.05), bevel=0.3)

    # --- フレークの部品とマテリアル
    mats = [Q.mat_flake(f"Flake{i}", t, translucent=tr) for i, (t, tr) in enumerate(TINTS)]
    meshes = [Q.flake_mesh(f"FlakeMesh{i}", rnd, size=FLAKE) for i in range(10)]
    # 山用: メッシュ×色の組み合わせ(30種)
    pile_meshes = []
    for i in range(30):
        me = meshes[i % 10].copy(); me.name = f"PileFlake{i}"
        me.materials.clear(); me.materials.append(rnd.choices(mats, TINT_W)[0])
        pile_meshes.append(me)
    coll = Q.instance_collection("PileFlakes", pile_meshes, mats)
    core_m = Q.mat_pile_core("PileCore", (0.55, 0.72, 0.85), scale=2.0)
    pile, core, win = Q.growing_pile("FlakePile", coll, len(pile_meshes), (0, 0, PILE_Z), r_pile, (1, FRAMES),
                                     k=PILE_K, density=4.0, shell=1.3, seed=3, flat=1.0, core_mat=core_m, r_core_in=1.6)
    print(f"[p05] pile points={len(pile.data.vertices)} visible@mid={win}")

    # --- 落ちるフレーク
    tracks = flake_tracks(rnd, N_FALL)
    fall_meshes = []
    for i in range(20):
        me = meshes[i % 10].copy(); me.name = f"FallFlake{i}"
        me.materials.clear(); me.materials.append(rnd.choices(mats, TINT_W)[0])
        fall_meshes.append(me)
    for i, (fr, L, R, S) in enumerate(tracks):
        o = Q.linked(fall_meshes[i % len(fall_meshes)], f"Fall{i:03d}")
        Q.bake_keys(o, "location", fr, L); Q.bake_keys(o, "rotation_euler", fr, R); Q.bake_keys(o, "scale", fr, S)

    # --- 照明: 工場の天井光(上)+左前のキー+右奥のリム(落ちるフレークがきらめく)+山へのスポット
    top = C.area_light((0, 10, 260), (0, 0, 0), 120, 2.5e5, (0.92, 0.96, 1.0), "Top"); C.light_look_at(top, (0, 0, 0))
    key = C.area_light((-170, -180, 110), (0, 0, 0), 120, 3.0e5, (1.0, 0.97, 0.92), "Key"); C.light_look_at(key, (0, 0, 25))
    rim = C.area_light((150, 160, 80), (0, 0, 0), 80, 4.0e5, (0.8, 0.9, 1.0), "Rim"); C.light_look_at(rim, (0, 0, 30))
    rim2 = C.area_light((-160, 150, 60), (0, 0, 0), 80, 2.5e5, (0.85, 0.92, 1.0), "Rim2"); C.light_look_at(rim2, (0, 0, 25))
    F.spot((40, -120, 160), (0, 0, 5), 6e4, color=(1.0, 0.96, 0.9), size_deg=35, blend=0.6, radius=10, name="PileSpot")
    P.light_card("Card", (200, 120), (60, -200, 120), (0, 0, 30), strength=1.5)
    P.reflection_probe((0, 0, 40), radius=300, clip_start=1)

    cam, tgt = C.camera((0, -160, 34), (0, 0, 24), lens=54, fstop=0.016)
    cam.data.dof.focus_object = None; cam.data.dof.focus_distance = 160
    P.key_seq(cam, "location", [(1, (-12, -170, 36)), (FRAMES, (6, -150, 32))])
    P.key_seq(tgt, "location", [(1, (0, 0, 25.5)), (FRAMES, (0, 0, 24))])
    sc.view_settings.exposure = 0.3
    sc.view_settings.look = "AgX - Medium High Contrast"


if __name__ == "__main__":
    C.EPISODE = "ep03"
    C.run_shot("p05_flakes", build, FRAMES)
