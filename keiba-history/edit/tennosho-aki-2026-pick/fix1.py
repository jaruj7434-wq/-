import sys
p=sys.argv[1]; s=open(p).read()
R=[("add(text('明日の', 72, stroke=8), L, 330,","add(text('明日の', 72, stroke=8), L, 1000,"),
("add(fit(text('天皇賞・秋', 150, stroke=12), 960), L, 470,","add(fit(text('天皇賞・秋', 150, stroke=12), 960), L, 1140,"),
("add(text('谷上の本命は…', 80, GOLD, stroke=8), L, 640,","add(text('谷上の本命は…', 80, GOLD, stroke=8), L, 1310,"),
("add(chip('最後に発表', 56, bg=RED, fg=WHITE), L, 770,","add(chip('最後に発表', 56, bg=RED, fg=WHITE), 600, 1310,"),
("add(text('国内での成績', 64, stroke=6), L, 560, S(3), S(5), anchor='l')","add(text('国内での成績', 64, stroke=6), L, 560, S(3), S(4), anchor='l')"),
("minw=920), L, 420, S(5) + 0.2, S(6), anchor='l')","minw=920), L, 1300, S(5) + 0.2, S(6), anchor='l')"),
("minw=920), L, 430, at(8, 0.4), S(9), anchor='l')","minw=920), L, 1300, at(8, 0.4), S(9), anchor='l')"),
("add(text('谷上の本命は…', 100, GOLD, stroke=10), W // 2, 450,","add(text('谷上の本命は…', 100, GOLD, stroke=10), W // 2, 1380,"),
("add(text('あんたの本命は？', 100, stroke=10), W // 2, 430,","add(text('あんたの本命は？', 100, stroke=10), W // 2, 1230,"),
("add(chip('コメントで教えて', 64, bg=GOLD), W // 2, 600,","add(chip('コメントで教えて', 64, bg=GOLD), W // 2, 1400,")]
for a,b in R:
    assert a in s, a; s=s.replace(a,b)
open(p,'w').write(s); print('ok')
