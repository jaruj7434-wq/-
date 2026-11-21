"""「当たるたびに大きくなる六角形で、六角形の枠を全部うめられる?」ゆっくり回る六角形の枠の中を、六角形の玉が重力で跳ねる。
壁に当たるたびに、玉はどの面も同じ割合で大きくなる。枠いっぱいまで育つと枠にカチッとぴったりハマって、色つきの六角形の輪になり、
一回り小さい新しい枠になる。その内側にまた新しい六角形の玉が出てきて、同じことをくり返す。まん中まで全部うまれば成功、
制限時間内にうまらなければ失敗。

- 重力・反発・回る枠の押し出しのまま(ねらい・補正なし)。大きくなるのは、壁から離れていた玉が新しく壁にぶつかった瞬間だけ。
- ハマる条件:玉(六角形)の外接円の半径が、いまの枠の外接円の半径の HIT_FIT 倍をこえたとき(それ以上は回れなくなる大きさ)。
  ハマるときは0.35秒かけて、枠の向き・まん中にぴったり合わさる(演出)。
- 成功ならパチンコの当たり風の演出、失敗なら幽霊。

使い方:
    python hex_nest.py search [-n 80]
    python hex_nest.py render --seed N
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
from pachinko import kyuin_music  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "glass_spiral"))
import jackpot_end as JP  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 6
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

CX, CY = 540.0, 990.0
R_FRAME = 430.0                                   # いちばん外の枠(六角形の外接円の半径)
LAYER = float(os.environ.get("LAYER", 80.0))      # 1段ごとに枠が小さくなる量(外接円の半径)
R_END = 70.0                                      # 枠がこれより小さくなったら、全部うまった(成功)
SPIN = float(os.environ.get("SPIN", 1.2))        # 枠が回る速さ
GROW = float(os.environ.get("GROW", 1.1))        # 1回当たるごとの大きさの倍率
START_K = 0.3                                     # (使わない)
R_START = float(os.environ.get("R_START", 18.0))  # 新しい玉の大きさ(外接円の半径・どの段でも同じ)
FIT = 0.84                                        # この大きさ(いまの枠に対する割合)まで育つとハマる
GRAVITY = float(os.environ.get("GRAVITY", 3000.0))
BALL_E = float(os.environ.get("BALL_E", 0.97))
SNAP_T = 0.22   # ハマるまでの時間(吸いこまれるように速くなって、ピタッと止まる)
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 48.1))
OUTRO = 4.2
WIN_DUR = JP.DURATION - JP.T_BIG   # 成功の演出の長さ(スロットなし。全部ハマった瞬間から、いきなり本番の大当たり演出)


def n_layers():
    n, r = 0, R_FRAME
    while r >= R_END:
        n += 1
        r -= LAYER
    return n


N_LAYERS = n_layers()


def hexv(r, rot=0.0):
    return [(r * math.cos(rot + k * math.pi / 3), r * math.sin(rot + k * math.pi / 3)) for k in range(6)]


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 25
        self.space = sp
        fb = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        fb.position = (CX, CY)
        fb.angle = rng.uniform(0, math.pi / 3)
        fb.angular_velocity = SPIN
        sp.add(fb)
        self.frame = fb
        self.walls = []
        self.rf = R_FRAME
        self.set_walls(self.rf)
        self.layers = 0
        self.ball = None
        self.t = 0.0
        self.events = []
        self.touching = 0
        self.last_sep = -1.0
        self.pending = False
        self.next_spawn = 0.0
        self.result, self.result_t = None, None
        sp.on_collision(1, 2, begin=self._hit, separate=self._sep)

    def set_walls(self, r):
        """枠の内側の壁(六角形)を、外接円の半径 r で作り直す。"""
        if self.walls:
            self.space.remove(*self.walls)
        v = hexv(r + 6)
        self.walls = []
        for a, b in zip(v, v[1:] + v[:1]):
            s = pymunk.Segment(self.frame, a, b, 6)
            s.elasticity, s.friction = 1.0, 0.5
            s.collision_type = 2
            self.walls.append(s)
        self.space.add(*self.walls)

    def spawn(self):
        r = R_START   # どの段でも、同じ小さな大きさからスタート
        b = pymunk.Body(1.0, pymunk.moment_for_poly(1.0, hexv(r)))
        b.position = (CX + self.rng.uniform(-0.2, 0.2) * self.rf, CY - self.rng.uniform(0.0, 0.3) * self.rf)
        b.velocity = (self.rng.uniform(-250, 250), self.rng.uniform(-150, 50))
        b.angle = self.rng.uniform(0, math.pi / 3)
        b.angular_velocity = self.rng.uniform(-2, 2)
        s = pymunk.Poly(b, hexv(r), radius=1)
        s.elasticity, s.friction = BALL_E, 0.5
        s.collision_type = 1
        self.space.add(b, s)
        self.ball, self.shape, self.r = b, s, r
        self.touching = 0
        self.events.append(("spawn", self.t, (r, self.layers)))

    def _hit(self, arb, space, data):
        self.touching += 1
        if self.touching == 1 and self.t - self.last_sep > 0.03:
            self.pending = True
        return True

    def _sep(self, arb, space, data):
        self.touching = max(0, self.touching - 1)
        if self.touching == 0:
            self.last_sep = self.t

    def grow(self):
        b = self.ball
        self.r *= GROW
        self.space.remove(self.shape)
        s = pymunk.Poly(b, hexv(self.r), radius=1)
        s.elasticity, s.friction = BALL_E, 0.5
        s.collision_type = 1
        m = (self.r / 30) ** 2
        b.mass = m
        b.moment = pymunk.moment_for_poly(m, hexv(self.r))
        self.space.add(s)
        self.shape = s

    def step(self, dt):
        if self.ball is None and self.result is None and self.t >= self.next_spawn:
            self.spawn()
        self.space.step(dt)
        self.t += dt
        if self.ball is not None and self.pending:
            self.pending = False
            self.grow()
            self.events.append(("grow", self.t, (self.r, self.layers)))
            if self.r >= FIT * self.rf:   # 枠いっぱい:ぴったりハマる
                b = self.ball
                self.events.append(("snap", self.t, (b.position.x, b.position.y, b.angle, self.r, self.rf, self.layers)))
                self.space.remove(b, self.shape)
                self.ball = None
                self.layers += 1
                self.rf -= LAYER
                self.touching = 0
                self.next_spawn = self.t + SNAP_T + 0.15
                if self.rf < R_END:
                    self.result, self.result_t = "success", self.t + SNAP_T
                    self.events.append(("success", self.t + SNAP_T, None))
                else:
                    self.set_walls(self.rf)
        if self.result is None and self.t >= TIME_LIMIT:
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
            b = g.ball
            frames.append({"t": g.t, "rot": g.frame.angle, "rf": g.rf, "layers": g.layers,
                           "ball": None if b is None else (b.position.x, b.position.y, b.angle, g.r)})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else WIN_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "layers": g.layers}


def score(seed):
    r = simulate(seed)
    snaps = [round(e[1], 1) for e in r["events"] if e[0] == "snap"]
    return seed, r["result"], round(r["result_t"], 1), r["layers"], snaps


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件 / 段数 {N_LAYERS}")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def layer_col(k):
    return colorsys.hsv_to_rgb((k / max(1, N_LAYERS)) * 0.85 % 1.0, 0.75, 1.0)


def hex_path(ctx, cx, cy, r, rot):
    v = hexv(r, rot)
    ctx.move_to(cx + v[0][0], cy + v[0][1])
    for x, y in v[1:]:
        ctx.line_to(cx + x, cy + y)
    ctx.close_path()


def draw_hex_ball(ctx, x, y, r, rot, col, glow=1.0):
    """六角形の玉(つやのある色ガラス+白いふち+光)。"""
    for mul, al in ((1.5, 0.2 * glow), (1.2, 0.35 * glow)):
        g = cairo.RadialGradient(x, y, r * 0.7, x, y, r * mul)
        g.add_color_stop_rgba(0, *col, al)
        g.add_color_stop_rgba(1, *col, 0)
        ctx.arc(x, y, r * mul, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
    hex_path(ctx, x, y, r, rot)
    g = cairo.RadialGradient(x - r * 0.3, y - r * 0.35, r * 0.05, x, y, r)
    g.add_color_stop_rgb(0, *(min(1, c + 0.5) for c in col))
    g.add_color_stop_rgb(0.5, *col)
    g.add_color_stop_rgb(1, *(c * 0.55 for c in col))
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.9)
    ctx.set_line_width(max(2, r * 0.04))
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    hex_path(ctx, x, y, r * 0.72, rot)
    ctx.set_source_rgba(1, 1, 1, 0.25)
    ctx.set_line_width(max(1.5, r * 0.02))
    ctx.stroke()


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    col = colorsys.hsv_to_rgb((t * 0.7) % 1.0, 0.8, 1.0) if kind == 6 else colorsys.hsv_to_rgb(kind / 7, 0.75, 1.0)
    draw_hex_ball(ctx, x, y, r * 0.9, t * 0.8 if kind == 6 else 0.0, col)


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"hex_nest_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"hex_nest_{seed}.wav")
    final = os.path.join(OUT_DIR, f"hex_nest_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"hn_preview_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, CX, CY, reel_ball, n_kinds=7, win=6,
                                          texts=("うまった!!", "COMPLETE", f"{N_LAYERS} / {N_LAYERS} 段"), shake=22)
    snaps = [e for e in events if e[0] == "snap"]
    flashes = []
    bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    bc = cairo.Context(bg)
    gr = cairo.RadialGradient(CX, CY, 50, CX, CY, 1100)
    gr.add_color_stop_rgb(0, 0.1, 0.08, 0.18)
    gr.add_color_stop_rgb(1, 0.02, 0.02, 0.05)
    bc.set_source(gr)
    bc.paint()
    frozen = None
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "snap":
                flashes.append(et)
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ending is not None and over and t - end_t >= 1 / FPS - 1e-9:
            ending.draw(surf, ctx, t - end_t + JP.T_BIG)   # スロットはとばして、本番から
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
        rot = fr["rot"]
        shake = 0.0
        for s_ in snaps:   # ピタッとハマった瞬間、画面がほんの少しだけゆれる
            a_ = t - s_[1] - SNAP_T
            if 0 <= a_ < 0.2:
                shake = max(shake, 7 * (1 - a_ / 0.2))
        ctx.save()
        ctx.translate(shake * math.sin(t * 90), shake * math.cos(t * 77))
        # すでにハマった段(色つきの六角形の輪)。いちばん外の枠も輪で描く
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        hex_path(ctx, CX, CY, R_FRAME + 26, rot)
        hex_path(ctx, CX, CY, R_FRAME + 4, rot)
        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        ctx.set_source_rgb(0.85, 0.87, 0.92)
        ctx.fill()
        ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
        done = [s for s in snaps if s[1] + SNAP_T <= t]
        for k, s in enumerate(done):
            ro, ri = s[2][4], s[2][4] - LAYER
            col = layer_col(k)
            hex_path(ctx, CX, CY, ro + 4, rot)
            hex_path(ctx, CX, CY, max(0, ri + 4), rot)
            ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            g = cairo.RadialGradient(CX, CY, ri, CX, CY, ro)
            g.add_color_stop_rgb(0, *(c * 0.6 for c in col))
            g.add_color_stop_rgb(0.5, *col)
            g.add_color_stop_rgb(1, *(min(1, c + 0.3) for c in col))
            ctx.set_source(g)
            ctx.fill()
            ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
            hex_path(ctx, CX, CY, ro + 4, rot)
            ctx.set_source_rgba(1, 1, 1, 0.6)
            ctx.set_line_width(2)
            ctx.stroke()
        # ハマっていく途中(0.35秒で、枠の向き・まん中にぴったり合わさる)
        for k, s in enumerate(snaps):
            et, (x0, y0, a0, r0, rf, lay) = s[1], s[2]
            u = (t - et) / SNAP_T
            if 0 <= u < 1:
                e = u * u * u   # 吸いこまれるように、だんだん速く
                da = (rot - a0 + math.pi / 6) % (math.pi / 3) - math.pi / 6
                x = x0 + (CX - x0) * e
                y = y0 + (CY - y0) * e
                a = a0 + da * e
                rr = r0 + (rf + 4 - r0) * e
                draw_hex_ball(ctx, x, y, rr, a, layer_col(lay))
        # 玉
        if fr["ball"] is not None:
            x, y, a, r = fr["ball"]
            k = min(1.0, (r / fr["rf"] - START_K) / (FIT - START_K))
            col = layer_col(fr["layers"])
            draw_hex_ball(ctx, x, y, r, a, tuple(c * (0.6 + 0.4 * k) for c in col), 0.5 + 0.8 * k)
        keep = []
        for et in flashes:   # ピタッとハマった瞬間:白い光・外へ広がる波紋・輪がキュッと光る
            a_ = t - et - SNAP_T
            if -SNAP_T < a_ < 0.6:
                if a_ >= 0:
                    ro = fr["rf"] + LAYER + 4
                    if a_ < 0.12:   # 一瞬、輪全体が白く光る
                        hex_path(ctx, CX, CY, ro, rot)
                        hex_path(ctx, CX, CY, fr["rf"] + 4, rot)
                        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
                        ctx.set_source_rgba(1, 1, 1, 0.85 * (1 - a_ / 0.12))
                        ctx.fill()
                        ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
                    for k2 in range(2):   # 外へ広がる波紋(2重)
                        b_ = a_ - 0.06 * k2
                        if 0 <= b_ < 0.5:
                            hex_path(ctx, CX, CY, ro + 260 * b_, rot)
                            ctx.set_source_rgba(1, 1, 1, 0.6 * (1 - b_ / 0.5))
                            ctx.set_line_width(6 * (1 - b_ / 0.5) + 1)
                            ctx.stroke()
                keep.append(et)
        flashes = keep
        ctx.restore()
        # 文字
        text(ctx, "当たるたびに大きくなる六角形", W / 2, 235, 60, sw=12)
        text(ctx, "枠を全部うめられる？", W / 2, 335, 92, rgb=GOLD, sw=16)
        text(ctx, f"{fr['layers']} / {N_LAYERS} 段", W / 2, 445, 66, rgb=(1, 1, 1), sw=10)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 520, 40, rgb=(1, 0.4, 0.4) if left < 10 else (0.95, 0.95, 0.95), sw=8)
        if not over:
            text(ctx, "失敗したら・・・", W / 2, 1530, 54, rgb=(1, 0.45, 0.45), sw=10)
        if over and fail:
            k = min(1.0, after / 0.25)
            ctx.rectangle(0, 880, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.6)
            ctx.fill()
            text(ctx, "時間切れ…", W / 2, 990, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"{res['layers']} / {N_LAYERS} 段までだった…", W / 2, 1110, 66, sw=12)
        elif ending is not None and over:
            ending.draw(surf, ctx, t - end_t + JP.T_BIG)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['layers']}/{N_LAYERS}段 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def marimba(f, amp):
    """壁に当たる「コン」:マリンバのような、やわらかくて気持ちいい音(木の響き+少しの金属のきらめき)。"""
    t = _t(0.6)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t * 7)
         + 0.45 * np.sin(2 * np.pi * 4.0 * f * t) * np.exp(-t * 28)
         + 0.2 * np.sin(2 * np.pi * 10.0 * f * t) * np.exp(-t * 60))
    return amp * y * np.minimum(1, t / 0.002)


def snap_snd(layer):
    """ピタッ!とハマる音:カチッ(高く短いクリック)+ドゥン(やわらかい低音)+キラキラと駆け上がる鐘の和音(段が上がるほど高い)。"""
    t = _t(1.4)
    rng = np.random.default_rng(layer + 5)
    n = rng.normal(0, 1, len(t))
    hp = n - np.convolve(n, np.ones(4) / 4, "same")
    click = (0.7 * hp * np.exp(-t * 400) + 0.6 * np.sin(2 * np.pi * 3800 * t) * np.exp(-t * 150))
    thump = 0.8 * np.sin(2 * np.pi * np.cumsum(110 * np.exp(-t * 25) + 55) / SR) * np.exp(-t * 14)
    root = 72 + 2 * layer
    bells = np.zeros(len(t))
    for k, m in enumerate((0, 4, 7, 12, 16)):
        d = int((0.04 + 0.045 * k) * SR)
        tt = t[: len(t) - d]
        f = midi_hz(root + m)
        bells[d:] += (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 2.76 * f * tt) * np.exp(-tt * 8)) * np.exp(-tt * 3.0)
    return click + thump + 0.28 * bells


def kyuin_one(up=1.0):
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
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.01:
            continue
        if kind == "grow":   # 当たって大きくなる「コン」:その段で育つほど、ドレミソラの音階で上がっていく
            r, lay = data
            rf = R_FRAME - LAYER * lay
            k = max(0.0, min(1.0, (r / rf - START_K) / (FIT - START_K)))
            penta = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]
            add(marimba(midi_hz(60 + 2 * lay + penta[int(k * (len(penta) - 1))]), 0.6), t)
        elif kind == "snap":
            add(snap_snd(data[5]), t + SNAP_T, 0.9)
    wet = out.copy()
    for dd, g_ in ((0.043, 0.25), (0.071, 0.16), (0.11, 0.1)):
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
        # 全部ハマった瞬間から:ドーン!+大当たりのファンファーレ連打・キュイン・チャリンチャリン(jackpot_end の本番の部分)に、
        # キュインキュインの連打+ファンファーレ+ジャラジャラ(pachinko.py)と「キュイン!」の連打を重ねる
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
        tb = np.arange(int(1.5 * SR)) / SR   # ドーン!
        boom = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-tb * 6) + 35) / SR) * np.exp(-tb * 2.5)
        mus[:len(boom)] += 0.9 * boom
        mus *= np.minimum(1, (WIN_DUR - np.arange(n) / SR) / 0.6)
        mus = np.tanh(1.6 * mus / (np.abs(mus).max() + 1e-9)) / np.tanh(1.6)
        i0 = int(end_t * SR)
        m = min(len(mus), n_out - i0)
        extra[i0:i0 + m] += 1.1 * mus[:m]
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
