"""第1話 仕上げ: ep01_v2.mp4(映像+効果音)にナレーションとBGMを重ねる。

  PYTHONPATH=scripts/science_0001 python3 scripts/science_0001/ep01_edit_v2.py
  python3 scripts/science_0001/ep01_mix.py
素材: assets/source/science_0001/ep01_na0〜5.mp3 (ElevenLabs v4 Turbo / Julian), ep01_bgm.mp3 (ElevenLabs Music v2.5)
出力: assets/output/science_0001/ep01_final.mp4
"""
import subprocess
from pathlib import Path

SRC = Path("assets/source/science_0001")
OUT = Path("assets/output/science_0001")
SEG_STARTS = [0.0, 4.0, 9.0, 14.0, 19.0, 24.0]
SEG_LENS = [4.0, 5.0, 5.0, 5.0, 5.0, 4.0]
LEAD = 0.15  # 各カット頭からの遅れ
SFX_VOL, BGM_VOL = 0.55, 0.16


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True, check=True).stdout)


def main():
    video = OUT / "ep01_v2.mp4"
    total = dur(video)
    inputs = ["-i", str(video)]
    fc, mix = [f"[0:a]volume={SFX_VOL}[sfx]"], ["[sfx]"]
    for i, (st, ln) in enumerate(zip(SEG_STARTS, SEG_LENS)):
        na = SRC / f"ep01_na{i}.mp3"
        inputs += ["-i", str(na)]
        tempo = max(1.0, dur(na) / (ln - LEAD - 0.2))  # カットに収まるよう必要なときだけ速める
        d = int((st + LEAD) * 1000)
        fc.append(f"[{i + 1}:a]atempo={tempo:.3f},volume=1.6,adelay={d}|{d}[n{i}]")
        mix.append(f"[n{i}]")
    k = len(SEG_STARTS) + 1
    inputs += ["-i", str(SRC / "ep01_bgm.mp3")]
    fc.append(f"[{k}:a]atrim=0:{total},volume={BGM_VOL},afade=t=in:d=0.5,afade=t=out:st={total - 1.5}:d=1.5[bgm]")
    mix.append("[bgm]")
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,alimiter=limit=0.95[a]")
    out = OUT / "ep01_final.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out)], check=True)
    print(f"wrote {out} ({total:.1f}s)")


if __name__ == "__main__":
    main()
