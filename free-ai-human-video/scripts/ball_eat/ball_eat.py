"""「パチンコのヘソに入った玉が、虹色の玉を食べつくせる?」(参考動画「balls eaten」の形 + パチンコ)
上はパチンコの盤面。左のレールから銀の玉が一発ずつ打ちこまれ、釘に当たりながら落ちる。
下のまん中のヘソ(入賞口)に入った玉だけが、下のへやに落ちて「口をあけたキャラ」に変身する。外れた玉は両はしのアウト口へ消える。
へやの中には小さな虹色の玉がぎっしりつまっていて、キャラはふれた玉を食べて大きくなる(面積を GROW の割合で足す)。
キャラは重力で落ちて、かべやほかのキャラにふつうに跳ね返る(物理エンジン pymunk。食べても向きは変わらない)。
TIME_LIMIT 秒以内に全部食べたら成功(大当たり演出)、残ったら失敗(幽霊 → 暗くなって「Failed...」+ 残った玉を赤い輪で表示)。

- ねらい・補正なし。シードで変わるのは、打ちこむ強さの小さなばらつき(ハンドルのぶれ)だけ。

使い方:
    python ball_eat.py search [-n 80]
    python ball_eat.py render --seed N
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
SUBSTEPS = int(os.environ.get("SUBSTEPS", 5))
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

GRAVITY = float(os.environ.get("GRAVITY", 1500.0))
# 盤面
BX0, BX1, BY0 = 140.0, 940.0, 372.0
FLOOR_C, FLOOR_S = 878.0, 922.0      # 床の高さ(ヘソのそば / かべのそば)。ヘソからはなれる向きに下がる
OUT_W = 42.0                          # アウト口のはば(左右のかべぎわ)
HX = 540.0                            # ヘソの位置
HW = float(os.environ.get("HW", 15.0))   # ヘソの口のはばの半分
RB = 9.0                              # パチンコ玉の半径
NAIL_R = 4.0
SHOT_DT = float(os.environ.get("SHOT_DT", 0.3))   # 打ちこむ間かく(秒)
LAUNCH_V = float(os.environ.get("LAUNCH_V", 640.0))
LAUNCH_J = float(os.environ.get("LAUNCH_J", 0.07))  # 打ちこむ強さのばらつき(±割合)
# へや
CX0, CX1, CY0, CY1, CR = 150.0, 930.0, 948.0, 1556.0, 110.0
PIPE_Y = 938.0
RS = float(os.environ.get("RS", 4.5))            # 小さな玉の半径
GROW = float(os.environ.get("GROW", 0.02))       # 食べた玉の面積のこの割合だけキャラの面積がふえる
E_BOUNCE = float(os.environ.get("E_BOUNCE", 1.0))   # へやの中の跳ね返り(はねかえり係数)
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 45.0))
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG
CCX, CCY = (CX0 + CX1) / 2, (CY0 + CY1) / 2


def rrect_pts(x0, y0, x1, y1, r, n=10):
    """角の丸い長方形のふち(右上の角から時計回り)。"""
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def inside_rrect(x, y, x0, y0, x1, y1, r, pad):
    x0 += pad; y0 += pad; x1 -= pad; y1 -= pad; r = max(0.0, r - pad)
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    qx = min(max(x, x0 + r), x1 - r)
    qy = min(max(y, y0 + r), y1 - r)
    return math.hypot(x - qx, y - qy) <= r


def lattice():
    s = 2 * RS
    pts = []
    j = 0
    y = CY0 + RS + 1
    while y < CY1:
        off = (s / 2) if j % 2 else 0.0
        x = CX0 + RS + 1 + off
        while x < CX1:
            if inside_rrect(x, y, CX0, CY0, CX1, CY1, CR, RS + 0.5):
                pts.append((x, y))
            x += s
        y += s * math.sqrt(3) / 2
        j += 1
    return np.array(pts)


PTS = lattice()
NB = len(PTS)
CELL = 24.0
_GX = ((PTS[:, 0] - CX0) // CELL).astype(int)
_GY = ((PTS[:, 1] - CY0) // CELL).astype(int)
BUCKET = {}
for _i, (_a, _b) in enumerate(zip(_GX, _GY)):
    BUCKET.setdefault((_a, _b), []).append(_i)
BUCKET = {k: np.array(v) for k, v in BUCKET.items()}


def nails():
    ns = []
    rows = 10
    for j in range(rows):
        y = 448 + j * 40
        off = 0 if j % 2 == 0 else 25
        x = BX0 + 38 + off
        while x < BX1 - 30:
            if not (abs(x - HX) < 30 and y > 760):   # ヘソのま上はあける
                ns.append((x, y))
            x += 50
    ns += [(HX - HW - 12, FLOOR_C - 34), (HX + HW + 12, FLOOR_C - 34)]   # ヘソの両わきの「命釘」
    return ns


NAILS = nails()


class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 20
        self.space = sp
        st = sp.static_body

        def seg(a, b, e, kind):
            s = pymunk.Segment(st, a, b, 2)
            s.elasticity, s.friction = e, 0.2
            s.collision_type = kind
            sp.add(s)
        # 盤面のかべ・天井
        seg((BX0, BY0), (BX0, FLOOR_S + 30), 0.5, 3)
        seg((BX1, BY0), (BX1, FLOOR_S + 30), 0.5, 3)
        seg((BX0, BY0), (BX1, BY0), 0.5, 3)
        # 床(ヘソに向かって高くなる)とアウト口
        seg((BX0 + OUT_W, FLOOR_S), (HX - HW, FLOOR_C), 0.3, 6)
        seg((HX + HW, FLOOR_C), (BX1 - OUT_W, FLOOR_S), 0.3, 6)
        # ヘソからへやへの短いパイプ
        seg((HX - HW, FLOOR_C), (HX - HW, CY0), 0.5, 3)
        seg((HX + HW, FLOOR_C), (HX + HW, CY0), 0.5, 3)
        # 釘
        for x, y in NAILS:
            c = pymunk.Circle(st, NAIL_R, (x, y))
            c.elasticity, c.friction = 0.55, 0.1
            c.collision_type = 2
            sp.add(c)
        # へや(角の丸い長方形)。上のまん中にヘソからの入口
        pts = rrect_pts(CX0, CY0, CX1, CY1, CR)
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if a[1] < CY0 + 1 and b[1] < CY0 + 1 and min(a[0], b[0]) < HX + HW and max(a[0], b[0]) > HX - HW:
                # 上の辺はヘソの口のところで切る
                lo, hi = min(a[0], b[0]), max(a[0], b[0])
                if lo < HX - HW:
                    seg((lo, CY0), (HX - HW, CY0), E_BOUNCE, 4)
                if hi > HX + HW:
                    seg((HX + HW, CY0), (hi, CY0), E_BOUNCE, 4)
                continue
            seg(a, b, E_BOUNCE, 4)
        sp.on_collision(1, 2, begin=self._nail)
        for sh in sp.shapes:   # 床はつるつる(玉が転がってアウト口へ)
            if sh.collision_type == 6:
                sh.friction = 0.0
        self.balls = []     # 盤面の玉
        self.eaters = []    # へやのキャラ
        self.alive = np.ones(NB, bool)
        self.left = NB
        self.t = 0.0
        self.next_shot = 0.3
        self.events = []
        self.result, self.result_t = None, None
        self.eat_now = 0
        self.nid = 0
        self.shots = 0
        self.entries = 0

    def _nail(self, arb, space, data):
        if arb.total_impulse.length > 0 or True:
            v = arb.shapes[0].body.velocity.length
            if v > 120:
                self.events.append(("nail", self.t, min(1.0, v / 900)))
        return True

    def shoot(self):
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, RB))
        b.position = (BX0 + 22, BY0 + 22)
        v = LAUNCH_V * (1 + self.rng.uniform(-LAUNCH_J, LAUNCH_J))
        b.velocity = (v, 40.0)
        s = pymunk.Circle(b, RB)
        s.elasticity, s.friction = 0.6, 0.1
        s.collision_type = 1
        self.space.add(b, s)
        self.nid += 1
        self.balls.append({"id": self.nid, "b": b, "s": s, "still": 0.0})
        self.shots += 1
        self.events.append(("shot", self.t, None))

    def step(self, dt):
        self.t += dt
        if self.result is None and self.t >= self.next_shot:
            self.next_shot += SHOT_DT
            self.shoot()
        self.space.step(dt)
        keep = []
        for o in self.balls:
            b = o["b"]
            x, y = b.position
            if y > CY0 + RB:            # ヘソに入ってへやに落ちた → キャラに変身
                o["s"].collision_type = 5
                o["s"].elasticity = 1.0
                o["s"].friction = 0.0
                o["r"] = RB
                o["eat"] = 0
                self.eaters.append(o)
                self.entries += 1
                self.events.append(("heso", self.t, (x, y)))
                continue
            if y > FLOOR_S - 6 and (x < BX0 + OUT_W + 2 or x > BX1 - OUT_W - 2):   # アウト口
                self.space.remove(b, o["s"])
                self.events.append(("out", self.t, None))
                continue
            o["still"] = o["still"] + dt if b.velocity.length < 6 else 0.0
            if o["still"] > 1.0:        # 引っかかって止まった玉は消える
                self.space.remove(b, o["s"])
                continue
            keep.append(o)
        self.balls = keep
        # 食べる
        if self.result is None:
            for o in self.eaters:
                b = o["b"]
                x, y = b.position
                r = o["r"]
                reach = r + RS
                gx0, gx1 = int((x - reach - CX0) // CELL), int((x + reach - CX0) // CELL)
                gy0, gy1 = int((y - reach - CY0) // CELL), int((y + reach - CY0) // CELL)
                n = 0
                for gx in range(gx0, gx1 + 1):
                    for gy in range(gy0, gy1 + 1):
                        idx = BUCKET.get((gx, gy))
                        if idx is None:
                            continue
                        idx = idx[self.alive[idx]]
                        if not len(idx):
                            continue
                        d = np.hypot(PTS[idx, 0] - x, PTS[idx, 1] - y)
                        hit = idx[d < reach]
                        if len(hit):
                            self.alive[hit] = False
                            n += len(hit)
                if n:
                    r = math.sqrt(r * r + GROW * n * RS * RS)
                    o["r"] = r
                    o["s"].unsafe_set_radius(r)
                    m = (r / RB) ** 2
                    b.mass = m
                    b.moment = pymunk.moment_for_circle(m, 0, r)
                    self.left -= n
                    self.eat_now += n
                    o["eat"] += n
                    self.events.append(("eat", self.t, (x, y, n, r, NB - self.left)))
            if self.left <= 0:
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
        g.eat_now = 0
        for o in g.eaters:
            o["eat"] = 0
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "left": g.left,
                           "balls": [(o["id"], *o["b"].position) for o in g.balls],
                           "eaters": [(o["id"], *o["b"].position, o["r"], *o["b"].velocity, o["eat"]) for o in g.eaters],
                           "alive": g.alive.copy() if (g.eat_now or not frames) else None, "eat": g.eat_now})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "left": g.left, "total": NB, "shots": g.shots, "entries": g.entries}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), r["left"], round(1 - r["left"] / r["total"], 4), r["entries"], r["shots"]


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件 (玉 {NB} 個)")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
HB = 36
_ANG = (np.arctan2(PTS[:, 1] - CCY, PTS[:, 0] - CCX) / (2 * math.pi)) % 1.0
HUE_BIN = (_ANG * HB).astype(int) % HB


def rrect(ctx, x0, y0, x1, y1, r):
    ctx.new_path()
    ctx.arc(x1 - r, y0 + r, r, -math.pi / 2, 0)
    ctx.arc(x1 - r, y1 - r, r, 0, math.pi / 2)
    ctx.arc(x0 + r, y1 - r, r, math.pi / 2, math.pi)
    ctx.arc(x0 + r, y0 + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def silver(ctx, x, y, r):
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.05, x, y, r)
    g.add_color_stop_rgb(0, 1.0, 1.0, 1.0)
    g.add_color_stop_rgb(0.35, 0.82, 0.85, 0.9)
    g.add_color_stop_rgb(1, 0.35, 0.38, 0.45)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()


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


# 小さな玉の色:まん中からの向きで虹色(色相 HB 段階)
def draw_hero(ctx, x, y, r, ang, mouth, t):
    """食べるキャラ:まんまるの体に目とほっぺ。進む向きに大きな口をあけて、食べるたびにパクパクする。
    ang:進む向き、mouth:口のあき具合(0〜1)。左向きのときは左右反転して、顔がさかさまにならないようにする。"""
    for k, al in ((2.4, 0.06), (1.7, 0.12), (1.25, 0.22)):   # まわりの光
        g = cairo.RadialGradient(x, y, r * 0.6, x, y, r * k)
        g.add_color_stop_rgba(0, 1.0, 0.85, 0.4, al)
        g.add_color_stop_rgba(1, 1.0, 0.7, 0.2, 0)
        ctx.arc(x, y, r * k, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
    ctx.save()
    ctx.translate(x, y)
    flip = math.cos(ang) < 0
    if flip:
        ctx.scale(-1, 1)
        ang = math.pi - ang
    ctx.rotate(ang)
    ctx.scale(r, r)
    # 体
    g = cairo.RadialGradient(-0.35, -0.45, 0.05, 0, 0, 1)
    g.add_color_stop_rgb(0, 1.0, 0.98, 0.85)
    g.add_color_stop_rgb(0.4, 1.0, 0.8, 0.3)
    g.add_color_stop_rgb(1, 0.92, 0.45, 0.08)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    # 口(進む向きにあく)
    mo = 0.12 + 0.88 * mouth
    mx, my = 0.5, 0.18
    rw, rh = 0.42, 0.42 * mo
    ctx.save()
    ctx.translate(mx, my)
    ctx.scale(rw, max(0.02, rh))
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.35, 0.05, 0.08)
    ctx.fill_preserve()
    ctx.save()
    ctx.clip()
    ctx.arc(mx + 0.05, my + rh * 0.9, 0.3, 0, 2 * math.pi)   # 舌
    ctx.set_source_rgb(1.0, 0.45, 0.55)
    ctx.fill()
    for tx_ in (mx - 0.16, mx + 0.1):                         # 上の歯
        ctx.rectangle(tx_, my - rh - 0.02, 0.11, 0.07 + 0.08 * mo)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
    ctx.restore()
    ctx.save()
    ctx.translate(mx, my)
    ctx.scale(rw, max(0.02, rh))
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.55, 0.2, 0.05)
    ctx.set_line_width(0.05)
    ctx.stroke()
    # 目(白目+黒目+光)
    blink = (t % 3.1) < 0.1
    for ex, ey, er in ((0.12, -0.42, 0.2), (0.55, -0.36, 0.17)):
        if blink:
            ctx.move_to(ex - er, ey)
            ctx.line_to(ex + er, ey)
            ctx.set_source_rgb(0.2, 0.08, 0.05)
            ctx.set_line_width(0.06)
            ctx.stroke()
            continue
        ctx.arc(ex, ey, er, 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        ctx.arc(ex + er * 0.35, ey + er * 0.05, er * 0.6, 0, 2 * math.pi)
        ctx.set_source_rgb(0.1, 0.06, 0.05)
        ctx.fill()
        ctx.arc(ex + er * 0.45, ey - er * 0.25, er * 0.22, 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
    # ほっぺ
    ctx.save()
    ctx.translate(-0.2, 0.15)
    ctx.scale(0.2, 0.12)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(1.0, 0.4, 0.45, 0.55)
    ctx.fill()
    ctx.restore()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"ball_eat_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"ball_eat_{seed}.wav")
    final = os.path.join(OUT_DIR, f"ball_eat_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"be_preview_{seed}_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, CCX, CCY, reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=("Congratulations!!", "COMPLETE", ""), font="Playfair Display", slim=True)
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    cols = [colorsys.hsv_to_rgb(k / HB, 0.85, 1.0) for k in range(HB)]
    # 動かない部分(盤面・釘・へやのわく)は先に1枚の絵にしておく
    base = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(base)
    bc.set_source_rgb(0.03, 0.035, 0.06)
    bc.paint()
    rrect(bc, BX0 - 14, BY0 - 14, BX1 + 14, FLOOR_S + 26, 40)
    g = cairo.LinearGradient(0, BY0, 0, FLOOR_S)
    g.add_color_stop_rgb(0, 0.09, 0.07, 0.2)
    g.add_color_stop_rgb(1, 0.05, 0.1, 0.2)
    bc.set_source(g)
    bc.fill_preserve()
    for wd, al in ((14, 0.1), (3, 0.85)):
        bc.set_source_rgba(1.0, 0.8, 0.35, al)
        bc.set_line_width(wd)
        bc.stroke_preserve()
    bc.new_path()
    for x, y in NAILS:
        bc.arc(x + 1, y + 1.5, NAIL_R, 0, 2 * math.pi)
        bc.set_source_rgba(0, 0, 0, 0.5)
        bc.fill()
        g = cairo.RadialGradient(x - 1.2, y - 1.2, 0.3, x, y, NAIL_R)
        g.add_color_stop_rgb(0, 1, 1, 1)
        g.add_color_stop_rgb(1, 0.6, 0.62, 0.7)
        bc.arc(x, y, NAIL_R, 0, 2 * math.pi)
        bc.set_source(g)
        bc.fill()
    # 床とアウト口
    bc.move_to(BX0 + OUT_W, FLOOR_S)
    bc.line_to(HX - HW, FLOOR_C)
    bc.move_to(HX + HW, FLOOR_C)
    bc.line_to(BX1 - OUT_W, FLOOR_S)
    bc.set_source_rgb(0.75, 0.8, 0.9)
    bc.set_line_width(4)
    bc.stroke()
    for ox in (BX0, BX1 - OUT_W):
        bc.rectangle(ox + 3, FLOOR_S - 4, OUT_W - 6, 26)
        bc.set_source_rgb(0, 0, 0)
        bc.fill()
    # へやのわく
    for wd, al in ((18, 0.08), (8, 0.18), (3, 0.9)):
        rrect(bc, CX0 - 2, CY0 - 2, CX1 + 2, CY1 + 2, CR + 2)
        bc.set_source_rgba(0.85, 0.95, 1.0, al)
        bc.set_line_width(wd)
        bc.stroke()
    # ヘソとパイプ
    bc.rectangle(HX - HW, FLOOR_C - 2, 2 * HW, CY0 - FLOOR_C + 6)
    bc.set_source_rgb(0.02, 0.02, 0.04)
    bc.fill()
    for sx in (-1, 1):
        bc.move_to(HX + sx * HW, FLOOR_C - 2)
        bc.line_to(HX + sx * HW, CY0)
    bc.set_source_rgb(1.0, 0.82, 0.3)
    bc.set_line_width(3)
    bc.stroke()
    # 打ちこみレール(左)
    bc.move_to(BX0 - 30, FLOOR_S + 20)
    bc.line_to(BX0 - 30, BY0 + 40)
    bc.arc(BX0 + 10, BY0 + 40, 40, math.pi, 1.5 * math.pi)
    bc.set_source_rgba(0.8, 0.85, 0.95, 0.5)
    bc.set_line_width(3)
    bc.stroke()

    def heso_deco(ctx, flash):
        """ヘソ:金色の小さな受け皿と羽。入った直後は光る。"""
        for sx in (-1, 1):
            ctx.move_to(HX + sx * HW, FLOOR_C - 2)
            ctx.curve_to(HX + sx * (HW + 10), FLOOR_C - 20, HX + sx * (HW + 26), FLOOR_C - 16, HX + sx * (HW + 34), FLOOR_C - 4)
        ctx.set_source_rgb(1.0, 0.8, 0.25)
        ctx.set_line_width(4)
        ctx.stroke()
        if flash > 0:
            gg = cairo.RadialGradient(HX, FLOOR_C, 2, HX, FLOOR_C, 90)
            gg.add_color_stop_rgba(0, 1, 0.95, 0.6, 0.9 * flash)
            gg.add_color_stop_rgba(1, 1, 0.7, 0.2, 0)
            ctx.arc(HX, FLOOR_C, 90, 0, 2 * math.pi)
            ctx.set_source(gg)
            ctx.fill()
        chic(ctx, "ヘソ", HX, FLOOR_C - 44, 22, rgb=(1, 0.85, 0.45), alpha=0.8, weight="Medium")

    heso_t = [t for k, t, _ in events if k == "heso"]
    hi = 0
    last_heso = -9.0
    prng = np.random.default_rng(seed + 9)
    parts = []
    alive = frames[0]["alive"]
    frozen = None
    face = {}   # キャラごとの向きと口
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while hi < len(heso_t) and heso_t[hi] <= t:
            last_heso = heso_t[hi]
            hi += 1
        if fr["alive"] is not None:
            prev_alive = alive
            alive = fr["alive"]
            gone = np.nonzero(prev_alive & ~alive)[0]
            for k in gone[:: max(1, len(gone) // 10)]:
                a = prng.uniform(0, 2 * math.pi)
                sp_ = prng.uniform(80, 300)
                parts.append([PTS[k, 0], PTS[k, 1], sp_ * math.cos(a), sp_ * math.sin(a), 0.0, HUE_BIN[k]])
        over = end_t is not None and t >= end_t
        win_b = (t - end_t) if (ending is not None and over) else -1.0
        if win_b >= PRE:
            ending.draw(surf, ctx, win_b - PRE + JP.T_BIG)
            giragira(ctx, win_b - PRE, fever, glints, W, H, WIN_DUR)
            ff.stdin.write(surf.get_data())
            continue
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        if fail and over:
            if frozen is None:
                frozen = (fr, alive)
            fr, alive = frozen
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        ctx.set_source_surface(base, 0, 0)
        ctx.paint()
        heso_deco(ctx, max(0.0, 1 - (t - last_heso) / 0.5))
        # 虹色の玉(キャラに近いほど明るい)
        near = np.zeros(NB, bool)
        for e in fr["eaters"]:
            near |= np.hypot(PTS[:, 0] - e[1], PTS[:, 1] - e[2]) < e[3] + 110
        for k in range(HB):
            sel = alive & (HUE_BIN == k)
            if not sel.any():
                continue
            c = cols[k]
            for lit in (False, True):
                ss = sel & (near if lit else ~near)
                if not ss.any():
                    continue
                for px, py in PTS[ss]:
                    ctx.new_sub_path()
                    ctx.arc(px, py, RS - 0.35, 0, 2 * math.pi)
                f = 1.0 if lit else 0.78
                ad = 0.22 if lit else 0.0
                ctx.set_source_rgb(min(1, c[0] * f + ad), min(1, c[1] * f + ad), min(1, c[2] * f + ad))
                ctx.fill()
        nleft = int(alive.sum())
        if 0 < nleft <= 80 and not over:   # 残りわずかは光らせる(見た目だけ)
            pul = 0.5 + 0.5 * math.sin(t * 7)
            for k in np.nonzero(alive)[0]:
                px, py = PTS[k]
                c = cols[HUE_BIN[k]]
                g = cairo.RadialGradient(px, py, 1, px, py, 22 + 6 * pul)
                g.add_color_stop_rgba(0, *c, 0.65)
                g.add_color_stop_rgba(1, *c, 0)
                ctx.arc(px, py, 22 + 6 * pul, 0, 2 * math.pi)
                ctx.set_source(g)
                ctx.fill()
        # 光のつぶ
        keep = []
        for p in parts:
            p[4] += 1 / FPS
            if p[4] > 0.5:
                continue
            p[0] += p[2] / FPS
            p[1] += p[3] / FPS
            p[2] *= 0.92
            p[3] *= 0.92
            ctx.arc(p[0], p[1], 2.2, 0, 2 * math.pi)
            ctx.set_source_rgba(*cols[p[5]], 1 - p[4] / 0.5)
            ctx.fill()
            keep.append(p)
        parts = keep[-700:]
        # 盤面の玉
        for _, x, y in fr["balls"]:
            silver(ctx, x, y, RB)
        # キャラ
        for eid, x, y, r, vx, vy, ne in fr["eaters"]:
            st = face.get(eid)
            want = math.atan2(vy, vx) if (vx * vx + vy * vy) > 400 else (st["ang"] if st else 0.0)
            if st is None:
                st = face[eid] = {"ang": want, "munch": 0.0, "ph": 0.0}
            if not over:
                d_ = (want - st["ang"] + math.pi) % (2 * math.pi) - math.pi
                st["ang"] += d_ * 0.3
                st["munch"] = min(1.0, st["munch"] + 0.5) if ne else max(0.0, st["munch"] - 0.05)
                st["ph"] += 0.55 * st["munch"]
            mouth = 0.85 if st["munch"] < 0.05 else 0.5 + 0.5 * math.cos(st["ph"])
            draw_hero(ctx, x, y, r, st["ang"], mouth, t + eid * 0.7)
        # 文字
        chic(ctx, "全部たべられる？", W / 2, 200, 62, rgb=(1, 0.88, 0.6))
        pct = int((1 - fr["left"] / NB) * 100)
        chic(ctx, f"{pct}%", W / 2 - 110, 310, 84, rgb=(1, 1, 1), weight="Medium")
        tt = min(t, end_t) if end_t is not None else t
        lft = max(0.0, TIME_LIMIT - tt)
        chic(ctx, f"{lft:4.1f}", W / 2 + 130, 305, 44, rgb=(1, 0.45, 0.45) if lft < 5 else (0.7, 0.75, 0.85), weight="Medium")
        if not over:
            horror(ctx, "失敗したら…", W / 2, 1650, 74, t)
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
            pul = 0.5 + 0.5 * math.sin(after * 6)
            a_ = min(1.0, after / 0.6)
            for px, py in PTS[alive][:60]:   # 食べのこした玉を赤い輪で示す(結果はそのまま)
                for wd, al in ((10, 0.18), (3, 0.9)):
                    ctx.arc(px, py, 20 + 5 * pul, 0, 2 * math.pi)
                    ctx.set_source_rgba(1.0, 0.15, 0.2, al * a_)
                    ctx.set_line_width(wd)
                    ctx.stroke()
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
    pct = 100 * (1 - res["left"] / res["total"])
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {pct:.2f}% / 長さ {duration:.1f}秒 / "
          f"打った玉 {res['shots']} / ヘソ {res['entries']})")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


SCALE = [0, 2, 4, 7, 9]   # ペンタトニック


def pop(f, amp):
    """食べた「ポッ」:やわらかいマリンバ風の短い音。"""
    tt = _t(0.22)
    env = np.minimum(1, tt / 0.003) * np.exp(-tt / 0.06)
    y = np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 4 * f * tt) * np.exp(-tt / 0.02)
    return amp * y * env


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)
    last_eat = -1.0
    last_nail = -1.0
    rng = np.random.default_rng(3)
    for kind, t, data in events:
        if t > end_t + 0.01:
            continue
        if kind == "eat":
            if t - last_eat < 0.05:
                continue
            last_eat = t
            frac = data[4] / NB
            step = int(frac * 30)            # 食べた量が多いほど音が上がる
            m = 60 + 12 * (step // 5) + SCALE[step % 5]
            sig = pop(midi_hz(m), min(1.0, 0.45 + data[2] / 25))
        elif kind == "nail":                 # 釘に当たる「チン」
            if t - last_nail < 0.03:
                continue
            last_nail = t
            tt = _t(0.08)
            f = 3200 + 600 * rng.uniform()
            sig = 0.22 * data * np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.015)
        elif kind == "shot":                 # 打ちこむ「カシャ」
            tt = _t(0.06)
            sig = 0.18 * rng.normal(0, 1, len(tt)) * np.exp(-tt / 0.012)
        elif kind == "heso":                 # ヘソに入った「キュイン!」
            sig = 0.6 * kyuin_one(1.3)
        else:
            continue
        i = int(t * SR)
        j = min(n_out, i + len(sig))
        if i < n_out:
            out[i:j] += sig[: j - i]
    wet = out.copy()
    for dd, g_ in ((0.083, 0.2), (0.131, 0.12), (0.197, 0.07)):
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
