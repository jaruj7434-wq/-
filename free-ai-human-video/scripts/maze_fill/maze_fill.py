"""「迷路を満タンにできる?」たて長の迷路の上の入口から、小さなカラフルなボールが流れ落ちてくる。
ボールは重力で迷路の中を流れて下からたまっていく。制限時間内に、迷路の全部のマスがボールで埋まったら成功。

- 迷路は動かない。重力は下向き。迷路の形はシードごとにちがう(サイドワインダー法。入口からどのマスへも上にのぼらずに行ける)。
- 迷路の上はふたなし。ボールは迷路の上のまん中に固定された注ぎ口から、毎秒 RATE 個ずつ出てくる。T_FAST 秒からは毎秒 RATE2 個に増量。
  注ぎ口のまわりがボールでいっぱいのときは出てこない。
- マスの中のボールが FILL_N 個以上になったら、そのマスは「埋まった」(画面上の満タン度に数える)。
- せまい通路でボールがつまる(アーチができる)と、その先が埋まらないことがある。
- ボールの動きは物理計算のまま(ねらい・補正なし)。
- 成功ならパチンコの大当たり風の演出、失敗なら幽霊。

使い方:
    python maze_fill.py search [-n 80]
    python maze_fill.py render --seed N
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

N_COL = int(os.environ.get("N_COL", 7))
N_ROW = int(os.environ.get("N_ROW", 9))
CELL = float(os.environ.get("CELL", 86.0))
MW, MH = N_COL * CELL, N_ROW * CELL
X0 = (W - MW) / 2
Y0 = 1475.0 - MH            # 迷路の上のふち
WALL_R = 4.0
BALL_R = float(os.environ.get("BALL_R", 7.0))
RATE = float(os.environ.get("RATE", 90.0))
RATE2 = float(os.environ.get("RATE2", 180.0))
T_FAST = float(os.environ.get("T_FAST", 10.0))
FILL_N = int(os.environ.get("FILL_N", 12))
LOOPS = float(os.environ.get("LOOPS", 0.2))
CLOSE = float(os.environ.get("CLOSE", 0.6))   # 横の通路のかたまりを区切る確率
GRAVITY = float(os.environ.get("GRAVITY", 1800.0))
FRICTION = float(os.environ.get("FRICTION", 0.05))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 32.0))
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG


NOZZLE_Y = Y0 - 190   # 注ぎ口(まん中に固定・動かない)


def nozzle(t):
    """注ぎ口の位置(x)と左右の速さ。迷路の上のまん中に固定。"""
    return X0 + MW / 2, 0.0


# ---------------------------------------------------------------- 迷路づくり
def make_maze(rng):
    nr, nc = N_ROW, N_COL
    hw = np.ones((nr + 1, nc), bool)   # hw[i][j]: 行 i の上側の横の壁
    vw = np.ones((nr, nc + 1), bool)   # vw[i][j]: 列 j の左側の縦の壁
    # サイドワインダー法:1段ごとに横の「通路のかたまり」を作り、かたまりごとに1か所だけ上の段とつなぐ。
    # → 入口からどのマスへも「上にのぼらずに」行ける(ボールが重力で全部のマスに流れこめる)形になる。
    vw[:, 1:nc] = True
    vw[0, 1:nc] = False   # いちばん上の段は1本の横の通路
    for i in range(1, nr):
        run = [0]
        for j in range(1, nc + 1):
            close = j == nc or rng.random() < CLOSE
            if close:
                k = run[rng.integers(len(run))]
                hw[i, k] = False          # かたまりのどこか1か所を上とつなぐ
                run = [j]
            else:
                vw[i, j] = False          # 右どなりとつなぐ
                run.append(j)
    for i in range(1, nr):   # 少しだけ、たての抜け道を増やす
        for j in range(nc):
            if rng.random() < LOOPS:
                hw[i, j] = False
    hw[0, :] = False   # 上はふたなし(どの列にも上から入れる → 上でつまらない)
    ent = 0
    segs = []
    for i in range(nr + 1):
        for j in range(nc):
            if hw[i, j]:
                y = Y0 + i * CELL
                segs.append(((X0 + j * CELL, y), (X0 + (j + 1) * CELL, y)))
    for i in range(nr):
        for j in range(nc + 1):
            if vw[i, j]:
                x = X0 + j * CELL
                segs.append(((x, Y0 + i * CELL), (x, Y0 + (i + 1) * CELL)))
    return segs, ent


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 10
        sp.use_spatial_hash(BALL_R * 2.5, 6000)
        self.space = sp
        self.segs, self.ent = make_maze(rng)
        shapes = []
        for a, b in self.segs:
            s = pymunk.Segment(sp.static_body, a, b, WALL_R)
            s.elasticity, s.friction = 0.3, FRICTION
            shapes.append(s)
        # 迷路の左右の壁を上にのばす(上にあふれたボールがこぼれないように)
        self.funnel = [((X0, Y0 - 170), (X0, Y0)), ((X0 + MW, Y0 - 170), (X0 + MW, Y0))]
        for a, b in self.funnel:
            s = pymunk.Segment(sp.static_body, a, b, WALL_R)
            s.elasticity, s.friction = 0.3, FRICTION
            shapes.append(s)
        sp.add(*shapes)
        self.t = 0.0
        self.events = []
        self.result, self.result_t = None, None
        self.balls = {}
        self.n_id = 0
        self.acc = 0.0
        self.filled = np.zeros((N_ROW, N_COL), bool)
        self.n_filled = 0
        self.dropped = 0

    def spawn(self):
        """左右に動く注ぎ口から1個出す(出口のまわりがボールでいっぱいなら出さない)。"""
        nx, vx = nozzle(self.t)
        for _ in range(8):
            x = nx + self.rng.uniform(-20, 20)
            y = NOZZLE_Y + 15 + self.rng.uniform(0, 70)
            hit = self.space.point_query((x, y), 2 * BALL_R + 0.5, pymunk.ShapeFilter())
            if not any(h.shape.body.body_type == pymunk.Body.DYNAMIC for h in hit):
                break
        else:
            return False   # 注ぎ口がつまっている
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, BALL_R))
        b.position = (x, y)
        b.velocity = (vx + self.rng.uniform(-20, 20), 1000)
        s = pymunk.Circle(b, BALL_R)
        s.elasticity, s.friction = 0.3, FRICTION
        self.space.add(b, s)
        self.balls[b] = {"id": self.n_id, "shape": s, "col": self.n_id % 12}
        self.n_id += 1
        self.dropped += 1
        return True

    def step(self, dt):
        if self.result is None:
            self.acc += (RATE if self.t < T_FAST else RATE2) * dt
            while self.acc >= 1:
                self.acc -= 1
                self.spawn()
        self.space.step(dt)
        self.t += dt
        if abs(self.t - T_FAST) < dt / 2:
            self.events.append(("fast", self.t, None))

    def check_fill(self):
        """フレームごとに、マスの埋まり具合を数える。"""
        gone = [b for b in self.balls if b.position.y > H + 50]
        for b in gone:
            self.space.remove(b, self.balls.pop(b)["shape"])
        if not self.balls:
            return
        pos = np.array([(b.position.x, b.position.y) for b in self.balls])
        j = np.floor((pos[:, 0] - X0) / CELL).astype(int)
        i = np.floor((pos[:, 1] - Y0) / CELL).astype(int)
        ok = (i >= 0) & (i < N_ROW) & (j >= 0) & (j < N_COL)
        cnt = np.zeros((N_ROW, N_COL), int)
        np.add.at(cnt, (i[ok], j[ok]), 1)
        new = (cnt >= FILL_N) & ~self.filled
        for ii, jj in sorted(zip(*np.nonzero(new))):
            self.filled[ii, jj] = True
            self.n_filled += 1
            self.events.append(("fill", self.t, (int(ii), int(jj), self.n_filled)))
        if self.result is None:
            if self.n_filled >= N_ROW * N_COL:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, None))
            if self.result is not None:
                self.final_n = self.n_filled


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        g.check_fill()
        if record:
            frames.append({"t": g.t, "n": g.n_filled, "filled": g.filled.copy(),
                           "balls": np.array([(b.position.x, b.position.y, i["col"]) for b, i in g.balls.items()],
                                             dtype=np.float32).reshape(-1, 3)})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "n": g.final_n, "segs": g.segs, "funnel": g.funnel, "dropped": g.dropped}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), r["n"], r["dropped"]


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
TOTAL = N_ROW * N_COL


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    draw_ball(ctx, x, y, r * 0.8, PALETTE[(kind * 12 // 7) % 12])


def maze_surface(segs, funnel):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    c.rectangle(X0, Y0, MW, MH)
    c.set_source_rgba(0.35, 0.6, 1.0, 0.06)
    c.fill()
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for wd, col, al in ((22, (0.2, 0.7, 1.0), 0.12), (13, (0.3, 0.8, 1.0), 0.3), (2 * WALL_R, (0.85, 0.97, 1.0), 1.0)):
        for a, b in segs + funnel:
            c.move_to(*a)
            c.line_to(*b)
        c.set_source_rgba(*col, al)
        c.set_line_width(wd)
        c.stroke()
    return surf


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"maze_fill_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"maze_fill_{seed}.wav")
    final = os.path.join(OUT_DIR, f"maze_fill_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"mf_preview_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, W / 2, Y0 + MH / 2, reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=("満タン!!", "COMPLETE", f"{TOTAL} / {TOTAL} マス"))
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    drips = drip_layout(ctx, "失敗したら", W / 2, 1590, 78, "失敗したら・・・", seed)
    msurf = maze_surface(res["segs"], res["funnel"])
    bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(bg)
    gr = cairo.RadialGradient(W / 2, Y0 + MH / 2, 50, W / 2, Y0 + MH / 2, 1100)
    gr.add_color_stop_rgb(0, 0.06, 0.08, 0.16)
    gr.add_color_stop_rgb(1, 0.01, 0.02, 0.05)
    bc.set_source(gr)
    bc.paint()
    sprites = {}
    m_ = int(math.ceil(BALL_R)) + 2
    for c in range(12):
        s_ = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2 * m_, 2 * m_)
        draw_ball(cairo.Context(s_), m_, m_, BALL_R, PALETTE[c])
        sprites[c] = s_
    frozen = None
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
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
        ctx.set_source_surface(msurf, 0, 0)
        ctx.paint()
        cyc = int(win_b * 30) if win_b >= 0 else 0
        for x, y, c in fr["balls"]:
            ctx.set_source_surface(sprites[(int(c) + cyc) % 12], x - m_, y - m_)
            ctx.paint()
        nx_, _ = nozzle(min(t, end_t) if end_t is not None else t)   # 注ぎ口
        ctx.rectangle(nx_ - 26, 496, 52, NOZZLE_Y + 12 - 496)
        g_ = cairo.LinearGradient(nx_ - 26, 0, nx_ + 26, 0)
        g_.add_color_stop_rgb(0, 0.45, 0.48, 0.55)
        g_.add_color_stop_rgb(0.4, 0.95, 0.97, 1.0)
        g_.add_color_stop_rgb(1, 0.35, 0.38, 0.45)
        ctx.set_source(g_)
        ctx.fill()
        if 0 <= t - T_FAST < 1.4 and not over:
            a_ = t - T_FAST
            k = min(1.0, a_ / 0.15)
            text(ctx, "ボール増量!!", W / 2, Y0 + MH * 0.45, 110 * (1.2 - 0.2 * k), rgb=hsv(t * 2), sw=16,
                 alpha=min(1.0, (1.4 - a_) / 0.3))
        # 文字
        text(ctx, "迷路にボールを流しこむ", W / 2, 235, 60, sw=12)
        text(ctx, "満タンにできる？", W / 2, 335, 96, rgb=GOLD, sw=16)
        n = fr["n"] if not over else res["n"]
        pct = int(100 * n / TOTAL)
        text(ctx, f"満タン度 {pct}%", W / 2 - 150, 435, 56, rgb=(1, 1, 1), sw=10)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2 + 230, 435, 44, rgb=(1, 0.4, 0.4) if left < 10 else (0.95, 0.95, 0.95), sw=8)
        bw = 760   # 満タン度のゲージ
        ctx.rectangle(W / 2 - bw / 2, 462, bw, 22)
        ctx.set_source_rgba(1, 1, 1, 0.15)
        ctx.fill()
        g_ = cairo.LinearGradient(W / 2 - bw / 2, 0, W / 2 + bw / 2, 0)
        for k in range(7):
            g_.add_color_stop_rgb(k / 6, *hsv(k / 7))
        ctx.rectangle(W / 2 - bw / 2, 462, bw * n / TOTAL, 22)
        ctx.set_source(g_)
        ctx.fill()
        if not over:
            scary_text(ctx, "失敗したら・・・", W / 2, 1590, 78, t, drips)
        if over and fail:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 880, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            text(ctx, "時間切れ…", W / 2, 990, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"満タン度 {pct}% だった…", W / 2, 1110, 66, sw=12)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['n']}マス / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def pour(dur, seed, t_fast):
    """ボールが流れ落ちる「ザーッ」「カラカラ」(増量後は大きく)。"""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    y = np.zeros(n)
    t = 0.0
    while t < dur:   # 小さな「カチッ」をたくさん重ねる
        rate = 220 if t < t_fast else 420
        t += rng.exponential(1 / rate)
        i = int(t * SR)
        tc = _t(0.02)
        f = rng.uniform(2500, 5500)
        c = np.sin(2 * np.pi * f * tc) * np.exp(-tc * 300) * rng.uniform(0.3, 1.0)
        j = min(n, i + len(c))
        if i < n:
            y[i:j] += c[: j - i]
    nz = rng.normal(0, 1, n)
    nz = nz - np.convolve(nz, np.ones(8) / 8, "same")
    y += 0.25 * nz * np.where(np.arange(n) / SR < t_fast, 0.6, 1.0)
    return 0.12 * y


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
    add(pour(end_t, 3, T_FAST), 0.0)
    for kind, t, data in events:
        if t > end_t + 0.01:
            continue
        if kind == "fast":
            tb = _t(0.5)
            for k, m in enumerate((79, 84, 91)):
                add(0.5 * np.sign(np.sin(2 * np.pi * midi_hz(m) * tb)) * np.exp(-tb * 6), t + 0.09 * k)
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
