"""「天井に当たるたびにパワー2倍のボール、一番下まで割れる?」(参考動画「Power doubles with each hit」の形)
たて長の穴の下に、うすいオレンジの板が N_LAYER 枚つみ重なっている。ボールのパワーは天井に当たるたびに2倍になる。
ボールは板に当たると、パワーを1使って板を1枚割り、そのまま進む。パワーが0になると板ではね返って天井へもどり、天井に当たるとパワーが前の2倍になる。
制限時間内に全部の板を割れたら成功、割れなければ失敗。

- 重力なし。ボールは一定の速さで、天井・左右の壁・板ではね返る(ねらい・補正なし)。パワーが大きいほどボールは速い。
- 板を割るとき、割れたかけらの勢いでボールの向きがほんの少しずつランダムにずれる(物理のゆらぎ)。
  ななめになるほど左右の壁を行ったり来たりして、天井や板にもどるのに時間がかかる。
- 成功ならパチンコの大当たり風の演出、失敗なら幽霊。

使い方:
    python power_drill.py search [-n 80]
    python power_drill.py render --seed N
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
SUBSTEPS = 8
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

SHAFT_W = 620.0                      # 穴のはば(世界の座標)
BALL_R = 9.0
PITCH = float(os.environ.get("PITCH", 6.0))     # 板1枚の厚み(すき間こみ)
N_LAYER = int(os.environ.get("N_LAYER", 2047))  # 板の枚数(1+2+4+…+1024 = 2047)
TOP0 = 420.0                         # 天井から1枚目の板までのきょり
V0 = float(os.environ.get("V0", 700.0))         # パワー1のときの速さ
V_EXP = float(os.environ.get("V_EXP", 0.3))     # 速さ = V0 × パワー^V_EXP
DRILL_V = float(os.environ.get("DRILL_V", 1500.0))   # 板を割りながら進むときの最高の速さ
JITTER = float(os.environ.get("JITTER", 0.012))      # 板1枚を割るたびの向きのずれ(ラジアン・標準偏差)
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 20.4))
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG
# 画面
SX0 = (W - SHAFT_W) / 2
VIEW_Y = 1020.0                      # ボールを画面のこの高さに映す
VIEW_TOP, VIEW_BOT = 560.0, 1500.0


# ---------------------------------------------------------------- シミュレーション(重力なし・一定の速さ)
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        self.x, self.y = SHAFT_W / 2 + rng.uniform(-60, 60), TOP0 * 0.5
        a = math.pi / 2 + rng.uniform(-0.25, 0.25)    # ほぼ真下に(少しななめ)
        self.dx, self.dy = math.cos(a), math.sin(a)
        self.power = 1
        self.maxp = 1
        self.broken = 0
        self.t = 0.0
        self.events = []
        self.result, self.result_t = None, None
        self.drilling = False

    def top(self):
        return TOP0 + self.broken * PITCH

    def speed(self):
        v = V0 * self.maxp ** V_EXP
        return min(v, DRILL_V) if self.drilling else v

    def step(self, dt):
        self.t += dt
        if self.result is not None and self.result == "success":
            return
        dist = self.speed() * dt
        while dist > 1e-9:
            d = min(dist, BALL_R)
            dist -= d
            self.x += self.dx * d
            self.y += self.dy * d
            if self.x < BALL_R:
                self.x, self.dx = 2 * BALL_R - self.x, -self.dx
                self.events.append(("wall", self.t, None))
            elif self.x > SHAFT_W - BALL_R:
                self.x, self.dx = 2 * (SHAFT_W - BALL_R) - self.x, -self.dx
                self.events.append(("wall", self.t, None))
            if self.y < BALL_R:   # 天井:パワー2倍
                self.y, self.dy = 2 * BALL_R - self.y, -self.dy
                self.maxp *= 2
                self.power = self.maxp
                self.events.append(("ceil", self.t, self.maxp))
            top = self.top()
            if self.y > top - BALL_R and self.dy > 0 and self.broken < N_LAYER:
                if self.power > 0:   # 板を1枚割る(かけらの勢いで向きが少しずれる)
                    self.power -= 1
                    self.broken += 1
                    self.drilling = True
                    da = self.rng.normal(0, JITTER)
                    c, s = math.cos(da), math.sin(da)
                    self.dx, self.dy = self.dx * c - self.dy * s, self.dx * s + self.dy * c
                    if self.broken >= N_LAYER and self.result is None:
                        self.result, self.result_t = "success", self.t
                        self.events.append(("success", self.t, None))
                        return
                else:                # パワー0:はね返る
                    self.y = 2 * (top - BALL_R) - self.y
                    self.dy = -abs(self.dy)
                    self.drilling = False
                    self.events.append(("bounce", self.t, None))
            elif self.dy < 0:
                self.drilling = False
        if self.result is None and self.t >= TIME_LIMIT:
            self.result, self.result_t = "fail", self.t
            self.events.append(("fail", self.t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        b0 = g.broken
        for _ in range(SUBSTEPS):
            if g.result is None:
                g.step(dt)
            else:
                g.t += dt
        if record:
            frames.append({"t": g.t, "x": g.x, "y": g.y, "power": g.power, "maxp": g.maxp,
                           "broken": g.broken, "nb": g.broken - b0, "drill": g.drilling})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "broken": g.broken, "maxp": g.maxp}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), N_LAYER - r["broken"], r["maxp"]


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
ORANGE = (1.0, 0.66, 0.15)


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    draw_ball(ctx, x, y, r * 0.8, PALETTE[(kind * 12 // 7) % 12])


def stripe_pattern(scale):
    """板のしま模様(くり返し)。"""
    h = max(2, int(round(PITCH * scale)))
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 4, h)
    c = cairo.Context(s)
    c.set_source_rgb(0.08, 0.05, 0.02)
    c.paint()
    c.rectangle(0, 0, 4, max(1, h * 0.65))
    c.set_source_rgb(*ORANGE)
    c.fill()
    p = cairo.SurfacePattern(s)
    p.set_extend(cairo.EXTEND_REPEAT)
    return p, h


def fmt(n):
    return f"{n:,}"


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"power_drill_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"power_drill_{seed}.wav")
    final = os.path.join(OUT_DIR, f"power_drill_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"pd_preview_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, W / 2, VIEW_Y, reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=("全部割った!!", "COMPLETE", f"パワー {fmt(res['maxp'])}"))
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    drips = drip_layout(ctx, "失敗したら", W / 2, 1590, 78, "失敗したら・・・", seed)
    bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(bg)
    gr = cairo.LinearGradient(0, 0, 0, H)
    gr.add_color_stop_rgb(0, 0.05, 0.07, 0.17)
    gr.add_color_stop_rgb(1, 0.01, 0.01, 0.04)
    bc.set_source(gr)
    bc.paint()
    S = 1.0
    pat, ph = stripe_pattern(S)
    prng = np.random.default_rng(seed + 9)
    parts = []    # 割れた板のかけら [x, y(世界), vx, vy, t0]
    cam = VIEW_Y - frames[0]["y"]
    ceil_t = -9.0
    frozen = None
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "ceil":
                ceil_t = et
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
        # カメラ:ボールを追いかける(天井より上は映さない)
        want = VIEW_Y - fr["y"]
        cam += (want - cam) * 0.25
        cam = min(cam, VIEW_TOP + 40)

        def sy(y):
            return y + cam

        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        ctx.save()
        ctx.rectangle(0, VIEW_TOP - 30, W, VIEW_BOT - VIEW_TOP + 30)
        ctx.clip()
        # 板(残っている分)
        top_y = sy(TOP0 + fr["broken"] * PITCH)
        bot_y = sy(TOP0 + N_LAYER * PITCH)
        if top_y < VIEW_BOT and fr["broken"] < N_LAYER:
            m = cairo.Matrix()
            m.translate(0, -(TOP0 % PITCH + cam))
            pat.set_matrix(m)
            ctx.rectangle(SX0, max(top_y, VIEW_TOP - 30), SHAFT_W, min(bot_y, VIEW_BOT) - max(top_y, VIEW_TOP - 30))
            ctx.set_source(pat)
            ctx.fill()
        if bot_y < VIEW_BOT:   # 底
            ctx.rectangle(SX0 - 10, bot_y, SHAFT_W + 20, 10)
            ctx.set_source_rgb(0.85, 0.9, 1.0)
            ctx.fill()
        # かけら
        nb = fr["nb"] if not over else 0
        for _ in range(min(nb, 40)):
            parts.append([SX0 + fr["x"] + prng.normal(0, 60), TOP0 + fr["broken"] * PITCH + prng.uniform(-4, 4),
                          prng.normal(0, 260), prng.uniform(-700, -150), t])
        keep = []
        for p_ in parts:
            age = t - p_[4]
            if age > 1.4:
                continue
            x = p_[0] + p_[2] * age
            y = p_[1] + p_[3] * age + 900 * age * age
            ctx.rectangle(x, sy(y), 4, 3)
            ctx.set_source_rgba(1, 0.8, 0.3, max(0.0, 1 - age / 1.4))
            ctx.fill()
            keep.append(p_)
        parts = keep[-1500:]
        # 穴のかべと天井
        ctx.set_source_rgba(0.9, 0.95, 1.0, 0.9)
        ctx.set_line_width(4)
        ctx.move_to(SX0, sy(0))
        ctx.line_to(SX0, VIEW_BOT + 50)
        ctx.move_to(SX0 + SHAFT_W, sy(0))
        ctx.line_to(SX0 + SHAFT_W, VIEW_BOT + 50)
        ctx.stroke()
        k_ = math.exp(-(t - ceil_t) * 5) if t >= ceil_t else 0.0
        if sy(0) > VIEW_TOP - 40:
            ctx.move_to(SX0, sy(0))
            ctx.line_to(SX0 + SHAFT_W, sy(0))
            ctx.set_source_rgba(1, 1, 1, 0.9)
            ctx.set_line_width(5 + 8 * k_)
            ctx.stroke()
        # ボール(光る)
        bx, by = SX0 + fr["x"], sy(fr["y"])
        g_ = cairo.RadialGradient(bx, by, 0, bx, by, 60 + 40 * k_)
        g_.add_color_stop_rgba(0, 1, 0.95, 0.75, 0.6 + 0.3 * k_)
        g_.add_color_stop_rgba(1, 1, 0.8, 0.4, 0)
        ctx.arc(bx, by, 60 + 40 * k_, 0, 2 * math.pi)
        ctx.set_source(g_)
        ctx.fill()
        ctx.arc(bx, by, BALL_R, 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 0.95)
        ctx.fill()
        ctx.restore()
        text(ctx, fmt(fr["power"]), bx, by - 22, 38 * (1 + 0.5 * k_), rgb=(1, 1, 1) if k_ < 0.3 else GOLD, sw=7)
        # 文字
        text(ctx, "天井に当たるたびにパワー2倍", W / 2, 235, 60, sw=12)
        text(ctx, f"板{fmt(N_LAYER)}枚、全部割れる？", W / 2, 335, 86, rgb=GOLD, sw=16)
        left_n = N_LAYER - (fr["broken"] if not over else res["broken"])
        text(ctx, f"あと {fmt(left_n)} 枚", W / 2 - 140, 445, 62, rgb=(1, 1, 1), sw=10)
        tt = min(t, end_t) if end_t is not None else t
        left = max(0.0, TIME_LIMIT - tt)
        text(ctx, f"残り {left:4.1f}秒", W / 2 + 250, 445, 44, rgb=(1, 0.4, 0.4) if left < 10 else (0.95, 0.95, 0.95), sw=8)
        if not over:
            scary_text(ctx, "失敗したら・・・", W / 2, 1590, 78, t, drips)
        if over and fail:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 880, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            text(ctx, "時間切れ…", W / 2, 990, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと {fmt(left_n)} 枚だった…", W / 2, 1110, 66, sw=12)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} 残り{N_LAYER - res['broken']}枚 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def power_up(p):
    """天井でパワー2倍の「キュイーン」(パワーが大きいほど高い)。"""
    t = _t(0.45)
    k = math.log2(p)
    f0 = midi_hz(55 + 3 * k)
    f = f0 * (1 + 1.0 * (1 - np.exp(-t / 0.08)))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sign(np.sin(ph))
    tb = _t(0.6)
    bell = np.sin(2 * np.pi * 2 * f0 * 2 * tb) * np.exp(-tb * 6)
    out = 0.5 * y * np.minimum(1, t / 0.01) * np.exp(-t * 4)
    out = np.concatenate([out, np.zeros(len(tb) - len(out))]) if len(tb) > len(out) else out
    out[:len(bell)] += 0.35 * bell[:len(out)]
    return out


def crackle(nb, seed):
    """板が割れる「パキパキ」(1フレーム分・割れた枚数に応じて)。"""
    rng = np.random.default_rng(seed)
    n = int(SR / FPS)
    y = np.zeros(n + 400)
    for _ in range(min(nb, 6)):
        i = int(rng.integers(0, n))
        tc = _t(0.008)
        c = np.sin(2 * np.pi * rng.uniform(1800, 4200) * tc) * np.exp(-tc * 600) * rng.uniform(0.5, 1.0)
        y[i:i + len(c)] += c
    return 0.5 * y


def tick():
    t = _t(0.05)
    return 0.25 * np.sin(2 * np.pi * 900 * t) * np.exp(-t * 80)


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    frames = res["frames"]
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)

    def add(sig, t0, gain=1.0, buf=None):
        b = out if buf is None else buf
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out and j > i:
            b[i:j] += gain * sig[: j - i]
    for k, fr in enumerate(frames):
        if fr["nb"] > 0 and fr["t"] <= end_t:
            add(crackle(fr["nb"], k), fr["t"] - 1 / FPS)
    rw = []
    for kind, t, data in events:
        if t > end_t + 0.01:
            continue
        if kind == "ceil":
            add(power_up(data), t, 1.2)
        elif kind in ("wall", "bounce"):
            rw = [x for x in rw if t - x < 0.08]
            if len(rw) >= 2:
                continue
            rw.append(t)
            add(tick(), t)
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
        tt = 0.0
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
