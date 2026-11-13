"""第3話「ペットボトルは何に生まれ変わる？」を通しで組み立てる。

第1話の ep01_build.py の仕組み(ナレーション→尺決め、3D/2D、字幕、BGM)をそのまま使い、
カット表・出力先・2D図解だけ差し替える。

  python3 scripts/mono_no_issho/edit/ep03_build.py --list
  python3 scripts/mono_no_issho/edit/ep03_build.py                # 仮ナレーション(Open JTalk)
  python3 scripts/mono_no_issho/edit/ep03_build.py --voice el     # ElevenLabs v4 ナレーション
  python3 scripts/mono_no_issho/edit/ep03_build.py --manifest     # ElevenLabs 用の行リストを書き出す
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ep01_build as B
import graphics2d_ep03 as G3

B.OUT = B.ROOT / "assets/output/mono_no_issho/ep03"
B.CLIPS = B.OUT / "clips"
B.WORK = B.OUT / "edit_work"
B.HF_MANIFEST = B.ROOT / "prompts/mono_no_issho/ep03_narration_lines.json"
B.HF_DIRS = {"hf": (B.WORK / "hf_tts", "wav"), "el": (B.WORK / "el_tts", "mp3")}
B.G.REGISTRY.clear()
B.G.REGISTRY.update(G3.REGISTRY)

B.EDL = [
    # 1. フック
    ("3d:p01_recycle_box", ["自販機の横の、リサイクルボックス。今日もここに、ペットボトルが入れられていきます。",
                            "この1本、次に会うときは、何になっていると思いますか？"], 5),
    ("2d:quiz", ["またペットボトル？　それとも、お弁当のフタ？　それとも、シャツ？",
                 "実は、そのすべてが正解です。"], 6),
    ("2d:title", [], 3.5),
    # 2. 誕生
    ("3d:p02_blow_mold", ["ペットボトルは、試験管のような小さな形から始まります。温めて、空気を吹き込むと、一瞬でボトルの形に。"], 5),
    ("2d:history", ["日本で最初にペットボトルが使われたのは、1977年。中身は、ジュースではなく、醤油でした。",
                    "1982年には清涼飲料にも使えるようになりましたが、ポイ捨てを心配した業界は、小さいサイズを自主的に控えていました。",
                    "1996年、その自主規制がなくなり、500ミリリットルのペットボトルが一気に広がります。"], 14),
    # 3. 量
    ("2d:amount", ["いま日本で売られるペットボトルは、1年間で約65万トン。",
                   "本数にすると、少し前のデータでも、年に200億本以上。"], 7),
    ("2d:lightweight", ["それでも、1本あたりはどんどん軽くなっていて、基準の年と比べて、使うプラスチックは約3割減っています。"], 6),
    # 4. 回収
    ("3d:p03_cap_label", ["飲み終わったボトルは、キャップとラベルを外して、中をすすいで、回収へ。"], 5),
    ("2d:rb_trash", ["ところが、自販機横のリサイクルボックスの中身を調べると、およそ3割が、ペットボトル以外のごみだったという調査もあります。",
                     "最近は、異物が入りにくいように、投入口の形を工夫したボックスも増えています。"], 10),
    # 5. 工場
    ("3d:p04_bale_conveyor", ["集められたボトルは、工場でぎゅっと押しつぶされ、ブロックのような塊に。「ベール」と呼ばれます。"], 5),
    ("3d:p05_flakes", ["次に細かく砕いて、洗って、「フレーク」に。"], 4),
    ("3d:p06_pellets", ["さらに溶かして、小さな粒の「ペレット」にします。これが、新しい製品の材料です。"], 5),
    ("2d:process", ["化学的に分解して、原料まで戻す方法もあります。"], 7),
    # 6. 生まれ変わり
    ("2d:rates", ["使われたペットボトルのうち、リサイクルされるのは約85%。世界でもトップクラスの水準です。"], 6),
    ("3d:p07_reborn", ["国内で生まれ変わる先を見ると、いちばん多いのは、またペットボトル。"], 5),
    ("2d:uses", ["次が、卵のパックや食品トレーなどのシート。そして、服などの繊維です。"], 6),
    ("2d:rates_b2b", ["ペットボトルからペットボトルへ戻る割合は、2024年度で37.7%。業界は、2030年度に50%を目指しています。"], 8),
    # 7. 締め
    ("3d:p08_new_bottles", ["今日、あなたが手にしたペットボトル。もしかしたら、何年か前にも、誰かの手の中にあったのかもしれません。"], 6),
    ("2d:next", ["次回、「着なくなった服はどこへ行く？」"], 4),
]

_tts_text = B.tts_text


def tts_text(s):
    s = _tts_text(s)
    for a, b in (("37.7%", "37.7パーセント"), ("85%", "85パーセント"), ("50%", "50パーセント")):
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
