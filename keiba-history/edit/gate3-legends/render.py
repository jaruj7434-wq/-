# 車に乗った名馬3頭 — 書き出し (1080x1920)。実行場所: サンドボックス ~/gate3
#   raw.mp4 = Kling 4.0 の1本の横移動 (7秒、job 4573cd9c)、bgm.m4a = sonilo_music (job fc8a2c1f)、name_*.png = mk_names.py
import subprocess
from PIL import Image
W, H, T = 1080, 1920, 7.0
# (画像, 出す時間, 消す時間) — ピントがその馬に合っている間、下の方を右から左へ少し流れる
names = [('name_deep.png', 0.15, 1.65), ('name_teio.png', 2.35, 3.75), ('name_suzuka.png', 4.3, 5.7)]
Y = 1330
args = ['-i', 'raw.mp4']; fc = f'[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30,format=yuv420p,trim=duration={T}[b0]'
cur = 'b0'
for k, (p, t0, t1) in enumerate(names):
    w = Image.open(p).size[0]
    x0 = (W - w) // 2 + 70; x1 = (W - w) // 2 - 70; sp = (x0 - x1) / (t1 - t0)  # 画面に収め、少しだけ左へ流す
    args += ['-loop', '1', '-framerate', '30', '-t', f'{T}', '-i', p]
    fc += (f';[{k+1}:v]format=rgba,fade=t=in:st={t0}:d=0.15:alpha=1,fade=t=out:st={t1-0.2}:d=0.2:alpha=1[n{k}]'
           f";[{cur}][n{k}]overlay=x='{x0}-(t-{t0})*{sp:.1f}':y={Y}:enable='between(t,{t0},{t1})'[c{k}]")
    cur = f'c{k}'
fc += f';[{cur}]fade=t=out:st={T-0.5}:d=0.5[vout]'
# 音: BGM + 引きになる所 (5.0秒) の低い衝撃音 (BGM が約6秒で消えるため足す)
args += ['-i', 'bgm.m4a', '-f', 'lavfi', '-t', '3', '-i', "aevalsrc='0.9*sin(2*PI*(62-30*t)*t)*exp(-1.6*t)+0.25*sin(2*PI*31*t)*exp(-1.2*t)':s=48000"]
na = len(names) + 1
fc += (f';[{na}:a]aresample=48000,apad,atrim=0:{T},volume=0.9[bg];[{na+1}:a]aresample=48000,adelay=5000:all=1,apad,atrim=0:{T},volume=0.8[hit]'
       f';[bg][hit]amix=inputs=2:normalize=0,alimiter=limit=0.9,afade=t=out:st={T-0.6}:d=0.6[aout]')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *args, '-filter_complex', fc, '-map', '[vout]', '-map', '[aout]',
                '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-t', f'{T}', 'horses_in_cars_v1.mp4'], check=True)
print('ok')
