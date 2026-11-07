"""最後の発表会(最新のZが横向きで大きく出る場面)を高級感のある見た目と音にする。

映像:
  - スポットライトの中を細かいほこりがきらきら漂う
  - ヘッドライトが点いて、横に長い青白いレンズフレアと星形の光
  - 光の帯がボディを走るときに、ボディの上でキラッと光る
  - 車名は普通の文字ではなく、クロームの金属のような文字に光が走る
  - 細い金のラインで上下をしめる
音(すべて合成):
  - 白い光が引くと同時に、映画の予告編のような重低音の「ドォォン」(サブベース+ひずんだ低音の和音が開いていく)
  - 高い音がきらめく広い和音(シマー)が長く鳴る
  - 光の帯で「シュワーン」、車名が出るときに金属の「キィィン」+低い「ドン」
  - 全体に長いホールの残響
"""
import math

import cairo
import numpy as np

# ---------------------------------------------------------------- 映像
_DUST = None


def _dust(W, H):
    global _DUST
    if _DUST is None:
        rng = np.random.default_rng(2022)
        _DUST = [(rng.uniform(-1, 1), rng.uniform(0, 1), rng.uniform(1.0, 3.6), rng.uniform(0, 6.28),
                  rng.uniform(4, 18)) for _ in range(150)]
    return _DUST


def draw_dust(ctx, age, W, a):
    """スポットライトの円すいの中をほこりがゆっくり漂って、きらっと光る。"""
    for u, v, sz, ph, sp in _dust(W, 0):
        y = 40 + v * 1380 + sp * age * 2 * math.sin(ph)
        half = 60 + 500 * (y / 1420)
        x = W / 2 + u * half * 0.9 + 12 * math.sin(age * 0.6 + ph)
        tw = 0.35 + 0.65 * max(0.0, math.sin(age * 2.3 + ph * 3)) ** 3
        g = cairo.RadialGradient(x, y, 0, x, y, sz * 3)
        g.add_color_stop_rgba(0, 1, 0.97, 0.9, 0.55 * tw * a)
        g.add_color_stop_rgba(1, 1, 0.97, 0.9, 0)
        ctx.set_source(g)
        ctx.arc(x, y, sz * 3, 0, 2 * math.pi)
        ctx.fill()


def flare(ctx, x, y, k, W, hue=(0.75, 0.88, 1.0)):
    """ヘッドライトのレンズフレア:中心の強い光+横に長い光の筋+星形の細い光+小さな光の輪。"""
    if k <= 0:
        return
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.RadialGradient(x, y, 0, x, y, 120 * k)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.95 * k)
    g.add_color_stop_rgba(0.25, *hue, 0.5 * k)
    g.add_color_stop_rgba(1, *hue, 0)
    ctx.set_source(g)
    ctx.arc(x, y, 120 * k, 0, 2 * math.pi)
    ctx.fill()
    for sy, a, rr in ((0.035, 0.8, 900), (0.01, 1.0, 1300)):   # 横に長い筋
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(1.0, sy)
        g = cairo.RadialGradient(0, 0, 0, 0, 0, rr * k)
        g.add_color_stop_rgba(0, *hue, a * k)
        g.add_color_stop_rgba(1, *hue, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, rr * k, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()
    for ang in (math.pi / 4, -math.pi / 4):   # 星形の細い光
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(ang)
        ctx.scale(1.0, 0.012)
        g = cairo.RadialGradient(0, 0, 0, 0, 0, 220 * k)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.7 * k)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, 220 * k, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()
    dx, dy = W / 2 - x, 960 - y   # 画面の中心をはさんで反対側に並ぶ小さな光の輪(ゴースト)
    for f, r, a in ((0.6, 34, 0.12), (1.1, 18, 0.18), (1.5, 60, 0.07), (1.9, 26, 0.12)):
        gx, gy = x + dx * f, y + dy * f
        g = cairo.RadialGradient(gx, gy, r * 0.6, gx, gy, r)
        g.add_color_stop_rgba(0, *hue, 0)
        g.add_color_stop_rgba(0.8, *hue, a * k)
        g.add_color_stop_rgba(1, *hue, 0)
        ctx.set_source(g)
        ctx.arc(gx, gy, r, 0, 2 * math.pi)
        ctx.fill()
    ctx.restore()


def glint(ctx, x, y, k, size=90):
    """ボディの上で一瞬キラッと光る星。"""
    if k <= 0:
        return
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_ADD)
    for ang, ln in ((0, 1.0), (math.pi / 2, 0.7)):
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(ang)
        ctx.scale(1.0, 0.03)
        g = cairo.RadialGradient(0, 0, 0, 0, 0, size * ln * k)
        g.add_color_stop_rgba(0, 1, 1, 1, k)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, size * ln * k, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()
    g = cairo.RadialGradient(x, y, 0, x, y, 22 * k)
    g.add_color_stop_rgba(0, 1, 1, 1, k)
    g.add_color_stop_rgba(1, 1, 1, 1, 0)
    ctx.set_source(g)
    ctx.arc(x, y, 22 * k, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


def chrome_text(ctx, s, cx, y, size, age, font="DejaVu Sans", spacing=0.22):
    """クロームの金属のような文字(上が明るく、真ん中に地平線のような暗い帯、下が少し明るい)+光が走る。"""
    a = min(1.0, age / 0.6)
    ctx.save()
    ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    adv = [ctx.text_extents(ch).x_advance for ch in s]
    total = sum(adv) + size * spacing * (len(s) - 1)
    x = cx - total / 2
    ctx.new_path()
    xx = x
    for ch, w in zip(s, adv):
        ctx.move_to(xx, y)
        ctx.text_path(ch)
        xx += w + size * spacing
    g = cairo.LinearGradient(0, y - size * 0.75, 0, y + size * 0.05)
    for st, c in ((0, (0.98, 0.99, 1)), (0.42, (0.78, 0.82, 0.9)), (0.5, (0.25, 0.28, 0.34)),
                  (0.62, (0.55, 0.6, 0.68)), (1, (0.95, 0.96, 1))):
        g.add_color_stop_rgba(st, *c, a)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.5 * a)
    ctx.set_line_width(1.2)
    ctx.stroke_preserve()
    p = ((age - 0.4) / 1.1)   # 光が左から右へ一度走る
    if 0 <= p <= 1:
        sx = x - 200 + (total + 400) * p
        g2 = cairo.LinearGradient(sx - 90, 0, sx + 90, 0)
        g2.add_color_stop_rgba(0, 1, 1, 1, 0)
        g2.add_color_stop_rgba(0.5, 1, 1, 1, 0.95)
        g2.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g2)
        ctx.fill()
        glint(ctx, sx, y - size * 0.35, math.sin(math.pi * p), 140)
    ctx.new_path()
    ctx.restore()
    # 上下の細い金のライン
    lk = 1 - (1 - min(1.0, age / 0.8)) ** 3
    for yy in (y - size - 34, y + 34):
        g = cairo.LinearGradient(cx - 330 * lk, 0, cx + 330 * lk, 0)
        g.add_color_stop_rgba(0, 0.95, 0.8, 0.45, 0)
        g.add_color_stop_rgba(0.5, 0.95, 0.8, 0.45, 0.9 * a)
        g.add_color_stop_rgba(1, 0.95, 0.8, 0.45, 0)
        ctx.set_source(g)
        ctx.rectangle(cx - 330 * lk, yy, 660 * lk, 1.6)
        ctx.fill()


# ---------------------------------------------------------------- 音
def _t(d, sr):
    return np.arange(int(d * sr)) / sr


def _hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _saw(f, t, rng, detune=0.006, n=3):
    y = np.zeros(len(t))
    for i in range(n):
        ff = f * (1 + detune * (i - (n - 1) / 2))
        ph = rng.uniform(0, 1)
        y += 2 * ((ff * t + ph) % 1.0) - 1
    return y / n


def _lowpass(x, cutoff_env, sr):
    """1次のローパス(遮断周波数を時間で変える)。"""
    y = np.zeros(len(x))
    s = 0.0
    a = 1 - np.exp(-2 * np.pi * cutoff_env / sr)
    for i in range(len(x)):
        s += a[i] * (x[i] - s)
        y[i] = s
    return y


def _reverb(x, sr, secs=3.2, seed=4):
    rng = np.random.default_rng(seed)
    n = int(secs * sr)
    t = np.arange(n) / sr
    ir = rng.normal(0, 1, n) * np.exp(-t * 2.2)
    ir = np.convolve(ir, np.ones(6) / 6, "same")
    ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n
    L = 1 << (m - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[:len(x)]


def reveal_sound(sr, dur, root, seed=0):
    """発表会の場面の音(モノラル)。0秒 = 白い光が引き始める瞬間。"""
    rng = np.random.default_rng(seed + 77)
    n = int(dur * sr)
    out = np.zeros(n)

    def put(sig, t0, g=1.0):
        i = int(t0 * sr)
        if i >= n:
            return
        j = min(n, i + len(sig))
        out[i:j] += g * sig[: j - i]

    # 1) 予告編のような「ドォォン」: サブベースの落ち込み+ひずんだ低音の和音がだんだん開く
    t = _t(4.5, sr)
    sub = np.sin(2 * np.pi * np.cumsum(32 + 60 * np.exp(-t * 5)) / sr) * np.exp(-t * 0.9)
    chord = sum(_saw(_hz(m), t, rng) for m in (root - 24, root - 17, root - 12, root - 5))
    chord = np.tanh(1.8 * chord)
    cut = 120 + 2600 * (1 - np.exp(-t * 2.5)) * np.exp(-t * 0.35)
    braam = _lowpass(chord, cut, sr) * np.minimum(1, t / 0.02) * np.exp(-t * 0.55)
    noise = rng.normal(0, 1, len(t))
    hit = (noise - np.convolve(noise, np.ones(5) / 5, "same")) * np.exp(-t * 18)
    put(0.9 * sub + 0.55 * braam + 0.25 * hit, 0.05)
    # 2) 高くきらめく広い和音(シマー)
    t = _t(5.5, sr)
    shim = sum(np.sin(2 * np.pi * _hz(m) * t * (1 + 0.002 * np.sin(2 * np.pi * (0.3 + 0.1 * i) * t)))
               for i, m in enumerate((root + 7, root + 12, root + 16, root + 19, root + 24, root + 28)))
    shim *= np.minimum(1, t / 1.2) * np.exp(-t * 0.35) * (0.8 + 0.2 * np.sin(2 * np.pi * 5 * t))
    put(0.09 * shim, 0.15)
    # 3) 光の帯が走る「シュワーン」(1.0秒〜)
    t = _t(1.3, sr)
    nz = rng.normal(0, 1, len(t))
    sw = (nz - np.convolve(nz, np.ones(3) / 3, "same")) * np.sin(np.pi * t / 1.3) ** 2
    sw += 0.4 * np.sin(2 * np.pi * np.cumsum(900 + 1800 * t / 1.3) / sr) * np.sin(np.pi * t / 1.3) ** 3
    put(0.22 * sw, 0.95)
    # 4) 車名が出る:逆再生のような吸い込み音 → 金属の「キィィン」+低い「ドン」(1.2秒)
    t = _t(0.6, sr)
    nz = rng.normal(0, 1, len(t))
    rev = (nz - np.convolve(nz, np.ones(4) / 4, "same")) * (t / 0.6) ** 4
    put(0.3 * rev, 1.2 - 0.6)
    t = _t(3.0, sr)
    metal = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d)
                for f, a, d in ((1318, 1.0, 1.2), (1975, 0.6, 1.6), (2637, 0.45, 2.0), (3520, 0.3, 2.6), (4699, 0.2, 3.2)))
    boom = np.sin(2 * np.pi * np.cumsum(45 + 70 * np.exp(-t * 9)) / sr) * np.exp(-t * 2.2)
    put(0.18 * metal + 0.7 * boom, 1.2)
    # 5) 最後の文字が出るときの、やわらかいピアノの和音(1.7秒)
    t = _t(3.5, sr)
    piano = sum(np.sin(2 * np.pi * _hz(m) * t) * np.exp(-t * 1.3) + 0.3 * np.sin(2 * np.pi * _hz(m) * 2 * t) * np.exp(-t * 3)
                for m in (root, root + 4, root + 7, root + 11, root + 14))
    put(0.08 * piano * np.minimum(1, t / 0.005), 1.7)
    wet = out + 0.45 * _reverb(out, sr)
    fade = np.ones(n)
    k = int(0.8 * sr)
    fade[-k:] = np.linspace(1, 0, k)
    ref = np.percentile(np.abs(wet), 99.7)
    wet = np.tanh(1.3 * wet / max(1e-9, ref)) / np.tanh(1.3) * 0.85   # 音割れしないよう、大きすぎる瞬間だけやわらかく抑える
    return wet * fade
