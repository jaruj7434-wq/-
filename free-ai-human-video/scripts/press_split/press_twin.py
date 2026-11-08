"""「1個のボールを1000個に増やせる?」左右2台のプレス機が一定の速さで閉じるたびに、はさまれたボールが2倍に増える物理ショート。

- 箱の中をボールが壁に当たりながら跳ね返り続ける(重力なし・止まらずに飛び回る)。
- 左右のかべから2台の小さめのプレス機が、なめらかに真ん中へ動いてくっつき、また戻る動きを PERIOD 秒ごとにくり返す。
- 閉じていく板のあいだにはさまれたボールは、つぶれて見えなくなり、板と板はぴったりくっつく。
  開くと、はさまれたボールが2倍になって上下にはじき出される(1個なら2個、5個同時なら10個)。ボールをねらってはさむことはしない(動きに身を任せる・補正なし)。
- 制限時間内に TARGET 個になれば成功、ならなければ失敗(幽霊)。
- 音: 壁に当たる「コッ」、プレスがくっつく「ガシャン」、開くときの「プシュー」、増えるたびに「ポポポポン」(数が増えるほど高く)。

使い方:
    python press_twin.py search [--want fail|success] [-n 200]
    python press_twin.py render --seed N
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
from ball_escape import text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
sys.path.insert(0, HERE)
import ballskin as BS  # noqa: E402
import press_fever as FV  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

# ---------------------------------------------------------------- 物理の設定
TARGET = int(os.environ.get("TARGET", 1000))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 35.0))
BALL_R = float(os.environ.get("BALL_R", 11.0))
SPEED = float(os.environ.get("SPEED", 330.0))           # ボールの速さ(重力も摩擦もないので、ずっとこの速さで飛び回る)
X0, X1 = 40.0, W - 40.0                                 # 箱の左右のかべ
Y0 = float(os.environ.get("Y0", 560.0))                 # 箱の天井
Y1 = float(os.environ.get("Y1", 1760.0))                # 箱の床
CY = (Y0 + Y1) / 2
PRESS_H = float(os.environ.get("PRESS_H", 400.0))       # プレス板の高さ
PERIOD = float(os.environ.get("PERIOD", 1.1))           # プレスの1往復の時間
# (板は PERIOD の半分の時刻でくっつく)
GAP = 0.0                                               # くっついたときの板と板のすきま(ぴったりくっつく)
SPAWN_DELAY = 0.12                                      # 開き始めてから、増えたボールが出てくるまで
OPEN_X = float(os.environ.get("OPEN_X", 280.0))                                         # 開いたときの板の先の位置(かべからの距離)
MAX_BALLS = TARGET + 60
OUTRO = 2.5


def press_x(t):
    """左のプレス板の先(右側の面)の x。右の板は左右対称。
    なめらかに閉じてぴったりくっつき、なめらかに開く動きをくり返す(止まったり、急に向きが変わったりしない)。"""
    ph = (t % PERIOD) / PERIOD
    x_open = X0 + OPEN_X
    x_shut = W / 2 - GAP / 2
    return x_open + (x_shut - x_open) * (1 - math.cos(2 * math.pi * ph)) / 2


class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, 0)
        sp.iterations = 20
        self.space = sp
        st = sp.static_body
        for a, b in (((X0, Y0), (X1, Y0)), ((X1, Y0), (X1, Y1)), ((X1, Y1), (X0, Y1)), ((X0, Y1), (X0, Y0))):
            s = pymunk.Segment(st, a, b, 16)
            s.elasticity, s.friction = 1.0, 0.0
            s.collision_type = 2
            sp.add(s)
        # 左右のプレス板(決まった動きをする板)。ボールは板に当たると跳ね返る
        self.plates = []
        for side in (-1, 1):
            b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            shape = pymunk.Poly.create_box(b, (500, PRESS_H))
            shape.elasticity, shape.friction = 1.0, 0.0
            shape.collision_type = 3
            sp.add(b, shape)
            self.plates.append((side, b))
        self._place_plates(0.0, 1e-3)
        sp.on_collision(1, 2, begin=self._wall)
        sp.on_collision(1, 3, begin=self._plate_hit, pre_solve=self._plate_hit)
        self.balls = {}
        self.next_id = 0
        self.t = 0.0
        self.events = []
        self.result, self.result_t = None, None
        self.trapped = []   # プレスの中でつぶれているボール(開いたら2倍になって出てくる)
        a = self.rng.uniform(0, 2 * math.pi)
        self.add_ball((W / 2, CY),   # 最初の1個はまん中から(向きはばらばら)
                      (SPEED * math.cos(a), SPEED * math.sin(a)), 0)

    def _place_plates(self, t, dt):
        xl = press_x(t)
        xl_prev = press_x(t - dt)
        for side, b in self.plates:
            if side < 0:
                b.position = (xl - 250, CY)
                b.velocity = ((xl - xl_prev) / dt, 0)
            else:
                b.position = (W - xl + 250, CY)
                b.velocity = (-(xl - xl_prev) / dt, 0)

    def add_ball(self, pos, vel, gen):
        m = 1.0
        b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, BALL_R))
        b.position = pos
        b.velocity = vel
        s = pymunk.Circle(b, BALL_R)
        s.elasticity, s.friction = 1.0, 0.0
        s.collision_type = 1
        self.space.add(b, s)
        self.balls[b] = {"id": self.next_id, "shape": s, "gen": gen}
        self.next_id += 1

    def _wall(self, arb, space, data):
        if len(self.events) < 200000:
            self.events.append(("bounce", self.t, None))

    def _plate_hit(self, arb, space, data):
        """閉じていく板に当たったボールは、板に押されていっしょに真ん中へ運ばれる(はさまれる)。"""
        b = arb.shapes[0].body
        info = self.balls.get(b)
        if info is None:
            return
        if (self.t % PERIOD) < PERIOD / 2 and abs(b.position.y - CY) < PRESS_H / 2:
            if "push" not in info:
                self.events.append(("bounce", self.t, None))
            info["push"] = -1 if b.position.x < W / 2 else 1

    def step(self, dt):
        t0 = self.t
        self.t += dt
        self._place_plates(self.t, dt)
        self.space.step(dt)
        # 速さはいつも同じ(重力も摩擦もない世界。押されて速くなりすぎたり、止まったりしない)
        xl = press_x(self.t)
        vx = (xl - press_x(self.t - dt)) / dt
        closing = (self.t % PERIOD) < PERIOD / 2
        for b, info in self.balls.items():
            side = info.get("push")
            if side is not None and closing and abs(b.position.y - CY) < PRESS_H / 2 + BALL_R:
                # 板の面にくっついて、板といっしょに動く
                b.velocity = (vx * -side, 0)
                fx = xl + BALL_R if side < 0 else W - xl - BALL_R
                b.position = (fx, b.position.y)
                continue
            info.pop("push", None)
            v = b.velocity
            n = v.length
            if n > 1e-6:
                b.velocity = v * (SPEED / n)
        ph0, ph = t0 % PERIOD, self.t % PERIOD
        # 閉じていく板のあいだにはさまれたボールは、つぶれて消える(板がぴったりくっつけるように)
        gap = 2 * (W / 2 - press_x(self.t))
        half = PERIOD / 2
        if ph < half + 0.01 and gap < BALL_R * 2.3:
            caught = [b for b, info in self.balls.items()
                      if (abs(b.position.x - W / 2) < gap / 2 + BALL_R * 0.6 or info.get("push") is not None)
                      and abs(b.position.y - CY) < PRESS_H / 2 + BALL_R * 0.3]
            for b in caught:
                info = self.balls.pop(b)
                self.space.remove(b, info["shape"])
                self.trapped.append((b.position.y, info["gen"]))
            if caught:
                self.events.append(("squash", self.t, len(caught)))
        if ph0 < half <= ph:
            self.events.append(("slam", self.t, None))
        if ph0 < half + 0.04 <= ph:
            self.events.append(("open", self.t, None))
        # 開き始めたら、はさまれたボールが2倍になって出てくる
        if ph0 < half + SPAWN_DELAY <= ph and self.trapped:
            k = 0
            for y, gen in self.trapped:
                for sgn in (-1, 1):
                    if len(self.balls) >= MAX_BALLS:
                        break
                    a = math.pi / 2 * sgn + self.rng.uniform(-0.35, 0.35)   # 上下にはじき出す(すぐ次のプレスにはさまれないように)
                    self.add_ball((W / 2 + self.rng.uniform(-3, 3), y + sgn * BALL_R * 0.6),
                                  (SPEED * math.cos(a), SPEED * math.sin(a)), gen + 1)
                k += 1
            self.trapped = []
            self.events.append(("split", self.t, (k, len(self.balls))))
        for b in list(self.balls):   # 箱を抜けたボール(めったにない)は消す
            x, y = b.position
            if not (X0 - 20 < x < X1 + 20 and Y0 - 20 < y < Y1 + 20):
                info = self.balls.pop(b)
                self.space.remove(b, info["shape"])
        if self.result is None:
            if len(self.balls) >= TARGET:
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
            frames.append({"t": g.t, "px": press_x(g.t), "n": len(g.balls) + len(g.trapped),
                           "balls": [(b.position.x, b.position.y, info["gen"], info["id"]) for b, info in g.balls.items()]})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else FV.DURATION
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "n": len(g.balls)}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["n"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    pick = succ if want == "success" else [r for r in rs if r[1] != "success"]
    pick.sort(key=lambda r: -r[2] if want == "success" else -r[3])
    for r in pick[:15]:
        print(f"seed={r[0]:4d}  {r[1]}  {r[2]:5.2f}秒  {r[3]}個")


# ---------------------------------------------------------------- 描画
BG = (0.02, 0.025, 0.045)
GOLD = (1, 0.86, 0.2)


def draw_box(ctx):
    ctx.rectangle(X0, Y0, X1 - X0, Y1 - Y0)
    for wdt, a in ((22, 0.08), (10, 0.2), (5, 0.95)):
        ctx.set_source_rgba(0.6, 0.75, 0.95, a)
        ctx.set_line_width(wdt)
        ctx.stroke_preserve()
    ctx.new_path()


def draw_presses(ctx, xl, flash):
    """左右のプレス機:かべの油圧シリンダー → ピストン → 黄色と黒のしま模様の板(先に金属の面)。"""
    for side in (-1, 1):
        ctx.save()
        if side > 0:   # 右は左右反転
            ctx.translate(W, 0)
            ctx.scale(-1, 1)
        # かべのシリンダー
        ctx.rectangle(X0 - 30, CY - 90, 70, 180)
        g = cairo.LinearGradient(0, CY - 90, 0, CY + 90)
        g.add_color_stop_rgb(0, 0.5, 0.52, 0.58)
        g.add_color_stop_rgb(1, 0.22, 0.24, 0.28)
        ctx.set_source(g)
        ctx.fill()
        # ピストン
        face = xl
        body_l = face - 80
        ctx.rectangle(X0 + 40, CY - 22, max(0.0, body_l - X0 - 40), 44)
        g = cairo.LinearGradient(0, CY - 22, 0, CY + 22)
        g.add_color_stop_rgb(0, 0.45, 0.47, 0.52)
        g.add_color_stop_rgb(0.4, 0.95, 0.96, 1.0)
        g.add_color_stop_rgb(1, 0.4, 0.42, 0.46)
        ctx.set_source(g)
        ctx.fill()
        # 板(しま模様)
        ctx.save()
        ctx.rectangle(body_l, CY - PRESS_H / 2, 80, PRESS_H)
        ctx.clip()
        ctx.set_source_rgb(0.95, 0.75, 0.1)
        ctx.paint()
        ctx.set_source_rgb(0.08, 0.08, 0.08)
        for k in range(-8, 14):
            y = CY - PRESS_H / 2 + k * 44
            ctx.move_to(body_l, y)
            ctx.line_to(body_l, y + 22)
            ctx.line_to(body_l + 80, y + 62)
            ctx.line_to(body_l + 80, y + 40)
            ctx.close_path()
            ctx.fill()
        ctx.restore()
        ctx.rectangle(face - 14, CY - PRESS_H / 2, 14, PRESS_H)   # 先の金属の面
        g = cairo.LinearGradient(face - 14, 0, face, 0)
        g.add_color_stop_rgb(0, 0.35, 0.37, 0.42)
        g.add_color_stop_rgb(1, 0.85, 0.87, 0.92)
        ctx.set_source(g)
        ctx.fill()
        ctx.restore()
    if flash > 0:   # くっついた瞬間の光
        g = cairo.RadialGradient(W / 2, CY, 10, W / 2, CY, 380)
        g.add_color_stop_rgba(0, 1, 0.95, 0.7, 0.65 * flash)
        g.add_color_stop_rgba(1, 1, 0.9, 0.5, 0)
        ctx.set_source(g)
        ctx.arc(W / 2, CY, 380, 0, 2 * math.pi)
        ctx.fill()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"press_twin_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"press_twin_{seed}.wav")
    final = os.path.join(OUT_DIR, f"press_twin_{seed}.mp4")
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    ending = None if fail else FV.FruitFever(W, H, seed, W / 2, CY, main=f"{TARGET}個達成!!", count=f"{TARGET} / {TARGET}")
    born = {}
    sparks = []
    pluses = []
    rng = np.random.default_rng(seed + 7)
    last_slam = -9.0
    ev_i = 0
    prev_n = 1
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "slam":
                last_slam = et
            elif kind == "split":
                k, total = data
                for _ in range(min(40, 6 + k * 3)):
                    a = rng.uniform(0, 2 * math.pi)
                    sparks.append([W / 2, CY + rng.uniform(-PRESS_H / 2, PRESS_H / 2), math.cos(a) * rng.uniform(150, 600),
                                   math.sin(a) * rng.uniform(150, 600), et])
                pluses.append([et, f"+{k}" if k > 1 else "+1"])
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        if ending is not None and over:   # 1000個になった瞬間に虹色の演出
            ending.draw(surf, ctx, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - SCARE_DUR) if over else 0
        ctx.set_source_rgb(*BG)
        ctx.paint()
        g = cairo.RadialGradient(W / 2, CY, 50, W / 2, CY, 900)
        g.add_color_stop_rgba(0, 0.12, 0.14, 0.25, 0.8)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(g)
        ctx.paint()
        # はさまれる場所の目印(うっすら)
        draw_box(ctx)
        for x, y, gen, bid in fr["balls"]:
            if bid not in born:
                born[bid] = t
            a = t - born[bid]
            k = 1.0 if a > 0.15 else 0.7 + 0.3 * a / 0.15 + 0.25 * math.sin(math.pi * a / 0.15)
            BS.draw_ball(ctx, x, y, BALL_R * k, BS.color(gen))
        flash = max(0.0, 1 - (t - last_slam) / 0.25) if t - last_slam < 0.25 else 0.0
        draw_presses(ctx, fr["px"], flash)
        keep = []
        for s in sparks:
            a = t - s[4]
            if a < 0.35:
                ctx.arc(s[0] + s[2] * a, s[1] + s[3] * a, 3.5 * (1 - a / 0.35) + 0.5, 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.95, 0.6, 1 - a / 0.35)
                ctx.fill()
                keep.append(s)
        sparks = keep
        keep = []
        for p in pluses:   # 増えた数がポンと出る
            a = t - p[0]
            if a < 0.7:
                text(ctx, p[1], W / 2, CY - PRESS_H / 2 - 40 - 80 * a, 70 * (1.2 - 0.2 * min(1, a / 0.1)), rgb=GOLD, sw=10, alpha=1 - a / 0.7)
                keep.append(p)
        pluses = keep
        text(ctx, "1個のボールを", W / 2, 150, 72, sw=12)
        text(ctx, f"{TARGET}個に増やせる？", W / 2, 280, 104, rgb=GOLD, sw=16)
        n = fr["n"]
        pop = 1.0 + (0.25 if n > prev_n else 0.0)
        prev_n = n
        text(ctx, f"{min(n, TARGET)}", W / 2 - 50, 470, 100 * pop, rgb=(1, 1, 1), sw=12)
        text(ctx, f"/ {TARGET} 個", W / 2 + 180, 470, 46, rgb=(0.8, 0.85, 0.9), sw=6)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 1855, 56, rgb=(1, 0.4, 0.4) if left < 8 else (0.9, 0.9, 0.92), sw=8)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 1080, 130 * (1.15 - 0.15 * k), rgb=(1, 0.3, 0.3), sw=18)
            text(ctx, f"あと{TARGET - res['n']}個だったのに…", W / 2, 1210, 72, sw=12)
        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['n']}個 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
from press_split import note_hz, pop, slam, hiss  # noqa: E402   ポン・ガシャン・プシューは前の版と同じ音


def tick(seed):
    """ボールが壁に当たる小さな「コッ」(ビー玉のような軽い音)。"""
    rng = np.random.default_rng(seed)
    t = np.arange(int(0.05 * SR)) / SR
    f = rng.uniform(1800, 2600)
    return np.sin(2 * np.pi * f * t) * np.exp(-t * 120) + 0.3 * rng.normal(0, 1, len(t)) * np.exp(-t * 400)


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 3) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)

    def add(sig, t0, g=1.0, buf=None):
        b = out if buf is None else buf
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out:
            b[i:j] += g * sig[: j - i]

    last_tick = -1.0
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.01:
            continue
        if kind == "bounce":
            if t - last_tick > 0.045:   # 壁の音は間引いて、ザワザワしすぎないように
                add(tick(int(t * 1000)), t, 0.06)
                last_tick = t
        elif kind == "slam":
            add(slam(int(t * 100)), t, 0.55)
        elif kind == "open":
            add(hiss(int(t * 100)), t, 0.18)
        elif kind == "split":
            k, total = data
            base = int(2.2 * math.log2(max(2, total)))   # 数が増えるほど高い音から
            for j in range(min(8, k)):                  # 「ポポポポン」と駆け上がる
                add(pop(note_hz(base + j), j), t + 0.02 + j * 0.035, 0.32)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:
        add(FV.music(SR).mean(axis=1) * 1.6, end_t, 1.0, extra)
    wet = out.copy()
    for d, g in ((0.043, 0.25), (0.071, 0.18), (0.113, 0.12)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    ref = np.percentile(np.abs(wet[np.abs(wet) > 1e-4]), 99.5)
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int((end_t or duration) * SR)]
    rms = np.sqrt(np.mean(body ** 2))
    if rms > 0:   # 通常部分の平均音量を約 -18dB にそろえる
        wet *= min(4.0, 10 ** (-18.0 / 20) / rms)
    wet = wet + (0.95 if fail else 1.0) * extra[: len(wet)]
    mag = np.abs(wet)
    wet = np.where(mag < 0.7, wet, np.sign(wet) * (0.7 + 0.1 * np.tanh((mag - 0.7) / 0.1)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--want", choices=["fail", "success"], default="success")
    ap.add_argument("-n", type=int, default=200)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
