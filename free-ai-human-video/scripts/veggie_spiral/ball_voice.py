"""刃物が落ちてくる瞬間の効果音(刃物版)。すべて合成で、掛け声は使わない。

刃を抜く「シャキン」。後の刃物ほど低く・長く・重くなり、日本刀は「シャキィィン」+低い「ブォン」。
"""
import numpy as np

LINES = ["バターナイフ", "ペティナイフ", "三徳包丁", "出刃包丁", "中華包丁", "日本刀"]


def _t(d, sr):
    return np.arange(int(d * sr)) / sr


def _lp(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


def _sfx(k, sr, rng):
    """刃を抜く「シャキン」(k が大きいほど低く長い)。"""
    dur = 0.45 + 0.18 * k
    t = _t(dur, sr)
    n = rng.normal(0, 1, len(t))
    scrape = (n - _lp(n, 2)) * np.exp(-((t - 0.06) / 0.05) ** 2) * 0.8    # 鞘をこする「シャッ」
    f0 = 2600 - 260 * k
    ring = sum(a * np.sin(2 * np.pi * f0 * m * t) * np.exp(-t * (6 - 0.6 * k) * m ** 0.5)
               for m, a in ((1.0, 1.0), (1.51, 0.5), (2.37, 0.3)))
    ring *= np.minimum(1, np.maximum(0, t - 0.05) / 0.005)                 # 抜けた瞬間に「キン」
    y = scrape + 0.5 * ring
    if k >= 4:   # 中華包丁・日本刀は空気を切る低い「ブォン」
        y += 0.5 * np.sin(2 * np.pi * np.cumsum(90 + 60 * np.sin(np.pi * t / dur)) / sr) * np.sin(np.pi * t / dur) ** 2
    return y


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
