"""ナレーションを Style-Bert-VITS2(無料・ローカル)で生成し、各セリフの時間を timings.json に書き出す。

使い方: python tts.py <出力フォルダ> [話者]
  話者の既定は jvnv-M1-jp(JVNV コーパス・CC BY-SA 4.0、男性・落ち着いた声)。
  初回は Hugging Face からモデル(約2GB)を自動でダウンロードする。
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np
from huggingface_hub import hf_hub_download

LINES = [
    "蚊に刺されたとき、皮膚の下では、何が起きているのか。",
    "実は、蚊の口は、1本の針ではありません。",
    "中には6本の針が隠れていて、ギザギザの2本が、皮膚を切り開きます。",
    "1本の針が、しなりながら血管を探し当てると、",
    "まず、唾液を注入。血が固まらないようにするためです。",
    "そして、ストローのように、血を吸い上げます。",
    "残された唾液に、体が反応して起きるのが、あのかゆみです。",
    "ちなみに、血を吸うのは、メスだけ。",
]
GAP = 0.2  # セリフ間の無音(秒)
REPO = "litagin/style_bert_vits2_jvnv"
FILES = {
    "jvnv-M1-jp": "jvnv-M1-jp_e158_s14000.safetensors",
    "jvnv-M2-jp": "jvnv-M2_e159_s17000.safetensors",
    "jvnv-F1-jp": "jvnv-F1-jp_e160_s14000.safetensors",
    "jvnv-F2-jp": "jvnv-F2_e166_s20000.safetensors",
}


def load_model(speaker):
    from style_bert_vits2.constants import Languages
    from style_bert_vits2.nlp import bert_models
    from style_bert_vits2.tts_model import TTSModel

    bert = "ku-nlp/deberta-v2-large-japanese-char-wwm"
    bert_models.load_model(Languages.JP, bert).float()  # CPU では半精度だと推論に失敗するため
    bert_models.load_tokenizer(Languages.JP, bert)
    get = lambda f: hf_hub_download(REPO, f"{speaker}/{f}")
    return TTSModel(model_path=get(FILES[speaker]), config_path=get("config.json"),
                    style_vec_path=get("style_vectors.npy"), device="cpu")


def write_wav(path, pcm, sr):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.astype(np.int16).tobytes())


def main(out_dir, speaker="jvnv-M1-jp"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    model = load_model(speaker)
    chunks, timings, t, sr = [], [], 0.0, 44100
    for i, text in enumerate(LINES):
        sr, audio = model.infer(text=text, style="Neutral", length=0.86, sdp_ratio=0.25, noise=0.5)
        audio = np.asarray(audio, dtype=np.float32)
        dur = len(audio) / sr
        timings.append({"index": i, "text": text, "start": round(t, 3), "end": round(t + dur, 3)})
        chunks += [audio, np.zeros(int(GAP * sr), dtype=np.float32)]
        t += dur + GAP
    write_wav(out / "narration.wav", np.concatenate(chunks), sr)
    (out / "timings.json").write_text(json.dumps({"total": round(t, 3), "speaker": speaker, "lines": timings},
                                                 ensure_ascii=False, indent=2))
    for x in timings:
        print(f'{x["start"]:6.2f}-{x["end"]:6.2f} {x["text"]}')
    print("total", round(t, 2))


if __name__ == "__main__":
    main(*sys.argv[1:3])
