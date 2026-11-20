"""忍者風のおしゃれ編集版。歌を流しながらネタ1〜3を進める。
使い方: python3 ninja_edit.py 歌.mp3 出力.mp4   (assets/output/naruto-iyada/anime で実行)
環境変数: NINJA_FONT(毛筆フォント、既定 Yuji Boku)、FALLBACK_FONT(「〜」用)、YUNET(顔検出モデル)

演出:
- 歌詞は毛筆フォント。後ろに墨の筆跡の帯が左から右へサッと引かれて出る
- カラオケ風に、歌った所から色が変わる(サビ=朱色、ネタの行=金色)
- 左上に赤い判子「其ノ壱/弐/参」がドンと押される(揺れ付き)
- ネタの切り替わりで、手裏剣が回転しながら横切り、煙がボフッと広がる
- 周辺減光と軽いフィルム粒子
- 歌詞の位置は顔検出で、顔に重ならない高さを選ぶ
"""
import sys, os, subprocess, math, shutil, json
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SONG, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 24
NINJA = os.environ.get('NINJA_FONT', 'YujiBoku-Regular.ttf')  # github.com/google/fonts ofl/yujiboku
FALLBACK_FONT = os.environ.get('FALLBACK_FONT', 'ZenAntique-Regular.ttf')  # ofl/zenantique(「〜」用)
GOTH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
YUNET = os.environ.get('YUNET', 'yunet.onnx')
SAME_POS = os.environ.get('SAME_POS', '1') == '1'  # ネタの行をサビと同じ位置に出し、サビは消す
rng = np.random.default_rng(7)

def ff(*a): subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *a], check=True)
def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))

T_END = dur(SONG)
SEG = [(0.00, 5.85), (5.85, 11.45), (11.45, T_END)]
SUNG = [((0.52, 3.11), (3.22, 5.68)), ((5.85, 8.59), (8.72, 11.16)), ((11.45, 14.05), (14.16, 16.63))]
if os.environ.get('LAYOUT'):
    _L = json.loads(os.environ['LAYOUT'])
    SEG = [(a, b if b is not None else T_END) for a, b in _L['SEG']]
    SUNG = [tuple(tuple(x) for x in p_) for p_ in _L['SUNG']]
BITS = ['bit1-sing.mp4', 'bit2-pasta-bono.mp4', 'bit3-taxi.mp4']
HOOK = ['こんなナルトは', 'まじでやだ〜']
ITEMS = [['分身全員', 'ドパガキ〜'], ['ラーメン嫌いで', 'パスタ食う〜'], ['移動は走らず', 'ヘイタクシー']]
KANJI = ['壱', '弐', '参']
WHITE, INK = (255, 255, 255), (12, 10, 10)
SHU, GOLD = (255, 112, 70), (255, 204, 60)  # 朱(明るめ)、金
HANKO_RED = (214, 44, 32)

# ---------- 下地の映像 ----------
parts = []
for k, ((s, e), bit) in enumerate(zip(SEG, BITS)):
    r = dur(bit) / (e - s)
    ff('-i', bit, '-vf', f'setpts=PTS/{r:.5f},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={FPS},format=yuv420p',
       '-t', f'{e - s:.3f}', '-an', '-c:v', 'libx264', '-crf', '17', f'_b{k}.mp4')
    parts.append(f'_b{k}.mp4')
with open('_l.txt', 'w') as f: f.writelines(f"file '{p}'\n" for p in parts)
ff('-f', 'concat', '-safe', '0', '-i', '_l.txt', '-c', 'copy', '_base.mp4')

# ---------- 顔を避けた配置 ----------
det = cv2.FaceDetectorYN.create(YUNET, '', (540, 960), 0.6, 0.3, 5000)
cap = cv2.VideoCapture('_base.mp4'); faces = []
while True:
    ok, fr = cap.read()
    if not ok: break
    _, fs = det.detect(cv2.resize(fr, (540, 960)))
    faces.append([(a * 2 - 30, b * 2 - 40, (a + c) * 2 + 30, (b + d) * 2 + 30) for a, b, c, d in (fs[:, :4] if fs is not None else [])])
def overlap(y0, y1, t0, t1):
    tot = 0
    for fi in range(int(t0 * FPS), min(len(faces), int(t1 * FPS))):
        for a, b, c, d in faces[fi]:
            tot += max(0, min(y1, d) - max(y0, b)) * max(0, min(c, W - 80) - max(a, 80))
    return tot
POS = []
for k in range(3):
    (s0, e0), (_, (i0, _)) = SEG[k], SUNG[k]
    best = None
    for hy in range(360, 1400, 20):
        oh = overlap(hy - 160, hy + 160, s0, e0)
        for iy in range(hy + 340, 1760, 20):
            sc = oh + overlap(iy - 170, iy + 170, i0, e0) + (abs(hy - 380) + abs(iy - 1600)) * 40
            if best is None or sc < best[0]: best = (sc, hy, iy)
    POS.append(best[1:])
    print(f'ネタ{k + 1}: サビ y={best[1]} / ネタの行 y={best[2]}')

# ---------- 素材 ----------
_fc = {}
def F(path, sz):
    if (path, sz) not in _fc: _fc[(path, sz)] = ImageFont.truetype(path, sz)
    return _fc[(path, sz)]

def text_layers(text, size, col, stroke=10):
    """(白の文字, 色付きの文字, 影) を返す。「〜」は代替フォント"""
    f, fb = F(NINJA, size), F(FALLBACK_FONT, int(size * 0.95))
    adv = [(fb if ch == '〜' else f).getlength(ch) * 0.98 for ch in text]
    tw = int(sum(adv)) + size // 3; th = int(size * 1.35); pad = stroke + 30
    def draw(fill, sfill, off=(0, 0)):
        im = Image.new('RGBA', (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        x = pad + off[0]
        for ch, a in zip(text, adv):
            ft = fb if ch == '〜' else f
            d.text((x, pad + th / 2 + off[1]), ch, font=ft, fill=fill, anchor='lm', stroke_width=stroke, stroke_fill=sfill)
            x += a
        return im
    sh = draw((0, 0, 0, 170), (0, 0, 0, 170), (6, 9)).filter(ImageFilter.GaussianBlur(8))
    glow = draw((255, 255, 255, 90), (255, 255, 255, 90)).filter(ImageFilter.GaussianBlur(10))
    sh = Image.alpha_composite(sh, glow)
    return draw(WHITE + (255,), INK + (255,)), draw(col + (255,), INK + (255,)), sh, pad, tw

def ink_band(w, h):
    """墨の筆跡の帯(左→右に引いた形、ガサガサの縁とかすれ)"""
    x = np.linspace(0, 1, w)
    top = h * (0.18 + 0.06 * np.sin(x * 7 + 1) + 0.05 * rng.standard_normal(w).cumsum() / np.sqrt(w))
    bot = h * (0.84 - 0.07 * np.sin(x * 5) + 0.05 * rng.standard_normal(w).cumsum() / np.sqrt(w))
    top[:int(w * .06)] += np.linspace(h * .25, 0, int(w * .06)); bot[-int(w * .1):] -= np.linspace(0, h * .3, int(w * .1))
    yy = np.arange(h)[:, None]
    a = ((yy > top[None]) & (yy < bot[None])).astype(np.float32)
    streak = (rng.random((h, 1)) > 0.86).astype(np.float32) * (np.clip(x[None] - 0.55, 0, 1) * 2.2)  # 右側のかすれ
    a *= 1 - np.clip(streak, 0, 1)
    a = cv2.GaussianBlur(a, (0, 0), 1.6)
    noise = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32), (0, 0), 3)
    a *= 0.82 + 0.18 * noise
    im = np.zeros((h, w, 4), np.uint8); im[..., :3] = (14, 12, 12); im[..., 3] = (np.clip(a, 0, 1) * 225).astype(np.uint8)
    return Image.fromarray(im)

def hanko(kanji, sz=230):
    im = Image.new('RGBA', (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 6, sz - 7, sz - 7], radius=18, fill=HANKO_RED + (255,))
    d.rounded_rectangle([18, 18, sz - 19, sz - 19], radius=10, outline=(255, 235, 220, 255), width=5)
    f = F(NINJA, int(sz * 0.30))
    for j, ch in enumerate(['其', 'ノ', kanji]):
        d.text((sz / 2, sz * (0.24 + j * 0.27)), ch, font=f, fill=(255, 240, 230, 255), anchor='mm')
    a = np.array(im); m = rng.random(a.shape[:2]) > 0.93  # かすれ
    a[..., 3][m] = (a[..., 3][m] * 0.35).astype(np.uint8)
    return Image.fromarray(a).rotate(-6, resample=Image.BICUBIC, expand=True)

def shuriken(sz=380):
    im = Image.new('RGBA', (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = sz / 2
    pts = []
    for i in range(8):
        ang = i * math.pi / 4; r = c * 0.96 if i % 2 == 0 else c * 0.28
        pts.append((c + r * math.cos(ang), c + r * math.sin(ang)))
    d.polygon(pts, fill=(70, 74, 82, 255), outline=(200, 205, 215, 255))
    for i in range(0, 8, 2):
        ang = i * math.pi / 4
        d.line([(c, c), (c + c * 0.9 * math.cos(ang), c + c * 0.9 * math.sin(ang))], fill=(160, 166, 178, 255), width=4)
    d.ellipse([c - 16, c - 16, c + 16, c + 16], fill=(20, 20, 24, 255))
    return im

def smoke(t, cx, cy):
    """白い煙のかたまり(t=0〜1で広がって消える)"""
    m = np.zeros((H // 4, W // 4), np.float32)
    r2 = np.random.default_rng(3)
    for _ in range(40):
        ox, oy = r2.normal(0, 70), r2.normal(0, 90); rr = r2.uniform(40, 90) * (0.5 + 1.2 * t)
        cv2.circle(m, (int((cx + ox * (1 + 2 * t)) / 4), int((cy + oy * (1 + 2 * t)) / 4)), int(rr / 4), 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), 12) * (1 - t) ** 1.3
    m = cv2.resize(np.clip(m, 0, 1), (W, H))
    im = np.zeros((H, W, 4), np.uint8); im[..., :3] = 245; im[..., 3] = (m * 235).astype(np.uint8)
    return Image.fromarray(im)

# 周辺減光+粒子
yy, xx = np.mgrid[0:H, 0:W]
vig = np.clip((np.hypot((xx - W / 2) / (W * .62), (yy - H / 2) / (H * .62)) - 0.55) * 1.6, 0, 1) ** 1.5
VIG = np.zeros((H, W, 4), np.uint8); VIG[..., 3] = (vig * 150).astype(np.uint8)
VIG = Image.fromarray(VIG)
GRAIN = [Image.fromarray(np.dstack([np.full((H, W), 128, np.uint8)] * 3 + [(rng.random((H, W)) * 14).astype(np.uint8)])) for _ in range(4)]

# 歌詞レイヤーを先に作る
LINES = []  # (k, kind, j, layers)
for k in range(3):
    hy, iy = POS[k]
    for j, t in enumerate(HOOK): LINES.append((k, 'h', j, text_layers(t, 112, SHU), hy - 66 + j * 132))
    for j, t in enumerate(ITEMS[k]): LINES.append((k, 'i', j, text_layers(t, 124, GOLD, 11), (hy - 72 + j * 146) if SAME_POS else (iy - 72 + j * 146)))
BANDS = {}
for k in range(3):
    BANDS[(k, 'h')] = ink_band(1040, 360); BANDS[(k, 'i')] = ink_band(1040, 380)
HANKO = [hanko(c) for c in KANJI]
SHURI = shuriken()

def ease(u): u = min(max(u, 0), 1); return 1 - (1 - u) ** 3

os.makedirs('_ov', exist_ok=True)
N = int(T_END * FPS)
for fi in range(N):
    t = fi / FPS
    k = 0 if t < SEG[1][0] else (1 if t < SEG[2][0] else 2)
    s0 = SEG[k][0]; (h0, h1), (i0, i1) = SUNG[k]; hy, iy = POS[k]
    cv = VIG.copy()
    # 墨の帯(左から引かれる)
    for kind, cy, start in (('h', hy, s0 + 0.05), ('i', hy if SAME_POS else iy, i0 - 0.12)):
        u = ease((t - start) / 0.28)
        if u <= 0: continue
        if SAME_POS and kind == 'h' and t >= i0 - 0.12: continue
        b = BANDS[(k, kind)]; w = int(b.size[0] * u)
        if w > 2: cv.alpha_composite(b.crop((0, 0, w, b.size[1])), (W // 2 - b.size[0] // 2, int(cy - b.size[1] / 2)))
    # 歌詞(カラオケ)
    for (kk, kind, j, (base, hi, sh, pad, tw), cy) in LINES:
        if kk != k: continue
        a0, a1 = (h0, h1) if kind == 'h' else (i0, i1)
        appear = (s0 + 0.15 if kind == 'h' else i0 - 0.05) + j * 0.06
        if t < appear: continue
        if SAME_POS and kind == 'h' and t >= i0 - 0.12: continue  # ネタの行が出たらサビは消す
        prog = (t - a0) / (a1 - a0) * 2 - j
        x0, y0 = int(W / 2 - base.size[0] / 2), int(cy - base.size[1] / 2)
        u = ease((t - appear) / 0.22); dy = int((1 - u) * 26)
        lay = base.copy()
        cut = int(pad + tw * max(0.0, min(1.0, prog)))
        if cut > pad:
            m = Image.new('L', lay.size, 0); ImageDraw.Draw(m).rectangle([0, 0, cut, lay.size[1]], fill=255)
            lay.paste(hi, (0, 0), Image.composite(hi.split()[3], Image.new('L', lay.size, 0), m))
        if u < 1:
            al = lay.split()[3].point(lambda v: int(v * u)); lay.putalpha(al)
            sh2 = sh.copy(); sh2.putalpha(sh.split()[3].point(lambda v: int(v * u)))
        else: sh2 = sh
        cv.alpha_composite(sh2, (x0, y0 + dy)); cv.alpha_composite(lay, (x0, y0 + dy))
    # 判子(ドンと押す)
    u = (t - s0) / 0.22
    if u >= 0:
        sc = 1.0 + 0.9 * (1 - ease(u)); hk = HANKO[k]
        img = hk.resize((int(hk.size[0] * sc), int(hk.size[1] * sc)), Image.LANCZOS) if sc > 1.001 else hk
        shake = int(6 * math.sin(u * 40) * max(0, 1 - (u - 1) * 3)) if 1 <= u < 1.4 else 0
        cv.alpha_composite(img, (int(170 - img.size[0] / 2) + shake, int(190 - img.size[1] / 2)))
    # 切り替わり: 手裏剣+煙
    for b in (SEG[1][0], SEG[2][0]):
        v = (t - b + 0.18) / 0.5
        if 0 <= v <= 1:
            sm = smoke(v, W / 2, H * 0.48); cv.alpha_composite(sm)
            ang = -v * 1100; img = SHURI.rotate(ang, resample=Image.BICUBIC)
            px = int(-300 + v * (W + 600)); py = int(H * 0.40 - 120 * math.sin(v * math.pi))
            for tr in (3, 2, 1):  # 残像
                g = img.copy(); g.putalpha(img.split()[3].point(lambda a_, tr=tr: int(a_ * 0.18 * (4 - tr))))
                cv.alpha_composite(g, (px - tr * 70 - img.size[0] // 2, py + tr * 8 - img.size[1] // 2))
            cv.alpha_composite(img, (px - img.size[0] // 2, py - img.size[1] // 2))
    cv.alpha_composite(GRAIN[fi % 4])
    cv.save(f'_ov/{fi:05d}.png', compress_level=1)

ff('-i', '_base.mp4', '-framerate', str(FPS), '-i', '_ov/%05d.png', '-i', SONG, '-filter_complex',
   '[0:v]eq=contrast=1.06:saturation=1.08[b];[b][1:v]overlay=0:0:format=auto,format=yuv420p[v]',
   '-map', '[v]', '-map', '2:a', '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-shortest', OUT)
shutil.rmtree('_ov')
for p in os.listdir('.'):
    if p.startswith('_'): os.remove(p)
