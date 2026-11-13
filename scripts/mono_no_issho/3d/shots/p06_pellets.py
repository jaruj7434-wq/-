"""P06 / カット(ペレット): リサイクル工場。斜めのステンレスのシュートの口から、溶かして固めた
小さなペレット(乳白〜半透明の粒)が帯になって流れ落ち、下のステンレス容器の中で山になっていく。5秒。

軽量化: 流れる粒は 1000 個を使い回し(シュート内→放物線で落下→山の斜面を少し転がって沈む→シュート内へ戻る)、
毎フレーム位置をキー。山はジオメトリノードのインスタンスで、表面付近だけ表示しながら円錐が大きくなる。
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
G = 981.0
PILE_K = 0.65
PILE_Z = 1.0                     # 容器の底(内側)
BIN = (62.0, 48.0, 16.0)         # 容器の外寸
N_STREAM = 1000
CH_ANG = math.radians(38)        # シュートの下り角
CH_DIR = Vector((math.cos(CH_ANG), 0, -math.sin(CH_ANG)))
MOUTH = Vector((-19.0, 0.0, 60.0))   # シュート口の中心
CH_W = 8.0                       # シュート内寸
SPEED = 85.0                     # 口から出る速さ cm/s
TINTS = [((0.88, 0.93, 0.91), 0.4), ((0.80, 0.90, 0.92), 0.45), ((0.93, 0.95, 0.93), 0.35)]


def r_pile(f):
    # 最初は速く、だんだんゆっくり(体積が一定の割合で増える ≒ r^3 ∝ t)
    v0, v1 = 7.0 ** 3, 19.0 ** 3
    return max(0.0, v0 + (v1 - v0) * (f - 1) / (FRAMES - 1)) ** (1 / 3)


def surf_z(x, y, f):
    return PILE_Z + max(0.0, PILE_K * (r_pile(f) - math.hypot(x, y)))


def in_bin(x, y, margin=1.0):
    return abs(x) < BIN[0] / 2 - 1.5 - margin and abs(y) < BIN[1] / 2 - 1.5 - margin


def stream_tracks(rnd, n, fps=24.0):
    side = Vector((0, 1, 0)); up = CH_DIR.cross(side).normalized()
    frames = list(range(1, FRAMES + 1))
    out = []
    for i in range(n):
        loc = {}; rot = {}
        t = rnd.uniform(-30, 0)
        while t < FRAMES + 1:
            a, b = rnd.uniform(-CH_W / 2 + 0.6, CH_W / 2 - 0.6), rnd.uniform(-CH_W / 2 + 0.6, 0.5)
            back = rnd.uniform(3, 12)                       # シュート内の奥から出てくる
            p0 = MOUTH + side * a + up * b - CH_DIR * back
            v = CH_DIR * SPEED * rnd.uniform(0.9, 1.1) + Vector((rnd.gauss(0, 3), rnd.gauss(0, 3), 0))
            e0 = [rnd.uniform(0, math.tau) for _ in range(3)]
            w = [rnd.uniform(-20, 20) for _ in range(3)]
            t_mouth = back / (SPEED * 1.0)
            f = int(math.ceil(t)); landed = None
            while f < FRAMES + 1:
                te = (f - t) / fps
                if landed is None:
                    if te < t_mouth:
                        p = p0 + v.normalized() * SPEED * te
                    else:
                        tf = te - t_mouth
                        pm = p0 + v.normalized() * SPEED * t_mouth
                        p = pm + v * tf + Vector((0, 0, -0.5 * G * tf * tf))
                    zs = surf_z(p.x, p.y, f) if in_bin(p.x, p.y) else -100
                    if p.z <= zs + 0.25:
                        landed = (f, p.x, p.y)
                        p = Vector((p.x, p.y, zs + 0.25))
                    if 1 <= f <= FRAMES:
                        loc[f] = tuple(p); rot[f] = tuple(e0[k] + w[k] * te for k in range(3))
                    if p.z < -5:
                        break
                else:
                    lf, lx, ly = landed
                    u = (f - lf) / 9.0
                    if u > 1:
                        break
                    rr = math.hypot(lx, ly) + 1e-3
                    ang = math.atan2(ly, lx) + rnd.uniform(-0.3, 0.3)
                    d = (2.0 + 5.0 * ((i * 7919) % 100) / 100) * (1 - (1 - u) ** 2)   # 斜面を転がり、止まる
                    x, y = lx + d * math.cos(ang), ly + d * math.sin(ang)
                    if not in_bin(x, y):
                        x, y = lx, ly
                    z = surf_z(x, y, f) + 0.25 - 0.9 * u * u
                    if 1 <= f <= FRAMES:
                        loc[f] = (x, y, z); rot[f] = tuple(e0[k] + w[k] * 0.05 * u for k in range(3))
                f += 1
            t = f + rnd.uniform(0, 2)
        L, R, S = [], [], []
        last = (0, 0, 0)
        for f in frames:
            if f in loc:
                L.append(loc[f]); R.append(rot[f]); S.append((1, 1, 1)); last = rot[f]
            else:
                L.append(tuple(MOUTH - CH_DIR * 30)); R.append(last); S.append((0, 0, 0))
        out.append((frames, L, R, S))
    return out


def chute(steel):
    """斜めの角ダクト(断面 CH_W 角・上が開いた樋ではなく四方を囲う)。口から奥へ 160cm。"""
    length = 160.0
    c = MOUTH - CH_DIR * (length / 2)
    rot = (0, CH_ANG, 0)   # X 軸を CH_DIR に合わせる(Y 回りに +ang で x→(cos,0,-sin))
    outer = P.box("Chute", (length, CH_W + 1.2, CH_W + 1.2), tuple(c), rot, mat=steel, bevel=0.3)
    cut = P.box("ChuteCut", (length + 4, CH_W, CH_W), tuple(c + CH_DIR * 2), rot)
    bo = outer.modifiers.new("hollow", "BOOLEAN"); bo.object = cut; bo.solver = "EXACT"
    outer.modifiers.move(len(outer.modifiers) - 1, 0)
    cut.hide_render = True; cut.hide_viewport = True
    # 口の補強枠と、奥を暗くする板
    P.box("MouthRim", (2.0, CH_W + 3.0, CH_W + 3.0), tuple(MOUTH - CH_DIR * 1.0), rot, mat=steel, bevel=0.3)
    dark = C.principled("ChuteIn", (0.015, 0.015, 0.017), rough=0.7)
    P.box("ChuteDark", (0.3, CH_W - 0.2, CH_W - 0.2), tuple(MOUTH - CH_DIR * 16), rot, mat=dark)
    # 吊り金具
    P.box("Hanger", (3, 3, 120), tuple(MOUTH - CH_DIR * 60 + Vector((0, 0, 60))), mat=steel)
    return outer


def build(sc):
    rnd = random.Random(6)
    F.world_gradient(top=(0.55, 0.58, 0.62), horizon=(0.06, 0.065, 0.07), bottom=(0.03, 0.03, 0.03),
                     strength=1.0, camera_color=(0.03, 0.035, 0.04), strips=6.0)
    steel, grey, blue = Q.plant_hall()
    chute(steel)
    # 容器(ステンレス)と台車
    bin_m, _ = F.mat_steel("BinSteel", (0.22, 0.225, 0.235), rough=0.3, streak_axis="X")
    P.open_box("Bin", BIN, (0, 0, BIN[2] / 2 - 0.5), wall=1.5, mat=bin_m, bevel=0.4)
    P.box("BinBase", (BIN[0] + 4, BIN[1] + 4, 6), (0, 0, -3.5), mat=blue, bevel=0.5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.cyl(f"Caster{sx}{sy}", 3, 3, (sx * (BIN[0] / 2 - 4), sy * (BIN[1] / 2 - 4), -8), (math.radians(90), 0, 0),
                  mat=C.principled("CasterM", (0.03, 0.03, 0.03), rough=0.6), verts=16)
    # 左奥: 出荷待ちの白い袋(文字なし)を積んだパレット
    sack = F.mat_canvas("Sack", (0.78, 0.79, 0.77), weave=1.5, rough=0.85)
    P.box("Pallet", (120, 100, 12), (-200, 280, -5), mat=P.mat_wood("PalletWood", base=(0.22, 0.15, 0.09), dark=(0.12, 0.08, 0.05)))
    for i, (dx, dy, dz) in enumerate(((-25, -20, 0), (28, -18, 0), (-22, 26, 0), (30, 28, 0), (0, 0, 24), (-30, 5, 24))):
        P.box(f"Sack{i}", (52, 44, 24), (-200 + dx, 280 + dy, 13 + dz), (0, 0, math.radians(rnd.uniform(-6, 6))), mat=sack, bevel=5)
    # 床を下げる(台車の下)
    bpy.data.objects["Floor"].location.z = -11.0
    bpy.data.objects["Walk"].location.z = -10.85

    # ペレット
    mats = [Q.mat_pellet(f"Pellet{i}", t, translucent=tr) for i, (t, tr) in enumerate(TINTS)]
    pm = []
    for i in range(6):
        me = Q.pellet_mesh(f"PelletMesh{i}", r=0.24 * rnd.uniform(0.9, 1.1), length=0.38 * rnd.uniform(0.85, 1.15))
        me.materials.append(mats[i % len(mats)])
        pm.append(me)
    coll = Q.instance_collection("PilePellets", pm, mats)
    core_m = Q.mat_pile_core("PileCore", (0.7, 0.76, 0.74), scale=6.0)
    clip = lambda x, y: ~((abs(x) < BIN[0] / 2 - 1.8) & (abs(y) < BIN[1] / 2 - 1.8))
    pile, core, win = Q.growing_pile("PelletPile", coll, len(pm), (0, 0, PILE_Z), r_pile, (1, FRAMES),
                                     k=PILE_K, density=12.0, shell=1.0, seed=4, core_mat=core_m, r_core_in=0.8, clip=clip)
    if core is not None:   # 芯の円錐も容器内に収める
        bo = core.modifiers.new("clip", "BOOLEAN"); bo.operation = "INTERSECT"; bo.solver = "EXACT"
        box = P.box("CoreClip", (BIN[0] - 3.6, BIN[1] - 3.6, 60), (0, 0, 30)); box.hide_render = True; box.hide_viewport = True
        bo.object = box
    print(f"[p06] pile points={len(pile.data.vertices)} visible@mid={win}")

    for i, (fr, L, R, S) in enumerate(stream_tracks(rnd, N_STREAM)):
        o = Q.linked(pm[i % len(pm)], f"Pel{i:04d}")
        Q.bake_keys(o, "location", fr, L); Q.bake_keys(o, "rotation_euler", fr, R); Q.bake_keys(o, "scale", fr, S)

    # 照明
    top = C.area_light((0, 10, 240), (0, 0, 0), 120, 1.0e5, (0.92, 0.96, 1.0), "Top"); C.light_look_at(top, (0, 0, 0))
    key = C.area_light((-170, -90, 70), (0, 0, 0), 90, 2.6e5, (1.0, 0.97, 0.92), "Key"); C.light_look_at(key, (-5, 0, 25))
    rim = C.area_light((130, 150, 90), (0, 0, 0), 80, 4.0e5, (0.8, 0.9, 1.0), "Rim"); C.light_look_at(rim, (-8, 0, 35))
    rim2 = C.area_light((-170, 120, 70), (0, 0, 0), 80, 2.0e5, (0.85, 0.92, 1.0), "Rim2"); C.light_look_at(rim2, (-5, 0, 30))
    F.spot((30, -100, 150), (0, 0, 5), 5e4, color=(1.0, 0.96, 0.9), size_deg=35, blend=0.6, radius=10, name="PileSpot")
    P.light_card("Card", (200, 120), (80, -180, 120), (0, 0, 30), strength=1.5)
    P.reflection_probe((0, 0, 40), radius=300, clip_start=1)

    cam, tgt = C.camera((34, -118, 92), (-6, 0, 24), lens=36, fstop=0.016)
    cam.data.dof.focus_object = None
    cam.data.dof.focus_distance = (Vector((34, -118, 92)) - Vector((-4, 0, 25))).length
    P.key_seq(cam, "location", [(1, (40, -122, 84)), (FRAMES, (30, -108, 78))])
    P.key_seq(tgt, "location", [(1, (-7, 0, 28)), (FRAMES, (-6, 0, 26))])
    sc.view_settings.exposure = 0.3
    sc.view_settings.look = "AgX - Medium High Contrast"


if __name__ == "__main__":
    C.EPISODE = "ep03"
    C.run_shot("p06_pellets", build, FRAMES)
