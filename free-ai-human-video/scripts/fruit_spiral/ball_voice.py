"""ボールが落ちてくる瞬間の効果音(スポーツボール版)。すべて合成で、掛け声は使わない。

ピンポン玉=「カコン」 / テニスボール=「ポーン」 / 野球ボール=バットの「カキーン」 / サッカーボール=蹴る「ボスッ」
ボウリング球=転がる「ゴロゴロ…」+ピンの「ガコン」 / 鉄球=重い金属の「ゴォン」
"""
import numpy as np

LINES = ["ピンポン玉", "テニスボール", "野球ボール", "サッカーボール", "ボウリング球", "鉄球"]


def _t(d, sr):
    return np.arange(int(d * sr)) / sr


def _lp(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


def _sfx(k, sr, rng):
    if k == 0:   # ピンポン:「カコン」(高い短い2回)
        y = np.zeros(int(0.35 * sr))
        for t0, f, a in ((0.0, 2400, 1.0), (0.14, 2100, 0.7)):
            t = _t(0.08, sr)
            s = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.6 * t)) * np.exp(-t * 70)
            i = int(t0 * sr)
            y[i:i + len(s)] += a * s
        return 0.6 * y
    if k == 1:   # テニス:ラケットで打つ「ポーン」
        t = _t(0.35, sr)
        n = rng.normal(0, 1, len(t))
        s = np.sin(2 * np.pi * np.cumsum(520 - 200 * t) / sr) * np.exp(-t * 18) + 0.5 * _lp(n, 6) * np.exp(-t * 60)
        return 0.6 * s
    if k == 2:   # 野球:金属バットの「カキーン」
        t = _t(0.9, sr)
        s = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in ((1850, 1.0, 5), (2780, 0.6, 7), (4100, 0.35, 9)))
        n = rng.normal(0, 1, len(t))
        s += (n - _lp(n, 3)) * np.exp(-t * 90) * 0.8
        return 0.45 * s
    if k == 3:   # サッカー:蹴る「ボスッ」
        t = _t(0.3, sr)
        n = rng.normal(0, 1, len(t))
        s = np.sin(2 * np.pi * np.cumsum(140 + 160 * np.exp(-t * 30)) / sr) * np.exp(-t * 16) + 0.6 * _lp(n, 12) * np.exp(-t * 30)
        return 0.7 * s
    if k == 4:   # ボウリング:転がる「ゴロゴロ」+「ガコン」
        t = _t(1.1, sr)
        n = rng.normal(0, 1, len(t))
        roll = _lp(_lp(n, 40), 20) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t)) * np.minimum(1, t / 0.1) * np.exp(-t * 1.5)
        roll /= np.abs(roll).max()
        y = 0.6 * roll
        tt = _t(0.4, sr)
        clack = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * 25) for f in (620, 1150, 1760)) + rng.normal(0, 1, len(tt)) * np.exp(-tt * 60)
        i = int(0.55 * sr)
        y[i:i + len(tt)] += 0.5 * clack[: len(y) - i]
        return 0.7 * y
    t = _t(1.6, sr)   # 鉄球:重い金属の「ゴォン」
    s = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in ((110, 1.0, 2.0), (271, 0.6, 2.6), (512, 0.4, 3.5), (840, 0.25, 5)))
    n = rng.normal(0, 1, len(t))
    s += _lp(n, 6) * np.exp(-t * 40) * 0.7
    return 0.55 * s


def _rms(x):
    e = np.sqrt(np.convolve(x ** 2, np.ones(2400) / 2400, "same"))
    on = e > 0.1 * e.max()
    return max(1e-9, np.sqrt(np.mean(x[on] ** 2)))


def drop_sounds(sr, seed=0):
    """ボールの種類ごとに (掛け声=無音, 効果音) を返す(glass_spiral と同じ形)。"""
    rng = np.random.default_rng(seed + 31)
    out = []
    for k in range(6):
        f = _sfx(k, sr, rng)
        f = f / _rms(f) * 0.2
        out.append((np.zeros(1), f))
    return out
