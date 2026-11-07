#!/usr/bin/env bash
# Preview (no audio) of the reversed-order opening + conversation.
# Clips: assets/output/deep-dodeuce/v2/ (Higgs Field jobs listed in prompts/deep-dodeuce/production-log.md)
set -euo pipefail
cd "$(dirname "$0")/../../assets/output/deep-dodeuce/v2"
L="V01 V02 V03 V04 V05 V06 V07 V08 V09 V07b_C6 V10 V11"
in=""; f=""; i=0
for c in $L; do in="$in -i $c.mp4"; f="$f[$i:v]scale=720:1280,setsar=1,fps=30[v$i];"; i=$((i+1)); done
cc=""; for j in $(seq 0 $((i-1))); do cc="$cc[v$j]"; done
ffmpeg -y -loglevel error $in -filter_complex "$f${cc}concat=n=$i:v=1:a=0[o]" -map "[o]" -c:v libx264 -crf 22 -pix_fmt yuv420p ../preview_v2.mp4
