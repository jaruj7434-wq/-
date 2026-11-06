"""成功したときの、おしゃれな終わり方(映像と音楽)。

映像: 白い光がふわっと広がる → 画面が静かに暗くなる → ガラスの粒がきらきら舞い上がる
      → 細い金のラインと「ALL CLEAR」の文字 → 6つのボールが音楽に合わせて1つずつ灯る。
音楽: ゆったりしたテンポのおしゃれなコード(エレピ風)に、やわらかいキック・スナップ・
      シェイカー・きらきらしたアルペジオを重ねた短い曲。すべてこのファイルの中で合成する。
"""
import math

import cairo
import numpy as np

DURATION = 9.6          # 成功してから動画が終わるまでの秒数(4小節ぶん)
BPM = 100
BEAT = 60 / BPM
INTRO = 0.4             # 割り切った瞬間から曲のビートが始まるまで
GOLD = (0.95, 0.80, 0.45)
JP_FONT = "IPAPGothic"
EN_FONT = "Liberation Serif"


# ---------------------------------------------------------------- 映像
class Ending:
    def __init__(self, W, H, seed, balls, draw_ball):
        rng = np.random.default_rng(seed + 4242)
        self.W, self.H = W, H
        self.balls, self.draw_ball = balls, draw_ball
        # 舞い上がるガラスの粒: x, y, 速さ, 大きさ, ちらつきの位相, 出てくる時刻
        self.motes = [(rng.uniform(0, W), rng.uniform(H * 0.25, H * 1.05), rng.uniform(25, 90),
                       rng.uniform(1.5, 5.5), rng.uniform(0, 6.28), rng.uniform(0.6, 2.2)) for _ in range(110)]

    def _spaced(self, ctx, s, cx, y, size, spacing, rgb, alpha, font, weight=cairo.FONT_WEIGHT_NORMAL):
        """文字の間をあけて中央にそろえて書く。"""
        ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL, weight)
        ctx.set_font_size(size)
        adv = [ctx.text_extents(ch).x_advance for ch in s]
        total = sum(adv) + spacing * (len(s) - 1)
        x = cx - total / 2
        ctx.set_source_rgba(*rgb, alpha)
        for ch, a in zip(s, adv):
            ctx.move_to(x, y)
            ctx.show_text(ch)
            x += a + spacing

    def draw(self, ctx, age):
        W, H = self.W, self.H
        cx, cy = W / 2, H * 0.46
        # 1) 割り切った瞬間、中心から白い光がやわらかく広がる
        if age < 1.2:
            k = age / 1.2
            r = 120 + 1500 * (1 - (1 - k) ** 3)
            g = cairo.RadialGradient(cx, cy, r * 0.55, cx, cy, r)
            g.add_color_stop_rgba(0, 1, 1, 1, 0)
            g.add_color_stop_rgba(0.75, 0.95, 0.98, 1, 0.55 * (1 - k))
            g.add_color_stop_rgba(1, 1, 1, 1, 0)
            ctx.rectangle(0, 0, W, H)
            ctx.set_source(g)
            ctx.fill()
            if age < 0.3:
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.55 * (1 - age / 0.3))
                ctx.fill()
        # 2) 画面がゆっくり暗くなる(真ん中は少し明るく残す)
        dk = min(1.0, max(0.0, (age - 0.7) / 1.3))
        dk = dk * dk * (3 - 2 * dk)
        if dk > 0:
            g = cairo.RadialGradient(cx, cy, 100, cx, cy, 1300)
            g.add_color_stop_rgba(0, 0.02, 0.025, 0.04, 0.70 * dk)
            g.add_color_stop_rgba(1, 0.0, 0.0, 0.01, 0.92 * dk)
            ctx.rectangle(0, 0, W, H)
            ctx.set_source(g)
            ctx.fill()
        # 3) ガラスの粒がきらきら舞い上がる
        for x0, y0, v, sz, ph, t0 in self.motes:
            a = age - t0
            if a <= 0:
                continue
            x = x0 + 18 * math.sin(a * 0.9 + ph)
            y = y0 - v * a
            fade = min(1.0, a / 0.6) * (0.55 + 0.45 * math.sin(a * 5 + ph * 3))
            if y < -20:
                continue
            g = cairo.RadialGradient(x, y, 0, x, y, sz * 3.5)
            g.add_color_stop_rgba(0, 0.9, 0.97, 1, 0.9 * fade)
            g.add_color_stop_rgba(1, 0.6, 0.85, 1, 0)
            ctx.set_source(g)
            ctx.arc(x, y, sz * 3.5, 0, 2 * math.pi)
            ctx.fill()
            if sz > 5.0:   # 大きい粒は十字に光る
                ctx.set_source_rgba(1, 1, 1, 0.5 * fade)
                ctx.set_line_width(1.2)
                ctx.move_to(x - sz * 4, y)
                ctx.line_to(x + sz * 4, y)
                ctx.move_to(x, y - sz * 4)
                ctx.line_to(x, y + sz * 4)
                ctx.stroke()
        # 4) 細い金のラインが真ん中から左右へのびる
        ty = H * 0.43
        lk = min(1.0, max(0.0, (age - 1.5) / 0.9))
        lk = 1 - (1 - lk) ** 3
        if lk > 0:
            for yy in (ty - 150, ty + 70):
                g = cairo.LinearGradient(cx - 380 * lk, 0, cx + 380 * lk, 0)
                g.add_color_stop_rgba(0, *GOLD, 0)
                g.add_color_stop_rgba(0.5, *GOLD, 0.9)
                g.add_color_stop_rgba(1, *GOLD, 0)
                ctx.set_source(g)
                ctx.rectangle(cx - 380 * lk, yy, 760 * lk, 2)
                ctx.fill()
        # 5) 「ALL CLEAR」が文字の間を広げながら浮かび上がる
        ak = min(1.0, max(0.0, (age - 1.8) / 1.0))
        ak = 1 - (1 - ak) ** 3
        if ak > 0:
            self._spaced(ctx, "ALL CLEAR", cx, ty + 12 * (1 - ak), 118, 10 + 16 * ak, (1, 1, 1), ak, EN_FONT)
            self._spaced(ctx, "— 432 / 432 GLASS —", cx, ty - 175, 30, 6, GOLD, ak * 0.95, EN_FONT)
        jk = min(1.0, max(0.0, (age - 2.6) / 0.8))
        if jk > 0:
            self._spaced(ctx, "6つのボールで、ぜんぶ割れました。", cx, ty + 150, 44, 4, (0.92, 0.94, 1.0), jk, JP_FONT)
        # 6) 6つのボールが拍に合わせて1つずつ灯る
        first = INTRO + 4 * BEAT
        for k in range(len(self.balls)):
            bt = first + k * BEAT / 2
            b = age - bt
            if b <= 0:
                continue
            x = cx + (k - 2.5) * 140
            y = H * 0.66
            pop = min(1.0, b / 0.25)
            sc = 1 + 0.35 * math.exp(-b * 8) * (b < 0.6)
            glow = cairo.RadialGradient(x, y, 0, x, y, 75)
            glow.add_color_stop_rgba(0, *self.balls[k][5], 0.45 * pop)
            glow.add_color_stop_rgba(1, *self.balls[k][5], 0)
            ctx.set_source(glow)
            ctx.arc(x, y, 75, 0, 2 * math.pi)
            ctx.fill()
            self.draw_ball(ctx, k, x, y, age * 1.5, 34 * sc * pop, age, pop, None)
            self._spaced(ctx, self.balls[k][0], x, y + 80, 22, 1, (0.85, 0.88, 0.95), pop * 0.9, JP_FONT)
        # 7) 最後はゆっくり暗転
        if age > DURATION - 0.9:
            ctx.rectangle(0, 0, W, H)
            ctx.set_source_rgba(0, 0, 0, min(1.0, (age - (DURATION - 0.9)) / 0.9))
            ctx.fill()


# ---------------------------------------------------------------- 音楽
def _hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _env(n, sr, a, d):
    t = np.arange(n) / sr
    return np.minimum(1, t / a) * np.exp(-t / d)


def _epiano(m, dur, sr, amp):
    """エレピ風の音(FM合成): 弾いた瞬間は明るく、すぐまろやかになる。"""
    n = int(dur * sr)
    t = np.arange(n) / sr
    f = _hz(m)
    idx = 1.6 * np.exp(-t * 6) + 0.25
    y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    y += 0.25 * np.sin(2 * np.pi * f * 14 * t) * np.exp(-t * 40)     # 「コン」という打鍵感
    y *= 1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)                        # ゆらぎ(トレモロ)
    return amp * y * _env(n, sr, 0.004, 0.9) * np.minimum(1, (n - np.arange(n)) / (0.05 * sr))


def _pluck(m, sr, amp):
    n = int(0.6 * sr)
    t = np.arange(n) / sr
    f = _hz(m)
    y = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 12)
    return amp * y * _env(n, sr, 0.002, 0.16)


def _kick(sr, amp):
    n = int(0.45 * sr)
    t = np.arange(n) / sr
    f = 48 + 90 * np.exp(-t * 28)
    return amp * np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 7) * np.minimum(1, t / 0.002)


def _snap(sr, amp, rng):
    n = int(0.25 * sr)
    t = np.arange(n) / sr
    x = rng.normal(0, 1, n)
    x = x - np.convolve(x, np.ones(6) / 6, mode="same")
    return amp * x * np.exp(-t * 28)


def _shaker(sr, amp, rng):
    n = int(0.08 * sr)
    t = np.arange(n) / sr
    x = rng.normal(0, 1, n)
    x = x - np.convolve(x, np.ones(3) / 3, mode="same")
    return amp * x * np.minimum(1, t / 0.01) * np.exp(-t * 60)


def _reverb(x, sr, secs=2.2, seed=3):
    """広いホールのような残響(減衰するノイズとの畳み込み)。"""
    rng = np.random.default_rng(seed)
    n = int(secs * sr)
    t = np.arange(n) / sr
    ir = rng.normal(0, 1, (n, 2)) * np.exp(-t * 3.2)[:, None]
    ir[:, 0] = np.convolve(ir[:, 0], np.ones(8) / 8, mode="same")   # 高い音を少しやわらかく
    ir[:, 1] = np.convolve(ir[:, 1], np.ones(8) / 8, mode="same")
    ir /= np.sqrt(np.sum(ir ** 2, axis=0))
    m = len(x) + n
    L = 1 << (m - 1).bit_length()
    out = np.zeros((len(x) + n - 1, 2))
    for c in range(2):
        out[:, c] = np.fft.irfft(np.fft.rfft(x[:, c], L) * np.fft.rfft(ir[:, c], L), L)[: len(x) + n - 1]
    return out[: len(x)]


def music(sr, seed=0):
    """成功した瞬間から流れる、おしゃれで気持ちのいい短い曲(ステレオ, 長さ DURATION 秒)。"""
    rng = np.random.default_rng(seed + 77)
    n = int(DURATION * sr)
    dry = np.zeros((n, 2))
    send = np.zeros((n, 2))   # 残響に送る音

    def put(buf, sig, t0, pan=0.0):
        i = int(t0 * sr)
        if i >= n:
            return
        j = min(n, i + len(sig))
        buf[i:j, 0] += sig[: j - i] * math.sqrt(0.5 * (1 - pan))
        buf[i:j, 1] += sig[: j - i] * math.sqrt(0.5 * (1 + pan))

    # 0) 割り切った瞬間の、ガラスのきらめき(上へかけ上がる)
    for k, m in enumerate((84, 88, 91, 95, 98, 100, 103)):
        s = _pluck(m, sr, 0.10)
        put(dry, s, k * 0.045, pan=-0.6 + 0.2 * k)
        put(send, s * 1.4, k * 0.045, pan=-0.6 + 0.2 * k)
    # コード進行(1小節ずつ): Fmaj9 → Em9 → Dm9 → Cmaj9(ゆったり下がっていく)
    chords = [(53, [57, 60, 64, 67]), (52, [55, 59, 62, 66]), (50, [53, 57, 60, 64]), (48, [52, 55, 59, 62])]
    bar = 4 * BEAT
    for b, (root, notes) in enumerate(chords):
        t0 = INTRO + b * bar
        last = b == len(chords) - 1
        # エレピ: 1拍目と、2拍目の裏(シンコペーション)
        hits = [(0.0, 1.0, 1.8)] if last else [(0.0, 1.0, 1.3), (1.5 * BEAT, 0.7, 1.0), (3 * BEAT, 0.55, 0.6)]
        for off, vel, dur in hits:
            for j, m in enumerate(notes):
                s = _epiano(m, dur + (2.5 if last else 0), sr, 0.075 * vel)
                put(dry, s, t0 + off + j * 0.012, pan=-0.3 + 0.2 * j)
                put(send, s * 0.6, t0 + off + j * 0.012, pan=-0.3 + 0.2 * j)
        # ベース(やわらかいサイン波)
        for off, dur in ([(0, 3.0)] if last else [(0, 1.4 * BEAT), (2.5 * BEAT, 1.2 * BEAT)]):
            k = int(dur * sr)
            tt = np.arange(k) / sr
            s = 0.20 * np.sin(2 * np.pi * _hz(root - 12) * tt) * np.minimum(1, tt / 0.01) * np.minimum(1, (k - np.arange(k)) / (0.06 * sr))
            put(dry, s, t0 + off)
        # きらきらしたアルペジオ(8分音符、左右に揺れる)
        arp = [notes[0] + 12, notes[2] + 12, notes[3] + 12, notes[1] + 24]
        for e in range(4 if last else 8):
            s = _pluck(arp[e % 4], sr, 0.05)
            pan = 0.5 if e % 2 else -0.5
            put(dry, s, t0 + e * BEAT / 2, pan)
            put(send, s, t0 + e * BEAT / 2 + 3 * BEAT / 4, -pan)   # 反対側にこだま
        if last:
            continue
        # リズム: キック(1・3拍)、スナップ(2・4拍)、シェイカー(16分)
        for q in range(4):
            if q in (0, 2):
                put(dry, _kick(sr, 0.36), t0 + q * BEAT)
            else:
                s = _snap(sr, 0.10, rng)
                put(dry, s, t0 + q * BEAT)
                put(send, s * 1.2, t0 + q * BEAT)
        for s16 in range(16):
            acc = 0.035 if s16 % 2 else 0.018
            put(dry, _shaker(sr, acc, rng), t0 + s16 * BEAT / 4, pan=0.35)
    # 最後の和音に向かって、すっと鳴る高いベル
    for k, m in enumerate((88, 91, 95)):
        s = _pluck(m, sr, 0.06)
        put(send, s * 2, INTRO + 3 * bar + 0.02 + k * 0.08, pan=0.3 * (k - 1))
    out = dry + 0.55 * _reverb(send + 0.25 * dry, sr)
    # 最後はゆっくり消える
    fade = np.ones(n)
    k = int(1.2 * sr)
    fade[-k:] = np.linspace(1, 0, k) ** 2
    return out * fade[:, None]
