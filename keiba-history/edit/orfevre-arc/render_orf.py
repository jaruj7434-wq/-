#!/usr/bin/env python3
"""オルフェーヴル凱旋門賞 — テロップ・字幕入りの書き出し (1080x1920)。
これまでの動画と同じ見た目: 見出し Dela Gothic One + 縁取り、強調は金、字幕は黒い角丸の帯、下に金の進行バー。

実行場所: Higgs のサンドボックス (~/orfed)。フォント (~/.fonts の DelaGothicOne / NotoSansJP-VF) がそこにあるため。
  clips/ … 再現 V01..V19・谷上 T*・bgm.m4a・title.png (Higgs の job の結果 URL から取得。job は prompts/orfevre-arc/production-log.md)
  vo/line_01..18.mp3 … 谷上のナレーション
使い方: TANIUE='{"3":"T03c",...,"tail":"V19c"}' python3 render_orf.py 出力.mp4
"""
import subprocess, json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
F_HEAD = os.path.expanduser('~/.fonts/DelaGothicOne-Regular.ttf')
F_BODY = os.path.expanduser('~/.fonts/NotoSansJP-VF.ttf')
GOLD = (255, 196, 46); WHITE = (255, 255, 255); INK = (12, 12, 16)
F_MIN = os.path.expanduser('~/.fonts/ShipporiMinchoB1-ExtraBold.ttf')
CHAMP = (226, 190, 120)  # 見出しの強調: 落ち着いたシャンパンゴールド
GAPS = [0.4, 1.0, 0.6, 0.5, 0.5, 0.9, 0.5, 0.8, 0.9, 0.6, 0.8, 0.6, 0.6, 0.8, 0.6, 0.8, 1.4, 1.0, 0.4]
# 19 = 締めの呼びかけ (谷上がカメラ目線でコメントを促す)。vo/line_19.mp3 と clips/T19.mp4 があれば入れる
N = 19 if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vo/line_19.mp3')) else 18
TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse")
TANIUE = json.loads(os.environ.get('TANIUE', '{"3":"T03","8":"T08","10":"T10","12":"T12","16":"T16","tail":"V19"}'))
OUT = sys.argv[1] if len(sys.argv) > 1 else 'orfevre_arc_v2.mp4'
SUBS = {1: '世界一まで、あと一歩のところで。', 2: '{ソラ}を使って、負けた。',
        3: '2012年、フランス・凱旋門賞。\n日本の夢を背負った、金色の馬がいました。',
        4: '直線、外から一気に先頭へ。\n誰もが「勝った」と思いました。',
        5: 'ところが先頭に立った途端、\n気を抜いて、内へよれてしまう。',
        6: '迫ってきた地元の牝馬に、ゴール寸前で\nかわされて、{クビ差}の2着。',
        7: '鞍上のスミヨンは、悔し涙を流しました。',
        8: '「彼はすべてをやってくれた。……\n僕は、自分を見つめ直さなければならない」',
        9: '何年たっても、彼はこう語っています。\n「なぜ勝てなかったのか、今でも理解できない」',
        10: 'でも、本当の相棒は日本にいました。\n{池添謙一}。',
        11: '三冠をともに勝ちながら、\n世界の舞台では手綱を降ろされた男です。',
        12: '2013年、引退レースの有馬記念。\n最後の手綱は、池添に戻ってきました。',
        13: '2着に{8馬身差}。\n誰も寄せつけない、圧勝でした。',
        14: '池添はスタンドに手を上げました。\n「この馬が1番なんだ」と伝えるために。',
        15: '世界最強を証明したからこそ、\n悔しさが残りました。',
        16: '池添は言います。\n「僕にとって、かけがえのない存在。財産です」',
        17: 'この馬で、世界一になりたかった。',
        19: 'あなたは、あの日の凱旋門賞、どう見ましたか。\nぜひ、{コメント}で聞かせてください。'}

def run(*a): subprocess.run(a, check=True)
def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).decode())
# --- ナレーション: 前後の無音を削って行間を足す
os.makedirs('vo/t', exist_ok=True); D = {}
for i in range(1, N + 1):
    run('ffmpeg', '-y', '-loglevel', 'error', '-i', f'vo/line_{i:02d}.mp3', '-af', TRIM + f',apad=pad_dur={GAPS[i-1]}', '-ar', '48000', '-ac', '1', f'vo/t/{i:02d}.wav')
    D[i] = dur(f'vo/t/{i:02d}.wav') - GAPS[i - 1]
with open('vo/t/list.txt', 'w') as f:
    for i in range(1, N + 1): f.write(f"file '{i:02d}.wav'\n")
run('ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'vo/t/list.txt', '-af', 'loudnorm=I=-16:TP=-1.5', '-ar', '48000', 'vo/narr.wav')
S, t = {}, 0.0
for i in range(1, N + 1): S[i] = t; t += D[i] + GAPS[i - 1]
NARR = t; TAIL = 3.0 if N == 18 else 1.6; TOTAL = NARR + TAIL

# --- 文字の部品
_fc = {}
def font(kind, sz):
    k = (kind, sz)
    if k not in _fc:
        if kind == 'head': _fc[k] = ImageFont.truetype(F_HEAD, sz)
        else:
            f = ImageFont.truetype(F_BODY, sz); f.set_variation_by_name('Black' if kind == 'black' else 'Bold'); _fc[k] = f
    return _fc[k]
def segs(t, base, hl):
    out, cur, on = [], '', False
    for ch in t:
        if ch == '{': out.append((cur, base)); cur = ''; on = True
        elif ch == '}': out.append((cur, hl)); cur = ''; on = False
        else: cur += ch
    out.append((cur, hl if on else base)); return [s for s in out if s[0]]
def text(t, sz, color=WHITE, kind='head', hl=GOLD, stroke=10, sc=INK, glow=False):
    lines = t.split('\n'); f = font(kind, sz)
    rows = []
    for ln in lines:
        sg = segs(ln, color, hl); ws = [f.getbbox(p, stroke_width=stroke)[2] for p, _ in sg]; rows.append((sg, ws))
    w = max(sum(ws) for _, ws in rows) + 40; lh = int(sz * 1.25); h = lh * len(rows) + 40
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for r, (sg, ws) in enumerate(rows):
        x = (w - sum(ws)) // 2; y = 20 + r * lh
        for (p, c), wd in zip(sg, ws):
            d.text((x + 4, y + 6), p, font=f, fill=(0, 0, 0, 150), stroke_width=stroke, stroke_fill=(0, 0, 0, 150)); x += wd
        x = (w - sum(ws)) // 2
        for (p, c), wd in zip(sg, ws):
            d.text((x, y), p, font=f, fill=c, stroke_width=stroke, stroke_fill=sc); x += wd
    if glow:
        g = im.filter(ImageFilter.GaussianBlur(18)); base = Image.new('RGBA', im.size, (0, 0, 0, 0)); base.alpha_composite(g); base.alpha_composite(im); im = base
    return im
def subband(t):
    s = text(t, 46, WHITE, kind='bold', stroke=0)
    s = s if s.width <= 980 else s.resize((980, int(s.height * 980 / s.width)), Image.LANCZOS)
    im = Image.new('RGBA', (s.width + 40, s.height + 16), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, im.width - 1, im.height - 1), 18, fill=(0, 0, 0, 170)); im.alpha_composite(s, (20, 8)); return im
def chip(t, sz=46, bg=GOLD, fg=INK):
    s = text(t, sz, fg, kind='black', stroke=0)
    im = Image.new('RGBA', (s.width + 30, s.height + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 8, im.width - 1, im.height - 9), (im.height - 16) // 2, fill=bg); im.alpha_composite(s, (15, 2)); return im
def stack(*sp, gap=0):
    w = max(s.width for s in sp); h = sum(s.height for s in sp) + gap * (len(sp) - 1)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); y = 0
    for s in sp: im.alpha_composite(s, ((w - s.width) // 2, y)); y += s.height + gap
    return im

def mtext(t, sz, color=WHITE, hl=CHAMP, track=0.08):
    # 明朝の見出し: 縁取りなし、文字間を少し空け、ぼかした影で浮かせる
    f = ImageFont.truetype(F_MIN, sz); rows = [segs(ln, color, hl) for ln in t.split('\n')]
    def row_w(sg): return sum(f.getbbox(ch)[2] + sz * track for p, _ in sg for ch in p) - sz * track
    w = int(max(row_w(sg) for sg in rows)) + 80; lh = int(sz * 1.35); h = lh * len(rows) + 60
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay); ds = ImageDraw.Draw(sh)
    for r, sg in enumerate(rows):
        x = (w - row_w(sg)) / 2; y = 30 + r * lh
        for p, c in sg:
            for ch in p:
                ds.text((x + 3, y + 5), ch, font=f, fill=(0, 0, 0, 200)); d.text((x, y), ch, font=f, fill=c)
                x += f.getbbox(ch)[2] + sz * track
    sh = sh.filter(ImageFilter.GaussianBlur(max(4, sz // 10))); out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.alpha_composite(sh); out.alpha_composite(sh); out.alpha_composite(lay); return out
def label(t, sz=34):
    # 日付・名前の札: 金の文字の左右に細い金の線
    s_ = mtext(t, sz, CHAMP, track=0.18); ln = 70
    im = Image.new('RGBA', (s_.width + ln * 2, s_.height), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    y = s_.height // 2 + 2
    d.line((0, y, ln - 6, y), fill=CHAMP + (230,), width=2); d.line((im.width - ln + 6, y, im.width, y), fill=CHAMP + (230,), width=2)
    im.alpha_composite(s_, (ln, 0)); return im
def veil(sp, pad=60, a=120):
    # 見出しの後ろの柔らかい暗がり (読みやすさのため。輪郭は見せない)
    W_, H_ = sp.width + pad * 2, sp.height + pad * 2
    v = Image.new('RGBA', (W_, H_), (0, 0, 0, 0))
    ImageDraw.Draw(v).rounded_rectangle((pad // 2, pad // 2, W_ - pad // 2, H_ - pad // 2), 60, fill=(0, 0, 0, a))
    v = v.filter(ImageFilter.GaussianBlur(pad * 0.9)); v.alpha_composite(sp, (pad, pad)); return v
def rule(w=360):
    im = Image.new('RGBA', (w, 12), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for x in range(w):
        a = int(230 * (1 - abs(x - w / 2) / (w / 2)))
        d.point((x, 6), fill=CHAMP + (a,)); d.point((x, 5), fill=CHAMP + (a // 2,))
    return im

EL = []  # (png, x, y, t0, t1)
os.makedirs('spr', exist_ok=True)
def add(im, x, y, t0, t1, anchor='c'):
    p = f'spr/{len(EL):02d}.png'; im.save(p)
    if anchor == 'c': x -= im.width // 2
    EL.append((p, int(x), int(y), max(0.0, t0), t1))
E = lambda i: S[i] + D[i] + GAPS[i - 1]  # 行の終わり (次の行の始まり)
# 字幕 (セリフの間だけ。18 は名前の文字があるので出さない)
for i, s in SUBS.items():
    if i > N: continue
    sb = subband(s); add(sb, W // 2, 1560 - sb.height // 2, S[i], S[i] + D[i] + 0.25)
# 見出し・テロップ (明朝・シャンパンゴールド・細い罫線。レースの場面は画面上部、谷上の場面は頭にかからない大きさ)
add(veil(stack(mtext('世界一まで、', 60), rule(), mtext('あと一歩', 120, CHAMP))), W // 2, 140, S[1] + 0.1, E(1))
add(veil(stack(mtext('{ソラ}を使って', 66), rule(), mtext('負けた', 124))), W // 2, 140, S[2], E(2))
add(stack(label('2012.10.7　ロンシャン競馬場', 30), mtext('凱旋門賞', 86)), W // 2, 40, S[3] + 0.2, E(3))
add(veil(stack(mtext('ソラを使う', 42, CHAMP), mtext('先頭に立って、気を抜くこと', 32)), pad=40, a=110), W // 2, 1160, S[5] + 0.3, E(5))
add(veil(stack(mtext('{クビ差}', 150), rule(300), mtext('2着', 76))), W // 2, 140, S[6] + D[6] * 0.55, E(6))
add(label('鞍上　C.スミヨン'), 40, 200, S[7] + 0.2, E(7), anchor='l')
add(mtext('―― C.スミヨン（2012年 レース後）', 32), W // 2, 1690, S[8], E(8))
add(mtext('―― C.スミヨン（後年のインタビュー）', 32), W // 2, 1690, S[9] + D[9] * 0.4, E(9))
add(label('主戦　池添謙一'), W // 2, 60, S[10] + D[10] * 0.55, E(10))
add(stack(label('2013.12.22　中山競馬場', 30), mtext('有馬記念　{ラストラン}', 72)), W // 2, 40, S[12] + 0.2, E(12))
add(veil(stack(mtext('{8馬身差}', 136), rule(300), mtext('の圧勝', 60))), W // 2, 140, S[13] + 0.3, E(13))
add(mtext('―― 池添謙一（インタビュー）', 32), W // 2, 1690, S[16] + 0.8, E(16))
def bubble(w=86, h=66):
    # コメントの吹き出し (細い金の線)
    im = Image.new('RGBA', (w + 8, h + 26), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, w + 4, h + 4), 18, outline=CHAMP + (240,), width=4)
    d.polygon([(22, h + 2), (22, h + 24), (44, h + 2)], fill=CHAMP + (240,))
    for k in range(3): d.ellipse((w // 2 - 22 + k * 22 - 5, h // 2 - 1, w // 2 - 22 + k * 22 + 5, h // 2 + 9), fill=CHAMP + (240,))
    return im
if N == 19:
    add(veil(stack(bubble(), mtext('あなたは、どう見ましたか', 54), rule(320), mtext('{コメント}で聞かせてください', 44), gap=6), pad=50, a=110),
        W // 2, 90, S[19] + 0.3, TOTAL)
json.dump(dict(S=S, D=D, NARR=NARR, TOTAL=TOTAL), open('timing.json', 'w'))

# --- 映像
SH = {1: ('V01', 'k'), 2: ('V02', 'white'), 3: (TANIUE['3'], 'wan'), 4: ('V04', 'k'), 5: ('V05', 'k'), 6: ('V06', 'k'),
      7: ('V07', 'k'), 8: (TANIUE['8'], TANIUE.get('8k', 'wan')), 9: (TANIUE.get('9', 'V09'), 'k'), 10: (TANIUE['10'], 'wan'), 11: ('V11', 'k'),
      12: (TANIUE['12'], 'wan'), 13: ('V13', 'k'), 14: ('V14', 'k'), 15: ('V15', 'k'), 16: (TANIUE['16'], TANIUE.get('16k', 'wan')),
      17: ('V01', 'memory'), 18: ('V18', 'k'), 19: ('T19', 'wan')}
args, ch, n = [], [], 0
def clip(name, kind, L):
    global n
    args.extend(['-ss', '0.1' if kind == 'wan' else '0', '-i', f'clips/{name}.mp4'])
    f = f'[{n}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30,format=yuv420p'
    if kind == 'memory': f += ',setpts=1.6*PTS,eq=saturation=0.55:brightness=0.03,vignette=angle=PI/4,gblur=sigma=0.8'
    f += f',tpad=stop_mode=clone:stop_duration={L},trim=duration={L:.3f},setpts=PTS-STARTPTS'
    if kind == 'white': f += f',fade=t=out:st={max(0, L - 0.6):.2f}:d=0.6:color=white'
    if kind == 'memory': f += f',fade=t=in:st=0:d=0.3:color=white,fade=t=out:st={L - 0.3:.2f}:d=0.3:color=white'
    ch.append(f + f'[v{n}]'); n += 1
for i in range(1, N + 1): clip(*SH[i], D[i] + GAPS[i - 1] + (TAIL if i == 19 else 0))
if N == 18: clip(TANIUE['tail'], 'k', TAIL)
vin = ''.join(f'[v{k}]' for k in range(n))
fc = ';'.join(ch) + f';{vin}concat=n={n}:v=1:a=0[b0]'
base = n
args += ['-loop', '1', '-framerate', '30', '-t', f'{TOTAL:.2f}', '-i', 'clips/title.png']
fc += f';[{base}:v]scale={W}:{H},format=rgba,fade=t=in:st={S[18] + 0.3:.2f}:d=0.8:alpha=1[ttl];[b0][ttl]overlay=0:0:enable=\'between(t,{S[18] + 0.3:.2f},{(S[19] if N == 19 else TOTAL):.2f})\'[b1]'
cur = 'b1'; k = base + 1
for j, (p, x, y, t0, t1) in enumerate(EL):
    args += ['-loop', '1', '-framerate', '30', '-t', f'{TOTAL:.2f}', '-i', p]
    fc += (f';[{k}:v]format=rgba,fade=t=in:st={t0:.2f}:d=0.25:alpha=1,fade=t=out:st={max(t0, t1 - 0.2):.2f}:d=0.2:alpha=1[s{j}]'
           f';[{cur}][s{j}]overlay={x}:{y}:enable=\'between(t,{t0:.2f},{t1:.2f})\'[c{j}]')
    cur = f'c{j}'; k += 1
# 下の金の進行バー
args += ['-f', 'lavfi', '-t', f'{TOTAL:.2f}', '-i', f'color=c=0xFFC42E:s={W}x10:r=30']
fc += f";[{cur}][{k}:v]overlay=x='-w+w*t/{TOTAL:.2f}':y=H-10,fade=t=in:st=0:d=0.5,fade=t=out:st={TOTAL - 1.0:.2f}:d=1.0[vout]"; k += 1
args += ['-i', 'vo/narr.wav', '-i', 'clips/bgm.m4a']
fc += (f';[{k}:a]aresample=48000,apad,atrim=0:{TOTAL:.2f}[na];[{k+1}:a]aresample=48000,apad,atrim=0:{TOTAL:.2f},volume=0.20,'
       f'afade=t=in:st=0:d=1.0,afade=t=out:st={TOTAL - 3:.2f}:d=3[bg];[na][bg]amix=inputs=2:duration=first:normalize=0[aout]')
run('ffmpeg', '-y', '-loglevel', 'error', *args, '-filter_complex', fc, '-map', '[vout]', '-map', '[aout]',
    '-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-t', f'{TOTAL:.2f}', OUT)
print(json.dumps(dict(out=OUT, total=round(TOTAL, 2), reveal=round(S[18], 2), sprites=len(EL))))
