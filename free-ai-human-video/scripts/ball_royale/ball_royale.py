"""「ピンクが勝てば成功!」丸いわくの中で、色ちがいのボール8個のバトルロイヤル。
ぶつかると大きいほうが小さいほうの一部を吸収して大きくなり、小さくなりすぎたボールは消えて脱落。最後に残った1個が勝ち。

- 重力なし。ボールはいつも同じ速さで、わく・ほかのボールで跳ね返る(ねらい・補正なし)。
- ぶつかった瞬間、大きいほうが小さいほうの面積の ABSORB(割合)をうばう。同じくらいの大きさ(半径の差が TIE 未満)なら、はね返るだけ。
- 小さいほうの半径が R_DEAD より小さくなったら、残りも全部吸収されて脱落。
- ピンクが最後に残れば成功(パチンコの当たり風の演出)、ほかの色が勝てば失敗(幽霊)。

使い方:
    python ball_royale.py search [-n 200]
    python ball_royale.py render --seed N
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
from pachinko import kyuin_music  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "glass_spiral"))
import jackpot_end as JP  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

CX, CY, R = 540.0, 1010.0, 420.0
SPEED = float(os.environ.get("SPEED", 400.0))
R_START = 38.0
ABSORB = float(os.environ.get("ABSORB", 0.3))
TIE = 1.0
R_DEAD = 12.0
MAX_T = 120.0
OUTRO = 4.2
WIN_DUR = JP.DURATION - JP.T_BIG

TEAMS = [("ピンク", (1.0, 0.35, 0.7)), ("レッド", (1.0, 0.2, 0.2)), ("オレンジ", (1.0, 0.6, 0.15)),
         ("イエロー", (1.0, 0.9, 0.2)), ("グリーン", (0.3, 0.9, 0.35)), ("シアン", (0.2, 0.85, 0.95)),
         ("ブルー", (0.25, 0.45, 1.0)), ("パープル", (0.65, 0.35, 1.0))]
HERO = 0   # ピンク


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, 0)
        sp.iterations = 15
        self.space = sp
        n = 120
        pts = [(CX + (R + 10) * math.cos(2 * math.pi * k / n), CY + (R + 10) * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
        for a, b in zip(pts, pts[1:]):
            s = pymunk.Segment(sp.static_body, a, b, 10)
            s.elasticity, s.friction = 1.0, 0.0
            s.collision_type = 2
            sp.add(s)
        self.balls = {}
        order = rng.permutation(len(TEAMS))   # スタートの位置はランダム(円の上に等間隔)
        a0 = rng.uniform(0, 2 * math.pi)
        for slot, k in enumerate(order):
            a = a0 + 2 * math.pi * slot / len(TEAMS)
            pos = (CX + 0.6 * R * math.cos(a), CY + 0.6 * R * math.sin(a))
            va = rng.uniform(0, 2 * math.pi)
            self.add(int(k), pos, (SPEED * math.cos(va), SPEED * math.sin(va)), R_START + rng.uniform(-6, 6))   # 少しだけ体格差
        self.t = 0.0
        self.events = []
        self.pairs = []
        self.result, self.result_t, self.winner = None, None, None
        self.out_order = []
        sp.on_collision(1, 1, begin=self._touch)
        sp.on_collision(1, 2, begin=self._wall)

    def add(self, k, pos, vel, r):
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, r))
        b.position, b.velocity = pos, vel
        s = pymunk.Circle(b, r)
        s.elasticity, s.friction = 1.0, 0.0
        s.collision_type = 1
        self.space.add(b, s)
        self.balls[k] = {"body": b, "shape": s, "r": r}

    def _touch(self, arb, space, data):
        a, b = arb.shapes
        self.pairs.append((a, b))
        return True

    def _wall(self, arb, space, data):
        self.events.append(("wall", self.t, None))
        return True

    def key_of(self, shape):
        for k, v in self.balls.items():
            if v["shape"] is shape:
                return k
        return None

    def set_r(self, k, r):
        v = self.balls[k]
        v["r"] = r
        v["shape"].unsafe_set_radius(r)
        m = (r / R_START) ** 2
        v["body"].mass = m
        v["body"].moment = pymunk.moment_for_circle(m, 0, r)

    def step(self, dt):
        self.space.step(dt)
        self.t += dt
        for a, b in self.pairs:
            ka, kb = self.key_of(a), self.key_of(b)
            if ka is None or kb is None or self.result is not None:
                continue
            ra, rb = self.balls[ka]["r"], self.balls[kb]["r"]
            if abs(ra - rb) < TIE:
                self.events.append(("bump", self.t, (ka, kb)))
                continue
            big, small = (ka, kb) if ra > rb else (kb, ka)
            a_big, a_small = math.pi * self.balls[big]["r"] ** 2, math.pi * self.balls[small]["r"] ** 2
            take = ABSORB * a_small
            new_small = math.sqrt(max(0.0, a_small - take) / math.pi)
            if new_small < R_DEAD:   # 小さくなりすぎ:残りも全部吸収されて脱落
                take = a_small
                self.set_r(big, math.sqrt((a_big + take) / math.pi))
                v = self.balls.pop(small)
                self.space.remove(v["body"], v["shape"])
                self.out_order.append(small)
                self.events.append(("out", self.t, (small, big, v["body"].position.x, v["body"].position.y, len(self.balls))))
            else:
                self.set_r(small, new_small)
                self.set_r(big, math.sqrt((a_big + take) / math.pi))
                self.events.append(("eat", self.t, (big, small)))
        self.pairs = []
        for v in self.balls.values():   # いつも同じ速さ
            b = v["body"]
            vel = b.velocity
            n = vel.length
            if n > 1e-6:
                b.velocity = vel * (SPEED / n)
            d = b.position - (CX, CY)
            if d.length > R - v["r"]:
                b.position = pymunk.Vec2d(CX, CY) + d.normalized() * (R - v["r"] - 1)
        if self.result is None and (len(self.balls) == 1 or self.t > MAX_T):
            self.winner = max(self.balls, key=lambda k: self.balls[k]["r"])
            self.result = "success" if self.winner == HERO else "fail"
            self.result_t = self.t
            self.events.append((self.result, self.t, self.winner))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "balls": [(k, v["body"].position.x, v["body"].position.y, v["r"]) for k, v in g.balls.items()]})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR + 1.0) if g.result == "fail" else WIN_DUR + 0.5
            if not record or g.t > g.result_t + extra:
                break
    alive = sorted(g.balls, key=lambda k: -g.balls[k]["r"])   # 時間切れで何個か残ったときは大きい順
    rank = alive + g.out_order[::-1]
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "winner": g.winner, "rank": rank}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), TEAMS[r["winner"]][0], r["rank"].index(HERO) + 1


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 ピンクの勝ち {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def draw_ball(ctx, x, y, r, col, glow=0.0):
    if glow > 0:
        g = cairo.RadialGradient(x, y, r * 0.8, x, y, r * 1.7)
        g.add_color_stop_rgba(0, *col, 0.5 * glow)
        g.add_color_stop_rgba(1, *col, 0)
        ctx.arc(x, y, r * 1.7, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r)
    g.add_color_stop_rgb(0, *(min(1, c + 0.5) for c in col))
    g.add_color_stop_rgb(0.5, *col)
    g.add_color_stop_rgb(1, *(c * 0.55 for c in col))
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.85)
    ctx.set_line_width(max(2, r * 0.05))
    ctx.stroke()


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    draw_ball(ctx, x, y, r * 0.8, TEAMS[HERO][1], 1.0)


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"ball_royale_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"ball_royale_{seed}.wav")
    final = os.path.join(OUT_DIR, f"ball_royale_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"br_preview_{pt:.1f}.png"))
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
                                          texts=("ピンク優勝!!", "WINNER", "8色の頂点"))
    winner = res["winner"]
    g0 = end_t + 1.0   # 決着してから1秒、勝ったボールを見せる
    outs = []
    labels = []
    alive = set(range(len(TEAMS)))
    bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(bg)
    gr = cairo.RadialGradient(CX, CY, 50, CX, CY, 1100)
    gr.add_color_stop_rgb(0, 0.1, 0.08, 0.18)
    gr.add_color_stop_rgb(1, 0.02, 0.02, 0.05)
    bc.set_source(gr)
    bc.paint()
    bc.arc(CX, CY, R, 0, 2 * math.pi)
    bc.set_source_rgba(0, 0, 0, 0.35)
    bc.fill()
    frozen = None
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "out":
                small, big, x, y, n = data
                alive.discard(small)
                outs.append((x, y, small, et))
                labels.append((f"{TEAMS[small][0]} 脱落!", TEAMS[small][1], et))
            ev_i += 1
        if ending is not None and t >= g0:
            ending.draw(surf, ctx, t - g0 + JP.T_BIG)
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
        for wd, al in ((14, 0.15), (5, 1.0)):
            ctx.arc(CX, CY, R + 4, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, al)
            ctx.set_line_width(wd)
            ctx.stroke()
        keep = []
        for x, y, k, t0 in outs:   # 脱落したときにはじける光
            a_ = t - t0
            if a_ < 0.5:
                ctx.arc(x, y, 20 + 160 * a_, 0, 2 * math.pi)
                ctx.set_source_rgba(*TEAMS[k][1], 0.8 * (1 - a_ / 0.5))
                ctx.set_line_width(6)
                ctx.stroke()
                keep.append((x, y, k, t0))
        outs = keep
        for k, x, y, r in sorted(fr["balls"], key=lambda b: b[3]):
            draw_ball(ctx, x, y, r, TEAMS[k][1], 1.0 if (k == HERO) else 0.4)
            if r > 26:
                text(ctx, TEAMS[k][0], x, y + r * 0.18, max(18, min(44, r * 0.45)), rgb=(1, 1, 1), sw=5)
        # 上の文字
        text(ctx, "8色バトルロイヤル", W / 2, 235, 64, sw=12)
        text(ctx, "ピンクが勝てば成功！", W / 2, 335, 88, rgb=TEAMS[HERO][1], sw=16)
        text(ctx, f"残り {len(fr['balls'])} 個", W / 2, 440, 60, rgb=(1, 1, 1), sw=10)
        # 生き残りの一覧(大きい順)
        order = sorted(fr["balls"], key=lambda b: -b[3])
        n_ = len(order)
        for i, (k, x, y, r) in enumerate(order):
            xx = W / 2 + (i - (n_ - 1) / 2) * 110
            draw_ball(ctx, xx, 525, 16 + 0.25 * min(60, r - 20), TEAMS[k][1])
        labels = [l_ for l_ in labels if t - l_[2] < 1.2]
        if labels and t < end_t:
            s_, col, t0 = labels[-1]
            k2 = min(1.0, (t - t0) / 0.12)
            text(ctx, s_, W / 2, 1515, 64 * (1.3 - 0.3 * k2), rgb=col, sw=12)
        elif t < end_t:
            text(ctx, "失敗したら・・・", W / 2, 1515, 54, rgb=(1, 0.45, 0.45), sw=10)
        if t >= end_t and t < g0:
            text(ctx, f"{TEAMS[winner][0]}の勝ち!!", W / 2, 1515, 80, rgb=TEAMS[winner][1], sw=14)
        if fail and t >= g0:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 880, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            text(ctx, f"{TEAMS[winner][0]}の勝ち…", W / 2, 990, 120 * (1.3 - 0.3 * k), rgb=TEAMS[winner][1], sw=20)
            text(ctx, f"ピンクは {res['rank'].index(HERO) + 1}位だった…", W / 2, 1110, 66, sw=12)
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
    print(f"完成: {os.path.abspath(final)}  ({'成功' if not fail else '失敗'} 勝ち:{TEAMS[winner][0]} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def pon(f, amp):
    t = _t(0.25)
    return amp * (np.sin(2 * np.pi * f * t) * np.exp(-t * 14) + 0.3 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 25))


def slurp(f, amp):
    """吸いとる「チュルッ」(上がる音)。"""
    t = _t(0.15)
    ff_ = f * (1 + 1.2 * t / 0.15)
    return amp * np.sin(2 * np.pi * np.cumsum(ff_) / SR) * np.sin(np.pi * t / 0.15)


def pop_out(amp, seed):
    """脱落の「パンッ!」+ 下がっていく音。"""
    t = _t(0.6)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    f = 700 * np.exp(-t * 4) + 120
    return amp * (0.8 * n * np.exp(-t * 40) + 0.6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4))


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
    last = -1.0
    lastw = -1.0
    for kind, t, data in events:
        if t > end_t + 0.01:
            continue
        if kind == "eat" and t - last > 0.03:
            big, small = data
            add(pon(midi_hz(64 + (big * 2) % 12), 0.4), t)
            add(slurp(600 + 60 * big, 0.3), t + 0.02)
            last = t
        elif kind == "bump" and t - last > 0.03:
            add(pon(midi_hz(72), 0.3), t)
            last = t
        elif kind == "wall" and t - lastw > 0.08:
            add(pon(midi_hz(55), 0.12), t)
            lastw = t
        elif kind == "out":
            add(pop_out(0.8, int(t * 100)), t)
    g0 = end_t + 1.0
    t_ = _t(1.2)   # 決着の「ジャーン」
    chord = sum(np.sin(2 * np.pi * midi_hz(60 + m) * t_) for m in (0, 4, 7, 12)) * np.exp(-t_ * 2)
    add(0.4 * chord, end_t)
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
        i0 = int(g0 * SR)
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
    ap.add_argument("-n", type=int, default=200)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
