"""成功したときの「虹色パチンコ演出」(映像と音)。キュインキュイン!と虹色に光って、脳汁が出るような大当たり演出。

すべてプログラムで描いた・作ったオリジナル(実在の台の絵・音・ロゴは使っていない)。

    fever = RainbowFever(W, H, seed)
    fever.draw_back(ctx, age)    # ボールより下に描く:虹色の放射の光・画面のフラッシュ
    fever.draw_front(ctx, age, text_fn, main, sub)   # ボールより上に描く:虹色の文字・キラキラ・虹の枠
    sig = kyuin_music(sr, DURATION)   # キュインキュイン+ファンファーレ+鐘の連打
"""
import math

import cairo
import numpy as np

DURATION = 8.5


def hsv(h, s=1.0, v=1.0):
    h = h % 1.0
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p, q, t_ = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    return [(v, t_, p), (q, v, p), (p, v, t_), (p, q, v), (t_, p, v), (v, p, q)][i]


class RainbowFever:
    def __init__(self, w, h, seed=0):
        self.w, self.h = w, h
        rng = np.random.default_rng(seed + 77)
        self.sparks = [(rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0, 1), rng.uniform(0.6, 1.6), rng.uniform(6, 16))
                       for _ in range(90)]

    def draw_back(self, ctx, age):
        w, h = self.w, self.h
        cx, cy = w / 2, h * 0.5
        # はじめの0.6秒は、虹色のフラッシュが何度も光る(キュインキュインに合わせて)
        if age < 3.0:
            beat = (age * 4) % 1.0
            a = (1 - beat) ** 2 * (0.75 if age < 0.6 else 0.35)
            ctx.set_source_rgba(*hsv(age * 2.3), a)
            ctx.paint()
        # 回る虹色の放射の光
        n = 24
        rot = age * 1.4
        big = math.hypot(w, h)
        for k in range(n):
            a0 = rot + 2 * math.pi * k / n
            ctx.move_to(cx, cy)
            ctx.arc(cx, cy, big, a0, a0 + math.pi / n)
            ctx.close_path()
            ctx.set_source_rgba(*hsv(k / n + age * 0.5), 0.33)
            ctx.fill()

    def draw_front(self, ctx, age, text_fn, main, sub):
        w, h = self.w, self.h
        # 画面のふちに虹色の光る枠(ぐるぐる色が流れる)
        for k in range(36):
            col = hsv(k / 36 - age * 1.2)
            ctx.set_source_rgba(*col, 0.95)
            ctx.set_line_width(26)
            seg = (2 * (w + h)) / 36
            s0 = k * seg
            pts = []
            for s_ in (s0, s0 + seg):
                s_ %= 2 * (w + h)
                if s_ < w:
                    pts.append((s_, 13))
                elif s_ < w + h:
                    pts.append((w - 13, s_ - w))
                elif s_ < 2 * w + h:
                    pts.append((w - (s_ - w - h), h - 13))
                else:
                    pts.append((13, h - (s_ - 2 * w - h)))
            ctx.move_to(*pts[0])
            ctx.line_to(*pts[1])
            ctx.stroke()
        # キラキラ(虹色の星)
        for x, y, ph, sp, sz in self.sparks:
            tw = abs(math.sin((age * sp + ph) * math.pi * 2))
            s = sz * (0.4 + 0.8 * tw)
            ctx.save()
            ctx.translate(x, (y - age * 60 * sp) % h)
            ctx.set_source_rgba(*hsv(ph + age), 0.5 + 0.5 * tw)
            ctx.move_to(0, -s)
            for i in range(4):
                a = math.pi / 2 * (i + 0.5)
                ctx.line_to(0.28 * s * math.cos(a), -0.28 * s * math.sin(a))
                ctx.line_to(s * math.cos(a + math.pi / 4), -s * math.sin(a + math.pi / 4))
            ctx.close_path()
            ctx.fill()
            ctx.restore()
        # 虹色に色が変わり続ける大きな文字(ドンッと出てから、ドクドク脈打つ)
        k = min(1.0, age / 0.18)
        pulse = 1 + 0.07 * math.sin(age * 2 * math.pi * 2)
        size = 150 * (2.2 - 1.2 * k) * pulse
        text_fn(ctx, main, w / 2, h * 0.36, size, rgb=hsv(age * 1.7), sw=22)
        if age > 0.35:
            text_fn(ctx, sub, w / 2, h * 0.36 + 150, 100 * pulse, rgb=hsv(age * 1.7 + 0.5), sw=16)


# ---------------------------------------------------------------- 音
def _kyuin(sr, amp=1.0):
    """「キュイン」:低いところから一気に高く上がるうなり音(ビブラートつき)。"""
    d = 0.32
    t = np.arange(int(d * sr)) / sr
    f = 500 + 2800 * (1 - np.exp(-t / 0.07))
    f = f * (1 + 0.03 * np.sin(2 * np.pi * 32 * t))
    ph = 2 * np.pi * np.cumsum(f) / sr
    y = np.sin(ph) + 0.4 * np.sign(np.sin(ph)) * 0.5 + 0.3 * np.sin(2 * ph)
    env = np.minimum(1, t / 0.01) * np.exp(-np.maximum(0, t - 0.18) / 0.06)
    return amp * y * env


def _note(f, d, sr, amp, kind="square"):
    t = np.arange(int(d * sr)) / sr
    if kind == "square":
        y = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + 0.5 * np.sin(2 * np.pi * f * t)
    else:
        y = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t * 8)
    env = np.minimum(1, t / 0.005) * np.exp(-t * (2.5 if kind == "square" else 4))
    return amp * y * env


def kyuin_music(sr, dur=DURATION):
    n = int(dur * sr)
    out = np.zeros(n)

    def add(sig, t0, g=1.0):
        i = int(t0 * sr)
        j = min(n, i + len(sig))
        if j > i:
            out[i:j] += g * sig[: j - i]
    hz = lambda m: 440.0 * 2 ** ((m - 69) / 12)   # noqa: E731
    # キュイン!キュイン!(はじめの3秒、どんどん連打)
    t = 0.0
    while t < 3.0:
        add(_kyuin(sr), t, 0.7)
        t += 0.25
    # ファンファーレ(ドミソド↑ → 大きな和音)
    seq = [(72, 0.0), (76, 0.12), (79, 0.24), (84, 0.36)]
    for m, t0 in seq:
        add(_note(hz(m), 0.3, sr, 0.35), 0.1 + t0)
    for m in (72, 76, 79, 84, 88):
        add(_note(hz(m), 2.2, sr, 0.22), 0.55)
    # ジャラジャラ…と鳴り続ける高い鐘(玉が出てくるイメージ)
    rng = np.random.default_rng(5)
    t = 0.6
    while t < dur - 0.3:
        add(_note(hz(rng.choice([84, 88, 91, 96, 100])), 0.25, sr, 0.12, "bell"), t)
        t += rng.uniform(0.04, 0.09)
    # 3秒すぎに、もう一度ファンファーレ
    for i, m in enumerate([79, 84, 88, 91]):
        add(_note(hz(m), 0.3, sr, 0.3), 3.2 + 0.12 * i)
    for m in (79, 84, 88, 91):
        add(_note(hz(m), 3.0, sr, 0.2), 3.7)
    out *= np.minimum(1, (dur - np.arange(n) / sr) / 0.8)
    return out / (np.abs(out).max() + 1e-9) * 0.9
