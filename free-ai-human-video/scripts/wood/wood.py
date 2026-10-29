"""「玉は木を全部こわせる?」うずまきの通路に並んだ木の板を、玉が跳ねながら壊していく物理ショートを生成する。

参考動画(Will the ball break through all the wood?)の動き・見た目・音を分析して再現したもの:
- 5重のうずまきの壁。通路には放射状に並んだ木の板(432枚)。
- 玉は右上のたて筒を落ちて、うずまきの外側の口から通路に入る。板に当たると板は割れて玉は突き抜けるが、そのたびに少し遅くなる。
- 玉は波のように増える:黄1 → 赤2 → 青4 → 黄5。
- 板が壊れるたびに短い木琴のような「コッ」という音。音の高さは玉の位置(角度)で上下する。
- 玉の動きは重力・反発・衝突の物理のまま(ねらい・補正なし)。
制限時間内に432枚すべて壊せば成功(天使)、残れば失敗(幽霊)。

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

CHUTE_L, CHUTE_R = CX + R_OUT - LANE, CX + R_OUT   # 入口のたて筒
CHUTE_TOP = CY - R_OUT - 150
GATE_Y = CY - 30
BREAK_KEEP = 0.965                     # 板を1枚割ったあとに残る玉の速さの割合
AIR_DAMP = 0.98                        # 1秒あたりに残る速さの割合(空気抵抗)
WALL_E = 1.0                           # 壁の反発係数
BALL_R = 16
GRAVITY = 1300.0
WAVES = [(0.5, 1, "yellow"), (3.6, 2, "red"), (8.2, 4, "blue"), (14.8, 5, "yellow")]
TIME_LIMIT = 20.0
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


def board_physics(body, gravity, damping, dt):
    """入口のたて筒の中だけ重力で落ちる。盤面は真上から見た水平な台なので重力は効かず、わずかな抵抗だけかかる。"""
    x, y = body.position
    if y < GATE_Y and x > CHUTE_L - 10:
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
            s = pymunk.Segment(st, a, b, 4)
            s.elasticity, s.friction = WALL_E, 0.0
            # つなぎ目で玉が変な向きにはじかれないよう、となりの線分を教えておく
            s.set_neighbors(pts[max(i - 1, 0)], pts[min(i + 2, n)])
            sp.add(s)
        # 入口のたて筒(うずまきの外側の口から真上へ)。筒の下には一方通行のふた(上から入る玉は通し、出ようとする玉ははね返す)
        for x in (CHUTE_L, CHUTE_R):
            seg = pymunk.Segment(st, (x, CY), (x, CHUTE_TOP), 4)
            seg.elasticity, seg.friction = 1.0, 0.0
            sp.add(seg)
        gate = pymunk.Segment(st, (CHUTE_L + 4, GATE_Y), (CHUTE_R - 4, GATE_Y), 3)
        gate.elasticity, gate.friction = 1.0, 0.0
        gate.collision_type = 5
        sp.add(gate)
        sp.on_collision(1, 5, pre_solve=self._gate)
        # 木の板(放射状。内側の壁から外側の壁まで)
        self.planks = []
        self.plank_of = {}
        for k in range(N_PLANKS):
            th = TH_WOOD0 + (TH_WOOD1 - TH_WOOD0) * (k + 0.5) / N_PLANKS
            a = wall_pt(th, 9)
            b = wall_pt(th + 2 * math.pi, -9)
            s = pymunk.Segment(st, a, b, 3)
            s.elasticity, s.friction = 1.0, 0.0
            s.collision_type = 4
            sp.add(s)
            self.plank_of[s] = k
            self.planks.append({"th": th, "alive": True, "shape": s,
                                "tint": float(self.rng.uniform(-0.06, 0.06))})
        sp.on_collision(1, 4, begin=self._hit)
        self.to_break = []
        self.balls = []
        self.events = []
        self.cleared = 0
        self.t = 0.0
        self.result, self.result_t = None, None
        self.queue = []
        for t0, n_b, col in WAVES:
            for j in range(n_b):
                self.queue.append((t0 + j * 0.28, col))

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

    @staticmethod
    def _gate(arb, space, data):
        arb.process_collision = arb.shapes[0].body.velocity.y < 0

    def drop(self, col):
        m = 1.0
        b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, BALL_R))
        x = (CHUTE_L + CHUTE_R) / 2 + self.rng.uniform(-6, 6)
        b.position = (x, CHUTE_TOP + 40)
        b.velocity = (self.rng.uniform(-15, 15), 300)
        b.velocity_func = board_physics
        c = pymunk.Circle(b, BALL_R)
        c.elasticity, c.friction = 1.0, 0.0
        c.collision_type = 1
        self.space.add(b, c)
        self.balls.append({"body": b, "col": col, "born": self.t})
        self.events.append(("drop", self.t, col))

    def step(self, dt):
        self.t += dt
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
        if self.result is None:
            if self.cleared == N_PLANKS:
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
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "cleared": g.cleared,
                           "balls": [(b["body"].position.x, b["body"].position.y,
                                      b["body"].velocity.x, b["body"].velocity.y, b["col"]) for b in g.balls],
                           "alive": [p["alive"] for p in g.planks]})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "cleared": g.cleared, "planks": g.planks}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["cleared"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "fail":
        for seed, _, _, c in sorted([r for r in rs if r[1] == "fail"], key=lambda r: -r[3])[:15]:
            print(f"seed={seed:4d}  {c}/{N_PLANKS} 枚で時間切れ")
    else:
        for seed, _, rt, _ in sorted(succ, key=lambda r: -r[2])[:15]:
            print(f"seed={seed:4d}  全部こわした {rt:5.2f}秒")


# ---------------------------------------------------------------- 描画
OFFSET_Y = 80                          # 物理の座標を画面上で少し下にずらして表示する
BG = (0.02, 0.027, 0.047)
STEEL = (0.62, 0.72, 0.88)
WOOD = (0.79, 0.63, 0.48)
BALL_COL = {"yellow": (1.0, 0.84, 0.22), "red": (1.0, 0.32, 0.30), "blue": (0.36, 0.66, 1.0)}
GOLD = (1, 0.86, 0.2)
MONO = "JetBrains Mono"
WAVE_TEXT = {2: "玉が2個に増えた！", 4: "玉が4個に増えた！", 5: "ラスト5個！"}


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
    lines = [[wall_pt(TH_END * k / n) for k in range(n + 1)],
             [(CHUTE_L, CY), (CHUTE_L, CHUTE_TOP)], [(CHUTE_R, CY), (CHUTE_R, CHUTE_TOP)]]
    for width, alpha in ((22, 0.05), (12, 0.10), (6, 1.0)):   # ぼんやり光る → 芯の線
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
    # 入口のふた(一方通行)と白い点
    ctx.new_path()
    ctx.move_to(CHUTE_L + 4, GATE_Y)
    ctx.line_to(CHUTE_R - 4, GATE_Y)
    ctx.set_dash([8, 8])
    ctx.set_source_rgba(1, 1, 1, 0.55)
    ctx.set_line_width(3)
    ctx.stroke()
    ctx.set_dash([])
    for x in (CHUTE_L, CHUTE_R):
        ctx.new_path()
        ctx.arc(x, GATE_Y, 7, 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()


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


def draw_ball(ctx, x, y, col, trail):
    r, g_, b = col
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
    shards, banners, trails = [], [], {}
    last10 = False
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
            elif kind == "drop":
                n_now = sum(1 for e in events if e[0] == "drop" and e[1] <= et)
                for t0, n_b, col in WAVES:
                    first = sum(nb for t1, nb, _ in WAVES if t1 < t0) + 1
                    if n_now == first and n_b > 1:
                        banners.append([et, WAVE_TEXT[n_b], BALL_COL[col]])
            ev_i += 1
        if not last10 and N_PLANKS - fr["cleared"] <= 10 and fr["cleared"] < N_PLANKS:
            last10 = True
            banners.append([t, "ラスト10枚！", GOLD])
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
        # 玉
        for i, (x, y, vx, vy, col) in enumerate(fr["balls"]):
            tr = trails.setdefault(i, [])
            draw_ball(ctx, x, y, BALL_COL[col], tr)
            tr.append((x, y))
            del tr[:-8]
        ctx.restore()

        # ふつうの文字(参考動画と同じ等幅のカウンター)
        mono(ctx, f"WOOD CLEARED {fr['cleared']} / {N_PLANKS}", W / 2, 1585, 40, (0.62, 0.64, 0.68))
        for bn in banners:
            age = t - bn[0]
            if 0 <= age < 1.3 and not over:
                k = min(1, age / 0.15)
                text(ctx, bn[1], W / 2, 1700, 84 * (1.4 - 0.4 * k), rgb=bn[2], sw=16,
                     alpha=min(1, 3 * (1.3 - age)))
        if angels is not None and over:
            angels.draw(ctx, t - end_t)

        # 上の帯
        g = cairo.LinearGradient(0, 0, 0, 470)
        g.add_color_stop_rgba(0, 0.01, 0.015, 0.03, 0.96)
        g.add_color_stop_rgba(0.8, 0.01, 0.015, 0.03, 0.85)
        g.add_color_stop_rgba(1, 0.01, 0.015, 0.03, 0.0)
        ctx.rectangle(0, 0, W, 470)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, f"{int(TIME_LIMIT)}秒で木を全部", W / 2, 165, 82, sw=14)
        text(ctx, "こわせる？", W / 2, 295, 124, rgb=GOLD, sw=18)
        text(ctx, "Will the ball break through all the wood?", W / 2, 360, 36, rgb=(0.85, 0.85, 0.9), sw=8)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        tcol = (1, 0.35, 0.35) if left < 5 else (1, 1, 1)
        text(ctx, f"残り {left:4.1f}秒" if left >= 3 else f"残り {left:4.2f}秒", W / 2, 440, 56, rgb=tcol, sw=10)
        if not over:
            text(ctx, "※失敗すると…アレが出ます", W / 2, 1840, 50, rgb=(1, 0.35, 0.35), sw=10)
        elif fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 1000, 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{N_PLANKS - res['cleared']}枚だったのに…", W / 2, 1130, 72, sw=12)
        else:
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
MIX_GAIN = 0.6   # 通常部分の音量(約 -18dB になるよう調整)
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
        elif kind == "drop":
            add(chime(midi_hz(84), 0.5, 0.06), t)
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
