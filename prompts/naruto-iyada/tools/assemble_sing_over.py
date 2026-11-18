"""歌を流しっぱなしにして、その上でネタ1〜3の映像を進める版。
使い方: python3 assemble_sing_over.py 歌.mp3 出力.mp4  (assets/output/naruto-iyada で実行)
- 歌(伴奏+慶太)を最初から最後まで流す。ネタの元の音は使わない
- 各ネタの映像を、対応する歌の区間の長さに速さを合わせて流す
- 歌詞テロップ: サビは上(オレンジ)、各ネタの行は下(白)
"""
import sys, subprocess, os
from PIL import Image, ImageDraw, ImageFont

SONG, OUT = sys.argv[1], sys.argv[2]
W, H = 1080, 1920
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
def ff(*a): subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *a], check=True)
def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))

# 歌の中の時刻(歌ファイルの先頭からの秒): 区間の開始, 項目の頭, 区間の終わり
SEG = [(0.00, 3.22, 5.85), (5.85, 8.72, 11.45), (11.45, 14.16, dur(SONG))]
BITS = ['bit1-kagebunshin.mp4', 'bit2-pasta-bono.mp4', 'bit3-taxi.mp4']
HOOK = 'こんななるとわ\nまじでやだ〜'
ITEMS = ['影分身全員\nドーパガキ〜', 'ラーメン嫌いで\nパスタ食う〜', '移動は走らず\nヘイタクシー']

def telop(top, bot, path):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def block(t, cy, size, fill):
        f = ImageFont.truetype(FONT, size)
        d.multiline_text((W / 2, cy), t, font=f, fill=fill, anchor='mm', align='center', spacing=14,
                         stroke_width=10, stroke_fill=(0, 0, 0, 255))
    if top: block(top, 330, 104, (255, 140, 0, 255))
    if bot: block(bot, 1560, 112, (255, 255, 255, 255))
    im.save(path)

parts = []
for k, ((s, i, e), bit) in enumerate(zip(SEG, BITS)):
    L = e - s; r = dur(bit) / L
    telop(HOOK, None, f'_t{k}a.png'); telop(HOOK, ITEMS[k], f'_t{k}b.png')
    ff('-i', bit, '-i', f'_t{k}a.png', '-i', f'_t{k}b.png', '-filter_complex',
       f'[0:v]setpts=PTS/{r:.5f},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=24[v];'
       f"[v][1:v]overlay=0:0:enable='lt(t,{i - s:.3f})'[v1];[v1][2:v]overlay=0:0:enable='gte(t,{i - s:.3f})',format=yuv420p[o]",
       '-map', '[o]', '-t', f'{L:.3f}', '-an', '-c:v', 'libx264', '-crf', '18', f'_p{k}.mp4')
    parts.append(f'_p{k}.mp4')
with open('_l.txt', 'w') as f: f.writelines(f"file '{p}'\n" for p in parts)
ff('-f', 'concat', '-safe', '0', '-i', '_l.txt', '-c', 'copy', '_v.mp4')
ff('-i', '_v.mp4', '-i', SONG, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', OUT)
for p in os.listdir('.'):
    if p.startswith('_'): os.remove(p)
