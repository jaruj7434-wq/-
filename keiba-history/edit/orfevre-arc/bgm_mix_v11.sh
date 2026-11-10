#!/usr/bin/env bash
# オルフェーヴル凱旋門賞 v11〜 の BGM (01 を「世界一まで、あと一歩、届かなかった。」にして約0.5秒のびた構成)。
# 実行場所: サンドボックス ~/orfed (clips/cueA..E.m4a。job は prompts/orfevre-arc/production-log.md)
#   0〜6.11秒  : A 前半 (atempo 0.89、タイトル中 ×6・その後 ×1.8)
#   5.81〜14.6秒: E 幻のゴールの夢の曲 (atempo 0.68、×0.75)
#   13.56秒〜  : A 後半 (A の 8.1秒以降。最高潮 → 敗れる瞬間 約33.5秒で止まる)
#   36.62秒〜  : B 涙 (-4dB) / 67.12秒〜: C 有馬記念の勝利 / 88.62秒〜: D 悔恨 → 名前の所で盛り上がる
set -euo pipefail
cd "$(dirname "$0")"
ffmpeg -y -loglevel error -i clips/cueA.m4a -i clips/cueB.m4a -i clips/cueC.m4a -i clips/cueD.m4a -i clips/cueE.m4a -filter_complex \
  "[0]aresample=48000,atempo=0.89,asplit=2[a0][a1];[a0]atrim=0:6.11,volume='if(lt(t,2.6),6,1.8)':eval=frame,afade=t=out:st=5.61:d=0.5[p1];[a1]atrim=start=8.1,asetpts=PTS-STARTPTS,volume=1.3,afade=t=in:d=0.8,adelay=13560:all=1[p2];[4]aresample=48000,atempo=0.68,volume=0.75,afade=t=in:d=0.4,afade=t=out:st=7.8:d=0.8,adelay=5810:all=1[e];[1]aresample=48000,volume=-4dB,afade=t=in:d=1.5,adelay=36620:all=1[b];[2]aresample=48000,afade=t=in:d=0.3,adelay=67120:all=1[c];[3]aresample=48000,afade=t=in:d=1.5,adelay=88620:all=1[d];[p1][e][p2][b][c][d]amix=inputs=6:normalize=0:duration=longest,atrim=0:113.5,alimiter=limit=0.9" \
  -c:a aac -b:a 192k clips/bgm_mix5.m4a
# 声: vo/line_02.mp3 = 02b「もしも〜」だけ (vo/_new_02b.wav を mp3 に)
# 書き出し: TANIUE='{"3":"T03c","8":"I08","8k":"k","9":"I09","10":"T10c","12":"T12c","16":"I16","16k":"k","tail":"V19c"}' \
#   SPLIT='{"3":[3.45,"H03"]}' WHATIF=1 NOSORA=1 L1V3=1 BGM=clips/bgm_mix5.m4a BGM_VOL=0.32 DUCK=1 python3 render_orf.py orfevre_arc_v11.mp4
