"""「ワープ穴で2倍になるボール、○個にできる?」
くぎの並んだたて長の箱を、ボールが落ちていく。箱の中には左右にゆっくり動く「IN」のワープ穴がいくつかあり、
ボールが IN の穴に入ると、箱の上の「OUT」の穴から2個になって出てくる。穴に入らずに下まで落ちたボールは外に落ちて消える。
画面の中のボールが TARGET 個になったら成功。制限時間が来たら失敗。
ボールは SUPPLY 秒ごとに1個ずつ OUT から補給される(全部落ちても終わらない)。

- 重力は下向き。ボールどうし・くぎ・壁とふつうに衝突する。ボールの動きは物理計算のまま(ねらい・補正なし)。
- OUT から出るボールの向きは毎回ランダム(どこに落ちるかは物理まかせ)。
- 成功ならパチンコの大当たり風の演出、失敗なら幽霊。

使い方:
    python ball_warp.py search [-n 80]
    python ball_warp.py render --seed N
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
SUBSTEPS = 4
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

BOX_W = float(os.environ.get("BOX_W", 640.0))
BX0, BX1 = (W - BOX_W) / 2, (W + BOX_W) / 2
BY0, BY1 = 560.0, 1480.0          # 箱の上と下(下はあいていて、落ちたボールは消える)
BALL_R = float(os.environ.get("BALL_R", 11.0))
PEG_R = 6.0
HOLE_R = float(os.environ.get("HOLE_R", 56.0))
N_LANE = int(os.environ.get("N_LANE", 5))       # IN の穴の数(1つの高さに1つ)
HOLE_SPEED = float(os.environ.get("HOLE_SPEED", 0.7))
OUT_X, OUT_Y = W / 2, BY0 + 55.0
TARGET = int(os.environ.get("TARGET", 100))
SUPPLY = float(os.environ.get("SUPPLY", 2.0))   # この秒数ごとに OUT から1個おまけで出てくる
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 20.0))
GRAVITY = 1500.0
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG
LANES = [BY0 + 230 + k * (BY1 - BY0 - 330) / max(1, N_LANE - 1) for k in range(N_LANE)]


def peg_points():
    pts = []
    y = BY0 + 140
    row = 0
    while y < BY1 - 40:
        if all(abs(y - ly) > HOLE_R + 10 for ly in LANES):
            off = 0 if row % 2 == 0 else 45
            x = BX0 + 45 + off
            while x < BX1 - 30:
                pts.append((x, y))
                x += 90
            row += 1
        y += 62
    return pts


PEGS = peg_points()


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 10
        self.space = sp
        segs = [((BX0, BY0 - 40), (BX0, BY1)), ((BX1, BY0 - 40), (BX1, BY1)), ((BX0, BY0), (BX1, BY0))]
        shapes = []
        for a, b in segs:
            s = pymunk.Segment(sp.static_body, a, b, 5)
            s.elasticity, s.friction = 0.5, 0.2
            shapes.append(s)
        for x, y in PEGS:
            s = pymunk.Circle(sp.static_body, PEG_R, (x, y))
            s.elasticity, s.friction = 0.5, 0.2
            shapes.append(s)
        sp.add(*shapes)
        # IN の穴:高さごとに1つ。左右にゆっくり動く(速さと向きはシードごとにちがう)
        self.holes = [(ly, rng.uniform(0.7, 1.3) * HOLE_SPEED * rng.choice([-1, 1]), rng.uniform(0, 2 * math.pi))
                      for ly in LANES]
        self.t = 0.0
        self.events = []
        self.result, self.result_t = None, None
        self.balls = {}
        self.n_id = 0
        self.warps = 0
        self.lost = 0
        self.best = 1
        self.next_supply = 0.0

    def hole_pos(self, k, t):
        ly, w, ph = self.holes[k]
        amp = (BX1 - BX0) / 2 - HOLE_R - 8
        return W / 2 + amp * math.sin(w * t + ph), ly

    def add_ball(self, x, y, vx, vy):
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, BALL_R))
        b.position = (x, y)
        b.velocity = (vx, vy)
        s = pymunk.Circle(b, BALL_R)
        s.elasticity, s.friction = 0.5, 0.2
        self.space.add(b, s)
        self.balls[b] = {"id": self.n_id, "shape": s, "col": self.n_id % 12}
        self.n_id += 1

    def step(self, dt):
        if self.result is None and self.t >= self.next_supply:   # 補給:SUPPLY 秒ごとに OUT から1個
            self.add_ball(OUT_X, OUT_Y, self.rng.uniform(-200, 200), 80)
            self.events.append(("supply", self.t, None))
            self.next_supply += SUPPLY
        self.space.step(dt)
        self.t += dt
        hp = [self.hole_pos(k, self.t) for k in range(len(self.holes))]
        warp, gone = [], []
        for b, info in self.balls.items():
            x, y = b.position
            if y > BY1 + 40:
                gone.append(b)
                continue
            for k, (hx, hy) in enumerate(hp):
                if (x - hx) ** 2 + (y - hy) ** 2 < (HOLE_R - BALL_R * 0.4) ** 2:
                    warp.append((b, k))
                    break
        warp.sort(key=lambda w_: self.balls[w_[0]]["id"])
        gone.sort(key=lambda b_: self.balls[b_]["id"])
        for b in gone:
            info = self.balls.pop(b)
            self.space.remove(b, info["shape"])
            if self.result is None:
                self.lost += 1
                self.events.append(("lost", self.t, (b.position.x, len(self.balls))))
        for b, k in warp:
            info = self.balls.pop(b)
            self.space.remove(b, info["shape"])
            x, y = b.position
            if self.result is None:
                self.warps += 1
                for sgn in (-1, 1):   # OUT の穴から2個(左右に少しずらして出す)
                    self.add_ball(OUT_X + sgn * (BALL_R + 1), OUT_Y + self.rng.uniform(-3, 3),
                                  sgn * self.rng.uniform(40, 260), self.rng.uniform(40, 160))
                self.events.append(("warp", self.t, (x, y, k, len(self.balls))))
        self.best = max(self.best, len(self.balls))
        if self.result is None:
            if len(self.balls) >= TARGET:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, None))
            if self.result is not None:
                self.final_n = len(self.balls)


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "n": len(g.balls),
                           "holes": [g.hole_pos(k, g.t) for k in range(len(g.holes))],
                           "balls": np.array([(b.position.x, b.position.y, i["col"]) for b, i in g.balls.items()],
                                             dtype=np.float32).reshape(-1, 3)})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "n": g.final_n, "best": g.best, "warps": g.warps, "lost": g.lost}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), r["n"], r["best"], r["warps"]


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
IN_COL = (0.7, 0.35, 1.0)
OUT_COL = (1.0, 0.55, 0.15)


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    draw_ball(ctx, x, y, r * 0.8, PALETTE[(kind * 12 // 7) % 12])


def portal(ctx, x, y, r, col, t, label, spin=1):
    """うずまきのワープ穴。"""
    g = cairo.RadialGradient(x, y, 0, x, y, r * 1.25)
    g.add_color_stop_rgba(0, 0, 0, 0, 1)
    g.add_color_stop_rgba(0.55, *[c * 0.5 for c in col], 0.95)
    g.add_color_stop_rgba(0.8, *col, 0.8)
    g.add_color_stop_rgba(1, *col, 0)
    ctx.arc(x, y, r * 1.25, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    for k in range(4):   # 回るうず
        a0 = spin * t * 5 + k * math.pi / 2
        ctx.new_path()
        for s in range(30):
            u = s / 29
            a = a0 + u * 3.0
            rr = r * (0.95 - 0.8 * u)
            ctx.line_to(x + rr * math.cos(a), y + rr * math.sin(a))
        ctx.set_source_rgba(*[min(1, c + 0.4) for c in col], 0.85)
        ctx.set_line_width(3)
        ctx.stroke()
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source_rgba(*[min(1, c + 0.5) for c in col], 0.9)
    ctx.set_line_width(4)
    ctx.stroke()
    text(ctx, label, x, y + 12, 32, rgb=(1, 1, 1), sw=6)


def board_surface():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    c.rectangle(BX0, BY0, BOX_W, BY1 - BY0)
    c.set_source_rgba(0.35, 0.6, 1.0, 0.06)
    c.fill()
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for wd, col, al in ((22, (0.2, 0.7, 1.0), 0.12), (13, (0.3, 0.8, 1.0), 0.3), (10, (0.85, 0.97, 1.0), 1.0)):
        c.move_to(BX0, BY1)
        c.line_to(BX0, BY0)
        c.line_to(BX1, BY0)
        c.line_to(BX1, BY1)
        c.set_source_rgba(*col, al)
        c.set_line_width(wd)
        c.stroke()
    for x, y in PEGS:
        g = cairo.RadialGradient(x - 2, y - 2, 0, x, y, PEG_R + 1)
        g.add_color_stop_rgb(0, 1, 1, 1)
        g.add_color_stop_rgb(1, 0.6, 0.65, 0.75)
        c.arc(x, y, PEG_R, 0, 2 * math.pi)
        c.set_source(g)
        c.fill()
    for ly in LANES:   # 穴が動くレール
        c.move_to(BX0 + 12, ly)
        c.line_to(BX1 - 12, ly)
        c.set_source_rgba(0.4, 0.6, 1.0, 0.18)
        c.set_line_width(4)
        c.set_dash([10, 10])
        c.stroke()
        c.set_dash([])
    return surf


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"ball_warp_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"ball_warp_{seed}.wav")
    final = os.path.join(OUT_DIR, f"ball_warp_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"bw_preview_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, W / 2, (BY0 + BY1) / 2, reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=(f"{TARGET}個!!", "COMPLETE", f"ワープ {res['warps']} 回"))
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    drips = drip_layout(ctx, "失敗したら", W / 2, 1590, 78, "失敗したら・・・", seed)
    board = board_surface()
    bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(bg)
    gr = cairo.RadialGradient(W / 2, (BY0 + BY1) / 2, 50, W / 2, (BY0 + BY1) / 2, 1100)
    gr.add_color_stop_rgb(0, 0.07, 0.06, 0.16)
    gr.add_color_stop_rgb(1, 0.01, 0.01, 0.05)
    bc.set_source(gr)
    bc.paint()
    sprites = {}
    m_ = int(math.ceil(BALL_R)) + 2
    for c in range(12):
        s_ = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2 * m_, 2 * m_)
        draw_ball(cairo.Context(s_), m_, m_, BALL_R, PALETTE[c])
        sprites[c] = s_
    fx = []   # ワープの光(入った場所 → OUT)
    out_flash = -9.0
    frozen = None
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "warp" and (end_t is None or et <= end_t):
                fx.append((data[0], data[1], et))
                out_flash = et
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
        ctx.set_source_surface(board, 0, 0)
        ctx.paint()
        tt = min(t, end_t) if end_t is not None else t
        for hx, hy in fr["holes"]:
            portal(ctx, hx, hy, HOLE_R, IN_COL, tt, "×2")
        k_ = math.exp(-(t - out_flash) * 6) if t >= out_flash else 0
        # ワープの出口(上から下りている金色の土管)。穴に入ったボールはここから2個になって出てくる
        pw = 60 * (1 + 0.15 * k_)
        for x0_, w_, y0_, y1_ in ((OUT_X - pw / 2 + 6, pw - 12, BY0, OUT_Y - 14), (OUT_X - pw / 2, pw, OUT_Y - 26, OUT_Y - 4)):
            g_ = cairo.LinearGradient(x0_, 0, x0_ + w_, 0)
            g_.add_color_stop_rgb(0, 0.55, 0.38, 0.05)
            g_.add_color_stop_rgb(0.35, 1.0, 0.92, 0.5)
            g_.add_color_stop_rgb(1, 0.5, 0.33, 0.04)
            ctx.rectangle(x0_, y0_, w_, y1_ - y0_)
            ctx.set_source(g_)
            ctx.fill()
        if k_ > 0.02:
            ctx.arc(OUT_X, OUT_Y, 30 + 25 * (1 - k_), 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.85, 0.3, 0.8 * k_)
            ctx.set_line_width(4)
            ctx.stroke()
        text(ctx, "← ワープの出口", OUT_X + 150, OUT_Y - 18, 30, rgb=(1, 0.85, 0.3), sw=6)
        text(ctx, "(2個になって出る)", OUT_X + 150, OUT_Y + 18, 26, rgb=(1, 0.85, 0.3), sw=6)
        # 下:落ちたら消える
        ctx.move_to(BX0, BY1)
        ctx.line_to(BX1, BY1)
        ctx.set_source_rgba(1, 0.3, 0.3, 0.8)
        ctx.set_line_width(4)
        ctx.set_dash([14, 10])
        ctx.stroke()
        ctx.set_dash([])
        text(ctx, "↓ 落ちたら消える ↓", W / 2, BY1 - 12, 30, rgb=(1, 0.45, 0.45), sw=6)
        keep = []
        for x, y, t0 in fx:   # 入った穴から OUT へ走る光
            a_ = t - t0
            if a_ < 0.3:
                k = 1 - a_ / 0.3
                ctx.move_to(x, y)
                ctx.curve_to(x, y - 120, OUT_X, OUT_Y + 120, OUT_X, OUT_Y)
                ctx.set_source_rgba(1, 0.85, 0.4, 0.7 * k)
                ctx.set_line_width(6 * k + 1)
                ctx.stroke()
                ctx.arc(x, y, HOLE_R * (1 + a_ * 2), 0, 2 * math.pi)
                ctx.set_source_rgba(*IN_COL, 0.8 * k)
                ctx.set_line_width(4)
                ctx.stroke()
                keep.append((x, y, t0))
        fx = keep
        cyc = int(win_b * 30) if win_b >= 0 else 0
        for x, y, c in fr["balls"]:
            ctx.set_source_surface(sprites[(int(c) + cyc) % 12], x - m_, y - m_)
            ctx.paint()
        # 文字
        text(ctx, "ワープ穴に入ると2個になって戻るボール", W / 2, 235, 52, sw=12)
        text(ctx, f"{TARGET}個にできる？", W / 2, 335, 96, rgb=GOLD, sw=16)
        n = fr["n"] if not over else res["n"]
        text(ctx, f"{n} / {TARGET} 個", W / 2, 445, 70, rgb=(1, 1, 1), sw=10)
        left = max(0.0, TIME_LIMIT - tt)
        text(ctx, f"残り {left:4.1f}秒", W / 2, 522, 40, rgb=(1, 0.4, 0.4) if left < 10 else (0.95, 0.95, 0.95), sw=8)
        if not over:
            scary_text(ctx, "失敗したら・・・", W / 2, 1590, 78, t, drips)
        if over and fail:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 880, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            msg = "全部落ちた…" if res["n"] == 0 else "時間切れ…"
            text(ctx, msg, W / 2, 990, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"いちばん多いときで {res['best']}個だった…", W / 2, 1110, 60, sw=12)
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


def warp_snd(n):
    """ワープの「ヒュイン」+ OUT から2個出る「ポポン」(数が増えるほど高く)。"""
    t = _t(0.25)
    f = 300 + 2200 * (t / 0.25) ** 1.5
    sweep = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6) * 0.5
    m = 72 + min(24, int(12 * math.log2(1 + n / 4)))
    tp = _t(0.15)
    pop = np.sin(2 * np.pi * midi_hz(m) * tp) * np.exp(-tp * 25)
    y = sweep
    y[:len(pop)] += 0.8 * pop
    i = int(0.06 * SR)
    y[i:i + len(pop)] += 0.6 * np.sin(2 * np.pi * midi_hz(m + 7) * tp)[: len(y) - i] * np.exp(-tp * 25)[: len(y) - i]
    return y


def lost_snd():
    """下に落ちて消える「ポトッ」。"""
    t = _t(0.18)
    return 0.4 * np.sin(2 * np.pi * (220 - 300 * t) * t) * np.exp(-t * 18)


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
    rw, rl = [], []
    for kind, t, data in events:
        if t > end_t + 0.01:
            continue
        if kind == "warp":
            rw = [x for x in rw if t - x < 0.08]
            if len(rw) >= 3:
                continue
            rw.append(t)
            add(warp_snd(data[3]), t)
        elif kind == "lost":
            rl = [x for x in rl if t - x < 0.1]
            if len(rl) >= 2:
                continue
            rl.append(t)
            add(lost_snd(), t)
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
