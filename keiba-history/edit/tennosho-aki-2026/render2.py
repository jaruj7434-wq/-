# 天皇賞・秋 データ検証ショート 編集 v3 (オリジナルデザイン)
# 背景はずっと馬の動画 (ときどき静止画をゆっくりズーム)。黒の半透明パネル + 金のアクセント、
# 左からスライドする文字、カウントアップする数字、棒グラフ・年表・スコアボードでデータを見せる。
# 入力 (Higgs sandbox ~/aki): img/*.png, vids/V*.mp4, vo2/timingB.txt
# 出力: ~/aki/ed/video_noaudio.mp4  (音声は run2.sh で合成)
import os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
A = os.path.expanduser('~/aki')
F_HEAD = os.path.expanduser('~/.fonts/DelaGothicOne-Regular.ttf')
F_BODY = os.path.expanduser('~/.fonts/NotoSansJP-VF.ttf')
WHITE, GOLD, RED, INK = (255, 255, 255), (255, 200, 61), (232, 58, 58), (12, 16, 26)
PANEL = (12, 16, 26, 190)
WAKU = {1: ((245, 245, 245), INK), 2: ((25, 25, 25), WHITE), 3: ((214, 40, 40), WHITE), 4: ((40, 90, 200), WHITE),
        5: ((245, 205, 0), INK), 6: ((30, 140, 70), WHITE), 7: ((240, 135, 30), WHITE), 8: ((235, 120, 165), WHITE)}

# ---------- timing ----------
T = {}
for l in open(f'{A}/vo2/timingB.txt'):
    n, _, s, _, d = l.split(); T[int(n)] = (float(s), float(s) + float(d))
NL = max(T); END = T[NL][1] + 1.2
def S(n): return T[n][0]
def E(n): return S(n + 1) if n < NL else END
def at(n, frac): return S(n) + (T[n][1] - S(n)) * frac

# ---------- fonts / primitives ----------
_fc = {}
def font(kind, sz):
    k = (kind, sz)
    if k not in _fc:
        if kind == 'head': _fc[k] = ImageFont.truetype(F_HEAD, sz)
        else:
            f = ImageFont.truetype(F_BODY, sz); f.set_variation_by_name('Black' if kind == 'black' else 'Bold'); _fc[k] = f
    return _fc[k]

def text(t, sz, color=WHITE, kind='head', hl=GOLD, stroke=0, sc=INK, shadow=True, outer=0, oc=INK):
    """'{...}' segments are drawn in hl color; outer adds a second (outside) outline in oc"""
    f = font(kind, sz); segs = [(p, hl if i % 2 else color) for i, p in enumerate(re.split(r'[{}]', t)) if p]
    ws = [f.getbbox(p, stroke_width=stroke + outer)[2] for p, _ in segs]
    im = Image.new('RGBA', (sum(ws) + 40, int(sz * 1.5) + 40), (0, 0, 0, 0))
    if outer:
        d = ImageDraw.Draw(im); x = 20
        for (p, _), w_ in zip(segs, ws): d.text((x, 20), p, font=f, fill=oc, stroke_width=stroke + outer, stroke_fill=oc); x += w_
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(sh); x = 20
        for (p, _), w_ in zip(segs, ws): d.text((x + 3, 24), p, font=f, fill=(0, 0, 0, 170), stroke_width=stroke, stroke_fill=(0, 0, 0, 170)); x += w_
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(im); x = 20
    for (p, c), w_ in zip(segs, ws): d.text((x, 20), p, font=f, fill=c, stroke_width=stroke, stroke_fill=sc); x += w_
    return im.crop(im.getbbox())

def fit(im, maxw): return im if im.width <= maxw else im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)

def panel(sprites, pad=36, gap=14, accent=GOLD, minw=0, align='left'):
    """dark glass panel with a gold bar on the left; sprites stacked vertically"""
    w = max([s.width for s in sprites] + [minw - 2 * pad - 12]) + 2 * pad + 12; h = sum(s.height for s in sprites) + gap * (len(sprites) - 1) + 2 * pad
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 22, fill=PANEL)
    d.rounded_rectangle((0, 0, 12, h - 1), 6, fill=accent)
    y = pad
    for s in sprites:
        x = pad + 12 if align == 'left' else (w + 12 - s.width) // 2
        im.alpha_composite(s, (x, y)); y += s.height + gap
    return im

def chip(t, sz=44, bg=GOLD, fg=INK, kind='black'):
    s = text(t, sz, fg, kind=kind, shadow=False); im = Image.new('RGBA', (s.width + 48, s.height + 26), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, im.width - 1, im.height - 1), im.height // 2, fill=bg); im.alpha_composite(s, (24, 13)); return im

def waku_badge(w, u, sz=44):
    bg, fg = WAKU[w]; s = text(f'{w}枠{u}番', sz, fg, kind='black', shadow=False)
    im = Image.new('RGBA', (s.width + 36, s.height + 22), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle((0, 0, im.width - 1, im.height - 1), fill=bg, outline=(90, 90, 90), width=3); im.alpha_composite(s, (18, 11)); return im

def photo(i, w, h, deg=-3):
    img = Image.open(f'{A}/img/{i}.png').convert('RGB'); s = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * s) + 1, int(img.height * s) + 1), Image.LANCZOS); x, y = (img.width - w) // 2, (img.height - h) // 2
    img = img.crop((x, y, x + w, y + h)); im = Image.new('RGBA', (w + 20, h + 20), WHITE + (255,)); im.paste(img, (10, 10))
    return im.rotate(deg, expand=True, resample=Image.BICUBIC)

# ---------- backgrounds ----------
def grad():
    g = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(g)
    for y in range(H):
        a = 150 - int(110 * min(1, y / 700)) if y < 700 else (40 if y < 1150 else 40 + int(160 * min(1, (y - 1150) / 600)))
        d.line((0, y, W, y), fill=(5, 8, 15, a))
    return g
GRAD = grad()

class Vid:
    def __init__(self, path, dur, mode):
        src = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]))
        slow = max(1.0, (dur + 0.3) / (src - 0.1))
        pre = f'setpts={slow:.4f}*PTS,fps={FPS}'
        if mode == 'cover':
            fc = f'[0:v]{pre},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}[o]'
        else:  # blurfill: blurred cover behind, sharp full-width video in the middle
            fc = (f'[0:v]{pre},split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:2,eq=brightness=-0.08[bg];'
                  f'[b]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2+40[o]')
        self.p = subprocess.Popen(['ffmpeg', '-v', 'quiet', '-i', path, '-filter_complex', fc, '-map', '[o]', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
        self.last = None
    def next(self):
        b = self.p.stdout.read(W * H * 3)
        if len(b) == W * H * 3: self.last = Image.frombytes('RGB', (W, H), b)
        return self.last

BG = []  # (t0, t1, kind, src)
def bg(kind, src, t0, t1): BG.append(dict(kind=kind, src=src, t0=t0, t1=t1, v=None, img=None))
def kb_frame(e, t):
    if e['img'] is None:
        im = Image.open(f'{A}/img/{e["src"]}.png').convert('RGB'); s = max(W * 1.15 / im.width, H * 1.15 / im.height)
        e['img'] = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    p = (t - e['t0']) / max(0.1, e['t1'] - e['t0']); z = 1.0 + 0.12 * p; im = e['img']
    cw, ch = int(im.width / 1.15 / z * 1.0), int(im.height / 1.15 / z)
    cw, ch = min(cw, im.width), min(ch, im.height); x = (im.width - cw) // 2; y = int((im.height - ch) * (0.5 - 0.15 * p))
    return im.crop((x, y, x + cw, y + ch)).resize((W, H), Image.BILINEAR)

# ---------- overlay elements ----------
EL = []
def ease(p): return 1 - (1 - p) ** 3
def add(spr, x, y, t0, t1, anim='slide', anchor='c', z=1):
    """x,y: center (anchor c) or left-center (anchor l)"""
    EL.append(dict(kind='spr', spr=spr, x=x, y=y, t0=t0, t1=t1, anim=anim, anchor=anchor, z=z))
def add_fn(fn, t0, t1, z=1): EL.append(dict(kind='fn', fn=fn, t0=t0, t1=t1, z=z))

def place(fr, spr, x, y, anchor, alpha=1.0, dx=0, scale=1.0):
    if scale != 1.0: spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if alpha < 1.0:
        a = spr.getchannel('A').point(lambda v: int(v * alpha)); spr = spr.copy(); spr.putalpha(a)
    px = int(x - spr.width / 2) if anchor == 'c' else int(x)
    fr.alpha_composite(spr, (px + int(dx), int(y - spr.height / 2)))

def draw_el(fr, e, t):
    dt = t - e['t0']
    if e['kind'] == 'fn':  # shapes are drawn on their own layer so translucent fills blend over the video
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); e['fn'](lay, t, dt); fr.alpha_composite(lay); return
    p = ease(min(1, dt / 0.28))
    if e['anim'] == 'slide': place(fr, e['spr'], e['x'], e['y'], e['anchor'], alpha=p, dx=-90 * (1 - p))
    elif e['anim'] == 'zoom': place(fr, e['spr'], e['x'], e['y'], e['anchor'], alpha=p, scale=1.35 - 0.35 * p)
    elif e['anim'] == 'right': place(fr, e['spr'], e['x'], e['y'], e['anchor'], alpha=p, dx=140 * (1 - p))
    else: place(fr, e['spr'], e['x'], e['y'], e['anchor'])

_cc = {}
def counter(fmt, target, sz, x, y, t0, t1, color=GOLD, dur=0.6, anchor='c'):
    def fn(fr, t, dt):
        n = round(target * ease(min(1, dt / dur))); k = (fmt, n, sz, color)
        if k not in _cc: _cc[k] = text(fmt.format(n), sz, color)
        place(fr, _cc[k], x, y, anchor, alpha=min(1, dt / 0.15))
    add_fn(fn, t0, t1)

# ---------- HUD (top tag + chapter dots + progress bar) ----------
HUD_TAG = chip('天皇賞・秋 データ検証', 34, bg=(12, 16, 26, 200), fg=WHITE)
def hud(fr, t, dt):
    fr.alpha_composite(HUD_TAG, (40, 70))
    ch = 0 if t < S(4) else 1 if t < S(9) else 2 if t < S(15) else 3 if t < S(19) else 4
    d = ImageDraw.Draw(fr)
    for i in range(3):
        x = W - 190 + i * 56; on = ch == i + 1; done = ch > i + 1
        d.rounded_rectangle((x, 88, x + 42, 100), 6, fill=GOLD if on else (GOLD[0], GOLD[1], GOLD[2], 150) if done else (255, 255, 255, 90))
    d.rectangle((0, H - 10, int(W * t / END), H), fill=GOLD)
add_fn(hud, 0, END, z=8)

# ---------- subtitles (black band) ----------
SUB = {
1: '明日は、{天皇賞・秋}。', 2: '予想でよく言われる/「常識」が{3つ}あります', 3: '本当なのか/{過去10年}のデータで調べました',
4: '1つ目/「1番人気は信用できる」', 5: '実は昔は{真逆}/{1988年}から1番人気が/{12年連続}で負けていました',
6: 'でもこの10年は/1番人気が{7勝}/{4番人気以下}は/1頭も勝っていません',
7: '負けた2回は/スタートの{出遅れ}と/{7か月ぶり}の休み明け/ちゃんと理由がありました', 8: '結論/1番人気は{信用していい}',
9: '2つ目/「前哨戦の王道/毎日王冠組が強い」', 10: 'ところが10年で{32頭}が出て/勝ち馬も2着馬も{ゼロ}',
11: 'カギはレースの{間隔}/{5週以内}は1勝だけ/{9週以上}あけた馬は{9勝}',
12: 'エフフォーリア/イクイノックス/マスカレードボール/3頭ともダービー2着から/{5か月}休んで勝っています',
13: '今年の毎日王冠組は{6頭}/全頭{中3週}です', 14: '結論/毎日王冠組は{過信禁物}',
15: '3つ目/「東京2000mは内枠が有利」/スタート直後に/カーブがあるからです',
16: 'でも2枠は16頭で{勝ち馬ゼロ}/1枠で勝ったのも/2019年の{アーモンドアイ}だけです',
17: 'そして今年は/主役のクロワデュノールが/{1枠1番}', 18: '結論/{内枠有利}はウソ', 19: '本当だったのは/{1番人気}だけ',
20: 'じゃあ/何を見ればいいのか', 21: 'この10年の勝ち馬は{全頭}が/{東京のGⅠ}を勝ったことがあるか/{ダービー2着}の馬でした',
22: 'この条件がない馬は/のべ{110頭}で/1頭も勝っていません',
23: '今年当てはまるのは/{17頭中4頭}/クロワデュノール/シャンパンカラー/マスカレードボール/ダノンデサイル',
24: 'あんたの本命は誰だ？/{コメント}で教えてくれ',
}
def subband(t):
    s = text(t, 60, WHITE, kind='black', hl=GOLD, shadow=False); s = fit(s, 960)
    im = Image.new('RGBA', (s.width + 60, s.height + 34), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, im.width - 1, im.height - 1), 14, fill=(0, 0, 0, 175)); im.alpha_composite(s, (30, 17)); return im
SUBY = 1590
for n, txt in SUB.items():
    parts = txt.split('/'); lens = [len(re.sub(r'[{}]', '', p)) for p in parts]; a, b = T[n]; t = a
    for i, (p, L) in enumerate(zip(parts, lens)):
        d_ = (b - a) * L / sum(lens); t1 = t + d_ if i < len(parts) - 1 else E(n) - 0.02
        add(subband(p), W // 2, SUBY, t, t1, anim='none', z=7); t += d_

# ---------- helpers for scenes ----------
L = 80  # left margin
def check_card(no, q, sub, n):
    """chapter opener: full-width dark band sliding in"""
    a, b = S(n), E(n)
    def fn(fr, t, dt):
        p = ease(min(1, dt / 0.35)); d = ImageDraw.Draw(fr)
        x1 = int(W * p); d.rectangle((0, 690, x1, 1130), fill=(8, 10, 18, 205)); d.rectangle((0, 690, x1, 698), fill=GOLD); d.rectangle((0, 1122, x1, 1130), fill=GOLD)
    add_fn(fn, a, b, z=2)
    add(text(f'CHECK {no}', 64, GOLD), L, 780, a + 0.2, b, anchor='l', z=3)
    add(fit(text(q, 92), 940), L, 910, a + 0.35, b, anchor='l', z=3)
    if sub: add(text(sub, 40, (220, 220, 220), kind='bold'), L, 1040, at(n, 0.5), b, anchor='l', z=3)

def verdict(ok, msg, n):
    a, b = S(n), E(n); c = GOLD if ok else RED; word = '本当' if ok else '思い込み'
    add(text('判定', 56, WHITE), L, 640, a, b, anchor='l')
    def fn(fr, t, dt):
        p = ease(min(1, max(0, dt - 0.2) / 0.3)); d = ImageDraw.Draw(fr)
        d.polygon([(0, 720), (int((W + 120) * p), 720), (int((W + 120) * p) - 120, 960), (0, 960)], fill=c + (235,))
    add_fn(fn, a, b, z=2)
    add(text(word, 150, INK if ok else WHITE, shadow=False), W // 2, 840, a + 0.4, b, anim='zoom', z=3)
    add(fit(text(msg, 56, WHITE, kind='black'), 960), W // 2, 1060, a + 0.7, b)

def bars(rows, x0, y0, maxw, t0, t1, rowh=150, grow=0.6, stagger=0.25, maxv=None):
    """rows: (label, value, valuetext, color)"""
    maxv = maxv or max(r[1] for r in rows) or 1
    labs = [text(r[0], 46, WHITE, kind='black') for r in rows]; vals = [text(r[2], 58, r[3]) for r in rows]
    def fn(fr, t, dt):
        d = ImageDraw.Draw(fr)
        for i, (lab, v, vt, c) in enumerate(rows):
            ti = dt - stagger * i
            if ti < 0: continue
            y = y0 + rowh * i; p = ease(min(1, ti / grow))
            place(fr, labs[i], x0, y, 'l', alpha=min(1, ti / 0.2))
            bw = int(max(10, maxw * v / maxv) * p); d.rounded_rectangle((x0, y + 40, x0 + bw, y + 84), 10, fill=c + (255,))
            if p > 0.6: place(fr, vals[i], x0 + bw + 24, y + 62, 'l', alpha=min(1, (p - 0.6) / 0.4))
    add_fn(fn, t0, t1)

# ================= scenes =================
# --- background plan (always moving) ---
bg('cover', 'V4', 0, S(2)); bg('cover', 'V2', S(2), S(3)); bg('kb', 10, S(3), S(4))
bg('cover', 'V8', S(4), S(5)); bg('cover', 'V6', S(5), S(6)); bg('blur', 'V1', S(6), S(7))
bg('blur', 'V3', S(7), S(8)); bg('blur', 'V9', S(8), S(9)); bg('cover', 'V4', S(9), S(10))
bg('kb', 12, S(10), S(11)); bg('cover', 'V2', S(11), S(12)); bg('blur', 'V5', S(12), S(13))
bg('kb', 10, S(13), S(14)); bg('blur', 'V1', S(14), S(15)); bg('cover', 'V6', S(15), S(16))
bg('kb', 14, S(16), S(17)); bg('blur', 'V7', S(17), S(18)); bg('cover', 'V4', S(18), S(19))
bg('cover', 'V2', S(19), S(20)); bg('cover', 'V8', S(20), S(21)); bg('kb', 16, S(21), S(22))
bg('blur', 'V5', S(22), S(23)); bg('kb', 12, S(23), S(24)); bg('blur', 'V9', S(24), END)

# 01 title
add(text('明日は', 96, stroke=9, sc=INK), L, 430, 0.0, S(2), anchor='l')
add(fit(text('天皇賞・秋', 190, stroke=14, sc=INK), 960), L, 620, 0.15, S(2), anchor='l', anim='zoom')
add(fit(text('知らなきゃ損', 176, (255, 0, 0), stroke=10, sc=WHITE, outer=10, oc=(110, 0, 0)), 980), L, 860, 0.45, S(2), anchor='l')
add(text('データで検証する3つの“常識”', 48, WHITE, kind='black'), L, 1010, 0.8, S(2), anchor='l')
# 02 three hidden checks
add(text('予想でよく聞く“常識”', 72), L, 430, S(2), S(3), anchor='l')
for i in range(3):
    add(panel([text(f'CHECK {i + 1}', 40, GOLD), text('？？？？？？', 56, WHITE, kind='black')], minw=920), L, 620 + 190 * i, S(2) + 0.3 + 0.25 * i, S(3), anchor='l')
# 03 data scope
add(text('2016→2025', 80, WHITE), L, 470, S(3), S(4), anchor='l')
counter('{}年分', 10, 200, L, 670, S(3) + 0.2, S(4), anchor='l')
add(chip('出走したのべ144頭をすべて集計', 44), L, 880, at(3, 0.5), S(4), anchor='l')
# 04 CHECK 1
check_card(1, '1番人気は信用できる？', '', 4)
# 05 12-year losing streak timeline
add(text('{1番人気}が勝てなかった時代', 64), L, 420, S(5), S(6), anchor='l')
def streak(fr, t, dt):
    d = ImageDraw.Draw(fr)
    for i in range(12):
        ti = dt - 0.35 - 0.16 * i
        if ti < 0: break
        x = 80 + (i % 6) * 156; y = 560 + (i // 6) * 190; p = ease(min(1, ti / 0.2))
        d.rounded_rectangle((x, y, x + 132, y + 160), 14, fill=(12, 16, 26, int(200 * p)))
        place(fr, _yr[i], x + 66, y + 42, 'c', alpha=p)
        r = int(28 * (1.4 - 0.4 * p)); cx, cy = x + 66, y + 110
        d.line((cx - r, cy - r, cx + r, cy + r), fill=RED + (int(255 * p),), width=12); d.line((cx + r, cy - r, cx - r, cy + r), fill=RED + (int(255 * p),), width=12)
_yr = [text(f'{y}', 40, WHITE, kind='black', shadow=False) for y in range(1988, 2000)]
add_fn(streak, S(5), S(6))
add(text('{12}年連続', 120, WHITE), L, 1000, at(5, 0.8), S(6), anchor='l', anim='zoom')
add(text('→ 2000年 テイエムオペラオーで連敗ストップ', 36, (220, 220, 220), kind='bold'), L, 1120, at(5, 0.92), S(6), anchor='l')
# 06 last 10 years
add(text('過去10年の{1番人気}', 64), L, 400, S(6), S(7), anchor='l')
counter('{}勝', 7, 210, L, 580, S(6) + 0.2, S(7), anchor='l')
add(text('/ 10回   勝率70%', 56, WHITE, kind='black'), 560, 610, S(6) + 0.5, S(7), anchor='l')
add(panel([text('4番人気以下', 50, WHITE, kind='black'), text('のべ114頭で  {0勝}', 84, WHITE, hl=RED)], minw=920), L, 900, at(6, 0.5), S(7), anchor='l')
# 07 two losses
add(panel([text('2018年  1番人気 → {10着}', 46, WHITE, kind='black'), text('スワーヴリチャード', 40, (210, 210, 210), kind='bold'), chip('スタートで出遅れ', 46, bg=RED, fg=WHITE)]), L, 360, S(7), S(8), anchor='l')
add(photo(5, 400, 300, deg=4), 790, 1170, at(7, 0.45), S(8), anim='right', z=2)
add(panel([text('2024年  1番人気 → {13着}', 46, WHITE, kind='black'), text('リバティアイランド', 40, (210, 210, 210), kind='bold'), chip('7か月ぶりのレース', 46, bg=RED, fg=WHITE)]), L, 1170, at(7, 0.45), S(8), anchor='l', z=3)
# 08 verdict
verdict(True, '1番人気は素直に信じていい', 8)
# 09 CHECK 2
check_card(2, '毎日王冠組は強い？', '本番の3〜4週前 / 東京芝1800m / GⅡ', 9)
# 10 scoreboard 0-0-4-28
add(text('前走が{毎日王冠}の馬', 64), L, 400, S(10), S(11), anchor='l')
counter('のべ{}頭', 32, 120, L, 560, S(10) + 0.2, S(11), color=WHITE, anchor='l')
def board(fr, t, dt):
    d = ImageDraw.Draw(fr); cells = [('1着', '0', RED), ('2着', '0', RED), ('3着', '4', WHITE), ('着外', '28', WHITE)]
    for i, (k, v, c) in enumerate(cells):
        ti = dt - at(10, 0.45) + S(10) - 0.15 * i
        if ti < 0: continue
        p = ease(min(1, ti / 0.25)); x = 80 + 235 * i
        d.rounded_rectangle((x, 760, x + 210, 1010), 18, fill=(12, 16, 26, int(210 * p)), outline=c + (int(255 * p),), width=5)
        place(fr, _bk[k], x + 105, 810, 'c', alpha=p); place(fr, _bv[(v, c)], x + 105, 920, 'c', alpha=p, scale=1.3 - 0.3 * p)
_bk = {k: text(k, 44, WHITE, kind='black', shadow=False) for k in ('1着', '2着', '3着', '着外')}
_bv = {(v, c): text(v, 110, c, shadow=False) for v, c in (('0', RED), ('4', WHITE), ('28', WHITE))}
add_fn(board, S(10), S(11))
# 11 interval bar chart
add(text('前走からの{間隔}と勝利数', 64), L, 400, S(11), S(12), anchor='l')
bars([('5週以内（58頭）', 1, '1勝', WHITE), ('6〜8週（8頭）', 0, '0勝', WHITE), ('9週以上（78頭）', 9, '9勝', GOLD)], L, 560, 700, at(11, 0.25), S(12), rowh=170, stagger=0.45)
# 12 derby 2nd -> 5 months -> win
add(text('ダービー2着 → {5か月}休み → 優勝', 56), L, 380, S(12), S(13), anchor='l')
for i, (yr, nm, ph) in enumerate([('2021', 'エフフォーリア', 17), ('2022', 'イクイノックス', 13), ('2025', 'マスカレードボール', 3)]):
    t0 = at(12, 0.1 + 0.18 * i); y = 560 + 120 * i
    add(panel([text(f'{yr}年  {nm}', 50, WHITE, kind='black')], pad=24, minw=760), L, y, t0, S(13), anchor='l')
add(photo(13, 380, 280, deg=-4), 800, 1110, at(12, 0.65), S(13), anim='right')
# 13 this year's mainichi group
add(text('2026年  前走が毎日王冠', 60), L, 400, S(13), S(14), anchor='l')
counter('{}頭', 6, 190, L, 570, S(13) + 0.2, S(14), anchor='l')
add(chip('全頭 中3週', 56, bg=RED, fg=WHITE), 520, 600, at(13, 0.55), S(14), anchor='l')
names = ['エルトンバローズ', 'レディネス', 'シャンパンカラー', 'セイウンハーデス', 'ホウオウビスケッツ', 'リアライズシリウス']
add(panel([text('　'.join(names[0:2]), 44, WHITE, kind='black'), text('　'.join(names[2:4]), 44, WHITE, kind='black'), text('　'.join(names[4:6]), 44, WHITE, kind='black')], minw=920), L, 890, S(13) + 0.6, S(14), anchor='l')
# 14 verdict
verdict(False, '毎日王冠組は過信禁物', 14)
# 15 CHECK 3
check_card(3, '東京2000mは内枠が有利？', 'スタートしてすぐ最初のコーナー', 15)
# 16 wins by gate
add(text('枠番別の勝利数（過去10年）', 60), L, 380, S(16), S(17), anchor='l')
WINS = {1: 1, 2: 0, 3: 1, 4: 4, 5: 2, 6: 1, 7: 1, 8: 0}
def gatechart(fr, t, dt):
    d = ImageDraw.Draw(fr); base = 1030
    for w in range(1, 9):
        ti = dt - 0.2 - 0.08 * w
        if ti < 0: continue
        p = ease(min(1, ti / 0.4)); x = 70 + 120 * (w - 1); bh = int((40 + 110 * WINS[w]) * p)
        bgc, fgc = WAKU[w]; hot = w in (1, 2)
        d.rectangle((x, base - bh, x + 96, base), fill=bgc + (255,), outline=(RED if hot and dt > at(16, 0.2) - S(16) else (90, 90, 90)) + (255,), width=6 if hot else 2)
        place(fr, _wl[w], x + 48, base + 46, 'c'); place(fr, _wv[w], x + 48, base - bh - 40, 'c', alpha=p)
_wl = {w: text(f'{w}枠', 36, WHITE, kind='black', shadow=False) for w in WINS}
_wv = {w: text(f'{WINS[w]}', 56, GOLD if WINS[w] else RED, shadow=False) for w in WINS}
add_fn(gatechart, S(16), S(17))
add(panel([text('2枠：のべ16頭で{0勝}', 48, WHITE, kind='black', hl=RED), text('1枠：2019年 アーモンドアイの1勝だけ', 40, WHITE, kind='black')], minw=920), L, 1270, at(16, 0.35), S(17), anchor='l')
# 17 Croix du Nord gate 1
add(text('2026年の主役', 56, WHITE), L, 380, S(17), S(18), anchor='l')
add(fit(text('クロワデュノール', 120), 960), L, 520, S(17) + 0.2, S(18), anchor='l', anim='zoom')
add(waku_badge(1, 1, 64), L, 1250, at(17, 0.6), S(18), anchor='l', anim='zoom')
# 18 verdict
verdict(False, '内枠有利は、データでは当てはまらない', 18)
# 19 scoreboard summary
add(text('検証結果', 72), L, 420, S(19), S(20), anchor='l')
for i, (q, ok) in enumerate([('1番人気は信用できる', True), ('毎日王冠組は強い', False), ('東京2000mは内枠有利', False)]):
    add(panel([text(q, 48, WHITE, kind='black')], pad=26, minw=600), L, 600 + 160 * i, S(19) + 0.2 + 0.2 * i, S(20), anchor='l')
    add(chip('本当' if ok else '思い込み', 46, bg=GOLD if ok else RED, fg=INK if ok else WHITE), 760, 600 + 160 * i, S(19) + 0.4 + 0.2 * i, S(20), anchor='l', anim='zoom')
# 20 question
add(text('じゃあ', 100), W // 2, 760, S(20), S(21))
add(fit(text('何を見ればいい？', 130, GOLD), 980), W // 2, 920, S(20) + 0.25, S(21), anim='zoom')
# 21 the condition
add(text('過去10年の勝ち馬', 64), L, 400, S(21), S(22), anchor='l')
counter('{}頭', 10, 170, L, 560, S(21) + 0.1, at(21, 0.35), anchor='l')
add(text('全頭に共通する条件がある', 56, WHITE, kind='black'), L, 740, S(21) + 0.4, at(21, 0.35), anchor='l')
add(panel([text('条件', 40, GOLD), text('東京のGⅠを勝っている', 64, WHITE, kind='black'), text('または', 40, (200, 200, 200), kind='bold'), text('日本ダービー2着', 64, WHITE, kind='black')], minw=920), L, 900, at(21, 0.35), S(22), anchor='l')
# 22 contrast
add(panel([text('条件あり  のべ34頭', 48, WHITE, kind='black'), text('{10勝}', 110)], minw=920), L, 520, S(22), S(23), anchor='l')
add(panel([text('条件なし  のべ110頭', 48, WHITE, kind='black'), text('{0勝}', 110, WHITE, hl=RED)], accent=RED, minw=920), L, 900, at(22, 0.35), S(23), anchor='l')
# 23 this year's 4
add(text('2026年  17頭中', 60), L, 380, S(23), S(24), anchor='l')
counter('{}頭', 4, 150, L, 500, S(23) + 0.2, S(24), anchor='l')
for i, (w, u, nm) in enumerate([(1, 1, 'クロワデュノール'), (3, 5, 'シャンパンカラー'), (4, 7, 'マスカレードボール'), (8, 17, 'ダノンデサイル')]):
    t0 = at(23, 0.3 + 0.17 * i); y = 700 + 160 * i
    add(panel([text(nm, 60, WHITE, kind='black')], pad=26, minw=920), L, y, t0, S(24), anchor='l')
    add(waku_badge(w, u, 40), 760, y, t0 + 0.1, S(24), anchor='l')
# 24 ending CTA
add(text('あんたの本命は？', 110), W // 2, 430, S(24), END, anim='zoom')
add(chip('コメントで教えて', 64, bg=GOLD), W // 2, 600, at(24, 0.4), END, anim='zoom')
add(text('保存して、明日のレース前にもう一度', 42, WHITE, kind='black'), W // 2, 1360, at(24, 0.6), END)

# ---------- render ----------
EL.sort(key=lambda e: e['z'])
def bg_frame(t):
    for e in BG:
        if e['t0'] <= t < e['t1']:
            if e['kind'] == 'kb': return kb_frame(e, t)
            if e['v'] is None: e['v'] = Vid(f"{A}/vids/{e['src']}.mp4", e['t1'] - e['t0'], 'cover' if e['kind'] == 'cover' else 'blur')
            return e['v'].next()
    return None
out = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', os.path.expanduser('~/aki/ed/video_noaudio.mp4')], stdin=subprocess.PIPE)
only = [float(x) for x in sys.argv[1:]]
frames = [int(x * FPS) for x in only] if only else range(int(END * FPS))
for f in frames:
    t = f / FPS; b = bg_frame(t)
    fr = (b.convert('RGBA') if b else Image.new('RGBA', (W, H), INK + (255,)))
    fr.alpha_composite(GRAD)
    for e in EL:
        if e['t0'] <= t < e['t1']: draw_el(fr, e, t)
    rgb = fr.convert('RGB')
    if only:
        rgb.save(os.path.expanduser(f'~/aki/ed/st_{t:06.2f}.jpg'), quality=85)
        for e in BG: e['v'] = None
    else: out.stdin.write(rgb.tobytes())
out.stdin.close(); out.wait(); print('frames', len(frames), 'end', END)
