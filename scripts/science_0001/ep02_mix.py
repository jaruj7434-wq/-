"""第2話の音: 効果音(合成) + ナレーション + BGM(第1話と同じ曲)。

  python3 scripts/science_0001/ep02_explainer.py
  python3 scripts/science_0001/ep02_mix.py   # → assets/output/science_0001/ep02.mp4
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from ep01_edit import SR, _lowpass, _noise, write_wav  # noqa: E402
from ep02_explainer import END_CHIPS, END_T, timeline  # noqa: E402

SRC = Path("assets/source/science_0001/ep02")
BGM = Path("assets/source/science_0001/ep01_bgm.mp3")
OUT = Path("assets/output/science_0001")
SFX_VOL, BGM_VOL, NA_VOL = 0.55, 0.13, 1.6

NARRATION = [
    (0, "hook_pause", 0.3),  # 揉んだこの一瞬、脳では何が起きてる？
    (1, "s1", 0.2),          # 指先には、触れたことを感じるセンサーがぎっしり。…
    (2, "s2", 0.2),          # その信号は、腕の神経を一気に駆け上がり、約0.02秒で脳に届きます。
    (3, "s3", 0.2),          # 届く先は、脳の中の、体の地図。…手がとても大きく…
    (4, "question", 0.3),    # でも実は、自分で揉んだときだけ、…
    (5, "s4", 0.5),          # 小脳が、これは自分の手だと先読みして、感じ方を約半分に…
    (6, "s4_pause", 2.8),    # 自分をくすぐっても、くすぐったくないのは、このしくみのせい。
    (7, "ending", 2.6),      # 次は、どんな一瞬をのぞいてみたい？コメントで教えてください。
]


def mx(*arrs):
    out = np.zeros(max(len(a) for a in arrs))
    for a in arrs:
        out[: len(a)] += a
    return out


def env(n, tau):
    return np.exp(-np.arange(n) / SR / tau)


def tone(f, d, tau, amp=0.5):
    n = int(d * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t) * env(n, tau) * amp


def sweep(f0, f1, d, amp=0.3):
    n = int(d * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * d))) * np.sin(np.pi * t / d) * amp


def build_sfx(tl):
    rng = np.random.default_rng(1)
    total = tl["total"]
    out = np.zeros(int((total + 1) * SR))

    def put(sig, t):
        i = int(t * SR)
        out[i:i + len(sig)] += sig[: max(0, len(out) - i)]

    def noise(d, a=0.5):
        return _lowpass(_noise(int(d * SR), rng), a)

    def squish(d=0.9, amp=0.5):  # むにゅっ: こもったノイズ + 下がる低音
        n = int(d * SR)
        e = np.sin(np.pi * np.arange(n) / n) ** 1.5
        return mx(noise(d, 0.05) * e * amp * 2.0, sweep(160, 90, d, amp * 0.5))

    def tick():
        return mx(tone(1800, 0.2, 0.012, 0.6), noise(0.3, 0.5) * env(int(0.3 * SR), 0.06) * 0.2)

    def swish():
        n = int(0.25 * SR)
        return mx(noise(0.25, 0.6) * np.sin(np.pi * np.arange(n) / n) * 0.25, tone(1200, 0.12, 0.03, 0.15))

    def heading():
        return np.r_[tone(784, 0.12, 0.08, 0.3), tone(1175, 0.35, 0.12, 0.3)]

    # 冒頭: むにゅっ → 戻る「ふわっ」 → 巻き戻し → スロー
    put(squish(1.4, 0.6), tl["open"] + 0.1)
    put(sweep(200, 420, 0.8, 0.12), tl["open"] + 2.7)
    rw = tl["slow"] - tl["rewind"]
    n = int(rw * SR)
    put(_lowpass(_noise(n, rng), 0.25) * (np.arange(n) / n) ** 2 * 0.45, tl["rewind"])
    put(sweep(160, 60, 1.2, 0.35), tl["slow"])
    put(squish(2.4, 0.35), tl["slow"] + 0.1)
    put(tick(), tl["hook_pause"])
    # 指先: センサーがパチパチ光る
    s1 = tl["s1"]
    put(heading(), s1)
    put(squish(1.2, 0.35), s1 + 0.8)
    for c in rng.uniform(2.0, 4.8, 30):
        put(tone(rng.uniform(1800, 3200), 0.06, 0.015, 0.15), s1 + c)
    put(swish(), s1 + 2.6)
    put(tick(), tl["s1_pause"])
    # 神経: 電気がビューンと駆け上がる + タイマー
    s2 = tl["s2"]
    put(heading(), s2)
    put(mx(sweep(300, 1600, 4.0, 0.18), _lowpass(_noise(int(4.0 * SR), rng), 0.6) * 0.06), s2 + 0.8)
    for k in np.arange(0.8, 4.8, 0.2):
        put(tone(3000, 0.03, 0.005, 0.15), s2 + k)
    put(mx(tone(1568, 1.0, 0.3, 0.3), tone(2093, 1.0, 0.25, 0.15)), s2 + 4.8)  # 脳に到着
    put(tick(), tl["s2_pause"])
    # 脳の地図
    s3 = tl["s3"]
    put(heading(), s3)
    put(swish(), s3 + 1.0)
    p3 = tl["s3_pause"]
    put(tick(), p3)
    for i in range(4):
        put(tone(660 + 110 * i, 0.25, 0.06, 0.25), p3 + 0.4 + 0.35 * i)
    put(mx(tone(523, 0.6, 0.2, 0.2), tone(784, 0.6, 0.2, 0.15)), p3 + 1.6)
    # 問いかけ: ふっと間をとる
    put(sweep(500, 380, 0.8, 0.15), tl["question"] + 0.2)
    # 小脳: 青い波で感覚が弱まる「ヒュウン」 + メーター
    s4 = tl["s4"]
    put(heading(), s4)
    put(swish(), s4 + 1.0)
    put(swish(), s4 + 2.2)
    put(sweep(900, 300, 1.4, 0.18), s4 + 2.0)
    put(tone(700, 0.3, 0.1, 0.25), s4 + 4.8)
    put(tone(500, 0.3, 0.1, 0.25), s4 + 5.6)
    put(tick(), tl["s4_pause"])
    put(mx(tone(880, 0.8, 0.25, 0.2), tone(1320, 0.8, 0.25, 0.12)), tl["s4_pause"] + 2.8)
    # エンディング
    en = tl["ending"]
    put(mx(tone(523, 1.5, 0.5, 0.15), tone(784, 1.5, 0.5, 0.1)), en + END_T["punch"])
    put(mx(tone(659, 1.2, 0.4, 0.15), tone(988, 1.2, 0.4, 0.1)), en + END_T["ask"])
    for i in range(len(END_CHIPS)):
        put(tone(1047 + 131 * i, 0.4, 0.12, 0.12), en + END_T["chips"] + 0.45 * i)
    put(sum(tone(f, 2.0, 0.6, 0.08) for f in (1047, 1319, 1568)), en + END_T["cta"])
    return out[: int(total * SR)] / (np.abs(out).max() / 0.8)


def main():
    tl = timeline()
    total = tl["total"]
    wav = OUT / "ep02_sfx.wav"
    write_wav(wav, build_sfx(tl))
    inputs = ["-i", str(OUT / "ep02_video.mp4"), "-i", str(wav)]
    fc, mix = [f"[1:a]volume={SFX_VOL}[sfx]"], ["[sfx]"]
    idx = 2
    for n, tag, off in NARRATION:
        inputs += ["-i", str(SRC / f"na{n}.mp3")]
        d = int((tl[tag] + off) * 1000)
        fc.append(f"[{idx}:a]volume={NA_VOL},adelay={d}|{d}[n{idx}]")
        mix.append(f"[n{idx}]")
        idx += 1
    inputs += ["-i", str(BGM), "-i", str(BGM), "-i", str(BGM)]
    fc.append(f"[{idx}:a][{idx + 1}:a]acrossfade=d=3[b01];[b01][{idx + 2}:a]acrossfade=d=3,atrim=0:{total},"
              f"volume={BGM_VOL},afade=t=in:d=0.5,afade=t=out:st={total - 2}:d=2[bgm]")
    mix.append("[bgm]")
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{total},"
              "alimiter=limit=0.95[a]")
    out = OUT / "ep02.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out)],
                   check=True)
    print(f"wrote {out} ({total:.1f}s)")


if __name__ == "__main__":
    main()
