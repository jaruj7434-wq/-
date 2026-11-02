#!/bin/bash
# Higgs Field(Seedance 2.0 Mini)で作った「ひよこ→ニワトリ→ダチョウ→ワニ→恐竜→ドラゴンが順番に1回ずつ鳴く」15秒の動画
# (calls_ai.mp4)から、鳴き声を1つずつ切り出す。声と声の間は約 -60dB でほぼ無音。
# 使い方: assets/source/dragon/sounds/ に calls_ai.mp4 を置いて実行
set -e
cd "$(dirname "$0")/../../assets/source/dragon/sounds"
ffmpeg -y -loglevel error -i calls_ai.mp4 -vn -ac 1 -ar 48000 calls.wav
cut() {   # 名前 開始秒 終了秒
  local fade
  fade=$(python3 -c "print(round($3-$2-0.3,3))")
  ffmpeg -y -loglevel error -i calls.wav \
    -af "atrim=$2:$3,asetpts=N/SR/TB,highpass=f=40,agate=threshold=0.02:ratio=8:attack=5:release=150,afade=t=in:d=0.02,afade=t=out:st=$fade:d=0.3" \
    -ac 1 -ar 48000 "$1.wav"
}
cut voice1 0.22 0.75     # ひよこ(かわいいピヨピヨ)
cut voice2 1.50 2.95     # ニワトリ(コケコッコー)
cut voice3 3.42 4.65     # ダチョウ(低いうなり)
cut voice4 5.40 7.98     # ワニ(シャーッという威嚇)
cut voice5 8.15 10.95    # 恐竜(太い咆哮)
cut voice6 11.12 14.60   # ドラゴン(一番低く凶暴な咆哮)
