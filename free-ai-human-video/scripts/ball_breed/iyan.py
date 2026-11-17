"""ボールが増えるときの、女性の短い声「いやーん」(無料のオープンソース音声合成 pyopenjtalk + 音声「Mei」で作る)。

音声「Mei」:HTS Voice "Mei" (c) 2009-2013 Nagoya Institute of Technology, MMDAgent Project Team / CC BY 3.0
iyan(k, sr, pitch) … k 番目の言い方(いくつかを順番に使う)。pitch で少し高さを変える(毎回ちがって聞こえるように)。
"""
import numpy as np

WORDS = [("いやーん", 4.0, 1.15), ("いやん", 5.0, 1.2), ("やーん", 4.0, 1.15), ("いやぁん", 5.0, 1.15)]
_RAW = {}
_CACHE = {}


def _raw(k):
    if k not in _RAW:
        import pyopenjtalk
        word, half, speed = WORDS[k]
        x, sr = pyopenjtalk.tts(word, half_tone=half, speed=speed)
        x = x.astype(float)
        e = np.abs(x)
        idx = np.where(e > 0.04 * e.max())[0]
        x = x[max(0, idx[0] - 150): idx[-1] + 300]
        _RAW[k] = (x / (np.abs(x).max() + 1e-9), sr)
    return _RAW[k]


def iyan(k, sr_out, pitch=1.0):
    """pitch > 1 で少し高く・短く(速く再生する)。"""
    k = k % len(WORDS)
    pitch = round(pitch, 2)
    key = (k, sr_out, pitch)
    if key in _CACHE:
        return _CACHE[key]
    x, sr = _raw(k)
    n_out = int(len(x) / pitch * sr_out / sr)
    y = np.interp(np.linspace(0, len(x) - 1, n_out), np.arange(len(x)), x)
    t = np.arange(len(y)) / sr_out
    y *= np.minimum(1, t / 0.008) * np.minimum(1, (t[-1] - t) / 0.08)
    y = y / (np.sqrt(np.mean(y ** 2)) + 1e-9) * 0.25
    _CACHE[key] = y
    return y
