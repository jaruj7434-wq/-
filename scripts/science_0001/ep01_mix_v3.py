"""第1話 解説強化版の音: 効果音(合成) + ナレーション + BGM を ep01_v3_video.mp4 に重ねる。

  python3 scripts/science_0001/ep01_explainer.py
  python3 scripts/science_0001/ep01_mix_v3.py
出力: assets/output/science_0001/ep01_v3.mp4
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from ep01_edit import SR, _lowpass, _noise, write_wav  # noqa: E402
from ep01_explainer import timeline  # noqa: E402

SRC = Path("assets/source/science_0001")
OUT = Path("assets/output/science_0001")
SFX_VOL, BGM_VOL, NA_VOL = 0.5, 0.15, 1.6

# (ナレーション番号, タイムラインのタグ, タグからの遅れ秒)
NARRATION = [
    (0, "hook_pause", 0.3),
    (1, "step1", 0.4),
    (2, "step2", 0.4),
    (3, "step3_pause", 0.4),
    (4, "step4_pause", 0.5),
    (5, "summary", 3.5),
]
EXTRA_NARRATION: list = []  # 追加ナレーション(ep01_na6.mp3〜)があればここに足す


def sfx(tl):
    total = tl["total"]
    rng = np.random.default_rng(0)
    out = np.zeros(int(total * SR) + SR)

    def put(sig, t):
        i = int(t * SR)
        out[i:i + len(sig)] += sig[: len(out) - i]

    def tick():  # 一時停止の「カチッ」+ 軽いシュッ
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 1800 * t) * np.exp(-t / 0.012) * 0.6
                + _lowpass(_noise(n, rng), 0.5) * np.exp(-t / 0.08) * 0.25)

    for tag in ("hook_pause", "step1_pause", "step2_pause", "step3_pause", "step4_pause"):
        put(tick(), tl[tag])
    # 冒頭の弾け
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    pop = (np.sin(2 * np.pi * 180 * t) * 0.9 + np.sin(2 * np.pi * 520 * t) * 0.4) * np.exp(-t / 0.06)
    pop += _noise(n, rng) * np.exp(-t / 0.01) * 0.8
    put(pop * 0.8, 1.1)
    # STEP2: 強くなるジュー音
    a, b = tl["step2"], tl["step2_pause"]
    n = int((b - a) * SR)
    t = np.arange(n) / SR
    put(np.diff(np.r_[0, _noise(n, rng)]) * 0.4 * (0.05 + 0.25 * (t / (b - a)) ** 2), a)
    # STEP3: ポン + シュー
    put(pop, tl["step3"] + 0.2)
    n = int(1.5 * SR)
    t = np.arange(n) / SR
    put(_lowpass(_noise(n, rng), 0.35) * np.exp(-t / 0.4) * 0.35, tl["step3"] + 0.25)
    # STEP4: 跳ぶヒュッ
    n = int(0.8 * SR)
    t = np.arange(n) / SR
    whoosh = np.sin(2 * np.pi * (300 + 900 * t) * t) * np.exp(-t / 0.25) * 0.2
    put(whoosh, tl["step4"] + 1.6)
    put(whoosh, tl["step4_pause"] + 5.0 + 0.3)
    # まとめ: 項目ごとのポン + 最後のチャイム
    for i in range(4):
        n = int(0.25 * SR)
        t = np.arange(n) / SR
        put(np.sin(2 * np.pi * (660 + 110 * i) * t) * np.exp(-t / 0.06) * 0.25, tl["summary"] + 0.5 + 0.6 * i)
    n = int(2.0 * SR)
    t = np.arange(n) / SR
    put(sum(np.sin(2 * np.pi * f * t) for f in (880, 1320, 1760)) * np.exp(-t / 0.5) * 0.12, tl["summary"] + 3.4)
    return out / (np.abs(out).max() / 0.8)


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True, check=True).stdout)


def main():
    tl = timeline()
    total = tl["total"]
    video = OUT / "ep01_v3_video.mp4"
    wav = OUT / "ep01_v3_sfx.wav"
    write_wav(wav, sfx(tl))
    inputs = ["-i", str(video), "-i", str(wav)]
    fc, mix = [f"[1:a]volume={SFX_VOL}[sfx]"], ["[sfx]"]
    idx = 2
    for n, tag, off in NARRATION + EXTRA_NARRATION:
        inputs += ["-i", str(SRC / f"ep01_na{n}.mp3")]
        d = int((tl[tag] + off) * 1000)
        fc.append(f"[{idx}:a]volume={NA_VOL},adelay={d}|{d}[n{n}]")
        mix.append(f"[n{n}]")
        idx += 1
    # BGM(30秒)をクロスフェードでつないで尺に合わせる
    bgm = SRC / "ep01_bgm.mp3"
    inputs += ["-i", str(bgm), "-i", str(bgm)]
    fc.append(f"[{idx}:a][{idx + 1}:a]acrossfade=d=3,atrim=0:{total},volume={BGM_VOL},"
              f"afade=t=in:d=0.5,afade=t=out:st={total - 2}:d=2[bgm]")
    mix.append("[bgm]")
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{total},"
              "alimiter=limit=0.95[a]")
    out = OUT / "ep01_v3.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out)], check=True)
    print(f"wrote {out} ({total:.1f}s)", tl)


if __name__ == "__main__":
    main()
