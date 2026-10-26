# 賭け金別 編集スクリプト (Higgs sandbox の ~/kakekin/ed で実行)
# 前提: vid/01..08.mp4 (Wan 2.7 出力), voice.wav (s1..s8 を連結), captions.ass (mkass.py で生成)
set -e
D=(3.532042 4.158042 4.135167 2.621979 2.385958 2.591604 2.527771 5.838667)
mkdir -p seg; : > list.txt
for i in $(seq 1 8); do n=$(printf %02d $i); d=${D[$((i-1))]}
  ffmpeg -v error -y -i vid/$n.mp4 -t $d -an -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1,format=yuv420p" -c:v libx264 -preset medium -crf 18 seg/$n.mp4
  echo "file 'seg/$n.mp4'" >> list.txt; done
ffmpeg -v error -y -f concat -safe 0 -i list.txt -c copy video_noaudio.mp4
ffmpeg -v error -y -i video_noaudio.mp4 -i voice.wav -vf "ass=captions.ass:fontsdir=$HOME/.fonts" -c:v libx264 -preset medium -crf 18 -c:a aac -b:a 192k -ar 48000 -shortest kakekin.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 kakekin.mp4
