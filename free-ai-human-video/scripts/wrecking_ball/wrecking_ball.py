"""「鉄球でレンガの塔をこわしきれる?」振り子の鉄球(レッキングボール)がレンガの塔をこわしていく物理ショート。

- 横から見た、レンガを積んだ塔。クレーンからつるした鉄球が振り子のように揺れて、塔にぶつかる。
- クレーンは決まった動き(一定のリズムで台車が前後に揺れる・少しずつ前へ進む・ワイヤーが少しずつのびる)をするだけで、
  鉄球の動きは重力・慣性・衝突のまま(ねらい・補正なし)。
- レンガは強く当たると割れる(割れやすさは1個ずつ少しちがう)。鉄球に当たって割れる・落ちて地面や他のレンガに当たって割れる。
  レンガが1個割れるたびに「ウィリアム・テル序曲」(ロッシーニ・パブリックドメイン)が1音進む。
- 途中で鉄球が2つになり、終盤は鉄球が巨大化する。
- 制限時間内に TARGET 個のレンガを割れば成功(天使)、割れなければ失敗(幽霊)。

使い方:
    python wrecking_ball.py search [-n 200]
    python wrecking_ball.py render --seed N
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
SUBSTEPS = 6
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

GRAVITY = 1800.0
GROUND_Y = 1640.0
# 塔
BW, BH = 64.0, 30.0                         # レンガ1個の大きさ
COLS = int(os.environ.get("COLS", 7))
ROWS = int(os.environ.get("ROWS", 30))
TOWER_X = 620.0                             # 塔の左はし
BREAK = float(os.environ.get("BREAK", 900.0))   # これより強い衝撃で割れる(1個ずつ ±25% ちがう)
BRICK_M = 1.0
# 鉄球とクレーン
BALL_R = 46.0
BALL_M = float(os.environ.get("BALL_M", 30.0))
PIVOT_Y = 330.0
ROPE0 = float(os.environ.get("ROPE0", 820.0))     # 最初のワイヤーの長さ
ROPE1 = float(os.environ.get("ROPE1", 1150.0))    # 最後のワイヤーの長さ(少しずつのびて低い所をねらう…のではなく決まった速さでのびる)
DRIVE_A = float(os.environ.get("DRIVE_A", 220.0))  # 台車が前後に揺れる幅
CRANE_X0, CRANE_X1 = 260.0, 470.0           # 台車の位置(少しずつ前へ)
TARGET = int(os.environ.get("TARGET", 190))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 39.0))
SECOND_AT = int(os.environ.get("SECOND_AT", 110))  # これだけ割ったら鉄球が2つに
GIANT_AT = int(os.environ.get("GIANT_AT", 165))    # これだけ割ったら鉄球が巨大化
GIANT_K = 1.6
OUTRO = 2.5

CT_BALL, CT_BRICK, CT_GROUND = 1, 2, 3


class Crane:
    def __init__(self, space, side, phase, t0):
        self.side = side          # +1: 左から(右へ振る)  -1: 右から
        self.phase = phase
        self.t0 = t0
        self.pivot = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.pivot.position = self.pos(t0)
        L = self.rope(t0)
        b = pymunk.Body(BALL_M, pymunk.moment_for_circle(BALL_M, 0, BALL_R))
        # 最初は、ワイヤーをななめに引いた位置から放す
        a0 = -0.9 * side
        b.position = (self.pivot.position.x + L * math.sin(a0), self.pivot.position.y + L * math.cos(a0))
        s = pymunk.Circle(b, BALL_R)
        s.friction, s.elasticity = 0.5, 0.2
        s.collision_type = CT_BALL
        j = pymunk.SlideJoint(self.pivot, b, (0, 0), (0, 0), 0, L)
        space.add(self.pivot, b, s, j)
        self.ball, self.shape, self.joint = b, s, j
        self.r = BALL_R

    def omega(self, t):
        return math.sqrt(GRAVITY / self.rope(t))

    def rope(self, t):
        u = min(1.0, max(0.0, (t - self.t0) / TIME_LIMIT))
        return ROPE0 + (ROPE1 - ROPE0) * u

    def pos(self, t):
        u = min(1.0, max(0.0, t / TIME_LIMIT))
        if self.side > 0:
            x = CRANE_X0 + (CRANE_X1 - CRANE_X0) * u
        else:
            x = W - 120.0
        return (x + DRIVE_A * math.sin(self.phase + self.omega(t) * (t - self.t0)), PIVOT_Y)

    def update(self, t, dt):
        p0 = self.pivot.position
        p1 = pymunk.Vec2d(*self.pos(t + dt))
        self.pivot.velocity = (p1 - p0) / dt
        self.joint.max = self.rope(t)

    def grow(self, k):
        self.r = BALL_R * k
        self.shape.unsafe_set_radius(self.r)
        m = BALL_M * k ** 2
        self.ball.mass = m
        self.ball.moment = pymunk.moment_for_circle(m, 0, self.r)


class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 25
        sp.collision_slop = 0.3
        self.space = sp
        g = pymunk.Segment(sp.static_body, (-2000, GROUND_Y + 20), (4000, GROUND_Y + 20), 20)
        g.friction, g.elasticity = 0.9, 0.05
        g.collision_type = CT_GROUND
        sp.add(g)
        self.bricks = {}
        for r in range(ROWS):
            y = GROUND_Y - BH / 2 - r * BH
            off = 0.0 if r % 2 == 0 else BW / 2
            xs = []
            x = TOWER_X - off
            while x < TOWER_X + COLS * BW - 1:
                x0, x1 = max(x, TOWER_X), min(x + BW, TOWER_X + COLS * BW)
                if x1 - x0 > 4:
                    xs.append((x0, x1))
                x += BW
            for x0, x1 in xs:
                self.add_brick((x0 + x1) / 2, y, x1 - x0 - 0.6, BH - 0.4)
        self.cranes = [Crane(sp, 1, rng.uniform(0, 2 * math.pi), 0.0)]
        h = sp.add_collision_handler if hasattr(sp, "add_collision_handler") else None
        sp.on_collision(CT_BALL, CT_BRICK, post_solve=self._hit)
        sp.on_collision(CT_BRICK, CT_BRICK, post_solve=self._hit)
        sp.on_collision(CT_BRICK, CT_GROUND, post_solve=self._hit)
        self.to_break = set()
        self.broken = 0
        self.events = []
        self.debris = []
        self.t = 0.0
        self.result, self.result_t = None, None
        self.n_total = len(self.bricks)
        self.giant = False
        self.next_id = 0

    def add_brick(self, x, y, w, h):
        m = BRICK_M * w / BW
        b = pymunk.Body(m, pymunk.moment_for_box(m, (w, h)))
        b.position = (x, y)
        s = pymunk.Poly.create_box(b, (w, h), 0.5)
        s.friction, s.elasticity = 0.7, 0.05
        s.collision_type = CT_BRICK
        self.space.add(b, s)
        self.bricks[b] = {"shape": s, "w": w, "h": h, "str": BREAK * self.rng_strength(),
                          "id": len(self.bricks) + 1000 * 0}

    def rng_strength(self):
        return float(np.random.default_rng(len(self.bricks) * 7919 + int(self.rng.integers(1 << 30))).uniform(0.75, 1.25))

    def _hit(self, arb, space, data):
        imp = arb.total_impulse.length
        for sh in arb.shapes:
            info = self.bricks.get(sh.body)
            if info is not None and imp > info["str"] * (info["w"] / BW):
                self.to_break.add(sh.body)

    def step(self, dt):
        for c in self.cranes:
            c.update(self.t, dt)
        self.t += dt
        self.space.step(dt)
        for b in list(self.to_break):
            info = self.bricks.pop(b, None)
            if info is None:
                continue
            self.space.remove(b, info["shape"])
            self.broken += 1
            self.events.append(("break", self.t, (b.position.x, b.position.y, b.angle, info["w"], info["h"])))
        self.to_break.clear()
        # レンガが画面の外へ飛んでいったら消す(数えない)
        for b in list(self.bricks):
            if b.position.y > GROUND_Y + 300 or abs(b.position.x - W / 2) > 1400:
                info = self.bricks.pop(b)
                self.space.remove(b, info["shape"])
        if len(self.cranes) == 1 and self.broken >= SECOND_AT:
            self.cranes.append(Crane(self.space, -1, self.rng.uniform(0, 2 * math.pi), self.t))
            self.events.append(("second", self.t, None))
        if not self.giant and self.broken >= GIANT_AT:
            self.giant = True
            for c in self.cranes:
                c.grow(GIANT_K)
            self.events.append(("giant", self.t, None))
        if self.result is None:
            if self.broken >= TARGET:
                self.result, self.result_t = "success", self.t
                self.final_broken = self.broken
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT:
                self.result, self.result_t = "fail", self.t
                self.final_broken = self.broken
                self.events.append(("fail", self.t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "bricks": [(b.position.x, b.position.y, b.angle, i["w"], i["h"], id(b) % 997)
                                                 for b, i in g.bricks.items()],
                           "cranes": [(c.pivot.position.x, c.pivot.position.y, c.ball.position.x, c.ball.position.y,
                                       c.ball.angle, c.r) for c in g.cranes],
                           "broken": g.broken})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "broken": g.final_broken, "total": g.n_total}


def score(seed):
    r = simulate(seed)
    ev = r["events"]
    ts = [e[1] for e in ev if e[0] == "break"]
    sec = next((e[1] for e in ev if e[0] == "second"), None)
    gi = next((e[1] for e in ev if e[0] == "giant"), None)
    return seed, r["result"], round(r["result_t"], 1), r["broken"], r["total"], sec and round(sec, 1), gi and round(gi, 1)


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def background():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, GROUND_Y)
    g.add_color_stop_rgb(0, 0.12, 0.1, 0.25)
    g.add_color_stop_rgb(0.6, 0.55, 0.3, 0.35)
    g.add_color_stop_rgb(1, 0.95, 0.6, 0.35)
    c.set_source(g)
    c.paint()
    rng = np.random.default_rng(3)
    x = -20
    while x < W:   # 遠くのビル(シルエット)
        w = rng.uniform(50, 120)
        h = rng.uniform(150, 420)
        c.rectangle(x, GROUND_Y - h, w, h)
        c.set_source_rgba(0.18, 0.12, 0.2, 0.85)
        c.fill()
        for _ in range(int(h / 40)):
            c.rectangle(x + rng.uniform(6, w - 14), GROUND_Y - rng.uniform(20, h - 10), 7, 9)
            c.set_source_rgba(1, 0.85, 0.5, rng.uniform(0.2, 0.7))
            c.fill()
        x += w + rng.uniform(5, 25)
    g = cairo.LinearGradient(0, GROUND_Y, 0, H)
    g.add_color_stop_rgb(0, 0.42, 0.32, 0.22)
    g.add_color_stop_rgb(1, 0.18, 0.13, 0.1)
    c.rectangle(0, GROUND_Y, W, H - GROUND_Y)
    c.set_source(g)
    c.fill()
    return surf


def draw_crane(ctx, side, px, py):
    """クレーン(柱・うで・台車)。"""
    mx = 70.0 if side > 0 else W - 50.0
    ctx.set_source_rgb(0.95, 0.72, 0.1)
    ctx.set_line_width(5)
    for xo in (-16, 16):
        ctx.move_to(mx + xo, GROUND_Y)
        ctx.line_to(mx + xo, py - 70)
    ctx.stroke()
    y = GROUND_Y
    k = 0
    while y > py - 70:   # 柱の筋交い
        ctx.move_to(mx - 16, y)
        ctx.line_to(mx + 16, y - 40)
        y -= 40
        k += 1
    ctx.set_line_width(2.5)
    ctx.stroke()
    x_end = 760.0 if side > 0 else 680.0
    ctx.set_line_width(6)
    ctx.move_to(mx - 40 * side, py - 30)
    ctx.line_to(x_end if side > 0 else W - x_end, py - 30)
    ctx.move_to(mx - 40 * side, py - 6)
    ctx.line_to(x_end if side > 0 else W - x_end, py - 6)
    ctx.stroke()
    ctx.set_line_width(3)
    x = mx
    while (x < x_end) if side > 0 else (x > W - x_end):
        ctx.move_to(x, py - 6)
        ctx.line_to(x + 30 * side, py - 30)
        x += 30 * side
    ctx.stroke()
    ctx.rectangle(px - 26, py - 12, 52, 22)   # 台車
    ctx.set_source_rgb(0.3, 0.3, 0.33)
    ctx.fill()


def draw_ball(ctx, px, py, bx, by, r, glow=0.0):
    ctx.set_source_rgb(0.15, 0.15, 0.17)
    ctx.set_line_width(4)
    ctx.move_to(px, py)
    ctx.line_to(bx, by)
    ctx.stroke()
    g = cairo.RadialGradient(bx - r * 0.35, by - r * 0.4, r * 0.08, bx, by, r)
    g.add_color_stop_rgb(0, 0.85, 0.86, 0.9)
    g.add_color_stop_rgb(0.45, 0.35, 0.36, 0.4)
    g.add_color_stop_rgb(1, 0.08, 0.08, 0.1)
    ctx.set_source(g)
    ctx.arc(bx, by, r, 0, 2 * math.pi)
    ctx.fill()
    if glow > 0:
        ctx.arc(bx, by, r * 1.15, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.6, 0.2, 0.35 * glow)
        ctx.set_line_width(8)
        ctx.stroke()


def brick_col(k):
    rng = np.random.default_rng(k)
    return (0.62 + rng.uniform(-0.08, 0.08), 0.26 + rng.uniform(-0.05, 0.05), 0.18 + rng.uniform(-0.04, 0.04))


def draw_brick(ctx, x, y, ang, w, h, col):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.rectangle(-w / 2, -h / 2, w, h)
    g = cairo.LinearGradient(0, -h / 2, 0, h / 2)
    g.add_color_stop_rgb(0, *(min(1, c * 1.25) for c in col))
    g.add_color_stop_rgb(1, *(c * 0.75 for c in col))
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(0.85, 0.8, 0.72)   # 目地
    ctx.set_line_width(2)
    ctx.stroke()
    ctx.restore()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"wrecking_ball_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"wrecking_ball_{seed}.wav")
    final = os.path.join(OUT_DIR, f"wrecking_ball_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"wb_preview_{pt:.1f}.png"))
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
    bg = background()
    rng = np.random.default_rng(seed + 5)
    frags = []    # 割れたレンガのかけら [x, y, vx, vy, rot, vr, size, col, t0]
    dusts = []    # 土けむり [x, y, r, t0]
    shake = 0.0
    second_t = giant_t = None
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "break":
                x, y, ang, w, h = data
                col = brick_col(int(x * 7 + y * 3))
                for _ in range(7):
                    a = rng.uniform(0, 2 * math.pi)
                    v = rng.uniform(100, 520)
                    frags.append([x + rng.uniform(-w / 3, w / 3), y + rng.uniform(-h / 3, h / 3), v * math.cos(a),
                                  v * math.sin(a) - 250, rng.uniform(0, 6), rng.uniform(-12, 12),
                                  rng.uniform(7, 16), col, et])
                dusts.append([x, y, rng.uniform(30, 55), et])
                shake = max(shake, 5.0)
            elif kind == "second":
                second_t = et
            elif kind == "giant":
                giant_t = et
                shake = max(shake, 14)
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0
        shake *= 0.85
        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        ctx.save()
        if shake > 0.5:
            ctx.translate(math.sin(t * 61) * shake, math.cos(t * 47) * shake)
        for k, (px, py, bx, by, ba, r) in enumerate(fr["cranes"]):
            draw_crane(ctx, 1 if k == 0 else -1, px, py)
        for x, y, ang, w, h, k in fr["bricks"]:
            draw_brick(ctx, x, y, ang, w, h, brick_col(k))
        for k, (px, py, bx, by, ba, r) in enumerate(fr["cranes"]):
            gl = max(0.0, 1 - (t - giant_t) / 1.0) if giant_t is not None and t >= giant_t else 0.0
            draw_ball(ctx, px, py, bx, by, r, gl)
        keep = []
        for f in frags:   # かけら(見た目だけ。地面で止まって消える)
            a = t - f[8]
            if a > 1.4:
                continue
            x = f[0] + f[2] * a
            y = min(GROUND_Y - 4, f[1] + f[3] * a + 0.5 * GRAVITY * a * a)
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(f[4] + f[5] * a)
            s_ = f[6]
            ctx.move_to(-s_, -s_ * 0.5)
            ctx.line_to(s_ * 0.8, -s_ * 0.7)
            ctx.line_to(s_ * 0.5, s_ * 0.6)
            ctx.line_to(-s_ * 0.6, s_ * 0.4)
            ctx.close_path()
            ctx.set_source_rgba(*f[7], 1 - max(0, a - 1.0) / 0.4)
            ctx.fill()
            ctx.restore()
            keep.append(f)
        frags = keep
        keep = []
        for d_ in dusts:
            a = t - d_[3]
            if a > 1.2:
                continue
            g = cairo.RadialGradient(d_[0], d_[1], 0, d_[0], d_[1], d_[2] * (1 + 2 * a))
            g.add_color_stop_rgba(0, 0.8, 0.65, 0.5, 0.45 * (1 - a / 1.2))
            g.add_color_stop_rgba(1, 0.8, 0.65, 0.5, 0)
            ctx.set_source(g)
            ctx.arc(d_[0], d_[1], d_[2] * (1 + 2 * a), 0, 2 * math.pi)
            ctx.fill()
            keep.append(d_)
        dusts = keep
        ctx.restore()
        if angels is not None and over:
            angels.draw(ctx, t - end_t)
        g = cairo.LinearGradient(0, 0, 0, 330)
        g.add_color_stop_rgba(0, 0.05, 0.04, 0.1, 0.9)
        g.add_color_stop_rgba(1, 0.05, 0.04, 0.1, 0.0)
        ctx.rectangle(0, 0, W, 330)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, "鉄球でレンガを", W / 2, 120, 76, sw=12)
        text(ctx, f"{TARGET}個こわせる？", W / 2, 240, 110, rgb=GOLD, sw=18)
        n = min(fr["broken"], TARGET) if not (end_t is not None and t >= end_t) else min(res["broken"], TARGET)
        text(ctx, f"こわした {n} / {TARGET}", W / 2, 1745, 64, sw=12)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 1840, 56, rgb=(1, 0.4, 0.4) if left < 8 else (0.95, 0.95, 0.95), sw=10)
        if second_t is not None and 0 <= t - second_t < 1.6:
            k2 = min(1.0, (t - second_t) / 0.15)
            text(ctx, "鉄球が2つに!", W / 2, 420, 96 * (1.25 - 0.25 * k2), rgb=(0.6, 1, 0.8), sw=16)
        if giant_t is not None and 0 <= t - giant_t < 1.6:
            k2 = min(1.0, (t - giant_t) / 0.15)
            text(ctx, "鉄球が巨大化!!", W / 2, 420, 100 * (1.25 - 0.25 * k2), rgb=(1, 0.6, 0.3), sw=16)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 900, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{TARGET - res['broken']}個だったのに…", W / 2, 1030, 72, sw=12)
        elif over:
            age = t - end_t
            if age < 0.3:
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.8 * (1 - age / 0.3))
                ctx.fill()
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['broken']}個 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
sys.path.insert(0, os.path.join(HERE, "..", "giant_domino"))
import giant_domino as GD  # noqa: E402

HOLY_GAIN = 0.85
# 「ウィリアム・テル序曲」終曲の有名な部分(ロッシーニ・1829年・パブリックドメイン)。(MIDI番号, 長さ[16分音符])
_P1 = [(64, 1), (64, 1), (64, 2), (64, 1), (64, 1), (64, 2), (64, 1), (64, 1), (69, 2), (71, 2), (73, 2)]
_P2 = [(64, 1), (64, 1), (64, 2), (64, 1), (64, 1), (69, 2), (73, 2), (71, 2), (68, 2), (64, 2)]
_P4 = [(64, 1), (64, 1), (69, 2), (73, 2), (76, 2), (73, 2), (69, 4)]
TELL = _P1 + _P2 + _P1 + _P4
SIXTEENTH = 0.1


def crunch(seed, amp):
    """レンガが割れる「ガシャッ」。"""
    t = GD._t(0.35)
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, len(t))
    n = np.convolve(n, np.ones(3) / 3, "same")
    thud = np.sin(2 * np.pi * rng.uniform(70, 110) * t) * np.exp(-t * 18)
    return amp * (0.8 * n * np.exp(-t * 22) + 0.7 * thud)


def tell_note(m, amp, big):
    f = midi_hz(m)
    root = 45 if m % 12 not in (8, 11) else 40   # A か E
    if not big:
        return GD.mix(GD.brass(f, amp, 0.35), GD.strings(f, amp * 0.5, 0.4), GD.piano(midi_hz(root), amp * 0.5))
    return GD.mix(GD.brass(f, amp, 0.4), GD.brass(f / 2, amp * 0.6, 0.4), GD.strings(f * 2, amp * 0.35, 0.4),
                  GD.brass(midi_hz(root), amp * 0.6, 0.4), GD.timpani(amp * 0.3, 0.4))


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

    note_i = -1
    next_ok = 0.0
    last_c = -1.0
    big = False
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.02:
            continue
        if kind == "break":
            if t - last_c > 0.03:
                add(crunch(int(t * 1000), 0.35), t)
                last_c = t
            if t >= next_ok:   # 割れるたびに曲が1音進む(速く割れても本来のテンポ)
                note_i += 1
                m, du = TELL[note_i % len(TELL)]
                add(tell_note(m, 0.6, big), t)
                next_ok = t + du * SIXTEENTH - 0.01
        elif kind == "second":
            add(GD.mix(GD.brass(midi_hz(57), 0.5, 0.6), GD.brass(midi_hz(64), 0.4, 0.6)), t)
        elif kind == "giant":
            big = True
            add(GD.timpani(1.0, 1.5), t)
            add(GD.mix(*[GD.brass(midi_hz(m_), 0.45, 0.9) for m_ in (45, 52, 57, 61, 64)]), t)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:
        add(GD.mix(*[GD.mix(GD.brass(midi_hz(m_), 0.5, 2.2), GD.strings(midi_hz(m_), 0.35, 2.5)) for m_ in (45, 57, 61, 64, 69)]), end_t)
        add(GD.timpani(1.0, 2.0), end_t)
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
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("-n", type=int, default=100)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
