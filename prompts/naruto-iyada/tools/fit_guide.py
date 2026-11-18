"""声を変換した仮歌を、伴奏の位置・キー・メロディに合わせる。
使い方: python3 fit_guide.py 変換後の声.wav 伴奏.mp3 出力(伴奏あり).wav 出力(声のみ).wav 目標の高さHz
"""
import sys, subprocess
import numpy as np, librosa, soundfile as sf, pyworld as pw
from scipy.ndimage import median_filter, uniform_filter1d
SRC, INST, OUT_MIX, OUT_VO, TARGET_HZ = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
sr, FP = 48000, 5.0
# 仮歌のフレーズ(秒)→ 元の歌の位置
SRCP = [(0.90, 3.68), (4.03, 7.20), (7.58, 10.34), (10.66, 13.50), (13.89, 16.61), (16.93, 19.78)]
DST = [(55.42, 58.01), (58.12, 60.58), (60.75, 63.49), (63.62, 66.06), (66.35, 68.95), (69.06, 71.53)]
HOOK = [(0, .585, 69), (.585, .647, 67), (.647, .697, 65), (.697, .735, 64), (.735, .788, 65), (.788, 1, 67)]
ITEM = [(0, .471, 67), (.471, .562, 69), (.562, .636, 67), (.636, .744, 65), (.744, .856, 64), (.856, .946, 65), (.946, 1, 67)]
T0, T1 = 54.9, 72.2
def expected(r, tm):
    for a, b, p in tm:
        if a <= r < b: return p
    return tm[-1][2]
def ff(*a): subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *a], check=True)

c, _ = librosa.load(SRC, sr=sr)
inst, _ = librosa.load(INST, sr=sr)
a = inst[int(T0 * sr):int(T1 * sr)].copy(); vo = np.zeros_like(a)
tmid = 69 + 12 * np.log2(TARGET_HZ / 440)
for k, ((s, e), (d, de)) in enumerate(zip(SRCP, DST)):
    seg = c[int((s - .03) * sr):int((e + .05) * sr)]
    y16 = librosa.resample(seg, orig_sr=sr, target_sr=16000)
    f0, v, _ = librosa.pyin(y16, fmin=70, fmax=900, sr=16000, frame_length=1024, hop_length=160)
    rel = np.clip(np.arange(len(f0)) * 160 / len(y16), 0, .999)
    tm = HOOK if k % 2 == 0 else ITEM
    exp = np.array([expected(r, tm) for r in rel])
    mi = librosa.hz_to_midi(np.where(v, f0, 1))
    diff = (exp - mi)[v]
    sh = np.angle(np.mean(np.exp(1j * 2 * np.pi * diff / 12))) / (2 * np.pi) * 12
    sh += 12 * np.round((tmid - (np.median(mi[v]) + sh)) / 12)   # 目標の高さに一番近いオクターブへ
    sf.write('_p.wav', seg, sr)
    rate = float(np.clip((len(seg) / sr) / (de - d + .08), .8, 1.25))
    ff('-i', '_p.wav', '-af', f'rubberband=tempo={rate:.4f}:pitch={2 ** (sh / 12):.5f}:formant=preserved', '_q.wav')
    q, _ = librosa.load('_q.wav', sr=sr)
    q[:int(.01 * sr)] *= np.linspace(0, 1, int(.01 * sr)); q[-int(.04 * sr):] *= np.linspace(1, 0, int(.04 * sr))
    st = int((d - .03 - T0) * sr); m = min(len(q), len(vo) - st); vo[st:st + m] += q[:m]
    print(f'フレーズ{k + 1}: 移調 {sh:+.2f}半音 速さ ×{rate:.2f}')
# 音の中心だけメロディへ寄せる(揺れは残す)
x = vo.astype(np.float64)
f0, t = pw.harvest(x, sr, f0_floor=100, f0_ceil=900, frame_period=FP); f0 = pw.stonemask(x, f0, t, sr)
sp, ap = pw.cheaptrick(x, f0, t, sr), pw.d4c(x, f0, t, sr)
n = len(f0); tt = T0 + np.arange(n) * FP / 1000; target = np.full(n, np.nan)
for (d, de), tm in zip(DST, [HOOK, ITEM] * 3):
    for s0, e0, p in tm:
        mm = (tt >= d + s0 * (de - d)) & (tt < d + e0 * (de - d)); target[mm] = p
vv = f0 > 0; mi = np.where(vv, 69 + 12 * np.log2(np.maximum(f0, 1) / 440), np.nan)
idx = np.where(vv, np.arange(n), 0); np.maximum.accumulate(idx, out=idx)
center = median_filter(np.nan_to_num(np.where(vv, mi, mi[idx]), nan=tmid), size=25)
tg = np.where(np.isfinite(target), target, center); tg = tg + 12 * np.round((center - tg) / 12)
corr = uniform_filter1d(np.clip(tg - center, -3, 3), 8)
y = pw.synthesize(np.where(vv, f0 * 2 ** (corr / 12), 0), sp, ap, sr, FP)[:len(a)]
EQ = ('highpass=f=160,equalizer=f=250:t=q:w=0.8:g=-4,equalizer=f=500:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1:g=3,'
      'highshelf=f=9000:g=2,deesser=i=0.3,acompressor=threshold=-22dB:ratio=2.5:attack=5:release=100')
sf.write('_y.wav', y.astype(np.float32), sr); ff('-i', '_y.wav', '-af', EQ, '_y2.wav')
y, _ = librosa.load('_y2.wav', sr=sr); y = y[:len(a)]
def db(z): return 20 * np.log10(np.percentile(librosa.feature.rms(y=z)[0], 90) + 1e-9)
y *= 10 ** ((db(a) + 5 - db(y)) / 20)
a[-sr:] *= np.linspace(1, 0, sr)
mix = a * 10 ** (-2 / 20) + y; mix = mix / np.abs(mix).max() * .95
sf.write(OUT_MIX, mix, sr); sf.write(OUT_VO, y / np.abs(y).max() * .95, sr)
f1, v1, _ = librosa.pyin(librosa.resample(y, orig_sr=sr, target_sr=16000), fmin=100, fmax=900, sr=16000, frame_length=1024)
print('仕上がりの音程中央値', round(float(np.nanmedian(f1[v1]))), 'Hz')
