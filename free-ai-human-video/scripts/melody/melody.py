"""「この玉、最後まで弾ききれる?」ピアノの鍵盤の階段を自然に跳ね落ちながら曲を奏でる物理ショートを生成する。

- 玉はジグザグに続く階段(1段ずつがピアノの鍵盤)を、重力・反発・摩擦だけで自然に跳ねながら落ちていく。
  玉の動きには一切手を加えない(ねらって打ち出したり、向きを直したりしない)。
- 玉が段に強く当たるたびに「きらきら星」が1音ずつ進む(強く跳ねて段を飛ばせば、リズムも自然に崩れる)。
- ところどころの段の真ん中にすき間(落とし穴)がある。跳ねてまたげば進めるが、はまったら失敗。
- 展開:最初の階段は穴なし → 落とし穴出現 → 階段が急になって速くなる → 穴が増える → ラスト1音。
42音すべて弾ききれば成功(天使)、その前に落とし穴に落ちたら失敗(曲が止まり、幽霊)。

使い方:
    python melody.py search [--want fail|success]
    python melody.py render --seed N
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
from ball_escape import hue_rgb, midi_hz, text  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from angels import DURATION as ANGEL_DUR, AngelShow, holy_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 6
SR = 48000
GRAVITY = 2200.0

# 「きらきら星」(フランス民謡・パブリックドメイン)
SONG_TITLE = "きらきら星"
MELODY = [60, 60, 67, 67, 69, 69, 67, 65, 65, 64, 64, 62, 62, 60,
          67, 67, 65, 65, 64, 64, 62, 67, 67, 65, 65, 64, 64, 62,
          60, 60, 67, 67, 69, 69, 67, 65, 65, 64, 64, 62, 62, 60]
CHORD = [48, 48, 48, 48, 53, 53, 48, 53, 53, 48, 48, 55, 55, 48,
         48, 48, 53, 53, 48, 48, 55, 48, 48, 53, 53, 48, 48, 55,
         48, 48, 48, 48, 53, 53, 48, 53, 53, 48, 48, 55, 55, 48]
DOREMI = {60: "ド", 62: "レ", 64: "ミ", 65: "ファ", 67: "ソ", 69: "ラ", 71: "シ"}
N = len(MELODY)

BALL_R = 15
STEPS = 8                  # 1つの階段の段数
STEP_W = 112
FLIGHTS = 14
STEP_H = [52, 52, 55, 58, 60, 62, 64, 66, 68, 70, 70, 70, 70, 70]     # 階段ごとの1段の高さ(だんだん急になる)
FLIGHT_GAP = 130           # 階段と、その下の階段の間のすき間
WALL_L, WALL_R = 40, W - 40   # 左右の壁。階段は壁にくっついて始まり、反対側の端に1段ぶんの落ち口がある
TILT = math.radians(9)     # 段は進む向きに少し下がっている(玉が止まらずに進む)
# 抜けている段(落とし穴)。(階段番号, 段番号)
HOLES_BY_FLIGHT = [[], [5], [4], [5], [3, 6], [4, 6], [3, 5], [4, 6], [3, 5], [4, 6], [3, 5], [4, 6], [3, 5], [4, 6]]
HOLE_W = [0, 50, 54, 58, 86, 90, 94, 94, 94, 94, 94, 94, 94, 94]   # 階段ごとの穴の幅(曲の終盤にあたる階段ほど広い)
NOTE_IMPULSE = 220.0       # これより強く当たったら1音進む
NOTE_GAP = 0.08            # 音と音の最小間隔(秒)
OUTRO = 3.0
TRAP_WAIT = 0.6            # 落とし穴に落ちてから失敗確定までの秒数

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


def layout(holes_by_flight):
    """各段の(左x, 上面y, 階段番号, 段番号, 抜けているか)と、階段の向きを返す。"""
    steps = []
    y = 520.0
    for f in range(FLIGHTS):
        d = 1 if f % 2 == 0 else -1
        for k in range(STEPS):
            xl = WALL_L + k * STEP_W if d > 0 else WALL_R - (k + 1) * STEP_W
            steps.append({"x": xl, "y": y + k * STEP_H[f], "f": f, "k": k, "dir": d,
                          "hole": k in holes_by_flight[f]})
        y += STEPS * STEP_H[f] + FLIGHT_GAP
    return steps


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed, holes=None):
        rng = np.random.default_rng(seed)
        self.rng = rng
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 25
        self.space = sp
        st = sp.static_body
        self.steps = layout(holes or HOLES_BY_FLIGHT)
        self.step_of_shape = {}
        for i, s in enumerate(self.steps):
            d = s["dir"]
            xa, xb = s["x"], s["x"] + STEP_W

            def surf_y(x):   # 段の上面(進む向きに少し下がる)
                u = (x - xa) / STEP_W if d > 0 else (xb - x) / STEP_W
                return s["y"] + u * STEP_W * math.tan(TILT)

            if s["hole"]:
                # 段の真ん中にすき間を空け、その下に落とし穴の箱をつるす(はまったら出られない)
                hw = HOLE_W[s["f"]]
                h0, h1 = (xa + xb) / 2 - hw / 2, (xa + xb) / 2 + hw / 2
                s["gap"] = (h0, h1)
                parts = [(xa, h0), (h1, xb)]
                top, bot = max(surf_y(h0), surf_y(h1)) + 8, max(surf_y(h0), surf_y(h1)) + 70
                for a, b in (((h0, top), (h0, bot)), ((h0, bot), (h1, bot)), ((h1, bot), (h1, top))):
                    seg = pymunk.Segment(st, a, b, 4)
                    seg.elasticity, seg.friction = 0.2, 0.9
                    seg.collision_type = 3
                    sp.add(seg)
            else:
                parts = [(xa, xb)]
            for p0, p1 in parts:
                seg = pymunk.Segment(st, (p0, surf_y(p0)), (p1, surf_y(p1)), 5)
                seg.elasticity, seg.friction = 0.62, 0.5
                seg.collision_type = 2
                sp.add(seg)
                self.step_of_shape[seg] = i
        # 画面の左右の壁
        for x in (WALL_L - 6, WALL_R + 6):
            seg = pymunk.Segment(st, (x, 0), (x, self.steps[-1]["y"] + 600), 6)
            seg.elasticity = 0.5
            sp.add(seg)
        # 玉:最初の段の少し上から、ほんの少し横向きの速さで落とす(ここだけ毎回わずかに違う)
        m = 1.0
        self.ball = pymunk.Body(m, pymunk.moment_for_circle(m, 0, BALL_R))
        self.ball.position = (WALL_L + STEP_W * 0.5, 380)
        self.ball.velocity = (rng.uniform(80, 220), 0)
        c = pymunk.Circle(self.ball, BALL_R)
        c.elasticity, c.friction = 0.62, 0.5
        c.collision_type = 1
        sp.add(self.ball, c)
        sp.on_collision(1, 2, post_solve=self._hit_step)
        sp.on_collision(1, 3, begin=self._hit_trap)
        self.t = 0.0
        self.events = []
        self.notes = 0
        self.last_note = -9.0
        self.trapped_t = None
        self.result, self.result_t = None, None
        self.cur_flight = 0

    def _hit_step(self, arb, space, data):
        if self.result is not None:
            return
        imp = arb.total_impulse.length
        if imp > NOTE_IMPULSE and self.t - self.last_note > NOTE_GAP:
            i = self.step_of_shape.get(arb.shapes[1])
            self.events.append(("note", self.t, (self.notes, i)))
            self.notes += 1
            self.last_note = self.t
            if self.notes == N:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))

    def _hit_trap(self, arb, space, data):
        if self.trapped_t is None and self.result is None:
            self.trapped_t = self.t
            self.events.append(("trap", self.t, None))

    def step(self, dt):
        self.t += dt
        self.space.step(dt)
        y = self.ball.position.y
        f = max(s["f"] for s in self.steps if s["y"] - 60 <= y) if y >= self.steps[0]["y"] - 60 else 0
        if f > self.cur_flight:
            self.cur_flight = f
            if f == 1:
                self.events.append(("holes", self.t, None))
            elif f == 3:
                self.events.append(("steep", self.t, None))
        if self.result is None and self.notes == N - 1 and not any(e[0] == "last" for e in self.events):
            self.events.append(("last", self.t, None))
        if self.result is None and self.trapped_t is not None and self.t >= self.trapped_t + TRAP_WAIT:
            self.result, self.result_t = "fail", self.t
            self.events.append(("fail", self.t, None))
        if self.result is None and (y > self.steps[-1]["y"] + 500 or self.t > 90):
            self.result, self.result_t = "fail", self.t   # 階段の最後まで行っても曲が終わらなかった
            self.events.append(("fail", self.t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "ball": tuple(g.ball.position), "angle": g.ball.angle, "notes": g.notes})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "notes": g.notes, "steps": g.steps, "flight": g.cur_flight}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["notes"], r["flight"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "fail":
        for seed, _, rt, notes, fl in sorted([r for r in rs if r[1] == "fail"], key=lambda r: -r[3])[:15]:
            print(f"seed={seed:4d}  {notes}/{N} 音で落とし穴  確定 {rt:5.2f}秒  階段{fl + 1}")
    else:
        for seed, _, rt, *_ in sorted(succ, key=lambda r: r[2])[:15]:
            print(f"seed={seed:4d}  弾ききった {rt:5.2f}秒")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
NOTE_HUE = {60: 0.0, 62: 0.08, 64: 0.15, 65: 0.33, 67: 0.5, 69: 0.62, 71: 0.78}
KEY_DEPTH = 46


def note_col(m, s=0.7):
    return hue_rgb(NOTE_HUE[m], s, 1.0)


def rounded(ctx, x, y, w, h, r):
    ctx.new_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def surf_y(s, x):
    xa, xb = s["x"], s["x"] + STEP_W
    u = (x - xa) / STEP_W if s["dir"] > 0 else (xb - x) / STEP_W
    return s["y"] + u * STEP_W * math.tan(TILT)


def draw_key(ctx, s, cam, flash_col, flash):
    """1段 = 1つの鍵盤。上面は進む向きに少し下がる。"""
    parts = [(s["x"], s["x"] + STEP_W)]
    if s["hole"]:
        h0, h1 = s["gap"]
        parts = [(s["x"], h0), (h1, s["x"] + STEP_W)]
        # 落とし穴(赤く光る箱)
        top = max(surf_y(s, h0), surf_y(s, h1)) + 8 - cam
        for grow, al in ((12, 0.18), (0, 0.85)):
            ctx.new_path()
            ctx.rectangle(h0 - grow, top - grow, h1 - h0 + 2 * grow, 62 + 2 * grow)
            ctx.set_source_rgba(0.9, 0.1, 0.15, al * 0.5)
            ctx.fill()
        ctx.new_path()
        ctx.move_to(h0, top)
        ctx.line_to(h0, top + 62)
        ctx.line_to(h1, top + 62)
        ctx.line_to(h1, top)
        ctx.set_source_rgb(1, 0.3, 0.3)
        ctx.set_line_width(5)
        ctx.stroke()
    base = (0.96, 0.94, 0.88)
    col = tuple(b + (c - b) * flash for b, c in zip(base, flash_col)) if flash_col else base
    for p0, p1 in parts:
        y0, y1 = surf_y(s, p0) - cam, surf_y(s, p1) - cam
        ctx.new_path()
        ctx.move_to(p0 + 2, y0)
        ctx.line_to(p1 - 2, y1)
        ctx.line_to(p1 - 2, y1 + KEY_DEPTH)
        ctx.line_to(p0 + 2, y0 + KEY_DEPTH)
        ctx.close_path()
        ctx.set_source_rgb(*col)
        ctx.fill_preserve()
        ctx.set_source_rgb(0.35, 0.33, 0.4)
        ctx.set_line_width(3)
        ctx.stroke()
    # 黒鍵っぽい飾り(段の奥側に小さく)
    if not s["hole"] and s["k"] % 7 not in (2, 6):
        xb = s["x"] + STEP_W - 18 if s["dir"] > 0 else s["x"] + 2
        yb = surf_y(s, xb + 8) - cam
        rounded(ctx, xb, yb + 2, 16, KEY_DEPTH * 0.55, 3)
        ctx.set_source_rgb(0.12, 0.12, 0.15)
        ctx.fill()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    steps = res["steps"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"melody_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"melody_{seed}.wav")
    final = os.path.join(OUT_DIR, f"melody_{seed}.mp4")
    rng = np.random.default_rng(seed + 999)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    bg = cairo.LinearGradient(0, 0, 0, H)
    bg.add_color_stop_rgb(0, 0.05, 0.03, 0.12)
    bg.add_color_stop_rgb(1, 0.10, 0.05, 0.18)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    angels = AngelShow(W, H, seed) if result == "success" else None
    floaters = [[rng.uniform(0, W), rng.uniform(0, H), rng.uniform(20, 60), str(rng.choice(["♪", "♫"])),
                 rng.uniform(0, 1)] for _ in range(26)]
    popups, banners = [], []
    key_flash = {}      # 段番号 → (時刻, 色)
    trail = []
    cam = frames[0]["ball"][1] - 900
    trap_t = next((e[1] for e in events if e[0] == "trap"), None)
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "note":
                n_i, step_i = data
                m = MELODY[n_i]
                col = GOLD if n_i == N - 1 else note_col(m)
                if step_i is not None:
                    key_flash[step_i] = (et, col)
                bx, by = fr["ball"]
                popups.append([et, bx, by, DOREMI[m], col])
            elif kind == "holes":
                banners.append([et, "落とし穴出現！", (1, 0.4, 0.4)])
            elif kind == "steep":
                banners.append([et, "階段が急になる！", (0.5, 0.95, 1.0)])
            elif kind == "last":
                banners.append([et, "ラスト1音！", GOLD])
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0
        bx, by = fr["ball"]
        cam += (by - 900 - cam) * 0.1    # カメラは玉をゆっくり追う

        ctx.set_source(bg)
        ctx.paint()
        for fl in floaters:   # ふわふわ漂う音符(奥行きを出すためゆっくり動く)
            sy = (fl[1] - cam * 0.3) % (H + 100) - 50
            text(ctx, fl[3], fl[0], sy, fl[2], rgb=hue_rgb(fl[4], 0.4, 1.0), sw=0, alpha=0.18)
        # 左右の壁
        for x in (WALL_L - 6, WALL_R + 6):
            ctx.new_path()
            ctx.move_to(x, 0)
            ctx.line_to(x, H)
            ctx.set_source_rgba(0.55, 0.62, 1.0, 0.6)
            ctx.set_line_width(6)
            ctx.stroke()
        # 鍵盤の階段
        for i, s in enumerate(steps):
            sy = s["y"] - cam
            if sy < 380 or sy > H + 80:
                continue
            fl_t, fl_c = key_flash.get(i, (None, None))
            flash = 0.0 if fl_t is None else max(0.35, 1 - (t - fl_t) / 0.3)
            draw_key(ctx, s, cam, fl_c, flash)
        # 玉と軌跡
        trail.append((bx, by))
        del trail[:-12]
        for j, (tx, ty) in enumerate(trail):
            a = (j + 1) / len(trail)
            ctx.new_path()
            ctx.arc(tx, ty - cam, BALL_R * (0.3 + 0.7 * a), 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.85, 0.5, 0.3 * a)
            ctx.fill()
        ctx.new_path()
        ctx.arc(bx, by - cam, BALL_R * 1.9, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.85, 0.5, 0.3)
        ctx.fill()
        ctx.new_path()
        ctx.arc(bx, by - cam, BALL_R, 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        for pu in popups:   # 鳴った音の名前がふわっと上がる
            age = t - pu[0]
            if 0 <= age < 0.7:
                text(ctx, pu[3], pu[1], pu[2] - cam - 40 - 90 * age, 60, rgb=pu[4], sw=10,
                     alpha=min(1, 2.5 * (0.7 - age)))
        for bn in banners:
            age = t - bn[0]
            if 0 <= age < 1.3 and not over:
                k = min(1, age / 0.15)
                text(ctx, bn[1], W / 2, 1250, 96 * (1.4 - 0.4 * k), rgb=bn[2], sw=18,
                     alpha=min(1, 3 * (1.3 - age)))
        if angels is not None and over:
            angels.draw(ctx, t - end_t)

        # 上の帯と文字
        g = cairo.LinearGradient(0, 0, 0, 560)
        g.add_color_stop_rgba(0, 0.03, 0.02, 0.08, 0.95)
        g.add_color_stop_rgba(0.8, 0.03, 0.02, 0.08, 0.85)
        g.add_color_stop_rgba(1, 0.03, 0.02, 0.08, 0.0)
        ctx.rectangle(0, 0, W, 560)
        ctx.set_source(g)
        ctx.fill()
        played = fr["notes"]
        text(ctx, "この玉、最後まで", W / 2, 195, 82, sw=14)
        text(ctx, "弾ききれる？", W / 2, 320, 120, rgb=GOLD, sw=18)
        text(ctx, "Can the ball play the whole song?", W / 2, 385, 38, rgb=(0.85, 0.85, 0.9), sw=8)
        text(ctx, f"♪ {SONG_TITLE}", 60, 470, 46, sw=10, align="left")
        pcol = (1, 0.3, 0.3) if (fail and over) else ((0.3, 1, 0.5) if over else (1, 1, 1))
        text(ctx, f"{played} / {N}", W - 170, 470, 52, rgb=pcol, sw=10)
        rounded(ctx, 60, 495, W - 120, 18, 9)
        ctx.set_source_rgba(1, 1, 1, 0.15)
        ctx.fill()
        if played:
            rounded(ctx, 60, 495, (W - 120) * played / N, 18, 9)
            ctx.set_source_rgb(*(GOLD if played == N else (0.5, 0.95, 1.0)))
            ctx.fill()
        if not over:
            text(ctx, "※失敗すると…アレが出ます", W / 2, 1840, 50, rgb=(1, 0.35, 0.35), sw=10)
        elif fail:
            k = min(1.0, after / 0.25)
            text(ctx, "落ちた…", W / 2, 1000, 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{N - played}音だったのに…", W / 2, 1130, 72, sw=12)
        else:
            k = min(1.0, (t - end_t) / 0.25)
            text(ctx, "弾ききった！", W / 2, 1000, 140 * (1.6 - 0.6 * k), rgb=GOLD, sw=20)

        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
    ff.stdin.close()
    ff.wait()
    duration = len(frames) / FPS
    synth_audio(res, duration, wav, trap_t)
    # 叫び声の大きさを残すため、音量の自動調整(loudnorm)はかけない
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(silent)
    os.remove(wav)
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['notes']}/{N}音 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
MIX_GAIN = 0.32  # 通常部分の音量(約 -18dB になるよう調整)
HOLY_GAIN = 0.85


def music_box(freq, dur, amp):
    """オルゴールのような音。"""
    t = np.arange(int(dur * SR)) / SR
    y = (np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 6)
         + 0.25 * np.sin(2 * np.pi * freq * 3.01 * t) * np.exp(-t * 9))
    return amp * y * np.exp(-t * 2.2) * np.minimum(1, t / 0.004)


def bass(freq, dur, amp):
    t = np.arange(int(dur * SR)) / SR
    y = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    return amp * y * np.exp(-t * 2.5) * np.minimum(1, t / 0.01)


def synth_audio(res, duration, path, trap_t):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    out = np.zeros(int((duration + 3) * SR))

    def add(sig, t0):
        i = int(t0 * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    for kind, t, data in events:
        if kind == "note":
            n_i = data[0]
            add(music_box(midi_hz(MELODY[n_i] + 12), 1.0, 0.5), t)
            add(bass(midi_hz(CHORD[n_i]), 1.0, 0.35), t)
            add(music_box(midi_hz(CHORD[n_i] + 16), 1.0, 0.12), t)
        elif kind in ("holes", "steep", "last"):
            for k, m in enumerate((79, 83, 86, 91)):
                add(music_box(midi_hz(m), 0.5, 0.18), t + k * 0.05)
    if trap_t is not None:   # 落とし穴にはまった「ヒューッ…」
        n = int(0.6 * SR)
        tt = np.arange(n) / SR
        f = 1200 * np.exp(-tt * 2.0)
        add(0.25 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, (0.6 - tt) / 0.15), trap_t)
    extra = np.zeros_like(out)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        extra[i0:i0 + len(sig)] += sig[: len(extra) - i0]
        sad_t = end_t + SCARE_DUR + 0.1
        for k, m in enumerate((64, 63, 62)):
            add(music_box(midi_hz(m), 0.6, 0.4) + bass(midi_hz(m - 12), 0.6, 0.3), sad_t + k * 0.42)
        add(music_box(midi_hz(61), 1.5, 0.4) + bass(midi_hz(49), 1.5, 0.3), sad_t + 1.26)
    elif end_t is not None:
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(end_t * SR)
        extra[i0:i0 + len(sig)] += HOLY_GAIN * sig[: len(extra) - i0]
    wet = out.copy()
    for d, g in ((0.043, 0.3), (0.071, 0.24), (0.113, 0.17)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    # 通常部分は軽く圧縮して聞こえやすくし、叫び声との差は約10dBに抑える
    wet = np.tanh(2.5 * wet / max(1e-9, np.max(np.abs(wet)))) / np.tanh(2.5) * MIX_GAIN
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
    ap.add_argument("-n", type=int, default=400)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
