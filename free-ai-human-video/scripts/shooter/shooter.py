"""「30秒でボスまで倒せる?」放物運動 + 空気抵抗 + 風のシューティング物理ショートを生成する。

展開:
  1. 最初は砲身1本・遅い連射で、風に流されてなかなか当たらない
  2. 大きいUFOを撃つと小さいUFO 2体に分裂する(敵が増える)
  3. ★付きのUFOを撃つと砲台が強化される(砲身が増える / 連射が速くなる / 爆発弾になる)
  4. WAVE 2 で新しいUFOの群れが飛んでくる
  5. ボス出現。HPが半分を切ると赤くなって速くなり、子分を呼ぶ
30秒以内にボスを倒せば成功、倒せなければ失敗(幽霊が出る)。

使い方:
    python shooter.py search [--want success|fail]
    python shooter.py render --seed N
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

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000

CANNON = (540.0, 1420.0)
GROUND_Y = 1460
SKY_TOP, SKY_BOTTOM = 640, 960   # UFOは高めを飛ぶ(砲弾の飛ぶ時間が長くなり、風の影響を受けやすい)
GRAVITY = 900.0
SHELL_SPEED = 1350.0
DRAG = 0.5                  # 空気抵抗(風に対する相対速度に比例)
WIND_MAX = 520.0
WIND_EVERY = 4.0
AIM_JITTER_START, AIM_JITTER_MIN, AIM_LEARN = 6.0, 1.5, 0.45   # 狙いのぶれ(度)。撃つたびに慣れて小さくなる
TIME_LIMIT = 30.0
OUTRO = 3.0

# 砲台の強化段階
BARREL_LEVELS = [1, 2, 3, 5]
SPREAD_DEG = {1: [0], 2: [-3, 3], 3: [-5, 0, 5], 5: [-10, -5, 0, 5, 10]}
FIRE_LEVELS = [0.6, 0.42, 0.3]
SHELL_R, BIG_SHELL_R, BLAST_R = 9, 15, 80

MID_R, SMALL_R, BOSS_R = 38, 24, 92
WAVE1 = 7
WAVE2 = 6
WAVE2_AT, BOSS_AT = 11.0, 19.0       # 前の群れが残っていてもこの時刻には次が来る
BOSS_HP = 100        # 成功率がおよそ半々になる値(40回中20回成功)
BOSS_SPEED = 170.0

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")
POWER_LABEL = {"barrel": "砲身+1!", "rapid": "連射UP!", "big": "爆発弾!"}


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        self.winds = [self.rng.uniform(-WIND_MAX, WIND_MAX) for _ in range(20)]
        # 最初の4秒は必ず強い風(序盤はなかなか当たらない)
        self.winds[0] = self.rng.choice([-1, 1]) * self.rng.uniform(0.8, 1.0) * WIND_MAX
        self.ufos, self.shells, self.events = [], [], []
        self.barrel_lv, self.fire_lv, self.big = 0, 0, False
        self.next_fire = 0.8
        self.ang = self.target_ang = math.pi / 2
        self.last_fire_t = -9.0
        self.volleys = 0
        self.wave, self.boss = 1, None
        self.t = 0.0
        self.result, self.result_t = None, None
        powers = ["barrel", "rapid", "barrel"] + [None] * (WAVE1 - 3)
        self.rng.shuffle(powers)
        for p in powers:
            self.spawn("mid", self.rng.uniform(140, W - 140), self.rng.uniform(SKY_TOP, SKY_BOTTOM - 60), p)

    def spawn(self, kind, x, y, power=None, vx=None, enter=False):
        r = {"mid": MID_R, "small": SMALL_R, "boss": BOSS_R}[kind]
        speed = {"mid": (90, 210), "small": (200, 320), "boss": (BOSS_SPEED, BOSS_SPEED)}[kind]
        u = {"kind": kind, "x": x, "y0": y, "r": r, "power": power,
             "vx": vx if vx is not None else self.rng.uniform(*speed) * self.rng.choice([-1, 1]),
             "bob_a": self.rng.uniform(10, 35), "bob_f": self.rng.uniform(0.4, 1.0),
             "bob_p": self.rng.uniform(0, 6.28), "alive": True, "hue": self.rng.uniform(),
             "hp": BOSS_HP if kind == "boss" else 1, "enter": enter, "enraged": False, "wave": self.wave}
        self.ufos.append(u)
        return u

    def pos(self, u, t=None):
        t = self.t if t is None else t
        return u["x"], u["y0"] + u["bob_a"] * math.sin(u["bob_f"] * 2 * math.pi * t + u["bob_p"])

    def wind(self):
        return self.winds[int(self.t // WIND_EVERY)]

    # 狙い:UFOの未来位置へ(重力のみ考慮、空気抵抗と風は無視)
    def aim(self, u):
        cx, cy = CANNON
        T, ang = 0.6, None
        for _ in range(6):
            tx = u["x"] + u["vx"] * T
            tx = min(max(tx, 80), W - 80)
            _, ty = self.pos({**u, "x": tx}, self.t + T)
            dx, h = tx - cx, cy - ty
            v2 = SHELL_SPEED ** 2
            disc = v2 * v2 - GRAVITY * (GRAVITY * dx * dx + 2 * h * v2)
            if disc < 0:
                return None, None
            if abs(dx) < 1:
                return math.pi / 2, h / SHELL_SPEED
            th = math.atan((v2 - math.sqrt(disc)) / (GRAVITY * abs(dx)))
            ang = th if dx > 0 else math.pi - th
            T = abs(dx) / (SHELL_SPEED * math.cos(th))
        return ang, T

    def fire(self):
        targets = [u for u in self.ufos if u["alive"] and not u["enter"]]
        best = None
        for u in targets:
            a, T = self.aim(u)
            if a is not None and (best is None or T < best[1]):
                best = (a, T)
        if best is None:
            return
        jitter = max(AIM_JITTER_MIN, AIM_JITTER_START - AIM_LEARN * self.volleys)
        self.volleys += 1
        base = best[0] + math.radians(self.rng.normal(0, jitter))
        self.target_ang = base
        n = BARREL_LEVELS[self.barrel_lv]
        r = BIG_SHELL_R if self.big else SHELL_R
        for off in SPREAD_DEG[n]:
            a = base + math.radians(off)
            self.shells.append({"x": CANNON[0] + math.cos(a) * 70, "y": CANNON[1] - math.sin(a) * 70,
                                "vx": SHELL_SPEED * math.cos(a), "vy": -SHELL_SPEED * math.sin(a),
                                "r": r, "big": self.big, "trail": []})
        self.last_fire_t = self.t
        self.events.append(("fire", self.t, n))

    def damage(self, u):
        if not u["alive"]:
            return
        u["hp"] -= 1
        x, y = self.pos(u)
        if u["kind"] == "boss":
            self.events.append(("boss_hit", self.t, (x, y)))
            if not u["enraged"] and u["hp"] <= BOSS_HP // 2:
                u["enraged"] = True
                u["vx"] *= 2.0
                self.events.append(("enrage", self.t, (x, y)))
                for k in range(3):
                    self.spawn("small", x, y - 30, vx=(-260, 0, 260)[k] or 150)
        if u["hp"] > 0:
            return
        u["alive"] = False
        self.events.append(("kill", self.t, (x, y, u["r"], u["hue"], u["kind"])))
        if u["kind"] == "mid":   # 分裂して小さいUFO 2体になる
            for d in (-1, 1):
                self.spawn("small", x + d * 20, y - 20, vx=d * self.rng.uniform(220, 320))
        if u["power"]:
            p = u["power"]
            if p == "barrel" and self.barrel_lv < len(BARREL_LEVELS) - 1:
                self.barrel_lv += 1
            elif p == "rapid" and self.fire_lv < len(FIRE_LEVELS) - 1:
                self.fire_lv += 1
            elif p == "big":
                self.big = True
            self.events.append(("power", self.t, (p, x, y)))
        if u["kind"] == "boss" and self.result is None:
            self.result, self.result_t = "success", self.t
            self.events.append(("success", self.t, None))

    def step(self, dt):
        self.t += dt
        t = self.t
        # 次の群れ・ボス
        alive_wave = [u for u in self.ufos if u["alive"] and u["kind"] != "boss"]
        if self.wave == 1 and (not alive_wave or t >= WAVE2_AT):
            self.wave = 2
            self.events.append(("wave", t, 2))
            powers = ["big", "barrel"] + [None] * (WAVE2 - 2)
            self.rng.shuffle(powers)
            for k, p in enumerate(powers):
                side = -1 if k % 2 == 0 else 1
                self.spawn("mid", W / 2 + side * (W / 2 + 60 + k * 40), self.rng.uniform(SKY_TOP, SKY_BOTTOM - 60),
                           p, vx=-side * self.rng.uniform(160, 240), enter=True)
        elif self.wave == 2 and (not alive_wave or t >= BOSS_AT) and self.boss is None:
            self.wave = 3
            self.boss = self.spawn("boss", W + 120, 790, vx=-BOSS_SPEED, enter=True)
            self.boss["bob_a"] = 40
            self.events.append(("boss", t, None))
        # UFOの移動
        for u in self.ufos:
            if not u["alive"]:
                continue
            u["x"] += u["vx"] * dt
            if u["enter"]:
                if 100 < u["x"] < W - 100:
                    u["enter"] = False
                continue
            lo, hi = 40 + u["r"], W - 40 - u["r"]
            if u["x"] < lo:
                u["x"], u["vx"] = lo, abs(u["vx"])
            if u["x"] > hi:
                u["x"], u["vx"] = hi, -abs(u["vx"])
        # 発射
        if self.result is None and t >= self.next_fire:
            self.fire()
            self.next_fire = t + FIRE_LEVELS[self.fire_lv]
        # 決着がついたら砲弾は消して、それ以降はダメージを与えない
        if self.result is not None:
            self.shells = []
        # 砲弾(重力 + 風に対する空気抵抗)
        wind = self.wind()
        for s in self.shells:
            s["vx"] += -DRAG * (s["vx"] - wind) * dt
            s["vy"] += (GRAVITY - DRAG * s["vy"]) * dt
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            for u in self.ufos:
                if not u["alive"] or u["enter"]:
                    continue
                ux, uy = self.pos(u)
                if (s["x"] - ux) ** 2 + (s["y"] - uy) ** 2 < (u["r"] + s["r"]) ** 2:
                    s["dead"] = True
                    if s["big"]:   # 爆発弾:周りのUFOにもダメージ
                        self.events.append(("blast", t, (s["x"], s["y"])))
                        for v in self.ufos:
                            if v["alive"] and not v["enter"]:
                                vx_, vy_ = self.pos(v)
                                if (vx_ - s["x"]) ** 2 + (vy_ - s["y"]) ** 2 < (BLAST_R + v["r"]) ** 2:
                                    self.damage(v)
                    else:
                        self.damage(u)
                    break
            if s["y"] > GROUND_Y or s["x"] < -80 or s["x"] > W + 80:
                s["dead"] = True
        self.shells = [s for s in self.shells if not s.get("dead")]
        if self.result is None and t >= TIME_LIMIT:
            self.result, self.result_t = "fail", TIME_LIMIT
            self.events.append(("fail", t, None))
        self.ang += (self.target_ang - self.ang) * 0.02


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            if g.result is None or record:
                g.step(dt)
        if record:
            for s in g.shells:
                s["trail"].append((s["x"], s["y"]))
                del s["trail"][:-12]
            frames.append({
                "t": g.t, "wind": g.wind(), "ang": g.ang,
                "recoil": max(0.0, 1 - (g.t - g.last_fire_t) / 0.15),
                "barrels": BARREL_LEVELS[g.barrel_lv], "fire_lv": g.fire_lv, "big": g.big,
                "ufos": [(g.pos(u), u["r"], u["kind"], u["hue"], u["power"], u["hp"], u["enraged"])
                         for u in g.ufos if u["alive"]],
                "shells": [(s["x"], s["y"], s["r"], list(s["trail"])) for s in g.shells],
                "boss_hp": g.boss["hp"] if g.boss else None,
            })
        if g.result is not None:
            extra = OUTRO + (SCARE_DUR if g.result == "fail" else 0)
            if not record or g.t > g.result_t + extra:
                break
    first_hit = next((e[1] for e in g.events if e[0] in ("kill", "boss_hit")), 99)
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "boss_hp": g.boss["hp"] if g.boss else BOSS_HP, "first_hit": first_hit,
            "boss_t": next((e[1] for e in g.events if e[0] == "boss"), None)}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], max(0, r["boss_hp"]), r["first_hit"], r["boss_t"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "success":
        good = sorted(succ, key=lambda r: -r[2])
        for seed, _, rt, _, fh, bt in good[:15]:
            print(f"seed={seed:4d}  ボス撃破 {rt:5.2f}秒  最初の命中 {fh:4.1f}秒  ボス出現 {bt}")
    else:
        good = sorted([r for r in rs if r[1] == "fail"], key=lambda r: r[3])
        for seed, _, _, hp, fh, bt in good[:15]:
            print(f"seed={seed:4d}  時間切れ ボス残りHP {hp}  最初の命中 {fh:4.1f}秒  ボス出現 {bt}")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def background(rng):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, 0.02, 0.02, 0.07)
    g.add_color_stop_rgb(0.6, 0.08, 0.06, 0.20)
    g.add_color_stop_rgb(1, 0.02, 0.02, 0.05)
    ctx.set_source(g)
    ctx.paint()
    for _ in range(140):
        ctx.new_path()
        ctx.arc(rng.uniform(0, W), rng.uniform(420, GROUND_Y - 40), rng.uniform(0.8, 2.4), 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, rng.uniform(0.2, 0.7))
        ctx.fill()
    for wdt, al in ((24, 0.08), (12, 0.18), (5, 0.9)):
        ctx.new_path()
        ctx.move_to(0, GROUND_Y)
        ctx.line_to(W, GROUND_Y)
        ctx.set_source_rgba(0.55, 0.62, 1.0, al)
        ctx.set_line_width(wdt)
        ctx.stroke()
    return surf


def ellipse(ctx, x, y, rx, ry, start=0, end=2 * math.pi):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(rx, ry)
    ctx.new_path()
    ctx.arc(0, 0, 1, start, end)
    ctx.restore()


def draw_ufo(ctx, x, y, r, col):
    for grow, al in ((r * 0.6, 0.10), (r * 0.3, 0.22)):
        ellipse(ctx, x, y, r + grow, (r + grow) * 0.42)
        ctx.set_source_rgba(*col, al)
        ctx.fill()
    ellipse(ctx, x, y - r * 0.22, r * 0.5, r * 0.45, math.pi, 2 * math.pi)
    ctx.set_source_rgba(0.75, 0.95, 1.0, 0.85)
    ctx.fill()
    ellipse(ctx, x, y, r, r * 0.36)
    ctx.set_source_rgb(*col)
    ctx.fill()
    for k in (-2, -1, 0, 1, 2):
        ctx.new_path()
        ctx.arc(x + k * r * 0.36, y + 2, max(2.5, r * 0.1), 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 0.85)
        ctx.fill()


def draw_cannon(ctx, ang, recoil, barrels, big, fire_lv):
    cx, cy = CANNON
    col = [(0.75, 0.8, 0.95), (0.5, 0.95, 1.0), (1, 0.85, 0.35)][min(2, fire_lv)]
    thick = 34 if big else 26
    for off in SPREAD_DEG[barrels]:
        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(-(ang + math.radians(off) * 2.2))   # 砲身の広がりは見やすいよう少し大げさに描く
        back = 16 * recoil
        for grow, al in ((10, 0.12), (0, 1.0)):
            ctx.new_path()
            ctx.rectangle(-back - grow, -thick / 2 - grow, 80 + 2 * grow, thick + 2 * grow)
            ctx.set_source_rgba(*col, al)
            ctx.fill()
        if recoil > 0.5:
            ctx.new_path()
            ctx.arc(80 - back + 16, 0, 24 * recoil, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.85, 0.4, 0.8 * recoil)
            ctx.fill()
        ctx.restore()
    ctx.new_path()
    ctx.arc(cx, cy + 6, 56, math.pi, 2 * math.pi)
    ctx.close_path()
    ctx.set_source_rgb(0.35, 0.4, 0.6)
    ctx.fill()


def draw_wind(ctx, wind, streaks):
    for st in streaks:
        st[0] = (st[0] + wind * 1.4 / FPS) % (W + 200)
        x = st[0] - 100
        ctx.new_path()
        ctx.move_to(x, st[1])
        ctx.line_to(x - wind * 0.12, st[1])
        ctx.set_source_rgba(0.8, 0.9, 1.0, 0.10 + 0.25 * min(1, abs(wind) / WIND_MAX))
        ctx.set_line_width(2)
        ctx.stroke()
    y = 570
    text(ctx, "風", W / 2 - 150, y + 16, 44, sw=8)
    ln = 140 * wind / WIND_MAX
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.new_path()
    ctx.move_to(W / 2 + 30 - ln / 2, y)
    ctx.line_to(W / 2 + 30 + ln / 2, y)
    ctx.set_source_rgb(0.6, 0.9, 1.0)
    ctx.set_line_width(10)
    ctx.stroke()
    if abs(ln) > 8:
        d = 1 if ln > 0 else -1
        tip = W / 2 + 30 + ln / 2
        ctx.new_path()
        ctx.move_to(tip + d * 18, y)
        ctx.line_to(tip - d * 6, y - 18)
        ctx.line_to(tip - d * 6, y + 18)
        ctx.close_path()
        ctx.fill()


def burst(particles, rng, x, y, col, n, speed, life):
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        sp = rng.uniform(*speed)
        particles.append([x, y, math.cos(a) * sp, math.sin(a) * sp, 0, rng.uniform(*life), col])


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"shooter_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"shooter_{seed}.wav")
    final = os.path.join(OUT_DIR, f"shooter_{seed}.mp4")
    rng = np.random.default_rng(seed + 999)
    bg = background(rng)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    particles, waves, popups, banners = [], [], [], []
    boss_flash = -9.0
    streaks = [[rng.uniform(0, W + 200), rng.uniform(620, GROUND_Y - 80)] for _ in range(40)]
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        dt = 1 / FPS
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "kill":
                x, y, r, hue, k = data
                col = (1, 0.3, 0.3) if k == "boss" else hue_rgb(hue)
                burst(particles, rng, x, y, col, 160 if k == "boss" else 40, (100, 900 if k == "boss" else 600), (0.5, 1.4))
                waves.append([et, x, y, col, r])
            elif kind == "blast":
                waves.append([et, data[0], data[1], (1, 0.6, 0.2), BLAST_R * 0.4])
            elif kind == "boss_hit":
                boss_flash = et
                burst(particles, rng, data[0], data[1], (1, 0.9, 0.5), 6, (100, 300), (0.2, 0.4))
            elif kind == "power":
                p, x, y = data
                popups.append([et, x, y, POWER_LABEL[p]])
                burst(particles, rng, x, y, GOLD, 50, (150, 500), (0.6, 1.0))
            elif kind == "wave":
                banners.append([et, "WAVE 2", (0.5, 0.95, 1.0)])
            elif kind == "boss":
                banners.append([et, "ボス出現！", (1, 0.3, 0.3)])
            elif kind == "enrage":
                banners.append([et, "ボス激怒！", (1, 0.3, 0.3)])
            elif kind == "success":
                for _ in range(240):
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
        draw_wind(ctx, fr["wind"], streaks)
        for (ux, uy), r, kind, hue, power, hp, enraged in fr["ufos"]:
            if kind == "boss":
                pulse = 0.5 + 0.5 * math.sin(t * 10)
                col = (1, 0.25 + 0.2 * pulse, 0.25) if enraged else (0.65, 0.45, 1.0)
                fl = max(0.0, 1 - (t - boss_flash) / 0.08)
                col = tuple(v + (1 - v) * fl * 0.6 for v in col)
                draw_ufo(ctx, ux, uy, r, col)
                # HPバー
                bw = 320
                frac = max(0, hp) / BOSS_HP
                ctx.new_path()
                ctx.rectangle(ux - bw / 2, uy - r - 40, bw, 18)
                ctx.set_source_rgba(0, 0, 0, 0.6)
                ctx.fill()
                ctx.new_path()
                ctx.rectangle(ux - bw / 2, uy - r - 40, bw * frac, 18)
                ctx.set_source_rgb(*((1, 0.3, 0.3) if frac < 0.5 else (0.4, 1, 0.5)))
                ctx.fill()
                text(ctx, f"BOSS  HP {max(0, hp)}", ux, uy - r - 52, 34, sw=6)
            else:
                draw_ufo(ctx, ux, uy, r, hue_rgb(hue))
                if power:
                    text(ctx, "★", ux, uy - r * 0.6, 40, rgb=GOLD, sw=6)
        for wv in waves:
            age = t - wv[0]
            if 0 <= age < 0.4:
                k = age / 0.4
                ctx.new_path()
                ctx.arc(wv[1], wv[2], wv[4] + 110 * k, 0, 2 * math.pi)
                ctx.set_source_rgba(*wv[3], 0.8 * (1 - k))
                ctx.set_line_width(10 * (1 - k) + 2)
                ctx.stroke()
        for sx, sy, sr, trail in fr["shells"]:
            for j, (tx, ty) in enumerate(trail):
                a = (j + 1) / max(1, len(trail))
                ctx.new_path()
                ctx.arc(tx, ty, sr * (0.3 + 0.7 * a), 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.75, 0.3, 0.3 * a)
                ctx.fill()
            ctx.new_path()
            ctx.arc(sx, sy, sr * 1.8, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.8, 0.3, 0.3)
            ctx.fill()
            ctx.new_path()
            ctx.arc(sx, sy, sr, 0, 2 * math.pi)
            ctx.set_source_rgb(1, 1, 0.9)
            ctx.fill()
        draw_cannon(ctx, fr["ang"], fr["recoil"], fr["barrels"], fr["big"], fr["fire_lv"])
        alive_p = []
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
            alive_p.append(p)
        particles = alive_p
        for pu in popups:   # 強化の文字がふわっと上がって消える
            age = t - pu[0]
            if 0 <= age < 1.2:
                text(ctx, pu[3], min(max(pu[1], 220), W - 220), pu[2] - 40 - 80 * age, 64,
                     rgb=GOLD, sw=12, alpha=min(1, 2 * (1.2 - age)))
        for bn in banners:  # 画面中央の大きな告知
            age = t - bn[0]
            if 0 <= age < 1.3:
                k = min(1, age / 0.15)
                text(ctx, bn[1], W / 2, 1080, 130 * (1.5 - 0.5 * k), rgb=bn[2], sw=20,
                     alpha=min(1, 3 * (1.3 - age)))

        # 文字
        shown_t = min(t, TIME_LIMIT)
        remain = TIME_LIMIT - shown_t
        text(ctx, "30秒で", W / 2, 200, 84, sw=14)
        text(ctx, "ボスまで倒せる？", W / 2, 320, 104, rgb=GOLD, sw=18)
        text(ctx, "Can it beat the boss in 30 seconds?", W / 2, 385, 38, rgb=(0.85, 0.85, 0.9), sw=8)
        danger = remain <= 5 and not over
        pulse = 1 + (0.12 * max(0, 1 - (shown_t % 1) / 0.25) if danger else 0)
        tcol = (1, 0.25, 0.25) if (danger or (fail and over)) else ((0.3, 1, 0.5) if over else (1, 1, 1))
        text(ctx, f"{remain:05.2f}", W / 2, 490, 84 * pulse, rgb=tcol, sw=12)
        text(ctx, f"砲身×{fr['barrels']}", 50, 490, 50, sw=10, align="left")
        lv = f"連射Lv{fr['fire_lv'] + 1}" + (" 爆発弾" if fr["big"] else "")
        text(ctx, lv, W - 190, 490, 40, sw=10)
        if not over:
            text(ctx, "※失敗すると…アレが出ます", W / 2, 1560, 50, rgb=(1, 0.35, 0.35), sw=10)
        elif fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 1080, 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"ボスのHP あと{max(0, res['boss_hp'])}", W / 2, 1210, 72, sw=12)
            text(ctx, "あと1発だったのに…" if res["boss_hp"] == 1 else "あと少しだったのに…",
                 W / 2, 1560, 54, rgb=(0.9, 0.9, 0.95), sw=10)
        else:
            k = min(1.0, (t - end_t) / 0.25)
            text(ctx, "ボス撃破！", W / 2, 1080, 150 * (1.6 - 0.6 * k), rgb=GOLD, sw=20)
            text(ctx, f"残り{TIME_LIMIT - end_t:.2f}秒", W / 2, 1210, 80, sw=12)

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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} ボスHP {res['boss_hp']} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
# ワーグナー「ワルキューレの騎行」(1870年・パブリックドメイン)の主題(分散和音の動き)
MELODY = [66, 71, 66, 71, 74, 71, 74, 78, 74, 78, 81, 78,
          69, 74, 69, 74, 78, 74, 73, 78, 73, 78, 81, 78]


def synth_audio(events, end_t, fail, duration, path):
    rng = np.random.default_rng(0)
    out = np.zeros(int((duration + 3) * SR))

    def add(sig, t0):
        i = int(t0 * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    note_i = 0
    last_hit = -1.0
    for kind, t, data in events:
        if kind == "fire":
            add(tone(70, 0.25, 0.5, 12) + noise(0.25, 0.25, 20, rng, smooth=8), t)
            m = MELODY[note_i % len(MELODY)]
            add(tone(midi_hz(m), 0.35, 0.30, 7), t)
            note_i += 1
        elif kind == "kill":
            big = data[4] == "boss"
            add(noise(1.2 if big else 0.5, 0.6 if big else 0.4, 4 if big else 8, rng, smooth=3), t)
            add(tone(50, 0.8 if big else 0.5, 0.6 if big else 0.4, 4), t)
        elif kind == "boss_hit":
            if t - last_hit > 0.07:
                add(tone(620, 0.08, 0.10, 40) + tone(930, 0.08, 0.06, 40), t)
                last_hit = t
        elif kind == "power":
            for k, m in enumerate((72, 76, 79, 84)):
                add(tone(midi_hz(m), 0.3, 0.25, 6), t + k * 0.06)
        elif kind in ("wave", "boss", "enrage"):
            for k, m in enumerate((47, 47, 54) if kind != "enrage" else (42, 41, 40)):
                add(tone(midi_hz(m), 0.5, 0.45, 3) + noise(0.5, 0.08, 6, rng, smooth=10), t + k * 0.22)
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
            add(tone(midi_hz(59 + iv), 2.5, 0.25, 1.2), end_t)
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


MIX_GAIN = 0.52  # 通常部分の音量(約 -18dB になるよう調整)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--want", choices=["success", "fail"], default="fail")
    ap.add_argument("-n", type=int, default=300)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
