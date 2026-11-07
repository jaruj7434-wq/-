"""刃物6種類の絵(cairo で描く・特定メーカーの刻印やデザインは使わない)。くるくる回転しながら通路を進む。

BALLS[k] = (名前, 予備, 予備, 予備, 予備, 代表の色)  … sports_balls.BALLS と同じ並び(0番=名前、5番=色)
draw_ball(ctx, kind, x, y, ang, r, t, alpha, rng) … 中心 (x, y)・回転 ang で、長さが r に比例する刃物を描く
"""
import math

import cairo

BALLS = [
    ("バターナイフ", 0, 0, 0, 0, (0.8, 0.82, 0.86)),
    ("ペティナイフ", 0, 0, 0, 0, (0.85, 0.88, 0.92)),
    ("三徳包丁", 0, 0, 0, 0, (0.88, 0.9, 0.95)),
    ("出刃包丁", 0, 0, 0, 0, (0.75, 0.78, 0.85)),
    ("中華包丁", 0, 0, 0, 0, (0.7, 0.73, 0.78)),
    ("日本刀", 0, 0, 0, 0, (0.92, 0.95, 1.0)),
]
SHORT = ["バター", "ペティ", "三徳", "出刃", "中華", "日本刀"]
LENGTH = [2.4, 2.6, 3.0, 3.0, 2.9, 4.2]   # 刃物の全長(半径 r の何倍か)


def _steel(ctx, y0, y1, alpha, dark=0.0):
    """刃の金属のグラデーション(背=暗め、刃先=明るく光る)。"""
    g = cairo.LinearGradient(0, y0, 0, y1)
    g.add_color_stop_rgba(0, 0.55 - dark, 0.58 - dark, 0.64 - dark, alpha)
    g.add_color_stop_rgba(0.45, 0.85 - dark, 0.88 - dark, 0.93 - dark, alpha)
    g.add_color_stop_rgba(0.8, 0.98, 0.99, 1.0, alpha)
    g.add_color_stop_rgba(1, 0.7, 0.75, 0.82, alpha)
    ctx.set_source(g)


def _handle(ctx, x0, x1, h, col, alpha, rivets=2):
    ctx.new_path()
    ctx.move_to(x0, -h)
    ctx.line_to(x1, -h * 0.85)
    ctx.curve_to(x1 + h * 0.6, -h * 0.85, x1 + h * 0.6, h * 0.85, x1, h * 0.85)
    ctx.line_to(x0, h)
    ctx.close_path()
    g = cairo.LinearGradient(0, -h, 0, h)
    g.add_color_stop_rgba(0, *(min(1, c * 1.4) for c in col), alpha)
    g.add_color_stop_rgba(0.5, *col, alpha)
    g.add_color_stop_rgba(1, *(c * 0.5 for c in col), alpha)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(0, 0, 0, 0.4 * alpha)
    ctx.set_line_width(max(0.6, h * 0.12))
    ctx.stroke()
    for i in range(rivets):
        rx = x0 + (x1 - x0) * (i + 1) / (rivets + 1)
        ctx.arc(rx, 0, h * 0.22, 0, 2 * math.pi)
        ctx.set_source_rgba(0.85, 0.85, 0.88, alpha)
        ctx.fill()


def _edge(ctx, alpha):
    ctx.set_source_rgba(1, 1, 1, 0.7 * alpha)   # 刃のふちが光る
    ctx.set_line_width(0.9)
    ctx.stroke()


def draw_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    if r <= 0.5 or alpha <= 0.01:
        return
    L = r * LENGTH[kind]          # 全長
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    # 回転しているのが分かる、うっすらした円の残像
    ctx.arc(0, 0, L * 0.5, 0, 2 * math.pi)
    ctx.set_source_rgba(1, 1, 1, 0.06 * alpha)
    ctx.fill()
    ctx.translate(-L * 0.5, 0)    # 柄の端を原点に(左が柄、右が刃先)
    if kind == 0:   # バターナイフ:丸い先・細い刃・明るい木の柄
        hl = L * 0.42
        _handle(ctx, 0, hl, r * 0.2, (0.85, 0.65, 0.4), alpha, 0)
        ctx.new_path()
        ctx.move_to(hl, -r * 0.14)
        ctx.line_to(L - r * 0.25, -r * 0.2)
        ctx.arc(L - r * 0.25, 0, r * 0.2, -math.pi / 2, math.pi / 2)
        ctx.line_to(hl, r * 0.14)
        ctx.close_path()
        _steel(ctx, -r * 0.2, r * 0.2, alpha, 0.1)
        ctx.fill_preserve()
        _edge(ctx, alpha)
    elif kind == 1:   # ペティナイフ:細くとがった刃・黒い柄
        hl = L * 0.4
        _handle(ctx, 0, hl, r * 0.19, (0.12, 0.12, 0.14), alpha)
        ctx.new_path()
        ctx.move_to(hl, -r * 0.22)
        ctx.line_to(L, -r * 0.05)
        ctx.curve_to(L - r * 0.4, r * 0.12, hl + r * 0.5, r * 0.2, hl, r * 0.2)
        ctx.close_path()
        _steel(ctx, -r * 0.22, r * 0.2, alpha)
        ctx.fill_preserve()
        _edge(ctx, alpha)
    elif kind == 2:   # 三徳包丁:幅広・先が下がる形・ダマスカス風の波模様
        hl = L * 0.33
        _handle(ctx, 0, hl, r * 0.22, (0.35, 0.2, 0.1), alpha)
        bw = r * 0.62
        ctx.new_path()
        ctx.move_to(hl, -bw * 0.45)
        ctx.line_to(L - r * 0.5, -bw * 0.45)
        ctx.curve_to(L - r * 0.1, -bw * 0.45, L, -bw * 0.1, L, bw * 0.05)
        ctx.curve_to(L - r * 0.4, bw * 0.45, hl + r * 0.4, bw * 0.55, hl, bw * 0.55)
        ctx.close_path()
        _steel(ctx, -bw * 0.45, bw * 0.55, alpha)
        ctx.fill_preserve()
        ctx.save()
        ctx.clip_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.18 * alpha)
        ctx.set_line_width(max(0.6, r * 0.04))
        for i in range(6):   # 波模様
            ctx.move_to(hl, -bw * 0.4 + i * bw * 0.17)
            ctx.curve_to(hl + (L - hl) * 0.3, -bw * 0.5 + i * bw * 0.17, hl + (L - hl) * 0.6, -bw * 0.3 + i * bw * 0.17, L, -bw * 0.4 + i * bw * 0.17)
        ctx.stroke()
        ctx.restore()
        _edge(ctx, alpha)
    elif kind == 3:   # 出刃包丁:厚い三角の刃・朴の柄に黒い口金
        hl = L * 0.36
        _handle(ctx, 0, hl, r * 0.24, (0.75, 0.62, 0.42), alpha, 0)
        ctx.rectangle(hl - r * 0.25, -r * 0.27, r * 0.25, r * 0.54)
        ctx.set_source_rgba(0.08, 0.08, 0.08, alpha)
        ctx.fill()
        bw = r * 0.7
        ctx.new_path()
        ctx.move_to(hl, -bw * 0.4)
        ctx.line_to(L, -bw * 0.25)
        ctx.curve_to(L - r * 0.6, bw * 0.25, hl + r * 0.6, bw * 0.6, hl, bw * 0.6)
        ctx.close_path()
        _steel(ctx, -bw * 0.4, bw * 0.6, alpha, 0.12)
        ctx.fill_preserve()
        _edge(ctx, alpha)
    elif kind == 4:   # 中華包丁:大きな四角い刃・穴・黒い柄
        hl = L * 0.3
        _handle(ctx, 0, hl, r * 0.22, (0.15, 0.1, 0.08), alpha)
        bw = r * 1.15
        ctx.new_path()
        ctx.move_to(hl, -bw * 0.45)
        ctx.line_to(L, -bw * 0.45)
        ctx.line_to(L, bw * 0.55)
        ctx.line_to(hl, bw * 0.55)
        ctx.close_path()
        _steel(ctx, -bw * 0.45, bw * 0.55, alpha, 0.15)
        ctx.fill_preserve()
        _edge(ctx, alpha)
        ctx.arc(L - r * 0.35, -bw * 0.22, r * 0.12, 0, 2 * math.pi)
        ctx.set_source_rgba(0.02, 0.02, 0.03, alpha)
        ctx.fill()
    else:   # 日本刀:長く反った刃・波紋・つば・巻いた柄
        hl = L * 0.25
        ctx.new_path()   # 柄(ひし形の巻き)
        ctx.rectangle(0, -r * 0.18, hl, r * 0.36)
        ctx.set_source_rgba(0.08, 0.06, 0.08, alpha)
        ctx.fill()
        ctx.set_source_rgba(0.85, 0.75, 0.55, 0.8 * alpha)
        ctx.set_line_width(max(0.6, r * 0.04))
        n = 6
        for i in range(n):
            x0_ = hl * i / n
            ctx.move_to(x0_, -r * 0.18)
            ctx.line_to(x0_ + hl / n, r * 0.18)
            ctx.move_to(x0_, r * 0.18)
            ctx.line_to(x0_ + hl / n, -r * 0.18)
        ctx.stroke()
        ctx.save()   # つば(金色の楕円)
        ctx.translate(hl, 0)
        ctx.scale(0.25, 1.0)
        ctx.arc(0, 0, r * 0.42, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(0.85, 0.68, 0.25, alpha)
        ctx.fill()
        ctx.new_path()   # 反った刃
        ctx.move_to(hl, -r * 0.16)
        ctx.curve_to(hl + (L - hl) * 0.5, -r * 0.22, L - r * 0.4, -r * 0.42, L, -r * 0.55)
        ctx.curve_to(L - r * 0.3, -r * 0.2, hl + (L - hl) * 0.5, r * 0.14, hl, r * 0.14)
        ctx.close_path()
        _steel(ctx, -r * 0.4, r * 0.14, alpha)
        ctx.fill_preserve()
        ctx.save()
        ctx.clip_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.5 * alpha)   # 波紋
        ctx.set_line_width(max(0.6, r * 0.05))
        ctx.move_to(hl, r * 0.05)
        for i in range(1, 13):
            px = hl + (L - hl) * i / 12
            py = r * 0.05 - (r * 0.45) * (i / 12) ** 2 + (r * 0.05 if i % 2 else -r * 0.03)
            ctx.line_to(px, py)
        ctx.stroke()
        ctx.restore()
        _edge(ctx, alpha)
    ctx.restore()
