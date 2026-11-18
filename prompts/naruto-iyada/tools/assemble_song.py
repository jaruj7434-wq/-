"""替え歌パート+ネタ1〜3 をつないで完成版を作る。
使い方: python3 assemble_song.py 作業ディレクトリ(歌の素材) 出力.mp4  (assets/output/naruto-iyada で実行)
歌の素材: inst.mp3(伴奏), h1..h3.wav / i1..i3.wav(慶太の歌)
"""
import sys, os, subprocess, numpy as np, librosa, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SD, OUT = sys.argv[1], sys.argv[2]
sr = 48000
W, H = 1080, 1920
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
def ff(*a): subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *a], check=True)

# 曲の区間(元の歌の時刻): (区間の開始, サビ頭, 項目の頭, 区間の終わり)
COUP = [(54.90, 55.16, 57.90, 60.82), (60.82, 60.82, 63.48, 66.16), (66.16, 66.16, 68.90, 71.66)]
HOOK = 'こんななるとは\nまじでやだ〜'
ITEMS = ['影分身全員\nドーパガキ〜', 'ラーメン嫌いで\nパスタ食う〜', '移動は走らず\nヘイタクシー']
BITS = ['bit1-kagebunshin.mp4', 'bit2-pasta-bono.mp4', 'bit3-taxi.mp4']
VOX_EQ = 'highpass=f=100,equalizer=f=300:t=q:w=1:g=-3,equalizer=f=3000:t=q:w=1:g=3,aecho=0.8:0.6:60:0.18,acompressor=threshold=-20dB:ratio=3'

inst, _ = librosa.load(f'{SD}/inst.mp3', sr=sr, mono=True)
def vox(name):
    ff('-i', f'{SD}/{name}.wav', '-af', VOX_EQ, '-ac', '1', '-ar', str(sr), '_v.wav')
    return librosa.load('_v.wav', sr=sr)[0]
def rms_db(z): return 20 * np.log10(np.percentile(librosa.feature.rms(y=z)[0], 90) + 1e-9)

def card(bit, text_top, text_bot, path):
    # ネタの最初のフレームをぼかして暗くした背景に、歌詞を大きく
    ff('-ss', '0.05', '-i', bit, '-frames:v', '1', '_f.png')
    im = Image.open('_f.png').convert('RGB').resize((W, H))
    im = im.filter(ImageFilter.GaussianBlur(18))
    im = Image.blend(im, Image.new('RGB', (W, H), (0, 0, 0)), 0.45)
    d = ImageDraw.Draw(im)
    def block(txt, cy, size, fill):
        f = ImageFont.truetype(FONT, size)
        d.multiline_text((W / 2, cy), txt, font=f, fill=fill, anchor='mm', align='center',
                         spacing=18, stroke_width=10, stroke_fill=(0, 0, 0))
    if text_top: block(text_top, 640, 120, (255, 140, 0))
    if text_bot: block(text_bot, 1240, 130, (255, 255, 255))
    im.save(path)

segs = []
for k, (t0, th, ti, t1) in enumerate(COUP):
    n = int((t1 - t0) * sr)
    a = inst[int(t0 * sr):int(t0 * sr) + n].copy()
    base = rms_db(a)
    for name, ts in ((f'h{k+1}', th), (f'i{k+1}', ti)):
        v = vox(name); v *= 10 ** ((base + 3 - rms_db(v)) / 20)
        st = int((ts - t0) * sr); m = min(len(v), n - st); a[st:st + m] += v[:m]
    sf.write(f'_s{k}.wav', np.clip(a, -.98, .98), sr)
    # 映像: サビ → 項目の順に歌詞を出す
    card(BITS[k], HOOK, None, f'_c{k}a.png'); card(BITS[k], HOOK, ITEMS[k], f'_c{k}b.png')
    da, db = ti - t0, t1 - ti
    ff('-loop', '1', '-t', f'{da:.3f}', '-i', f'_c{k}a.png', '-loop', '1', '-t', f'{db:.3f}', '-i', f'_c{k}b.png', '-i', f'_s{k}.wav',
       '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0,zoompan=z=\'min(zoom+0.0006,1.06)\':d=1:s=1080x1920:fps=24,format=yuv420p[v]',
       '-map', '[v]', '-map', '2:a', '-c:v', 'libx264', '-crf', '18', '-c:a', 'aac', '-ar', str(sr), '-ac', '2', '-shortest', f'_seg{2*k}.mp4')
    # ネタ: 伴奏を小さく流し続け、最後でフェードアウト
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', BITS[k]]))
    bed = inst[int(t1 * sr):int((t1 + dur) * sr)].copy() * 10 ** (-14 / 20)
    fo = int(0.8 * sr); bed[-fo:] *= np.linspace(1, 0, fo)
    sf.write(f'_bed{k}.wav', bed, sr)
    ff('-i', BITS[k], '-i', f'_bed{k}.wav', '-filter_complex',
       '[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p[v];'
       '[0:a]aresample=48000[x];[1:a]aresample=48000[y];[x][y]amix=inputs=2:normalize=0,aformat=channel_layouts=stereo[a]',
       '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', '18', '-c:a', 'aac', '-ar', str(sr), '-t', f'{dur:.3f}', f'_seg{2*k+1}.mp4')
    segs += [f'_seg{2*k}.mp4', f'_seg{2*k+1}.mp4']

with open('_list.txt', 'w') as f:
    f.writelines(f"file '{s}'\n" for s in segs)
ff('-f', 'concat', '-safe', '0', '-i', '_list.txt', '-c:v', 'libx264', '-crf', '18', '-c:a', 'aac', '-b:a', '192k', OUT)
for p in os.listdir('.'):
    if p.startswith('_'): os.remove(p)
