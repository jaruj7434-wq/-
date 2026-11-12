"""第2話「なくした傘はどこへ行く？」を通しで組み立てる。

第1話の ep01_build.py の仕組み(ナレーション→尺決め、3D/2D、字幕、BGM)をそのまま使い、
カット表・出力先・2D図解だけ差し替える。

  python3 scripts/mono_no_issho/edit/ep02_build.py --list
  python3 scripts/mono_no_issho/edit/ep02_build.py --voice el   # ElevenLabs v4 ナレーション
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ep01_build as B
import graphics2d_ep02 as G2

B.OUT = B.ROOT / "assets/output/mono_no_issho/ep02"
B.CLIPS = B.OUT / "clips"
B.WORK = B.OUT / "edit_work"
B.HF_MANIFEST = B.ROOT / "prompts/mono_no_issho/ep02_narration_lines.json"
B.HF_DIRS = {"hf": (B.WORK / "hf_tts", "wav"), "el": (B.WORK / "el_tts", "mp3")}
B.G.REGISTRY.clear()
B.G.REGISTRY.update(G2.REGISTRY)

# 第1話の雨の駅カットを流用(ep02/clips に無ければ ep01 からコピー)
_src = B.ROOT / "assets/output/mono_no_issho/ep01/clips/h15_rain_umbrella.mp4"
B.CLIPS.mkdir(parents=True, exist_ok=True)
if _src.exists() and not (B.CLIPS / "k01_station_bench.mp4").exists():
    (B.CLIPS / "k01_station_bench.mp4").write_bytes(_src.read_bytes())

B.EDL = [
    # 1. フック
    ("3d:k01_station_bench", ["雨上がりの駅。ホームのベンチに、一本のビニール傘。",
                              "あなたが最後に傘をなくしたのは、いつですか？"], 5),
    ("2d:counter", ["東京だけで、1年に約28万本の傘が、落とし物として警察に届けられています。",
                    "そのほとんどは、持ち主のもとへ帰りません。"], 6),
    ("2d:title", [], 3.5),
    # 2. 誕生
    ("2d:consumption", ["日本で1年間に使われる傘は、1億2千万本から1億3千万本と言われています。",
                        "そのうち約8千万本が、ビニール傘だという推計もあります。"], 7),
    ("2d:history", ["実はビニール傘は、日本生まれ。1950年代に、東京の傘メーカーが作ったのが始まりと言われています。",
                    "1964年の東京オリンピック。来日したアメリカのバイヤーの目に留まり、ニューヨークで人気になったそうです。",
                    "やがて海外から安い傘が大量に入ってくるようになり、ビニール傘は「使い捨て」のイメージに。"], 14),
    ("3d:k02_store_stand", ["安くて、どこでも買える。急な雨でも、コンビニに行けばすぐ手に入る。",
                            "だから、なくしても、あまり探さない。"], 5),
    # 3. 忘れられる
    ("3d:k03_train_seat", ["傘が置き去りにされるのは、電車の中、駅のベンチ、お店の傘立て。",
                           "東京の落とし物の中で、傘はいつも上位の常連です。"], 5),
    ("2d:return_rate", ["ところが、「傘をなくしました」と届け出る人は、ほとんどいません。",
                        "ある鉄道会社では、忘れ物全体のうち持ち主に戻るのは3割ほど。傘に限ると、1割ほどだそうです。",
                        "警察に届いた傘に限ると、持ち主に戻るのは約1%という報道もあります。"], 10),
    # 4. 保管
    ("3d:k04_lost_storage", ["拾われた傘は、まず駅の忘れ物置き場へ。タグをつけられ、日付ごとに並べられます。"], 5),
    ("2d:storage_rule", ["法律では、落とし物の保管期間は原則3か月。",
                         "でも、傘は数が多くて、値段は安い。",
                         "そこで、鉄道会社などは、届け出から2週間たっても持ち主が見つからなければ、売ったり処分したりできるルールがあります。",
                         "2007年に施行された、今の遺失物法で決められたルールです。"], 14),
    ("3d:k05_cart_out", ["ある鉄道会社は、傘の保管期間を3か月から1か月に短くしました。"], 5),
    # 5. 最期
    ("2d:fate_flow", ["持ち主が現れなかった傘は、業者に売られたり、廃棄されたりします。"], 6),
    ("3d:k06_umbrella_explode", ["実は傘は、捨てるのが難しいモノです。"], 4),
    ("2d:materials", ["骨は金属、生地はプラスチックや布。素材が混ざっているため、金属は回収されることもありますが、残りは燃やされることが多いと言われています。"], 9),
    ("3d:k07_resale_machine", ["最近は、引き取り手のない傘を駅で安く売り直したり、ビニール傘を集めて新しい素材に作り変えたりする取り組みも始まっています。"], 7),
    # 6. 締め
    ("3d:k08_last_umbrella", ["次の雨の日。あなたの手の中の傘は、どこから来て、どこへ行くのでしょう。"], 6),
    ("2d:next", ["次回、「ペットボトルは何に生まれ変わる？」"], 4),
]

if __name__ == "__main__":
    B.main()
