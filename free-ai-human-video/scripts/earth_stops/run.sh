#!/usr/bin/env bash
# 「もしも地球が1秒止まったら?」を一括制作する(すべて無料ツール)。
# 使い方: bash run.sh <作業フォルダ> [--preview]
#   事前に: python -m venv venv && venv/bin/pip install bpy pyopenjtalk-plus numpy
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:?作業フォルダを指定してください}"
PY="${PYTHON:-python3}"
OUT="$HERE/../../assets/output"
mkdir -p "$WORK" "$OUT"

"$PY" "$HERE/tts.py" "$WORK"
if [[ "${2:-}" == "--preview" ]]; then
  "$PY" "$HERE/scene.py" "$WORK/timings.json" "$WORK/preview" --preview
  exit 0
fi
"$PY" "$HERE/scene.py" "$WORK/timings.json" "$WORK/frames"
"$PY" "$HERE/compose.py" "$WORK" "$OUT/earth-stops-1sec.mp4"
