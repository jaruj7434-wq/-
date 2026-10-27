"""成功したときに出す「天使のお祝い演出」の映像と、神々しいBGM。

天使はプログラムで描いたオリジナルの絵(丸い顔・ほっぺ・にっこり目・金の輪・白い羽)。
画面の下から次々と現れて、羽ばたきながらゆらゆら昇っていく。背景には金色の光の筋と星。

    show = AngelShow(W, H, seed)
    show.draw(ctx, age)             # age = 成功してからの経過秒(ずっと天使が出続ける)
    sig = holy_music(sr, DURATION)  # 神々しいBGM(numpy 配列, -1〜1)
"""

import math

import cairo
import numpy as np

DURATION = 6.0   # お祝い演出の秒数


def _ellipse(ctx, x, y, rx, ry):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(rx, ry)
    ctx.new_path()
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()


def draw_angel(ctx, x, y, s, flap, tilt=0.0, alpha=1.0):
    """かわいい天使を1体描く。s は顔の大きさの目安、flap は羽ばたき(-1〜1)。"""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(tilt)
    # 羽(肩から外向きに広がる羽根。羽ばたきで全体が上下に動く)
    for side in (-1, 1):
        ctx.save()
        ctx.translate(side * s * 0.28, s * 0.55)
        ctx.rotate(side * (0.25 * flap))
        for deg, ln in ((-60, 0.95), (-35, 1.05), (-10, 0.95), (15, 0.75)):
            a = math.radians(deg)
            ctx.save()
            ctx.rotate(side * a if side > 0 else math.pi - a)
            _ellipse(ctx, s * ln * 0.5, 0, s * ln * 0.5, s * 0.17)
            ctx.restore()
            ctx.set_source_rgba(1, 1, 1, 0.97 * alpha)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.72, 0.8, 1.0, 0.9 * alpha)
            ctx.set_line_width(max(1.5, s * 0.035))
            ctx.stroke()
        ctx.restore()
    # 体(白い服)
    ctx.new_path()
    ctx.move_to(-s * 0.32, s * 0.45)
    ctx.curve_to(-s * 0.55, s * 1.25, s * 0.55, s * 1.25, s * 0.32, s * 0.45)
    ctx.close_path()
    ctx.set_source_rgba(1, 1, 1, alpha)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.8, 0.85, 1.0, alpha)
    ctx.set_line_width(max(1.5, s * 0.04))
    ctx.stroke()
    # 顔
    _ellipse(ctx, 0, 0, s * 0.5, s * 0.48)
    ctx.set_source_rgba(1.0, 0.86, 0.74, alpha)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.92, 0.7, 0.58, alpha)
    ctx.set_line_width(max(1.5, s * 0.035))
    ctx.stroke()
    # 金色の髪(くるっと巻いた前髪)
    for dx in (-0.22, 0.0, 0.22):
        _ellipse(ctx, s * dx, -s * 0.38, s * 0.16, s * 0.13)
        ctx.set_source_rgba(1.0, 0.82, 0.35, alpha)
        ctx.fill()
    # ほっぺ
    for side in (-1, 1):
        _ellipse(ctx, side * s * 0.27, s * 0.12, s * 0.1, s * 0.07)
        ctx.set_source_rgba(1.0, 0.55, 0.6, 0.6 * alpha)
        ctx.fill()
    # にっこり目
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_width(max(2.0, s * 0.06))
    ctx.set_source_rgba(0.35, 0.22, 0.2, alpha)
    for side in (-1, 1):
        ctx.new_path()
        ctx.arc(side * s * 0.17, -s * 0.02, s * 0.09, math.pi * 1.1, math.pi * 1.9)
        ctx.stroke()
    # 口
    ctx.new_path()
    ctx.arc(0, s * 0.12, s * 0.1, math.pi * 0.15, math.pi * 0.85)
    ctx.stroke()
    # 天使の輪(光る)
    for wdt, col, al in ((0.16, (1.0, 0.97, 0.75), 0.35), (0.07, (1.0, 0.85, 0.3), 1.0)):
        ctx.save()
        ctx.translate(0, -s * 0.68)
        ctx.scale(s * 0.36, s * 0.11)
        ctx.new_path()
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(*col, al * alpha)
        ctx.set_line_width(max(2.5, s * wdt))
        ctx.stroke()
    ctx.restore()


class AngelShow:
    def __init__(self, w, h, seed=0):
        self.w, self.h = w, h
        self.rng = np.random.default_rng(seed)
        self.angels = []
        self.next_spawn = 0.0
        self.last_age = 0.0
        self.stars = [(self.rng.uniform(0, w), self.rng.uniform(0, h), self.rng.uniform(0, 6.28),
                       self.rng.uniform(2, 5)) for _ in range(70)]

    def _spawn(self, age, anywhere=False):
        r = self.rng
        size = r.uniform(55, 120)
        if anywhere:            # 最初の一瞬で画面じゅうにポンと現れる
            x, y = r.uniform(80, self.w - 80), r.uniform(450, self.h - 150)
            vx, vy = r.uniform(-40, 40), -r.uniform(150, 260)
        elif r.random() < 0.75:   # 下から昇ってくる
            x, y = r.uniform(80, self.w - 80), self.h + 120
            vx, vy = r.uniform(-30, 30), -r.uniform(260, 380)
        else:                   # 横から飛んでくる
            side = r.choice([-1, 1])
            x, y = (self.w + 120) if side > 0 else -120, r.uniform(500, self.h - 300)
            vx, vy = -side * r.uniform(180, 260), -r.uniform(30, 90)
        self.angels.append({"x": x, "y": y, "vx": vx, "vy": vy, "s": size, "born": age,
                            "phase": r.uniform(0, 6.28), "sway": r.uniform(30, 70)})

    def draw(self, ctx, age):
        dt = max(0.0, age - self.last_age)
        self.last_age = age
        w, h = self.w, self.h
        k = min(1.0, age / 0.6)
        # やわらかい金色の光
        g = cairo.RadialGradient(w / 2, 260, 20, w / 2, 260, h * 0.9)
        g.add_color_stop_rgba(0, 1.0, 0.95, 0.75, 0.55 * k)
        g.add_color_stop_rgba(1, 1.0, 0.85, 0.6, 0.0)
        ctx.set_source(g)
        ctx.paint()
        # 光の筋(ゆっくり回る)
        ctx.save()
        ctx.translate(w / 2, 260)
        ctx.rotate(age * 0.15)
        for i in range(16):
            a = i * 2 * math.pi / 16
            ctx.new_path()
            ctx.move_to(0, 0)
            ctx.line_to(math.cos(a - 0.07) * 2200, math.sin(a - 0.07) * 2200)
            ctx.line_to(math.cos(a + 0.07) * 2200, math.sin(a + 0.07) * 2200)
            ctx.close_path()
            ctx.set_source_rgba(1.0, 0.92, 0.6, 0.10 * k)
            ctx.fill()
        ctx.restore()
        # キラキラの星
        for x, y, ph, sz in self.stars:
            tw = 0.5 + 0.5 * math.sin(age * 6 + ph)
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(math.pi / 4)
            ctx.new_path()
            for j in range(8):
                rr = sz * (2.2 if j % 2 == 0 else 0.6) * (0.6 + 0.6 * tw)
                ctx.line_to(rr * math.cos(j * math.pi / 4), rr * math.sin(j * math.pi / 4))
            ctx.close_path()
            ctx.set_source_rgba(1, 1, 0.85, 0.8 * tw * k)
            ctx.fill()
            ctx.restore()
        # 天使(最初にどっと現れ、そのあともずっと出続ける)
        if not self.angels and age < 0.1 and self.next_spawn == 0.0:
            for _ in range(12):
                self._spawn(0.0, anywhere=True)
        while self.next_spawn <= age:
            self._spawn(self.next_spawn)
            self.next_spawn += 0.16
        alive = []
        for a in self.angels:
            a["x"] += a["vx"] * dt
            a["y"] += a["vy"] * dt
            life = age - a["born"]
            if a["y"] < -200 or a["x"] < -250 or a["x"] > w + 250:
                continue
            alive.append(a)
        self.angels = alive
        for a in sorted(self.angels, key=lambda a_: a_["s"]):
            life = age - a["born"]
            x = a["x"] + a["sway"] * math.sin(life * 2.2 + a["phase"])
            flap = math.sin(life * 14 + a["phase"])
            pop = min(1.0, life / 0.18)   # ポンと大きくなって現れる
            draw_angel(ctx, x, a["y"], a["s"] * (0.4 + 0.6 * pop), flap, tilt=0.12 * math.sin(life * 2.2 + a["phase"]),
                       alpha=pop)


def _choir_note(freq, dur, sr, amp):
    """「アー」という合唱のような音(倍音を母音の形にそろえ、ゆっくり立ち上がる)。"""
    n = int(dur * sr)
    t = np.arange(n) / sr
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t)
    phase = 2 * np.pi * freq * np.cumsum(vib) / sr
    y = np.zeros(n)
    for k in range(1, 14):
        fk = freq * k
        w = 1.0 / k + 1.2 * math.exp(-((fk - 750) / 260) ** 2) + 0.7 * math.exp(-((fk - 1150) / 330) ** 2)
        y += w * np.sin(k * phase)
    env = np.minimum(1, t / 0.35) * np.minimum(1, (dur - t) / 0.5).clip(0, 1)
    return amp * y * env / 6


def _bell(freq, dur, sr, amp):
    t = np.arange(int(dur * sr)) / sr
    y = np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t * 3)
    return amp * y * np.exp(-t * 1.6) * np.minimum(1, t / 0.003)


def holy_music(sr, dur=DURATION):
    """神々しいBGM:合唱の和音(ハ長調 I-IV-V-I)+ ハープのグリッサンド + 鐘。"""
    out = np.zeros(int((dur + 1) * sr))

    def add(sig, t0):
        i = int(t0 * sr)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    def hz(m):
        return 440.0 * 2 ** ((m - 69) / 12)

    chords = [[48, 55, 60, 64, 67, 72], [53, 60, 65, 69, 72, 77],
              [55, 62, 67, 71, 74, 79], [48, 55, 60, 64, 67, 72, 76, 84]]
    seg = dur / 4
    for i, ch in enumerate(chords):
        last = i == len(chords) - 1
        length = (dur - i * seg) if last else seg + 0.45
        for m in ch:
            add(_choir_note(hz(m), length, sr, 0.22 if m < 60 else 0.18), i * seg)
    # ハープのグリッサンド(下から上へ)
    for k, m in enumerate([60, 64, 67, 72, 76, 79, 84, 88, 91, 96]):
        add(_bell(hz(m), 1.8, sr, 0.16), 0.05 + k * 0.045)
    # 鐘
    for t0, m in ((1.2, 84), (2.6, 88), (4.1, 91), (seg * 3, 96)):
        add(_bell(hz(m), 2.5, sr, 0.18), t0)
    # 残響
    wet = out.copy()
    for d, g in ((0.05, 0.35), (0.083, 0.28), (0.127, 0.22), (0.19, 0.15)):
        k = int(d * sr)
        wet[k:] += out[:-k] * g
    wet = wet[: int(dur * sr)]
    return wet / max(1e-9, np.max(np.abs(wet)))
