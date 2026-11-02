# ---------- ハルウララ編 (render_haru.py の後半) ----------
# render2.py の部品 (text / panel / chip / Vid / counter など) を使い、馬の再現映像 + 谷上 (Wan) で構成する。
# 谷上 (W) の場面は続けない: V01 W02 V03 V04 W05 V06 V07 W08 V09 V10 W11 V12 W13
P = os.path.expanduser('~/aki/haru')
PINK = (255, 128, 176)

# ---------- HUD ----------
HUD_TAG = chip('谷上の好きな馬', 34, bg=(12, 16, 26, 200), fg=WHITE)
NOTE = chip('※AIによる再現イメージ', 26, bg=(12, 16, 26, 150), fg=(220, 220, 220), kind='bold')
WSCENES = []
def hud(fr, t, dt):
    fr.alpha_composite(HUD_TAG, (40, 70))
    if not any(a <= t < b for a, b in WSCENES): fr.alpha_composite(NOTE, (W - NOTE.width - 40, 78))
    ImageDraw.Draw(fr).rectangle((0, H - 10, int(W * t / END), H), fill=PINK)
add_fn(hud, 0, END, z=8)

# ---------- 字幕帯 (render2.py と同じ) ----------
def subband(t):
    s = text(t, 60, WHITE, kind='black', hl=PINK, shadow=False); s = fit(s, 960)
    im = Image.new('RGBA', (s.width + 60, s.height + 34), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, im.width - 1, im.height - 1), 14, fill=(0, 0, 0, 175)); im.alpha_composite(s, (30, 17)); return im

SUB = {
1: '{113戦}して/1回も勝てなかった馬がいる', 2: '俺が大好きな馬/{ハルウララ}だ',
3: '1996年 北海道の生まれ/小さくて{臆病}な馬だった', 4: '高知競馬でデビューして/負けて 負けて/それでも{走り続けた}',
5: 'でもな ウララは{手を抜かなかった}/いつだって一生懸命なんだ', 6: '2003年 連敗が話題になって/{「負け組の星」}と呼ばれた',
7: '当たらない単勝馬券は/{「交通安全のお守り」}になった', 8: '2004年には あの{武豊}が乗った/高知競馬場に{1万3000人}だぞ',
9: '結果は{10着}/それでも武豊は/{ウイニングラン}をしてくれた', 10: '引退後は千葉の牧場で/たくさんのファンに会いに来てもらって/{2025年 29歳}で天国へ',
11: '勝てなくても/こんなに{愛される}/ウララは そういう馬だった', 12: '{113戦0勝}/俺にとっては{最高の名馬}だ',
13: 'あんたの大好きな馬は誰だ？/{コメント}で教えてくれ',
}
SUBY = 1590
for n, txt in SUB.items():
    parts = txt.split('/'); lens = [len(re.sub(r'[{}]', '', p)) for p in parts]; a, b = T[n]; t = a
    for i, (p, L_) in enumerate(zip(parts, lens)):
        d_ = (b - a) * L_ / sum(lens); t1 = t + d_ if i < len(parts) - 1 else E(n) - 0.02
        add(subband(p), W // 2, SUBY, t, t1, anim='none', z=7); t += d_

L = 80
def bgv(name, a, b, ss=0.0):
    BG.append(dict(kind='cover', src=name, t0=a, t1=b, v=None, img=None, ss=ss))
    if name.startswith('W'): WSCENES.append((a, b))

# --- background plan ---
bgv('V01', 0, S(2)); bgv('W02', S(2), S(3), 0.1); bgv('V03', S(3), S(4)); bgv('V04', S(4), S(5)); bgv('W05', S(5), S(6), 0.1)
bgv('V06', S(6), S(7)); bgv('V07', S(7), S(8)); bgv('W08', S(8), S(9), 0.1); bgv('V09', S(9), S(10)); bgv('V10', S(10), S(11))
bgv('W11', S(11), S(12), 0.1); bgv('V12', S(12), S(13)); bgv('W13', S(13), END, 0.1)

# 01 hook: 113戦 → 0勝
counter('{}戦', 113, 220, L, 580, 0.1, S(2), color=WHITE, dur=1.2, anchor='l')
add(text('1回も勝てなかった', 76, stroke=8), L, 800, at(1, 0.45), S(2), anchor='l')
add(text('0勝', 200, RED, stroke=10, sc=WHITE, outer=10, oc=(110, 0, 0)), W // 2, 1040, at(1, 0.75), S(2), anim='zoom')
# 02 名前 (谷上)
add(text('俺が大好きな馬', 64, stroke=7), W // 2, 230, S(2) + 0.1, S(3), anim='zoom')
add(fit(text('ハルウララ', 170, PINK, stroke=14, sc=WHITE, outer=8, oc=INK), 980), W // 2, 370, at(2, 0.5), S(3), anim='zoom')
# 03 生まれ
add(chip('1996年2月27日', 48, bg=PINK), L, 420, S(3) + 0.1, S(4), anchor='l')
add(text('北海道 三石町生まれ', 76, stroke=8), L, 540, S(3) + 0.3, S(4), anchor='l')
for i, w_ in enumerate(['小柄', '臆病']):
    add(panel([text(w_, 70, WHITE, kind='black')], pad=26), L + 300 * i, 1300, at(3, 0.6) + 0.2 * i, S(4), anchor='l', anim='zoom')
# 04 デビュー
add(chip('1998年 高知競馬でデビュー', 46, bg=(12, 16, 26, 210), fg=WHITE), L, 420, S(4) + 0.1, S(5), anchor='l')
add(text('負けて、', 110, stroke=10), L, 600, at(4, 0.25), S(5), anchor='l')
add(text('負けて、', 110, stroke=10), L + 160, 760, at(4, 0.45), S(5), anchor='l')
add(text('{走り続けた}', 110, stroke=10, hl=PINK), L, 940, at(4, 0.7), S(5), anchor='l', anim='zoom')
# 05 一生懸命 (谷上)
add(panel([text('いつだって', 50, WHITE, kind='black'), text('{一生懸命}', 96, WHITE, kind='black', hl=PINK)], accent=PINK, minw=700), L, 1300, at(5, 0.45), S(6), anchor='l')
# 06 負け組の星
add(chip('2003年', 50, bg=PINK), L, 420, S(6) + 0.1, S(7), anchor='l')
add(text('連敗が話題に', 80, stroke=8), L, 560, S(6) + 0.3, S(7), anchor='l')
add(fit(text('「負け組の星」', 140, PINK, stroke=12, sc=WHITE, outer=8, oc=INK), 980), W // 2, 760, at(6, 0.55), S(7), anim='zoom')
# 07 お守り
add(panel([text('当たらない単勝馬券', 56, WHITE, kind='black'), text('= {交通安全のお守り}', 66, WHITE, kind='black', hl=PINK)], accent=PINK, minw=920), L, 520, at(7, 0.3), S(8), anchor='l')
# 08 武豊騎乗 (谷上)
add(chip('2004年3月22日', 44, bg=PINK), L, 230, S(8) + 0.1, S(9), anchor='l')
add(panel([text('武豊騎手が騎乗', 56, WHITE, kind='black')], pad=26, minw=600), L, 340, at(8, 0.2), S(9), anchor='l')
counter('{:,}人', 13000, 130, W // 2, 1340, at(8, 0.55), S(9), color=GOLD, dur=0.9)
add(text('高知競馬場に', 58, stroke=6), W // 2, 1210, at(8, 0.5), S(9))
# 09 10着 → ウイニングラン
add(text('結果は', 70, stroke=7), L, 440, S(9) + 0.1, S(10), anchor='l')
counter('{}着', 10, 200, L + 250, 440, S(9) + 0.3, S(10), color=WHITE, dur=0.6, anchor='l')
add(panel([text('それでも', 48, WHITE, kind='black'), text('{ウイニングラン}', 84, WHITE, kind='black', hl=GOLD)], minw=760), L, 680, at(9, 0.45), S(10), anchor='l', anim='zoom')
# 10 引退後
add(chip('引退後', 46, bg=PINK), L, 420, S(10) + 0.1, S(11), anchor='l')
add(text('千葉の牧場で', 80, stroke=8), L, 550, S(10) + 0.3, S(11), anchor='l')
add(text('ファンに囲まれて', 70, stroke=7), L, 680, at(10, 0.3), S(11), anchor='l')
add(panel([text('2025年9月9日', 46, WHITE, kind='black'), text('{29歳}で天国へ', 74, WHITE, kind='black', hl=PINK)], accent=PINK, minw=760), L, 1300, at(10, 0.68), S(11), anchor='l')
# 11 愛される (谷上)
add(text('勝てなくても', 72, stroke=7), W // 2, 1180, S(11) + 0.2, S(12), anim='zoom')
add(text('{愛される}', 130, stroke=12, hl=PINK), W // 2, 1350, at(11, 0.45), S(12), anim='zoom')
# 12 113戦0勝 / 最高の名馬
add(text('113戦0勝', 170, stroke=14), W // 2, 600, S(12) + 0.1, S(13), anim='zoom')
add(text('最高の名馬', 140, GOLD, stroke=12, sc=INK, outer=8, oc=(90, 60, 0)), W // 2, 800, at(12, 0.5), S(13), anim='zoom')
# 13 CTA (谷上)
add(chip('ハルウララ  113戦0勝', 40, bg=PINK), L, 200, S(13), END, anchor='l', anim='none')
add(text('あんたの大好きな馬は？', 84, stroke=9), W // 2, 1230, S(13), END, anim='zoom')
add(chip('コメントで教えて', 64, bg=PINK), W // 2, 1400, at(13, 0.4), END, anim='zoom')
