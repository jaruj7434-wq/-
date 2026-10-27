#!/usr/bin/env bash
# 「蚊に刺された瞬間」を一括制作する(すべて無料ツール)。途中で止まっても、再実行すれば続きから再開する。
# 使い方: bash run_all.sh <作業フォルダ>
#   BLENDER_PY: bpy を入れた Python(既定 python3)/ ML_PY: style-bert-vits2・spandrel を入れた Python
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:?作業フォルダを指定してください}"
BPY="${BLENDER_PY:-python3}"
MPY="${ML_PY:-python3}"
OUT="$HERE/../../assets/output"
mkdir -p "$WORK" "$OUT"
export SCALE="${SCALE:-50}" SAMPLES="${SAMPLES:-10}"

[[ -f "$WORK/timings.json" ]] || "$MPY" "$HERE/tts.py" "$WORK"
for shot in surface_approach surface_bend tip_closeup section_search vessel section_react surface_withdraw; do
  echo "=== render $shot $(date +%T)"
  "$BPY" "$HERE/render_shot.py" "$shot" "$WORK/timings.json" "$WORK/frames/$shot" 2>&1 | grep -E "^\[|Error|Traceback" || true
done
for shot in surface_approach surface_bend tip_closeup section_search vessel section_react surface_withdraw; do
  echo "=== upscale $shot $(date +%T)"
  "$MPY" "$HERE/upscale.py" "$WORK/frames/$shot" "$WORK/up/$shot" | tail -1
done
python3 "$HERE/compose.py" "$WORK" "$OUT/mosquito-bite.mp4"
echo "=== done $(date +%T)"
