#!/usr/bin/env bash
# テロップ用フォント(いずれも SIL Open Font License)を tools/showa_film/fonts/ に用意する
#  - Dela Gothic One      : 昭和の看板・タイトル風の極太ゴシック
#  - しっぽり明朝 B1       : 古い活字・映画字幕風の明朝
#  - Kaisei Tokumin       : 昭和の広告・新聞見出しの「特太明朝」風(スーパー・題字)
#  - Zen Antique          : 金属活字のかすれた明朝風(字幕・注記)
#  - Yuji Syuku           : 筆で書いた文字(手書きのフリップ・封筒)
# npm の @fontsource パッケージから取り出し、TTF に変換する
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p fonts && work=$(mktemp -d)
pip install -q fonttools >/dev/null 2>&1 || true
(cd "$work" && npm pack -s @fontsource/dela-gothic-one @fontsource/shippori-mincho-b1 \
    @fontsource/kaisei-tokumin @fontsource/zen-antique @fontsource/yuji-syuku >/dev/null \
  && for f in *.tgz; do tar xzf "$f" --one-top-level; done)
python3 - "$work" <<'PY'
import sys, glob
from fontTools.ttLib import TTFont
w = sys.argv[1]
pairs = {
    "dela-gothic-one-japanese-400-normal.woff": "DelaGothicOne-Regular.ttf",
    "shippori-mincho-b1-japanese-800-normal.woff": "ShipporiMinchoB1-ExtraBold.ttf",
    "shippori-mincho-b1-japanese-400-normal.woff": "ShipporiMinchoB1-Regular.ttf",
    "kaisei-tokumin-japanese-800-normal.woff": "KaiseiTokumin-ExtraBold.ttf",
    "zen-antique-japanese-400-normal.woff": "ZenAntique-Regular.ttf",
    "yuji-syuku-japanese-400-normal.woff": "YujiSyuku-Regular.ttf",
}
for src, dst in pairs.items():
    f = glob.glob(f"{w}/*/package/files/{src}")[0]
    t = TTFont(f); t.flavor = None; t.save(f"fonts/{dst}"); print("ok", dst)
PY
rm -rf "$work"
