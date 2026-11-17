"""チャンネルのサムネ(アイコン)に描いてある「光る白いボール」を、6段階の強さで描く。

アイコンのボール:まっ白に光る芯 + 色のついた光の輪(何重かのにじむ光)+ 尾を引く光の軌跡。
6段階(弱い順):ブルー → ピンク → パープル → グリーン → ゴールド → レインボー。強いほど光が大きく・明るく、光のトゲも出る。
draw_ball(ctx, kind, x, y, ang, r, t, alpha, rng) は glass_drum.draw_ball と同じ引数(うずまき・大当たり演出からそのまま呼べる)。
drop_sounds(sr) は、ボールが落ちてくる瞬間の音(段階ごとに高く・豪華な「キュイン」)を返す(声は使わない)。
"""
import colorsys
import math

import cairo
import numpy as np

# (名前, -, -, -, -, 光の色)  ※ glass_drum.BALLS と同じ並び(名前と色だけ使う)
BALLS = [("ブルー", 0, 0, 0, 0, (0.2, 0.6, 1.0)),
         ("ピンク", 0, 0, 0, 0, (1.0, 0.3, 0.62)),
         ("パープル", 0, 0, 0, 0, (0.7, 0.35, 1.0)),
         ("グリーン", 0, 0, 0, 0, (0.25, 1.0, 0.5)),
         ("ゴールド", 0, 0, 0, 0, (1.0, 0.8, 0.2)),
         ("レインボー", 0, 0, 0, 0, None)]


def color(kind, t):
    c = BALLS[kind][5]
    if c is None:
        return colorsys.hsv_to_rgb((t * 0.6) % 1.0, 0.8, 1.0)
    return c


def draw_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    col = color(kind, t)
    ctx.save()
    ctx.translate(x, y)
    # 光の輪(アイコンと同じ:外側ほど薄い、何重かの色の輪)
    for mul, a in ((3.4 + 0.25 * kind, 0.18), (2.3 + 0.12 * kind, 0.32), (1.55, 0.55)):
        g = cairo.RadialGradient(0, 0, r * 0.8, 0, 0, r * mul)
        g.add_color_stop_rgba(0, *col, a * alpha)
        g.add_color_stop_rgba(1, *col, 0)
        ctx.arc(0, 0, r * mul, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
    if kind >= 3:   # 強いボールは光のトゲ(ゆっくり回る)
        n = 8 + 2 * kind
        for j in range(n):
            a = 2 * math.pi * j / n + t * 1.5
            ln = r * (2.2 + 0.5 * (j % 2) + 0.2 * kind)
            c2 = colorsys.hsv_to_rgb((j / n + t * 0.4) % 1, 0.7, 1) if kind == 5 else col
            g = cairo.RadialGradient(0, 0, r, 0, 0, ln)
            g.add_color_stop_rgba(0, *c2, 0.6 * alpha)
            g.add_color_stop_rgba(1, *c2, 0)
            ctx.move_to(0, 0)
            ctx.arc(0, 0, ln, a - 0.06, a + 0.06)
            ctx.close_path()
            ctx.set_source(g)
            ctx.fill()
    # まっ白に光る芯
    g = cairo.RadialGradient(-r * 0.2, -r * 0.25, r * 0.05, 0, 0, r)
    g.add_color_stop_rgba(0, 1, 1, 1, alpha)
    g.add_color_stop_rgba(0.75, 1, 1, 1, alpha)
    g.add_color_stop_rgba(1, *(0.75 + 0.25 * c for c in col), alpha)
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    ctx.restore()


# ---------------------------------------------------------------- 音
def _kyuin(sr, f0, f1, dur, amp):
    t = np.arange(int(dur * sr)) / sr
    f = f0 + (f1 - f0) * (1 - np.exp(-t / (dur * 0.3)))
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.02 * np.sin(2 * np.pi * 28 * t))) / sr
    y = np.sin(ph) + 0.3 * np.sin(2 * ph)
    return amp * y * np.minimum(1, t / 0.01) * np.minimum(1, (dur - t) / 0.08)


def _bell(sr, f, dur, amp):
    t = np.arange(int(dur * sr)) / sr
    return amp * (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t * 6)) * np.exp(-t * 3)


def drop_sounds(sr, seed=0):
    """段階ごとに (落ちる瞬間の「キュイン」, キラキラ) を返す。強いボールほど高く・長く・音が多い。"""
    out = []
    for k in range(6):
        sw = _kyuin(sr, 400 + 80 * k, 1800 + 300 * k, 0.3 + 0.08 * k, 0.5)
        n = int((0.8 + 0.1 * k) * sr)
        fx = np.zeros(n)
        for j in range(2 + k):
            f = 1047 * 2 ** ((j * 4 + k * 2) / 12)
            b = _bell(sr, f, 0.6, 0.25)
            i = int(j * 0.05 * sr)
            m = min(len(b), n - i)
            fx[i:i + m] += b[:m]
        out.append((sw / (np.abs(sw).max() + 1e-9) * 0.5, fx / (np.abs(fx).max() + 1e-9) * 0.4))
    return out
