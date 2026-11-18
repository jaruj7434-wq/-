"""話し声(慶太のTTS)を、元の歌の音程とリズムに合わせて「歌」にする。
使い方: python3 sing.py 話し声.mp3 元ボーカル.mp3 開始秒 終了秒 出力.wav [半音シフト]
- 話し声の中の長い無音(0.12秒以上)を詰める
- 話し声全体を、目標区間の長さに合わせて時間伸縮
- 有声部分の音程を、元ボーカルの音程(半音シフト済み)に置き換える(WORLD で再合成)
"""
import sys
import numpy as np, librosa, soundfile as sf, pyworld as pw

SR = 44100
FP = 5.0  # ms frame period


def load_speech(path):
    y, _ = librosa.load(path, sr=SR)
    iv = librosa.effects.split(y, top_db=38, frame_length=1024, hop_length=256)
    parts = []
    for i, (a, b) in enumerate(iv):
        parts.append(y[a:b])
        if i < len(iv) - 1:
            gap = iv[i + 1][0] - b
            parts.append(np.zeros(min(gap, int(0.04 * SR)), np.float32))
    return np.concatenate(parts).astype(np.float64)


def target_f0(voc_path, t0, t1, shift):
    v, _ = librosa.load(voc_path, sr=SR, offset=t0, duration=t1 - t0)
    v = v.astype(np.float64)
    f0, t = pw.harvest(v, SR, f0_floor=120, f0_ceil=1000, frame_period=FP)
    f0 = pw.stonemask(v, f0, t, SR)
    f0[f0 > 0] *= 2 ** (shift / 12)
    return f0


def main(speech, voc, t0, t1, out, shift=-12.0):
    x = load_speech(speech)
    f0s, ts = pw.harvest(x, SR, f0_floor=60, f0_ceil=500, frame_period=FP)
    f0s = pw.stonemask(x, f0s, ts, SR)
    sp = pw.cheaptrick(x, f0s, ts, SR)
    ap = pw.d4c(x, f0s, ts, SR)
    ft = target_f0(voc, t0, t1, shift)
    n = len(ft)
    # 時間伸縮(フレームの再サンプル)
    idx = np.clip(np.round(np.linspace(0, len(f0s) - 1, n)).astype(int), 0, len(f0s) - 1)
    sp2, ap2, v2 = sp[idx], ap[idx], f0s[idx] > 0
    # 目標の音程: 無声の所は前後の音程で埋める
    tv = ft > 0
    if tv.any():
        xs = np.arange(n)
        fill = np.interp(xs, xs[tv], ft[tv])
    else:
        fill = np.full(n, 150.0)
    f02 = np.where(v2, fill, 0.0)
    y = pw.synthesize(f02, sp2, ap2, SR, FP)
    y = y / (np.abs(y).max() + 1e-9) * 0.8
    sf.write(out, y.astype(np.float32), SR)


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], float(a[3]), float(a[4]), a[5], float(a[6]) if len(a) > 6 else -12.0)
