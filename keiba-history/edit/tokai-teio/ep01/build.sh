#!/bin/bash
# 第1話の編集スクリプト(Higgs Field sandbox_exec 上で実行)
# 前提: vid/01..15.mp4(Kling 4.0 の各カット)、nar2/NN.wav(seed_audio の各セリフ)、
#       captions.ass、Noto Sans JP Bold が ~/.fonts に入っていること
set -e
cd "$(dirname "$0")"
# ナレーション: 先頭の無音を削除、0.25秒を超える無音を0.25秒に短縮、1.05倍(ピッチ保持)、末尾0.15秒
mkdir -p nar2/fin
for f in nar2/??.wav; do sox "$f" nar2/fin/$(basename "$f") silence -l 1 0.03 -40d -1 0.25 -40d tempo -s 1.05 pad 0 0.15; done
sox nar2/fin/??.wav nar2/fin/narration_full.wav
# 各カットの尺 = 対応するセリフの長さ(最終カットのみ「つづく」用に +1.3秒)
: > cutdurs.txt
for i in $(seq -w 1 15); do d=$(soxi -D nar2/fin/$i.wav); [ $i = 15 ] && d=$(echo "$d + 1.3" | bc); echo $d >> cutdurs.txt; done
mapfile -t D < cutdurs.txt
mkdir -p seg
for i in $(seq 1 15); do
  n=$(printf %02d $i); d=${D[$((i-1))]}
  extra=""; [ $i -eq 3 ] && extra="crop=iw*0.90:ih*0.90,"   # カット3はフィルム枠を切り落とす
  ffmpeg -v error -y -i vid/$n.mp4 -t $d -an -vf "${extra}scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1,format=yuv420p" -c:v libx264 -preset medium -crf 18 seg/$n.mp4
done
: > list.txt; for i in $(seq -w 1 15); do echo "file 'seg/$i.mp4'" >> list.txt; done
ffmpeg -v error -y -f concat -safe 0 -i list.txt -c copy video_noaudio.mp4
sox nar2/fin/narration_full.wav narration_padded.wav pad 0 1.4
ffmpeg -v error -y -i video_noaudio.mp4 -i narration_padded.wav -vf "ass=captions.ass" -map 0:v -map 1:a \
  -c:v libx264 -preset medium -crf 19 -c:a aac -b:a 192k -ar 48000 -movflags +faststart tokai-teio_ep01_final.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 tokai-teio_ep01_final.mp4
