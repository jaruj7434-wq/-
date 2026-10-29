"""「12個の玉で木を全部こわせる?」うずまきの通路に並んだ木の板を、玉が割っていく物理ショートを生成する。

参考動画(Will the ball break through all the wood?)の動き・見た目・音を分析して再現したもの:
- 5重のうずまきの壁。通路には放射状に並んだ木の板(432枚)。中心には小さな部屋。
- 玉はうずまきの外側の口の真上から落ちてきて通路に入る。板に当たると板は割れて玉は突き抜けるが、そのたびに少し遅くなる。
  盤面は真上から見た水平な台で、転がり抵抗でも少しずつ遅くなり、勢いがなくなった玉は薄くなって消える(中心の小部屋に小さな玉として集まる)。
- 前の玉が全部消えたら次の波が落ちてくる:黄1 → 赤2 → 青4 → 黄5(計12個)。
- 板が壊れるたびに短い木の「コッ」という音。音の高さは玉の位置(角度)で上下する。BGMなし。
- 玉の動きは重力・反発・衝突の物理のまま(ねらい・補正なし)。
12個の玉で432枚すべて壊せば成功(天使)、玉が尽きたら失敗(幽霊)。

使い方:
    python wood.py search [--want fail|success] [-n 200]
    python wood.py render --seed N
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

CX, CY = 540.0, 930.0
TURNS = 5
R_IN, R_OUT = 70.0, 420.0
TH_END = TURNS * 2 * math.pi
B = (R_OUT - R_IN) / TH_END            # うずまきの広がり(1ラジアンあたり)
LANE = 2 * math.pi * B                 # 通路の幅
N_PLANKS = 432
TH_WOOD0 = 2 * math.pi * 0.35          # 板を並べ始める位置(中心の小部屋は空ける)
TH_WOOD1 = TH_END - 2 * math.pi - 0.35  # 板を並べ終える位置(入口は少し空ける)

BREAK_KEEP = 0.978                     # 板を1枚割ったあとに残る玉の速さの割合
AIR_DAMP = 0.7832                      # 盤面で1秒あたりに残る速さの割合(転がり抵抗)
V_DIE = 200.0                          # これより遅くなった玉は消えていく
FADE = 0.5                             # 消えていく時間(秒)
WALL_E = 1.0                           # 壁の反発係数
BALL_R = 19
GRAVITY = 2600.0
DROP_X = CX + R_OUT - LANE / 2         # 玉はうずまきの外側の口の真上から落ちてくる
DROP_Y = CY - 600
WAVES = [(1, "yellow"), (2, "red"), (4, "blue"), (5, "yellow")]   # 前の玉が全部消えたら次の波
N_BALLS = sum(n for n, _ in WAVES)
WAVE_GAP = 0.6                         # 前の玉が消えてから次の玉が落ちてくるまで
DROP_EVERY = 0.35                      # 同じ波の玉どうしの間隔
FAIL_WAIT = 0.8                        # 最後の玉が消えてから失敗確定まで
MAX_T = 90.0
OUTRO = 2.5

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


def r_of(th):
    return R_IN + B * th


def phi_of(th):
    """うずまきのパラメータ th の画面上の角度。外側の端(th=TH_END)が右(0)、内側へ進むと時計回り。"""
    return TH_END - th


def wall_pt(th, dr=0.0):
    r, p = r_of(th) + dr, phi_of(th)
    return CX + r * math.cos(p), CY + r * math.sin(p)


def outside_board(x, y):
    """うずまきの一番外側の壁よりも外(=空中)にいるか。"""
    dx, dy = x - CX, y - CY
    phi = math.atan2(dy, dx) % (2 * math.pi)
    return math.hypot(dx, dy) > R_OUT - B * phi + 2


def board_physics(body, gravity, damping, dt):
    """うずまきの外(空中)では重力で落ちる。盤面は真上から見た水平な台なので重力は効かず、転がり抵抗で少しずつ遅くなる。"""
    x, y = body.position
    if outside_board(x, y):
        pymunk.Body.update_velocity(body, gravity, 1.0, dt)
    else:
        pymunk.Body.update_velocity(body, (0, 0), AIR_DAMP ** dt, dt)


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 20
        self.space = sp
        st = sp.static_body
        # うずまきの壁
        n = int(TH_END / 0.025)
        pts = [wall_pt(TH_END * k / n) for k in range(n + 1)]
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            s = pymunk.Segment(st, a, b, 3)
            s.elasticity, s.friction = WALL_E, 0.0
            # つなぎ目で玉が変な向きにはじかれないよう、となりの線分を教えておく
            s.set_neighbors(pts[max(i - 1, 0)], pts[min(i + 2, n)])
            sp.add(s)
        # 木の板(放射状。内側の壁から外側の壁まで)
        self.planks = []
        self.plank_of = {}
        for k in range(N_PLANKS):
            th = TH_WOOD0 + (TH_WOOD1 - TH_WOOD0) * (k + 0.5) / N_PLANKS
            a = wall_pt(th, 8)
            b = wall_pt(th + 2 * math.pi, -8)
            s = pymunk.Segment(st, a, b, 3)
            s.elasticity, s.friction = 1.0, 0.0
            s.collision_type = 4
            sp.add(s)
            self.plank_of[s] = k
            self.planks.append({"th": th, "alive": True, "shape": s,
                                "tint": float(self.rng.uniform(-0.06, 0.06))})
        sp.on_collision(1, 4, begin=self._hit)
        self.to_break = []
        self.breaking = set()
        self.balls = []
        self.events = []
        self.cleared = 0
        self.t = 0.0
        self.result, self.result_t = None, None
        self.wave = -1
        self.queue = []
        self.next_wave_t = 0.5
        self.dropped = 0
        self.all_gone_t = None

    def _hit(self, arb, space, data):
        """玉が板に当たったら、板は割れて玉は突き抜ける。割るのに使った分だけ玉は遅くなる。"""
        if self.result is not None:
            return
        arb.process_collision = False
        k = self.plank_of.get(arb.shapes[1])
        body = arb.shapes[0].body
        if k is not None and self.planks[k]["alive"] and k not in self.breaking:
            self.breaking.add(k)
            self.to_break.append((k, body, body.velocity.length))
            body.velocity = body.velocity * BREAK_KEEP

    def drop(self, col):
        m = 1.0
        b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, BALL_R))
        b.position = (DROP_X + self.rng.uniform(-8, 8), DROP_Y)
        b.velocity = (self.rng.uniform(-10, 10), 0)
        b.velocity_func = board_physics
        c = pymunk.Circle(b, BALL_R)
        c.elasticity, c.friction = 1.0, 0.0
        c.collision_type = 1
        self.space.add(b, c)
        bid = self.dropped
        self.dropped += 1
        self.balls.append({"id": bid, "body": b, "shape": c, "col": col})
        self.events.append(("drop", self.t, (bid, col)))

    def step(self, dt):
        self.t += dt
        if self.result is None and not self.balls and not self.queue and self.next_wave_t is not None \
                and self.t >= self.next_wave_t and self.wave + 1 < len(WAVES):
            self.wave += 1
            n_b, col = WAVES[self.wave]
            self.queue = [(self.t + j * DROP_EVERY, col) for j in range(n_b)]
            self.next_wave_t = None
        while self.queue and self.queue[0][0] <= self.t:
            self.drop(self.queue.pop(0)[1])
        self.to_break = []
        self.breaking = set()
        self.space.step(dt)
        for k, body, speed in self.to_break:
            p = self.planks[k]
            if not p["alive"]:
                continue
            p["alive"] = False
            self.space.remove(p["shape"])
            self.cleared += 1
            x, y = body.position
            self.events.append(("break", self.t, (k, x, y, speed)))
        # 勢いがなくなった玉(と画面の外へ落ちた玉)は消える
        for bl in list(self.balls):
            b = bl["body"]
            x, y = b.position
            slow = b.velocity.length < V_DIE and not outside_board(x, y)
            if slow or y > H + 200 or x < -200 or x > W + 200:
                self.space.remove(b, bl["shape"])
                self.balls.remove(bl)
                self.events.append(("die", self.t, (bl["id"], x, y, bl["col"])))
        if self.result is None:
            if self.cleared == N_PLANKS:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif not self.balls and not self.queue:
                if self.wave + 1 < len(WAVES):
                    if self.next_wave_t is None:
                        self.next_wave_t = self.t + WAVE_GAP
                else:
                    if self.all_gone_t is None:
                        self.all_gone_t = self.t
                    if self.t >= self.all_gone_t + FAIL_WAIT:
                        self.result, self.result_t = "fail", self.t
                        self.events.append(("fail", self.t, None))
            if self.result is None and self.t >= MAX_T:
                self.result, self.result_t = "fail", self.t


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "cleared": g.cleared, "dropped": g.dropped,
                           "balls": [(b["id"], b["body"].position.x, b["body"].position.y, b["col"])
                                     for b in g.balls],
                           "alive": [p["alive"] for p in g.planks]})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "cleared": g.cleared, "planks": g.planks}


def score(seed):
    r = simulate(seed)
    waves = [sum(1 for e in r["events"] if e[0] == "break" and e[1] <= t) for t in
             [e[1] for e in r["events"] if e[0] == "drop"]]
    return seed, r["result"], r["result_t"], r["cleared"], waves


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "fail":
        for seed, _, _, c, _ in sorted([r for r in rs if r[1] == "fail"], key=lambda r: -r[3])[:15]:
            print(f"seed={seed:4d}  {c}/{N_PLANKS} 枚で玉が尽きた")
    else:
        for seed, _, rt, _, _ in sorted(succ, key=lambda r: -r[2])[:15]:
            print(f"seed={seed:4d}  全部こわした {rt:5.2f}秒")


# ---------------------------------------------------------------- 描画
OFFSET_Y = 80                          # 物理の座標を画面上で少し下にずらして表示する
BG = (0.02, 0.027, 0.047)
STEEL = (0.62, 0.72, 0.88)
WOOD = (0.79, 0.63, 0.48)
BALL_COL = {"yellow": (1.0, 0.84, 0.22), "red": (1.0, 0.32, 0.30), "blue": (0.36, 0.66, 1.0)}
GOLD = (1, 0.86, 0.2)
MONO = "JetBrains Mono"
HUB_R = 46                             # 中心の小部屋(消えた玉が小さくなって集まる)


def plank_quad(th):
    """板1枚の4すみ(内側の壁から外側の壁まで、幅の細い長方形)。"""
    ax, ay = wall_pt(th, 4)
    bx, by = wall_pt(th + 2 * math.pi, -4)
    dx, dy = bx - ax, by - ay
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln * 3.6, dx / ln * 3.6
    return [(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)]


def draw_walls(ctx):
    n = int(TH_END / 0.02)
    lines = [[wall_pt(TH_END * k / n) for k in range(n + 1)]]
    for width, alpha in ((12, 0.06), (4, 0.9)):   # うっすら光る → 細い芯の線
        for pts in lines:
            ctx.new_path()
            ctx.move_to(*pts[0])
            for p in pts[1:]:
                ctx.line_to(*p)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.set_source_rgba(*STEEL, alpha)
            ctx.set_line_width(width)
            ctx.stroke()
    # うずまきの外側の端の白い点
    ctx.new_path()
    ctx.arc(CX + R_OUT, CY, 6, 0, 2 * math.pi)
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    # 中心の小部屋
    ctx.new_path()
    ctx.arc(CX, CY, HUB_R, 0, 2 * math.pi)
    ctx.set_source_rgb(0.01, 0.015, 0.03)
    ctx.fill_preserve()
    ctx.set_source_rgba(*STEEL, 0.9)
    ctx.set_line_width(3)
    ctx.stroke()


def draw_planks(ctx, planks, alive):
    for p, a in zip(planks, alive):
        if not a:
            continue
        q = p["quad"]
        ctx.new_path()
        ctx.move_to(*q[0])
        for c in q[1:]:
            ctx.line_to(*c)
        ctx.close_path()
        tint = p["tint"]
        ctx.set_source_rgb(WOOD[0] + tint, WOOD[1] + tint, WOOD[2] + tint * 0.8)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.25, 0.15, 0.08, 0.9)
        ctx.set_line_width(1.6)
        ctx.stroke()


def draw_ball(ctx, x, y, col, trail, fade=1.0):
    r, g_, b = col
    ctx.push_group()
    for j, (tx, ty) in enumerate(trail):   # 残像(だんだん薄く・小さく)
        a = (j + 1) / (len(trail) + 1)
        ctx.new_path()
        ctx.arc(tx, ty, BALL_R * (0.45 + 0.5 * a), 0, 2 * math.pi)
        ctx.set_source_rgba(r, g_, b, 0.22 * a)
        ctx.fill()
    halo = cairo.RadialGradient(x, y, BALL_R * 0.6, x, y, BALL_R * 3.2)
    halo.add_color_stop_rgba(0, r, g_, b, 0.45)
    halo.add_color_stop_rgba(1, r, g_, b, 0.0)
    ctx.new_path()
    ctx.arc(x, y, BALL_R * 3.2, 0, 2 * math.pi)
    ctx.set_source(halo)
    ctx.fill()
    body = cairo.RadialGradient(x - BALL_R * 0.35, y - BALL_R * 0.4, BALL_R * 0.1, x, y, BALL_R)
    body.add_color_stop_rgb(0, min(1, r + 0.55), min(1, g_ + 0.55), min(1, b + 0.55))
    body.add_color_stop_rgb(0.55, r, g_, b)
    body.add_color_stop_rgb(1, r * 0.55, g_ * 0.55, b * 0.55)
    ctx.new_path()
    ctx.arc(x, y, BALL_R, 0, 2 * math.pi)
    ctx.set_source(body)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.85)
    ctx.set_line_width(2)
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(fade)


def mono(ctx, s, x, y, size, rgb, alpha=1.0):
    ctx.select_font_face(MONO, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    ext = ctx.text_extents(s)
    ctx.move_to(x - ext.width / 2 - ext.x_bearing, y)
    ctx.set_source_rgba(*rgb, alpha)
    ctx.show_text(s)


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    planks = res["planks"]
    for p in planks:
        p["quad"] = plank_quad(p["th"])
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"wood_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"wood_{seed}.wav")
    final = os.path.join(OUT_DIR, f"wood_{seed}.mp4")
    rng = np.random.default_rng(seed + 999)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    # 動かない背景と壁は最初に1回だけ描いておく
    static = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    sc = cairo.Context(static)
    vg = cairo.RadialGradient(CX, CY + OFFSET_Y, 200, CX, CY + OFFSET_Y, 1250)
    vg.add_color_stop_rgb(0, 0.035, 0.045, 0.075)
    vg.add_color_stop_rgb(1, *BG)
    sc.set_source(vg)
    sc.paint()
    sc.translate(0, OFFSET_Y)
    draw_walls(sc)
    wood_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    alive_drawn = None

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    angels = AngelShow(W, H, seed) if result == "success" else None
    shards, trails, dying, hub = [], {}, [], []
    ev_i = 0
    prev_t = 0.0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        dt = t - prev_t
        prev_t = t
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "break":
                k, x, y, speed = data
                q = planks[k]["quad"]
                mx, my = (q[0][0] + q[2][0]) / 2, (q[0][1] + q[2][1]) / 2
                for _ in range(6):   # 木くず
                    a = rng.uniform(0, 2 * math.pi)
                    v = rng.uniform(60, 260)
                    shards.append([mx + rng.uniform(-14, 14), my + rng.uniform(-14, 14),
                                   math.cos(a) * v, math.sin(a) * v, rng.uniform(0, math.pi),
                                   rng.uniform(-12, 12), rng.uniform(4, 11), et])
            elif kind == "die":   # 勢いがなくなった玉は、その場で薄くなって消える
                bid, x, y, col = data
                dying.append([et, x, y, col, trails.pop(bid, [])])
                hub.append([col, rng.uniform(0, 2 * math.pi), rng.uniform(0, HUB_R - 14), rng.uniform(0, 100)])
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0

        ctx.set_source_surface(static, 0, 0)
        ctx.paint()
        if fr["alive"] != alive_drawn:   # 板が割れたときだけ描き直す
            wood_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            wc = cairo.Context(wood_surf)
            wc.translate(0, OFFSET_Y)
            draw_planks(wc, planks, fr["alive"])
            alive_drawn = fr["alive"]
        ctx.set_source_surface(wood_surf, 0, 0)
        ctx.paint()
        ctx.save()
        ctx.translate(0, OFFSET_Y)
        # 木くず
        keep = []
        for sh in shards:
            age = t - sh[7]
            if age > 0.8:
                continue
            sh[0] += sh[2] * dt
            sh[1] += sh[3] * dt
            sh[2] *= 0.93
            sh[3] *= 0.93
            sh[4] += sh[5] * dt
            ctx.save()
            ctx.translate(sh[0], sh[1])
            ctx.rotate(sh[4])
            ctx.rectangle(-sh[6] / 2, -1.6, sh[6], 3.2)
            ctx.set_source_rgba(*WOOD, 1 - age / 0.8)
            ctx.fill()
            ctx.restore()
            keep.append(sh)
        shards = keep
        # 中心の小部屋に集まった小さな玉(ぷるぷる動く)
        for col, a0, r0, ph in hub:
            a = a0 + 0.6 * math.sin(t * 1.3 + ph)
            rr = r0 + 3 * math.sin(t * 5.1 + ph)
            hx = CX + rr * math.cos(a) + 1.5 * math.sin(t * 17 + ph)
            hy = CY + rr * math.sin(a) + 1.5 * math.cos(t * 19 + ph)
            ctx.new_path()
            ctx.arc(hx, hy, 6, 0, 2 * math.pi)
            ctx.set_source_rgb(*BALL_COL[col])
            ctx.fill()
        # 消えていく玉
        keep = []
        for d in dying:
            age = t - d[0]
            if age < FADE:
                k = 1 - age / FADE
                draw_ball(ctx, d[1], d[2], BALL_COL[d[3]], d[4][-int(8 * k):] if k > 0.15 else [], fade=k)
                keep.append(d)
        dying = keep
        # 玉
        for bid, x, y, col in fr["balls"]:
            tr = trails.setdefault(bid, [])
            draw_ball(ctx, x, y, BALL_COL[col], tr)
            tr.append((x, y))
            del tr[:-10]
        ctx.restore()

        # ふつうの文字(参考動画と同じ等幅のカウンター)
        mono(ctx, f"WOOD CLEARED {fr['cleared']} / {N_PLANKS}", W / 2, 1585, 40, (0.62, 0.64, 0.68))
        # 残りの玉(まだ落ちてきていない玉)
        rest = [col for n_b, col in WAVES for _ in range(n_b)][fr["dropped"]:]
        for j, col in enumerate(rest):
            x = W / 2 + (j - (len(rest) - 1) / 2) * 40
            ctx.new_path()
            ctx.arc(x, 1650, 11, 0, 2 * math.pi)
            ctx.set_source_rgba(*BALL_COL[col], 0.85)
            ctx.fill()
        if angels is not None and over:
            angels.draw(ctx, t - end_t)

        # 上の帯
        g = cairo.LinearGradient(0, 0, 0, 400)
        g.add_color_stop_rgba(0, 0.01, 0.015, 0.03, 0.96)
        g.add_color_stop_rgba(0.8, 0.01, 0.015, 0.03, 0.85)
        g.add_color_stop_rgba(1, 0.01, 0.015, 0.03, 0.0)
        ctx.rectangle(0, 0, W, 400)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, f"{N_BALLS}個の玉で木を全部", W / 2, 165, 82, sw=14)
        text(ctx, "こわせる？", W / 2, 295, 124, rgb=GOLD, sw=18)
        text(ctx, "Will the ball break through all the wood?", W / 2, 360, 36, rgb=(0.85, 0.85, 0.9), sw=8)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "玉が尽きた…", W / 2, 1000, 140 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{N_PLANKS - res['cleared']}枚だったのに…", W / 2, 1130, 72, sw=12)
        elif over:
            age = t - end_t
            if age < 0.35:   # 参考動画のような白いフラッシュ
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.85 * (1 - age / 0.35))
                ctx.fill()
            k = min(1.0, age / 0.25)
            text(ctx, "全部こわした！", W / 2, 1000, 130 * (1.6 - 0.6 * k), rgb=GOLD, sw=20)

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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['cleared']}/{N_PLANKS}枚 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
MIX_GAIN = 0.72  # 通常部分の音量(約 -18dB になるよう調整)
HOLY_GAIN = 0.85
F_LO, F_HI = 300.0, 1000.0             # 木の音の高さの範囲(参考動画と同じくらい)


def wood_tick(freq, amp):
    """木の板が割れる「コッ」という短い音(基音+少しずれた倍音+打った瞬間のカチッ)。"""
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * freq * t) * np.exp(-t * 90)
         + 0.32 * np.sin(2 * np.pi * freq * 3.4 * t) * np.exp(-t * 160)
         + 0.12 * np.sin(2 * np.pi * freq * 6.1 * t) * np.exp(-t * 260))
    click = np.random.default_rng(int(freq)).normal(0, 1, n) * np.exp(-t * 900) * 0.25
    return amp * (y + click) * np.minimum(1, t / 0.0006)


def tick_freq(x, y):
    """玉の位置で音の高さが上下する(うずまきを1周するあいだに 低→高→低)。"""
    ang = (math.atan2(y - CY, x - CX) / (2 * math.pi)) % 1.0
    tri = 1 - abs(2 * ang - 1)
    return F_LO * (F_HI / F_LO) ** tri


def chime(freq, dur, amp):
    t = np.arange(int(dur * SR)) / SR
    y = np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2.01 * t) * np.exp(-t * 5)
    return amp * y * np.exp(-t * 3) * np.minimum(1, t / 0.003)


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 3) * SR)
    out = np.zeros((n_out, 2))

    def add(sig, t0, pan=0.0):
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        out[i:j, 0] += sig[: j - i] * math.sqrt(0.5 * (1 - pan))
        out[i:j, 1] += sig[: j - i] * math.sqrt(0.5 * (1 + pan))

    for kind, t, data in events:
        if kind == "break" and (end_t is None or t <= end_t):
            k, x, y, speed = data
            amp = 0.35 + 0.65 * min(1.0, speed / 900)   # 速い玉ほど強い音
            add(wood_tick(tick_freq(x, y), 0.5 * amp), t, pan=(x - CX) / (R_OUT * 1.6))
    extra = np.zeros_like(out)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m, None]
        sad_t = end_t + SCARE_DUR + 0.1
        for k, m_ in enumerate((64, 63, 62, 61)):
            add(chime(midi_hz(m_), 0.8, 0.35), sad_t + k * 0.42)
    elif end_t is not None:
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += HOLY_GAIN * sig[:m, None]
    wet = out.copy()
    for d, g in ((0.023, 0.22), (0.041, 0.16), (0.067, 0.1)):   # 小さな部屋の響き
        k = int(d * SR)
        wet[k:, 0] += out[:-k, 1] * g
        wet[k:, 1] += out[:-k, 0] * g
    wet = wet[: int(duration * SR)]
    # 通常部分は軽く圧縮して聞こえやすくし、叫び声との差は約10dBに抑える
    wet = np.tanh(2.5 * wet / max(1e-9, np.max(np.abs(wet)))) / np.tanh(2.5) * MIX_GAIN
    wet = np.clip(wet + (0.95 if fail else 1.0) * extra[: len(wet)], -0.98, 0.98)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
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
