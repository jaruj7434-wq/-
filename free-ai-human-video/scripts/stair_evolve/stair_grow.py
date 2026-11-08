"""「小石は階段を落ちて巨大化できる?」光る階段を転がり落ちる小石が、新しい段に当たるたびにどんどん大きくなっていく物理ショート。

参考動画(猫が階段を落ちるたびに大きくなる)と同じく、当たるたびに大きく・重くなる(1回で約1.2倍)。
- 新しい段に初めて当たるたびに1段階大きくなる(同じ段に何度当たっても1回だけ)。LEVELS 回大きくなれば「巨大化成功」。
- 大きく重くなるほど大きく跳ねて段を飛ばしやすい。階段の一番下の床(GOAL)に着く前に巨大化できれば成功、
  できなかったら失敗(幽霊)。段の上で止まっても失敗。動きは自然な物理のまま(ねらい・補正なし)。
- 大きくなるたびに「ボヨン」という面白い音が鳴り、大きくなるほど低く・大きくなる。

使い方:
    python stair_grow.py search [--want fail|success] [-n 200]
    python stair_grow.py render --seed N
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
from ball_escape import text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
sys.path.insert(0, HERE)
import space_items as S  # noqa: E402
import space_fever as FV  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

# ---------------------------------------------------------------- 物理の設定
GOAL = int(os.environ.get("LEVELS", 12))                # 何回大きくなれば巨大化成功か
R0, GROW = 16.0, float(os.environ.get("GROW", 1.2))     # 最初の大きさ(半径 px)と、1回で大きくなる倍率
RADII = [R0 * GROW ** k for k in range(GOAL + 1)]
DENSITY = [1.0] * (GOAL + 1)


def mult(st):
    return RADII[st] / RADII[0]
GRAVITY = 1500.0
ELAST = float(os.environ.get("ELAST", 0.35))             # 反発係数(跳ねやすさ)
FRICTION = float(os.environ.get("FRICTION", 0.35))
N_STEPS = int(os.environ.get("N_STEPS", 16))             # 床の前にある段の数
STEP_W = (float(os.environ.get("STEP_W0", 380)), float(os.environ.get("STEP_W1", 900)))   # 段の奥行き(最初 → 最後)
STEP_H = (float(os.environ.get("STEP_H0", 150)), float(os.environ.get("STEP_H1", 300)))   # 段の高さ(最初 → 最後)
EVOLVE_EVERY = int(os.environ.get("EVOLVE_EVERY", 1))   # 新しい段に何回当たると1段階進化するか
TILT = float(os.environ.get("TILT", 0.24))                                            # 段がほんの少し下り坂(止まらないように)
FLOOR_W = 3000.0
MAX_T = 40.0
OUTRO = 2.5
STOP_WAIT = 2.0
FEVER_DELAY = 1.2                                       # 太陽になってからフィーバーが始まるまで                                         # 床の上で止まってから失敗確定まで


def build_stairs(rng):
    """段のリスト [(x0, y0, x1, y1, x_riser_bottom_y)] と床。画面の左上から右下へ下っていく。"""
    steps = []
    x, y = 0.0, 0.0
    for i in range(N_STEPS):
        f = i / max(1, N_STEPS - 1)
        w = (STEP_W[0] + (STEP_W[1] - STEP_W[0]) * f) * rng.uniform(0.85, 1.15)
        h = (STEP_H[0] + (STEP_H[1] - STEP_H[0]) * f) * rng.uniform(0.85, 1.15)
        x1, y1 = x + w, y + w * TILT
        steps.append((x, y, x1, y1, y1 + h))
        x, y = x1, y1 + h
    floor = (x, y, x + FLOOR_W, y)
    return steps, floor


class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 30
        self.space = sp
        self.steps, self.floor = build_stairs(self.rng)
        st = sp.static_body
        self.seg_step = {}
        for i, (x0, y0, x1, y1, yb) in enumerate(self.steps):
            for a, b in (((x0, y0), (x1, y1)), ((x1, y1), (x1, yb))):   # 踏み面と、下へ下りるかべ
                s = pymunk.Segment(st, a, b, 3)
                s.elasticity, s.friction = ELAST, FRICTION
                s.collision_type = 2
                sp.add(s)
                self.seg_step[s] = i
        fx0, fy, fx1, _ = self.floor
        s = pymunk.Segment(st, (fx0, fy), (fx1, fy), 3)
        s.elasticity, s.friction = ELAST, FRICTION
        s.collision_type = 3
        sp.add(s)
        wall = pymunk.Segment(st, (-30, -2000), (-30, 50), 3)   # 左はしのかべ(画面の外へ戻らない)
        wall.elasticity = 0.5
        sp.add(wall)
        sp.on_collision(1, 2, begin=self._hit_step)
        sp.on_collision(1, 3, begin=self._hit_floor)
        self.stage = 0
        base = S.rock_poly(self.rng, 1.0)   # 形は同じまま、大きさだけ変わる
        self.poly = {k: [(x * RADII[k], y * RADII[k]) for x, y in base] for k in range(GOAL + 1)}
        self.body = None
        self.shape = None
        self._make(0, (60.0, -260.0), (self.rng.uniform(250, 420), 0.0), self.rng.uniform(-3, 3))
        self.visited = set()
        self.pending = None
        self.events = []
        self.t = 0.0
        self.result, self.result_t = None, None
        self.floor_t = None
        self.slow_t = None   # 止まりかけた時刻(止まったまま動かなければ失敗)

    def _make(self, st, pos, vel, w):
        r = RADII[st]
        mass = DENSITY[st] * math.pi * r * r / 400.0
        if True:   # いつも同じ形の石(大きさだけ変わる)
            poly = self.poly[st]
            moment = pymunk.moment_for_poly(mass, poly)
            b = pymunk.Body(mass, moment)
            shape = pymunk.Poly(b, poly)
        else:
            b = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, r))
            shape = pymunk.Circle(b, r)
        b.position = pos
        b.velocity = vel
        b.angular_velocity = w
        shape.elasticity, shape.friction = ELAST, FRICTION
        shape.collision_type = 1
        if self.body is not None:
            self.space.remove(self.body, self.shape)
        self.space.add(b, shape)
        self.body, self.shape = b, shape

    def _hit_step(self, arb, space, data):
        i = self.seg_step.get(arb.shapes[1])
        if i is None or self.result is not None:
            return
        speed = self.body.velocity.length
        self.events.append(("bump", self.t, (i, speed, self.stage)))
        if i not in self.visited:
            self.visited.add(i)
            self.events.append(("new_step", self.t, (i, len(self.visited))))
            if self.stage < GOAL and self.pending is None and len(self.visited) % EVOLVE_EVERY == 0:
                n = arb.contact_point_set.normal
                self.pending = (i, (n.x, n.y))

    def _hit_floor(self, arb, space, data):
        if self.result is None and self.floor_t is None:
            self.floor_t = self.t
            self.events.append(("floor", self.t, (self.stage,)))

    def step(self, dt):
        self.t += dt
        self.space.step(dt)
        if self.pending is not None and self.result is None:
            i, n = self.pending
            self.pending = None
            old = self.stage
            st = old + 1
            b = self.body
            # 大きくなった分だけ、当たった面から離す(めりこまないように)
            grow = RADII[st] - RADII[old]
            px, py = b.position
            px -= n[0] * grow * 1.05
            py -= n[1] * grow * 1.05
            self.stage = st
            self._make(st, (px, py), tuple(b.velocity), b.angular_velocity)
            self.events.append(("evolve", self.t, (st, px, py, i)))
            if st == GOAL:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
        if self.result is None and self.floor_t is not None and self.stage < GOAL:
            self.result, self.result_t = "fail", self.t
            self.events.append(("fail", self.t, None))
        if self.result is None:   # 段の上で止まってしまったら失敗(永久に止まったままにしない)
            if self.body.velocity.length < 12 and abs(self.body.angular_velocity) < 0.3:
                if self.slow_t is None:
                    self.slow_t = self.t
                elif self.t - self.slow_t > STOP_WAIT:
                    self.result, self.result_t = "fail", self.t
                    self.events.append(("fail", self.t, "stuck"))
            else:
                self.slow_t = None
        if self.result is None and (self.t > MAX_T or self.body.position.y > self.floor[1] + 3000):
            self.result, self.result_t = "fail", self.t
            self.events.append(("fail", self.t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            b = g.body
            frames.append({"t": g.t, "stage": g.stage, "x": b.position.x, "y": b.position.y, "ang": b.angle,
                           "visited": len(g.visited)})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else FV.DURATION + FEVER_DELAY
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "stage": g.stage, "steps": g.steps, "floor": g.floor, "poly": g.poly}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["stage"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    pick = succ if want == "success" else [r for r in rs if r[1] != "success"]
    pick.sort(key=lambda r: (-r[3], -r[2]))
    for r in pick[:15]:
        print(f"seed={r[0]:4d}  {r[1]}  {r[2]:5.2f}秒  最高 ×{mult(r[3]):.1f}")


# ---------------------------------------------------------------- 描画
BG = (0.01, 0.015, 0.03)
NEON = (0.15, 0.75, 1.0)
GOLD = (1, 0.86, 0.2)


def neon_line(ctx, pts, col, zoom, a=1.0):
    for wdt, al in ((16, 0.08), (8, 0.18), (3.2, 0.95)):
        ctx.new_path()
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgba(*col, al * a)
        ctx.set_line_width(wdt / zoom ** 0.5)
        ctx.stroke()


def draw_gauge(ctx, stage, t):
    """上の大きさゲージ:今の大きさ(×何倍)と、巨大化までのメモリ。"""
    y = 400
    x0, x1 = 120, W - 120
    ctx.set_source_rgba(1, 1, 1, 0.15)
    ctx.rectangle(x0, y - 14, x1 - x0, 28)
    ctx.fill()
    f = stage / GOAL
    g = cairo.LinearGradient(x0, 0, x1, 0)
    g.add_color_stop_rgb(0, 0.4, 0.8, 1.0)
    g.add_color_stop_rgb(1, 1.0, 0.85, 0.2)
    ctx.set_source(g)
    ctx.rectangle(x0, y - 14, (x1 - x0) * f, 28)
    ctx.fill()
    for k in range(1, GOAL):
        x = x0 + (x1 - x0) * k / GOAL
        ctx.move_to(x, y - 14)
        ctx.line_to(x, y + 14)
    ctx.set_source_rgba(0, 0, 0, 0.6)
    ctx.set_line_width(2)
    ctx.stroke()
    S.draw_stage(ctx, 0, x0 - 50, y, 0.3, 14)
    S.draw_stage(ctx, 0, x1 + 52, y, 0.3, 40)
    text(ctx, f"×{mult(stage):.1f}", W / 2, y + 80, 58, rgb=GOLD if stage >= GOAL else (1, 1, 1), sw=8)
    text(ctx, f"巨大化 ×{mult(GOAL):.0f}", x1 + 10, y - 40, 30, rgb=GOLD, sw=5)


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    steps, floor = res["steps"], res["floor"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"stair_grow_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"stair_grow_{seed}.wav")
    final = os.path.join(OUT_DIR, f"stair_grow_{seed}.mp4")
    rng = np.random.default_rng(seed + 99)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    stars = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 2.0), rng.uniform(0, 6.28)) for _ in range(140)]
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    ending = None if fail else FV.FruitFever(W, H, seed, W / 2, H * 0.55, main="巨大化成功!!", count=f"×{mult(GOAL):.1f}")
    cam_x, cam_y, cam_z = frames[0]["x"], frames[0]["y"], 2.5
    pops, trail = [], []
    lit = {}   # 光った段(当たって進化した段は少しのあいだ明るく光る)
    ev_i = 0
    prev_t = 0.0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        dt = t - prev_t
        prev_t = t
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "evolve":
                st, px, py, i = data
                pops.append([et, px, py, st])
                lit[i] = et
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        if ending is not None and over and t - end_t >= FEVER_DELAY:   # 太陽になったところを少し見せてからフィーバー
            ending.draw(surf, ctx, t - end_t - FEVER_DELAY)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - SCARE_DUR) if over else 0
        st = fr["stage"]
        # カメラ:転がるモノを追いかけ、大きくなるほど引いて見せる
        tz = 2.5 * (R0 / RADII[st]) ** 0.32   # 大きくなるにつれて少しずつ引く(画面の中でも石がどんどん大きく見える)
        k = 1 - math.exp(-dt / 0.25)
        cam_x += (fr["x"] + 60 / cam_z * 2 - cam_x) * k
        cam_y += (fr["y"] + 40 - cam_y) * k
        cam_z += (tz - cam_z) * (1 - math.exp(-dt / 0.6))
        # 背景(星がまたたく宇宙)
        ctx.set_source_rgb(*BG)
        ctx.paint()
        for sx, sy, sz, ph in stars:
            x = (sx - cam_x * 0.08) % W
            y = (sy - cam_y * 0.08) % H
            ctx.arc(x, y, sz, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, 0.3 + 0.3 * math.sin(t * 2 + ph))
            ctx.fill()
        ctx.save()
        ctx.translate(W / 2, H * 0.6)
        ctx.scale(cam_z, cam_z)
        ctx.translate(-cam_x, -cam_y)
        # 階段(光るネオンの線)
        for i, (x0, y0, x1, y1, yb) in enumerate(steps):
            glow = 0.0
            if i in lit:
                glow = max(0.0, 1 - (t - lit[i]) / 0.6)
            col = tuple(c + (1 - c) * glow for c in NEON)
            neon_line(ctx, [(x0, y0), (x1, y1), (x1, yb)], col, cam_z)
        fx0, fy, fx1, _ = floor
        neon_line(ctx, [(fx0, fy), (fx1, fy)], GOLD, cam_z)
        text(ctx, "GOAL", fx0 + 260, fy + 90, 70, rgb=GOLD, sw=8)
        # 通ったあとの残像
        trail.append((fr["x"], fr["y"]))
        del trail[:-12]
        for j, (tx, ty) in enumerate(trail[:-1]):
            a = (j + 1) / len(trail)
            ctx.arc(tx, ty, RADII[st] * (0.3 + 0.5 * a), 0, 2 * math.pi)
            ctx.set_source_rgba(*S.COLORS[0], 0.12 * a)
            ctx.fill()
        # 進化した瞬間:ぷくっとふくらむ+光の輪+キラキラ
        sc = 1.0
        for p in pops:
            a = t - p[0]
            if 0 <= a < 0.3 and p[3] == st:
                sc = 0.6 + 0.4 * (a / 0.3) + 0.25 * math.sin(math.pi * a / 0.3)
        S.draw_stage(ctx, 0, fr["x"], fr["y"], fr["ang"], RADII[st] * sc, [(x * sc, y * sc) for x, y in res["poly"][st]], t)
        keep = []
        for p in pops:
            a = t - p[0]
            if a < 0.7:
                r0 = RADII[p[3]]
                ctx.arc(p[1], p[2], r0 * (1.2 + 3 * a), 0, 2 * math.pi)
                ctx.set_source_rgba(1, 1, 1, 0.8 * (1 - a / 0.7))
                ctx.set_line_width(6 / cam_z)
                ctx.stroke()
                for q in range(10):
                    aa = q * 2 * math.pi / 10 + p[3]
                    d = r0 * (1.3 + 4 * a)
                    ctx.arc(p[1] + d * math.cos(aa), p[2] + d * math.sin(aa), 5 / cam_z * (1 - a / 0.7) + 1, 0, 2 * math.pi)
                    ctx.set_source_rgba(1, 0.9, 0.5, 1 - a / 0.7)
                    ctx.fill()
                if a < 0.6:   # 進化した名前がポンと出る
                    text(ctx, f"×{mult(p[3]):.1f}", p[1], p[2] - r0 * 1.6 - 40 * a, 60 / cam_z * (1.2 - 0.2 * min(1, a / 0.1)),
                         rgb=GOLD if p[3] == GOAL else (1, 1, 1), sw=8 / cam_z, alpha=1 - a / 0.6)
                keep.append(p)
        pops = keep
        ctx.restore()
        # 上の帯
        g = cairo.LinearGradient(0, 0, 0, 520)
        g.add_color_stop_rgba(0, 0.0, 0.0, 0.02, 0.95)
        g.add_color_stop_rgba(0.85, 0.0, 0.0, 0.02, 0.8)
        g.add_color_stop_rgba(1, 0.0, 0.0, 0.02, 0.0)
        ctx.rectangle(0, 0, W, 520)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, "小石は階段を落ちて", W / 2, 150, 72, sw=12)
        text(ctx, "巨大化できる？", W / 2, 280, 118, rgb=GOLD, sw=16)
        draw_gauge(ctx, st, t)
        if over and fail:
            k = min(1.0, after / 0.25)
            stuck = any(e[0] == "fail" and e[2] == "stuck" for e in events)
            text(ctx, "止まってしまった…" if stuck else "床に着いてしまった…", W / 2, 1050, 96 * (1.15 - 0.15 * k), rgb=(1, 0.3, 0.3), sw=16)
            text(ctx, f"×{mult(res['stage']):.1f}までだった…", W / 2, 1180, 72, sw=12)
        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} 最高 ×{mult(res['stage']):.1f} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def grow_freq(st):
    """大きくなった段階ごとの「ボヨン」の高さ(だんだん低く)。"""
    return 680.0 * 0.86 ** st


def boing(f0, dur=0.55, seed=0):
    """面白い「ボヨヨン」:高さがはね上がってから下がり、ビブラートでぷるぷるゆれる。"""
    t = np.arange(int(dur * SR)) / SR
    f = f0 * (1 + 0.9 * np.exp(-t * 18)) * (1 + 0.12 * np.sin(2 * np.pi * 11 * t) * np.exp(-t * 3))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)
    return y * np.minimum(1, t / 0.004) * np.exp(-t * 4.5)


def thud(f0, amp, seed):
    """段に当たったときの「コツ」「ドン」(大きいほど低い)。"""
    rng = np.random.default_rng(seed)
    t = np.arange(int(0.25 * SR)) / SR
    n = rng.normal(0, 1, len(t))
    y = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 1.5 * np.exp(-t * 40))) / SR) * np.exp(-t * 22)
    y += 0.4 * np.convolve(n, np.ones(6) / 6, "same") * np.exp(-t * 50)
    return amp * y


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 3) * SR)
    out = np.zeros(n_out)

    def add(sig, t0, g=1.0, buf=None):
        b = out if buf is None else buf
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out:
            b[i:j] += g * sig[: j - i]

    last_bump = -1.0
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.01:
            continue
        if kind == "bump":
            i, speed, st = data
            if t - last_bump > 0.06 and speed > 60:
                add(thud(260 * 0.9 ** st + 40, (0.1 + 0.3 * min(1.0, speed / 900)) * (0.7 + 0.05 * st), int(t * 1000)), t)
                last_bump = t
        elif kind == "evolve":
            st = data[0]
            add(boing(grow_freq(st), 0.45 + 0.04 * st, st), t, 0.3 + 0.045 * st)   # 大きくなるほど低く・大きく・長く
        elif kind == "floor":
            add(thud(90, 0.6, 5), t)
    extra = np.zeros(n_out)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:
        mus = FV.music(SR).mean(axis=1) * 1.6
        add(mus, end_t + FEVER_DELAY, 1.0, extra)
    wet = out.copy()
    for d, g in ((0.043, 0.25), (0.071, 0.18), (0.113, 0.12)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    ref = np.percentile(np.abs(wet[np.abs(wet) > 1e-4]), 99.5) if np.any(np.abs(wet) > 1e-4) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int((end_t or duration) * SR)]
    rms = np.sqrt(np.mean(body ** 2)) if len(body) else 0
    if rms > 0:   # 通常部分の平均音量を約 -18dB にそろえる
        wet *= min(4.0, 10 ** (-18.0 / 20) / rms)
    wet = wet + (0.95 if fail else 1.0) * extra[: len(wet)]
    mag = np.abs(wet)
    wet = np.where(mag < 0.7, wet, np.sign(wet) * (0.7 + 0.1 * np.tanh((mag - 0.7) / 0.1)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--want", choices=["fail", "success"], default="success")
    ap.add_argument("-n", type=int, default=200)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
