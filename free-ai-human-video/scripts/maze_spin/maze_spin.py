"""「回る迷路から○個にげられる?」正方形の迷路が90°ずつ回る(=ボールにかかる重力の向きが90°ずつ変わる)。
迷路のまん中にボールがたくさん入っていて、重力で転がって、迷路のふちにある出口から外に出たら「脱出」。
制限時間内に TARGET 個脱出できたら成功、できなければ失敗。

- 重力はいつも画面の下向き。迷路が回るので、迷路から見ると重力の向きが変わる。
- 迷路の形はシードごとにちがう(穴掘り法で作り、少しだけ壁をぬいて回り道を作る)。
- はじめはまん中の部屋にしきりがあり、START 秒でしきりが消えてスタート。同時に迷路が、HOLD1 秒止まる → TURN 秒で90°回る、をくり返す。T_FAST 秒からは止まる時間が HOLD2 秒に短くなる(スピードアップ)。
- ボールの動きは物理計算のまま(ねらい・補正なし)。
- 成功ならパチンコの大当たり風の演出、失敗なら幽霊。

使い方:
    python maze_spin.py search [-n 80]
    python maze_spin.py render --seed N
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ball_escape"))
from ball_escape import midi_hz, text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from fail_bgm import fail_music  # noqa: E402
from pachinko import RainbowFever, hsv, kyuin_music  # noqa: E402
from flashy import PALETTE, draw_ball, drip_layout, giragira, kyuin_one, scary_text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "glass_spiral"))
import jackpot_end as JP  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 6
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

CX, CY = 540.0, 1045.0
N_CELL = int(os.environ.get("N_CELL", 9))
MAZE = 660.0
CELL = MAZE / N_CELL
HALF = MAZE / 2
WALL_R = 4.0
BALL_R = float(os.environ.get("BALL_R", 13.0))
N_BALLS = int(os.environ.get("N_BALLS", 40))
TARGET = int(os.environ.get("TARGET", 20))
GRAVITY = 2200.0
LOOPS = float(os.environ.get("LOOPS", 0.12))     # 回り道を作るために、ぬく壁の割合
START = 1.0
TURN = 0.6
HOLD1 = float(os.environ.get("HOLD1", 2.4))
HOLD2 = float(os.environ.get("HOLD2", 1.3))
T_FAST = float(os.environ.get("T_FAST", 12.0))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 24.7))
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG


# ---------------------------------------------------------------- 迷路の回転
def turn_starts(until=200.0):
    ts, t = [], START
    while t < until:
        ts.append(t)
        t += TURN + (HOLD1 if t < T_FAST else HOLD2)
    return ts


TURNS = turn_starts()


def maze_angle(t):
    a = 0.0
    for t0 in TURNS:
        if t <= t0:
            break
        k = min(1.0, (t - t0) / TURN)
        a += (math.pi / 2) * (k * k * (3 - 2 * k))
    return a


# ---------------------------------------------------------------- 迷路づくり
def make_maze(rng):
    """壁の線分(迷路の中心が原点の座標)と、出口の位置を返す。"""
    n = N_CELL
    hw = np.ones((n + 1, n), bool)   # hw[i][j]: 行 i の上側の横の壁(列 j)
    vw = np.ones((n, n + 1), bool)   # vw[i][j]: 列 j の左側の縦の壁(行 i)
    seen = np.zeros((n, n), bool)
    c = n // 2
    stack = [(c, c)]
    seen[c, c] = True
    while stack:   # 穴掘り法
        i, j = stack[-1]
        nb = [(di, dj) for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1))
              if 0 <= i + di < n and 0 <= j + dj < n and not seen[i + di, j + dj]]
        if not nb:
            stack.pop()
            continue
        di, dj = nb[rng.integers(len(nb))]
        if di == -1:
            hw[i, j] = False
        elif di == 1:
            hw[i + 1, j] = False
        elif dj == -1:
            vw[i, j] = False
        else:
            vw[i, j + 1] = False
        seen[i + di, j + dj] = True
        stack.append((i + di, j + dj))
    for i in range(1, n):   # 回り道
        for j in range(n):
            if rng.random() < LOOPS:
                hw[i, j] = False
    for i in range(n):
        for j in range(1, n):
            if rng.random() < LOOPS:
                vw[i, j] = False
    for i in (c - 1, c, c + 1):   # まん中の3x3はスタートの部屋
        for j in (c - 1, c, c + 1):
            if i > c - 1:
                hw[i, j] = False
            if j > c - 1:
                vw[i, j] = False
    exits = []   # 出口は、ななめ向かいの2つのすみ(上と下のふち)
    j = 0 if rng.random() < 0.5 else n - 1
    hw[0, j] = False
    exits.append((-HALF + (j + 0.5) * CELL, -HALF))
    j = n - 1 - j
    hw[n, j] = False
    exits.append((-HALF + (j + 0.5) * CELL, HALF))
    gate = []   # スタートの部屋のまわりのしきり(スタートで消える)
    lo, hi = -1.5 * CELL, 1.5 * CELL
    gate += [((lo, lo), (hi, lo)), ((hi, lo), (hi, hi)), ((hi, hi), (lo, hi)), ((lo, hi), (lo, lo))]
    segs = []
    for i in range(n + 1):
        for j in range(n):
            if hw[i, j]:
                y = -HALF + i * CELL
                segs.append(((-HALF + j * CELL, y), (-HALF + (j + 1) * CELL, y)))
    for i in range(n):
        for j in range(n + 1):
            if vw[i, j]:
                x = -HALF + j * CELL
                segs.append(((x, -HALF + i * CELL), (x, -HALF + (i + 1) * CELL)))
    return segs, exits, gate


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 20
        self.space = sp
        self.segs, self.exits, self.gate = make_maze(rng)
        self.maze = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.maze.position = (CX, CY)
        shapes = []
        for a, b in self.segs:
            s = pymunk.Segment(self.maze, a, b, WALL_R)
            s.elasticity, s.friction = 0.4, 0.5
            s.collision_type = 2
            shapes.append(s)
        sp.add(self.maze, *shapes)
        self.gate_shapes = []
        for a, b in self.gate:
            s = pymunk.Segment(self.maze, a, b, WALL_R)
            s.elasticity, s.friction = 0.4, 0.5
            self.gate_shapes.append(s)
        sp.add(*self.gate_shapes)
        self.t = 0.0
        self.events = []
        self.result, self.result_t = None, None
        self.balls = {}
        self.flying = []
        self.escaped = 0
        # まん中の部屋(3セル四方)に、すきまをあけてボールを並べる
        room = 3 * CELL - 2 * WALL_R - 2
        k = int(math.ceil(math.sqrt(N_BALLS)))
        step = room / k
        spots = [(-room / 2 + (a + 0.5) * step, -room / 2 + (b + 0.5) * step) for a in range(k) for b in range(k)]
        order = rng.permutation(len(spots))[:N_BALLS]
        for idx, o in enumerate(order):
            x, y = spots[o]
            x += rng.uniform(-1.5, 1.5)
            y += rng.uniform(-1.5, 1.5)
            b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, BALL_R))
            b.position = (CX + x, CY + y)
            s = pymunk.Circle(b, BALL_R)
            s.elasticity, s.friction = 0.35, 0.4
            s.collision_type = 1
            sp.add(b, s)
            self.balls[b] = {"id": idx, "shape": s, "col": idx % 12, "last_hit": -1.0}
        sp.on_collision(1, 2, post_solve=self._hit)
        sp.on_collision(1, 1, post_solve=self._hit)

    def _hit(self, arb, space, data):
        if not arb.is_first_contact:
            return
        imp = arb.total_impulse.length
        if imp < 120:
            return
        b = arb.shapes[0].body
        info = self.balls.get(b)
        if info is None or self.t - info["last_hit"] < 0.08:
            return
        info["last_hit"] = self.t
        self.events.append(("hit", self.t, (min(1.0, imp / 900), info["col"])))

    def step(self, dt):
        target = maze_angle(self.t + dt)
        self.maze.angular_velocity = (target - self.maze.angle) / dt
        self.space.step(dt)
        self.t += dt
        if self.gate_shapes and self.t >= START:   # スタート!しきりが消える
            self.space.remove(*self.gate_shapes)
            self.gate_shapes = []
            self.events.append(("start", self.t, None))
        if any(abs(self.t - t0) < dt / 2 for t0 in TURNS):
            self.events.append(("turn", self.t, None))
        if abs(self.t - T_FAST) < dt / 2:
            self.events.append(("fast", self.t, None))
        out = []
        ang = self.maze.angle
        ca, sa = math.cos(-ang), math.sin(-ang)
        for b, info in self.balls.items():
            dx, dy = b.position.x - CX, b.position.y - CY
            lx, ly = dx * ca - dy * sa, dx * sa + dy * ca
            if max(abs(lx), abs(ly)) > HALF + BALL_R + WALL_R + 2:
                out.append(b)
        out.sort(key=lambda b_: self.balls[b_]["id"])
        for b in out:
            info = self.balls.pop(b)
            self.space.remove(b, info["shape"])
            if self.result is None or self.result == "success":
                self.escaped += 1
            self.flying.append([b.position.x, b.position.y, b.velocity.x, b.velocity.y, info["col"]])
            self.events.append(("escape", self.t, (b.position.x, b.position.y, self.escaped, info["col"])))
        keep = []
        for f in self.flying:   # 外に出たボールは、そのまま落ちていく(見た目だけ)
            f[3] += GRAVITY * dt
            f[0] += f[2] * dt
            f[1] += f[3] * dt
            if f[1] < H + 60:
                keep.append(f)
        self.flying = keep
        if self.result is None:
            if self.escaped >= TARGET:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, None))
            if self.result is not None:
                self.final_n = self.escaped


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "ang": g.maze.angle, "n": g.escaped,
                           "balls": [(b.position.x, b.position.y, i["col"]) for b, i in g.balls.items()],
                           "fly": [(f[0], f[1], f[4]) for f in g.flying]})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "n": g.final_n, "segs": g.segs, "exits": g.exits, "gate": g.gate}


def score(seed):
    r = simulate(seed)
    esc = [e[1] for e in r["events"] if e[0] == "escape"]
    first = round(esc[0], 1) if esc else None
    return seed, r["result"], round(r["result_t"], 1), r["n"], first


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    draw_ball(ctx, x, y, r * 0.8, PALETTE[(kind * 12 // 7) % 12])


def maze_surface(segs, exits):
    S = int(MAZE + 120)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, S, S)
    c = cairo.Context(surf)
    c.translate(S / 2, S / 2)
    c.rectangle(-HALF, -HALF, MAZE, MAZE)
    c.set_source_rgba(0.35, 0.6, 1.0, 0.07)
    c.fill()
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for wd, col, al in ((22, (0.2, 0.7, 1.0), 0.12), (13, (0.3, 0.8, 1.0), 0.3), (2 * WALL_R, (0.85, 0.97, 1.0), 1.0)):
        for a, b in segs:
            c.move_to(*a)
            c.line_to(*b)
        c.set_source_rgba(*col, al)
        c.set_line_width(wd)
        c.stroke()
    for ex, ey in exits:   # 出口:緑に光るしるし
        out = -1 if ey < 0 else 1
        for wd, al in ((26, 0.25), (10, 0.9)):
            c.move_to(ex - CELL * 0.42, ey)
            c.line_to(ex + CELL * 0.42, ey)
            c.set_source_rgba(0.2, 1.0, 0.4, al)
            c.set_line_width(wd)
            c.stroke()
        for k in range(2):
            yy = ey + out * (16 + 14 * k)
            c.move_to(ex - 13, yy - out * 7)
            c.line_to(ex, yy + out * 5)
            c.line_to(ex + 13, yy - out * 7)
            c.set_source_rgba(0.3, 1.0, 0.5, 0.9 - 0.3 * k)
            c.set_line_width(5)
            c.stroke()
    return surf, S


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"maze_spin_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"maze_spin_{seed}.wav")
    final = os.path.join(OUT_DIR, f"maze_spin_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"ms_preview_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, CX, CY, reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=("脱出成功!!", "COMPLETE", f"{res['n']} 個 脱出"))
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    drips = drip_layout(ctx, "失敗したら", W / 2, 1590, 78, "失敗したら・・・", seed)
    msurf, MS = maze_surface(res["segs"], res["exits"])
    bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(bg)
    gr = cairo.RadialGradient(CX, CY, 50, CX, CY, 1100)
    gr.add_color_stop_rgb(0, 0.06, 0.08, 0.16)
    gr.add_color_stop_rgb(1, 0.01, 0.02, 0.05)
    bc.set_source(gr)
    bc.paint()
    sprites = {}

    def ball(x, y, c):
        sp_ = sprites.get(c)
        if sp_ is None:
            m_ = int(math.ceil(BALL_R)) + 2
            s_ = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2 * m_, 2 * m_)
            draw_ball(cairo.Context(s_), m_, m_, BALL_R, PALETTE[c])
            sprites[c] = sp_ = (s_, m_)
        ctx.set_source_surface(sp_[0], x - sp_[1], y - sp_[1])
        ctx.paint()

    pops = []
    frozen = None
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "escape" and (end_t is None or et <= end_t):
                pops.append((data[0], data[1], data[2], data[3], et))
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
        if fail and over:
            if frozen is None:
                frozen = fr
            fr = frozen
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        cyc = int(win_b * 30) if win_b >= 0 else 0
        for x, y, c in fr["fly"]:
            ball(x, y, (c + cyc) % 12)
        ctx.save()
        ctx.translate(CX, CY)
        ctx.rotate(fr["ang"])
        ctx.set_source_surface(msurf, -MS / 2, -MS / 2)
        ctx.paint()
        if t < START:   # スタートの部屋のしきり(オレンジの点線)
            ctx.set_line_width(2 * WALL_R)
            ctx.set_dash([14, 10])
            for a, b in res["gate"]:
                ctx.move_to(*a)
                ctx.line_to(*b)
            ctx.set_source_rgba(1, 0.6, 0.15, 0.9)
            ctx.stroke()
            ctx.set_dash([])
        ctx.restore()
        if 0 <= t - START < 0.8 and not over:
            a_ = t - START
            text(ctx, "スタート!", W / 2, CY + 40, 130 * (1.4 - 0.4 * min(1, a_ / 0.12)), rgb=GOLD, sw=16,
                 alpha=min(1.0, (0.8 - a_) / 0.25))
        for x, y, c in fr["balls"]:
            ball(x, y, (c + cyc) % 12)
        keep = []
        for x, y, n_, c, t0 in pops:   # 脱出した瞬間のキラッと「+1」
            a_ = t - t0
            if a_ < 0.6:
                k = 1 - a_ / 0.6
                ctx.arc(x, y, BALL_R + 70 * a_, 0, 2 * math.pi)
                ctx.set_source_rgba(*PALETTE[c], 0.8 * k)
                ctx.set_line_width(4)
                ctx.stroke()
                keep.append((x, y, n_, c, t0))
        pops = keep
        # スピードアップのお知らせ
        if 0 <= t - T_FAST < 1.4 and not over:
            a_ = t - T_FAST
            k = min(1.0, a_ / 0.15)
            text(ctx, "回転スピードアップ!!", W / 2, 655, 80 * (1.2 - 0.2 * k), rgb=hsv(t * 2), sw=14,
                 alpha=min(1.0, (1.4 - a_) / 0.3))
        # 文字
        text(ctx, "回る迷路からボールをにがせ", W / 2, 235, 60, sw=12)
        text(ctx, f"{TARGET}個にげられる？", W / 2, 335, 96, rgb=GOLD, sw=16)
        n = fr["n"] if not over else res["n"]
        text(ctx, f"{n} / {TARGET} 個 脱出", W / 2, 445, 70, rgb=(1, 1, 1), sw=10)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 522, 40, rgb=(1, 0.4, 0.4) if left < 10 else (0.95, 0.95, 0.95), sw=8)
        if not over:
            scary_text(ctx, "失敗したら・・・", W / 2, 1590, 78, t, drips)
        if over and fail:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 900, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            text(ctx, "時間切れ…", W / 2, 1010, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"{res['n']}個しかにげられなかった…", W / 2, 1130, 62, sw=12)
        if win_b >= 0:   # 虹ストロボがどんどん速く・明るくなって、真っ白にはじける
            k = win_b / PRE
            ph = (win_b * (8 + 14 * k)) % 1.0
            ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*hsv(win_b * 4), (0.25 + 0.4 * k) * (1 - ph) ** 2)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['n']}個 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def clack(amp, seed):
    """ボールが壁に当たる「コッ」。"""
    rng = np.random.default_rng(seed)
    t = _t(0.06)
    f = rng.uniform(1400, 2400)
    n = rng.normal(0, 1, len(t))
    return amp * (np.sin(2 * np.pi * f * t) * np.exp(-t * 90) + 0.4 * n * np.exp(-t * 200))


def rumble(dur, seed):
    """迷路が回る「ゴゴゴ」と、止まるときの「ガチャン」。"""
    rng = np.random.default_rng(seed)
    t = _t(dur + 0.25)
    n = rng.normal(0, 1, len(t))
    lp = np.convolve(n, np.ones(60) / 60, "same") * 6
    env = np.clip(t / 0.08, 0, 1) * np.clip((dur - t) / 0.15, 0, 1)
    y = lp * env * (0.8 + 0.2 * np.sin(2 * np.pi * 18 * t)) + 0.25 * np.sin(2 * np.pi * 55 * t) * env
    i = int(dur * SR)
    tc = _t(0.25)
    click = np.sin(2 * np.pi * 180 * tc) * np.exp(-tc * 30) + 0.5 * rng.normal(0, 1, len(tc)) * np.exp(-tc * 60)
    y[i:i + len(tc)] += 0.8 * click[: len(y) - i]
    return 0.5 * y


def chime(f, amp):
    """脱出の「ピロン」。"""
    t = _t(0.5)
    y = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 8) + 0.2 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 14)
    return amp * y * np.exp(-t * 6) * np.minimum(1, t / 0.004)


PENTA = [0, 2, 4, 7, 9]


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
    recent = []
    for kind, t, data in events:
        if t > end_t + 0.01:
            continue
        if kind == "hit":
            recent = [x for x in recent if t - x < 0.05]
            if len(recent) >= 4:
                continue
            recent.append(t)
            add(clack(0.35 * data[0], int(t * 1000)), t)
        elif kind == "start":
            tb = _t(0.35)
            add(0.6 * np.sin(2 * np.pi * midi_hz(84) * tb) * np.exp(-tb * 8), t)
            add(0.5 * np.sin(2 * np.pi * midi_hz(91) * tb) * np.exp(-tb * 8), t + 0.08)
        elif kind == "turn":
            add(rumble(TURN, int(t * 10)), t)
        elif kind == "fast":
            tb = _t(0.5)
            for k, m in enumerate((79, 84, 91)):
                add(0.5 * np.sign(np.sin(2 * np.pi * midi_hz(m) * tb)) * np.exp(-tb * 6), t + 0.09 * k)
        elif kind == "escape":
            k = data[2] - 1
            m = 72 + 12 * (k // 5) + PENTA[k % 5]
            add(chime(midi_hz(min(m, 108)), 0.8), t)
    wet = out.copy()
    for dd, g_ in ((0.043, 0.2), (0.071, 0.13)):
        kk = int(dd * SR)
        wet[kk:] += out[:-kk] * g_
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
        b_ = JP.music(SR, 3)
        b_ = b_.mean(axis=1) if b_.ndim == 2 else b_
        b_ = b_[int(JP.T_BIG * SR) - int(0.05 * SR):]
        n = int(WIN_DUR * SR)
        mus = np.zeros(n)
        mus[:min(n, len(b_))] += b_[:n] / (np.abs(b_).max() + 1e-9)
        a_ = kyuin_music(SR, WIN_DUR)
        mus[:min(n, len(a_))] += 0.8 * a_[:n]
        tt = 0.0
        while tt < WIN_DUR - 0.5:
            ky = kyuin_one(1.0 + 0.15 * ((int(tt / 0.3)) % 3))
            i = int(tt * SR)
            m = min(len(ky), n - i)
            mus[i:i + m] += 0.4 * ky[:m]
            tt += 0.3
        tb = np.arange(int(1.5 * SR)) / SR
        boom = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-tb * 6) + 35) / SR) * np.exp(-tb * 2.5)
        mus[:len(boom)] += 0.9 * boom
        mus *= np.minimum(1, (WIN_DUR - np.arange(n) / SR) / 0.6)
        mus = np.tanh(1.6 * mus / (np.abs(mus).max() + 1e-9)) / np.tanh(1.6)
        i0 = int((end_t + PRE) * SR)
        m = min(len(mus), n_out - i0)
        extra[i0:i0 + m] += 1.1 * mus[:m]
        tt = 0.0   # 成功の瞬間:どんどん速く高くなるキュイン
        while tt < PRE - 0.05:
            k = tt / PRE
            ky = kyuin_one(1.0 + 0.6 * k)
            i = int((end_t + tt) * SR)
            m = min(len(ky), n_out - i)
            extra[i:i + m] += (0.35 + 0.35 * k) * ky[:m]
            tt += 0.11 - 0.05 * k
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
    ap.add_argument("-n", type=int, default=80)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
