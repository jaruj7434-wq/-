"""小石 → 岩 → 隕石 → 月 → 地球 → 木星 → 太陽 の絵(cairo で描く・無料)。

draw_stage(ctx, st, x, y, ang, r, poly=None) … 段階 st を中心 (x, y)・回転 ang・半径 r で描く
                                              (小石と岩は poly(重心が原点の多角形)があればその形で描く)
KINDS / draw_fruit / draw_cut は、成功演出(fruit_fever と同じ作り)で使うための同じ形の関数。
"""
import math

import cairo
import numpy as np

NAMES = ["小石", "岩", "隕石", "月", "地球", "木星", "太陽"]
COLORS = [(0.62, 0.6, 0.57), (0.55, 0.45, 0.35), (0.35, 0.22, 0.15), (0.78, 0.78, 0.76),
          (0.2, 0.45, 0.9), (0.85, 0.7, 0.5), (1.0, 0.7, 0.15)]


def rock_poly(rng, r, n=8):
    """ごつごつした石の形(凸多角形・重心が原点)。"""
    angs = np.sort(rng.uniform(0, 2 * math.pi, n))
    pts = [(r * rng.uniform(0.78, 1.05) * math.cos(a), r * rng.uniform(0.7, 1.0) * math.sin(a)) for a in angs]
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n
    return [(x - cx, y - cy) for x, y in pts]


def _poly_path(ctx, poly):
    ctx.new_path()
    ctx.move_to(*poly[0])
    for p in poly[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def _sphere(ctx, r, col, hi=0.25, lo=0.35):
    g = cairo.RadialGradient(-r * 0.35, -r * 0.4, r * 0.05, 0, 0, r * 1.05)
    g.add_color_stop_rgb(0, *(min(1, c * 1.1 + hi) for c in col))
    g.add_color_stop_rgb(0.6, *col)
    g.add_color_stop_rgb(1, *(c * lo for c in col))
    ctx.set_source(g)
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.fill()


def _shadow(ctx, r, k=0.55):
    """球の右下を暗くする(光は左上から)。回転させずに上からかぶせる。"""
    g = cairo.RadialGradient(-r * 0.4, -r * 0.45, r * 0.2, -r * 0.1, -r * 0.1, r * 1.25)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(0.6, 0, 0, 0, 0.1 * k)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.85 * k)
    ctx.set_source(g)
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.fill()


def draw_stage(ctx, st, x, y, ang, r, poly=None, t=0.0, alpha=1.0):
    ctx.save()
    ctx.translate(x, y)
    if st <= 1:   # 小石・岩(多角形・ざらざらの点)
        if poly is None:
            poly = rock_poly(np.random.default_rng(st + 3), r)
        ctx.save()
        ctx.rotate(ang)
        _poly_path(ctx, poly)
        col = COLORS[st]
        g = cairo.LinearGradient(-r, -r, r, r)
        g.add_color_stop_rgb(0, *(min(1, c * 1.35) for c in col))
        g.add_color_stop_rgb(0.5, *col)
        g.add_color_stop_rgb(1, *(c * 0.45 for c in col))
        ctx.set_source(g)
        ctx.fill_preserve()
        ctx.save()
        ctx.clip_preserve()
        rng = np.random.default_rng(st * 7 + 1)
        for _ in range(int(14 + 10 * st)):   # ざらざら・くぼみ
            px, py = rng.uniform(-r, r), rng.uniform(-r, r)
            ctx.arc(px, py, r * rng.uniform(0.04, 0.12), 0, 2 * math.pi)
            ctx.set_source_rgba(0, 0, 0, rng.uniform(0.1, 0.3))
            ctx.fill()
        if st == 1:   # 岩のひび
            ctx.set_source_rgba(0.1, 0.07, 0.05, 0.6)
            ctx.set_line_width(max(1, r * 0.05))
            ctx.move_to(-r * 0.5, -r * 0.2)
            ctx.line_to(-r * 0.1, r * 0.05)
            ctx.line_to(r * 0.3, -r * 0.1)
            ctx.move_to(-r * 0.1, r * 0.05)
            ctx.line_to(r * 0.05, r * 0.5)
            ctx.stroke()
        ctx.restore()
        ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.set_line_width(max(1, r * 0.05))
        ctx.stroke()
        ctx.restore()
    elif st == 2:   # 隕石(黒っぽい岩+光る溶岩のひび+熱のかがやき)
        g = cairo.RadialGradient(0, 0, r * 0.8, 0, 0, r * 1.6)
        g.add_color_stop_rgba(0, 1, 0.4, 0.05, 0.5)
        g.add_color_stop_rgba(1, 1, 0.2, 0, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, r * 1.6, 0, 2 * math.pi)
        ctx.fill()
        ctx.save()
        ctx.rotate(ang)
        _sphere(ctx, r, COLORS[2], 0.08, 0.3)
        ctx.set_source_rgba(1, 0.55, 0.1, 0.95)
        ctx.set_line_width(max(1, r * 0.07))
        rng = np.random.default_rng(11)
        for _ in range(5):
            a = rng.uniform(0, 2 * math.pi)
            ctx.move_to(r * 0.1 * math.cos(a), r * 0.1 * math.sin(a))
            for k in range(1, 4):
                aa = a + rng.uniform(-0.5, 0.5)
                ctx.line_to(r * 0.28 * k * math.cos(aa), r * 0.28 * k * math.sin(aa))
            ctx.stroke()
        ctx.restore()
        _shadow(ctx, r, 0.4)
    elif st == 3:   # 月(灰色+クレーター)
        ctx.save()
        ctx.rotate(ang)
        _sphere(ctx, r, COLORS[3], 0.15, 0.6)
        rng = np.random.default_rng(5)
        for _ in range(11):
            a = rng.uniform(0, 2 * math.pi)
            d = r * math.sqrt(rng.uniform(0, 0.75))
            cr = r * rng.uniform(0.07, 0.2)
            cx_, cy_ = d * math.cos(a), d * math.sin(a)
            ctx.arc(cx_, cy_, cr, 0, 2 * math.pi)
            ctx.set_source_rgba(0.45, 0.45, 0.45, 0.55)
            ctx.fill()
            ctx.arc(cx_ - cr * 0.15, cy_ - cr * 0.15, cr * 0.8, 0, 2 * math.pi)
            ctx.set_source_rgba(0.62, 0.62, 0.6, 0.6)
            ctx.fill()
        ctx.restore()
        _shadow(ctx, r)
    elif st == 4:   # 地球(青い海+緑の陸+白い雲)
        ctx.save()
        ctx.rotate(ang)
        _sphere(ctx, r, COLORS[4], 0.2, 0.5)
        ctx.save()
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.clip()
        rng = np.random.default_rng(9)
        for _ in range(5):   # 大陸(どの国の形にも似せない、ぼんやりした形)
            cx_, cy_ = rng.uniform(-r * 0.7, r * 0.7), rng.uniform(-r * 0.7, r * 0.7)
            ctx.new_path()
            n = 9
            for k in range(n):
                a = k * 2 * math.pi / n
                rr = r * rng.uniform(0.15, 0.35)
                ctx.line_to(cx_ + rr * math.cos(a), cy_ + rr * math.sin(a) * 0.8)
            ctx.close_path()
            ctx.set_source_rgb(0.25, 0.6, 0.25)
            ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.75)
        ctx.set_line_width(max(1, r * 0.08))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for k in range(5):   # 雲のすじ
            y0 = -r * 0.7 + k * r * 0.35
            ctx.move_to(-r * 0.8 + rng.uniform(0, r * 0.3), y0)
            ctx.curve_to(-r * 0.2, y0 - r * 0.1, r * 0.2, y0 + r * 0.1, r * 0.6 + rng.uniform(0, r * 0.2), y0)
            ctx.stroke()
        ctx.restore()
        ctx.restore()
        _shadow(ctx, r, 0.6)
        g = cairo.RadialGradient(0, 0, r * 0.95, 0, 0, r * 1.12)   # 大気のうす青いふち
        g.add_color_stop_rgba(0, 0.4, 0.7, 1, 0.45)
        g.add_color_stop_rgba(1, 0.4, 0.7, 1, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, r * 1.12, 0, 2 * math.pi)
        ctx.fill()
    elif st == 5:   # 木星(しま模様+大赤斑)
        ctx.save()
        ctx.rotate(ang * 0.3)
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.clip()
        bands = [(0.92, 0.85, 0.72), (0.75, 0.55, 0.38), (0.95, 0.88, 0.75), (0.68, 0.45, 0.3),
                 (0.9, 0.8, 0.65), (0.78, 0.6, 0.42), (0.93, 0.86, 0.72), (0.7, 0.5, 0.35)]
        for k, c in enumerate(bands):
            y0 = -r + k * 2 * r / len(bands)
            ctx.rectangle(-r, y0, 2 * r, 2 * r / len(bands) + 1)
            ctx.set_source_rgb(*c)
            ctx.fill()
        ctx.save()
        ctx.translate(r * 0.3, r * 0.3)
        ctx.scale(1.0, 0.6)
        ctx.arc(0, 0, r * 0.2, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(0.75, 0.3, 0.2)
        ctx.fill()
        ctx.restore()
        _shadow(ctx, r, 0.6)
    else:   # 太陽(光る+コロナがゆらめく)
        for k, (rr, a) in enumerate(((2.2, 0.15), (1.6, 0.3), (1.25, 0.55))):
            g = cairo.RadialGradient(0, 0, r * 0.9, 0, 0, r * rr * (1 + 0.04 * math.sin(t * 5 + k)))
            g.add_color_stop_rgba(0, 1, 0.75, 0.2, a)
            g.add_color_stop_rgba(1, 1, 0.5, 0.0, 0)
            ctx.set_source(g)
            ctx.arc(0, 0, r * rr * 1.05, 0, 2 * math.pi)
            ctx.fill()
        g = cairo.RadialGradient(-r * 0.2, -r * 0.2, r * 0.1, 0, 0, r)
        g.add_color_stop_rgb(0, 1, 1, 0.85)
        g.add_color_stop_rgb(0.5, 1, 0.82, 0.3)
        g.add_color_stop_rgb(1, 1, 0.5, 0.05)
        ctx.set_source(g)
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.fill()
        ctx.save()
        ctx.rotate(ang * 0.2)
        rng = np.random.default_rng(2)
        for _ in range(16):   # 表面のつぶつぶ(粒状斑)
            a = rng.uniform(0, 2 * math.pi)
            d = r * math.sqrt(rng.uniform(0, 0.8))
            ctx.arc(d * math.cos(a), d * math.sin(a), r * rng.uniform(0.05, 0.12), 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.6, 0.1, 0.35)
            ctx.fill()
        ctx.restore()
    ctx.restore()


# ---- 成功演出(fruit_fever と同じ形)で使う関数
KINDS = [(n, c, c, 0.5) for n, c in zip(NAMES, COLORS)]


def draw_fruit(ctx, kind, x, y, r, rot=0.0):
    draw_stage(ctx, kind, x, y, rot, r)


def draw_cut(ctx, kind, r):
    draw_stage(ctx, kind, 0, 0, 0.0, r)
