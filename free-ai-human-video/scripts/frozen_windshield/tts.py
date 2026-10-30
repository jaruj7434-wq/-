"""「凍ったフロントガラスにお湯はNG」のナレーションを Style-Bert-VITS2(無料・ローカル)で生成し、各セリフの時間を timings.json に書き出す。

使い方: python tts.py <出力フォルダ> [話者]
  モデルの読み込み・WAV 書き出しは heat_shock/tts.py と同じ(jvnv-M1-jp・CC BY-SA 4.0)。
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

_spec = importlib.util.spec_from_file_location("hs_tts", Path(__file__).resolve().parent.parent / "heat_shock" / "tts.py")
hs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hs)

LINES = [
    "これだけで、修理代10万円以上になることも。",
    "冬の朝、凍ったフロントガラスにお湯。やっていませんか?",
    "凍った窓を、たった1分で溶かす方法は、最後に教えます。",
    "フロントガラスは、2枚のガラスで樹脂を挟んだ合わせガラス。",
    "お湯をかけると、表面だけが急に温まって膨らみ、ゆがみが生まれます。",
    "目に見えない、飛び石の小さな傷があると、そこから一気にヒビが広がります。",
    "じゃあ、ぬるま湯ならセーフ? 実は、氷点下だとすぐに再び凍って、もっと厚い氷に。",
    "凍ったワイパーを、無理に動かすのもNG。ゴムが切れたり、モーターが壊れることも。",
    "正解は、エンジンをかけて、デフロスター。ただ、10分ほどかかります。",
    "急ぐ朝は、解氷スプレー。約1分で、視界スッキリ。",
    "前の晩に、カバーをかけておけば、そもそも凍りません。",
    "冬の朝に困らないように、保存しておいてください。",
]
READ = {"NG": "エヌジー", "10万円": "じゅうまんえん", "1分": "いっぷん", "樹脂": "じゅし"}  # 読み間違い対策(字幕は元の表記)
GAP = 0.1


def main(out_dir, speaker="jvnv-M1-jp"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    model = hs.load_model(speaker)
    chunks, timings, t, sr = [], [], 0.0, 44100
    for i, text in enumerate(LINES):
        spoken = text
        for a, b in READ.items():
            spoken = spoken.replace(a, b)
        sr, audio = model.infer(text=spoken, style="Neutral", length=0.74, sdp_ratio=0.25, noise=0.5)
        audio = np.asarray(audio, dtype=np.float32)
        lead = np.argmax(np.abs(audio) > 300) if i == 0 else 0  # 1本目は頭の無音を削って 0 秒目から声を出す
        audio = audio[max(0, lead - int(0.02 * sr)):]
        dur = len(audio) / sr
        timings.append({"index": i, "text": text, "start": round(t, 3), "end": round(t + dur, 3)})
        chunks += [audio, np.zeros(int(GAP * sr), dtype=np.float32)]
        t += dur + GAP
    hs.write_wav(out / "narration.wav", np.concatenate(chunks), sr)
    (out / "timings.json").write_text(json.dumps({"total": round(t, 3), "speaker": speaker, "lines": timings},
                                                 ensure_ascii=False, indent=2))
    for x in timings:
        print(f'{x["start"]:6.2f}-{x["end"]:6.2f} {x["text"]}')
    print("total", round(t, 2))


if __name__ == "__main__":
    main(*sys.argv[1:3])
