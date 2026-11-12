"""第1話ショート①「1円玉の意外なヒミツ」(9:16・約43秒)

ep02_short1.py の組み立て処理をそのまま使い、カット・字幕・締めの文言だけ差し替える。
身近な雑学をテンポよく並べ、最後は「自動販売機です。」で止めて、使えない理由は本編へ誘導。

  python3 scripts/mono_no_issho/edit/ep01_short1.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ep02_short1 as S

S.configure("short1_ichien")
S.TITLE = ["1円玉の", "意外なヒミツ"]
S.SEGS = [
    ("3d:h01_wallet", 0, None, 0, ["1円玉"]),
    ("2d:per_capita", 16, None, 0, ["300枚"]),
    ("3d:h09_drawer", 17, None, 0, ["どこにある"]),
    ("3d:h09_piggy", 18, None, 0, ["家の中"]),
    ("3d:h09_piggy", 19, (0.0, 0.85), 0, ["貯金箱"], ["貯金箱"]),
    ("3d:h09_drawer", 19, (1.30, 2.00), 0, ["引き出し"], ["引き出し"]),
    ("3d:h09_cupholder", 19, (2.48, 4.02), 0, ["ドリンクホルダー"], ["車のドリンクホルダー"]),
    ("3d:h12_counter_pile", 34, None, 0, ["断ることができます"]),
    ("2d:law20", 35, None, 0, ["20枚まで"]),
    ("2d:law_damage", 40, (1.01, 11.37), 0, ["法律で禁止", "拘禁刑", "罰金"],
     ["1円玉を溶かしたり", "穴を開けたりするのは", "法律で禁止", "1年以下の拘禁刑か", "20万円以下の罰金"]),
    ("3d:h10_vending", 21, None, 0, ["行けない場所", "自動販売機"]),
]
S.CAPS = {}
S.CTA_AT = 1.0   # 自販機の全体が映っている所で止める
S.CTA = ["自販機で1円玉が", "使えない{\\c&H00D7FF&}“理由”{\\c&HFFFFFF&}とは…？"]
S.CTA2 = ["フルはコメント欄から！", "▼ 本編で答え合わせ"]

if __name__ == "__main__":
    S.main()
