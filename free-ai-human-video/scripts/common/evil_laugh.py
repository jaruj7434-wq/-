"""悪い笑い声(「ムフフ…ハッハッハ!」)をプログラムで合成する(録音・音声合成ソフトは使わないオリジナル)。

声の作り方(フォルマント合成):
- 声帯の音:ふるえの速さ(声の高さ f0)の三角っぽいパルス列。少しのゆらぎ(ジッター)を入れて人の声らしく。
- 口の形:母音ごとの共鳴(フォルマント)を2次のフィルターで重ねる。「ア」は 730/1090/2440Hz、「ウ」は 300/870/2240Hz。
  悪役らしく体が大きく聞こえるよう、共鳴を少し低くずらす。
- 「ハ」の息:ノイズを口の共鳴に通して、母音の前に短く入れる。
- 1オクターブ下の声をうすく重ね、少しだけ歪ませて、こだまをかける(低くて不気味に)。

使い方:
    from evil_laugh import evil_laugh
    y = evil_laugh(level, sr)   # level が大きいほど長く・低く・こわい(0〜6)
"""

import numpy as np
from scipy.signal import lfilter

_CACHE = {}


def _reson(x, f, bw, sr):
    """2次の共鳴フィルター(フォルマント1つ)。"""
    r = np.exp(-np.pi * bw / sr)
    th = 2 * np.pi * f / sr
    a = [1.0, -2 * r * np.cos(th), r * r]
    b = [1 - r]
    return lfilter(b, a, x)


def _formants(src, vowel, sr, shift):
    fs = {"a": ((730, 90, 1.0), (1090, 110, 0.6), (2440, 170, 0.25), (3400, 250, 0.12)),
          "u": ((300, 70, 1.0), (870, 100, 0.45), (2240, 160, 0.15), (3300, 250, 0.06)),
          "e": ((530, 80, 1.0), (1840, 120, 0.5), (2480, 170, 0.25), (3400, 250, 0.1))}[vowel]
    y = np.zeros_like(src)
    for f, bw, g in fs:
        y += g * _reson(src, f * shift, bw, sr)
    return y


def _glottal(f0, sr, rng):
    """声帯の音:f0(時間ごとの声の高さの列)にそったパルス列。"""
    f = f0 * (1 + 0.012 * rng.standard_normal(len(f0)))          # ゆらぎ
    ph = np.cumsum(f) / sr
    fr = ph % 1.0
    pulse = np.where(fr < 0.6, np.sin(np.pi * fr / 0.6) ** 2, 0.0)  # ひらいて閉じる
    d = np.diff(pulse, prepend=0.0)                                # 声のかたさ(微分)
    return d


def _syllable(sr, rng, vowel, dur, f0a, f0b, h_dur, shift, amp):
    n = int(dur * sr)
    t = np.arange(n) / sr
    f0 = f0a + (f0b - f0a) * (t / dur) ** 0.7
    src = _glottal(f0, sr, rng) + 0.5 * _glottal(f0 / 2, sr, rng)   # 1オクターブ下をうすく重ねる
    env = np.minimum(1, t / 0.015) * np.minimum(1, (dur - t) / 0.05) ** 1.5
    voice = _formants(src, vowel, sr, shift) * env
    nh = int(h_dur * sr)
    if nh:
        th = np.arange(nh) / sr
        noise = rng.standard_normal(nh)
        h = _formants(noise, vowel, sr, shift) * np.minimum(1, th / 0.01) * (0.5 + 0.5 * th / h_dur)
        h = 0.25 * h / (np.abs(h).max() + 1e-9)
        v = voice / (np.abs(voice).max() + 1e-9)
        out = np.concatenate([h, v])
        out[nh:nh + int(0.02 * sr)] += 0   # 息から声へつながる
    else:
        out = voice / (np.abs(voice).max() + 1e-9)
    return amp * out


def evil_laugh(level, sr, seed=7):
    """level 0〜6:大きいほど長く・低く・こわい笑い。"""
    key = (level, sr, seed)
    if key in _CACHE:
        return _CACHE[key]
    rng = np.random.default_rng(seed + level)
    shift = 0.92 - 0.02 * level          # 共鳴を低くずらす(体が大きく聞こえる)
    base = 118 - 6 * level               # 声の高さ(Hz)
    n_ha = [2, 3, 3, 4, 5, 6, 8][level]
    parts = []
    if level >= 2:                       # 「ムフッ…」の前ぶれ
        parts.append(_syllable(sr, rng, "u", 0.28 + 0.04 * level, base * 0.8, base * 1.05, 0.0, shift, 0.75))
        parts.append(np.zeros(int(0.06 * sr)))
    for k in range(n_ha):                # 「ハッ ハッ ハッ…」だんだん低く
        last = k == n_ha - 1
        f0 = base * (1.25 - 0.35 * k / max(1, n_ha - 1))
        dur = (0.22 + 0.05 * level) if last else 0.11
        parts.append(_syllable(sr, rng, "a", dur, f0 * 1.04, f0 * (0.85 if last else 0.96), 0.045, shift,
                               1.0 if k == 0 else 0.85))
        parts.append(np.zeros(int((0.05 if not last else 0.0) * sr)))
    y = np.concatenate(parts)
    y = np.tanh(2.2 * y / (np.abs(y).max() + 1e-9)) / np.tanh(2.2)   # 少し歪ませて太く
    for d, g in ((0.09, 0.32), (0.17, 0.2), (0.29, 0.12), (0.43, 0.07)):   # 洞くつのようなこだま
        m = int(d * sr)
        y = np.concatenate([y, np.zeros(m)])
        y[m:] += g * y[:-m]
    y = y / (np.abs(y).max() + 1e-9)
    _CACHE[key] = y
    return y
