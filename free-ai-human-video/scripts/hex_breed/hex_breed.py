"""「ぶつかると増えるボール、○個にできる?」ゆっくり回る六角形のわくの中で、ボールどうしがぶつかるたびに1個ずつ増える。
ただし六角形の1辺にはすき間(出口)があいていて、そこから外に出たボールは消えてしまう。

- 重力・摩擦なし。ボールはいつも同じ速さで、わく・ほかのボールで跳ね返る(ねらい・補正なし)。
- ボールとボールが触れたら、そのあいだのすぐ横の空いている所に1個生まれる(29本目と同じ増え方)。
  生まれて MATURE 秒たっていないボールは増やさない。1個生んだ2個は REST 秒休む(生まれた瞬間に次々増える連鎖はしない)。
- 六角形は一定の速さで回り続ける。すき間の向きもいっしょに回る。
- ボールが TARGET 個になったら成功。制限時間が来るか、ボールが1個以下(もう増えられない)になったら失敗。
- 成功ならパチンコの大当たり風の演出、失敗なら幽霊。

使い方:
    python hex_breed.py search [-n 80]
    python hex_breed.py render --seed N
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ball_escape"))
from ball_escape import midi_hz, text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from fail_bgm import fail_music  # noqa: E402
from pachinko import RainbowFever, hsv, kyuin_music  # noqa: E402
from flashy import PALETTE, draw_ball, drip_layout, giragira, kyuin_one, scary_text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "glass_spiral"))
import jackpot_end as JP  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

CX, CY = 540.0, 1030.0
HEX_R = float(os.environ.get("HEX_R", 450.0))     # 六角形の中心から角までのきょり
APO = HEX_R * math.cos(math.pi / 6)
WALL_R = 8.0
GAP = float(os.environ.get("GAP", 0.3))          # すき間の大きさ(1辺の長さに対する割合)
SPIN = float(os.environ.get("SPIN", 0.45))        # 六角形が回る速さ(ラジアン/秒)
BALL_R = float(os.environ.get("BALL_R", 11.0))
SPEED = float(os.environ.get("SPEED", 320.0))
N_START = int(os.environ.get("N_START", 5))
TARGET = int(os.environ.get("TARGET", 300))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 33.0))
BIRTH_GAP = 0.3
MATURE = float(os.environ.get("MATURE", 0.6))   # 生まれてからこの秒数は、ぶつかっても増やさない
REST = float(os.environ.get("REST", 0.8))       # 1個生んだ2個は、この秒数休む
MAX_OBJ = TARGET + 40
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG


def hex_segments():
    """六角形の辺(中心が原点)。0番の辺のまん中にすき間をあける。"""
    pts = [(HEX_R * math.cos(math.pi / 2 + k * math.pi / 3), HEX_R * math.sin(math.pi / 2 + k * math.pi / 3)) for k in range(7)]
    segs = []
    for k in range(6):
        a, b = pts[k], pts[k + 1]
        if k == 0:
            h = (1 - GAP) / 2
            segs.append((a, (a[0] + (b[0] - a[0]) * h, a[1] + (b[1] - a[1]) * h)))
            segs.append(((a[0] + (b[0] - a[0]) * (1 - h), a[1] + (b[1] - a[1]) * (1 - h)), b))
        else:
            segs.append((a, b))
    return segs


SEGS = hex_segments()


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, 0)
        sp.iterations = 12
        self.space = sp
        self.frame = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.frame.position = (CX, CY)
        self.frame.angle = rng.uniform(0, 2 * math.pi)
        self.frame.angular_velocity = SPIN * rng.choice([-1, 1])
        shapes = []
        for a, b in SEGS:
            s = pymunk.Segment(self.frame, a, b, WALL_R)
            s.elasticity, s.friction = 1.0, 0.0
            s.collision_type = 2
            shapes.append(s)
        sp.add(self.frame, *shapes)
        self.objs = {}
        self.next_id = 0
        self.t = 0.0
        self.events = []
        self.pairs = []
        self.flying = []
        self.escaped = 0
        self.best = N_START
        self.result, self.result_t = None, None
        for k in range(N_START):   # はじめのボール:まん中のまわりにばらばらの向きで
            a = 2 * math.pi * k / N_START + rng.uniform(-0.3, 0.3)
            d = rng.uniform(60, 180)
            va = rng.uniform(0, 2 * math.pi)
            self.add((CX + d * math.cos(a), CY + d * math.sin(a)), (SPEED * math.cos(va), SPEED * math.sin(va)))
        for info in self.objs.values():   # はじめのボールはすぐ増やせる
            info["ready"] = 0.0
        sp.on_collision(1, 1, begin=self._touch)

    def add(self, pos, vel):
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, BALL_R))
        b.position = pos
        b.velocity = vel
        s = pymunk.Circle(b, BALL_R)
        s.elasticity, s.friction = 1.0, 0.0
        s.collision_type = 1
        self.space.add(b, s)
        self.space.reindex_shapes_for_body(b)
        self.objs[b] = {"id": self.next_id, "shape": s, "col": self.next_id % 12, "ready": self.t + MATURE}
        self.next_id += 1
        return b

    def free_spot(self, mid, perp):
        """生まれる場所:当たった所のすぐ横で、ほかのボールと重ならない所(六角形の内側の円の中)。"""
        base = math.atan2(perp.y, perp.x)
        offs = [0.0, math.pi]
        for k in range(1, 6):
            for sgn in (1, -1):
                offs += [sgn * k * math.pi / 8, math.pi + sgn * k * math.pi / 8]
        for dist in (1.75, 1.9, 2.1, 2.4, 2.8, 3.3, 4.0, 5.0, 6.5, 8.5):
            for o in offs:
                p = mid + pymunk.Vec2d(math.cos(base + o), math.sin(base + o)) * BALL_R * dist
                if (p - (CX, CY)).length > APO - WALL_R - BALL_R - 2:
                    continue
                q = self.space.point_query_nearest(p, BALL_R + BIRTH_GAP, pymunk.ShapeFilter())
                if q is None or q.shape is None or q.shape.collision_type != 1:
                    return p
        return None   # 近くに空きがない(生まれない)

    def _touch(self, arb, space, data):
        a, b = (s.body for s in arb.shapes)
        if a in self.objs and b in self.objs:
            self.pairs.append((a, b))
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
        for a, b in self.pairs:   # ボールとボールが触れたら1個生まれる
            if a not in self.objs or b not in self.objs or len(self.objs) >= MAX_OBJ or self.result is not None:
                continue
            ia, ib = self.objs[a], self.objs[b]
            if self.t < ia["ready"] or self.t < ib["ready"]:   # 生まれたて・休み中のボールは増やさない
                continue
            ia["ready"] = ib["ready"] = self.t + REST
            mid = (a.position + b.position) / 2
            d = b.position - a.position
            if d.length < 1e-6:
                d = pymunk.Vec2d(1, 0)
            perp = pymunk.Vec2d(-d.y, d.x).normalized() * (1 if self.rng.random() < 0.5 else -1)
            pos = self.free_spot(mid, perp)
            if pos is None:
                continue
            out = pos - mid
            vel = out.normalized() * SPEED if out.length > 1e-6 else perp * SPEED
            self.add(pos, vel)
            self.events.append(("born", self.t, (pos.x, pos.y, len(self.objs))))
        self.pairs = []
        gone = [b for b in self.objs if (b.position - (CX, CY)).length > HEX_R + 30]
        for b in sorted(gone, key=lambda b_: self.objs[b_]["id"]):   # すき間から外に出たボールは消える
            info = self.objs.pop(b)
            self.space.remove(b, info["shape"])
            self.flying.append([b.position.x, b.position.y, b.velocity.x, b.velocity.y, info["col"], self.t])
            if self.result is None:
                self.escaped += 1
                self.events.append(("out", self.t, (b.position.x, b.position.y, len(self.objs))))
        self.flying = [f for f in self.flying if self.t - f[5] < 1.0]
        for f in self.flying:
            f[0] += f[2] * dt
            f[1] += f[3] * dt
        self.best = max(self.best, len(self.objs))
        if self.result is None:
            if len(self.objs) >= TARGET:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT or len(self.objs) <= 1:
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
            frames.append({"t": g.t, "n": len(g.objs), "ang": g.frame.angle, "esc": g.escaped,
                           "balls": np.array([(b.position.x, b.position.y, i["col"]) for b, i in g.objs.items()],
                                             dtype=np.float32).reshape(-1, 3),
                           "fly": [(f[0], f[1], f[4], g.t - f[5]) for f in g.flying]})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "n": g.final_n, "best": g.best, "escaped": g.escaped}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), r["n"], r["best"], r["escaped"]


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    draw_ball(ctx, x, y, r * 0.8, PALETTE[(kind * 12 // 7) % 12])


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"hex_breed_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"hex_breed_{seed}.wav")
    final = os.path.join(OUT_DIR, f"hex_breed_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"hb_preview_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, CX, CY, reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=(f"{TARGET}個!!", "COMPLETE", f"にげた {res['escaped']}個"))
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    drips = drip_layout(ctx, "失敗したら", W / 2, 1590, 78, "失敗したら・・・", seed)
    bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(bg)
    gr = cairo.RadialGradient(CX, CY, 50, CX, CY, 1100)
    gr.add_color_stop_rgb(0, 0.08, 0.06, 0.15)
    gr.add_color_stop_rgb(1, 0.02, 0.02, 0.05)
    bc.set_source(gr)
    bc.paint()
    sprites = {}
    m_ = int(math.ceil(BALL_R)) + 2
    for c in range(12):
        s_ = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2 * m_, 2 * m_)
        draw_ball(cairo.Context(s_), m_, m_, BALL_R, PALETTE[c])
        sprites[c] = s_
    pops = []
    frozen = None
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "born" and len(pops) < 80:
                pops.append((data[0], data[1], et))
            ev_i += 1
        over = end_t is not None and t >= end_t
        win_b = (t - end_t) if (ending is not None and over) else -1.0
        if win_b >= PRE:
            ending.draw(surf, ctx, win_b - PRE + JP.T_BIG)
            giragira(ctx, win_b - PRE, fever, glints, W, H, WIN_DUR)
            ff.stdin.write(surf.get_data())
            continue
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        if fail and over:
            if frozen is None:
                frozen = fr
            fr = frozen
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        # 六角形のわく(すき間のところは赤く光る「出口」)
        ctx.save()
        ctx.translate(CX, CY)
        ctx.rotate(fr["ang"])
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for wd, col, al in ((30, (0.2, 0.7, 1.0), 0.12), (18, (0.3, 0.8, 1.0), 0.3), (2 * WALL_R, (0.85, 0.97, 1.0), 1.0)):
            for a, b in SEGS:
                ctx.move_to(*a)
                ctx.line_to(*b)
            ctx.set_source_rgba(*col, al)
            ctx.set_line_width(wd)
            ctx.stroke()
        a, b = SEGS[0][1], SEGS[1][0]   # すき間
        ctx.move_to(*a)
        ctx.line_to(*b)
        ctx.set_source_rgba(1, 0.25, 0.25, 0.55 + 0.25 * math.sin(t * 8))
        ctx.set_line_width(5)
        ctx.set_dash([12, 10])
        ctx.stroke()
        ctx.set_dash([])
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ctx.restore()
        ca, sa = math.cos(fr["ang"]), math.sin(fr["ang"])
        ex, ey = CX + mx * ca - my * sa, CY + mx * sa + my * ca
        nd = math.hypot(ex - CX, ey - CY)
        lx, ly = CX + (ex - CX) * (nd + 50) / nd, CY + (ey - CY) * (nd + 50) / nd
        text(ctx, "出口", lx, ly + 14, 40, rgb=(1, 0.4, 0.4), sw=8)
        cyc = int(win_b * 30) if win_b >= 0 else 0
        for x, y, c, age in fr["fly"]:   # 外に出たボール(うすくなって消える)
            ctx.arc(x, y, BALL_R, 0, 2 * math.pi)
            ctx.set_source_rgba(*PALETTE[int(c)], max(0.0, 1 - age))
            ctx.fill()
        for x, y, c in fr["balls"]:
            ctx.set_source_surface(sprites[(int(c) + cyc) % 12], x - m_, y - m_)
            ctx.paint()
        keep = []
        for x, y, t0 in pops:   # 生まれた瞬間のキラッ
            a_ = t - t0
            if a_ < 0.3:
                k = 1 - a_ / 0.3
                ctx.arc(x, y, BALL_R + 25 * a_ / 0.3, 0, 2 * math.pi)
                ctx.set_source_rgba(1, 1, 1, 0.8 * k)
                ctx.set_line_width(2.5)
                ctx.stroke()
                keep.append((x, y, t0))
        pops = keep
        # 文字
        text(ctx, "ぶつかると1個増えるボール", W / 2, 235, 60, sw=12)
        text(ctx, f"{TARGET}個にできる？", W / 2, 335, 96, rgb=GOLD, sw=16)
        n = fr["n"] if not over else res["n"]
        text(ctx, f"{n} / {TARGET} 個", W / 2, 445, 70, rgb=(1, 1, 1), sw=10)
        tt = min(t, end_t) if end_t is not None else t
        left = max(0.0, TIME_LIMIT - tt)
        text(ctx, f"残り {left:4.1f}秒", W / 2 - 150, 522, 40, rgb=(1, 0.4, 0.4) if left < 10 else (0.95, 0.95, 0.95), sw=8)
        text(ctx, f"にげた {fr['esc'] if not over else res['escaped']}個", W / 2 + 170, 522, 40, rgb=(1, 0.5, 0.5), sw=8)
        if not over:
            scary_text(ctx, "失敗したら・・・", W / 2, 1590, 78, t, drips)
        if over and fail:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 880, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            msg = "全部にげた…" if res["n"] <= 1 else "時間切れ…"
            text(ctx, msg, W / 2, 990, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"{res['n']}個までだった…", W / 2, 1110, 66, sw=12)
        if win_b >= 0:
            k = win_b / PRE
            ph = (win_b * (8 + 14 * k)) % 1.0
            ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*hsv(win_b * 4), (0.25 + 0.4 * k) * (1 - ph) ** 2)
            ctx.paint()
            ctx.set_operator(cairo.OPERATOR_OVER)
            if k > 0.75:
                ctx.set_source_rgba(1, 1, 1, ((k - 0.75) / 0.25) ** 2)
                ctx.paint()
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


def pop_snd(n):
    """生まれる「ポン」(数が増えるほど少しずつ高く)。"""
    t = _t(0.12)
    m = 67 + min(24, int(10 * math.log2(1 + n / 8)))
    f = midi_hz(m)
    return 0.6 * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 30)


def out_snd():
    """出口から出て消える「ヒュッ」。"""
    t = _t(0.25)
    f = 1200 - 2800 * t
    return 0.35 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 10)


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
    rb, ro = [], []
    for kind, t, data in events:
        if t > end_t + 0.01:
            continue
        if kind == "born":
            rb = [x for x in rb if t - x < 0.06]
            if len(rb) >= 3:
                continue
            rb.append(t)
            add(pop_snd(data[2]), t)
        elif kind == "out":
            ro = [x for x in ro if t - x < 0.12]
            if len(ro) >= 2:
                continue
            ro.append(t)
            add(out_snd(), t)
    wet = out.copy()
    for dd, g_ in ((0.043, 0.2), (0.071, 0.13)):
        kk = int(dd * SR)
        wet[kk:] += out[:-kk] * g_
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
        b_ = JP.music(SR, 3)
        b_ = b_.mean(axis=1) if b_.ndim == 2 else b_
        b_ = b_[int(JP.T_BIG * SR) - int(0.05 * SR):]
        n = int(WIN_DUR * SR)
        mus = np.zeros(n)
        mus[:min(n, len(b_))] += b_[:n] / (np.abs(b_).max() + 1e-9)
        a_ = kyuin_music(SR, WIN_DUR)
        mus[:min(n, len(a_))] += 0.8 * a_[:n]
        tt = 0.0
        while tt < WIN_DUR - 0.5:
            ky = kyuin_one(1.0 + 0.15 * ((int(tt / 0.3)) % 3))
            i = int(tt * SR)
            m = min(len(ky), n - i)
            mus[i:i + m] += 0.4 * ky[:m]
            tt += 0.3
        tb = np.arange(int(1.5 * SR)) / SR
        boom = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-tb * 6) + 35) / SR) * np.exp(-tb * 2.5)
        mus[:len(boom)] += 0.9 * boom
        mus *= np.minimum(1, (WIN_DUR - np.arange(n) / SR) / 0.6)
        mus = np.tanh(1.6 * mus / (np.abs(mus).max() + 1e-9)) / np.tanh(1.6)
        i0 = int((end_t + PRE) * SR)
        m = min(len(mus), n_out - i0)
        extra[i0:i0 + m] += 1.1 * mus[:m]
        tt = 0.0
        while tt < PRE - 0.05:
            k = tt / PRE
            ky = kyuin_one(1.0 + 0.6 * k)
            i = int((end_t + tt) * SR)
            m = min(len(ky), n_out - i)
            extra[i:i + m] += (0.35 + 0.35 * k) * ky[:m]
            tt += 0.11 - 0.05 * k
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
    ap.add_argument("-n", type=int, default=80)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
