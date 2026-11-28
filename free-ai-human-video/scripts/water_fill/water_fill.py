"""「虹色の水でコップを満タンにできる?」
上の蛇口から虹色の水(小さな粒)が流れ出る。斜めの板 → 水の勢いで回る水車 → 穴のあいた反対向きの板 → 下のコップ。
穴から落ちた水や、水車ではねて外に飛んだ水はこぼれてしまう。とちゅうで蛇口が全開になって水の量がふえる。
TIME_LIMIT 秒以内にコップの線まで水がたまれば成功(大当たり演出)、こぼれて足りなければ失敗(幽霊 → 暗くなって「Failed...」)。

- 水は小さな円の粒(物理エンジン pymunk。重力・衝突・まさつなし)。見た目は粒をぼかしてつなげ、水のように見せる。
- 水車は、水が当たった力だけで回る(モーターなし)。
- ねらい・補正なし。シードで変わるのは、蛇口から出る水のほんの少しのばらつきだけ。

使い方:
    python water_fill.py search [-n 80]
    python water_fill.py render --seed N
"""

import argparse
import colorsys
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import cairo
import numpy as np
import pymunk
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ball_escape"))
from ball_escape import midi_hz  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from fail_bgm import fail_music  # noqa: E402
from pachinko import RainbowFever, hsv, kyuin_music  # noqa: E402
from flashy import PALETTE, chic, draw_ball as shiny_ball, giragira, horror, kyuin_one  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "glass_spiral"))
import jackpot_end as JP  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = int(os.environ.get("SUBSTEPS", 4))
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

GRAVITY = float(os.environ.get("GRAVITY", 1400.0))
PR = float(os.environ.get("PR", 6.0))              # 水の粒の半径
RATE1 = float(os.environ.get("RATE1", 32.0))       # はじめの水の量(粒/秒)
RATE2 = float(os.environ.get("RATE2", 64.0))      # 全開のあとの水の量
FULL_T = float(os.environ.get("FULL_T", 12.0))     # 蛇口が全開になる時間
SPOUT = (262.0, 440.0)
SPOUT_V = float(os.environ.get("SPOUT_V", 230.0))
JIT = float(os.environ.get("JIT", 30.0))           # 出る水のばらつき(px/秒)
# 水車
WH_C = (800.0, 700.0)
WH_R = float(os.environ.get("WH_R", 105.0))
WH_N = 6
WH_M = float(os.environ.get("WH_M", 40.0))
# コップ
CUP_X0, CUP_X1, CUP_Y1 = 170.0, 560.0, 1560.0
LINE_Y = float(os.environ.get("LINE_Y", 1300.0))   # この線まで水がたまれば満タン
HOLE = float(os.environ.get("HOLE", 28.0))         # 板Bの穴のはば
HOLES = (650.0, 830.0)                             # 板Bの穴の位置(x)
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 26.41))
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG
CELL_A = (2 * PR) ** 2 * math.sqrt(3) / 2
N_FULL = int(float(os.environ.get("PACK", 0.92)) * (CUP_X1 - CUP_X0 - 8) * (CUP_Y1 - LINE_Y) / CELL_A)

def plate_b():
    """板B(右から左に下がる)。とちゅうに穴が2つ。"""
    x0, y0, x1, y1 = 1000.0, 840.0, 300.0, 1035.0
    yy = lambda x: y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    cuts = sorted(HOLES, reverse=True)
    segs, cx = [], x0
    for h in cuts:
        segs.append(((cx, yy(cx)), (h + HOLE / 2, yy(h + HOLE / 2))))
        cx = h - HOLE / 2
    segs.append(((cx, yy(cx)), (x1, y1)))
    return segs


PLATES = [   # 板(とちゅうの線)
    ((175.0, 400.0), (175.0, 470.0)),     # 蛇口のうしろのかべ
    ((175.0, 470.0), (690.0, 600.0)),     # 板A(右に下がる)
    ((1000.0, 620.0), (1000.0, 840.0)),   # 右のかべ
    ((230.0, 960.0), (230.0, 1080.0)),    # 板Bの先の受け止めかべ
    ((CUP_X0, 1250.0), (CUP_X0, CUP_Y1)),
    ((CUP_X1, 1250.0), (CUP_X1, CUP_Y1)),
    ((CUP_X0, CUP_Y1), (CUP_X1, CUP_Y1)),
] + plate_b()


class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 12
        sp.collision_slop = 0.3
        self.space = sp
        st = sp.static_body
        for a, b in PLATES:
            s = pymunk.Segment(st, a, b, 4)
            s.elasticity, s.friction = 0.0, 0.0
            sp.add(s)
        # 水車(自由に回る)
        wb = pymunk.Body(WH_M, WH_M * WH_R * WH_R / 2)
        wb.position = WH_C
        sp.add(wb, pymunk.PivotJoint(st, wb, WH_C))
        for k in range(WH_N):
            a = 2 * math.pi * k / WH_N
            s = pymunk.Segment(wb, (0, 0), (WH_R * math.cos(a), WH_R * math.sin(a)), 5)
            s.elasticity, s.friction = 0.0, 0.3
            sp.add(s)
        hub = pymunk.Circle(wb, 18)
        sp.add(hub)
        self.wheel = wb
        self.parts = []      # [body, shape, hue]
        self.t = 0.0
        self.emit_acc = 0.0
        self.emitted = 0
        self.events = []
        self.result, self.result_t = None, None
        self.in_cup = 0
        self.full_on = False

    def emit(self, n):
        for _ in range(n):
            b = pymunk.Body(1.0, float("inf"))
            b.position = (SPOUT[0] + self.rng.uniform(-2, 2), SPOUT[1] + self.rng.uniform(-6, 6))
            b.velocity = (SPOUT_V + self.rng.normal(0, JIT), self.rng.normal(0, JIT))
            s = pymunk.Circle(b, PR)
            s.elasticity, s.friction = 0.0, 0.0
            self.space.add(b, s)
            self.parts.append([b, s, (self.emitted * 0.0025) % 1.0])
            self.emitted += 1

    def step(self, dt):
        self.t += dt
        if self.result is None:
            if not self.full_on and self.t >= FULL_T:
                self.full_on = True
                self.events.append(("full", self.t, None))
            rate = RATE2 if self.full_on else RATE1
            self.emit_acc += rate * dt
            n = int(self.emit_acc)
            if n:
                self.emit_acc -= n
                self.emit(n)
        self.space.step(dt)
        keep = []
        for p in self.parts:
            if p[0].position.y > H + 40 or p[0].position.x < -40 or p[0].position.x > W + 40:
                self.space.remove(p[0], p[1])
                continue
            keep.append(p)
        self.parts = keep

    def count_cup(self):
        n = 0
        for b, _, _ in self.parts:
            x, y = b.position
            if CUP_X0 < x < CUP_X1 and y < CUP_Y1 and y > 1240:
                n += 1
        return n


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        g.in_cup = g.count_cup()
        if g.result is None:
            if g.in_cup >= N_FULL:
                g.result, g.result_t = "success", g.t
                g.events.append(("success", g.t, None))
            elif g.t >= TIME_LIMIT:
                g.result, g.result_t = "fail", g.t
                g.events.append(("fail", g.t, None))
        if record:
            frames.append({"t": g.t, "n": g.in_cup,
                           "p": np.array([(b.position.x, b.position.y, h) for b, _, h in g.parts]) if g.parts else np.zeros((0, 3)),
                           "wa": g.wheel.angle})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "n": g.in_cup,
            "emitted": g.emitted}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), r["n"], round(r["n"] / N_FULL, 3)


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件 (満タン {N_FULL} 粒)")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    shiny_ball(ctx, x, y, r * 0.8, PALETTE[(kind * 12 // 7) % 12])


def failed_text(ctx, s, x, y, size, alpha):
    """失敗の文字:Playfair Display の斜体。暗い赤で、うっすら赤黒くにじむ。"""
    if alpha <= 0:
        return
    ctx.select_font_face("Playfair Display", cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    e = ctx.text_extents(s)
    if e.width > W * 0.86:
        size *= W * 0.86 / e.width
        ctx.set_font_size(size)
        e = ctx.text_extents(s)
    tx = x - e.width / 2 - e.x_bearing
    for wd, al in ((30, 0.10), (16, 0.18)):
        ctx.move_to(tx, y)
        ctx.text_path(s)
        ctx.set_source_rgba(0.45, 0.02, 0.05, al * alpha)
        ctx.set_line_width(wd)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    g = cairo.LinearGradient(0, y - size * 0.8, 0, y + size * 0.1)
    g.add_color_stop_rgba(0, 0.85, 0.25, 0.28, alpha)
    g.add_color_stop_rgba(1, 0.45, 0.05, 0.08, alpha)
    ctx.move_to(tx, y)
    ctx.text_path(s)
    ctx.set_source(g)
    ctx.fill()


SC = 0.5                       # 水の絵は半分の大きさで作ってから広げる
HW_, HH_ = int(W * SC), int(H * SC)
_HUES = np.array([colorsys.hsv_to_rgb(k / 64, 0.8, 1.0) for k in range(64)])


def water_layer(p):
    """水の粒をぼかしてつなげ、なめらかな虹色の水にする(メタボール)。"""
    acc = np.zeros((HH_, HW_, 3))
    den = np.zeros((HH_, HW_))
    if len(p):
        xs = np.clip((p[:, 0] * SC).astype(int), 0, HW_ - 1)
        ys = np.clip((p[:, 1] * SC).astype(int), 0, HH_ - 1)
        cols = _HUES[(p[:, 2] * 64).astype(int) % 64]
        np.add.at(den, (ys, xs), 1.0)
        for c in range(3):
            np.add.at(acc[:, :, c], (ys, xs), cols[:, c])
    sig = PR * SC * 0.95
    d = ndimage.gaussian_filter(den, sig)
    col = np.stack([ndimage.gaussian_filter(acc[:, :, c], sig) for c in range(3)], axis=2)
    col = col / np.maximum(d, 1e-6)[:, :, None]
    lv = 1.0 / (2 * math.pi * sig * sig)            # 1粒の中心の濃さ
    a = np.clip((d / lv - 0.32) / 0.25, 0, 1)
    a = a * a * (3 - 2 * a)
    edge = np.clip(1 - np.abs(d / lv - 0.45) / 0.18, 0, 1) * 0.35   # ふちを少し明るく
    rgb = np.clip(col * 0.92 + edge[:, :, None], 0, 1)
    al = a * 0.93
    buf = np.zeros((HH_, HW_, 4), np.uint8)
    buf[:, :, 0] = (rgb[:, :, 2] * al * 255).astype(np.uint8)
    buf[:, :, 1] = (rgb[:, :, 1] * al * 255).astype(np.uint8)
    buf[:, :, 2] = (rgb[:, :, 0] * al * 255).astype(np.uint8)
    buf[:, :, 3] = (al * 255).astype(np.uint8)
    return buf


def draw_static(bc):
    bc.set_source_rgb(0.03, 0.035, 0.06)
    bc.paint()
    # 板
    for a, b in PLATES:
        if CUP_X0 - 1 <= a[0] <= CUP_X1 + 1 and a[1] >= 1240:
            continue
        bc.move_to(*a)
        bc.line_to(*b)
    bc.set_line_cap(cairo.LINE_CAP_ROUND)
    for wd, rgba in ((16, (0.6, 0.8, 1.0, 0.12)), (8, (0.75, 0.85, 0.95, 1.0))):
        bc.set_source_rgba(*rgba)
        bc.set_line_width(wd)
        bc.stroke_preserve()
    bc.new_path()
    # 穴のまわりに赤い印
    for h in HOLES:
        y = 840.0 + (1035.0 - 840.0) * (h - 1000.0) / (300.0 - 1000.0)
        bc.arc(h, y + 2, HOLE / 2 + 6, 0, math.pi)
        bc.set_source_rgba(1.0, 0.3, 0.35, 0.8)
        bc.set_line_width(3)
        bc.stroke()
    # コップ(ガラス)
    bc.rectangle(CUP_X0, 1250, CUP_X1 - CUP_X0, CUP_Y1 - 1250)
    bc.set_source_rgba(0.7, 0.85, 1.0, 0.06)
    bc.fill()
    bc.move_to(CUP_X0, 1250)
    bc.line_to(CUP_X0, CUP_Y1)
    bc.line_to(CUP_X1, CUP_Y1)
    bc.line_to(CUP_X1, 1250)
    for wd, rgba in ((18, (0.7, 0.9, 1.0, 0.1)), (6, (0.85, 0.93, 1.0, 0.95))):
        bc.set_source_rgba(*rgba)
        bc.set_line_width(wd)
        bc.stroke_preserve()
    bc.new_path()
    # 蛇口
    bc.rectangle(120, SPOUT[1] - 22, SPOUT[0] - 120, 44)
    g = cairo.LinearGradient(0, SPOUT[1] - 22, 0, SPOUT[1] + 22)
    g.add_color_stop_rgb(0, 0.95, 0.96, 1.0)
    g.add_color_stop_rgb(0.5, 0.6, 0.64, 0.72)
    g.add_color_stop_rgb(1, 0.35, 0.38, 0.45)
    bc.set_source(g)
    bc.fill()
    bc.rectangle(150, 360, 40, SPOUT[1] - 382)
    bc.set_source(g)
    bc.fill()


def draw_line(ctx, t, glow):
    """満タンの線(金色の点線)。"""
    ctx.set_dash([18, 12])
    ctx.move_to(CUP_X0 + 8, LINE_Y)
    ctx.line_to(CUP_X1 - 8, LINE_Y)
    ctx.set_source_rgba(1.0, 0.82, 0.3, 0.6 + 0.4 * glow)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.set_dash([])


def draw_wheel(ctx, ang):
    cx, cy = WH_C
    for k in range(WH_N):
        a = ang + 2 * math.pi * k / WH_N
        ctx.move_to(cx, cy)
        ctx.line_to(cx + WH_R * math.cos(a), cy + WH_R * math.sin(a))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for wd, rgb in ((14, (0.55, 0.35, 0.1)), (8, (1.0, 0.78, 0.3))):
        ctx.set_source_rgb(*rgb)
        ctx.set_line_width(wd)
        ctx.stroke_preserve()
    ctx.new_path()
    ctx.arc(cx, cy, 20, 0, 2 * math.pi)
    ctx.set_source_rgb(1.0, 0.85, 0.4)
    ctx.fill()
    ctx.arc(cx, cy, 7, 0, 2 * math.pi)
    ctx.set_source_rgb(0.5, 0.3, 0.08)
    ctx.fill()


def draw_handle(ctx, k):
    """蛇口のハンドル:全開で回る。"""
    cx, cy = 170, 350
    a = -0.4 + k * 1.4
    for s in (0, math.pi):
        ctx.move_to(cx, cy)
        ctx.line_to(cx + 40 * math.cos(a + s), cy + 14 * math.sin(a + s))
    ctx.set_source_rgb(1.0, 0.35, 0.4)
    ctx.set_line_width(10)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.arc(cx, cy, 10, 0, 2 * math.pi)
    ctx.set_source_rgb(0.9, 0.9, 1.0)
    ctx.fill()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"water_fill_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"water_fill_{seed}.wav")
    final = os.path.join(OUT_DIR, f"water_fill_{seed}.mp4")
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    if preview:
        class _P:
            def __init__(self):
                self.stdin = self
                self.fi = 0

            def write(self, _):
                t_ = (self.fi + 1) / FPS
                for pt in preview:
                    if abs(t_ - pt) < 0.5 / FPS:
                        surf.write_to_png(os.path.join(OUT_DIR, f"wf_preview_{seed}_{pt:.1f}.png"))
                self.fi += 1
        ff = _P()
        frames = [f for f in frames if f["t"] <= max(preview) + 0.05]
    else:
        ff = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
             "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
            stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    ending = None if fail else JP.Jackpot(W, H, seed, (CUP_X0 + CUP_X1) / 2, 1100, reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=("Congratulations!!", "FULL", ""), font="Playfair Display", slim=True)
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    base = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    draw_static(cairo.Context(base))
    wsurf = cairo.ImageSurface(cairo.FORMAT_ARGB32, HW_, HH_)
    full_t = next((t for k, t, _ in events if k == "full"), 1e9)
    frozen = None
    for fi, fr in enumerate(frames):
        t = fr["t"]
        over = end_t is not None and t >= end_t
        win_b = (t - end_t) if (ending is not None and over) else -1.0
        if win_b >= PRE:
            ending.draw(surf, ctx, win_b - PRE + JP.T_BIG)
            giragira(ctx, win_b - PRE, fever, glints, W, H, WIN_DUR)
            ff.stdin.write(surf.get_data())
            continue
        if fail and over:   # 失敗した瞬間の様子で止める
            if frozen is None:
                frozen = fr
            fr = frozen
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        ctx.set_source_surface(base, 0, 0)
        ctx.paint()
        draw_handle(ctx, min(1.0, max(0.0, (t - full_t) / 0.4)))
        draw_wheel(ctx, fr["wa"])
        # 水
        buf = water_layer(fr["p"])
        wsurf.flush()
        np.ndarray((HH_, wsurf.get_stride() // 4, 4), np.uint8, wsurf.get_data())[:, :HW_] = buf
        wsurf.mark_dirty()
        ctx.save()
        ctx.scale(1 / SC, 1 / SC)
        ctx.set_source_surface(wsurf, 0, 0)
        ctx.get_source().set_filter(cairo.FILTER_BILINEAR)
        ctx.paint()
        ctx.restore()
        frac = fr["n"] / N_FULL
        draw_line(ctx, t, 0.5 + 0.5 * math.sin(t * 6) if frac > 0.85 else 0.0)
        # 全開のしるし
        if 0 <= t - full_t < 1.2:
            k = (t - full_t) / 1.2
            chic(ctx, "全開!", 330, 330 - 20 * k, 50, rgb=(1, 0.55, 0.5), alpha=1 - k * k)
        # 文字
        chic(ctx, "満タンにできる？", W / 2, 200, 62, rgb=(1, 0.88, 0.6))
        pct = min(100, int(frac * 100))
        chic(ctx, f"{pct}%", W / 2 - 110, 310, 84, rgb=(1, 1, 1), weight="Medium")
        tt = min(t, end_t) if end_t is not None else t
        lft = max(0.0, TIME_LIMIT - tt)
        chic(ctx, f"{lft:4.1f}", W / 2 + 130, 305, 44, rgb=(1, 0.45, 0.45) if lft < 5 else (0.7, 0.75, 0.85), weight="Medium")
        if not over:
            horror(ctx, "失敗したら…", W / 2, 1680, 74, t)
        if over and fail:
            ctx.set_operator(cairo.OPERATOR_HSL_SATURATION)
            ctx.set_source_rgba(0.5, 0.5, 0.5, min(1.0, after / 0.8))
            ctx.paint()
            ctx.set_operator(cairo.OPERATOR_OVER)
            ctx.set_source_rgba(0, 0, 0, 0.6 * min(1.0, after / 1.2))
            ctx.paint()
            vg = cairo.RadialGradient(W / 2, H / 2, 300, W / 2, H / 2, 1150)
            vg.add_color_stop_rgba(0, 0, 0, 0, 0)
            vg.add_color_stop_rgba(1, 0, 0, 0, 0.85 * min(1.0, after / 1.2))
            ctx.set_source(vg)
            ctx.paint()
            k = min(1.0, max(0.0, (after - 0.2) / 1.4))
            k = k * k * (3 - 2 * k)
            failed_text(ctx, "Failed...", W / 2, 1010 + 40 * (1 - k), 160, k)
        if win_b >= 0:
            k = win_b / PRE
            ph_ = (win_b * (8 + 14 * k)) % 1.0
            ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*hsv(win_b * 4), (0.25 + 0.4 * k) * (1 - ph_) ** 2)
            ctx.paint()
            ctx.set_operator(cairo.OPERATOR_OVER)
            if k > 0.75:
                ctx.set_source_rgba(1, 1, 1, ((k - 0.75) / 0.25) ** 2)
                ctx.paint()
        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
    if preview:
        return
    ff.stdin.close()
    ff.wait()
    duration = len(frames) / FPS
    synth_audio(res, duration, wav)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(silent)
    os.remove(wav)
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['n']}/{N_FULL}粒 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def synth_audio(res, duration, path):
    events, end_t, fail, frames = res["events"], res["result_t"], res["result"] == "fail", res["frames"]
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)
    rng = np.random.default_rng(4)
    # 水の流れる「サー」:画面の水の量に合わせた、こもったノイズ
    fl = SR // FPS
    nz = rng.normal(0, 1, n_out)
    lp = ndimage.uniform_filter1d(nz, 9)
    lp = lp - ndimage.uniform_filter1d(lp, 200)
    amp = np.zeros(n_out)
    prev_n = 0
    last = -1.0
    for fr in frames:
        if fr["t"] > end_t:
            break
        i = int((fr["t"] - 1 / FPS) * SR)
        amp[i:i + fl] = min(1.0, len(fr["p"]) / 900)
        dn = fr["n"] - prev_n
        prev_n = fr["n"]
        if dn > 0 and fr["t"] - last > 0.07:   # コップにたまる「ポチャ」(たまるほど音が上がる)
            last = fr["t"]
            frac = fr["n"] / N_FULL
            f0 = midi_hz(55 + int(frac * 24))
            tt = _t(0.14)
            fsw = f0 * (1 + 1.2 * np.exp(-tt / 0.02))
            sig = np.sin(2 * np.pi * np.cumsum(fsw) / SR) * np.exp(-tt / 0.04) * min(1.0, 0.3 + dn / 6)
            j = min(n_out, i + len(sig))
            out[i:j] += 0.6 * sig[: j - i]
    amp = ndimage.uniform_filter1d(amp, SR // 10)
    out += 1.2 * lp * amp
    for k, t, _ in events:
        if k == "full" and t < end_t:
            sig = 0.7 * kyuin_one(1.2)
            i = int(t * SR)
            out[i:i + len(sig)] += sig[: max(0, n_out - i)]
    wet = out.copy()
    for dd, g_ in ((0.083, 0.2), (0.131, 0.12)):
        kk = int(dd * SR)
        wet[kk:] += out[:-kk] * g_
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int(end_t * SR)]
    rms = np.sqrt(np.mean(body ** 2))
    if rms > 0:
        wet *= min(6.0, 10 ** (-15.0 / 20) / rms)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
        sig = fail_music(SR, OUTRO)
        i0 = int((end_t + SCARE_DUR) * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += 0.6 * sig[:m]
    else:
        b_ = JP.music(SR, 3)
        b_ = b_.mean(axis=1) if b_.ndim == 2 else b_
        b_ = b_[int(JP.T_BIG * SR) - int(0.05 * SR):]
        n = int(WIN_DUR * SR)
        mus = np.zeros(n)
        mus[:min(n, len(b_))] += b_[:n] / (np.abs(b_).max() + 1e-9)
        a_ = kyuin_music(SR, WIN_DUR)
        mus[:min(n, len(a_))] += 0.8 * a_[:n]
        t2 = 0.0
        while t2 < WIN_DUR - 0.5:
            ky = kyuin_one(1.0 + 0.15 * ((int(t2 / 0.3)) % 3))
            i = int(t2 * SR)
            m = min(len(ky), n - i)
            mus[i:i + m] += 0.4 * ky[:m]
            t2 += 0.3
        tb = np.arange(int(1.5 * SR)) / SR
        boom = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-tb * 6) + 35) / SR) * np.exp(-tb * 2.5)
        mus[:len(boom)] += 0.9 * boom
        mus *= np.minimum(1, (WIN_DUR - np.arange(n) / SR) / 0.6)
        mus = np.tanh(1.6 * mus / (np.abs(mus).max() + 1e-9)) / np.tanh(1.6)
        i0 = int((end_t + PRE) * SR)
        m = min(len(mus), n_out - i0)
        extra[i0:i0 + m] += 1.1 * mus[:m]
        t2 = 0.0
        while t2 < PRE - 0.05:
            k = t2 / PRE
            ky = kyuin_one(1.0 + 0.6 * k)
            i = int((end_t + t2) * SR)
            m = min(len(ky), n_out - i)
            extra[i:i + m] += (0.35 + 0.35 * k) * ky[:m]
            t2 += 0.11 - 0.05 * k
    wet = wet + 0.95 * extra[: len(wet)]
    mag = np.abs(wet)
    wet = np.where(mag < 0.7, wet, np.sign(wet) * (0.7 + 0.2 * np.tanh((mag - 0.7) / 0.2)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


def debug(seed, times):
    """配置をたしかめる簡単な絵。"""
    g = Game(seed)
    dt = 1 / FPS / SUBSTEPS
    for T in times:
        while g.t < T:
            g.step(dt)
        s = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
        c = cairo.Context(s)
        c.set_source_rgb(0.05, 0.05, 0.08)
        c.paint()
        c.set_source_rgb(0.8, 0.8, 0.9)
        c.set_line_width(8)
        for sh in g.space.shapes:
            if isinstance(sh, pymunk.Segment):
                a = sh.body.local_to_world(sh.a)
                b = sh.body.local_to_world(sh.b)
                c.move_to(*a)
                c.line_to(*b)
                c.stroke()
        for b, _, h in g.parts:
            c.arc(b.position.x, b.position.y, PR, 0, 2 * math.pi)
            c.set_source_rgb(*colorsys.hsv_to_rgb(h, 0.8, 1))
            c.fill()
        c.move_to(CUP_X0, LINE_Y)
        c.line_to(CUP_X1, LINE_Y)
        c.set_source_rgb(1, 0.3, 0.3)
        c.set_line_width(2)
        c.stroke()
        c.select_font_face("sans")
        c.set_font_size(40)
        c.move_to(60, 120)
        c.show_text(f"t={g.t:.1f} cup={g.count_cup()}/{N_FULL} parts={len(g.parts)}")
        s.write_to_png(os.path.join(OUT_DIR, f"wf_dbg_{T:.0f}.png"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render", "debug"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("-n", type=int, default=80)
    ap.add_argument("--times", default="3,8,15,25")
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    elif a.mode == "debug":
        debug(a.seed, [float(x) for x in a.times.split(",")])
    else:
        render(a.seed)
