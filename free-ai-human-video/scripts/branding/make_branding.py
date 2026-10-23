"""「ギリギリ物理」のアカウント用画像(アイコン・YouTube バナー・ショート用カバー)を作る。

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


def bg(ctx, w, h, cx, cy):
    g = cairo.RadialGradient(cx, cy, 30, cx, cy, max(w, h) * 0.75)
    g.add_color_stop_rgb(0, 0.10, 0.08, 0.24)
    g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
    ctx.set_source(g)
    ctx.paint()


def rings(ctx, cx, cy, r0, step, n, gap_deg=40, rot=0.0, width=8):
    """すき間が一直線にそろったリング群(=ボールが抜けていく道)を描く。"""
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(n):
        r = r0 + i * step
        gap = math.radians(gap_deg) * (1 - i * 0.03)
        a = rot + i * 0.10  # 少しずつずらして回転感を出す
        for wdt, al in ((width * 3.4, 0.08), (width * 2.2, 0.16), (width, 1.0)):
            ctx.new_path()
            ctx.arc(cx, cy, r, a + gap / 2, a - gap / 2 + 2 * math.pi)
            ctx.set_source_rgba(*hue_rgb(i / max(n, 1)), al)
            ctx.set_line_width(wdt)
            ctx.stroke()


def ball(ctx, x, y, r, dx, dy, color=(1, 0.3, 0.6)):
    """ボールと、進んできた方向の軌跡を描く。"""
    for k in range(14, 0, -1):
        ctx.new_path()
        ctx.arc(x - dx * k, y - dy * k, r * (1 - k / 18), 0, 2 * math.pi)
        ctx.set_source_rgba(*color, 0.3 * (1 - k / 14))
        ctx.fill()
    for rr, al in ((r * 2.6, 0.15), (r * 1.7, 0.3)):
        ctx.new_path()
        ctx.arc(x, y, rr, 0, 2 * math.pi)
        ctx.set_source_rgba(*color, al)
        ctx.fill()
    ctx.new_path()
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()


def icon(path, size=800):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    c = cairo.Context(s)
    cx = cy = size / 2
    bg(c, size, size, cx, cy)
    # 丸く切り抜かれても欠けないよう、中心から半径 0.42 以内に収める
    rot = -math.pi / 4
    rings(c, cx, cy, size * 0.10, size * 0.052, 6, gap_deg=48, rot=rot, width=size * 0.016)
    r_out = size * 0.10 + 5 * size * 0.052
    bx, by = cx + math.cos(rot) * (r_out + size * 0.05), cy + math.sin(rot) * (r_out + size * 0.05)
    ball(c, bx, by, size * 0.035, math.cos(rot) * size * 0.022, math.sin(rot) * size * 0.022)
    s.write_to_png(path)


def banner(path):
    w, h = 2560, 1440
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    c = cairo.Context(s)
    bg(c, w, h, w / 2, h / 2)
    # 左右の飾りリング(パソコン表示でだけ見える範囲)
    rings(c, 330, h / 2, 60, 34, 9, gap_deg=40, rot=0.2, width=7)
    rings(c, w - 330, h / 2, 60, 34, 9, gap_deg=40, rot=math.pi + 0.2, width=7)
    ball(c, 330 + 400, h / 2 + 90, 18, 14, 3)
    # 全端末で表示される中央 1546x423 の安全範囲に文字を収める
    text(c, "ギリギリ物理", w / 2, h / 2 + 20, 150, rgb=YELLOW, sw=18)
    text(c, "GIRIGIRI PHYSICS", w / 2, h / 2 + 100, 56, sw=8)
    text(c, "毎日、ギリギリで決着する物理シミュレーション", w / 2, h / 2 + 175, 48,
         rgb=(0.85, 0.85, 0.92), sw=6)
    s.write_to_png(path)


def cover(path, hook="ラスト1秒で…!?"):
    """ショート動画のカバー画像(TikTok / Instagram でアップロード用)。"""
    w, h = 1080, 1920
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    c = cairo.Context(s)
    cx, cy = w / 2, 1130
    bg(c, w, h, cx, cy)
    rot = -math.pi / 4
    rings(c, cx, cy, 100, 30, 10, gap_deg=40, rot=rot, width=9)
    r_out = 100 + 9 * 30
    ball(c, cx + math.cos(rot) * (r_out + 60), cy + math.sin(rot) * (r_out + 60), 22,
         math.cos(rot) * 18, math.sin(rot) * 18)
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
    cover(os.path.join(OUT, "cover_ball_escape_136.png"))
    print("完成:", os.path.abspath(OUT))
