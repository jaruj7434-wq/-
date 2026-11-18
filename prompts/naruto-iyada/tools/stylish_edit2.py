"""歌いながら進む版を、見やすくおしゃれなテロップで仕上げる(v2: 毛筆フォント、顔を避ける配置)。
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
BRUSH = '/usr/share/fonts/truetype/kouzan-mouhitsu/kouzan-mouhitsu.ttf'  # 衡山毛筆フォント(apt: fonts-kouzan-mouhitsu)
YUNET = os.environ.get('YUNET', 'yunet.onnx')  # 顔検出モデル(Hugging Face: opencv/face_detection_yunet)
def ff(*a): subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *a], check=True)
def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))

T_END = dur(SONG)
SEG = [(0.00, 5.85), (5.85, 11.45), (11.45, T_END)]
BITS = ['bit1-sing.mp4', 'bit2-pasta-bono.mp4', 'bit3-taxi.mp4']
# 歌っている時間(歌ファイル基準): サビ, ネタの行
SUNG = [((0.52, 3.11), (3.22, 5.68)), ((5.85, 8.59), (8.72, 11.16)), ((11.45, 14.05), (14.16, 16.63))]
HOOK = ['こんなナルトは', 'まじでやだ〜']
if os.environ.get('LAYOUT'):  # 例: '{"SEG": [[0,5],[5,9.1],[9.1,null]], "SUNG": [[[1.08,3.0],[3.22,4.9]], ...]}'
    import json
    _L = json.loads(os.environ['LAYOUT'])
    SEG = [(a, b if b is not None else T_END) for a, b in _L['SEG']]
    SUNG = [tuple(tuple(x) for x in p_) for p_ in _L['SUNG']]
ITEMS = [['分身全員', 'ドパガキ〜'], ['ラーメン嫌いで', 'パスタ食う〜'], ['移動は走らず', 'ヘイタクシー']]
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

bfonts = {}
def bfont(sz):
    if sz not in bfonts: bfonts[sz] = ImageFont.truetype(BRUSH, sz)
    return bfonts[sz]

FALLBACK = '〜'  # 毛筆フォントでは空の字形なので、ゴシック体で描く
def draw_brush(d, ox, oy, text, f, fill, stroke, sfill, track):
    for pas in (0, 1):
        x = ox
        for ch in text:
            ff_ = font(int(f.size * 0.9)) if ch in FALLBACK else f
            yy = oy + (f.size * 0.12 if ch in FALLBACK else 0)
            if pas == 0:
                d.text((x, yy), ch, font=ff_, fill=sfill, stroke_width=stroke, stroke_fill=sfill)
            else:
                d.text((x, yy), ch, font=ff_, fill=fill, stroke_width=3, stroke_fill=fill)  # 少し太らせる
            x += f.getlength(ch) * track

def karaoke_line(img, text, cx, cy, size, prog, col, stroke=11, track=0.86):
    """prog(0〜1)の所まで col、残りは白。毛筆フォント、縁取り+影つき"""
    f = bfont(size)
    tw = int(sum(f.getlength(ch) for ch in text[:-1]) * track + f.getlength(text[-1]) + size * 0.25)
    bb = f.getbbox('あ漢'); th = bb[3] - bb[1]
    pad = stroke + 24
    lay = Image.new('RGBA', (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
    ox, oy = pad, pad - bb[1]
    x0, y0 = int(cx - tw / 2), int(cy - th / 2)
    sh = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    draw_brush(ImageDraw.Draw(sh), ox + 6, oy + 8, text, f, (0, 0, 0, 150), stroke, (0, 0, 0, 150), track)
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    base = Image.new('RGBA', lay.size, (0, 0, 0, 0)); draw_brush(ImageDraw.Draw(base), ox, oy, text, f, WHITE + (255,), stroke, NAVY + (255,), track)
    hi = Image.new('RGBA', lay.size, (0, 0, 0, 0)); draw_brush(ImageDraw.Draw(hi), ox, oy, text, f, col + (255,), stroke, NAVY + (255,), track)
    bb = (0, 0)
    cut = int(pad + tw * max(0.0, min(1.0, prog)))
    m = Image.new('L', lay.size, 0); ImageDraw.Draw(m).rectangle([0, 0, cut, lay.size[1]], fill=255)
    out = Image.alpha_composite(sh, base); out.paste(hi, (0, 0), Image.composite(hi.split()[3], Image.new('L', lay.size, 0), m))
    return out, (x0 - pad, y0 - pad)

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

import cv2
det = cv2.FaceDetectorYN.create(YUNET, '', (540, 960), 0.6, 0.3, 5000)
cap = cv2.VideoCapture('_base.mp4'); faces = []
while True:
    ok, fr = cap.read()
    if not ok: break
    _, fs = det.detect(cv2.resize(fr, (540, 960)))
    faces.append([(f_[0] * 2 - 30, f_[1] * 2 - 40, f_[0] * 2 + f_[2] * 2 + 30, f_[1] * 2 + f_[3] * 2 + 30) for f_ in (fs if fs is not None else [])])
def overlap(y0, y1, t0, t1):
    tot = 0
    for fi in range(int(t0 * FPS), min(len(faces), int(t1 * FPS))):
        for (a, b, c, d) in faces[fi]:
            if c > 90 and a < W - 90:  # テロップは横幅ほぼいっぱい
                tot += max(0, min(y1, d) - max(y0, b)) * (min(c, W - 90) - max(a, 90))
    return tot
def choose(t0, t1, hgt, default, avoid=None):
    best = None
    for cy in range(200, 1760, 20):
        y0, y1 = cy - hgt / 2, cy + hgt / 2
        if avoid and not (y1 < avoid[0] - 20 or y0 > avoid[1] + 20): continue
        score = overlap(y0, y1, t0, t1) + abs(cy - default) * 40
        if best is None or score < best[0]: best = (score, cy)
    return best[1]
POS = []
for k in range(3):
    s0, e0 = SEG[k]; (h0, h1), (i0, i1) = SUNG[k]
    # サビは必ずネタの行より上。バッジ(y<200)とは重ねない
    best = None
    for hy in range(340, 1400, 20):
        oh = overlap(hy - 150, hy + 150, s0, e0)
        for iy in range(hy + 330, 1760, 20):
            sc = oh + overlap(iy - 160, iy + 160, i0, e0) + (abs(hy - 360) + abs(iy - 1600)) * 40
            if best is None or sc < best[0]: best = (sc, hy, iy)
    hy, iy = best[1], best[2]
    POS.append((hy, iy))
    print(f'ネタ{k+1}: サビの中心 y={hy}, ネタの行の中心 y={iy}')
def band(cy, hgt):
    """テロップの後ろに敷く、ぼかした暗い帯"""
    m = np.zeros((H, W), np.float32); y0, y1 = int(cy - hgt / 2), int(cy + hgt / 2)
    m[max(0, y0):min(H, y1), :] = 1
    m = cv2.GaussianBlur(m, (0, 0), 45)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); im.putalpha(Image.fromarray((m * 140).astype(np.uint8)))
    return im
BANDS = [(band(h, 300), band(i, 320)) for h, i in POS]
grad = Image.new('RGBA', (W, H), (0, 0, 0, 0))
BADGES = [badge(i + 1) for i in range(3)]

os.makedirs('_ov', exist_ok=True)
N = int(T_END * FPS)
for fi in range(N):
    t = fi / FPS
    k = 0 if t < SEG[1][0] else (1 if t < SEG[2][0] else 2)
    s0 = SEG[k][0]
    cv = grad.copy()
    hy, iy = POS[k]
    cv.alpha_composite(BANDS[k][0])
    if t >= SUNG[k][1][0] - 0.05: cv.alpha_composite(BANDS[k][1])
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
            lay, pos = karaoke_line(cv, txt, W / 2, hy - 68 + j * 136, 124, pp, ORANGE)
            paste_scaled(cv, lay, pos, sc)
    # ネタの行(下)
    if t >= i0 - 0.05:
        sc = pop(t - (i0 - 0.05))
        prog = (t - i0) / (i1 - i0)
        p1, p2 = min(1, prog * 2), max(0, prog * 2 - 1)
        for j, (txt, pp) in enumerate(zip(ITEMS[k], (p1, p2))):
            lay, pos = karaoke_line(cv, txt, W / 2, iy - 72 + j * 146, 134, pp, YELLOW, stroke=12)
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
