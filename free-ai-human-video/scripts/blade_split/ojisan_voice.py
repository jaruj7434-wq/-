"""増殖した瞬間に流す、おじさんの英語の声(フルーツの名前)。
元の声は Higgs Field の Seed Audio 1.0(男性プリセット Grady)で、日本語の発音ではっきり言わせた6本
(assets/source/ojisan_fruit/voice/v0〜v5.wav・git 管理外。番号は ojisan.NAMES と同じ:りんご・オレンジ・レモン・いちご・もも・スイカ)。
ここで、前後の無音を切る → 少し低く・ゆっくりにする → 強いビブラート(声をふるわせる)をかける。
"""
import os
import wave

import numpy as np

VOICE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "source", "ojisan_fruit", "voice")
WORDS = ["アッポー!", "オーレンジ!", "レモーン!", "ストロベリー!", "ピーチ!", "ウォーターメローン!"]


def _load(k):
    with wave.open(os.path.join(VOICE_DIR, f"v{k}.wav")) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float).reshape(-1, ch).mean(1) / 32768
    e = np.sqrt(np.convolve(x ** 2, np.ones(240) / 240, "same"))
    on = np.where(e > 0.15 * e.max())[0]
    x = x[max(0, on[0] - int(0.02 * sr)): on[-1] + int(0.06 * sr)]
    return x, sr


def voice(k, sr_out, pitch=1.0, vib_hz=6.5, vib_depth=0.06):
    """k 番目のフルーツの声。言葉がはっきり聞こえるよう、少しだけ低く、ゆるいビブラートをかけるだけにする
    (pitch<1 で低く・ゆっくり、vib_depth はビブラートの深さ ±%)。"""
    x, sr = _load(k)
    n_out = int(len(x) / pitch * sr_out / sr)
    t = np.arange(n_out) / sr_out
    depth = vib_depth * np.minimum(1, t / 0.2)   # 言葉の出だしははっきり、語尾をふるわせる
    rate = pitch * (1 + depth * np.sin(2 * np.pi * vib_hz * t))
    pos = np.clip(np.cumsum(rate) * sr / sr_out, 0, len(x) - 2)
    y = np.interp(pos, np.arange(len(x)), x)
    y = np.tanh(1.3 * y / max(1e-9, np.abs(y).max())) / np.tanh(1.3)
    fade = np.ones(len(y))
    m = int(0.03 * sr_out)
    fade[-m:] = np.linspace(1, 0, m)
    return y * fade
