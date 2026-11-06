"""成功したときの「大当たり」風の終わり方(映像と音)。

映像: 白いフラッシュ → 虹色の光の筋がぐるぐる回り、画面のふちが虹色に点滅、
      虹色のキラキラが中心からはじけ飛ぶ → 虹色にギラギラ光る「全部割った!!」が弾むように出る。
音:   「キュインキュイン!」と上がる電子音を何度も鳴らし、そのあと明るいファンファーレ風のアルペジオと
      チャリンチャリンというきらめき音を重ねる。すべてこのファイルの中で合成する(既存の曲や効果音は使わない)。
"""
import colorsys
import math

import cairo
import numpy as np

DURATION = 7.0
FONT = "IPAGothic"


def _rainbow(h, s=1.0, v=1.0):
    return colorsys.hsv_to_rgb(h % 1.0, s, v)


# ---------------------------------------------------------------- 映像
class Jackpot:
    def __init__(self, W, H, seed, cx, cy):
        rng = np.random.default_rng(seed + 8080)
        self.W, self.H, self.cx, self.cy = W, H, cx, cy
        # 中心からはじけ飛ぶキラキラ: 角度, 速さ, 大きさ, 色, 出る時刻, 回転
        self.sparks = [(rng.uniform(0, 2 * math.pi), rng.uniform(300, 1300), rng.uniform(6, 18),
                        rng.uniform(0, 1), rng.uniform(0.0, 4.5), rng.uniform(-6, 6)) for _ in range(260)]
        # 画面じゅうでまたたく星
        self.twinkle = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(5, 16), rng.uniform(0, 1),
                         rng.uniform(0, 6.28), rng.uniform(5, 11)) for _ in range(90)]

    @staticmethod
    def _star(ctx, x, y, r, rot):
        ctx.new_path()
        for i in range(8):
            a = rot + i * math.pi / 4
            rr = r if i % 2 == 0 else r * 0.28
            ctx.line_to(x + rr * math.cos(a), y + rr * math.sin(a))
        ctx.close_path()

    def _text(self, ctx, s, y, size, age):
        """虹色にギラギラ光る文字(太い白ふち+黒ふち、虹のグラデーションが流れる)。"""
        ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(size)
        ext = ctx.text_extents(s)
        x = self.W / 2 - ext.width / 2 - ext.x_bearing
        ctx.new_path()
        ctx.move_to(x, y)
        ctx.text_path(s)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(size * 0.32)
        ctx.stroke_preserve()
        ctx.set_source_rgb(1, 1, 1)
        ctx.set_line_width(size * 0.16)
        ctx.stroke_preserve()
        g = cairo.LinearGradient(x, y - size, x + ext.width, y)
        for i in range(8):
            g.add_color_stop_rgb(i / 7, *_rainbow(i / 7 - age * 0.9))
        ctx.set_source(g)
        ctx.fill_preserve()
        # 光の筋が文字の上を走る
        p = (age * 1.4) % 1.6 - 0.3
        sx = x + ext.width * p
        g2 = cairo.LinearGradient(sx - 90, y - size, sx + 90, y)
        g2.add_color_stop_rgba(0, 1, 1, 1, 0)
        g2.add_color_stop_rgba(0.5, 1, 1, 1, 0.85)
        g2.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g2)
        ctx.fill()

    def draw(self, ctx, age):
        W, H, cx, cy = self.W, self.H, self.cx, self.cy
        # 1) 背景を暗くして、虹色の光の筋をぐるぐる回す
        dk = min(1.0, age / 0.25)
        ctx.rectangle(0, 0, W, H)
        ctx.set_source_rgba(0, 0, 0, 0.6 * dk)
        ctx.fill()
        n = 24
        rot = age * 1.6
        for i in range(n):
            a0 = rot + i * 2 * math.pi / n
            col = _rainbow(i / n + age * 0.5)
            ctx.new_path()
            ctx.move_to(cx, cy)
            ctx.arc(cx, cy, 1600, a0, a0 + math.pi / n)
            ctx.close_path()
            g = cairo.RadialGradient(cx, cy, 0, cx, cy, 1300)
            g.add_color_stop_rgba(0, *col, 0.55 * dk)
            g.add_color_stop_rgba(1, *col, 0.05 * dk)
            ctx.set_source(g)
            ctx.fill()
        # 中心の強い光(脈打つ)
        pulse = 0.75 + 0.25 * math.sin(age * 14)
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, 420)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.9 * pulse * dk)
        g.add_color_stop_rgba(0.4, *_rainbow(age * 0.8), 0.45 * dk)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g)
        ctx.arc(cx, cy, 420, 0, 2 * math.pi)
        ctx.fill()
        # 2) 中心からはじけ飛ぶ虹色のキラキラ
        for ang, v, sz, hue, t0, spin in self.sparks:
            a = age - t0
            if a <= 0 or a > 1.6:
                continue
            d = v * a * (1 - 0.25 * a)
            x, y = cx + d * math.cos(ang), cy + d * math.sin(ang)
            al = 1 - a / 1.6
            tw = 0.6 + 0.4 * math.sin(age * 30 + hue * 20)
            self._star(ctx, x, y, sz * (0.7 + 0.5 * tw), spin * a)
            ctx.set_source_rgba(*_rainbow(hue + age), al)
            ctx.fill_preserve()
            ctx.set_source_rgba(1, 1, 1, al * tw)
            ctx.set_line_width(1.5)
            ctx.stroke()
        # 画面じゅうでまたたく星
        for x, y, sz, hue, ph, sp in self.twinkle:
            tw = max(0.0, math.sin(age * sp + ph))
            if tw < 0.05:
                continue
            self._star(ctx, x, y, sz * tw * 1.4, age)
            ctx.set_source_rgba(*_rainbow(hue + age * 0.7, 0.4), tw * dk)
            ctx.fill()
        # 3) 画面のふちが虹色に点滅する
        bw = 34
        for k, (rx, ry, rw, rh, gx0, gy0, gx1, gy1) in enumerate((
                (0, 0, W, bw, 0, 0, 0, bw), (0, H - bw, W, bw, 0, H, 0, H - bw),
                (0, 0, bw, H, 0, 0, bw, 0), (W - bw, 0, bw, H, W, 0, W - bw, 0))):
            col = _rainbow(age * 2.5 + k * 0.25)
            flick = 0.55 + 0.45 * (int(age * 14 + k) % 2)
            g = cairo.LinearGradient(gx0, gy0, gx1, gy1)
            g.add_color_stop_rgba(0, *col, flick * dk)
            g.add_color_stop_rgba(1, *col, 0)
            ctx.rectangle(rx, ry, rw, rh)
            ctx.set_source(g)
            ctx.fill()
        # 4) 「全部割った!!」がドンと弾んで出てくる
        if age > 0.35:
            a = age - 0.35
            sc = 1 + 0.6 * math.exp(-a * 7) * math.cos(a * 22)
            ctx.save()
            ctx.translate(W / 2, H * 0.47)
            ctx.scale(sc, sc)
            ctx.translate(-W / 2, -H * 0.47)
            self._text(ctx, "全部割った!!", H * 0.47 + 50, 150, age)
            ctx.restore()
        if age > 0.9:
            a = min(1.0, (age - 0.9) / 0.3)
            ctx.save()
            ctx.translate(W / 2, H * 0.58)
            ctx.scale(a, a)
            ctx.translate(-W / 2, -H * 0.58)
            self._text(ctx, "432 / 432", H * 0.58 + 30, 92, age + 0.3)
            ctx.restore()
        # 5) 最初の白いフラッシュ(2回ピカッ)
        for t0 in (0.0, 0.32):
            a = age - t0
            if 0 <= a < 0.18:
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.85 * (1 - a / 0.18))
                ctx.fill()
        if age > DURATION - 0.5:
            ctx.rectangle(0, 0, W, H)
            ctx.set_source_rgba(0, 0, 0, (age - (DURATION - 0.5)) / 0.5)
            ctx.fill()


# ---------------------------------------------------------------- 音
def _hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _kyuin(sr):
    """「キュイン!」: 一気に高く上がる明るい電子音(ビブラートつき)。"""
    t = np.arange(int(0.32 * sr)) / sr
    f = 700 + 2300 * (1 - np.exp(-t / 0.07))
    f *= 1 + 0.03 * np.sin(2 * np.pi * 28 * t)
    ph = 2 * np.pi * np.cumsum(f) / sr
    y = np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph) + 0.15 * np.sin(5 * ph)
    env = np.minimum(1, t / 0.006) * np.exp(-np.maximum(0, t - 0.16) * 14)
    return y * env


def _square(m, dur, sr, amp):
    t = np.arange(int(dur * sr)) / sr
    f = _hz(m)
    y = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 3, 5, 7))
    env = np.minimum(1, t / 0.004) * np.exp(-t * 6)
    return amp * y * env


def _bell(f, sr, amp):
    t = np.arange(int(0.7 * sr)) / sr
    y = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 8)
    return amp * y * np.exp(-t * 6) * np.minimum(1, t / 0.002)


def music(sr, seed=0):
    rng = np.random.default_rng(seed + 99)
    n = int(DURATION * sr)
    out = np.zeros((n, 2))

    def put(sig, t0, pan=0.0):
        i = int(t0 * sr)
        if i >= n:
            return
        j = min(n, i + len(sig))
        out[i:j, 0] += sig[: j - i] * math.sqrt(0.5 * (1 - pan))
        out[i:j, 1] += sig[: j - i] * math.sqrt(0.5 * (1 + pan))

    # キュインキュイン!(2回ずつを3セット、だんだん高く)
    for s, base in enumerate((0.0, 0.75, 1.5)):
        for j in range(2):
            k = _kyuin(sr)
            k = np.interp(np.arange(len(k)) * (1 + 0.12 * s), np.arange(len(k)), k)
            put(0.32 * k, base + j * 0.2, pan=-0.4 if j == 0 else 0.4)
    # ファンファーレ風のアルペジオ(16分音符、明るい長調でぐんぐん上がる)
    bpm = 150
    s16 = 60 / bpm / 4
    prog = [(60, 64, 67, 72), (62, 65, 69, 74), (64, 67, 71, 76), (65, 69, 72, 77),
            (67, 71, 74, 79), (69, 72, 76, 81)]
    t = 2.1
    i = 0
    while t < DURATION - 1.4:
        ch = prog[min(len(prog) - 1, int((t - 2.1) / (16 * s16)))]
        m = ch[i % 4] + 12 * ((i // 4) % 2)
        put(_square(m, 0.25, sr, 0.10), t, pan=0.3 * math.sin(i))
        if i % 4 == 0:   # 低い音で支える
            put(_square(ch[0] - 24, 0.4, sr, 0.10), t)
        t += s16
        i += 1
    # 最後に高い和音でジャーン
    t_end = DURATION - 1.4
    for m in (72, 76, 79, 84, 88):
        sig = _square(m, 1.4, sr, 0.06)
        sig *= np.exp(np.arange(len(sig)) / sr * 4.5)   # 減衰を打ち消して伸ばす
        sig *= np.exp(-np.arange(len(sig)) / sr * 5.2)
        put(sig, t_end)
    # チャリンチャリン(ずっとキラキラ)
    for _ in range(70):
        tt = rng.uniform(0.1, DURATION - 0.8)
        put(_bell(rng.uniform(2600, 5200), sr, 0.05), tt, pan=rng.uniform(-0.8, 0.8))
    # 少しだけ響きを足す
    wet = out.copy()
    for d, g in ((0.031, 0.25), (0.057, 0.18), (0.089, 0.12)):
        k = int(d * sr)
        wet[k:, 0] += out[:-k, 1] * g
        wet[k:, 1] += out[:-k, 0] * g
    fade = np.ones(n)
    k = int(0.6 * sr)
    fade[-k:] = np.linspace(1, 0, k)
    return wet * fade[:, None]
