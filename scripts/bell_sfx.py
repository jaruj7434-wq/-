"""激しく連打される鐘の効果音を合成する(numpy のみ)。

参考動画「中さんの鐘鳴らし」の解析値を使う:
- 打撃テンポ 約3回/秒、間隔 0.13〜0.55 秒の不規則な連打(舌が左右に当たる二度打ちを含む)
- 主な倍音 約 560 / 930 / 1420 / 2210 / 3170 Hz
使い方: python3 scripts/bell_sfx.py <出力.wav> <秒数> [seed]
"""
import sys
import wave
import numpy as np

SR = 44100
PARTIALS = [(560, 1.0, 1.6), (930, 0.8, 1.2), (1420, 0.55, 0.9),
            (2210, 0.4, 0.6), (3170, 0.3, 0.4), (4350, 0.15, 0.25)]
# 参考動画から検出した打撃間隔(秒)
REF_INTERVALS = [0.17, 0.38, 0.47, 0.19, 0.13, 0.33, 0.23, 0.48, 0.46, 0.27,
                 0.26, 0.26, 0.20, 0.13, 0.17, 0.24, 0.19, 0.37, 0.55, 0.51]


def strike(rng, strength):
    n = int(SR * 2.0)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f, amp, decay in PARTIALS:
        f2 = f * (1 + rng.uniform(-0.012, 0.012))  # 鐘の揺れによる音程の揺らぎ
        beat = 1 + 0.15 * np.sin(2 * np.pi * rng.uniform(2, 5) * t)
        out += amp * beat * np.sin(2 * np.pi * f2 * t + rng.uniform(0, 6.28)) * np.exp(-t / decay)
    # ガシャンという金属の打撃ノイズ(高域の短いバースト)
    noise = rng.standard_normal(n)
    noise = noise - np.convolve(noise, np.ones(8) / 8, mode="same")
    out += 1.6 * noise * np.exp(-t / 0.035)
    # 舌の跳ね返りによる小さな二打目
    off = int(SR * rng.uniform(0.02, 0.05))
    out[off:] += 0.35 * (noise[:-off] * np.exp(-t[:-off] / 0.02))
    return out * strength


def render(seconds, seed=0):
    rng = np.random.default_rng(seed)
    n = int(SR * (seconds + 2.0))
    mix = np.zeros(n)
    pos, i = 0.05, 0
    while pos < seconds:
        s = strike(rng, rng.uniform(0.7, 1.0))
        a = int(pos * SR)
        mix[a:a + len(s)] += s[: n - a]
        pos += REF_INTERVALS[i % len(REF_INTERVALS)] * rng.uniform(0.85, 1.1)
        i += 1
    # 屋外の軽い残響
    for d, g in [(0.043, 0.25), (0.071, 0.18), (0.113, 0.12)]:
        k = int(d * SR)
        mix[k:] += g * mix[:-k]
    mix = np.tanh(mix * 0.3)  # 少し歪ませて荒々しく
    mix = mix[: int(SR * seconds)]
    fade = int(0.3 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return mix / np.max(np.abs(mix)) * 0.89


def main():
    path, seconds = sys.argv[1], float(sys.argv[2])
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    data = (render(seconds, seed) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


if __name__ == "__main__":
    main()
