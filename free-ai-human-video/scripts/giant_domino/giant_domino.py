"""「最後の巨大ドミノまで倒れきる?」指先ほどの小さなドミノから、1枚ごとに少しずつ大きくなっていくドミノ倒しの物理ショートを生成する。

- 横から見たドミノの列。最初は小さなドミノ(高さ30px)で、1枚ごとに約1.035倍ずつ大きくなる。
- 最後の5枚は「巨大化ゾーン」:1枚ごとに約1.5倍。大きすぎる相手は倒しきれないこともある(本物の物理と同じ限界)。
- ドミノの並びの間隔はシードごとに少しずつばらつく。最初に小さく押すだけで、あとは重力・衝突・摩擦のまま(ねらい・補正なし)。
- カメラは倒れていく先を追いかけ、ドミノが大きくなるにつれてズームアウトしていく。
- ドミノが倒れると「ジングルベル」(パブリックドメイン)が1音ずつ本来のテンポで進む。ドミノが大きくなるほど楽器が豪華になる
  (オルゴール → ピアノ → ブラス → オーケストラ)。
最後の巨大ドミノが倒れて大きな鐘を鳴らせば成功(天使)、途中で止まれば失敗(幽霊)。

使い方:
    python giant_domino.py search [--want fail|success] [-n 200]
    python giant_domino.py render --seed N
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
from ball_escape import midi_hz, text  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from angels import DURATION as ANGEL_DUR, AngelShow, holy_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
GRAVITY = 1500.0

H0 = 30.0                 # 最初のドミノの高さ
N1, R1 = 60, 1.035        # ふつうに大きくなっていく区間:枚数, 1枚ごとの倍率
N2, R2 = 5, float(os.environ.get("R2", 1.49))          # 巨大化ゾーン:枚数, 1枚ごとの倍率
K = 0.6                   # ドミノの間隔(手前のドミノの高さに対する割合)
JIT = 0.15                # 間隔のばらつき(±)
THICK = 0.18              # ドミノの厚み(高さに対する割合)
BELL_GAP = float(os.environ.get("BELL_GAP", 0.85))  # 最後のドミノの前の面から鐘のふちまでの距離(最後のドミノの高さに対する割合)
BELL_JIT = float(os.environ.get("BELL_JIT", 0.0))   # 鐘の位置のばらつき(±)。今は固定(倒れきれば必ず届く距離)
MACHO_P = float(os.environ.get("MACHO_P", 0.34))  # 最後の巨大ドミノが鐘に当たる直前にマッチョが現れて止める確率
MACHO_ANG = 0.72          # 最後のドミノがこの角度まで倒れたらマッチョが現れる(手に当たるのは約1.1)
BELL_SIZE = 0.55          # 鐘の大きさ(最後のドミノの高さに対する割合)
STOP_WAIT = 3.0           # これだけ次のドミノが倒れなければ止まった(失敗)
OUTRO = 2.5

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


def heights():
    hs = [H0 * R1 ** i for i in range(N1)]
    for _ in range(N2):
        hs.append(hs[-1] * R2)
    return hs


N = N1 + N2


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 40
        self.space = sp
        floor = pymunk.Segment(sp.static_body, (-2000, 0), (1e6, 0), 2)
        floor.friction, floor.elasticity = 0.8, 0.05
        sp.add(floor)
        self.hs = heights()
        self.doms = []
        x = 0.0
        for i, h in enumerate(self.hs):
            w = THICK * h
            m = w * h / 100
            b = pymunk.Body(m, pymunk.moment_for_box(m, (w, h)))
            b.position = (x + w / 2, -h / 2)
            s = pymunk.Poly.create_box(b, (w, h))
            s.friction, s.elasticity = 0.6, 0.05
            s.collision_type = 3
            self.idx_of = getattr(self, "idx_of", {})
            self.idx_of[s] = i
            sp.add(b, s)
            self.doms.append(b)
            if i + 1 < N:
                x += w + K * h * (1 + rng.uniform(-JIT, JIT))
        # 鐘(最後のドミノが倒れこむ先)
        # 鐘は床の上につるされた本物の当たり判定。倒れた巨大ドミノがふちに触れたら鳴る
        hl = self.hs[-1]
        bs = BELL_SIZE * hl
        self.bell_x = x + THICK * hl + BELL_GAP * hl * (1 + rng.uniform(-BELL_JIT, BELL_JIT)) + 0.55 * bs
        bx = self.bell_x
        bell = pymunk.Poly(sp.static_body, [(bx - 0.22 * bs, -1.25 * bs), (bx + 0.22 * bs, -1.25 * bs),
                                            (bx + 0.55 * bs, -0.4 * bs), (bx - 0.55 * bs, -0.4 * bs)])
        bell.friction, bell.elasticity = 0.5, 0.1
        bell.collision_type = 2
        sp.add(bell)
        self.bell_hit = False
        self.landed = False
        self.hit = [None] * N        # ドミノ i が前のドミノに当てられた(=音を鳴らす)瞬間
        self.hit[0] = 0.0            # 最初の1枚は指で押す

        def on_bell(arb, space, data):
            a, b = arb.shapes
            if self.idx_of.get(a, self.idx_of.get(b)) == N - 1 and not self.macho_caught:
                self.bell_hit = True
        sp.on_collision(3, 2, begin=on_bell)

        def on_dom(arb, space, data):   # ドミノどうしが実際にぶつかった瞬間
            a, b = arb.shapes
            i, j = sorted((self.idx_of[a], self.idx_of[b]))
            if j == i + 1 and self.hit[j] is None:
                self.hit[j] = self.t
                self.events.append(("hit", self.t, j))
        sp.on_collision(3, 3, begin=on_dom)
        # マッチョ:最後の巨大ドミノが鐘に当たる直前に現れ、両手(本物の当たり判定)で受け止める
        self.macho = rng.uniform() < MACHO_P
        lip = bx - 0.55 * bs
        self.hand = (lip - 0.06 * hl, -0.40 * hl)
        self.hand_r = 0.05 * hl
        self.macho_t, self.macho_caught = None, False

        def on_hand(arb, space, data):
            if not self.macho_caught:
                self.macho_caught = True
                self.events.append(("catch", self.t, None))
        sp.on_collision(3, 4, begin=on_hand)
        b0 = self.doms[0]
        b0.apply_impulse_at_local_point((b0.mass * 60, 0), (0, -self.hs[0] * 0.4))   # 最初のドミノを指で軽く押す
        self.fell = [None] * N
        self.events = [("hit", 0.0, 0)]   # 最初の1枚を指で押した音
        self.t = 0.0
        self.result, self.result_t = None, None

    def step(self, dt):
        self.t += dt
        self.space.step(dt)
        for i, b in enumerate(self.doms):
            if self.fell[i] is None and abs(b.angle) > 0.5:
                self.fell[i] = self.t
                self.events.append(("fall", self.t, i))
        if self.macho and self.macho_t is None and abs(self.doms[-1].angle) > MACHO_ANG:
            self.macho_t = self.t   # シュッ!とマッチョ登場。手の位置に当たり判定を置く
            hand = pymunk.Circle(self.space.static_body, self.hand_r, self.hand)
            hand.friction, hand.elasticity = 1.0, 0.0
            hand.collision_type = 4
            self.space.add(hand)
            self.events.append(("macho", self.t, None))
        if self.fell[-1] is not None and not self.landed and abs(self.doms[-1].angle) > 1.45:
            self.landed = True   # 巨大ドミノが床にドスン
            self.events.append(("land", self.t, None))
        if self.result is None:
            last = max((i for i in range(N) if self.fell[i] is not None), default=-1)
            if self.bell_hit:   # 巨大ドミノが鐘に当たった
                self.result, self.result_t = "success", self.t
                self.events.append(("bell", self.t, None))
            elif last == N - 1 and self.t - self.fell[last] > 1.5 \
                    and abs(self.doms[-1].angular_velocity) < 0.05 and abs(self.doms[-1].velocity.x) < 5:
                # 最後のドミノは倒れたが、鐘に届かずに止まった
                self.result, self.result_t = "fail", self.t
                self.events.append(("miss", self.t, None))
            elif last >= 0 and last < N - 1 and self.t - self.fell[last] > STOP_WAIT \
                    and abs(self.doms[last + 1].angular_velocity) < 0.05:   # 次のドミノがもう動いていない
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, last + 1))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "doms": [(b.position.x, b.position.y, b.angle) for b in g.doms],
                           "fell": sum(f is not None for f in g.fell)})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
        if g.t > 120:
            break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "fell": sum(f is not None for f in g.fell), "hs": g.hs, "bell_x": g.bell_x,
            "hand": g.hand, "hand_r": g.hand_r, "macho_t": g.macho_t}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["fell"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "fail":
        for seed, _, rt, c in sorted([r for r in rs if r[1] == "fail"], key=lambda r: -r[3])[:15]:
            print(f"seed={seed:4d}  {c}/{N} 枚で止まった {rt:5.2f}秒")
    else:
        for seed, _, rt, _ in sorted(succ, key=lambda r: -r[2])[:15]:
            print(f"seed={seed:4d}  鐘を鳴らした {rt:5.2f}秒")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
FLOOR_Y = 1480.0          # 画面上の床の高さ


def dom_col(i):
    """ドミノの色:小さいうちは白っぽいアイボリー、大きくなるほど深い赤 → 巨大化ゾーンは金。"""
    if i >= N1:
        return (0.95, 0.75, 0.25)
    k = i / (N1 - 1)
    return (0.96 - 0.25 * k, 0.94 - 0.70 * k, 0.88 - 0.68 * k)


def background():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, H)   # 夜の体育館のような、上から光が当たる空間
    g.add_color_stop_rgb(0, 0.10, 0.12, 0.20)
    g.add_color_stop_rgb(0.7, 0.20, 0.20, 0.28)
    g.add_color_stop_rgb(1, 0.10, 0.10, 0.14)
    ctx.set_source(g)
    ctx.paint()
    spot = cairo.RadialGradient(W / 2, 600, 50, W / 2, 900, 1100)
    spot.add_color_stop_rgba(0, 1, 0.95, 0.85, 0.22)
    spot.add_color_stop_rgba(1, 1, 0.95, 0.85, 0.0)
    ctx.set_source(spot)
    ctx.paint()
    return surf


def draw_floor(ctx, cam_x, s):
    """木の床:板の継ぎ目が、カメラの動きとズームに合わせて流れる。"""
    ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y)
    g = cairo.LinearGradient(0, FLOOR_Y, 0, H)
    g.add_color_stop_rgb(0, 0.55, 0.36, 0.20)
    g.add_color_stop_rgb(1, 0.30, 0.18, 0.09)
    ctx.set_source(g)
    ctx.fill()
    plank = 120.0
    x0 = math.floor((cam_x - W / 2 / s) / plank) * plank
    x = x0
    while (x - cam_x) * s + W / 2 < W:
        sx = (x - cam_x) * s + W / 2
        ctx.new_path()
        ctx.move_to(sx, FLOOR_Y)
        ctx.line_to(sx, H)
        ctx.set_source_rgba(0.2, 0.1, 0.05, 0.35)
        ctx.set_line_width(2)
        ctx.stroke()
        x += plank
    ctx.new_path()
    ctx.move_to(0, FLOOR_Y)
    ctx.line_to(W, FLOOR_Y)
    ctx.set_source_rgba(1, 0.9, 0.7, 0.5)
    ctx.set_line_width(2)
    ctx.stroke()


def draw_domino(ctx, x, y, ang, h, col, hit):
    w = THICK * h
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    r = min(w, h) * 0.18
    ctx.new_path()
    ctx.move_to(-w / 2 + r, -h / 2)
    ctx.arc(w / 2 - r, -h / 2 + r, r, -math.pi / 2, 0)
    ctx.arc(w / 2 - r, h / 2 - r, r, 0, math.pi / 2)
    ctx.arc(-w / 2 + r, h / 2 - r, r, math.pi / 2, math.pi)
    ctx.arc(-w / 2 + r, -h / 2 + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()
    g = cairo.LinearGradient(-w / 2, 0, w / 2, 0)
    g.add_color_stop_rgb(0, col[0] * 0.65, col[1] * 0.65, col[2] * 0.65)
    g.add_color_stop_rgb(0.35, min(1, col[0] * 1.1), min(1, col[1] * 1.1), min(1, col[2] * 1.1))
    g.add_color_stop_rgb(1, col[0] * 0.75, col[1] * 0.75, col[2] * 0.75)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.1, 0.06, 0.04, 0.8)
    ctx.set_line_width(max(1.0, w * 0.06))
    ctx.stroke()
    # 真ん中の線(ドミノの模様)
    ctx.new_path()
    ctx.move_to(-w * 0.35, 0)
    ctx.line_to(w * 0.35, 0)
    ctx.set_source_rgba(0.1, 0.06, 0.04, 0.6)
    ctx.set_line_width(max(1.0, w * 0.06))
    ctx.stroke()
    if hit > 0:
        ctx.new_path()
        ctx.rectangle(-w / 2, -h / 2, w, h)
        ctx.set_source_rgba(1, 1, 0.85, 0.5 * hit)
        ctx.fill()
    ctx.restore()


def draw_bell(ctx, x, y_base, size, swing):
    """大きな金色の鐘(床に置いた台につるしてある)。"""
    ctx.save()
    ctx.translate(x, y_base - size * 1.25)
    # 台
    ctx.set_source_rgb(0.35, 0.22, 0.12)
    # 台は奥側(右)の柱1本から腕を出してつるす形。手前(左)には何もないので、鐘のふちまでのすき間がよく見える
    ctx.rectangle(-size * 0.1, -size * 0.18, size * 0.95, size * 0.12)
    ctx.fill()
    ctx.rectangle(size * 0.75, -size * 0.18, size * 0.1, size * 1.43)
    ctx.fill()
    ctx.rectangle(-size * 0.04, -size * 0.1, size * 0.08, size * 0.12)
    ctx.fill()
    ctx.rotate(swing)
    ctx.new_path()
    ctx.move_to(-size * 0.22, 0)
    ctx.curve_to(-size * 0.3, size * 0.2, -size * 0.35, size * 0.6, -size * 0.55, size * 0.85)
    ctx.line_to(size * 0.55, size * 0.85)
    ctx.curve_to(size * 0.35, size * 0.6, size * 0.3, size * 0.2, size * 0.22, 0)
    ctx.close_path()
    g = cairo.LinearGradient(-size * 0.55, 0, size * 0.55, 0)
    g.add_color_stop_rgb(0, 0.55, 0.38, 0.08)
    g.add_color_stop_rgb(0.4, 1.0, 0.88, 0.45)
    g.add_color_stop_rgb(1, 0.5, 0.33, 0.06)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(0.3, 0.2, 0.05)
    ctx.set_line_width(max(2, size * 0.02))
    ctx.stroke()
    ctx.restore()


SKIN = (0.93, 0.66, 0.46)
SKIN_D = (0.72, 0.45, 0.30)


def _limb(ctx, pts, w, col):
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.set_source_rgb(0.25, 0.13, 0.07)
    ctx.set_line_width(w + w * 0.18)
    ctx.stroke_preserve()
    ctx.set_source_rgb(*col)
    ctx.set_line_width(w)
    ctx.stroke()


def _blob(ctx, x, y, rx, ry, col, line=True):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(*col)
    if line:
        ctx.fill_preserve()
        ctx.set_source_rgb(0.25, 0.13, 0.07)
        ctx.set_line_width(max(1.0, rx * 0.06))
        ctx.stroke()
    else:
        ctx.fill()


def draw_macho(ctx, hand, h, age, part):
    """マッチョ(ワールド座標)。hand=両手の位置、h=最後のドミノの高さ、age=登場してからの秒数。
    part="body" はドミノより奥(体)、"hands" はドミノより手前(にぎった手)。"""
    hx, hy = hand
    k = min(1.0, age / 0.12)
    pop = k * (1 + 0.25 * math.sin(min(1.0, age / 0.35) * math.pi))   # ボンッと出てくる
    if pop <= 0:
        return
    cx = hx + 0.20 * h                 # 立ち位置(手より少し奥=鐘の前)
    ctx.save()
    ctx.translate(cx, 0)
    ctx.scale(pop, pop)
    ctx.translate(-cx, 0)
    u = h
    if part == "body":
        # 登場の煙
        if age < 0.6:
            a = 1 - age / 0.6
            for j in range(7):
                ang = j / 7 * 2 * math.pi
                rr = 0.18 * u + 0.25 * u * (1 - a)
                ctx.arc(cx + math.cos(ang) * rr, -0.3 * u + math.sin(ang) * rr * 0.7, 0.09 * u * a + 0.02 * u, 0, 2 * math.pi)
                ctx.set_source_rgba(1, 1, 1, 0.75 * a)
                ctx.fill()
        sh_x, sh_y = cx - 0.02 * u, -0.50 * u        # 肩
        # 脚(赤いパンツ)
        _limb(ctx, [(cx + 0.05 * u, -0.22 * u), (cx + 0.08 * u, -0.03 * u)], 0.085 * u, SKIN)
        _limb(ctx, [(cx - 0.06 * u, -0.22 * u), (cx - 0.09 * u, -0.03 * u)], 0.085 * u, SKIN)
        for fx_ in (cx + 0.10 * u, cx - 0.11 * u):    # くつ
            _blob(ctx, fx_, -0.02 * u, 0.06 * u, 0.025 * u, (0.15, 0.15, 0.2))
        ctx.move_to(cx - 0.12 * u, -0.30 * u)
        ctx.line_to(cx + 0.12 * u, -0.30 * u)
        ctx.line_to(cx + 0.11 * u, -0.19 * u)
        ctx.line_to(cx - 0.11 * u, -0.19 * u)
        ctx.close_path()
        ctx.set_source_rgb(0.85, 0.12, 0.15)
        ctx.fill_preserve()
        ctx.set_source_rgb(0.25, 0.13, 0.07)
        ctx.set_line_width(0.008 * u)
        ctx.stroke()
        # 逆三角形の胴体
        ctx.move_to(sh_x - 0.19 * u, sh_y - 0.02 * u)
        ctx.curve_to(sh_x - 0.10 * u, sh_y - 0.06 * u, sh_x + 0.12 * u, sh_y - 0.06 * u, sh_x + 0.21 * u, sh_y - 0.02 * u)
        ctx.curve_to(sh_x + 0.20 * u, sh_y + 0.10 * u, sh_x + 0.15 * u, sh_y + 0.16 * u, cx + 0.12 * u, -0.30 * u)
        ctx.line_to(cx - 0.12 * u, -0.30 * u)
        ctx.curve_to(sh_x - 0.14 * u, sh_y + 0.16 * u, sh_x - 0.19 * u, sh_y + 0.10 * u, sh_x - 0.19 * u, sh_y - 0.02 * u)
        ctx.close_path()
        ctx.set_source_rgb(*SKIN)
        ctx.fill_preserve()
        ctx.set_source_rgb(0.25, 0.13, 0.07)
        ctx.set_line_width(0.01 * u)
        ctx.stroke()
        # 胸と腹筋のライン
        ctx.set_source_rgb(*SKIN_D)
        ctx.set_line_width(0.008 * u)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for sx in (-1, 1):
            ctx.arc(sh_x + sx * 0.075 * u, sh_y + 0.035 * u, 0.07 * u, 0.15 * math.pi, 0.85 * math.pi)
            ctx.new_sub_path()
        ctx.stroke()
        for yy in (-0.40, -0.36, -0.32):
            ctx.move_to(cx - 0.05 * u, yy * u)
            ctx.line_to(cx + 0.05 * u, yy * u)
        ctx.move_to(cx, -0.42 * u)
        ctx.line_to(cx, -0.31 * u)
        ctx.stroke()
        # 頭(サングラス・にやり)
        hcx, hcy = sh_x + 0.01 * u, sh_y - 0.11 * u
        _limb(ctx, [(hcx, sh_y - 0.02 * u), (hcx, hcy)], 0.07 * u, SKIN)   # 太い首
        _blob(ctx, hcx, hcy, 0.075 * u, 0.085 * u, SKIN)
        ctx.move_to(hcx - 0.075 * u, hcy - 0.03 * u)
        ctx.curve_to(hcx - 0.07 * u, hcy - 0.12 * u, hcx + 0.07 * u, hcy - 0.12 * u, hcx + 0.075 * u, hcy - 0.03 * u)
        ctx.close_path()
        ctx.set_source_rgb(0.12, 0.08, 0.06)
        ctx.fill()
        ctx.rectangle(hcx - 0.07 * u, hcy - 0.015 * u, 0.14 * u, 0.035 * u)
        ctx.set_source_rgb(0.05, 0.05, 0.08)
        ctx.fill()
        ctx.rectangle(hcx - 0.055 * u, hcy - 0.01 * u, 0.03 * u, 0.008 * u)
        ctx.set_source_rgba(1, 1, 1, 0.7)
        ctx.fill()
        ctx.arc(hcx - 0.005 * u, hcy + 0.035 * u, 0.03 * u, 0.1 * math.pi, 0.75 * math.pi)
        ctx.set_source_rgb(0.25, 0.1, 0.05)
        ctx.set_line_width(0.009 * u)
        ctx.stroke()
        # 腕(ムキッとした力こぶ)。手はドミノの手前に描く
        for dy in (-0.015, 0.015):
            ex, ey = (sh_x + hx) / 2 + 0.02 * u, (sh_y + hy) / 2 + 0.07 * u + dy * u
            _limb(ctx, [(sh_x - 0.13 * u, sh_y + dy * u), (ex, ey), (hx, hy + dy * u)], 0.075 * u, SKIN)
            _blob(ctx, (sh_x - 0.13 * u + ex) / 2, (sh_y + ey) / 2 - 0.035 * u, 0.065 * u, 0.045 * u, SKIN, line=False)
    else:
        _blob(ctx, hx, hy, 0.055 * u, 0.05 * u, SKIN)
        ctx.set_source_rgb(*SKIN_D)
        ctx.set_line_width(0.006 * u)
        for j in range(3):
            ctx.move_to(hx - 0.03 * u, hy - 0.02 * u + j * 0.018 * u)
            ctx.line_to(hx + 0.01 * u, hy - 0.02 * u + j * 0.018 * u)
        ctx.stroke()
    ctx.restore()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    hs = res["hs"]
    fail = result == "fail"
    miss = any(e[0] == "miss" for e in events)   # 最後まで倒れたのに鐘に届かなかった
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"giant_domino_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"giant_domino_{seed}.wav")
    final = os.path.join(OUT_DIR, f"giant_domino_{seed}.mp4")
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
    fall_t = {}
    bell_t = None
    shake = 0.0
    cam_x = frames[0]["doms"][0][0] + 60
    cam_s = 3.0
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "hit":
                fall_t[data] = et
                shake = max(shake, 0.4 * math.sqrt(hs[data]) if data >= N1 else 0)
            elif kind == "catch":
                shake = max(shake, 26)
            elif kind == "bell":
                bell_t = et
                shake = max(shake, 30)
            elif kind == "land" and bell_t is None:
                shake = max(shake, 22)
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0
        # カメラ:倒れていく先のドミノを追い、大きくなるほどズームアウト
        front = min(fr["fell"], N - 1)
        fx = fr["doms"][front][0]
        hf = hs[front]
        # 画面上のドミノの高さ:最初は260px、大きくなるほど画面の中でも大きく見える(最後は約1000px)
        tgt_s = 260.0 * (hf / H0) ** 0.33 / hf
        tgt_x = fx + hf * 0.25
        if front >= N - 1:   # 最後の巨大ドミノ(倒れた後の長さ)と鐘が両方入るように引く
            left = frames[0]["doms"][N - 1][0] - hs[-1] * 0.3
            right = res["bell_x"] + hs[-1] * BELL_SIZE * 0.8
            tgt_s = min(tgt_s, 0.94 * W / (right - left))
            tgt_x = (left + right) / 2
        cam_s += (tgt_s - cam_s) * 0.06
        cam_x += (tgt_x - cam_x) * 0.08
        shake *= 0.86
        dx, dy = (math.sin(t * 57) * shake, math.cos(t * 49) * shake) if shake > 0.5 else (0, 0)

        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        ctx.save()
        ctx.translate(dx, dy)
        draw_floor(ctx, cam_x, cam_s)
        # 巨大化ゾーンの床の目印
        zx = (fr["doms"][N1][0] - hs[N1] * 0.5 - cam_x) * cam_s + W / 2
        if -200 < zx < W + 200:
            ctx.rectangle(zx, FLOOR_Y + 4, W * 3, 18)
            ctx.set_source_rgba(1, 0.75, 0.2, 0.55)
            ctx.fill()
            text(ctx, "ここから巨大化ゾーン", zx + 20, FLOOR_Y + 70, 40, rgb=GOLD, sw=8, align="left")
        # 鐘
        swing = 0.0
        if bell_t is not None:
            a = t - bell_t
            swing = 0.35 * math.exp(-a * 1.2) * math.sin(a * 7)
        bx = (res["bell_x"] - cam_x) * cam_s + W / 2
        bsize = hs[-1] * 0.55 * cam_s
        if bx - bsize < W:
            draw_bell(ctx, bx, FLOOR_Y, bsize, swing)
        ctx.save()
        ctx.translate(W / 2, FLOOR_Y)
        ctx.scale(cam_s, cam_s)
        ctx.translate(-cam_x, 0)
        lo = cam_x - W / 2 / cam_s - 200
        hi = cam_x + W / 2 / cam_s + 200
        m_age = t - res["macho_t"] if res["macho_t"] is not None and t >= res["macho_t"] else None
        if m_age is not None:
            draw_macho(ctx, res["hand"], hs[-1], m_age, "body")
        for i, (x, y, ang) in enumerate(fr["doms"]):
            if x < lo - hs[i] or x > hi + hs[i]:
                continue
            ft = fall_t.get(i)
            hit = max(0.0, 1 - (t - ft) / 0.25) if ft is not None and t >= ft else 0.0
            draw_domino(ctx, x, y, ang, hs[i], dom_col(i), hit)
        if m_age is not None:
            draw_macho(ctx, res["hand"], hs[-1], m_age, "hands")
        ctx.restore()
        ctx.restore()
        if angels is not None and over:
            angels.draw(ctx, t - end_t)

        # 文字
        g = cairo.LinearGradient(0, 0, 0, 420)
        g.add_color_stop_rgba(0, 0.04, 0.05, 0.10, 0.85)
        g.add_color_stop_rgba(1, 0.04, 0.05, 0.10, 0.0)
        ctx.rectangle(0, 0, W, 420)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, "最後の巨大ドミノまで", W / 2, 150, 76, sw=14)
        text(ctx, "倒れきる？", W / 2, 280, 118, rgb=GOLD, sw=18)
        text(ctx, f"ドミノ {min(fr['fell'], N)} / {N}", W / 2, 1720, 60, sw=12)
        if m_age is not None and not over:
            hx_s = (res["hand"][0] + 0.2 * hs[-1] - cam_x) * cam_s + W / 2
            hy_s = FLOOR_Y - 0.95 * hs[-1] * cam_s
            k2 = min(1.0, m_age / 0.15)
            text(ctx, "ストップ!!", min(W - 230, max(230, hx_s)), hy_s, 92 * k2, rgb=(1, 0.95, 0.3), sw=16)
        if over and fail:
            k = min(1.0, after / 0.25)
            if miss and res["macho_t"] is not None:
                text(ctx, "止められた…", W / 2, 900, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
                text(ctx, "鐘まであと少しだったのに…", W / 2, 1030, 70, sw=12)
            elif miss:
                text(ctx, "届かなかった…", W / 2, 900, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
                text(ctx, "鐘まであと少しだったのに…", W / 2, 1030, 70, sw=12)
            else:
                text(ctx, "止まった…", W / 2, 900, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
                text(ctx, f"あと{N - res['fell']}枚だったのに…", W / 2, 1030, 70, sw=12)
        elif over:
            age = t - end_t
            if age < 0.3:
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.8 * (1 - age / 0.3))
                ctx.fill()

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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['fell']}/{N}枚 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
MIX_GAIN = 0.43  # 通常部分の音量(約 -18dB になるよう調整)
HOLY_GAIN = 0.85
# 「ジングルベル」のサビ(ピアポント作・1857年・パブリックドメイン)
MELODY = [64, 64, 64, 64, 64, 64, 64, 67, 60, 62, 64,
          65, 65, 65, 65, 65, 64, 64, 64, 64, 62, 62, 64, 62, 67,
          64, 64, 64, 64, 64, 64, 64, 67, 60, 62, 64,
          65, 65, 65, 65, 65, 64, 64, 64, 67, 67, 65, 62, 60]
DURS = [1, 1, 2, 1, 1, 2, 1, 1, 1.5, 0.5, 4,
        1, 1, 1.5, 0.5, 1, 1, 1, 0.5, 0.5, 1, 1, 1, 2, 2,
        1, 1, 2, 1, 1, 2, 1, 1, 1.5, 0.5, 4,
        1, 1, 1, 1, 1, 1, 1, 0.5, 0.5, 1, 1, 1, 4]
CHORD = [48] * 11 + [53, 53, 53, 53, 53, 48, 48, 48, 48, 43, 43, 48, 43, 43] + [48] * 11 + \
        [53, 53, 53, 53, 53, 48, 48, 48, 43, 43, 43, 43, 48]
BEAT = 0.24     # 4分音符の長さ(秒)


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def music_box(f, amp):
    t = _t(1.2)
    y = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 6) + 0.2 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 9)
    return amp * y * np.exp(-t * 2.5) * np.minimum(1, t / 0.003)


def piano(f, amp):
    t = _t(1.6)
    y = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * d) for m, a, d in ((1, 1, 2.2), (2, 0.5, 3.5), (3, 0.25, 5), (4, 0.12, 7)))
    return amp * y * np.minimum(1, t / 0.004)


def brass(f, amp, dur=0.7):
    t = _t(dur)
    y = sum(np.sin(2 * np.pi * f * h * t) / h * (0.8 ** h) for h in range(1, 9))
    return amp * y * np.minimum(1, t / 0.025) * np.exp(-t * 2.0)


def strings(f, amp, dur=1.2):
    t = _t(dur)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t)
    y = sum(np.sin(2 * np.pi * f * h * vib * t) / h for h in range(1, 6))
    return amp * y * np.minimum(1, t / 0.06) * np.exp(-t * 1.5)


def timpani(amp, dur=1.8):
    t = _t(dur)
    return amp * (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82 * t)) * np.exp(-t * 2.2) * np.minimum(1, t / 0.005)


def click(h, seed):
    """ドミノが倒れて当たる音。小さいうちは「カチッ」、大きくなるほど低く重い「ドン」。"""
    t = _t(0.3)
    f = 2400 / math.sqrt(h / 30)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    dec = 80 / math.sqrt(h / 30)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * dec) + 0.5 * n * np.exp(-t * dec * 2)) * min(1.0, 0.25 + h / 600)


def mix(*sigs):
    """長さの違う音を、短いほうを無音で伸ばして重ねる。"""
    out = np.zeros(max(len(x) for x in sigs))
    for x in sigs:
        out[:len(x)] += x
    return out


def note_sound(i_dom, f, root, amp):
    """ドミノが大きくなるほど楽器が豪華になる:オルゴール → ピアノ → ブラス → オーケストラ。"""
    if i_dom < 20:
        return music_box(f * 2, amp)
    if i_dom < 40:
        return mix(piano(f, amp), piano(midi_hz(root), amp * 0.35))
    if i_dom < N1:
        return mix(piano(f, amp * 0.7), brass(f, amp * 0.6), strings(midi_hz(root), amp * 0.4))
    return mix(brass(f, amp * 0.9, 1.0), strings(f, amp * 0.6, 1.5), brass(midi_hz(root), amp * 0.6, 1.0), timpani(amp * 0.6))


def bell_sound(amp):
    """大きな鐘の「ゴーン」。"""
    t = _t(4.0)
    f = 110.0
    y = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * d) for m, a, d in ((0.5, 0.6, 0.6), (1, 1, 0.8), (2.0, 0.6, 1.2), (2.76, 0.5, 1.6), (5.4, 0.3, 2.5)))
    return amp * y * np.minimum(1, t / 0.003)


def whoosh(dur=0.35):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(7)
    x = rng.standard_normal(n)
    # 高い音から低い音へ流れる風切り音(簡易バンドパスを時間で動かす)
    out = np.zeros(n)
    y1 = y2 = 0.0
    for i in range(n):
        f = 3000 - 2400 * t[i] / dur
        a = 2 * math.pi * f / SR
        y1 += a * (x[i] - y1 - y2 * 0.3)
        y2 += a * y1
        out[i] = y2
    env = np.sin(np.pi * t / dur) ** 2
    out = out * env
    return out / (np.max(np.abs(out)) + 1e-9) * 0.6


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    hs = res["hs"]
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)

    def add(sig, t0, gain=1.0):
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out:
            out[i:j] += gain * sig[: j - i]

    note_i = -1
    next_ok = 0.0
    for kind, t, data in events:
        if kind == "hit":   # ドミノが次のドミノに実際に当たった瞬間に鳴らす
            i = data
            add(click(hs[i], i), t)
            if t >= next_ok:   # 前の音の長さが経っていたら、曲が1音進む(ドミノが速く倒れても本来のテンポ)
                note_i += 1
                m = note_i % len(MELODY)
                add(note_sound(i, midi_hz(MELODY[m]), CHORD[m], 0.6), t)
                next_ok = t + DURS[m] * BEAT - 0.01
        elif kind == "bell":
            add(bell_sound(1.2), t)
            for m_, a in ((48, 0.7), (55, 0.5), (60, 0.6), (64, 0.5), (67, 0.4)):   # 最後のジャーン
                add(mix(brass(midi_hz(m_), a, 2.0), strings(midi_hz(m_), a * 0.6, 2.5)), t + 0.05)
            add(timpani(1.0, 2.5), t)
        elif kind == "macho":   # シュッ!(登場)
            add(whoosh(), t, 0.9)
        elif kind == "catch":   # ガシッ!(受け止め)+ ジャン!
            add(click(hs[-1], N + 1), t, 1.3)
            add(timpani(0.9, 1.2), t)
            for m_ in (50, 57, 62):
                add(brass(midi_hz(m_), 0.5, 0.45), t + 0.02)
        elif kind == "land" and not any(e[0] == "catch" for e in events):   # 巨大ドミノが床に倒れこむ重い音(鐘に当たったときは鐘の音が主役)
            if not any(e[0] == "bell" for e in events):
                add(click(hs[-1], N), t, 1.2)
                add(timpani(0.8, 1.5), t)
    extra = np.zeros(n_out)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(end_t * SR) + int(1.5 * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += HOLY_GAIN * sig[:m]
    wet = out.copy()
    for d, g in ((0.047, 0.3), (0.079, 0.22), (0.121, 0.15)):   # 広い会場の響き
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * MIX_GAIN
    # 通常部分の平均音量を約 -18dB にそろえる(回によって音数が違うため)
    body = wet[: int((end_t or duration) * SR)]
    rms = np.sqrt(np.mean(body ** 2)) if len(body) else 0
    if rms > 0:
        wet *= min(1.6, 10 ** (-18.0 / 20) / rms)
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
