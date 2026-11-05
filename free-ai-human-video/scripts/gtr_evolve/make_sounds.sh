#!/bin/bash
# Higgs Field(Seedance 2.0 Mini)で作った「古いスポーツカーから最新型へ順番にエンジンをふかす」音つき動画から音を切り出す。
# ここで切り出した素材を gtr_evolve.py の make_voices() で加工して、かわいい音 → イカついエンジン音の順にする
cd "$(dirname "$0")/../../assets/source/gtr"
mkdir -p sounds
ffmpeg -y -loglevel error -i engine_src.mp4 -vn -ac 1 -ar 48000 engine_src.wav
cut() { ffmpeg -y -loglevel error -ss $2 -t $3 -i engine_src.wav -af "afade=t=in:d=0.02,afade=t=out:st=$(python3 -c "print($3 - 0.25)"):d=0.25" sounds/voice$1.wav; }
cut 1 4.1 1.1     # 1960年代の直6:かん高くふかす(高くして「かわいい小さなエンジン」に使う)
cut 2 4.3 1.3     # 1960年代の直6:そのまま
cut 3 6.1 1.6     # ツインターボをふかして「プシュー」
cut 4 8.5 1.4     # 直6ツインターボのかん高いうなり
cut 5 11.5 1.5    # 現代のV6ツインターボの「ブォォーン」+パンパンというアフターファイア
cut 7 13.5 1.4    # 最後のアイドリング(発表会の演出で小さく鳴らす)
