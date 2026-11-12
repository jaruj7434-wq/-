"""第1話 解説強化版: 実写風カットに 矢印・グラフ・色文字テロップ・一時停止 を重ねる。

  python3 scripts/science_0001/ep01_explainer.py            # 映像(無音) assets/output/science_0001/ep01_v3_video.mp4
  python3 scripts/science_0001/ep01_explainer.py --still 20 # 20秒目の1枚だけ確認用に書き出す

フォント(~/.fonts): Dela Gothic One / M PLUS Rounded 1c ExtraBold (Fontsource の分割ファイルを結合したもの)
数字は plan.md の出典付きの値のみ。グラフの曲線は水の飽和蒸気圧(Antoine式)。
"""
from __future__ import annotations

import argparse
import math
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
SRC = Path("assets/source/science_0001")
OUT = Path("assets/output/science_0001")
FONT_DIR = Path.home() / ".fonts"
F_HEAD = str(FONT_DIR / "DelaGothicOne-Regular.ttf")
F_BODY = str(FONT_DIR / "MPLUSRounded1c-ExtraBold.ttf")

# 色
YEL = (255, 201, 77)
BLUE = (94, 200, 255)
HOT = (255, 106, 61)
WHITE = (255, 255, 255)
INK = (20, 22, 30)
CARD = (12, 14, 22, 200)

_font_cache: dict = {}


def font(path, size):
    k = (path, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(path, size)
    return _font_cache[k]


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def appear(t, start, dur=0.35):
    return ease((t - start) / dur)


# ------------------------------------------------------------------ 描画パーツ
def rich_line(d: ImageDraw.ImageDraw, segs, y, size, fnt=F_BODY, alpha=1.0, cx=W / 2, stroke=8):
    """segs: [(text, color), ...] を1行で中央ぞろえ。"""
    f = font(fnt, size)
    widths = [d.textlength(s, font=f) for s, _ in segs]
    x = cx - sum(widths) / 2
    a = int(255 * alpha)
    for (s, c), w in zip(segs, widths):
        d.text((x, y), s, font=f, fill=c + (a,), stroke_width=stroke, stroke_fill=(0, 0, 0, int(a * 0.85)))
        x += w
    return sum(widths)


def rich(d, lines, y, size, fnt=F_BODY, alpha=1.0, gap=1.3, cx=W / 2, stroke=8):
    """lines: 各行が [(text,color),...]。'**語**' 記法の文字列も受け付ける(強調色=YEL)。"""
    for i, ln in enumerate(lines):
        if isinstance(ln, str):
            ln = parse(ln)
        rich_line(d, ln, y + i * size * gap, size, fnt, alpha, cx, stroke)


def parse(s, base=WHITE, hi=YEL):
    """'熱で**水蒸気**に' → [(熱で,白),(水蒸気,黄),(に,白)]。{b}..{/} で青, {r}..{/} で赤。"""
    out, color, buf, i = [], base, "", 0
    while i < len(s):
        if s.startswith("**", i):
            if buf:
                out.append((buf, color))
            buf, color = "", (hi if color == base else base)
            i += 2
        elif s.startswith("{b}", i) or s.startswith("{r}", i):
            if buf:
                out.append((buf, color))
            buf, color = "", BLUE if s[i + 1] == "b" else HOT
            i += 3
        elif s.startswith("{/}", i):
            if buf:
                out.append((buf, color))
            buf, color = "", base
            i += 3
        else:
            buf += s[i]
            i += 1
    if buf:
        out.append((buf, color))
    return out


def card(d, box, alpha=1.0, accent=None, radius=36):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=radius, fill=CARD[:3] + (int(CARD[3] * alpha),))
    if accent:
        d.rounded_rectangle((x0, y0, x0 + 14, y1), radius=7, fill=accent + (int(255 * alpha),))


def pill(d, xy, text, bg, fg=INK, size=40, fnt=F_BODY, alpha=1.0, anchor="lt"):
    f = font(fnt, size)
    w = d.textlength(text, font=f)
    padx, pady = size * 0.55, size * 0.28
    x, y = xy
    if anchor == "mt":
        x -= (w + 2 * padx) / 2
    box = (x, y, x + w + 2 * padx, y + size + 2 * pady + size * 0.1)
    a = int(255 * alpha)
    d.rounded_rectangle(box, radius=(box[3] - box[1]) / 2, fill=bg + (a,))
    d.text((x + padx, y + pady - size * 0.08), text, font=f, fill=fg + (a,))
    return box


def chapter(d, t, num, title, color=YEL):
    a = appear(t, 0.0)
    off = (1 - a) * -40
    pill(d, (48 + off, 120), f"STEP {num}", color, size=40, fnt=F_HEAD, alpha=a)
    f = font(F_BODY, 54)
    d.text((300 + off, 118), title, font=f, fill=WHITE + (int(255 * a),), stroke_width=8,
           stroke_fill=(0, 0, 0, int(220 * a)))


def series_badge(d, a=1.0):
    pill(d, (W / 2, 48), "0.001秒の世界", (255, 255, 255), INK, size=34, fnt=F_HEAD, alpha=0.9 * a, anchor="mt")


def arrow(d, p0, p1, color, prog=1.0, width=12, head=38, alpha=1.0):
    """p0 → p1 へ伸びる矢印(prog で途中まで)。"""
    if prog <= 0:
        return
    x0, y0 = p0
    x1, y1 = p0[0] + (p1[0] - x0) * prog, p0[1] + (p1[1] - y0) * prog
    a = int(255 * alpha)
    d.line((x0, y0, x1, y1), fill=(0, 0, 0, int(a * 0.6)), width=width + 8)
    d.line((x0, y0, x1, y1), fill=color + (a,), width=width)
    ang = math.atan2(y1 - y0, x1 - x0)
    pts = [(x1 + head * 0.35 * math.cos(ang), y1 + head * 0.35 * math.sin(ang)),
           (x1 - head * math.cos(ang - 0.5), y1 - head * math.sin(ang - 0.5)),
           (x1 - head * math.cos(ang + 0.5), y1 - head * math.sin(ang + 0.5))]
    d.polygon(pts, fill=color + (a,), outline=(0, 0, 0, int(a * 0.6)))


def label_arrow(d, t, start, label_xy, target, text, color, size=44):
    """ラベル(色付きピル)からターゲットへ矢印。"""
    a = appear(t, start)
    if a <= 0:
        return
    box = pill(d, label_xy, text, color, INK, size=size, alpha=a, anchor="mt")
    sx = (box[0] + box[2]) / 2
    sy = box[3] + 6 if target[1] > box[3] else box[1] - 6
    arrow(d, (sx, sy), target, color, prog=appear(t, start + 0.15, 0.4), alpha=a)


def ring(d, c, r, color, t, width=8):
    k = 1 + 0.06 * math.sin(t * 6)
    rr = r * k
    d.ellipse((c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr), outline=color + (230,), width=width)


def pause_badge(d, t):
    a = appear(t, 0, 0.2)
    x, y = W - 270, 118
    d.rounded_rectangle((x, y, x + 222, y + 70), radius=35, fill=(255, 255, 255, int(230 * a)))
    d.rectangle((x + 30, y + 18, x + 40, y + 52), fill=INK + (int(255 * a),))
    d.rectangle((x + 50, y + 18, x + 60, y + 52), fill=INK + (int(255 * a),))
    d.text((x + 76, y + 14), "一時停止", font=font(F_BODY, 34), fill=INK + (int(255 * a),))


def bottom_caption(d, t, lines, start=0.1, size=60, accent=YEL, y=1520):
    a = appear(t, start)
    if a <= 0:
        return
    n = len(lines)
    h = n * size * 1.32 + 70
    off = (1 - a) * 40
    card(d, (60, y + off, W - 60, y + h + off), a, accent)
    rich(d, lines, y + 38 + off, size, F_BODY, a, stroke=0)


# ------------------------------------------------------------------ グラフ
def p_sat(T):
    return 10 ** (8.14019 - 1810.94 / (244.485 + T)) / 760.0


def pressure_graph(d, t, box):
    x0, y0, x1, y1 = box
    a = appear(t, 0.0)
    card(d, box, a, HOT)
    px0, py0, px1, py1 = x0 + 150, y0 + 140, x1 - 60, y1 - 120  # プロット領域
    Tmin, Tmax, Pmax = 100, 190, 12

    def X(T):
        return px0 + (T - Tmin) / (Tmax - Tmin) * (px1 - px0)

    def Y(P):
        return py1 - P / Pmax * (py1 - py0)

    fa = int(255 * a)
    d.text((x0 + 50, y0 + 36), "粒の中の圧力", font=font(F_HEAD, 46), fill=WHITE + (fa,))
    # 軸
    d.line((px0, py1, px1, py1), fill=(200, 200, 210, fa), width=4)
    d.line((px0, py0, px0, py1), fill=(200, 200, 210, fa), width=4)
    fs = font(F_BODY, 30)
    for T in (100, 140, 180):
        d.text((X(T) - 30, py1 + 14), f"{T}℃", font=fs, fill=(200, 200, 210, fa))
    for P in (1, 5, 10):
        d.line((px0 - 10, Y(P), px0, Y(P)), fill=(200, 200, 210, fa), width=3)
        d.text((px0 - 120, Y(P) - 18), f"{P}気圧", font=fs, fill=(200, 200, 210, fa))
    d.text((px1 - 110, py1 + 52), "温度 →", font=fs, fill=(200, 200, 210, fa))
    # 1気圧の線
    d.line((px0, Y(1), px1, Y(1)), fill=BLUE + (int(160 * a),), width=3)
    d.text((X(150), Y(1) - 46), "ふだんの空気 1気圧", font=font(F_BODY, 30), fill=BLUE + (fa,))
    # 曲線を描いていく
    prog = ease((t - 0.3) / 1.6)
    Tend = Tmin + (180 - Tmin) * prog
    pts = [(X(T), Y(p_sat(T))) for T in np.linspace(Tmin, max(Tmin + 0.1, Tend), 80)]
    if len(pts) > 1 and prog > 0:
        d.line(pts, fill=HOT + (fa,), width=10, joint="curve")
    if prog >= 1:
        k = appear(t, 2.0)
        cx, cy = X(180), Y(p_sat(180))
        # 点線
        for yy in np.arange(cy, py1, 22):
            d.line((cx, yy, cx, yy + 11), fill=YEL + (int(255 * k),), width=3)
        for xx in np.arange(px0, cx, 22):
            d.line((xx, cy, xx + 11, cy), fill=YEL + (int(255 * k),), width=3)
        r = 16 + 4 * math.sin(t * 7)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=YEL + (int(255 * k),), outline=INK + (255,), width=3)
        pill(d, (cx - 40, cy - 120), "約180℃・約10気圧", YEL, INK, size=40, fnt=F_HEAD, alpha=k, anchor="mt")
        d.text((cx - 380, cy + 24), "ここで殻が限界！", font=font(F_BODY, 38), fill=HOT + (int(255 * k),),
               stroke_width=6, stroke_fill=(0, 0, 0, int(255 * k)))


def donut(d, t, center, r, frac, color):
    a = appear(t, 0.0)
    prog = ease((t - 0.2) / 1.0)
    x, y = center
    box = (x - r, y - r, x + r, y + r)
    d.ellipse(box, fill=(60, 64, 80, int(255 * a)))
    d.pieslice(box, -90, -90 + 360 * frac * prog, fill=color + (int(255 * a),))
    ir = r * 0.62
    d.ellipse((x - ir, y - ir, x + ir, y + ir), fill=(16, 18, 28, int(255 * a)))
    f = font(F_HEAD, 74)
    s = f"{round(14 * prog)}%"
    w = d.textlength(s, font=f)
    d.text((x - w / 2, y - 50), s, font=f, fill=color + (int(255 * a),))


def ms_timer(d, t, dur):
    a = appear(t, 0.0)
    prog = min(1.0, t / dur)
    ms = 90 * ease(prog)
    box = (60, 1500, W - 60, 1800)
    card(d, box, a, BLUE)
    d.text((110, 1530), "殻が裂けてから 花になるまで", font=font(F_BODY, 44), fill=WHITE + (int(255 * a),))
    f = font(F_HEAD, 96)
    s = f"{ms:4.0f}"
    d.text((110, 1590), s, font=f, fill=YEL + (int(255 * a),))
    d.text((110 + d.textlength(s, font=f) + 16, 1630), "ミリ秒", font=font(F_BODY, 50), fill=WHITE + (int(255 * a),))
    d.text((640, 1610), "実際は 0.09秒未満", font=font(F_BODY, 38), fill=BLUE + (int(255 * a),))
    d.text((640, 1660), "（映像は超スロー）", font=font(F_BODY, 32), fill=(190, 190, 200, int(255 * a)))
    d.rounded_rectangle((110, 1740, W - 110, 1760), radius=10, fill=(60, 64, 80, int(255 * a)))
    d.rounded_rectangle((110, 1740, 110 + (W - 220) * ease(prog), 1760), radius=10, fill=YEL + (int(255 * a),))


def thermometer(d, t, dur, x=W - 170, y=300):
    a = appear(t, 0.2)
    T = 100 + 80 * ease(t / dur)
    d.rounded_rectangle((x, y, x + 110, y + 470), radius=55, fill=(12, 14, 22, int(190 * a)))
    d.rounded_rectangle((x + 40, y + 40, x + 70, y + 360), radius=15, fill=(60, 64, 80, int(255 * a)))
    hh = 320 * (T - 20) / 180
    d.rounded_rectangle((x + 40, y + 360 - hh, x + 70, y + 360), radius=15, fill=HOT + (int(255 * a),))
    d.ellipse((x + 25, y + 340, x + 85, y + 400), fill=HOT + (int(255 * a),))
    s = f"{T:.0f}℃"
    f = font(F_HEAD, 34)
    d.text((x + 55 - d.textlength(s, font=f) / 2, y + 412), s, font=f, fill=WHITE + (int(255 * a),))


def pressure_arrows(d, t, c, rx, ry):
    a = appear(t, 0.8)
    for k in range(8):
        ang = k * math.pi / 4 + 0.2
        pulse = 0.5 + 0.5 * math.sin(t * 6 - k)
        r0x, r0y = rx * 0.55, ry * 0.55
        r1x, r1y = rx * (1.05 + 0.08 * pulse), ry * (1.05 + 0.08 * pulse)
        arrow(d, (c[0] + r0x * math.cos(ang), c[1] + r0y * math.sin(ang)),
              (c[0] + r1x * math.cos(ang), c[1] + r1y * math.sin(ang)), HOT, prog=1, width=10, head=32,
              alpha=a * (0.6 + 0.4 * pulse))


# ------------------------------------------------------------------ タイムライン
@dataclass
class Shot:
    src: str
    start: float  # 素材の開始秒
    dur: float  # この区間の長さ
    freeze: bool = False  # True: start のフレームで静止
    overlay: Callable | None = None
    dim: float = 0.0  # 暗くする量(0〜1)
    blur: float = 0.0
    tag: str = ""
    extra: dict = field(default_factory=dict)


def ov_hook_play(d, t, g):
    series_badge(d)
    rich(d, ["ポップコーンが", "弾ける瞬間…"], 300, 84, F_HEAD, appear(t, 0.1))


def ov_hook_freeze(d, t, g):
    series_badge(d)
    pause_badge(d, t)
    ring(d, (560, 1180), 150, YEL, t)
    rich(d, ["この一瞬、", "中で**何が起きてる？**"], 300, 86, F_HEAD, appear(t, 0.15))


def ov_hook_play2(d, t, g):
    series_badge(d)
    a = appear(t, 0.2)
    rich(d, ["**4つのステップ**で", "分解してみよう"], 300, 80, F_HEAD, a)


def ov_s1(d, t, g):
    chapter(d, t, 1, "水分が蒸気に")
    label_arrow(d, t, 0.8, (540, 400), (510, 820), "水分 → 水蒸気", BLUE)
    label_arrow(d, t, 1.6, (250, 1290), (250, 1010), "でんぷん", YEL)
    label_arrow(d, t, 2.4, (820, 1290), (1000, 1120), "かたい殻", HOT)
    bottom_caption(d, t, ["粒の中の{b}水分{/}が熱せられて", "**水蒸気**に変わる"], start=3.0)


def ov_s1_freeze(d, t, g):
    chapter(d, 9, 1, "水分が蒸気に")
    pause_badge(d, t)
    a = appear(t, 0)
    card(d, (60, 1000, W - 60, 1800), a, BLUE)
    donut(d, t, (300, 1400), 190, 0.14, BLUE)
    rich(d, ["粒の重さの", "{b}約14%{/}が水", ""], 1230, 56, F_BODY, appear(t, 0.6), cx=770, stroke=0)
    rich(d, ["これが", "**膨らむ力の源**"], 1450, 48, F_BODY, appear(t, 1.2), cx=770, stroke=0)
    d.text((110, 1680), "※弾けやすい水分量は約13.5〜14%", font=font(F_BODY, 30), fill=(190, 190, 200, int(255 * appear(t, 1.6))))


def ov_s2(d, t, g):
    chapter(d, t, 2, "殻が圧力鍋になる", HOT)
    pressure_arrows(d, t, (545, 930), 300, 360)
    thermometer(d, t, g.dur)
    a = appear(t, 1.2)
    if a > 0:
        pill(d, (545, 1380), "蒸気が内側から押す", HOT, INK, size=46, alpha=a, anchor="mt")
    bottom_caption(d, t, ["かたい殻が{r}フタ{/}になって", "蒸気を**閉じこめる**"], start=2.2)


def ov_s2_freeze(d, t, g):
    chapter(d, 9, 2, "殻が圧力鍋になる", HOT)
    pause_badge(d, t)
    pressure_graph(d, t, (60, 260, W - 60, 1180))
    bottom_caption(d, t, ["ふだんの空気の **約10倍** の圧力", "殻が耐えられなくなる"], start=3.0, y=1500)


def ov_s3_freeze(d, t, g):
    chapter(d, 9, 3, "殻が裂ける", BLUE)
    pause_badge(d, t)
    label_arrow(d, t, 0.2, (250, 1120), (590, 820), "亀裂", HOT, size=48)
    label_arrow(d, t, 0.8, (820, 560), (580, 360), "水蒸気が噴き出す", BLUE)
    label_arrow(d, t, 1.4, (830, 1280), (700, 1000), "でんぷんが泡に", YEL)
    bottom_caption(d, t, ["圧力が一気に抜けて", "でんぷんが**白い泡**にふくらむ"], start=1.9)


def ov_s3_chapter(d, t, g):
    chapter(d, t, 3, "殻が裂ける", BLUE)


def ov_s3_play(d, t, g):
    chapter(d, 9, 3, "殻が裂ける", BLUE)
    ms_timer(d, t, g.dur)


def ov_s4_play(d, t, g):
    chapter(d, t, 4, "脚でジャンプ")


def ov_s4_freeze(d, t, g):
    chapter(d, 9, 4, "脚でジャンプ")
    pause_badge(d, t)
    a = appear(t, 0.2)
    # 脚が床を押す(下向き)
    arrow(d, (360, 960), (470, 1260), HOT, prog=appear(t, 0.2, 0.5), width=16, head=48, alpha=a)
    if a > 0:
        pill(d, (300, 830), "脚が床を押す", HOT, INK, size=46, alpha=a, anchor="mt")
    b = appear(t, 1.0)
    arrow(d, (800, 1000), (800, 640), YEL, prog=appear(t, 1.0, 0.5), width=16, head=48, alpha=b)
    if b > 0:
        pill(d, (800, 1040), "反動で跳ぶ", YEL, INK, size=46, alpha=b, anchor="mt")
    c = appear(t, 1.8)
    if c > 0:
        card(d, (60, 300, W - 60, 560), c, YEL)
        d.text((110, 330), "跳び出す瞬間の加速度", font=font(F_BODY, 44), fill=WHITE + (int(255 * c),))
        d.text((110, 395), "約20G", font=font(F_HEAD, 120), fill=YEL + (int(255 * c),))
        d.text((560, 450), "（重力の約20倍）", font=font(F_BODY, 40), fill=WHITE + (int(255 * c),))
    bottom_caption(d, t, ["跳ぶ力は{r}蒸気のジェット{/}ではなく", "でんぷんの**「脚」**"], start=2.4)


def ov_s4_end(d, t, g):
    chapter(d, 9, 4, "脚でジャンプ")
    rich(d, ["空中で", "**花が開く！**"], 1450, 84, F_HEAD, appear(t, 0.3))


def ov_summary(d, t, g):
    series_badge(d)
    a = appear(t, 0)
    rich(d, ["まとめ"], 230, 90, F_HEAD, a)
    rows = [
        ("1", BLUE, "水分が熱で **水蒸気** に"),
        ("2", HOT, "約180℃・約10気圧で **殻が限界**"),
        ("3", BLUE, "殻が裂けて **白い泡** に（0.09秒未満）"),
        ("4", YEL, "でんぷんの **「脚」** でジャンプ"),
    ]
    for i, (n, col, txt) in enumerate(rows):
        k = appear(t, 0.5 + i * 0.6)
        if k <= 0:
            continue
        y = 430 + i * 190 + (1 - k) * 30
        card(d, (60, y, W - 60, y + 150), k, col)
        d.ellipse((100, y + 30, 190, y + 120), fill=col + (int(255 * k),))
        f = font(F_HEAD, 54)
        d.text((145 - d.textlength(n, font=f) / 2, y + 36), n, font=f, fill=INK + (int(255 * k),))
        x = 220
        for s, c in parse(txt):
            ff = font(F_BODY, 46)
            d.text((x, y + 48), s, font=ff, fill=c + (int(255 * k),))
            x += d.textlength(s, font=ff)
    k = appear(t, 3.4, 0.5)
    rich(d, ["ポップコーンは", "**自分の「脚」で跳んでいた！**"], 1300, 70, F_HEAD, k)


SHOTS = [
    Shot("ep01_hook_kling.mp4", 0.0, 1.15, overlay=ov_hook_play),
    Shot("ep01_hook_kling.mp4", 1.15, 2.2, freeze=True, overlay=ov_hook_freeze, dim=0.25, tag="hook_pause"),
    Shot("ep01_hook_kling.mp4", 1.15, 2.35, overlay=ov_hook_play2),
    Shot("ep01_s1_cutaway.mp4", 0.0, 5.0, overlay=ov_s1, tag="step1"),
    Shot("ep01_s1_cutaway.mp4", 4.9, 4.0, freeze=True, overlay=ov_s1_freeze, dim=0.35, tag="step1_pause"),
    Shot("ep01_s2_pressure.mp4", 0.0, 5.0, overlay=ov_s2, tag="step2"),
    Shot("ep01_s2_pressure.mp4", 4.9, 5.5, freeze=True, overlay=ov_s2_freeze, dim=0.55, tag="step2_pause"),
    Shot("ep01_s3_rupture.mp4", 0.0, 0.4, overlay=ov_s3_chapter, tag="step3"),
    Shot("ep01_s3_rupture.mp4", 0.4, 3.6, freeze=True, overlay=ov_s3_freeze, dim=0.3, tag="step3_pause"),
    Shot("ep01_s3_rupture.mp4", 0.4, 4.6, overlay=ov_s3_play),
    Shot("ep01_s4_leg.mp4", 0.0, 2.3, overlay=ov_s4_play, tag="step4"),
    Shot("ep01_s4_leg.mp4", 2.3, 5.0, freeze=True, overlay=ov_s4_freeze, dim=0.3, tag="step4_pause"),
    Shot("ep01_s4_leg.mp4", 2.3, 2.7, overlay=ov_s4_end),
    Shot("ep01_s4_leg.mp4", 4.95, 6.5, freeze=True, overlay=ov_summary, dim=0.6, blur=14, tag="summary"),
]


def timeline():
    t, out = 0.0, {}
    for s in SHOTS:
        if s.tag:
            out[s.tag] = round(t, 3)
        t += s.dur
    out["total"] = round(t, 3)
    return out


def frames_of(shot: Shot):
    n = int(round(shot.dur * FPS))
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}"
    if shot.freeze:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(shot.start), "-i", str(SRC / shot.src),
                              "-frames:v", "1", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        base = Image.frombytes("RGB", (W, H), raw[: W * H * 3])
        for _ in range(n):
            yield base
        return
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(shot.start), "-i", str(SRC / shot.src),
                          "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    last, k = None, 0
    while k < n:
        raw = p.stdout.read(W * H * 3)
        if len(raw) < W * H * 3:
            break
        last = Image.frombytes("RGB", (W, H), raw)
        k += 1
        yield last
    p.kill()
    while k < n:  # 素材が足りなければ最後のフレームで埋める
        k += 1
        yield last


def render_frame(shot, base, t):
    img = base
    if shot.freeze:
        z = 1 + 0.03 * ease(t / shot.dur)  # ゆっくりズーム
        if z > 1.001:
            w2, h2 = int(W / z), int(H / z)
            img = img.crop(((W - w2) // 2, (H - h2) // 2, (W + w2) // 2, (H + h2) // 2)).resize((W, H), Image.BILINEAR)
    if shot.blur:
        img = img.filter(ImageFilter.GaussianBlur(shot.blur))
    if shot.dim:
        img = ImageEnhance.Brightness(img).enhance(1 - shot.dim * appear(t, 0, 0.3))
    img = img.convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if shot.overlay:
        shot.overlay(d, t, shot)
    return Image.alpha_composite(img, layer).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=float, nargs="*")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.still:
        starts = np.cumsum([0] + [s.dur for s in SHOTS])
        for ts in a.still:
            i = int(np.searchsorted(starts, ts, side="right") - 1)
            s = SHOTS[i]
            lt = ts - starts[i]
            sub = Shot(**{**s.__dict__, "start": s.start if s.freeze else s.start + lt, "dur": 1 / FPS})
            base = next(frames_of(sub))
            render_frame(s, base, lt).save(OUT / f"still_{ts:05.1f}.png")
        return
    out = OUT / "ep01_v3_video.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                            "-preset", "medium", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    for s in SHOTS:
        for k, base in enumerate(frames_of(s)):
            enc.stdin.write(render_frame(s, base, k / FPS).tobytes())
    enc.stdin.close()
    enc.wait()
    print("wrote", out, timeline())


if __name__ == "__main__":
    main()
