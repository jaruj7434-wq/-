"""「〇秒以内にガラスを全部割れる?」ゆっくり回るドラム(回転する円い容器)の中にたまったガラスを、
弱いボールから強いボールへ順番に入れて割っていく物理ショートを生成する。

- ドラムの内側には羽根がついていて、回転でガラスやボールを持ち上げては落とす(ねらい・補正なし)。
- ガラスは4種類:薄い板ガラス(2)、ビン(4)、ガラスブロック(8)、分厚い強化ガラス(13)。()はこわれるまでのダメージ。
- ボールは弱い順に1個ずつ入ってくる:スーパーボール → 木の玉 → 鉄球 → 火の玉 → 雷の玉 → 隕石。
  強いボールほど1回で与えるダメージが大きく、エフェクトも派手になる。それぞれ決まった時間だけ暴れて消える。
- ガラスは割れると破片が飛び散る。
6つのボールを使い切るまでに全部割れば成功、割り残したら失敗(幽霊)。

使い方:
    python glass_drum.py search [--want fail|success] [-n 200]
    python glass_drum.py render --seed N
"""

import argparse
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
from ball_escape import FONT, midi_hz, text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
GRAVITY = 1500.0
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

DX, DY, DR = 540.0, 1130.0, 480.0          # ドラムの中心と半径
OMEGA = float(os.environ.get("OMEGA", 0.55))   # ドラムの回る速さ(rad/秒)
N_FINS = 6
FIN_L = float(os.environ.get("FIN_L", 70.0))
WALL_F = float(os.environ.get("WALL_F", 0.25))   # かべの摩擦(低いほどガラスがかべにはりつかない)
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 60.0))   # 実際はボールを使い切った時点で終わり
SETTLE = 2.5                                # 始まる前にガラスを落ち着かせる時間(画面には出さない)
V_MIN = 220.0                               # これより弱い当たりはダメージなし

# ガラス:名前, こわれるまでのダメージ, 数
GLASS = [("板ガラス", 2, 14), ("ビン", 4, 10), ("ガラスブロック", 8, 8), ("強化ガラス", 13, 4)]
if os.environ.get("GLASS_HP"):
    GLASS = [(g[0], int(h), g[2]) for g, h in zip(GLASS, os.environ["GLASS_HP"].split(","))]
# ボール:名前, ダメージ, 半径, 重さ, 暴れる時間(秒), 色
BALLS = [("スーパーボール", 1, 30, 1.0, 5.0, (1.0, 0.35, 0.55)),
         ("木の玉", 2, 34, 2.0, 5.0, (0.75, 0.52, 0.30)),
         ("鉄球", 3, 36, 6.0, 5.5, (0.75, 0.77, 0.82)),
         ("火の玉", 4, 38, 4.0, 5.5, (1.0, 0.45, 0.1)),
         ("雷の玉", 5, 38, 4.0, 5.5, (0.45, 0.75, 1.0)),
         ("隕石", 8, 48, 12.0, 7.0, (0.55, 0.25, 0.15))]
if os.environ.get("BALL_DMG"):
    BALLS = [(b[0], int(d), *b[2:]) for b, d in zip(BALLS, os.environ["BALL_DMG"].split(","))]
if os.environ.get("BALL_LIFE"):
    BALLS = [(*b[:4], float(l), b[5]) for b, l in zip(BALLS, os.environ["BALL_LIFE"].split(","))]
GAP = 0.6                                   # 前のボールが消えてから次が入るまで
OUTRO = 2.5
WIN_DUR = 5.5


def glass_poly(kind, rng):
    """ガラスの形(重心が原点の凸多角形)と、描画用の情報。"""
    if kind == 0:     # 板ガラス:細長い板
        w, h = rng.uniform(110, 150), 14
        return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], (w, h)
    if kind == 1:     # ビン:胴と肩(凸包でまとめる)
        w, h = 38, 100
        pts = [(-w / 2, h / 2), (w / 2, h / 2), (w / 2, -h * 0.05), (w * 0.2, -h * 0.3), (w * 0.2, -h / 2),
               (-w * 0.2, -h / 2), (-w * 0.2, -h * 0.3), (-w / 2, -h * 0.05)]
        return pts, (w, h)
    if kind == 2:     # ガラスブロック:四角
        s = rng.uniform(56, 66)
        return [(-s / 2, -s / 2), (s / 2, -s / 2), (s / 2, s / 2), (-s / 2, s / 2)], (s, s)
    w, h = 130, 36    # 強化ガラス:分厚い板
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], (w, h)


class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 25
        self.space = sp
        # ドラム(キネマティック):円の壁+内側の羽根
        drum = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        drum.position = (DX, DY)
        sp.add(drum)
        self.drum = drum
        n = 96
        pts = [(DR * math.cos(2 * math.pi * i / n), DR * math.sin(2 * math.pi * i / n)) for i in range(n)]
        for i in range(n):
            s = pymunk.Segment(drum, pts[i], pts[(i + 1) % n], 12)
            s.elasticity, s.friction = 0.5, WALL_F
            sp.add(s)
        self.fins = []
        for k in range(N_FINS):   # 羽根:根元の広い三角(かべとの角がとがらないので、ガラスがはさまらない)
            a = 2 * math.pi * k / N_FINS
            da = FIN_L * 0.9 / DR
            tri = [((DR + 5) * math.cos(a - da), (DR + 5) * math.sin(a - da)),
                   ((DR + 5) * math.cos(a + da), (DR + 5) * math.sin(a + da)),
                   ((DR - FIN_L) * math.cos(a), (DR - FIN_L) * math.sin(a))]
            s = pymunk.Poly(drum, tri, radius=4)
            s.elasticity, s.friction = 0.4, 0.3
            sp.add(s)
            self.fins.append(tri)
        # ガラス:ドラムの下の方にばらまいて、落ち着かせる
        self.glass = []
        self.glass_of = {}
        kinds = [k for k, g in enumerate(GLASS) for _ in range(g[2])]
        rng.shuffle(kinds)
        for i, k in enumerate(kinds):
            poly, size = glass_poly(k, rng)
            m = 0.4 * (size[0] * size[1]) / 1000
            b = pymunk.Body(m, pymunk.moment_for_poly(m, poly))
            while True:   # ドラムの中(下半分寄り)に置く
                x, y = rng.uniform(-DR, DR), rng.uniform(-DR * 0.6, DR)
                if math.hypot(x, y) < DR - 110:
                    break
            b.position = (DX + x, DY + y)
            b.angle = rng.uniform(0, math.pi)
            s = pymunk.Poly(b, poly, radius=1)
            s.elasticity, s.friction = 0.25, 0.6
            s.collision_type = 2
            sp.add(b, s)
            g = {"id": i, "kind": k, "hp": GLASS[k][1], "hp0": GLASS[k][1], "body": b, "shape": s,
                 "alive": True, "size": size, "poly": poly, "break_t": None, "hit_t": None}
            self.glass.append(g)
            self.glass_of[s] = g
        # 落ち着かせる(ドラムは止めたまま)
        for _ in range(int(SETTLE * 240)):
            sp.step(1 / 240)
        drum.angular_velocity = OMEGA
        sp.on_collision(1, 2, begin=self._hit)
        self.balls = []
        self.ball_i = -1
        self.next_ball_t = 0.3
        self.events = []
        self.t = 0.0
        self.broken = 0
        self.result, self.result_t = None, None
        self.to_break = []

    def _hit(self, arb, space, data):
        if self.result is not None:
            return
        bs, gs = arb.shapes
        g = self.glass_of.get(gs)
        ball = next((b for b in self.balls if b["shape"] is bs), None)
        if g is None or ball is None or not g["alive"]:
            return
        vrel = (bs.body.velocity - gs.body.velocity).dot(arb.normal)
        if abs(vrel) < V_MIN:
            return
        dmg = BALLS[ball["kind"]][1]
        g["hp"] -= dmg
        g["hit_t"] = self.t
        p = arb.contact_point_set.points[0].point_a if arb.contact_point_set.points else bs.body.position
        if g["hp"] <= 0 and g not in self.to_break:
            self.to_break.append(g)
            self.events.append(("break", self.t, (g["id"], ball["kind"], gs.body.position.x, gs.body.position.y)))
        else:
            self.events.append(("hit", self.t, (g["id"], ball["kind"], p.x, p.y)))

    def add_ball(self, kind):
        _, dmg, r, m, life, col = BALLS[kind]
        b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, r))
        b.position = (DX + self.rng.uniform(-60, 60), DY - DR + r + 40)
        b.velocity = (self.rng.uniform(-150, 150), 300)
        b.angular_velocity = self.rng.uniform(-8, 8)
        s = pymunk.Circle(b, r)
        s.elasticity, s.friction = 0.75, 0.5
        s.collision_type = 1
        self.space.add(b, s)
        self.balls.append({"kind": kind, "body": b, "shape": s, "born": self.t, "life": life})
        self.events.append(("ball", self.t, kind))

    def step(self, dt):
        self.t += dt
        if self.result is None and not self.balls and self.t >= self.next_ball_t and self.ball_i + 1 < len(BALLS):
            self.ball_i += 1
            self.add_ball(self.ball_i)
        self.to_break = []
        self.space.step(dt)
        for g in self.to_break:
            if g["alive"]:
                g["alive"] = False
                g["break_t"] = self.t
                self.space.remove(g["body"], g["shape"])
                self.broken += 1
        for b in list(self.balls):
            if self.t - b["born"] > b["life"]:
                self.space.remove(b["body"], b["shape"])
                self.balls.remove(b)
                self.events.append(("ball_end", self.t, (b["kind"], b["body"].position.x, b["body"].position.y)))
                self.next_ball_t = self.t + GAP
        if self.result is None:
            if self.broken == len(self.glass):
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT or (not self.balls and self.ball_i + 1 >= len(BALLS)):
                self.result, self.result_t = "fail", min(self.t, TIME_LIMIT)
                self.events.append(("fail", self.t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "drum": g.drum.angle,
                           "glass": [(x["id"], x["body"].position.x, x["body"].position.y, x["body"].angle)
                                     for x in g.glass if x["alive"]],
                           "balls": [(b["kind"], b["body"].position.x, b["body"].position.y, b["body"].angle,
                                      b["body"].velocity.x, b["body"].velocity.y, g.t - b["born"]) for b in g.balls],
                           "broken": g.broken, "ball_i": g.ball_i})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else WIN_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "broken": g.broken, "n_glass": len(g.glass),
            "glass": [{"kind": x["kind"], "poly": x["poly"], "size": x["size"], "hp0": x["hp0"]} for x in g.glass]}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["broken"], r["n_glass"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "fail":
        for seed, _, rt, b, ng in sorted([r for r in rs if r[1] == "fail"], key=lambda r: -r[3])[:12]:
            print(f"seed={seed:4d}  {b}/{ng} 枚  {rt:5.2f}秒")
    else:
        for seed, _, rt, b, ng in sorted(succ, key=lambda r: -r[2])[:12]:
            print(f"seed={seed:4d}  全部割った {rt:5.2f}秒")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def background():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, 0.03, 0.035, 0.045)
    g.add_color_stop_rgb(0.6, 0.06, 0.065, 0.08)
    g.add_color_stop_rgb(1, 0.02, 0.02, 0.025)
    ctx.set_source(g)
    ctx.paint()
    spot = cairo.RadialGradient(DX, DY - 200, 40, DX, DY, 950)
    spot.add_color_stop_rgba(0, 1, 0.97, 0.92, 0.10)
    spot.add_color_stop_rgba(1, 1, 0.97, 0.92, 0)
    ctx.set_source(spot)
    ctx.paint()
    # ドラムの奥(暗い鉄板)
    ctx.arc(DX, DY, DR, 0, 2 * math.pi)
    inner = cairo.RadialGradient(DX - 120, DY - 160, 30, DX, DY, DR)
    inner.add_color_stop_rgb(0, 0.13, 0.14, 0.16)
    inner.add_color_stop_rgb(1, 0.05, 0.05, 0.06)
    ctx.set_source(inner)
    ctx.fill()
    return surf


def draw_drum(ctx, ang):
    """鋼のドラム:太い金属のふち+回るボルト+三角の羽根。"""
    ctx.new_path()
    ctx.arc(DX, DY, DR + 14, 0, 2 * math.pi)
    rim = cairo.LinearGradient(DX - DR, DY - DR, DX + DR, DY + DR)
    rim.add_color_stop_rgb(0, 0.85, 0.87, 0.9)
    rim.add_color_stop_rgb(0.35, 0.35, 0.37, 0.4)
    rim.add_color_stop_rgb(0.6, 0.75, 0.77, 0.8)
    rim.add_color_stop_rgb(1, 0.25, 0.26, 0.29)
    ctx.set_source(rim)
    ctx.set_line_width(30)
    ctx.stroke()
    ctx.new_path()
    ctx.arc(DX, DY, DR + 30, 0, 2 * math.pi)
    ctx.set_source_rgba(0, 0, 0, 0.6)
    ctx.set_line_width(4)
    ctx.stroke()
    for k in range(24):   # ボルト
        a = ang + 2 * math.pi * k / 24
        x, y = DX + (DR + 14) * math.cos(a), DY + (DR + 14) * math.sin(a)
        g = cairo.RadialGradient(x - 2, y - 2, 1, x, y, 7)
        g.add_color_stop_rgb(0, 0.95, 0.95, 0.97)
        g.add_color_stop_rgb(1, 0.3, 0.3, 0.33)
        ctx.new_path()
        ctx.arc(x, y, 6, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
    for k in range(N_FINS):   # 三角の羽根
        a = ang + 2 * math.pi * k / N_FINS
        da = FIN_L * 0.9 / DR
        pts = [(DX + (DR + 2) * math.cos(a - da), DY + (DR + 2) * math.sin(a - da)),
               (DX + (DR + 2) * math.cos(a + da), DY + (DR + 2) * math.sin(a + da)),
               (DX + (DR - FIN_L) * math.cos(a), DY + (DR - FIN_L) * math.sin(a))]
        ctx.new_path()
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        g = cairo.LinearGradient(pts[0][0], pts[0][1], pts[2][0], pts[2][1])
        g.add_color_stop_rgb(0, 0.55, 0.57, 0.6)
        g.add_color_stop_rgb(1, 0.85, 0.87, 0.9)
        ctx.set_source(g)
        ctx.fill_preserve()
        ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.set_line_width(2)
        ctx.stroke()


GLASS_TINT = [(0.75, 0.9, 1.0), (0.45, 0.85, 0.55), (0.8, 0.95, 1.0), (0.55, 0.75, 1.0)]


def draw_glass(ctx, g, x, y, ang, dmg, flash, gid):
    """透明なガラス:うすい色+白いふち+映りこみの線。ダメージに応じてヒビ。"""
    poly, kind = g["poly"], g["kind"]
    tint = GLASS_TINT[kind]
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.new_path()
    ctx.move_to(*poly[0])
    for p in poly[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    w, h = g["size"]
    fill = cairo.LinearGradient(-w / 2, -h / 2, w / 2, h / 2)
    a0 = 0.30 if kind != 2 else 0.40
    fill.add_color_stop_rgba(0, *tint, a0 + 0.15)
    fill.add_color_stop_rgba(0.5, *tint, a0 * 0.5)
    fill.add_color_stop_rgba(1, *tint, a0 + 0.1)
    ctx.set_source(fill)
    ctx.fill_preserve()
    ctx.set_source_rgba(*[min(1, c + 0.2) for c in tint], 0.9)
    ctx.set_line_width(2.5 if kind != 3 else 4)
    ctx.stroke()
    # 映りこみ(ななめの白い線)
    ctx.new_path()
    ctx.move_to(-w * 0.35, -h * 0.35)
    ctx.line_to(-w * 0.05, h * 0.35)
    ctx.set_source_rgba(1, 1, 1, 0.45)
    ctx.set_line_width(3)
    ctx.stroke()
    if kind == 2:   # ガラスブロックの内側の四角
        ctx.rectangle(-w * 0.3, -h * 0.3, w * 0.6, h * 0.6)
        ctx.set_source_rgba(1, 1, 1, 0.25)
        ctx.set_line_width(2)
        ctx.stroke()
    if kind == 3:   # 強化ガラスの網
        ctx.set_source_rgba(0.85, 0.9, 1, 0.35)
        ctx.set_line_width(1.2)
        for i in range(-6, 7):
            ctx.move_to(i * 10, -h / 2 + 3)
            ctx.line_to(i * 10 + 8, h / 2 - 3)
        ctx.stroke()
    if dmg > 0:   # ヒビ
        rng = np.random.default_rng(gid)
        ctx.set_source_rgba(1, 1, 1, 0.85)
        ctx.set_line_width(1.6)
        for _ in range(1 + int(dmg * 6)):
            px, py = rng.uniform(-w * 0.3, w * 0.3), rng.uniform(-h * 0.3, h * 0.3)
            ctx.move_to(px, py)
            for _ in range(3):
                px = max(-w / 2, min(w / 2, px + rng.uniform(-w * 0.25, w * 0.25)))
                py = max(-h / 2, min(h / 2, py + rng.uniform(-h * 0.4, h * 0.4)))
                ctx.line_to(px, py)
        ctx.stroke()
    if flash > 0:
        ctx.new_path()
        ctx.move_to(*poly[0])
        for p in poly[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.set_source_rgba(1, 1, 1, 0.6 * flash)
        ctx.fill()
    ctx.restore()


def draw_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    """ボール。回転が見えるよう模様をつけ、強いボールほど派手なエフェクト。"""
    col = BALLS[kind][5]
    ctx.save()
    ctx.translate(x, y)
    if kind >= 3:   # 光る(火・雷・隕石)
        glow_c = {3: (1, 0.5, 0.1), 4: (0.4, 0.7, 1), 5: (1, 0.35, 0.1)}[kind]
        g = cairo.RadialGradient(0, 0, r * 0.5, 0, 0, r * 3.2)
        g.add_color_stop_rgba(0, *glow_c, 0.55 * alpha)
        g.add_color_stop_rgba(1, *glow_c, 0)
        ctx.arc(0, 0, r * 3.2, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
    ctx.rotate(ang)
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.clip()
    if kind == 0:     # スーパーボール:ピンクにうず巻きの線
        ctx.set_source_rgba(*col, alpha)
        ctx.paint()
        for j, c in enumerate(((1, 0.9, 0.2), (0.3, 0.8, 1), (1, 1, 1))):
            ctx.new_path()
            ctx.arc(0, 0, r * (0.35 + 0.25 * j), j * 1.2, j * 1.2 + 2.6)
            ctx.set_source_rgba(*c, 0.9 * alpha)
            ctx.set_line_width(r * 0.16)
            ctx.stroke()
    elif kind == 1:   # 木の玉:年輪
        ctx.set_source_rgba(*col, alpha)
        ctx.paint()
        for j in range(1, 6):
            ctx.new_path()
            ctx.arc(r * 0.25, r * 0.1, r * 0.2 * j, 0, 2 * math.pi)
            ctx.set_source_rgba(0.45, 0.28, 0.12, 0.6 * alpha)
            ctx.set_line_width(2.5)
            ctx.stroke()
    elif kind == 2:   # 鉄球:金属のグラデ+回るすじ
        g = cairo.RadialGradient(-r * 0.35, -r * 0.35, r * 0.1, 0, 0, r)
        g.add_color_stop_rgba(0, 1, 1, 1, alpha)
        g.add_color_stop_rgba(0.4, 0.72, 0.74, 0.78, alpha)
        g.add_color_stop_rgba(1, 0.2, 0.21, 0.24, alpha)
        ctx.set_source(g)
        ctx.paint()
        for j in range(3):
            ctx.new_path()
            ctx.move_to(-r, -r * 0.6 + j * r * 0.6)
            ctx.line_to(r, -r * 0.4 + j * r * 0.6)
            ctx.set_source_rgba(1, 1, 1, 0.18 * alpha)
            ctx.set_line_width(3)
            ctx.stroke()
    elif kind == 3:   # 火の玉:明るい芯
        g = cairo.RadialGradient(0, 0, 0, 0, 0, r)
        g.add_color_stop_rgba(0, 1, 1, 0.8, alpha)
        g.add_color_stop_rgba(0.5, 1, 0.6, 0.1, alpha)
        g.add_color_stop_rgba(1, 0.8, 0.15, 0.0, alpha)
        ctx.set_source(g)
        ctx.paint()
    elif kind == 4:   # 雷の玉:青白い芯
        g = cairo.RadialGradient(0, 0, 0, 0, 0, r)
        g.add_color_stop_rgba(0, 1, 1, 1, alpha)
        g.add_color_stop_rgba(0.45, 0.6, 0.85, 1, alpha)
        g.add_color_stop_rgba(1, 0.15, 0.35, 0.9, alpha)
        ctx.set_source(g)
        ctx.paint()
    else:             # 隕石:黒い岩に光る溶岩のひび
        g = cairo.RadialGradient(-r * 0.3, -r * 0.3, r * 0.1, 0, 0, r)
        g.add_color_stop_rgba(0, 0.45, 0.35, 0.3, alpha)
        g.add_color_stop_rgba(1, 0.12, 0.08, 0.07, alpha)
        ctx.set_source(g)
        ctx.paint()
        cr = np.random.default_rng(5)
        ctx.set_line_width(4)
        for _ in range(6):
            px, py = cr.uniform(-r * 0.6, r * 0.6), cr.uniform(-r * 0.6, r * 0.6)
            ctx.move_to(px, py)
            for _ in range(3):
                px += cr.uniform(-r * 0.35, r * 0.35)
                py += cr.uniform(-r * 0.35, r * 0.35)
                ctx.line_to(px, py)
        ctx.set_source_rgba(1, 0.55 + 0.2 * math.sin(t * 9), 0.1, 0.95 * alpha)
        ctx.stroke()
    ctx.restore()
    if kind == 4 and rng is not None:   # 電気のアーク
        ctx.save()
        ctx.translate(x, y)
        for _ in range(4):
            a = rng.uniform(0, 2 * math.pi)
            px, py = r * math.cos(a), r * math.sin(a)
            ctx.move_to(px, py)
            for j in range(4):
                px += math.cos(a) * r * 0.35 + rng.uniform(-14, 14)
                py += math.sin(a) * r * 0.35 + rng.uniform(-14, 14)
                ctx.line_to(px, py)
        ctx.set_source_rgba(0.8, 0.92, 1, 0.9 * alpha)
        ctx.set_line_width(2.5)
        ctx.stroke()
        ctx.restore()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    glass = res["glass"]
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"glass_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"glass_{seed}.wav")
    final = os.path.join(OUT_DIR, f"glass_{seed}.mp4")
    bg = background()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "18", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    rng = np.random.default_rng(seed + 3)
    dmg = {}
    hit_t = {}
    shards, embers = [], []
    shake = 0.0
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind in ("hit", "break"):
                gid, bk, x, y = data
                g = glass[gid]
                dmg[gid] = min(1.0, dmg.get(gid, 0) + BALLS[bk][1] / g["hp0"])
                hit_t[gid] = et
                if kind == "break":   # 破片が飛び散る
                    n = 10 + 4 * g["kind"]
                    for _ in range(n):
                        a = rng.uniform(0, 2 * math.pi)
                        sp = rng.uniform(150, 650)
                        sz = rng.uniform(6, 18) * (1 + 0.3 * g["kind"])
                        shards.append([x, y, math.cos(a) * sp, math.sin(a) * sp - 200, rng.uniform(0, 6),
                                       rng.uniform(-12, 12), sz, et, GLASS_TINT[g["kind"]]])
                    shake = max(shake, 4 + 3 * g["kind"] + BALLS[bk][1] * 0.6)
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        shake *= 0.85
        dx, dy = (math.sin(t * 57) * shake, math.cos(t * 49) * shake) if shake > 0.5 else (0, 0)
        ctx.save()
        ctx.translate(dx, dy)
        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        for gid, x, y, ang in fr["glass"]:
            ht = hit_t.get(gid)
            fl = max(0.0, 1 - (t - ht) / 0.15) if ht is not None and t >= ht else 0.0
            draw_glass(ctx, glass[gid], x, y, ang, dmg.get(gid, 0), fl, gid)
        # 火の粉・炎の尾
        for bk, x, y, ang, vx, vy, age in fr["balls"]:
            if bk in (3, 5):
                for _ in range(3 if bk == 3 else 6):
                    embers.append([x + rng.uniform(-10, 10), y + rng.uniform(-10, 10), -vx * 0.15 + rng.uniform(-60, 60),
                                   -vy * 0.15 - rng.uniform(40, 140), t, rng.uniform(8, 20) * (1.6 if bk == 5 else 1)])
        keep = []
        for e in embers:
            age = t - e[4]
            if age < 0.45:
                k = 1 - age / 0.45
                ex, ey = e[0] + e[2] * age, e[1] + e[3] * age
                gg = cairo.RadialGradient(ex, ey, 0, ex, ey, e[5] * k)
                gg.add_color_stop_rgba(0, 1, 0.85, 0.4, 0.9 * k)
                gg.add_color_stop_rgba(1, 1, 0.3, 0.0, 0)
                ctx.set_source(gg)
                ctx.arc(ex, ey, e[5] * k, 0, 2 * math.pi)
                ctx.fill()
                keep.append(e)
        embers = keep
        for bk, x, y, ang, vx, vy, age in fr["balls"]:
            r_ = BALLS[bk][2]
            life = BALLS[bk][4]
            a = min(1.0, age / 0.2) * min(1.0, max(0.0, (life - age) / 0.4))
            draw_ball(ctx, bk, x, y, ang, r_ * (0.6 + 0.4 * min(1.0, age / 0.2)), t, a, rng)
        draw_drum(ctx, fr["drum"])
        # ガラスの破片
        keep = []
        for sh in shards:
            age = t - sh[7]
            if age < 1.0:
                k = 1 - age
                sx = sh[0] + sh[2] * age
                sy = sh[1] + sh[3] * age + 0.5 * GRAVITY * age * age
                ctx.save()
                ctx.translate(sx, sy)
                ctx.rotate(sh[4] + sh[5] * age)
                sz = sh[6]
                ctx.move_to(-sz / 2, -sz / 3)
                ctx.line_to(sz / 2, -sz / 5)
                ctx.line_to(0, sz / 2)
                ctx.close_path()
                ctx.set_source_rgba(*sh[8], 0.55 * k)
                ctx.fill_preserve()
                ctx.set_source_rgba(1, 1, 1, 0.9 * k)
                ctx.set_line_width(1.2)
                ctx.stroke()
                ctx.restore()
                keep.append(sh)
        shards = keep
        ctx.restore()

        # 文字
        text(ctx, "6つのボールで", W / 2, 130, 66, sw=8)
        text(ctx, "ガラスを全部割れる？", W / 2, 236, 88, rgb=GOLD, sw=10)
        left = res["n_glass"] - fr["broken"]
        text(ctx, f"のこりガラス {left}", W / 2, 320, 48, rgb=(0.92, 0.95, 1) if left > 3 else (1, 0.45, 0.4), sw=6)
        # ボールの順番(今のボールは明るく、使ったボールはうすく)
        bi = fr["ball_i"]
        for k in range(len(BALLS)):
            x = W / 2 + (k - (len(BALLS) - 1) / 2) * 160
            y = 450
            a = 1.0 if k == bi else (0.3 if k < bi else 0.65)
            draw_ball(ctx, k, x, y, 0.0, 34, t, a, None)
            text(ctx, BALLS[k][0], x, y + 72, 26, rgb=(1, 1, 1), sw=0, alpha=a)
            if k == bi and fr["balls"]:   # のこり時間のバー
                age = fr["balls"][0][6]
                p = max(0.0, 1 - age / BALLS[k][4])
                ctx.rectangle(x - 55, y + 88, 110, 7)
                ctx.set_source_rgba(1, 1, 1, 0.2)
                ctx.fill()
                ctx.rectangle(x - 55, y + 88, 110 * p, 7)
                ctx.set_source_rgba(1, 0.85, 0.3, 0.95)
                ctx.fill()
        if over and fail:
            after = t - end_t - SCARE_DUR
            k = min(1.0, after / 0.25)
            text(ctx, "割りきれなかった…", W / 2, 900, 96 * (1.12 - 0.12 * k), rgb=(1, 0.3, 0.3), sw=14)
            text(ctx, f"あと{left}枚だったのに…", W / 2, 1010, 62, sw=10)
        elif over:
            age = t - end_t
            if age < 0.25:
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.7 * (1 - age / 0.25))
                ctx.fill()
            k = min(1.0, age / 0.4)
            text(ctx, "全部割った！", W / 2, 900, 120 * (1.2 - 0.2 * k), rgb=GOLD, sw=14, alpha=k)
            text(ctx, f"{BALLS[-1][0]}が最後の1枚を割った", W / 2, 1010, 50, sw=8, alpha=k)
        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
    ff.stdin.close()
    ff.wait()
    duration = len(frames) / FPS
    synth_audio(res, duration, wav)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(silent)
    os.remove(wav)
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['broken']}/{res['n_glass']}枚 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音(仮:合成音。本物のガラスの音は Higgs Field で作って差し替える)
def _t(d):
    return np.arange(int(d * SR)) / SR


def glass_break(seed, big):
    """ガラスが割れる「パリーン」:高い音のきらめき+ノイズのくだける音。"""
    rng = np.random.default_rng(seed)
    t = _t(0.9)
    out = rng.normal(0, 1, len(t)) * np.exp(-t * (9 - big * 2))
    out = out - np.convolve(out, np.ones(5) / 5, mode="same")   # 高い成分だけ
    for _ in range(10 + 4 * big):
        f = rng.uniform(2500, 7500)
        t0 = rng.uniform(0, 0.25)
        i0 = int(t0 * SR)
        tt = t[: len(t) - i0]
        out[i0:] += 0.35 * np.sin(2 * np.pi * f * tt) * np.exp(-tt * rng.uniform(15, 40))
    return out / (np.max(np.abs(out)) + 1e-9)


def ball_hit(kind, seed):
    """ボールが当たった音:ボールの種類で変える。"""
    rng = np.random.default_rng(seed)
    t = _t(0.35)
    if kind == 0:   # ボヨン
        f = 300 + 500 * np.exp(-t * 20)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12) * 0.6
    if kind == 1:   # コン(木)
        return (np.sin(2 * np.pi * 420 * t) + 0.5 * rng.normal(0, 1, len(t)) * np.exp(-t * 60)) * np.exp(-t * 30) * 0.6
    if kind == 2:   # カーン(金属)
        return sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((880, 8), (1350, 10), (2100, 14))) * 0.3
    if kind == 3:   # ボワッ(火)
        n = rng.normal(0, 1, len(t))
        return np.convolve(n, np.ones(30) / 30, mode="same") * np.exp(-t * 7) * 1.5
    if kind == 4:   # バチッ(電気)
        return np.sign(np.sin(2 * np.pi * 90 * t)) * rng.normal(0, 1, len(t)) * np.exp(-t * 18) * 0.5
    sub = np.sin(2 * np.pi * (60 - 20 * t) * t) * np.exp(-t * 6)   # ドゴォン(隕石)
    return (sub + 0.6 * np.convolve(rng.normal(0, 1, len(t)), np.ones(20) / 20, mode="same") * np.exp(-t * 8)) * 0.9


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    glass = res["glass"]
    n = int((duration + 3) * SR)
    out = np.zeros(n)

    def add(sig, t0, g=1.0):
        i = int(t0 * SR)
        j = min(n, i + len(sig))
        if 0 <= i < n:
            out[i:j] += g * sig[: j - i]

    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.05:
            continue
        if kind == "hit":
            gid, bk, _, _ = data
            add(ball_hit(bk, int(t * 1000)), t, 0.5 + 0.08 * bk)
            add(glass_break(int(t * 777), 0)[: int(0.15 * SR)], t, 0.25)   # ピキッ
        elif kind == "break":
            gid, bk, _, _ = data
            add(ball_hit(bk, int(t * 1000)), t, 0.5 + 0.08 * bk)
            add(glass_break(int(t * 999), glass[gid]["kind"]), t, 0.6 + 0.12 * glass[gid]["kind"])
        elif kind == "ball":   # ボールが入ってくる「シュッ」
            tt = _t(0.3)
            add(np.random.default_rng(int(t * 100)).normal(0, 1, len(tt)) * np.sin(np.pi * tt / 0.3) * 0.25, t)
    extra = np.zeros(n)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:   # 成功のジャーン
        tt = _t(2.5)
        chord = sum(np.sin(2 * np.pi * midi_hz(m_) * tt) for m_ in (60, 64, 67, 72, 76)) * np.exp(-tt * 1.2) * 0.25
        i0 = int((end_t + 0.1) * SR)
        m = min(len(chord), n - i0)
        extra[i0:i0 + m] += chord[:m]
    wet = out.copy()
    for d, g in ((0.05, 0.25), (0.09, 0.15)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.4
    body = wet[: int((end_t or duration) * SR)]
    rms = np.sqrt(np.mean(body ** 2)) if len(body) else 0
    if rms > 0:   # 通常部分の平均音量を約 -18dB にそろえる
        wet *= min(2.0, 10 ** (-18.0 / 20) / rms)
    wet = np.clip(wet + extra[: len(wet)], -0.98, 0.98)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("-n", type=int, default=200)
    ap.add_argument("--want", choices=["fail", "success"], default="fail")
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
