"""「60秒でブロックを全部こわせる?」パドルで打ち返すブロック崩しの物理ショートを生成する。

- 1つの玉をパドル(自動操作)で打ち返す。パドルの当たった位置で跳ね返る角度が変わる(反射角)。
- ブロックには「あと何回で壊れるか」の数字。上の段ほど硬い。
- 壊したブロックからまれにアイテムが落ちる:「×2」(玉がすべて2つに分裂)/「LONG」(パドルが長くなる)。
- パドルに戻らずにブロックを連続で壊すと COMBO が増える。すき間からブロックの裏に入り込むと
  天井とブロックの間で跳ね続けて連続で壊れていく。
制限時間内に全部壊せば成功、壊せなければ失敗(幽霊が出る)。

使い方:
    python breakout.py search [--want success|fail]
    python breakout.py render --seed N
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ball_escape"))
from ball_escape import hue_rgb, midi_hz, noise, text, tone  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from angels import DURATION as ANGEL_DUR, AngelShow, holy_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 6
SR = 48000
TIME_LIMIT = 60.0        # 成功率がおよそ半々になる値(600回中約52%)
OUTRO = 3.2

AX0, AX1, AY0, AY1 = 60, 1020, 560, 1420    # 枠(下は開いていて、落ちたらミス)
COLS, ROWS = 8, 6
GAP = 6
BX0, BY0 = AX0 + 12, AY0 + 180   # ブロックの上にすき間(裏に入った玉が跳ね回る場所)
CW = (AX1 - AX0 - 24 - GAP * (COLS - 1)) / COLS
CH = 34
BALL_R = 11
SPEED0, SPEED_MAX = 1400.0, 1700.0
PADDLE_Y, PADDLE_H = 1340, 20
PADDLE_W0, PADDLE_W_LONG = 150, 250
PADDLE_SPEED = 1150.0
MAX_ANGLE = math.radians(62)      # パドルの端に当たったときの最大の跳ね返り角(真上から)
ITEM_P = 0.12
ITEM_SPEED = 330.0
ITEM_W, ITEM_H = 92, 38
MAX_BALLS = 24
RESPAWN = 0.9
TUNNEL_MIN = 12          # 残りがこれ以上あるときだけ、すき間から裏へ送り込む

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        self.bricks = []
        for row in range(ROWS):
            for col in range(COLS):
                # 下の段ほど硬い(最初はなかなか突破できない)。上の段はもろく、裏に入ると一気に壊れる
                hp = 3 if row >= ROWS - 1 else (2 if row >= ROWS - 3 else 1)
                if self.rng.random() < 0.15:
                    hp = max(1, hp + int(self.rng.choice([-1, 1])))
                self.bricks.append({"x": BX0 + col * (CW + GAP), "y": BY0 + row * (CH + GAP),
                                    "hp": hp, "hp0": hp, "row": row})
        self.balls = []
        self.items = []
        self.events = []
        self.paddle_x = W / 2
        self.paddle_w = PADDLE_W0
        self.speed = SPEED0
        self.combo = 0
        self.max_combo = 0
        self.broken = 0
        self.respawn_at = 0.5
        self.t = 0.0
        self.result, self.result_t = None, None
        self.aim_noise = 0.0
        self.aim_for = None

    def launch(self):
        a = math.radians(self.rng.uniform(-35, 35))
        self.balls.append([self.paddle_x, PADDLE_Y - PADDLE_H / 2 - BALL_R - 1,
                           self.speed * math.sin(a), -self.speed * math.cos(a)])
        self.events.append(("launch", self.t, None))

    def hit_brick(self, b, br, idx):
        x, y, vx, vy = b
        nx_ = min(max(x, br["x"]), br["x"] + CW)
        ny_ = min(max(y, br["y"]), br["y"] + CH)
        dx, dy = x - nx_, y - ny_
        d2 = dx * dx + dy * dy
        if d2 > BALL_R * BALL_R:
            return False
        if d2 > 1e-9:
            d = math.sqrt(d2)
            nx, ny, pen = dx / d, dy / d, BALL_R - d
        else:
            cands = [(x - br["x"], -1, 0), (br["x"] + CW - x, 1, 0),
                     (y - br["y"], 0, -1), (br["y"] + CH - y, 0, 1)]
            pen, nx, ny = min(cands)
            pen += BALL_R
        dot = vx * nx + vy * ny
        if dot < 0:
            b[2], b[3] = vx - 2 * dot * nx, vy - 2 * dot * ny
        b[0] += nx * pen
        b[1] += ny * pen
        br["hp"] -= 1
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        cx, cy = br["x"] + CW / 2, br["y"] + CH / 2
        if br["hp"] <= 0:
            self.broken += 1
            self.events.append(("break", self.t, (idx, cx, cy, self.combo)))
            if self.broken % 10 == 0:   # 10個壊すごとに少し速くなる
                self.speed = min(SPEED_MAX, self.speed * 1.03)
            if self.rng.random() < ITEM_P:
                kind = "multi" if self.rng.random() < 0.55 else "long"
                self.items.append([cx, cy, kind])
                self.events.append(("drop", self.t, (kind, cx, cy)))
        else:
            self.events.append(("hit", self.t, (idx, cx, cy, self.combo)))
        return True

    def predict_x(self, b):
        """壁の反射だけを考えて、玉がパドルの高さに来る x を予測する。"""
        x, y, vx, vy = b
        if vy <= 0:
            return None, None
        T = (PADDLE_Y - y) / vy
        lo, hi = AX0 + BALL_R, AX1 - BALL_R
        span = hi - lo
        px = x + vx * T - lo
        px = px % (2 * span)
        px = lo + (px if px <= span else 2 * span - px)
        return px, T

    def move_paddle(self, dt):
        target = None
        soonest = None
        for b in self.balls:
            px, T = self.predict_x(b)
            if px is not None and (soonest is None or T < soonest):
                soonest, target = T, px
        if target is not None:
            # 残りが一番少ない列の、一番下のブロックをねらって打ち返す(すき間を空けて裏に入れる作戦)。
            # 当てる位置で跳ね返る角度が決まるので、必要な角度からパドルの位置を逆算する。少しぶれる。
            cols = {}
            for br in self.bricks:
                if br["hp"] > 0:
                    c = int(round((br["x"] - BX0) / (CW + GAP)))
                    cols.setdefault(c, []).append(br)
            if cols:
                empty = [k for k in range(COLS) if k not in cols]
                n_alive = sum(len(v) for v in cols.values())
                if empty and n_alive >= TUNNEL_MIN:
                    # すき間(空の列)があれば、そこを通してブロックの裏へ玉を送り込む
                    k = min(empty, key=lambda k_: abs(BX0 + k_ * (CW + GAP) + CW / 2 - target))
                    gx = BX0 + k * (CW + GAP) + CW / 2
                    ang = math.atan2(gx - target, PADDLE_Y - BY0)
                    sd = 0.07
                else:
                    c = min(cols, key=lambda k: (len(cols[k]), abs(BX0 + k * (CW + GAP) - target)))
                    br = max(cols[c], key=lambda b_: b_["y"])
                    ang = math.atan2(br["x"] + CW / 2 - target, PADDLE_Y - (br["y"] + CH))
                    sd = 0.18
                if soonest != self.aim_for:
                    self.aim_noise = self.rng.normal(0, sd)
                self.aim_for = soonest
                off = max(-0.95, min(0.95, ang / MAX_ANGLE + self.aim_noise))
                target -= off * self.paddle_w / 2
        if self.items and (soonest is None or soonest > 0.7):   # 余裕があればアイテムを取りに行く
            it = max(self.items, key=lambda i: i[1])
            target = it[0]
        if target is None:
            target = W / 2
        d = target - self.paddle_x
        step = max(-PADDLE_SPEED * dt, min(PADDLE_SPEED * dt, d))
        lo, hi = AX0 + self.paddle_w / 2, AX1 - self.paddle_w / 2
        self.paddle_x = min(max(self.paddle_x + step, lo), hi)

    def step(self, dt):
        self.t += dt
        t = self.t
        if self.result is None and not self.balls and t >= self.respawn_at:
            self.launch()
        self.move_paddle(dt)
        keep = []
        for b in self.balls:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            if b[0] < AX0 + BALL_R:
                b[0], b[2] = AX0 + BALL_R, abs(b[2])
            if b[0] > AX1 - BALL_R:
                b[0], b[2] = AX1 - BALL_R, -abs(b[2])
            if b[1] < AY0 + BALL_R:
                b[1], b[3] = AY0 + BALL_R, abs(b[3])
                self.events.append(("ceiling", t, None))
            # パドル:当たった位置で跳ね返る角度が決まる
            on_paddle = (PADDLE_Y - PADDLE_H / 2 - BALL_R <= b[1] <= PADDLE_Y + PADDLE_H / 2
                         and abs(b[0] - self.paddle_x) <= self.paddle_w / 2 + BALL_R)
            if b[3] > 0 and on_paddle:
                off = max(-1, min(1, (b[0] - self.paddle_x) / (self.paddle_w / 2)))
                a = off * MAX_ANGLE
                b[2], b[3] = self.speed * math.sin(a), -self.speed * math.cos(a)
                b[1] = PADDLE_Y - PADDLE_H / 2 - BALL_R
                self.combo = 0
                self.events.append(("paddle", t, None))
            if self.result is None:
                col = int((b[0] - BX0) // (CW + GAP))
                row = int((b[1] - BY0) // (CH + GAP))
                done = False
                for rr in (row - 1, row, row + 1):
                    for cc in (col - 1, col, col + 1):
                        if done or not (0 <= rr < ROWS and 0 <= cc < COLS):
                            continue
                        idx = rr * COLS + cc
                        br = self.bricks[idx]
                        if br["hp"] > 0 and self.hit_brick(b, br, idx):
                            done = True
            # 速さを一定に保ち、ほぼ水平の往復にはまらないようにする
            sp = math.hypot(b[2], b[3])
            b[2], b[3] = b[2] * self.speed / sp, b[3] * self.speed / sp
            if abs(b[3]) < self.speed * 0.25:
                b[3] = math.copysign(self.speed * 0.25, b[3] or -1)
                b[2] = math.copysign(math.sqrt(self.speed ** 2 - b[3] ** 2), b[2] or 1)
            if b[1] > H + 30:
                self.events.append(("lost", t, (b[0],)))
            else:
                keep.append(b)
        self.balls = keep
        if self.result is None and not self.balls and self.respawn_at < t:
            self.respawn_at = t + RESPAWN
            self.combo = 0
            self.events.append(("miss", t, None))
        # アイテム
        items = []
        for it in self.items:
            it[1] += ITEM_SPEED * dt
            if abs(it[1] - PADDLE_Y) < (ITEM_H + PADDLE_H) / 2 and abs(it[0] - self.paddle_x) < (ITEM_W + self.paddle_w) / 2:
                if self.result is None:
                    if it[2] == "multi":
                        new = []
                        for b in self.balls:
                            if len(self.balls) + len(new) >= MAX_BALLS:
                                break
                            a = math.atan2(b[2], -b[3]) + math.radians(self.rng.choice([-1, 1]) * self.rng.uniform(20, 35))
                            new.append([b[0], b[1], self.speed * math.sin(a), -self.speed * math.cos(a) * (1 if b[3] < 0 else -1)])
                        self.balls.extend(new)
                    else:
                        self.paddle_w = PADDLE_W_LONG
                    self.events.append(("pickup", t, (it[2], it[0])))
            elif it[1] < H + 40:
                items.append(it)
        self.items = items
        if self.result is None:
            if all(br["hp"] <= 0 for br in self.bricks):
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
                "t": g.t, "paddle_x": g.paddle_x, "paddle_w": g.paddle_w, "combo": g.combo,
                "balls": [(b[0], b[1]) for b in g.balls], "items": [tuple(i) for i in g.items],
                "hps": [br["hp"] for br in g.bricks],
            })
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR   # 成功時は天使のお祝い
            if not record or g.t > g.result_t + extra:
                break
    # 最後の連続破壊:決着前 6 秒以内の最大コンボ
    breaks = [e for e in g.events if e[0] == "break"]
    late = [breaks[-1][2][3]] if (g.result == "success" and breaks) else [0]   # 最後の1個を壊したときのコンボ
    picks = [e[2][0] for e in g.events if e[0] == "pickup"]
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "left": sum(1 for br in g.bricks if br["hp"] > 0), "max_combo": g.max_combo,
            "late_combo": max(late) if late else 0, "picks": picks, "bricks": g.bricks}


def score(seed):
    r = simulate(seed)
    return (seed, r["result"], r["result_t"], r["left"], r["max_combo"], r["late_combo"],
            "".join("2" if p == "multi" else "L" for p in r["picks"]))


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "success":
        good = sorted([r for r in succ if "2" in r[6] and "L" in r[6]], key=lambda r: (-r[5], -r[2]))
        for seed, _, rt, _, mc, lc, pk in good[:15]:
            print(f"seed={seed:4d}  成功 {rt:5.2f}秒  最後のコンボ {lc}  最大コンボ {mc}  アイテム {pk}")
    else:
        for seed, _, _, left, mc, lc, pk in sorted([r for r in rs if r[1] == "fail"], key=lambda r: r[3])[:15]:
            print(f"seed={seed:4d}  残り {left} 個で時間切れ  最大コンボ {mc}  アイテム {pk}")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
HP_COLOR = {1: (0.35, 0.85, 1.0), 2: (1.0, 0.65, 0.25), 3: (1.0, 0.3, 0.4)}
ITEM_STYLE = {"multi": ("×2", (0.35, 1, 0.55)), "long": ("LONG", (0.45, 0.65, 1.0))}


def rounded(ctx, x, y, w, h, r):
    ctx.new_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def background():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.RadialGradient(W / 2, 1000, 50, W / 2, 1000, 1300)
    g.add_color_stop_rgb(0, 0.09, 0.07, 0.20)
    g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
    ctx.set_source(g)
    ctx.paint()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for wdt, al in ((24, 0.08), (12, 0.18), (5, 0.9)):   # 枠(下は開いている)
        ctx.new_path()
        ctx.move_to(AX0 - 4, AY1)
        ctx.line_to(AX0 - 4, AY0 - 4)
        ctx.line_to(AX1 + 4, AY0 - 4)
        ctx.line_to(AX1 + 4, AY1)
        ctx.set_source_rgba(0.55, 0.62, 1.0, al)
        ctx.set_line_width(wdt)
        ctx.stroke()
    return surf


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    bricks = res["bricks"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"breakout_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"breakout_{seed}.wav")
    final = os.path.join(OUT_DIR, f"breakout_{seed}.mp4")
    rng = np.random.default_rng(seed + 999)
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
    particles, popups = [], []
    last_hit = {}
    trails = {}
    combo_peak_t = -9.0
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        dt = 1 / FPS
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind in ("hit", "break"):
                idx, cx, cy, combo = data
                last_hit[idx] = et
                if combo >= 3:
                    combo_peak_t = et
                if kind == "break":
                    col = HP_COLOR[min(3, bricks[idx]["hp0"])]
                    for _ in range(22):
                        a = rng.uniform(0, 2 * math.pi)
                        sp = rng.uniform(120, 520)
                        particles.append([cx, cy, math.cos(a) * sp, math.sin(a) * sp, 0, rng.uniform(0.35, 0.8), col])
            elif kind == "pickup":
                k, x = data
                popups.append([et, x, PADDLE_Y - 70, "玉×2！" if k == "multi" else "パドルLONG！", ITEM_STYLE[k][1]])
            elif kind == "miss":
                popups.append([et, W / 2, PADDLE_Y - 70, "ミス…", (0.85, 0.85, 0.9)])
            elif kind == "success":
                for _ in range(260):
                    a = rng.uniform(0, 2 * math.pi)
                    sp = rng.uniform(300, 1300)
                    particles.append([W / 2, 900, math.cos(a) * sp, math.sin(a) * sp - 500,
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
        # ブロック(数字は「あと何回で壊れるか」)
        for i, hp in enumerate(fr["hps"]):
            if hp <= 0:
                continue
            br = bricks[i]
            col = HP_COLOR[min(3, hp)]
            fl = max(0.0, 1 - (t - last_hit.get(i, -9)) / 0.12)
            c2 = tuple(v + (1 - v) * fl * 0.8 for v in col)
            rounded(ctx, br["x"], br["y"], CW, CH, 8)
            ctx.set_source_rgba(*c2, 0.25)
            ctx.fill_preserve()
            ctx.set_source_rgba(*c2, 1)
            ctx.set_line_width(4)
            ctx.stroke()
            text(ctx, str(hp), br["x"] + CW / 2, br["y"] + CH / 2 + 11, 30, sw=5)
        # アイテム
        for ix, iy, kind in fr["items"]:
            label, col = ITEM_STYLE[kind]
            for grow, al in ((10, 0.18), (0, 1.0)):
                rounded(ctx, ix - ITEM_W / 2 - grow, iy - ITEM_H / 2 - grow, ITEM_W + 2 * grow, ITEM_H + 2 * grow, ITEM_H / 2 + grow)
                ctx.set_source_rgba(*col, al)
                ctx.fill()
            text(ctx, label, ix, iy + 11, 30, sw=5)
        # パドル
        pw = fr["paddle_w"]
        px = fr["paddle_x"]
        for grow, al in ((14, 0.12), (6, 0.25), (0, 1.0)):
            rounded(ctx, px - pw / 2 - grow, PADDLE_Y - PADDLE_H / 2 - grow, pw + 2 * grow, PADDLE_H + 2 * grow, PADDLE_H / 2 + grow)
            ctx.set_source_rgba(0.85, 0.95, 1.0, al)
            ctx.fill()
        # 玉
        for k, (bx, by) in enumerate(fr["balls"]):
            tr = trails.setdefault(k, [])
            if tr and math.hypot(tr[-1][0] - bx, tr[-1][1] - by) > 120:
                tr.clear()
            tr.append((bx, by))
            del tr[:-10]
            for j, (tx, ty) in enumerate(tr):
                a = (j + 1) / len(tr)
                ctx.new_path()
                ctx.arc(tx, ty, BALL_R * (0.4 + 0.6 * a), 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.5, 0.8, 0.3 * a)
                ctx.fill()
            ctx.new_path()
            ctx.arc(bx, by, BALL_R * 2, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.5, 0.8, 0.25)
            ctx.fill()
            ctx.new_path()
            ctx.arc(bx, by, BALL_R, 0, 2 * math.pi)
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill()
        for k in list(trails):
            if k >= len(fr["balls"]):
                del trails[k]
        # 粒子
        alive = []
        for p in particles:
            p[4] += dt
            if p[4] >= p[5]:
                continue
            p[3] += 900 * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            ctx.new_path()
            ctx.rectangle(p[0] - 5, p[1] - 5, 10, 10)
            ctx.set_source_rgba(*p[6], 1 - p[4] / p[5])
            ctx.fill()
            alive.append(p)
        particles = alive
        for pu in popups:
            age = t - pu[0]
            if 0 <= age < 1.1 and not over:
                text(ctx, pu[3], min(max(pu[1], 200), W - 200), pu[2] - 70 * age, 58,
                     rgb=pu[4], sw=12, alpha=min(1, 2 * (1.1 - age)))
        # コンボ(3以上で表示。大きくなるほど派手に)
        combo = fr["combo"]
        if combo >= 3 and not over:
            k = min(1.0, (t - combo_peak_t) / 0.12)
            size = min(150, 70 + combo * 2.2) * (1.25 - 0.25 * k)
            col = hue_rgb((combo * 0.04) % 1, 0.7, 1.0)
            text(ctx, f"COMBO ×{combo}", W / 2, 1150, size, rgb=col, sw=16)

        if angels is not None and over:   # 成功:かわいい天使がずっと現れる
            angels.draw(ctx, t - end_t)
        # 文字
        shown_t = min(t, end_t if end_t is not None else TIME_LIMIT)   # 決着したら時計を止める
        remain = TIME_LIMIT - shown_t
        left = sum(1 for hp in fr["hps"] if hp > 0)
        text(ctx, f"{int(TIME_LIMIT)}秒で", W / 2, 200, 84, sw=14)
        text(ctx, "全部こわせる？", W / 2, 320, 112, rgb=GOLD, sw=18)
        text(ctx, f"Can it break every block in {int(TIME_LIMIT)}s?", W / 2, 385, 38, rgb=(0.85, 0.85, 0.9), sw=8)
        danger = remain <= 5 and not over
        text(ctx, f"残り {left} 個", W / 2, 500, 80, rgb=(0.3, 1, 0.5) if (over and not fail) else (1, 1, 1), sw=12)
        text(ctx, f"{remain:05.2f}", W - 150, 495, 48, rgb=(1, 0.3, 0.3) if danger else (1, 1, 1), sw=10)
        text(ctx, f"玉×{len(fr['balls'])}", 150, 495, 46, sw=10)
        if not over:
            text(ctx, "※失敗すると…アレが出ます", W / 2, 1580, 50, rgb=(1, 0.35, 0.35), sw=10)
        elif fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 960, 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{left}個だった…", W / 2, 1090, 72, sw=12)
        else:
            k = min(1.0, (t - end_t) / 0.25)
            text(ctx, "全部こわした！", W / 2, 960, 140 * (1.6 - 0.6 * k), rgb=GOLD, sw=20)
            text(ctx, f"{end_t:.2f}秒  最大COMBO ×{res['max_combo']}", W / 2, 1090, 64, sw=12)

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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['result_t']:.2f}秒 最大COMBO {res['max_combo']} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
# ペツォールト「メヌエット ト長調」(バッハ「アンナ・マグダレーナの音楽帳」より・パブリックドメイン)
MELODY = [74, 67, 69, 71, 72, 74, 67, 67, 76, 72, 74, 76, 78, 79, 67, 67,
          72, 74, 72, 71, 69, 71, 72, 71, 69, 67, 66, 67, 69, 71, 67, 71, 69]
COMBO_SCALE = [60, 62, 64, 67, 69, 72, 74, 76, 79, 81, 84, 86, 88, 91, 93, 96]   # コンボ中は音が上がっていく
HOLY_GAIN = 0.85  # 成功BGMの音量
MIX_GAIN = 0.67  # 通常部分の音量(約 -18dB になるよう調整)


def synth_audio(events, end_t, fail, duration, path):
    rng = np.random.default_rng(0)
    out = np.zeros(int((duration + 3) * SR))

    def add(sig, t0):
        i = int(t0 * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    note_i = 0
    last_note = -1.0
    for kind, t, data in events:
        if kind in ("hit", "break"):
            combo = data[3]
            if t - last_note >= 0.035:
                if combo >= 3:
                    m = COMBO_SCALE[min(len(COMBO_SCALE) - 1, combo - 3)]
                    add(tone(midi_hz(m), 0.25, 0.30, 9), t)
                else:
                    add(tone(midi_hz(MELODY[note_i % len(MELODY)]), 0.35, 0.32, 7), t)
                    note_i += 1
                last_note = t
            if kind == "break":
                add(noise(0.08, 0.18, 40, rng, smooth=3), t)
        elif kind == "paddle":
            add(tone(180, 0.12, 0.25, 20), t)
        elif kind == "pickup":
            for k, m in enumerate((72, 76, 79, 84, 88)):
                add(tone(midi_hz(m), 0.3, 0.25, 6), t + k * 0.05)
        elif kind == "miss":
            for k, m in enumerate((67, 64, 60)):
                add(tone(midi_hz(m), 0.3, 0.25, 6), t + k * 0.12)
    scare = np.zeros_like(out)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        scare[i0:i0 + len(sig)] += sig[: len(scare) - i0]
        sad_t = end_t + SCARE_DUR + 0.1
        for k, m in enumerate((64, 63, 62)):
            add(tone(midi_hz(m), 0.45, 0.35, 3) + tone(midi_hz(m - 12), 0.45, 0.25, 3), sad_t + k * 0.42)
        add(tone(midi_hz(61), 1.4, 0.35, 1.5) + tone(midi_hz(49), 1.4, 0.25, 1.5), sad_t + 1.26)
    elif end_t is not None:   # 成功:神々しいBGM(正規化のあとに重ねる)
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(end_t * SR)
        scare[i0:i0 + len(sig)] += HOLY_GAIN * sig[: len(scare) - i0]
    wet = out.copy()
    for d, g in ((0.043, 0.3), (0.071, 0.24), (0.113, 0.17)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    # 通常部分は軽く圧縮して聞こえやすくし、叫び声との差は約10dBに抑える
    wet = np.tanh(2.5 * wet / max(1e-9, np.max(np.abs(wet)))) / np.tanh(2.5) * MIX_GAIN
    wet = np.clip(wet + (0.95 if fail else 1.0) * scare[: len(wet)], -0.98, 0.98)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--want", choices=["success", "fail"], default="success")
    ap.add_argument("-n", type=int, default=200)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
