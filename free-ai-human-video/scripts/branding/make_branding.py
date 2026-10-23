"""「失敗したら出る物理」のアカウント用画像(アイコン・YouTube バナー)と、動画ごとのカバー画像を作る。

アイコンとバナーは特定の動画の形式(リング脱出など)に寄せず、
「飛ぶボール + 下から目だけのぞく幽霊」という絵柄にしている。
幽霊の顔全体は見せない(動画内のびっくり演出のネタバレを防ぐ)。

使い方:
    python make_branding.py
出力先: assets/output/branding/
"""

import math
import os
import sys

import cairo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ball_escape"))
from ball_escape import hue_rgb, text  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output", "branding")
YELLOW = (1, 0.86, 0.2)
NAME_JA = "失敗したら出る物理"
NAME_EN = "DERU PHYSICS"
TAGLINE = "成功を祈れ。失敗すると…アレが出る。"


def bg(ctx, w, h, cx, cy):
    g = cairo.RadialGradient(cx, cy, 30, cx, cy, max(w, h) * 0.75)
    g.add_color_stop_rgb(0, 0.10, 0.08, 0.24)
    g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
    ctx.set_source(g)
    ctx.paint()


def flying_ball(ctx, x0, y0, vx, vy, g, t_end, r, color, width):
    """放物線を描いて飛ぶボールと、その軌跡を描く。"""
    pts = [(x0 + vx * t, y0 + vy * t + 0.5 * g * t * t)
           for t in (t_end * k / 60 for k in range(61))]
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(1, len(pts)):
        a = i / len(pts)
        for wdt, al in ((width * 3, 0.10), (width, 0.9)):
            ctx.new_path()
            ctx.move_to(*pts[i - 1])
            ctx.line_to(*pts[i])
            ctx.set_source_rgba(*color, al * a)
            ctx.set_line_width(wdt * (0.3 + 0.7 * a))
            ctx.stroke()
    x, y = pts[-1]
    for rr, al in ((r * 2.6, 0.15), (r * 1.7, 0.3)):
        ctx.new_path()
        ctx.arc(x, y, rr, 0, 2 * math.pi)
        ctx.set_source_rgba(*color, al)
        ctx.fill()
    ctx.new_path()
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()


def balls_motif(ctx, cx, cy, s):
    """4色のボールが中央に向かって飛び交う絵(s は全体の大きさ)。"""
    specs = [  # 開始位置(中心からの比率), 速度, 終了時刻, 色の色相
        ((-0.62, 0.45), (0.95, -1.75), 0.78, 0.00),
        ((0.62, 0.48), (-0.85, -1.85), 0.82, 0.58),
        ((-0.55, -0.05), (1.20, -1.10), 0.70, 0.30),
        ((0.58, 0.05), (-1.05, -1.25), 0.62, 0.80),
    ]
    for (sx, sy), (vx, vy), te, hue in specs:
        flying_ball(ctx, cx + sx * s, cy + sy * s, vx * s, vy * s, 3.2 * s, te,
                    s * 0.045, hue_rgb(hue), s * 0.018)


def _ellipse(ctx, x, y, rx, ry):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()


def peeking_ghost(ctx, cx, base_y, s):
    """base_y の線から上に、目だけのぞかせる幽霊(s は顔の幅の目安)。"""
    ctx.save()
    ctx.rectangle(cx - s * 3, base_y - s * 3, s * 6, s * 3 + s * 0.16)  # 鼻の下あたりまで見せる
    ctx.clip()
    hair = (0.015, 0.012, 0.012)
    # 後ろ髪(肩に向かって広がる)
    ctx.new_path()
    ctx.move_to(cx - s * 0.95, base_y + s * 0.3)
    ctx.curve_to(cx - s * 0.85, base_y - s * 0.35, cx - s * 0.6, base_y - s * 0.68, cx, base_y - s * 0.68)
    ctx.curve_to(cx + s * 0.6, base_y - s * 0.68, cx + s * 0.85, base_y - s * 0.35, cx + s * 0.95, base_y + s * 0.3)
    ctx.close_path()
    ctx.set_source_rgb(*hair)
    ctx.fill()
    # 青白い顔
    g = cairo.RadialGradient(cx, base_y - s * 0.1, s * 0.05, cx, base_y + s * 0.1, s * 0.6)
    g.add_color_stop_rgb(0, 0.86, 0.89, 0.87)
    g.add_color_stop_rgb(1, 0.38, 0.42, 0.41)
    _ellipse(ctx, cx, base_y + s * 0.25, s * 0.50, s * 0.62)
    ctx.set_source(g)
    ctx.fill()
    # 目(くぼみ → 黒目 → 小さな白い瞳)
    for sx in (-1, 1):
        ex, ey = cx + sx * s * 0.19, base_y - s * 0.06
        g2 = cairo.RadialGradient(ex, ey, 2, ex, ey, s * 0.20)
        g2.add_color_stop_rgba(0, 0.05, 0.03, 0.05, 0.9)
        g2.add_color_stop_rgba(1, 0.05, 0.03, 0.05, 0.0)
        _ellipse(ctx, ex, ey, s * 0.20, s * 0.20)
        ctx.set_source(g2)
        ctx.fill()
        _ellipse(ctx, ex, ey, s * 0.085, s * 0.10)
        ctx.set_source_rgb(0, 0, 0)
        ctx.fill()
        _ellipse(ctx, ex - sx * s * 0.012, ey + s * 0.012, s * 0.016, s * 0.016)
        ctx.set_source_rgb(0.95, 0.95, 0.9)
        ctx.fill()
    # 前髪(眉の上でまっすぐ)と、顔の左右にかかる垂れ髪
    ctx.new_path()
    ctx.move_to(cx - s * 0.60, base_y - s * 0.16)
    ctx.curve_to(cx - s * 0.60, base_y - s * 0.62, cx + s * 0.60, base_y - s * 0.62, cx + s * 0.60, base_y - s * 0.16)
    ctx.line_to(cx - s * 0.60, base_y - s * 0.16)
    ctx.close_path()
    ctx.set_source_rgb(*hair)
    ctx.fill()
    for sx, inner in ((-1, 0.40), (1, 0.34)):
        ctx.new_path()
        ctx.move_to(cx + sx * s * 0.60, base_y - s * 0.25)
        ctx.curve_to(cx + sx * s * inner, base_y - s * 0.18, cx + sx * s * (inner - 0.03), base_y + s * 0.05,
                     cx + sx * s * (inner + 0.03), base_y + s * 0.3)
        ctx.line_to(cx + sx * s * 1.0, base_y + s * 0.3)
        ctx.close_path()
        ctx.set_source_rgb(*hair)
        ctx.fill()
    # 毛束でふちを自然に
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for k in range(40):
        sx = 1 if k % 2 else -1
        inner = 0.40 if sx < 0 else 0.34
        x0 = cx + sx * s * (inner + 0.015 * (k % 7) - 0.04)
        ctx.move_to(x0, base_y - s * 0.2)
        ctx.curve_to(x0, base_y - s * 0.05, x0 - sx * s * 0.02, base_y + s * 0.1, x0 + sx * s * 0.01, base_y + s * 0.3)
        ctx.set_source_rgba(*hair, 0.85)
        ctx.set_line_width(max(1.0, s * 0.008))
        ctx.stroke()
    # 前髪の毛先を少し乱す
    for k in range(18):
        x0 = cx - s * 0.55 + s * 1.1 * k / 17
        ctx.move_to(x0, base_y - s * 0.2)
        ctx.line_to(x0 + s * 0.01 * ((k * 7) % 5 - 2), base_y - s * (0.13 + 0.02 * (k % 3)))
        ctx.set_source_rgba(*hair, 0.9)
        ctx.set_line_width(max(1.5, s * 0.02))
        ctx.stroke()
    ctx.restore()


def icon(path, size=800):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    c = cairo.Context(s)
    cx = cy = size / 2
    bg(c, size, size, cx, cy)
    # 下からじわっと赤い光
    g = cairo.RadialGradient(cx, size, 10, cx, size, size * 0.55)
    g.add_color_stop_rgba(0, 0.6, 0.05, 0.1, 0.55)
    g.add_color_stop_rgba(1, 0.6, 0.05, 0.1, 0.0)
    c.set_source(g)
    c.paint()
    # 上を飛ぶボール(丸く切り抜かれても欠けないよう中心から半径 0.42 以内)
    flying_ball(c, cx - size * 0.34, cy - size * 0.02, size * 0.9, -size * 1.05, size * 2.3, 0.62,
                size * 0.05, (1, 0.3, 0.6), size * 0.022)
    flying_ball(c, cx + size * 0.30, cy + size * 0.02, -size * 0.55, -size * 0.95, size * 2.3, 0.40,
                size * 0.028, hue_rgb(0.55), size * 0.012)
    # 下から目だけのぞく幽霊
    peeking_ghost(c, cx, size * 0.74, size * 0.50)
    s.write_to_png(path)


def banner(path):
    w, h = 2560, 1440
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    c = cairo.Context(s)
    bg(c, w, h, w / 2, h / 2)
    safe_bottom = h / 2 + 423 / 2   # スマホでも表示される範囲の下端
    # 左側:飛び交うボール / 右側:安全範囲の下端から目だけのぞく幽霊
    balls_motif(c, 330, h / 2 + 40, 420)
    gx = w / 2 + 640
    g = cairo.RadialGradient(gx, safe_bottom, 10, gx, safe_bottom, 300)
    g.add_color_stop_rgba(0, 0.6, 0.05, 0.1, 0.5)
    g.add_color_stop_rgba(1, 0.6, 0.05, 0.1, 0.0)
    c.set_source(g)
    c.paint()
    peeking_ghost(c, gx, safe_bottom - 230 * 0.16, 230)
    # 全端末で表示される中央 1546x423 の安全範囲に文字を収める
    text(c, NAME_JA, w / 2 - 120, h / 2 + 10, 120, rgb=YELLOW, sw=16)
    text(c, NAME_EN, w / 2 - 120, h / 2 + 85, 52, sw=8)
    text(c, TAGLINE, w / 2 - 120, h / 2 + 160, 50, rgb=(1, 0.45, 0.45), sw=8)
    s.write_to_png(path)


def ring_art(ctx, cx, cy, r0, step, n, gap_deg, rot, width):
    """リング脱出回のカバー用の絵。"""
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(n):
        r = r0 + i * step
        gap = math.radians(gap_deg) * (1 - i * 0.03)
        a = rot + i * 0.10
        for wdt, al in ((width * 3.4, 0.08), (width * 2.2, 0.16), (width, 1.0)):
            ctx.new_path()
            ctx.arc(cx, cy, r, a + gap / 2, a - gap / 2 + 2 * math.pi)
            ctx.set_source_rgba(*hue_rgb(i / max(n, 1)), al)
            ctx.set_line_width(wdt)
            ctx.stroke()


def cover_ball_escape(path, hook="ラスト1秒で…!?"):
    """リング脱出回のカバー画像(TikTok / Instagram でアップロード用)。動画ごとに作る。"""
    w, h = 1080, 1920
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    c = cairo.Context(s)
    cx, cy = w / 2, 1130
    bg(c, w, h, cx, cy)
    rot = -math.pi / 4
    ring_art(c, cx, cy, 100, 30, 10, 40, rot, 9)
    r_out = 100 + 9 * 30
    flying_ball(c, cx + math.cos(rot) * (r_out - 40), cy + math.sin(rot) * (r_out - 40),
                math.cos(rot) * 300, math.sin(rot) * 300, 0, 0.35, 22, (1, 0.3, 0.6), 8)
    # Instagram のグリッド表示(中央の 1080x1350)からはみ出さない位置に大きな文字を置く
    text(c, "30秒以内に", cx, 430, 96, sw=16)
    text(c, "全部脱出", cx, 580, 170, rgb=YELLOW, sw=22)
    text(c, "できる？", cx, 720, 130, sw=18)
    text(c, hook, cx, 1630, 84, rgb=(1, 0.35, 0.35), sw=14)
    s.write_to_png(path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    icon(os.path.join(OUT, "icon_800.png"))
    banner(os.path.join(OUT, "youtube_banner_2560x1440.png"))
    cover_ball_escape(os.path.join(OUT, "cover_ball_escape_136.png"))
    print("完成:", os.path.abspath(OUT))
