#!/bin/bash
# Higgs Field(Seedance 2.0 Mini)で作った「古い車から新しい車へ順番にエンジンをかける」音つき動画から、
# 進化したときに鳴らすエンジン音を切り出す。 voice{st}.wav = st 段階目(3代目…16代目)に進化したときの音
cd "$(dirname "$0")/../../assets/source/crown"
mkdir -p sounds
ffmpeg -y -loglevel error -i engine_src.mp4 -vn -ac 1 -ar 48000 engine_src.wav
cut() { ffmpeg -y -loglevel error -ss $2 -t $3 -i engine_src.wav -af "afade=t=in:d=0.02,afade=t=out:st=$(python3 -c "print($3 - 0.25)"):d=0.25" sounds/voice$1.wav; }
cut 1 2.9 1.2     # 1950〜60年代:ポンポンという古いエンジン
cut 2 4.1 0.9     # 昔のクラクション「プップー」
cut 3 5.1 1.4     # 1970〜80年代:低くうなるエンジン
cut 4 7.5 1.4     # 1990年代:なめらかにふかす音
cut 5 10.0 1.4    # 2000年代:力強いV6の「ブォーン」
cut 6 10.9 1.4    # 2010年代:さらに力強く
cut 7 13.35 1.2   # 2020年代:静かなハイブリッドの起動音
