"""「凍ったフロントガラスにお湯はNG」:各カットの連番PNGをつなぎ、テロップ・字幕・タイマー・効果音・BGM を FFmpeg(無料)で合成して MP4 にする。

使い方: python compose.py <作業フォルダ> <出力mp4>
  作業フォルダ: frames/ または up/<カット名>/f_####.png、narration.wav、timings.json
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

TELOPS = ["これだけで\n修理代10万円以上も", "凍った窓にお湯\nやってない?", "1分で溶かす方法は\n最後に", "合わせガラス",
          "急な温度差でゆがむ", "小さな傷から一気に", "ぬるま湯もNG", "ワイパーも動かさない", "デフロスター 約10分",
          "解氷スプレー 約1分", "前の晩にカバー", "保存して冬に備えて"]
HIGHLIGHT = re.compile(r"10万円|お湯|1分|合わせガラス|ゆがみ|傷|ヒビ|ぬるま湯|厚い氷|NG|デフロスター|10分|解氷スプレー|カバー|保存")


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
    F = {k: win[k][1] for k in SHOTS}
    sec = lambda shot, fr: S[shot] + fr / FPS

    draws = []
    for i, (label, s, e) in enumerate(zip(TELOPS, starts, ends)):
        f = tmp / f"t{i}.txt"
        f.write_text(label)
        a = "1" if i == 0 else f"if(lt(t-{s:.2f},0.15),(t-{s:.2f})/0.15,1)"   # 1カット目は 0 秒目から表示
        draws.append(f"drawtext=fontfile={FONT}:textfile={esc(f)}:fontsize=92:fontcolor=#FFE14D:alpha='{a}':"
                     f"borderw=3:bordercolor=#FFE14D:box=1:boxcolor=black@0.6:boxborderw=26:"
                     f"line_spacing=14:x=(w-text_w)/2:y=h*0.1:enable='between(t,{s:.2f},{e:.2f})'")
    # 「答えまで あと◯秒」:予告(3カット目)から答え(解氷スプレー)まで、右上に残り時間とバー
    a0, a1 = S["stopwatch"], S["spray"]
    left = f"max(0\\,ceil({a1:.2f}-t))"
    draws.append(f"drawtext=fontfile={FONT}:text='答えまで あと %{{eif\\:{left}\\:d}}秒':fontsize=40:fontcolor=white:"
                 f"borderw=4:bordercolor=black:x=w-text_w-40:y=h*0.035:enable='between(t,{a0:.2f},{a1:.2f})'")
    draws.append(f"drawbox=x=w-440:y=h*0.035+56:w=400:h=12:color=white@0.35:t=fill:enable='between(t,{a0:.2f},{a1:.2f})'")
    draws.append(f"drawbox=x=w-440:y=h*0.035+56:w='400*max(0,({a1:.2f}-t)/{a1 - a0:.2f})':h=12:color=#FFE14D:t=fill:"
                 f"enable='between(t,{a0:.2f},{a1:.2f})'")
    # タイマー:デフロスターは10分、解氷スプレーは1分を早回しで表示
    for shot, minutes, lead in (("defroster", 10, 4), ("spray", 1, 6)):
        s0, dur = sec(shot, lead), D[shot] - lead / FPS - 8 / FPS
        p = f"min(1\\,max(0\\,(t-{s0:.2f})/{dur:.2f}))"
        total_s = f"floor({minutes * 60}*{p})"
        txt = f"%{{eif\\:floor({total_s}/60)\\:d}}\\:%{{eif\\:mod({total_s}\\,60)\\:d\\:2}}"
        en = f"enable='between(t,{S[shot]:.2f},{S[shot] + D[shot]:.2f})'"
        draws.append(f"drawtext=fontfile={FONT}:text='{txt}':fontsize=96:fontcolor=white:borderw=6:bordercolor=black:"
                     f"box=1:boxcolor=black@0.45:boxborderw=18:x=(w-text_w)/2:y=h*0.52:{en}")
    draws.append(f"drawtext=fontfile={FONT}:text='外気温 氷点下':fontsize=48:fontcolor=#9FD8FF:borderw=4:bordercolor=black:"
                 f"x=40:y=h*0.035:enable='between(t,{S['lukewarm']:.2f},{S['wiper']:.2f})'")
    for i, (s, e, text) in enumerate(chunks(t["lines"])):
        f = tmp / f"c{i}.txt"
        f.write_text(wrap(text))
        color = "#FFE14D" if HIGHLIGHT.search(text) else "white"
        en = f"enable='between(t,{s:.2f},{e:.2f})'"
        for border, bcolor, fcolor in ((16, "black", "black"), (2, color, color)):
            draws.append(f"drawtext=fontfile={FONT}:textfile={esc(f)}:fontsize=78:fontcolor={fcolor}:"
                         f"borderw={border}:bordercolor={bcolor}:line_spacing=18:x=(w-text_w)/2:y=h*0.72:{en}")
    vf = (f"scale=1080:1920:flags=lanczos,eq=contrast=1.04:saturation=1.06,vignette=angle=0.4,"
          f"{','.join(draws)},format=yuv420p")

    noise = "0.9*(random(0)*2-1)"
    crack = "(random(0)*2-1)*exp(-30*t)+0.7*sin(2*PI*2400*t)*exp(-45*t)"
    tick = "0.8*sin(2*PI*3000*t)*exp(-120*mod(t,0.25))"
    chime = "0.45*sin(2*PI*880*t)*exp(-4*t)+0.3*sin(2*PI*1320*t)*exp(-5*t)"
    sting = "0.4*sin(2*PI*660*t)*exp(-3*t)+0.3*sin(2*PI*990*t)*exp(-3*t)*gt(t,0.12)"
    stuck = int(F["wiper"] * 0.25)
    lift = stuck + 26
    spray_end = 6 + int(0.55 * (F["spray"] - 14))
    cover_lift = int(F["cover"] * 0.3) + 8
    sfx = [  # (式, 長さ, 開始秒, 音量, フィルター)
        (noise, D["hook"], 0.0, 0.5, "highpass=f=600,lowpass=f=5000"),                     # お湯を注ぐ音
        (noise, D["hook"], 0.0, 0.25, "highpass=f=3000"),                                    # ジュワッという湯気
        (crack, 0.5, sec("hook", 13), 1.4, "highpass=f=1500"),                              # パキッ
        ("0.9*sin(2*PI*55*t)*exp(-6*t)", 0.8, sec("hook", 13), 1.0, "anull"),              # ドンという衝撃
        (noise, D["morning"], S["morning"], 0.18, "lowpass=f=400,highpass=f=60"),          # 冬の朝の風
        (tick, D["stopwatch"] - 0.8, S["stopwatch"] + 0.3, 0.35, "anull"),                 # 秒針
        (sting, 1.2, S["stopwatch"] + D["stopwatch"] - 1.2, 0.5, "anull"),
        ("0.25*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.5*t))", D["layers"], S["layers"], 0.4, "anull"),
        (noise, 2.0, sec("thermal", 4), 0.4, "highpass=f=600,lowpass=f=5000"),
        ("0.5*sin(2*PI*(70+20*t)*t)", D["thermal"] - 1.5, sec("thermal", 30), 0.45, "anull"),  # きしむ音
        (chime, 1.2, sec("chip", 8), 0.6, "anull"),
        (noise, 2.0, sec("chip", 48), 0.45, "highpass=f=600,lowpass=f=5000"),
        (crack, 0.6, sec("chip", 56), 1.5, "highpass=f=1200"),
        (sting, 1.0, S["lukewarm"], 0.5, "anull"),                                           # 「セーフ?」
        (noise, D["lukewarm"] * 0.3, S["lukewarm"], 0.35, "highpass=f=600,lowpass=f=4000"),
        ("0.6*sin(2*PI*2600*t)*exp(-25*mod(t,0.17))*gt(random(0),0.3)", D["lukewarm"] * 0.5, sec("lukewarm", int(F["lukewarm"] * 0.45)),
         0.25, "anull"),                                                                      # ピキピキ凍る音
        ("0.5*sgn(sin(2*PI*90*t))", 1.0, sec("wiper", stuck), 0.12, "lowpass=f=800"),     # モーターのうなり
        (crack, 0.4, sec("wiper", lift + 6), 1.1, "highpass=f=500"),                        # ブチッ
        ("0.5*sgn(sin(2*PI*180*t))*lt(mod(t,0.35),0.25)", 0.65, sec("wiper", lift + 14), 0.22, "anull"),  # ブブー
        (noise, D["defroster"], S["defroster"], 0.25, "lowpass=f=700,highpass=f=100"),    # 送風
        (chime, 1.2, S["spray"], 0.5, "anull"),
        (noise, (spray_end - 6) / FPS, sec("spray", 6), 0.55, "highpass=f=2500"),          # シューッ
        (noise, 1.2, sec("cover", cover_lift), 0.35, "highpass=f=1200,lowpass=f=6000"),   # カバーを外す音
        ("0.4*sin(2*PI*45*t)+0.2*sin(2*PI*90*t)", D["drive"], S["drive"], 0.3, "lowpass=f=300"),  # エンジン
        (chime, 1.4, S["drive"] + 0.3, 0.5, "anull"),
    ]
    ms = lambda sec_: int(max(0.0, sec_) * 1000)
    inputs, af, labels = [], [], []
    for k, (expr, length, start, vol, filt) in enumerate(sfx):
        inputs += ["-f", "lavfi", "-t", f"{length:.2f}", "-i", f"aevalsrc='{expr}':s=48000:c=stereo"]
        af.append(f"[{3 + k}:a]{filt},volume={vol},afade=t=in:d=0.02,afade=t=out:st={max(0.0, length - 0.2):.2f}:d=0.2,"
                  f"adelay={ms(start)}|{ms(start)}[s{k}]")
        labels.append(f"[s{k}]")
    af = [
        "[1:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,"
        "aformat=channel_layouts=stereo:sample_rates=48000[vo]",
        f"[2:a]lowpass=f=1500,volume=0.12,afade=t=in:d=0.5,afade=t=out:st={total - 1.2:.2f}:d=1.2[bgm]",
    ] + af + [
        f"[vo][bgm]{''.join(labels)}amix=inputs={2 + len(labels)}:duration=longest:normalize=0,"
        f"apad=whole_dur={total:.2f},atrim=0:{total:.2f},loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    ]
    # BGM:軽快な8分音符のベースと和音(Am-F-C-G を2秒ずつ)
    roots = "(110*lt(mod(t,8),2)+87.3*between(mod(t,8),2,4)+130.8*between(mod(t,8),4,6)+98*gte(mod(t,8),6))"
    bgm = (f"aevalsrc='0.3*sin(2*PI*{roots}*t)*exp(-6*mod(t,0.25))+0.12*sin(2*PI*2*{roots}*t)+0.08*sin(2*PI*3*{roots}*t)"
           f"+0.15*sin(2*PI*4*{roots}*t)*exp(-10*mod(t,0.5))':s=48000:c=stereo")
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
