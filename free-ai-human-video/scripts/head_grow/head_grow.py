"""「女の子の頭の形の枠いっぱいまで育つ?」ゆっくり回る、チャンネルのサムネの女の子(おかっぱ)の頭の形をした枠の中を、
1個の玉が重力で跳ねる。枠はいくつかの区切りに分かれていて、区切りごとに「×1.2」「×1.5」「−1.5」の効果がある。
玉が当たった区切りの効果で、玉の大きさ(数字)が変わる。区切りの1つはすき間で、そこから落ちたら失敗。
大きさが0以下になって消えても失敗。枠いっぱいの大きさまで育てば成功。

- 玉はサムネの女の子の顔+光る輪(icon_spiral/icon_ball.py の絵)。半径は大きさの数字に比例する。
- 重力・反発・回る壁の押し出しのまま(ねらい・補正なし)。効果が出るのは区切りに新しくぶつかった瞬間だけ。
- 成功ならパチンコの当たり風の演出、失敗なら幽霊。

使い方:
    python head_grow.py search [-n 80]
    python head_grow.py render --seed N
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
from pachinko import kyuin_music  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "glass_spiral"))
import jackpot_end as JP  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "icon_spiral"))
import icon_ball as IB  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 6
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

CX, CY = 540.0, 1000.0
SPIN = float(os.environ.get("SPIN", 0.5))         # 枠が回る速さ(ラジアン/秒)
HW = 340.0                                        # 頭の枠の半分の幅
DOME_Y = -40.0                                    # 上の丸い部分の中心(枠の中心から)
BOT_Y = 330.0                                     # 下の平らな部分
CORNER = 70.0                                     # 下の角の丸み
UNIT = 12.0                                       # 大きさ1あたりの玉の半径(px)
S0 = float(os.environ.get("S0", 3.0))             # はじめの大きさ
S_WIN = float(os.environ.get("S_WIN", 25.0))      # この大きさ(半径300px=枠いっぱい)になれば成功
GRAVITY = float(os.environ.get("GRAVITY", 700.0))
BALL_E = float(os.environ.get("BALL_E", 0.9))
WALL_E = 1.0
OUTRO = 4.2
MAX_T = 90.0
# 枠の区切り(上の右から時計回り)。"gap" はすき間
LAYOUT = os.environ.get("LAYOUT", "x1.2,x1.5,gap,x1.2,m1.5,x1.2,x1.5,m1.5,x1.2,x1.2,m1.5,x1.5").split(",")
OPS = {"x1.2": ("×1.2", (0.3, 0.95, 0.45)), "x1.5": ("×1.5", (1.0, 0.8, 0.15)), "m1.5": ("−1.5", (1.0, 0.25, 0.3))}


def head_outline(n=240):
    """頭の形の輪郭(枠の中心が原点):上は半円の髪、横はまっすぐ、下は平らで角が丸い。時計回りの点。"""
    pts = []
    for k in range(60):   # 上の半円(左→上→右)
        a = math.pi + math.pi * k / 59
        pts.append((HW * math.cos(a), DOME_Y + HW * math.sin(a)))
    for k in range(1, 20):   # 右の辺
        pts.append((HW, DOME_Y + (BOT_Y - CORNER - DOME_Y) * k / 19))
    for k in range(1, 15):   # 右下の角
        a = (math.pi / 2) * k / 14
        pts.append((HW - CORNER + CORNER * math.cos(a), BOT_Y - CORNER + CORNER * math.sin(a)))
    for k in range(1, 30):   # 下の辺
        pts.append((HW - CORNER - (2 * HW - 2 * CORNER) * k / 29, BOT_Y))
    for k in range(1, 15):   # 左下の角
        a = math.pi / 2 + (math.pi / 2) * k / 14
        pts.append((-HW + CORNER + CORNER * math.cos(a), BOT_Y - CORNER + CORNER * math.sin(a)))
    for k in range(1, 19):   # 左の辺
        pts.append((-HW, BOT_Y - CORNER - (BOT_Y - CORNER - DOME_Y) * k / 19))
    # 周の長さで等しく区切れるよう、長さに沿って点をならべ直す
    pts.append(pts[0])
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    out = []
    for k in range(n):
        target = L[-1] * k / n
        i = max(0, np.searchsorted(L, target) - 1)
        u = (target - L[i]) / max(1e-9, L[i + 1] - L[i])
        out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u))
    return out


_OUT = head_outline()


def segments():
    """区切りごとの線分リスト [(op, [(a, b), ...])]。"""
    n = len(_OUT)
    m = len(LAYOUT)
    res = []
    for j, op in enumerate(LAYOUT):
        i0, i1 = n * j // m, n * (j + 1) // m
        pts = [_OUT[i % n] for i in range(i0, i1 + 1)]
        res.append((op, list(zip(pts, pts[1:]))))
    return res


R_MAX = min(HW, BOT_Y - DOME_Y)    # 枠の中に入る、いちばん大きな円の半径


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 25
        self.space = sp
        hb = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        hb.position = (CX, CY)
        hb.angle = rng.uniform(-0.5, 0.5)   # はじめはだいたい頭が上(すき間は下の左のあたり)
        hb.angular_velocity = SPIN
        walls = []
        self.seg_of = {}
        for k, (op, segs) in enumerate(segments()):
            if op == "gap":
                continue
            for a, b in segs:
                s = pymunk.Segment(hb, a, b, 7)
                s.elasticity, s.friction = WALL_E, 0.6
                s.collision_type = 2
                walls.append(s)
                self.seg_of[s] = k
        sp.add(hb, *walls)
        self.hexb = hb
        self.S = S0
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, UNIT * S0))
        b.position = (CX + rng.uniform(-80, 80), CY - rng.uniform(50, 200))
        b.velocity = (rng.uniform(-300, 300), rng.uniform(-200, 100))
        s = pymunk.Circle(b, UNIT * S0)
        s.elasticity, s.friction = BALL_E, 0.6
        s.collision_type = 1
        sp.add(b, s)
        self.ball, self.shape = b, s
        self.r = UNIT * S0
        self.hits = 0
        self.t = 0.0
        self.events = []
        self.pending = None
        self.result, self.result_t, self.why = None, None, ""
        self.touching = 0
        self.last_sep = -1.0
        sp.on_collision(1, 2, begin=self._hit, separate=self._sep)

    def _hit(self, arb, space, data):
        """壁から離れていた玉が、新しく壁にぶつかった瞬間だけ「当たった」(壁を転がっているあいだは数えない)。"""
        self.touching += 1
        if self.touching == 1 and self.result is None and self.pending is None and self.t - self.last_sep > 0.03:
            for sh in arb.shapes:
                if sh in self.seg_of:
                    self.pending = self.seg_of[sh]
        return True

    def _sep(self, arb, space, data):
        self.touching = max(0, self.touching - 1)
        if self.touching == 0:
            self.last_sep = self.t

    def step(self, dt):
        self.space.step(dt)
        self.t += dt
        if self.pending is not None and self.result is None:   # 当たった区切りの効果で、大きさが変わる
            k = self.pending
            self.pending = None
            op = LAYOUT[k]
            old = self.S
            if op == "x1.2":
                self.S *= 1.2
            elif op == "x1.5":
                self.S *= 1.5
            else:
                self.S -= 1.5
            self.hits += 1
            self.events.append(("hit", self.t, (op, old, self.S, k)))
            if self.S <= 0:
                self.result, self.result_t, self.why = "fail", self.t, "vanish"
                self.events.append(("fail", self.t, "vanish"))
                self.space.remove(self.ball, self.shape)
                return
            self.S = min(self.S, S_WIN)
            self.r = UNIT * self.S
            self.shape.unsafe_set_radius(self.r)
            m = (self.S / S0) ** 2
            self.ball.mass = m
            self.ball.moment = pymunk.moment_for_circle(m, 0, self.r)
        if self.result is None:
            d = math.hypot(self.ball.position.x - CX, self.ball.position.y - CY)
            if d > 520 + self.r:   # すき間から外へ出た
                self.result, self.result_t, self.why = "fail", self.t, "fall"
                self.events.append(("fail", self.t, "fall"))
            elif self.S >= S_WIN:   # 枠いっぱいの大きさになった
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t > MAX_T:
                self.result, self.result_t, self.why = "fail", self.t, "time"
                self.events.append(("fail", self.t, "time"))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    fall_show = 1.0
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
            if g.result is not None and not record:
                break
        if record:
            frames.append({"t": g.t, "x": g.ball.position.x, "y": g.ball.position.y, "ang": g.ball.angle,
                           "r": g.r, "S": g.S, "hits": g.hits, "rot": g.hexb.angle,
                           "gone": g.why == "vanish"})
        if g.result is not None:
            extra = (fall_show + OUTRO + SCARE_DUR) if g.result == "fail" else JP.DURATION
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "S": g.S, "hits": g.hits, "why": g.why}


def score(seed):
    r = simulate(seed)
    best = max([e[2][2] for e in r["events"] if e[0] == "hit"], default=S0)
    return seed, r["result"], round(r["result_t"], 1), r["hits"], round(r["S"], 2), round(best, 1), r["why"]


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def ball_col(r):
    """玉の光の色:大きくなるほど 青 → 緑 → 黄 → オレンジ → 赤 と変わる。"""
    k = min(1.0, max(0.0, (r / UNIT - S0) / (S_WIN - S0)))
    return colorsys.hsv_to_rgb((0.6 - 0.75 * k) % 1.0, 0.75, 1.0)


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    """当たり演出のリールの絵柄:光る女の子の顔(7色。7番目=虹色が揃う)。"""
    col = colorsys.hsv_to_rgb((t * 0.7) % 1.0, 0.8, 1.0) if kind == 6 else colorsys.hsv_to_rgb(kind / 7, 0.75, 1.0)
    g = cairo.RadialGradient(x, y, r * 0.5, x, y, r * 1.5)
    g.add_color_stop_rgba(0, *col, 0.6 * alpha)
    g.add_color_stop_rgba(1, *col, 0)
    ctx.arc(x, y, r * 1.5, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    ctx.save()
    ctx.translate(x, y)
    IB.draw_face(ctx, r * 0.85, col, alpha)
    ctx.restore()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"head_grow_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"head_grow_{seed}.wav")
    final = os.path.join(OUT_DIR, f"head_grow_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"hd_preview_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, CX, CY, reel_ball, n_kinds=7, win=6, shake=16,
                                          texts=("枠いっぱい!!", "COMPLETE", f"{res['hits']}回で成功"))
    g0 = (end_t + 1.0) if fail else end_t   # 幽霊が出る時刻(落ちていく/消えるところを1秒見せる)
    trail = []
    rings = []
    pops = []
    segs_l = segments()
    ev_i = 0
    bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(bg)
    gr = cairo.RadialGradient(CX, CY, 50, CX, CY, 1100)
    gr.add_color_stop_rgb(0, 0.1, 0.08, 0.18)
    gr.add_color_stop_rgb(1, 0.02, 0.02, 0.05)
    bc.set_source(gr)
    bc.paint()
    frozen = None
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "hit":
                op, old, new, k_ = data
                rings.append((et, op))
                pops.append((et, op, new))
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ending is not None and over and t - end_t >= 1 / FPS - 1e-9:
            ending.draw(surf, ctx, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        if ghost is not None and t >= g0 and t - g0 < SCARE_DUR:
            ghost.draw(surf, t - g0)
            ff.stdin.write(surf.get_data())
            continue
        if fail and t >= g0:
            if frozen is None:
                frozen = fr
            fr = frozen
        after = (t - g0 - SCARE_DUR) if (fail and t >= g0) else 0
        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        # 頭の形の枠(ゆっくり回る)。区切りごとに効果の色、すき間は赤い点線。区切りのまん中に効果の文字
        rot = fr["rot"]
        ca, sa = math.cos(rot), math.sin(rot)
        tf = lambda p: (CX + p[0] * ca - p[1] * sa, CY + p[0] * sa + p[1] * ca)   # noqa: E731
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        lit = {}
        for t0, op in rings:
            if t - t0 < 0.3:
                lit[op] = max(lit.get(op, 0), 1 - (t - t0) / 0.3)
        for k, (op, segs) in enumerate(segs_l):
            pts = [tf(segs[0][0])] + [tf(b) for _, b in segs]
            if op == "gap":
                ctx.move_to(*pts[0])
                for p_ in pts[1:]:
                    ctx.line_to(*p_)
                ctx.set_dash([10, 10])
                ctx.set_source_rgba(1, 0.3, 0.3, 0.6)
                ctx.set_line_width(3)
                ctx.stroke()
                ctx.set_dash([])
                continue
            col_ = OPS[op][1]
            for wd, al in ((28, 0.14), (15, 0.32), (8, 1.0)):
                ctx.move_to(*pts[0])
                for p_ in pts[1:]:
                    ctx.line_to(*p_)
                ctx.set_source_rgba(*col_, al)
                ctx.set_line_width(wd)
                ctx.stroke()
        for k, (op, segs) in enumerate(segs_l):   # 効果の文字(枠の内側)
            if op == "gap":
                continue
            a_, b_ = segs[len(segs) // 2]
            mx, my = (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2
            d = math.hypot(mx, my - 80)
            ix, iy = mx - (mx) / d * 46, my - (my - 80) / d * 46
            px, py = tf((ix, iy))
            text(ctx, OPS[op][0], px, py + 14, 38, rgb=OPS[op][1], sw=8)
        # 玉(光の尾+光る輪+女の子の顔)
        x, y, r = fr["x"], fr["y"], fr["r"]
        col = ball_col(r)
        gone = fr["gone"]
        trail.append((x, y, r))
        trail = trail[-14:]
        for j, (tx, ty, tr) in enumerate(trail[:-1]):
            k = (j + 1) / len(trail)
            ctx.arc(tx, ty, tr * (0.5 + 0.5 * k), 0, 2 * math.pi)
            ctx.set_source_rgba(*col, 0.18 * k)
            ctx.fill()
        for mul, al in ((2.2, 0.18), (1.5, 0.35)):
            g = cairo.RadialGradient(x, y, r * 0.8, x, y, r * mul)
            g.add_color_stop_rgba(0, *col, al)
            g.add_color_stop_rgba(1, *col, 0)
            ctx.arc(x, y, r * mul, 0, 2 * math.pi)
            ctx.set_source(g)
            ctx.fill()
        keep = []
        for t0, op in rings:   # 大きさが変わった瞬間の光の輪(効果の色)
            a_ = t - t0
            if a_ < 0.3:
                ctx.arc(x, y, r * (1.05 + 0.8 * a_), 0, 2 * math.pi)
                ctx.set_source_rgba(*OPS[op][1], 0.9 * (1 - a_ / 0.3))
                ctx.set_line_width(4)
                ctx.stroke()
                keep.append((t0, op))
        rings = keep
        if not gone:
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(fr["ang"])
            IB.draw_face(ctx, r * 1.08, col)
            ctx.restore()
        keep = []
        for t0, op, new in pops:   # 当たった効果が、玉の上にポンと出る
            a_ = t - t0
            if a_ < 0.7:
                k = min(1.0, a_ / 0.1)
                text(ctx, OPS[op][0], x, y - r - 30 - 60 * a_, 64 * (1.3 - 0.3 * k), rgb=OPS[op][1], sw=10,
                     alpha=1.0 if a_ < 0.5 else (0.7 - a_) / 0.2)
                keep.append((t0, op, new))
        pops = keep
        # 文字
        text(ctx, "当たった所で大きさが変わる玉", W / 2, 235, 62, sw=12)
        text(ctx, "枠いっぱいまで育つ？", W / 2, 335, 92, rgb=GOLD, sw=16)
        Sv = fr["S"] if not gone else 0.0
        text(ctx, f"大きさ {Sv:.1f} / {S_WIN:.0f}", W / 2, 445, 64, rgb=(1, 1, 1), sw=10)
        if not over:
            text(ctx, "失敗したら・・・", W / 2, 1530, 54, rgb=(1, 0.45, 0.45), sw=10)
        if fail and t >= g0:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 880, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            text(ctx, "消えた…" if res["why"] == "vanish" else "落ちた…", W / 2, 990, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            best = max([e[2][2] for e in events if e[0] == "hit"], default=S0)
            text(ctx, f"いちばん大きくて {best:.1f} だった…", W / 2, 1110, 66, sw=12)
        elif ending is not None and over:
            ending.draw(surf, ctx, t - end_t)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['hits']}回・大きさ{res['S']:.1f}・{res['why']} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def bounce(f, amp):
    """壁に当たる「ポン」+ ふくらむ「ぷくっ」(玉が大きくなるほど低く太い音)。"""
    t = _t(0.35)
    body = np.sin(2 * np.pi * f * t * (1 - 0.15 * t)) * np.exp(-t * 9)
    puff = np.sin(2 * np.pi * np.cumsum(f * 1.5 * (1 + 0.6 * np.minimum(1, t / 0.08))) / SR) * np.exp(-np.maximum(0, t - 0.02) * 25) * (t > 0.02)
    return amp * (body + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 14) + 0.4 * puff)


def kyuin_one(up=1.0):
    t = _t(0.28)
    f = up * (500 + 2900 * (1 - np.exp(-t / 0.06))) * (1 + 0.03 * np.sin(2 * np.pi * 32 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.35 * np.sign(np.sin(ph)) + 0.3 * np.sin(2 * ph)
    return y * np.minimum(1, t / 0.01) * np.exp(-np.maximum(0, t - 0.16) / 0.05)


def fall_whoosh(amp):
    t = _t(1.0)
    f = 900 * np.exp(-t * 2.2) + 120
    return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.05) * np.exp(-t * 1.5)


def shrink_snd(amp):
    """小さくなる「ブッ…」(下がる音)。"""
    t = _t(0.35)
    f = 420 * np.exp(-t * 3) + 90
    ph = 2 * np.pi * np.cumsum(f) / SR
    return amp * (np.sign(np.sin(ph)) * 0.4 + np.sin(ph)) * np.minimum(1, t / 0.005) * np.exp(-t * 6)


def pop_vanish(amp):
    """消える「パフッ」。"""
    t = _t(0.4)
    n = np.random.default_rng(3).normal(0, 1, len(t))
    return amp * (n * np.exp(-t * 18) * 0.6 + np.sin(2 * np.pi * 300 * t * (1 - t)) * np.exp(-t * 10))


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
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.01:
            continue
        if kind == "hit":   # 当たった効果ごとの音:×1.2=ポン(大きさで音階が上がる)、×1.5=キュイン+ポン、−1.5=ブッ(下がる音)
            op, old, new, k_ = data
            m = 55 + int(round(12 * math.log2(max(new, 0.5) / S0) * 1.2))
            if op == "m1.5":
                add(shrink_snd(0.6), t)
            else:
                add(bounce(midi_hz(min(96, max(40, m))), 0.6), t)
                if op == "x1.5":
                    add(kyuin_one(0.8 + 0.02 * min(20, new)) * 0.35, t + 0.02)
    if fail and res['why'] == 'fall':
        add(fall_whoosh(0.7), end_t)
    elif fail:
        add(pop_vanish(0.7), end_t)
    wet = out.copy()
    for dd, g_ in ((0.043, 0.25), (0.071, 0.16), (0.11, 0.1)):
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
        g0 = end_t + 1.0
        sig = scream(SR)
        i0 = int(g0 * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
        sig = fail_music(SR, OUTRO)
        i0 = int((g0 + SCARE_DUR) * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += 0.6 * sig[:m]
    else:
        b_ = JP.music(SR, 3)
        b_ = b_.mean(axis=1) if b_.ndim == 2 else b_
        n = int(JP.DURATION * SR)
        mus = np.zeros(n)
        mus[:min(n, len(b_))] += b_[:n] / (np.abs(b_).max() + 1e-9)
        a_ = kyuin_music(SR, JP.DURATION - JP.T_BIG)
        i = int(JP.T_BIG * SR)
        m = min(len(a_), n - i)
        mus[i:i + m] += 0.8 * a_[:m]
        tt = JP.T_BIG
        while tt < JP.DURATION - 0.5:
            ky = kyuin_one(1.0 + 0.15 * ((int(tt / 0.3)) % 3))
            i = int(tt * SR)
            m = min(len(ky), n - i)
            mus[i:i + m] += 0.4 * ky[:m]
            tt += 0.3
        mus *= np.minimum(1, (JP.DURATION - np.arange(n) / SR) / 0.6)
        mus = np.tanh(1.6 * mus / (np.abs(mus).max() + 1e-9)) / np.tanh(1.6)
        i0 = int(end_t * SR)
        m = min(len(mus), n_out - i0)
        extra[i0:i0 + m] += 1.1 * mus[:m]
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
    ap.add_argument("-n", type=int, default=60)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
