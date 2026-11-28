"""「ニュートンのゆりかごで、金の鐘を鳴らせる?」
上の棒から虹色の鉄球が糸で一列につり下がっている(左から大きい球 → 小さい球)。
左のモーターつきハンマーが PERIOD 秒ごとに、左はしの球をたたく。勢いは「カチン!」と球から球へ伝わり、
重い球が軽い球に当たると軽い球は速く飛び出すので、小さい球ほど勢いがます。
右はしのいちばん小さい球が大きく振り上がって、右上の金の鐘に当たれば成功(大当たり演出)。
TIME_LIMIT 秒までに鳴らせなければ失敗(幽霊 → 暗くなって「Failed...」)。

- 物理エンジン pymunk。球は糸(たるむ・のびない)でつるした剛体の円。球どうしの衝突は はねかえり係数 E。
- ハンマーは決まった動きをくり返すだけ(ねらい・補正なし)。シードで変わるのは、球と球のすき間(0〜1.5px)と
  はじめの球の位置のほんのわずかなずれだけ。前の揺れが残っているので、たたくたびに伝わり方がかわる(カオス)。

使い方:
    python cradle.py search [-n 80]
    python cradle.py render --seed N
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
SUBSTEPS = int(os.environ.get("SUBSTEPS", 10))
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

GRAVITY = float(os.environ.get("GRAVITY", 1500.0))
E = float(os.environ.get("E", 0.93))                 # 球どうしのはねかえり係数
GROUPS = [(36, 4), (27, 4), (20, 4), (14, 3)]        # (半径, 個数) 大きい球 → 小さい球
RF = 11.0                                            # 右はしの球
BAR_Y = 640.0                                        # つり下げる棒
Y0 = 1150.0                                          # 球の中心の高さ
LF = 170.0                                           # 右はしの球の糸の長さ
X_START = 70.0
GAP = float(os.environ.get("GAP", 1.5))              # 球と球のすき間(0〜GAP のランダム)
# ハンマー
HL = 420.0
HR = 44.0
UP = float(os.environ.get("UP", 0.12))               # 1回目にふり上げる角度(ラジアン)
DUP = float(os.environ.get("DUP", 0.02))            # たたくたびにふり上げる角度がこれだけふえる(パワーアップ)
SW = float(os.environ.get("SW", 0.8))                # ふりおろす時間
FT = float(os.environ.get("FT", 0.1))                # 振りぬく角度
PERIOD = float(os.environ.get("PERIOD", 4.0))
# 鐘
BELL_A = float(os.environ.get("BELL_A", 135.0))      # 右はしの球の糸の角度(下から・度)で鐘のある所
BELL_R = 30.0
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 30.5))
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG


def layout(rng):
    """球の位置・半径・糸の長さ・つり下げ点。"""
    out = []
    x = X_START
    rs = [r for r, n in GROUPS for _ in range(n)] + [RF]
    for i, r in enumerate(rs):
        x += r
        ls = LF if i == len(rs) - 1 else Y0 - BAR_Y
        out.append({"r": float(r), "x": x, "L": ls, "anchor": (x, Y0 - ls), "g": min(len(GROUPS), sum(1 for _ in range(1))) })
        x += r + (rng.uniform(0, GAP) if rng is not None else GAP / 2)
    return out


_L0 = layout(None)
PF = _L0[-1]["anchor"]
BELL = (PF[0] + LF * math.sin(math.radians(BELL_A)), PF[1] + LF * math.cos(math.radians(BELL_A)))


def hammer_ang(t):
    """ハンマーの角度(下向き 0・左がプラス)。PERIOD 秒ごとに1回たたく(モーターの決まった動き)。
    たたくたびに少しずつ高くふり上げる(だんだん強くなる)。"""
    n = int(t // PERIOD)
    k = t % PERIOD
    up = UP + DUP * n
    up_next = UP + DUP * (n + 1)
    if k < 0.5:
        return up
    if k < 0.5 + SW:                    # ふりおろす(だんだん速く)
        u = (k - 0.5) / SW
        return up - (up + FT) * u * u    # 少し先まで振りぬく
    if k < 0.5 + SW + 1.2:              # もどる(次の高さまで)
        u = (k - 0.5 - SW) / 1.2
        return -FT + (up_next + FT) * (0.5 - 0.5 * math.cos(math.pi * u))
    return up_next


class Game:
    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 60
        self.space = sp
        st = sp.static_body
        self.balls = []
        for i, d in enumerate(layout(rng)):
            r = d["r"]
            m = (r / 10) ** 3
            b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, r))
            b.position = (d["x"], Y0)
            s = pymunk.Circle(b, r)
            s.elasticity, s.friction = E, 0.0
            s.collision_type = 1
            sp.add(b, s)
            sp.add(pymunk.SlideJoint(st, b, d["anchor"], (0, 0), 0, d["L"]))
            self.balls.append((b, d))
        x0 = self.balls[0][1]["x"]
        self.hp = (x0 - self.balls[0][1]["r"] - HR - 2 + 0.0, Y0 - HL)
        hb = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        hb.position = self.hp
        head = pymunk.Circle(hb, HR, (0, HL))
        head.elasticity = 0.8
        head.collision_type = 2
        sp.add(hb, head)
        hb.angle = hammer_ang(0)
        self.hammer = hb
        sp.on_collision(1, 1, post_solve=self._clack)
        sp.on_collision(1, 2, post_solve=self._clack)
        self.t = 0.0
        self.events = []
        self.result, self.result_t = None, None
        self.last_clack = {}
        self.max_ang = 0.0

    def _clack(self, arb, space, data):
        if not arb.is_first_contact:
            return
        j = arb.total_impulse.length
        if j <= 0:
            return
        a, b = arb.shapes
        r = min(a.radius, b.radius)
        self.events.append(("clack", self.t, (j / (r / 10) ** 3, r, b.collision_type == 2)))

    def step(self, dt):
        a1 = hammer_ang(self.t + dt)
        self.hammer.angular_velocity = (a1 - self.hammer.angle) / dt
        self.space.step(dt)
        self.t += dt
        bf = self.balls[-1][0]
        if self.result is None:
            ang = math.degrees(math.atan2(bf.position.x - PF[0], bf.position.y - PF[1]))
            self.max_ang = max(self.max_ang, ang)
            if math.hypot(bf.position.x - BELL[0], bf.position.y - BELL[1]) < RF + BELL_R:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "b": [(b.position.x, b.position.y) for b, _ in g.balls], "ha": g.hammer.angle})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "max_ang": g.max_ang}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 2), round(r["max_ang"], 1)


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
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



ZOOM = 0.95
NB_ = len(_L0)
BALL_COL = [colorsys.hsv_to_rgb(0.92 * i / (NB_ - 1), 0.75, 1.0) for i in range(NB_)]


def draw_bell(ctx, x, y, shake, glow):
    """金の鐘(下向きの口)。鳴るとゆれて光る。"""
    ctx.save()
    ctx.translate(x, y - 6)
    ctx.rotate(0.25 * shake)
    if glow > 0:
        for k in range(3):
            rr = 50 + 70 * (1 - glow) + 30 * k
            ctx.arc(0, 10, rr, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.85, 0.3, 0.35 * glow / (k + 1))
            ctx.set_line_width(6)
            ctx.stroke()
    ctx.move_to(0, -44)
    ctx.line_to(0, -30)
    ctx.set_source_rgb(0.7, 0.55, 0.2)
    ctx.set_line_width(5)
    ctx.stroke()
    ctx.move_to(-10, -30)
    ctx.curve_to(-24, -26, -26, 0, -30, 22)
    ctx.line_to(30, 22)
    ctx.curve_to(26, 0, 24, -26, 10, -30)
    ctx.close_path()
    g = cairo.LinearGradient(-30, 0, 30, 0)
    g.add_color_stop_rgb(0, 0.75, 0.5, 0.1)
    g.add_color_stop_rgb(0.35, 1.0, 0.92, 0.5)
    g.add_color_stop_rgb(1, 0.65, 0.42, 0.08)
    ctx.set_source(g)
    ctx.fill()
    ctx.arc(0, 26, 6, 0, 2 * math.pi)
    ctx.set_source_rgb(0.85, 0.65, 0.2)
    ctx.fill()
    ctx.restore()


def draw_static(bc):
    bc.set_source_rgb(0.03, 0.035, 0.06)
    bc.paint()
    # 台(上の棒と柱)
    x0, x1 = 30, _L0[-2]["x"] + 40
    g = cairo.LinearGradient(0, BAR_Y - 10, 0, BAR_Y + 10)
    g.add_color_stop_rgb(0, 0.95, 0.96, 1.0)
    g.add_color_stop_rgb(0.5, 0.55, 0.6, 0.7)
    g.add_color_stop_rgb(1, 0.3, 0.33, 0.4)
    bc.rectangle(x0, BAR_Y - 10, x1 - x0, 20)
    bc.set_source(g)
    bc.fill()
    # 右はしの球のうで
    ax, ay = PF
    bc.rectangle(x1 - 10, BAR_Y, 14, 20)
    bc.move_to(x1 - 3, BAR_Y + 5)
    bc.line_to(ax + 40, BAR_Y + 5)
    bc.line_to(ax + 40, ay)
    bc.line_to(ax, ay)
    bc.set_source_rgb(0.7, 0.74, 0.82)
    bc.set_line_width(8)
    bc.set_line_join(cairo.LINE_JOIN_ROUND)
    bc.stroke()
    bc.arc(ax, ay, 6, 0, 2 * math.pi)
    bc.fill()
    # 床のかげ
    g = cairo.RadialGradient(W / 2, Y0 + 130, 10, W / 2, Y0 + 130, 520)
    g.add_color_stop_rgba(0, 0.4, 0.5, 0.8, 0.12)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    bc.rectangle(0, Y0 + 60, W, 160)
    bc.set_source(g)
    bc.fill()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"cradle_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"cradle_{seed}.wav")
    final = os.path.join(OUT_DIR, f"cradle_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"cr_preview_{seed}_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, BELL[0] - 200, BELL[1], reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=("Congratulations!!", "DING!", ""), font="Playfair Display", slim=True)
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    base = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    draw_static(cairo.Context(base))
    frozen = None
    prev = None
    trail = []
    for fi, fr in enumerate(frames):
        t = fr["t"]
        over = end_t is not None and t >= end_t
        win_b = (t - end_t) if (ending is not None and over) else -1.0
        if win_b >= PRE:
            ending.draw(surf, ctx, win_b - PRE + JP.T_BIG)
            giragira(ctx, win_b - PRE, fever, glints, W, H, WIN_DUR)
            ff.stdin.write(surf.get_data())
            continue
        if fail and over:
            if frozen is None:
                frozen = fr
            fr = frozen
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        ctx.set_source_rgb(0.03, 0.035, 0.06)
        ctx.paint()
        ctx.save()
        ctx.translate(540, 1000)          # 装置全体(ふり上げたハンマーまで)が画面に入るように(見た目だけ)
        ctx.scale(ZOOM, ZOOM)
        ctx.translate(-412, -920)
        ctx.set_source_surface(base, 0, 0)
        ctx.paint()
        # 鐘
        rung = (not fail) and over
        bt = (t - end_t) if rung else 0
        draw_bell(ctx, BELL[0], BELL[1], math.sin(bt * 30) * math.exp(-bt * 3) if rung else 0.0,
                  max(0.0, 1 - bt / 0.7) if rung else 0.0)
        # 右はしの球の光の軌跡
        bx, by = fr["b"][-1]
        trail.append((bx, by))
        trail = trail[-14:]
        for i, (tx_, ty_) in enumerate(trail[:-1]):
            ctx.arc(tx_, ty_, RF * (0.4 + 0.6 * i / len(trail)), 0, 2 * math.pi)
            ctx.set_source_rgba(*BALL_COL[-1], 0.05 + 0.25 * i / len(trail))
            ctx.fill()
        # ハンマー
        ha = fr["ha"]
        hp = (_L0[0]["x"] - _L0[0]["r"] - HR - 2, Y0 - HL)
        hx, hy = hp[0] - HL * math.sin(ha), hp[1] + HL * math.cos(ha)
        ctx.move_to(*hp)
        ctx.line_to(hx, hy)
        ctx.set_source_rgb(0.75, 0.55, 0.3)
        ctx.set_line_width(10)
        ctx.stroke()
        g = cairo.RadialGradient(hx - 14, hy - 16, 3, hx, hy, HR)
        g.add_color_stop_rgb(0, 1.0, 0.95, 0.7)
        g.add_color_stop_rgb(0.5, 1.0, 0.72, 0.25)
        g.add_color_stop_rgb(1, 0.6, 0.35, 0.08)
        ctx.arc(hx, hy, HR, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
        # 糸と球(速く動く球は光る)
        for i, (x, y) in enumerate(fr["b"]):
            ax, ay = _L0[i]["anchor"]
            ctx.move_to(ax, ay)
            ctx.line_to(x, y)
            ctx.set_source_rgba(0.85, 0.9, 1.0, 0.6)
            ctx.set_line_width(2)
            ctx.stroke()
        for i, (x, y) in enumerate(fr["b"]):
            r = _L0[i]["r"]
            sp_ = 0.0
            if prev is not None and not over:
                sp_ = math.hypot(x - prev[i][0], y - prev[i][1]) * FPS
            gl = min(1.0, sp_ / 900)
            if gl > 0.05:
                g = cairo.RadialGradient(x, y, r * 0.5, x, y, r * 2.4)
                g.add_color_stop_rgba(0, *BALL_COL[i], 0.5 * gl)
                g.add_color_stop_rgba(1, *BALL_COL[i], 0)
                ctx.arc(x, y, r * 2.4, 0, 2 * math.pi)
                ctx.set_source(g)
                ctx.fill()
            shiny_ball(ctx, x, y, r, BALL_COL[i])
        if not over:
            prev = fr["b"]
        ctx.restore()
        # 文字
        chic(ctx, "鐘を鳴らせる？", W / 2, 200, 62, rgb=(1, 0.88, 0.6))
        lv = min(int(min(t, end_t if end_t else t) // PERIOD) + 1, 99)
        chic(ctx, f"Lv.{lv}", W / 2 - 110, 310, 72, rgb=(1, 1, 1), weight="Medium")
        tt = min(t, end_t) if end_t is not None else t
        lft = max(0.0, TIME_LIMIT - tt)
        chic(ctx, f"{lft:4.1f}", W / 2 + 130, 305, 44, rgb=(1, 0.45, 0.45) if lft < 5 else (0.7, 0.75, 0.85), weight="Medium")
        if not over:
            horror(ctx, "失敗したら…", W / 2, 1600, 74, t)
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
            failed_text(ctx, "Failed...", W / 2, 960 + 40 * (1 - k), 160, k)
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
    print(f"完成: {os.path.abspath(final)}  ({'成功' if not fail else '失敗'} {end_t:.2f}秒 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def clack(r, amp, rng):
    """鉄球の「カチン」:小さい球ほど高い。"""
    tt = _t(0.12)
    f = 2400 * (36 / r) ** 0.5
    y = (np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.018) + 0.5 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt / 0.008)
         + 0.4 * rng.normal(0, 1, len(tt)) * np.exp(-tt / 0.002))
    return amp * y


def bell_sound():
    tt = _t(3.5)
    y = np.zeros(len(tt))
    for k, (m, a, d) in enumerate(((1.0, 1.0, 1.6), (2.0, 0.6, 1.1), (2.76, 0.45, 0.8), (5.4, 0.25, 0.4), (0.5, 0.35, 2.0))):
        y += a * np.sin(2 * np.pi * 880 * m * tt) * np.exp(-tt / d)
    return y * np.minimum(1, tt / 0.003)


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)
    rng = np.random.default_rng(4)
    last = -1.0
    for k, t, d in events:
        if k != "clack" or t > end_t:
            continue
        sp_, r, is_hammer = d
        if sp_ < 40 or t - last < 0.006:
            continue
        last = t
        amp = min(1.0, (sp_ / 900) ** 0.7)
        sig = clack(r, amp, rng)
        if is_hammer:
            tt = _t(0.2)
            thud = 1.3 * amp * np.sin(2 * np.pi * 180 * tt) * np.exp(-tt / 0.05)
            thud[:len(sig)] += sig
            sig = thud
        i = int(t * SR)
        j = min(n_out, i + len(sig))
        out[i:j] += sig[: j - i]
    if not fail:
        b = bell_sound()
        i = int(end_t * SR)
        j = min(n_out, i + len(b))
        extra[i:j] += 0.9 * b[: j - i]
    wet = out.copy()
    for dd, g_ in ((0.061, 0.18), (0.097, 0.1)):
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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("-n", type=int, default=80)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
