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
for l in open(os.path.expanduser('~/aki/pick/vo/timingB.txt')):
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
    def __init__(self, path, dur, mode, ss=0.0):
        src = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]))
        slow = max(1.0, (dur + 0.3) / (src - 0.1))
        pre = f'setpts={slow:.4f}*PTS,fps={FPS}'
        if mode == 'cover':
            fc = f'[0:v]{pre},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}[o]'
        else:  # blurfill: blurred cover behind, sharp full-width video in the middle
            fc = (f'[0:v]{pre},split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:2,eq=brightness=-0.08[bg];'
                  f'[b]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2+40[o]')
        self.p = subprocess.Popen(['ffmpeg', '-v', 'quiet', '-ss', f'{ss:.2f}', '-i', path, '-filter_complex', fc, '-map', '[o]', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
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

# ---------- 本命予想編 (render3.py の後半) ----------
# render2.py の部品 (text / panel / chip / waku_badge / Vid / counter など) を使い、谷上の解説 + 馬の動画で構成する。
# 本命の馬名は 10 の発表まで出さない。
P = os.path.expanduser('~/aki/pick')

# ---------- HUD ----------
HUD_TAG = chip('天皇賞・秋  谷上の本命', 34, bg=(12, 16, 26, 200), fg=WHITE)
def hud(fr, t, dt):
    fr.alpha_composite(HUD_TAG, (40, 70))
    ImageDraw.Draw(fr).rectangle((0, H - 10, int(W * t / END), H), fill=GOLD)
add_fn(hud, 0, END, z=8)

# ---------- render2.py と同じ字幕帯・棒グラフ ----------
def subband(t):
    s = text(t, 60, WHITE, kind='black', hl=GOLD, shadow=False); s = fit(s, 960)
    im = Image.new('RGBA', (s.width + 60, s.height + 34), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, im.width - 1, im.height - 1), 14, fill=(0, 0, 0, 175)); im.alpha_composite(s, (30, 17)); return im

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

# ---------- subtitles ----------
SUB = {
1: '明日の{天皇賞・秋}/俺の本命は……/{最後に発表}する', 2: 'まずはヒントから/その馬は/これまで{GⅠを4勝}',
3: '国内で{馬券圏外}に負けたのは/凱旋門賞帰りの/{ジャパンカップ}ただ1回だけ', 4: 'それでも{4着}/地力の高さは/改めて証明済みだ',
5: '宝塚記念からは/少し{間隔}が空いた', 6: 'でも調教を見る限り/春に{3戦}した疲れは感じない/しっかり仕上がってる印象だ',
7: '臨戦態勢は/{十分}に整ってる', 8: '人気になるのは間違いない/でも{人気を理由に嫌う}必要はない',
9: 'ここは素直に{実力}を信頼/自信を持って推す/俺の本命は……', 10: '{1枠1番}/{クロワデュノール}',
11: 'あんたの本命は誰だ？/{コメント}で教えてくれ',
}
SUBY = 1590
for n, txt in SUB.items():
    parts = txt.split('/'); lens = [len(re.sub(r'[{}]', '', p)) for p in parts]; a, b = T[n]; t = a
    for i, (p, L_) in enumerate(zip(parts, lens)):
        d_ = (b - a) * L_ / sum(lens); t1 = t + d_ if i < len(parts) - 1 else E(n) - 0.02
        add(subband(p), W // 2, SUBY, t, t1, anim='none', z=7); t += d_

L = 80
def hint(no, n, y=420): add(chip(f'HINT {no}', 44, bg=GOLD), L, y, S(n), E(n), anchor='l')
def bgv(name, a, b, ss=0.0): BG.append(dict(kind='cover', src=name, t0=a, t1=b, v=None, img=None, ss=ss))

# --- background plan: 谷上 (W) と馬 (K) を交互に ---
bgv('W01', 0, S(2), 0.1); bgv('K1', S(2), S(3)); bgv('K2', S(3), S(5)); bgv('W05', S(5), S(6), 0.1)
BG.append(dict(kind='kb', src='p3', t0=S(6), t1=S(7), v=None, img=None)) if not os.path.exists(f'{P}/vids/K3ok') else bgv('K3', S(6), S(7)); bgv('K4', S(7), S(8)); bgv('W08', S(8), S(9), 0.1); bgv('W09', S(9), S(10), 0.1)
bgv('K5', S(10), S(11)); bgv('W11', S(11), END, 0.1)

# 01 hook (谷上)
add(text('明日の', 72, stroke=8), L, 1000, 0.0, S(2), anchor='l')
add(fit(text('天皇賞・秋', 150, stroke=12), 960), L, 1140, 0.1, S(2), anchor='l', anim='zoom')
add(text('谷上の本命は…', 80, GOLD, stroke=8), L, 1310, at(1, 0.35), S(2), anchor='l')
add(chip('最後に発表', 56, bg=RED, fg=WHITE), 600, 1310, at(1, 0.7), S(2), anchor='l', anim='zoom')
# 02 HINT 1: GI 4勝
hint(1, 2)
add(text('その馬は', 64, stroke=6), L, 560, S(2), S(3), anchor='l')
counter('GⅠ {}勝', 4, 170, L, 740, at(2, 0.55), S(3), anchor='l')
for i, r in enumerate(['ホープフルS', '日本ダービー', '大阪杯', '天皇賞（春）']):
    add(chip(r, 40, bg=(12, 16, 26, 210), fg=WHITE), L + 470 * (i % 2), 930 + 90 * (i // 2), at(2, 0.65) + 0.12 * i, S(3), anchor='l')
# 03 HINT 2: 国内成績
hint(2, 3)
add(text('国内での成績', 64, stroke=6), L, 560, S(3), S(4), anchor='l')
bars([('1着', 6, '6回', GOLD), ('2着', 2, '2回', WHITE), ('3着', 0, '0回', WHITE), ('4着以下', 1, '1回', RED)], L, 660, 600, S(3) + 0.3, S(4), rowh=120, stagger=0.2, maxv=6)
add(panel([text('馬券圏外はこの1回だけ', 44, WHITE, kind='black'), text('凱旋門賞帰りの{ジャパンカップ}', 52, WHITE, kind='black', hl=GOLD)], accent=RED, minw=920), L, 1230, at(3, 0.55), S(4), anchor='l')
# 04 それでも4着
add(text('それでも', 80, stroke=8), L, 680, S(4), S(5), anchor='l')
counter('{}着', 4, 260, L, 900, S(4) + 0.15, S(5), anchor='l')
add(chip('地力の高さを証明', 56, bg=GOLD), L, 1120, at(4, 0.5), S(5), anchor='l', anim='zoom')
# 05 間隔 (谷上)
add(panel([text('前走  宝塚記念 2着', 48, WHITE, kind='black'), text('→ {140日}ぶりのレース', 60, WHITE, kind='black')], minw=920), L, 1300, S(5) + 0.2, S(6), anchor='l')
# 06 HINT 3: 春3戦
hint(3, 6)
add(text('春の3戦', 80, stroke=8), L, 560, S(6), S(7), anchor='l')
for i, (r, p) in enumerate([('大阪杯', '1着'), ('天皇賞（春）', '1着'), ('宝塚記念', '2着')]):
    add(panel([text(f'{r}  {{{p}}}', 54, WHITE, kind='black')], pad=24, minw=760), L, 700 + 130 * i, S(6) + 0.3 + 0.25 * i, S(7), anchor='l')
add(chip('調教を見る限り 疲れは感じない', 48, bg=GOLD), L, 1150, at(6, 0.45), S(7), anchor='l', anim='zoom')
# 07 臨戦態勢
add(text('臨戦態勢', 150, stroke=12), L, 650, S(7), S(8), anchor='l', anim='zoom')
add(text('{十分}に整った', 100, stroke=10), L, 840, S(7) + 0.4, S(8), anchor='l')
# 08 人気 (谷上)
add(panel([text('人気になっても', 52, WHITE, kind='black'), text('{嫌う必要はない}', 76, WHITE, kind='black')], minw=920), L, 1300, at(8, 0.4), S(9), anchor='l')
# 09 ため (谷上)
add(text('谷上の本命は…', 100, GOLD, stroke=10), W // 2, 1380, at(9, 0.6), S(10), anim='zoom')
# 10 発表
def flash(fr, t, dt):
    a = max(0, 1 - dt / 0.35)
    if a > 0: ImageDraw.Draw(fr).rectangle((0, 0, W, H), fill=(255, 255, 255, int(255 * a)))
add_fn(flash, S(10), S(10) + 0.4, z=6)
add(text('◎', 260, GOLD, kind='black', stroke=12, sc=INK), W // 2, 440, S(10) + 0.05, S(11), anim='zoom')
add(waku_badge(1, 1, 72), W // 2, 640, S(10) + 0.2, S(11), anim='zoom')
add(fit(text('クロワデュノール', 150, WHITE, stroke=14, sc=INK), 1000), W // 2, 820, at(10, 0.45), S(11), anim='zoom')
# 11 CTA (谷上)
add(chip('◎ 1枠1番 クロワデュノール', 44, bg=GOLD), L, 200, S(11), END, anchor='l', anim='none')
add(text('あんたの本命は？', 100, stroke=10), W // 2, 1230, S(11), END, anim='zoom')
add(chip('コメントで教えて', 64, bg=GOLD), W // 2, 1400, at(11, 0.4), END, anim='zoom')

# ---------- render ----------
EL.sort(key=lambda e: e['z'])
def bg_frame(t):
    for e in BG:
        if e['t0'] <= t < e['t1']:
            if e['kind'] == 'kb': return kb_frame(e, t)
            if e['v'] is None: e['v'] = Vid(f"{P}/vids/{e['src']}.mp4", e['t1'] - e['t0'], 'cover' if e['kind'] == 'cover' else 'blur', e.get('ss', 0.0))
            return e['v'].next()
    return None
out = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', os.path.expanduser('~/aki/pick/video_noaudio.mp4')], stdin=subprocess.PIPE)
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
        rgb.save(os.path.expanduser(f'~/aki/pick/st_{t:06.2f}.jpg'), quality=85)
        for e in BG: e['v'] = None
    else: out.stdin.write(rgb.tobytes())
out.stdin.close(); out.wait(); print('frames', len(frames), 'end', END)
