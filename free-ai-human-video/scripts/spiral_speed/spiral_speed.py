"""「スピード○○でガラスを全部割れる?」(参考動画「Ball breaks glass」の形)
うずまきの通路を、虹色のガラスがすき間なくうめている。ボールを上から落とすと、うずまきの外側の口から入ってガラスを割りながら内側へ進む。
スピードを 100 → 250 → 400 → 600 と上げながら4回挑戦し、毎回ガラスは元どおり。最後のスピード600で全部割れたら成功。

- うずまきのコース・物理は 18本目(glass_spiral.py)と同じ:盤面は真上から見た水平な台。ガラスを1枚割るたびにボールは少し遅くなり、
  転がり抵抗でも少しずつ遅くなる。勢いがなくなったボールは消える。
- ボールがうずまきの口に入るときの速さが「スピード」(スピード × V_PER px/秒)。落とす位置はほんの少しずつ毎回ちがう(ねらい・補正なし)。
- 成功ならパチンコの大当たり風の演出、失敗なら幽霊。

使い方:
    python spiral_speed.py search [-n 80]
    python spiral_speed.py render --seed N
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
from ball_escape import midi_hz  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from fail_bgm import fail_music  # noqa: E402
from pachinko import RainbowFever, hsv, kyuin_music  # noqa: E402
from flashy import PALETTE, chic, draw_ball as shiny_ball, giragira, horror, kyuin_one  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "glass_spiral"))
import glass_spiral as GS  # noqa: E402   うずまきの形と物理
import jackpot_end as JP  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

SPEEDS = [100, 250, 400, 600]
V_PER = float(os.environ.get("V_PER", 7.55))          # スピード1あたりの、うずまきに入るときの速さ(px/秒)
KEEP = float(os.environ.get("KEEP", 0.996))           # ガラスを1枚割ったあとに残る速さの割合
N_GLASS = GS.N_PLANKS
GAP = 1.2                                              # 次の挑戦までの間(ガラスが元にもどる)
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG
OFFSET_Y = 120.0                                       # 画面上で少し下にずらす
VS = 1.18                                              # 画面に描くときの拡大(物理はそのまま)
CX, CY = GS.CX, GS.CY


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GS.GRAVITY)
        sp.iterations = 20
        self.space = sp
        st = sp.static_body
        n = int(GS.TH_END / 0.025)
        pts = [GS.wall_pt(GS.TH_END * k / n) for k in range(n + 1)]
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            s = pymunk.Segment(st, a, b, 3)
            s.elasticity, s.friction = GS.WALL_E, 0.0
            s.set_neighbors(pts[max(i - 1, 0)], pts[min(i + 2, n)])
            sp.add(s)
        self.ths = [GS.TH_WOOD0 + (GS.TH_WOOD1 - GS.TH_WOOD0) * (k + 0.5) / N_GLASS for k in range(N_GLASS)]
        self.shapes = []
        self.k_of = {}
        for k, th in enumerate(self.ths):
            s = pymunk.Segment(st, GS.wall_pt(th, 8), GS.wall_pt(th + 2 * math.pi, -8), 3)
            s.elasticity, s.friction = 1.0, 0.0
            s.collision_type = 4
            self.shapes.append(s)
            self.k_of[s] = k
        self.alive = [False] * N_GLASS
        sp.on_collision(1, 4, begin=self._hit)
        self.to_break, self.breaking = [], set()
        self.ball = None
        self.events = []
        self.t = 0.0
        self.attempt = -1
        self.next_t = 0.3
        self.cleared = 0
        self.counts = []
        self.result, self.result_t = None, None

    def reset_glass(self):
        for k in range(N_GLASS):
            if not self.alive[k]:
                self.space.add(self.shapes[k])
                self.alive[k] = True
        self.cleared = 0

    def _hit(self, arb, space, data):
        arb.process_collision = False
        k = self.k_of.get(arb.shapes[1])
        body = arb.shapes[0].body
        if k is not None and self.alive[k] and k not in self.breaking:
            self.breaking.add(k)
            self.to_break.append((k, body, body.velocity.length))
            body.velocity = body.velocity * KEEP

    def drop(self):
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, GS.BALL_R))
        b.position = (GS.DROP_X + self.rng.uniform(-8, 8), GS.DROP_Y)
        b.velocity = (self.rng.uniform(-10, 10), SPEEDS[self.attempt] * V_PER)
        b.velocity_func = GS.board_physics
        c = pymunk.Circle(b, GS.BALL_R)
        c.elasticity, c.friction = 1.0, 0.0
        c.collision_type = 1
        self.space.add(b, c)
        self.ball = (b, c)
        self.entered = False
        self.events.append(("drop", self.t, self.attempt))

    def step(self, dt):
        self.t += dt
        if self.result is None and self.ball is None and self.next_t is not None and self.t >= self.next_t:
            self.attempt += 1
            self.reset_glass()
            self.events.append(("reset", self.t, self.attempt))
            self.drop()
            self.next_t = None
        self.to_break, self.breaking = [], set()
        self.space.step(dt)
        for k, body, speed in self.to_break:
            if not self.alive[k]:
                continue
            self.alive[k] = False
            self.space.remove(self.shapes[k])
            self.cleared += 1
            self.events.append(("break", self.t, (k, body.position.x, body.position.y, speed)))
        if self.ball is not None and not self.entered:   # うずまきの口に入った瞬間の速さ = スピード × V_PER
            b = self.ball[0]
            if not GS.outside_board(*b.position):
                self.entered = True
                v = b.velocity
                b.velocity = v.normalized() * (SPEEDS[self.attempt] * V_PER)
        if self.ball is not None:
            b, c = self.ball
            x, y = b.position
            if (b.velocity.length < GS.V_DIE and not GS.outside_board(x, y)) or y > H + 200:
                self.space.remove(b, c)
                self.ball = None
                self.events.append(("die", self.t, (x, y)))
                self.counts.append(self.cleared)
                if self.result is None:
                    if self.cleared == N_GLASS and self.attempt == len(SPEEDS) - 1:
                        pass
                    elif self.attempt == len(SPEEDS) - 1:
                        self.result, self.result_t = "fail", self.t + 0.4
                        self.events.append(("fail", self.t + 0.4, None))
                    else:
                        self.next_t = self.t + GAP
        if self.result is None and self.cleared == N_GLASS:
            if self.attempt == len(SPEEDS) - 1:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            b = g.ball[0] if g.ball else None
            frames.append({"t": g.t, "attempt": g.attempt, "cleared": g.cleared, "alive": list(g.alive),
                           "ball": (b.position.x, b.position.y) if b else None})
        if g.result is not None and g.t >= g.result_t:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
        if g.t > 200:
            break
    counts = g.counts + ([g.cleared] if g.ball else [])
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "counts": counts, "ths": g.ths}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), r["counts"]


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
BALL_COLS = [(0.2, 0.85, 1.0), (0.2, 0.95, 0.85), (0.25, 1.0, 0.6), (0.3, 1.0, 0.35)]


GLASS_HUES = [0.0, 0.08, 0.15, 0.3, 0.47, 0.58, 0.7, 0.8, 0.9]


def glass_color(k, ths):
    """虹色のガラス:うずまきを半周するごとに色が変わる(赤→オレンジ→黄→緑→水色→青→紫→ピンク…)。"""
    half = int((ths[k] - GS.TH_WOOD0) / math.pi)
    hue = GLASS_HUES[(len(GLASS_HUES) - 1 - half) % len(GLASS_HUES)]
    return colorsys.hsv_to_rgb(hue, 0.62, 0.9)


def cell_poly(k, ths):
    """ガラス1枚:となりの板とのあいだをうめる、うずまきの通路の一区画。"""
    a = ths[k] - (ths[1] - ths[0]) / 2
    b = ths[k] + (ths[1] - ths[0]) / 2
    pts = [GS.wall_pt(a, 4), GS.wall_pt(b, 4), GS.wall_pt(b + 2 * math.pi, -4), GS.wall_pt(a + 2 * math.pi, -4)]
    return pts


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    shiny_ball(ctx, x, y, r * 0.8, PALETTE[(kind * 12 // 7) % 12])


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    ths = res["ths"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"spiral_speed_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"spiral_speed_{seed}.wav")
    final = os.path.join(OUT_DIR, f"spiral_speed_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"sp_preview_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, CX, CY + OFFSET_Y, reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=("全部割った!!", "COMPLETE", "スピード 600"))
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    polys = [cell_poly(k, ths) for k in range(N_GLASS)]
    cols = [glass_color(k, ths) for k in range(N_GLASS)]
    # 背景+うずまきの壁(動かないので1回だけ)
    static = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    sc = cairo.Context(static)
    sc.set_source_rgb(0.0, 0.0, 0.0)
    sc.paint()
    sc.translate(CX, CY + OFFSET_Y)
    sc.scale(VS, VS)
    sc.translate(-CX, -CY)
    n = int(GS.TH_END / 0.02)
    wpts = [GS.wall_pt(GS.TH_END * k / n) for k in range(n + 1)]
    sc.move_to(*wpts[0])
    for p in wpts[1:]:
        sc.line_to(*p)
    sc.set_source_rgba(1, 1, 1, 0.92)
    sc.set_line_width(4)
    sc.set_line_cap(cairo.LINE_CAP_ROUND)
    sc.stroke()
    prng = np.random.default_rng(seed + 9)
    shards = []
    trail = []
    reset_t = -9.0
    frozen = None
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "break" and (end_t is None or et <= end_t):
                k, x, y, sp_ = data
                for _ in range(5):
                    a = prng.uniform(0, 2 * math.pi)
                    v = prng.uniform(60, 420)
                    shards.append([x, y, v * math.cos(a), v * math.sin(a), prng.uniform(0, 6), prng.uniform(-12, 12),
                                   prng.uniform(5, 13), cols[k], et])
            elif kind == "reset":
                reset_t = et
                trail = []
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
        ctx.set_source_surface(static, 0, 0)
        ctx.paint()
        ctx.save()
        ctx.translate(CX, CY + OFFSET_Y)
        ctx.scale(VS, VS)
        ctx.translate(-CX, -CY)
        # ガラス(元にもどるときは、外側から順にふわっと現れる)
        ra = t - reset_t if fr["attempt"] > 0 else 9.0   # 1回目は最初から全部ある
        for k in range(N_GLASS):
            if not fr["alive"][k]:
                continue
            al = 0.88
            if ra < 0.6:
                al *= max(0.0, min(1.0, (ra * 1.6 - (N_GLASS - 1 - k) / N_GLASS * 0.6) / 0.4))
                if al <= 0:
                    continue
            q = polys[k]
            ctx.move_to(*q[0])
            for c in q[1:]:
                ctx.line_to(*c)
            ctx.close_path()
            ctx.set_source_rgba(*cols[k], al)
            ctx.fill_preserve()
            ctx.set_source_rgba(1, 1, 1, 0.22 * al)
            ctx.set_line_width(1.0)
            ctx.stroke()
        # かけら
        keep = []
        for s_ in shards:
            age = t - s_[8]
            if age > 1.6 or age < 0:
                continue
            x = s_[0] + s_[2] * age
            y = s_[1] + s_[3] * age + 500 * age * age
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(s_[4] + s_[5] * age)
            sz = s_[6]
            ctx.move_to(-sz * 0.6, -sz * 0.3)
            ctx.line_to(sz * 0.5, -sz * 0.5)
            ctx.line_to(sz * 0.1, sz * 0.6)
            ctx.close_path()
            ctx.set_source_rgba(*s_[7], max(0.0, 0.9 * (1 - age / 1.6)))
            ctx.fill()
            ctx.restore()
            keep.append(s_)
        shards = keep[-1600:]
        # ボール(光る・長い光の尾)
        att = max(0, fr["attempt"])
        bc = BALL_COLS[min(att, 3)]
        if fr["ball"] is not None and not over:
            trail.append(fr["ball"])
            trail = trail[-26:]
        elif not over:
            trail = trail[1:] if trail else []
        if len(trail) > 1:
            for j in range(1, len(trail)):
                a = j / len(trail)
                ctx.move_to(*trail[j - 1])
                ctx.line_to(*trail[j])
                ctx.set_source_rgba(*bc, 0.5 * a)
                ctx.set_line_width(GS.BALL_R * 1.4 * a)
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.stroke()
        if fr["ball"] is not None:
            bx, by = fr["ball"]
            g_ = cairo.RadialGradient(bx, by, 0, bx, by, GS.BALL_R * 3)
            g_.add_color_stop_rgba(0, *bc, 0.6)
            g_.add_color_stop_rgba(1, *bc, 0)
            ctx.arc(bx, by, GS.BALL_R * 3, 0, 2 * math.pi)
            ctx.set_source(g_)
            ctx.fill()
            shiny_ball(ctx, bx, by, GS.BALL_R * 0.8, bc)
        ctx.restore()
        # 文字(少なめ)
        chic(ctx, "スピード600で全部割れる？", W / 2, 250, 60, rgb=(1, 0.88, 0.6))
        sp_now = SPEEDS[att] if fr["attempt"] >= 0 else SPEEDS[0]
        chic(ctx, f"スピード {sp_now}", W / 2, 345, 70, rgb=(1, 1, 1), weight="Medium")
        left_n = N_GLASS - fr["cleared"]
        chic(ctx, f"のこり {left_n}", W / 2, 410, 40, rgb=(0.7, 0.75, 0.85), weight="Medium")
        if not over:
            horror(ctx, "失敗したら…", W / 2, 1660, 74, t)
        if over and fail:
            k = min(1.0, after / 0.25)
            chic(ctx, f"あと {left_n} 枚", W / 2, 1060, 100 * (1.2 - 0.2 * k), rgb=(1, 0.4, 0.4))
        if win_b >= 0:
            k = win_b / PRE
            ph_ = (win_b * (8 + 14 * k)) % 1.0
            ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*hsv(win_b * 4), (0.25 + 0.4 * k) * (1 - ph_) ** 2)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['counts']} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


PENTA = [0, 2, 4, 7, 9]


def ping(k, seed):
    """ガラスが割れる「チリン」(うずまきの内側へ進むほど高い)。"""
    rng = np.random.default_rng(seed)
    idx = int(k / N_GLASS * 14)
    m = 72 + 12 * (idx // 5) + PENTA[idx % 5]
    f = midi_hz(m)
    t = _t(0.35)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 12) + 0.5 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t * 20)
    n = rng.normal(0, 1, len(t))
    y += 0.4 * (n - np.convolve(n, np.ones(4) / 4, "same")) * np.exp(-t * 60)
    return 0.4 * y


def whoosh():
    """ボールが落ちてくる「ヒュッ」。"""
    t = _t(0.35)
    n = np.random.default_rng(3).normal(0, 1, len(t))
    lp = np.convolve(n, np.ones(20) / 20, "same")
    return 0.8 * lp * np.sin(np.pi * t / 0.35)


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
    rb = []
    for kind, t, data in events:
        if t > end_t + 0.01:
            continue
        if kind == "break":
            rb = [x for x in rb if t - x < 0.03]
            if len(rb) >= 2:
                continue
            rb.append(t)
            add(ping(data[0], int(t * 1000)), t)
        elif kind == "drop":
            add(whoosh(), t)
    wet = out.copy()
    for dd, g_ in ((0.043, 0.22), (0.071, 0.15), (0.113, 0.1)):
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
