"""連番PNG + ナレーションに、テロップ・効果音・BGMを FFmpeg(無料)で合成して 1080x1920 の MP4 を作る。

使い方: python compose.py <作業フォルダ> <出力mp4>
  作業フォルダには frames/f_####.png, narration.wav, timings.json があること。
"""
import json
import subprocess
import sys
from pathlib import Path

FPS = 30
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"  # IPAゴシック(無料フォント)

# (上部の大見出し, 下部の字幕) — 字幕は改行位置を手動で指定
CAPTIONS = [
    ("もしも地球が\n1秒止まったら?", "もしも地球の回転が、\n1秒だけ止まったら?"),
    ("時速 約1,700km", "赤道の地面は、\n時速1700キロで動いています。"),
    ("空気も海も\n止まれない", "地面が止まっても、空気や海、\nそして私たちは止まれません。"),
    ("音速を超える爆風", "音速を超えるスピードで、\nすべてが東へ吹き飛ばされます。"),
    ("たった1秒で\n世界は終わる", "たった1秒で、\n世界は終わるのです。"),
]


def main(work, out_mp4):
    work = Path(work)
    t = json.loads((work / "timings.json").read_text())
    lines = t["lines"]
    total = len(list((work / "frames").glob("f_*.png"))) / FPS
    stop = lines[2]["start"] + 0.4
    blast = lines[3]["start"] + 10 / FPS

    txt_dir = work / "captions"
    txt_dir.mkdir(exist_ok=True)
    draws = []
    for i, ((head, sub), ln) in enumerate(zip(CAPTIONS, lines)):
        s, e = ln["start"], (lines[i + 1]["start"] if i + 1 < len(lines) else total)
        (txt_dir / f"h{i}.txt").write_text(head)
        (txt_dir / f"s{i}.txt").write_text(sub)
        en = f"enable='between(t,{s:.2f},{e:.2f})'"
        draws.append(
            f"drawtext=fontfile={FONT}:textfile={txt_dir}/h{i}.txt:fontsize=104:fontcolor=#FFE14D:"
            f"borderw=8:bordercolor=black:line_spacing=12:x=(w-text_w)/2:y=h*0.11:{en}"
        )
        draws.append(
            f"drawtext=fontfile={FONT}:textfile={txt_dir}/s{i}.txt:fontsize=54:fontcolor=white:"
            f"borderw=6:bordercolor=black:line_spacing=14:x=(w-text_w)/2:y=h*0.74:{en}"
        )
    vf = (
        f"scale=1080:1920:flags=lanczos,{','.join(draws)},"
        f"fade=t=in:st=0:d=0.3,fade=t=out:st={total - 0.6:.2f}:d=0.6,format=yuv420p"
    )

    # BGM(低いドローン)と効果音(停止時の衝撃・爆風)を FFmpeg 内で合成する
    # 入力: 0=映像, 1=ナレーション, 2=BGM, 3=衝撃音, 4=風音
    ms = lambda sec: int(sec * 1000)
    af = (
        f"[2:a]volume=0.10,afade=t=in:d=1,afade=t=out:st={total - 1:.2f}:d=1[bgm];"
        f"[3:a]lowpass=f=120,volume=1.4,afade=t=in:d=0.02,afade=t=out:st=0.1:d=1.3,adelay={ms(stop)}|{ms(stop)}[boom];"
        f"[4:a]highpass=f=300,lowpass=f=3500,volume=0.45,afade=t=in:d=0.25,afade=t=out:st=0.6:d=1.4,adelay={ms(blast)}|{ms(blast)}[wind];"
        f"[1:a]aformat=channel_layouts=stereo:sample_rates=48000[vo];"
        f"[vo][bgm][boom][wind]amix=inputs=4:duration=first:normalize=0,"
        f"apad=whole_dur={total:.2f},atrim=0:{total:.2f},loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", str(FPS), "-i", str(work / "frames" / "f_%04d.png"),
        "-i", str(work / "narration.wav"),
        "-f", "lavfi", "-t", f"{total:.2f}", "-i", "aevalsrc=0.5*sin(2*PI*55*t)*(0.7+0.3*sin(2*PI*0.25*t))+0.3*sin(2*PI*82.5*t):s=48000:c=stereo",
        "-f", "lavfi", "-t", "1.6", "-i", "anoisesrc=color=brown:sample_rate=48000:amplitude=1",
        "-f", "lavfi", "-t", "2.2", "-i", "anoisesrc=color=pink:sample_rate=48000:amplitude=1",
        "-filter_complex", f"[0:v]{vf}[v];{af}",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True)
    print("done:", out_mp4, f"{total:.2f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
