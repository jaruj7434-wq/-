"""歌うように読んだ素材(途切れない声)を、元の歌の音符に合わせる。
使い方: python3 sing3.py 素材.mp3 元ボーカル.mp3 開始秒 終了秒 出力.wav [半音シフト]
- 素材の前後の無音を落とし、区間の長さに合わせて線形に伸縮
- 元の歌の音程を半音単位に丸め、短い揺れ(しゃくり・ずり上げ)を消して、音符ごとにまっすぐな音にする
- 元の歌が無声の所も直前の音符を保ち、声を途切れさせない
"""
import sys
import numpy as np, librosa, soundfile as sf, pyworld as pw
from scipy.ndimage import median_filter

SR, FP = 44100, 5.0


def notes(f0):
    v = f0 > 0
    midi = np.where(v, 69 + 12 * np.log2(np.maximum(f0, 1) / 440), np.nan)
    # 無声は直前の値で埋める(先頭は最初の有声値)
    idx = np.where(v, np.arange(len(f0)), 0)
    np.maximum.accumulate(idx, out=idx)
    first = np.argmax(v) if v.any() else 0
    midi = np.where(v, midi, midi[idx])
    midi[:first] = midi[first]
    q = np.round(median_filter(midi, size=13))          # 65ms の中央値 → 半音に丸める
    # 60ms 未満の短い音符は前の音符にまとめる
    out = q.copy(); i = 0; n = len(q)
    while i < n:
        j = i
        while j < n and q[j] == q[i]: j += 1
        if j - i < 12 and i > 0: out[i:j] = out[i - 1]
        i = j
    return 440 * 2 ** ((out - 69) / 12)


def main(src, voc, t0, t1, out, shift=-12.0):
    x, _ = librosa.load(src, sr=SR)
    iv = librosa.effects.split(x, top_db=36)
    x = x[iv[0][0]:iv[-1][1]].astype(np.float64)
    f0s, ts = pw.harvest(x, SR, f0_floor=60, f0_ceil=600, frame_period=FP)
    f0s = pw.stonemask(x, f0s, ts, SR)
    sp, ap = pw.cheaptrick(x, f0s, ts, SR), pw.d4c(x, f0s, ts, SR)
    v, _ = librosa.load(voc, sr=SR, offset=t0, duration=t1 - t0)
    v = v.astype(np.float64)
    ft, tt = pw.harvest(v, SR, f0_floor=120, f0_ceil=1000, frame_period=FP)
    ft = pw.stonemask(v, ft, tt, SR)
    target = notes(ft) * 2 ** (shift / 12)
    n, m = len(target), len(f0s)
    idx = np.clip(np.round(np.linspace(0, m - 1, n)).astype(int), 0, m - 1)
    vs = f0s[idx] > 0
    f02 = np.where(vs, target, 0.0)
    # 音符の切り替わりを 15ms でなめらかに(ずり上げにはしない)
    k = 3
    f02s = f02.copy()
    for i in range(k, n - k):
        if vs[i - k:i + k + 1].all():
            f02s[i] = np.exp(np.log(f02[i - k:i + k + 1]).mean())
    # 人の声らしい細かな揺れ: 素材の音程の細かい動き(±40セントまで)を足す
    fs = f0s[idx]
    lf = np.where(fs > 0, np.log(np.maximum(fs, 1)), np.nan)
    sm = np.copy(lf)
    ok = ~np.isnan(lf)
    if ok.sum() > 30:
        from scipy.ndimage import uniform_filter1d
        tmp = np.interp(np.arange(n), np.where(ok)[0], lf[ok])
        dev = np.clip(tmp - uniform_filter1d(tmp, 40), -0.023, 0.023)
        f02s = np.where(f02s > 0, f02s * np.exp(dev), 0.0)
    apx = ap[idx].copy()
    apx[vs] = np.minimum(apx[vs], 0.6)   # 有声部分のガサつき(ノイズ成分)を抑える
    y = pw.synthesize(f02s, sp[idx], apx, SR, FP)
    y = y / (np.abs(y).max() + 1e-9) * 0.9
    sf.write(out, y.astype(np.float32), SR)


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], float(a[3]), float(a[4]), a[5], float(a[6]) if len(a) > 6 else -12.0)
