"""各カットの連番PNGをつなぎ、強調テロップ・字幕・効果音・BGM を FFmpeg(無料)で合成して MP4 にする。

使い方: python compose.py <作業フォルダ> <出力mp4>
  作業フォルダ: up/<カット名>/f_####.png(なければ frames/)、narration.wav、timings.json
  字幕の区切り方・折り返しは mosquito_bite/compose.py と同じ。
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mosquito_bite"))

from compose import FONT, FPS, chunks, esc, wrap  # noqa: E402

SHOTS = ["shake", "buttons", "nearest", "auto", "stuck", "doors_no", "bell", "blackout", "clock", "cabinet", "outro"]
TELOPS = ["最初に押すボタンは?", "全部の階!", "近い階ですぐ降りる", "2009年以降は自動停止", "古いものは要注意",
          "こじ開けない", "ベルのボタン", "非常灯がつく", "救助まで数時間", "隅の箱=防災グッズ", "保存して家族にも"]
HIGHLIGHT = re.compile(r"全部の階|すぐ降り|2009年|自動|古い|絶対にダメ|ベル|非常灯|何時間|水や簡易トイレ|保存")


def frame_list(work, tmp):
    n, starts = 0, []
    for shot in SHOTS:
        src = work / "up" / shot
        if not src.exists():
            src = work / "frames" / shot
        starts.append(n / FPS)
        for f in sorted(src.glob("f_*.png")):
            n += 1
            (tmp / f"{n:05d}.png").symlink_to(f)
    return n, starts


def main(work, out_mp4):
    work = Path(work)
    t = json.loads((work / "timings.json").read_text())
    tmp = Path(tempfile.mkdtemp(prefix="compose_"))
    frames, starts = frame_list(work, tmp)
    total = frames / FPS
    ends = starts[1:] + [total]
    dur = [e - s for s, e in zip(starts, ends)]
    S = dict(zip(SHOTS, starts))
    Dd = dict(zip(SHOTS, dur))

    draws = []
    for i, (label, s, e) in enumerate(zip(TELOPS, starts, ends)):  # カットごとの強調テロップ(上部)
        f = tmp / f"t{i}.txt"
        f.write_text(label)
        a = f"if(lt(t-{s:.2f},0.15),(t-{s:.2f})/0.15,1)"
        draws.append(f"drawtext=fontfile={FONT}:textfile={esc(f)}:fontsize=92:fontcolor=#FFE14D:alpha='{a}':"
                     f"borderw=3:bordercolor=#FFE14D:box=1:boxcolor=black@0.6:boxborderw=26:"
                     f"x=(w-text_w)/2:y=h*0.1:enable='between(t,{s:.2f},{e:.2f})'")
    for i, (s, e, text) in enumerate(chunks(t["lines"])):  # ナレーション字幕(下部)
        f = tmp / f"c{i}.txt"
        f.write_text(wrap(text))
        color = "#FFE14D" if HIGHLIGHT.search(text) else "white"
        en = f"enable='between(t,{s:.2f},{e:.2f})'"
        for border, bcolor, fcolor in ((16, "black", "black"), (2, color, color)):
            draws.append(f"drawtext=fontfile={FONT}:textfile={esc(f)}:fontsize=78:fontcolor={fcolor}:"
                         f"borderw={border}:bordercolor={bcolor}:line_spacing=18:x=(w-text_w)/2:y=h*0.7:{en}")
    vf = (f"scale=1080:1920:flags=lanczos,eq=contrast=1.05:saturation=1.1,vignette=angle=0.45,"
          f"{','.join(draws)},fade=t=in:st=0:d=0.2,format=yuv420p")

    # 効果音(すべて FFmpeg で合成):(式, 長さ, 開始秒, 音量)
    sfx = [
        ("0.9*(random(0)*2-1)", Dd["shake"] + 0.3, 0.0, 1.4),                                       # 揺れ(ゴゴゴ)
        ("0.35*sin(2*PI*1400*t)*lt(mod(t,0.0833),0.05)", 0.85, S["buttons"] + 4 / FPS, 0.6),         # ボタン連打
        ("0.9*(random(0)*2-1)", Dd["nearest"] + Dd["auto"], S["nearest"], 0.7),                     # ビルの揺れ
        ("0.5*sin(2*PI*660*t)*exp(-3*t)+0.5*sin(2*PI*880*t)*exp(-3*(t-0.35))*gte(t,0.35)", 1.6,
         S["nearest"] + Dd["nearest"] * 0.66, 0.6),                                                  # 到着チャイム
        ("0.5*sin(2*PI*660*t)*exp(-3*t)+0.5*sin(2*PI*880*t)*exp(-3*(t-0.35))*gte(t,0.35)", 1.6,
         S["auto"] + Dd["auto"] * 0.8, 0.6),
        ("0.3*sin(2*PI*520*t)*lt(mod(t,0.25),0.12)", Dd["stuck"] * 0.75, S["stuck"] + Dd["stuck"] * 0.25, 0.5),  # 警告音
        ("0.5*sgn(sin(2*PI*180*t))*lt(mod(t,0.35),0.25)", 0.65, S["doors_no"] + 14 / FPS, 0.35),    # ブブー
        ("0.5*sin(2*PI*1900*t)*(0.6+0.4*sin(2*PI*22*t))*exp(-0.8*t)", 1.8, S["bell"] + 0.45, 0.45),  # ベル
        ("0.6*sin(2*PI*(400-300*t/0.6)*t)*exp(-2*t)", 0.7, S["blackout"] + Dd["blackout"] * 0.2, 0.7),  # 電源が落ちる音
        ("0.8*sin(2*PI*3000*t)*exp(-250*mod(t,0.125))", Dd["clock"], S["clock"], 0.35),            # 時計の早回し
        ("0.8*(random(0)*2-1)*exp(-30*t)", 0.3, S["cabinet"] + Dd["cabinet"] * 0.25, 0.5),          # キャビネットを開ける
    ]
    ms = lambda sec: int(max(0.0, sec) * 1000)
    inputs, af, labels = [], [], []
    for k, (expr, length, start, vol) in enumerate(sfx):
        idx = 3 + k
        inputs += ["-f", "lavfi", "-t", f"{length:.2f}", "-i", f"aevalsrc='{expr}':s=48000:c=stereo"]
        filt = "lowpass=f=110," if "random" in expr and k != len(sfx) - 1 else ""
        af.append(f"[{idx}:a]{filt}volume={vol},afade=t=in:d=0.03,afade=t=out:st={max(0.0, length - 0.25):.2f}:d=0.25,"
                  f"adelay={ms(start)}|{ms(start)}[s{k}]")
        labels.append(f"[s{k}]")
    af = [
        "[1:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,"
        "aformat=channel_layouts=stereo:sample_rates=48000[vo]",
        f"[2:a]lowpass=f=1200,volume=0.16,afade=t=in:d=1,afade=t=out:st={total - 1.2:.2f}:d=1.2[bgm]",
    ] + af + [
        f"[vo][bgm]{''.join(labels)}amix=inputs={2 + len(labels)}:duration=longest:normalize=0,"
        f"apad=whole_dur={total:.2f},atrim=0:{total:.2f},loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    ]
    # BGM:低いパッド+テンポを感じる控えめなパルス(120BPM)
    bgm = ("aevalsrc='0.22*sin(2*PI*55*t)+0.16*sin(2*PI*82.4*t)+0.1*sin(2*PI*110*t)*(0.5+0.5*sin(2*PI*0.25*t))"
           "+0.25*sin(2*PI*70*t)*exp(-12*mod(t,0.5))':s=48000:c=stereo")
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
    print("done:", out_mp4, f"{total:.2f}s, {frames} frames")


if __name__ == "__main__":
    main(*sys.argv[1:3])
