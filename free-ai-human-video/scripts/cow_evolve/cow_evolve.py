"""「子牛を合体させて巨大な雄牛にできる?」本物の写真の牛が落ちてきて、同じ大きさどうしがぶつかると進化する物理ショートを生成する。

- 牛の写真(Higgs Field で生成・背景透明)5段階:生まれたての子牛 → 子牛 → 若い牛 → 大人の牛 → 巨大な雄牛(ゴール)
- 写真の輪郭(凸包)そのものを当たり判定にして、重力・摩擦・回転のまま自然に落ちて転がる(ねらい・補正なし)。
  止まった牛は眠らせて(動かなくなって)永久には動き続けない。
- 同じ段階の牛どうしが触れると合体して1段階大きくなり、その段階の本物の鳴き声(Wikimedia Commons の録音)が鳴る。
- 入れ物は底の丸い大きなボウル。巨大な雄牛ができれば成功(天使)、時間切れかボウルからあふれたら失敗(幽霊)。

使い方:
    python fetch_assets.py              # 写真と鳴き声を集める(初回のみ)
    python cow_evolve.py search [--want fail|success] [-n 200]
    python cow_evolve.py render --seed N
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
from ball_escape import text  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from angels import DURATION as ANGEL_DUR, AngelShow, holy_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
GRAVITY = 1800.0

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
IMG_DIR = os.path.join(ROOT, "assets", "source", "cow")
SND_DIR = os.path.join(IMG_DIR, "sounds")
OUT_DIR = os.path.join(ROOT, "assets", "output")

NAMES = ["生まれたての子牛", "子牛", "若い牛", "大人の牛", "巨大な雄牛"]
SHORT = ["赤ちゃん", "子牛", "若牛", "大人", "雄牛"]
GOAL = len(NAMES) - 1
WIDTHS = [118, 170, 240, 330, 470]     # 段階ごとの写真の横幅(px)

# 底の丸いボウル
BOWL_CX, BOWL_CY, BOWL_R = 540.0, 1200.0, 470.0
BOWL_TOP = 700.0                       # 左右のまっすぐな壁の上端
OVER_Y = 760.0                         # 止まった牛の上端がこれより上ならあふれ
OVER_WAIT = 1.5
DROP_Y = 520.0
DROP_X0, DROP_X1 = 230.0, 850.0
DROP_EVERY = 0.85
P_STAGE2 = 0.18                        # 落ちてくるのが「子牛」のことがある確率
TIME_LIMIT = 17.0
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
        path = os.path.join(IMG_DIR, f"cow{stage + 1}.png")
        if not os.path.exists(path):
            raise SystemExit(f"写真がありません: {path}\n先に python fetch_assets.py を実行してください")
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
    pts = [(BOWL_CX - BOWL_R, BOWL_TOP)]
    for k in range(41):
        a = math.pi - math.pi * k / 40
        pts.append((BOWL_CX + BOWL_R * math.cos(a), BOWL_CY + BOWL_R * math.sin(a)))
    pts.append((BOWL_CX + BOWL_R, BOWL_TOP))
    return pts


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
            s = pymunk.Segment(sp.static_body, a, b, 8)
            s.elasticity, s.friction = 0.2, 0.8
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
        a, b = arb.shapes
        if self.result is None:
            self.pairs.append((a.body, b.body))

    def add(self, stage, x, y, ang=0.0, vx=0.0, vy=0.0, w=0.0):
        poly = self.polys[stage]
        mass = 1.0 * (WIDTHS[stage] / WIDTHS[0]) ** 2
        b = pymunk.Body(mass, pymunk.moment_for_poly(mass, poly))
        b.position, b.angle = (x, y), ang
        b.velocity, b.angular_velocity = (vx, vy), w
        s = pymunk.Poly(b, poly, radius=2)
        s.elasticity, s.friction = 0.15, 0.7
        s.collision_type = 10 + stage
        self.space.add(b, s)
        cow = {"id": self.next_id, "stage": stage, "body": b, "shape": s, "born": self.t}
        self.next_id += 1
        self.cows.append(cow)
        return cow

    def step(self, dt):
        self.t += dt
        if self.result is None and self.t >= self.next_drop:
            self.next_drop += DROP_EVERY
            stage = 1 if self.rng.random() < P_STAGE2 else 0
            x = self.rng.uniform(DROP_X0, DROP_X1)
            c = self.add(stage, x, DROP_Y, ang=self.rng.uniform(-0.3, 0.3),
                         vx=self.rng.uniform(-40, 40), w=self.rng.uniform(-1.5, 1.5))
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
            # 止まった牛がボウルのふちより上にはみ出していたら、あふれ(画面の座標は下向きなので bb.bottom が見た目の上端)
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
            print(f"seed={seed:4d}  最高 {NAMES[best]} / 大人の牛 {n3}頭 / {'時間切れ' if why == 'time' else 'あふれ'} {rt:5.2f}秒")
    else:
        for seed, _, rt, _, _, _ in sorted(succ, key=lambda r: -r[2])[:15]:
            print(f"seed={seed:4d}  雄牛 {rt:5.2f}秒")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def background():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, H)   # 夕方の牧場の空 → 草地
    g.add_color_stop_rgb(0, 0.10, 0.13, 0.25)
    g.add_color_stop_rgb(0.45, 0.42, 0.42, 0.55)
    g.add_color_stop_rgb(0.62, 0.62, 0.55, 0.45)
    g.add_color_stop_rgb(0.63, 0.24, 0.36, 0.17)
    g.add_color_stop_rgb(1, 0.10, 0.18, 0.08)
    ctx.set_source(g)
    ctx.paint()
    v = cairo.RadialGradient(W / 2, H / 2, 300, W / 2, H / 2, 1300)
    v.add_color_stop_rgba(0, 0, 0, 0, 0)
    v.add_color_stop_rgba(1, 0, 0, 0, 0.55)
    ctx.set_source(v)
    ctx.paint()
    return surf


def draw_bowl(ctx):
    pts = bowl_points()
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.set_source_rgba(0.85, 0.92, 1.0, 0.10)   # ガラスのボウル
    ctx.fill_preserve()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for wdt, al in ((30, 0.10), (16, 0.35), (6, 0.9)):
        ctx.set_source_rgba(0.85, 0.93, 1.0, al)
        ctx.set_line_width(wdt)
        ctx.stroke_preserve()
    ctx.new_path()
    # 光の反射
    ctx.arc(BOWL_CX, BOWL_CY, BOWL_R - 26, math.radians(140), math.radians(165))
    ctx.set_source_rgba(1, 1, 1, 0.5)
    ctx.set_line_width(8)
    ctx.stroke()
    # あふれライン
    ctx.new_path()
    ctx.move_to(BOWL_CX - BOWL_R + 10, OVER_Y)
    ctx.line_to(BOWL_CX + BOWL_R - 10, OVER_Y)
    ctx.set_dash([18, 14])
    ctx.set_source_rgba(1, 0.35, 0.35, 0.7)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.set_dash([])


def draw_chart(ctx, sprites, best, t):
    """上の進化表。5段階の写真を並べ、たどり着いた段階は明るく、ゴールは金の輪。"""
    y = 560
    xs = [120 + k * 210 for k in range(len(NAMES))]
    for k in range(len(NAMES) - 1):
        text(ctx, "▶", (xs[k] + xs[k + 1]) / 2, y + 14, 34, rgb=(1, 1, 1), sw=0, alpha=0.6)
    for k, x in enumerate(xs):
        goal = k == GOAL
        r = 80 if goal else 66
        reached = k <= best
        ctx.new_path()
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.16 if reached else 0.06)
        ctx.fill_preserve()
        if goal:
            pulse = 1 + 0.05 * math.sin(t * 5)
            ctx.set_source_rgba(*GOLD, 0.9)
            ctx.set_line_width(6 * pulse)
            ctx.stroke()
        else:
            ctx.new_path()
        sp = sprites[k]
        k_fit = (r * 1.7) / max(sp.w, sp.h)
        sp.draw(ctx, x, y, 0.0, k_fit, alpha=1.0 if (reached or goal) else 0.35)
        text(ctx, SHORT[k], x, y + r + 34, 30 if not goal else 36,
             rgb=GOLD if goal else ((1, 1, 1) if reached else (0.7, 0.7, 0.75)), sw=7)


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    sprites = [Sprite(k) for k in range(len(NAMES))]
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"cow_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"cow_{seed}.wav")
    final = os.path.join(OUT_DIR, f"cow_{seed}.mp4")
    bg = background()
    bctx = cairo.Context(bg)
    draw_bowl(bctx)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    angels = AngelShow(W, H, seed) if result == "success" else None
    born = {}         # 牛id → 生まれた時刻(合体で出てきた牛は少しふくらんで登場)
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
                shake = max(shake, 6 + 5 * st)
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0
        shake *= 0.85
        dx, dy = (math.sin(t * 61) * shake, math.cos(t * 53) * shake) if shake > 0.5 else (0, 0)

        ctx.set_source_surface(bg, dx, dy)
        ctx.paint()
        ctx.save()
        ctx.translate(dx, dy)
        for cid, st, x, y, ang in sorted(fr["cows"], key=lambda c: c[1]):
            b_t = born.get(cid)
            k = 1.0
            if b_t is not None and t - b_t < 0.25:   # 進化した直後はぷくっとふくらむ
                a = (t - b_t) / 0.25
                k = 0.7 + 0.3 * a + 0.12 * math.sin(a * math.pi)
            # 足元の影
            ctx.new_path()
            ctx.save()
            ctx.translate(x, y + sprites[st].h * 0.42)
            ctx.scale(sprites[st].w * 0.42, 10)
            ctx.arc(0, 0, 1, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgba(0, 0, 0, 0.18)
            ctx.fill()
            sprites[st].draw(ctx, x, y, ang, k)
        for p in pops:   # 進化の光の輪と名前
            age = t - p[0]
            if 0 <= age < 0.9:
                ctx.new_path()
                ctx.arc(p[1], p[2], 40 + 380 * age * (0.6 + 0.2 * p[3]), 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.95, 0.7, 0.8 * (1 - age / 0.9))
                ctx.set_line_width(10)
                ctx.stroke()
                text(ctx, f"{NAMES[p[3]]}に進化！", p[1], p[2] - 60 - 120 * age, 58 + 6 * p[3],
                     rgb=GOLD if p[3] == GOAL else (1, 1, 1), sw=12, alpha=min(1, 3 * (0.9 - age)))
        ctx.restore()
        if fr["over"] is not None and not over:   # あふれそうな警告
            if int(t * 6) % 2 == 0:
                text(ctx, "あふれそう！", W / 2, OVER_Y - 20, 64, rgb=(1, 0.35, 0.35), sw=12)
        if angels is not None and over:
            angels.draw(ctx, t - end_t)

        # 上の帯
        g = cairo.LinearGradient(0, 0, 0, 700)
        g.add_color_stop_rgba(0, 0.02, 0.03, 0.06, 0.92)
        g.add_color_stop_rgba(0.85, 0.02, 0.03, 0.06, 0.75)
        g.add_color_stop_rgba(1, 0.02, 0.03, 0.06, 0.0)
        ctx.rectangle(0, 0, W, 700)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, "子牛を合体させて", W / 2, 150, 80, sw=14)
        text(ctx, "巨大な雄牛にできる？", W / 2, 270, 92, rgb=GOLD, sw=18)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 365, 54, rgb=(1, 0.35, 0.35) if left < 10 else (1, 1, 1), sw=10)
        draw_chart(ctx, sprites, fr["best"], t)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "あふれた…" if fail_why == "overflow" else "時間切れ…", W / 2, 1100,
                 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"{NAMES[res['best']]}までだった…", W / 2, 1240, 70, sw=12)
        elif over:
            age = t - end_t
            if age < 0.3:
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.8 * (1 - age / 0.3))
                ctx.fill()
            k = min(1.0, age / 0.25)
            text(ctx, "巨大な雄牛に進化！", W / 2, 1650, 96 * (1.3 - 0.3 * k), rgb=GOLD, sw=20)

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
MIX_GAIN = 0.5   # 通常部分の音量(約 -18dB になるよう調整)
HOLY_GAIN = 0.85
# 進化した段階 → 鳴き声ファイルと音の高さ(1.0 = そのまま)
VOICE = {1: ("calf_0.wav", 1.08), 2: ("calf_1.wav", 0.95), 3: ("cow_0.wav", 1.0), 4: ("bull_0.wav", 1.0)}
VOICE_LEN = 1.8


def load_voice(name, pitch):
    """録音から一番大きい部分(VOICE_LEN 秒)を切り出し、音の高さを変えて返す。"""
    with wave.open(os.path.join(SND_DIR, name)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    n = int(VOICE_LEN * SR)
    if len(x) > n:
        env = np.convolve(x ** 2, np.ones(2400) / 2400, mode="same")
        start = max(0, int(np.argmax(env)) - int(0.35 * SR))
        x = x[start:start + n]
    idx = np.arange(0, len(x) - 1, pitch)
    y = np.interp(idx, np.arange(len(x)), x)
    fade = min(len(y), int(0.25 * SR))
    y[-fade:] *= np.linspace(1, 0, fade)
    y[:240] *= np.linspace(0, 1, 240)
    return y / max(1e-9, np.max(np.abs(y)))


def thud(amp, seed):
    """牛が落ちてぶつかる「ドスッ」という低い音。"""
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(seed).normal(0, 1, n)
    low = np.convolve(noise, np.ones(60) / 60, mode="same")
    return amp * (np.sin(2 * np.pi * 70 * t) * np.exp(-t * 25) + 2.5 * low * np.exp(-t * 40))


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 3) * SR)
    out = np.zeros(n_out)

    def add(sig, t0, gain=1.0):
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out:
            out[i:j] += gain * sig[: j - i]

    voices = {st: load_voice(*v) for st, v in VOICE.items()}
    for kind, t, data in events:
        if kind == "drop":
            add(thud(0.25, int(t * 1000)), t + 0.32)
        elif kind == "merge":
            st = data[1]
            add(thud(0.5 + 0.1 * st, int(t * 1000)), t)
            add(voices[st], t, 0.45 + 0.12 * st)
    extra = np.zeros(n_out)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(end_t * SR) + int(0.8 * SR)    # 雄牛の鳴き声のあとに神々しいBGM
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += HOLY_GAIN * sig[:m]
    wet = out.copy()
    for d, g in ((0.031, 0.25), (0.057, 0.18), (0.089, 0.12)):   # 牧場の小屋のような響き
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    wet = np.tanh(2.0 * wet / max(1e-9, np.max(np.abs(wet)))) / np.tanh(2.0) * MIX_GAIN
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
