"""
連番 PNG(各 SOFT 段階)に「◯% SOFT」の文字を入れて 1 本の縦型動画に連結する。
FFmpeg(無料)が必要。Windows / Mac / Linux で動く。

フォルダ構成(keyhole_scene.py の --render で書き出したもの):
  RENDER_DIR/s0/f_0001.png ...
  RENDER_DIR/s25/ ...  s50/  s75/  s100/

使い方:
  python compose.py RENDER_DIR out.mp4
  python compose.py RENDER_DIR out.mp4 --fps 30 --font "C:/Windows/Fonts/arial.ttf"
  python compose.py RENDER_DIR out.mp4 --audio sfx.wav     # 効果音トラックを重ねる
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

LEVELS = [0, 25, 50, 75, 100]

DEFAULT_FONTS = [
    "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
    "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
    "C:/Windows/Fonts/segoeui.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]

ap = argparse.ArgumentParser()
ap.add_argument("render_dir")
ap.add_argument("out")
ap.add_argument("--fps", type=float, default=30)
ap.add_argument("--font", default=None)
ap.add_argument("--audio", default=None)
ap.add_argument("--crf", type=int, default=16)
a = ap.parse_args()

if not shutil.which("ffmpeg"):
    sys.exit("ffmpeg が見つかりません。https://ffmpeg.org からインストールしてください。")

font = a.font or next((f for f in DEFAULT_FONTS if os.path.exists(f)), None)
if not font:
    sys.exit("フォントが見つかりません。--font でフォントファイルを指定してください。")
font_esc = font.replace("\\", "/").replace(":", "\\:")

tmp = tempfile.mkdtemp()
parts = []
for lv in LEVELS:
    d = os.path.join(a.render_dir, f"s{lv}")
    if not os.path.isdir(d):
        print(f"スキップ: {d} がありません")
        continue
    out = os.path.join(tmp, f"part_{lv:03d}.mp4")
    text = f"{lv}\\\\% SOFT"  # drawtext では % をエスケープ
    # 文字: 白・中央上部・画面幅の約 7%。0.3 秒でフェードイン
    vf = (
        f"drawtext=fontfile='{font_esc}':text='{text}':fontcolor=white:"
        f"fontsize=h*0.042:x=(w-text_w)/2:y=h*0.085:"
        f"alpha='min(1,t/0.3)':shadowcolor=black@0.25:shadowx=0:shadowy=2,"
        f"format=yuv420p"
    )
    # 連番が飛んでいても(--step 2 など)使えるよう、番号を振り直してコピー
    seq = os.path.join(tmp, f"seq_{lv}")
    os.makedirs(seq)
    frames = sorted(f for f in os.listdir(d) if f.lower().endswith(".png"))
    for i, fn in enumerate(frames):
        shutil.copy(os.path.join(d, fn), os.path.join(seq, f"{i:05d}.png"))
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps),
        "-i", os.path.join(seq, "%05d.png"),
        "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), out,
    ], check=True)
    parts.append(out)

lst = os.path.join(tmp, "list.txt")
with open(lst, "w") as f:
    for p in parts:
        f.write(f"file '{p}'\n")

cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst]
if a.audio:
    cmd += ["-i", a.audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
cmd += ["-c:v", "copy", "-movflags", "+faststart", a.out]
subprocess.run(cmd, check=True)
shutil.rmtree(tmp)
print("完成:", a.out)
