# 天皇賞・秋 データ解説ショート 編集: 参考動画と同じ「図解スライド型」を1フレームずつ描画して書き出す
# 入力 (Higgs sandbox ~/aki): img/*.png, vids/V*.mp4, vo2/timingB.txt, vo2/narrationB.wav, bgm.mp3
# 出力: ~/aki/ed/video_noaudio.mp4  (音声は run.sh で合成)
import os, re, subprocess, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
A = os.path.expanduser('~/aki')
FONT = os.path.expanduser('~/.fonts/MPLUSRounded1c-Black.ttf')
DARK, RED, YEL, WHITE, GREEN, BLUE = (35, 40, 38), (226, 38, 38), (255, 214, 0), (255, 255, 255), (32, 120, 70), (40, 100, 210)
WAKU = {1: ((255, 255, 255), DARK), 2: ((30, 30, 30), WHITE), 3: ((220, 40, 40), WHITE), 4: ((40, 90, 200), WHITE),
        5: ((250, 210, 0), DARK), 6: ((40, 150, 70), WHITE), 7: ((245, 140, 30), WHITE), 8: ((240, 130, 170), WHITE)}

# ---------- timing ----------
T = {}
for l in open(f'{A}/vo2/timingB.txt'):
    n, _, s, _, d = l.split(); T[int(n)] = (float(s), float(s) + float(d))
NL = max(T)
TAIL = 1.2
END = T[NL][1] + TAIL
def S(n): return T[n][0]
def E(n): return S(n + 1) if n < NL else END
def at(n, frac): return S(n) + (T[n][1] - S(n)) * frac

# ---------- primitives ----------
_fc = {}
def font(sz):
    if sz not in _fc: _fc[sz] = ImageFont.truetype(FONT, sz)
    return _fc[sz]

def rich(text, sz, color=DARK, stroke=WHITE, sw=None, hl=RED, shadow=True):
    """text with {highlight} segments -> RGBA sprite"""
    sw = sw if sw is not None else max(4, sz // 9)
    segs = [(p, hl if i % 2 else color) for i, p in enumerate(re.split(r'[{}]', text)) if p]
    f = font(sz)
    widths = [f.getbbox(p, stroke_width=sw)[2] for p, _ in segs]
    tw = sum(widths) + 2 * sw + 12; th = int(sz * 1.35) + 2 * sw + 12
    im = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(sh); x = sw + 6
        for (p, c), w_ in zip(segs, widths):
            d.text((x + 4, sw + 10), p, font=f, fill=(0, 0, 0, 90), stroke_width=sw, stroke_fill=(0, 0, 0, 90)); x += w_
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(4)))
    d = ImageDraw.Draw(im); x = sw + 6
    for (p, c), w_ in zip(segs, widths):
        d.text((x, sw + 6), p, font=f, fill=c, stroke_width=sw, stroke_fill=stroke); x += w_
    return im.crop(im.getbbox())

def fit(im, maxw):
    return im if im.width <= maxw else im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)

def label(text, sz=46, bg=GREEN):
    f = font(sz); tw = f.getbbox(text)[2]; pw, ph = tw + 56, int(sz * 1.55)
    im = Image.new('RGBA', (pw + 8, ph + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 8, pw + 4, ph + 6), 16, fill=(0, 0, 0, 60))
    d.rounded_rectangle((0, 0, pw, ph), 16, fill=bg, outline=WHITE, width=5)
    d.text((28, ph / 2), text, font=f, fill=WHITE, anchor='lm'); return im

def box(text, sz=60, fg=DARK, bg=WHITE, border=None, pad=34):
    spr = rich(text, sz, fg, stroke=bg, sw=0, shadow=False)
    w, h = spr.width + pad * 2, spr.height + pad
    im = Image.new('RGBA', (w + 10, h + 12), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((5, 10, w + 5, h + 10), 20, fill=(0, 0, 0, 60))
    d.rounded_rectangle((0, 0, w, h), 20, fill=bg, outline=border or (200, 200, 200), width=6)
    im.alpha_composite(spr, (pad, pad // 2)); return im

def stamp(ok):
    c = RED if ok else BLUE; txt = '本当' if ok else 'ウソ'
    im = Image.new('RGBA', (560, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, 550, 250), 34, fill=(255, 255, 255, 235), outline=c, width=14)
    if ok: d.ellipse((50, 60, 190, 200), outline=c, width=20)
    else: d.line((60, 70, 180, 190), fill=c, width=24); d.line((180, 70, 60, 190), fill=c, width=24)
    d.text((370, 132), txt, font=font(120), fill=c, anchor='mm')
    return im.rotate(-8, expand=True, resample=Image.BICUBIC)

def mark(ok, sz=110):
    c = RED if ok else BLUE; im = Image.new('RGBA', (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, sz - 1, sz - 1), 18, fill=WHITE, outline=c, width=7)
    if ok: d.ellipse((20, 20, sz - 20, sz - 20), outline=c, width=12)
    else: d.line((24, 24, sz - 24, sz - 24), fill=c, width=14); d.line((sz - 24, 24, 24, sz - 24), fill=c, width=14)
    return im

def waku_badge(w, u, sz=44):
    bg, fg = WAKU[w]; t = f'{w}枠{u}番'; f = font(sz); tw = f.getbbox(t)[2]
    im = Image.new('RGBA', (tw + 40, int(sz * 1.5)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), 12, fill=bg, outline=(60, 60, 60), width=3)
    d.text((im.width / 2, im.height / 2), t, font=f, fill=fg, anchor='mm'); return im

def qcard():
    im = Image.new('RGBA', (230, 160), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 10, 226, 156), 22, fill=(0, 0, 0, 50))
    d.rounded_rectangle((0, 0, 222, 148), 22, fill=(253, 253, 248), outline=GREEN, width=7)
    d.text((111, 74), '？', font=font(90), fill=DARK, anchor='mm'); return im

def icon(i, w): im = Image.open(f'{A}/img/i{i}.png').convert('RGBA'); return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)

def card_frame(content, border=12, radius=26):
    w, h = content.size; im = Image.new('RGBA', (w + 2 * border + 12, h + 2 * border + 14), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 12, w + 2 * border + 6, h + 2 * border + 12), radius, fill=(0, 0, 0, 70))
    d.rounded_rectangle((0, 0, w + 2 * border, h + 2 * border), radius, fill=WHITE)
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius - 8, fill=255)
    im.paste(content.convert('RGB'), (border, border), m); return im

def cover(img, w, h):
    s = max(w / img.width, h / img.height); r = img.resize((int(img.width * s) + 1, int(img.height * s) + 1), Image.LANCZOS)
    x, y = (r.width - w) // 2, (r.height - h) // 2; return r.crop((x, y, x + w, y + h))

# ---------- video reader ----------
class Vid:
    def __init__(self, path, w, h, dur):
        src = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]))
        slow = max(1.0, (dur + 0.2) / (src - 0.1))
        vf = f'setpts={slow:.4f}*PTS,fps={FPS},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}'
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
        self.w, self.h, self.last = w, h, None
    def next(self):
        b = self.p.stdout.read(self.w * self.h * 3)
        if len(b) == self.w * self.h * 3: self.last = Image.frombytes('RGB', (self.w, self.h), b)
        return self.last

# ---------- elements ----------
EL = []
def pop_scale(dt):
    if dt < 0: return 0
    if dt < 0.12: return 0.55 + (1.12 - 0.55) * dt / 0.12
    if dt < 0.24: return 1.12 - 0.12 * (dt - 0.12) / 0.12
    return 1.0
def add(spr, cx, cy, t0, t1, pop=True, z=1):
    EL.append(dict(kind='spr', spr=spr, cx=cx, cy=cy, t0=t0, t1=t1, pop=pop, z=z, cache={}))
def add_vcard(path, cx, cy, w, h, t0, t1, z=1):
    EL.append(dict(kind='vcard', path=path, cx=cx, cy=cy, w=w, h=h, t0=t0, t1=t1, z=z, v=None, pop=True, cache={}))
def add_full(path, t0, t1, dim=0.38):
    EL.append(dict(kind='full', path=path, t0=t0, t1=t1, z=0, v=None, dim=dim))
def add_bg(name, t0, t1):
    EL.append(dict(kind='bg', img=Image.open(f'{A}/img/{name}.png').convert('RGB').resize((W, H), Image.LANCZOS), t0=t0, t1=t1, z=-1))
def img_card(i, w, h): return card_frame(cover(Image.open(f'{A}/img/{i}.png').convert('RGB'), w, h))
V = lambda k: f'{A}/vids/V{k}.mp4'

# ---------- subtitles ----------
SUB = {
1: '明日は、{天皇賞・秋}。',
2: '予想でよく言われる/「常識」が{3つ}あります',
3: '本当なのか/{過去10年}のデータで調べました',
4: '1つ目/「1番人気は信用できる」',
5: '実は昔は{真逆}/{1988年}から1番人気が/{12年連続}で負けていました',
6: 'でもこの10年は/1番人気が{7勝}/{4番人気以下}は/1頭も勝っていません',
7: '負けた2回は/スタートの{出遅れ}と/{7か月ぶり}の休み明け/ちゃんと理由がありました',
8: '結論/1番人気は{信用していい}',
9: '2つ目/「前哨戦の王道/毎日王冠組が強い」',
10: 'ところが10年で{32頭}が出て/勝ち馬も2着馬も{ゼロ}',
11: 'カギはレースの{間隔}/{5週以内}は1勝だけ/{9週以上}あけた馬は{9勝}',
12: 'エフフォーリア/イクイノックス/マスカレードボール/3頭ともダービー2着から/{5か月}休んで勝っています',
13: '今年の毎日王冠組は{6頭}/全頭{中3週}です',
14: '結論/毎日王冠組は{過信禁物}',
15: '3つ目/「東京2000mは内枠が有利」/スタート直後に/カーブがあるからです',
16: 'でも2枠は16頭で{勝ち馬ゼロ}/1枠で勝ったのも/2019年の{アーモンドアイ}だけです',
17: 'そして今年は/主役のクロワデュノールが/{1枠1番}',
18: '結論/{内枠有利}はウソ',
19: '本当だったのは/{1番人気}だけ',
20: 'じゃあ/何を見ればいいのか',
21: 'この10年の勝ち馬は{全頭}が/{東京のGⅠ}を勝ったことがあるか/{ダービー2着}の馬でした',
22: 'この条件がない馬は/のべ{110頭}で/1頭も勝っていません',
23: '今年当てはまるのは/{17頭中4頭}/クロワデュノール/シャンパンカラー/マスカレードボール/ダノンデサイル',
24: 'あんたの本命は誰だ？/{コメント}で教えてくれ',
}
SUBY = 1335
for n, txt in SUB.items():
    parts = txt.split('/'); lens = [len(re.sub(r'[{}]', '', p)) for p in parts]; a, b = T[n]; t = a
    for i, (p, L) in enumerate(zip(parts, lens)):
        d = (b - a) * L / sum(lens); t1 = t + d if i < len(parts) - 1 else E(n) - 0.02
        add(fit(rich(p, 68, WHITE, stroke=(20, 20, 20), sw=9, hl=YEL), 1000), W // 2, SUBY, t, t1, pop=False, z=9); t = t + d

# ---------- scenes ----------
CH = {1: '① 1番人気', 2: '② 毎日王冠', 3: '③ 内枠'}
def chapter(c, a, b): add(label(CH[c]), W // 2, 200, a, b, pop=False, z=5)

# 01 title
add_bg(0, 0, S(2))
add(rich('明日は', 84), W // 2, 210, 0, S(2))
add(rich('天皇賞・秋', 168), W // 2, 380, 0, S(2))
add(fit(rich('知らなきゃ損', 150, RED), 980), W // 2, 570, 0.15, S(2))
add_vcard(V(1), W // 2, 960, 900, 560, 0, S(2))
# 02 ? cards
add_bg(1, S(2), S(4))
for i, x in enumerate((250, 540, 830)): add(qcard(), x, 620, S(2) + 0.25 * i, S(3))
add(fit(rich('知らなきゃ損な{3つの“常識”}', 76), 1000), W // 2, 380, S(2) + 0.6, S(3))
# 03 10 years
add(rich('2016〜2025年', 92), W // 2, 330, S(3), S(4))
add(rich('{10}回', 200), W // 2, 540, S(3) + 0.3, S(4))
add(icon(6, 300), W // 2, 870, S(3) + 0.6, S(4))
# 04 chapter 1 full
add_full(V(2), S(4), S(5))
add(label(CH[1], 64), W // 2, 640, S(4), S(5), z=5)
add(fit(rich('「1番人気は{信用できる}」', 92, WHITE, stroke=(20, 20, 20), hl=YEL), 1020), W // 2, 820, S(4) + 0.3, S(5))
# 05-08
add_bg(0, S(5), S(9)); chapter(1, S(5), S(9))
add(rich('1988〜1999年', 92), W // 2, 360, S(5), S(6))
add(rich('1番人気が', 92), W // 2, 520, at(5, 0.35), S(6))
add(rich('{12}連敗', 190, hl=RED), W // 2, 720, at(5, 0.55), S(6))
add(rich('過去10年 1番人気', 84), W // 2, 340, S(6), S(7))
add(rich('{7}勝', 200), W // 2, 520, S(6) + 0.3, S(7))
add(rich('4番人気以下', 84), W // 2, 760, at(6, 0.5), S(7))
add(box('{0勝}', 120, fg=DARK, border=RED), W // 2, 930, at(6, 0.6), S(7))
add_vcard(V(3), 290, 560, 470, 330, S(7), S(8))
add(rich('2018年', 56), 290, 790, S(7), S(8)); add(rich('1番人気→{10着}', 54), 290, 870, S(7), S(8))
add(rich('{出遅れ}', 92), 290, 990, at(7, 0.3), S(8))
add(img_card(5, 470, 330), 790, 560, at(7, 0.45), S(8))
add(rich('2024年', 56), 790, 790, at(7, 0.45), S(8)); add(rich('1番人気→{13着}', 54), 790, 870, at(7, 0.45), S(8))
add(rich('{7か月ぶり}', 92), 790, 990, at(7, 0.55), S(8))
add(box('「1番人気は信用できる」', 64), W // 2, 420, S(8), S(9))
add(stamp(True), W // 2, 760, S(8) + 0.35, S(9))
# 09 chapter 2 full
add_full(V(4), S(9), S(10))
add(label(CH[2], 64), W // 2, 600, S(9), S(10), z=5)
add(fit(rich('「前哨戦の王道', 80, WHITE, stroke=(20, 20, 20)), 1000), W // 2, 770, S(9) + 0.3, S(10))
add(fit(rich('{毎日王冠組}が強い」', 96, WHITE, stroke=(20, 20, 20), hl=YEL), 1020), W // 2, 900, at(9, 0.4), S(10))
add(rich('本番3〜4週前 / 東京1800m GⅡ', 44, WHITE, stroke=(20, 20, 20)), W // 2, 1040, at(9, 0.5), S(10))
# 10-14
add_bg(0, S(10), S(15)); chapter(2, S(10), S(15))
add(rich('前走 毎日王冠 → 10年で{32頭}', 70), W // 2, 340, S(10), S(11))
add(rich('0-0-4-28', 150), W // 2, 520, S(10) + 0.3, S(11))
add(rich('1着-2着-3着-着外', 40), W // 2, 640, S(10) + 0.3, S(11))
add(rich('1着 {0回}', 120), W // 2, 790, at(10, 0.6), S(11))
add(rich('2着 {0回}', 120), W // 2, 950, at(10, 0.75), S(11))
add(rich('前走からの間隔', 80), W // 2, 330, S(11), S(12))
add(icon(18, 220), W // 2, 520, S(11) + 0.2, S(12))
add(rich('5週以内', 70), 290, 740, at(11, 0.3), S(12)); add(rich('1勝', 150, DARK), 290, 900, at(11, 0.35), S(12)); add(rich('58頭中', 52), 290, 1040, at(11, 0.35), S(12))
add(rich('9週以上', 70), 790, 740, at(11, 0.62), S(12)); add(rich('{9勝}', 170), 790, 900, at(11, 0.68), S(12)); add(rich('78頭中', 52), 790, 1040, at(11, 0.68), S(12))
for i, (k, yr, nm) in enumerate([(17, '2021年', 'エフフォーリア'), ('V5', '2022年', 'イクイノックス'), (3, '2025年', 'マスカレードボール')]):
    x = 190 + 350 * i; t0 = at(12, 0.12 * (i + 1))
    if k == 'V5': add_vcard(V(5), x, 470, 310, 240, t0, S(13))
    else: add(img_card(k, 310, 240), x, 470, t0, S(13))
    add(rich(yr, 48), x, 650, t0, S(13)); add(fit(rich(nm, 40), 330), x, 715, t0, S(13))
add(rich('日本ダービー2着', 70), W // 2, 840, at(12, 0.55), S(13))
add(rich('↓ {5か月}休み ↓', 80), W // 2, 960, at(12, 0.7), S(13))
add(rich('{優勝}', 110), W // 2, 1100, at(12, 0.85), S(13))
add(rich('2026年 毎日王冠組', 80), W // 2, 330, S(13), S(14))
add(rich('{6}頭', 180), W // 2, 510, S(13) + 0.3, S(14))
add(box('全頭 {中3週}', 76, border=RED), W // 2, 700, at(13, 0.55), S(14))
for i, nm in enumerate(['エルトンバローズ', 'レディネス', 'シャンパンカラー', 'セイウンハーデス', 'ホウオウビスケッツ', 'リアライズシリウス']):
    add(rich(nm, 44), 290 + 500 * (i % 2), 880 + 80 * (i // 2), S(13) + 0.6 + 0.08 * i, S(14))
add(box('「毎日王冠組が強い」', 64), W // 2, 420, S(14), S(15))
add(stamp(False), W // 2, 760, S(14) + 0.35, S(15))
# 15 chapter 3 full
add_full(V(6), S(15), S(16))
add(label(CH[3], 64), W // 2, 600, S(15), S(16), z=5)
add(fit(rich('「東京2000mは', 84, WHITE, stroke=(20, 20, 20)), 1000), W // 2, 770, S(15) + 0.3, S(16))
add(fit(rich('{内枠}が有利」', 104, WHITE, stroke=(20, 20, 20), hl=YEL), 1000), W // 2, 900, at(15, 0.3), S(16))
add(rich('スタート直後にカーブ', 56, WHITE, stroke=(20, 20, 20)), W // 2, 1050, at(15, 0.6), S(16))
# 16-18
add_bg(0, S(16), S(19)); chapter(3, S(16), S(19))
add(icon(19, 760), W // 2, 430, S(16), S(17))
add(box('2枠 16頭で {0勝}', 76, border=RED), W // 2, 720, S(16) + 0.3, S(17))
add(rich('1枠の勝利は', 70), W // 2, 900, at(16, 0.45), S(17))
add(rich('2019年 {アーモンドアイ}だけ', 70), W // 2, 1010, at(16, 0.6), S(17))
add_vcard(V(7), W // 2, 560, 760, 470, S(17), S(18))
add(rich('2026年', 64), W // 2, 870, S(17), S(18))
add(rich('クロワデュノール', 96), W // 2, 980, at(17, 0.3), S(18))
add(waku_badge(1, 1, 64), W // 2, 1110, at(17, 0.7), S(18))
add(box('「内枠が有利」', 64), W // 2, 420, S(18), S(19))
add(stamp(False), W // 2, 760, S(18) + 0.3, S(19))
# 19 summary table
add_bg(1, S(19), S(20))
for i, (t, ok) in enumerate([('1番人気', True), ('毎日王冠', False), ('内枠', False)]):
    y = 400 + 190 * i; t0 = S(19) + 0.15 * i
    add(box(t, 64), 430, y, t0, S(20)); add(mark(ok, 130), 760, y, t0 + 0.1, S(20))
# 20 full
add_full(V(8), S(20), S(21), dim=0.3)
add(rich('じゃあ', 90, WHITE, stroke=(20, 20, 20)), W // 2, 700, S(20), S(21))
add(fit(rich('何を見ればいい？', 110, WHITE, stroke=(20, 20, 20)), 1020), W // 2, 860, S(20) + 0.3, S(21))
# 21-23
add_bg(1, S(21), S(24))
tro = icon(7, 150)
for i in range(10): add(tro, 160 + 190 * (i % 5), 330 + 170 * (i // 5), S(21) + 0.07 * i, at(21, 0.4))
add(rich('{全頭}', 190), W // 2, 720, S(21) + 0.5, at(21, 0.4))
add(rich('過去10年の勝ち馬 全頭', 64), W // 2, 330, at(21, 0.4), S(22))
add(box('東京のGⅠを勝っている', 72, border=RED), W // 2, 540, at(21, 0.4), S(22))
add(rich('or', 70), W // 2, 690, at(21, 0.6), S(22))
add(box('日本ダービー2着', 72, border=RED), W // 2, 830, at(21, 0.75), S(22))
add(rich('この条件がない馬', 80), W // 2, 380, S(22), S(23))
add(rich('のべ{110}頭', 110), W // 2, 560, S(22) + 0.3, S(23))
add(box('{0勝}', 150, border=RED), W // 2, 800, at(22, 0.6), S(23))
add(rich('2026年 17頭中', 80), W // 2, 300, S(23), S(24))
add(rich('{4}頭', 180), W // 2, 470, S(23) + 0.3, S(24))
for i, (w, u, nm) in enumerate([(1, 1, 'クロワデュノール'), (3, 5, 'シャンパンカラー'), (4, 7, 'マスカレードボール'), (8, 17, 'ダノンデサイル')]):
    t0 = at(23, 0.32 + 0.17 * i); y = 680 + 140 * i
    add(waku_badge(w, u, 44), 250, y, t0, S(24)); add(box(nm, 60), 650, y, t0, S(24))
# 24 ending
add_bg(0, S(24), END)
add_vcard(V(9), W // 2, 520, 860, 500, S(24), END)
add(rich('あんたの本命は？', 100), W // 2, 900, S(24), END)
add(fit(rich('{コメント}で教えて！', 110), 1020), W // 2, 1060, at(24, 0.45), END)
add(box('保存して明日チェック', 56, border=GREEN), W // 2, 1650, at(24, 0.6), END)

# ---------- render ----------
EL.sort(key=lambda e: e['z'])
def scaled(e, s):
    k = round(s, 3)
    if k not in e['cache']:
        sp = e['spr']; e['cache'][k] = sp if k == 1.0 else sp.resize((max(1, int(sp.width * k)), max(1, int(sp.height * k))), Image.BILINEAR)
    return e['cache'][k]
os.makedirs(os.path.expanduser('~/aki/ed'), exist_ok=True)
out = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', os.path.expanduser('~/aki/ed/video_noaudio.mp4')], stdin=subprocess.PIPE)
N = int(END * FPS)
only = sys.argv[1:]  # optional: list of seconds to render as stills
frames = [int(float(x) * FPS) for x in only] if only else range(N)
for f in frames:
    t = f / FPS; fr = Image.new('RGB', (W, H), (190, 225, 245))
    for e in EL:
        if not (e['t0'] <= t < e['t1']): continue
        if e['kind'] == 'bg': fr.paste(e['img']); continue
        if e['kind'] == 'full':
            if e['v'] is None: e['v'] = Vid(e['path'], W, H, e['t1'] - e['t0'])
            v = e['v'].next() if not only else Image.open(f'{A}/img/10.png').convert('RGB').resize((W, H))
            if v: fr.paste(Image.blend(v, Image.new('RGB', (W, H), (0, 0, 0)), e['dim']))
            continue
        if e['kind'] == 'vcard':
            if e['v'] is None: e['v'] = Vid(e['path'], e['w'], e['h'], e['t1'] - e['t0'])
            v = e['v'].next() if not only else Image.new('RGB', (e['w'], e['h']), (90, 120, 90))
            if v is None: continue
            sp = card_frame(v); s = pop_scale(t - e['t0'])
            if s != 1.0: sp = sp.resize((max(1, int(sp.width * s)), max(1, int(sp.height * s))), Image.BILINEAR)
        else:
            sp = scaled(e, pop_scale(t - e['t0']) if e['pop'] else 1.0)
        if sp.width < 2: continue
        fr.paste(sp, (int(e['cx'] - sp.width / 2), int(e['cy'] - sp.height / 2)), sp)
    if only: fr.save(os.path.expanduser(f'~/aki/ed/still_{f / FPS:06.2f}.jpg'), quality=85)
    else: out.stdin.write(fr.tobytes())
out.stdin.close(); out.wait(); print('frames', N, 'end', END)
