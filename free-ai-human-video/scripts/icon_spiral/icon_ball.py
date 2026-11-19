"""チャンネルのサムネ(アイコン)の「光るボール」の光と、サムネの女の子の顔で、6段階の強さのボールを描く。

ボール本体はサムネの女の子(黒いおかっぱ髪から青白い顔と大きな黒い目がのぞく)の顔。

アイコンのボール:まっ白に光る芯 + 色のついた光の輪(何重かのにじむ光)+ 尾を引く光の軌跡。
7段階(弱い順):ホワイト → ブルー → パープル → グリーン → レッド → ゴールド → レインボー。強いほど光が大きく・明るく、光のトゲも出る。
draw_ball(ctx, kind, x, y, ang, r, t, alpha, rng) は glass_drum.draw_ball と同じ引数(うずまき・大当たり演出からそのまま呼べる)。
drop_sounds(sr) は、ボールが落ちてくる瞬間の音(段階ごとに高く・豪華な「キュイン」)を返す(声は使わない)。
"""
import colorsys
import math
import os

import cairo
import numpy as np

# (名前, -, -, -, -, 光の色)  ※ glass_drum.BALLS と同じ並び(名前と色だけ使う)
BALLS = [("ホワイト", 0, 0, 0, 0, (0.92, 0.95, 1.0)),
         ("ブルー", 0, 0, 0, 0, (0.2, 0.6, 1.0)),
         ("パープル", 0, 0, 0, 0, (0.7, 0.35, 1.0)),
         ("グリーン", 0, 0, 0, 0, (0.25, 1.0, 0.5)),
         ("レッド", 0, 0, 0, 0, (1.0, 0.18, 0.18)),
         ("ゴールド", 0, 0, 0, 0, (1.0, 0.8, 0.2)),
         ("レインボー", 0, 0, 0, 0, None)]
N = len(BALLS)
RAINBOW = N - 1


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
    for mul, a in ((3.2 + 0.25 * kind, 0.18), (2.2 + 0.12 * kind, 0.32), (1.55, 0.55)):
        g = cairo.RadialGradient(0, 0, r * 0.8, 0, 0, r * mul)
        g.add_color_stop_rgba(0, *col, a * alpha)
        g.add_color_stop_rgba(1, *col, 0)
        ctx.arc(0, 0, r * mul, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
    if kind >= 3:   # グリーンから上は光のトゲ(ゆっくり回る)
        n = 8 + 2 * kind
        for j in range(n):
            a = 2 * math.pi * j / n + t * 1.5
            ln = r * (2.2 + 0.5 * (j % 2) + 0.2 * kind)
            c2 = colorsys.hsv_to_rgb((j / n + t * 0.4) % 1, 0.7, 1) if kind == RAINBOW else col
            g = cairo.RadialGradient(0, 0, r, 0, 0, ln)
            g.add_color_stop_rgba(0, *c2, 0.6 * alpha)
            g.add_color_stop_rgba(1, *c2, 0)
            ctx.move_to(0, 0)
            ctx.arc(0, 0, ln, a - 0.06, a + 0.06)
            ctx.close_path()
            ctx.set_source(g)
            ctx.fill()
    # ボール本体:サムネの女の子の顔(転がるぶんだけ回る)
    ctx.rotate(ang)
    draw_face(ctx, r * 1.15, col, alpha)
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


WORDS = ["White!", "Blue!", "Purple!", "Green!", "Red!", "Gold!", "Rainbow!"]
PIPER_MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "source",
                           "icon_spiral", "piper", "en_US-norman-medium.onnx")
_VOICE = {}


def voice(k, sr):
    """ボールが落ちるときの掛け声:色の名前を英語で(White! / Blue! / … / Rainbow!)。
    大人の男性の低くて渋い声。無料のオープンソース音声合成 Piper(MIT)の英語の声「Norman」
    (元の録音は LibriVox のパブリックドメイン)。モデルは assets/source/icon_spiral/piper/(git 管理外)に置く。
    少しだけ低くして(約 -1.5 半音)渋さを足し、強いボールほどゆっくり重く・こだまも深く。"""
    if (k, sr) not in _VOICE:
        import io
        import wave
        from piper import PiperVoice, SynthesisConfig
        v = PiperVoice.load(PIPER_MODEL)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            v.synthesize_wav(WORDS[k], wf, syn_config=SynthesisConfig(length_scale=1.0 + 0.04 * k, noise_scale=0.5))
        buf.seek(0)
        with wave.open(buf) as wf:
            vsr = wf.getframerate()
            x = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(float)
        # 最初のひと声だけ使う(この声は単語のあとに余計な音が続くことがあるので、0.12秒以上の無音で切る)
        e = np.convolve(np.abs(x), np.ones(200) / 200, "same")
        on = e > 0.05 * e.max()
        i0 = int(np.argmax(on))
        gap = int(0.12 * vsr)
        i1 = len(x)
        quiet = 0
        for i in range(i0, len(x)):
            quiet = quiet + 1 if not on[i] else 0
            if quiet >= gap:
                i1 = i - gap
                break
        x = x[max(0, i0 - 200): i1 + int(0.06 * vsr)]
        x = x * np.minimum(1, (len(x) - np.arange(len(x))) / (0.05 * vsr))
        low = 2 ** (-1.5 / 12)   # 少し低く(ゆっくり再生)
        n = int(len(x) / low * sr / vsr)
        y = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
        y = y / (np.abs(y).max() + 1e-9)
        y = np.tanh(1.6 * y) / np.tanh(1.6)   # 少し太く
        for d, g in ((0.11, 0.18 + 0.04 * k), (0.23, 0.08 + 0.03 * k)):   # 会場に響くようなこだま
            m = int(d * sr)
            y = np.concatenate([y, np.zeros(m)])
            y[m:] += g * y[:-m]
        _VOICE[(k, sr)] = y / (np.abs(y).max() + 1e-9)
    return _VOICE[(k, sr)]


def drop_sounds(sr, seed=0):
    """段階ごとに (色の名前の掛け声, 「キュイン」+キラキラ) を返す。強いボールほど高く・長く・音が多い。"""
    out = []
    for k in range(N):
        sw = _kyuin(sr, 400 + 70 * k, 1800 + 260 * k, 0.3 + 0.07 * k, 0.5)
        n = int((0.8 + 0.1 * k) * sr)
        fx = np.zeros(n)
        for j in range(2 + k):
            f = 1047 * 2 ** ((j * 4 + k * 2) / 12)
            b = _bell(sr, f, 0.6, 0.25)
            i = int(j * 0.05 * sr)
            m = min(len(b), n - i)
            fx[i:i + m] += b[:m]
        sfx = np.zeros(max(len(sw), len(fx)))
        sfx[:len(sw)] += sw / (np.abs(sw).max() + 1e-9) * 0.5
        sfx[:len(fx)] += fx / (np.abs(fx).max() + 1e-9) * 0.4
        out.append((voice(k, sr) * 0.9, sfx))
    return out

# ---------------------------------------------------------------- サムネの女の子の顔のボール
def _head_path(ctx, r):
    """おかっぱの頭のシルエット(上は丸い髪、横はまっすぐ、下は平らで角が丸い)。半径 r の円にだいたい収まる大きさ。"""
    ctx.new_path()
    cy = -0.18 * r
    ctx.arc(0, cy, 0.92 * r, math.pi, 2 * math.pi)
    bot = 0.78 * r
    cr = 0.25 * r
    ctx.line_to(0.92 * r, bot - cr)
    ctx.arc(0.92 * r - cr, bot - cr, cr, 0, math.pi / 2)
    ctx.line_to(-0.92 * r + cr, bot)
    ctx.arc(-0.92 * r + cr, bot - cr, cr, math.pi / 2, math.pi)
    ctx.close_path()


def draw_face(ctx, r, col, alpha=1.0):
    """チャンネルのサムネ(アイコン)の女の子:黒いつやつやのおかっぱ髪の下から、青白い顔と大きな黒い目がのぞく。
    髪のふちに、ボールの色の光(リムライト)。"""
    ctx.push_group()
    _head_path(ctx, r)
    g = cairo.LinearGradient(-r * 0.3, -r * 1.1, r * 0.3, r * 0.8)   # 黒い髪(上にツヤ)
    g.add_color_stop_rgb(0, 0.35, 0.36, 0.42)
    g.add_color_stop_rgb(0.25, 0.08, 0.08, 0.1)
    g.add_color_stop_rgb(1, 0.02, 0.02, 0.03)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(*col, 0.95)   # ボールの色のふち
    ctx.set_line_width(max(1.5, r * 0.09))
    ctx.stroke()
    ctx.save()
    _head_path(ctx, r)
    ctx.clip()
    ctx.save()   # 髪のツヤ(天使の輪のような光の帯)
    ctx.translate(-0.05 * r, -0.62 * r)
    ctx.scale(0.62 * r, 0.14 * r)
    ctx.arc(0, 0, 1, math.pi * 1.05, math.pi * 1.95)
    ctx.restore()
    ctx.set_source_rgba(1, 1, 1, 0.5)
    ctx.set_line_width(max(1.0, r * 0.07))
    ctx.stroke()
    # 顔(下の方の窓):青白い肌
    fx, fy0, fy1 = 0.64 * r, -0.1 * r, 0.8 * r
    g = cairo.RadialGradient(0, 0.38 * r, r * 0.05, 0, 0.38 * r, r * 0.7)
    g.add_color_stop_rgb(0, 0.9, 0.94, 0.92)
    g.add_color_stop_rgb(1, 0.5, 0.55, 0.55)
    ctx.rectangle(-fx, fy0, 2 * fx, fy1 - fy0)
    ctx.set_source(g)
    ctx.fill()
    for side in (-1, 1):   # 顔の横の髪の毛すじ
        for j in range(2):
            xx = side * (fx - 0.05 * r * j)
            ctx.move_to(xx, fy0)
            ctx.line_to(xx, fy1)
        ctx.set_source_rgba(0.05, 0.05, 0.06, 0.8)
        ctx.set_line_width(max(0.6, r * 0.025))
        ctx.stroke()
    ctx.set_source_rgb(0.02, 0.02, 0.03)   # 前髪の毛先
    for j in range(6):
        xx = -fx + 2 * fx * (j + 0.5) / 6
        ctx.move_to(xx, fy0 - 1)
        ctx.line_to(xx, fy0 + (0.05 + 0.04 * (j % 3)) * r)
    ctx.set_line_width(max(1.0, r * 0.05))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ey = 0.32 * r   # 大きな黒い目
    for ex in (-0.28 * r, 0.28 * r):
        ctx.save()
        ctx.translate(ex, ey)
        ctx.scale(0.18 * r, 0.23 * r)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(0, 0, 0)
        ctx.fill()
        ctx.arc(ex + 0.03 * r, ey + 0.05 * r, max(0.8, 0.04 * r), 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 0.88)
        ctx.fill()
    ctx.restore()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
