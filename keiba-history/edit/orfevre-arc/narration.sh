#!/usr/bin/env bash
# オルフェーヴル凱旋門賞 — 谷上ナレーション (台本 v5、1行1ファイル) をダウンロードして1本につなぐ
# 出力: assets/output/orfevre-arc/vo/line_XX.mp3, narration_full.m4a
set -euo pipefail
OUT="$(dirname "$0")/../../assets/output/orfevre-arc/vo"; mkdir -p "$OUT"; cd "$OUT"
B=https://d8j0ntlcm91z4.cloudfront.net/user_3IAIfINAmehvTGXEdm9EGpVegmO/hf_20261109_
JOBS=(
220053_827d9623-541b-4b15-9724-2120493a29e2 220053_ac500f8c-11b8-4bd9-a145-49ed60f4693a 220053_6fb10e35-9c8e-45c1-9192-d53d04502fc8
220053_e30e29da-84b6-4573-8d70-f57a77ae92fa 220053_553dd04f-8b18-407b-a501-15b9a6d06fb9 220053_467af4c7-7721-4855-a568-e94eb2663153
220053_9410ebc0-e73f-4dc3-ab6c-7c59045ce125 220053_4c9a807b-eb5d-450b-818c-d3e04f9605d1 220053_a1582e79-2fdd-4d5a-b0bd-aba23cdc0df4
220053_0d59f9fa-105e-40e5-8a4a-a9cd16dd38c0 220053_b920ccdf-0599-414e-8d87-c9676010ef73 220052_e945ac5c-7571-4e89-8d95-99a1cff4cfce
220117_e3dc49be-d1b5-45c1-8dfe-d2c5dd712b44 220116_4663c389-d13a-44ef-aa49-0082b0f74768 220117_a48907e6-2588-4b7e-b45d-cfb62461bacc
220117_64c9253b-92f6-43cd-8452-a9b80e5ff6f1 220116_19ce9813-d29e-4997-84a7-ac027ae39686 220116_8118de42-3b8e-4428-a2fb-d9076f5ead2b
)
# 各行のあとの間 (秒): つかみの後・名言の前後・名前を明かす前は長めに
GAPS=(0.6 1.0 0.6 0.5 0.5 0.9 0.5 0.8 0.9 0.6 0.8 0.6 0.6 0.8 0.6 0.8 1.4 1.0)
in=(); f=""; n=0
for i in "${!JOBS[@]}"; do
  k=$(printf %02d $((i+1)))
  [ -s line_$k.mp3 ] || curl -sS -o line_$k.mp3 "$B${JOBS[$i]}.mp3"
  in+=(-i line_$k.mp3)
  f+="[$n:a]aresample=48000,aformat=channel_layouts=mono,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,apad=pad_dur=${GAPS[$i]}[a$n];"; n=$((n+1))
done
cat=""; for j in $(seq 0 $((n-1))); do cat+="[a$j]"; done
ffmpeg -y -loglevel error "${in[@]}" -filter_complex "${f}${cat}concat=n=$n:v=0:a=1,loudnorm=I=-16:TP=-1.5[o]" -map "[o]" -c:a aac -b:a 192k narration_full.m4a
for k in $(seq -w 1 $n); do printf "%s %s\n" $k "$(ffprobe -v error -show_entries format=duration -of csv=p=0 line_$k.mp3)"; done > durations.txt
ffprobe -v error -show_entries format=duration -of csv=p=0 narration_full.m4a
