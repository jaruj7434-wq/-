#!/usr/bin/env bash
# 「地震のとき、エレベーターにいたら?」を一括制作する(すべて無料ツール)。再実行すれば続きから再開する。
# 使い方: BLENDER_PY=... ML_PY=... bash run_all.sh <作業フォルダ>
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:?作業フォルダを指定してください}"
BPY="${BLENDER_PY:-python3}"
MPY="${ML_PY:-python3}"
OUT="$HERE/../../assets/output"
mkdir -p "$WORK" "$OUT"
export SCALE="${SCALE:-67}" SAMPLES="${SAMPLES:-14}"
SHOTS="shake buttons nearest auto stuck doors_no bell blackout clock cabinet outro"

[[ -f "$WORK/timings.json" ]] || "$MPY" "$HERE/tts.py" "$WORK"
for shot in $SHOTS; do
  echo "=== render $shot $(date +%T)"
  "$BPY" "$HERE/render_shot.py" "$shot" "$WORK/timings.json" "$WORK/frames/$shot" 2>&1 | grep -E "^\[|Error|Traceback" || true
done
for shot in $SHOTS; do
  echo "=== upscale $shot $(date +%T)"
  "$MPY" "$HERE/../mosquito_bite/upscale.py" "$WORK/frames/$shot" "$WORK/up/$shot" | tail -1
done
python3 "$HERE/compose.py" "$WORK" "$OUT/elevator-earthquake.mp4"
echo "=== done $(date +%T)"
