#!/usr/bin/env bash
# オルフェーヴル凱旋門賞の BGM (v7〜)。場面ごとに作った4つの曲 (同じ調・テンポ) を映像の時間に合わせてつなぐ。
# 実行場所: サンドボックス ~/orfed (clips/cueA..D.m4a は Higgs の job の結果。job は prompts/orfevre-arc/production-log.md)
#   0〜3秒   : 冒頭タイトルは衝撃音だけ (BGM なし)
#   3秒〜    : A 緊張 → 気高いホルン → 直線の攻防で最高潮 → 敗れる瞬間に止まる
#   31秒〜   : B 涙・名言の場面 (ピアノとチェロ、-4dB)
#   61.5秒〜 : C 有馬記念の勝利
#   83秒〜   : D 悔恨 → 名前を明かす所で盛り上がる → 静かに終わる
set -euo pipefail
cd "$(dirname "$0")"
ffmpeg -y -loglevel error -i clips/cueA.m4a -i clips/cueB.m4a -i clips/cueC.m4a -i clips/cueD.m4a -filter_complex \
  "[0]aresample=48000,adelay=3000:all=1[a];[1]aresample=48000,volume=-4dB,afade=t=in:d=1.5,adelay=31000:all=1[b];[2]aresample=48000,afade=t=in:d=0.3,adelay=61500:all=1[c];[3]aresample=48000,afade=t=in:d=1.5,adelay=83000:all=1[d];[a][b][c][d]amix=inputs=4:normalize=0:duration=longest,atrim=0:107.4" \
  -c:a aac -b:a 192k clips/bgm_mix.m4a
# 書き出し: TANIUE='...' SPLIT='{"3":[3.45,"H03"]}' BGM=clips/bgm_mix.m4a BGM_VOL=0.32 DUCK=1 python3 render_orf.py orfevre_arc_v7.mp4
