#!/bin/bash
# たくさんのシードで物理だけ計算して、最後の1匹のゴール時刻を一覧にする(4つずつ並べて計算)
# 使い方: bash search3d.sh 開始シード 終了シード > 結果.txt
PY=${PY:-python}
seq $1 $2 | xargs -P 4 -I{} sh -c "$PY $(dirname $0)/race3d.py sim --seed {} 2>/dev/null | grep '\"finish\"' | sed 's/^/{} /'"
