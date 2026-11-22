"""「レーザーで切って100個にできる?」丸いわくの中を、まん中を通るレーザーがゆっくり回る。
ボールがレーザーに切られるたびに、面積が半分の2個に分かれる。小さくなりすぎたボールは、切られると消えてしまう。
制限時間内に100個になれば成功、ならなければ失敗。

- 重力なし。ボールはいつも同じ速さで、わく・ほかのボールで跳ね返る(ねらい・補正なし)。
- 「切られる」=レーザーの線がボールに少しでも触れた瞬間(レーザーが回って触れても、ボールが動いて触れても)。
  分かれた2個はレーザーをはさんだ反対側(別の部屋)に1個ずつ、はじけるように飛び出す。分かれたばかりのボールは IMMUNE 秒のあいだ切られない。
- 半径が R_MIN より小さいボールが切られると、2個にならずに消える。
- はじめの LASER_ON 秒はレーザーのスイッチが切れていて、ボールは1個だけ。
- 成功ならパチンコの当たり風の演出、失敗なら幽霊。

使い方:
    python ball_laser.py search [-n 80]
    python ball_laser.py render --seed N
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

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

CX, CY, R = 540.0, 1030.0, 460.0
R0 = float(os.environ.get("R0", 220.0))            # はじめのボールの半径
R_MIN = float(os.environ.get("R_MIN", 3.0))       # これより小さいボールは、切られると消える
SPEED = float(os.environ.get("SPEED", 260.0))
SPIN = float(os.environ.get("SPIN", 0.9))         # レーザーが回る速さ(ラジアン/秒)
IMMUNE = 0.35
KICK = 140.0                                      # 分かれたボールが両側へはじける速さ
LASER_ON = 1.0                                    # この時間にレーザーのスイッチが入る(それまでは1個だけ)
TARGET = int(os.environ.get("TARGET", 2000))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 22.2))
OUTRO = 4.2
WIN_DUR = JP.DURATION - JP.T_BIG


def laser_ang(t):
    return SPIN * t


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, 0)
        sp.iterations = 12
        self.space = sp
        n = 120
        pts = [(CX + (R + 10) * math.cos(2 * math.pi * k / n), CY + (R + 10) * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
        for a, b in zip(pts, pts[1:]):
            s = pymunk.Segment(sp.static_body, a, b, 10)
            s.elasticity, s.friction = 1.0, 0.0
            sp.add(s)
        self.balls = {}
        self.next_id = 0
        self.t = 0.0
        self.events = []
        self.result, self.result_t = None, None
        # はじめの1個は、レーザー(t=0 で横向き)に触れない上か下に置く
        a = rng.choice([-1, 1]) * (math.pi / 2 + rng.uniform(-0.15, 0.15))
        p = (CX + (R - R0 - 1) * math.cos(a), CY + (R - R0 - 1) * math.sin(a))
        va = rng.uniform(0, 2 * math.pi)
        self.add(p, (SPEED * math.cos(va), SPEED * math.sin(va)), R0, 0, -1.0)
        self.best = 1

    def add(self, pos, vel, r, gen, born):
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, r))
        b.position, b.velocity = pos, vel
        s = pymunk.Circle(b, r)
        s.elasticity, s.friction = 1.0, 0.0
        self.space.add(b, s)
        self.balls[b] = {"id": self.next_id, "shape": s, "r": r, "gen": gen, "born": born, "side": None}
        self.next_id += 1

    def side(self, b, ang):
        """ボールのまん中が、レーザーの線のどちら側にあるか(+1 / -1)。"""
        dx, dy = b.position.x - CX, b.position.y - CY
        return 1 if (math.cos(ang) * dy - math.sin(ang) * dx) >= 0 else -1

    def step(self, dt):
        self.space.step(dt)
        self.t += dt
        ang = laser_ang(self.t)
        cuts = []
        for b, info in self.balls.items():
            v = b.velocity   # いつも同じ速さ
            n = v.length
            if n > 1e-6:
                b.velocity = v * (SPEED / n)
            d = b.position - (CX, CY)
            if d.length > R - info["r"]:
                b.position = pymunk.Vec2d(CX, CY) + d.normalized() * (R - info["r"] - 1)
            dist = math.cos(ang) * (b.position.y - CY) - math.sin(ang) * (b.position.x - CX)
            if self.t >= LASER_ON and abs(dist) < info["r"] and self.t - info["born"] > IMMUNE and self.result is None:
                cuts.append(b)   # レーザーに触れた
        cuts.sort(key=lambda b_: self.balls[b_]["id"])
        nx, ny = -math.sin(ang), math.cos(ang)   # レーザーに垂直な向き
        for b in cuts:
            info = self.balls.pop(b)
            self.space.remove(b, info["shape"])
            p, v, r = b.position, b.velocity, info["r"]
            if r < R_MIN:   # 小さすぎ:消える
                self.events.append(("vanish", self.t, (p.x, p.y, r, info["gen"], len(self.balls))))
                continue
            r2 = r / math.sqrt(2)
            dist = nx * (p.x - CX) + ny * (p.y - CY)   # レーザーの線からの距離(符号つき)
            for sgn in (1, -1):   # レーザーをはさんで、反対側の部屋に1個ずつ
                off = sgn * r2 * 1.05 - dist
                q = (p.x + nx * off, p.y + ny * off)
                vv = (v.x + sgn * nx * KICK, v.y + sgn * ny * KICK)
                self.add(q, vv, r2, info["gen"] + 1, self.t)
            self.events.append(("split", self.t, (p.x, p.y, r, info["gen"] + 1, len(self.balls))))
            self.best = max(self.best, len(self.balls))
        if self.result is None:
            if len(self.balls) >= TARGET:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT or not self.balls:
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
            frames.append({"t": g.t, "ang": laser_ang(g.t), "n": len(g.balls),
                           "balls": [(b.position.x, b.position.y, i["r"], i["gen"]) for b, i in g.balls.items()]})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else WIN_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "n": g.final_n, "best": g.best}


def score(seed):
    r = simulate(seed)
    van = sum(1 for e in r["events"] if e[0] == "vanish")
    return seed, r["result"], round(r["result_t"], 1), r["n"], r["best"], van


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def gen_col(g):
    return colorsys.hsv_to_rgb((0.55 + 0.11 * g) % 1.0, 0.75, 1.0)


def draw_ball(ctx, x, y, r, col):
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r)
    g.add_color_stop_rgb(0, *(min(1, c + 0.5) for c in col))
    g.add_color_stop_rgb(0.5, *col)
    g.add_color_stop_rgb(1, *(c * 0.55 for c in col))
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    draw_ball(ctx, x, y, r * 0.8, gen_col(kind))


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"ball_laser_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"ball_laser_{seed}.wav")
    final = os.path.join(OUT_DIR, f"ball_laser_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"bl_preview_{pt:.1f}.png"))
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
                                          texts=(f"{TARGET}個!!", "COMPLETE", f"{res['n']} 個"))
    sparks = []
    bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(bg)
    gr = cairo.RadialGradient(CX, CY, 50, CX, CY, 1100)
    gr.add_color_stop_rgb(0, 0.08, 0.06, 0.14)
    gr.add_color_stop_rgb(1, 0.02, 0.02, 0.05)
    bc.set_source(gr)
    bc.paint()
    bc.arc(CX, CY, R, 0, 2 * math.pi)
    bc.set_source_rgba(0, 0, 0, 0.35)
    bc.fill()
    frozen = None
    ev_i = 0
    sprites = {}
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind in ("split", "vanish") and len(sparks) < 60:
                sparks.append((data[0], data[1], data[2], kind, et))
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ending is not None and over:
            ending.draw(surf, ctx, t - end_t + JP.T_BIG)
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
        for wd, al in ((14, 0.15), (5, 1.0)):
            ctx.arc(CX, CY, R + 4, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, al)
            ctx.set_line_width(wd)
            ctx.stroke()
        for x, y, r, g in fr["balls"]:
            sp_ = sprites.get(g)
            if sp_ is None:   # 世代ごとに大きさが決まっているので、絵を作り置きする
                m_ = int(math.ceil(r)) + 2
                sp_ = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2 * m_, 2 * m_)
                draw_ball(cairo.Context(sp_), m_, m_, r, gen_col(g))
                sprites[g] = sp_ = (sp_, m_)
            ctx.set_source_surface(sp_[0], x - sp_[1], y - sp_[1])
            ctx.paint()
        # レーザー(赤く光る線。まん中に回転の軸)
        a = fr["ang"]
        x0, y0 = CX - R * math.cos(a), CY - R * math.sin(a)
        x1, y1 = CX + R * math.cos(a), CY + R * math.sin(a)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for wd, col, al in ((26, (1, 0.1, 0.2), 0.18), (12, (1, 0.2, 0.3), 0.45), (4, (1, 0.9, 0.9), 1.0)):
            ctx.move_to(x0, y0)
            ctx.line_to(x1, y1)
            on = 1.0 if t >= LASER_ON else 0.12 + 0.08 * (math.sin(t * 25) > 0)   # スイッチ前はうすく点滅
            ctx.set_source_rgba(*col, on * al * (0.85 + 0.15 * math.sin(t * 40)))
            ctx.set_line_width(wd)
            ctx.stroke()
        ctx.arc(CX, CY, 16, 0, 2 * math.pi)
        ctx.set_source_rgb(0.9, 0.9, 0.95)
        ctx.fill()
        keep = []
        for x, y, r, kind, t0 in sparks:   # 切れた瞬間の火花 / 消えるときの煙
            a_ = t - t0
            if a_ < 0.35:
                k = 1 - a_ / 0.35
                if kind == "split":
                    for j in range(6):
                        aa = 2 * math.pi * j / 6 + t0 * 7
                        d = r * 0.6 + 90 * a_
                        ctx.arc(x + d * math.cos(aa), y + d * math.sin(aa), 3 * k + 1, 0, 2 * math.pi)
                        ctx.set_source_rgba(1, 0.9, 0.5, k)
                        ctx.fill()
                else:
                    ctx.arc(x, y, r + 30 * a_, 0, 2 * math.pi)
                    ctx.set_source_rgba(0.7, 0.7, 0.75, 0.6 * k)
                    ctx.set_line_width(3)
                    ctx.stroke()
                keep.append((x, y, r, kind, t0))
        sparks = keep
        # 文字
        text(ctx, "レーザーで切ると2つに分かれるボール", W / 2, 235, 56, sw=12)
        text(ctx, f"{TARGET}個にできる？", W / 2, 335, 96, rgb=GOLD, sw=16)
        n = fr["n"] if not over else res["n"]
        text(ctx, f"{n} / {TARGET} 個", W / 2, 445, 70, rgb=(1, 1, 1), sw=10)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 522, 40, rgb=(1, 0.4, 0.4) if left < 10 else (0.95, 0.95, 0.95), sw=8)
        if not over:
            text(ctx, "失敗したら・・・", W / 2, 1530, 54, rgb=(1, 0.45, 0.45), sw=10)
        if over and fail:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 880, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            text(ctx, "時間切れ…", W / 2, 990, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"{res['n']}個までだった…", W / 2, 1110, 66, sw=12)
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


def zap(f, amp):
    """切れる「ジュッ」+分かれる「ポン」(小さいボールほど高い)。"""
    t = _t(0.25)
    n = np.random.default_rng(int(f)).normal(0, 1, len(t))
    hp = n - np.convolve(n, np.ones(5) / 5, "same")
    sizzle = hp * np.exp(-t * 30) * 0.5
    pon = np.sin(2 * np.pi * f * t) * np.exp(-t * 16) + 0.3 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 26)
    return amp * (sizzle + pon)


def poof(amp, seed):
    """消える「パシュッ」。"""
    t = _t(0.3)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    f = 500 * np.exp(-t * 8) + 150
    return amp * (0.6 * n * np.exp(-t * 25) + 0.4 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 10))


def hum(dur):
    """レーザーの低いうなり。"""
    t = _t(dur)
    return 0.15 * (np.sin(2 * np.pi * 110 * t) + 0.5 * np.sin(2 * np.pi * 220.7 * t)) * (0.8 + 0.2 * np.sin(2 * np.pi * 6 * t))


def kyuin_one(up=1.0):
    t = _t(0.28)
    f = up * (500 + 2900 * (1 - np.exp(-t / 0.06))) * (1 + 0.03 * np.sin(2 * np.pi * 32 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.35 * np.sign(np.sin(ph)) + 0.3 * np.sin(2 * ph)
    return y * np.minimum(1, t / 0.01) * np.exp(-np.maximum(0, t - 0.16) / 0.05)


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
    add(hum(end_t - LASER_ON), LASER_ON)
    tb = _t(0.4)   # スイッチが入る「ブォン」
    add(0.8 * np.sin(2 * np.pi * np.cumsum(60 + 200 * (1 - np.exp(-tb * 12))) / SR) * np.exp(-tb * 5), LASER_ON - 0.05)
    recent = []
    for kind, t, data in events:
        if t > end_t + 0.01:
            continue
        recent = [x for x in recent if t - x < 0.1]
        if len(recent) >= 6:
            continue
        recent.append(t)
        if kind == "split":
            r = data[2]
            m = 55 + int(round(7 * math.log2(R0 / r)))
            add(zap(midi_hz(min(100, m)), 0.6), t)
        elif kind == "vanish":
            add(poof(0.5, int(t * 100)), t)
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
    ap.add_argument("-n", type=int, default=80)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
