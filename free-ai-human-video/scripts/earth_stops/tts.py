"""ナレーション音声を pyopenjtalk(無料・ローカル)で生成し、各セリフの長さを timings.json に書き出す。"""
import json
import sys
from pathlib import Path

import numpy as np
import pyopenjtalk
import wave

LINES = [
    "もしも地球の回転が、1秒だけ止まったら?",
    "赤道の地面は、時速1700キロで動いています。",
    "地面が止まっても、空気や海、そして私たちは止まれません。",
    "音速を超えるスピードで、すべてが東へ吹き飛ばされます。",
    "たった1秒で、世界は終わるのです。",
]
GAP = 0.35  # セリフ間の無音(秒)


def write_wav(path, data, sr):
    pcm = np.clip(data / 32768.0, -1, 1)
    pcm = (pcm * 32767 * 0.9).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    chunks, timings, t = [], [], 0.0
    sr = 48000
    for i, text in enumerate(LINES):
        wav, sr = pyopenjtalk.tts(text, speed=1.15)
        dur = len(wav) / sr
        timings.append({"index": i, "text": text, "start": round(t, 3), "end": round(t + dur, 3)})
        chunks += [wav, np.zeros(int(GAP * sr))]
        t += dur + GAP
    write_wav(out / "narration.wav", np.concatenate(chunks), sr)
    (out / "timings.json").write_text(json.dumps({"total": round(t, 3), "lines": timings}, ensure_ascii=False, indent=2))
    print(json.dumps(timings, ensure_ascii=False, indent=1), "total", round(t, 2))


if __name__ == "__main__":
    main(sys.argv[1])
