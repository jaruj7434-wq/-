#!/usr/bin/env bash
# 「凍ったフロントガラスにお湯はNG」を一括制作する(すべて無料ツール)。再実行すれば続きから再開する。
# 使い方: BLENDER_PY=<bpy と numba を入れた Python> ML_PY=<style-bert-vits2 の Python> bash run_all.sh <作業フォルダ>
#   <作業フォルダ>/hdri/ に Poly Haven の HDRI(CC0)を置いておく:passendorf_snow_1k.exr
#   (Hugging Face の leodriesch/open-hdri-1k から取得できる)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:?作業フォルダを指定してください}"
BPY="${BLENDER_PY:-python3}"
MPY="${ML_PY:-python3}"
OUT="$HERE/../../assets/output"
mkdir -p "$WORK" "$OUT"
export SCALE="${SCALE:-50}" SAMPLES="${SAMPLES:-10}" VOLUME_STEP="${VOLUME_STEP:-2}"  # 540x960 で描いて AI で 1080x1920 に拡大
SHOTS="hook morning stopwatch layers thermal chip lukewarm wiper defroster spray cover drive"

[[ -f "$WORK/timings.json" ]] || "$MPY" "$HERE/tts.py" "$WORK"
[[ -f "$WORK/maps/spray_melt.png" ]] || "$BPY" "$HERE/maps.py" "$WORK/maps"
echo "=== simulate steam $(date +%T)"
"$BPY" "$HERE/sims.py" "$WORK/timings.json" "$WORK/sims"
for shot in $SHOTS; do
  echo "=== render $shot $(date +%T)"
  "$BPY" "$HERE/shots.py" "$shot" "$WORK" "$WORK/frames/$shot" 2>&1 | grep -E "Error|Traceback" || true
done
for shot in $SHOTS; do
  echo "=== upscale $shot $(date +%T)"
  "$MPY" "$HERE/../mosquito_bite/upscale.py" "$WORK/frames/$shot" "$WORK/up/$shot" | tail -1
done
[[ -z "${NARRATION_DIR:-}" ]] || python3 "$HERE/fit_narration.py" "$WORK" "$NARRATION_DIR"
python3 "$HERE/compose.py" "$WORK" "$OUT/frozen-windshield.mp4"
echo "=== done $(date +%T)"
