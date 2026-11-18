"""ネタ1・ネタ2 の編集を作り直す(assets/output/naruto-iyada で実行)。plan.md の記録と同じ処理。"""
import subprocess, numpy as np, librosa, soundfile as sf
sr = 48000
CLEAR_M = ('highpass=f=90,equalizer=f=250:t=q:w=0.8:g=-5,equalizer=f=450:t=q:w=1.0:g=-4,'
           'equalizer=f=2500:t=q:w=1.0:g=4,equalizer=f=4500:t=q:w=1.0:g=3,highshelf=f=8000:g=2,'
           'aexciter=amount=1:drive=4:blend=0:freq=3000:ceil=12000,deesser=i=0.4,'
           'acompressor=threshold=-22dB:ratio=2.5:attack=5:release=100')
def ff(*a): subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *a], check=True)
def load(p, eq=False):
    ff('-i', p, *(['-af', CLEAR_M] if eq else []), '-vn', '-ac', '1', '-ar', str(sr), '_t.wav')
    return librosa.load('_t.wav', sr=sr)[0]
def lvl(z, db): return z * 10 ** ((db - 20 * np.log10(np.percentile(librosa.feature.rms(y=z)[0], 90) + 1e-9)) / 20)
# ネタ1
s = lvl(load('audio/shout.mp3', True)[:int(1.32 * sr)], -13)
g = librosa.load('audio/sigh.mp3', sr=sr)[0][:int(1.25 * sr)]; g[-int(.15*sr):] *= np.linspace(1, 0, int(.15*sr))
sf.write('_g.wav', g, sr); g = lvl(load('_g.wav', True), -19)
A = load('bit1-A-clones.mp4'); B = load('bit1-B-sigh.mp4')
out = np.zeros(int(9.51 * sr))
a = A[int(.95*sr):].copy(); a[:int(.03*sr)] *= np.linspace(0, 1, int(.03*sr)); st = int(1.375*sr); out[st:st+len(a)] += a*.9
out[int(.03*sr):int(.03*sr)+len(s)] += s
b = B[:int(2.75*sr)].copy(); b[-int(.2*sr):] *= np.linspace(1, 0, int(.2*sr)); st = int(4.47*sr); out[st:st+len(b)] += b
st = int(7.22*sr); out[st:st+len(g)] += g
sf.write('audio/bit1-mix.wav', np.clip(out[:int(8.51*sr)], -.98, .98), sr)
ff('-i', 'bit1-A-clones.mp4', '-i', 'bit1-B-sigh.mp4', '-i', 'audio/bit1-mix.wav', '-filter_complex',
   '[0:v]trim=0:0.85,setpts=1.5*(PTS-STARTPTS)[a1];[0:v]trim=0.85,setpts=PTS-STARTPTS[a2];[1:v]setpts=PTS-STARTPTS[b];'
   '[a1][a2][b]concat=n=3:v=1:a=0,fps=24,format=yuv420p[v]', '-map', '[v]', '-map', '2:a',
   '-c:v', 'libx264', '-crf', '17', '-c:a', 'aac', '-b:a', '192k', '-shortest', 'bit1-kagebunshin.mp4')
# ネタ2
bo = lvl(load('audio/bono.mp3', True)[:int(.78*sr)], -15); bo[-int(.06*sr):] *= np.linspace(1, 0, int(.06*sr))
v = load('bit2-pasta.mp4'); st = int(4.25*sr); n = min(len(bo), len(v)-st); v[st:st+n] += bo[:n]
sf.write('audio/bit2-mix.wav', np.clip(v, -.98, .98), sr)
ff('-i', 'bit2-pasta.mp4', '-i', 'audio/bit2-mix.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', 'bit2-pasta-bono.mp4')
