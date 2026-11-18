"""sing.py の改良版: 間を詰めて、元の歌のリズムに合わせる。
使い方: python3 sing2.py 話し声.mp3 元ボーカル.mp3 開始秒 終了秒 出力.wav [半音シフト]
- 話し声の途中の無音をすべて詰める
- 話し声と元の歌の音量の動き(音節の山)を DTW で対応づけて時間を合わせる
- 元の歌が伸ばしている所は、直前の母音を伸ばしてつなげる(レガート)
- 音程は元の歌の音程(既定で1オクターブ下)
"""
import sys
import numpy as np, librosa, soundfile as sf, pyworld as pw

SR = 44100
FP = 5.0
HOP = int(SR * FP / 1000)


def load_speech(path):
    y, _ = librosa.load(path, sr=SR)
    iv = librosa.effects.split(y, top_db=36, frame_length=1024, hop_length=256)
    return np.concatenate([y[a:b] for a, b in iv]).astype(np.float64)


def env(y, n):
    r = librosa.feature.rms(y=y, frame_length=4 * HOP, hop_length=HOP, center=True)[0][:n]
    r = np.pad(r, (0, max(0, n - len(r))), mode='edge')
    e = 20 * np.log10(r + 1e-6)
    e = (e - e.mean()) / (e.std() + 1e-6)
    return np.convolve(e, np.ones(5) / 5, mode='same')


def main(speech, voc, t0, t1, out, shift=-12.0):
    x = load_speech(speech)
    f0s, ts = pw.harvest(x, SR, f0_floor=60, f0_ceil=500, frame_period=FP)
    f0s = pw.stonemask(x, f0s, ts, SR)
    sp = pw.cheaptrick(x, f0s, ts, SR)
    ap = pw.d4c(x, f0s, ts, SR)
    v, _ = librosa.load(voc, sr=SR, offset=t0, duration=t1 - t0)
    v = v.astype(np.float64)
    ft, tt = pw.harvest(v, SR, f0_floor=120, f0_ceil=1000, frame_period=FP)
    ft = pw.stonemask(v, ft, tt, SR)
    ft[ft > 0] *= 2 ** (shift / 12)
    n, m = len(ft), len(f0s)
    # DTW(大まかに線形を保つよう、線形対応からのずれを罰する)
    es, et = env(x, m), env(v, n)
    D, wp = librosa.sequence.dtw(X=es[None, :], Y=et[None, :], metric='euclidean',
                                 global_constraints=True, band_rad=0.15)
    wp = wp[::-1]
    idx = np.zeros(n, int)
    for i_s, i_t in wp:
        idx[i_t] = i_s
    idx = np.maximum.accumulate(idx)
    # 線形対応と混ぜて暴れを抑える
    lin = np.linspace(0, m - 1, n)
    W_DTW = float(__import__('os').environ.get('W_DTW', '0.6'))
    idx = np.clip(np.round(W_DTW * idx + (1 - W_DTW) * lin).astype(int), 0, m - 1)
    idx = np.maximum.accumulate(idx)
    sp2, ap2, vs = sp[idx].copy(), ap[idx].copy(), f0s[idx] > 0
    tv = ft > 0
    xs = np.arange(n)
    fill = np.interp(xs, xs[tv], ft[tv]) if tv.any() else np.full(n, 150.0)
    # レガート: 元の歌が声を出している所で、話し声側が無声なら直前の有声フレームを伸ばす
    last = -1
    voiced = np.zeros(n, bool)
    for i in range(n):
        if vs[i]:
            last = i; voiced[i] = True
        elif tv[i] and last >= 0 and i - last < int(float(__import__('os').environ.get('LEGATO', '0.35')) * 1000 / FP):
            # 子音(無声で音量がある所)は残す
            if es[idx[i]] < -0.3:
                sp2[i], ap2[i] = sp2[last], ap2[last]
                voiced[i] = True
    f02 = np.where(voiced, fill, 0.0)
    y = pw.synthesize(f02, sp2, ap2, SR, FP)
    y = y / (np.abs(y).max() + 1e-9) * 0.9
    sf.write(out, y.astype(np.float32), SR)


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], float(a[3]), float(a[4]), a[5], float(a[6]) if len(a) > 6 else -12.0)
