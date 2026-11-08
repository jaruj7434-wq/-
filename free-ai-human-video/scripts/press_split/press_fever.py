"""全部切れたときの「ボールフィーバー」演出(映像と音)。リールの演出はなし。

  0.0秒 … 白く2回ピカッ+「ドカン!」、画面がゆれる
  すぐに  うずまきの中心から星が噴水のように噴き出して画面いっぱいにあふれ、下から山のように積み上がっていく
          (丸ごとの星と、切れた半分の星が混ざる。果汁のしぶきも虹色に光る)
  背景   … 虹色の光の筋が高速回転、虹色ストロボ、ふちの電飾が虹色に流れる、虹色のキラキラ
  文字   … 虹色にギラギラ光る「全部切った!!」がドンと出て脈打つ、金色の「ALL CLEAR」「160 / 160」
  音     … 「ドカン!」→「キュインキュイン!」連発 → ファンファーレ風の連打、星が飛び出す「ポンポンポン」、
            チャリンチャリン、小節ごとのキュイン、最後に「ジャーン」
映像も音もすべてこのファイル(と jackpot_end の部品)の中で作る。
"""
import math

import cairo
import numpy as np

import ballskin as FR
from jackpot_end import Jackpot, _rainbow, _kyuin, _sq, _bell, _boom, _lp

DURATION = 8.5


class FruitFever(Jackpot):
    def __init__(self, W, H, seed, cx, cy, main="全部切った!!", count="160 / 160"):
        super().__init__(W, H, seed, cx, cy, None, main=main, count=count)
        rng = np.random.default_rng(seed + 4321)
        # 噴き出す星: 出る時刻, 横の速さ, 上向きの速さ, 種類, 大きさ, 回転の速さ, 半分か(切れ目の角度)
        self.spray = []
        t = 0.05
        while t < DURATION - 1.2:
            rate = 70 if t < 3.5 else 45
            self.spray.append((t, rng.normal(0, 520), rng.uniform(1300, 2500), int(rng.integers(0, len(FR.KINDS))),
                               rng.uniform(26, 58), rng.normal(0, 5), rng.uniform(0, math.pi) if rng.random() < 0.45 else None))
            t += 1 / rate
        # 下に積み上がる山(行ごとに星を並べておき、時間とともに高くなる)
        self.pile = [(rng.uniform(-30, W + 30), rng.uniform(0, 1), int(rng.integers(0, len(FR.KINDS))),
                      rng.uniform(34, 62), rng.uniform(-0.6, 0.6)) for _ in range(260)]
        self.pile.sort(key=lambda p: p[1])

    def _fruit(self, ctx, kind, x, y, r, rot, half):
        if half is None:
            FR.draw_fruit(ctx, kind, x, y, r, rot)
            return
        # 輪切り:断面がくるくる回りながら降ってくる
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(rot * 0.3 + half)
        ctx.scale(max(0.15, abs(math.cos(rot + half))), 1.0)
        FR.draw_cut(ctx, kind, r * 0.85)
        ctx.restore()

    def draw(self, surf, ctx, age):
        W, H, cx, cy = self.W, self.H, self.cx, self.cy
        shake = 22 * math.exp(-age * 3) * math.sin(age * 80)
        # 背景(暗い紫)+虹の光の筋
        bg = cairo.RadialGradient(cx, cy, 0, cx, cy, 1300)
        bg.add_color_stop_rgb(0, 0.3, 0.05, 0.3)
        bg.add_color_stop_rgb(1, 0.03, 0.0, 0.06)
        ctx.set_source(bg)
        ctx.paint()
        ctx.save()
        ctx.translate(shake, -shake * 0.6)
        self._rays(ctx, age, 4.5, min(1.0, age / 0.2))
        pulse = 0.7 + 0.3 * math.sin(age * 16)
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, 560)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.95 * pulse)
        g.add_color_stop_rgba(0.35, *_rainbow(age), 0.55)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g)
        ctx.arc(cx, cy, 560, 0, 2 * math.pi)
        ctx.fill()
        # 噴き出す星(重力で落ちて画面の下へ)
        for t0, vx, vy, kind, r, spin, half in self.spray:
            a = age - t0
            if a < 0:
                break
            x = cx + vx * a
            y = cy - vy * a + 0.5 * 2600 * a * a
            if y > H + 80 or a > 3.0:
                continue
            self._fruit(ctx, kind, x, y, r * min(1.0, 0.3 + a * 4), spin * a, half)
            if a < 0.25:   # 飛び出した瞬間の虹色のしぶき
                ctx.set_source_rgba(*_rainbow(t0 * 3), 0.6 * (1 - a / 0.25))
                ctx.arc(x, y, r * (1.2 + a * 4), 0, 2 * math.pi)
                ctx.fill()
        # 下から積み上がる星の山
        level = min(1.0, max(0.0, (age - 0.6) / 5.5))
        top = H - 80 - 560 * level ** 0.8
        for x, v, kind, r, rot in self.pile:
            y = H + 40 - (H + 40 - top) * v
            if y < top or level <= 0:
                continue
            self._fruit(ctx, kind, x, y + 12 * math.sin(age * 6 + x), r, rot, None)
        ctx.restore()
        # 虹色のキラキラ
        for ang, v, sz, hue in self.burst:
            b = (age * 1.3 + hue) % 1.5
            d = v * b * (1 - 0.3 * b)
            x, y = cx + d * math.cos(ang + age), cy + d * math.sin(ang + age)
            self._star(ctx, x, y, sz, b * 5)
            ctx.set_source_rgba(*_rainbow(hue + age), max(0.0, 1 - b / 1.5))
            ctx.fill()
        # 文字
        land = min(1.0, age / 0.2)
        sc = (2.6 - 1.6 * land) * (1 + 0.05 * math.sin(age * 12))
        ctx.save()
        ctx.translate(W / 2 + shake, H * 0.30)
        ctx.scale(sc, sc)
        self._text(ctx, self.main, 0, 55, 140, age)
        ctx.restore()
        if age > 0.4:
            k = min(1.0, (age - 0.4) / 0.15)
            ctx.save()
            ctx.translate(W / 2, H * 0.40)
            ctx.scale(k * (1 + 0.05 * math.sin(age * 10)), k)
            self._text(ctx, "ALL CLEAR", 0, 35, 100, age + 0.5, gold=True)
            ctx.restore()
        if age > 0.65:
            k = min(1.0, (age - 0.65) / 0.15)
            ctx.save()
            ctx.translate(W / 2, H * 0.48)
            ctx.scale(k, k)
            self._text(ctx, self.count, 0, 30, 84, age + 0.2)
            ctx.restore()
        self._bulbs(ctx, age, 1.0)
        # フラッシュと虹ストロボ
        for t0 in (0.0, 0.25):
            a = age - t0
            if 0 <= a < 0.18:
                ctx.set_source_rgba(1, 1, 1, 0.9 * (1 - a / 0.18))
                ctx.paint()
        if int(age * 24) % 2 == 0 and int(age * 2.5) % 3 == 0:
            ctx.set_source_rgba(*_rainbow(age * 3), 0.2)
            ctx.paint()
        if age > DURATION - 0.6:
            ctx.set_source_rgba(0, 0, 0, (age - (DURATION - 0.6)) / 0.6)
            ctx.paint()


def _pop(sr, rng, f):
    """星が飛び出す「ポン」+ みずみずしい「ピチャ」。"""
    t = np.arange(int(0.12 * sr)) / sr
    s = np.sin(2 * np.pi * np.cumsum(f * (1 + 1.2 * np.exp(-t * 60))) / sr) * np.exp(-t * 40)
    n = rng.normal(0, 1, len(t))
    s += 0.4 * (n - _lp(n, 5)) * np.exp(-t * 60)
    return s


def music(sr, seed=0):
    rng = np.random.default_rng(seed + 55)
    n = int(DURATION * sr)
    out = np.zeros((n, 2))

    def put(sig, t0, pan=0.0):
        i = int(t0 * sr)
        if i >= n or len(sig) == 0:
            return
        j = min(n, i + len(sig))
        out[i:j, 0] += sig[: j - i] * math.sqrt(0.5 * (1 - pan))
        out[i:j, 1] += sig[: j - i] * math.sqrt(0.5 * (1 + pan))

    put(_boom(sr, rng, 0.75, 1.8, 38), 0.0)          # ドカン!
    for j in range(4):                               # キュインキュイン!連発
        put(0.3 * _kyuin(sr, 1 + 0.07 * j), 0.05 + j * 0.2, pan=(-0.5, 0.5, -0.3, 0.3)[j])
    bpm = 165   # ファンファーレ風の連打
    s16 = 60 / bpm / 4
    prog = [(60, 64, 67, 72), (65, 69, 72, 77), (67, 71, 74, 79), (72, 76, 79, 84)]
    t = 0.85
    i = 0
    while t < DURATION - 1.3:
        ch = prog[int((t - 0.85) / (8 * s16)) % len(prog)]
        m = ch[i % 4] + 12 * ((i // 4) % 2)
        put(_sq(m, 0.22, sr, 0.09), t, pan=0.35 * math.sin(i * 1.3))
        if i % 4 == 0:
            put(_sq(ch[0] - 24, 0.35, sr, 0.11, 4), t)
            c = np.arange(int(0.15 * sr)) / sr
            put(0.38 * np.sin(2 * np.pi * np.cumsum(50 + 100 * np.exp(-c * 30)) / sr) * np.exp(-c * 14), t)
        if i % 8 == 4:
            c = np.arange(int(0.15 * sr)) / sr
            nn = rng.normal(0, 1, len(c))
            put(0.2 * (nn - _lp(nn, 4)) * np.exp(-c * 25), t)
        if i % 16 == 0:
            put(0.22 * _kyuin(sr, 1.0 + 0.1 * ((i // 16) % 3)), t, pan=0.4 * (-1) ** (i // 16))
        t += s16
        i += 1
    for _ in range(150):   # 星が飛び出す「ポンポン」
        tt = rng.uniform(0.05, DURATION - 1.3)
        put(0.1 * _pop(sr, rng, rng.uniform(300, 900)), tt, pan=rng.uniform(-0.8, 0.8))
    for _ in range(110):   # チャリンチャリン
        put(_bell(rng.uniform(2600, 5600), sr, 0.045), rng.uniform(0.3, DURATION - 0.7), pan=rng.uniform(-0.9, 0.9))
    for m in (72, 76, 79, 84, 88, 91):   # 最後にジャーン
        put(_sq(m, 1.3, sr, 0.055, 1.8), DURATION - 1.3)
    put(_boom(sr, rng, 0.45, 1.3, 50), DURATION - 1.3)
    wet = out.copy()
    for d, g in ((0.031, 0.25), (0.057, 0.18), (0.089, 0.12)):
        k = int(d * sr)
        wet[k:, 0] += out[:-k, 1] * g
        wet[k:, 1] += out[:-k, 0] * g
    fade = np.ones(n)
    k = int(0.6 * sr)
    fade[-k:] = np.linspace(1, 0, k)
    return wet * fade[:, None]
