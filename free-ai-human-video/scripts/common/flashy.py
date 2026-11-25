"""シリーズ共通の派手な部品。
- giragira: パチンコ大当たり本番(jackpot_end)の上に重ねる、虹色のギラギラ
- scary_text / drip_layout: 「失敗したら・・・」用の、血がしたたる怖い筆文字(Yuji Boku・SIL OFL。~/.fonts に入れて使う)
- draw_ball / PALETTE: つやのあるボールと12色の虹
- kyuin_one: キュイン1回分の音
- chic: すっきりしたゴシック体の文字(Zen Kaku Gothic New)/ horror: 怖い筆文字(Yuji Syuku)の「失敗したら…」
"""
import colorsys
import math

import cairo
import numpy as np

from pachinko import hsv

SR = 48000
SCARY_FONT = "Yuji Boku"
PALETTE = [colorsys.hsv_to_rgb(k / 12, 0.85, 1.0) for k in range(12)]   # 12色の虹


def _t(d):
    return np.arange(int(d * SR)) / SR


def giragira(ctx, b, fever, glints, W, H, main):
    """大当たり本番の上に重ねる、虹色のギラギラ(ホログラムの光・ストロボ・サーチライト・きらめき・虹の枠)。"""
    ctx.set_operator(cairo.OPERATOR_ADD)
    # ホログラムのように、ななめに流れる虹の光
    off = (b * 1100) % 1400
    g = cairo.LinearGradient(-1400 + off, -200, off + 400, H + 200)
    for k in range(25):
        g.add_color_stop_rgba(k / 24, *hsv(k / 8 + b * 0.8), 0.26 if k % 2 == 0 else 0.0)
    ctx.set_source(g)
    ctx.paint()
    # キュインの拍(0.3秒)ごとの虹ストロボ
    ph = (b % 0.3) / 0.3
    ctx.set_source_rgba(*hsv(b * 2.7), 0.32 * (1 - ph) ** 3)
    ctx.paint()
    # 下の両すみから振れる虹のサーチライト
    for side in (-1, 1):
        for j in range(3):
            ang = -math.pi / 2 + side * (0.35 + 0.3 * math.sin(b * 2.2 + j * 2.1))
            x0 = W / 2 + side * (W / 2 + 40)
            y0 = H + 40
            ln = 2400
            spread = 0.07
            ctx.move_to(x0, y0)
            ctx.line_to(x0 + ln * math.cos(ang - spread), y0 + ln * math.sin(ang - spread))
            ctx.line_to(x0 + ln * math.cos(ang + spread), y0 + ln * math.sin(ang + spread))
            ctx.close_path()
            lg = cairo.LinearGradient(x0, y0, x0 + ln * math.cos(ang), y0 + ln * math.sin(ang))
            col = hsv(b * 0.9 + j / 3 + (0.5 if side > 0 else 0))
            lg.add_color_stop_rgba(0, *col, 0.55)
            lg.add_color_stop_rgba(1, *col, 0.0)
            ctx.set_source(lg)
            ctx.fill()
    # 画面じゅうでピカッと光るきらめき(十字の光)
    for x, y, ph0, sp, sz in glints:
        tw = max(0.0, math.sin((b * sp + ph0) * 2 * math.pi)) ** 6
        if tw < 0.02:
            continue
        L = sz * (0.5 + tw)
        for ang, ll in ((0, L), (math.pi / 2, L), (math.pi / 4, L * 0.45), (-math.pi / 4, L * 0.45)):
            dx, dy = ll * math.cos(ang), ll * math.sin(ang)
            lg = cairo.LinearGradient(x - dx, y - dy, x + dx, y + dy)
            lg.add_color_stop_rgba(0, 1, 1, 1, 0)
            lg.add_color_stop_rgba(0.5, 1, 1, 1, tw)
            lg.add_color_stop_rgba(1, 1, 1, 1, 0)
            ctx.set_source(lg)
            ctx.set_line_width(3)
            ctx.move_to(x - dx, y - dy)
            ctx.line_to(x + dx, y + dy)
            ctx.stroke()
        rg = cairo.RadialGradient(x, y, 0, x, y, L * 0.35)
        rg.add_color_stop_rgba(0, *hsv(ph0 + b), tw)
        rg.add_color_stop_rgba(1, *hsv(ph0 + b), 0)
        ctx.set_source(rg)
        ctx.arc(x, y, L * 0.35, 0, 2 * math.pi)
        ctx.fill()
    ctx.set_operator(cairo.OPERATOR_OVER)
    # 画面のふちの、色が流れる虹の枠と、虹の星
    fever.draw_front(ctx, b, lambda *a, **k: None, "", "")
    if b > main - 0.6:
        ctx.set_source_rgba(0, 0, 0, min(1.0, (b - (main - 0.6)) / 0.6))
        ctx.paint()


def drip_layout(ctx, part, cx, y, size, full, seed):
    """「失敗したら」の文字の下から垂れる血のしずくの位置(x, 最大の長さ, 太さ, 垂れはじめる時間)。"""
    ctx.select_font_face(SCARY_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    ef = ctx.text_extents(full)
    ep = ctx.text_extents(part)
    x0 = cx - ef.width / 2 - ef.x_bearing + ep.x_bearing
    rng = np.random.default_rng(seed + 11)
    return [(x0 + ep.width * (k + rng.uniform(0.25, 0.75)) / 6, rng.uniform(30, 80), rng.uniform(8, 13), rng.uniform(0, 6))
            for k in range(6)]


def scary_text(ctx, s, x, y, size, t, drips):
    """怖い筆文字:赤くにじむ光+血のしずく+ときどきチラつく。"""
    flick = (t % 2.3) < 0.09   # 2.3秒に一度、一瞬チラつく
    jx = (6 * math.sin(t * 97)) if flick else 0.0
    alpha = 0.55 if flick else 1.0
    ctx.select_font_face(SCARY_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    e = ctx.text_extents(s)
    tx = x - e.width / 2 - e.x_bearing + jx
    # 血のしずく(文字のうしろから、ゆっくり垂れる)
    for dx, ln, wd, t0 in drips:
        k = max(0.0, min(1.0, (t - t0) / 6.0))
        L = 6 + ln * (k * k * (3 - 2 * k))
        x_ = dx + jx
        top = y - size * 0.25
        ctx.move_to(x_ - wd / 2, top)
        ctx.line_to(x_ - wd * 0.3, y + L)
        ctx.line_to(x_ + wd * 0.3, y + L)
        ctx.line_to(x_ + wd / 2, top)
        ctx.close_path()
        ctx.set_source_rgba(0.55, 0.0, 0.03, alpha)
        ctx.fill()
        ctx.arc(x_, y + L, wd * 0.75, 0, 2 * math.pi)
        ctx.fill()
    # 赤くにじむ光
    for wd, al in ((34, 0.10), (22, 0.18), (12, 0.35)):
        ctx.move_to(tx, y)
        ctx.text_path(s)
        ctx.set_source_rgba(0.9, 0.0, 0.05, al * alpha)
        ctx.set_line_width(wd)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    ctx.move_to(tx, y)
    ctx.text_path(s)
    ctx.set_source_rgba(0.05, 0, 0, alpha)
    ctx.set_line_width(6)
    ctx.stroke_preserve()
    g = cairo.LinearGradient(0, y - size * 0.9, 0, y + size * 0.15)
    g.add_color_stop_rgba(0, 1.0, 0.25, 0.25, alpha)
    g.add_color_stop_rgba(0.5, 0.85, 0.02, 0.05, alpha)
    g.add_color_stop_rgba(1, 0.4, 0.0, 0.02, alpha)
    ctx.set_source(g)
    ctx.fill()


def kyuin_one(up=1.0):
    t = _t(0.28)
    f = up * (500 + 2900 * (1 - np.exp(-t / 0.06))) * (1 + 0.03 * np.sin(2 * np.pi * 32 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.35 * np.sign(np.sin(ph)) + 0.3 * np.sin(2 * ph)
    return y * np.minimum(1, t / 0.01) * np.exp(-np.maximum(0, t - 0.16) / 0.05)


def draw_ball(ctx, x, y, r, col):
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r)
    g.add_color_stop_rgb(0, *(min(1, c + 0.5) for c in col))
    g.add_color_stop_rgb(0.5, *col)
    g.add_color_stop_rgb(1, *(c * 0.55 for c in col))
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()


def chic(ctx, s, x, y, size, rgb=(1, 1, 1), alpha=1.0, weight="Bold"):
    """すっきりしたゴシック体(Zen Kaku Gothic New・SIL OFL)。太いふちどりはなし、やわらかい影だけ。"""
    ctx.select_font_face("Zen Kaku Gothic New" if weight == "Bold" else "Zen Kaku Gothic New Medium",
                         cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if weight == "Bold" else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    e = ctx.text_extents(s)
    tx = x - e.width / 2 - e.x_bearing
    for dx, dy, a in ((0, 4, 0.45), (0, 2, 0.35)):   # やわらかい影
        ctx.move_to(tx + dx, y + dy)
        ctx.text_path(s)
        ctx.set_source_rgba(0, 0, 0, a * alpha)
        ctx.fill()
    ctx.move_to(tx, y)
    ctx.text_path(s)
    ctx.set_source_rgba(*rgb, alpha)
    ctx.fill()


def horror(ctx, s, x, y, size, t):
    """怖い筆文字(Yuji Syuku・SIL OFL)。赤黒くにじむ光と、ときどき入るノイズのようなズレ。"""
    flick = (t % 2.3) < 0.09
    ctx.select_font_face("Yuji Syuku", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    e = ctx.text_extents(s)
    tx = x - e.width / 2 - e.x_bearing
    for wd, al in ((26, 0.08), (14, 0.16)):   # 赤黒くにじむ光
        ctx.move_to(tx, y)
        ctx.text_path(s)
        ctx.set_source_rgba(0.6, 0.0, 0.03, al)
        ctx.set_line_width(wd)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    if flick:   # ズレた残像(ノイズ)
        for dx, col in ((-7, (0.2, 0.0, 0.0)), (6, (1.0, 0.2, 0.25))):
            ctx.move_to(tx + dx, y)
            ctx.text_path(s)
            ctx.set_source_rgba(*col, 0.6)
            ctx.fill()
    ctx.move_to(tx + 2, y + 4)
    ctx.text_path(s)
    ctx.set_source_rgba(0, 0, 0, 0.6)
    ctx.fill()
    g = cairo.LinearGradient(0, y - size * 0.9, 0, y + size * 0.15)
    g.add_color_stop_rgb(0, 0.95, 0.15, 0.18)
    g.add_color_stop_rgb(1, 0.5, 0.0, 0.03)
    ctx.move_to(tx, y)
    ctx.text_path(s)
    ctx.set_source(g)
    ctx.fill()
