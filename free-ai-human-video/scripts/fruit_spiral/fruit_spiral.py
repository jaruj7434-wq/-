"""「6つの刃物でフルーツを全部切れる?」うずまきの通路に並んだフルーツを、弱い刃物から強い刃物へ順番に切っていく物理ショート。

18本目(ガラスの板こわし・glass_spiral.py)と同じうずまきのコースで、ガラスの板をフルーツにしたもの。
刃物は弱い順に1本ずつ、くるくる回りながら進む:バターナイフ → ペティナイフ → 三徳包丁 → 出刃包丁 → 中華包丁 → 日本刀。
  後の刃物ほど速く打ち出され、切っても遅くなりにくい。勢いがなくなった刃物は消える。
  (当たり判定は回転する刃物を囲む円。動きは自然な物理のまま)
- フルーツは切られると真っ二つに分かれて飛び、果汁が飛び散る。「シュパッ」という音(高さは刃物の位置で変わる)。
- 全部切れば成功(フルーツがあふれる「フルーツフィーバー」演出)、刃物が尽きたら失敗(幽霊)。

使い方:
    python fruit_spiral.py search [--want fail|success] [-n 200]
    python fruit_spiral.py render --seed N
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glass_drum"))
import blades as GD  # noqa: E402   刃物の絵(バターナイフ〜日本刀)
import fruits as FR  # noqa: E402   フルーツの絵
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
import ball_voice as BV  # noqa: E402   ボールが落ちるときの掛け声と効果音
import fruit_fever as JP  # noqa: E402   成功したときの「フルーツフィーバー」演出(映像と音)

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
N_PLANKS = int(os.environ.get("N_PLANKS", 160))   # フルーツの数
TH_WOOD0 = 2 * math.pi * 0.35          # 板を並べ始める位置(中心の小部屋は空ける)
TH_WOOD1 = TH_END - 2 * math.pi - 0.35  # 板を並べ終える位置(入口は少し空ける)

# ボールの種類ごとに、フルーツを1個つぶしたあとに残る速さの割合(強いボールほど減りにくい)
KEEP = [float(x) for x in os.environ.get("KEEP", "0.916,0.929,0.942,0.955,0.965,0.9687").split(",")]
# ボールの種類ごとに、落とすときに下向きに足す速さ(px/秒)。後のボールほど速く打ち出される
V0 = [float(x) for x in os.environ.get("V0", "0,250,500,800,1100,1450").split(",")]
AIR_DAMP = 0.7832                      # 盤面で1秒あたりに残る速さの割合(転がり抵抗)
V_DIE = 200.0                          # これより遅くなった玉は消えていく
FADE = 0.5                             # 消えていく時間(秒)
WALL_E = 1.0                           # 壁の反発係数
BALL_R = 19
GRAVITY = 2600.0
DROP_X = CX + R_OUT - LANE / 2         # 玉はうずまきの外側の口の真上から落ちてくる
DROP_Y = CY - 600
WAVES = [(1, k) for k in range(6)]   # 前のボールが消えたら次のボール(弱い順に1個ずつ)
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
                                "tint": float(self.rng.uniform(-0.06, 0.06)),
                                "fruit": int(self.rng.integers(0, len(FR.KINDS))), "rot": float(self.rng.uniform(-0.4, 0.4))})
        sp.on_collision(1, 4, begin=self._hit)
        self.to_break = []
        self.breaking = set()
        self.kind_of = {}
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
            body.velocity = body.velocity * KEEP[self.kind_of.get(body, 0)]

    def drop(self, col):
        m = 1.0
        b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, BALL_R))
        b.position = (DROP_X + self.rng.uniform(-8, 8), DROP_Y)
        b.velocity = (self.rng.uniform(-10, 10), V0[col])   # ボールごとに打ち出す速さ(後のボールほど速い)
        b.velocity_func = board_physics
        c = pymunk.Circle(b, BALL_R)
        c.elasticity, c.friction = 1.0, 0.0
        c.collision_type = 1
        self.space.add(b, c)
        bid = self.dropped
        self.dropped += 1
        self.balls.append({"id": bid, "body": b, "shape": c, "col": col})
        self.kind_of[b] = col
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
            extra = OUTRO + SCARE_DUR if g.result == "fail" else JP.DURATION
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
WOOD = (0.75, 0.9, 1.0)   # ガラスの色(名前は9本目のまま)
BALL_COL = {k: GD.BALLS[k][5] for k in range(6)}
SHORT_NAMES = GD.SHORT   # 下に並べるときの短い名前
VIS_R = [1.3, 1.35, 1.35, 1.4, 1.4, 1.15]   # 見た目の大きさ(日本刀は長いので少し小さめ)
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


def draw_walls(ctx, zoom=1.0):
    n = int(TH_END / 0.02)
    lines = [[wall_pt(TH_END * k / n) for k in range(n + 1)]]
    lw = 1 / math.sqrt(zoom)   # 寄ったときに線が太くなりすぎないように
    for width, alpha in ((12 * lw, 0.06), (4 * lw, 0.9)):   # うっすら光る → 細い芯の線
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


def plank_mid(th):
    (ax, ay), (bx, by) = wall_pt(th, 0), wall_pt(th + 2 * math.pi, 0)
    return (ax + bx) / 2, (ay + by) / 2


FRUIT_R = LANE * 0.36   # フルーツの大きさ(通路の幅に合わせる)


def draw_planks(ctx, planks, alive, zoom=1.0):
    """うずまきに並んだフルーツ(奥=内側から描いて、手前のフルーツが上に重なるように)。"""
    for p, a in zip(planks, alive):
        if not a:
            continue
        x, y = p["mid"]
        FR.draw_fruit(ctx, p["fruit"], x, y, FRUIT_R, p["rot"])


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
        p["mid"] = plank_mid(p["th"])
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"fruit_spiral_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"fruit_spiral_{seed}.wav")
    final = os.path.join(OUT_DIR, f"fruit_spiral_{seed}.mp4")
    rng = np.random.default_rng(seed + 999)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    # 動かない背景は最初に1回だけ描いておく(壁とフルーツはカメラの寄りに合わせて毎回描く)
    static = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    sc = cairo.Context(static)
    vg = cairo.RadialGradient(CX, CY + OFFSET_Y, 200, CX, CY + OFFSET_Y, 1250)
    vg.add_color_stop_rgb(0, 0.035, 0.045, 0.075)
    vg.add_color_stop_rgb(1, *BG)
    sc.set_source(vg)
    sc.paint()
    # カメラ: 残っているフルーツがいつも同じくらいの大きさに見えるよう、割れるにつれて寄っていく。
    # 新しいボールが落ちてくるときは、そのボールが画面に入るように少し引き、ボールが内側へ進むにつれてまた寄る。
    cam_r = R_OUT + 30

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    ending = None if fail else JP.FruitFever(W, H, seed, CX, CY + OFFSET_Y, main="全部切った!!", count=f"{N_PLANKS} / {N_PLANKS}")
    shards, trails, dying, hub = [], {}, [], []
    spin, embers = {}, []
    stains = []   # 床に残る果汁のしみ
    halves = []   # 真っ二つに切れたフルーツ
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
                mx, my = planks[k]["mid"]
                fk = planks[k]["fruit"]
                juice, skin = FR.KINDS[fk][2], FR.KINDS[fk][1]
                cut = math.atan2(my - CY, mx - CX) + math.pi / 2   # 刃物が進む向き(うずまきの接線)で切れる
                halves.append([mx, my, fk, cut, et, rng.uniform(-6, 6), rng.uniform(90, 170)])
                for j_ in range(14):   # 果汁のしずくと、皮のかけら
                    a = rng.uniform(0, 2 * math.pi)
                    v = rng.uniform(80, 420)
                    col = skin if j_ < 2 else juice
                    shards.append([mx + rng.uniform(-8, 8), my + rng.uniform(-8, 8),
                                   math.cos(a) * v, math.sin(a) * v, rng.uniform(0, math.pi),
                                   rng.uniform(-12, 12), rng.uniform(3, 9) * (1.6 if j_ < 4 else 1.0), et, col, j_ < 4])
                stains.append([mx, my, juice, et, rng.uniform(0.8, 1.3), rng.uniform(0, math.pi)])
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

        # カメラの寄り具合
        alive_k = [k for k, a in enumerate(fr["alive"]) if a]
        target = (r_of(planks[alive_k[-1]]["th"] + 2 * math.pi) + 45) if alive_k else cam_r
        for _, bx, by, _ in fr["balls"]:
            if outside_board(bx, by):
                target = R_OUT + 30
            else:
                target = max(target, math.hypot(bx - CX, by - CY) + BALL_R + 70)
        target = min(R_OUT + 30, max(150.0, target))
        cam_r += (target - cam_r) * (1 - math.exp(-dt / 0.35))
        zoom = (R_OUT + 30) / cam_r

        ctx.set_source_surface(static, 0, 0)
        ctx.paint()
        ctx.save()
        ctx.translate(CX, CY + OFFSET_Y)
        ctx.scale(zoom, zoom)
        ctx.translate(-CX, -CY)
        draw_walls(ctx, zoom)
        draw_planks(ctx, planks, fr["alive"], zoom)
        # 真っ二つに切れたフルーツ(切り口を見せながら左右に分かれ、回って薄くなる)
        keep = []
        for hv in halves:
            age = t - hv[4]
            if age > 0.7:
                continue
            hx, hy, fk, cut, _, sp_, sep = hv
            fa = 1 - age / 0.7
            for sgn in (-1, 1):
                d = sep * (1 - math.exp(-age * 6)) / 6 * 6
                px = hx + sgn * d * math.cos(cut + math.pi / 2)
                py = hy + sgn * d * math.sin(cut + math.pi / 2)
                ctx.save()
                ctx.translate(px, py)
                ctx.rotate(cut + sgn * sp_ * age * 0.3)
                ctx.rectangle(-FRUIT_R * 1.4, 0 if sgn > 0 else -FRUIT_R * 1.4, FRUIT_R * 2.8, FRUIT_R * 1.4)
                ctx.clip()
                ctx.push_group()
                FR.draw_fruit(ctx, fk, 0, 0, FRUIT_R, -cut)
                ctx.scale(1.0, 0.3)   # 切り口(果汁の色)
                ctx.arc(0, 0, FRUIT_R * 0.95, 0, 2 * math.pi)
                ctx.set_source_rgb(*FR.KINDS[fk][2])
                ctx.fill()
                ctx.pop_group_to_source()
                ctx.paint_with_alpha(fa)
                ctx.restore()
            if age < 0.12:   # 切った瞬間の光の線
                ctx.save()
                ctx.translate(hx, hy)
                ctx.rotate(cut)
                ctx.scale(1.0, 0.06)
                g = cairo.RadialGradient(0, 0, 0, 0, 0, FRUIT_R * 2.2)
                g.add_color_stop_rgba(0, 1, 1, 1, 0.95 * (1 - age / 0.12))
                g.add_color_stop_rgba(1, 1, 1, 1, 0)
                ctx.set_source(g)
                ctx.arc(0, 0, FRUIT_R * 2.2, 0, 2 * math.pi)
                ctx.fill()
                ctx.restore()
            keep.append(hv)
        halves = keep
        # 床に残る果汁のしみ(だんだん薄くなる)
        keep = []
        for st_ in stains:
            age = t - st_[3]
            if age > 2.5:
                continue
            al = 0.45 * (1 - age / 2.5)
            sx, sy, jc, _, sc_, rot_ = st_
            ctx.save()
            ctx.translate(sx, sy)
            ctx.rotate(rot_)
            ctx.scale(1.0, 0.75)
            rr = FRUIT_R * sc_ * min(1.0, 0.5 + age * 4)
            ctx.arc(0, 0, rr, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgba(*jc, al)
            ctx.fill()
            keep.append(st_)
        stains = keep
        # 果汁のしずくと皮のかけら
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
            sz = sh[6]
            fa = 1 - age / 0.8
            if sh[9]:   # 皮のかけら(三角っぽい)
                ctx.move_to(-sz / 2, -sz / 3)
                ctx.line_to(sz / 2, -sz / 5)
                ctx.line_to(0, sz / 2)
                ctx.close_path()
                ctx.set_source_rgba(*sh[8], 0.95 * fa)
                ctx.fill()
            else:       # 果汁のしずく(進む向きに少し伸びる)
                ctx.scale(1.6, 1.0)
                ctx.arc(0, 0, sz / 2, 0, 2 * math.pi)
                ctx.set_source_rgba(*sh[8], 0.85 * fa)
                ctx.fill()
                ctx.arc(-sz * 0.12, -sz * 0.12, sz * 0.15, 0, 2 * math.pi)
                ctx.set_source_rgba(1, 1, 1, 0.6 * fa)
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
                GD.draw_ball(ctx, d[3], d[1], d[2], 0.0, BALL_R * 1.15 * (0.6 + 0.4 * k), t, k, None)
                keep.append(d)
        dying = keep
        # 玉
        for bid, x, y, col in fr["balls"]:
            tr = trails.setdefault(bid, [])
            if tr:   # 転がった距離のぶん回す
                spin[bid] = spin.get(bid, 0.0) + math.hypot(x - tr[-1][0], y - tr[-1][1]) / (BALL_R * 1.2)
            for j in range(1, len(tr)):   # 刃物が通ったあとの細い光の筋(だんだん細く・薄く)
                a = j / len(tr)
                ctx.move_to(*tr[j - 1])
                ctx.line_to(*tr[j])
                ctx.set_source_rgba(0.9, 0.95, 1.0, 0.35 * a)
                ctx.set_line_width(1 + 5 * a)
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.stroke()
            if False:   # (火の粉はなし)
                for _ in range(2 if col == 3 else 4):
                    embers.append([x, y, rng.uniform(-80, 80), rng.uniform(-80, 80), t, rng.uniform(6, 13) * (1.5 if col == 5 else 1)])
            GD.draw_ball(ctx, col, x, y, spin.get(bid, 0.0), BALL_R * VIS_R[col], t, 1.0, rng)
            tr.append((x, y))
            del tr[:-10]
        keep = []
        for e in embers:
            age = t - e[4]
            if age < 0.4:
                k = 1 - age / 0.4
                ex, ey = e[0] + e[2] * age, e[1] + e[3] * age
                gg = cairo.RadialGradient(ex, ey, 0, ex, ey, e[5] * k)
                gg.add_color_stop_rgba(0, 1, 0.85, 0.4, 0.9 * k)
                gg.add_color_stop_rgba(1, 1, 0.3, 0.0, 0)
                ctx.set_source(gg)
                ctx.arc(ex, ey, e[5] * k, 0, 2 * math.pi)
                ctx.fill()
                keep.append(e)
        embers = keep
        ctx.restore()

        # ふつうの文字(参考動画と同じ等幅のカウンター)
        mono(ctx, f"FRUIT SLICED {fr['cleared']} / {N_PLANKS}", W / 2, 1585, 40, (0.62, 0.64, 0.68))
        # ボールの順番(今のボールは明るく、使ったボールはうすく)
        cur = fr["dropped"] - 1
        for k in range(len(WAVES)):
            x = W / 2 + (k - (len(WAVES) - 1) / 2) * 150
            a = 1.0 if k == cur and fr["balls"] else (0.28 if k <= cur else 0.7)
            GD.draw_ball(ctx, k, x, 1680, -0.5, 38 if k < 5 else 30, t, a, None)
            text(ctx, SHORT_NAMES[k], x, 1745, 24, rgb=(1, 1, 1), sw=0, alpha=a)


        # 上の帯
        g = cairo.LinearGradient(0, 0, 0, 400)
        g.add_color_stop_rgba(0, 0.01, 0.015, 0.03, 0.96)
        g.add_color_stop_rgba(0.8, 0.01, 0.015, 0.03, 0.85)
        g.add_color_stop_rgba(1, 0.01, 0.015, 0.03, 0.0)
        ctx.rectangle(0, 0, W, 400)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, f"{N_BALLS}つの刃物でフルーツを全部", W / 2, 165, 70, sw=14)
        text(ctx, "切れる？", W / 2, 295, 124, rgb=GOLD, sw=18)
        text(ctx, "Can the blades slice every fruit?", W / 2, 360, 36, rgb=(0.85, 0.85, 0.9), sw=8)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "刃物が尽きた…", W / 2, 1000, 120 * (1.15 - 0.15 * k), rgb=(1, 0.3, 0.3), sw=18)
            text(ctx, f"あと{N_PLANKS - res['cleared']}個だったのに…", W / 2, 1130, 72, sw=12)
        elif over:
            ending.draw(surf, ctx, t - end_t)

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
VOICE_GAIN = 0.55      # 掛け声の大きさ(つぶれる音より少し大きい程度)
SFX_GAIN = 0.50        # ボールごとの効果音の大きさ
END_MUSIC_GAIN = 1.1   # 成功後の「大当たり」の音の大きさ(お祝いなので通常部分より少し大きめ)
F_LO, F_HI = 300.0, 1000.0             # 木の音の高さの範囲(参考動画と同じくらい)


def wood_tick(freq, amp):
    """フルーツを切る「シュパッ」という音(刃が空気を切る高い音+金属のきらめき+みずみずしい「ピチャ」。高さは刃物の位置で変わる)。"""
    n = int(0.2 * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(int(freq * 7))
    noise = rng.normal(0, 1, n)
    swish = (noise - np.convolve(noise, np.ones(3) / 3, mode="same")) * np.exp(-((t - 0.015) / 0.012) ** 2)   # シュッ
    ring = np.sin(2 * np.pi * freq * 4.2 * t) * np.exp(-t * 45) + 0.5 * np.sin(2 * np.pi * freq * 6.9 * t) * np.exp(-t * 60)   # キン
    juicy = np.convolve(noise, np.ones(10) / 10, mode="same") * np.exp(-((t - 0.04) / 0.025) ** 2) * 2.5   # パッ(果汁)
    drip = np.sin(2 * np.pi * np.cumsum(freq * 1.6 * (1 - 0.4 * t / 0.2)) / SR) * np.exp(-((t - 0.08) / 0.02) ** 2) * 0.35
    return amp * (0.8 * swish + 0.35 * ring + 0.6 * juicy + drip) * np.minimum(1, t / 0.0008)


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
    # ボールが落ちてくる瞬間の掛け声(ファイアー!! など)と、その種類の効果音
    snd = BV.drop_sounds(SR)
    fx = np.zeros_like(out)

    def add_x(sig, t0, gain, pan=0.0):
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if j > i:
            fx[i:j, 0] += gain * sig[: j - i] * math.sqrt(0.5 * (1 - pan)) * 1.414
            fx[i:j, 1] += gain * sig[: j - i] * math.sqrt(0.5 * (1 + pan)) * 1.414

    for kind, t, data in events:
        if kind == "drop" and (end_t is None or t <= end_t):
            voice, sfx = snd[data[1]]
            add_x(sfx, t + 0.05, SFX_GAIN)
            add_x(voice, t, VOICE_GAIN)
    extra += 0.6 * np.tanh(fx / 0.6)   # 音割れしないよう、大きすぎる瞬間だけやわらかく抑える
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m, None]
        sad_t = end_t + SCARE_DUR + 0.1
        for k, m_ in enumerate((64, 63, 62, 61)):
            add(chime(midi_hz(m_), 0.8, 0.35), sad_t + k * 0.42)
    elif end_t is not None:   # 成功:おしゃれで気持ちのいい短い曲
        sig = JP.music(SR, res.get("seed", 0)) * END_MUSIC_GAIN
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    wet = out.copy()
    for d, g in ((0.023, 0.22), (0.041, 0.16), (0.067, 0.1)):   # 小さな部屋の響き
        k = int(d * SR)
        wet[k:, 0] += out[:-k, 1] * g
        wet[k:, 1] += out[:-k, 0] * g
    wet = wet[: int(duration * SR)]
    # 通常部分は軽く圧縮して聞こえやすくし、叫び声との差は約10dBに抑える
    wet = np.tanh(2.5 * wet / max(1e-9, np.max(np.abs(wet)))) / np.tanh(2.5) * MIX_GAIN
    body = wet[: int((end_t or duration) * SR)]
    rms = np.sqrt(np.mean(body ** 2)) if len(body) else 0
    if rms > 0:   # 通常部分の平均音量を約 -18dB にそろえる
        wet *= min(2.0, 10 ** (-18.0 / 20) / rms)
    wet = wet + (0.95 if fail else 1.0) * extra[: len(wet)]
    # 0.78 を超える瞬間だけなめらかに抑えて、音割れ(クリップ)を防ぐ
    mag = np.abs(wet)
    wet = np.where(mag < 0.68, wet, np.sign(wet) * (0.68 + 0.1 * np.tanh((mag - 0.68) / 0.1)))
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


def remix(seed):
    """映像はそのままで、音だけ作り直して差し替える。"""
    res = simulate(seed)
    final = os.path.join(OUT_DIR, f"fruit_spiral_{seed}.mp4")
    tmp = os.path.join(OUT_DIR, f"fruit_spiral_{seed}_tmp.mp4")
    wav = os.path.join(OUT_DIR, f"fruit_spiral_{seed}.wav")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", final],
                               capture_output=True, text=True).stdout)
    synth_audio(res, dur, wav)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", final, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, final)
    os.remove(wav)
    print("音を差し替えました:", final)


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
