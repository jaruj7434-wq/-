"""各カットの連番PNGをつなぎ、強調テロップ・字幕・効果音・BGM を FFmpeg(無料)で合成して MP4 にする。

使い方: python compose.py <作業フォルダ> <出力mp4>
  作業フォルダ: frames/<カット名>/f_####.png、narration.wav、timings.json
  字幕の区切り方・折り返しは mosquito_bite/compose.py と同じ。
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mosquito_bite"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from compose import FONT, FPS, chunks, esc, wrap  # noqa: E402
from plan import SHOTS, events, windows  # noqa: E402

TELOPS = ["水をかけたら?", "天井まで火柱", "約1700倍", "油が飛び散る", "約370℃で発火", "目を離さない",
          "黄色マークの消火器", "ふたで空気を断つ", "マヨネーズは✕", "保存して家族にも"]
HIGHLIGHT = re.compile(r"天井|1700倍|飛び散|370|目を離|黄色|消火器|ふた|開けない|マヨネーズ|危険|保存")


def main(work, out_mp4):
    work = Path(work)
    t = json.loads((work / "timings.json").read_text())
    win = windows(work / "timings.json")
    ev = events({k: v[1] for k, v in win.items()})
    tmp = Path(tempfile.mkdtemp(prefix="compose_"))
    n, starts = 0, []
    for shot in SHOTS:
        starts.append(n / FPS)
        for f in sorted((work / "frames" / shot).glob("f_*.png")):
            n += 1
            (tmp / f"{n:05d}.png").symlink_to(f)
    total = n / FPS
    ends = starts[1:] + [total]
    S = dict(zip(SHOTS, starts))
    D = {k: e - s for k, s, e in zip(SHOTS, starts, ends)}

    draws = []
    for i, (label, s, e) in enumerate(zip(TELOPS, starts, ends)):
        f = tmp / f"t{i}.txt"
        f.write_text(label)
        a = f"if(lt(t-{s:.2f},0.15),(t-{s:.2f})/0.15,1)"
        draws.append(f"drawtext=fontfile={FONT}:textfile={esc(f)}:fontsize=92:fontcolor=#FFE14D:alpha='{a}':"
                     f"borderw=3:bordercolor=#FFE14D:box=1:boxcolor=black@0.6:boxborderw=26:"
                     f"x=(w-text_w)/2:y=h*0.1:enable='between(t,{s:.2f},{e:.2f})'")
    for i, (s, e, text) in enumerate(chunks(t["lines"])):
        f = tmp / f"c{i}.txt"
        f.write_text(wrap(text))
        color = "#FFE14D" if HIGHLIGHT.search(text) else "white"
        en = f"enable='between(t,{s:.2f},{e:.2f})'"
        for border, bcolor, fcolor in ((16, "black", "black"), (2, color, color)):
            draws.append(f"drawtext=fontfile={FONT}:textfile={esc(f)}:fontsize=78:fontcolor={fcolor}:"
                         f"borderw={border}:bordercolor={bcolor}:line_spacing=18:x=(w-text_w)/2:y=h*0.7:{en}")
    vf = (f"scale=1080:1920:flags=lanczos,eq=contrast=1.05:saturation=1.08,vignette=angle=0.45,"
          f"{','.join(draws)},fade=t=in:st=0:d=0.2,format=yuv420p")

    crackle = "0.9*(random(0)*2-1)*(0.4+0.6*gt(random(1),0.97))"   # パチパチと燃える音
    hiss = "0.8*(random(0)*2-1)"                                     # シュー(白い雑音)
    sec = lambda shot, fr: S[shot] + fr / FPS
    sfx = [  # (式, 長さ, 開始秒, 音量, フィルター)
        (crackle, D["hook"] + D["erupt"], 0.0, 0.5, "highpass=f=400,lowpass=f=6000"),
        ("0.9*(random(0)*2-1)", 2.5, sec("erupt", ev["erupt_burst"]), 1.6, "lowpass=f=160"),             # ボンッという火柱の音
        (hiss, 1.8, sec("erupt", ev["erupt_burst"]), 0.6, "highpass=f=1500"),
        (hiss, D["section"] * 0.5, sec("section", 46), 0.35, "highpass=f=2500"),                           # 水が一気に沸騰
        (crackle, D["spray"], S["spray"], 0.7, "highpass=f=300,lowpass=f=7000"),
        (hiss, D["heat"] + D["unattended"], S["heat"], 0.15, "highpass=f=3000,lowpass=f=9000"),          # 油が熱される音
        ("0.9*(random(0)*2-1)", 1.2, sec("heat", ev["heat_ignite"]), 1.0, "lowpass=f=250"),               # 発火のボッ
        (crackle, D["extinguisher"] * 0.6, S["extinguisher"], 0.4, "highpass=f=400,lowpass=f=6000"),
        (hiss, 2.2, sec("extinguisher", ev["ext_spray"]), 0.9, "highpass=f=800,lowpass=f=9000"),        # 消火器の噴射
        (crackle, D["lid"] * 0.45, S["lid"], 0.4, "highpass=f=400,lowpass=f=6000"),
        ("0.5*sin(2*PI*1200*t)*exp(-6*t)+0.35*sin(2*PI*1830*t)*exp(-8*t)", 1.0, sec("lid", ev["lid_end"]), 0.7, "anull"),  # ふたの金属音
        (crackle, D["mayo"], S["mayo"], 0.35, "highpass=f=400,lowpass=f=6000"),
        (hiss, D["outro"], S["outro"], 0.12, "highpass=f=2500,lowpass=f=8000"),                         # 揚げ物の音
    ]
    ms = lambda sec_: int(max(0.0, sec_) * 1000)
    inputs, af, labels = [], [], []
    for k, (expr, length, start, vol, filt) in enumerate(sfx):
        inputs += ["-f", "lavfi", "-t", f"{length:.2f}", "-i", f"aevalsrc='{expr}':s=48000:c=stereo"]
        af.append(f"[{3 + k}:a]{filt},volume={vol},afade=t=in:d=0.04,afade=t=out:st={max(0.0, length - 0.3):.2f}:d=0.3,"
                  f"adelay={ms(start)}|{ms(start)}[s{k}]")
        labels.append(f"[s{k}]")
    af = [
        "[1:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,"
        "aformat=channel_layouts=stereo:sample_rates=48000[vo]",
        f"[2:a]lowpass=f=900,volume=0.14,afade=t=in:d=1,afade=t=out:st={total - 1.2:.2f}:d=1.2[bgm]",
    ] + af + [
        f"[vo][bgm]{''.join(labels)}amix=inputs={2 + len(labels)}:duration=longest:normalize=0,"
        f"apad=whole_dur={total:.2f},atrim=0:{total:.2f},loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    ]
    bgm = ("aevalsrc='0.22*sin(2*PI*55*t)+0.16*sin(2*PI*65.4*t)+0.1*sin(2*PI*110*t)*(0.5+0.5*sin(2*PI*0.25*t))"
           "+0.22*sin(2*PI*60*t)*exp(-10*mod(t,0.5))':s=48000:c=stereo")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-framerate", str(FPS), "-i", str(tmp / "%05d.png"),
           "-i", str(work / "narration.wav"),
           "-f", "lavfi", "-t", f"{total:.2f}", "-i", bgm,
           *inputs,
           "-filter_complex", f"[0:v]{vf}[v];" + ";".join(af),
           "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out_mp4)]
    subprocess.run(cmd, check=True)
    print("done:", out_mp4, f"{total:.2f}s, {n} frames")


if __name__ == "__main__":
    main(*sys.argv[1:3])
