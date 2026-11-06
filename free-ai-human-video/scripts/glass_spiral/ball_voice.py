"""ボールが落ちてくる瞬間の掛け声と効果音。

掛け声: Higgs Field の Seed Audio 1.0(男性プリセット「Knox」)で作った6本
        (assets/source/glass_spiral/voice/v0.wav〜v5.wav・git 管理外)。
        スーパーボール! / ウッド! / アイアン!! / ファイアー!! / サンダー!! / メテオ!!!
効果音: すべてこのファイルの中で合成する(弾む音・木の音・金属音・炎・電気・地響き)。
"""
import os
import wave

import numpy as np

VOICE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "source", "glass_spiral", "voice")
LINES = ["スーパーボール!", "ウッド!", "アイアン!!", "ファイアー!!", "サンダー!!", "メテオ!!!"]


def _load_voice(k, sr):
    with wave.open(os.path.join(VOICE_DIR, f"v{k}.wav")) as w:
        src_sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float).reshape(-1, ch).mean(1) / 32768
    # 前後の無音を切る
    e = np.sqrt(np.convolve(x ** 2, np.ones(480) / 480, "same"))
    on = np.where(e > 0.08 * e.max())[0]
    x = x[max(0, on[0] - int(0.02 * src_sr)): on[-1] + int(0.08 * src_sr)]
    # 48kHz へ
    n = int(len(x) * sr / src_sr)
    x = np.interp(np.arange(n) * src_sr / sr, np.arange(len(x)), x)
    # 叫び声らしく: 強めに圧縮して少しひずませ、短いこだまを足す
    x = x / max(1e-9, np.abs(x).max())
    x = np.tanh(2.2 * x) / np.tanh(2.2)
    d = int(0.085 * sr)
    y = np.concatenate([x, np.zeros(2 * d)])
    y[d:d + len(x)] += 0.28 * x
    y[2 * d:2 * d + len(x)] += 0.12 * x
    fade = np.ones(len(y))
    fade[-int(0.03 * sr):] = np.linspace(1, 0, int(0.03 * sr))
    return y * fade


def _t(dur, sr):
    return np.arange(int(dur * sr)) / sr


def _lp(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


def _sfx(k, sr, rng):
    if k == 0:   # スーパーボール: びよよーんと弾む
        t = _t(0.9, sr)
        f = 180 + 220 * np.abs(np.sin(2 * np.pi * 2.2 * t)) * np.exp(-t * 1.5) + 80 * t
        y = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 3)
        return 0.55 * y * np.minimum(1, t / 0.005)
    if k == 1:   # 木の玉: コーン、コン
        y = np.zeros(int(0.7 * sr))
        for t0, a in ((0.0, 1.0), (0.22, 0.5)):
            t = _t(0.4, sr)
            s = (np.sin(2 * np.pi * 520 * t) + 0.6 * np.sin(2 * np.pi * 1180 * t) * np.exp(-t * 20)) * np.exp(-t * 22)
            s += _lp(rng.normal(0, 1, len(t)), 3) * np.exp(-t * 200) * 0.5
            i = int(t0 * sr)
            y[i:i + len(s)] += a * s[: len(y) - i]
        return 0.55 * y
    if k == 2:   # 鉄球: 重いガキーン
        t = _t(1.6, sr)
        y = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d)
                for f, a, d in ((210, 1.0, 2.2), (563, 0.7, 3.0), (1102, 0.5, 4.5), (1790, 0.35, 6), (2620, 0.25, 9)))
        y += rng.normal(0, 1, len(t)) * np.exp(-t * 60) * 0.8
        return 0.40 * y
    if k == 3:   # 火の玉: ゴォッと燃え上がる + パチパチ
        t = _t(1.3, sr)
        n = rng.normal(0, 1, len(t))
        env = np.minimum(1, t / 0.18) * np.exp(-np.maximum(0, t - 0.18) * 2.8)
        y = (_lp(n, 18) * 2.2 + _lp(n, 5) * 0.5) * env
        for _ in range(28):   # 火の粉がはぜる音
            i = int(rng.uniform(0.05, 1.1) * sr)
            m = int(0.006 * sr)
            y[i:i + m] += rng.normal(0, 1, m) * np.exp(-np.arange(m) / (0.0015 * sr)) * rng.uniform(0.3, 0.9)
        return 0.55 * y / np.abs(y).max()
    if k == 4:   # 雷の玉: バリバリッ + ジジジという電磁音
        t = _t(1.4, sr)
        buzz = np.sign(np.sin(2 * np.pi * 120 * t)) * 0.5 + np.sin(2 * np.pi * 360 * t) * 0.3
        buzz *= 0.5 + 0.5 * (rng.random(len(t)) < 0.6).astype(float)   # ちらつく
        buzz = _lp(buzz, 4) * np.exp(-t * 1.6) * 0.6
        crack = np.zeros(len(t))
        tt = 0.0
        while tt < 0.7:   # 放電の「バリッ」が何回も
            i = int(tt * sr)
            m = int(rng.uniform(0.01, 0.05) * sr)
            crack[i:i + m] += rng.normal(0, 1, m) * np.exp(-np.arange(m) / (0.012 * sr))
            tt += rng.uniform(0.02, 0.09)
        crack -= _lp(crack, 6)   # 高い音だけ残す
        y = buzz + crack * 1.4 * np.exp(-t * 2)
        return 0.5 * y / np.abs(y).max()
    # 隕石: 地響きのような低い轟音
    t = _t(2.0, sr)
    n = rng.normal(0, 1, len(t))
    rumble = _lp(_lp(n, 60), 40)
    rumble /= np.abs(rumble).max()
    env = np.minimum(1, t / 0.25) * np.exp(-np.maximum(0, t - 0.25) * 1.6)
    boom = np.sin(2 * np.pi * np.cumsum(38 + 40 * np.exp(-t * 6)) / sr) * np.exp(-t * 2.2)
    y = rumble * env * 0.9 + boom * 0.8 + _lp(n, 8) * env * 0.12
    return 0.6 * y / np.abs(y).max()


def drop_sounds(sr, seed=0):
    """ボールの種類ごとに (掛け声, 効果音) を返す。"""
    rng = np.random.default_rng(seed + 31)
    out = []
    for k in range(6):
        v, f = _load_voice(k, sr), _sfx(k, sr, rng)
        # どのボールでも同じくらいの大きさに聞こえるよう、鳴っている部分の平均の大きさをそろえる
        v = v / _rms(v) * 0.25
        f = f / _rms(f) * 0.12
        out.append((v, f))
    return out


def _rms(x):
    e = np.sqrt(np.convolve(x ** 2, np.ones(2400) / 2400, "same"))
    on = e > 0.1 * e.max()
    return max(1e-9, np.sqrt(np.mean(x[on] ** 2)))
