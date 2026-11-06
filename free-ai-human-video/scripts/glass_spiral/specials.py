"""ボールの必殺技。勢いがなくなって止まったボールが、最後に1回だけ技を出して前のガラスを割る。

技はボールが止まった場所から「進む先(うずまきの内側)」にある、まだ割れていないガラスに向かって出る。
どこまで届くかは技ごとに決まっていて(後のボールほど強い)、結果に合わせて変えることはしない。
雷と隕石は、落ちる場所が少しばらつく(乱数・シードで決まる)。

| ボール | 技の名前 | 内容 | 割る枚数の目安 |
|---|---|---|---|
| スーパーボール | スーパーバウンド | その場で3回はねて、1回ごとに1枚 | 3 |
| 木の玉 | ウッドスパイク | 木のトゲを前へ撃ち出す | 5 |
| 鉄球 | アイアンインパクト | 地面をたたいて衝撃波 | 8 |
| 火の玉 | ファイアブレス | 前へ火を吹いて焼きつくす | 12 |
| 雷の玉 | サンダーボルト | 空から3回落雷(1回で5枚) | 最大15 |
| 隕石 | メテオストライク | 空から巨大な隕石が落ちてくる | 最大24 |
"""
import math

import cairo
import numpy as np

NAMES = ["スーパーバウンド", "ウッドスパイク", "アイアンインパクト", "ファイアブレス", "サンダーボルト", "メテオストライク"]
COLORS = [(1.0, 0.45, 0.75), (0.85, 0.6, 0.3), (0.8, 0.85, 0.95), (1.0, 0.5, 0.1), (0.5, 0.75, 1.0), (1.0, 0.35, 0.1)]


def schedule(col, t, ahead, rng):
    """技で割るガラスと、その時刻の一覧 [(時刻, 板の番号)] と、技の終わる時刻、落雷/隕石の位置(ahead の何番目か)。
    ahead は進む先にある割れていないガラス(近い順)。"""
    hits, marks = [], []
    if col == 0:
        hits = [(t + 0.35 + 0.3 * i, k) for i, k in enumerate(ahead[:3])]
    elif col == 1:
        hits = [(t + 0.5 + 0.07 * i, k) for i, k in enumerate(ahead[:5])]
    elif col == 2:
        hits = [(t + 0.55 + 0.035 * i, k) for i, k in enumerate(ahead[:8])]
    elif col == 3:
        hits = [(t + 0.4 + 0.08 * i, k) for i, k in enumerate(ahead[:12])]
    elif col == 4:
        span = max(1, min(len(ahead), 30))
        offs = sorted(int(o) for o in rng.integers(0, span, 3))
        seen = set()
        for j, o in enumerate(offs):
            marks.append(o)
            for i in range(max(0, o - 2), min(len(ahead), o + 3)):
                if ahead[i] not in seen:
                    seen.add(ahead[i])
                    hits.append((t + 0.45 + 0.3 * j, ahead[i]))
    else:
        c = int(rng.integers(6, 16))
        marks.append(c)
        for i in range(max(0, c - 12), min(len(ahead), c + 12)):
            hits.append((t + 0.95 + 0.006 * abs(i - c), ahead[i]))
    end = max([h[0] for h in hits], default=t + 0.6) + 0.5
    end = max(end, t + (1.6 if col >= 4 else 1.2))
    return sorted(hits), end, marks


# ---------------------------------------------------------------- 映像
def _bolt(ctx, x0, y0, x1, y1, rng, width, alpha):
    pts = [(x0, y0)]
    n = 12
    for i in range(1, n):
        f = i / n
        pts.append((x0 + (x1 - x0) * f + rng.uniform(-28, 28), y0 + (y1 - y0) * f + rng.uniform(-10, 10)))
    pts.append((x1, y1))
    for w, a, rgb in ((width * 5, 0.25, (0.5, 0.75, 1)), (width, 1.0, (1, 1, 1))):
        ctx.new_path()
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.set_source_rgba(*rgb, a * alpha)
        ctx.set_line_width(w)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()


def shake(sp, t):
    """画面のゆれ(鉄球・隕石)。"""
    age = t - sp["t"]
    if sp["col"] == 2 and 0.55 <= age < 0.9:
        a = 10 * (1 - (age - 0.55) / 0.35)
    elif sp["col"] == 5 and 0.95 <= age < 1.6:
        a = 26 * (1 - (age - 0.95) / 0.65)
    else:
        return 0.0, 0.0
    return a * math.sin(age * 90), a * math.cos(age * 71)


def draw(ctx, sp, t, rng, draw_ball, text):
    """ctx は盤面の座標(OFFSET_Y でずらした後)。sp は技1回ぶんの情報。"""
    col, x, y, age = sp["col"], sp["x"], sp["y"], t - sp["t"]
    targets = sp["targets"]   # [(時刻, 板, 板の中心x, 板の中心y)]
    # ためのオーラ
    k = min(1.0, age / 0.3)
    pulse = 1 + 0.15 * math.sin(age * 30)
    g = cairo.RadialGradient(x, y, 0, x, y, 70 * k * pulse)
    g.add_color_stop_rgba(0, *COLORS[col], 0.7)
    g.add_color_stop_rgba(1, *COLORS[col], 0)
    ctx.set_source(g)
    ctx.arc(x, y, 70 * k * pulse, 0, 2 * math.pi)
    ctx.fill()
    by = y
    if col == 0:   # その場ではねる(はねるたびに影が小さく、ボールが大きく)
        ph = (age - 0.05) / 0.3
        if 0 <= ph < 3:
            h = math.sin(math.pi * (ph % 1))
            by = y - 0
            r = 19 * (1.15 + 0.6 * h)
            draw_ball(ctx, 0, x, by, age * 6, r, t, 1.0, None)
        else:
            draw_ball(ctx, 0, x, y, 0, 22, t, 1.0, None)
        for tb, _, mx, my in targets:   # はねるたびに衝撃の輪
            a = t - tb
            if 0 <= a < 0.35:
                ctx.set_source_rgba(*COLORS[0], 0.8 * (1 - a / 0.35))
                ctx.set_line_width(4)
                ctx.arc(mx, my, 10 + 120 * a, 0, 2 * math.pi)
                ctx.stroke()
    else:
        draw_ball(ctx, col, x, y, age * 3, 19 * (1.15 if col < 5 else 1.4), t, 1.0, rng)
    if col == 1:   # 木のトゲが飛んでいく
        for tb, _, mx, my in targets:
            f = (age - 0.25) / (tb - sp["t"] - 0.25)
            if 0 <= f <= 1.0 or 0 <= t - tb < 0.15:
                f = min(1.0, max(0.0, f))
                px, py = x + (mx - x) * f, y + (my - y) * f
                ang = math.atan2(my - y, mx - x)
                ctx.save()
                ctx.translate(px, py)
                ctx.rotate(ang)
                ctx.move_to(22, 0)
                ctx.line_to(-18, -7)
                ctx.line_to(-18, 7)
                ctx.close_path()
                ctx.set_source_rgb(0.55, 0.36, 0.18)
                ctx.fill_preserve()
                ctx.set_source_rgb(0.9, 0.7, 0.45)
                ctx.set_line_width(1.5)
                ctx.stroke()
                ctx.restore()
    elif col == 2:   # 衝撃波
        a = age - 0.55
        if 0 <= a < 0.5:
            for d, w in ((0, 10), (0.08, 5)):
                aa = a - d
                if aa > 0:
                    ctx.set_source_rgba(0.85, 0.9, 1, 0.9 * (1 - a / 0.5))
                    ctx.set_line_width(w)
                    ctx.arc(x, y, 20 + 520 * aa, 0, 2 * math.pi)
                    ctx.stroke()
    elif col == 3:   # 火を吹く(炎の粒が、焼く板へ向かって流れる)
        if 0.3 <= age < sp["end"] - sp["t"] - 0.2:
            last = max([tb for tb, *_ in targets if tb <= t], default=None)
            reach = [(mx, my) for tb, _, mx, my in targets if tb <= t + 0.08]
            if not reach and targets:
                reach = [targets[0][2:]]
            for _ in range(26):
                if not reach:
                    break
                mx, my = reach[int(rng.integers(0, len(reach)))]
                f = rng.uniform(0, 1)
                px = x + (mx - x) * f + rng.normal(0, 10 + 18 * f)
                py = y + (my - y) * f + rng.normal(0, 10 + 18 * f)
                rr = 8 + 22 * f
                g = cairo.RadialGradient(px, py, 0, px, py, rr)
                g.add_color_stop_rgba(0, 1, 0.9, 0.5, 0.55)
                g.add_color_stop_rgba(0.5, 1, 0.45, 0.05, 0.35)
                g.add_color_stop_rgba(1, 0.8, 0.1, 0, 0)
                ctx.set_source(g)
                ctx.arc(px, py, rr, 0, 2 * math.pi)
                ctx.fill()
            del last
    elif col == 4:   # 落雷
        for j, o in enumerate(sp["marks"]):
            tb = sp["t"] + 0.45 + 0.3 * j
            a = t - tb
            hit = [tg for tg in targets if abs(tg[0] - tb) < 1e-6]
            if not hit:
                continue
            mx = sum(h[2] for h in hit) / len(hit)
            my = sum(h[3] for h in hit) / len(hit)
            if -0.12 <= a < 0:   # 落ちる直前の予兆
                ctx.set_source_rgba(0.6, 0.8, 1, 0.5)
                ctx.arc(mx, my, 30, 0, 2 * math.pi)
                ctx.fill()
            if 0 <= a < 0.25:
                al = 1 - a / 0.25
                _bolt(ctx, mx + rng.uniform(-60, 60), -400, mx, my, rng, 4, al)
                g = cairo.RadialGradient(mx, my, 0, mx, my, 160)
                g.add_color_stop_rgba(0, 0.9, 0.95, 1, 0.9 * al)
                g.add_color_stop_rgba(1, 0.4, 0.6, 1, 0)
                ctx.set_source(g)
                ctx.arc(mx, my, 160, 0, 2 * math.pi)
                ctx.fill()
    elif col == 5:   # 隕石が空から落ちてくる
        hit = targets
        if hit:
            c = sp["marks"][0]
            cx = sum(h[2] for h in hit) / len(hit)
            cy = sum(h[3] for h in hit) / len(hit)
            ci = [h for h in hit if h[0] == min(hh[0] for hh in hit)]
            cx, cy = ci[0][2], ci[0][3]
            del c
            ti = sp["t"] + 0.95
            a = t - ti
            if -0.75 <= a < 0:   # 右上から落ちてくる
                f = 1 + a / 0.75
                f = f ** 1.6
                sx, sy = cx + 420 * (1 - f), cy - 950 * (1 - f)
                for i in range(10):   # 炎の尾
                    ff = i / 10
                    tx, ty = sx + 90 * ff * 3, sy - 170 * ff * 3
                    g = cairo.RadialGradient(tx, ty, 0, tx, ty, 70 * (1 - ff))
                    g.add_color_stop_rgba(0, 1, 0.8, 0.3, 0.5 * (1 - ff))
                    g.add_color_stop_rgba(1, 1, 0.2, 0, 0)
                    ctx.set_source(g)
                    ctx.arc(tx, ty, 70 * (1 - ff), 0, 2 * math.pi)
                    ctx.fill()
                draw_ball(ctx, 5, sx, sy, a * 4, 75, t, 1.0, rng)
                # 落ちる場所の影
                ctx.set_source_rgba(1, 0.3, 0.1, 0.35 * f)
                ctx.arc(cx, cy, 30 + 120 * f, 0, 2 * math.pi)
                ctx.fill()
            elif 0 <= a < 0.9:   # 大爆発
                al = 1 - a / 0.9
                r = 60 + 380 * (1 - (1 - min(1, a / 0.4)) ** 2)
                g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
                g.add_color_stop_rgba(0, 1, 1, 0.85, 0.95 * al)
                g.add_color_stop_rgba(0.4, 1, 0.6, 0.1, 0.7 * al)
                g.add_color_stop_rgba(1, 0.6, 0.1, 0, 0)
                ctx.set_source(g)
                ctx.arc(cx, cy, r, 0, 2 * math.pi)
                ctx.fill()
                ctx.set_source_rgba(1, 0.85, 0.5, 0.8 * al)
                ctx.set_line_width(6)
                ctx.arc(cx, cy, 40 + 700 * a, 0, 2 * math.pi)
                ctx.stroke()


def draw_name(ctx, sp, t, W, y, text):
    """技の名前を、画面の下側に大きく出す(画面の座標で描く)。"""
    age = t - sp["t"]
    dur = sp["end"] - sp["t"]
    if age < 0 or age > dur:
        return
    k = min(1.0, age / 0.15)
    a = min(1.0, (dur - age) / 0.25)
    size = 92 * (1.35 - 0.35 * k)
    text(ctx, NAMES[sp["col"]] + "!!", W / 2, y, size, rgb=COLORS[sp["col"]], sw=16, alpha=a)


# ---------------------------------------------------------------- 音
def _t(d, sr):
    return np.arange(int(d * sr)) / sr


def _lp(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


def sounds(sp, sr, rng):
    """技1回ぶんの効果音 [(開始時刻, 音)]。"""
    col, t0 = sp["col"], sp["t"]
    out = []
    # ためる音(上がっていく)
    t = _t(0.35, sr)
    f = 300 + 900 * t / 0.35
    out.append((t0, 0.12 * np.sin(2 * np.pi * np.cumsum(f) / sr) * np.minimum(1, t / 0.02) * (1 - t / 0.35)))
    if col == 0:
        for tb, *_ in sp["targets"]:
            t = _t(0.35, sr)
            f = 160 + 500 * np.exp(-t * 18)
            out.append((tb - 0.02, 0.4 * np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 9)))
    elif col == 1:
        for tb, *_ in sp["targets"]:
            t = _t(0.2, sr)
            s = (np.sin(2 * np.pi * 380 * t) + 0.5 * np.sin(2 * np.pi * 870 * t)) * np.exp(-t * 30)
            out.append((tb, 0.35 * s))
        t = _t(0.3, sr)
        out.append((t0 + 0.25, 0.2 * _lp(rng.normal(0, 1, len(t)), 4) * np.exp(-t * 12)))
    elif col == 2:
        t = _t(1.0, sr)
        boom = np.sin(2 * np.pi * np.cumsum(55 + 120 * np.exp(-t * 15)) / sr) * np.exp(-t * 4)
        out.append((t0 + 0.55, 0.6 * boom + 0.25 * _lp(rng.normal(0, 1, len(t)), 10) * np.exp(-t * 8)))
    elif col == 3:
        d = sp["end"] - t0 - 0.3
        t = _t(d, sr)
        n = rng.normal(0, 1, len(t))
        env = np.minimum(1, t / 0.1) * np.minimum(1, (d - t) / 0.25)
        roar = (_lp(n, 14) * 2.5 + _lp(n, 40) * 4) * env * (1 + 0.3 * np.sin(2 * np.pi * 9 * t))
        out.append((t0 + 0.3, 0.32 * roar / np.abs(roar).max()))
    elif col == 4:
        for j in range(len(sp["marks"])):
            tb = t0 + 0.45 + 0.3 * j
            t = _t(1.2, sr)
            n = rng.normal(0, 1, len(t))
            crack = (n - _lp(n, 5)) * np.exp(-t * 25)
            rumble = _lp(_lp(n, 50), 30)
            rumble = rumble / np.abs(rumble).max() * np.exp(-t * 2.5) * np.minimum(1, t / 0.05)
            out.append((tb, 0.55 * crack + 0.5 * rumble))
    else:
        ti = t0 + 0.95
        t = _t(0.75, sr)   # 落ちてくるヒューッ
        f = 1400 - 1100 * t / 0.75
        out.append((ti - 0.75, 0.12 * np.sin(2 * np.pi * np.cumsum(f) / sr) * (t / 0.75)
                    + 0.1 * _lp(rng.normal(0, 1, len(t)), 6) * (t / 0.75)))
        t = _t(2.2, sr)   # ドカーン
        n = rng.normal(0, 1, len(t))
        boom = np.sin(2 * np.pi * np.cumsum(35 + 90 * np.exp(-t * 8)) / sr) * np.exp(-t * 2)
        rum = _lp(_lp(n, 40), 20)
        rum = rum / np.abs(rum).max() * np.exp(-t * 1.8)
        out.append((ti, 0.7 * boom + 0.5 * rum + 0.35 * (n - _lp(n, 4)) * np.exp(-t * 12)))
    return out
