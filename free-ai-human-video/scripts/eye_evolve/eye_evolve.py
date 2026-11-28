"""「光る瞳の玉を、虹の瞳まで進化させられる?」首のついた丸いフラスコに、赤く光る瞳の玉が上から落ちてきて、
同じ段階どうしが触れると次の段階に進化(合体)する物理ショート。

- 進化の順番(7段階・模様はすべてオリジナル):点 → 輪 → 花びら2 → 花びら3 → 星 → うずまき → 虹の瞳(ゴール)
  段階が上がるほど玉が大きくなり、光が強くなる。
- 落ちてくるのはいつも「点」の瞳。落ちる間隔はだんだん短くなる。
- 重力・反発・摩擦のまま自然に落ちて転がる(ねらい・補正なし)。玉が転がると瞳の模様も一緒に回る。
- 合体は「同じ段階どうしが触れたら」必ず起きる(1回の接触で1回)。
- 虹の瞳ができれば成功(大当たり演出)、首までつまってあふれるか時間切れなら失敗(幽霊 → 暗くなって「Failed...」)。
- 絵・音はすべてプログラムで作ったオリジナル。

使い方:
    python eye_evolve.py search [-n 80]
    python eye_evolve.py render --seed N
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
from pachinko import RainbowFever, kyuin_music  # noqa: E402
from flashy import PALETTE, chic, draw_ball as shiny_ball, giragira, horror, kyuin_one  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "glass_spiral"))
import jackpot_end as JP  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
GRAVITY = 1500.0
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

NAMES = ["点", "輪", "花びら2", "花びら3", "星", "うずまき", "虹の瞳"]
GOAL = len(NAMES) - 1
RADII = [22, 31, 44, 61, 82, 108, 140]   # 保留玉の大きさ(半径)。色が上がるほど大きい
COLORS = [(1.0, 0.25, 0.25), (1.0, 0.2, 0.22), (1.0, 0.16, 0.2), (1.0, 0.12, 0.18),
          (1.0, 0.1, 0.15), (1.0, 0.08, 0.12), None]

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
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 49.45))
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG


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
        b = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, r))
        b.position = (x, y)
        b.velocity, b.angular_velocity = (vx, vy), w
        s = pymunk.Circle(b, r)
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
            extra = OUTRO + SCARE_DUR if g.result == "fail" else PRE + WIN_DUR
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
    """光る瞳の玉(オリジナルの模様)。ang で模様が回る。k はふくらみ。"""
    r *= k
    ink = (0.05, 0.0, 0.02)
    # まわりの光(段階が上がるほど強い)
    gl = 1.25 + 0.08 * st
    col = (1, 0.2, 0.2) if st < GOAL else hsv(t * 0.5)
    g = cairo.RadialGradient(x, y, r * 0.8, x, y, r * gl * 1.2)
    g.add_color_stop_rgba(0, *col, 0.18 + 0.05 * st)
    g.add_color_stop_rgba(1, *col, 0)
    ctx.arc(x, y, r * gl * 1.2, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    # ひとみの色
    if st < GOAL:
        g = cairo.RadialGradient(x, y, r * 0.1, x, y, r)
        g.add_color_stop_rgb(0, 1, 0.4, 0.33)
        g.add_color_stop_rgb(0.7, 0.85, 0.08, 0.12)
        g.add_color_stop_rgb(1, 0.33, 0, 0.02)
    else:
        g = cairo.LinearGradient(x - r, y - r, x + r, y + r)
        for j in range(7):
            g.add_color_stop_rgb(j / 6, *hsv((j / 7 + t * 0.3) % 1.0, 0.8, 1.0))
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    lw = max(1.5, r * 0.06)
    if st >= 1:
        ctx.arc(0, 0, r * 0.55, 0, 2 * math.pi)
        ctx.set_source_rgb(*ink)
        ctx.set_line_width(lw)
        ctx.stroke()
    if st in (2, 3):     # 花びら(だ円)
        for j in range(st):
            a = 2 * math.pi * j / st + 0.3
            ctx.save()
            ctx.rotate(a)
            ctx.translate(r * 0.42, 0)
            ctx.scale(r * 0.42, r * 0.16)
            ctx.arc(0, 0, 1, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgb(*ink)
            ctx.fill()
    if st == 4:          # 星
        ctx.move_to(r * 0.8, 0)
        for j in range(1, 11):
            a = math.pi * j / 5
            rr = r * (0.8 if j % 2 == 0 else 0.35)
            ctx.line_to(rr * math.cos(a), rr * math.sin(a))
        ctx.close_path()
        ctx.set_source_rgb(*ink)
        ctx.set_line_width(lw)
        ctx.stroke()
    if st >= 5:          # うずまき
        ctx.move_to(0, 0)
        for j in range(120):
            a = j * 0.16
            rr = r * 0.75 * j / 120
            ctx.line_to(rr * math.cos(a), rr * math.sin(a))
        ctx.set_source_rgb(*((1, 1, 1) if st == GOAL else ink))
        ctx.set_line_width(lw)
        ctx.stroke()
    ctx.arc(0, 0, r * 0.14, 0, 2 * math.pi)
    ctx.set_source_rgb(*ink)
    ctx.fill()
    ctx.restore()
    # 光の反射(回らない)
    ctx.arc(x - r * 0.3, y - r * 0.35, r * 0.12, 0, 2 * math.pi)
    ctx.set_source_rgba(1, 1, 1, 0.75)
    ctx.fill()
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source_rgba(1, 0.75, 0.7, 0.35)
    ctx.set_line_width(max(1.0, r * 0.03))
    ctx.stroke()


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    shiny_ball(ctx, x, y, r * 0.8, PALETTE[(kind * 12 // 7) % 12])


def failed_text(ctx, s, x, y, size, alpha):
    """失敗の文字:Playfair Display の斜体。暗い赤で、うっすら赤黒くにじむ。"""
    if alpha <= 0:
        return
    ctx.select_font_face("Playfair Display", cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    e = ctx.text_extents(s)
    if e.width > W * 0.86:
        size *= W * 0.86 / e.width
        ctx.set_font_size(size)
        e = ctx.text_extents(s)
    tx = x - e.width / 2 - e.x_bearing
    for wd, al in ((30, 0.10), (16, 0.18)):
        ctx.move_to(tx, y)
        ctx.text_path(s)
        ctx.set_source_rgba(0.45, 0.02, 0.05, al * alpha)
        ctx.set_line_width(wd)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    g = cairo.LinearGradient(0, y - size * 0.8, 0, y + size * 0.1)
    g.add_color_stop_rgba(0, 0.85, 0.25, 0.28, alpha)
    g.add_color_stop_rgba(1, 0.45, 0.05, 0.08, alpha)
    ctx.move_to(tx, y)
    ctx.text_path(s)
    ctx.set_source(g)
    ctx.fill()



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
        chic(ctx, "›", (xs[k] + xs[k + 1]) / 2, y + 10, 30, rgb=(1, 1, 1), alpha=0.5)
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
        chic(ctx, NAMES[k], x, y + 60, 22, rgb=(1, 1, 1) if reached else (0.5, 0.5, 0.55), weight="Medium")


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"eye_evolve_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"eye_evolve_{seed}.wav")
    final = os.path.join(OUT_DIR, f"eye_evolve_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"ee_preview_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, FL_CX, FL_CY, reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=("Congratulations!!", "RAINBOW EYE", ""), font="Playfair Display", slim=True)
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
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
            ev_i += 1
        over = end_t is not None and t >= end_t
        win_b = (t - end_t) if (ending is not None and over) else -1.0
        if win_b >= PRE:
            ending.draw(surf, ctx, win_b - PRE + JP.T_BIG)
            giragira(ctx, win_b - PRE, fever, glints, W, H, WIN_DUR)
            ff.stdin.write(surf.get_data())
            continue
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
            chic(ctx, "つまりそう…", W / 2, OVER_Y + 70, 48, rgb=(1, 0.4, 0.4))
        # 上の文字(最小限)
        chic(ctx, "虹の瞳にできる？", W / 2, 230, 66, rgb=(1, 0.88, 0.6))
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        chic(ctx, f"{left:4.1f}", W / 2, 330, 48, rgb=(1, 0.45, 0.45) if left < 5 else (0.7, 0.75, 0.85), weight="Medium")
        draw_chart(ctx, fr["best"], t)
        if not over:
            horror(ctx, "失敗したら…", W / 2, 1600, 74, t)
        if over and fail:
            ctx.set_operator(cairo.OPERATOR_HSL_SATURATION)
            ctx.set_source_rgba(0.5, 0.5, 0.5, min(1.0, after / 0.8))
            ctx.paint()
            ctx.set_operator(cairo.OPERATOR_OVER)
            ctx.set_source_rgba(0, 0, 0, 0.6 * min(1.0, after / 1.2))
            ctx.paint()
            vg = cairo.RadialGradient(W / 2, H / 2, 300, W / 2, H / 2, 1150)
            vg.add_color_stop_rgba(0, 0, 0, 0, 0)
            vg.add_color_stop_rgba(1, 0, 0, 0, 0.85 * min(1.0, after / 1.2))
            ctx.set_source(vg)
            ctx.paint()
            k = min(1.0, max(0.0, (after - 0.2) / 1.4))
            k = k * k * (3 - 2 * k)
            failed_text(ctx, "Failed...", W / 2, 1010 + 40 * (1 - k), 160, k)
        if win_b >= 0:
            k = win_b / PRE
            ph_ = (win_b * (8 + 14 * k)) % 1.0
            ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*hsv(win_b * 4), (0.25 + 0.4 * k) * (1 - ph_) ** 2)
            ctx.paint()
            ctx.set_operator(cairo.OPERATOR_OVER)
            if k > 0.75:
                ctx.set_source_rgba(1, 1, 1, ((k - 0.75) / 0.25) ** 2)
                ctx.paint()
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


def pad(root, dur, amp, notes=(0, 4, 7, 12, 16)):
    """ふわっと広がるストリングス/クワイア風の和音(少しずつずらした音を重ねて厚く)。"""
    t = _t(dur)
    y = np.zeros_like(t)
    for m in notes:
        f = midi_hz(root + m)
        for det in (-0.004, 0.0, 0.004):
            ph = 2 * np.pi * f * (1 + det) * t
            y += np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)
    env = np.minimum(1, t / 0.12) * np.minimum(1, (dur - t) / 0.5)
    return amp * y / (len(notes) * 3) * env


def glitter(root, n, step, amp, up=True):
    """キラキラと駆け上がる鐘のアルペジオ。"""
    seq = [0, 4, 7, 12, 16, 19, 24, 28, 31, 36]
    parts = []
    for k in range(n):
        m = seq[k % len(seq)] + 12 * (k // len(seq))
        parts.append((k * step, bell(midi_hz(root + (m if up else 36 - m)), 0.9, amp)))
    return combine(parts)


def timpani(amp, dur=1.6):
    t = _t(dur)
    return amp * (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82 * t)) * np.exp(-t * 2.2) * np.minimum(1, t / 0.005)


def sub_boom(amp, dur=1.8):
    """お腹にひびく低い「ドーン」。"""
    t = _t(dur)
    f = 30 + 60 * np.exp(-t * 6)
    return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.8) * np.minimum(1, t / 0.004)


def reverb(x, wet, length=1.8):
    """ホールのような残響(くし形フィルタを重ねた簡単なリバーブ)。豪華さ・広がりを出す。"""
    n = len(x) + int(length * SR)
    y = np.zeros(n)
    y[:len(x)] = x
    out = y.copy()
    for d, g in ((0.0297, 0.78), (0.0371, 0.76), (0.0411, 0.74), (0.0437, 0.72)):
        k = int(d * SR)
        buf = y.copy()
        for i0 in range(k, n, k):   # くし形フィルタ(ブロックごとに計算して速く)
            buf[i0:i0 + k] += g * buf[i0 - k:i0 - k + len(buf[i0:i0 + k])]
        out += wet * 0.25 * buf
    fade = np.minimum(1, (n - np.arange(n)) / (0.3 * SR))
    return out * fade


def evolve_sound(st):
    """色ごとにちがう音。色が上がるほど、音が重なって豪華に・残響も深く。"""
    if st == 1:   # 青:ピロン+小さなキラキラ
        x = combine([(0, bell(1319, 0.5, 0.5)), (0.08, bell(1976, 0.6, 0.5)), (0.16, glitter(84, 4, 0.04, 0.12))])
        return reverb(x, 0.25, 1.0)
    if st == 2:   # 緑:キュイン+駆け上がるキラキラ
        x = combine([(0, sweep(700, 2600, 0.3, 0.55, 0.02)), (0.05, bell(2093, 0.7, 0.35)),
                     (0.1, glitter(79, 6, 0.035, 0.15)), (0.05, pad(67, 0.9, 0.25))])
        return reverb(x, 0.35, 1.3)
    if st == 3:   # 紫:ギュイン+鐘の和音+ストリングス+キラキラ
        x = combine([(0, sweep(300, 1800, 0.45, 0.6, 0.05, 0.4, 0.1)),
                     (0.1, bell(1047, 1.2, 0.35)), (0.1, bell(1319, 1.2, 0.3)), (0.1, bell(1568, 1.2, 0.3)),
                     (0.1, pad(65, 1.4, 0.4)), (0.15, glitter(77, 8, 0.035, 0.16))])
        return reverb(x, 0.45, 1.6)
    if st == 4:   # 赤:キュインキュイン+ブラス+ドラム+ストリングス+キラキラの滝
        x = combine([(0, sweep(600, 3000, 0.25, 0.6, 0.03, 0.3)), (0.22, sweep(600, 3000, 0.3, 0.65, 0.03, 0.3)),
                     (0.45, brass(64, 1.1, 0.65)), (0.45, drum(0.75)), (0.45, pad(64, 1.8, 0.5)),
                     (0.45, glitter(76, 10, 0.03, 0.18)), (0.45, cymbal(0.25, 1.2, 7))])
        return reverb(x, 0.55, 2.0)
    if st == 5:   # 金:ピキーン!+3連ファンファーレ+ティンパニ+ストリングス+ハープ風の駆け上がり
        x = combine([(0, pikiin(0.6)), (0.15, brass(67, 0.22, 0.45)), (0.3, brass(72, 0.22, 0.5)),
                     (0.45, brass(76, 1.8, 0.75)), (0.45, brass(64, 1.8, 0.45)), (0.45, cymbal(0.45, 1.8)),
                     (0.45, timpani(0.9)), (0.45, pad(67, 2.4, 0.6)), (0.45, glitter(79, 14, 0.028, 0.2)),
                     (0.45, sub_boom(0.6))])
        return reverb(x, 0.65, 2.4)
    if st == 6:   # 虹:長いギュイーン+低いドーン+全部
        x = combine([(0, sweep(200, 3200, 1.1, 0.75, 0.04, 0.5, 0.35)), (0, cymbal(0.4, 1.5, 4)),
                     (1.0, sub_boom(0.9, 2.4)), (1.0, timpani(1.0, 2.0)), (1.0, pad(72, 3.0, 0.6)),
                     (1.0, glitter(84, 16, 0.025, 0.2))])
        return reverb(x, 0.7, 2.8)
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
        wet *= min(6.0, 10 ** (-15.0 / 20) / rms)
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
        b_ = JP.music(SR, 3)
        b_ = b_.mean(axis=1) if b_.ndim == 2 else b_
        b_ = b_[int(JP.T_BIG * SR) - int(0.05 * SR):]
        n = int(WIN_DUR * SR)
        mus = np.zeros(n)
        mus[:min(n, len(b_))] += b_[:n] / (np.abs(b_).max() + 1e-9)
        a_ = kyuin_music(SR, WIN_DUR)
        mus[:min(n, len(a_))] += 0.8 * a_[:n]
        t2 = 0.0
        while t2 < WIN_DUR - 0.5:
            ky = kyuin_one(1.0 + 0.15 * ((int(t2 / 0.3)) % 3))
            i = int(t2 * SR)
            m = min(len(ky), n - i)
            mus[i:i + m] += 0.4 * ky[:m]
            t2 += 0.3
        tb = np.arange(int(1.5 * SR)) / SR
        boom = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-tb * 6) + 35) / SR) * np.exp(-tb * 2.5)
        mus[:len(boom)] += 0.9 * boom
        mus *= np.minimum(1, (WIN_DUR - np.arange(n) / SR) / 0.6)
        mus = np.tanh(1.6 * mus / (np.abs(mus).max() + 1e-9)) / np.tanh(1.6)
        i0 = int((end_t + PRE) * SR)
        m = min(len(mus), n_out - i0)
        extra[i0:i0 + m] += 1.1 * mus[:m]
        t2 = 0.0
        while t2 < PRE - 0.05:
            k = t2 / PRE
            ky = kyuin_one(1.0 + 0.6 * k)
            i = int((end_t + t2) * SR)
            m = min(len(ky), n_out - i)
            extra[i:i + m] += (0.35 + 0.35 * k) * ky[:m]
            t2 += 0.11 - 0.05 * k
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
