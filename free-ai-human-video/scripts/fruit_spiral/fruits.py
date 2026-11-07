"""うずまきに並べるフルーツの絵(cairo で描く)と、つぶれたときの果汁の色。

KINDS[k] = (名前, 皮の色, 果汁の色)
draw_fruit(ctx, kind, x, y, r, rot) … 半径 r くらいのフルーツを1個描く
"""
import math

import cairo

KINDS = [
    ("りんご", (0.85, 0.08, 0.12), (1.0, 0.92, 0.75)),
    ("オレンジ", (1.0, 0.55, 0.05), (1.0, 0.65, 0.1)),
    ("レモン", (1.0, 0.9, 0.15), (1.0, 0.95, 0.4)),
    ("いちご", (0.92, 0.1, 0.2), (1.0, 0.2, 0.3)),
    ("ぶどう", (0.45, 0.15, 0.6), (0.6, 0.2, 0.7)),
    ("もも", (1.0, 0.65, 0.6), (1.0, 0.85, 0.7)),
    ("キウイ", (0.55, 0.4, 0.22), (0.45, 0.8, 0.2)),
    ("スイカ", (0.15, 0.55, 0.2), (1.0, 0.2, 0.25)),
]


def _ball(ctx, x, y, rx, ry, col, hi=0.35):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(rx, ry)
    g = cairo.RadialGradient(-0.35, -0.4, 0.05, 0, 0, 1.05)
    g.add_color_stop_rgb(0, *(min(1, c * 1.15 + hi) for c in col))
    g.add_color_stop_rgb(0.6, *col)
    g.add_color_stop_rgb(1, *(c * 0.5 for c in col))
    ctx.set_source(g)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


def _leaf(ctx, x, y, s, ang, col=(0.2, 0.65, 0.2)):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.move_to(0, 0)
    ctx.curve_to(s * 0.4, -s * 0.5, s * 0.9, -s * 0.3, s, 0)
    ctx.curve_to(s * 0.9, s * 0.3, s * 0.4, s * 0.4, 0, 0)
    ctx.set_source_rgb(*col)
    ctx.fill()
    ctx.restore()


def draw_fruit(ctx, kind, x, y, r, rot=0.0):
    name, skin, juice = KINDS[kind]
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    if kind == 0:   # りんご
        _ball(ctx, 0, 0, r, r * 0.92, skin)
        ctx.set_source_rgb(0.35, 0.22, 0.1)
        ctx.set_line_width(max(1, r * 0.1))
        ctx.move_to(0, -r * 0.7)
        ctx.line_to(r * 0.08, -r * 1.05)
        ctx.stroke()
        _leaf(ctx, r * 0.08, -r * 0.95, r * 0.5, -0.5)
    elif kind == 1:   # オレンジ(つぶつぶの皮)
        _ball(ctx, 0, 0, r, r, skin, 0.25)
        ctx.set_source_rgba(0.8, 0.4, 0.0, 0.35)
        for i in range(10):
            a = i * 2.4
            rr = r * 0.6 * ((i * 0.37) % 1)
            ctx.arc(rr * math.cos(a), rr * math.sin(a), r * 0.05, 0, 2 * math.pi)
            ctx.fill()
        _leaf(ctx, 0, -r * 0.9, r * 0.35, -1.2)
    elif kind == 2:   # レモン(両はしがとがった楕円)
        _ball(ctx, 0, 0, r * 1.08, r * 0.8, skin, 0.3)
        ctx.set_source_rgb(*(c * 0.85 for c in skin))
        for sgn in (-1, 1):
            ctx.arc(sgn * r * 1.05, 0, r * 0.14, 0, 2 * math.pi)
            ctx.fill()
    elif kind == 3:   # いちご(三角に近い形+種+へた)
        ctx.move_to(0, r * 1.0)
        ctx.curve_to(-r * 1.1, r * 0.2, -r * 0.9, -r * 0.8, 0, -r * 0.75)
        ctx.curve_to(r * 0.9, -r * 0.8, r * 1.1, r * 0.2, 0, r * 1.0)
        g = cairo.RadialGradient(-r * 0.3, -r * 0.3, r * 0.05, 0, 0, r * 1.1)
        g.add_color_stop_rgb(0, 1, 0.45, 0.45)
        g.add_color_stop_rgb(0.6, *skin)
        g.add_color_stop_rgb(1, 0.5, 0.02, 0.08)
        ctx.set_source(g)
        ctx.fill()
        ctx.set_source_rgb(1, 0.9, 0.4)
        for i in range(9):
            sx = (-0.45 + 0.45 * (i % 3)) * r
            sy = (-0.3 + 0.35 * (i // 3)) * r
            ctx.arc(sx, sy, r * 0.05, 0, 2 * math.pi)
            ctx.fill()
        for a in (-2.2, -1.57, -0.9):
            _leaf(ctx, 0, -r * 0.72, r * 0.45, a)
    elif kind == 4:   # ぶどう(小さな粒の房)
        pos = [(0, -0.55), (-0.45, -0.35), (0.45, -0.35), (-0.25, 0.05), (0.25, 0.05), (0, 0.45), (-0.55, 0.15), (0.55, 0.15)]
        for px, py in pos:
            _ball(ctx, px * r, py * r, r * 0.36, r * 0.36, skin, 0.35)
        ctx.set_source_rgb(0.35, 0.25, 0.1)
        ctx.set_line_width(max(1, r * 0.08))
        ctx.move_to(0, -r * 0.85)
        ctx.line_to(0, -r * 1.1)
        ctx.stroke()
    elif kind == 5:   # もも(うすいピンク+ほんのり赤+まんなかの線)
        _ball(ctx, 0, 0, r, r * 0.95, skin, 0.25)
        g = cairo.RadialGradient(r * 0.25, -r * 0.1, 0, r * 0.25, -r * 0.1, r * 0.7)
        g.add_color_stop_rgba(0, 0.95, 0.25, 0.3, 0.55)
        g.add_color_stop_rgba(1, 0.95, 0.25, 0.3, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgba(0.75, 0.35, 0.35, 0.6)
        ctx.set_line_width(max(1, r * 0.06))
        ctx.move_to(0, -r * 0.9)
        ctx.curve_to(-r * 0.3, -r * 0.3, -r * 0.2, r * 0.4, 0, r * 0.9)
        ctx.stroke()
        _leaf(ctx, 0, -r * 0.9, r * 0.45, -0.7)
    elif kind == 6:   # キウイ(切った面:緑の果肉+黒い種+白い芯)
        ctx.set_source_rgb(*skin)
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.fill()
        g = cairo.RadialGradient(0, 0, r * 0.1, 0, 0, r * 0.88)
        g.add_color_stop_rgb(0, 0.95, 0.98, 0.8)
        g.add_color_stop_rgb(0.35, 0.55, 0.85, 0.2)
        g.add_color_stop_rgb(1, 0.35, 0.65, 0.12)
        ctx.set_source(g)
        ctx.arc(0, 0, r * 0.88, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(0.08, 0.06, 0.04)
        for i in range(14):
            a = i * 2 * math.pi / 14
            ctx.arc(r * 0.42 * math.cos(a), r * 0.42 * math.sin(a), r * 0.05, 0, 2 * math.pi)
            ctx.fill()
    else:   # スイカ(緑に濃いしま模様)
        _ball(ctx, 0, 0, r * 1.05, r, skin, 0.2)
        ctx.save()
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.clip()
        ctx.set_source_rgba(0.03, 0.25, 0.06, 0.8)
        ctx.set_line_width(max(1, r * 0.14))
        for i in range(-2, 3):
            ctx.move_to(i * r * 0.42, -r)
            ctx.curve_to(i * r * 0.42 + r * 0.15, -r * 0.3, i * r * 0.42 - r * 0.15, r * 0.3, i * r * 0.42, r)
            ctx.stroke()
        ctx.restore()
    ctx.restore()
