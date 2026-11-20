"""「つぶすと増えるボール、1000個いける?」丸いわくの左右に歯車つきの「つかみ腕」があり、
開いたり閉じたりしながら首をふる。腕にはさまれてつぶされたボールは、次の色のボール3個に分かれる物理ショート。

- 参考:ユーザーから受け取った「Satisfying ball crusher」(左右の歯車の腕がボールをはさんでつぶすと増える)の形式。
  絵・色・音・ルールの数字はすべて自作(参考動画のロゴやデザインは使っていない)。
- はじめはわくの中に白いボールが1個。重力なし、ボールはいつも同じ速さでまっすぐ進み、わく・ほかのボール・腕で跳ね返る(ねらい・補正なし)。
- つかみ腕:歯車を支点に、L字に曲がった2本の腕。首をふりながら(左右に約50度)、あごを開いたり閉じたりする(決まったリズム)。
  閉じきると、2本の腕の先が合わさって四角い「かご」になる。
- 1個のボールが、同じつかみ腕の上の腕と下の腕の両方に同時にふれて、しかも腕が閉じようとしているとき = はさまれて「つぶれる」。
  つぶれたボールは消えて、腕のすぐ外の空いている所に、次の色のボール3個が生まれる(重なって生まれることはない。腕のあいだには生まれないので、生まれた瞬間にまたつぶれる連鎖は起きない)。
  色の順番:白 → 青 → 紫 → 緑 → 赤 → 金 → 虹(虹はそれ以上変わらない)。
- 制限時間内に1000個になれば成功(虹色パチンコ演出)、ならなければ失敗(幽霊)。

使い方:
    python claw_crush.py search [-n 40]
    python claw_crush.py render --seed N
"""

import argparse
import colorsys
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import cairo
import numpy as np
import pymunk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ball_escape"))
from ball_escape import midi_hz, text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from fail_bgm import fail_music  # noqa: E402
from pachinko import DURATION as FEVER_DUR, RainbowFever, kyuin_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

CX, CY, R = 540.0, 1000.0, 430.0          # 丸いわく
BALL_R = float(os.environ.get("BALL_R", 4.5))   # 5000個がわくに入るよう小さめ
V_START = float(os.environ.get("V_START", 260.0))                                   # はじめのボールの速さ(px/秒)
DAMP = float(os.environ.get("DAMP", 0.999))       # 1秒あたりに残る速さ(ほとんど減らない、軽く漂う)
KICK = float(os.environ.get("KICK", 180.0))       # はさまれて分かれたボールが飛び出す速さ
PINCH_MARGIN = BALL_R * 0.9 + 2.0                 # 刃からこの距離までのボールは「刃にかかっている」とみなす
SPLIT = int(os.environ.get("SPLIT", 2))           # はさまれると何個に分かれるか(はさまった数の2倍になる)
TARGET = int(os.environ.get("TARGET", 5000))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 57.0))
OUTRO = 4.2

# つかみ腕(参考動画と同じ:V字に開く → [字 → ひし形のかご → 腕どうしが重なる「T」字まで閉じきる)
L1, L2 = float(os.environ.get("L1", 225.0)), float(os.environ.get("L2", 225.0))   # 刃の根元側と、先の曲がった部分(参考動画と同じでほぼ同じ長さ)
ARM_W = 8.0                              # 刃の太さ(半分)
BLADE_T = float(os.environ.get("BLADE_T", 3.0))     # 刃が1周する時間(秒)。2本の刃はハサミのように逆向きに一定の速さで回り続ける
TH0 = math.radians(150)                  # はじめの刃の角度(外向きに開いたV字)
GEARS = [(CX - R, CY, 0.0, 0.0), (CX + R, CY, math.pi, 0.0)]   # (x, y, まっすぐ内向きの角度, -)。左右の役物は同じ動き

NAMES = ["白", "青", "紫", "緑", "赤", "金", "虹"]
COLORS = [(0.95, 0.96, 1.0), (0.2, 0.55, 1.0), (0.68, 0.3, 1.0), (0.2, 0.95, 0.4),
          (1.0, 0.2, 0.2), (1.0, 0.8, 0.15), None]
TOP = len(NAMES) - 1


OMEGA = 2 * math.pi / BLADE_T


def blade(t):
    """刃の角度(軸からの角度・巻き戻さない)。一定の速さで減っていく:外向きV字 → [字 → ひし形 → T字(重なる)→ 交差して反対側へ…"""
    return TH0 - OMEGA * t


def inner(t):
    """内側(わくの中)の刃の開き。(0, π] のあいだは内側で閉じていく途中、0 で2本が重なる。"""
    w = (blade(t) + math.pi) % (2 * math.pi) - math.pi
    return w


def close_start(t):
    """内側で閉じ始めた(開きが π だった)時刻。"""
    return t - (math.pi - inner(t)) / OMEGA


TH_BOX = math.atan(L2 / L1)   # 刃の先どうしが合わさって、ひし形のかごになる角度


def _in_cage(u, v):
    """閉じたひし形のかご(歯車 → 上のひじ → 刃の先が合わさる所 → 下のひじ)の中か。"""
    c_, s_ = math.cos(TH_BOX), math.sin(TH_BOX)
    pts = [(0, 0), (L1 * c_, -L1 * s_), (L1 * c_ + L2 * s_, 0), (L1 * c_, L1 * s_)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (x1 - x0) * (v - y0) - (y1 - y0) * (u - x0) < 0:
            return False
    return True


def _seg_dist(x, y, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    k = 0.0 if L == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L))
    return math.hypot(x - ax - k * dx, y - ay - k * dy)


def arm_local(sign):
    """腕の形(歯車が原点、腕は +x 方向)。sign=-1 が上の腕(先は +y へ曲がる)、+1 が下の腕。"""
    return [(0, 0), (L1, 0), (L1, -sign * L2)]


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, 0)
        sp.iterations = 15
        sp.damping = DAMP
        self.space = sp
        n = 120
        pts = [(CX + (R + 10) * math.cos(2 * math.pi * k / n), CY + (R + 10) * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
        for a, b in zip(pts, pts[1:]):
            s = pymunk.Segment(sp.static_body, a, b, 10)
            s.elasticity, s.friction = 1.0, 0.0
            s.collision_type = 3
            sp.add(s)
        self.t = 0.0
        self.claws = []
        for gi, (gx, gy, base, ph) in enumerate(GEARS):
            arms = []
            for sign in (-1, 1):
                b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
                b.position = (gx, gy)
                b.angle = base + sign * blade(0)
                p = arm_local(sign)
                shapes = []
                for a_, c_ in zip(p, p[1:]):
                    s = pymunk.Segment(b, a_, c_, ARM_W)
                    s.elasticity, s.friction = float(os.environ.get("ARM_E", 0.5)), 0.2
                    s.collision_type = 2
                    shapes.append(s)
                # はさみ判定用の、刃より少し太い「感じとる範囲」(ぶつからない。刃にほぼふれているボールを見つける)
                sensors = []
                for a_, c_ in zip(p, p[1:]):
                    s = pymunk.Segment(b, a_, c_, ARM_W + PINCH_MARGIN)
                    s.sensor = True
                    s.collision_type = 4
                    sensors.append(s)
                sp.add(b, *shapes, *sensors)
                arms.append((b, sensors, sign))
            self.claws.append({"gear": (gx, gy), "base": base, "ph": ph, "arms": arms, "caught": set()})
        self.balls = {}
        self.next_id = 0
        self.events = []
        self.result, self.result_t = None, None
        # はじめは白いボール1個(まん中あたりで、ゆっくり漂っている)
        a = rng.uniform(0, 2 * math.pi)
        self.add((CX + rng.uniform(-60, 60), CY + rng.uniform(-60, 60)), 0, (V_START * math.cos(a), V_START * math.sin(a)))

    def add(self, pos, tier, vel):
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, BALL_R))
        b.position = pos
        b.velocity = vel
        s = pymunk.Circle(b, BALL_R)
        s.elasticity, s.friction = float(os.environ.get("BALL_E", 0.95)), 0.1
        s.collision_type = 1
        self.space.add(b, s)
        self.balls[b] = {"id": self.next_id, "tier": tier, "shape": s, "born": self.t}
        self.next_id += 1
        return b

    def angles(self, c, t):
        return c["base"], blade(t)

    def step(self, dt):
        t1 = self.t + dt
        for c in self.claws:   # 腕を、決まった動きのとおりに動かす(角速度をあたえてボールを正しく押す)
            ph1, th1 = self.angles(c, t1)
            for b, _, sign in c["arms"]:
                b.angular_velocity = (ph1 + sign * th1 - b.angle) / dt
        self.space.step(dt)
        self.t = t1
        for b in self.balls:   # (めったにないが)わくの外へ押し出されたらもどす
            d = b.position - (CX, CY)
            if d.length > R - BALL_R:
                b.position = pymunk.Vec2d(CX, CY) + d.normalized() * (R - BALL_R - 1)
                b.velocity = -d.normalized() * 60
        # はさまれた瞬間:閉じていく2本の腕のあいだで、すき間がボールより細くなった(=両側の腕にはさまれた)ボール
        pinched = []
        for ci, c in enumerate(self.claws if self.result is None else []):   # 成功・失敗が決まったあとは、もう増えない
            w0, w1 = inner(self.t - dt), inner(self.t)
            gx, gy = c["gear"]
            if w0 > 0 >= w1 or (w0 > 0 and w1 > w0):   # 刃がT字に重なった瞬間:ひし形に囲まれていたボールは、ここで必ずはさまれる
                for bb in sorted(c["caught"], key=lambda b_: self.balls[b_]["id"] if b_ in self.balls else -1):
                    if bb in self.balls:
                        pinched.append((bb, ci))
                c["caught"] = set()
                continue
            if not 0 < w1 <= math.pi:   # 内側で2本の刃が近づいていく途中だけ、はさめる
                continue
            cs = close_start(self.t)
            if w0 > TH_BOX >= w1:   # 刃の先が合わさってひし形になった瞬間:中にいるボールは囲まれた(逃げられない)
                cph, sph = math.cos(-c["base"]), math.sin(-c["base"])
                c_, s_b = math.cos(TH_BOX), math.sin(TH_BOX)
                cx_l = (L1 * c_ + L2 * s_b) / 2
                mx, my = gx + cx_l * math.cos(c["base"]), gy + cx_l * math.sin(c["base"])
                rad = max(cx_l, L1 * s_b) + 5
                for q in self.space.bb_query(pymunk.BB(mx - rad, my - rad, mx + rad, my + rad), pymunk.ShapeFilter()):
                    bb = q.body
                    info = self.balls.get(bb)
                    if info is None or info["born"] >= cs - 1e-6:
                        continue
                    dx, dy = bb.position.x - gx, bb.position.y - gy
                    if _in_cage(dx * cph - dy * sph, dx * sph + dy * cph):
                        c["caught"].add(bb)
            # 2本の腕それぞれに、いまふれているボール(物理エンジンの当たり判定で調べる・速い)
            touch = []
            for b, shapes, sign in c["arms"]:
                got = set()
                for s_ in shapes:   # (shapes はここでは「感じとる範囲」)
                    for q in self.space.shape_query(s_):
                        if q.shape is not None and q.shape.collision_type == 1:
                            got.add(q.shape.body)
                touch.append(got)
            for bb in touch[0] & touch[1]:          # 閉じていく2本の腕の両方に同時にふれた = はさまれた
                info = self.balls.get(bb)
                if info is not None and info["born"] < cs - 1e-6:   # 閉じ始めたあとに生まれたボールは、その回にははさまれない
                    pinched.append((bb, ci))
        pinched.sort(key=lambda x: self.balls[x[0]]["id"] if x[0] in self.balls else -1)   # 毎回同じ順番で処理する(同じシードなら必ず同じ結果)
        for bb, ci in pinched:
            if bb not in self.balls:
                continue
            info = self.balls.pop(bb)
            pos, vel = bb.position, bb.velocity
            self.space.remove(bb, info["shape"])
            nt = min(TOP, info["tier"] + 1)
            # その場で、次の色のボール SPLIT 個(2個)に分かれる(押しつぶされて、まわりへ少し広がる)
            a0 = self.rng.uniform(0, 2 * math.pi)
            for k in range(SPLIT):
                a = a0 + 2 * math.pi * k / SPLIT
                off = pymunk.Vec2d(math.cos(a), math.sin(a)) * BALL_R * 1.05
                self.add(pos + off, nt, vel * 0.5 + off.normalized() * KICK)   # 軽く、ぱっとはじけて飛び出す
            self.events.append(("crush", self.t, (pos.x, pos.y, info["tier"], nt, len(self.balls), ci)))
        if self.result is None:
            if len(self.balls) >= TARGET:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, None))
            if self.result is not None:
                self.final_n = len(self.balls)


def simulate(seed, record=False):
    import gc
    gc.disable()   # 大量の小さなデータで、ごみ集めが何度も走って遅くなるのをふせぐ
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "n": len(g.balls),
                           # 記録は小さな数値の表(numpy)にまとめる(数千個×数千コマでもメモリと時間を使いすぎないように)
                           "balls": np.array([(b.position.x, b.position.y, i["tier"], i["id"]) for b, i in g.balls.items()],
                                             dtype=np.float32).reshape(-1, 4),
                           "arms": [[(b.position.x, b.position.y, b.angle, sign) for b, _, sign in c["arms"]] for c in g.claws]})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else FEVER_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "n": g.final_n}


def score(seed):
    r = simulate(seed)
    cr = [e for e in r["events"] if e[0] == "crush"]
    t100 = next((e[1] for e in cr if e[2][4] >= 100), None)
    return seed, r["result"], round(r["result_t"], 1), r["n"], len(cr), t100 and round(t100, 1)


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def tier_col(tier, t, oid=0):
    c = COLORS[tier]
    if c is None:
        return colorsys.hsv_to_rgb((t * 0.5 + oid * 0.137) % 1.0, 0.75, 1.0)
    return c


def draw_gear(ctx, x, y, r, ang):
    """歯車(銀色の金属)。"""
    n = 12
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.new_path()
    for k in range(n * 2):
        a0 = 2 * math.pi * k / (n * 2)
        rr = r if k % 2 == 0 else r * 0.78
        ctx.arc(0, 0, rr, a0, a0 + 2 * math.pi / (n * 2))
    ctx.close_path()
    g = cairo.LinearGradient(-r, -r, r, r)
    g.add_color_stop_rgb(0, 0.95, 0.96, 1.0)
    g.add_color_stop_rgb(0.5, 0.55, 0.57, 0.62)
    g.add_color_stop_rgb(1, 0.85, 0.86, 0.9)
    ctx.set_source(g)
    ctx.fill()
    ctx.arc(0, 0, r * 0.38, 0, 2 * math.pi)
    ctx.set_source_rgb(0.25, 0.26, 0.3)
    ctx.fill()
    ctx.arc(0, 0, r * 0.18, 0, 2 * math.pi)
    ctx.set_source_rgb(0.85, 0.86, 0.9)
    ctx.fill()
    ctx.restore()


def draw_arm(ctx, x, y, ang, sign):
    """L字の腕(メタリックな灰色の太い棒)。"""
    p = arm_local(sign)
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.new_path()
    ctx.move_to(*p[0])
    for q in p[1:]:
        ctx.line_to(*q)
    ctx.set_source_rgb(0.25, 0.26, 0.3)
    ctx.set_line_width(ARM_W * 2 + 4)
    ctx.stroke_preserve()
    g = cairo.LinearGradient(0, -ARM_W, 0, ARM_W)
    g.add_color_stop_rgb(0, 0.92, 0.93, 0.96)
    g.add_color_stop_rgb(0.5, 0.6, 0.62, 0.68)
    g.add_color_stop_rgb(1, 0.75, 0.76, 0.8)
    ctx.set_source(g)
    ctx.set_line_width(ARM_W * 2)
    ctx.stroke()
    ctx.restore()


def draw_ball(ctx, x, y, col, r=BALL_R):
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r)
    g.add_color_stop_rgb(0, *(min(1, c + 0.5) for c in col))
    g.add_color_stop_rgb(0.5, *col)
    g.add_color_stop_rgb(1, *(c * 0.55 for c in col))
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()


_SPR = {}


def fast_ball(ctx, x, y, col):
    """ボールをすばやく描く(色ごとに一度だけ描いた小さな絵を貼る。数千個でも速い)。"""
    key = tuple(round(c * 24) for c in col)
    spr = _SPR.get(key)
    if spr is None:
        n = int(BALL_R * 2 + 4)
        spr = cairo.ImageSurface(cairo.FORMAT_ARGB32, n, n)
        draw_ball(cairo.Context(spr), n / 2, n / 2, tuple(k / 24 for k in key))
        _SPR[key] = spr
    n = spr.get_width()
    ctx.set_source_surface(spr, x - n / 2, y - n / 2)
    ctx.rectangle(x - n / 2, y - n / 2, n, n)
    ctx.fill()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"claw_crush_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"claw_crush_{seed}.wav")
    final = os.path.join(OUT_DIR, f"claw_crush_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"cc_preview_{pt:.1f}.png"))
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
    fever = RainbowFever(W, H, seed) if not fail else None
    pops = []
    ev_i = 0
    best = 0
    frozen = None
    prev_n = 1
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "crush":
                x, y, t0, nt, n, ci = data
                if len(pops) < 80:
                    pops.append((x, y, nt, et))
                best = max(best, nt)
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        if fail and over:
            if frozen is None:
                frozen = fr
            fr = frozen
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        ctx.set_source_rgb(0, 0, 0)
        ctx.paint()
        if fever is not None and over:
            fever.draw_back(ctx, t - end_t)
        # わく
        for wdt, a in ((10, 0.12), (4, 1.0)):
            ctx.arc(CX, CY, R + 3, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, a)
            ctx.set_line_width(wdt)
            ctx.stroke()
        for x, y, tier, oid in fr["balls"].tolist():
            tier, oid = int(tier), int(oid)
            fast_ball(ctx, x, y, tier_col(tier, t, oid))
        keep = []
        for x, y, nt, t0 in pops:   # つぶれた瞬間の、はじける光
            a = t - t0
            if a < 0.3:
                col = tier_col(nt, t)
                ctx.arc(x, y, BALL_R * (1.2 + 5 * a), 0, 2 * math.pi)
                ctx.set_source_rgba(*col, 0.9 * (1 - a / 0.3))
                ctx.set_line_width(2.5)
                ctx.stroke()
                keep.append((x, y, nt, t0))
        pops = keep
        for c, (gx, gy, base, ph) in zip(fr["arms"], GEARS):
            for x, y, ang, sign in c:
                draw_arm(ctx, x, y, ang, sign)
            draw_gear(ctx, gx, gy, 34, -t * 2.0 if gx < CX else t * 2.0)
        # 文字
        text(ctx, "はさむと2倍に増えるボール", W / 2, 235, 62, sw=12)
        text(ctx, f"{TARGET}個にできる？", W / 2, 335, 96, rgb=GOLD, sw=16)
        n = min(fr["n"], TARGET) if not over else res["n"]
        bump = 1.0 + (0.12 if n > prev_n else 0)
        prev_n = n
        text(ctx, f"{n}", W / 2 - 90, 440, 84 * bump, rgb=(1, 1, 1), sw=12)
        text(ctx, f"/ {TARGET} 個", W / 2 + 160, 440, 44, rgb=(0.85, 0.85, 0.9), sw=6)
        # 色の進化表(いままでに出た色まで明るく)
        for k in range(len(NAMES)):
            x = W / 2 + (k - 3) * 92
            col = tier_col(k, t)
            reached = k <= best
            draw_ball(ctx, x, 1478, col if reached else tuple(c * 0.3 for c in col), 15)
            text(ctx, NAMES[k], x, 1516, 26, rgb=(1, 1, 1) if reached else (0.5, 0.5, 0.55), sw=5)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 518, 40, rgb=(1, 0.4, 0.4) if left < 10 else (0.95, 0.95, 0.95), sw=8)
        if over and fail:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 880, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            text(ctx, "時間切れ…", W / 2, 990, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"{res['n']}個までだった…", W / 2, 1110, 66, sw=12)
        elif over:
            fever.draw_front(ctx, t - end_t, text, "大当たり!!", f"{TARGET}個達成!!")
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
def _t(d):
    return np.arange(int(d * SR)) / SR


def crunch(amp, seed, tier):
    """つぶれる「パキッ」:短いノイズのはじける音+はじける高い音(色が上がるほど高い)。"""
    t = _t(0.12)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    hp = n - np.convolve(n, np.ones(6) / 6, "same")
    f = midi_hz(72 + 3 * tier)
    ton = np.sin(2 * np.pi * f * t * (1 + 2 * t)) * np.exp(-t * 40)
    return amp * (0.7 * hp * np.exp(-t * 60) + 0.6 * ton)


def pops3(tier):
    """4つに分かれる「ポポポポン」(色が上がるほど高い)。"""
    out = np.zeros(int(0.3 * SR))
    for k in range(4):
        t = _t(0.08)
        f = midi_hz(76 + 3 * tier + 4 * k)
        s = np.sin(2 * np.pi * f * t) * np.exp(-t * 45)
        i = int(k * 0.045 * SR)
        out[i:i + len(s)] += 0.5 * s
    return out


def pop1(tier, v):
    """増えたボール1個ぶんの「ポン」(色が上がるほど高く、6とおりの高さ)。"""
    t = _t(0.09)
    f = midi_hz(74 + 3 * tier + [0, 2, 4, 7, 9, 12][v])
    return np.sin(2 * np.pi * f * t * (1 + 0.6 * t)) * np.exp(-t * 40) * np.minimum(1, t / 0.002)


def clank(amp):
    """腕が閉じきったときの「カシャン」(金属)。"""
    t = _t(0.25)
    y = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in ((410, 1, 18), (1130, 0.6, 25), (2650, 0.4, 35)))
    return amp * y


def kyuin_one(up=1.0):
    """「キュイン!」:低いところから一気に高く上がる音(パチンコの当たり風)。"""
    t = _t(0.28)
    f = up * (500 + 2900 * (1 - np.exp(-t / 0.06))) * (1 + 0.03 * np.sin(2 * np.pi * 32 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.35 * np.sign(np.sin(ph)) + 0.3 * np.sin(2 * ph)
    return y * np.minimum(1, t / 0.01) * np.exp(-np.maximum(0, t - 0.16) / 0.05)


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
    # 刃が重なる「カシャン」
    tc = TH0 / OMEGA   # 内側で2本の刃が重なる瞬間(左右同時なので2つ分の大きさ)
    while tc <= (end_t or duration):
        add(clank(0.4), tc)
        tc += BLADE_T
    # 増えたボール1個ごとに「ポン」(増えた数だけ鳴る。たくさん増えると「ポポポポ…」の大合唱)+ はさまれた「パキッ」
    rng = np.random.default_rng(11)
    pops = {}
    recent = []
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.01:
            continue
        if kind == "crush":
            nt = data[3]
            recent = [x for x in recent if t - x < 0.1]
            if len(recent) < 6:
                add(crunch(0.6, len(recent) + int(t * 100), nt), t, 1 / (1 + 0.2 * len(recent)))
            recent.append(t)
            for k in range(SPLIT):
                v = int(rng.integers(0, 6))
                key = (nt, v)
                if key not in pops:
                    pops[key] = pop1(nt, v)
                add(pops[key], t + 0.02 + k * 0.035 + rng.uniform(0, 0.03), 0.55)
    win = int(0.6 * SR)   # 効果音の大きさを時間でならす(はじめの静かなところも聞こえるように)
    pw = np.convolve(out ** 2, np.ones(win) / win, "same")
    agc = np.clip(0.08 / np.sqrt(pw + 1e-8), 0.6, 6.0)
    agc = np.convolve(agc, np.ones(win) / win, "same")
    out = out * agc
    wet = out.copy()
    for dd, g in ((0.043, 0.2), (0.071, 0.13)):
        kk = int(dd * SR)
        wet[kk:] += out[:-kk] * g
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int(end_t * SR)]
    rms = np.sqrt(np.mean(body ** 2))
    if rms > 0:
        wet *= min(6.0, 10 ** (-14.0 / 20) / rms)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
        sig = fail_music(SR, OUTRO)
        i0 = int((end_t + SCARE_DUR) * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += 0.6 * sig[:m]
    else:
        # 虹色パチンコ演出の音:キュインキュインの連打+ファンファーレ+ジャラジャラ(pachinko.py)に、
        # 大当たりのファンファーレ連打+キュイン+チャリンチャリン(glass_spiral/jackpot_end.py)を重ね、演出のあいだずっと「キュイン!」を鳴らし続ける
        sys.path.insert(0, os.path.join(HERE, "..", "glass_spiral"))
        import jackpot_end as JP
        a_ = kyuin_music(SR, FEVER_DUR)
        b_ = JP.music(SR, 3)
        b_ = b_.mean(axis=1) if b_.ndim == 2 else b_
        n = int(FEVER_DUR * SR)
        mus = np.zeros(n)
        mus[:min(n, len(a_))] += a_[:n]
        mus[:min(n, len(b_))] += 0.8 * b_[:n] / (np.abs(b_).max() + 1e-9)
        tt = 0.0
        while tt < FEVER_DUR - 0.5:   # キュイン!キュイン!を最後まで連打
            ky = kyuin_one(1.0 + 0.15 * ((int(tt / 0.3)) % 3))
            i = int(tt * SR)
            m = min(len(ky), n - i)
            mus[i:i + m] += 0.45 * ky[:m]
            tt += 0.3
        mus *= np.minimum(1, (FEVER_DUR - np.arange(n) / SR) / 0.6)
        mus = np.tanh(1.6 * mus / (np.abs(mus).max() + 1e-9)) / np.tanh(1.6)
        i0 = int((end_t + 0.05) * SR)
        m = min(len(mus), n_out - i0)
        extra[i0:i0 + m] += 1.05 * mus[:m]
    wet = wet + 0.95 * extra[: len(wet)]
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
    ap.add_argument("-n", type=int, default=40)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
