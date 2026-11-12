"""第2話（作り直し・脳汁）の音: 効果音(合成) + ナレーション + BGM(第1話と同じ曲)。

  python3 scripts/science_0001/ep02b_mix.py   # → assets/output/science_0001/ep02b.mp4
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from ep01_edit import SR, _lowpass, _noise, write_wav  # noqa: E402
from ep02_mix import env, mx, sweep, tone  # noqa: E402
from ep02b_explainer import END_CHIPS, END_T, OUT, timeline  # noqa: E402

SRC = Path("assets/source/science_0001/ep02")
BGM = Path("assets/source/science_0001/ep01_bgm.mp3")
SFX_VOL, BGM_VOL, NA_VOL = 0.55, 0.13, 1.6

NARRATION = [
    ("na0", "hook_pause", 0.3),  # 揉んだこの一瞬、脳では何が起きてる？
    ("nb1", "signal", 0.3),      # 指先からの信号は、約0.02秒で脳に届きます。
    ("nb2", "reward", 0.3),      # 気持ちいい感触は、脳の、ごほうびに関わる場所を動かします。
    ("nb3", "dopa", 0.3),        # そして脳の奥から出るのが、いわゆる脳汁、ドーパミンです。
    ("nb4", "question", 0.3),    # でも実は、ドーパミンは、気持ちいいの物質ではありません。
    ("nb5", "punch", 0.4),       # 正体は、もっとほしいを生む物質。だから、つい、もう一回揉みたくなる、と考えられています。
    ("na7", "ending", 2.6),      # 次は、どんな一瞬をのぞいてみたい？コメントで教えてください。
]


def build_sfx(tl):
    rng = np.random.default_rng(2)
    total = tl["total"]
    out = np.zeros(int((total + 1) * SR))

    def put(sig, t):
        i = int(t * SR)
        out[i:i + len(sig)] += sig[: max(0, len(out) - i)]

    def noise(d, a=0.5):
        return _lowpass(_noise(int(d * SR), rng), a)

    def squish(d=0.9, amp=0.5):
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

    def sparkle(t0, n=12, spread=1.5, base=1800):
        for c in rng.uniform(0, spread, n):
            put(tone(rng.uniform(base, base * 1.8), 0.25, 0.08, 0.08), t0 + c)

    # 冒頭: むにゅっ → ふわっと戻る → 巻き戻し → スロー
    put(squish(1.0, 0.6), tl["open"] + 0.1)
    put(sweep(200, 420, 1.2, 0.12), tl["open"] + 1.3)
    rw = tl["slow"] - tl["rewind"]
    n = int(rw * SR)
    put(_lowpass(_noise(n, rng), 0.25) * (np.arange(n) / n) ** 2 * 0.45, tl["rewind"])
    put(sweep(160, 60, 1.2, 0.35), tl["slow"])
    put(squish(2.2, 0.35), tl["slow"] + 0.1)
    put(tick(), tl["hook_pause"])
    # 信号: ビューンと上がる + タイマーの刻み + 到着
    s = tl["signal"]
    put(heading(), s)
    put(mx(sweep(300, 1500, 2.3, 0.18), noise(2.3, 0.6) * 0.05), s + 0.3)
    for k in np.arange(0.3, 2.6, 0.15):
        put(tone(3000, 0.03, 0.005, 0.15), s + k)
    put(mx(tone(1568, 1.0, 0.3, 0.3), tone(2093, 1.0, 0.25, 0.15)), s + 2.6)
    # ごほうびエリアが光る: あたたかい和音
    r = tl["reward"]
    put(heading(), r)
    put(mx(tone(523, 2.0, 0.8, 0.12), tone(659, 2.0, 0.8, 0.1), tone(784, 2.0, 0.8, 0.08)), r + 0.6)
    put(swish(), r + 1.4)
    # 脳汁: キラキラが湧き出す
    dp = tl["dopa"]
    put(heading(), dp)
    put(swish(), dp + 1.0)
    sparkle(dp + 0.5, n=40, spread=3.5)
    put(mx(tone(880, 1.2, 0.4, 0.2), tone(1320, 1.2, 0.4, 0.12)), dp + 2.2)
    # 問いかけ / オチ
    put(sweep(500, 380, 0.8, 0.15), tl["question"] + 0.2)
    p = tl["punch"]
    put(tone(440, 0.4, 0.12, 0.2), p + 0.2)
    put(mx(tone(880, 0.6, 0.2, 0.22), tone(1320, 0.6, 0.2, 0.14)), p + 1.2)
    sparkle(p + 1.2, n=8, spread=0.8, base=2000)
    put(squish(0.8, 0.3), p + 4.4)
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
    wav = OUT / "ep02b_sfx.wav"
    write_wav(wav, build_sfx(tl))
    inputs = ["-i", str(OUT / "ep02b_video.mp4"), "-i", str(wav)]
    fc, mix = [f"[1:a]volume={SFX_VOL}[sfx]"], ["[sfx]"]
    idx = 2
    for n, tag, off in NARRATION:
        inputs += ["-i", str(SRC / f"{n}.mp3")]
        d = int((tl[tag] + off) * 1000)
        fc.append(f"[{idx}:a]volume={NA_VOL},adelay={d}|{d}[n{idx}]")
        mix.append(f"[n{idx}]")
        idx += 1
    inputs += ["-i", str(BGM), "-i", str(BGM)]
    fc.append(f"[{idx}:a][{idx + 1}:a]acrossfade=d=3,atrim=0:{total},"
              f"volume={BGM_VOL},afade=t=in:d=0.5,afade=t=out:st={total - 2}:d=2[bgm]")
    mix.append("[bgm]")
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{total},"
              "alimiter=limit=0.95[a]")
    out = OUT / "ep02b.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out)],
                   check=True)
    print(f"wrote {out} ({total:.1f}s)")


if __name__ == "__main__":
    main()
