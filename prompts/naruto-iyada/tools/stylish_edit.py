"""歌いながら進む版を、見やすくおしゃれなテロップで仕上げる。
使い方: python3 stylish_edit.py 歌.mp3 出力.mp4  (assets/output/naruto-iyada で実行)
テロップ:
- 歌詞はカラオケ風に、歌った所から色が変わる(サビ=オレンジ、ネタの行=黄色)
- 出るときにポンと弾む。下の歌詞の後ろに暗いグラデーションを敷いて読みやすく
- 左上にネタ番号のバッジ(①②③)と、なるとの渦巻きマーク
- ネタの切り替わりで白いフラッシュ
"""
import sys, os, subprocess, math, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SONG, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 24
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
def ff(*a): subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *a], check=True)
def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))

T_END = dur(SONG)
SEG = [(0.00, 5.85), (5.85, 11.45), (11.45, T_END)]
BITS = ['bit1-sing.mp4', 'bit2-pasta-bono.mp4', 'bit3-taxi.mp4']
# 歌っている時間(歌ファイル基準): サビ, ネタの行
SUNG = [((0.52, 3.11), (3.22, 5.68)), ((5.85, 8.59), (8.72, 11.16)), ((11.45, 14.05), (14.16, 16.63))]
HOOK = ['こんななるとわ', 'まじでやだ〜']
ITEMS = [['影分身全員', 'ドーパガキ〜'], ['ラーメン嫌いで', 'パスタ食う〜'], ['移動は走らず', 'ヘイタクシー']]
ORANGE, YELLOW, WHITE, NAVY = (255, 138, 0), (255, 225, 77), (255, 255, 255), (20, 24, 48)

# 1) 下地の映像(テロップなし)
parts = []
for k, ((s, e), bit) in enumerate(zip(SEG, BITS)):
    L = e - s; r = dur(bit) / L
    ff('-i', bit, '-vf', f'setpts=PTS/{r:.5f},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={FPS},format=yuv420p',
       '-t', f'{L:.3f}', '-an', '-c:v', 'libx264', '-crf', '17', f'_b{k}.mp4')
    parts.append(f'_b{k}.mp4')
with open('_l.txt', 'w') as f: f.writelines(f"file '{p}'\n" for p in parts)
ff('-f', 'concat', '-safe', '0', '-i', '_l.txt', '-c', 'copy', '_base.mp4')

# 2) テロップを1コマずつ描く
fonts = {}
def font(sz):
    if sz not in fonts: fonts[sz] = ImageFont.truetype(FONT, sz)
    return fonts[sz]

def karaoke_line(img, text, cx, cy, size, prog, col, stroke=11):
    """prog(0〜1)の所まで col、残りは白。縁取り+影つき"""
    f = font(size)
    bb = f.getbbox(text); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x0, y0 = int(cx - tw / 2 - bb[0]), int(cy - th / 2 - bb[1])
    pad = stroke + 20
    lay = Image.new('RGBA', (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    ox, oy = pad - bb[0], pad - bb[1]
    # 影
    sh = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((ox + 6, oy + 8), text, font=f, fill=(0, 0, 0, 150), stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    base = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(base).text((ox, oy), text, font=f, fill=WHITE + (255,), stroke_width=stroke, stroke_fill=NAVY + (255,))
    hi = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(hi).text((ox, oy), text, font=f, fill=col + (255,), stroke_width=stroke, stroke_fill=NAVY + (255,))
    cut = int(pad + tw * max(0.0, min(1.0, prog)))
    m = Image.new('L', lay.size, 0); ImageDraw.Draw(m).rectangle([0, 0, cut, lay.size[1]], fill=255)
    out = Image.alpha_composite(sh, base); out.paste(hi, (0, 0), Image.composite(hi.split()[3], Image.new('L', lay.size, 0), m))
    return out, (x0 - pad + bb[0], y0 - pad + bb[1])

def pop(t):
    """出現からの経過秒 → 拡大率(ポンと弾む)"""
    if t < 0: return 0
    if t > 0.25: return 1.0
    u = t / 0.25
    return 1 + 0.18 * math.sin(math.pi * u) * (1 - u) + (u - 1) * 0.35 * (1 - u) ** 2 * 0 if u > 0.4 else 0.55 + 0.6 * u / 0.4

def paste_scaled(canvas, lay, pos, s):
    if s <= 0: return
    if abs(s - 1) > 1e-3:
        w, h = lay.size
        lay = lay.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
        pos = (int(pos[0] + w / 2 - lay.size[0] / 2), int(pos[1] + h / 2 - lay.size[1] / 2))
    canvas.alpha_composite(lay, (max(0, pos[0]), max(0, pos[1])))

def spiral(sz):
    im = Image.new('RGBA', (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([2, 2, sz - 3, sz - 3], fill=(255, 255, 255, 255), outline=NAVY + (255,), width=5)
    c = sz / 2; pts = [(c + (2 + 0.42 * c * t / (2.6 * math.pi)) * math.cos(t), c + (2 + 0.42 * c * t / (2.6 * math.pi)) * math.sin(t)) for t in np.linspace(0, 2.6 * math.pi, 120)]
    d.line(pts, fill=(235, 80, 120, 255), width=max(3, sz // 12), joint='curve')
    return im

def badge(n):
    im = Image.new('RGBA', (300, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 299, 119], radius=60, fill=ORANGE + (235,), outline=WHITE + (255,), width=5)
    im.alpha_composite(spiral(92), (14, 14))
    d.text((200, 60), f'その{n}', font=font(56), fill=WHITE, anchor='mm', stroke_width=4, stroke_fill=NAVY)
    return im

grad = Image.new('RGBA', (W, H), (0, 0, 0, 0))
ga = np.zeros((H, W), np.uint8)
for y in range(1180, H): ga[y, :] = int(170 * min(1, (y - 1180) / 380))
for y in range(0, 560): ga[y, :] = max(ga[y, 0], int(120 * (1 - y / 560)))
grad.putalpha(Image.fromarray(ga))
BADGES = [badge(i + 1) for i in range(3)]

os.makedirs('_ov', exist_ok=True)
N = int(T_END * FPS)
for fi in range(N):
    t = fi / FPS
    k = 0 if t < SEG[1][0] else (1 if t < SEG[2][0] else 2)
    s0 = SEG[k][0]
    cv = grad.copy()
    # バッジ(区間の頭でポン)
    paste_scaled(cv, BADGES[k], (40, 70), pop(t - s0))
    (h0, h1), (i0, i1) = SUNG[k]
    # サビ(上)
    if t >= s0:
        sc = pop(t - s0)
        prog = (t - h0) / (h1 - h0)
        # 2行を通しで進める
        p1, p2 = min(1, prog * 2), max(0, prog * 2 - 1)
        for j, (txt, pp) in enumerate(zip(HOOK, (p1, p2))):
            lay, pos = karaoke_line(cv, txt, W / 2, 290 + j * 125, 104, pp, ORANGE)
            paste_scaled(cv, lay, pos, sc)
    # ネタの行(下)
    if t >= i0 - 0.05:
        sc = pop(t - (i0 - 0.05))
        prog = (t - i0) / (i1 - i0)
        p1, p2 = min(1, prog * 2), max(0, prog * 2 - 1)
        for j, (txt, pp) in enumerate(zip(ITEMS[k], (p1, p2))):
            lay, pos = karaoke_line(cv, txt, W / 2, 1530 + j * 140, 118, pp, YELLOW, stroke=12)
            paste_scaled(cv, lay, pos, sc)
    # 切り替わりの白フラッシュ
    for b in (SEG[1][0], SEG[2][0]):
        if 0 <= t - b < 0.17:
            a = int(220 * (1 - (t - b) / 0.17))
            cv.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, a)))
    cv.save(f'_ov/{fi:05d}.png', compress_level=1)

ff('-i', '_base.mp4', '-framerate', str(FPS), '-i', '_ov/%05d.png', '-i', SONG, '-filter_complex', '[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]',
   '-map', '[v]', '-map', '2:a', '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-shortest', OUT)
shutil.rmtree('_ov')
for p in os.listdir('.'):
    if p.startswith('_'): os.remove(p)
