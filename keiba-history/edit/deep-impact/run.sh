#!/bin/bash
# ディープインパクト編 書き出し: build.py → concat → ナレーションと字幕(ASS)を合成
# vid/NN.mp4 (vids.txt の対応表どおり) と ~/deep/el/v4/fin/NN.wav が必要。フォントは ~/.fonts/NotoSansJP-Bold.otf
cd ~/deep/ed
python3 build.py > build.log 2>&1 || exit 1
ffmpeg -v error -y -f concat -safe 0 -i list.txt -c copy video_noaudio.mp4
ffmpeg -v error -y -i video_noaudio.mp4 -i narration_full.wav -vf "ass=captions.ass:fontsdir=$HOME/.fonts" -c:v libx264 -preset medium -crf 19 -c:a aac -b:a 192k -ar 48000 -shortest deep_impact.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 deep_impact.mp4 >> build.log
echo done >> build.log
