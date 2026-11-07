#!/usr/bin/env python3
"""ディープ × ドウデュース「おい、別れの言葉は無しか？」完成版の書き出し。

使い方: python3 edit/deep-dodeuce/build.py [A|B]
  A/B = 騎手の声 (assets/output/deep-dodeuce/voice_A.mp3 / voice_B.mp3)
素材: assets/output/deep-dodeuce/v2/ (Higgs Field の job は prompts/deep-dodeuce/production-log.md)
"""
import subprocess, sys
from pathlib import Path

VOICE = (sys.argv[1] if len(sys.argv) > 1 else "A").upper()
ROOT = Path(__file__).resolve().parents[2] / "assets/output/deep-dodeuce"
V2 = ROOT / "v2"
OUT = ROOT / f"deep_dodeuce_farewell_voice{VOICE}.mp4"
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

# (ファイル, 開始秒, 長さ) — None は黒画面
SEGS = [
    ("V01", 0, 4.0),   # 真上: ディープが来て停止線で止まる
    ("V02", 0, 4.0),   # 左後ろ: 車が横切る
    ("V03", 0, 5.0),   # 真横: 考え込むディープ
    ("V04", 0, 8.0),   # 後ろの引き: ドウデュースが走ってきて並ぶ
    ("V05", 0, 3.0),   # 足元
    ("V06", 0, 3.0),   # 真上: 2頭
    ("V07", 0, 4.0),   # ③ セリフ
    ("V08", 0, 3.0),   # ④ 騎手
    ("V09", 0, 3.0),   # ⑤ ディープが頷く
    ("V07b_C6", 0, 3.0),  # ⑥ ディープのアップ
    ("V10", 0, 3.0),   # ⑦ 耳
    ("V11", 0, 4.0),   # ⑧ 首をなでる
    (None, 0, 0.8),    # 黒
    ("W01", 0.3, 1.2), # 蹄
    ("W02", 0.0, 1.8), # 前の上から発進
    ("W03", 0.0, 2.2), # 路面から走り去る
    ("W04", 0, 4.0),   # 横から並走
    ("W05", 0, 5.0),   # 後ろ上空
    ("W06", 0, 4.0),   # 騎手の正面
    ("W07", 0, 4.0),   # 肩越しのディープ
    ("W08", 0, 8.0),   # 真上: 分かれ道
    ("W09", 0, 8.0),   # 左の道 → 空
]
LINE_SEG = "V07"
LINE_OFFSET = 0.35  # ③ が始まってから声を入れるまで
LINE_TEXT = "おい、別れの言葉は無しか？"
NOTE_TEXT = "※イメージ映像です。セリフは創作です"

args, chains, t, line_at = [], [], 0.0, None
for i, (name, ss, dur) in enumerate(SEGS):
    if name is None:
        args += ["-f", "lavfi", "-t", str(dur), "-i", "color=c=black:s=720x1280:r=30"]
        chains.append(f"[{i}:v]setsar=1,format=yuv420p[v{i}]")
    else:
        args += ["-ss", str(ss), "-t", str(dur), "-i", str(V2 / f"{name}.mp4")]
        chains.append(f"[{i}:v]scale=720:1280,setsar=1,fps=30,format=yuv420p,trim=duration={dur},setpts=PTS-STARTPTS[v{i}]")
    if name == LINE_SEG:
        line_at = t + LINE_OFFSET
    t += dur
total = t
n = len(SEGS)
vin = "".join(f"[v{i}]" for i in range(n))
voice_i, bgm_i = n, n + 1
args += ["-i", str(ROOT / f"voice_{VOICE}.mp3"), "-i", str(V2 / "bgm.m4a")]
line_end = line_at + 3.4
txt = (
    f"drawtext=fontfile={FONT}:text='{NOTE_TEXT}':fontsize=26:fontcolor=white@0.9:"
    f"box=1:boxcolor=black@0.35:boxborderw=8:x=(w-tw)/2:y=h-150:enable='lt(t,4)',"
    f"drawtext=fontfile={FONT}:text='{LINE_TEXT}':fontsize=44:fontcolor=white:"
    f"borderw=3:bordercolor=black@0.8:x=(w-tw)/2:y=h-300:enable='between(t,{line_at:.2f},{line_end:.2f})',"
    f"fade=t=in:st=0:d=0.8,fade=t=out:st={total-1.2:.2f}:d=1.2:color=white"
)
ms = int(line_at * 1000)
fc = ";".join(chains) + f";{vin}concat=n={n}:v=1:a=0[cat];[cat]{txt}[vout];" \
    f"[{voice_i}:a]aresample=48000,volume=1.6,adelay={ms}|{ms},apad[vo];" \
    f"[{bgm_i}:a]aresample=48000,atrim=0:{total},volume=0.55," \
    f"volume=enable='between(t,{line_at-0.3:.2f},{line_end:.2f})':volume=0.4," \
    f"afade=t=in:st=0:d=1.5,afade=t=out:st={total-3:.2f}:d=3[bg];" \
    f"[bg][vo]amix=inputs=2:duration=first:normalize=0,atrim=0:{total}[aout]"
cmd = ["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex", fc,
       "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-crf", "20", "-preset", "medium",
       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.2f}", str(OUT)]
subprocess.run(cmd, check=True)
print(f"{OUT} {total:.1f}s line_at={line_at:.2f}s")
