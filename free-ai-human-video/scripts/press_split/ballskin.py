"""つやつやのカラーボールの絵。成功演出(fruit_fever と同じ形の関数)でも使う。"""
import colorsys
import math

import cairo

N_COLORS = 10


def color(k):
    """k 番目の色(虹色をぐるっと回る)。"""
    return colorsys.hsv_to_rgb((k * 0.1) % 1.0, 0.75, 1.0)


KINDS = [("ball", color(k), color(k), 0.5) for k in range(N_COLORS)]


def draw_ball(ctx, x, y, r, col, alpha=1.0):
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.05, x, y, r * 1.05)
    g.add_color_stop_rgba(0, *(min(1, c * 0.5 + 0.6) for c in col), alpha)
    g.add_color_stop_rgba(0.55, *col, alpha)
    g.add_color_stop_rgba(1, *(c * 0.4 for c in col), alpha)
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.45, 0, x - r * 0.35, y - r * 0.45, r * 0.45)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.85 * alpha)
    g.add_color_stop_rgba(1, 1, 1, 1, 0)
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()


def draw_fruit(ctx, kind, x, y, r, rot=0.0):
    draw_ball(ctx, x, y, r, color(kind))


def draw_cut(ctx, kind, r):
    draw_ball(ctx, 0, 0, r, color(kind))
