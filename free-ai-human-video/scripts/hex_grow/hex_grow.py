"""「当たるたびに大きくなる玉、出られなくなるまで大きくなれる?」ゆっくり回る六角形の中を、1個の玉が重力で跳ねる。
壁に当たるたびに玉が少しずつ大きくなる。六角形の1辺にはすき間があり、そこから外へ落ちたら失敗。
すき間より大きくなって、もう出られなくなったら成功。

- 玉はチャンネルのサムネの女の子(おかっぱの幽霊)の顔+光る輪(icon_spiral/icon_ball.py の絵)。転がるぶんだけ回る。
- 重力・反発・回転する壁による押し出しのまま(ねらい・補正なし)。玉はいつも少しだけ弾む(反発係数1未満)。
- 大きくなるのは「六角形の壁に新しくぶつかった瞬間」だけ(ずっと触れていても増えない)。
- 成功(すき間より大きくなった)ならパチンコの当たり風の演出、失敗(すき間から落ちた)なら幽霊。

使い方:
    python hex_grow.py search [-n 60]
    python hex_grow.py render --seed N
"""

import argparse
import colorsys
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
from pachinko import kyuin_music  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "glass_spiral"))
import jackpot_end as JP  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "icon_spiral"))
import icon_ball as IB  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 6
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

CX, CY = 540.0, 990.0
HEX_R = 420.0                                     # 六角形の外接円の半径
SPIN = float(os.environ.get("SPIN", 0.55))        # 六角形が回る速さ(ラジアン/秒)
GAP = float(os.environ.get("GAP", 145.0))         # すき間の幅(px)
R0 = 14.0                                         # はじめの玉の半径
DR = float(os.environ.get("DR", 1.6))             # 1回当たるごとに大きくなる量(半径・px)
GRAVITY = 1400.0
BALL_E = float(os.environ.get("BALL_E", 0.93))    # 玉の弾み
WALL_E = 1.0
WIN_R = GAP / 2 * 1.04                            # この半径をこえたら、すき間を通れない=成功
OUTRO = 4.2
MAX_T = 90.0


def hex_pts(rot):
    return [(CX + HEX_R * math.cos(rot + math.pi / 2 + k * math.pi / 3),
             CY + HEX_R * math.sin(rot + math.pi / 2 + k * math.pi / 3)) for k in range(6)]


def hex_local():
    """六角形の壁(回転の中心が原点)。下の辺(k=0→1 の辺)にすき間。辺ごとに (a, b) の線分。"""
    p = [(HEX_R * math.cos(math.pi / 2 + k * math.pi / 3), HEX_R * math.sin(math.pi / 2 + k * math.pi / 3)) for k in range(6)]
    segs = []
    for k in range(6):
        a, b = p[k], p[(k + 1) % 6]
        if k == 0:   # すき間のある辺:まん中を GAP だけあける
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            h = (L - GAP) / 2
            segs.append((a, (a[0] + u[0] * h, a[1] + u[1] * h)))
            segs.append(((b[0] - u[0] * h, b[1] - u[1] * h), b))
        else:
            segs.append((a, b))
    return segs


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 25
        self.space = sp
        hb = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        hb.position = (CX, CY)
        hb.angle = math.pi + rng.uniform(-0.4, 0.4)   # はじめ、すき間は上にある(始まってすぐ落ちないように)
        hb.angular_velocity = SPIN
        walls = []
        for a, b in hex_local():
            s = pymunk.Segment(hb, a, b, 7)
            s.elasticity, s.friction = WALL_E, 0.6
            s.collision_type = 2
            walls.append(s)
        sp.add(hb, *walls)
        self.hexb = hb
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, R0))
        b.position = (CX + rng.uniform(-60, 60), CY - rng.uniform(0, 120))
        b.velocity = (rng.uniform(-300, 300), rng.uniform(-200, 100))
        s = pymunk.Circle(b, R0)
        s.elasticity, s.friction = BALL_E, 0.6
        s.collision_type = 1
        sp.add(b, s)
        self.ball, self.shape = b, s
        self.r = R0
        self.hits = 0
        self.t = 0.0
        self.events = []
        self.pending = 0
        self.result, self.result_t = None, None
        sp.on_collision(1, 2, begin=self._hit)

    def _hit(self, arb, space, data):
        if self.result is None:
            self.pending += 1
            self.events.append(("hit", self.t, (self.r, arb.total_impulse.length if hasattr(arb, "total_impulse") else 0)))
        return True

    def step(self, dt):
        self.space.step(dt)
        self.t += dt
        if self.pending:   # 当たった瞬間に大きくなる
            self.pending = 0
            self.hits += 1
            self.r += DR
            self.shape.unsafe_set_radius(self.r)
            m = (self.r / R0) ** 2
            self.ball.mass = m
            self.ball.moment = pymunk.moment_for_circle(m, 0, self.r)
            self.events.append(("grow", self.t, (self.r, self.hits)))
        if self.result is None:
            d = math.hypot(self.ball.position.x - CX, self.ball.position.y - CY)
            if d > HEX_R + self.r + 10:   # すき間から外へ出た
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, None))
            elif self.r >= WIN_R:          # すき間より大きくなった=もう出られない
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t > MAX_T:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, "time"))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    fall_show = 1.0   # 失敗のときは、落ちていくところを少し見せてから幽霊
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "x": g.ball.position.x, "y": g.ball.position.y, "ang": g.ball.angle,
                           "r": g.r, "hits": g.hits, "rot": g.hexb.angle})
        if g.result is not None:
            extra = (fall_show + OUTRO + SCARE_DUR) if g.result == "fail" else JP.DURATION
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "r": g.r, "hits": g.hits}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), r["hits"], round(r["r"], 1)


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def ball_col(r):
    """玉の光の色:大きくなるほど 青 → 紫 → ピンク → 赤 → 金 と変わる。"""
    k = min(1.0, (r - R0) / (WIN_R - R0))
    return colorsys.hsv_to_rgb((0.6 - 0.75 * k) % 1.0, 0.75, 1.0)


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    """当たり演出のリールの絵柄:光る女の子の顔(7色。7番目=虹色が揃う)。"""
    col = colorsys.hsv_to_rgb((t * 0.7) % 1.0, 0.8, 1.0) if kind == 6 else colorsys.hsv_to_rgb(kind / 7, 0.75, 1.0)
    g = cairo.RadialGradient(x, y, r * 0.5, x, y, r * 1.5)
    g.add_color_stop_rgba(0, *col, 0.6 * alpha)
    g.add_color_stop_rgba(1, *col, 0)
    ctx.arc(x, y, r * 1.5, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    ctx.save()
    ctx.translate(x, y)
    IB.draw_face(ctx, r * 0.85, col, alpha)
    ctx.restore()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"hex_grow_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"hex_grow_{seed}.wav")
    final = os.path.join(OUT_DIR, f"hex_grow_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"hg_preview_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, CX, CY, reel_ball, n_kinds=7, win=6, shake=16,
                                          texts=("出られない!!", "COMPLETE", f"{res['hits']}回で成功"))
    g0 = (end_t + 1.0) if fail else end_t   # 幽霊が出る時刻(落ちていくところを1秒見せる)
    trail = []
    rings = []
    ev_i = 0
    bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(bg)
    gr = cairo.RadialGradient(CX, CY, 50, CX, CY, 1100)
    gr.add_color_stop_rgb(0, 0.1, 0.08, 0.18)
    gr.add_color_stop_rgb(1, 0.02, 0.02, 0.05)
    bc.set_source(gr)
    bc.paint()
    frozen = None
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "grow":
                rings.append((et,))
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ending is not None and over and t - end_t >= 1 / FPS - 1e-9:
            ending.draw(surf, ctx, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        if ghost is not None and t >= g0 and t - g0 < SCARE_DUR:
            ghost.draw(surf, t - g0)
            ff.stdin.write(surf.get_data())
            continue
        if fail and t >= g0:
            if frozen is None:
                frozen = fr
            fr = frozen
        after = (t - g0 - SCARE_DUR) if (fail and t >= g0) else 0
        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        # 六角形(ゆっくり回る。すき間は赤く光る)
        rot = fr["rot"]
        ca, sa = math.cos(rot), math.sin(rot)
        tf = lambda p: (CX + p[0] * ca - p[1] * sa, CY + p[0] * sa + p[1] * ca)   # noqa: E731
        segs = [(tf(a), tf(b)) for a, b in hex_local()]
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for wd, al in ((26, 0.12), (14, 0.3), (7, 1.0)):
            for k, (a, b) in enumerate(segs):
                ctx.move_to(*a)
                ctx.line_to(*b)
                hue = (t * 0.08 + k / 7) % 1.0
                ctx.set_source_rgba(*colorsys.hsv_to_rgb(hue, 0.5, 1.0), al)
                ctx.set_line_width(wd)
                ctx.stroke()
        # すき間の目印
        a, b = segs[0][1], segs[1][0]
        ctx.move_to(*a)
        ctx.line_to(*b)
        ctx.set_dash([10, 10])
        ctx.set_source_rgba(1, 0.3, 0.3, 0.7)
        ctx.set_line_width(3)
        ctx.stroke()
        ctx.set_dash([])
        # 玉(光の尾+光る輪+女の子の顔)
        x, y, r = fr["x"], fr["y"], fr["r"]
        col = ball_col(r)
        trail.append((x, y, r))
        trail = trail[-14:]
        for j, (tx, ty, tr) in enumerate(trail[:-1]):
            k = (j + 1) / len(trail)
            ctx.arc(tx, ty, tr * (0.5 + 0.5 * k), 0, 2 * math.pi)
            ctx.set_source_rgba(*col, 0.18 * k)
            ctx.fill()
        for mul, al in ((2.2, 0.18), (1.5, 0.35)):
            g = cairo.RadialGradient(x, y, r * 0.8, x, y, r * mul)
            g.add_color_stop_rgba(0, *col, al)
            g.add_color_stop_rgba(1, *col, 0)
            ctx.arc(x, y, r * mul, 0, 2 * math.pi)
            ctx.set_source(g)
            ctx.fill()
        keep = []
        for (t0,) in rings:   # 大きくなった瞬間の光の輪
            a_ = t - t0
            if a_ < 0.3:
                ctx.arc(x, y, r * (1.05 + 0.8 * a_), 0, 2 * math.pi)
                ctx.set_source_rgba(1, 1, 1, 0.8 * (1 - a_ / 0.3))
                ctx.set_line_width(3)
                ctx.stroke()
                keep.append((t0,))
        rings = keep
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(fr["ang"])
        IB.draw_face(ctx, r * 1.08, col)
        ctx.restore()
        # 文字
        text(ctx, "当たるたびに大きくなる玉", W / 2, 235, 62, sw=12)
        text(ctx, "すき間から出る前に", W / 2, 320, 56, sw=10)
        text(ctx, "出られない大きさになれる？", W / 2, 400, 70, rgb=GOLD, sw=14)
        pct = min(100.0, 100 * (r - R0) / (WIN_R - R0))
        bx, by, bw, bh = 140, 1475, W - 280, 30   # 大きさのメーター(100%で出られない)
        ctx.rectangle(bx, by, bw, bh)
        ctx.set_source_rgba(1, 1, 1, 0.15)
        ctx.fill()
        ctx.rectangle(bx, by, bw * pct / 100, bh)
        ctx.set_source_rgb(*col)
        ctx.fill()
        ctx.rectangle(bx, by, bw, bh)
        ctx.set_source_rgb(1, 1, 1)
        ctx.set_line_width(3)
        ctx.stroke()
        text(ctx, f"当たった回数 {fr['hits']}  ・  大きさ {pct:.0f}%", W / 2, 1535, 40, sw=8)
        if fail and t >= g0:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 880, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            text(ctx, "落ちた…", W / 2, 990, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"大きさ{pct:.0f}%までだった…", W / 2, 1110, 66, sw=12)
        elif ending is not None and over:
            ending.draw(surf, ctx, t - end_t)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['hits']}回・半径{res['r']:.0f} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def bounce(f, amp):
    """壁に当たる「ポン」+ ふくらむ「ぷくっ」(玉が大きくなるほど低く太い音)。"""
    t = _t(0.35)
    body = np.sin(2 * np.pi * f * t * (1 - 0.15 * t)) * np.exp(-t * 9)
    puff = np.sin(2 * np.pi * np.cumsum(f * 1.5 * (1 + 0.6 * np.minimum(1, t / 0.08))) / SR) * np.exp(-np.maximum(0, t - 0.02) * 25) * (t > 0.02)
    return amp * (body + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 14) + 0.4 * puff)


def kyuin_one(up=1.0):
    t = _t(0.28)
    f = up * (500 + 2900 * (1 - np.exp(-t / 0.06))) * (1 + 0.03 * np.sin(2 * np.pi * 32 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.35 * np.sign(np.sin(ph)) + 0.3 * np.sin(2 * ph)
    return y * np.minimum(1, t / 0.01) * np.exp(-np.maximum(0, t - 0.16) / 0.05)


def fall_whoosh(amp):
    t = _t(1.0)
    f = 900 * np.exp(-t * 2.2) + 120
    return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.05) * np.exp(-t * 1.5)


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
    scale = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23, 24]
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.01:
            continue
        if kind == "grow":   # 当たるたびに、音階が1つずつ上がっていく(大きくなるほどゴージャスに)
            r, hits = data
            m = 60 + scale[min(len(scale) - 1, hits // 4)] + [0, 4, 7, 12][hits % 4]
            add(bounce(midi_hz(m), 0.6), t)
    if fail:
        add(fall_whoosh(0.7), end_t)
    wet = out.copy()
    for dd, g_ in ((0.043, 0.25), (0.071, 0.16), (0.11, 0.1)):
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
        g0 = end_t + 1.0
        sig = scream(SR)
        i0 = int(g0 * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
        sig = fail_music(SR, OUTRO)
        i0 = int((g0 + SCARE_DUR) * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += 0.6 * sig[:m]
    else:
        b_ = JP.music(SR, 3)
        b_ = b_.mean(axis=1) if b_.ndim == 2 else b_
        n = int(JP.DURATION * SR)
        mus = np.zeros(n)
        mus[:min(n, len(b_))] += b_[:n] / (np.abs(b_).max() + 1e-9)
        a_ = kyuin_music(SR, JP.DURATION - JP.T_BIG)
        i = int(JP.T_BIG * SR)
        m = min(len(a_), n - i)
        mus[i:i + m] += 0.8 * a_[:m]
        tt = JP.T_BIG
        while tt < JP.DURATION - 0.5:
            ky = kyuin_one(1.0 + 0.15 * ((int(tt / 0.3)) % 3))
            i = int(tt * SR)
            m = min(len(ky), n - i)
            mus[i:i + m] += 0.4 * ky[:m]
            tt += 0.3
        mus *= np.minimum(1, (JP.DURATION - np.arange(n) / SR) / 0.6)
        mus = np.tanh(1.6 * mus / (np.abs(mus).max() + 1e-9)) / np.tanh(1.6)
        i0 = int(end_t * SR)
        m = min(len(mus), n_out - i0)
        extra[i0:i0 + m] += 1.1 * mus[:m]
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
    ap.add_argument("-n", type=int, default=60)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
