"""成功したときの「大当たり」風の終わり方(映像と音)。

パチンコの当たり演出でよく使われる「お約束」を、特定の機種のまねにならないよう自前の絵と音で組み合わせた:
  1. フリーズ   … 最後の1枚が割れた瞬間、画面が止まって色が抜け、音も消える(0.5秒)→ ドンッ!
  2. 虹ストロボ … 画面全体が虹色にバチバチ点滅し「キュインキュイン!」
  3. 図柄揃い   … 3つのリールにボールの絵柄が回り、左・右・真ん中の順に止まって 隕石・隕石・隕石 が揃う
                  (真ん中はゆっくりになって、じらしてから止まる)
  4. 大当たり   … 虹色の光の筋が高速回転、画面のふちの電飾が虹色に流れ、紙吹雪とキラキラが噴き出し、
                  金と虹にギラギラ光る「全部割った!!」がドンと出る。音はファンファーレ風の連打+キュイン+チャリンチャリン
映像も音もすべてこのファイルの中で作る(既存の曲・効果音・機種の素材は使わない)。
"""
import colorsys
import math

import cairo
import numpy as np

DURATION = 9.5
FONT = "IPAGothic"
T_FREEZE = 0.5      # フリーズの長さ
T_STROBE = 1.2      # 虹ストロボの終わり
REEL_STOP = (2.0, 2.45, 3.35)   # 左・右・真ん中のリールが止まる時刻
T_BIG = 3.45        # 大当たり本番の始まり
WIN = 5             # 揃う絵柄(隕石)


def _rainbow(h, s=1.0, v=1.0):
    return colorsys.hsv_to_rgb(h % 1.0, s, v)


# ---------------------------------------------------------------- 映像
class Jackpot:
    def __init__(self, W, H, seed, cx, cy, draw_ball, n_kinds=6, main="全部割った!!", count="432 / 432"):
        rng = np.random.default_rng(seed + 8080)
        self.W, self.H, self.cx, self.cy = W, H, cx, cy
        self.draw_ball, self.n = draw_ball, n_kinds
        self.main, self.count = main, count
        self.frozen = None
        self.confetti = [(rng.uniform(0, W), rng.uniform(-900, -20), rng.uniform(140, 380), rng.uniform(0, 1),
                          rng.uniform(0, 6.28), rng.uniform(-9, 9), rng.uniform(10, 22)) for _ in range(220)]
        self.fountain = [(rng.uniform(-0.55, 0.55), rng.uniform(1300, 2300), rng.uniform(7, 18), rng.uniform(0, 1),
                          rng.uniform(0, 5.5), rng.uniform(-8, 8)) for _ in range(260)]
        self.burst = [(rng.uniform(0, 2 * math.pi), rng.uniform(500, 1600), rng.uniform(8, 20), rng.uniform(0, 1))
                      for _ in range(160)]

    # ------------------------------------------------ 部品
    @staticmethod
    def _star(ctx, x, y, r, rot):
        ctx.new_path()
        for i in range(8):
            a = rot + i * math.pi / 4
            rr = r if i % 2 == 0 else r * 0.3
            ctx.line_to(x + rr * math.cos(a), y + rr * math.sin(a))
        ctx.close_path()

    def _text(self, ctx, s, cx, y, size, age, gold=False):
        """ギラギラ光る文字(黒ふち+白ふち、中は虹(または金)のグラデーションが流れ、光の筋が走る)。"""
        ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(size)
        ext = ctx.text_extents(s)
        x = cx - ext.width / 2 - ext.x_bearing
        ctx.new_path()
        ctx.move_to(x, y)
        ctx.text_path(s)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        # 外側に虹色の光(にじみ)
        for w, a in ((size * 0.55, 0.25), (size * 0.40, 0.45)):
            ctx.set_source_rgba(*_rainbow(age * 1.3), a)
            ctx.set_line_width(w)
            ctx.stroke_preserve()
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(size * 0.28)
        ctx.stroke_preserve()
        ctx.set_source_rgb(1, 1, 1)
        ctx.set_line_width(size * 0.13)
        ctx.stroke_preserve()
        g = cairo.LinearGradient(x, y - size, x + ext.width * 0.4, y)
        if gold:
            for i, c in enumerate(((1, 0.97, 0.7), (1, 0.8, 0.15), (0.75, 0.45, 0.0), (1, 0.9, 0.4), (0.85, 0.55, 0.05))):
                g.add_color_stop_rgb(i / 4, *c)
            g.set_extend(cairo.EXTEND_REFLECT)
        else:
            for i in range(8):
                g.add_color_stop_rgb(i / 7, *_rainbow(i / 7 - age * 1.2))
            g.set_extend(cairo.EXTEND_REPEAT)
        ctx.set_source(g)
        ctx.fill_preserve()
        p = (age * 1.8) % 1.5 - 0.25
        sx = x + ext.width * p
        g2 = cairo.LinearGradient(sx - 70, y - size, sx + 70, y)
        g2.add_color_stop_rgba(0, 1, 1, 1, 0)
        g2.add_color_stop_rgba(0.5, 1, 1, 1, 0.95)
        g2.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g2)
        ctx.fill()

    def _rays(self, ctx, age, speed, alpha, n=28):
        cx, cy = self.cx, self.cy
        rot = age * speed
        for i in range(n):
            a0 = rot + i * 2 * math.pi / n
            col = _rainbow(i / n + age * 0.8)
            ctx.new_path()
            ctx.move_to(cx, cy)
            ctx.arc(cx, cy, 1700, a0, a0 + math.pi / n)
            ctx.close_path()
            g = cairo.RadialGradient(cx, cy, 0, cx, cy, 1300)
            g.add_color_stop_rgba(0, *col, 0.75 * alpha)
            g.add_color_stop_rgba(1, *col, 0.15 * alpha)
            ctx.set_source(g)
            ctx.fill()

    def _bulbs(self, ctx, age, alpha):
        """画面のふちの電飾。虹色の光が周りをぐるぐる流れる。"""
        W, H = self.W, self.H
        step = 54
        pts = [(x, 22) for x in range(22, W, step)] + [(W - 22, y) for y in range(22, H, step)] + \
              [(x, H - 22) for x in range(W - 22, 0, -step)] + [(22, y) for y in range(H - 22, 0, -step)]
        n = len(pts)
        for i, (x, y) in enumerate(pts):
            ph = (i / n * 6 - age * 3.5) % 1.0
            on = 1.0 if ph < 0.5 else 0.35
            col = _rainbow(i / n * 3 - age * 1.5)
            g = cairo.RadialGradient(x, y, 0, x, y, 26)
            g.add_color_stop_rgba(0, 1, 1, 1, alpha * on)
            g.add_color_stop_rgba(0.35, *col, alpha * on)
            g.add_color_stop_rgba(1, *col, 0)
            ctx.set_source(g)
            ctx.arc(x, y, 26, 0, 2 * math.pi)
            ctx.fill()

    def _reels(self, ctx, age):
        """3つのリール(図柄)。左・右・真ん中の順に止まり、隕石が揃う。"""
        W, cy = self.W, self.H * 0.47
        rw, rh, gap = 310, 440, 22
        x0 = W / 2 - 1.5 * rw - gap
        cell = 380.0
        # 枠
        ctx.rectangle(x0 - 26, cy - rh / 2 - 26, 3 * rw + 2 * gap + 52, rh + 52)
        g = cairo.LinearGradient(0, cy - rh / 2 - 26, 0, cy + rh / 2 + 26)
        g.add_color_stop_rgb(0, 1, 0.9, 0.4)
        g.add_color_stop_rgb(0.5, 0.6, 0.35, 0.0)
        g.add_color_stop_rgb(1, 1, 0.85, 0.3)
        ctx.set_source(g)
        ctx.fill()
        for r in range(3):
            rx = x0 + r * (rw + gap)
            stop = REEL_STOP[(0, 2, 1)[r]]   # 左・真ん中・右 → 左・右・真ん中の順に止まる
            ctx.save()
            ctx.rectangle(rx, cy - rh / 2, rw, rh)
            ctx.clip()
            bg = cairo.LinearGradient(0, cy - rh / 2, 0, cy + rh / 2)
            bg.add_color_stop_rgb(0, 0.05, 0.02, 0.12)
            bg.add_color_stop_rgb(0.5, 0.18, 0.1, 0.3)
            bg.add_color_stop_rgb(1, 0.05, 0.02, 0.12)
            ctx.set_source(bg)
            ctx.paint()
            t = age - T_STROBE
            # 位置(絵柄何個ぶん回ったか)。止まる時刻に WIN がちょうど真ん中に来るように逆算する
            ts = stop - T_STROBE
            spd = 22.0   # 1秒に回る絵柄の数
            end_pos = (10 + 3 * r) * self.n + WIN   # 止まったとき真ん中に隕石が来る位置
            if t < ts:
                if r == 1:
                    # 真ん中: 速さが途中から落ちていく(位置は止まる位置から逆算)
                    slow0 = REEL_STOP[1] - T_STROBE
                    if t <= slow0:
                        pos = end_pos - (spd * (slow0 - t) + 0.5 * spd * (ts - slow0))
                    else:
                        u = (t - slow0) / (ts - slow0)
                        pos = end_pos - 0.5 * spd * (ts - slow0) * (1 - u) ** 2
                else:
                    pos = end_pos - spd * (ts - t)
                bounce = 0.0
            else:
                pos = end_pos
                a = t - ts
                bounce = 0.18 * math.exp(-a * 9) * math.sin(a * 30)
            pos += bounce
            blur = t < ts - 0.05 and (r != 1 or t < REEL_STOP[1] - T_STROBE + 0.5)
            for j in range(-2, 3):
                idx = math.floor(pos) + j
                off = (idx - pos) * cell
                kind = idx % self.n
                yy = cy + off
                if blur:
                    for b in range(3):
                        self.draw_ball(ctx, kind, rx + rw / 2, yy - b * 50, 0.0, 115, age, 0.35, None)
                else:
                    self.draw_ball(ctx, kind, rx + rw / 2, yy, 0.0, 128, age, 1.0, None)
            # 上下を暗く
            sh = cairo.LinearGradient(0, cy - rh / 2, 0, cy + rh / 2)
            sh.add_color_stop_rgba(0, 0, 0, 0, 0.85)
            sh.add_color_stop_rgba(0.25, 0, 0, 0, 0)
            sh.add_color_stop_rgba(0.75, 0, 0, 0, 0)
            sh.add_color_stop_rgba(1, 0, 0, 0, 0.85)
            ctx.set_source(sh)
            ctx.paint()
            # 止まった瞬間に白く光る
            if 0 <= t - ts < 0.2:
                ctx.set_source_rgba(1, 1, 1, 0.7 * (1 - (t - ts) / 0.2))
                ctx.paint()
            ctx.restore()
        # 真ん中がじらしているあいだは「リーチ!」
        if REEL_STOP[1] + 0.05 < age < REEL_STOP[2]:
            k = min(1.0, (age - REEL_STOP[1] - 0.05) / 0.12)
            self._text(ctx, "リーチ!!", W / 2, cy - rh / 2 - 70, 110 * (1.3 - 0.3 * k), age, gold=True)

    # ------------------------------------------------ 本体
    def draw(self, surf, ctx, age):
        W, H, cx, cy = self.W, self.H, self.cx, self.cy
        # 1) フリーズ: 割れた瞬間の画面で止まり、色が抜けていく
        if self.frozen is None:
            self.frozen = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            fc = cairo.Context(self.frozen)
            fc.set_source_surface(surf, 0, 0)
            fc.paint()
        if age < T_FREEZE:
            ctx.set_source_surface(self.frozen, 0, 0)
            ctx.paint()
            k = age / T_FREEZE
            ctx.set_operator(cairo.OPERATOR_HSL_SATURATION)
            ctx.set_source_rgba(0.5, 0.5, 0.5, min(1.0, k * 1.5))
            ctx.paint()
            ctx.set_operator(cairo.OPERATOR_OVER)
            ctx.set_source_rgba(0, 0, 0, 0.45 * k)
            ctx.paint()
            return
        a = age - T_FREEZE
        # 2) 虹ストロボ(バチバチ点滅)
        if age < T_STROBE:
            ctx.set_source_surface(self.frozen, 0, 0)
            ctx.paint()
            on = int(a * 24) % 2 == 0
            ctx.set_source_rgba(*_rainbow(a * 5), 0.9 if on else 0.35)
            ctx.paint()
            if a < 0.08:
                ctx.set_source_rgba(1, 1, 1, 1 - a / 0.08)
                ctx.paint()
            self._text(ctx, "!!", W / 2, H * 0.52, 360 * (1 + 0.2 * math.sin(a * 40)), age)
            return
        # 背景(暗い紫)+光の筋(大当たり本番で一気に速く・明るく)
        bg = cairo.RadialGradient(cx, cy, 0, cx, cy, 1300)
        bg.add_color_stop_rgb(0, 0.25, 0.05, 0.3)
        bg.add_color_stop_rgb(1, 0.02, 0.0, 0.05)
        ctx.set_source(bg)
        ctx.paint()
        big = age >= T_BIG
        self._rays(ctx, age, 4.0 if big else 0.8, 1.0 if big else 0.35)
        if not big:
            self._reels(ctx, age)
            self._bulbs(ctx, age, 0.6)
            for i, st in enumerate(REEL_STOP[:2]):   # 止まるたびに軽くフラッシュ
                if 0 <= age - st < 0.12:
                    ctx.set_source_rgba(1, 1, 1, 0.4 * (1 - (age - st) / 0.12))
                    ctx.paint()
            return
        b = age - T_BIG
        # 3) 大当たり本番
        # 中心の脈打つ光
        pulse = 0.7 + 0.3 * math.sin(age * 16)
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, 520)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.95 * pulse)
        g.add_color_stop_rgba(0.35, *_rainbow(age), 0.55)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g)
        ctx.arc(cx, cy, 520, 0, 2 * math.pi)
        ctx.fill()
        # 中心からはじける虹のキラキラ
        for ang, v, sz, hue in self.burst:
            if b > 1.5:
                break
            d = v * b * (1 - 0.3 * b)
            x, y = cx + d * math.cos(ang), cy + d * math.sin(ang)
            self._star(ctx, x, y, sz, b * 5)
            ctx.set_source_rgba(*_rainbow(hue + age), 1 - b / 1.5)
            ctx.fill()
        # 下から噴き上がるキラキラ(噴水)
        for vx, v, sz, hue, t0, spin in self.fountain:
            tt = b - t0 * 0.9
            if tt <= 0 or tt > 1.8:
                continue
            x = W / 2 + vx * v * tt
            y = H + 40 - v * tt + 0.5 * 2200 * tt * tt
            tw = 0.6 + 0.4 * math.sin(age * 35 + hue * 30)
            self._star(ctx, x, y, sz * tw, spin * tt)
            ctx.set_source_rgba(*_rainbow(hue + age * 0.5), 0.95)
            ctx.fill_preserve()
            ctx.set_source_rgba(1, 1, 1, tw)
            ctx.set_line_width(1.5)
            ctx.stroke()
        # 紙吹雪
        for x0, y0, v, hue, ph, spin, sz in self.confetti:
            y = y0 + v * b
            if y > H + 40:
                continue
            x = x0 + 40 * math.sin(b * 2 + ph)
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(ph + spin * b)
            ctx.scale(1, abs(math.cos(b * 6 + ph)) + 0.15)
            ctx.rectangle(-sz / 2, -sz / 4, sz, sz / 2)
            ctx.set_source_rgb(*_rainbow(hue))
            ctx.fill()
            ctx.restore()
        # 文字(ドンと出て、少しゆれながら脈打つ)
        land = min(1.0, b / 0.18)
        sc = (2.6 - 1.6 * land) * (1 + 0.04 * math.sin(age * 12))
        shx = 18 * math.exp(-b * 8) * math.sin(b * 70)
        ctx.save()
        ctx.translate(W / 2 + shx, H * 0.43)
        ctx.scale(sc, sc)
        self._text(ctx, self.main, 0, 55, 132 if len(self.main) > 6 else 150, age)
        ctx.restore()
        if b > 0.35:
            k = min(1.0, (b - 0.35) / 0.15)
            ctx.save()
            ctx.translate(W / 2, H * 0.56)
            ctx.scale(k * (1 + 0.05 * math.sin(age * 10)), k)
            self._text(ctx, "ALL CLEAR", 0, 35, 100, age + 0.5, gold=True)
            ctx.restore()
        if b > 0.6:
            k = min(1.0, (b - 0.6) / 0.15)
            ctx.save()
            ctx.translate(W / 2, H * 0.64)
            ctx.scale(k, k)
            self._text(ctx, self.count, 0, 30, 84, age + 0.2)
            ctx.restore()
        self._bulbs(ctx, age, 1.0)
        # 本番開始のフラッシュと、たまに入る虹ストロボ
        if b < 0.25:
            ctx.set_source_rgba(1, 1, 1, 0.95 * (1 - b / 0.25))
            ctx.paint()
        elif int(age * 3) % 4 == 0 and int(age * 24) % 2 == 0:
            ctx.set_source_rgba(*_rainbow(age * 3), 0.18)
            ctx.paint()
        if age > DURATION - 0.6:
            ctx.set_source_rgba(0, 0, 0, (age - (DURATION - 0.6)) / 0.6)
            ctx.paint()


# ---------------------------------------------------------------- 音
def _hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _kyuin(sr, up=1.0):
    """「キュイン!」: 一気に高く上がる明るい電子音。"""
    t = np.arange(int(0.3 * sr)) / sr
    f = (650 + 2400 * (1 - np.exp(-t / 0.06))) * up
    f *= 1 + 0.035 * np.sin(2 * np.pi * 30 * t)
    ph = 2 * np.pi * np.cumsum(f) / sr
    y = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph) + 0.15 * np.sin(5 * ph)
    return y * np.minimum(1, t / 0.005) * np.exp(-np.maximum(0, t - 0.15) * 14)


def _sq(m, dur, sr, amp, decay=6.0):
    t = np.arange(int(dur * sr)) / sr
    f = _hz(m)
    y = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 3, 5, 7))
    return amp * y * np.minimum(1, t / 0.004) * np.exp(-t * decay)


def _bell(f, sr, amp, dur=0.6):
    t = np.arange(int(dur * sr)) / sr
    y = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 8)
    return amp * y * np.exp(-t * 6) * np.minimum(1, t / 0.002)


def _lp(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


def _boom(sr, rng, amp, dur=1.4, f0=45):
    t = np.arange(int(dur * sr)) / sr
    n = rng.normal(0, 1, len(t))
    y = np.sin(2 * np.pi * np.cumsum(f0 + 120 * np.exp(-t * 12)) / sr) * np.exp(-t * 3)
    y += 0.5 * (n - _lp(n, 3)) * np.exp(-t * 30) + 0.4 * _lp(n, 30) * np.exp(-t * 5) * 3
    return amp * y


def music(sr, seed=0):
    rng = np.random.default_rng(seed + 99)
    n = int(DURATION * sr)
    out = np.zeros((n, 2))

    def put(sig, t0, pan=0.0):
        i = int(t0 * sr)
        if i >= n or len(sig) == 0:
            return
        j = min(n, i + len(sig))
        out[i:j, 0] += sig[: j - i] * math.sqrt(0.5 * (1 - pan))
        out[i:j, 1] += sig[: j - i] * math.sqrt(0.5 * (1 + pan))

    # フリーズ中は無音 → ドンッ!(直前に吸い込むような音)
    t = np.arange(int(0.25 * sr)) / sr
    suck = _lp(rng.normal(0, 1, len(t)), 6) * (t / 0.25) ** 3 * 0.25
    put(suck, T_FREEZE - 0.25)
    put(_boom(sr, rng, 0.55), T_FREEZE)
    # 虹ストロボ: キュインキュイン!
    for j in range(3):
        put(0.30 * _kyuin(sr, 1 + 0.06 * j), T_FREEZE + 0.05 + j * 0.22, pan=(-0.5, 0.5, 0)[j])
    # リール回転: カラカラ(細かいクリック)
    t = T_STROBE
    while t < REEL_STOP[2]:
        speed = 0.04 if t < REEL_STOP[1] else 0.04 + 0.14 * (t - REEL_STOP[1]) / (REEL_STOP[2] - REEL_STOP[1])
        c = np.arange(int(0.012 * sr)) / sr
        put(0.12 * np.sin(2 * np.pi * 2200 * c) * np.exp(-c * 400), t, pan=0.2)
        t += speed
    # 真ん中のじらし: だんだん上がっていく音(ドキドキ)
    t = np.arange(int((REEL_STOP[2] - REEL_STOP[1]) * sr)) / sr
    f = 300 + 900 * (t / t[-1]) ** 2
    rise = np.sin(2 * np.pi * np.cumsum(f) / sr) * (0.4 + 0.6 * (np.sin(2 * np.pi * 8 * t) > 0)) * 0.10
    put(rise, REEL_STOP[1])
    for k, st in enumerate(REEL_STOP[:2]):   # ガコン!
        c = np.arange(int(0.3 * sr)) / sr
        put(0.35 * np.sin(2 * np.pi * (140 + 300 * np.exp(-c * 40)) * c) * np.exp(-c * 18) + _bell(1800, sr, 0.15, 0.3), st,
            pan=(-0.5, 0.5)[k])
    # 揃った!ドカン+キュイン
    put(_boom(sr, rng, 0.7, 1.8, 38), REEL_STOP[2])
    put(0.32 * _kyuin(sr, 1.15), REEL_STOP[2] + 0.02)
    # 大当たり本番: ファンファーレ風の連打(明るい長調でぐんぐん上がる)
    bpm = 160
    s16 = 60 / bpm / 4
    prog = [(60, 64, 67, 72), (65, 69, 72, 77), (67, 71, 74, 79), (72, 76, 79, 84)]
    t = T_BIG
    i = 0
    while t < DURATION - 1.3:
        ch = prog[min(len(prog) - 1, int((t - T_BIG) / (8 * s16)) % len(prog))]
        m = ch[i % 4] + 12 * ((i // 4) % 2)
        put(_sq(m, 0.22, sr, 0.09), t, pan=0.35 * math.sin(i * 1.3))
        if i % 4 == 0:
            put(_sq(ch[0] - 24, 0.35, sr, 0.11, 4), t)
            c = np.arange(int(0.15 * sr)) / sr   # キック
            put(0.35 * np.sin(2 * np.pi * np.cumsum(50 + 100 * np.exp(-c * 30)) / sr) * np.exp(-c * 14), t)
        if i % 8 == 4:   # スネア
            c = np.arange(int(0.15 * sr)) / sr
            nn = rng.normal(0, 1, len(c))
            put(0.18 * (nn - _lp(nn, 4)) * np.exp(-c * 25), t)
        if i % 16 == 0:   # 小節ごとにキュイン
            put(0.22 * _kyuin(sr, 1.0 + 0.1 * ((i // 16) % 3)), t, pan=0.4 * (-1) ** (i // 16))
        t += s16
        i += 1
    # 最後に高い和音でジャーン
    for m in (72, 76, 79, 84, 88, 91):
        put(_sq(m, 1.3, sr, 0.055, 1.8), DURATION - 1.3)
    put(_boom(sr, rng, 0.4, 1.3, 50), DURATION - 1.3)
    # チャリンチャリン(本番中ずっと)
    for _ in range(110):
        put(_bell(rng.uniform(2600, 5600), sr, 0.045), rng.uniform(T_BIG, DURATION - 0.7), pan=rng.uniform(-0.9, 0.9))
    wet = out.copy()
    for d, g in ((0.031, 0.25), (0.057, 0.18), (0.089, 0.12)):
        k = int(d * sr)
        wet[k:, 0] += out[:-k, 1] * g
        wet[k:, 1] += out[:-k, 0] * g
    fade = np.ones(n)
    k = int(0.6 * sr)
    fade[-k:] = np.linspace(1, 0, k)
    return wet * fade[:, None]
