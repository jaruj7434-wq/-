"""増殖した瞬間に流す、おじさんの英語の声(フルーツの名前)。
元の声は Higgs Field の Seed Audio 1.0(男性プリセット Grady)で作った6本
(assets/source/ojisan_fruit/voice/v0〜v5.wav・git 管理外。番号は ojisan.NAMES と同じ:りんご・オレンジ・レモン・いちご・もも・スイカ)。
ここで、前後の無音を切る → 少し低く・ゆっくりにする → 強いビブラート(声をふるわせる)をかける。
"""
import os
import wave

import numpy as np

VOICE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "source", "ojisan_fruit", "voice")
WORDS = ["Apple!", "Orange!", "Lemon!", "Strawberry!", "Peach!", "Watermelon!"]


def _load(k):
    with wave.open(os.path.join(VOICE_DIR, f"v{k}.wav")) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float).reshape(-1, ch).mean(1) / 32768
    e = np.sqrt(np.convolve(x ** 2, np.ones(240) / 240, "same"))
    on = np.where(e > 0.08 * e.max())[0]
    x = x[max(0, on[0] - int(0.02 * sr)): on[-1] + int(0.06 * sr)]
    return x, sr


def voice(k, sr_out, pitch=0.74, vib_hz=8.5, vib_depth=0.2):
    """k 番目のフルーツの声。pitch<1 で低く・ゆっくり、vib_depth はビブラートの深さ(音の高さのゆれ ±%)。"""
    x, sr = _load(k)
    n_out = int(len(x) / pitch * sr_out / sr)
    t = np.arange(n_out) / sr_out
    # 読み出し位置をゆらして、音の高さを周期的に上下させる(ビブラート)。最初は小さく、だんだん深く
    depth = vib_depth * np.minimum(1, t / 0.15)
    rate = pitch * (1 + depth * np.sin(2 * np.pi * vib_hz * t))
    pos = np.cumsum(rate) * sr / sr_out
    pos = np.clip(pos, 0, len(x) - 2)
    y = np.interp(pos, np.arange(len(x)), x)
    # 変な声に:ゆらぎ方の違う「もう1人のおじさん」を少し高い声で重ね、ガラガラした感じ(ひずみ)を足す
    rate2 = pitch * 1.12 * (1 + depth * 0.8 * np.sin(2 * np.pi * vib_hz * 0.73 * t + 1.3))
    pos2 = np.clip(np.cumsum(rate2) * sr / sr_out, 0, len(x) - 2)
    y = y + 0.45 * np.interp(pos2, np.arange(len(x)), x)
    y = y * (1 + 0.25 * np.sin(2 * np.pi * 31 * t))   # ぶるぶる震える
    y = np.tanh(2.6 * y / max(1e-9, np.abs(y).max())) / np.tanh(2.6)
    fade = np.ones(len(y))
    m = int(0.03 * sr_out)
    fade[-m:] = np.linspace(1, 0, m)
    return y * fade
