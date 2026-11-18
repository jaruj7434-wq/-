"""元の歌を「音符」に分解し、慶太の声を音符ごとに1つずつ当てる(しゃべるように歌う)。
使い方: python3 sing4.py 素材.mp3 元ボーカル.mp3 開始秒 終了秒 出力.wav [半音シフト] [--table]
- 元ボーカル: 音の出だし(オンセット)で区切り、各区間の音程の中央値を半音に丸めて1音符にする
- 素材: 同じ数の区間に区切り(音の出だしの強い順)、i 番目を i 番目の音符の長さに伸縮し、音程は音符の高さで一定
- ビブラートや揺れは付けない
"""
import sys
import numpy as np, librosa, soundfile as sf, pyworld as pw

SR, FP = 44100, 5.0
HOP = int(SR * FP / 1000)
NAMES = ['ド', 'ド#', 'レ', 'レ#', 'ミ', 'ファ', 'ファ#', 'ソ', 'ソ#', 'ラ', 'ラ#', 'シ']


def onsets(y, n_frames):
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    on = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP, backtrack=True, units='frames')
    on = [o for o in on if 0 < o < n_frames - 8]
    return on, env


def target_notes(v):
    f0, vf, _ = librosa.pyin(v, fmin=150, fmax=1000, sr=SR, frame_length=2048, hop_length=HOP)
    n = len(f0)
    on, env = onsets(v, n)
    # 音程の変わり目も区切りに加える(0.7半音以上の変化が 40ms 続く所)
    midi = np.where(vf, librosa.hz_to_midi(np.nan_to_num(f0, nan=1)), np.nan)
    sm = np.array([np.nanmedian(midi[max(0, i - 4):i + 5]) if np.isfinite(midi[max(0, i - 4):i + 5]).any() else np.nan for i in range(n)])
    for i in range(10, n - 10):
        a, b = sm[i - 8:i], sm[i:i + 8]
        if np.isfinite(a).sum() > 5 and np.isfinite(b).sum() > 5 and abs(np.nanmedian(b) - np.nanmedian(a)) > 0.7:
            if all(abs(i - o) > 12 for o in on): on.append(i)
    on = sorted(set(on))
    first = int(np.argmax(vf)) if vf.any() else 0
    bounds = [first] + [o for o in on if o > first + 8] + [n]
    notes = []
    for s, e in zip(bounds[:-1], bounds[1:]):
        mid = midi[s + (e - s) // 5: e - (e - s) // 5 or e]
        if np.isfinite(mid).sum() < 3:
            if notes: notes[-1][1] = e
            continue
        notes.append([s, e, int(np.round(np.nanmedian(mid)))])
    SCALE = {0, 2, 4, 5, 7, 9, 11}  # ハ長調(ド レ ミ ファ ソ ラ シ)。経過音の半音はずり上げとして除く
    for nt in notes:
        p = nt[2]
        if p % 12 not in SCALE:
            # 前後の音符に近い方の音階音へ
            cand = [p - 1, p + 1]
            nt[2] = min(cand, key=lambda q: 0 if q % 12 in SCALE else 9)
    merged = []
    for nt in notes:
        if merged and merged[-1][2] == nt[2]:
            merged[-1][1] = nt[1]
        else:
            merged.append(list(nt))
    out = []
    for nt in merged:
        if out and nt[1] - nt[0] < 16:   # 80ms 未満
            out[-1][1] = nt[1]
        else:
            out.append(nt)
    # まとめた後、また同じ音が並んだら結合
    final = []
    for nt in out:
        if final and final[-1][2] == nt[2]:
            final[-1][1] = nt[1]
        else:
            final.append(nt)
    return final, n


def split_source(x, notes, m):
    on, env = onsets(x, m)
    s0, e0 = notes[0][0], notes[-1][1]
    b = [0]
    for s, e, p in notes[1:]:
        pos = (s - s0) / (e0 - s0) * m
        near = [o for o in on if abs(o - pos) < 14 and o > b[-1] + 4]
        b.append(min(near, key=lambda o: abs(o - pos)) if near else int(pos))
    b.append(m)
    return b


def main(src, voc, t0, t1, out, shift=-12.0, table=False):
    x, _ = librosa.load(src, sr=SR)
    iv = librosa.effects.split(x, top_db=36)
    x = x[iv[0][0]:iv[-1][1]].astype(np.float64)
    f0s, ts = pw.harvest(x, SR, f0_floor=60, f0_ceil=600, frame_period=FP)
    f0s = pw.stonemask(x, f0s, ts, SR)
    sp, ap = pw.cheaptrick(x, f0s, ts, SR), pw.d4c(x, f0s, ts, SR)
    m = len(f0s)
    import os
    tm = os.environ.get('TMPL')  # 例 "55.42,58.01": 同じメロディの代表区間の音符を、この区間の長さに合わせて使う
    if tm:
        a0, a1 = map(float, tm.split(','))
        tv, _ = librosa.load(voc, sr=SR, offset=a0, duration=a1 - a0)
        tn, tnn = target_notes(tv)
        clean = []
        for nt in tn:  # 100ms 未満の音は前の音符にまとめる
            if clean and nt[1] - nt[0] < int(os.environ.get('MINLEN', '20')): clean[-1][1] = nt[1]
            elif clean and clean[-1][2] == nt[2]: clean[-1][1] = nt[1]
            else: clean.append(list(nt))
        n = int(round((t1 - t0) * 1000 / FP))
        r = n / tnn
        notes = [[int(round(a * r)), int(round(b * r)), p] for a, b, p in clean]
        notes[-1][1] = n
    else:
        v, _ = librosa.load(voc, sr=SR, offset=t0, duration=t1 - t0)
        notes, n = target_notes(v)
    if table:
        for s, e, p in notes:
            print(f"  {t0 + s * FP / 1000:6.2f}–{t0 + e * FP / 1000:6.2f}秒  {NAMES[p % 12]}{p // 12 - 1}")
    b = split_source(x, notes, m)
    idx = np.zeros(n, int); f0 = np.zeros(n)
    start = notes[0][0]
    idx[:start] = 0
    for (s, e, p), a, c in zip(notes, b[:-1], b[1:]):
        idx[s:e] = np.clip(np.round(np.linspace(a, c - 1, e - s)).astype(int), 0, m - 1)
        f0[s:e] = 440 * 2 ** ((p + shift - 69) / 12)
    vs = f0s[idx] > 0
    vs[:start] = False
    f02 = np.where(vs, f0, 0.0)
    ap2 = ap[idx].copy(); ap2[vs] = np.minimum(ap2[vs], 0.6)
    y = pw.synthesize(f02, sp[idx], ap2, SR, FP)
    y = y / (np.abs(y).max() + 1e-9) * 0.9
    sf.write(out, y.astype(np.float32), SR)


if __name__ == "__main__":
    a = [s for s in sys.argv if s != '--table']
    main(a[1], a[2], float(a[3]), float(a[4]), a[5], float(a[6]) if len(a) > 6 else -12.0, '--table' in sys.argv)
