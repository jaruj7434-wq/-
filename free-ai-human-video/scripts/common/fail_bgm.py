"""失敗して幽霊が出たあとに流す、しょんぼりしたBGM(プログラムで作った音・無料)。

fail_music(sr, dur) … 「ワッ・ワッ・ワッ・ワ〜ン」と下がっていく残念なトランペット(ミュート風)+ 暗いピアノの和音。
"""
import numpy as np


def _tone(f, dur, sr, amp, vib=0.0, bright=6):
    t = np.arange(int(dur * sr)) / sr
    ph = 2 * np.pi * np.cumsum(f * (1 + vib * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.3))) / sr
    y = sum(np.sin(ph * h) / h ** 0.8 * (0.85 ** h) for h in range(1, bright + 1))
    env = np.minimum(1, t / 0.03) * np.minimum(1, (dur - t) / 0.08)
    return amp * y * env


def _wah(f, dur, sr, amp, vib=0.0):
    """ミュートをつけたトランペットの「ワ〜」(音の明るさがゆっくり変わる)。"""
    t = np.arange(int(dur * sr)) / sr
    dark = _tone(f, dur, sr, 1.0, vib, 2)
    bright = _tone(f, dur, sr, 1.0, vib, 7)
    k = 0.5 - 0.5 * np.cos(2 * np.pi * np.minimum(t / 0.45, 1) * 0.5)
    return amp * (dark * (1 - k) + bright * k)


def _piano(f, dur, sr, amp):
    t = np.arange(int(dur * sr)) / sr
    y = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * d) for m, a, d in ((1, 1, 1.6), (2, 0.4, 3), (3, 0.15, 5)))
    return amp * y * np.minimum(1, t / 0.005)


def fail_music(sr, dur=4.0):
    out = np.zeros(int(dur * sr) + sr)

    def put(sig, t0):
        i = int(t0 * sr)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]
    hz = lambda m: 440.0 * 2 ** ((m - 69) / 12)   # noqa: E731
    # ワッ・ワッ・ワッ・ワ〜ン(B♭ → A → A♭ → G)
    for k, (m, d) in enumerate(((58, 0.42), (57, 0.42), (56, 0.42), (55, 1.6))):
        put(_wah(hz(m), d, sr, 0.5, vib=0.012 if k == 3 else 0.0), 0.15 + k * 0.48)
    # 暗いピアノの和音(ト短調 → 下がっていく)
    for t0, chord in ((0.15, (43, 50, 55, 58)), (1.6, (41, 48, 53, 56)), (2.4, (43, 50, 55, 58))):
        for m in chord:
            put(_piano(hz(m), 1.8, sr, 0.18), t0)
    out = out[: int(dur * sr)]
    fade = np.minimum(1, (dur - np.arange(len(out)) / sr) / 0.6)
    return out * np.clip(fade, 0, 1)
