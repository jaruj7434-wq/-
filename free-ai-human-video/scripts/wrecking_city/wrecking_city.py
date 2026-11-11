"""「鉄球でビル街を全部なぎ倒せる?」転がる鉄球が、レンガのビルを次々に突き破っていく物理ショート。

- 横から見た地面に、レンガのビルが7棟(だんだん大きく、最後は超高層ビル)。
- 鉄球は地面を右へ転がり、ビルにぶつかって突き破る(重力・慣性・衝突・転がり抵抗のまま。ねらい・補正なし)。
- ビルとビルのあいだに「加速床」があり、通ると決まった分だけ速くなる。ビルを1棟こわしきるたびに鉄球が大きく重くなる。
- レンガは強い衝撃で割れる(割れやすさは1個ずつ少しちがう)。割れるたびに「ウィリアム・テル序曲」(パブリックドメイン)が1音進む。
- 最後の超高層ビルを突きぬけてゴールすれば成功(天使)、途中で止まれば失敗(幽霊)。

使い方:
    python wrecking_city.py search [-n 200]
    python wrecking_city.py render --seed N
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

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "ball_escape"))
from ball_escape import midi_hz, text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from angels import DURATION as ANGEL_DUR, AngelShow, holy_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 6
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

GRAVITY = 1800.0
BW, BH = 40.0, 20.0
# ビル:(左はしの x, 列, 段)
BUILDINGS = [(700, 4, 8), (1500, 4, 12), (2300, 5, 15), (3100, 5, 19), (3950, 6, 24), (4850, 6, 30)]
FINAL = (int(os.environ.get("FINAL_C", 10)), int(os.environ.get("FINAL_R", 42)))
BUILDINGS.append((5900, FINAL[0], FINAL[1]))   # 最後の超高層ビル(コンクリートブロック・かたい)
FINAL_STR = float(os.environ.get("FINAL_STR", 3.2))   # 最後のビルのブロックの、割れにくさの倍率
GOAL_X = BUILDINGS[-1][0] + BUILDINGS[-1][1] * BW + 260   # 地面の長さ・ゴールの旗の位置(見た目)
BREAK = float(os.environ.get("BREAK", 700.0))
BALL_R0 = float(os.environ.get("BALL_R0", 38.0))
BALL_DENS = float(os.environ.get("BALL_DENS", 0.02))
GROW = float(os.environ.get("GROW", 1.05))       # ビルを1棟こわすたびの大きさの倍率
V0 = float(os.environ.get("V0", 650.0))          # 最初の速さ
BOOST = float(os.environ.get("BOOST", 440.0))    # 加速床で足される速さ
ROLL_DAMP = float(os.environ.get("ROLL_DAMP", 0.06))   # 転がり抵抗(1秒あたりに失う速さの割合)
STOP_V = 25.0
STOP_WAIT = 1.5
OUTRO = 2.5
CT_BALL, CT_BRICK, CT_GROUND = 1, 2, 3


def boost_pads():
    """加速床:2棟目からのビルの手前(前のビルとのあいだ)。"""
    pads = []
    for k in range(1, len(BUILDINGS)):
        x_prev = BUILDINGS[k - 1][0] + BUILDINGS[k - 1][1] * BW
        x = BUILDINGS[k][0]
        pads.append(((x_prev + x) / 2 - 70, (x_prev + x) / 2 + 70))
    return pads


PADS = boost_pads()


class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 20
        sp.collision_slop = 0.3
        self.space = sp
        g = pymunk.Segment(sp.static_body, (-1000, 20), (GOAL_X + 3000, 20), 20)
        g.friction, g.elasticity = 0.9, 0.05
        g.collision_type = CT_GROUND
        sp.add(g)
        self.bricks = {}
        self.bld_of = {}
        self.bld_left = [0] * len(BUILDINGS)
        for bi, (x0, cols, rows) in enumerate(BUILDINGS):
            for r in range(rows):
                y = -BH / 2 - r * BH
                off = 0.0 if r % 2 == 0 else BW / 2
                x = x0 - off
                while x < x0 + cols * BW - 1:
                    a, b = max(x, x0), min(x + BW, x0 + cols * BW)
                    if b - a > 4:
                        ci = int((a - x0) // BW)
                        win = (r % 3 == 1) and (ci % 2 == 1) and r < rows - 1
                        self.add_brick((a + b) / 2, y, b - a - 0.5, BH - 0.4, bi, win)
                    x += BW
        self.n_bld = [self.bld_left[i] for i in range(len(BUILDINGS))]
        self.r = BALL_R0
        m = BALL_DENS * math.pi * self.r ** 2
        b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, self.r))
        b.position = (150, -self.r)
        b.velocity = (V0 * rng.uniform(0.95, 1.05), 0)
        b.angular_velocity = b.velocity.x / self.r
        s = pymunk.Circle(b, self.r)
        s.friction, s.elasticity = 0.6, 0.15
        s.collision_type = CT_BALL
        sp.add(b, s)
        self.ball, self.bshape = b, s
        sp.on_collision(CT_BALL, CT_BRICK, post_solve=self._hit)
        sp.on_collision(CT_BRICK, CT_BRICK, post_solve=self._hit)
        sp.on_collision(CT_BRICK, CT_GROUND, post_solve=self._hit)
        sp.on_collision(CT_BALL, CT_BRICK, begin=self._touch)
        self.to_break = set()
        self.broken = 0
        self.events = []
        self.t = 0.0
        self.result, self.result_t = None, None
        self.touched = set()
        self.cleared = set()
        self.on_pad = None
        self.slow_since = None
        self.level = 0

    def add_brick(self, x, y, w, h, bi, win=False):
        m = w / BW
        b = pymunk.Body(m, pymunk.moment_for_box(m, (w, h)))
        b.position = (x, y)
        s = pymunk.Poly.create_box(b, (w, h), 0.4)
        s.friction, s.elasticity = 0.7, 0.05
        s.collision_type = CT_BRICK
        self.space.add(b, s)
        self.bricks[b] = {"shape": s, "w": w, "h": h, "str": BREAK * float(self.rng.uniform(0.75, 1.25)) * (FINAL_STR if bi == len(BUILDINGS) - 1 else 1.0), "bld": bi,
                          "k": int(self.rng.integers(1 << 20)), "win": win}
        self.bld_left[bi] += 1

    def _touch(self, arb, space, data):
        for sh in arb.shapes:
            info = self.bricks.get(sh.body)
            if info is not None and info["bld"] not in self.touched:
                self.touched.add(info["bld"])
                self.events.append(("crash", self.t, info["bld"]))
        return True

    def _hit(self, arb, space, data):
        imp = arb.total_impulse.length
        for sh in arb.shapes:
            info = self.bricks.get(sh.body)
            if info is not None and imp > info["str"] * (info["w"] / BW):
                self.to_break.add(sh.body)

    def grow(self):
        self.r *= GROW
        self.bshape.unsafe_set_radius(self.r)
        m = BALL_DENS * math.pi * self.r ** 2
        self.ball.mass = m
        self.ball.moment = pymunk.moment_for_circle(m, 0, self.r)

    def step(self, dt):
        self.t += dt
        self.space.step(dt)
        b = self.ball
        b.velocity = b.velocity * (1 - ROLL_DAMP * dt)
        b.angular_velocity *= (1 - ROLL_DAMP * dt)
        for brick in list(self.to_break):
            info = self.bricks.pop(brick, None)
            if info is None:
                continue
            self.space.remove(brick, info["shape"])
            self.broken += 1
            self.events.append(("break", self.t, (brick.position.x, brick.position.y, brick.angle, info["w"], info["h"],
                                                  info["k"], tuple(brick.velocity), info["bld"], info["win"])))
        self.to_break.clear()
        for brick in list(self.bricks):   # 遠くへ飛んだレンガは消す(数えない)
            if brick.position.y > 600 or brick.position.y < -3000:
                info = self.bricks.pop(brick)
                self.space.remove(brick, info["shape"])
        # 加速床
        x = b.position.x
        pad = next((k for k, (a, c) in enumerate(PADS) if a <= x <= c and b.position.y > -self.r - 30), None)
        if pad is not None and pad != self.on_pad:
            b.velocity = (b.velocity.x + BOOST, b.velocity.y)
            b.angular_velocity = b.velocity.x / self.r
            self.events.append(("boost", self.t, pad))
        self.on_pad = pad
        # ビルを1棟ぬけた(鉄球がビルの右はしをこえた)→ 巨大化
        for bi, (x0, cols, rows) in enumerate(BUILDINGS):
            if bi not in self.cleared and x - self.r > x0 + cols * BW:
                self.cleared.add(bi)
                if bi < len(BUILDINGS) - 1:
                    self.grow()
                    self.events.append(("grow", self.t, bi))
        if self.result is None:
            if len(BUILDINGS) - 1 in self.cleared:   # 最後の超高層ビルを突きぬけた
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            else:
                if b.velocity.length < STOP_V:
                    if self.slow_since is None:
                        self.slow_since = self.t
                    elif self.t - self.slow_since > STOP_WAIT:
                        self.result, self.result_t = "fail", self.t
                        self.events.append(("fail", self.t, None))
                else:
                    self.slow_since = None
            if self.result is not None:
                self.final = (len(self.cleared), self.broken)


def simulate(seed, record_times=None):
    """record_times: 記録する時刻のリスト(スロー再生のため細かく)。None なら記録しない。"""
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    ri = 0
    while True:
        g.step(dt)
        while record_times is not None and ri < len(record_times) and record_times[ri] <= g.t + 1e-9:
            frames.append({"t": record_times[ri],
                           "bricks": [(br.position.x, br.position.y, br.angle, i["w"], i["h"], i["k"], i["bld"], i["win"])
                                      for br, i in g.bricks.items()],
                           "ball": (g.ball.position.x, g.ball.position.y, g.ball.angle, g.r),
                           "broken": g.broken, "cleared": len(g.cleared)})
            ri += 1
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if record_times is None or ri >= len(record_times):
                if record_times is not None or True:
                    break
        if g.t > 120:
            break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "final": getattr(g, "final", (len(g.cleared), g.broken)), "total": sum(g.n_bld)}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"] and round(r["result_t"], 1), r["final"]


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    from collections import Counter
    print(sorted(Counter(r[3][0] for r in rs).items()))
    for r in rs:
        print(r)


# ---------------------------------------------------------------- スロー再生(見せ方だけ。物理の計算は同じ)
SLOW = float(os.environ.get("SLOW", 0.28))


def time_map(res):
    """動画の各コマに対応する、物理の時刻。ビルにぶつかった瞬間だけスローにする。"""
    crashes = [(e[1], e[2]) for e in res["events"] if e[0] == "crash"]
    end_t = res["result_t"]
    extra = OUTRO + SCARE_DUR if res["result"] == "fail" else ANGEL_DUR

    def speed(tau):
        for tc, bi in crashes:
            last = bi == len(BUILDINGS) - 1
            a, b = tc - 0.04, tc + (1.0 if last else 0.45)
            if a <= tau <= b:
                return SLOW * (0.75 if last else 1.0)
        return 1.0
    ts = []
    tau = 0.0
    while tau < end_t + extra:
        tau += speed(tau) / FPS
        ts.append(tau)
    return ts


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
GROUND_SY = 1520.0
BALL_SX = 330.0
BLD_COLS = [(0.72, 0.28, 0.18), (0.82, 0.45, 0.2), (0.75, 0.6, 0.3), (0.5, 0.35, 0.55), (0.3, 0.45, 0.6),
            (0.35, 0.55, 0.4), (0.62, 0.63, 0.66)]


def sky():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, GROUND_SY)
    g.add_color_stop_rgb(0, 0.18, 0.35, 0.7)
    g.add_color_stop_rgb(0.7, 0.55, 0.75, 0.95)
    g.add_color_stop_rgb(1, 0.95, 0.85, 0.7)
    c.set_source(g)
    c.paint()
    return surf


def skyline(ctx, cam_x, rng_seed, par, col, hmin, hmax):
    rng = np.random.default_rng(rng_seed)
    xs = []
    x = -400.0
    while x < GOAL_X * par + 2000:
        w = rng.uniform(70, 160)
        xs.append((x, w, rng.uniform(hmin, hmax)))
        x += w + rng.uniform(0, 30)
    off = cam_x * par
    for x, w, h in xs:
        sx = x - off
        if -200 < sx < W + 200:
            ctx.rectangle(sx, GROUND_SY - h, w, h)
    ctx.set_source_rgba(*col)
    ctx.fill()


def draw_brick(ctx, sx, sy, ang, w, h, col, win, sc):
    ctx.save()
    ctx.translate(sx, sy)
    ctx.rotate(ang)
    ctx.rectangle(-w * sc / 2, -h * sc / 2, w * sc, h * sc)
    if win:
        g = cairo.LinearGradient(-w * sc / 2, -h * sc / 2, w * sc / 2, h * sc / 2)
        g.add_color_stop_rgb(0, 0.75, 0.9, 1.0)
        g.add_color_stop_rgb(1, 0.25, 0.45, 0.7)
    else:
        g = cairo.LinearGradient(0, -h * sc / 2, 0, h * sc / 2)
        g.add_color_stop_rgb(0, *(min(1, c * 1.2) for c in col))
        g.add_color_stop_rgb(1, *(c * 0.75 for c in col))
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.95, 0.9, 0.82, 0.8)
    ctx.set_line_width(max(1.0, 1.6 * sc))
    ctx.stroke()
    ctx.restore()


def brick_col(bi, k):
    c = BLD_COLS[bi]
    v = ((k % 97) / 97 - 0.5) * 0.12
    return tuple(min(1, max(0, x + v)) for x in c)


def draw_ball(ctx, sx, sy, r, ang, speed):
    if speed > 500:   # 速いときは後ろに残像
        for k in range(1, 5):
            ctx.arc(sx - k * r * 0.35 * min(2.0, speed / 900), sy, r * (1 - 0.06 * k), 0, 2 * math.pi)
            ctx.set_source_rgba(0.5, 0.5, 0.55, 0.12)
            ctx.fill()
    g = cairo.RadialGradient(sx - r * 0.35, sy - r * 0.4, r * 0.08, sx, sy, r)
    g.add_color_stop_rgb(0, 0.92, 0.93, 0.96)
    g.add_color_stop_rgb(0.45, 0.4, 0.42, 0.47)
    g.add_color_stop_rgb(1, 0.08, 0.08, 0.1)
    ctx.set_source(g)
    ctx.arc(sx, sy, r, 0, 2 * math.pi)
    ctx.fill()
    ctx.save()   # 転がっているのがわかる、ボルトの印
    ctx.translate(sx, sy)
    ctx.rotate(ang)
    for a in (0, math.pi * 2 / 3, math.pi * 4 / 3):
        ctx.arc(r * 0.6 * math.cos(a), r * 0.6 * math.sin(a), r * 0.12, 0, 2 * math.pi)
        ctx.set_source_rgba(0.15, 0.15, 0.18, 0.8)
        ctx.fill()
    ctx.restore()


def render(seed):
    res0 = simulate(seed)
    sim_ts = time_map(res0)
    res = simulate(seed, record_times=sim_ts)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    vt_of = lambda tau: float(np.interp(tau, sim_ts, np.arange(1, len(sim_ts) + 1) / FPS))   # noqa: E731
    v_end = vt_of(end_t)
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"wrecking_city_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"wrecking_city_{seed}.wav")
    final = os.path.join(OUT_DIR, f"wrecking_city_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"wc_preview_{pt:.1f}.png"))
                self.fi += 1
        ff = _P()
        frames = frames[: int(max(preview) * FPS) + 2]
    else:
        ff = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
             "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
            stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    angels = AngelShow(W, H, seed) if result == "success" else None
    bg = sky()
    rng = np.random.default_rng(seed + 5)
    frags, dusts = [], []
    shake = 0.0
    flash = 0.0
    labels = []   # (文字, 色, 出た動画時刻)
    cam_x = frames[0]["ball"][0]
    cam_sc = 1.4
    ev_i = 0
    prev_vt = 0.0
    for fi, fr in enumerate(frames):
        tau = fr["t"]
        vt = (fi + 1) / FPS
        dvt = vt - prev_vt
        prev_vt = vt
        while ev_i < len(events) and events[ev_i][1] <= tau:
            kind, et, data = events[ev_i]
            if kind == "break":
                x, y, ang, w, h, k, vel, bi, win = data
                col = (0.7, 0.88, 1.0) if win else brick_col(bi, k)
                for _ in range(9 if win else 6):
                    a = rng.uniform(0, 2 * math.pi)
                    v = rng.uniform(150, 650)
                    frags.append([x, y, vel[0] * 0.6 + v * math.cos(a), vel[1] * 0.6 + v * math.sin(a) - 300,
                                  rng.uniform(0, 6), rng.uniform(-14, 14), rng.uniform(5, 13) * (0.7 if win else 1), col, et])
                if rng.uniform() < 0.5:
                    dusts.append([x, y, rng.uniform(40, 80), et])
                shake = max(shake, 4.0)
            elif kind == "crash":
                shake = max(shake, 28 if data == len(BUILDINGS) - 1 else 18)
                flash = 0.55
                if data == len(BUILDINGS) - 1:
                    labels.append(("最後の超高層ビル!!", (1, 0.5, 0.3), vt))
            elif kind == "boost":
                labels.append(("加速!!", (0.5, 1, 1), vt))
            elif kind == "grow":
                labels.append((f"{data + 1}棟目クリア! 鉄球パワーアップ", GOLD, vt))
            ev_i += 1
        over = end_t is not None and tau >= end_t
        if ghost is not None and over and vt - v_end < SCARE_DUR:
            ghost.draw(surf, vt - v_end)
            ff.stdin.write(surf.get_data())
            continue
        after = (vt - v_end - (SCARE_DUR if fail else 0)) if over else 0
        bx, by, ba, br = fr["ball"]
        # カメラ:鉄球を追いかけ、次のビルが入るように引く
        nxt = next((b for b in BUILDINGS if b[0] + b[1] * BW > bx - br), BUILDINGS[-1])
        bh = nxt[2] * BH
        tgt_sc = min(1.45, 1050.0 / (bh + 300))
        if over and not fail:
            tgt_sc = min(tgt_sc, 0.9)
        cam_sc += (tgt_sc - cam_sc) * 0.05
        cam_x += (bx - cam_x) * 0.2
        sc = cam_sc
        SX = lambda x: BALL_SX + (x - cam_x) * sc   # noqa: E731
        SY = lambda y: GROUND_SY + y * sc           # noqa: E731
        shake *= 0.86
        flash *= 0.85
        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        skyline(ctx, cam_x, 1, 0.15, (0.55, 0.65, 0.82, 1), 200, 520)
        skyline(ctx, cam_x, 2, 0.35, (0.42, 0.5, 0.66, 1), 120, 380)
        ctx.save()
        if shake > 0.5:
            ctx.translate(math.sin(vt * 61) * shake, math.cos(vt * 47) * shake)
        # 地面(道路)
        ctx.rectangle(-50, GROUND_SY, W + 100, H - GROUND_SY)
        ctx.set_source_rgb(0.25, 0.25, 0.28)
        ctx.fill()
        ctx.rectangle(-50, GROUND_SY, W + 100, 10)
        ctx.set_source_rgb(0.55, 0.55, 0.58)
        ctx.fill()
        x = (cam_x - BALL_SX / sc) // 160 * 160
        while SX(x) < W + 100:   # 道路の白線
            ctx.rectangle(SX(x), GROUND_SY + 60, 80 * sc, 10)
            x += 160
        ctx.set_source_rgba(1, 1, 1, 0.7)
        ctx.fill()
        for k, (a, c) in enumerate(PADS):   # 加速床
            if SX(c) < -50 or SX(a) > W + 50:
                continue
            ctx.rectangle(SX(a), GROUND_SY - 4, (c - a) * sc, 12)
            ctx.set_source_rgba(0.2, 1, 1, 0.85)
            ctx.fill()
            for j in range(3):
                xx = SX(a + (c - a) * (j + 0.3) / 3)
                ph = (vt * 2 + j / 3) % 1
                ctx.move_to(xx, GROUND_SY - 34)
                ctx.line_to(xx + 22 * sc, GROUND_SY - 20)
                ctx.line_to(xx, GROUND_SY - 6)
                ctx.set_source_rgba(0.3, 1, 1, 0.4 + 0.6 * ph)
                ctx.set_line_width(5)
                ctx.stroke()
        # ゴール
        gx = SX(GOAL_X)
        if -50 < gx < W + 50:
            ctx.set_source_rgb(0.9, 0.9, 0.9)
            ctx.rectangle(gx - 4, GROUND_SY - 330, 8, 330)
            ctx.fill()
            for r_ in range(6):
                for c_ in range(4):
                    ctx.rectangle(gx + 4 + c_ * 22, GROUND_SY - 330 + r_ * 18, 22, 18)
                    ctx.set_source_rgb(*((0.05, 0.05, 0.05) if (r_ + c_) % 2 else (1, 1, 1)))
                    ctx.fill()
            text(ctx, "GOAL", gx + 50, GROUND_SY - 370, 56, rgb=GOLD, sw=10)
        lo = cam_x - (BALL_SX + 100) / sc
        hi = cam_x + (W - BALL_SX + 100) / sc
        for x, y, ang, w, h, k, bi, win in fr["bricks"]:
            if lo < x < hi:
                draw_brick(ctx, SX(x), SY(y), ang, w, h, brick_col(bi, k), win, sc)
        spd = math.hypot(*(np.subtract(fr["ball"][:2], frames[fi - 1]["ball"][:2]) * FPS)) / max(1e-3, (tau - frames[fi - 1]["t"]) * FPS) if fi else 0
        draw_ball(ctx, SX(bx), SY(by), br * sc, ba, spd)
        keep = []
        for f in frags:
            a = tau - f[8]
            if a > 1.6:
                continue
            x = f[0] + f[2] * a
            y = min(-3, f[1] + f[3] * a + 0.5 * GRAVITY * a * a)
            ctx.save()
            ctx.translate(SX(x), SY(y))
            ctx.rotate(f[4] + f[5] * a)
            s_ = f[6] * sc
            ctx.move_to(-s_, -s_ * 0.5)
            ctx.line_to(s_ * 0.8, -s_ * 0.7)
            ctx.line_to(s_ * 0.5, s_ * 0.6)
            ctx.line_to(-s_ * 0.6, s_ * 0.4)
            ctx.close_path()
            ctx.set_source_rgba(*f[7], 1 - max(0, a - 1.1) / 0.5)
            ctx.fill()
            ctx.restore()
            keep.append(f)
        frags = keep
        keep = []
        for d_ in dusts:
            a = tau - d_[3]
            if a > 1.5:
                continue
            rr = d_[2] * (1 + 2.2 * a) * sc
            g = cairo.RadialGradient(SX(d_[0]), SY(d_[1]), 0, SX(d_[0]), SY(d_[1]), rr)
            g.add_color_stop_rgba(0, 0.85, 0.78, 0.68, 0.4 * (1 - a / 1.5))
            g.add_color_stop_rgba(1, 0.85, 0.78, 0.68, 0)
            ctx.set_source(g)
            ctx.arc(SX(d_[0]), SY(d_[1]), rr, 0, 2 * math.pi)
            ctx.fill()
            keep.append(d_)
        dusts = keep
        ctx.restore()
        slow = fi > 0 and (tau - frames[fi - 1]["t"]) < 0.7 / FPS
        if slow:   # スロー中は画面のふちを暗く
            g = cairo.RadialGradient(W / 2, H / 2, 300, W / 2, H / 2, 1100)
            g.add_color_stop_rgba(0, 0, 0, 0, 0)
            g.add_color_stop_rgba(1, 0, 0, 0, 0.45)
            ctx.set_source(g)
            ctx.paint()
        if flash > 0.02:
            ctx.set_source_rgba(1, 1, 1, flash)
            ctx.paint()
        if angels is not None and over:
            angels.draw(ctx, vt - v_end)
        g = cairo.LinearGradient(0, 0, 0, 330)
        g.add_color_stop_rgba(0, 0.05, 0.06, 0.12, 0.85)
        g.add_color_stop_rgba(1, 0.05, 0.06, 0.12, 0.0)
        ctx.rectangle(0, 0, W, 330)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, "鉄球でビル街を", W / 2, 120, 78, sw=12)
        text(ctx, "全部なぎ倒せる？", W / 2, 240, 112, rgb=GOLD, sw=18)
        cleared = fr["cleared"] if not over else res["final"][0]
        text(ctx, f"ビル {cleared} / {len(BUILDINGS)}", W / 2 - 200, 1760, 64, sw=12)
        text(ctx, f"レンガ {fr['broken'] if not over else res['final'][1]}個", W / 2 + 220, 1760, 56, rgb=(0.9, 0.85, 0.8), sw=10)
        labels = [l_ for l_ in labels if vt - l_[2] < 1.3]
        for j, (s_, col, t0) in enumerate(labels[-2:]):
            k2 = min(1.0, (vt - t0) / 0.12)
            text(ctx, s_, W / 2, 420 + 100 * j, 80 * (1.25 - 0.25 * k2), rgb=col, sw=14)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "止まった…", W / 2, 900, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{len(BUILDINGS) - res['final'][0]}棟だったのに…", W / 2, 1030, 72, sw=12)
        elif over:
            text(ctx, "全部なぎ倒した!!", W / 2, 640, 110, rgb=GOLD, sw=18)
        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
    if preview:
        return
    ff.stdin.close()
    ff.wait()
    duration = len(frames) / FPS
    synth_audio(res, duration, wav, vt_of)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(silent)
    os.remove(wav)
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} ビル{res['final'][0]}棟 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
sys.path.insert(0, os.path.join(HERE, "..", "giant_domino"))
import giant_domino as GD  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "wrecking_ball"))
from wrecking_ball import TELL, SIXTEENTH, crunch, tell_note  # noqa: E402

HOLY_GAIN = 0.85


def boom(seed, amp, dur=1.6):
    t = GD._t(dur)
    rng = np.random.default_rng(seed)
    n = np.convolve(rng.normal(0, 1, len(t)), np.ones(12) / 12, "same")
    return amp * (0.9 * np.sin(2 * np.pi * 48 * t * (1 - 0.3 * t / dur)) * np.exp(-t * 2.5) + 1.2 * n * np.exp(-t * 4))


def whoosh_up(amp):
    t = GD._t(0.45)
    f = 300 + 1600 * (t / 0.45) ** 2
    rng = np.random.default_rng(3)
    n = rng.normal(0, 1, len(t))
    return amp * (0.4 * np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * n) * np.sin(np.pi * t / 0.45)


def synth_audio(res, duration, path, vt_of):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    v_end = vt_of(end_t)
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)

    def add(sig, t0, gain=1.0, buf=None):
        b = out if buf is None else buf
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out and j > i:
            b[i:j] += gain * sig[: j - i]

    note_i = -1
    next_ok = 0.0
    last_c = -1.0
    big = False
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.02:
            continue
        vt = vt_of(t)
        if kind == "break":
            if vt - last_c > 0.035:
                add(crunch(int(t * 1000), 0.3), vt)
                last_c = vt
            if vt >= next_ok:
                note_i += 1
                m, du = TELL[note_i % len(TELL)]
                add(tell_note(m, 0.6, big), vt)
                next_ok = vt + du * SIXTEENTH - 0.01
        elif kind == "crash":
            add(boom(int(t * 100), 1.0 if data == len(BUILDINGS) - 1 else 0.7), vt)
        elif kind == "boost":
            add(whoosh_up(0.6), vt)
        elif kind == "grow":
            if data >= 2:
                big = True
            add(GD.mix(GD.brass(midi_hz(69), 0.4, 0.35), GD.brass(midi_hz(76), 0.35, 0.35)), vt)
    if fail:
        sig = scream(SR)
        i0 = int(v_end * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:
        add(GD.mix(*[GD.mix(GD.brass(midi_hz(m_), 0.5, 2.2), GD.strings(midi_hz(m_), 0.35, 2.5)) for m_ in (45, 57, 61, 64, 69)]), v_end)
        add(GD.timpani(1.0, 2.0), v_end)
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(v_end * SR) + int(1.8 * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += HOLY_GAIN * sig[:m]
    wet = out.copy()
    for dd, g in ((0.047, 0.28), (0.079, 0.2), (0.121, 0.13)):
        k = int(dd * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int(v_end * SR)]
    rms = np.sqrt(np.mean(body ** 2)) if len(body) else 0
    if rms > 0:
        wet *= min(4.0, 10 ** (-14.0 / 20) / rms)
    wet = wet + (0.95 if fail else 1.0) * extra[: len(wet)]
    mag = np.abs(wet)
    wet = np.where(mag < 0.7, wet, np.sign(wet) * (0.7 + 0.25 * np.tanh((mag - 0.7) / 0.25)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("-n", type=int, default=100)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
