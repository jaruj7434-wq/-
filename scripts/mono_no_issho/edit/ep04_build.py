"""第4話「着なくなった服はどこへ行く？」を通しで組み立てる。

第1話の ep01_build.py の仕組み(ナレーション→尺決め、3D/2D、字幕、BGM)をそのまま使い、
カット表・出力先・2D図解だけ差し替える。

  python3 scripts/mono_no_issho/edit/ep04_build.py --list
  python3 scripts/mono_no_issho/edit/ep04_build.py                # 仮ナレーション(Open JTalk)
  python3 scripts/mono_no_issho/edit/ep04_build.py --voice el     # ElevenLabs v4 ナレーション
  python3 scripts/mono_no_issho/edit/ep04_build.py --manifest     # ElevenLabs 用の行リストを書き出す
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ep01_build as B
import graphics2d_ep04 as G4

B.OUT = B.ROOT / "assets/output/mono_no_issho/ep04"
B.CLIPS = B.OUT / "clips"
B.WORK = B.OUT / "edit_work"
B.HF_MANIFEST = B.ROOT / "prompts/mono_no_issho/ep04_narration_lines.json"
B.HF_DIRS = {"hf": (B.WORK / "hf_tts", "wav"), "el": (B.WORK / "el_tts", "mp3")}
B.G.REGISTRY.clear()
B.G.REGISTRY.update(G4.REGISTRY)

B.EDL = [
    # 1. フック
    ("3d:c01_closet", ["クローゼットの奥で、眠っている服。",
                       "この1年で、一度も着なかった服。あなたは、何枚ありますか？"], 5),
    ("2d:unworn", ["実は、日本人の平均で、約25枚。",
                   "その服たちは、手放されたあと、どこへ行くのでしょうか。"], 6),
    ("2d:title", [], 3.5),
    # 2. 誕生
    ("3d:c02_fabric_cut", ["服を1着つくるのに、出るCO2は、約25.5キロ。"], 5),
    ("2d:footprint", ["使う水は、約2300リットル。お風呂の浴槽、11杯分です。"], 7),
    ("2d:per_person", ["そんな服を、私たちは1人あたり、1年に約18枚買って、約12枚手放しています。"], 7),
    # 3. 眠る服
    ("2d:closet_share", ["家にある服のうち、ふだん着られているのは、およそ半分。残りの45%は、しまい込まれたままです。"], 7),
    # 4. 手放された服
    ("3d:c03_garbage_bag", ["家庭から手放される服は、1年間で、約51万トン。",
                            "そのほとんどは、燃えるごみや燃えないごみとして出され、燃やされたり、埋め立てられたりしています。"], 5),
    ("2d:discard", ["手放した服のうち、もう一度使われるのは、およそ3分の1だけ。"], 7),
    # 5. 回収された服のゆくえ
    ("3d:c04_sorting", ["回収ボックスなどで集められた服は、まず選別工場へ。人の手で、1着ずつ仕分けられます。"], 5),
    ("3d:c05_container", ["まだ着られる服は、古着として。その多くは海を渡り、東南アジアなどで、また誰かに着られます。"], 5),
    ("3d:c06_wiping_rag", ["着られない服は、四角く切って「ウエス」に。工場で、機械の油をふき取る布になります。"], 5),
    ("3d:c07_hanmo", ["さらに、細かくほぐして綿のようにする「反毛」。固めて、車の防音材などに生まれ変わります。"], 5),
    ("2d:routes", ["古着、ウエス、反毛。回収された服は、およそ3分の1ずつ、この3つに分かれていきます。"], 7),
    # 6. これから
    ("2d:goal", ["国は、2030年度までに、家庭から捨てられる服を、2020年度より25%減らす目標を立てています。"], 7),
    # 7. 締め
    ("3d:c08_empty_hanger", ["クローゼットの奥の1着。次に着る人は、もしかしたら、海の向こうにいるのかもしれません。"], 6),
    ("2d:next", ["次回、「使い終わった乾電池はどこへ行く？」"], 4),
]

_tts_text = B.tts_text


def tts_text(s):
    s = _tts_text(s)
    for a, b in (("45%", "45パーセント"), ("25%", "25パーセント"), ("CO2", "シーオーツー"), ("反毛", "はんもう")):
        s = s.replace(a, b)
    return s


B.tts_text = tts_text


def write_manifest():
    lines = [l for _, ls, _ in B.EDL for l in ls]
    m = [{"i": i, "line": l, "text": tts_text(l), "h": hashlib.md5(l.encode()).hexdigest()[:12]}
         for i, l in enumerate(lines)]
    B.HF_MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {B.HF_MANIFEST} ({len(m)} lines, {sum(len(x['line']) for x in m)} chars)")


if __name__ == "__main__":
    if "--manifest" in sys.argv:
        write_manifest()
    else:
        B.main()
