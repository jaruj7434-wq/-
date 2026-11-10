"""「枝分かれドミノで『天国と地獄』を最後まで演奏できる?」1列のドミノが 2列→4列→8列 に枝分かれしていく物理ショート。

- 上から見たドミノの列。最初は1列、途中で 2列、4列、8列 と枝分かれして増えていく。
- ドミノは「天国と地獄」(オッフェンバック・パブリックドメイン)の音符に1枚ずつ対応していて、
  長い音符のところはドミノの間隔が広い(だから倒れるリズムがそのまま曲のリズムになる)。
  列が増えるたびに、増えた列がハモり(3度下・オクターブ)や別の楽器を受け持ち、音が厚くなる。
- 物理は横から見た2Dの剛体(倒れる・回転・衝突・摩擦)。列ごとに当たり判定を分けて計算し、上から見た絵に直して描く。
  間隔は手で並べたように少しずつばらつく。広いすきまで止まると、その先の枝は全部止まって、そのパートの音が消える。
- 最後は8列が横に並んだ1枚の巨大ドミノにぶつかる。たどりついた列の力が足りれば巨大ドミノが倒れて成功(天使)、
  足りなければ倒れずに失敗(幽霊)。押すのは最初の1枚だけ(ねらい・補正なし)。

使い方:
    python branch_domino.py search [-n 200]
    python branch_domino.py render --seed N
"""
import argparse
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import cairo
import numpy as np
import pymunk

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "ball_escape"))
from ball_escape import midi_hz, text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from angels import DURATION as ANGEL_DUR, AngelShow, holy_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
GRAVITY = 650.0
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

# ---------------------------------------------------------------- 曲(天国と地獄・ハ長調)  (MIDI番号, 長さ[8分音符])
_A = [(60, 4), (62, 1), (65, 1), (64, 1), (62, 1), (67, 2), (67, 2), (67, 1), (69, 1), (64, 1), (65, 1),
      (62, 2), (62, 2), (62, 1), (65, 1), (64, 1), (62, 1), (60, 1), (72, 1), (71, 1), (69, 1),
      (67, 1), (65, 1), (64, 1), (62, 1)]
_B = [(60, 4), (62, 1), (65, 1), (64, 1), (62, 1), (67, 2), (67, 2), (67, 1), (69, 1), (64, 1), (65, 1),
      (62, 2), (62, 2), (62, 1), (65, 1), (64, 1), (62, 1), (60, 1), (67, 1), (64, 1), (62, 1), (60, 4)]
PHRASES = [_A, _B, _A, _B]        # 2回くり返す。1フレーズ(8小節)ごとに列が倍になる
# ドミノ1枚 = 8分音符1つ。長い音符は、音の出るドミノ1枚のあとに、音の出ない白いドミノ(のばし)が続く
SEG = []                           # 区間ごとの [(MIDI番号 or None, 小節内の位置), ...]
for ph in PHRASES:
    seq = []
    for m, du in ph:
        seq.append(m)
        seq += [None] * (du - 1)
    SEG.append(seq)
SEG_N = [len(x) for x in SEG]      # 32枚ずつ
SONG = [m for x in SEG for m in x]
NOTES = len(SONG)
LEVELS = len(SEG)

DOM_H = 50.0                      # ドミノの高さ
DOM_T = 0.18 * DOM_H              # 厚み
DOM_W = 34.0                      # 幅(上から見たときの横幅)
GAP = float(os.environ.get("GAP", 0.5))          # すきま(ドミノの高さに対する割合)
JIT = float(os.environ.get("JIT", 0.08))         # すきまのばらつき(±・手で並べた感じ)
FORK_LO = float(os.environ.get("FORK_LO", 0.6))  # 枝分かれした直後の1枚目までのすきま(ここだけ並べにくく、ばらつきが大きい)
FORK_HI = float(os.environ.get("FORK_HI", 1.0))
GIANT_H = float(os.environ.get("GIANT_H", 2.4)) * DOM_H
GIANT_T = float(os.environ.get("GIANT_TR", 0.18)) * GIANT_H
GIANT_GAP = 0.55 * DOM_H
GIANT_DENS = float(os.environ.get("GIANT_DENS", 1.7))   # 巨大ドミノの重さ(ふつうのドミノに対する密度)
STOP_WAIT = 2.5
OUTRO = 2.5


def seg_range(d):
    a = sum(SEG_N[:d])
    return a, a + SEG_N[d]


class Game:
    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 30
        self.space = sp
        floor = pymunk.Segment(sp.static_body, (-500, 0), (1e5, 0), 2)
        floor.friction, floor.elasticity = 0.8, 0.05
        sp.add(floor)
        # 区間(枝)の番号:レベル d の j 本目 → node = 2**d - 1 + j(当たり判定の種類として使う)
        self.doms = []       # (body, shape, level, lane, note)
        self.idx = {}
        x_end = DOM_T * NOTES + DOM_H * GAP * (NOTES - LEVELS) + DOM_H * (FORK_LO + FORK_HI) / 2 * (LEVELS - 1)
        ends = {}            # node → その枝の最後のドミノの右はしの位置
        for d in range(LEVELS):
            a, b = seg_range(d)
            for j in range(2 ** d):
                node = 2 ** d - 1 + j
                parent = (node - 1) // 2 if node > 0 else None
                x = ends[parent] if parent is not None else 0.0
                gaps = []
                for k in range(a, b):
                    if k == 0:
                        gaps.append(0.0)
                    elif k == a:   # 枝分かれの直後(ここだけ並べにくく、ばらつきが大きい)
                        gaps.append(DOM_H * rng.uniform(FORK_LO, FORK_HI))
                    else:
                        gaps.append(DOM_H * GAP * (1 + rng.uniform(-JIT, JIT)))
                if d == LEVELS - 1:   # 最後の8列は、巨大ドミノの前でそろうように(定規で測って)間隔を少しのばし縮みする
                    want = x_end - x - DOM_T * (b - a) - gaps[0]
                    sc = want / sum(gaps[1:])
                    gaps = [gaps[0]] + [g_ * sc for g_ in gaps[1:]]
                for k, g_ in zip(range(a, b), gaps):
                    x += g_
                    self._add_dom(x, d, j, node, k, parent, last=(k == b - 1))
                    x += DOM_T
                ends[node] = x
        # 巨大ドミノ(8列ぜんぶがぶつかる)
        xg = x_end + GIANT_GAP
        m = GIANT_T * GIANT_H / 100 * GIANT_DENS
        gb = pymunk.Body(m, pymunk.moment_for_box(m, (GIANT_T, GIANT_H)))
        gb.position = (xg + GIANT_T / 2, -GIANT_H / 2)
        gs = pymunk.Poly.create_box(gb, (GIANT_T, GIANT_H))
        gs.friction, gs.elasticity = 0.6, 0.05
        gs.filter = pymunk.ShapeFilter(categories=1 << 30)
        gs.collision_type = 3
        sp.add(gb, gs)
        self.giant = gb
        self.idx[gs] = -1
        self.hit = {}
        self.events = []

        def on_dom(arb, space, data):
            s1, s2 = arb.shapes
            i1, i2 = self.idx[s1], self.idx[s2]
            if i1 == -1 or i2 == -1:
                if "giant" not in self.hit:
                    self.hit["giant"] = self.t
                    self.events.append(("giant_hit", self.t, None))
                return
            # 後ろ(音符の番号が大きい)ほうのドミノが、当てられた
            j_ = i1 if self.doms[i1][4] > self.doms[i2][4] else i2
            if j_ not in self.hit:
                self.hit[j_] = self.t
                _, _, d, lane, k = self.doms[j_]
                self.events.append(("hit", self.t, (d, lane, k)))
        sp.on_collision(3, 3, begin=on_dom)
        b0 = self.doms[0][0]
        b0.apply_impulse_at_local_point((b0.mass * 60, 0), (0, -DOM_H * 0.4))
        self.hit[0] = 0.0
        self.events.append(("hit", 0.0, (0, 0, 0)))
        self.t = 0.0
        self.last_hit_t = 0.0
        self.result, self.result_t = None, None
        self.giant_down = False

    def _add_dom(self, x, d, j, node, k, parent, last):
        m = DOM_T * DOM_H / 100
        b = pymunk.Body(m, pymunk.moment_for_box(m, (DOM_T, DOM_H)))
        b.position = (x + DOM_T / 2, -DOM_H / 2)
        s = pymunk.Poly.create_box(b, (DOM_T, DOM_H))
        s.friction, s.elasticity = 0.6, 0.05
        s.collision_type = 3
        mask = 1 << node
        if parent is not None:
            mask |= 1 << parent
        if last:
            if d + 1 < LEVELS:   # 枝分かれのドミノは、次の2本の枝の最初のドミノを押す
                mask |= (1 << (2 * node + 1)) | (1 << (2 * node + 2))
            else:
                mask |= 1 << 30
        s.filter = pymunk.ShapeFilter(categories=1 << node, mask=mask)
        self.space.add(b, s)
        self.idx[s] = len(self.doms)
        self.doms.append((b, s, d, j, k))

    def step(self, dt):
        self.t += dt
        self.space.step(dt)
        if self.hit:
            self.last_hit_t = max(v for v in self.hit.values())
        if self.result is None:
            if abs(self.giant.angle) > 0.9:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t - self.last_hit_t > STOP_WAIT and abs(self.giant.angular_velocity) < 0.03:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, None))
        if not self.giant_down and abs(self.giant.angle) > 1.45:
            self.giant_down = True
            self.events.append(("land", self.t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "doms": [(b.position.x, b.position.y, b.angle) for b, *_ in g.doms],
                           "giant": (g.giant.position.x, g.giant.position.y, g.giant.angle)})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
        if g.t > 90:
            break
    leaves = sum(1 for i, (_, _, d, _, k) in enumerate(g.doms) if d == LEVELS - 1 and k == NOTES - 1 and i in g.hit)
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "leaves": leaves, "hit": dict(g.hit), "doms": [(d, j, k) for _, _, d, j, k in g.doms]}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["leaves"]


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[0] is not None and r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件")
    from collections import Counter
    print("最後までたどりついた列の数:", sorted(Counter((r[3], r[1]) for r in rs).items()))
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 上から見た形(コースの道すじ)
COL = 72.0                 # 最後の8列の間かく
FORK_OFF = DOM_W * 0.55    # 枝分かれした直後の2本の、左右のずれ
L_T = 300.0                # 枝分かれしてから自分の列の位置に移るまでの長さ
GIANT_W = COL * 8 + 40


def lane_x(d, j):
    return (j - (2 ** d - 1) / 2) * COL * 2 ** (LEVELS - 1 - d)


def _smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


class Course:
    """枝(node)ごとの道すじ。s(横から見た物理の x)→ 上から見た位置 (x, y)。"""
    def __init__(self, s0):
        self.s0 = s0       # node → その枝の最初のドミノの s

    def x_of(self, node, s):
        d = int(math.log2(node + 1))
        j = node - (2 ** d - 1)
        X = lane_x(d, j)
        if d == 0:
            return X
        parent = (node - 1) // 2
        pd = d - 1
        x0 = lane_x(pd, parent - (2 ** pd - 1)) + (-FORK_OFF if j % 2 == 0 else FORK_OFF)
        return x0 + (X - x0) * _smooth((s - self.s0[node]) / L_T)

    def frame(self, node, s):
        x = self.x_of(node, s)
        dx = (self.x_of(node, s + 2) - self.x_of(node, s - 2)) / 4
        n = math.hypot(dx, 1)
        return x, s, dx / n, 1 / n      # 位置と、進む向き(上から見た単位ベクトル)


# ---------------------------------------------------------------- 描画
TILT = float(os.environ.get("TILT", 0.32))
CT, ST = math.cos(TILT), math.sin(TILT)
VIEW = (0.0, ST, CT)       # カメラのほうを向く向き
LIGHT = (-0.35, 0.45, 0.82)
BG = (0.035, 0.04, 0.07)
GOLD = (1, 0.86, 0.2)


def pitch_col(m):
    """音の高さごとの色(ドレミ…で虹色)。"""
    pc = [0, 2, 4, 5, 7, 9, 11].index(m % 12) if m % 12 in (0, 2, 4, 5, 7, 9, 11) else 0
    hue = pc / 7.0
    r, g, b = (0.5 + 0.5 * math.cos(2 * math.pi * (hue + o)) for o in (0, -1 / 3, -2 / 3))
    return (0.25 + 0.75 * r, 0.25 + 0.75 * g, 0.25 + 0.75 * b)


class Cam:
    def __init__(self):
        self.y, self.x, self.sc = 0.0, 0.0, 2.6
        self.sy0 = 900.0

    def p(self, x, y, z):
        return (W / 2 + (x - self.x) * self.sc, self.sy0 + ((y - self.y) * CT - z * ST) * self.sc)


def box_faces(cx, cy, tx, ty, u_c, z_c, ang, th, hh, ww):
    """横から見た姿勢(中心 u_c, z_c, 角度 ang)の箱を、上から見た向き (tx, ty) に置いた 3D の 6面。"""
    ca, sa = math.cos(ang), math.sin(ang)
    nx, ny = ty, -tx
    pts = []
    for du in (-th / 2, th / 2):
        for dz in (-hh / 2, hh / 2):
            # 物理(横から)の座標:x 右 = 進む向き、y 下 = 地面の下。z = 上
            ru = du * ca - dz * (-sa)      # dz は上向きなので、横から見た y は -dz
            rz = -(du * sa + (-dz) * ca)
            for dw in (-ww / 2, ww / 2):
                u = u_c + ru
                z = z_c + rz
                pts.append((cx + tx * (u - u_c) + nx * dw, cy + ty * (u - u_c) + ny * dw, z))
    # pts の番号: (du, dz, dw) の順に 0/1
    def P(a, b, c):
        return pts[a * 4 + b * 2 + c]
    faces = [
        [P(0, 0, 0), P(0, 1, 0), P(0, 1, 1), P(0, 0, 1)],
        [P(1, 0, 0), P(1, 0, 1), P(1, 1, 1), P(1, 1, 0)],
        [P(0, 0, 0), P(0, 0, 1), P(1, 0, 1), P(1, 0, 0)],
        [P(0, 1, 0), P(1, 1, 0), P(1, 1, 1), P(0, 1, 1)],
        [P(0, 0, 0), P(1, 0, 0), P(1, 1, 0), P(0, 1, 0)],
        [P(0, 0, 1), P(0, 1, 1), P(1, 1, 1), P(1, 0, 1)],
    ]
    cen = [sum(p[i] for p in pts) / 8 for i in range(3)]
    out = []
    for f in faces:
        a, b, c = f[0], f[1], f[2]
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        fc = [sum(p[i] for p in f) / 4 for i in range(3)]
        if sum(n[i] * (fc[i] - cen[i]) for i in range(3)) < 0:
            n = [-q for q in n]
        ln = math.sqrt(sum(q * q for q in n)) or 1
        n = [q / ln for q in n]
        out.append((f, n))
    return out


def draw_box(ctx, cam, faces, col, glow=0.0, alpha=1.0):
    for f, n in faces:
        if n[0] * VIEW[0] + n[1] * VIEW[1] + n[2] * VIEW[2] <= 0.02:
            continue
        sh = 0.45 + 0.55 * max(0.0, n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2])
        r, g, b = (min(1, c * sh + glow * 0.7) for c in col)
        ctx.new_path()
        for p in f:
            ctx.line_to(*cam.p(*p))
        ctx.close_path()
        ctx.set_source_rgba(r, g, b, alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(0, 0, 0, 0.35 * alpha)
        ctx.set_line_width(1.0)
        ctx.stroke()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    info = res["doms"]            # (d, j, k)
    hit = res["hit"]
    nodes = {}
    for i, (d, j, k) in enumerate(info):
        node = 2 ** d - 1 + j
        nodes.setdefault(node, []).append(i)
    s0 = {nd: frames[0]["doms"][ix[0]][0] for nd, ix in nodes.items()}
    course = Course(s0)
    # 止まった枝(枝分かれの直後で止まった)と、止まった時刻
    dead = {}
    for nd, ix in nodes.items():
        if nd == 0:
            continue
        par = nodes[(nd - 1) // 2][-1]
        if par in hit and ix[0] not in hit:
            dead[nd] = hit[par] + 0.9
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"branch_domino_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"branch_domino_{seed}.wav")
    final = os.path.join(OUT_DIR, f"branch_domino_{seed}.mp4")
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    if preview:   # 確認用:指定した時刻のコマだけ PNG で書き出す
        class _P:
            def __init__(self):
                self.stdin = self
                self.fi = 0

            def write(self, _):
                t_ = (self.fi + 1) / FPS
                for pt in preview:
                    if abs(t_ - pt) < 0.5 / FPS:
                        surf.write_to_png(os.path.join(OUT_DIR, f"bd_preview_{pt:.1f}.png"))
                self.fi += 1
        ff = _P()
        frames = [f for f in frames if f["t"] <= max(preview) + 0.05]
    else:
        ff = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
             "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
            stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    angels = AngelShow(W, H, seed) if result == "success" else None
    cam = Cam()
    cam.y = s0[0] - 200
    paths = {nd: [(course.x_of(nd, s), s) for s in np.arange(s0[nd] - 10, frames[0]["doms"][ix[-1]][0] + 30, 12)]
             for nd, ix in nodes.items()}
    gx0 = frames[0]["giant"][0]
    shake = 0.0
    land_t = None
    giant_hit_t = None
    for e in events:
        if e[0] == "land":
            land_t = e[1]
        if e[0] == "giant_hit":
            giant_hit_t = e[1]
    for fi, fr in enumerate(frames):
        t = fr["t"]
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0
        # カメラ:いちばん先まで倒れたドミノを追いかける
        hits_now = [i for i, ht in hit.items() if isinstance(i, int) and ht <= t]
        front = max((frames[0]["doms"][i][0] for i in hits_now), default=s0[0])
        lvl = max((info[i][0] for i in hits_now), default=0)
        tgt_y = min(front - 60, gx0 - 40)
        if giant_hit_t is not None and t > giant_hit_t - 1.0:
            tgt_y = gx0 - 120
        cam.y += (tgt_y - cam.y) * 0.08
        tgt_sc = [2.6, 2.25, 1.95, 1.7][lvl]
        if giant_hit_t is not None and t > giant_hit_t - 1.0:
            tgt_sc = 1.45
        cam.sc += (tgt_sc - cam.sc) * 0.04
        if land_t is not None and abs(t - land_t) < 1 / FPS:
            shake = 30
        shake *= 0.88
        ctx.set_source_rgb(*BG)
        ctx.paint()
        ctx.save()
        if shake > 0.5:
            ctx.translate(math.sin(t * 57) * shake, math.cos(t * 49) * shake)
        # 床(うっすら光る道すじ)
        g = cairo.LinearGradient(0, 0, 0, H)
        g.add_color_stop_rgb(0, 0.05, 0.05, 0.1)
        g.add_color_stop_rgb(1, 0.1, 0.08, 0.16)
        ctx.set_source(g)
        ctx.paint()
        for nd, pts in paths.items():
            if nd in dead and t >= dead[nd]:
                col = (1, 0.3, 0.3, 0.12)
            else:
                col = (0.6, 0.75, 1.0, 0.13)
            ctx.new_path()
            for x, y in pts:
                ctx.line_to(*cam.p(x, y, 0))
            ctx.set_source_rgba(*col)
            ctx.set_line_width(DOM_W * cam.sc * 1.25)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()
        # ドミノ(遠いものから順に)
        lo_y = cam.y - (cam.sy0 + 200) / (cam.sc * CT)
        hi_y = cam.y + (H - cam.sy0 + 300) / (cam.sc * CT)
        items = []
        for i, (sx, sy, ang) in enumerate(fr["doms"]):
            d, j, k = info[i]
            nd = 2 ** d - 1 + j
            u0 = frames[0]["doms"][i][0]
            if u0 < lo_y - 100 or u0 > hi_y:
                continue
            items.append((u0 + sx * 0.0, i, sx, sy, ang, nd, k))
        items.sort()
        for _, i, sx, sy, ang, nd, k in items:
            u0 = frames[0]["doms"][i][0]
            cx, cy, tx, ty = course.frame(nd, u0)
            last = k == sum(SEG_N[:info[i][0] + 1]) - 1 and info[i][0] < LEVELS - 1
            ww = DOM_W + 2 * FORK_OFF if last else DOM_W
            # 道すじの上で、ドミノの中心がずれた分だけ進める
            cx2, cy2 = cx + tx * (sx - u0), cy + ty * (sx - u0)
            faces = box_faces(cx2, cy2, tx, ty, sx, -sy, ang, DOM_T, DOM_H, ww)
            m = SONG[k]
            # 立っているあいだは白。倒れると、その音の色に変わる(音の出ないドミノは白いまま)
            base = (0.9, 0.9, 0.88)
            if m is not None:
                pc_ = pitch_col(m)
                f_ = min(1.0, abs(ang) / 0.5)
                col = tuple(base[q] + (pc_[q] - base[q]) * (0.25 + 0.75 * f_) for q in range(3))
            else:
                col = (0.62, 0.62, 0.64) if abs(ang) > 0.3 else base
            ht = hit.get(i)
            glow = max(0.0, 1 - (t - ht) / 0.2) if ht is not None and t >= ht and m is not None else 0.0
            draw_box(ctx, cam, faces, col, glow)
        # 巨大ドミノ
        gx, gy, ga = fr["giant"]
        faces = box_faces(0.0, gx0, 0.0, 1.0, gx, -gy, ga, GIANT_T, GIANT_H, GIANT_W)
        draw_box(ctx, cam, faces, (1.0, 0.78, 0.25), 0.15 + (0.3 if giant_hit_t is not None and t > giant_hit_t else 0))
        # 止まった枝に ✕
        for nd, td in dead.items():
            if t >= td:
                i0 = nodes[nd][0]
                u0 = frames[0]["doms"][i0][0]
                x, y = cam.p(course.x_of(nd, u0), u0, DOM_H * 0.6)
                k2 = min(1.0, (t - td) / 0.15)
                ctx.set_source_rgba(1, 0.2, 0.2, 0.95)
                ctx.set_line_width(9 * k2)
                r_ = 26 * (1.4 - 0.4 * k2)
                ctx.move_to(x - r_, y - r_); ctx.line_to(x + r_, y + r_)
                ctx.move_to(x + r_, y - r_); ctx.line_to(x - r_, y + r_)
                ctx.stroke()
                if t - td < 1.2:
                    text(ctx, "ストップ…", x, y - 60, 44, rgb=(1, 0.45, 0.45), sw=8)
        ctx.restore()
        if angels is not None and over:
            angels.draw(ctx, t - end_t)
        # 文字
        g = cairo.LinearGradient(0, 0, 0, 430)
        g.add_color_stop_rgba(0, 0.03, 0.03, 0.07, 0.92)
        g.add_color_stop_rgba(1, 0.03, 0.03, 0.07, 0.0)
        ctx.rectangle(0, 0, W, 430)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, "枝分かれドミノで", W / 2, 140, 70, sw=12)
        text(ctx, "「天国と地獄」を", W / 2, 245, 92, rgb=GOLD, sw=16)
        text(ctx, "最後まで演奏できる？", W / 2, 350, 80, rgb=GOLD, sw=14)
        # 今のレベルで生きている列 = 今のレベルの枝のうち、止まった親や自分が止まっていないもの
        lv_nodes = range(2 ** lvl - 1, 2 ** (lvl + 1) - 1)
        alive = sum(1 for nd in lv_nodes if not any(a in dead and t >= dead[a] for a in _anc(nd)))
        k_note = max((info[i][2] for i in hits_now), default=0)
        text(ctx, f"♪ {k_note + 1} / {NOTES}", W / 2 - 230, 1800, 56, sw=10)
        text(ctx, f"{alive}列 / {2 ** lvl}列", W / 2 + 230, 1800, 56, rgb=(0.7, 0.9, 1.0), sw=10)
        # 枝分かれした瞬間の文字
        for d in range(1, LEVELS):
            i0 = nodes[2 ** d - 1][0]
            par = nodes[2 ** (d - 1) - 1][-1]
            tf = hit.get(par)
            if tf is not None and 0 <= t - tf < 1.3:
                k2 = min(1.0, (t - tf) / 0.15)
                text(ctx, f"{2 ** d}列に分かれた!", W / 2, 520, 84 * (1.25 - 0.25 * k2), rgb=(0.6, 1.0, 0.8), sw=14)
        if giant_hit_t is not None and not over and t >= giant_hit_t:
            text(ctx, "巨大ドミノ!!", W / 2, 520, 92, rgb=GOLD, sw=16)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "倒れない…", W / 2, 900, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, "最後の巨大ドミノを倒せなかった", W / 2, 1030, 58, sw=10)
        elif over:
            age = t - end_t
            if age < 0.3:
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.8 * (1 - age / 0.3))
                ctx.fill()
            text(ctx, "演奏成功!!", W / 2, 640, 120, rgb=GOLD, sw=18)
        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
    if preview:
        return
    ff.stdin.close()
    ff.wait()
    duration = len(frames) / FPS
    synth_audio(res, duration, wav)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(silent)
    os.remove(wav)
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} 最後の列 {res['leaves']}/8 / 長さ {duration:.1f}秒)")


def _anc(nd):
    """自分と、その親・祖父…(枝の番号)。"""
    out = [nd]
    while nd > 0:
        nd = (nd - 1) // 2
        out.append(nd)
    return out


# ---------------------------------------------------------------- 音
sys.path.insert(0, os.path.join(HERE, "..", "giant_domino"))
import giant_domino as GD  # noqa: E402   楽器(オルゴール・ピアノ・ブラス・ストリングス・ティンパニ)

HOLY_GAIN = 0.85
CHORDS_A = [48, 43, 48, 48, 43, 43, 48, 43]   # 小節ごとの根音(C=48, G=43)
CHORDS_B = [48, 43, 48, 48, 43, 43, 48, 48]
SEG_CHORDS = [CHORDS_A, CHORDS_B, CHORDS_A, CHORDS_B]
SCALE = [0, 2, 4, 5, 7, 9, 11]


def third_below(m):
    o, pc = divmod(m, 12)
    i = SCALE.index(pc)
    j = i - 2
    return (o + (j // 7)) * 12 + SCALE[j % 7]


def chord_tones(root):
    return [root + 12, root + 16, root + 19] if root == 48 else [root + 12, root + 16, root + 19, root + 22]


def snare(seed, amp):
    t = GD._t(0.18)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    return amp * (0.7 * n * np.exp(-t * 28) + 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30))


def hat(seed, amp):
    t = GD._t(0.06)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    n = n - np.convolve(n, np.ones(3) / 3, "same")
    return amp * n * np.exp(-t * 70)


def crash(seed, amp):
    t = GD._t(1.6)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    n = n - np.convolve(n, np.ones(2) / 2, "same")
    return amp * n * np.exp(-t * 2.5)


def glock(f, amp):
    t = GD._t(0.9)
    return amp * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 8)) * np.exp(-t * 4) * np.minimum(1, t / 0.002)


def xylo(f, amp):
    t = GD._t(0.35)
    return amp * (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 30)) * np.exp(-t * 11) * np.minimum(1, t / 0.002)


def part_sound(d, j, k, seed):
    """レベル d の j 本目の列が、k 番目のドミノで鳴らす音(列ごとに受け持ちのパートがちがう)。"""
    m = SONG[k]
    a = sum(SEG_N[:d])
    pos = k - a
    root = SEG_CHORDS[d][pos // 4]
    role = j
    if role == 0:   # メロディ(進むほど楽器が豪華に)
        if m is None:
            return None
        f = midi_hz(m)
        return [xylo(f * 2, 0.7), GD.piano(f, 0.6), GD.mix(GD.piano(f, 0.45), GD.brass(f, 0.4, 0.4)),
                GD.mix(GD.brass(f, 0.55, 0.45), GD.strings(f, 0.3, 0.5))][d]
    if role == 1:   # 3度下のハモり
        if m is None:
            return None
        return GD.piano(midi_hz(third_below(m)), 0.4) if d < 3 else GD.brass(midi_hz(third_below(m)), 0.4, 0.4)
    if role == 2:   # ズン(根音)・チャッ(和音)の伴奏
        if pos % 2 == 0:
            return GD.piano(midi_hz(root if pos % 4 == 0 else root + 7), 0.55)
        return GD.mix(*[GD.piano(midi_hz(x), 0.16) for x in chord_tones(root)])
    if role == 3:   # 小太鼓(うら拍)
        return snare(seed, 0.35) if pos % 2 == 1 else hat(seed, 0.25)
    if role == 4:   # メロディ1オクターブ上(鉄琴)
        return glock(midi_hz(m + 12), 0.3) if m is not None else None
    if role == 5:   # ベース(低い金管)
        return GD.brass(midi_hz(root - 12 + (7 if pos % 4 == 2 else 0)), 0.45, 0.3) if pos % 2 == 0 else None
    if role == 6:   # ストリングス(メロディ)
        return GD.strings(midi_hz(m), 0.3, 0.6) if m is not None else None
    # 7: シンバル(小節の頭)とハイハット
    return crash(seed, 0.3) if pos % 8 == 0 else hat(seed, 0.2)


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)

    def add(sig, t0, gain=1.0, buf=None):
        if sig is None:
            return
        b = out if buf is None else buf
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out and j > i:
            b[i:j] += gain * sig[: j - i]

    for kind, t, data in events:
        if end_t is not None and t > end_t + 3:
            continue
        if kind == "hit":
            d, j, k = data
            add(GD.click(30, k * 8 + j), t, 0.12)
            # 1つ上のレベルの同じパートとの音量をそろえる(列が増えても1パートずつ足されていく)
            add(part_sound(d, j % 8, k, k * 13 + j), t, 0.9)
        elif kind == "giant_hit":
            add(GD.timpani(0.7, 1.2), t)
        elif kind == "land":
            add(GD.click(300, 99), t, 1.3)
            add(GD.timpani(1.0, 2.2), t)
            for m_, a in ((36, 0.7), (48, 0.6), (55, 0.5), (60, 0.6), (64, 0.5), (67, 0.4), (72, 0.4)):
                add(GD.mix(GD.brass(midi_hz(m_), a, 2.2), GD.strings(midi_hz(m_), a * 0.6, 2.5)), t + 0.03)
            add(crash(5, 0.6), t)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(end_t * SR) + int(1.8 * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += HOLY_GAIN * sig[:m]
    wet = out.copy()
    for dd, g in ((0.047, 0.28), (0.079, 0.2), (0.121, 0.13)):
        k = int(dd * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int((end_t or duration) * SR)]
    rms = np.sqrt(np.mean(body ** 2)) if len(body) else 0
    if rms > 0:
        wet *= min(4.0, 10 ** (-14.0 / 20) / rms)
    wet = wet + (0.95 if fail else 1.0) * extra[: len(wet)]
    mag = np.abs(wet)
    wet = np.where(mag < 0.7, wet, np.sign(wet) * (0.7 + 0.25 * np.tanh((mag - 0.7) / 0.25)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render", "timing"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("-n", type=int, default=100)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    elif a.mode == "timing":
        r = simulate(a.seed)
        ts = sorted((v, r["doms"][k]) for k, v in r["hit"].items() if isinstance(k, int) and r["doms"][k][1] == 0)
        ts = ts[:200]
        print(r["result"], r["result_t"], r["leaves"])
        prev = 0
        for t, (d, j, k) in ts:
            print(f"{k:3d} d{d} t={t:6.3f} dt={t - prev:5.3f} note={SONG[k]}")
            prev = t
    else:
        render(a.seed)
