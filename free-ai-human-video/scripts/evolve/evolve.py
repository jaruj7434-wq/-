"""「60秒でゾウまで進化できる?」同じ動物どうしがぶつかると合体して次の動物に進化する物理ショートを生成する。

ひよこ → ネズミ → ウサギ → ネコ → イヌ → ブタ → パンダ → ライオン → ゾウ(ゴール)
- 上を左右に動くドロッパーから、小さい動物がびんの中に落ちてくる。
- 同じ動物どうしが触れると合体して、2つの真ん中に次の動物が生まれる(大きくなって周りを押しのける)。
- 展開:15秒でドロップ加速、30秒でラッキードロップ(ウサギが続けて落ちる)、40秒でびんがシェイク、
  48秒でマグネットタイム(同じ動物どうしが引き合う)。
60秒以内にゾウが生まれれば成功(天使)、生まれなければ失敗(幽霊)。

使い方:
    python evolve.py search [--want fail|success]
    python evolve.py render --seed N
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ball_escape"))
from ball_escape import midi_hz, noise, text, tone  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from angels import DURATION as ANGEL_DUR, AngelShow, holy_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 3
SR = 48000
GRAVITY = 1500.0
TIME_LIMIT = 60.0
OUTRO = 3.0

NAMES = ["ひよこ", "ネズミ", "ウサギ", "ネコ", "イヌ", "ブタ", "パンダ", "ライオン", "ゾウ"]
GOAL_LV = len(NAMES) - 1
R0, R_RATIO = 22.0, 1.32
RADII = [R0 * R_RATIO ** k for k in range(len(NAMES))]

# びん(角の丸い広口びん)
JAR_X0, JAR_X1, JAR_TOP, JAR_BOTTOM, JAR_CORNER = 90, 990, 820, 1470, 130
DROP_Y = 760
DROPPER_SPEED = 0.55          # ドロッパーの往復の速さ(1秒あたりの位相)
DROP_SLOW, DROP_FAST = 0.42, 0.18
FAST_AT, LUCKY_AT, SHAKE_AT, MAGNET_AT = 15.0, 30.0, 40.0, 48.0
MAGNET_ACC = 2000.0          # マグネットタイムに同じ動物どうしが引き合う強さ(成功率およそ半々になる値)
LUCKY_N = 6
SHAKE_DUR, SHAKE_AMP, SHAKE_HZ = 2.0, 26.0, 3.0
P_LV2 = 0.45                  # ふだん落ちてくる動物のうち、ネズミの割合(残りはひよこ)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


def jar_points():
    """びんの輪郭(左上 → 左下の丸い角 → 底 → 右下の丸い角 → 右上)。"""
    pts = [(JAR_X0, JAR_TOP)]
    c = JAR_CORNER
    for k in range(9):   # 左下の角
        a = math.pi - k * (math.pi / 2) / 8
        pts.append((JAR_X0 + c + c * math.cos(a), JAR_BOTTOM - c + c * math.sin(a) * -1 * -1))
    for k in range(9):   # 右下の角
        a = math.pi / 2 - k * (math.pi / 2) / 8
        pts.append((JAR_X1 - c + c * math.cos(a), JAR_BOTTOM - c + c * math.sin(a)))
    pts.append((JAR_X1, JAR_TOP))
    # 左下の角は下向きの円弧になるよう並べ直す
    left = [(JAR_X0 + c - c * math.cos(math.radians(d)), JAR_BOTTOM - c + c * math.sin(math.radians(d)))
            for d in range(0, 91, 11)]
    right = [(JAR_X1 - c + c * math.cos(math.radians(d)), JAR_BOTTOM - c + c * math.sin(math.radians(d)))
             for d in range(90, -1, -11)]
    return [(JAR_X0, JAR_TOP)] + left + right + [(JAR_X1, JAR_TOP)]


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 20
        self.space = sp
        # びんはキネマティック(シェイクで動かせる)
        self.jar = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        sp.add(self.jar)
        pts = jar_points()
        for a, b in zip(pts, pts[1:]):
            s = pymunk.Segment(self.jar, a, b, 8)
            s.friction, s.elasticity = 0.6, 0.1
            sp.add(s)
        self.pairs = []
        sp.on_collision(1, 1, pre_solve=self._touch)
        self.animals = []     # {"body","shape","lv","id","born"}
        self.next_id = 0
        self.events = []
        self.t = 0.0
        self.next_drop = 0.4
        self.drop_x = W / 2
        self.drop_phase = self.rng.uniform(0, 6.28)
        self.lucky_left = 0
        self.fast = self.lucky = self.shaken = self.magnet = False
        self.best = 0
        self.result, self.result_t = None, None

    def _touch(self, arb, space, data):
        a, b = arb.shapes
        if a.lv == b.lv and a.lv < GOAL_LV:
            self.pairs.append((a, b))

    def add(self, lv, x, y, vx=0.0, vy=0.0):
        r = RADII[lv]
        m = r * r / 400
        body = pymunk.Body(m, pymunk.moment_for_circle(m, 0, r))
        body.position = (x, y)
        body.velocity = (vx, vy)
        sh = pymunk.Circle(body, r)
        sh.friction, sh.elasticity = 0.5, 0.15
        sh.collision_type = 1
        sh.lv = lv
        sh.aid = self.next_id
        self.space.add(body, sh)
        self.animals.append({"body": body, "shape": sh, "lv": lv, "id": self.next_id, "born": self.t})
        self.next_id += 1
        self.best = max(self.best, lv)

    def step(self, dt):
        self.t += dt
        t = self.t
        # 展開
        if not self.fast and t >= FAST_AT:
            self.fast = True
            self.events.append(("fast", t, None))
        if not self.lucky and t >= LUCKY_AT:
            self.lucky = True
            self.lucky_left = LUCKY_N
            self.events.append(("lucky", t, None))
        if not self.shaken and t >= SHAKE_AT:
            self.shaken = True
            self.events.append(("shake", t, None))
        if not self.magnet and t >= MAGNET_AT:
            self.magnet = True
            self.events.append(("magnet", t, None))
        # マグネットタイム:いちばん近い同じ動物の方へ引っぱられる
        if self.magnet:
            for x in self.animals:
                if x["lv"] >= GOAL_LV:
                    continue
                px, py = x["body"].position
                best, bd = None, 1e18
                for y in self.animals:
                    if y is x or y["lv"] != x["lv"]:
                        continue
                    qx, qy = y["body"].position
                    d = (qx - px) ** 2 + (qy - py) ** 2
                    if d < bd:
                        best, bd = (qx, qy), d
                if best:
                    d = math.sqrt(bd) + 1e-6
                    m = x["body"].mass
                    x["body"].apply_force_at_world_point(((best[0] - px) / d * MAGNET_ACC * m,
                                                         (best[1] - py) / d * MAGNET_ACC * m), (px, py))
        # シェイク(びんを左右にゆする)
        if self.shaken and t - SHAKE_AT < SHAKE_DUR:
            w = 2 * math.pi * SHAKE_HZ
            self.jar.velocity = (SHAKE_AMP * w * math.cos(w * (t - SHAKE_AT)), 0)
        else:
            self.jar.velocity = (0, 0)
            if self.jar.position.x != 0:
                self.jar.position = (0, 0)
        # ドロッパー
        self.drop_phase += DROPPER_SPEED * 2 * math.pi * dt
        self.drop_x = W / 2 + 380 * math.sin(self.drop_phase)
        if self.result is None and t >= self.next_drop:
            if self.lucky_left > 0:
                lv = 2
                self.lucky_left -= 1
            else:
                lv = 1 if self.rng.random() < P_LV2 else 0
            self.add(lv, self.drop_x, DROP_Y, self.rng.uniform(-30, 30), 120)
            self.events.append(("drop", t, lv))
            self.next_drop += DROP_FAST if self.fast else DROP_SLOW
        self.pairs = []
        self.space.step(dt)
        # 合体(1体は1回まで)
        used = set()
        for a, b in self.pairs:
            if a.aid in used or b.aid in used or a.lv != b.lv:
                continue
            used.add(a.aid)
            used.add(b.aid)
            pa, pb = a.body.position, b.body.position
            va, vb = a.body.velocity, b.body.velocity
            for sh in (a, b):
                self.space.remove(sh.body, sh)
            self.animals = [x for x in self.animals if x["id"] not in (a.aid, b.aid)]
            lv = a.lv + 1
            mx, my = (pa.x + pb.x) / 2, (pa.y + pb.y) / 2
            self.add(lv, mx, my, (va.x + vb.x) / 2, (va.y + vb.y) / 2 - 150)
            self.events.append(("merge", t, (lv, mx, my)))
            if lv == GOAL_LV and self.result is None:
                self.result, self.result_t = "success", t
                self.events.append(("success", t, None))
        # びんからあふれた動物は消える
        keep = []
        for x in self.animals:
            if x["body"].position.y > H + 100:
                self.space.remove(x["body"], x["shape"])
            else:
                keep.append(x)
        self.animals = keep
        if self.result is None and t >= TIME_LIMIT:
            self.result, self.result_t = "fail", TIME_LIMIT
            self.events.append(("fail", t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            if g.result is None or record:
                g.step(dt)
        if record:
            frames.append({
                "t": g.t, "drop_x": g.drop_x, "jar_x": g.jar.position.x, "best": g.best,
                "animals": [(x["body"].position.x, x["body"].position.y, x["body"].angle, x["lv"], x["born"])
                            for x in g.animals],
            })
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
    counts = [0] * len(NAMES)
    for x in g.animals:
        counts[x["lv"]] += 1
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "best": g.best, "counts": counts}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["best"], r["counts"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "fail":
        # ライオン(lv7)が2体いるのにくっつかずに時間切れ、を優先
        fails = [r for r in rs if r[1] == "fail"]
        fails.sort(key=lambda r: (-r[3], -r[4][GOAL_LV - 1], -r[4][GOAL_LV - 2]))
        for seed, _, _, best, counts in fails[:15]:
            print(f"seed={seed:4d}  最高 {NAMES[best]}  ライオン{counts[7]} パンダ{counts[6]} ブタ{counts[5]}")
    else:
        for seed, _, rt, *_ in sorted(succ, key=lambda r: -r[2])[:15]:
            print(f"seed={seed:4d}  ゾウ誕生 {rt:5.2f}秒")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
BODY = [(1.0, 0.88, 0.3), (0.76, 0.76, 0.84), (0.97, 0.97, 1.0), (1.0, 0.66, 0.3), (0.86, 0.6, 0.38),
        (1.0, 0.7, 0.78), (0.98, 0.98, 0.98), (1.0, 0.8, 0.4), (0.62, 0.72, 0.86)]
PINK = (1.0, 0.6, 0.7)
INK = (0.18, 0.12, 0.12)


def _ell(ctx, x, y, rx, ry, rot=0.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(rx, ry)
    ctx.new_path()
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()


def _fill(ctx, col, outline=None, lw=2.0):
    ctx.set_source_rgb(*col)
    if outline:
        ctx.fill_preserve()
        ctx.set_source_rgb(*outline)
        ctx.set_line_width(lw)
        ctx.stroke()
    else:
        ctx.fill()


def _darker(c, k=0.75):
    return tuple(v * k for v in c)


def draw_animal(ctx, x, y, r, lv):
    """かわいい動物の顔を1つ描く(r は当たり判定の半径)。"""
    c = BODY[lv]
    out = _darker(c, 0.7)
    lw = max(2.0, r * 0.06)
    ctx.save()
    ctx.translate(x, y)
    # --- 顔より後ろに描く部分(耳・たてがみ)
    if lv == 1:   # ネズミの丸い耳
        for sx in (-1, 1):
            _ell(ctx, sx * r * 0.62, -r * 0.62, r * 0.42, r * 0.42)
            _fill(ctx, c, out, lw)
            _ell(ctx, sx * r * 0.62, -r * 0.62, r * 0.25, r * 0.25)
            _fill(ctx, PINK)
    elif lv == 2:   # ウサギの長い耳
        for sx in (-1, 1):
            _ell(ctx, sx * r * 0.32, -r * 1.0, r * 0.2, r * 0.6, sx * 0.15)
            _fill(ctx, c, out, lw)
            _ell(ctx, sx * r * 0.32, -r * 0.98, r * 0.1, r * 0.45, sx * 0.15)
            _fill(ctx, PINK)
    elif lv in (3, 5):   # ネコ・ブタの三角の耳
        for sx in (-1, 1):
            ctx.new_path()
            ctx.move_to(sx * r * 0.25, -r * 0.8)
            ctx.line_to(sx * r * 0.85, -r * 0.95)
            ctx.line_to(sx * r * 0.8, -r * 0.3)
            ctx.close_path()
            _fill(ctx, c, out, lw)
    elif lv == 6:   # パンダの黒い耳
        for sx in (-1, 1):
            _ell(ctx, sx * r * 0.7, -r * 0.72, r * 0.32, r * 0.32)
            _fill(ctx, (0.1, 0.1, 0.12), (0.45, 0.45, 0.5), max(2.0, r * 0.05))
    elif lv == 7:   # ライオンのたてがみ
        for k in range(14):
            a = k * 2 * math.pi / 14
            _ell(ctx, math.cos(a) * r * 0.78, math.sin(a) * r * 0.78, r * 0.3, r * 0.3)
            _fill(ctx, (0.8, 0.45, 0.15))
    elif lv == 8:   # ゾウの大きな耳
        for sx in (-1, 1):
            _ell(ctx, sx * r * 0.82, -r * 0.05, r * 0.5, r * 0.62)
            _fill(ctx, c, out, lw)
            _ell(ctx, sx * r * 0.85, -r * 0.05, r * 0.32, r * 0.45)
            _fill(ctx, (0.95, 0.75, 0.82))
    # --- 顔
    face_r = r * (0.78 if lv == 7 else 1.0)
    _ell(ctx, 0, 0, face_r, face_r * 0.96)
    _fill(ctx, c, out, lw)
    if lv == 6:   # パンダの目のまわり
        for sx in (-1, 1):
            _ell(ctx, sx * r * 0.33, -r * 0.02, r * 0.2, r * 0.27, sx * -0.5)
            _fill(ctx, (0.1, 0.1, 0.12))
    if lv == 4:   # イヌの口元
        _ell(ctx, 0, r * 0.3, r * 0.42, r * 0.32)
        _fill(ctx, (0.97, 0.88, 0.75))
    # 目(パンダは白い目)
    ey = -r * 0.05
    for sx in (-1, 1):
        if lv == 6:
            _ell(ctx, sx * r * 0.3, ey, r * 0.07, r * 0.08)
            _fill(ctx, (1, 1, 1))
        else:
            _ell(ctx, sx * r * 0.3, ey, r * 0.1, r * 0.12)
            _fill(ctx, INK)
            _ell(ctx, sx * r * 0.3 - r * 0.03, ey - r * 0.04, r * 0.035, r * 0.035)
            _fill(ctx, (1, 1, 1))
    # ほっぺ
    if lv != 6:
        for sx in (-1, 1):
            _ell(ctx, sx * r * 0.52, r * 0.2, r * 0.13, r * 0.08)
            ctx.set_source_rgba(1, 0.45, 0.55, 0.45)
            ctx.fill()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_width(lw)
    # 鼻・口など
    if lv == 0:   # ひよこのくちばしと頭の毛
        ctx.new_path()
        ctx.move_to(-r * 0.15, r * 0.14)
        ctx.line_to(0, r * 0.03)
        ctx.line_to(r * 0.15, r * 0.14)
        ctx.line_to(0, r * 0.28)
        ctx.close_path()
        _fill(ctx, (1, 0.55, 0.15))
        for dx in (-0.1, 0.05):
            ctx.new_path()
            ctx.move_to(r * dx, -r * 0.95)
            ctx.curve_to(r * dx, -r * 1.2, r * (dx + 0.15), -r * 1.2, r * (dx + 0.12), -r * 1.05)
            ctx.set_source_rgb(*out)
            ctx.stroke()
    elif lv == 5:   # ブタの鼻
        _ell(ctx, 0, r * 0.22, r * 0.32, r * 0.22)
        _fill(ctx, (1, 0.55, 0.65), out, lw)
        for sx in (-1, 1):
            _ell(ctx, sx * r * 0.11, r * 0.22, r * 0.05, r * 0.08)
            _fill(ctx, (0.6, 0.25, 0.35))
    elif lv == 8:   # ゾウの鼻(くるっと)
        ctx.new_path()
        ctx.move_to(0, r * 0.1)
        ctx.curve_to(0, r * 0.6, -r * 0.05, r * 0.85, r * 0.25, r * 0.8)
        ctx.set_source_rgb(*c)
        ctx.set_line_width(r * 0.24)
        ctx.stroke_preserve()
        ctx.set_source_rgb(*out)
        ctx.set_line_width(lw)
        ctx.stroke()
    else:
        nose = {1: PINK, 2: PINK, 3: (0.95, 0.45, 0.45), 4: INK, 6: INK, 7: (0.5, 0.25, 0.15)}[lv]
        _ell(ctx, 0, r * 0.16, r * 0.08, r * 0.06)
        _fill(ctx, nose)
        ctx.new_path()   # ω の口
        ctx.arc(-r * 0.07, r * 0.24, r * 0.07, 0.1, math.pi - 0.1)
        ctx.arc(r * 0.07, r * 0.24, r * 0.07, 0.1, math.pi - 0.1)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(max(1.5, r * 0.04))
        ctx.stroke()
        if lv in (1, 3):   # ひげ
            ctx.set_line_width(max(1.2, r * 0.025))
            for sx in (-1, 1):
                for dy in (-0.04, 0.08):
                    ctx.new_path()
                    ctx.move_to(sx * r * 0.3, r * (0.2 + dy))
                    ctx.line_to(sx * r * 0.8, r * (0.15 + dy * 2))
                    ctx.stroke()
        if lv == 3:   # ネコのおでこのしま
            ctx.set_source_rgb(*_darker(c, 0.8))
            ctx.set_line_width(max(1.5, r * 0.05))
            for dx in (-0.15, 0, 0.15):
                ctx.new_path()
                ctx.move_to(r * dx, -r * 0.85)
                ctx.line_to(r * dx, -r * 0.6)
                ctx.stroke()
    if lv == 4:   # イヌのたれ耳(顔の上に重ねる)
        for sx in (-1, 1):
            _ell(ctx, sx * r * 0.82, -r * 0.2, r * 0.25, r * 0.5, sx * -0.3)
            _fill(ctx, (0.55, 0.35, 0.2))
    ctx.restore()


def background():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.RadialGradient(W / 2, 1100, 50, W / 2, 1100, 1300)
    g.add_color_stop_rgb(0, 0.10, 0.08, 0.20)
    g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
    ctx.set_source(g)
    ctx.paint()
    return surf


def draw_jar(ctx, dx):
    pts = [(x + dx, y) for x, y in jar_points()]
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.set_source_rgba(0.7, 0.85, 1.0, 0.05)
    ctx.fill()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    n = len(pts) - 1
    for wdt, al in ((26, 0.10), (14, 0.22), (7, 1.0)):   # 虹色のふち
        for i in range(n):
            ctx.new_path()
            ctx.move_to(*pts[i])
            ctx.line_to(*pts[i + 1])
            r_, g_, b_ = colorsys_hue(i / n)
            ctx.set_source_rgba(r_, g_, b_, al)
            ctx.set_line_width(wdt)
            ctx.stroke()


def colorsys_hue(h):
    import colorsys
    return colorsys.hsv_to_rgb(h * 0.8, 0.75, 1.0)


def draw_chart(ctx, best, t, fail_over):
    """上の進化表。たどり着いた動物は明るく、まだの動物は暗く。ゴールのゾウは大きく金の輪。"""
    y = 610
    xs = [70 + k * 117.5 for k in range(len(NAMES))]
    for k in range(len(NAMES) - 1):
        ctx.new_path()
        ctx.move_to(xs[k] + 34, y)
        ctx.line_to(xs[k + 1] - 34, y)
        ctx.set_source_rgba(1, 1, 1, 0.35)
        ctx.set_line_width(3)
        ctx.stroke()
    for k, x in enumerate(xs):
        goal = k == GOAL_LV
        r = 52 if goal else 30
        reached = k <= best
        if goal:
            pulse = 1 + 0.06 * math.sin(t * 5)
            for grow, al in ((14, 0.2), (6, 0.45)):
                ctx.new_path()
                ctx.arc(x, y, (r + grow) * pulse, 0, 2 * math.pi)
                ctx.set_source_rgba(*GOLD, al)
                ctx.fill()
        draw_animal(ctx, x, y, r * 0.78, k)
        if not reached and not goal:   # ゴールのゾウはずっと明るく見せる
            ctx.new_path()
            ctx.arc(x, y, r * 0.95, 0, 2 * math.pi)
            ctx.set_source_rgba(0.02, 0.02, 0.06, 0.6)
            ctx.fill()
        text(ctx, NAMES[k], x, y + r + 30, 24 if not goal else 30,
             rgb=GOLD if goal else ((1, 1, 1) if reached else (0.55, 0.55, 0.6)), sw=5)
    text(ctx, "GOAL", xs[-1], y - 60, 30, rgb=GOLD, sw=6)


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"evolve_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"evolve_{seed}.wav")
    final = os.path.join(OUT_DIR, f"evolve_{seed}.mp4")
    rng = np.random.default_rng(seed + 999)
    bg = background()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    angels = AngelShow(W, H, seed) if result == "success" else None
    particles, rings, popups, banners = [], [], [], []
    magnet_on = False
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        dt = 1 / FPS
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "merge":
                lv, mx, my = data
                col = BODY[lv]
                rings.append([et, mx, my, RADII[lv], col])
                for _ in range(8 + 4 * lv):
                    a = rng.uniform(0, 2 * math.pi)
                    sp = rng.uniform(150, 450 + 60 * lv)
                    particles.append([mx, my, math.cos(a) * sp, math.sin(a) * sp, 0, rng.uniform(0.3, 0.7), col])
                if lv >= 5:
                    popups.append([et, mx, my - RADII[lv] - 20, f"{NAMES[lv]}誕生！", GOLD if lv >= 7 else (1, 1, 1)])
            elif kind == "fast":
                banners.append([et, "ドロップ加速！", (0.5, 0.95, 1.0)])
            elif kind == "lucky":
                banners.append([et, "ラッキードロップ！", GOLD])
            elif kind == "shake":
                banners.append([et, "シェイク！", (1, 0.6, 0.3)])
            elif kind == "magnet":
                banners.append([et, "マグネットタイム！", (1, 0.4, 0.8)])
                magnet_on = True
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0

        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        draw_jar(ctx, fr["jar_x"])
        # マグネットタイム:同じ動物どうしを点線で結ぶ
        if magnet_on and not over:
            ctx.set_dash([10, 10], -t * 60)
            byl = {}
            for ax, ay, _, lv, _ in fr["animals"]:
                byl.setdefault(lv, []).append((ax, ay))
            for lv, ps in byl.items():
                if lv >= GOAL_LV or len(ps) < 2:
                    continue
                for i, (ax, ay) in enumerate(ps):
                    j = min((k for k in range(len(ps)) if k != i),
                            key=lambda k: (ps[k][0] - ax) ** 2 + (ps[k][1] - ay) ** 2)
                    if j > i or min((k for k in range(len(ps)) if k != j),
                                    key=lambda k: (ps[k][0] - ps[j][0]) ** 2 + (ps[k][1] - ps[j][1]) ** 2) != i:
                        ctx.new_path()
                        ctx.move_to(ax, ay)
                        ctx.line_to(*ps[j])
                        ctx.set_source_rgba(1, 0.45, 0.85, 0.35 + 0.1 * lv / GOAL_LV)
                        ctx.set_line_width(2 + lv * 0.6)
                        ctx.stroke()
            ctx.set_dash([])
        # 動物(生まれた瞬間はポンと大きくなる)
        for ax, ay, _, lv, born in sorted(fr["animals"], key=lambda a: a[3]):
            pop = min(1.0, (t - born) / 0.12)
            draw_animal(ctx, ax, ay, RADII[lv] * (0.5 + 0.5 * pop) * (1 + 0.15 * max(0, 1 - (t - born) / 0.25)), lv)
        # ドロッパー
        if not over:
            dx = fr["drop_x"]
            ctx.new_path()
            ctx.move_to(dx - 30, DROP_Y - 70)
            ctx.line_to(dx + 30, DROP_Y - 70)
            ctx.line_to(dx, DROP_Y - 34)
            ctx.close_path()
            ctx.set_source_rgb(0.5, 0.95, 1.0)
            ctx.fill()
        for rg in rings:
            age = t - rg[0]
            if 0 <= age < 0.35:
                k = age / 0.35
                ctx.new_path()
                ctx.arc(rg[1], rg[2], rg[3] * (1 + 0.8 * k), 0, 2 * math.pi)
                ctx.set_source_rgba(*rg[4], 0.8 * (1 - k))
                ctx.set_line_width(8 * (1 - k) + 2)
                ctx.stroke()
        alive = []
        for p in particles:
            p[4] += dt
            if p[4] >= p[5]:
                continue
            p[3] += 900 * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            ctx.new_path()
            ctx.arc(p[0], p[1], 5, 0, 2 * math.pi)
            ctx.set_source_rgba(*p[6], 1 - p[4] / p[5])
            ctx.fill()
            alive.append(p)
        particles = alive
        for pu in popups:
            age = t - pu[0]
            if 0 <= age < 1.2 and not over:
                text(ctx, pu[3], min(max(pu[1], 200), W - 200), pu[2] - 60 * age, 56,
                     rgb=pu[4], sw=12, alpha=min(1, 2 * (1.2 - age)))
        for bn in banners:
            age = t - bn[0]
            if 0 <= age < 1.4 and not over:
                k = min(1, age / 0.15)
                text(ctx, bn[1], W / 2, 1060, 100 * (1.4 - 0.4 * k), rgb=bn[2], sw=18,
                     alpha=min(1, 3 * (1.4 - age)))
        if angels is not None and over:
            angels.draw(ctx, t - end_t)

        # 文字
        shown_t = min(t, end_t if end_t is not None else TIME_LIMIT)
        remain = TIME_LIMIT - shown_t
        text(ctx, "60秒で", W / 2, 190, 80, sw=14)
        text(ctx, "ゾウまで進化できる？", W / 2, 305, 96, rgb=GOLD, sw=18)
        text(ctx, "Can they evolve into an elephant in 60s?", W / 2, 368, 36, rgb=(0.85, 0.85, 0.9), sw=8)
        danger = remain <= 5 and not over
        pulse = 1 + (0.12 * max(0, 1 - (shown_t % 1) / 0.25) if danger else 0)
        tcol = (1, 0.25, 0.25) if (danger or (fail and over)) else ((0.3, 1, 0.5) if over else (1, 1, 1))
        text(ctx, f"{remain:05.2f}", W / 2, 470, 80 * pulse, rgb=tcol, sw=12)
        draw_chart(ctx, fr["best"], t, fail and over)
        if not over:
            text(ctx, "※失敗すると…アレが出ます", W / 2, 1580, 50, rgb=(1, 0.35, 0.35), sw=10)
        elif fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 1060, 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            n_top = sum(1 for a_ in fr["animals"] if a_[3] == fr["best"])
            msg = f"{NAMES[fr['best']]}まで…"
            if fr["best"] == GOAL_LV - 1 and n_top >= 2:
                msg = "あと1回の合体でゾウだった…"
            text(ctx, msg, W / 2, 1180, 66, sw=12)
        else:
            k = min(1.0, (t - end_t) / 0.25)
            text(ctx, "ゾウ誕生！", W / 2, 1060, 150 * (1.6 - 0.6 * k), rgb=GOLD, sw=20)
            text(ctx, f"{end_t:.2f}秒", W / 2, 1180, 80, sw=12)

        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
    ff.stdin.close()
    ff.wait()
    duration = len(frames) / FPS
    synth_audio(events, end_t, fail, duration, wav)
    # 叫び声の大きさを残すため、音量の自動調整(loudnorm)はかけない
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(silent)
    os.remove(wav)
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} 最高 {NAMES[res['best']]} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
MERGE_NOTES = [72, 74, 76, 79, 81, 84, 86, 88, 91]   # 進化するほど高い音
MIX_GAIN = 1.0   # 通常部分の音量(約 -18dB になるよう調整)
HOLY_GAIN = 0.85


def synth_audio(events, end_t, fail, duration, path):
    rng = np.random.default_rng(0)
    out = np.zeros(int((duration + 3) * SR))

    def add(sig, t0):
        i = int(t0 * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    last_drop = -1.0
    for kind, t, data in events:
        if kind == "drop":
            if t - last_drop > 0.08:
                add(tone(300, 0.08, 0.10, 30), t)
                last_drop = t
        elif kind == "merge":
            lv = data[0]
            m = MERGE_NOTES[min(lv, len(MERGE_NOTES) - 1)]
            add(tone(midi_hz(m), 0.35, 0.28, 7) + tone(midi_hz(m + 7), 0.35, 0.12, 9), t)
            add(noise(0.05, 0.12, 60, rng, smooth=3), t)
            if lv >= 5:   # 大きい動物はジャーン
                for k, iv in enumerate((0, 4, 7, 12)):
                    add(tone(midi_hz(m - 12 + iv), 0.9, 0.18, 2.5), t + k * 0.04)
        elif kind in ("fast", "lucky", "shake", "magnet"):
            notes = {"fast": (72, 76, 79, 84), "lucky": (79, 83, 86, 91), "shake": (60, 64, 60, 64),
                     "magnet": (67, 71, 74, 79)}[kind]
            for k, m in enumerate(notes):
                add(tone(midi_hz(m), 0.3, 0.25, 6), t + k * 0.07)
    for s_ in range(55, 60):
        if end_t is None or s_ < end_t:
            add(noise(0.06, 0.5, 60, rng) + tone(1800, 0.06, 0.2, 40), s_)
    extra = np.zeros_like(out)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        extra[i0:i0 + len(sig)] += sig[: len(extra) - i0]
        sad_t = end_t + SCARE_DUR + 0.1
        for k, m in enumerate((64, 63, 62)):
            add(tone(midi_hz(m), 0.45, 0.35, 3) + tone(midi_hz(m - 12), 0.45, 0.25, 3), sad_t + k * 0.42)
        add(tone(midi_hz(61), 1.4, 0.35, 1.5) + tone(midi_hz(49), 1.4, 0.25, 1.5), sad_t + 1.26)
    elif end_t is not None:
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(end_t * SR)
        extra[i0:i0 + len(sig)] += HOLY_GAIN * sig[: len(extra) - i0]
    wet = out.copy()
    for d, g in ((0.043, 0.3), (0.071, 0.24), (0.113, 0.17)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    # 通常部分は軽く圧縮して聞こえやすくし、叫び声との差は約10dBに抑える
    wet = np.tanh(2.5 * wet / max(1e-9, np.max(np.abs(wet)))) / np.tanh(2.5) * MIX_GAIN
    wet = np.clip(wet + (0.95 if fail else 1.0) * extra[: len(wet)], -0.98, 0.98)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--want", choices=["fail", "success"], default="fail")
    ap.add_argument("-n", type=int, default=200)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
