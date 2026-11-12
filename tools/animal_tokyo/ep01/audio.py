"""第1話の環境音・効果音・BGMを合成して WAV に書き出す。

使い方: python3 ep01/audio.py <out.wav>
時間軸は timeline.json と shots.js の動き（はばたき・ジャンプ・つつく）に合わせている。
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
HERE = Path(__file__).parent
TL = json.loads((HERE / "timeline.json").read_text())
DUR = TL["duration"]
N = int(DUR * SR)
T = np.arange(N) / SR
rs = np.random.default_rng(7)

L = np.zeros(N)
R = np.zeros(N)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), x)


def env(points):
    """[(t, v), ...] を直線補間した音量カーブ"""
    ts, vs = zip(*points)
    return np.interp(T, ts, vs)


def add(sig, t0=0.0, gain=1.0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    sig = sig[: N - i0]
    gl, gr = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)
    L[i0 : i0 + len(sig)] += sig * gain * gl
    R[i0 : i0 + len(sig)] += sig * gain * gr


def brown(n):
    w = rs.standard_normal(n)
    b = np.cumsum(w)
    b = hp(b, 15)
    return b / (np.abs(b).max() + 1e-9)


def reverb_ir(sec=1.2, damp=3.0):
    n = int(sec * SR)
    ir = rs.standard_normal(n) * np.exp(-np.arange(n) / SR * damp)
    ir = lp(ir, 5000)
    ir[0] = 1.0
    return ir / np.abs(ir).sum() * 6


IR = reverb_ir()


def wet(x, mix=0.35):
    y = fftconvolve(x, IR)[: len(x) + len(IR) // 2]
    out = np.zeros(len(y))
    out[: len(x)] += x * (1 - mix)
    return out + y * mix


# ---------------------------------------------------------------- 素材
def caw(pitch=520.0, dur=0.38, rough=0.6):
    """ハシブトガラスの「カァ」：鼻にかかった澄んだ声。倍音＋母音のフォルマント"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    prog = t / dur
    f0 = pitch * (1.0 + 0.08 * np.sin(np.pi * prog) - 0.12 * prog) * (1 + 0.006 * np.sin(2 * np.pi * 23 * t))
    ph = 2 * np.pi * np.cumsum(f0) / SR
    src = sum(np.sin(k * ph) / k ** 0.9 for k in range(1, 18))
    src *= 1 + rough * 0.5 * np.sin(2 * np.pi * 70 * t + rs.random() * 6)  # しわがれ
    src += rs.standard_normal(n) * 0.25
    y = bp(src, 650, 900) * 1.0 + bp(src, 1150, 1450) * 0.8 + bp(src, 2400, 2900) * 0.35
    a = np.minimum(1, t / 0.025) * np.exp(-np.maximum(0, t - dur * 0.55) * 14)
    y *= a
    return y / (np.abs(y).max() + 1e-9)


def caw_series(t0, count, pitch, gap, gain, pan, dist=0.0):
    for k in range(count):
        c = caw(pitch * (1 + rs.uniform(-0.03, 0.03)), rs.uniform(0.32, 0.42))
        if dist > 0:
            c = lp(c, 4000 - dist * 2800)
            c = wet(c, 0.25 + dist * 0.5)
        add(c, t0 + k * gap * rs.uniform(0.9, 1.1), gain, pan)


def whoosh(dur=0.12, lo=150, hi=900):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = bp(rs.standard_normal(n), lo, hi) * np.sin(np.pi * t / dur) ** 2
    return y / (np.abs(y).max() + 1e-9)


def flaps(t0, t1, hz, gain, pan=0.0):
    t = t0
    while t < t1:
        add(whoosh(0.11, 120, 700), t, gain, pan - 0.2)
        add(whoosh(0.11, 140, 800), t + 0.004, gain, pan + 0.2)
        add(whoosh(0.05, 1500, 5000), t + 0.03, gain * 0.25, pan)
        t += 1 / hz


def crinkle(dur=0.3, density=900, gain=1.0):
    """ビニール袋のカサカサ"""
    n = int(dur * SR)
    x = np.zeros(n)
    idx = rs.integers(0, n, int(density * dur))
    x[idx] = rs.uniform(-1, 1, len(idx)) * np.exp(-idx / n * 3)
    x = bp(x, 1800, 9000) + bp(x, 500, 1800) * 0.4
    x *= np.exp(-np.arange(n) / SR * 8)
    return x / (np.abs(x).max() + 1e-9) * gain


def thud(dur=0.08, f=110):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t * (1 - t * 3)) * np.exp(-t * 60) + bp(rs.standard_normal(n), 2000, 6000) * np.exp(-t * 120) * 0.3
    return y


def chirp_bird(t0, gain, pan):
    """スズメのチュン"""
    for k in range(rs.integers(2, 4)):
        n = int(0.07 * SR)
        t = np.arange(n) / SR
        f = 4200 + 1600 * np.sin(np.pi * t / 0.07) + rs.uniform(-300, 300)
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.07) ** 2
        add(wet(y, 0.3), t0 + k * rs.uniform(0.11, 0.16), gain, pan)


# ---------------------------------------------------------------- ベッド（環境音の土台）
hum = lp(brown(N), 180) * 0.6 + bp(rs.standard_normal(N), 200, 900) * 0.05
hum_env = env([(0, 0.0), (0.4, 0.13), (5, 0.12), (10, 0.1), (15, 0.09), (20, 0.1), (22.2, 0.14), (22.3, 0.26), (25, 0.24), (25.05, 0.2), (31, 0.2), (31.05, 0.07), (37, 0.07), (37.05, 0.06), (43, 0.06), (43.05, 0.2), (49, 0.2), (49.05, 0.17), (55, 0.17), (55.05, 0.12), (60, 0.1), (60.3, 0.03), (68, 0.0)])
add(hum * hum_env, 0, 1.0)

wind_src = bp(rs.standard_normal(N), 250, 1600) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.23 * T) * np.sin(2 * np.pi * 0.071 * T + 1))
wind_env = env([(0, 0.02), (5.6, 0.03), (6.2, 0.16), (8, 0.24), (10, 0.22), (10.05, 0.02), (21.5, 0.02), (22.0, 0.2), (22.3, 0.14), (25, 0.14), (25.05, 0.02), (37, 0.02), (37.05, 0.05), (43, 0.05), (43.05, 0.1), (49, 0.1), (49.05, 0.04), (55, 0.04), (55.05, 0.2), (60, 0.2), (60.4, 0.0), (68, 0)])
add(wind_src * wind_env, 0, 1.0, -0.1)
add(np.roll(wind_src, 9000) * wind_env, 0, 1.0, 0.1)

# 森の葉ずれ（C1）と飛び立ち（C2）
leaf = bp(rs.standard_normal(N), 1500, 6500) * (0.3 + 0.7 * np.abs(lp(rs.standard_normal(N), 4) * 25).clip(0, 1))
add(leaf * env([(0, 0), (0.5, 0.006), (4.8, 0.008), (5.5, 0.008), (5.7, 0.09), (6.6, 0.06), (7.2, 0.0), (37, 0), (37.05, 0.012), (43, 0.012), (43.05, 0), (68, 0)]), 0, 1.0)

# ---------------------------------------------------------------- C1・C2：夜明け前の森
caw_series(0.9, 2, 470, 0.55, 0.10, -0.6, dist=0.9)
caw_series(2.1, 3, 540, 0.48, 0.22, 0.45, dist=0.5)
caw_series(3.9, 2, 500, 0.5, 0.09, -0.2, dist=0.95)
caw_series(5.15, 2, 530, 0.45, 0.3, 0.2, dist=0.3)   # 自分の群れ
flaps(5.6, 7.6, 5.2, 0.32)
caw_series(7.9, 2, 480, 0.5, 0.08, 0.6, dist=0.9)
caw_series(9.0, 3, 560, 0.42, 0.06, -0.5, dist=1.0)

# ---------------------------------------------------------------- C3・C4：路地
# 遠くの電車
train = lp(brown(int(5 * SR)), 300)
clack = np.zeros(int(5 * SR))
for k in np.arange(0.4, 4.8, 0.62):
    i = int(k * SR)
    clack[i : i + 2000] += thud(2000 / SR, 70)[:2000]
    clack[i + 6000 : i + 8000] += thud(2000 / SR, 75)[:2000]
tr = (train + clack * 0.5) * np.sin(np.pi * np.arange(len(train)) / len(train))
add(wet(lp(tr, 900), 0.5), 10.0, 0.16, -0.5)
for t0, pan in [(10.6, 0.5), (12.4, -0.4), (13.9, 0.6), (15.8, -0.6), (17.3, 0.5), (19.1, -0.3)]:
    chirp_bird(t0, 0.07, pan)
caw_series(13.2, 1, 500, 0.5, 0.06, 0.7, dist=0.8)
add(crinkle(0.5, 300, 0.05), 11.6, 1.0, 0.1)  # 風で袋がゆれる

hopT = [0.25, 0.7, 1.15, 1.6, 2.05, 2.5, 2.9]
for h in hopT:
    add(thud(0.06, 140), 15 + h + 0.22, 0.22, 0)
    add(bp(rs.standard_normal(1500), 3000, 9000) * np.exp(-np.arange(1500) / 300), 15 + h + 0.23, 0.05)
for q in [3.35, 3.85, 4.3]:
    add(crinkle(0.35, 1400, 1.0), 15 + q + 0.1, 0.42, 0.15)
    add(thud(0.03, 300), 15 + q + 0.1, 0.12, 0.15)
add(crinkle(0.6, 500, 1.0), 19.0, 0.18, 0.2)

# ---------------------------------------------------------------- C5：収集車 → 交差点
n = int(2.4 * SR)
t = np.arange(n) / SR
f = 32 + 3 * np.sin(2 * np.pi * 0.7 * t)
ph = 2 * np.pi * np.cumsum(f) / SR
eng = sum(np.sin(k * ph) / k for k in range(1, 10)) + lp(rs.standard_normal(n), 400) * 0.6
eng *= np.linspace(0.25, 1.0, n) ** 2
add(lp(eng, 1200) / np.abs(eng).max(), 20.0, 0.5)
add(bp(rs.standard_normal(int(0.6 * SR)), 2500, 8000) * np.exp(-np.arange(int(0.6 * SR)) / SR * 4), 21.4, 0.06)  # エアブレーキ
caw_series(21.62, 1, 540, 0.4, 0.33, 0.0)
flaps(21.55, 22.25, 5.5, 0.38)
# 交差点：雑踏・足音・歩行者用の誘導音
crowd = bp(rs.standard_normal(N), 250, 2800) * (0.7 + 0.3 * lp(rs.standard_normal(N), 3) * 20)
add(crowd * env([(0, 0), (22.2, 0), (22.35, 0.07), (24.9, 0.07), (25.05, 0), (38, 0)]), 0, 1.0)
for k in range(140):
    tt = 22.3 + rs.uniform(0, 2.7)
    add(bp(rs.standard_normal(600), 1500, 6000) * np.exp(-np.arange(600) / 120), tt, 0.015, rs.uniform(-0.8, 0.8))
for tt in np.arange(22.5, 24.9, 0.75):
    for j, (fa, fb) in enumerate([(2200, 3000), (2400, 3200)]):
        n = int(0.09 * SR)
        tq = np.arange(n) / SR
        y = np.sin(2 * np.pi * np.cumsum(np.linspace(fa, fb, n)) / SR) * np.sin(np.pi * tq / 0.09)
        add(wet(y, 0.4), tt + j * 0.14, 0.035, 0.3)


# ---------------------------------------------------------------- 日中（D1〜D5）
def traffic(t0, dur, gain, density=1.0):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    y = lp(rs.standard_normal(n), 500) * 0.5
    for k in range(int(dur * density)):  # 通りすぎる車
        c = rs.uniform(0, dur)
        y += bp(rs.standard_normal(n), 200, 1800) * np.exp(-((tt - c) / 0.7) ** 2) * rs.uniform(0.5, 1.2)
    add(y / (np.abs(y).max() + 1e-9), t0, gain, rs.uniform(-0.3, 0.3))


def chatter(t0, dur, gain):
    """遠くの人の話し声（言葉にならない程度）"""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    y = np.zeros(n)
    for k in range(int(dur * 3)):
        c = rs.uniform(0, dur); L = rs.uniform(0.3, 1.2); f = rs.uniform(110, 240)
        m = (np.abs(tt - c - L / 2) < L / 2) * (0.6 + 0.4 * np.sin(2 * np.pi * rs.uniform(3, 6) * tt))
        ph = 2 * np.pi * np.cumsum(f * (1 + 0.1 * np.sin(2 * np.pi * 1.5 * tt))) / SR
        v = sum(np.sin(h * ph) / h for h in range(1, 8))
        y += bp(v, 300, 2500) * m
    add(wet(lp(y, 1500), 0.6)[:n] / (np.abs(y).max() + 1e-9), t0, gain, rs.uniform(-0.4, 0.4))


def splash(t0, gain):
    n = int(0.45 * SR)
    tt = np.arange(n) / SR
    y = bp(rs.standard_normal(n), 400, 7000) * np.exp(-tt * 9)
    for k in range(25):  # 水滴
        i = rs.integers(0, n - 800)
        f = rs.uniform(900, 2500)
        y[i:i + 800] += np.sin(2 * np.pi * f * np.arange(800) / SR * (1 + np.arange(800) / 800)) * np.exp(-np.arange(800) / 150) * 0.4
    add(y / (np.abs(y).max() + 1e-9), t0, gain, rs.uniform(-0.2, 0.2))


# D1 貯食（25〜31）：歩道・車・土をつつく音
traffic(25, 6, 0.22, 1.2)
for h in [0.3, 0.8]:
    add(thud(0.05, 160), 25 + h + 0.22, 0.18)
for k in np.arange(27.9, 28.6, 0.12):  # 土に押し込む
    add(lp(bp(rs.standard_normal(2400), 200, 3000) * np.exp(-np.arange(2400) / 500), 2500), k, 0.12)
add(crinkle(0.25, 400, 1.0), 28.85, 0.08)  # 落ち葉
add(crinkle(0.2, 400, 1.0), 29.4, 0.07)
for t0, pan in [(25.6, 0.5), (27.0, -0.4), (30.2, 0.3)]:
    chirp_bird(t0, 0.06, pan)
# D2 水浴び（31〜37）
water = bp(rs.standard_normal(int(6 * SR)), 300, 4000) * 0.15 + lp(rs.standard_normal(int(6 * SR)), 300) * 0.3
add(water / np.abs(water).max(), 31, 0.07)
for d in [1.7, 2.35, 3.0, 3.6, 4.15]:
    splash(31 + d, 0.45)
    flaps(31 + d, 31 + d + 0.35, 9, 0.12)
for k in np.arange(35.7, 36.5, 0.05):  # ブルブルッ
    add(whoosh(0.05, 300, 2500), k, 0.12)
chatter(31, 6, 0.05)
for t0, pan in [(31.4, -0.5), (34.6, 0.6)]:
    chirp_bird(t0, 0.05, pan)
# D3 昼の休息（37〜43）
chatter(37, 6, 0.1)
for t0, pan in [(37.8, 0.4), (39.6, -0.5), (41.5, 0.2)]:
    chirp_bird(t0, 0.05, pan)
caw_series(40.8, 1, 500, 0.5, 0.05, 0.6, dist=0.8)
for k in np.arange(39.5, 41.1, 0.09):  # 羽づくろい
    add(whoosh(0.04, 2000, 7000), k, 0.04)
# D4 屋上（43〜49）
traffic(43, 6, 0.3, 2.5)
chatter(43, 6, 0.04)
flaps(45.3, 46.6, 5, 0.3, 0.4)
caw_series(46.0, 2, 520, 0.45, 0.28, 0.4)
caw_series(47.3, 1, 560, 0.4, 0.2, 0.2)
# D5 集合（49〜55）
traffic(49, 6, 0.18, 1.5)
for k in range(22):
    caw_series(49.1 + rs.uniform(0, 5.6), rs.integers(1, 3), rs.uniform(460, 600), 0.45, rs.uniform(0.06, 0.24), rs.uniform(-0.8, 0.8), dist=rs.uniform(0.1, 0.8))
for k in range(9):
    flaps(49.2 + k * 0.6 + 0.9, 49.2 + k * 0.6 + 1.7, 6, 0.08, rs.uniform(-0.6, 0.6))

# ---------------------------------------------------------------- 時刻が切り替わる合図（タイマーの「ピピピー」）
def timer_beep():
    """デジタルタイマーの電子音：ピ・ピ・ピー"""
    parts = []
    for dur, gap in [(0.07, 0.06), (0.07, 0.06), (0.32, 0.0)]:
        n = int(dur * SR)
        t = np.arange(n) / SR
        ph = 2 * np.pi * 2900 * t
        y = np.sign(np.sin(ph)) * 0.35 + np.sin(ph) * 0.65  # 角ばった電子音
        y = lp(y, 7000)
        y *= np.minimum(1, t / 0.004) * np.minimum(1, (dur - t) / 0.01)
        parts += [y, np.zeros(int(gap * SR))]
    return np.concatenate(parts)


BEEP = timer_beep()
for sh in TL["shots"]:
    if sh.get("time"):
        add(BEEP, sh["start"] + 0.12, 0.2, 0.0)


# ---------------------------------------------------------------- C6：夕方の群れ
for k in range(26):
    tt = 55.1 + rs.uniform(0, 4.6)
    caw_series(tt, rs.integers(1, 4), rs.uniform(450, 600), 0.45, rs.uniform(0.05, 0.2), rs.uniform(-0.8, 0.8), dist=rs.uniform(0.2, 0.9))
for k in range(2):
    flaps(55 + k * 2.4, 55 + k * 2.4 + 1.0, 4.2, 0.22)

# ---------------------------------------------------------------- BGM（静かなパッド）
def pad(freqs, dur, gain):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f in freqs:
        for d in (-0.15, 0.0, 0.15):
            ff = f * 2 ** (d / 12)
            y += (2 * ((ff * t) % 1) - 1) * 0.3 + np.sin(2 * np.pi * ff * t)
    y = lp(y, 1100)
    a = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.2)
    return y / (np.abs(y).max() + 1e-9) * a * gain


hz = lambda m: 440 * 2 ** ((m - 69) / 12)
chords = [[50, 57, 60, 64, 69], [46, 53, 57, 62, 65], [43, 50, 53, 58, 62], [45, 52, 57, 61, 64]]
bgm = np.zeros(N)
for i, start in enumerate(np.arange(0, DUR, 4.75)):
    c = chords[i % 4]
    seg = pad([hz(m) for m in c], 5.6, 1.0)
    i0 = int(start * SR)
    bgm[i0 : i0 + len(seg)] += seg[: N - i0]
# 地図カードでは柔らかいアルペジオ
for k, tt in enumerate(np.arange(60.2, 67.6, 0.3)):
    m = [62, 65, 69, 72, 74, 72, 69, 65][k % 8]
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * hz(m) * t) * np.exp(-t * 6) + 0.3 * np.sin(4 * np.pi * hz(m) * t) * np.exp(-t * 9)
    i0 = int(tt * SR)
    bgm[i0 : i0 + n] += y[: N - i0] * 0.25
bgm = wet(bgm, 0.4)[:N]
add(bgm * env([(0, 0), (1, 0.05), (59.5, 0.05), (60.3, 0.16), (67, 0.16), (68, 0)]), 0, 1.0)

# ---------------------------------------------------------------- 書き出し
mix = np.stack([L, R], axis=1)
mix *= env([(0, 0), (0.3, 1), (DUR - 0.6, 1), (DUR, 0)])[:, None]
mix = np.tanh(mix * 1.6) / 1.6
mix /= np.abs(mix).max() / 0.89
out = sys.argv[1] if len(sys.argv) > 1 else "ep01_audio.wav"
import wave

with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("wrote", out, f"{DUR}s")
