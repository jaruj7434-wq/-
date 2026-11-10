#!/usr/bin/env bash
# オルフェーヴル凱旋門賞 v12〜 の BGM (冒頭タイトルと 01 をカットし、「もしも〜」から始める構成)。
# 実行場所: サンドボックス ~/orfed (clips/cueA..E.m4a。job は prompts/orfevre-arc/production-log.md)
#   0〜8.3秒  : E 幻のゴールの夢の曲 (atempo 0.68、0秒目から等倍の音量)
#   7.45秒〜  : A 後半 (A の 8.1秒以降。最高潮 → 敗れる瞬間 約27.5秒で止まる)
#   30.51秒〜 : B 涙 (-4dB) / 61.01秒〜: C 有馬記念の勝利 / 82.51秒〜: D 悔恨 → 名前の所で盛り上がる
set -euo pipefail
cd "$(dirname "$0")"
ffmpeg -y -loglevel error -i clips/cueA.m4a -i clips/cueB.m4a -i clips/cueC.m4a -i clips/cueD.m4a -i clips/cueE.m4a -filter_complex \
  "[0]aresample=48000,atempo=0.89,atrim=start=8.1,asetpts=PTS-STARTPTS,volume=1.3,afade=t=in:d=0.8,adelay=7450:all=1[p2];[4]aresample=48000,atempo=0.68,volume=1.0,afade=t=out:st=7.5:d=0.8[e];[1]aresample=48000,volume=-4dB,afade=t=in:d=1.5,adelay=30510:all=1[b];[2]aresample=48000,afade=t=in:d=0.3,adelay=61010:all=1[c];[3]aresample=48000,afade=t=in:d=1.5,adelay=82510:all=1[d];[e][p2][b][c][d]amix=inputs=5:normalize=0:duration=longest,atrim=0:107.5,alimiter=limit=0.9" \
  -c:a aac -b:a 192k clips/bgm_mix6.m4a
# 書き出し: PRE=0 TANIUE='{"3":"T03c","8":"I08","8k":"k","9":"I09","10":"T10c","12":"T12c","16":"I16","16k":"k","tail":"V19c"}' \
#   SPLIT='{"3":[3.45,"H03"]}' WHATIF=1 NOSORA=1 L1V3=1 SKIP1=1 BGM=clips/bgm_mix6.m4a BGM_VOL=0.32 DUCK=1 python3 render_orf.py orfevre_arc_v12.mp4
