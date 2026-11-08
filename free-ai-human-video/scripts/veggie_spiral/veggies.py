"""うずまきに並べる野菜の絵と、切ったときの断面(輪切り)の絵。fruits.py と同じ形の関数をそろえる。

KINDS[k] = (名前, 皮の色, 断面のしぶきの色, 音のかたさ 0=やわらかい〜1=かたい)
draw_fruit(ctx, kind, x, y, r, rot) … 野菜を1個描く(長い野菜は rot の向きに寝かせる)
draw_cut(ctx, kind, r)             … 原点を中心に、半径 r の断面(輪切り)を描く
"""
import math

import cairo

KINDS = [
    ("きゅうり", (0.15, 0.45, 0.12), (0.75, 0.92, 0.6), 0.9),
    ("にんじん", (1.0, 0.45, 0.05), (1.0, 0.6, 0.2), 1.0),
    ("トマト", (0.9, 0.1, 0.08), (1.0, 0.3, 0.25), 0.2),
    ("ナス", (0.32, 0.12, 0.38), (0.95, 0.92, 0.78), 0.5),
    ("玉ねぎ", (0.78, 0.52, 0.2), (0.97, 0.95, 0.9), 0.8),
    ("ピーマン", (0.15, 0.6, 0.15), (0.6, 0.85, 0.4), 0.7),
    ("大根", (0.96, 0.96, 0.92), (0.98, 0.98, 0.94), 0.95),
    ("キャベツ", (0.55, 0.8, 0.35), (0.85, 0.95, 0.7), 0.85),
]


def _grad(ctx, x, y, r, col, hi=0.3):
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.05, x, y, r * 1.05)
    g.add_color_stop_rgb(0, *(min(1, c * 1.15 + hi) for c in col))
    g.add_color_stop_rgb(0.6, *col)
    g.add_color_stop_rgb(1, *(c * 0.5 for c in col))
    return g


def _leafy(ctx, x, y, s, ang, col=(0.25, 0.6, 0.2)):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    for a in (-0.5, 0, 0.5):
        ctx.save()
        ctx.rotate(a)
        ctx.move_to(0, 0)
        ctx.curve_to(s * 0.3, -s * 0.15, s * 0.8, -s * 0.12, s, 0)
        ctx.curve_to(s * 0.8, s * 0.12, s * 0.3, s * 0.15, 0, 0)
        ctx.set_source_rgb(*col)
        ctx.fill()
        ctx.restore()
    ctx.restore()


def draw_fruit(ctx, kind, x, y, r, rot=0.0):
    name, skin, juice, _ = KINDS[kind]
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    if kind == 0:   # きゅうり(細長い・つぶつぶ)
        ctx.save()
        ctx.scale(1.35, 0.55)
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.restore()
        g = cairo.LinearGradient(0, -r * 0.55, 0, r * 0.55)
        g.add_color_stop_rgb(0, 0.35, 0.65, 0.3)
        g.add_color_stop_rgb(0.5, *skin)
        g.add_color_stop_rgb(1, 0.05, 0.2, 0.05)
        ctx.set_source(g)
        ctx.fill()
        ctx.set_source_rgba(0.85, 0.95, 0.7, 0.6)
        for i in range(9):
            ctx.arc(-r * 1.1 + i * r * 0.28, (-0.2 if i % 2 else 0.15) * r, r * 0.04, 0, 2 * math.pi)
            ctx.fill()
    elif kind == 1:   # にんじん(先細りの円すい+葉)
        ctx.move_to(-r * 1.2, -r * 0.42)
        ctx.curve_to(-r * 0.2, -r * 0.4, r * 0.8, -r * 0.15, r * 1.3, 0)
        ctx.curve_to(r * 0.8, r * 0.15, -r * 0.2, r * 0.4, -r * 1.2, r * 0.42)
        ctx.close_path()
        g = cairo.LinearGradient(0, -r * 0.42, 0, r * 0.42)
        g.add_color_stop_rgb(0, 1, 0.7, 0.35)
        g.add_color_stop_rgb(0.5, *skin)
        g.add_color_stop_rgb(1, 0.6, 0.22, 0.0)
        ctx.set_source(g)
        ctx.fill()
        ctx.set_source_rgba(0.6, 0.25, 0.0, 0.5)
        ctx.set_line_width(max(0.6, r * 0.04))
        for i in range(4):
            px = -r * 0.7 + i * r * 0.45
            ctx.move_to(px, -r * 0.25)
            ctx.line_to(px + r * 0.05, -r * 0.05)
        ctx.stroke()
        _leafy(ctx, -r * 1.2, 0, r * 0.7, math.pi)
    elif kind == 2:   # トマト(丸・緑のへた)
        ctx.set_source(_grad(ctx, 0, 0, r, skin))
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(0.2, 0.5, 0.15)
        for i in range(5):
            a = i * 2 * math.pi / 5
            ctx.save()
            ctx.rotate(a)
            ctx.move_to(0, 0)
            ctx.curve_to(r * 0.15, -r * 0.1, r * 0.4, -r * 0.05, r * 0.45, 0)
            ctx.curve_to(r * 0.4, r * 0.05, r * 0.15, r * 0.1, 0, 0)
            ctx.fill()
            ctx.restore()
    elif kind == 3:   # ナス(しずく形・つやのある紫・緑のへた)
        ctx.save()
        ctx.move_to(r * 1.2, 0)
        ctx.curve_to(r * 1.2, -r * 0.75, -r * 0.6, -r * 0.6, -r * 0.9, -r * 0.25)
        ctx.curve_to(-r * 1.1, 0, -r * 1.1, 0, -r * 0.9, r * 0.25)
        ctx.curve_to(-r * 0.6, r * 0.6, r * 1.2, r * 0.75, r * 1.2, 0)
        g = cairo.LinearGradient(0, -r * 0.7, 0, r * 0.7)
        g.add_color_stop_rgb(0, 0.6, 0.35, 0.65)
        g.add_color_stop_rgb(0.3, *skin)
        g.add_color_stop_rgb(1, 0.1, 0.02, 0.12)
        ctx.set_source(g)
        ctx.fill()
        ctx.restore()
        ctx.move_to(-r * 1.25, 0)
        for a in (-0.6, 0.0, 0.6):
            ctx.move_to(-r * 0.8, 0)
            ctx.line_to(-r * 0.55 + r * 0.1, a * r * 0.6)
        ctx.set_source_rgb(0.2, 0.42, 0.15)
        ctx.set_line_width(max(1, r * 0.18))
        ctx.stroke()
        ctx.move_to(-r * 0.85, 0)
        ctx.line_to(-r * 1.3, 0)
        ctx.set_line_width(max(1, r * 0.12))
        ctx.stroke()
        ctx.arc(r * 0.4, -r * 0.3, r * 0.15, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.35)
        ctx.fill()
    elif kind == 4:   # 玉ねぎ(金茶色の丸・すじ)
        ctx.set_source(_grad(ctx, 0, 0, r, skin, 0.25))
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgba(0.5, 0.3, 0.08, 0.5)
        ctx.set_line_width(max(0.6, r * 0.04))
        for a in (-0.6, -0.25, 0.1, 0.45):
            ctx.save()
            ctx.scale(1.0, 1.0)
            ctx.arc(0, 0, r * 0.95, math.pi * 1.2 + a, math.pi * 1.8 + a)
            ctx.restore()
            ctx.stroke()
        ctx.set_source_rgb(0.6, 0.4, 0.15)
        ctx.arc(0, 0, r * 0.15, 0, 2 * math.pi)
        ctx.fill()
    elif kind == 5:   # ピーマン(でこぼこの丸・へた)
        for i in range(4):
            a = i * math.pi / 2 + 0.3
            ctx.set_source(_grad(ctx, r * 0.25 * math.cos(a), r * 0.25 * math.sin(a), r * 0.8, skin, 0.35))
            ctx.arc(r * 0.25 * math.cos(a), r * 0.25 * math.sin(a), r * 0.75, 0, 2 * math.pi)
            ctx.fill()
        ctx.set_source_rgb(0.25, 0.4, 0.12)
        ctx.arc(0, 0, r * 0.2, 0, 2 * math.pi)
        ctx.fill()
    elif kind == 6:   # 大根(白く太い・上が緑)
        ctx.save()
        ctx.scale(1.4, 0.55)
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.restore()
        g = cairo.LinearGradient(-r * 1.4, 0, r * 1.4, 0)
        g.add_color_stop_rgb(0, 0.55, 0.78, 0.4)
        g.add_color_stop_rgb(0.3, 0.92, 0.95, 0.88)
        g.add_color_stop_rgb(1, 0.98, 0.98, 0.96)
        ctx.set_source(g)
        ctx.fill()
        _leafy(ctx, -r * 1.35, 0, r * 0.7, math.pi, (0.2, 0.55, 0.18))
    else:   # キャベツ(重なった葉)
        ctx.set_source(_grad(ctx, 0, 0, r, skin, 0.25))
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgba(0.9, 1.0, 0.8, 0.6)
        ctx.set_line_width(max(0.6, r * 0.05))
        for i in range(5):
            a = i * 1.3
            ctx.arc(r * 0.2 * math.cos(a), r * 0.2 * math.sin(a), r * (0.45 + 0.1 * i), a, a + 2.2)
            ctx.stroke()
    ctx.restore()


def draw_cut(ctx, kind, r):
    """断面(輪切り)。原点中心・半径 r。"""
    name, skin, juice, _ = KINDS[kind]
    ctx.save()
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source_rgb(*skin)   # 皮
    ctx.fill()
    if kind == 0:   # きゅうり:うす緑+種の輪
        ctx.arc(0, 0, r * 0.88, 0, 2 * math.pi)
        ctx.set_source_rgb(0.8, 0.93, 0.65)
        ctx.fill()
        ctx.arc(0, 0, r * 0.5, 0, 2 * math.pi)
        ctx.set_source_rgb(0.9, 0.97, 0.8)
        ctx.fill()
        ctx.set_source_rgb(0.95, 0.98, 0.88)
        for i in range(3):
            a = i * 2 * math.pi / 3
            for j in range(3):
                b = a + (j - 1) * 0.35
                ctx.arc(r * 0.33 * math.cos(b), r * 0.33 * math.sin(b), r * 0.07, 0, 2 * math.pi)
                ctx.fill()
    elif kind == 1:   # にんじん:オレンジ+明るい芯
        ctx.arc(0, 0, r * 0.9, 0, 2 * math.pi)
        ctx.set_source_rgb(1, 0.52, 0.1)
        ctx.fill()
        ctx.arc(0, 0, r * 0.45, 0, 2 * math.pi)
        ctx.set_source_rgb(1, 0.68, 0.3)
        ctx.fill()
    elif kind == 2:   # トマト:果肉+ゼリー状の種の部屋
        ctx.arc(0, 0, r * 0.88, 0, 2 * math.pi)
        ctx.set_source_rgb(0.95, 0.25, 0.2)
        ctx.fill()
        for i in range(4):
            a = i * math.pi / 2 + 0.4
            ctx.save()
            ctx.translate(r * 0.45 * math.cos(a), r * 0.45 * math.sin(a))
            ctx.rotate(a)
            ctx.scale(1.0, 0.65)
            ctx.arc(0, 0, r * 0.3, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgb(1, 0.55, 0.35)
            ctx.fill()
            ctx.set_source_rgb(1, 0.9, 0.55)
            for j in range(3):
                ctx.arc(r * 0.45 * math.cos(a) + r * 0.08 * (j - 1) * math.cos(a + 1.57),
                        r * 0.45 * math.sin(a) + r * 0.08 * (j - 1) * math.sin(a + 1.57), r * 0.05, 0, 2 * math.pi)
                ctx.fill()
    elif kind == 3:   # ナス:クリーム色+茶色の種の点
        ctx.arc(0, 0, r * 0.92, 0, 2 * math.pi)
        ctx.set_source_rgb(0.96, 0.93, 0.78)
        ctx.fill()
        ctx.set_source_rgb(0.6, 0.5, 0.3)
        for i in range(12):
            a = i * 0.9
            rr = r * (0.2 + 0.35 * ((i * 0.37) % 1))
            ctx.arc(rr * math.cos(a), rr * math.sin(a), r * 0.04, 0, 2 * math.pi)
            ctx.fill()
    elif kind == 4:   # 玉ねぎ:同心円の層
        for i in range(6):
            ctx.arc(0, 0, r * (0.92 - i * 0.15), 0, 2 * math.pi)
            ctx.set_source_rgb(0.97 - 0.03 * (i % 2), 0.96 - 0.04 * (i % 2), 0.9 - 0.05 * (i % 2))
            ctx.fill_preserve()
            ctx.set_source_rgba(0.85, 0.78, 0.6, 0.6)
            ctx.set_line_width(max(0.5, r * 0.025))
            ctx.stroke()
    elif kind == 5:   # ピーマン:中が空洞+白いわたと種
        ctx.arc(0, 0, r * 0.82, 0, 2 * math.pi)
        ctx.set_source_rgb(0.65, 0.88, 0.45)
        ctx.fill()
        ctx.arc(0, 0, r * 0.68, 0, 2 * math.pi)
        ctx.set_source_rgb(0.08, 0.12, 0.06)
        ctx.fill()
        ctx.set_source_rgb(0.95, 0.93, 0.8)
        for i in range(7):
            a = i * 0.9
            ctx.arc(r * 0.22 * math.cos(a), r * 0.22 * math.sin(a), r * 0.07, 0, 2 * math.pi)
            ctx.fill()
    elif kind == 6:   # 大根:半透明の白+放射状のすじ
        ctx.arc(0, 0, r * 0.94, 0, 2 * math.pi)
        ctx.set_source_rgb(0.97, 0.98, 0.95)
        ctx.fill()
        ctx.set_source_rgba(0.85, 0.88, 0.8, 0.7)
        ctx.set_line_width(max(0.5, r * 0.02))
        for i in range(16):
            a = i * 2 * math.pi / 16
            ctx.move_to(r * 0.15 * math.cos(a), r * 0.15 * math.sin(a))
            ctx.line_to(r * 0.85 * math.cos(a), r * 0.85 * math.sin(a))
        ctx.stroke()
    else:   # キャベツ:波打つ葉の層
        ctx.arc(0, 0, r * 0.92, 0, 2 * math.pi)
        ctx.set_source_rgb(0.88, 0.96, 0.75)
        ctx.fill()
        ctx.set_source_rgba(0.55, 0.78, 0.4, 0.9)
        ctx.set_line_width(max(0.6, r * 0.05))
        for i in range(5):
            rr = r * (0.2 + 0.15 * i)
            ctx.new_path()
            for k in range(41):
                a = k * 2 * math.pi / 40
                w = rr + r * 0.04 * math.sin(a * 7 + i)
                ctx.line_to(w * math.cos(a), w * math.sin(a))
            ctx.close_path()
            ctx.stroke()
    ctx.arc(-r * 0.3, -r * 0.35, r * 0.25, 0, 2 * math.pi)   # みずみずしいつや
    ctx.set_source_rgba(1, 1, 1, 0.18)
    ctx.fill()
    ctx.restore()
