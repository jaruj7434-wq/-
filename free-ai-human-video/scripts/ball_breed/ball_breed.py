"""「ボールを1000個に増やせる?」丸いわくの中で、ボールが当たるたびに1個ずつ増えていく物理ショート。

- 丸いわくの中を、はじめは2個の小さなボールが、ゆっくり跳ね返りながら軌道どおりに動く(重力・摩擦なし。いつも同じ速さ)。
- ボールとボールが触れたら必ず1個増える(そのあいだから1個生まれる)。わくに当たっても増えない。
  新しいボールは、ほかのボールと重ならない近くの空いている所に生まれる(触れても増えない、ということはない)。
- ボールの大きさはずっと同じ。1個ずつちがう、あざやかな色。ねらって近づけることはしない(補正なし)。
- 制限時間内に 1000 個になれば成功(天使)、ならなければ失敗(幽霊)。
- ボールが生まれる瞬間に、かん高い鳴き声のような「ピヨッ」。

使い方:
    python ball_breed.py search [-n 200]
    python ball_breed.py render --seed N
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
from fail_bgm import fail_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

TARGET = int(os.environ.get("TARGET", 500))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 60.0))
CX, CY, R = 540.0, 1130.0, float(os.environ.get("ARENA_R", 460.0))
R0 = float(os.environ.get("R0", 10.0))                                            # はじめのボールの大きさ(半径)
SPEED = float(os.environ.get("SPEED", 400.0))       # ボールの速さ(いつも同じ)
MATURE = 0.0                                         # (数えない時間はなし。触れたら必ず増える)
N_FULL = 30.0
N_START = int(os.environ.get("N_START", 2))          # はじめのボールの数
MIN_R = 6.0
MAX_OBJ = TARGET + 40
OUTRO = 4.2
FAIL_SHOW = 0.0   # 時間切れになった瞬間に幽霊が出る


def size_for(n):
    return R0   # ボールの大きさはずっと同じ


class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, 0)
        sp.iterations = 12
        self.space = sp
        n = 96
        pts = [(CX + (R + 14) * math.cos(2 * math.pi * k / n), CY + (R + 14) * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
        for a, b in zip(pts, pts[1:]):
            s = pymunk.Segment(sp.static_body, a, b, 14)
            s.elasticity, s.friction = 1.0, 0.0
            s.collision_type = 2
            sp.add(s)
        self.r = R0
        self.objs = {}
        self.next_id = 0
        self.t = 0.0
        self.events = []
        self.pairs = []
        self.result, self.result_t = None, None
        # スタート:2個を向かい合わせに置く(始まってすぐ当たって3個になる)。少しだけずらすので、当たり方は毎回ちがう
        y0 = CY + rng.uniform(-120, 120)
        off = rng.uniform(-0.8, 0.8) * R0            # 正面からのずれ(2個の半径より小さいので必ず当たる)
        d0 = rng.uniform(150, 220)
        tilt = rng.uniform(-0.25, 0.25)
        ca, sa = math.cos(tilt), math.sin(tilt)
        for sgn in (-1, 1):
            px, py = sgn * d0, (off / 2) * sgn
            pos = (CX + px * ca - py * sa, y0 + px * sa + py * ca)
            vel = (-sgn * SPEED * ca, -sgn * SPEED * sa)
            self.add(pos, vel, born=-MATURE, parent_col=None)
        sp.on_collision(1, 1, begin=self._touch)
        sp.on_collision(1, 2, post_solve=self._wall)
        self.walls = []

    def add(self, pos, vel, born, parent_col):
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, self.r))
        b.position = pos
        b.velocity = vel
        s = pymunk.Circle(b, self.r)
        s.elasticity, s.friction = 1.0, 0.0
        s.collision_type = 1
        self.space.add(b, s)
        hue = self.rng.uniform(0, 1)   # 1個ずつちがう、あざやかな色
        self.objs[b] = {"id": self.next_id, "shape": s, "born": born, "ready": born + MATURE, "hue": hue}
        self.next_id += 1
        return b

    def free_spot(self, mid, perp):
        """生まれる場所:当たった所(2つのボールのあいだ)のすぐ横で、ほかのボールと重ならない所。
        重なると、生まれた瞬間に「当たった」ことになるため、重ならないぎりぎりの所から順にさがす。"""
        base = math.atan2(perp.y, perp.x)
        offs = [0.0, math.pi]
        for k in range(1, 6):
            for sgn in (1, -1):
                offs += [sgn * k * math.pi / 8, math.pi + sgn * k * math.pi / 8]
        best, best_d = None, -1e9
        for dist in (1.75, 1.9, 2.1, 2.4, 2.8, 3.3, 4.0, 5.0, 6.5, 8.5):
            for o in offs:
                p = mid + pymunk.Vec2d(math.cos(base + o), math.sin(base + o)) * self.r * dist
                if (p - (CX, CY)).length > R - self.r - 1:
                    continue
                q = self.space.point_query_nearest(p, self.r + 0.3, pymunk.ShapeFilter())   # ふちまでの距離が半径より近いと重なる
                if q is None or q.shape is None or q.shape.collision_type != 1:
                    return p
                if q.distance > best_d:
                    best, best_d = p, q.distance
        return best if best is not None else mid

    def _touch(self, arb, space, data):
        a, b = (s.body for s in arb.shapes)
        if a not in self.objs or b not in self.objs:
            return True
        self.pairs.append((a, b))   # 当たったら必ず1個増える
        return True

    def _wall(self, arb, space, data):
        """わくに当たったときは増えない(音だけ)。"""
        if arb.is_first_contact and len(self.events) < 400000:
            self.events.append(("wall", self.t, None))

    def _wall_begin(self, arb, space, data):
        """わくに当たったときも1個増える(はじめの1個は、わくに当たって増えていく)。"""
        for sh in arb.shapes:
            info = self.objs.get(sh.body)
            if info is not None and self.t >= info["ready"]:
                self.walls.append(sh.body)
        return True

    def step(self, dt):
        self.t += dt
        self.space.step(dt)
        k = 1 - math.exp(-dt / 0.6)
        for b in self.objs:   # いつも同じ速さ(ぶつかって速さが変わっても、ゆっくりもどる)
            v = b.velocity
            n = v.length
            if n > 1e-6:
                b.velocity = v * ((n + (SPEED - n) * k) / n)
        # ボールとボールが触れたら、必ず1個生まれる(1回触れるごとに1個。数えない時間はなし)
        for a, b in self.pairs:
            if a not in self.objs or b not in self.objs or len(self.objs) >= MAX_OBJ:
                continue
            mid = (a.position + b.position) / 2
            d = b.position - a.position
            if d.length < 1e-6:
                d = pymunk.Vec2d(1, 0)
            perp = pymunk.Vec2d(-d.y, d.x).normalized() * (1 if self.rng.random() < 0.5 else -1)
            pos = self.free_spot(mid, perp)
            out = pos - mid
            vel = out.normalized() * SPEED if out.length > 1e-6 else perp * SPEED
            self.add(pos, vel, self.t, None)
            self.events.append(("born", self.t, (pos.x, pos.y, len(self.objs))))
        self.pairs = []
        for b in self.walls:
            info = self.objs.get(b)
            if info is None or len(self.objs) >= MAX_OBJ:
                continue
            info["ready"] = self.t + MATURE
            nrm = (b.position - (CX, CY)).normalized()   # わくから中心へ
            pos = b.position - nrm * self.r * 2.6
            tang = pymunk.Vec2d(-nrm.y, nrm.x) * (1 if self.rng.random() < 0.5 else -1)
            vel = (tang * 0.6 - nrm * 0.8).normalized() * SPEED
            self.add(pos, vel, self.t, None)
            self.events.append(("born", self.t, (pos.x, pos.y, len(self.objs))))
            self.events.append(("wall", self.t, None))
        self.walls = []
        want = size_for(len(self.objs))
        if want < self.r - 0.01:
            self.r = max(want, self.r - 15.0 * dt)
            for info in self.objs.values():
                info["shape"].unsafe_set_radius(self.r)
        for b in list(self.objs):   # わくの外へぬけたもの(めったにない)はもどす
            if (b.position - (CX, CY)).length > R:
                d = (b.position - (CX, CY)).normalized()
                b.position = pymunk.Vec2d(CX, CY) + d * (R - self.r - 2)
                b.velocity = -d * SPEED
        if self.result is None:
            if len(self.objs) >= TARGET:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, None))
            if self.result is not None:
                self.final_n = len(self.objs)


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "r": g.r, "n": len(g.objs),
                           "objs": [(b.position.x, b.position.y, i["id"], i["born"], i["hue"], g.t >= i["ready"])
                                    for b, i in g.objs.items()]})
        if g.result is not None:
            extra = FAIL_SHOW + OUTRO + SCARE_DUR if g.result == "fail" else 8.5
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "n": g.final_n}


def score(seed):
    r = simulate(seed)
    t1000 = next((e[1] for e in r["events"] if e[0] == "born" and e[2][2] >= TARGET), None)
    t100 = next((e[1] for e in r["events"] if e[0] == "born" and e[2][2] >= 100), None)
    first = next((e[1] for e in r["events"] if e[0] == "born"), None)
    return seed, r["result"], round(r["result_t"], 1), r["n"], first and round(first, 1), t100 and round(t100, 1)


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def hsv(h, s, v):
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p, q, t_ = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    return [(v, t_, p), (q, v, p), (p, v, t_), (p, q, v), (t_, p, v), (v, p, q)][i]


def draw_ball(ctx, x, y, r, hue, ready, eyes):
    col = hsv(hue, 0.95, 1.0)   # 目立つ、あざやかな色(1個ずつちがう)
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.05, x, y, r)
    g.add_color_stop_rgb(0, *(min(1, c + 0.45) for c in col))
    g.add_color_stop_rgb(0.4, *col)
    g.add_color_stop_rgb(1, *(c * 0.7 for c in col))
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()
    if eyes:   # 小さな目(ひよこみたいに)
        for dx in (-0.3, 0.3):
            ctx.arc(x + dx * r, y - 0.05 * r, max(1.2, 0.11 * r), 0, 2 * math.pi)
            ctx.set_source_rgb(0.1, 0.08, 0.1)
            ctx.fill()
        ctx.move_to(x - 0.12 * r, y + 0.18 * r)   # くちばし
        ctx.line_to(x + 0.12 * r, y + 0.18 * r)
        ctx.line_to(x, y + 0.36 * r)
        ctx.close_path()
        ctx.set_source_rgb(1.0, 0.6, 0.1)
        ctx.fill()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"ball_breed_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"ball_breed_{seed}.wav")
    final = os.path.join(OUT_DIR, f"ball_breed_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"bb_preview_{pt:.1f}.png"))
                self.fi += 1
        ff = _P()
        frames = [f for f in frames if f["t"] <= max(preview) + 0.05]
    else:
        ff = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
             "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
            stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    angels = None
    if not fail:
        from angels import AngelShow
        angels = AngelShow(W, H, seed)
    rng = np.random.default_rng(seed + 3)
    rings = []   # 生まれた瞬間の光の輪 [x, y, t0]
    frozen = None
    t_goal = next((e[1] for e in events if e[0] == "born" and e[2][2] >= TARGET), None)
    late = (t_goal - end_t) if (fail and t_goal is not None and t_goal <= end_t + FAIL_SHOW) else None
    ev_i = 0
    prev_n = 2
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "born" and len(rings) < 60:
                rings.append([data[0], data[1], et])
            ev_i += 1
        over = end_t is not None and t >= end_t
        if fail and over and FAIL_SHOW == 0:   # 失敗したら、時間切れの瞬間の画面のまま止める
            if frozen is None:
                frozen = fr
            fr = frozen
        g0 = end_t + FAIL_SHOW if fail else None   # 幽霊が出る時刻
        if ghost is not None and t >= g0 and t - g0 < SCARE_DUR:
            ghost.draw(surf, t - g0)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - g0 - SCARE_DUR) if (fail and t >= g0) else 0
        g = cairo.LinearGradient(0, 0, 0, H)
        g.add_color_stop_rgb(0, 0.12, 0.1, 0.22)
        g.add_color_stop_rgb(1, 0.05, 0.04, 0.1)
        ctx.set_source(g)
        ctx.paint()
        g = cairo.RadialGradient(CX, CY, 40, CX, CY, R)
        g.add_color_stop_rgb(0, 0.98, 0.95, 0.88)
        g.add_color_stop_rgb(1, 0.88, 0.84, 0.78)
        ctx.set_source(g)
        ctx.arc(CX, CY, R, 0, 2 * math.pi)
        ctx.fill()
        for wdt, a in ((30, 0.1), (14, 0.25), (7, 1.0)):
            ctx.arc(CX, CY, R + 7, 0, 2 * math.pi)
            ctx.set_source_rgba(1.0, 0.75, 0.35, a)
            ctx.set_line_width(wdt)
            ctx.stroke()
        r = fr["r"]
        eyes = False   # 顔はなし(シンプルに)
        for x, y, oid, born, hue, ready in fr["objs"]:
            a = t - born
            k = 1.0   # 当たった瞬間に、最初から同じ大きさで出る
            draw_ball(ctx, x, y, r * 0.93 * k, hue, ready, eyes)   # 当たり判定より少しだけ小さく描く(画面で触れて見えたら、必ず本当に当たっている)
        keep = []
        for rg in rings:
            a = t - rg[2]
            if a < 0.35:
                ctx.arc(rg[0], rg[1], r * (1 + 3 * a), 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.9, 0.4, 0.8 * (1 - a / 0.35))
                ctx.set_line_width(3)
                ctx.stroke()
                keep.append(rg)
        rings = keep
        if angels is not None and over:
            angels.draw(ctx, t - end_t)
        text(ctx, "ボールを", W / 2, 150, 80, sw=12)
        text(ctx, f"{TARGET}個に増やせる？", W / 2, 280, 108, rgb=GOLD, sw=16)
        n = min(fr["n"], TARGET)   # 時間切れのあとも、そのまま数え続ける
        bump = 1.0 + (0.15 if n > prev_n else 0)
        prev_n = n
        text(ctx, f"{n}", W / 2 - 90, 500, 110 * bump, rgb=(1, 1, 1), sw=12)
        text(ctx, f"/ {TARGET} 個", W / 2 + 170, 500, 50, rgb=(0.85, 0.85, 0.9), sw=6)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 1760, 64, rgb=(1, 0.4, 0.4) if left < 8 else (0.95, 0.95, 0.95), sw=10)
        if over and fail and t < g0:   # 時間切れの直後:物理はそのまま。何秒おそかったかを見せる
            k = min(1.0, (t - end_t) / 0.15)
            text(ctx, "時間切れ!!", W / 2, 680, 120 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"(時間切れのときは {res['n']}個)", W / 2, 790, 54, sw=10)
            if late is not None and t >= end_t + late:
                text(ctx, f"{TARGET}個まで、あと{late:.1f}秒だった…", W / 2, 1720 - 120, 64, rgb=(1, 0.85, 0.3), sw=12)
        elif over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 1000, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{late:.1f}秒だったのに…" if late is not None else f"あと{TARGET - res['n']}個だったのに…",
                 W / 2, 1130, 72, sw=12)
        elif over:
            text(ctx, f"{TARGET}個達成!!", W / 2, 700, 120, rgb=GOLD, sw=18)
        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
    if preview:
        return
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
def piyo(rng, amp=1.0):
    """かん高い鳴き声のような「ピヨッ」(ピ:高く短く → ヨ:少し下がる)。高さは毎回少しちがう。"""
    p = rng.uniform(0.85, 1.2)
    d1, d2 = 0.045, 0.09
    t1 = np.arange(int(d1 * SR)) / SR
    f1 = p * (2900 + 600 * t1 / d1)
    t2 = np.arange(int(d2 * SR)) / SR
    f2 = p * (2600 - 900 * (t2 / d2) ** 0.7) * (1 + 0.04 * np.sin(2 * np.pi * 28 * t2))
    f = np.concatenate([f1, np.full(int(0.012 * SR), f1[-1] * 0.9), f2])
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)
    n = len(y)
    env = np.ones(n)
    a = int(0.004 * SR)
    env[:a] = np.linspace(0, 1, a)
    i1 = len(t1)
    env[i1:i1 + int(0.012 * SR)] *= 0.35   # ピ と ヨ のあいだの小さな切れ目
    env[-int(0.03 * SR):] *= np.linspace(1, 0, int(0.03 * SR))
    return amp * y * env


def music_box_bgm(dur, n_out):
    """オルゴールの軽いBGM(ハ長調・テンポ120・4小節をくり返す)。"""
    out = np.zeros(n_out)
    beat = 0.5
    seq = [72, 76, 79, 76, 77, 81, 79, 76, 74, 77, 81, 77, 76, 79, 84, 79]
    roots = [48, 53, 50, 55]
    hz = lambda m: 440.0 * 2 ** ((m - 69) / 12)   # noqa: E731
    t = 0.0
    k = 0
    while t < dur:
        m = seq[k % len(seq)]
        tt = np.arange(int(0.9 * SR)) / SR
        sig = (np.sin(2 * np.pi * hz(m) * tt) + 0.3 * np.sin(2 * np.pi * hz(m) * 2.01 * tt) * np.exp(-tt * 6)) * np.exp(-tt * 3.5)
        if k % 4 == 0:
            r_ = roots[(k // 4) % 4]
            sig = sig + 0.6 * np.sin(2 * np.pi * hz(r_) * tt) * np.exp(-tt * 2.5)
        i = int(t * SR)
        j = min(n_out, i + len(sig), int(dur * SR))
        if j > i:
            out[i:j] += sig[: j - i] * np.minimum(1, (dur - (i + np.arange(j - i)) / SR) / 0.3)
        t += beat / 2
        k += 1
    return out


def pop_s(amp, f=420):
    t = np.arange(int(0.05 * SR)) / SR
    return amp * np.sin(2 * np.pi * f * t) * np.exp(-t * 70)


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)

    def add(sig, t0, gain=1.0, buf=None):
        b = out if buf is None else buf
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out and j > i:
            b[i:j] += gain * sig[: j - i]
    rng = np.random.default_rng(7)
    last_w = -1.0
    recent = []
    for kind, t, data in events:
        if end_t is not None and t > end_t + (FAIL_SHOW if fail else 0.01):
            continue
        if kind == "born":
            # 数が少ないうちは1回ずつはっきり。多くなったら、たくさん重なって「ピヨピヨピヨ…」の大合唱
            recent = [x for x in recent if t - x < 0.25]
            if len(recent) < 10:
                add(piyo(rng), t, 0.9 / (1 + 0.15 * len(recent)))
                recent.append(t)
        elif kind == "wall":
            if t - last_w > 0.08:
                add(pop_s(0.25, rng.uniform(300, 500)), t)
                last_w = t
    if fail:
        sig = scream(SR)
        i0 = int((end_t + FAIL_SHOW) * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
        sig = fail_music(SR, OUTRO)
        i0 = int((end_t + FAIL_SHOW + SCARE_DUR) * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += 0.6 * sig[:m]
    else:
        from angels import holy_music
        sig = holy_music(SR, 8.5)
        i0 = int(end_t * SR) + int(0.5 * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += 0.85 * sig[:m]
    # 効果音の音量を時間でならす(はじめの静かなところも、ピヨッとポコッがはっきり聞こえるように)
    win = int(0.6 * SR)
    pw = np.convolve(out ** 2, np.ones(win) / win, "same")
    agc = np.clip(0.08 / np.sqrt(pw + 1e-8), 0.6, 9.0)
    agc = np.convolve(agc, np.ones(win) / win, "same")
    out = out * agc
    # (プレイ中のBGMはなし。効果音だけ)
    wet = out.copy()
    for dd, g in ((0.043, 0.22), (0.071, 0.15)):
        k = int(dd * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int(end_t * SR)]
    rms = np.sqrt(np.mean(body ** 2))
    if rms > 0:
        wet *= min(6.0, 10 ** (-14.0 / 20) / rms)
    wet = wet + (0.95 if fail else 1.0) * extra[: len(wet)]
    mag = np.abs(wet)
    wet = np.where(mag < 0.7, wet, np.sign(wet) * (0.7 + 0.2 * np.tanh((mag - 0.7) / 0.2)))
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
