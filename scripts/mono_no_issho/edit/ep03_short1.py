"""第3話ショート①「ペットボトルの意外な一生」(9:16・約43秒)

ep02_short1.py の組み立て処理を使い、カット・字幕・締めの文言だけ差し替える。
雑学（最初は醤油／回収ボックスの3割はごみ／工場の工程）をテンポよく並べ、
最後は3択クイズを答えを出さずに止めて、答えは本編へ誘導。

  python3 scripts/mono_no_issho/edit/ep03_short1.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ep03_build  # noqa: F401  第3話の設定（出力先・REGISTRY）を読み込む
import ep02_short1 as S

S.configure("short1_pet")
S.TITLE = ["ペットボトルの", "意外な一生"]
S.SEGS = [
    ("2d:history", 5, None, 0, ["1977年", "醤油"]),
    ("2d:rb_trash", 12, None, 0, ["3割", "ごみ"]),
    ("3d:p04_bale_conveyor", 14, None, 0, ["ベール"]),
    ("3d:p05_flakes", 15, None, 0, ["フレーク"]),
    ("3d:p06_pellets", 16, (0.0, 4.1), 0, ["ペレット"]),
    ("3d:p03_cap_label", 1, None, 0, ["何になっている"]),
    ("2d:quiz_q", 2, None, 0, ["ペットボトル", "フタ", "シャツ"]),
]
S.CAPS = {}
S.CTA_Y = (330, 450)   # 3択の図の上に置く
S.CTA_AT = 3.6   # 3択がすべて出ている所で止める（最後はフェードで暗い）
S.CTA = ["A・B・C", "正解は{\\c&H00D7FF&}どれ{\\c&HFFFFFF&}…？"]
S.CTA2 = ["フルはコメント欄から！", "▼ 本編で答え合わせ"]

if __name__ == "__main__":
    S.main()
