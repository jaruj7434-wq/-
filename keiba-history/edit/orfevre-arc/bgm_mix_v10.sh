#!/usr/bin/env bash
# オルフェーヴル凱旋門賞 v10〜 の BGM (「ソラを使って、負けた。」を外し、01 → すぐ「もしも」へつなぐ構成)。
# 実行場所: サンドボックス ~/orfed (clips/cueA..E.m4a。job は prompts/orfevre-arc/production-log.md)
#   0〜5.6秒   : A 前半 (atempo 0.89、タイトル中 ×6・その後 ×1.8)
#   5.3〜14.1秒: E 幻のゴールの夢の曲 (atempo 0.68、×0.75)
#   13.05秒〜  : A 後半 (A の 8.1秒以降。最高潮 → 敗れる瞬間 約33秒で止まる)
#   36.11秒〜  : B 涙 (-4dB) / 66.61秒〜: C 有馬記念の勝利 / 88.11秒〜: D 悔恨 → 名前の所で盛り上がる
set -euo pipefail
cd "$(dirname "$0")"
ffmpeg -y -loglevel error -i clips/cueA.m4a -i clips/cueB.m4a -i clips/cueC.m4a -i clips/cueD.m4a -i clips/cueE.m4a -filter_complex \
  "[0]aresample=48000,atempo=0.89,asplit=2[a0][a1];[a0]atrim=0:5.6,volume='if(lt(t,2.6),6,1.8)':eval=frame,afade=t=out:st=5.1:d=0.5[p1];[a1]atrim=start=8.1,asetpts=PTS-STARTPTS,volume=1.3,afade=t=in:d=0.8,adelay=13050:all=1[p2];[4]aresample=48000,atempo=0.68,volume=0.75,afade=t=in:d=0.4,afade=t=out:st=7.8:d=0.8,adelay=5300:all=1[e];[1]aresample=48000,volume=-4dB,afade=t=in:d=1.5,adelay=36110:all=1[b];[2]aresample=48000,afade=t=in:d=0.3,adelay=66610:all=1[c];[3]aresample=48000,afade=t=in:d=1.5,adelay=88110:all=1[d];[p1][e][p2][b][c][d]amix=inputs=6:normalize=0:duration=longest,atrim=0:113,alimiter=limit=0.9" \
  -c:a aac -b:a 192k clips/bgm_mix4.m4a
# 声: vo/line_02.mp3 = 02b「もしも〜」だけ (vo/_new_02b.wav を mp3 に)
# 書き出し: TANIUE='{"3":"T03c","8":"I08","8k":"k","9":"I09","10":"T10c","12":"T12c","16":"I16","16k":"k","tail":"V19c"}' \
#   SPLIT='{"3":[3.45,"H03"]}' WHATIF=1 NOSORA=1 BGM=clips/bgm_mix4.m4a BGM_VOL=0.32 DUCK=1 python3 render_orf.py orfevre_arc_v10.mp4
