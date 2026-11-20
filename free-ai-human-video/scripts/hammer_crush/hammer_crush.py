"""「ぶつかると2倍に増えるボール、2000個いける?」丸いわくのまん中からぶら下がった振り子のハンマーが左右に振れて、
左下と右の固定ブロックに交互にぶつかる。ハンマーとブロックのあいだにはさまれたボールは、次の色のボール2個になって上へ噴き出す。

- 参考:ユーザーから受け取った参考動画(振り子のハンマーが左右のブロックにぶつかり、はさまれたボールが2倍になる)の形式。
  絵・色・音・数字は自作(参考動画のロゴやデザインは使っていない)。
- 重力あり。ボールは下にたまり、ハンマーの下のふちに押されて転がる(ねらい・補正なし)。
- ハンマーは決まったリズムで左右に振れる(左のブロックより右のブロックのほうが高い位置にあるので、右へ大きく振れる)。
- ハンマーのわきの面とブロックの面のすき間がボールより細くなった瞬間、そのすき間にいるボールは「はさまれて」、
  次の色のボール2個になってすき間から上へ噴き出す(ハンマーが近づき始めたあとに生まれたボールは、その回にははさまれない)。
- 制限時間内に2000個になれば成功(虹色パチンコ演出)、ならなければ失敗(幽霊)。

使い方:
    python hammer_crush.py search [-n 40]
    python hammer_crush.py render --seed N
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
from ball_escape import midi_hz, text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from fail_bgm import fail_music  # noqa: E402
from pachinko import DURATION as FEVER_DUR, RainbowFever, kyuin_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

CX, CY, R = 540.0, 1000.0, 430.0          # 丸いわく。ハンマーの支点はわくの中心
BALL_R = 6.0
GRAVITY = 1500.0
SPLIT = 2
TARGET = int(os.environ.get("TARGET", 2000))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 40.65))
OUTRO = 4.2
SPRAY = float(os.environ.get("SPRAY", 650.0))   # はさまれて生まれたボールが噴き出す速さ

# ハンマーとブロック(どれも支点を中心にした扇形。角度は「真下」から右回りを+)
R_IN = 0.36 * R                  # ハンマー・ブロックの内側の半径
R_OUT_H = R - 7.0                # ハンマーの外側(わくとのすき間はボールより小さく、下にたまったボールを押していく)
HALF = math.radians(17)          # ハンマーの半分の幅(角度)
SWING_L = math.radians(24)       # 左にいちばん振れた角度(左のブロックにぶつかる)。角度は+が画面の左
SWING_R = math.radians(-40)      # 右にいちばん振れた角度(右のブロックにぶつかる)
SWING_T = float(os.environ.get("SWING_T", 2.4))    # 左右1往復の時間(秒)
BLOCK_W = math.radians(34)       # ブロックの幅(角度)
BLOCK_L = (SWING_L + HALF, SWING_L + HALF + BLOCK_W)   # 左のブロックの角度の範囲(その面が、ハンマーの左の面とぴったり合う)
BLOCK_R = (SWING_R - HALF - BLOCK_W, SWING_R - HALF)   # 右のブロック
CRUSH_GAP = 2 * BALL_R * 1.05    # すき間がこれより細くなったら、はさまれた

PALETTE = [(1.0, 0.82, 0.2), (0.3, 0.85, 1.0), (0.45, 0.95, 0.35), (1.0, 0.55, 0.15), (0.97, 0.97, 1.0),
           (1.0, 0.35, 0.65), (0.65, 0.45, 1.0), (0.2, 0.9, 0.75), (1.0, 0.3, 0.3), (0.95, 0.95, 0.4)]


def swing(t):
    """ハンマーの角度。左右に、なめらかに(振り子のように)振れる。"""
    mid, amp = (SWING_L + SWING_R) / 2, (SWING_R - SWING_L) / 2
    return mid - amp * math.cos(2 * math.pi * t / SWING_T)   # t=0 で左にいちばん振れている


def polar(a, r):
    """真下から a ラジアン回った向き(+が画面の左)に、支点から r の点。"""
    return (CX - r * math.sin(a), CY + r * math.cos(a))


def sector(a0, a1, r_in, r_out, n=10):
    """扇形(内側はまっすぐ、外側は円弧)の多角形の点(画面の座標)。"""
    pts = [polar(a0, r_in), polar(a1, r_in)]
    for k in range(n + 1):
        a = a1 + (a0 - a1) * k / n
        pts.append(polar(a, r_out))
    return pts


def hammer_local():
    """ハンマーの形(支点が原点、まっすぐ下向き)。"""
    pts = sector(-HALF, HALF, R_IN, R_OUT_H)
    pts.insert(1, polar(0.0, R_IN * 0.72))   # 上は山形(ボールが上に乗らず、すべり落ちる)
    return [(x - CX, y - CY) for x, y in pts]


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 15
        self.space = sp
        n = 120
        pts = [(CX + (R + 10) * math.cos(2 * math.pi * k / n), CY + (R + 10) * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
        for a, b in zip(pts, pts[1:]):
            s = pymunk.Segment(sp.static_body, a, b, 10)
            s.elasticity, s.friction = 0.3, 0.4
            sp.add(s)
        for a0, a1 in (BLOCK_L, BLOCK_R):   # 固定ブロック(わくにくっついている)
            s = pymunk.Poly(sp.static_body, sector(a0, a1, R_IN * 0.92, R + 12))
            s.elasticity, s.friction = 0.3, 0.4
            sp.add(s)
        # ハンマー(決まった動きのキネマティック物体)と、支点からの棒
        hb = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        hb.position = (CX, CY)
        hb.angle = swing(0)
        hs = pymunk.Poly(hb, hammer_local())
        hs.elasticity, hs.friction = 0.3, 0.4
        rod = pymunk.Segment(hb, (0, 0), (0, R_IN * 0.72), 7)
        rod.elasticity, rod.friction = 0.3, 0.4
        sp.add(hb, hs, rod)
        self.hammer = hb
        self.t = 0.0
        self.balls = {}
        self.next_id = 0
        self.events = []
        self.result, self.result_t = None, None
        self.final_n = 0
        # はじめはボール1個(下のすき間の上あたりから落ちてくる。左右どちらかはランダム)
        a = (SWING_R + SWING_L) / 2 + (1 if rng.random() < 0.5 else -1) * math.radians(rng.uniform(32, 48))
        p = polar(a, R * rng.uniform(0.55, 0.7))
        self.add(p, 0, (rng.uniform(-40, 40), 0))
        self.app_start = [0.0, 0.0]   # それぞれのブロックへハンマーが近づき始めた時刻

    def add(self, pos, gen, vel):
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, BALL_R))
        b.position = pos
        b.velocity = vel
        s = pymunk.Circle(b, BALL_R)
        s.elasticity, s.friction = 0.35, 0.3
        self.space.add(b, s)
        self.balls[b] = {"id": self.next_id, "gen": gen, "shape": s, "born": self.t}
        self.next_id += 1
        return b

    def step(self, dt):
        a0 = swing(self.t)
        a1 = swing(self.t + dt)
        self.hammer.angular_velocity = (a1 - self.hammer.angle) / dt
        self.space.step(dt)
        self.t += dt
        w = a1 - a0
        # 近づき始めた時刻を覚える(左へ動いている=左のブロックへ近づいている)
        u = (self.t / SWING_T) % 1.0
        if u < 0.5:   # 左→右へ動いている(右のブロックへ近づいている)
            self.app_start[1] = self.t - u * SWING_T
        else:         # 右→左へ動いている(左のブロックへ近づいている)
            self.app_start[0] = self.t - (u - 0.5) * SWING_T
        if self.result is None:
            self.crush(a1, w)
        if self.result is None:
            if len(self.balls) >= TARGET:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, None))
            if self.result is not None:
                self.final_n = len(self.balls)

    def crush(self, a, w):
        """ハンマーのわきの面とブロックの面のすき間が、ボールより細くなった瞬間にはさまれる。"""
        for side, (face_h, face_b, moving_in) in enumerate((
                (a + HALF, BLOCK_L[0], w > 0),     # 左:ハンマーの左の面 と 左のブロックの面
                (a - HALF, BLOCK_R[1], w < 0))):   # 右:ハンマーの右の面 と 右のブロックの面
            if not moving_in:
                continue
            lo, hi = sorted((face_h, face_b))
            gap_ang = hi - lo
            if gap_ang * R > 60:   # まだ遠い
                continue
            # すき間(扇形)のまわりのボールを調べる
            mid = (lo + hi) / 2
            mx, my = polar(mid, (R_IN + R) / 2)
            ext = (R - R_IN) / 2 + 30
            out = []
            for q in self.space.bb_query(pymunk.BB(mx - ext, my - ext, mx + ext, my + ext), pymunk.ShapeFilter()):
                bb = q.body
                info = self.balls.get(bb)
                if info is None or info["born"] >= self.app_start[side] - 1e-6:
                    continue
                dx, dy = bb.position.x - CX, bb.position.y - CY
                rho = math.hypot(dx, dy)
                if not (R_IN - BALL_R < rho < R):
                    continue
                phi = math.atan2(-dx, dy)   # 真下からの角度(+が画面の左)
                margin = BALL_R / rho
                if lo - margin <= phi <= hi + margin and gap_ang * rho < CRUSH_GAP:
                    out.append(bb)
            out.sort(key=lambda b_: self.balls[b_]["id"])   # 毎回同じ順番(同じシードなら同じ結果)
            for bb in out:
                info = self.balls.pop(bb)
                pos = bb.position
                self.space.remove(bb, info["shape"])
                ng = info["gen"] + 1
                d = pymunk.Vec2d(CX - pos.x, CY - pos.y)
                inward = d.normalized() if d.length > 1e-6 else pymunk.Vec2d(0, -1)
                for k in range(SPLIT):   # すき間から、支点のほうへ(上へ)噴き出す
                    p = pos + inward * (BALL_R * (1.2 + 2.2 * k))
                    ang = self.rng.uniform(-0.25, 0.25)
                    v = inward.rotated(ang) * (SPRAY * self.rng.uniform(0.7, 1.1))
                    self.add(p, ng, v)
                self.events.append(("crush", self.t, (pos.x, pos.y, ng, len(self.balls), side)))
            if out:
                self.events.append(("hit", self.t, (side, len(out))))


def simulate(seed, record=False):
    import gc
    gc.disable()
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "n": len(g.balls), "ang": g.hammer.angle,
                           "balls": np.array([(b.position.x, b.position.y, i["gen"]) for b, i in g.balls.items()],
                                             dtype=np.float32).reshape(-1, 3)})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else FEVER_DUR
            if not record or g.t > g.result_t + extra:
                break
    gc.enable()
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "n": g.final_n}


def score(seed):
    r = simulate(seed)
    cr = [e for e in r["events"] if e[0] == "crush"]
    t100 = next((e[1] for e in cr if e[2][3] >= 100), None)
    return seed, r["result"], round(r["result_t"], 1), r["n"], len(cr), t100 and round(t100, 1)


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
_SPR = {}


def gen_col(g):
    return PALETTE[g % len(PALETTE)]


def ball_sprite(g):
    if g not in _SPR:
        n = int(BALL_R * 2 + 4)
        spr = cairo.ImageSurface(cairo.FORMAT_ARGB32, n, n)
        c = cairo.Context(spr)
        col = gen_col(g)
        x = y = n / 2
        r = BALL_R
        gr = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r)
        gr.add_color_stop_rgb(0, *(min(1, k + 0.45) for k in col))
        gr.add_color_stop_rgb(0.55, *col)
        gr.add_color_stop_rgb(1, *(k * 0.6 for k in col))
        c.arc(x, y, r, 0, 2 * math.pi)
        c.set_source(gr)
        c.fill()
        _SPR[g] = spr
    return _SPR[g]


def draw_poly(ctx, pts, light=0.82, alpha=1.0):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    g = cairo.LinearGradient(min(xs), min(ys), max(xs), max(ys))
    g.add_color_stop_rgba(0, light + 0.08, light + 0.09, light + 0.12, alpha)
    g.add_color_stop_rgba(1, light - 0.12, light - 0.11, light - 0.08, alpha)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.9 * alpha)
    ctx.set_line_width(2.5)
    ctx.stroke()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"hammer_crush_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"hammer_crush_{seed}.wav")
    final = os.path.join(OUT_DIR, f"hammer_crush_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"hc_preview_{pt:.1f}.png"))
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
    fever = RainbowFever(W, H, seed) if not fail else None
    flashes = []
    ev_i = 0
    frozen = None
    blocks = [sector(a0, a1, R_IN * 0.92, R + 2) for a0, a1 in (BLOCK_L, BLOCK_R)]
    hloc = hammer_local()
    bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(bg)
    g = cairo.RadialGradient(CX, CY, 100, CX, CY, 1100)
    g.add_color_stop_rgb(0, 0.09, 0.1, 0.16)
    g.add_color_stop_rgb(1, 0.02, 0.025, 0.05)
    bc.set_source(g)
    bc.paint()
    bc.arc(CX, CY, R, 0, 2 * math.pi)
    bc.set_source_rgb(0.02, 0.02, 0.04)
    bc.fill()
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "hit":
                flashes.append((data[0], et))
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        if fail and over:
            if frozen is None:
                frozen = fr
            fr = frozen
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        if fever is not None and over:
            fever.draw_back(ctx, t - end_t)
            ctx.arc(CX, CY, R, 0, 2 * math.pi)
            ctx.set_source_rgba(0.02, 0.02, 0.04, 0.85)
            ctx.fill()
        # ボール
        for x, y, gg in fr["balls"].tolist():
            spr = ball_sprite(int(gg))
            n = spr.get_width()
            ctx.set_source_surface(spr, x - n / 2, y - n / 2)
            ctx.rectangle(x - n / 2, y - n / 2, n, n)
            ctx.fill()
        # ブロックとハンマー
        for b in blocks:
            draw_poly(ctx, b, 0.72)
        ang = fr["ang"]
        ca, sa = math.cos(ang), math.sin(ang)
        hp = [(CX + x * ca - y * sa, CY + x * sa + y * ca) for x, y in hloc]
        ctx.move_to(CX, CY)
        ctx.line_to(CX - R_IN * 0.72 * sa, CY + R_IN * 0.72 * ca)
        ctx.set_source_rgb(0.75, 0.77, 0.82)
        ctx.set_line_width(16)
        ctx.stroke()
        draw_poly(ctx, hp, 0.8)
        ctx.arc(CX, CY, 22, 0, 2 * math.pi)
        ctx.set_source_rgb(0.85, 0.86, 0.9)
        ctx.fill()
        ctx.arc(CX, CY, 9, 0, 2 * math.pi)
        ctx.set_source_rgb(0.3, 0.32, 0.38)
        ctx.fill()
        # ぶつかった瞬間の光(当たった面が白く光る)
        keep = []
        for side, t0 in flashes:
            a_ = t - t0
            if a_ < 0.35:
                face = BLOCK_L[0] if side == 0 else BLOCK_R[1]
                p0, p1 = polar(face, R_IN), polar(face, R)
                ctx.move_to(*p0)
                ctx.line_to(*p1)
                ctx.set_source_rgba(1, 1, 1, 0.9 * (1 - a_ / 0.35))
                ctx.set_line_width(10 * (1 - a_ / 0.35) + 2)
                ctx.stroke()
                keep.append((side, t0))
        flashes = keep
        ctx.arc(CX, CY, R, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.set_line_width(4)
        ctx.stroke()
        # 文字
        text(ctx, "ぶつかると2倍に増えるボール", W / 2, 235, 60, sw=12)
        text(ctx, f"{TARGET}個にできる？", W / 2, 335, 96, rgb=GOLD, sw=16)
        n = fr["n"] if not over else res["n"]
        text(ctx, f"{n:,} 個", W / 2, 455, 80, rgb=(1, 1, 1), sw=12)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 530, 40, rgb=(1, 0.4, 0.4) if left < 10 else (0.95, 0.95, 0.95), sw=8)
        if not over:
            text(ctx, "失敗したら・・・", W / 2, 1515, 52, rgb=(1, 0.45, 0.45), sw=10)
        if over and fail:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 880, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            text(ctx, "時間切れ…", W / 2, 990, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"{res['n']:,}個までだった…", W / 2, 1110, 66, sw=12)
        elif over:
            fever.draw_front(ctx, t - end_t, text, "大当たり!!", f"{TARGET}個達成!!")
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['n']}個 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def pop1(g, v):
    """増えたボール1個ぶんの「ポン」(世代で高さが変わる)。"""
    t = _t(0.09)
    f = midi_hz(72 + (g % 8) * 2 + [0, 3, 5, 7, 10, 12][v])
    return np.sin(2 * np.pi * f * t * (1 + 0.6 * t)) * np.exp(-t * 40) * np.minimum(1, t / 0.002)


def slam(amp, seed, big=1.0):
    """ハンマーがブロックにぶつかる「ガシャン!」(低い衝撃+金属の響き)。"""
    t = _t(0.6)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    thump = np.sin(2 * np.pi * np.cumsum(90 * np.exp(-t * 20) + 45) / SR) * np.exp(-t * 10)
    metal = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in ((380, 0.6, 9), (970, 0.4, 14), (2300, 0.25, 22)))
    return amp * (thump + 0.5 * metal * big + 0.4 * n * np.exp(-t * 35))


def kyuin_one(up=1.0):
    t = _t(0.28)
    f = up * (500 + 2900 * (1 - np.exp(-t / 0.06))) * (1 + 0.03 * np.sin(2 * np.pi * 32 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.35 * np.sign(np.sin(ph)) + 0.3 * np.sin(2 * ph)
    return y * np.minimum(1, t / 0.01) * np.exp(-np.maximum(0, t - 0.16) / 0.05)


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)

    def add(sig, t0, gain=1.0, buf=None):
        b = out if buf is None else buf
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out and j > i:
            b[i:j] += gain * sig[: j - i]
    # ハンマーがブロックにぶつかる「ガシャン」(左右に振れきるたび)
    k = 0
    while True:
        tc = (k + 0.0) * SWING_T / 2
        k += 1
        if tc > (end_t or duration):
            break
        if tc > 0.05:
            add(slam(0.35, k), tc)
    rng = np.random.default_rng(11)
    pops = {}
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.01:
            continue
        if kind == "hit":
            add(slam(0.25, int(t * 100), 1.6), t, min(1.5, 0.5 + 0.05 * data[1]))
        elif kind == "crush":
            g = data[2]
            for k2 in range(SPLIT):   # 増えたボール1個ごとに「ポン」
                v = int(rng.integers(0, 6))
                key = (g % 8, v)
                if key not in pops:
                    pops[key] = pop1(g, v)
                add(pops[key], t + 0.02 + k2 * 0.03 + rng.uniform(0, 0.08), 0.5)
    win = int(0.6 * SR)
    pw = np.convolve(out ** 2, np.ones(win) / win, "same")
    agc = np.clip(0.08 / np.sqrt(pw + 1e-8), 0.6, 6.0)
    agc = np.convolve(agc, np.ones(win) / win, "same")
    out = out * agc
    wet = out.copy()
    for dd, g_ in ((0.043, 0.2), (0.071, 0.13)):
        kk = int(dd * SR)
        wet[kk:] += out[:-kk] * g_
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int(end_t * SR)]
    rms = np.sqrt(np.mean(body ** 2))
    if rms > 0:
        wet *= min(6.0, 10 ** (-14.0 / 20) / rms)
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
        # 虹色パチンコ演出:キュインキュイン+ファンファーレ+ジャラジャラ(pachinko.py)に、大当たりのファンファーレ連打(jackpot_end.py)を重ね、
        # 演出のあいだずっと「キュイン!」を鳴らし続ける
        sys.path.insert(0, os.path.join(HERE, "..", "glass_spiral"))
        import jackpot_end as JP
        a_ = kyuin_music(SR, FEVER_DUR)
        b_ = JP.music(SR, 3)
        b_ = b_.mean(axis=1) if b_.ndim == 2 else b_
        n = int(FEVER_DUR * SR)
        mus = np.zeros(n)
        mus[:min(n, len(a_))] += a_[:n]
        mus[:min(n, len(b_))] += 0.8 * b_[:n] / (np.abs(b_).max() + 1e-9)
        tt = 0.0
        while tt < FEVER_DUR - 0.5:
            ky = kyuin_one(1.0 + 0.15 * ((int(tt / 0.3)) % 3))
            i = int(tt * SR)
            m = min(len(ky), n - i)
            mus[i:i + m] += 0.45 * ky[:m]
            tt += 0.3
        mus *= np.minimum(1, (FEVER_DUR - np.arange(n) / SR) / 0.6)
        mus = np.tanh(1.6 * mus / (np.abs(mus).max() + 1e-9)) / np.tanh(1.6)
        i0 = int((end_t + 0.05) * SR)
        m = min(len(mus), n_out - i0)
        extra[i0:i0 + m] += 1.05 * mus[:m]
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
    ap.add_argument("-n", type=int, default=40)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
