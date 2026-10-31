#!/bin/bash
# 天皇賞・秋 ショート 書き出し: render.py で映像 → ナレーション + BGM(ループ・小さめ) を合成
cd ~/aki/ed
python3 render.py > render.log 2>&1 || exit 1
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 video_noaudio.mp4)
ffmpeg -v error -y -i video_noaudio.mp4 -i ~/aki/vo2/narrationB.wav -stream_loop -1 -i ~/aki/bgm.m4a \
  -filter_complex "[1:a]aresample=48000,apad[n];[2:a]aresample=48000,volume=0.11,afade=t=out:st=$(python3 -c "print($DUR-1.5)"):d=1.5[b];[n][b]amix=inputs=2:duration=first:normalize=0,atrim=0:$DUR[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest tennosho_aki_v1.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 tennosho_aki_v1.mp4 >> render.log
echo done >> render.log
