"""「シーソーに○個のせられる?」まん中で支えた長いシーソーに、上の落とし口からいろいろな大きさ・重さのボールが落ちてくる。
重いほうにかたむくと、ボールが転がってはしからこぼれ落ちる。シーソーの上のボールが TARGET 個になったら成功。

- シーソーはまん中の支点で自由に回る(ばねで少しだけ水平にもどろうとする。かたむきは最大 MAX_TILT まで)。
- 落とし口は上を左右に行ったり来たりしていて、INTERVAL 秒ごとに1個落とす(落とす場所をねらったりしない)。
- ボールはやわらかく、ころがり抵抗がある(かたむきがゆるいとその場にとどまり、急になるとすべり落ちる)。
- ボールの重さは面積に比例(大きいほど重い)。10個ごとに、とても重い金のボールが落ちてくる。
- ボールの動きは物理計算のまま(ねらい・補正なし)。
- 成功ならパチンコの大当たり風の演出、失敗なら幽霊。

使い方:
    python seesaw.py search [-n 80]
    python seesaw.py render --seed N
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

PIV_X, PIV_Y = W / 2, 1300.0
PLANK_L = float(os.environ.get("PLANK_L", 820.0))
PLANK_T = 18.0
PLANK_M = 30.0
MAX_TILT = float(os.environ.get("MAX_TILT", 0.42))
SPRING_K = float(os.environ.get("SPRING_K", 2.0e7))
SPRING_D = float(os.environ.get("SPRING_D", 8.0e5))
DROP_Y = 700.0
DROP_AMP = float(os.environ.get("DROP_AMP", 330.0))
INTERVAL = float(os.environ.get("INTERVAL", 0.55))
R_MIN, R_MAX = 14.0, 30.0
GOLD_EVERY = 10
GOLD_R = 40.0
GOLD_DENS = 3.0
FRICTION = float(os.environ.get("FRICTION", 0.6))
ROLL_DAMP = float(os.environ.get("ROLL_DAMP", 0.9))   # 1ステップごとの回転の残り方
TARGET = int(os.environ.get("TARGET", 24))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 35.0))
GRAVITY = 1500.0
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG


def dropper_x(t, w, ph):
    return PIV_X + DROP_AMP * math.sin(w * t + ph)


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 20
        self.space = sp
        self.plank = pb = pymunk.Body(PLANK_M, pymunk.moment_for_box(PLANK_M, (PLANK_L, PLANK_T)) * 4)
        pb.position = (PIV_X, PIV_Y - PLANK_T / 2 - 10)
        ps = pymunk.Poly.create_box(pb, (PLANK_L, PLANK_T), radius=2)
        ps.friction, ps.elasticity = FRICTION, 0.2
        ps.collision_type = 2
        sb = sp.static_body
        piv = pymunk.PivotJoint(pb, sb, (PIV_X, PIV_Y - PLANK_T / 2 - 10))
        lim = pymunk.RotaryLimitJoint(pb, sb, -MAX_TILT, MAX_TILT)
        spr = pymunk.DampedRotarySpring(pb, sb, 0.0, SPRING_K, SPRING_D)
        sp.add(pb, ps, piv, lim, spr)
        self.w = rng.uniform(1.6, 2.6) * rng.choice([-1, 1])
        self.ph = rng.uniform(0, 2 * math.pi)
        self.t = 0.0
        self.events = []
        self.result, self.result_t = None, None
        self.balls = {}
        self.n_id = 0
        self.next_drop = 0.3
        self.best = 0
        self.n_on = 0
        sp.on_collision(1, 2, begin=self._land)
        sp.on_collision(1, 1, begin=self._land2)

    def _land(self, arb, space, data):
        b = arb.shapes[0].body
        info = self.balls.get(b)
        if info is not None and not info["landed"]:
            info["landed"] = True
            self.events.append(("land", self.t, (info["r"], info["gold"])))

    def _land2(self, arb, space, data):
        for s in arb.shapes:   # ボールの上に落ちたときも「のった」に数える(相手がのっているボールなら)
            info = self.balls.get(s.body)
            other = self.balls.get(arb.shapes[1].body if s is arb.shapes[0] else arb.shapes[0].body)
            if info is not None and other is not None and not info["landed"] and other["landed"]:
                info["landed"] = True
                self.events.append(("land", self.t, (info["r"], info["gold"])))

    def drop(self):
        k = self.n_id
        gold = (k + 1) % GOLD_EVERY == 0
        r = GOLD_R if gold else self.rng.uniform(R_MIN, R_MAX)
        m = (r / 20.0) ** 2 * (GOLD_DENS if gold else 1.0)
        b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, r))
        b.position = (dropper_x(self.t, self.w, self.ph), DROP_Y)
        b.velocity = (0, 100)
        s = pymunk.Circle(b, r)
        s.friction, s.elasticity = FRICTION, 0.2
        s.collision_type = 1
        self.space.add(b, s)
        self.balls[b] = {"id": k, "shape": s, "r": r, "gold": gold, "col": k % 12, "landed": False}
        self.n_id += 1
        self.events.append(("drop", self.t, (b.position.x, gold)))

    def step(self, dt):
        if self.result is None and self.t >= self.next_drop:
            self.drop()
            self.next_drop += INTERVAL
        for b in self.balls:   # ころがり抵抗(やわらかいボールなので、ころがるとすぐ勢いが落ちる)
            b.angular_velocity *= ROLL_DAMP
        self.space.step(dt)
        self.t += dt

    def check(self):
        gone = [b for b in self.balls if b.position.y > H + 80]
        for b in sorted(gone, key=lambda b_: self.balls[b_]["id"]):
            self.space.remove(b, self.balls.pop(b)["shape"])
        n_on = 0
        pp, pa = self.plank.position, self.plank.angle
        for b, info in self.balls.items():
            rel = (b.position - pp).rotated(-pa)   # シーソーの板から見た位置
            on_plank = abs(rel.x) < PLANK_L / 2 + 4 and rel.y < 0
            if info["landed"] and on_plank and not info.get("fell"):
                n_on += 1
            elif info["landed"] and not on_plank and not info.get("fell"):
                info["fell"] = True
                if self.result is None:
                    self.events.append(("fall", self.t, (b.position.x, info["r"])))
        self.n_on = n_on
        self.best = max(self.best, n_on)
        if self.result is None:
            if n_on >= TARGET:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, None))
            if self.result is not None:
                self.final_n = n_on


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        g.check()
        if record:
            frames.append({"t": g.t, "n": g.n_on, "ang": g.plank.angle, "pos": tuple(g.plank.position),
                           "drop_x": dropper_x(g.t, g.w, g.ph),
                           "balls": [(b.position.x, b.position.y, b.angle, i["r"], i["gold"], i["col"])
                                     for b, i in g.balls.items()]})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "n": g.final_n, "best": g.best, "dropped": g.n_id}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), r["n"], r["best"], r["dropped"]


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


def draw_gold(ctx, x, y, r, ang, t):
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r)
    g.add_color_stop_rgb(0, 1, 1, 0.85)
    g.add_color_stop_rgb(0.4, 1, 0.8, 0.2)
    g.add_color_stop_rgb(1, 0.55, 0.35, 0.02)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    text(ctx, "重", x, y + r * 0.35, r * 0.95, rgb=(0.45, 0.25, 0.0), stroke=(1, 0.95, 0.7), sw=4)


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"seesaw_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"seesaw_{seed}.wav")
    final = os.path.join(OUT_DIR, f"seesaw_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"ss_preview_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, PIV_X, PIV_Y - 200, reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=(f"{TARGET}個!!", "COMPLETE", "バランス成功"))
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    drips = drip_layout(ctx, "失敗したら", W / 2, 1590, 78, "失敗したら・・・", seed)
    bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(bg)
    gr = cairo.LinearGradient(0, 0, 0, H)
    gr.add_color_stop_rgb(0, 0.05, 0.06, 0.15)
    gr.add_color_stop_rgb(1, 0.02, 0.02, 0.06)
    bc.set_source(gr)
    bc.paint()
    # 支点(三角の台)
    bc.move_to(PIV_X, PIV_Y - 8)
    bc.line_to(PIV_X - 70, PIV_Y + 130)
    bc.line_to(PIV_X + 70, PIV_Y + 130)
    bc.close_path()
    g_ = cairo.LinearGradient(PIV_X - 70, 0, PIV_X + 70, 0)
    g_.add_color_stop_rgb(0, 0.35, 0.38, 0.45)
    g_.add_color_stop_rgb(0.45, 0.85, 0.88, 0.95)
    g_.add_color_stop_rgb(1, 0.3, 0.32, 0.4)
    bc.set_source(g_)
    bc.fill()
    frozen = None
    ev_i = 0
    land_fx = []
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
        # 落とし口(上を左右に動く)
        dx = fr["drop_x"]
        ctx.rectangle(PIV_X - DROP_AMP - 40, DROP_Y - 64, 2 * DROP_AMP + 80, 6)
        ctx.set_source_rgba(0.8, 0.85, 0.95, 0.5)
        ctx.fill()
        ctx.move_to(dx - 36, DROP_Y - 60)
        ctx.line_to(dx + 36, DROP_Y - 60)
        ctx.line_to(dx + 16, DROP_Y - 30)
        ctx.line_to(dx - 16, DROP_Y - 30)
        ctx.close_path()
        g_ = cairo.LinearGradient(dx - 36, 0, dx + 36, 0)
        g_.add_color_stop_rgb(0, 0.45, 0.48, 0.55)
        g_.add_color_stop_rgb(0.4, 0.95, 0.97, 1.0)
        g_.add_color_stop_rgb(1, 0.35, 0.38, 0.45)
        ctx.set_source(g_)
        ctx.fill()
        # シーソーの板
        ctx.save()
        ctx.translate(*fr["pos"])
        ctx.rotate(fr["ang"])
        g_ = cairo.LinearGradient(0, -PLANK_T / 2, 0, PLANK_T / 2)
        g_.add_color_stop_rgb(0, 0.95, 0.75, 0.45)
        g_.add_color_stop_rgb(1, 0.55, 0.35, 0.15)
        ctx.rectangle(-PLANK_L / 2, -PLANK_T / 2, PLANK_L, PLANK_T)
        ctx.set_source(g_)
        ctx.fill()
        ctx.arc(0, 0, 8, 0, 2 * math.pi)
        ctx.set_source_rgb(0.3, 0.3, 0.35)
        ctx.fill()
        ctx.restore()
        cyc = int(win_b * 30) if win_b >= 0 else 0
        for x, y, a, r, gold, c in fr["balls"]:
            if gold:
                draw_gold(ctx, x, y, r, a, t)
            else:
                draw_ball(ctx, x, y, r, PALETTE[(c + cyc) % 12])
        # 文字
        text(ctx, "シーソーにボールをのせる", W / 2, 235, 60, sw=12)
        text(ctx, f"{TARGET}個のせられる？", W / 2, 335, 96, rgb=GOLD, sw=16)
        n = fr["n"] if not over else res["n"]
        text(ctx, f"{n} / {TARGET} 個", W / 2, 445, 70, rgb=(1, 1, 1), sw=10)
        left = max(0.0, TIME_LIMIT - (min(t, end_t) if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 522, 40, rgb=(1, 0.4, 0.4) if left < 10 else (0.95, 0.95, 0.95), sw=8)
        if not over:
            scary_text(ctx, "失敗したら・・・", W / 2, 1590, 78, t, drips)
        if over and fail:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 880, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            text(ctx, "時間切れ…", W / 2, 990, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"いちばん多いときで {res['best']}個だった…", W / 2, 1110, 60, sw=12)
        if win_b >= 0:
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


def thud(r, gold):
    """のったときの「トン」(大きいほど低い。金は「ドスン」)。"""
    t = _t(0.3 if gold else 0.15)
    f = 900 * (14 / r) if not gold else 90
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * (12 if gold else 35))
    if gold:
        y += 0.6 * np.random.default_rng(1).normal(0, 1, len(t)) * np.exp(-t * 30)
    return (0.9 if gold else 0.5) * y


def fall_snd():
    """こぼれ落ちる「ヒューン」。"""
    t = _t(0.4)
    f = 900 - 1500 * t
    return 0.3 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5)


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
    rf = []
    for kind, t, data in events:
        if t > end_t + 0.01:
            continue
        if kind == "land":
            add(thud(data[0], data[1]), t)
        elif kind == "fall":
            rf = [x for x in rf if t - x < 0.15]
            if len(rf) >= 2:
                continue
            rf.append(t)
            add(fall_snd(), t)
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
