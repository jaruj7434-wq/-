"""「30秒で玉を100個カップに入れられる?」パチンコ盤 + 増殖ゲートの物理ショートを生成する。

- 上から玉が落ち、釘に当たってランダムに散らばりながら落ちていく(ガルトンボードの原理)。
- 「×2」「×3」ゲートを通った玉は分裂して増える。
- 一番下を左右に動くカップに入った玉だけが数に入る。外れた玉は落ちて消える。
- 展開:8秒でドロッパー+1、16秒で×3ゲート出現、24秒でカップが速くなる。
30秒で GOAL 個に届けば成功、届かなければ失敗(幽霊が出る)。

使い方:
    python plinko.py search [--want fail|success]
    python plinko.py render --seed N
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
from ball_escape import hue_rgb, midi_hz, noise, text, tone  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 3
SR = 48000
GRAVITY = 1400.0
TIME_LIMIT = 30.0
OUTRO = 3.0
GOAL = 100

BALL_R = 11
PEG_R = 7
PEG_TOP, PEG_ROWS, PEG_DY, PEG_DX = 660, 9, 62, 84
DROP_Y = 590
DROP_EVERY = 0.18          # 成功率がおよそ半々になる値(300回中168回成功)
DROPPER2_AT, GATE3_AT, FAST_AT = 8.0, 16.0, 24.0
CUP_Y, CUP_W, CUP_H = 1400, 220, 70
CUP_AMP, CUP_PERIOD, CUP_PERIOD_FAST = 330.0, 4.0, 2.3
MAX_BALLS = 500

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 15
        self.space = sp
        st = sp.static_body
        # 釘(互い違い)
        self.pegs = []
        for row in range(PEG_ROWS):
            y = PEG_TOP + row * PEG_DY
            off = PEG_DX / 2 if row % 2 else 0
            x = 60 + off
            while x < W - 50:
                c = pymunk.Circle(st, PEG_R, (x, y))
                c.elasticity, c.friction = 0.55, 0.2
                sp.add(c)
                self.pegs.append((x, y))
                x += PEG_DX
        # 左右の壁
        for x in (8, W - 8):
            s = pymunk.Segment(st, (x, 520), (x, CUP_Y + 40), 6)
            s.elasticity = 0.6
            sp.add(s)
        # 動くカップ(キネマティック)
        self.cup = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.cup.position = (W / 2, CUP_Y)
        sp.add(self.cup)
        hw = CUP_W / 2
        for a, b in (((-hw, -CUP_H), (-hw, 0)), ((-hw, 0), (hw, 0)), ((hw, 0), (hw, -CUP_H))):
            s = pymunk.Segment(self.cup, a, b, 6)
            s.elasticity, s.friction = 0.3, 0.8
            sp.add(s)
        self.cup_phase = 0.0
        # 増殖ゲート [x, y, 幅, 倍率, 出現時刻]
        gy = [PEG_TOP + PEG_DY * 2.5, PEG_TOP + PEG_DY * 5.5]
        self.gates = [
            {"x": self.rng.uniform(220, W - 220), "y": gy[0], "w": 170, "mul": 2, "at": 0.0},
            {"x": self.rng.uniform(220, W - 220), "y": gy[1], "w": 170, "mul": 2, "at": 0.0},
            {"x": self.rng.uniform(260, W - 260), "y": PEG_TOP + PEG_DY * 7.5, "w": 150, "mul": 3, "at": GATE3_AT},
        ]
        self.balls = []    # {"body", "id", "used": set(), "hue"}
        self.next_id = 0
        self.count = 0
        self.events = []
        self.droppers = [W / 2 + self.rng.uniform(-60, 60)]
        self.next_drop = 0.3
        self.t = 0.0
        self.result, self.result_t = None, None
        self.dropper2 = self.gate3 = self.fast = False

    def add_ball(self, x, y, vx=0.0, vy=0.0, used=None, hue=None):
        if len(self.balls) >= MAX_BALLS:
            return
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, BALL_R))
        b.position = (x, y)
        b.velocity = (vx, vy)
        c = pymunk.Circle(b, BALL_R)
        c.elasticity, c.friction = 0.45, 0.2
        self.space.add(b, c)
        self.balls.append({"body": b, "shape": c, "id": self.next_id, "used": set(used or ()),
                           "hue": self.rng.uniform() if hue is None else hue})
        self.next_id += 1

    def remove(self, ball):
        self.space.remove(ball["body"], ball["shape"])

    def step(self, dt):
        self.t += dt
        t = self.t
        # 展開イベント
        if not self.dropper2 and t >= DROPPER2_AT:
            self.dropper2 = True
            # 2つ目は1つ目から離れた位置に置き、増えたことがひと目で分かるようにする
            self.droppers.append(self.droppers[0] + self.rng.choice([-1, 1]) * self.rng.uniform(250, 330))
            self.events.append(("dropper", t, None))
        if not self.gate3 and t >= GATE3_AT:
            self.gate3 = True
            self.events.append(("gate3", t, None))
        if not self.fast and t >= FAST_AT:
            self.fast = True
            self.events.append(("fast", t, None))
        # 玉を落とす
        if self.result is None and t >= self.next_drop:
            for x in self.droppers:
                self.add_ball(x + self.rng.uniform(-6, 6), DROP_Y, self.rng.uniform(-40, 40), 0)
            self.next_drop += DROP_EVERY
        # カップを動かす(速度を与えて物理的に押す)
        period = CUP_PERIOD_FAST if self.fast else CUP_PERIOD
        self.cup_phase += 2 * math.pi / period * dt
        target_v = CUP_AMP * 2 * math.pi / period * math.cos(self.cup_phase)
        self.cup.velocity = (target_v, 0)
        self.space.step(dt)
        # ゲート・カップ・画面外の判定
        keep = []
        for ball in self.balls:
            x, y = ball["body"].position
            gone = False
            for gi, g in enumerate(self.gates):
                if t < g["at"] or gi in ball["used"]:
                    continue
                if abs(x - g["x"]) < g["w"] / 2 and abs(y - g["y"]) < 14:
                    ball["used"].add(gi)
                    vx, vy = ball["body"].velocity
                    for k in range(g["mul"] - 1):
                        a = math.radians(self.rng.uniform(-25, 25))
                        self.add_ball(x + self.rng.uniform(-8, 8), y,
                                      vx * math.cos(a) - vy * math.sin(a), vx * math.sin(a) + vy * math.cos(a),
                                      used=ball["used"], hue=ball["hue"])
                    self.events.append(("multiply", t, (gi, g["mul"])))
            cx = self.cup.position.x
            if self.result is None and abs(x - cx) < CUP_W / 2 - 4 and CUP_Y - CUP_H + 10 < y < CUP_Y:
                self.count += 1
                self.events.append(("goal", t, (x, y, ball["hue"])))
                gone = True
            elif y > H + 40:
                gone = True
            if gone:
                self.remove(ball)
            else:
                keep.append(ball)
        self.balls = keep
        if self.result is None:
            if self.count >= GOAL:
                self.result, self.result_t = "success", t
                self.events.append(("success", t, None))
            elif t >= TIME_LIMIT:
                self.result, self.result_t = "fail", TIME_LIMIT
                self.events.append(("fail", t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({
                "t": g.t, "count": g.count, "cup_x": g.cup.position.x,
                "balls": [(b["body"].position.x, b["body"].position.y, b["hue"]) for b in g.balls],
                "droppers": list(g.droppers), "fast": g.fast,
            })
        if g.result is not None:
            extra = OUTRO + (SCARE_DUR if g.result == "fail" else 0)
            if not record or g.t > g.result_t + extra:
                break
    # 10秒時点の数(序盤の苦戦の度合い)
    c10 = sum(1 for e in g.events if e[0] == "goal" and e[1] <= 10)
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "count": g.count, "c10": c10, "gates": g.gates, "pegs": g.pegs}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["count"], r["c10"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "fail":
        for seed, _, _, c, c10 in sorted([r for r in rs if r[1] == "fail"], key=lambda r: -r[3])[:15]:
            print(f"seed={seed:4d}  {c}/{GOAL}個で時間切れ  10秒時点 {c10}個")
    else:
        for seed, _, rt, c, c10 in sorted(succ, key=lambda r: -r[2])[:15]:
            print(f"seed={seed:4d}  成功 {rt:5.2f}秒  10秒時点 {c10}個")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def rounded(ctx, x, y, w, h, r):
    ctx.new_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def background(pegs):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.RadialGradient(W / 2, 1000, 50, W / 2, 1000, 1300)
    g.add_color_stop_rgb(0, 0.09, 0.07, 0.20)
    g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
    ctx.set_source(g)
    ctx.paint()
    for x in (8, W - 8):   # 壁
        for wdt, al in ((18, 0.10), (6, 0.8)):
            ctx.new_path()
            ctx.move_to(x, 520)
            ctx.line_to(x, CUP_Y + 40)
            ctx.set_source_rgba(0.55, 0.62, 1.0, al)
            ctx.set_line_width(wdt)
            ctx.stroke()
    for x, y in pegs:      # 釘
        for rr, al in ((PEG_R * 2.2, 0.15), (PEG_R, 1.0)):
            ctx.new_path()
            ctx.arc(x, y, rr, 0, 2 * math.pi)
            ctx.set_source_rgba(0.75, 0.8, 1.0, al)
            ctx.fill()
    return surf


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    gates = res["gates"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"plinko_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"plinko_{seed}.wav")
    final = os.path.join(OUT_DIR, f"plinko_{seed}.mp4")
    rng = np.random.default_rng(seed + 999)
    bg = background(res["pegs"])
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    particles, banners = [], []
    gate_flash = [-9.0] * len(gates)
    cup_flash = -9.0
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        dt = 1 / FPS
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "multiply":
                gate_flash[data[0]] = et
            elif kind == "goal":
                cup_flash = et
                x, y, hue = data
                for _ in range(6):
                    a = rng.uniform(-math.pi, 0)
                    sp = rng.uniform(150, 450)
                    particles.append([x, y, math.cos(a) * sp, math.sin(a) * sp, 0, rng.uniform(0.3, 0.6), GOLD])
            elif kind == "dropper":
                banners.append([et, "ドロッパー+1！", (0.5, 0.95, 1.0)])
            elif kind == "gate3":
                banners.append([et, "×3ゲート出現！", GOLD])
                gate_flash[2] = et
            elif kind == "fast":
                banners.append([et, "カップが速くなる…！", (1, 0.35, 0.35)])
            elif kind == "success":
                for _ in range(240):
                    a = rng.uniform(0, 2 * math.pi)
                    sp = rng.uniform(300, 1300)
                    particles.append([W / 2, 1000, math.cos(a) * sp, math.sin(a) * sp - 500,
                                      0, rng.uniform(1.5, 2.8), hue_rgb(rng.uniform())])
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0

        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        # ゲート
        for gi, g in enumerate(gates):
            if t < g["at"]:
                continue
            fl = max(0.0, 1 - (t - gate_flash[gi]) / 0.15)
            col = GOLD if g["mul"] == 3 else (0.4, 1, 0.6)
            c2 = tuple(v + (1 - v) * fl * 0.7 for v in col)
            x0, y0 = g["x"] - g["w"] / 2, g["y"] - 18
            for grow, al in ((10, 0.15), (0, 0.35)):
                rounded(ctx, x0 - grow, y0 - grow, g["w"] + 2 * grow, 36 + 2 * grow, 12 + grow)
                ctx.set_source_rgba(*c2, al)
                ctx.fill()
            rounded(ctx, x0, y0, g["w"], 36, 12)
            ctx.set_source_rgba(*c2, 1)
            ctx.set_line_width(4)
            ctx.stroke()
            text(ctx, f"×{g['mul']}", g["x"], g["y"] + 15, 42, rgb=(1, 1, 1), sw=7)
        # ドロッパー
        for dx in fr["droppers"]:
            ctx.new_path()
            ctx.move_to(dx - 34, DROP_Y - 50)
            ctx.line_to(dx + 34, DROP_Y - 50)
            ctx.line_to(dx + 12, DROP_Y - 14)
            ctx.line_to(dx - 12, DROP_Y - 14)
            ctx.close_path()
            ctx.set_source_rgb(0.5, 0.95, 1.0)
            ctx.fill()
        # 玉
        for bx, by, hue in fr["balls"]:
            col = hue_rgb(hue, 0.6, 1.0)
            ctx.new_path()
            ctx.arc(bx, by, BALL_R * 1.6, 0, 2 * math.pi)
            ctx.set_source_rgba(*col, 0.2)
            ctx.fill()
            ctx.new_path()
            ctx.arc(bx, by, BALL_R, 0, 2 * math.pi)
            ctx.set_source_rgb(*col)
            ctx.fill()
            ctx.new_path()
            ctx.arc(bx - 3, by - 3, BALL_R * 0.35, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, 0.8)
            ctx.fill()
        # カップ
        cx = fr["cup_x"]
        fl = max(0.0, 1 - (t - cup_flash) / 0.12)
        ccol = (1, 0.4, 0.35) if fr["fast"] else GOLD
        ccol = tuple(v + (1 - v) * fl * 0.6 for v in ccol)
        hw = CUP_W / 2
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        for wdt, al in ((30, 0.12), (18, 0.25), (10, 1.0)):
            ctx.new_path()
            ctx.move_to(cx - hw, CUP_Y - CUP_H)
            ctx.line_to(cx - hw, CUP_Y)
            ctx.line_to(cx + hw, CUP_Y)
            ctx.line_to(cx + hw, CUP_Y - CUP_H)
            ctx.set_source_rgba(*ccol, al)
            ctx.set_line_width(wdt)
            ctx.stroke()
        text(ctx, "GOAL", cx, CUP_Y - 18, 36, rgb=ccol, sw=6)
        # 粒子
        alive = []
        for p in particles:
            p[4] += dt
            if p[4] >= p[5]:
                continue
            p[3] += GRAVITY * 0.5 * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            ctx.new_path()
            ctx.rectangle(p[0] - 5, p[1] - 5, 10, 10)
            ctx.set_source_rgba(*p[6], 1 - p[4] / p[5])
            ctx.fill()
            alive.append(p)
        particles = alive
        for bn in banners:
            age = t - bn[0]
            if 0 <= age < 1.4 and not over:
                k = min(1, age / 0.15)
                text(ctx, bn[1], W / 2, 1230, 100 * (1.4 - 0.4 * k), rgb=bn[2], sw=18,
                     alpha=min(1, 3 * (1.4 - age)))

        # 文字
        shown_t = min(t, TIME_LIMIT)
        remain = TIME_LIMIT - shown_t
        count = fr["count"]
        text(ctx, f"30秒で{GOAL}個", W / 2, 200, 84, sw=14)
        text(ctx, "カップに入れられる？", W / 2, 320, 96, rgb=GOLD, sw=18)
        text(ctx, f"Can {GOAL} balls land in the cup in 30s?", W / 2, 385, 38, rgb=(0.85, 0.85, 0.9), sw=8)
        danger = remain <= 5 and not over
        ccount = (1, 0.3, 0.3) if (fail and over) else ((0.3, 1, 0.5) if over else (1, 1, 1))
        text(ctx, f"{count} / {GOAL}", W / 2, 505, 96, rgb=ccount, sw=14)
        pulse = 1 + (0.12 * max(0, 1 - (shown_t % 1) / 0.25) if danger else 0)
        text(ctx, f"{remain:05.2f}", W - 150, 500, 50 * pulse, rgb=(1, 0.3, 0.3) if danger else (1, 1, 1), sw=10)
        text(ctx, f"玉×{len(fr['balls'])}", 150, 500, 46, sw=10)
        if not over:
            text(ctx, "※失敗すると…アレが出ます", W / 2, 1580, 50, rgb=(1, 0.35, 0.35), sw=10)
        elif fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 1050, 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{GOAL - count}個だった…", W / 2, 1180, 72, sw=12)
        else:
            k = min(1.0, (t - end_t) / 0.25)
            text(ctx, f"{GOAL}個達成！", W / 2, 1050, 140 * (1.6 - 0.6 * k), rgb=GOLD, sw=20)
            text(ctx, f"残り{TIME_LIMIT - end_t:.2f}秒", W / 2, 1180, 80, sw=12)

        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
    ff.stdin.close()
    ff.wait()
    duration = len(frames) / FPS
    synth_audio(events, end_t, fail, duration, wav)
    # 叫び声の大きさを残すため、音量の自動調整(loudnorm)はかけない
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(silent)
    os.remove(wav)
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['count']}/{GOAL} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
# ベートーヴェン「歓喜の歌」(交響曲第9番、1824年・パブリックドメイン)の旋律
MELODY = [76, 76, 77, 79, 79, 77, 76, 74, 72, 72, 74, 76, 76, 74, 74,
          76, 76, 77, 79, 79, 77, 76, 74, 72, 72, 74, 76, 74, 72, 72]
MIX_GAIN = 0.7   # 通常部分の音量(約 -18dB になるよう調整)


def synth_audio(events, end_t, fail, duration, path):
    rng = np.random.default_rng(0)
    out = np.zeros(int((duration + 3) * SR))

    def add(sig, t0):
        i = int(t0 * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    note_i = 0
    last_note = last_pop = -1.0
    for kind, t, data in events:
        if kind == "goal":
            if t - last_note >= 0.09:   # カップに入るたびに「歓喜の歌」が進む(詰まりすぎる分はコイン音)
                add(tone(midi_hz(MELODY[note_i % len(MELODY)]), 0.4, 0.35, 6), t)
                note_i += 1
                last_note = t
            else:
                add(tone(2600, 0.05, 0.05, 50), t)
        elif kind == "multiply":
            if t - last_pop >= 0.05:
                add(tone(midi_hz(84 + 7 * (data[1] - 2)), 0.12, 0.12, 25), t)
                last_pop = t
        elif kind in ("dropper", "gate3"):
            for k, m in enumerate((72, 76, 79, 84)):
                add(tone(midi_hz(m), 0.3, 0.25, 6), t + k * 0.06)
        elif kind == "fast":
            for k in range(3):   # 警告音
                add(tone(880, 0.18, 0.25, 4), t + k * 0.3)
                add(tone(660, 0.18, 0.25, 4), t + k * 0.3 + 0.15)
    for s_ in range(25, 30):
        if end_t is None or s_ < end_t:
            add(noise(0.06, 0.5, 60, rng) + tone(1800, 0.06, 0.2, 40), s_)
    scare = np.zeros_like(out)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        scare[i0:i0 + len(sig)] += sig[: len(scare) - i0]
        sad_t = end_t + SCARE_DUR + 0.1
        for k, m in enumerate((64, 63, 62)):
            add(tone(midi_hz(m), 0.45, 0.35, 3) + tone(midi_hz(m - 12), 0.45, 0.25, 3), sad_t + k * 0.42)
        add(tone(midi_hz(61), 1.4, 0.35, 1.5) + tone(midi_hz(49), 1.4, 0.25, 1.5), sad_t + 1.26)
    elif end_t is not None:
        for iv in (0, 4, 7, 12, 16):
            add(tone(midi_hz(60 + iv), 2.5, 0.25, 1.2), end_t)
        add(noise(1.5, 0.25, 2.5, rng, smooth=2), end_t)
    wet = out.copy()
    for d, g in ((0.043, 0.3), (0.071, 0.24), (0.113, 0.17)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    # 通常部分は軽く圧縮して聞こえやすくし、叫び声との差は約10dBに抑える
    wet = np.tanh(2.5 * wet / max(1e-9, np.max(np.abs(wet)))) / np.tanh(2.5) * MIX_GAIN
    wet = np.clip(wet + 0.95 * scare[: len(wet)], -0.98, 0.98)
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
