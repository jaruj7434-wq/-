#!/usr/bin/env bash
# 「天ぷら油の火に水をかけると?」を一括制作する(すべて無料ツール)。再実行すれば続きから再開する。
# 使い方: BLENDER_PY=<bpy と numba を入れた Python> ML_PY=<style-bert-vits2 の Python> bash run_all.sh <作業フォルダ>
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:?作業フォルダを指定してください}"
BPY="${BLENDER_PY:-python3}"
MPY="${ML_PY:-python3}"
OUT="$HERE/../../assets/output"
mkdir -p "$WORK" "$OUT"
export SCALE="${SCALE:-50}" SAMPLES="${SAMPLES:-10}"  # 540x960 で描いて AI で 1080x1920 に拡大

[[ -f "$WORK/timings.json" ]] || "$MPY" "$HERE/tts.py" "$WORK"
for sim in steady erupt spray heat extinguisher lid; do
  if [[ ! -f "$WORK/sims/$sim/grid.json" ]]; then
    echo "=== simulate $sim $(date +%T)"
    "$BPY" "$HERE/sims.py" "$sim" "$WORK/timings.json" "$WORK/sims"
  fi
done
for shot in hook erupt section spray heat unattended extinguisher lid mayo outro; do
  echo "=== render $shot $(date +%T)"
  "$BPY" "$HERE/shots.py" "$shot" "$WORK/timings.json" "$WORK/sims" "$WORK/frames/$shot" 2>&1 | grep -E "Error|Traceback" || true
done
for shot in hook erupt section spray heat unattended extinguisher lid mayo outro; do
  echo "=== upscale $shot $(date +%T)"
  "$MPY" "$HERE/../mosquito_bite/upscale.py" "$WORK/frames/$shot" "$WORK/up/$shot" | tail -1
done
python3 "$HERE/compose.py" "$WORK" "$OUT/tempura-fire.mp4"
echo "=== done $(date +%T)"
