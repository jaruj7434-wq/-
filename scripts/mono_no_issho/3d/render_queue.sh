#!/usr/bin/env bash
# 使い方: scripts/mono_no_issho/3d/render_queue.sh h13_worn_coin h14_melt ...
# 各ショットを全フレーム書き出し → assets/output/mono_no_issho/ep01/clips/<name>.mp4
set -u
cd "$(dirname "$0")/../../.."
OUT=assets/output/mono_no_issho/ep01
mkdir -p "$OUT/clips"
for s in "$@"; do
  if [ -f "$OUT/clips/$s.mp4" ]; then echo "skip $s"; continue; fi
  echo "[$(date +%T)] render $s"
  rm -f "$OUT/3d/$s"/f_*.png
  python3 "scripts/mono_no_issho/3d/shots/$s.py" > "$OUT/3d/$s.log" 2>&1 || { echo "FAIL $s"; continue; }
  ffmpeg -y -loglevel error -framerate 24 -i "$OUT/3d/$s/f_%04d.png" -c:v libx264 -pix_fmt yuv420p -crf 18 "$OUT/clips/$s.mp4" \
    && echo "[$(date +%T)] done $s"
done
