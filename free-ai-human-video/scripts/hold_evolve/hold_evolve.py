"""「白保留を虹保留にできる?」首のついた丸いフラスコに、パチンコの保留玉が上からゆっくり落ちてきて、
同じ色どうしが触れると次の色に進化(合体)する物理ショート。

- 進化の順番(7段階):白 → 青 → 緑 → 紫 → 赤 → 金 → 虹(ゴール)
  パチンコの保留変化で一般的な「白・青は期待度が低く、緑・赤・金と上がり、虹は大当たり濃厚」という並びにならった
  (紫は緑と赤のあいだ)。色が上がるほど玉が大きくなり、光り方も派手になる。
- 落ちてくるのはいつも白保留。落ちる間隔はだんだん短くなる。
- 保留の形は、チャンネルのアイコンの女の子(おかっぱの幽霊)の顔の形(まんまるではない)。当たり判定もこの形。
- 重力・反発・摩擦のまま自然に落ちて転がる(ねらい・補正なし)。止まったものは眠らせる。
- 合体は「同じ色どうしが触れたら」必ず起きる(1回の接触で1回)。
- 音は色ごとにちがい、色が上がるほど豪華な、パチンコらしい気持ちいい音(ピロン → キュイン → ギュイン →
  キュインキュイン+ブラス → ピキーン!+ファンファーレ → 虹は長い「ギュイーン」+大当たりのファンファーレ)。
- 虹保留ができれば成功(虹色パチンコ演出)、首までつまってあふれるか時間切れなら失敗(幽霊)。
- 絵・音はすべてプログラムで作ったオリジナル(実在の台の絵・音・ロゴは使っていない)。

使い方:
    python hold_evolve.py search [-n 200]
    python hold_evolve.py render --seed N
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
from fail_bgm import fail_music  # noqa: E402
from pachinko import DURATION as FEVER_DUR, RainbowFever, kyuin_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
GRAVITY = 1500.0
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

NAMES = ["白", "青", "緑", "紫", "赤", "金", "虹"]
GOAL = len(NAMES) - 1
RADII = [22, 30, 40, 53, 70, 93, 124]   # 保留玉の大きさ(半径)。色が上がるほど大きい
COLORS = [(0.96, 0.96, 1.0), (0.15, 0.45, 1.0), (0.1, 0.85, 0.35), (0.68, 0.22, 0.98),
          (1.0, 0.12, 0.15), (1.0, 0.78, 0.12), None]

# 首のついた丸いフラスコ(TikTok などの文字に隠れないよう、上下の安全な範囲に収める)
FL_CX, FL_CY, FL_R = 540.0, 1080.0, 390.0
NECK_HW = 60.0
NECK_TOP = 600.0
NECK_Y = FL_CY - math.sqrt(FL_R ** 2 - NECK_HW ** 2)
OVER_Y = NECK_Y + 10
OVER_WAIT = 1.5
DROP_Y = NECK_TOP - 30
DROP_START = float(os.environ.get("DROP_START", 0.9))
DROP_END = float(os.environ.get("DROP_END", 0.3))
DROP_RAMP = 40.0
BALL_E, BALL_F = 0.35, 0.4
GLASS_E, GLASS_F = 0.4, 0.4
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 51.0))
OUTRO = 4.2


def flask_points():
    a0 = math.atan2(NECK_Y - FL_CY, -NECK_HW) % (2 * math.pi)
    a1 = math.atan2(NECK_Y - FL_CY, NECK_HW)
    pts = [(FL_CX - NECK_HW, NECK_TOP)]
    n = 72
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        pts.append((FL_CX + FL_R * math.cos(a), FL_CY + FL_R * math.sin(a)))
    pts.append((FL_CX + NECK_HW, NECK_TOP))
    return pts


def drop_every(t):
    return max(DROP_END, DROP_START - (DROP_START - DROP_END) * t / DROP_RAMP)


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 25
        sp.sleep_time_threshold = 0.6
        self.space = sp
        pts = flask_points()
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            s = pymunk.Segment(sp.static_body, a, b, 8)
            s.elasticity, s.friction = GLASS_E, GLASS_F
            s.set_neighbors(pts[max(i - 1, 0)], pts[min(i + 2, len(pts) - 1)])
            sp.add(s)
        for k in range(len(NAMES)):
            sp.on_collision(10 + k, 10 + k, begin=self._touch)
        self.balls = []
        self.next_id = 0
        self.pairs = []
        self.events = []
        self.t = 0.0
        self.next_drop = 0.4
        self.best = 0
        self.result, self.result_t = None, None
        self.over_since = None

    def _touch(self, arb, space, data):
        a, b = arb.shapes
        if self.result is None:
            self.pairs.append((a.body, b.body))
        return True

    def add(self, st, x, y, vx=0.0, vy=0.0, w=0.0):
        r = RADII[st]
        mass = (r / RADII[0]) ** 2
        poly = shape_pts(st)   # まんまるではない、女の子の頭の形(当たり判定もこの形)
        b = pymunk.Body(mass, pymunk.moment_for_poly(mass, poly))
        b.position = (x, y)
        b.velocity, b.angular_velocity = (vx, vy), w
        s = pymunk.Poly(b, poly, radius=1)
        s.elasticity, s.friction = BALL_E, BALL_F
        s.collision_type = 10 + st
        self.space.add(b, s)
        c = {"id": self.next_id, "stage": st, "body": b, "shape": s, "born": self.t}
        self.next_id += 1
        self.balls.append(c)
        return c

    def step(self, dt):
        self.t += dt
        if self.result is None and self.t >= self.next_drop:
            self.next_drop += drop_every(self.t)
            x = FL_CX + self.rng.uniform(-12, 12)
            c = self.add(0, x, DROP_Y, vx=self.rng.uniform(-25, 25), w=self.rng.uniform(-2, 2))
            self.events.append(("drop", self.t, c["id"]))
        self.pairs = []
        self.space.step(dt)
        by_body = {c["body"]: c for c in self.balls}
        used = set()
        for ba, bb in self.pairs:
            ca, cb = by_body.get(ba), by_body.get(bb)
            if ca is None or cb is None or ca["id"] in used or cb["id"] in used or ca["stage"] != cb["stage"]:
                continue
            if ca["stage"] >= GOAL:
                continue
            used |= {ca["id"], cb["id"]}
            st = ca["stage"] + 1
            pa, pb = ba.position, bb.position
            x, y = (pa.x + pb.x) / 2, (pa.y + pb.y) / 2
            v = (ba.velocity + bb.velocity) / 2
            for c in (ca, cb):
                self.space.remove(c["body"], c["shape"])
                self.balls.remove(c)
            nc = self.add(st, x, y, vx=v.x, vy=v.y, w=(ba.angular_velocity + bb.angular_velocity) / 2)
            self.events.append(("merge", self.t, (nc["id"], st, x, y)))
            if st > self.best:
                self.best = st
                if st == GOAL and self.result is None:
                    self.result, self.result_t = "success", self.t
                    self.events.append(("success", self.t, None))
        if self.result is None:
            top = min((c["shape"].bb.bottom for c in self.balls
                       if self.t - c["born"] > 1.5 and c["body"].velocity.length < 60), default=H)
            if top < OVER_Y:
                if self.over_since is None:
                    self.over_since = self.t
                if self.t - self.over_since > OVER_WAIT:
                    self.result, self.result_t = "fail", self.t
                    self.events.append(("fail", self.t, "overflow"))
            else:
                self.over_since = None
            if self.result is None and self.t >= TIME_LIMIT:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, "time"))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "best": g.best, "over": g.over_since,
                           "balls": [(c["id"], c["stage"], c["body"].position.x, c["body"].position.y, c["body"].angle)
                                     for c in g.balls]})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else FEVER_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "best": g.best}


def score(seed):
    r = simulate(seed)
    why = next((e[2] for e in r["events"] if e[0] == "fail"), "")
    n5 = sum(1 for e in r["events"] if e[0] == "merge" and e[2][1] == GOAL - 1)
    return seed, r["result"], round(r["result_t"], 1), NAMES[r["best"]], why, n5


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def hsv(h, s=1.0, v=1.0):
    h = h % 1.0
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p, q, t_ = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    return [(v, t_, p), (q, v, p), (p, v, t_), (p, q, v), (t_, p, v), (v, p, q)][i]


def mix(c, d, k):
    return tuple(a + (b - a) * k for a, b in zip(c, d))


def _bezel_grad(x, y, r, gold=False):
    """金属のふち(ベゼル):上が明るく下が暗い、メタリックな縦のグラデーション。"""
    g = cairo.LinearGradient(x - r * 0.5, y - r, x + r * 0.5, y + r)
    if gold:
        stops = [(0, (1.0, 0.97, 0.75)), (0.25, (0.95, 0.72, 0.18)), (0.5, (0.45, 0.28, 0.02)),
                 (0.7, (0.98, 0.82, 0.35)), (1, (0.5, 0.32, 0.04))]
    else:
        stops = [(0, (1, 1, 1)), (0.22, (0.78, 0.8, 0.86)), (0.5, (0.2, 0.21, 0.25)),
                 (0.72, (0.88, 0.9, 0.95)), (1, (0.3, 0.31, 0.36))]
    for o, c in stops:
        g.add_color_stop_rgb(o, *c)
    return g


def _flare(ctx, x, y, s, a, rot=0.0):
    """レンズフレアのような細い光の十字。"""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    for ang, ln in ((0, 1.0), (math.pi / 2, 1.0), (math.pi / 4, 0.45), (-math.pi / 4, 0.45)):
        ctx.save()
        ctx.rotate(ang)
        g = cairo.LinearGradient(-s * ln, 0, s * ln, 0)
        g.add_color_stop_rgba(0, 1, 1, 1, 0)
        g.add_color_stop_rgba(0.5, 1, 1, 1, a)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.rectangle(-s * ln, -max(0.8, s * 0.035), 2 * s * ln, 2 * max(0.8, s * 0.035))
        ctx.set_source(g)
        ctx.fill()
        ctx.restore()
    g = cairo.RadialGradient(0, 0, 0, 0, 0, s * 0.25)
    g.add_color_stop_rgba(0, 1, 1, 1, a)
    g.add_color_stop_rgba(1, 1, 1, 1, 0)
    ctx.arc(0, 0, s * 0.25, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    ctx.restore()


def head_shape(r, n=10):
    """保留の形:チャンネルのアイコンの女の子(おかっぱの幽霊)の頭のシルエット。
    上はまるい髪、横はまっすぐ下りる髪、下は平ら(角だけ丸い)。まんまるではない、ゆがんだ形。重心が(0,0)になるようにずらす。"""
    pts = []
    cy = -0.12 * r
    for k in range(n + 1):   # 上の丸い髪(左→右)
        a = math.pi + math.pi * k / n
        pts.append((r * math.cos(a), cy + r * 0.98 * math.sin(a)))
    cr = 0.28 * r            # 下の角の丸み
    bot = 0.86 * r
    for k in range(5):       # 右下の角
        a = 0 + (math.pi / 2) * k / 4
        pts.append((r - cr + cr * math.cos(a), bot - cr + cr * math.sin(a)))
    for k in range(5):       # 左下の角
        a = math.pi / 2 + (math.pi / 2) * k / 4
        pts.append((-r + cr + cr * math.cos(a), bot - cr + cr * math.sin(a)))
    # 重心をまん中に
    A = cx = cyy = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        c = x0 * y1 - x1 * y0
        A += c
        cx += (x0 + x1) * c
        cyy += (y0 + y1) * c
    A *= 0.5
    cx /= 6 * A
    cyy /= 6 * A
    return [(x - cx, y - cyy) for x, y in pts]


_SHAPES = {}


def shape_pts(st):
    if st not in _SHAPES:
        _SHAPES[st] = head_shape(RADII[st])
    return _SHAPES[st]


def _hair_grad(r, col, st, t):
    """髪(保留の本体)のメタリックなグラデーション。色つきの金属に、横じまの映りこみ。"""
    g = cairo.LinearGradient(-r * 0.4, -r * 1.1, r * 0.4, r * 0.9)
    if st == 0:
        stops = [(0, (1, 1, 1)), (0.18, (0.78, 0.8, 0.86)), (0.42, (0.25, 0.26, 0.3)), (0.5, (0.12, 0.12, 0.15)),
                 (0.62, (0.7, 0.72, 0.78)), (1, (0.2, 0.21, 0.25))]
    elif st == 5:
        stops = [(0, (1, 0.98, 0.8)), (0.18, (1, 0.8, 0.25)), (0.42, (0.55, 0.33, 0.02)), (0.5, (0.35, 0.2, 0.0)),
                 (0.62, (1, 0.85, 0.4)), (1, (0.45, 0.28, 0.02))]
    else:
        stops = [(0, mix(col, (1, 1, 1), 0.85)), (0.18, mix(col, (1, 1, 1), 0.3)), (0.42, mix(col, (0, 0, 0), 0.45)),
                 (0.5, mix(col, (0, 0, 0), 0.7)), (0.62, mix(col, (1, 1, 1), 0.45)), (1, mix(col, (0, 0, 0), 0.6))]
    for o, c in stops:
        g.add_color_stop_rgb(o, *c)
    return g


def _path(ctx, pts):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def draw_hold(ctx, x, y, r, st, t, ang=0.0, k=1.0):
    """パチンコのキャラ保留:チャンネルのアイコンの女の子(おかっぱの幽霊)の顔の形をした、メタリックな保留。
    髪の部分が色つきの金属(ツヤ・映りこみ・ハイライト)、前髪の下から白い顔と大きな黒い目がのぞく。
    色が上がるほど後光・光の流れ・レンズフレアが強くなる。金は金属の金、虹は虹色が回る。"""
    rainbow = COLORS[st] is None
    col = COLORS[st] if not rainbow else hsv(t * 0.5)
    ph = t * 2.2 + x * 0.013
    s = (r / RADII[st]) * k   # RADII と違う大きさで描くとき(進化表など)の倍率
    pts = [(px * s, py * s) for px, py in shape_pts(st)]
    rr = RADII[st] * s
    # 1. 外の光(後光)
    if st >= 1:
        ar = rr * (1.35 + 0.07 * st)
        g = cairo.RadialGradient(x, y, rr * 0.9, x, y, ar)
        g.add_color_stop_rgba(0, *col, 0.2 + 0.07 * st + 0.05 * math.sin(ph))
        g.add_color_stop_rgba(1, *col, 0)
        ctx.arc(x, y, ar, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
    if st >= 5:
        for j in range(16):
            a = 2 * math.pi * j / 16 + t * 0.7
            ln = rr * (1.6 + 0.25 * (j % 2))
            g = cairo.RadialGradient(x, y, rr, x, y, ln)
            c2 = hsv(j / 16 + t * 0.3) if rainbow else (1, 0.9, 0.55)
            g.add_color_stop_rgba(0, *c2, 0.55)
            g.add_color_stop_rgba(1, *c2, 0)
            ctx.move_to(x, y)
            ctx.arc(x, y, ln, a - 0.035, a + 0.035)
            ctx.close_path()
            ctx.set_source(g)
            ctx.fill()
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    # 2. 髪(本体):メタリック
    _path(ctx, pts)
    if rainbow:
        ctx.save()
        ctx.clip()
        for j in range(24):
            a = 2 * math.pi * j / 24 + t * 1.2
            ctx.move_to(0, 0)
            ctx.arc(0, 0, rr * 1.6, a, a + 2 * math.pi / 24 + 0.01)
            ctx.close_path()
            ctx.set_source_rgb(*hsv(j / 24 + t * 0.25, 0.85, 1.0))
            ctx.fill()
        g = cairo.LinearGradient(0, -rr * 1.1, 0, rr * 0.9)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.55)
        g.add_color_stop_rgba(0.45, 1, 1, 1, 0.0)
        g.add_color_stop_rgba(0.5, 0, 0, 0, 0.35)
        g.add_color_stop_rgba(0.62, 1, 1, 1, 0.2)
        g.add_color_stop_rgba(1, 0, 0, 0, 0.4)
        ctx.rectangle(-rr * 2, -rr * 2, rr * 4, rr * 4)
        ctx.set_source(g)
        ctx.fill()
        ctx.restore()
    else:
        ctx.set_source(_hair_grad(rr, col, st, t))
        ctx.fill()
    # 髪の毛すじ(上の丸い部分に、細い光のすじ)
    ctx.save()
    _path(ctx, pts)
    ctx.clip()
    for j in range(7):
        a = math.pi * (1.15 + 0.7 * j / 6)
        ctx.move_to(0.15 * rr * math.cos(a), -0.12 * rr + 0.15 * rr * math.sin(a))
        ctx.line_to(0.95 * rr * math.cos(a), -0.12 * rr + 0.95 * rr * math.sin(a))
    ctx.set_source_rgba(1, 1, 1, 0.12)
    ctx.set_line_width(max(1.0, rr * 0.035))
    ctx.stroke()
    # 光の流れ(緑から上)
    if st >= 2:
        sx = -rr * 2 + ((t * (0.5 + 0.12 * st) + x * 0.002) % 1.0) * rr * 4
        g = cairo.LinearGradient(sx - rr * 0.3, 0, sx + rr * 0.3, 0)
        g.add_color_stop_rgba(0, 1, 1, 1, 0)
        g.add_color_stop_rgba(0.5, 1, 1, 1, 0.22 + 0.05 * st)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.move_to(sx - rr * 0.2, -rr * 1.3)
        ctx.line_to(sx + rr * 0.35, -rr * 1.3)
        ctx.line_to(sx - rr * 0.15, rr)
        ctx.line_to(sx - rr * 0.7, rr)
        ctx.close_path()
        ctx.set_source(g)
        ctx.fill()
    ctx.restore()
    # 3. 顔(アイコンと同じ:前髪の下から、青白い顔と大きな黒い目がのぞく。下は髪のふちで切れている)
    fx0, fx1 = -0.56 * rr, 0.56 * rr
    top = min(py for _, py in pts)
    bot = max(py for _, py in pts)
    fy0, fy1 = bot - 0.8 * rr, bot + 2
    ctx.save()
    _path(ctx, pts)
    ctx.clip()
    fcx, fcy = 0, fy0 + 0.45 * rr
    g = cairo.RadialGradient(fcx, fcy, rr * 0.05, fcx, fcy, rr * 0.75)
    g.add_color_stop_rgb(0, 0.86, 0.9, 0.88)
    g.add_color_stop_rgb(0.55, 0.7, 0.75, 0.73)
    g.add_color_stop_rgb(1, 0.42, 0.46, 0.46)
    ctx.rectangle(fx0, fy0, fx1 - fx0, fy1 - fy0)
    ctx.set_source(g)
    ctx.fill()
    # 顔の両横の髪の毛すじ(たてのしま)
    hair_dark = (0.06, 0.06, 0.08) if st == 0 else mix(col, (0, 0, 0), 0.75)
    for side in (-1, 1):
        x0 = fx0 if side < 0 else fx1
        for j2 in range(4):
            xx = x0 - side * (0.03 + 0.035 * j2) * rr * -1
            ctx.move_to(xx, fy0)
            ctx.line_to(xx, fy1)
        ctx.set_source_rgba(1, 1, 1, 0.35)
        ctx.set_line_width(max(0.6, rr * 0.012))
        ctx.stroke()
    # 目(大きな黒い目+まわりのくま)
    ey = fy0 + 0.42 * rr
    for ex in (-0.25 * rr, 0.25 * rr):
        g = cairo.RadialGradient(ex, ey, rr * 0.1, ex, ey, rr * 0.3)
        g.add_color_stop_rgba(0, 0.2, 0.22, 0.24, 0.6)
        g.add_color_stop_rgba(1, 0.2, 0.22, 0.24, 0)
        ctx.arc(ex, ey, rr * 0.3, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
        ctx.save()
        ctx.translate(ex, ey)
        ctx.scale(0.16 * rr, 0.2 * rr)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(0.01, 0.01, 0.02)
        ctx.fill()
        ctx.arc(ex + 0.02 * rr, ey + 0.03 * rr, max(0.8, 0.032 * rr), 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 0.88)
        ctx.fill()
    # 前髪:まっすぐ切りそろえた前髪+細い毛先がたれる
    ctx.rectangle(fx0 - 2, fy0 - 3, fx1 - fx0 + 4, 4)   # 前髪のふちの影
    ctx.set_source_rgba(0, 0, 0, 0.5)
    ctx.fill()
    ctx.set_source_rgba(*(hair_dark if not rainbow else mix(hsv(t * 0.4), (0, 0, 0), 0.5)), 0.85)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for j2 in range(9):
        xx = fx0 + (fx1 - fx0) * (j2 + 0.5) / 9
        ln = (0.07 + 0.05 * ((j2 * 7) % 3)) * rr
        ctx.move_to(xx, fy0 - 1)
        ctx.line_to(xx + 0.01 * rr, fy0 + ln)
    ctx.set_line_width(max(1.0, rr * 0.045))
    ctx.stroke()
    ctx.restore()
    # 4. ふち(クロームの線)とハイライト
    _path(ctx, pts)
    ctx.set_source_rgba(0, 0, 0, 0.7)
    ctx.set_line_width(max(1.5, rr * 0.09))
    ctx.stroke()
    _path(ctx, pts)
    g = cairo.LinearGradient(0, -rr * 1.1, 0, rr)
    g.add_color_stop_rgb(0, 1, 1, 1)
    g.add_color_stop_rgb(0.45, 0.55, 0.57, 0.62)
    g.add_color_stop_rgb(0.7, 0.95, 0.96, 1)
    g.add_color_stop_rgb(1, 0.35, 0.36, 0.4)
    ctx.set_source(g)
    ctx.set_line_width(max(1.0, rr * 0.045))
    ctx.stroke()
    hx, hy = -0.42 * rr, top + 0.32 * rr
    ctx.save()
    ctx.translate(hx, hy)
    ctx.rotate(-0.55)
    ctx.scale(rr * 0.34, rr * 0.12)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.95)
    g.add_color_stop_rgba(1, 1, 1, 1, 0)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    ctx.restore()
    ctx.arc(hx - 0.04 * rr, hy, max(1.0, rr * 0.06), 0, 2 * math.pi)
    ctx.set_source_rgba(1, 1, 1, 1)
    ctx.fill()
    if st >= 3:
        a = 0.55 + 0.35 * (0.5 + 0.5 * math.sin(ph * 1.7))
        _flare(ctx, hx - 0.04 * rr, hy, rr * (0.6 + 0.18 * (st - 3)), a, rot=t * 0.4 if st >= 5 else 0.0)
    ctx.restore()


def background():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(0.02, 0.02, 0.05)
    ctx.paint()
    v = cairo.RadialGradient(FL_CX, FL_CY, 100, FL_CX, FL_CY, 900)
    v.add_color_stop_rgba(0, 0.12, 0.08, 0.22, 0.7)
    v.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(v)
    ctx.paint()
    return surf


def draw_flask(ctx, t, best):
    """フラスコの輪郭。いま一番上の色でうっすら光る。"""
    pts = flask_points()
    col = COLORS[best] if COLORS[best] is not None else hsv(t * 0.6)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for wd, al in ((22, 0.12), (12, 0.25), (6, 1.0)):
        ctx.new_path()
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.set_source_rgba(*mix(col, (1, 1, 1), 0.5), al)
        ctx.set_line_width(wd)
        ctx.stroke()
    ctx.new_path()
    ctx.move_to(FL_CX - NECK_HW + 8, OVER_Y)
    ctx.line_to(FL_CX + NECK_HW - 8, OVER_Y)
    ctx.set_dash([10, 8])
    ctx.set_source_rgba(1, 0.35, 0.35, 0.8)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.set_dash([])


def draw_merge_fx(ctx, x, y, st, age):
    """進化の光:色が上がるほど大きく、まぶしく。"""
    col = COLORS[st] if COLORS[st] is not None else hsv(age * 3)
    big = 1 + 0.4 * st
    if age < 0.3:
        k = 1 - age / 0.3
        g = cairo.RadialGradient(x, y, 0, x, y, 80 * big)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.95 * k)
        g.add_color_stop_rgba(0.4, *col, 0.6 * k)
        g.add_color_stop_rgba(1, *col, 0)
        ctx.arc(x, y, 80 * big, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
    if age < 0.7:
        k = 1 - age / 0.7
        ctx.arc(x, y, 30 * big + 160 * big * age, 0, 2 * math.pi)
        ctx.set_source_rgba(*mix(col, (1, 1, 1), 0.4), 0.9 * k)
        ctx.set_line_width(3 + st)
        ctx.stroke()


def draw_chart(ctx, best, t):
    """上の進化表:白→青→緑→紫→赤→金→虹。たどり着いた色は明るく。"""
    y = 485
    xs = [120 + k * 140 for k in range(len(NAMES))]
    for k in range(len(NAMES) - 1):
        text(ctx, "▶", (xs[k] + xs[k + 1]) / 2, y + 6, 22, rgb=(1, 1, 1), sw=0, alpha=0.5)
    for k, x in enumerate(xs):
        reached = k <= best
        rr = 20 + 3 * k
        if reached or k == GOAL:
            draw_hold(ctx, x, y, rr, k, t)
        else:
            draw_hold(ctx, x, y, rr, k, 0.0)
            ctx.arc(x, y, rr * 1.5, 0, 2 * math.pi)
            ctx.set_source_rgba(0.02, 0.02, 0.05, 0.6)
            ctx.fill()
        text(ctx, NAMES[k], x, y + 62, 30, rgb=(1, 1, 1) if reached else (0.55, 0.55, 0.6), sw=6)


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"hold_evolve_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"hold_evolve_{seed}.wav")
    final = os.path.join(OUT_DIR, f"hold_evolve_{seed}.mp4")
    bg = background()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    if preview:
        class _P:
            def __init__(self):
                self.stdin = self
                self.fi = 0

            def write(self, _):
                t_ = (self.fi + 1) / FPS
                for pt in preview:
                    if abs(t_ - pt) < 0.5 / FPS:
                        surf.write_to_png(os.path.join(OUT_DIR, f"he_preview_{pt:.1f}.png"))
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
    fever = RainbowFever(W, H, seed) if not fail else None
    born = {}
    pops = []
    shake = 0.0
    ev_i = 0
    labels = []
    fail_why = next((e[2] for e in events if e[0] == "fail"), "")
    frozen = None
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "merge":
                cid, st, x, y = data
                born[cid] = et
                pops.append([et, x, y, st])
                shake = max(shake, 2 + 3 * st)
                if st >= 3:
                    labels.append((f"{NAMES[st]}保留!!", st, et))
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        if fail and over:   # 失敗したら、決まった瞬間の画面のまま止める
            if frozen is None:
                frozen = fr
            fr = frozen
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        shake *= 0.85
        dx, dy = (math.sin(t * 61) * shake, math.cos(t * 53) * shake) if shake > 0.5 else (0, 0)
        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        if fever is not None and over:
            fever.draw_back(ctx, t - end_t)
        ctx.save()
        ctx.translate(dx, dy)
        draw_flask(ctx, t, fr["best"])
        for cid, st, x, y, ang in sorted(fr["balls"], key=lambda c: c[1]):
            b_t = born.get(cid)
            k = 1.0
            if b_t is not None and t - b_t < 0.25:   # 進化した直後はぷくっとふくらむ
                a = (t - b_t) / 0.25
                k = 0.7 + 0.3 * a + 0.15 * math.sin(a * math.pi)
            draw_hold(ctx, x, y, RADII[st], st, t, ang, k)
        keep = []
        for p in pops:
            age = t - p[0]
            if age < 0.7:
                draw_merge_fx(ctx, p[1], p[2], p[3], age)
                keep.append(p)
        pops = keep
        ctx.restore()
        if fr["over"] is not None and not over and int(t * 6) % 2 == 0:
            text(ctx, "つまりそう！", W / 2, OVER_Y + 70, 56, rgb=(1, 0.35, 0.35), sw=12)
        # 上の文字
        text(ctx, "白保留を", W / 2, 240, 60, sw=12)
        text(ctx, "虹保留にできる？", W / 2, 330, 84, rgb=GOLD, sw=16)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 412, 44, rgb=(1, 0.35, 0.35) if left < 10 else (1, 1, 1), sw=10)
        draw_chart(ctx, fr["best"], t)
        labels = [l_ for l_ in labels if t - l_[2] < 1.0 and not over]
        if labels:
            s_, st, t0 = labels[-1]
            k2 = min(1.0, (t - t0) / 0.12)
            col = COLORS[st] if COLORS[st] is not None else hsv(t)
            text(ctx, s_, W / 2, 800, (60 + 8 * st) * (1.4 - 0.4 * k2), rgb=mix(col, (1, 1, 1), 0.2), sw=14)
        if not over:
            text(ctx, "失敗したら・・・", W / 2, 1530, 54, rgb=(1, 0.45, 0.45), sw=10)
        if over and fail:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 900, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.55)
            ctx.fill()
            text(ctx, "つまった…" if fail_why == "overflow" else "時間切れ…", W / 2, 1010,
                 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"{NAMES[res['best']]}保留までだった…", W / 2, 1130, 66, sw=12)
        elif over:
            fever.draw_front(ctx, t - end_t, text, "虹保留!!", "大当たり確定!!")
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} 最高 {NAMES[res['best']]} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def sweep(f0, f1, dur, amp, vib=0.0, square=0.0, tau=0.06):
    """「キュイン」系の上がる音。f0 から f1 へ一気に上がる。"""
    t = _t(dur)
    f = f0 + (f1 - f0) * (1 - np.exp(-t / tau))
    f = f * (1 + vib * np.sin(2 * np.pi * 30 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.3 * np.sin(2 * ph) + square * np.sign(np.sin(ph)) * 0.5
    env = np.minimum(1, t / 0.008) * np.minimum(1, (dur - t) / 0.06)
    return amp * y * env


def bell(f, dur, amp):
    t = _t(dur)
    y = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t * 6) + 0.25 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t * 10)
    return amp * y * np.exp(-t * 3) * np.minimum(1, t / 0.003)


def brass(root, dur, amp):
    t = _t(dur)
    y = np.zeros_like(t)
    for m in (0, 4, 7, 12):
        f = midi_hz(root + m)
        for h in range(1, 8):
            y += np.sin(2 * np.pi * f * h * t) / h * (0.8 ** h)
    return amp * y / 6 * np.minimum(1, t / 0.02) * np.exp(-t * 2.0)


def drum(amp, seed=1):
    t = _t(0.35)
    kick = np.sin(2 * np.pi * np.cumsum(120 * np.exp(-t * 18) + 45) / SR) * np.exp(-t * 9)
    snare = np.random.default_rng(seed).normal(0, 1, len(t)) * np.exp(-t * 22) * 0.6
    return amp * (kick + snare)


def cymbal(amp, dur=1.2, seed=2):
    t = _t(dur)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    hp = n - np.convolve(n, np.ones(8) / 8, mode="same")
    return amp * hp * np.exp(-t * 3)


def pikiin(amp):
    """「ピキーン!」:高くて金属的な、はりつめた音。"""
    t = _t(1.2)
    y = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d)
            for f, a, d in ((2637, 1.0, 2.5), (3951, 0.6, 3.5), (5274, 0.4, 4.5), (7040, 0.25, 6), (2650, 0.5, 2.5)))
    return amp * y * np.minimum(1, t / 0.002)


def combine(parts):
    n = max(len(p) for _, p in parts)
    out = np.zeros(n + int(1.0 * SR))
    for t0, p in parts:
        i = int(t0 * SR)
        out[i:i + len(p)] += p
    return out


def evolve_sound(st):
    """色ごとにちがう音。色が上がるほど豪華に。"""
    if st == 1:   # 青:ピロン
        return combine([(0, bell(1319, 0.5, 0.5)), (0.08, bell(1976, 0.6, 0.5))])
    if st == 2:   # 緑:キュイン
        return combine([(0, sweep(700, 2600, 0.3, 0.55, 0.02)), (0.05, bell(2093, 0.7, 0.35))])
    if st == 3:   # 紫:ギュイン+鐘の和音
        return combine([(0, sweep(300, 1800, 0.45, 0.6, 0.05, 0.4, 0.1)),
                        (0.1, bell(1047, 1.0, 0.35)), (0.1, bell(1319, 1.0, 0.3)), (0.1, bell(1568, 1.0, 0.3))])
    if st == 4:   # 赤:キュインキュイン+ブラス+ドラム
        return combine([(0, sweep(600, 3000, 0.25, 0.6, 0.03, 0.3)), (0.22, sweep(600, 3000, 0.3, 0.65, 0.03, 0.3)),
                        (0.45, brass(64, 0.9, 0.6)), (0.45, drum(0.7))])
    if st == 5:   # 金:ピキーン!+ファンファーレ+シンバル
        return combine([(0, pikiin(0.6)), (0.15, brass(67, 0.25, 0.45)), (0.3, brass(72, 0.25, 0.5)),
                        (0.45, brass(76, 1.4, 0.7)), (0.45, cymbal(0.4)), (0.45, drum(0.8, 3))])
    if st == 6:   # 虹:長いギュイーン
        return combine([(0, sweep(200, 3200, 1.1, 0.75, 0.04, 0.5, 0.35)), (0, cymbal(0.4, 1.5, 4))])
    return np.zeros(10)


def click(amp, seed):
    """保留玉が落ちて当たる「カチッ」(パチンコ玉のような小さな金属音)。"""
    t = _t(0.08)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    return amp * (np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 70) + 0.5 * np.sin(2 * np.pi * 3700 * t) * np.exp(-t * 90) + 0.3 * n * np.exp(-t * 150))


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)

    def add(sig, t0, gain=1.0, buf=None):
        b = out if buf is None else buf
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out and j > i:
            b[i:j] += gain * sig[: j - i]
    cache = {}
    k = 0
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.01:
            continue
        if kind == "drop":
            add(click(0.35, k), t + 0.25)
            k += 1
        elif kind == "merge":
            st = data[1]
            if st not in cache:
                cache[st] = evolve_sound(st)
            add(cache[st], t, 0.6 + 0.1 * st)
    wet = out.copy()
    for dd, g in ((0.043, 0.2), (0.071, 0.13)):
        kk = int(dd * SR)
        wet[kk:] += out[:-kk] * g
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int(end_t * SR)]
    rms = np.sqrt(np.mean(body ** 2))
    if rms > 0:
        wet *= min(6.0, 10 ** (-14.0 / 20) / rms)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
        sig = fail_music(SR, OUTRO)
        i0 = int((end_t + SCARE_DUR) * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += 0.6 * sig[:m]
    else:
        sig = kyuin_music(SR, FEVER_DUR)
        i0 = int((end_t + 0.6) * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += 0.9 * sig[:m]
        sig = evolve_sound(6)   # 虹のギュイーンは演出と重なっても大きく聞こえるように
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += 0.6 * sig[:m]
    wet = wet + 0.95 * extra[: len(wet)]
    mag = np.abs(wet)
    wet = np.where(mag < 0.7, wet, np.sign(wet) * (0.7 + 0.2 * np.tanh((mag - 0.7) / 0.2)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("-n", type=int, default=40)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
