"""ダメージを受けたときの、おじさんの渋くて低い「おぅっ!」「ゔぅっ!」(無料のオープンソース音声合成 pyopenjtalk で作る)。

grunt(k, sr) … k 番目の声(いくつかの言い方を順番に使う)。声を低くして(ピッチを下げて)、少しだけ歪ませて太くする。
"""
import numpy as np

WORDS = ["おうっ", "ぐうっ", "うおっ", "ぬうっ", "ごふっ", "おおっ"]
_CACHE = {}


def _raw(word):
    import pyopenjtalk
    x, sr = pyopenjtalk.tts(word)
    x = x.astype(float)
    e = np.abs(x)
    idx = np.where(e > 0.05 * e.max())[0]
    x = x[max(0, idx[0] - 200): idx[-1] + 400]
    return x / (np.abs(x).max() + 1e-9), sr


def grunt(k, sr_out, low=0.72):
    """low < 1 で声が低く・太くなる(ゆっくり再生して低くする)。"""
    key = (k % len(WORDS), sr_out, low)
    if key in _CACHE:
        return _CACHE[key]
    x, sr = _raw(WORDS[k % len(WORDS)])
    # 低くする:サンプルを間引かずに引きのばす(ピッチも長さも下がる)
    n_out = int(len(x) / low * sr_out / sr)
    y = np.interp(np.linspace(0, len(x) - 1, n_out), np.arange(len(x)), x)
    # のどをしめたような太さ(軽い歪み)+ 低い胸の響き
    y = np.tanh(2.2 * y) / np.tanh(2.2)
    t = np.arange(len(y)) / sr_out
    env = np.convolve(np.abs(y), np.ones(400) / 400, "same")
    y = y + 0.35 * np.sin(2 * np.pi * 75 * t) * env
    # 頭を強く、おしりは短く
    y *= np.minimum(1, t / 0.01) * np.minimum(1, (t[-1] - t) / 0.06)
    y = y / (np.sqrt(np.mean(y ** 2)) + 1e-9) * 0.25
    _CACHE[key] = y
    return y
