"""「初代クラウンを合体させて最新クラウンにできる?」首の長い丸フラスコに初代クラウンが次々落ちてきて、
同じ世代どうしが触れると次の世代に進化する物理ショート(歴代クラウン版の合体進化)。

- 写真(Higgs Field の Seedream 5.0 Pro で生成・背景透明)8段階:
  初代(1955)→ 3代目「白いクラウン」(1967)→ 4代目「クジラ」(1971)→ 7代目(1983)→ 9代目(1991)
  → 12代目「ゼロクラウン」(2003)→ 14代目(2012)→ 16代目「クロスオーバー」(2022・ゴール)
  ※AIが描いた「その世代らしい」車。メーカーの公式の画像ではない。
- 首から落ちてくるのは必ず初代で、落ちてくる間隔がだんだん短くなる(テンポアップ)。新しい世代ほど車が大きい。
- 写真の輪郭(凸包)を当たり判定にして、重力・反発・摩擦・回転のまま自然に落ちる(ねらい・補正なし)。止まったものは眠らせる。
- 進化したときは、その世代らしいエンジン音(Higgs Field の Seedance 2.0 Mini で作った音つき動画から切り出し)と、
  段階が上がるほど豪華になる効果音。
- 最新のクラウンができれば成功(天使)、首までつまってあふれるか時間切れなら失敗(幽霊)。

使い方:
    python crown_evolve.py search [--want fail|success] [-n 200]
    python crown_evolve.py render --seed N
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
from ball_escape import FONT, midi_hz, text  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
ANGEL_DUR = 6.0   # 成功したときの発表演出の長さ(天使の演出は使わない)

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
GRAVITY = float(os.environ.get("GRAVITY", 1100.0))   # ゆっくりめに落ちる

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
IMG_DIR = os.path.join(ROOT, "assets", "source", "crown")
SND_DIR = os.path.join(IMG_DIR, "sounds")
OUT_DIR = os.path.join(ROOT, "assets", "output")

NAMES = ["初代", "3代目", "4代目", "7代目", "9代目", "12代目", "14代目", "16代目"]
SHORT = ["1955", "1967", "1971", "1983", "1991", "2003", "2012", "2022"]   # 進化表に出す年
NICK = ["観音開き", "白いクラウン", "クジラ", "いつかはクラウン", "", "ゼロクラウン", "", "クロスオーバー"]   # 世代の呼び名
GOAL = len(NAMES) - 1
WIDTHS = [112, 140, 172, 212, 260, 318, 392, 500]   # 段階ごとの写真の横幅(px)。新しい世代ほど大きい(最後は発表演出でさらに巨大に)

# 首のついた丸いフラスコ(参考動画と同じ形)
FL_CX, FL_CY, FL_R = 540.0, 1180.0, 430.0
NECK_HW = 66.0                         # 首の半分の幅
NECK_TOP = 600.0                       # 首の上端
NECK_Y = FL_CY - math.sqrt(FL_R ** 2 - NECK_HW ** 2)   # 首と丸い部分のつなぎ目
OVER_Y = NECK_Y + 10                   # 止まったものの上端がこれより上(首の中)まで積み上がったら、あふれ
OVER_WAIT = 1.5
DROP_Y = NECK_TOP - 40
DROP_START, DROP_END, DROP_RAMP = float(os.environ.get("DROP_START", 0.7)), float(os.environ.get("DROP_END", 0.2)), float(os.environ.get("DROP_RAMP", 25.0))   # 落ちてくる間隔(秒):最初 → 最後、何秒かけて速くなるか
V_MERGE = 0.0                          # 合体に必要なぶつかる速さ(px/秒)。0 = 同じ段階どうしが触れたら合体
COW_E, COW_F = 0.5, 0.5                # 反発係数・摩擦(落ちたら跳ねる)
BOWL_E, BOWL_F = 0.6, 0.5              # フラスコの反発係数・摩擦
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 43.0))
OUTRO = 2.5


# ---------------------------------------------------------------- 写真と当たり判定
def convex_hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def simplify(poly, min_d=8.0, max_n=24):
    out = []
    for p in poly:
        if not out or math.dist(p, out[-1]) >= min_d:
            out.append(p)
    while len(out) > max_n:
        out = out[::2]
    return out


class Sprite:
    """背景透明の写真1枚。切り抜き済みの画像と、物理用の凸包(重心が原点)を持つ。"""

    def __init__(self, stage):
        path = os.path.join(IMG_DIR, f"stage{stage + 1}.png")
        if not os.path.exists(path):
            raise SystemExit(f"写真がありません: {path}")
        img = cairo.ImageSurface.create_from_png(path)
        w, h = img.get_width(), img.get_height()
        a = np.ndarray((h, w, 4), np.uint8, img.get_data(), strides=(img.get_stride(), 4, 1))[:, :, 3]
        ys, xs = np.nonzero(a > 100)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        self.scale = WIDTHS[stage] / (x1 - x0)
        # 輪郭の点(4px おきに間引き)→ 凸包
        sub = a[y0:y1:4, x0:x1:4] > 100
        yy, xx = np.nonzero(sub)
        pts = [(float(x * 4), float(y * 4)) for x, y in zip(xx, yy)]
        hull = convex_hull(pts)
        hull = [(x * self.scale, y * self.scale) for x, y in hull]
        cx = sum(p[0] for p in hull) / len(hull)
        cy = sum(p[1] for p in hull) / len(hull)
        self.poly = simplify([(x - cx, y - cy) for x, y in hull])
        self.offset = (cx, cy)          # 切り抜いた画像の左上から重心まで(縮小後)
        self.img, self.crop = img, (x0, y0, x1 - x0, y1 - y0)
        self.w, self.h = (x1 - x0) * self.scale, (y1 - y0) * self.scale

    def draw(self, ctx, x, y, ang, k=1.0, alpha=1.0):
        x0, y0, cw, ch = self.crop
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(ang)
        ctx.scale(k, k)
        ctx.translate(-self.offset[0], -self.offset[1])
        ctx.scale(self.scale, self.scale)
        ctx.rectangle(0, 0, cw, ch)
        ctx.clip()
        ctx.set_source_surface(self.img, -x0, -y0)
        ctx.get_source().set_filter(cairo.FILTER_GOOD)
        ctx.paint_with_alpha(alpha)
        ctx.restore()


_POLYS = None


def polys():
    global _POLYS
    if _POLYS is None:
        _POLYS = [Sprite(k).poly for k in range(len(NAMES))]
    return _POLYS


def bowl_points():
    """フラスコの輪郭:左の首の上 → 首のつなぎ目 → 丸い部分を左・下・右とまわる → 右のつなぎ目 → 右の首の上。"""
    a0 = math.atan2(NECK_Y - FL_CY, -NECK_HW) % (2 * math.pi)   # 左のつなぎ目(約260°)
    a1 = math.atan2(NECK_Y - FL_CY, NECK_HW)                    # 右のつなぎ目(約-80°)
    pts = [(FL_CX - NECK_HW, NECK_TOP)]
    n = 72
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        pts.append((FL_CX + FL_R * math.cos(a), FL_CY + FL_R * math.sin(a)))
    pts.append((FL_CX + NECK_HW, NECK_TOP))
    return pts


def drop_every(t):
    return max(DROP_END, DROP_START - (DROP_START - DROP_END) * t / DROP_RAMP)


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 25
        sp.sleep_time_threshold = 0.6     # しばらく止まっていたら眠らせる(永久に動き続けない)
        self.space = sp
        pts = bowl_points()
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            s = pymunk.Segment(sp.static_body, a, b, 14)   # 厚めのかべ(大きい車がめりこんでもすり抜けない)
            s.elasticity, s.friction = BOWL_E, BOWL_F
            s.set_neighbors(pts[max(i - 1, 0)], pts[min(i + 2, len(pts) - 1)])
            sp.add(s)
        self.polys = polys()
        for k in range(len(NAMES)):
            sp.on_collision(10 + k, 10 + k, begin=self._touch)
        self.cows = []
        self.next_id = 0
        self.pairs = []
        self.events = []
        self.t = 0.0
        self.next_drop = 0.4
        self.best = 0
        self.result, self.result_t = None, None
        self.over_since = None

    def _touch(self, arb, space, data):
        """同じ段階どうしが触れたら合体する(V_MERGE = 0)。"""
        a, b = arb.shapes
        if self.result is None:
            n = arb.normal
            rel = (a.body.velocity - b.body.velocity).dot(n)
            if abs(rel) >= V_MERGE:
                self.pairs.append((a.body, b.body))

    def add(self, stage, x, y, ang=0.0, vx=0.0, vy=0.0, w=0.0):
        poly = self.polys[stage]
        mass = 1.0 * (WIDTHS[stage] / WIDTHS[0]) ** 2
        b = pymunk.Body(mass, pymunk.moment_for_poly(mass, poly))
        b.position, b.angle = (x, y), ang
        b.velocity, b.angular_velocity = (vx, vy), w
        s = pymunk.Poly(b, poly, radius=2)
        s.elasticity, s.friction = COW_E, COW_F
        s.collision_type = 10 + stage
        self.space.add(b, s)
        cow = {"id": self.next_id, "stage": stage, "body": b, "shape": s, "born": self.t}
        self.next_id += 1
        self.cows.append(cow)
        return cow

    def step(self, dt):
        self.t += dt
        if self.result is None and self.t >= self.next_drop:
            self.next_drop += drop_every(self.t)
            stage = 0   # 首から落ちてくるのは、いつも初代
            x = FL_CX + self.rng.uniform(-14, 14)
            c = self.add(stage, x, DROP_Y, ang=self.rng.uniform(-0.4, 0.4),
                         vx=self.rng.uniform(-30, 30), w=self.rng.uniform(-2.0, 2.0))
            self.events.append(("drop", self.t, (c["id"], stage)))
        self.pairs = []
        self.space.step(dt)
        by_body = {c["body"]: c for c in self.cows}
        used = set()
        for ba, bb in self.pairs:
            ca, cb = by_body.get(ba), by_body.get(bb)
            if ca is None or cb is None or ca["id"] in used or cb["id"] in used or ca["stage"] != cb["stage"]:
                continue
            if ca["stage"] >= GOAL:
                continue
            used |= {ca["id"], cb["id"]}
            st = ca["stage"] + 1
            pa, pb = ba.position, bb.position
            x, y = (pa.x + pb.x) / 2, (pa.y + pb.y) / 2
            v = (ba.velocity + bb.velocity) / 2
            # 首の中で合体したときは、大きくなった車が首につかえて外へはじき出されないよう、丸い部分の入口に出す
            half = WIDTHS[st] / 2
            if y < NECK_Y + half * 0.5:
                x, y = FL_CX, NECK_Y + half * 0.6
                v = pymunk.Vec2d(0, max(0.0, v.y))
            # 丸い部分のかべにめりこまないよう、中心側へ寄せる
            dx, dy = x - FL_CX, y - FL_CY
            dist = math.hypot(dx, dy)
            lim = FL_R - half - 12
            if dist > lim > 0:
                x, y = FL_CX + dx / dist * lim, FL_CY + dy / dist * lim
            ang = math.atan2(math.sin(ba.angle) + math.sin(bb.angle), math.cos(ba.angle) + math.cos(bb.angle))
            for c in (ca, cb):
                self.space.remove(c["body"], c["shape"])
                self.cows.remove(c)
            nc = self.add(st, x, y, ang=ang, vx=v.x, vy=v.y, w=(ba.angular_velocity + bb.angular_velocity) / 2)
            self.events.append(("merge", self.t, (nc["id"], st, x, y, ca["id"], cb["id"])))
            if st > self.best:
                self.best = st
                if st == GOAL and self.result is None:
                    self.result, self.result_t = "success", self.t
                    self.events.append(("success", self.t, None))
        if self.result is None:
            # 止まったものが首の中まで積み上がったら、あふれ(画面の座標は下向きなので bb.bottom が見た目の上端)
            top = min((c["shape"].bb.bottom for c in self.cows
                       if self.t - c["born"] > 1.5 and c["body"].velocity.length < 60), default=H)
            if top < OVER_Y:
                if self.over_since is None:
                    self.over_since = self.t
                if self.t - self.over_since > OVER_WAIT:
                    self.result, self.result_t = "fail", self.t
                    self.events.append(("fail", self.t, "overflow"))
            else:
                self.over_since = None
            if self.result is None and self.t >= TIME_LIMIT:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, "time"))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "best": g.best,
                           "cows": [(c["id"], c["stage"], c["body"].position.x, c["body"].position.y,
                                     c["body"].angle) for c in g.cows],
                           "over": g.over_since})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "best": g.best}


def score(seed):
    r = simulate(seed)
    why = next((e[2] for e in r["events"] if e[0] == "fail"), "")
    n3 = sum(1 for e in r["events"] if e[0] == "merge" and e[2][1] == GOAL - 1)
    return seed, r["result"], r["result_t"], r["best"], why, n3


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "fail":
        for seed, _, rt, best, why, n3 in sorted([r for r in rs if r[1] == "fail"], key=lambda r: (-r[3], -r[5]))[:15]:
            print(f"seed={seed:4d}  最高 {NAMES[best]} / {NAMES[GOAL - 1]} {n3}頭 / {'時間切れ' if why == 'time' else 'あふれ'} {rt:5.2f}秒")
    else:
        for seed, _, rt, _, _, _ in sorted(succ, key=lambda r: -r[2])[:15]:
            print(f"seed={seed:4d}  最新クラウン {rt:5.2f}秒")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def background():
    """夜のショールームのような暗い背景:上からのやわらかいスポットライトと、床のにぶい反射。"""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, 0.035, 0.04, 0.05)
    g.add_color_stop_rgb(0.55, 0.07, 0.075, 0.09)
    g.add_color_stop_rgb(1, 0.02, 0.02, 0.025)
    ctx.set_source(g)
    ctx.paint()
    spot = cairo.RadialGradient(FL_CX, FL_CY - 250, 50, FL_CX, FL_CY, 900)
    spot.add_color_stop_rgba(0, 1, 0.97, 0.9, 0.10)
    spot.add_color_stop_rgba(1, 1, 0.97, 0.9, 0.0)
    ctx.set_source(spot)
    ctx.paint()
    floor = cairo.RadialGradient(FL_CX, FL_CY + FL_R + 20, 10, FL_CX, FL_CY + FL_R + 20, 520)
    floor.add_color_stop_rgba(0, 0.8, 0.8, 0.85, 0.10)
    floor.add_color_stop_rgba(1, 0.8, 0.8, 0.85, 0.0)
    ctx.save()
    ctx.translate(0, 0)
    ctx.scale(1, 0.25)
    ctx.translate(0, (FL_CY + FL_R + 20) * 3)
    ctx.set_source(floor)
    ctx.paint()
    ctx.restore()
    return surf


def draw_flask(ctx, t):
    """透明なガラスの容器:細い白い線と、左上に光の映りこみ。"""
    pts = bowl_points()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.set_source_rgba(1, 1, 1, 0.10)
    ctx.set_line_width(14)
    ctx.stroke_preserve()
    ctx.set_source_rgba(0.92, 0.95, 1.0, 0.75)
    ctx.set_line_width(3)
    ctx.stroke()
    # ガラスの映りこみ(左上の弧と右下のうすい弧)
    for a0, a1, al, rr in ((math.radians(200), math.radians(245), 0.35, FL_R - 22),
                           (math.radians(20), math.radians(50), 0.15, FL_R - 22)):
        ctx.new_path()
        ctx.arc(FL_CX, FL_CY, rr, a0, a1)
        ctx.set_source_rgba(1, 1, 1, al)
        ctx.set_line_width(7)
        ctx.stroke()
    # あふれライン(首のつなぎ目)
    ctx.new_path()
    ctx.move_to(FL_CX - NECK_HW + 10, OVER_Y)
    ctx.line_to(FL_CX + NECK_HW - 10, OVER_Y)
    ctx.set_source_rgba(1, 0.4, 0.4, 0.45)
    ctx.set_line_width(2)
    ctx.stroke()


def draw_merge_fx(ctx, x, y, st, age):
    """進化の光:やわらかい白い光が一瞬ふくらみ、細い光の筋が数本のびて消える。"""
    big = 1 + 0.25 * st
    if age < 0.45:
        k = 1 - age / 0.45
        g = cairo.RadialGradient(x, y, 0, x, y, 110 * big)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.75 * k)
        g.add_color_stop_rgba(0.35, 1, 0.96, 0.85, 0.30 * k)
        g.add_color_stop_rgba(1, 1, 0.95, 0.8, 0)
        ctx.new_path()
        ctx.arc(x, y, 110 * big, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
    if age < 0.6:
        k = 1 - age / 0.6
        ln = (60 + 220 * age) * big
        for j in range(6):
            a = j * math.pi / 3 + 0.4
            ctx.new_path()
            ctx.move_to(x + math.cos(a) * ln * 0.35, y + math.sin(a) * ln * 0.35)
            ctx.line_to(x + math.cos(a) * ln, y + math.sin(a) * ln)
            ctx.set_source_rgba(1, 1, 1, 0.55 * k)
            ctx.set_line_width(2)
            ctx.stroke()


def year_tag(ctx, x, y, st):
    """車の上に小さな年のタグ。"""
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(24)
    s_ = SHORT[st]
    e = ctx.text_extents(s_)
    w_, h_ = e.width + 18, 32
    ctx.new_path()
    r_ = 10
    x0, y0 = x - w_ / 2, y - h_ / 2
    ctx.arc(x0 + r_, y0 + r_, r_, math.pi, 1.5 * math.pi)
    ctx.arc(x0 + w_ - r_, y0 + r_, r_, 1.5 * math.pi, 0)
    ctx.arc(x0 + w_ - r_, y0 + h_ - r_, r_, 0, 0.5 * math.pi)
    ctx.arc(x0 + r_, y0 + h_ - r_, r_, 0.5 * math.pi, math.pi)
    ctx.close_path()
    ctx.set_source_rgba(0.05, 0.05, 0.06, 0.72 if st < GOAL else 0.85)
    ctx.fill_preserve()
    ctx.set_source_rgba(*(GOLD if st == GOAL else (1, 1, 1)), 0.55)
    ctx.set_line_width(1.5)
    ctx.stroke()
    ctx.move_to(x - e.width / 2 - e.x_bearing, y - e.height / 2 - e.y_bearing)
    ctx.set_source_rgba(*(GOLD if st == GOAL else (1, 1, 1)), 0.95)
    ctx.show_text(s_)


def gen_label(st):
    return f"{SHORT[st]}年 {NAMES[st]}" + (f"「{NICK[st]}」" if NICK[st] else "")


def draw_reveal(ctx, sprite, age, src):
    """成功したときの発表演出:背景が暗くなり、上からのスポットライトの中で最新のクラウンが巨大になって現れ、
    ボディに光の帯が走る。最後に「70年の進化、完成。」"""
    x0, y0 = src
    dark = min(1.0, age / 0.6)
    ctx.rectangle(0, 0, W, H)
    ctx.set_source_rgba(0, 0, 0, 0.88 * dark)
    ctx.fill()
    # スポットライト(上から広がる光の円すい)
    if age > 0.3:
        a = min(1.0, (age - 0.3) / 0.6)
        ctx.new_path()
        ctx.move_to(W / 2 - 60, 0)
        ctx.line_to(W / 2 + 60, 0)
        ctx.line_to(W / 2 + 560, 1420)
        ctx.line_to(W / 2 - 560, 1420)
        ctx.close_path()
        g = cairo.LinearGradient(0, 0, 0, 1420)
        g.add_color_stop_rgba(0, 1, 0.97, 0.9, 0.22 * a)
        g.add_color_stop_rgba(1, 1, 0.97, 0.9, 0.04 * a)
        ctx.set_source(g)
        ctx.fill()
        fl = cairo.RadialGradient(W / 2, 1330, 10, W / 2, 1330, 520)
        fl.add_color_stop_rgba(0, 1, 0.97, 0.9, 0.25 * a)
        fl.add_color_stop_rgba(1, 1, 0.97, 0.9, 0)
        ctx.save()
        ctx.translate(0, 1330)
        ctx.scale(1, 0.18)
        ctx.translate(0, -1330)
        ctx.set_source(fl)
        ctx.arc(W / 2, 1330, 520, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()
    # 車が真ん中に巨大になって現れる
    p = min(1.0, max(0.0, (age - 0.2) / 1.3))
    e = 1 - (1 - p) ** 3
    tx, ty = W / 2, 1200
    x = x0 + (tx - x0) * e
    y = y0 + (ty - y0) * e
    k = (1 + 1.06 * e) * (1 + 0.01 * math.sin(age * 2))
    car = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c2 = cairo.Context(car)
    sprite.draw(c2, x, y, 0.0, k)
    # 床への映りこみ
    if e > 0.5:
        ctx.save()
        ctx.translate(0, 2 * (y + sprite.h * k / 2))
        ctx.scale(1, -1)
        ctx.set_source_surface(car, 0, 0)
        ctx.paint_with_alpha(0.18 * (e - 0.5) * 2)
        ctx.restore()
    ctx.set_source_surface(car, 0, 0)
    ctx.paint()
    # ボディに走る光の帯(車の形で切り抜く)
    if 1.5 < age < 2.7:
        q = (age - 1.5) / 1.2
        cx_ = -300 + (W + 600) * q
        band = cairo.LinearGradient(cx_ - 160, 0, cx_ + 160, 120)
        band.add_color_stop_rgba(0, 1, 1, 1, 0)
        band.add_color_stop_rgba(0.5, 1, 1, 1, 0.55)
        band.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(band)
        ctx.mask_surface(car, 0, 0)
    # 文字
    if age > 2.2:
        a = min(1.0, (age - 2.2) / 0.6)
        text(ctx, "70年の進化、完成。", W / 2, 1560, 78, rgb=(1, 1, 1), sw=0, alpha=a)
        text(ctx, "2022年  16代目「クロスオーバー」", W / 2, 1650, 40, rgb=GOLD, sw=0, alpha=a * 0.9)


def draw_chart(ctx, sprites, best, t):
    """上の進化表。8世代の写真を並べ、たどり着いた世代は明るく、ゴールの最新クラウンは金の輪。"""
    y = 410
    xs = [72 + k * 133.7 for k in range(len(NAMES))]
    for k in range(len(NAMES) - 1):
        mx = (xs[k] + xs[k + 1]) / 2   # 小さな三角の矢印
        ctx.new_path()
        ctx.move_to(mx - 5, y - 7)
        ctx.line_to(mx + 6, y)
        ctx.line_to(mx - 5, y + 7)
        ctx.close_path()
        ctx.set_source_rgba(1, 1, 1, 0.4)
        ctx.fill()
    for k, x in enumerate(xs):
        goal = k == GOAL
        r = 60 if goal else 52
        reached = k <= best
        ctx.new_path()
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.14 if reached else 0.05)
        ctx.fill_preserve()
        if goal:
            ctx.set_source_rgba(*GOLD, 0.7)
            ctx.set_line_width(2)
            ctx.stroke()
        else:
            ctx.new_path()
        sp = sprites[k]
        k_fit = (r * 1.75) / max(sp.w, sp.h)
        sp.draw(ctx, x, y, 0.0, k_fit, alpha=1.0 if (reached or goal) else 0.35)
        text(ctx, SHORT[k], x, y + r + 30, 26,
             rgb=GOLD if goal else ((1, 1, 1) if reached else (0.55, 0.55, 0.6)), sw=0)


def remix(seed):
    """映像はそのままで、音だけ作り直して差し替える。"""
    res = simulate(seed)
    final = os.path.join(OUT_DIR, f"crown_{seed}.mp4")
    tmp = os.path.join(OUT_DIR, f"crown_{seed}_tmp.mp4")
    wav = os.path.join(OUT_DIR, f"crown_{seed}.wav")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", final],
                               capture_output=True, text=True).stdout)
    synth_audio(res, dur, wav)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", final, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, final)
    os.remove(wav)
    print("音を差し替えました:", final)


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    sprites = [Sprite(k) for k in range(len(NAMES))]
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"crown_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"crown_{seed}.wav")
    final = os.path.join(OUT_DIR, f"crown_{seed}.mp4")
    bg = background()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    reveal_src = None
    born = {}
    pops = []
    shake = 0.0
    ev_i = 0
    fail_why = next((e[2] for e in events if e[0] == "fail"), "")
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "merge":
                cid, st, x, y = data[:4]
                born[cid] = et
                pops.append([et, x, y, st])
                shake = max(shake, 3 + 4 * st)
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0
        shake *= 0.85
        dx, dy = (math.sin(t * 61) * shake, math.cos(t * 53) * shake) if shake > 0.5 else (0, 0)

        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        ctx.save()
        ctx.translate(dx, dy)
        draw_flask(ctx, t)
        cars = sorted(fr["cows"], key=lambda c: c[1])
        for cid, st, x, y, ang in cars:
            b_t = born.get(cid)
            k = 1.0
            if b_t is not None and t - b_t < 0.25:   # 進化した直後はぷくっとふくらむ
                a = (t - b_t) / 0.25
                k = 0.7 + 0.3 * a + 0.12 * math.sin(a * math.pi)
            if over and not fail and st == GOAL:
                if reveal_src is None:
                    reveal_src = (x, y)
                continue
            sprites[st].draw(ctx, x, y, ang, k)
        for cid, st, x, y, ang in cars:   # 年のタグ(車の上に、いつもまっすぐ)
            if over and not fail and st == GOAL:
                continue
            year_tag(ctx, x, y - sprites[st].h * 0.5 - 22, st)
        keep = []
        for p in pops:
            age = t - p[0]
            if age < 1.4:
                if age < 0.9:
                    draw_merge_fx(ctx, p[1], p[2], p[3], age)
                keep.append(p)
        pops = keep
        ctx.restore()
        if fr["over"] is not None and not over:   # あふれそうな警告
            if int(t * 6) % 2 == 0:
                text(ctx, "つまりそう！", W / 2, OVER_Y + 70, 60, rgb=(1, 0.35, 0.35), sw=12)
        if over and not fail and reveal_src is not None:
            draw_reveal(ctx, sprites[GOAL], t - end_t, reveal_src)

        # 上の帯(発表演出の間は消す)
        hide = over and not fail
        ui_a = 1.0 if not hide else max(0.0, 1 - (t - end_t) / 0.5)
        if ui_a > 0:
            text(ctx, "初代クラウンを合体させて", W / 2, 130, 66, sw=8, alpha=ui_a)
            text(ctx, "最新クラウンにできる？", W / 2, 236, 88, rgb=GOLD, sw=10, alpha=ui_a)
            left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
            text(ctx, f"残り {left:4.1f}秒", W / 2, 316, 46, rgb=(1, 0.4, 0.4) if left < 10 else (0.9, 0.9, 0.92),
                 sw=6, alpha=ui_a)
            if not hide:
                draw_chart(ctx, sprites, fr["best"], t)
            # 進化した瞬間の世代の名前
            for p in reversed(pops):   # いちばん新しい進化だけ出す
                age = t - p[0]
                if age < 1.4:
                    a = min(1.0, age / 0.15) * min(1.0, (1.4 - age) / 0.3) * ui_a
                    text(ctx, gen_label(p[3]), W / 2, 640, 52 if p[3] < GOAL else 58,
                         rgb=GOLD if p[3] == GOAL else (1, 1, 1), sw=8, alpha=a)
                    break
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "つまった…" if fail_why == "overflow" else "時間切れ…", W / 2, 1100,
                 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"{SHORT[res['best']]}年の{NAMES[res['best']]}までだった…", W / 2, 1230, 62, sw=10)

        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
    ff.stdin.close()
    ff.wait()
    duration = len(frames) / FPS
    synth_audio(res, duration, wav)
    # 叫び声の大きさを残すため、音量の自動調整(loudnorm)はかけない
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(silent)
    os.remove(wav)
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} 最高 {NAMES[res['best']]} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
MIX_GAIN = 0.39  # 通常部分の音量(約 -18dB になるよう調整)
HOLY_GAIN = 0.85
ROOTS = [60, 62, 64, 65, 67, 69, 71, 72]   # 進化した段階ごとの和音の根音(段階が上がるほど高い)


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def pop(amp):
    """「ポン」:高い音から下がる短い音。"""
    t = _t(0.12)
    f = 900 * np.exp(-t * 25) + 250
    return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30)


def chime(freq, amp, dur=1.0):
    t = _t(dur)
    y = sum(a * np.sin(2 * np.pi * freq * m * t) * np.exp(-t * d)
            for m, a, d in ((1, 1, 3), (2.01, 0.4, 5), (3.0, 0.2, 8)))
    return amp * y * np.minimum(1, t / 0.003)


def drum(amp, seed):
    """ドラム:低い「ドン」+「パン」。"""
    t = _t(0.35)
    kick = np.sin(2 * np.pi * np.cumsum(120 * np.exp(-t * 18) + 45) / SR) * np.exp(-t * 9)
    snare = np.random.default_rng(seed).normal(0, 1, len(t)) * np.exp(-t * 22) * 0.6
    return amp * (kick + snare)


def brass(root, amp, dur=0.7):
    """ブラス:のこぎり波の和音(ド・ミ・ソ)をやわらかくした「パーン」。"""
    t = _t(dur)
    y = np.zeros_like(t)
    for m in (0, 4, 7, 12):
        f = midi_hz(root + m)
        for h in range(1, 8):   # のこぎり波の倍音
            y += np.sin(2 * np.pi * f * h * t) / h * (0.8 ** h)
    env = np.minimum(1, t / 0.02) * np.exp(-t * 2.2)
    return amp * y / 6 * env


def strings(root, amp, dur=1.4):
    """弦楽器のような、ふわっと広がる和音(ビブラートつき)。"""
    t = _t(dur)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t)
    y = sum(np.sin(2 * np.pi * midi_hz(root + m - 12) * vib * t) + 0.5 * np.sin(4 * np.pi * midi_hz(root + m - 12) * vib * t)
            for m in (0, 4, 7, 12, 16))
    env = np.minimum(1, t / 0.08) * np.exp(-t * 1.4)
    return amp * y / 5 * env


def cymbal(amp, seed, dur=1.2):
    t = _t(dur)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    hp = n - np.convolve(n, np.ones(8) / 8, mode="same")
    return amp * hp * np.exp(-t * 3)


def timpani(amp, dur=1.5):
    t = _t(dur)
    return amp * (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82 * t)) * np.exp(-t * 2.5) * np.minimum(1, t / 0.005)


def evolve_sound(st, seed):
    """進化の効果音。段階が上がるほど音が重なって豪華になる:
    ひよこ=ポン / ニワトリ=+キラキラ / ダチョウ=+ドラム / ワニ=+ブラス / 恐竜=+弦とシンバル / ドラゴン=全部+ティンパニの「ドーン!」"""
    root = ROOTS[st]
    parts = [pop(0.5)]
    if st >= 2:
        parts.append(chime(midi_hz(root + 12), 0.35))
    if st >= 3:
        parts.append(drum(0.6, seed))
    if st >= 4:
        parts.append(brass(root, 0.55))
    if st >= 5:
        parts.append(strings(root, 0.5))
        parts.append(cymbal(0.25, seed + 1))
    if st >= GOAL:   # 最新クラウン:長く大きな「ドーン!」
        parts.append(brass(root - 12, 0.8, dur=2.2))
        parts.append(strings(root, 0.8, dur=2.8))
        parts.append(timpani(1.0, dur=2.2))
        parts.append(cymbal(0.4, seed + 2, dur=2.5))
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


# 進化した段階の鳴き声(Higgs Field の Seedance 2.0 Mini で「6匹が順番に鳴く」動画を作り、音声から切り出したもの)
# 1=ひよこ(かわいいピヨピヨ)… 6=ドラゴン(一番低く凶暴な咆哮)。大きくなるほど声も低く・大きく
VOICE_GAIN = [0, 0.6, 0.65, 0.7, 0.8, 0.9, 1.0, 1.1]


def load_voice(st):
    path = os.path.join(SND_DIR, f"voice{st}.wav")
    if not os.path.exists(path):
        return None
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    return x / max(1e-9, np.max(np.abs(x)))


def thud(amp, seed):
    """卵が落ちて当たる「コトッ」。"""
    t = _t(0.12)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    return amp * (np.sin(2 * np.pi * 320 * t) * np.exp(-t * 45) + 0.4 * n * np.exp(-t * 120))


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 4) * SR)
    out = np.zeros(n_out)

    def add(sig, t0, gain=1.0):
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out:
            out[i:j] += gain * sig[: j - i]

    voices = {st: load_voice(st) for st in range(1, len(NAMES))}
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.05:
            continue
        if kind == "drop":
            add(thud(0.18, int(t * 1000)), t + 0.25)
        elif kind == "merge":
            st = data[1]
            add(evolve_sound(st, int(t * 1000)), t, 0.35 + 0.06 * st)   # 豪華になる効果音(鳴き声の下にひかえめに)
            if voices.get(st) is not None:
                add(voices[st], t + 0.03, VOICE_GAIN[st])
    extra = np.zeros(n_out)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:   # 発表演出:重いオーケストラの和音がのび、静かなハイブリッドの起動音、光の帯でシンバル
        def put(sig, t0, g):
            i0 = int(t0 * SR)
            m = min(len(sig), n_out - i0)
            if m > 0:
                extra[i0:i0 + m] += g * sig[:m]
        root = ROOTS[GOAL]
        for m_, a in ((root - 24, 0.5), (root - 12, 0.5), (root - 5, 0.35), (root, 0.35), (root + 4, 0.3)):
            put(strings(m_, a, dur=5.0), end_t + 0.3, 0.55)
            put(brass(m_, a * 0.8, dur=2.5), end_t + 0.3, 0.45)
        put(timpani(1.0, dur=2.5), end_t + 0.3, 0.6)
        if voices.get(GOAL) is not None:   # 16代目に進化したときと同じハイブリッドの起動音
            put(voices[GOAL], end_t + 1.2, 0.6)
        put(cymbal(0.5, 7, dur=2.0), end_t + 1.5, 0.35)
    wet = out.copy()
    for d, g in ((0.043, 0.28), (0.071, 0.2), (0.113, 0.14)):   # 広い部屋の響き
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    # 最後の「ドーン!」だけが大きくて全体が小さくならないよう、ほぼ最大(上位0.5%を除く)の大きさを基準にそろえる
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * MIX_GAIN
    wet = np.clip(wet + (0.95 if fail else 1.0) * extra[: len(wet)], -0.98, 0.98)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render", "remix"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--want", choices=["fail", "success"], default="fail")
    ap.add_argument("-n", type=int, default=200)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    elif a.mode == "remix":
        remix(a.seed)
    else:
        render(a.seed)
