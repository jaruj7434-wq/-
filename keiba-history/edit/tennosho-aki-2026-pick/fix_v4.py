# 本命予想 v4: 冒頭を東京競馬場の映像に、「ヒント」「最後に発表」を削除、谷上の場面が続かない並びに変更
import sys, re
p = sys.argv[1]; s = open(p).read()
R = [
("1: '明日の{天皇賞・秋}/俺の本命は……/{最後に発表}する', 2: 'まずはヒントから/その馬は/これまで{GⅠを4勝}',",
 "1: '明日の{天皇賞・秋}/俺の本命は……', 2: 'これまで/{GⅠは4勝}',"),
("bgv('W01', 0, S(2), 0.1); bgv('K1', S(2), S(3));", "bgv('T1', 0, S(2)); bgv('K1', S(2), S(3));"),
("bgv('W08', S(8), S(9), 0.1);", "bgv('T2', S(8), S(9));"),
("# --- background plan: 谷上 (W) と馬 (K) を交互に ---", "# --- background plan: 谷上 (W) の場面は続けない (馬・競馬場の映像の間に1つずつ) ---"),
]
for a, b in R:
    assert a in s, a; s = s.replace(a, b)
# 01: 競馬場の映像の上にタイトル。「最後に発表」の帯は削除
i = s.index('# 01 hook'); j = s.index('# 02 HINT 1')
s = s[:i] + '''# 01 hook (東京競馬場の映像)
add(text('明日の', 80, stroke=8), L, 520, 0.0, S(2), anchor='l')
add(fit(text('天皇賞・秋', 170, stroke=14), 960), L, 680, 0.1, S(2), anchor='l', anim='zoom')
add(text('谷上の本命は…', 90, GOLD, stroke=9), L, 870, at(1, 0.45), S(2), anchor='l')
''' + s[j:]
# 「HINT」チップと「その馬は」を削除
s = s.replace("hint(1, 2)\nadd(text('その馬は', 64, stroke=6), L, 560, S(2), S(3), anchor='l')\n", "add(text('これまで', 72, stroke=7), L, 560, S(2), S(3), anchor='l')\n")
s = s.replace("hint(2, 3)\n", "").replace("hint(3, 6)\n", "")
s = s.replace("counter('GⅠ {}勝', 4, 170, L, 740, at(2, 0.55), S(3), anchor='l')", "counter('GⅠ {}勝', 4, 170, L, 740, at(2, 0.3), S(3), anchor='l')")
s = s.replace("at(2, 0.65) + 0.12 * i, S(3), anchor='l')", "at(2, 0.45) + 0.12 * i, S(3), anchor='l')")
s = s.replace("# 02 HINT 1: GI 4勝", "# 02 GI 4勝").replace("# 03 HINT 2: 国内成績", "# 03 国内成績").replace("# 06 HINT 3: 春3戦", "# 06 春3戦").replace("# 08 人気 (谷上)", "# 08 人気 (競馬場の観客)")
assert 'hint(' not in s.split('def hint')[1].split('\n', 1)[1] and '最後に発表' not in s
open(p, 'w').write(s); print('ok')
