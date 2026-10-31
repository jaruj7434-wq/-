"""「振り子で全部のベルを鳴らせる?」二重振り子の鉄球が、まわりに並んだベルを鳴らしていく物理ショートを生成する。

- 1つの支点からぶら下がった二重振り子(腕2本・鉄球2個)。手を離す角度がシードごとにほんの少し違うだけで、
  あとは重力・振り子・衝突の物理のまま(ねらい・補正なし)。二重振り子なので動きはカオスで予想できない。
- 支点のまわりに真ちゅうのベル24個。鉄球が当たるとベルが鳴って光り、鉄球ははね返る。
- 空気抵抗とベルへの衝突で勢いは少しずつ落ちていく(永久には動かない)。上のほうのベルほど届きにくい。
- 8個鳴らすと2本目、16個で3本目の振り子が落ちてくる(左右交互)。振り子どうしもぶつかる。
制限時間内に24個すべて鳴らせば成功(天使)、残れば失敗(幽霊)。

使い方:
    python pendulum.py search [--want fail|success] [-n 200]
    python pendulum.py render --seed N
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
SUBSTEPS = 8
SR = 48000
GRAVITY = 1600.0

PX, PY = 540.0, 1000.0                 # 振り子の支点
L1, L2 = 230.0, 200.0                  # 腕の長さ
R1, R2 = 20.0, 30.0                    # 鉄球の半径
M1, M2 = 1.0, 1.5
DAMPING = 0.998                        # 1秒あたりに残る速さの割合(空気抵抗)
BELL_R = 22.0
A1, A2 = 160.0, 175.0                 # 手を離す角度(真下から。ほぼ真上に持ち上げてから離す)
BELL_E, BALL_E = 1.0, 0.97             # 反発係数
RINGS = [(170, 6, 0.0), (285, 12, 0.5), (358, 12, 0.0)]  # ベルの輪(支点からの距離, 1周あたりの個数, 角度のずらし)
BOTTOM_FREE = math.radians(50)         # 真下(振り子が止まって垂れ下がる所)の左右この角度にはベルを置かない
ADD_AT = [7, 13, 18, 20, 21]                      # この数だけ鳴らすたびに振り子が1本増える(2本目・3本目)
RING_IMPULSE = 40.0                    # これより強く当たったらベルが鳴る
TIME_LIMIT = 30.0
OUTRO = 2.5

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


def bell_positions():
    pos = []
    for r, n, off in RINGS:
        for k in range(n):
            a = 2 * math.pi * (k + off) / n - math.pi / 2
            from_down = abs((a - math.pi / 2 + math.pi) % (2 * math.pi) - math.pi)
            if from_down < BOTTOM_FREE:
                continue
            pos.append((PX + r * math.cos(a), PY + r * math.sin(a), r))
    return pos


N_BELLS = len(bell_positions())


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 30
        sp.damping = DAMPING
        self.space = sp
        self.bells = []
        for i, (x, y, r) in enumerate(bell_positions()):
            s = pymunk.Circle(sp.static_body, BELL_R, (x, y))
            s.elasticity, s.friction = BELL_E, 0.0
            s.collision_type = 2
            sp.add(s)
            self.bells.append({"x": x, "y": y, "r": r, "rung": False, "shape": s})
        self.bell_of = {b["shape"]: i for i, b in enumerate(self.bells)}
        sp.on_collision(1, 2, post_solve=self._hit_bell)
        sp.on_collision(1, 1, post_solve=self._hit_ball)
        self.pends = []
        self.events = []
        self.rung = 0
        self.t = 0.0
        self.result, self.result_t = None, None
        self.hits = []
        self.add_pendulum(side=1)

    def add_pendulum(self, side):
        """支点から二重振り子をつるして、高い位置から手を離す(角度はシードでほんの少しだけ違う)。"""
        a1 = side * math.radians(A1 + self.rng.uniform(-1.0, 1.0))
        a2 = side * math.radians(A2 + self.rng.uniform(-1.0, 1.0))
        p1 = (PX + L1 * math.sin(a1), PY + L1 * math.cos(a1))
        p2 = (p1[0] + L2 * math.sin(a2), p1[1] + L2 * math.cos(a2))
        bodies = []
        for p, m, r in ((p1, M1, R1), (p2, M2, R2)):
            b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, r))
            b.position = p
            c = pymunk.Circle(b, r)
            c.elasticity, c.friction = BALL_E, 0.0
            c.collision_type = 1
            c.filter = pymunk.ShapeFilter(group=len(self.pends) + 1)   # 同じ振り子の鉄球どうしはぶつからない
            self.space.add(b, c)
            bodies.append(b)
        self.space.add(pymunk.PinJoint(self.space.static_body, bodies[0], (PX, PY), (0, 0)),
                       pymunk.PinJoint(bodies[0], bodies[1], (0, 0), (0, 0)))
        self.pends.append(bodies)
        self.events.append(("pendulum", self.t, len(self.pends)))

    def _hit_bell(self, arb, space, data):
        imp = arb.total_impulse.length
        i = self.bell_of.get(arb.shapes[1])
        if i is not None and imp > RING_IMPULSE:
            self.hits.append((i, imp))

    def _hit_ball(self, arb, space, data):
        imp = arb.total_impulse.length
        if imp > 60:
            p = arb.contact_point_set.points[0].point_a if arb.contact_point_set.points else arb.shapes[0].body.position
            self.events.append(("clank", self.t, (p.x, p.y, imp)))

    def step(self, dt):
        self.t += dt
        self.hits = []
        self.space.step(dt)
        last = {}
        for i, imp in self.hits:
            last[i] = max(imp, last.get(i, 0))
        for i, imp in last.items():
            b = self.bells[i]
            first = not b["rung"] and self.result is None
            if first:
                b["rung"] = True
                self.rung += 1
            self.events.append(("ring", self.t, (i, imp, first)))
            b["last_hit"] = self.t
        if self.result is None:
            k = len(self.pends) - 1
            if k < len(ADD_AT) and self.rung >= ADD_AT[k]:
                self.add_pendulum(side=-1 if k % 2 == 0 else 1)
            if self.rung == N_BELLS:
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
            frames.append({"t": g.t, "rung": g.rung,
                           "pends": [[(b.position.x, b.position.y) for b in p] for p in g.pends],
                           "lit": [b["rung"] for b in g.bells]})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "rung": g.rung, "bells": g.bells}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["rung"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "fail":
        for seed, _, _, c in sorted([r for r in rs if r[1] == "fail"], key=lambda r: -r[3])[:15]:
            print(f"seed={seed:4d}  {c}/{N_BELLS} 個で時間切れ")
    else:
        for seed, _, rt, _ in sorted(succ, key=lambda r: -r[2])[:15]:
            print(f"seed={seed:4d}  全部鳴らした {rt:5.2f}秒")


# ---------------------------------------------------------------- 描画
VIEW_SCALE = 1.2
GOLD = (1, 0.86, 0.2)
BRASS = (0.86, 0.66, 0.26)
BALL_COL = [(0.78, 0.80, 0.84), (0.70, 0.74, 0.80), (0.82, 0.78, 0.72), (0.74, 0.80, 0.78), (0.80, 0.76, 0.82)]


def background():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.RadialGradient(PX, PY, 80, PX, PY, 1300)    # 夜の鐘楼のような暗い背景
    g.add_color_stop_rgb(0, 0.16, 0.11, 0.07)
    g.add_color_stop_rgb(0.5, 0.07, 0.05, 0.05)
    g.add_color_stop_rgb(1, 0.02, 0.02, 0.03)
    ctx.set_source(g)
    ctx.paint()
    # 支点の金具
    ctx.new_path()
    ctx.arc(PX, PY, 31, 0, 2 * math.pi)
    rg = cairo.RadialGradient(PX - 10, PY - 10, 2, PX, PY, 31)
    rg.add_color_stop_rgb(0, 0.95, 0.85, 0.55)
    rg.add_color_stop_rgb(1, 0.45, 0.32, 0.12)
    ctx.set_source(rg)
    ctx.fill()
    return surf


def draw_bell(ctx, x, y, lit, swing, glow):
    """手持ちのハンドベルの形(上に持ち手、下に広がる口)。鳴ると金色に光って左右に揺れる。"""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(swing)
    s = BELL_R / 22.0
    if glow > 0:
        hg = cairo.RadialGradient(0, 4 * s, 4, 0, 4 * s, 70 * s)
        hg.add_color_stop_rgba(0, 1, 0.85, 0.35, 0.55 * glow)
        hg.add_color_stop_rgba(1, 1, 0.85, 0.35, 0.0)
        ctx.new_path()
        ctx.arc(0, 4 * s, 70 * s, 0, 2 * math.pi)
        ctx.set_source(hg)
        ctx.fill()
    # 持ち手
    ctx.new_path()
    ctx.rectangle(-4 * s, -34 * s, 8 * s, 14 * s)
    ctx.set_source_rgb(0.30, 0.18, 0.10)
    ctx.fill()
    # 本体(ドーム → 広がる口)
    ctx.new_path()
    ctx.move_to(-10 * s, -20 * s)
    ctx.curve_to(-14 * s, -20 * s, -16 * s, -6 * s, -18 * s, 8 * s)
    ctx.curve_to(-20 * s, 16 * s, -26 * s, 20 * s, -27 * s, 24 * s)
    ctx.line_to(27 * s, 24 * s)
    ctx.curve_to(26 * s, 20 * s, 20 * s, 16 * s, 18 * s, 8 * s)
    ctx.curve_to(16 * s, -6 * s, 14 * s, -20 * s, 10 * s, -20 * s)
    ctx.close_path()
    bg = cairo.LinearGradient(-27 * s, 0, 27 * s, 0)
    if lit:
        bg.add_color_stop_rgb(0, 0.62, 0.42, 0.10)
        bg.add_color_stop_rgb(0.35, 1.0, 0.92, 0.55)
        bg.add_color_stop_rgb(0.6, 0.95, 0.74, 0.25)
        bg.add_color_stop_rgb(1, 0.50, 0.32, 0.08)
    else:
        bg.add_color_stop_rgb(0, 0.22, 0.15, 0.08)
        bg.add_color_stop_rgb(0.35, 0.48, 0.36, 0.18)
        bg.add_color_stop_rgb(1, 0.18, 0.12, 0.06)
    ctx.set_source(bg)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.12, 0.07, 0.02, 0.9)
    ctx.set_line_width(1.5)
    ctx.stroke()
    # 口のふち
    ctx.new_path()
    ctx.save()
    ctx.translate(0, 24 * s)
    ctx.scale(27 * s, 4 * s)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(*((0.55, 0.38, 0.10) if lit else (0.16, 0.11, 0.05)))
    ctx.fill()
    ctx.restore()


def draw_ball(ctx, x, y, r, col, trail):
    for j, (tx, ty) in enumerate(trail):
        a = (j + 1) / (len(trail) + 1)
        ctx.new_path()
        ctx.arc(tx, ty, r * (0.5 + 0.4 * a), 0, 2 * math.pi)
        ctx.set_source_rgba(*col, 0.10 * a)
        ctx.fill()
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.08, x, y, r)
    g.add_color_stop_rgb(0, 1, 1, 1)
    g.add_color_stop_rgb(0.35, *col)
    g.add_color_stop_rgb(1, col[0] * 0.25, col[1] * 0.25, col[2] * 0.28)
    ctx.new_path()
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()


def draw_rod(ctx, a, b, w):
    for wd, col in ((w + 4, (0.08, 0.08, 0.09)), (w, (0.55, 0.57, 0.60)), (w * 0.35, (0.85, 0.87, 0.90))):
        ctx.new_path()
        ctx.move_to(*a)
        ctx.line_to(*b)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgb(*col)
        ctx.set_line_width(wd)
        ctx.stroke()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"pendulum_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"pendulum_{seed}.wav")
    final = os.path.join(OUT_DIR, f"pendulum_{seed}.mp4")
    bg = background()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    angels = AngelShow(W, H, seed) if result == "success" else None
    bells = bell_positions()
    hit_t = {}            # ベル番号 → 最後に当たった時刻と強さ
    waves = []
    trails = {}
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "ring":
                i, imp, first = data
                hit_t[i] = (et, min(1.0, imp / 400))
                waves.append([et, bells[i][0], bells[i][1], first])
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0

        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        ctx.save()   # 盤面は支点を中心に少し拡大して見せる(物理はそのまま)
        ctx.translate(PX, PY)
        ctx.scale(VIEW_SCALE, VIEW_SCALE)
        ctx.translate(-PX, -PY)
        for i, (x, y, _) in enumerate(bells):
            swing, glow = 0.0, 0.0
            if i in hit_t:
                age = t - hit_t[i][0]
                k = hit_t[i][1]
                swing = 0.45 * k * math.exp(-age * 2.5) * math.sin(age * 18)
                glow = max(0.0, 1 - age / 0.8) if age < 0.8 else 0.0
            draw_bell(ctx, x, y, fr["lit"][i], swing, max(glow, 0.25 if fr["lit"][i] else 0.0))
        keep = []
        for wv in waves:   # 鳴った音の広がり
            age = t - wv[0]
            if age < 0.7:
                ctx.new_path()
                ctx.arc(wv[1], wv[2], 30 + 160 * age, 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.88, 0.45, (0.7 if wv[3] else 0.3) * (1 - age / 0.7))
                ctx.set_line_width(4)
                ctx.stroke()
                keep.append(wv)
        waves = keep
        for k, (p1, p2) in enumerate(fr["pends"]):
            draw_rod(ctx, (PX, PY), p1, 7)
            draw_rod(ctx, p1, p2, 6)
        for k, (p1, p2) in enumerate(fr["pends"]):
            tr = trails.setdefault(k, [])
            col = BALL_COL[k % len(BALL_COL)]
            draw_ball(ctx, p1[0], p1[1], R1, col, [])
            draw_ball(ctx, p2[0], p2[1], R2, col, tr)
            tr.append(p2)
            del tr[:-8]
        ctx.new_path()
        ctx.arc(PX, PY, 12, 0, 2 * math.pi)
        ctx.set_source_rgb(0.9, 0.78, 0.45)
        ctx.fill()
        ctx.restore()
        if angels is not None and over:
            angels.draw(ctx, t - end_t)

        # 上の帯
        g = cairo.LinearGradient(0, 0, 0, 470)
        g.add_color_stop_rgba(0, 0.02, 0.015, 0.01, 0.92)
        g.add_color_stop_rgba(0.85, 0.02, 0.015, 0.01, 0.75)
        g.add_color_stop_rgba(1, 0.02, 0.015, 0.01, 0.0)
        ctx.rectangle(0, 0, W, 470)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, "振り子で全部の", W / 2, 150, 80, sw=14)
        text(ctx, "ベルを鳴らせる？", W / 2, 270, 100, rgb=GOLD, sw=18)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 360, 54, rgb=(1, 0.35, 0.35) if left < 8 else (1, 1, 1), sw=10)
        text(ctx, f"ベル {fr['rung']} / {N_BELLS}", W / 2, 1620, 64,
             rgb=GOLD if fr["rung"] == N_BELLS else (1, 1, 1), sw=12)
        text(ctx, f"♪ {SONG_TITLE}", W / 2, 1710, 46, rgb=(1, 0.9, 0.6), sw=10)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 1000, 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{N_BELLS - res['rung']}音で曲が終わったのに…", W / 2, 1130, 66, sw=12)
        elif over:
            age = t - end_t
            if age < 0.3:
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.8 * (1 - age / 0.3))
                ctx.fill()
            k = min(1.0, age / 0.25)
            text(ctx, "全部鳴らした！", W / 2, 1700, 100 * (1.4 - 0.4 * k), rgb=GOLD, sw=20)

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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['rung']}/{N_BELLS}個 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
MIX_GAIN = 0.6   # 通常部分の音量(約 -18dB になるよう調整)
HOLY_GAIN = 0.85
# ベルを新しく1個鳴らすたびに曲が1音進む:「ジングルベル」(ピアポント作・1857年・パブリックドメイン)のサビを22音に
SONG_TITLE = "ジングルベル"
#            ジン グル ベー ル  ジン グル ベー ル  ジン グル オー ル ザ ウェイ
MELODY = [76, 76, 76, 76, 76, 76, 76, 79, 72, 74, 76,
          77, 77, 77, 77, 76, 76, 79, 79, 77, 74, 72]
#         オー ワッ ファン イッ イズ トゥ ライ ド ... (最後はド=Cで終わる)
CHORD = [48, 48, 48, 48, 48, 48, 48, 48, 48, 43, 48,
         53, 53, 53, 53, 48, 48, 43, 43, 43, 43, 48]
assert len(MELODY) == N_BELLS
# 1度鳴ったベルにまた当たったときは、いま鳴っている音を小さく響かせる(曲が濁らない)
PENTA = [0, 2, 4, 7, 9]


def bell_note(i):
    pos = bell_positions()
    r = pos[i][2]
    ring = [rr for rr, _, _ in RINGS].index(r)
    base = [84, 76, 69][ring]   # 内側 C6 付近 / 真ん中 E5 付近 / 外側 A4 付近
    return base + PENTA[i % 5]


def handbell(freq, amp, seed):
    """ハンドベルの音:少しずれた倍音(1, 2.76, 5.40, 8.93倍)が長く響き、打った瞬間に金属音。"""
    dur = 2.6
    t = np.arange(int(dur * SR)) / SR
    y = np.zeros_like(t)
    for ratio, a, dec in ((1.0, 1.0, 1.4), (2.0, 0.35, 2.2), (2.76, 0.45, 3.0), (5.40, 0.22, 5.5), (8.93, 0.10, 9.0)):
        y += a * np.sin(2 * np.pi * freq * ratio * t + ratio) * np.exp(-t * dec)
    y *= 1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)          # わずかなうなり
    hit = np.random.default_rng(seed).normal(0, 1, len(t)) * np.exp(-t * 300) * 0.4
    return amp * (y + hit) * np.minimum(1, t / 0.002)


def clank(amp, seed):
    """鉄球どうしがぶつかる「カチン」。"""
    t = np.arange(int(0.25 * SR)) / SR
    rng = np.random.default_rng(seed)
    y = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((2100, 30), (3400, 45), (5200, 60)))
    return amp * (y / 3 + rng.normal(0, 1, len(t)) * np.exp(-t * 400) * 0.3)


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 3) * SR)
    out = np.zeros((n_out, 2))
    pos = bell_positions()

    def add(sig, t0, pan=0.0, gain=1.0):
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out:
            out[i:j, 0] += gain * sig[: j - i] * math.sqrt(0.5 * (1 - pan))
            out[i:j, 1] += gain * sig[: j - i] * math.sqrt(0.5 * (1 + pan))

    note_i = -1
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.05:
            continue
        if kind == "ring":
            i, imp, first = data
            pan = (pos[i][0] - PX) / 500
            if first:   # 曲が1音進む:メロディ+低い和音
                note_i += 1
                amp = 0.55 + 0.45 * min(1.0, imp / 400)
                add(handbell(midi_hz(MELODY[note_i]), amp, int(t * 1000)), t, pan=pan)
                add(handbell(midi_hz(CHORD[note_i]), 0.35, int(t * 1000) + 1), t, pan=0.0)
                add(handbell(midi_hz(CHORD[note_i] + 7), 0.18, int(t * 1000) + 2), t, pan=0.0)
            elif note_i >= 0:   # 鳴らし済みのベル:いまの音を小さく1オクターブ上で
                add(handbell(midi_hz(MELODY[note_i] + 12), 0.12, int(t * 1000)), t, pan=pan)
        elif kind == "clank":
            x, y, imp = data
            add(clank(min(1.0, imp / 600) * 0.5, int(t * 1000)), t, pan=(x - PX) / 500)
    extra = np.zeros(n_out)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += HOLY_GAIN * sig[:m]
    wet = out.copy()
    for d, g in ((0.037, 0.35), (0.061, 0.28), (0.097, 0.2), (0.151, 0.14)):   # 鐘楼のような長い響き
        k = int(d * SR)
        wet[k:, 0] += wet[:-k, 1] * g
        wet[k:, 1] += wet[:-k, 0] * g
    wet = wet[: int(duration * SR)]
    wet = np.tanh(2.0 * wet / max(1e-9, np.max(np.abs(wet)))) / np.tanh(2.0) * MIX_GAIN
    wet = np.clip(wet + (0.95 if fail else 1.0) * extra[: len(wet), None], -0.98, 0.98)
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
