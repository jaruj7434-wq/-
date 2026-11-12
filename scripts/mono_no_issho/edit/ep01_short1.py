"""第1話ショート①「1円玉、実は作られてない？」(9:16・約40秒)

ep02_short1.py の組み立て処理をそのまま使い、カット・字幕・締めの文言だけ差し替える。
最後は「造幣局の公式アカウントが、こう投稿しました。」で止め、投稿の中身は本編へ誘導。

  python3 scripts/mono_no_issho/edit/ep01_short1.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ep02_short1 as S

S.configure("short1_ichien")
S.TITLE = ["1円玉、", "実は作られてない？"]
S.SEGS = [
    ("3d:h01_wallet", 1, None, 0, ["10年間", "作られていません"]),
    ("3d:h14_melt@0-5", 2, None, 0, ["溶かされます"]),
    ("2d:rumor", 25, None, 0, ["3円"]),
    ("2d:cost", 26, None, 0, ["公表していません", "偽造"]),
    ("2d:chart", 29, None, 0, ["約27億枚", "55万枚"]),
    ("3d:h11_factory_line", 32, None, 0, ["2026年の夏", "こう投稿"]),
]
S.CAPS = {1: ["実はこの1円玉", "10年間\\Nほとんど作られて\\Nいませんでした"],
          32: ["ところが2026年の夏", "造幣局の公式アカウントが", "こう投稿しました…"]}
S.CTA = ["造幣局の公式アカウントが", "投稿した{\\c&H00D7FF&}“ひと言”{\\c&HFFFFFF&}とは…？"]
S.CTA2 = ["フルはコメント欄から！", "▼ 本編で答え合わせ"]

if __name__ == "__main__":
    S.main()
