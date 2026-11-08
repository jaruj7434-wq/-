"""「1個のボールを時間内に512個に増やせる?」プレス機が一定のリズムで押しつぶすたびに、押されたボールが2個に分かれて増えていく物理ショート。

- 真ん中にプレス機。一定の速さで下りては上がる(PERIOD 秒ごと)。
- 下りてきた板に当たったボールは、2個に分かれて左右へ勢いよく飛び出す(1回のプレスで同じボールは1回だけ)。
- 床はまん中へ向かって下がる V 字の坂なので、飛び出したボールはまた転がってプレス機の下へ戻ってくる。
- 制限時間内に TARGET 個になれば成功、ならなければ失敗(幽霊)。動きは自然な物理のまま(ねらい・補正なし)。
- 音: プレスの「ガシャン」、上がるときの「プシュー」、ボールが増えるたびに「ポンッ」(数が増えるほど音が高くなっていく)。

使い方:
    python press_split.py search [--want fail|success] [-n 200]
    python press_split.py render --seed N
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
TARGET = int(os.environ.get("TARGET", 512))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 21.3))
BALL_R = float(os.environ.get("BALL_R", 12.0))
GRAVITY = 1800.0
BALL_E, BALL_F = 0.55, 0.3
EJECT = (float(os.environ.get("EJECT0", 450)), float(os.environ.get("EJECT1", 850)))   # 分かれたボールが飛び出す速さ
PERIOD = float(os.environ.get("PERIOD", 1.3))           # プレスの1往復の時間
DOWN, HOLD, UP = 0.22, 0.06, 0.32                       # 下りる・止まる・上がる時間(残りは上で待つ)
PRESS_W = float(os.environ.get("PRESS_W", 120.0))       # プレス板の幅
PRESS_TOP = 760.0                                       # 板の下面のいちばん上の位置
X0, X1 = 50.0, W - 50.0                                 # 左右のかべ
FLOOR_Y = 1640.0                                        # まん中の平らな床の高さ
SLOPE_Y = 1440.0                                        # 左右のかべぎわの床の高さ(V 字の坂)
PRESS_BOTTOM = FLOOR_Y - 14 - BALL_R * 2.0 + 1               # 板が下りきったときの下面(床のボールに触れる高さ)
CEIL_Y = 560.0                                          # 天井
MAX_BALLS = TARGET + 40
OUTRO = 2.5


def press_y(t):
    """プレス板の下面の高さ(一定の速さで下りて、少し止まって、上がる)。"""
    ph = t % PERIOD
    span = PRESS_BOTTOM - PRESS_TOP
    if ph < DOWN:
        return PRESS_TOP + span * ph / DOWN
    if ph < DOWN + HOLD:
        return PRESS_BOTTOM
    if ph < DOWN + HOLD + UP:
        return PRESS_BOTTOM - span * (ph - DOWN - HOLD) / UP
    return PRESS_TOP


class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 20
        self.space = sp
        st = sp.static_body
        hx = PRESS_W / 2 + 10
        pts = [(X0, CEIL_Y), (X0, SLOPE_Y), (W / 2 - hx, FLOOR_Y), (W / 2 + hx, FLOOR_Y), (X1, SLOPE_Y), (X1, CEIL_Y), (X0, CEIL_Y)]
        for a, b in zip(pts, pts[1:]):
            s = pymunk.Segment(st, a, b, 14)   # 太めにして、押しつぶされたボールが床を突き抜けないように
            s.elasticity, s.friction = 0.5, 0.4
            sp.add(s)
        # プレス板(決まった動きをする板)
        self.plate = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.plate.position = (W / 2, PRESS_TOP - 30)
        ps = pymunk.Poly.create_box(self.plate, (PRESS_W, 60))
        ps.elasticity, ps.friction = 0.3, 0.5
        ps.collision_type = 5
        sp.add(self.plate, ps)
        sp.on_collision(1, 5, begin=self._pressed, pre_solve=self._pressed)
        self.balls = {}   # body -> {"id", "shape", "gen", "stroke"}
        self.next_id = 0
        self.t = 0.0
        self.stroke = 0
        self.to_split = []
        self.events = []
        self.result, self.result_t = None, None
        self.escaped = 0
        self.add_ball((W / 2 + self.rng.uniform(-40, 40), 900.0), (self.rng.uniform(-60, 60), 0), 0)

    def add_ball(self, pos, vel, gen):
        m = 1.0
        b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, BALL_R))
        b.position = pos
        b.velocity = vel
        s = pymunk.Circle(b, BALL_R)
        s.elasticity, s.friction = BALL_E, BALL_F
        s.collision_type = 1
        self.space.add(b, s)
        self.balls[b] = {"id": self.next_id, "shape": s, "gen": gen, "stroke": -1}
        self.next_id += 1
        return b

    def _pressed(self, arb, space, data):
        arb.process_collision = False   # 板はボールを押しこまない(床を突き抜けないように)。触れたボールが分かれて飛び出す
        b = arb.shapes[0].body
        info = self.balls.get(b)
        if info is None or self.result is not None:
            return
        down = (self.t % PERIOD) < DOWN + HOLD
        if down and info["stroke"] != self.stroke:
            info["stroke"] = self.stroke
            self.to_split.append(b)

    def step(self, dt):
        t0 = self.t
        self.t += dt
        if int(self.t / PERIOD) != int(t0 / PERIOD):
            self.stroke += 1
        y = press_y(self.t)
        y_prev = press_y(t0)
        self.plate.position = (W / 2, y - 30)
        self.plate.velocity = (0, (y - y_prev) / dt)
        ph = self.t % PERIOD
        if (t0 % PERIOD) < DOWN <= ph:
            self.events.append(("slam", self.t, None))
        if (t0 % PERIOD) < DOWN + HOLD <= ph:
            self.events.append(("lift", self.t, None))
        self.to_split = []
        self.space.step(dt)
        n_split = 0
        for b in self.to_split:
            if b not in self.balls or len(self.balls) >= MAX_BALLS:
                continue
            info = self.balls.pop(b)
            self.space.remove(b, info["shape"])
            x, yb = b.position
            gen = info["gen"] + 1
            for sgn in (-1, 1):
                v = self.rng.uniform(*EJECT)
                nb = self.add_ball((x + sgn * BALL_R * 0.9, yb - BALL_R * 0.3), (sgn * v, self.rng.uniform(-350, -50)), gen)
                self.balls[nb]["stroke"] = self.stroke   # 同じプレスでもう一度分かれない
            n_split += 1
        if n_split:
            self.events.append(("split", self.t, (n_split, len(self.balls))))
        # かべを抜けたボール(めったにない)は消す
        for b in list(self.balls):
            if len(self.balls) == 0:
                break
            x, yb = b.position
            if not (X0 - 30 < x < X1 + 30 and CEIL_Y - 60 < yb < FLOOR_Y + 60):
                info = self.balls.pop(b)
                self.space.remove(b, info["shape"])
                self.escaped += 1
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
            frames.append({"t": g.t, "py": press_y(g.t), "n": len(g.balls),
                           "balls": [(b.position.x, b.position.y, info["gen"], info["id"]) for b, info in g.balls.items()]})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else FV.DURATION + 1.0
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "n": len(g.balls),
            "escaped": g.escaped}


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


def draw_arena(ctx):
    hx = PRESS_W / 2 + 10
    pts = [(X0, CEIL_Y), (X0, SLOPE_Y), (W / 2 - hx, FLOOR_Y), (W / 2 + hx, FLOOR_Y), (X1, SLOPE_Y), (X1, CEIL_Y)]
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    for wdt, a in ((18, 0.08), (8, 0.2), (4, 0.95)):
        ctx.set_source_rgba(0.6, 0.75, 0.95, a)
        ctx.set_line_width(wdt)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke_preserve()
    ctx.new_path()


def draw_press(ctx, y, t, flash):
    """プレス機:上の油圧シリンダー → ピストン → 黄色と黒のしま模様の板。"""
    cx = W / 2
    # 本体(上の箱)
    ctx.rectangle(cx - 190, CEIL_Y - 150, 380, 120)
    g = cairo.LinearGradient(0, CEIL_Y - 150, 0, CEIL_Y - 30)
    g.add_color_stop_rgb(0, 0.45, 0.48, 0.55)
    g.add_color_stop_rgb(1, 0.22, 0.24, 0.28)
    ctx.set_source(g)
    ctx.fill()
    for k in range(4):   # ボルト
        ctx.arc(cx - 160 + k * 107, CEIL_Y - 90, 9, 0, 2 * math.pi)
        ctx.set_source_rgb(0.7, 0.72, 0.76)
        ctx.fill()
    # ピストン(光る金属の棒)
    top = CEIL_Y - 30
    ctx.rectangle(cx - 22, top, 44, y - 60 - top)
    g = cairo.LinearGradient(cx - 22, 0, cx + 22, 0)
    g.add_color_stop_rgb(0, 0.45, 0.47, 0.52)
    g.add_color_stop_rgb(0.4, 0.95, 0.96, 1.0)
    g.add_color_stop_rgb(1, 0.4, 0.42, 0.46)
    ctx.set_source(g)
    ctx.fill()
    # 板
    ctx.save()
    ctx.rectangle(cx - PRESS_W / 2, y - 60, PRESS_W, 60)
    ctx.clip()
    ctx.set_source_rgb(0.95, 0.75, 0.1)
    ctx.paint()
    ctx.set_source_rgb(0.08, 0.08, 0.08)
    for k in range(-6, 12):
        x = cx - PRESS_W / 2 + k * 44
        ctx.move_to(x, y - 60)
        ctx.line_to(x + 22, y - 60)
        ctx.line_to(x + 82, y)
        ctx.line_to(x + 60, y)
        ctx.close_path()
        ctx.fill()
    ctx.restore()
    ctx.rectangle(cx - PRESS_W / 2, y - 12, PRESS_W, 12)
    ctx.set_source_rgb(0.3, 0.32, 0.36)
    ctx.fill()
    if flash > 0:   # 押した瞬間の光
        g = cairo.RadialGradient(cx, y, 10, cx, y, 360)
        g.add_color_stop_rgba(0, 1, 0.95, 0.7, 0.6 * flash)
        g.add_color_stop_rgba(1, 1, 0.9, 0.5, 0)
        ctx.set_source(g)
        ctx.arc(cx, y, 360, 0, 2 * math.pi)
        ctx.fill()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"press_split_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"press_split_{seed}.wav")
    final = os.path.join(OUT_DIR, f"press_split_{seed}.mp4")
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    ending = None if fail else FV.FruitFever(W, H, seed, W / 2, 1100, main=f"{TARGET}個達成!!", count=f"{TARGET} / {TARGET}")
    born = {}
    sparks = []
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
                for _ in range(min(30, data[0] * 2)):
                    a = rng.uniform(math.pi, 2 * math.pi)
                    sparks.append([W / 2 + rng.uniform(-PRESS_W / 2, PRESS_W / 2), press_y(et), math.cos(a) * rng.uniform(200, 700),
                                   math.sin(a) * rng.uniform(100, 500), et])
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        if ending is not None and over and t - end_t >= 1.0:
            ending.draw(surf, ctx, t - end_t - 1.0)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - SCARE_DUR) if over else 0
        ctx.set_source_rgb(*BG)
        ctx.paint()
        g = cairo.RadialGradient(W / 2, 1200, 50, W / 2, 1200, 1000)
        g.add_color_stop_rgba(0, 0.12, 0.14, 0.25, 0.8)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(g)
        ctx.paint()
        draw_arena(ctx)
        # ボール(生まれた直後はぷくっと)
        for x, y, gen, bid in fr["balls"]:
            if bid not in born:
                born[bid] = t
            a = t - born[bid]
            k = 1.0 if a > 0.15 else 0.7 + 0.3 * a / 0.15 + 0.2 * math.sin(math.pi * a / 0.15)
            BS.draw_ball(ctx, x, y, BALL_R * k, BS.color(gen))
        flash = max(0.0, 1 - (t - last_slam) / 0.2) if t - last_slam < 0.2 else 0.0
        draw_press(ctx, fr["py"], t, flash)
        keep = []
        for s in sparks:
            a = t - s[4]
            if a < 0.35:
                x = s[0] + s[2] * a
                y = s[1] + s[3] * a + 900 * a * a
                ctx.arc(x, y, 3.5 * (1 - a / 0.35) + 0.5, 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.95, 0.6, 1 - a / 0.35)
                ctx.fill()
                keep.append(s)
        sparks = keep
        # 上の文字
        text(ctx, "1個のボールを", W / 2, 140, 70, sw=12)
        text(ctx, f"{TARGET}個に増やせる？", W / 2, 260, 100, rgb=GOLD, sw=16)
        n = fr["n"]
        pop = 1.0 + (0.25 if n > prev_n else 0.0)
        prev_n = n
        text(ctx, f"{min(n, TARGET)}", W / 2, 400, 96 * pop, rgb=(1, 1, 1), sw=12)
        text(ctx, f"/ {TARGET} 個", W / 2 + 190, 400, 44, rgb=(0.8, 0.85, 0.9), sw=6)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 1800, 56, rgb=(1, 0.4, 0.4) if left < 8 else (0.9, 0.9, 0.92), sw=8)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 1050, 130 * (1.15 - 0.15 * k), rgb=(1, 0.3, 0.3), sw=18)
            text(ctx, f"あと{TARGET - res['n']}個だったのに…", W / 2, 1180, 72, sw=12)
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
PENTA = [0, 2, 4, 7, 9]


def note_hz(i):
    """ペンタトニック(どれを鳴らしてもきれいに聞こえる音階)の i 番目の音。"""
    return 220.0 * 2 ** ((12 * (i // 5) + PENTA[i % 5]) / 12)


def pop(f, seed):
    """ボールが増える「ポンッ」(泡がはじけるような、高さが少し下がる丸い音)。"""
    t = np.arange(int(0.18 * SR)) / SR
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.5 * np.exp(-t * 60))) / SR
    y = np.sin(ph) + 0.25 * np.sin(2 * ph) * np.exp(-t * 30)
    return y * np.minimum(1, t / 0.002) * np.exp(-t * 22)


def slam(seed):
    """プレスの「ガシャン」(重い低音+金属のひびき)。"""
    rng = np.random.default_rng(seed)
    t = np.arange(int(0.6 * SR)) / SR
    n = rng.normal(0, 1, len(t))
    y = np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-t * 25)) / SR) * np.exp(-t * 9)
    y += 0.35 * sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in ((420, 1, 14), (1130, 0.6, 18), (2310, 0.35, 25)))
    y += 0.3 * (n - np.convolve(n, np.ones(4) / 4, "same")) * np.exp(-t * 40)
    return y


def hiss(seed):
    """プレスが上がるときの「プシュー」(空気が抜ける音)。"""
    rng = np.random.default_rng(seed)
    t = np.arange(int(0.3 * SR)) / SR
    n = rng.normal(0, 1, len(t))
    y = n - np.convolve(n, np.ones(3) / 3, "same")
    return y * np.minimum(1, t / 0.03) * np.exp(-t * 9)


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

    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.01:
            continue
        if kind == "slam":
            add(slam(int(t * 100)), t, 0.55)
        elif kind == "lift":
            add(hiss(int(t * 100)), t, 0.18)
        elif kind == "split":
            k, total = data
            base = int(2.2 * math.log2(max(2, total)))   # 数が増えるほど高い音から
            for j in range(min(6, k)):                  # 「ポポポポン」と駆け上がる
                add(pop(note_hz(base + j), j), t + j * 0.035, 0.32)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:
        add(FV.music(SR).mean(axis=1) * 1.6, end_t + 1.0, 1.0, extra)
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
