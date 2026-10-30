#!/bin/bash
# Higgs Field で生成した「牛たちが順番に鳴く」動画(moo_ai.mp4)から、鳴き声を一声ずつ切り出す。
# 使い方: assets/source/cow/sounds/ に moo_ai.mp4 を置いて実行
set -e
cd "$(dirname "$0")/../../assets/source/cow/sounds"
ffmpeg -y -loglevel error -i moo_ai.mp4 -vn -ac 1 -ar 48000 moo_ai.wav
cut() {   # 名前 開始秒 終了秒
  local len fade
  len=$(python3 -c "print($3-$2)")
  fade=$(python3 -c "print(round($3-$2-0.25,3))")
  ffmpeg -y -loglevel error -i moo_ai.wav \
    -af "atrim=$2:$3,asetpts=N/SR/TB,highpass=f=70,agate=threshold=0.02:ratio=8:attack=5:release=120,afade=t=in:d=0.02,afade=t=out:st=$fade:d=0.25" \
    -ac 1 -ar 48000 "$1.wav"
}
cut calf_newborn 0.36 1.45   # 生まれたての子牛
cut calf_0 2.22 3.72         # 子牛
cut calf_1 4.93 7.78         # 若い牛
cut cow_0 7.99 10.95         # 大人の牛
cut bull_0 11.77 15.10       # 巨大な雄牛
