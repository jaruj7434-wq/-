"""各カットの連番PNG(拡大済み)をつなぎ、字幕・BGM・効果音を FFmpeg(無料)で合成して MP4 にする。

使い方: python compose.py <作業フォルダ> <出力mp4>
  作業フォルダ: up/<カット名>/f_####.png(なければ frames/ を使う)、narration.wav、timings.json
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

FPS = 24
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"  # IPAゴシック(無料)
SHOTS = ["surface_approach", "surface_bend", "tip_closeup", "section_search", "vessel", "section_react",
         "surface_withdraw"]
TITLE = "蚊に刺された瞬間\n皮膚の下では…"
HIGHLIGHT = re.compile(r"6本|ギザギザ|唾液|ストロー|かゆみ|メス")  # 黄色で強調する語


def chunks(lines):
    """セリフを読点・句点で区切り、文字数に比例して表示時間を割り振る。"""
    out = []
    for ln in lines:
        parts = [p for p in re.split(r"(?<=[、。])", ln["text"]) if p.strip()]
        total = sum(len(p) for p in parts)
        t = ln["start"]
        for p in parts:
            d = (ln["end"] - ln["start"]) * len(p) / total
            out.append((t, t + d, p.rstrip("、。")))
            t += d
    return out


def wrap(text, limit=11):
    """長い字幕は、真ん中に近い助詞の後ろで2行に分ける。"""
    if len(text) <= limit:
        return text
    mid = len(text) / 2
    cands = [i + 1 for i, ch in enumerate(text[:-1]) if ch in "がをにではのとても"]
    cut = min(cands, key=lambda i: abs(i - mid)) if cands else int(mid)
    if abs(cut - mid) > 4:
        cut = int(mid)
    return text[:cut] + "\n" + text[cut:]


def frame_list(work, tmp):
    """全カットのフレームを通し番号のシンボリックリンクにする。"""
    n = 0
    for shot in SHOTS:
        src = work / "up" / shot
        if not src.exists():
            src = work / "frames" / shot
        for f in sorted(src.glob("f_*.png")):
            n += 1
            (tmp / f"{n:05d}.png").symlink_to(f)
    return n


def esc(path):
    return str(path).replace(":", r"\:")


def main(work, out_mp4):
    work = Path(work)
    t = json.loads((work / "timings.json").read_text())
    tmp = Path(tempfile.mkdtemp(prefix="compose_"))
    frames = frame_list(work, tmp)
    total = frames / FPS

    draws = []
    title_file = tmp / "title.txt"
    title_file.write_text(TITLE)
    draws.append(f"drawtext=fontfile={FONT}:textfile={esc(title_file)}:fontsize=64:fontcolor=white:borderw=7:"
                 f"bordercolor=black@0.85:line_spacing=10:x=(w-text_w)/2:y=h*0.075")
    for i, (s, e, text) in enumerate(chunks(t["lines"])):
        f = tmp / f"c{i}.txt"
        f.write_text(wrap(text))
        color = "#FFE14D" if HIGHLIGHT.search(text) else "white"
        en = f"enable='between(t,{s:.2f},{e:.2f})'"
        for border, bcolor, fcolor in ((16, "black", "black"), (2, color, color)):  # 太い縁取り+疑似太字
            draws.append(f"drawtext=fontfile={FONT}:textfile={esc(f)}:fontsize=80:fontcolor={fcolor}:"
                         f"borderw={border}:bordercolor={bcolor}:line_spacing=18:x=(w-text_w)/2:y=h*0.68:{en}")
    vf = (f"scale=1080:1920:flags=lanczos,eq=contrast=1.04:saturation=1.08,vignette=angle=0.5,"
          f"noise=alls=3:allf=t,{','.join(draws)},fade=t=in:st=0:d=0.25,format=yuv420p")

    # 効果音とBGM(すべて FFmpeg 内で合成。素材の購入・ダウンロードは不要)
    L = t["lines"]
    pierce = L[1]["start"] + 1.0     # 針が皮膚に入る
    vessel = L[4]["start"]           # 血管の中(鼓動)
    suck = L[5]["start"] + 0.3       # 吸い上げ
    ms = lambda sec: int(sec * 1000)
    cuts = [L[i]["start"] for i in (1, 2, 3, 4, 6, 7)]
    whoosh = "".join(f"[w{i}]" for i in range(len(cuts)))
    af = [
        "[1:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,aformat=channel_layouts=stereo:sample_rates=48000[vo]",
        f"[2:a]lowpass=f=900,volume=0.18,afade=t=in:d=1.5,afade=t=out:st={total - 1.5:.2f}:d=1.5[pad]",
        f"[3:a]asplit={len(cuts)}" + "".join(f"[ws{i}]" for i in range(len(cuts))),
    ]
    for i, c in enumerate(cuts):
        af.append(f"[ws{i}]bandpass=f=900:width_type=o:w=2,volume=0.35,afade=t=in:d=0.15,afade=t=out:st=0.15:d=0.3,"
                  f"adelay={ms(max(0, c - 0.15))}|{ms(max(0, c - 0.15))}[w{i}]")
    af += [
        f"[4:a]lowpass=f=2500,highpass=f=400,volume=0.5,afade=t=in:d=0.05,afade=t=out:st=0.2:d=0.5,adelay={ms(pierce)}|{ms(pierce)}[pierce]",
        f"[5:a]volume=0.9,afade=t=in:d=0.3,afade=t=out:st={L[6]['start'] - vessel - 0.6:.2f}:d=0.6,adelay={ms(vessel)}|{ms(vessel)}[beat]",
        f"[6:a]lowpass=f=600,volume=0.6,afade=t=in:d=0.4,afade=t=out:st=1.6:d=0.8,adelay={ms(suck)}|{ms(suck)}[suck]",
        f"[vo][pad]{whoosh}[pierce][beat][suck]amix=inputs={4 + len(cuts) + 1}:duration=longest:normalize=0,"
        f"apad=whole_dur={total:.2f},atrim=0:{total:.2f},loudnorm=I=-14:TP=-1.5:LRA=11[a]",
    ]
    heartbeat = ("aevalsrc='0.9*sin(2*PI*48*t)*exp(-18*mod(t,0.85))+0.6*sin(2*PI*42*t)*exp(-22*mod(t-0.22,0.85))"
                 "*gte(mod(t,0.85),0.22)':s=48000:c=stereo")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", str(FPS), "-i", str(tmp / "%05d.png"),
        "-i", str(work / "narration.wav"),
        "-f", "lavfi", "-t", f"{total:.2f}", "-i",
        "aevalsrc='0.25*sin(2*PI*55*t)+0.2*sin(2*PI*82.4*t)*(0.6+0.4*sin(2*PI*0.1*t))+0.12*sin(2*PI*110*t)':s=48000:c=stereo",
        "-f", "lavfi", "-t", "0.6", "-i", "anoisesrc=color=pink:sample_rate=48000",
        "-f", "lavfi", "-t", "0.8", "-i", "anoisesrc=color=white:sample_rate=48000",
        "-f", "lavfi", "-t", f"{L[6]['start'] - vessel:.2f}", "-i", heartbeat,
        "-f", "lavfi", "-t", "2.5", "-i", "anoisesrc=color=brown:sample_rate=48000",
        "-filter_complex", f"[0:v]{vf}[v];" + ";".join(af),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True)
    print("done:", out_mp4, f"{total:.2f}s, {frames} frames")


if __name__ == "__main__":
    main(*sys.argv[1:3])
