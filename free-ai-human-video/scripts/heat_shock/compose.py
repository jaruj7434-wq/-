"""「冬のヒートショック」:各カットの連番PNGをつなぎ、強調テロップ・字幕・効果音・BGM を FFmpeg(無料)で合成して MP4 にする。

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mosquito_bite"))  # 同名の compose より先に見つかるよう最後に先頭へ

from compose import FONT, FPS, chunks, esc, wrap  # noqa: E402
from plan import SHOTS, windows  # noqa: E402

TELOPS = ["家族を守るために最後まで見て", "交通事故より多い", "ヒートショック", "温度差が危ない", "血圧が乱高下",
          "防ぐポイント5つ", "①先に暖める", "②41℃以下・10分まで", "③急に立たない", "④食後・飲酒後は避ける",
          "⑤家族に一声", "大切な人に送って"]
HIGHLIGHT = re.compile(r"最後まで|交通事故|ヒートショック|温度差|血圧|5つ|暖め|41度|10分|急に|食事|お酒|一声|大切な人")


def main(work, out_mp4):
    work = Path(work)
    t = json.loads((work / "timings.json").read_text())
    win = windows(work / "timings.json")
    tmp = Path(tempfile.mkdtemp(prefix="compose_"))
    n, starts = 0, []
    for shot in SHOTS:
        starts.append(n / FPS)
        src = work / "up" / shot if (work / "up" / shot).exists() else work / "frames" / shot  # 拡大済みがあれば使う
        for f in sorted(src.glob("f_*.png")):
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

    wind = "0.9*(random(0)*2-1)"
    sec = lambda shot, fr: S[shot] + fr / FPS
    chime = "0.45*sin(2*PI*880*t)*exp(-4*t)+0.3*sin(2*PI*1320*t)*exp(-5*t)"
    heartbeat = ("0.9*sin(2*PI*48*t)*exp(-18*mod(t,0.7))+0.6*sin(2*PI*42*t)*exp(-22*mod(t-0.2,0.7))"
                 "*gte(mod(t,0.7),0.2)")
    sfx = [  # (式, 長さ, 開始秒, 音量, フィルター)
        (wind, D["exterior"], 0.0, 0.35, "lowpass=f=500,highpass=f=80"),                    # 雪の夜の風
        (wind, D["bath"] + D["heatshock"], S["bath"], 0.12, "highpass=f=2000,lowpass=f=6000"),  # 浴室の湯の音
        (heartbeat, D["pressure"], S["pressure"], 0.9, "anull"),                             # 鼓動
        (chime, 1.2, S["five"], 0.6, "anull"),
        (chime, 1.2, S["heater"], 0.5, "anull"), (chime, 1.2, S["temp_timer"], 0.5, "anull"),
        (chime, 1.2, S["handrail"], 0.5, "anull"), (chime, 1.2, S["food"], 0.5, "anull"),
        (chime, 1.2, S["one_word"], 0.5, "anull"),
        (wind, D["heater"] * 0.7, sec("heater", int(win["heater"][1] * 0.22)), 0.1, "lowpass=f=300"),  # 暖房の音
        ("0.5*sgn(sin(2*PI*180*t))*lt(mod(t,0.35),0.25)", 0.65, sec("food", 30), 0.25, "anull"),  # ✕のブブー
        (wind, D["exterior_end"], S["exterior_end"], 0.3, "lowpass=f=500,highpass=f=80"),
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
    # BGM:やさしい長調の和音(C-E-G)をゆっくり鳴らす(注意喚起だが怖がらせすぎない)
    bgm = ("aevalsrc='(0.16*sin(2*PI*261.6*t)+0.12*sin(2*PI*329.6*t)+0.1*sin(2*PI*392*t))*(0.55+0.45*sin(2*PI*0.2*t))"
           "+0.12*sin(2*PI*130.8*t)':s=48000:c=stereo")
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
