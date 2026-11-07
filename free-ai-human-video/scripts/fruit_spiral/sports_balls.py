"""スポーツボール6種類の絵(すべて cairo で描く、特定のメーカーのロゴやデザインは使わない)。

BALLS[k] = (名前, 予備, 予備, 予備, 予備, 代表の色)  … glass_drum.BALLS と同じ並び(0番=名前、5番=色)
draw_ball(ctx, kind, x, y, ang, r, t, alpha, rng) … 回転 ang つきで半径 r のボールを描く
"""
import math

import cairo

BALLS = [
    ("ピンポン玉", 0, 0, 0, 0, (1.0, 0.62, 0.25)),
    ("テニスボール", 0, 0, 0, 0, (0.85, 0.95, 0.25)),
    ("野球ボール", 0, 0, 0, 0, (0.96, 0.95, 0.9)),
    ("サッカーボール", 0, 0, 0, 0, (0.95, 0.95, 0.95)),
    ("ボウリング球", 0, 0, 0, 0, (0.35, 0.25, 0.85)),
    ("鉄球", 0, 0, 0, 0, (0.62, 0.65, 0.7)),
]


def _shade(ctx, x, y, r, base, alpha, gloss=0.5):
    """球らしく見える陰影(左上が明るく、右下が暗い)。"""
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.05, x, y, r * 1.05)
    hi = tuple(min(1.0, c * 1.12 + 0.12) for c in base)
    lo = tuple(c * 0.45 for c in base)
    g.add_color_stop_rgba(0, *hi, alpha)
    g.add_color_stop_rgba(0.55, *base, alpha)
    g.add_color_stop_rgba(1, *lo, alpha)
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()


def _gloss(ctx, x, y, r, alpha, k=0.6):
    g = cairo.RadialGradient(x - r * 0.38, y - r * 0.42, 0, x - r * 0.38, y - r * 0.42, r * 0.45)
    g.add_color_stop_rgba(0, 1, 1, 1, k * alpha)
    g.add_color_stop_rgba(1, 1, 1, 1, 0)
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()


def _outline(ctx, x, y, r, alpha):
    ctx.set_source_rgba(0, 0, 0, 0.35 * alpha)
    ctx.set_line_width(max(1.0, r * 0.06))
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.stroke()


def draw_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    if r <= 0.5 or alpha <= 0.01:
        return
    ctx.save()
    ctx.new_path()
    if kind == 0:   # ピンポン玉(オレンジ・つるっとした表面に細い継ぎ目)
        _shade(ctx, x, y, r, BALLS[0][5], alpha)
        ctx.save()
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.clip()
        ctx.translate(x, y)
        ctx.rotate(ang)
        ctx.scale(1, 0.35)
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(1, 1, 1, 0.35 * alpha)
        ctx.set_line_width(max(0.8, r * 0.05))
        ctx.stroke()
        _gloss(ctx, x, y, r, alpha, 0.85)
    elif kind == 1:   # テニスボール(黄緑・白い曲線の継ぎ目)
        _shade(ctx, x, y, r, BALLS[1][5], alpha)
        ctx.save()
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.clip()
        ctx.translate(x, y)
        ctx.rotate(ang)
        ctx.set_source_rgba(1, 1, 1, 0.92 * alpha)
        ctx.set_line_width(max(1.0, r * 0.12))
        ctx.arc(-r * 1.05, 0, r * 0.78, -1.2, 1.2)
        ctx.stroke()
        ctx.arc(r * 1.05, 0, r * 0.78, math.pi - 1.2, math.pi + 1.2)
        ctx.stroke()
        ctx.restore()
        _gloss(ctx, x, y, r, alpha, 0.25)
    elif kind == 2:   # 野球ボール(白・赤い縫い目)
        _shade(ctx, x, y, r, BALLS[2][5], alpha)
        ctx.save()
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.clip()
        ctx.translate(x, y)
        ctx.rotate(ang)
        for sgn in (-1, 1):
            cx_ = sgn * r * 1.1
            rr = r * 0.8
            a0, a1 = (-1.15, 1.15) if sgn < 0 else (math.pi - 1.15, math.pi + 1.15)
            ctx.set_source_rgba(0.85, 0.12, 0.12, alpha)
            ctx.set_line_width(max(0.8, r * 0.05))
            ctx.arc(cx_, 0, rr, a0, a1)
            ctx.stroke()
            for i in range(9):   # 縫い目のV字
                a = a0 + (a1 - a0) * (i + 0.5) / 9
                px, py = cx_ + rr * math.cos(a), rr * math.sin(a)
                nx, ny = math.cos(a), math.sin(a)
                tx, ty = -ny, nx
                ctx.move_to(px - nx * r * 0.09 - tx * r * 0.04, py - ny * r * 0.09 - ty * r * 0.04)
                ctx.line_to(px, py)
                ctx.line_to(px - nx * r * 0.09 + tx * r * 0.04, py - ny * r * 0.09 + ty * r * 0.04)
                ctx.move_to(px + nx * r * 0.09 - tx * r * 0.04, py + ny * r * 0.09 - ty * r * 0.04)
                ctx.line_to(px, py)
                ctx.line_to(px + nx * r * 0.09 + tx * r * 0.04, py + ny * r * 0.09 + ty * r * 0.04)
            ctx.stroke()
        ctx.restore()
        _gloss(ctx, x, y, r, alpha, 0.35)
    elif kind == 3:   # サッカーボール(白地に黒い五角形)
        _shade(ctx, x, y, r, BALLS[3][5], alpha)
        ctx.save()
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.clip()
        ctx.translate(x, y)
        ctx.rotate(ang)

        def pent(cx_, cy_, s, rot, sq=1.0):
            ctx.new_path()
            for i in range(5):
                a = rot + i * 2 * math.pi / 5 - math.pi / 2
                ctx.line_to(cx_ + s * math.cos(a) * sq, cy_ + s * math.sin(a))
            ctx.close_path()
        ctx.set_source_rgba(0.08, 0.08, 0.1, alpha)
        pent(0, 0, r * 0.32, 0)
        ctx.fill()
        for i in range(5):   # まわりの五角形(球のふちに向かって小さく・つぶれて見える)
            a = i * 2 * math.pi / 5 - math.pi / 2 + math.pi / 5
            px, py = r * 0.86 * math.cos(a), r * 0.86 * math.sin(a)
            ctx.save()
            ctx.translate(px, py)
            ctx.rotate(a + math.pi / 2)
            pent(0, 0, r * 0.26, 0, 0.75)
            ctx.restore()
            ctx.fill()
        ctx.set_source_rgba(0.2, 0.2, 0.22, 0.6 * alpha)   # 継ぎ目の線
        ctx.set_line_width(max(0.6, r * 0.03))
        for i in range(5):
            a = i * 2 * math.pi / 5 - math.pi / 2
            ctx.move_to(r * 0.32 * math.cos(a), r * 0.32 * math.sin(a))
            ctx.line_to(r * 0.62 * math.cos(a), r * 0.62 * math.sin(a))
        ctx.stroke()
        ctx.restore()
        _gloss(ctx, x, y, r, alpha, 0.4)
    elif kind == 4:   # ボウリング球(つやのある紫のマーブル・指穴3つ)
        _shade(ctx, x, y, r, BALLS[4][5], alpha)
        ctx.save()
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.clip()
        ctx.translate(x, y)
        ctx.rotate(ang)
        for i in range(4):   # マーブル模様
            ctx.set_source_rgba(0.75, 0.55, 1.0, 0.25 * alpha)
            ctx.set_line_width(max(1.0, r * 0.1))
            ctx.arc(-r * 0.2 + i * r * 0.15, r * 0.1 * (i - 1.5), r * (0.5 + 0.12 * i), 0.3 + i, 1.8 + i)
            ctx.stroke()
        for hx, hy, hr in ((-0.18, -0.25, 0.12), (0.18, -0.25, 0.12), (0, 0.15, 0.14)):
            g = cairo.RadialGradient(hx * r, hy * r, 0, hx * r, hy * r, hr * r)
            g.add_color_stop_rgba(0, 0, 0, 0, alpha)
            g.add_color_stop_rgba(0.8, 0.05, 0.03, 0.12, alpha)
            g.add_color_stop_rgba(1, 0.25, 0.2, 0.45, alpha)
            ctx.set_source(g)
            ctx.arc(hx * r, hy * r, hr * r, 0, 2 * math.pi)
            ctx.fill()
        ctx.restore()
        _gloss(ctx, x, y, r, alpha, 0.9)
    else:   # 鉄球(重い金属・映りこみ)
        g = cairo.LinearGradient(x - r, y - r, x + r, y + r)
        for st, c in ((0, (0.9, 0.92, 0.95)), (0.35, (0.55, 0.58, 0.63)), (0.55, (0.3, 0.32, 0.36)),
                      (0.75, (0.6, 0.63, 0.68)), (1, (0.2, 0.21, 0.24))):
            g.add_color_stop_rgba(st, *c, alpha)
        ctx.set_source(g)
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.fill()
        ctx.save()
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.clip()
        ctx.translate(x, y)
        ctx.rotate(ang)
        ctx.set_source_rgba(0.15, 0.15, 0.17, 0.35 * alpha)   # 回っているのが分かる細い溝
        ctx.set_line_width(max(0.8, r * 0.05))
        ctx.move_to(-r, r * 0.15)
        ctx.line_to(r, r * 0.15)
        ctx.stroke()
        ctx.restore()
        _gloss(ctx, x, y, r, alpha, 1.0)
    _outline(ctx, x, y, r, alpha)
    ctx.restore()
