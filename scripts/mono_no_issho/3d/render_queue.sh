#!/usr/bin/env bash
# 使い方: scripts/mono_no_issho/3d/render_queue.sh h13_worn_coin h14_melt ...
#        EP=ep02 scripts/mono_no_issho/3d/render_queue.sh k02_store_stand ...   (第2話。既定 EP=ep01)
# 30フレームずつ別プロセスで書き出し(EEVEE/ソフトウェアGLのクラッシュ対策)。
# 既存フレームは残して続きから再開。完成したら clips/<name>.mp4 に書き出す。
set -u
cd "$(dirname "$0")/../../.."
EP=${EP:-ep01}
export EP   # common.py もこの話数の出力先に書く
OUT=assets/output/mono_no_issho/$EP
CHUNK=${CHUNK:-30}
STEP=${STEP:-1}   # STEP=2 で1フレームおき(12fps)に描いて24fpsへ複製
mkdir -p "$OUT/clips" "$OUT/3d"
for s in "$@"; do
  if [ -f "$OUT/clips/$s.mp4" ]; then echo "skip $s"; continue; fi
  py="scripts/mono_no_issho/3d/shots/$s.py"
  F=$(grep -oE '^(S\.)?FRAMES = [0-9]+' "$py" | grep -oE '[0-9]+$' | tail -1); F=${F:-120}
  echo "[$(date +%T)] render $s ($F frames)"
  mkdir -p "$OUT/3d/$s"
  fails=0
  last=""
  while :; do
    first=""
    for ((i=1; i<=F; i+=STEP)); do
      [ -f "$OUT/3d/$s/f_$(printf %04d $i).png" ] || { first=$i; break; }
    done
    [ -z "$first" ] && break
    # 前回より先に進んでいれば失敗回数をリセット（終了時だけ落ちるケース対策）
    [ "$first" != "$last" ] && fails=0; last=$first
    end=$(( first + CHUNK * STEP - 1 )); [ $end -gt $F ] && end=$F
    if ! python3 "$py" --start "$first" --end "$end" --step "$STEP" >> "$OUT/3d/$s.log" 2>&1; then
      fails=$((fails+1)); echo "  crash at ~$first (retry $fails)"
      [ $fails -ge 8 ] && { echo "FAIL $s"; continue 2; }
    fi
  done
  ffmpeg -y -loglevel error -framerate $((24 / STEP)) -pattern_type glob -i "$OUT/3d/$s/f_*.png" -r 24 -c:v libx264 -pix_fmt yuv420p -crf 18 "$OUT/clips/$s.mp4" \
    && echo "[$(date +%T)] done $s"
done
