"""外部で作ったナレーション(セリフごとの音声ファイル)を、既存のカット割り(timings.json)に合わせて並べ直す。

使い方: python fit_narration.py <作業フォルダ> <音声フォルダ>
  <音声フォルダ> に 00.mp3〜11.mp3(LINES の順)を置く。今回は Higgsfield の Eleven v4(声:Julian)で生成した。
  各セリフの前後の無音を削り、枠(timings.json の start〜end)に収まらないものだけ速度を上げて(ピッチは保ったまま)
  start の位置に置く。映像は描き直さずに済む。元の narration.wav は narration_sbv2.wav として残す。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

SR = 48000
TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB,areverse")


def duration(path, filt="anull"):
    err = subprocess.run(["ffmpeg", "-i", str(path), "-af", filt, "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    h, m, s = re.findall(r"time=(\d+):(\d+):([\d.]+)", err)[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def main(work, clips):
    work, clips = Path(work), Path(clips)
    lines = json.loads((work / "timings.json").read_text())["lines"]
    total = json.loads((work / "timings.json").read_text())["total"]
    src = work / "narration.wav"
    backup = work / "narration_sbv2.wav"
    if src.exists() and not backup.exists():
        src.rename(backup)
    inputs, filters, labels = [], [], []
    for x in lines:
        f = clips / f"{x['index']:02d}.mp3"
        slot = x["end"] - x["start"] + 0.05
        speed = max(1.0, duration(f, TRIM) / slot)
        stretch = f",rubberband=tempo={speed:.3f}" if speed > 1.0 else ""
        k = len(inputs) // 2
        inputs += ["-i", str(f)]
        ms = int(x["start"] * 1000)
        filters.append(f"[{k}:a]aresample={SR},{TRIM}{stretch},adelay={ms}|{ms}[n{k}]")
        labels.append(f"[n{k}]")
        print(f"{x['index']:2d} speed x{speed:.2f}  {x['text']}")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,apad=whole_dur={total:.3f},"
                   f"atrim=0:{total:.3f},aformat=channel_layouts=mono[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
                    "-map", "[a]", "-ar", str(SR), str(src)], check=True)
    print("wrote", src)


if __name__ == "__main__":
    main(*sys.argv[1:3])
