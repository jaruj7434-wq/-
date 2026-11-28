"""「ヘソに入った玉がぶつかると増える、へやをパンパンにできる?」(パチンコ+増える玉)
上はパチンコの盤面。左のレールから銀の玉が一発ずつ打ちこまれ、釘に当たりながら落ちる。
下のまん中のヘソ(入賞口)に入った玉だけが、パイプを通って下のへやに落ち、虹色の玉になる。外れた玉は両はしのアウト口へ消える。
へやの玉どうしが勢いよくぶつかる(ぶつかる速さが V_MIN 以上)と、ぶつかった所に新しい玉がポンと生まれる(小さく生まれてふくらむ)。
増えた玉はしばらく(COOL 秒)は増やさない。へやの中はふつうに跳ね返る(はねかえり係数 E_BOUNCE。少しずつ勢いがなくなる)。
TIME_LIMIT 秒以内に玉が N_FULL 個(へやがパンパン)になったら成功(大当たり演出)、ならなければ失敗(幽霊 → 暗くなって「Failed...」)。

- ねらい・補正なし。シードで変わるのは、打ちこむ強さの小さなばらつき(ハンドルのぶれ)だけ。

使い方:
    python heso_breed.py search [-n 80]
    python heso_breed.py render --seed N
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
BR = float(os.environ.get("BR", 16.0))           # へやの玉の半径
V_MIN = float(os.environ.get("V_MIN", 120.0))    # これ以上の速さでぶつかったら増える
COOL = float(os.environ.get("COOL", 0.4))        # 増やしたあと、次に増やせるまでの時間(秒)
BIRTH_T = 0.25                                    # 生まれた玉がふくらみきるまでの時間
FILL = float(os.environ.get("FILL", 0.82))       # へやの面積のこの割合を玉がうめたら「パンパン」
E_BOUNCE = float(os.environ.get("E_BOUNCE", 0.97))   # へやの中の跳ね返り(はねかえり係数)
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 39.5))
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


def rrect_area(x0, y0, x1, y1, r):
    return (x1 - x0) * (y1 - y0) - (4 - math.pi) * r * r


N_FULL = int(FILL * rrect_area(CX0, CY0, CX1, CY1, CR) / (math.pi * BR * BR))


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
        sp.on_collision(5, 5, begin=self._touch)
        for sh in sp.shapes:   # 床はつるつる(玉が転がってアウト口へ)
            if sh.collision_type == 6:
                sh.friction = 0.0
        self.balls = []     # 盤面の玉
        self.room = []      # へやの玉
        self.by_shape = {}
        self.pending = []
        self.t = 0.0
        self.next_shot = 0.3
        self.events = []
        self.result, self.result_t = None, None
        self.born_now = 0
        self.nid = 0
        self.hue = 0
        self.shots = 0
        self.entries = 0
        self.born = 0

    def _touch(self, arb, space, data):
        """へやの玉どうしがぶつかった:勢いがあれば、あとで新しい玉を生む。"""
        a, b = arb.shapes
        oa, ob = self.by_shape.get(a), self.by_shape.get(b)
        if oa is None or ob is None:
            return True
        n = arb.contact_point_set.normal
        rv = oa["b"].velocity - ob["b"].velocity
        vn = abs(rv.dot(n))
        if vn >= V_MIN and self.t >= oa["cool"] and self.t >= ob["cool"]:
            p = arb.contact_point_set.points[0].point_a if arb.contact_point_set.points else (oa["b"].position + ob["b"].position) / 2
            oa["cool"] = ob["cool"] = self.t + COOL
            self.pending.append((p, (oa["b"].velocity + ob["b"].velocity) / 2, n))
        return True

    def add_room(self, pos, vel, born=False):
        bd = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, BR))
        bd.position = pos
        bd.velocity = vel
        r0 = BR * 0.3 if born else BR
        sh = pymunk.Circle(bd, r0)
        sh.elasticity, sh.friction = 1.0, 0.1
        sh.collision_type = 5
        self.space.add(bd, sh)
        self.nid += 1
        o = {"id": self.nid, "b": bd, "s": sh, "r": r0, "t0": self.t if born else -9, "hue": self.hue % 12,
             "cool": self.t + COOL}
        self.hue += 1
        self.room.append(o)
        self.by_shape[sh] = o
        return o

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
            if y > CY0 + RB:            # ヘソに入ってへやに落ちた → 虹色の玉に
                self.space.remove(b, o["s"])
                self.add_room((x, y), b.velocity)
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
        # 生まれたばかりの玉はふくらむ
        for o in self.room:
            if o["r"] < BR:
                r = BR * min(1.0, 0.3 + 0.7 * (self.t - o["t0"]) / BIRTH_T)
                o["r"] = r
                o["s"].unsafe_set_radius(r)
        # 増える
        if self.result is None and self.pending:
            for p, v, n in self.pending:
                if len(self.room) >= N_FULL:
                    break
                o = self.add_room(p, v, born=True)
                self.born += 1
                self.born_now += 1
                self.events.append(("born", self.t, (p[0], p[1], len(self.room))))
        self.pending = []
        if self.result is None:
            if len(self.room) >= N_FULL:
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
        g.born_now = 0
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "n": len(g.room),
                           "balls": [(o["id"], *o["b"].position) for o in g.balls],
                           "room": [(o["id"], *o["b"].position, o["r"], o["hue"]) for o in g.room],
                           "born": g.born_now})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "n": len(g.room), "shots": g.shots, "entries": g.entries, "born": g.born}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), r["n"], round(r["n"] / N_FULL, 3), r["entries"], r["shots"]


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件 (目標 {N_FULL} 個)")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
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
def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"heso_breed_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"heso_breed_{seed}.wav")
    final = os.path.join(OUT_DIR, f"heso_breed_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"hb_preview_{seed}_{pt:.1f}.png"))
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
    frozen = None
    born_ev = [(t, d) for k, t, d in events if k == "born"]
    bi = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while hi < len(heso_t) and heso_t[hi] <= t:
            last_heso = heso_t[hi]
            hi += 1
        while bi < len(born_ev) and born_ev[bi][0] <= t:   # 生まれた所に光のつぶ
            _, d = born_ev[bi]
            bi += 1
            for _ in range(5):
                a = prng.uniform(0, 2 * math.pi)
                sp_ = prng.uniform(60, 220)
                parts.append([d[0], d[1], sp_ * math.cos(a), sp_ * math.sin(a), 0.0, int(d[2]) % 12])
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
                frozen = fr
            fr = frozen
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        ctx.set_source_surface(base, 0, 0)
        ctx.paint()
        heso_deco(ctx, max(0.0, 1 - (t - last_heso) / 0.5))
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
            ctx.set_source_rgba(*PALETTE[p[5]], 1 - p[4] / 0.5)
            ctx.fill()
            keep.append(p)
        parts = keep[-700:]
        # 盤面の玉
        for _, x, y in fr["balls"]:
            silver(ctx, x, y, RB)
        # へやの玉(虹色・生まれたては白く光る)
        for _, x, y, r, hue in fr["room"]:
            shiny_ball(ctx, x, y, r, PALETTE[hue])
        # 文字
        chic(ctx, "パンパンにできる？", W / 2, 200, 62, rgb=(1, 0.88, 0.6))
        pct = min(100, int(fr["n"] / N_FULL * 100))
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['n']}/{N_FULL}個 / 長さ {duration:.1f}秒 / "
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
        if kind == "born":                   # 増えた「ポン」(数が多いほど音階が上がる)
            if t - last_eat < 0.05:
                continue
            last_eat = t
            frac = data[2] / N_FULL
            step = int(frac * 30)
            m = 60 + 12 * (step // 5) + SCALE[step % 5]
            sig = pop(midi_hz(m), 0.8)
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
