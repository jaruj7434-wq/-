"""「30秒でボスまで倒せる?」自機UFOのシューティング物理ショートを生成する。

- 自機UFOは常に左右に動きながら真上へ撃つ。弾は自機の横の速さを受け継ぐので斜めに飛ぶ(相対運動)。
  弾は重力で減速し、空気抵抗と風で流される。
- 敵には「あと何回当てれば壊れるか」の数字(HP)を表示する。大きい敵は壊すと小さい敵 2体に分裂する。
- 雑魚敵を倒すとまれにアイテムが落ちてくる(重力 + 風)。自機が拾うと強化される:
    攻撃力UP(1発のダメージ+1) / ショットUP(同時に撃つ弾+1) / UFO+1(僚機が増える)
  僚機はバネのように自機についてくる。アイテムは取り逃すこともある。
- WAVE 2 → ボス出現。ボスはHPが半分を切ると赤くなって速くなり、子分を呼ぶ。
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

GROUND_Y = 1470
PLAYER_Y = 1360
SKY_TOP, SKY_BOTTOM = 650, 980
GRAVITY = 900.0
DRAG = 0.5                  # 空気抵抗(風に対する相対速度に比例)
WIND_MAX = 450.0
WIND_EVERY = 4.0
TIME_LIMIT = 30.0
OUTRO = 3.0

# 自機
SHIP_R = 40
PATROL_SPEED = 300.0        # ふだんの左右移動の速さ
CHASE_SPEED = 460.0         # アイテムを取りに行くときの最高速度
SHIP_MIN_X, SHIP_MAX_X = 100, W - 100
FIRE_EVERY = 0.32
BULLET_SPEED = 1300.0
BULLET_R = 8
SPREAD_DEG = {1: [0], 2: [-4, 4], 3: [-7, 0, 7], 4: [-10, -3.5, 3.5, 10], 5: [-12, -6, 0, 6, 12]}
MAX_SHOTS, MAX_SHIPS, MAX_ATK = 5, 3, 4
WING_OFFSETS = [-130, 130]
SPRING_K, SPRING_C = 40.0, 9.0     # 僚機のバネ(少し揺れが残る程度の減衰)

# 敵
MID_R, SMALL_R, BOSS_R = 40, 26, 92
WAVE1, WAVE2 = 8, 7
WAVE2_AT, BOSS_AT = 11.0, 19.0     # 前の群れが残っていてもこの時刻には次が来る
BOSS_HP = 60         # 成功率がおよそ半々になる値(60回中30回成功)
BOSS_SPEED = 170.0

# アイテム
ITEM_P = 0.16               # 雑魚を倒したときにアイテムが落ちる確率
ITEM_KINDS = ["atk", "shot", "ufo"]
ITEM_WEIGHTS = [0.35, 0.40, 0.25]
ITEM_R = 30
ITEM_GRAVITY = 420.0
ITEM_DRAG = 1.2
ITEM_LABEL = {"atk": "攻撃力UP!", "shot": "ショットUP!", "ufo": "UFO+1!"}
ITEM_TEXT = {"atk": "攻", "shot": "弾", "ufo": "機"}
ITEM_COLOR = {"atk": (1, 0.35, 0.35), "shot": (1, 0.85, 0.25), "ufo": (0.35, 1, 0.6)}

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        self.winds = [self.rng.uniform(-WIND_MAX, WIND_MAX) for _ in range(20)]
        self.winds[0] = self.rng.choice([-1, 1]) * self.rng.uniform(0.8, 1.0) * WIND_MAX   # 序盤は強風
        self.enemies, self.bullets, self.items, self.events = [], [], [], []
        self.atk, self.shots = 1, 1
        # 自機(先頭が本機、残りが僚機)。[x, vx]
        self.ships = [[W / 2, PATROL_SPEED * self.rng.choice([-1, 1])]]
        self.patrol_dir = 1 if self.ships[0][1] > 0 else -1
        self.next_fire = 0.6
        self.wave, self.boss = 1, None
        self.t = 0.0
        self.result, self.result_t = None, None
        for _ in range(WAVE1):
            self.spawn("mid", self.rng.uniform(140, W - 140), self.rng.uniform(SKY_TOP, SKY_BOTTOM),
                       hp=int(self.rng.integers(2, 6)))

    def spawn(self, kind, x, y, hp, vx=None, enter=False):
        r = {"mid": MID_R, "small": SMALL_R, "boss": BOSS_R}[kind]
        speed = {"mid": (90, 200), "small": (200, 300), "boss": (BOSS_SPEED, BOSS_SPEED)}[kind]
        e = {"kind": kind, "x": x, "y0": y, "r": r, "hp": hp,
             "vx": vx if vx is not None else self.rng.uniform(*speed) * self.rng.choice([-1, 1]),
             "bob_a": self.rng.uniform(10, 30), "bob_f": self.rng.uniform(0.4, 1.0),
             "bob_p": self.rng.uniform(0, 6.28), "alive": True, "hue": self.rng.uniform(),
             "enter": enter, "enraged": False}
        self.enemies.append(e)
        return e

    def pos(self, e):
        return e["x"], e["y0"] + e["bob_a"] * math.sin(e["bob_f"] * 2 * math.pi * self.t + e["bob_p"])

    def wind(self):
        return self.winds[int(self.t // WIND_EVERY)]

    def damage(self, e, dmg):
        if not e["alive"]:
            return
        e["hp"] -= dmg
        x, y = self.pos(e)
        if e["kind"] == "boss":
            self.events.append(("boss_hit", self.t, (x, y)))
            if not e["enraged"] and e["hp"] <= BOSS_HP // 2:
                e["enraged"] = True
                e["vx"] *= 2.0
                self.events.append(("enrage", self.t, (x, y)))
                for vx in (-260, 150, 260):
                    self.spawn("small", x, y - 30, hp=3, vx=vx)
        elif e["hp"] > 0:
            self.events.append(("hit", self.t, (x, y)))
        if e["hp"] > 0:
            return
        e["alive"] = False
        self.events.append(("kill", self.t, (x, y, e["r"], e["hue"], e["kind"])))
        if e["kind"] == "mid":   # 分裂して小さい敵 2体になる
            for d in (-1, 1):
                self.spawn("small", x + d * 20, y - 20, hp=int(self.rng.integers(1, 3)),
                           vx=d * self.rng.uniform(220, 320))
        if e["kind"] != "boss" and self.rng.random() < ITEM_P:   # まれにアイテムが落ちる
            kind = ITEM_KINDS[int(self.rng.choice(3, p=ITEM_WEIGHTS))]
            self.items.append({"kind": kind, "x": x, "y": y, "vx": 0.0, "vy": -150.0})
            self.events.append(("drop", self.t, (kind, x, y)))
        if e["kind"] == "boss" and self.result is None:
            self.result, self.result_t = "success", self.t
            self.events.append(("success", self.t, None))

    def pickup(self, it):
        k = it["kind"]
        if k == "atk":
            self.atk = min(MAX_ATK, self.atk + 1)
        elif k == "shot":
            self.shots = min(MAX_SHOTS, self.shots + 1)
        elif k == "ufo" and len(self.ships) < MAX_SHIPS:
            lead = self.ships[0][0]
            self.ships.append([lead, 0.0])
        self.events.append(("pickup", self.t, (k, it["x"], it["y"])))

    def move_ships(self, dt):
        lead = self.ships[0]
        # 落ちてくるアイテムがあれば、着地しそうな位置へ向かう(間に合わないこともある)
        target = None
        if self.items:
            best = None
            for it in self.items:
                dy = PLAYER_Y - it["y"]
                if dy < -20:
                    continue
                tt = dy / max(80.0, it["vy"] + 1) if it["vy"] > 0 else 1.5
                px = it["x"] + it["vx"] * min(tt, 2.0)
                if best is None or tt < best[0]:
                    best = (tt, px)
            if best:
                target = min(max(best[1], SHIP_MIN_X), SHIP_MAX_X)
        if target is not None:
            d = target - lead[0]
            lead[1] = max(-CHASE_SPEED, min(CHASE_SPEED, d * 4))
        else:
            if lead[0] <= SHIP_MIN_X:
                self.patrol_dir = 1
            elif lead[0] >= SHIP_MAX_X:
                self.patrol_dir = -1
            lead[1] += (PATROL_SPEED * self.patrol_dir - lead[1]) * min(1, 4 * dt)
        lead[0] = min(max(lead[0] + lead[1] * dt, SHIP_MIN_X), SHIP_MAX_X)
        # 僚機はバネで本機の左右についてくる
        for k, s in enumerate(self.ships[1:]):
            goal = lead[0] + WING_OFFSETS[k]
            acc = SPRING_K * (goal - s[0]) - SPRING_C * s[1]
            s[1] += acc * dt
            s[0] = min(max(s[0] + s[1] * dt, 40), W - 40)

    def fire(self):
        for s in self.ships:
            for off in SPREAD_DEG[self.shots]:
                a = math.radians(off)
                self.bullets.append({"x": s[0], "y": PLAYER_Y - SHIP_R,
                                     "vx": s[1] + BULLET_SPEED * math.sin(a),   # 自機の横の速さを受け継ぐ
                                     "vy": -BULLET_SPEED * math.cos(a), "trail": []})
        self.events.append(("fire", self.t, len(self.ships) * self.shots))

    def step(self, dt):
        self.t += dt
        t = self.t
        # 次の群れ・ボス
        alive = [e for e in self.enemies if e["alive"] and e["kind"] != "boss"]
        if self.wave == 1 and (not alive or t >= WAVE2_AT):
            self.wave = 2
            self.events.append(("wave", t, 2))
            for k in range(WAVE2):
                side = -1 if k % 2 == 0 else 1
                self.spawn("mid", W / 2 + side * (W / 2 + 60 + k * 40), self.rng.uniform(SKY_TOP, SKY_BOTTOM),
                           hp=int(self.rng.integers(3, 7)), vx=-side * self.rng.uniform(160, 240), enter=True)
        elif self.wave == 2 and (not alive or t >= BOSS_AT) and self.boss is None:
            self.wave = 3
            self.boss = self.spawn("boss", W + 120, 790, hp=BOSS_HP, vx=-BOSS_SPEED, enter=True)
            self.boss["bob_a"] = 40
            self.events.append(("boss", t, None))
        # 敵の移動
        for e in self.enemies:
            if not e["alive"]:
                continue
            e["x"] += e["vx"] * dt
            if e["enter"]:
                if 100 < e["x"] < W - 100:
                    e["enter"] = False
                continue
            lo, hi = 40 + e["r"], W - 40 - e["r"]
            if e["x"] < lo:
                e["x"], e["vx"] = lo, abs(e["vx"])
            if e["x"] > hi:
                e["x"], e["vx"] = hi, -abs(e["vx"])
        self.move_ships(dt)
        if self.result is None and t >= self.next_fire:
            self.fire()
            self.next_fire = t + FIRE_EVERY
        if self.result is not None:   # 決着後は弾を消してダメージを与えない
            self.bullets = []
        wind = self.wind()
        # 弾(重力 + 風に対する空気抵抗)
        for b in self.bullets:
            b["vx"] += -DRAG * (b["vx"] - wind) * dt
            b["vy"] += (GRAVITY - DRAG * b["vy"]) * dt
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            for e in self.enemies:
                if not e["alive"] or e["enter"]:
                    continue
                ex, ey = self.pos(e)
                if (b["x"] - ex) ** 2 + (b["y"] - ey) ** 2 < (e["r"] + BULLET_R) ** 2:
                    b["dead"] = True
                    self.damage(e, self.atk)
                    break
            if b["y"] > GROUND_Y or b["x"] < -60 or b["x"] > W + 60 or (b["vy"] > 0 and b["y"] > PLAYER_Y):
                b["dead"] = True
        self.bullets = [b for b in self.bullets if not b.get("dead")]
        # アイテム(重力 + 風に流される)
        for it in self.items:
            it["vx"] += -ITEM_DRAG * (it["vx"] - wind * 0.6) * dt
            it["vy"] += (ITEM_GRAVITY - ITEM_DRAG * 0.3 * it["vy"]) * dt
            it["x"] = min(max(it["x"] + it["vx"] * dt, 30), W - 30)
            it["y"] += it["vy"] * dt
            if self.result is None and any((it["x"] - s[0]) ** 2 + (it["y"] - PLAYER_Y) ** 2 < (ITEM_R + SHIP_R) ** 2
                                           for s in self.ships):
                it["dead"] = True
                self.pickup(it)
            elif it["y"] > GROUND_Y:
                it["dead"] = True
                self.events.append(("miss_item", t, (it["kind"], it["x"])))
        self.items = [it for it in self.items if not it.get("dead")]
        if self.result is None and t >= TIME_LIMIT:
            self.result, self.result_t = "fail", TIME_LIMIT
            self.events.append(("fail", t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            if g.result is None or record:
                g.step(dt)
        if record:
            for b in g.bullets:
                b["trail"].append((b["x"], b["y"]))
                del b["trail"][:-8]
            frames.append({
                "t": g.t, "wind": g.wind(), "atk": g.atk, "shots": g.shots,
                "ships": [(s[0], s[1]) for s in g.ships],
                "enemies": [(g.pos(e), e["r"], e["kind"], e["hue"], e["hp"], e["enraged"])
                            for e in g.enemies if e["alive"]],
                "bullets": [(b["x"], b["y"], list(b["trail"])) for b in g.bullets],
                "items": [(it["x"], it["y"], it["kind"]) for it in g.items],
                "boss_hp": g.boss["hp"] if g.boss else None,
            })
        if g.result is not None:
            extra = OUTRO + (SCARE_DUR if g.result == "fail" else 0)
            if not record or g.t > g.result_t + extra:
                break
    first_kill = next((e[1] for e in g.events if e[0] == "kill"), 99)
    pickups = [e[2][0] for e in g.events if e[0] == "pickup"]
    misses = sum(1 for e in g.events if e[0] == "miss_item")
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "boss_hp": max(0, g.boss["hp"]) if g.boss else BOSS_HP, "first_kill": first_kill,
            "pickups": pickups, "misses": misses,
            "boss_t": next((e[1] for e in g.events if e[0] == "boss"), None)}


def score(seed):
    r = simulate(seed)
    return (seed, r["result"], r["result_t"], r["boss_hp"], r["first_kill"], r["boss_t"],
            "".join(ITEM_TEXT[k] for k in r["pickups"]), r["misses"])


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "success":
        good = sorted(succ, key=lambda r: -r[2])
        for seed, _, rt, _, fk, bt, pk, ms in good[:15]:
            print(f"seed={seed:4d}  ボス撃破 {rt:5.2f}秒  最初の撃破 {fk:4.1f}秒  ボス {bt}  取得 {pk}  取り逃し {ms}")
    else:
        good = sorted([r for r in rs if r[1] == "fail"], key=lambda r: r[3])
        for seed, _, _, hp, fk, bt, pk, ms in good[:15]:
            print(f"seed={seed:4d}  ボス残りHP {hp}  最初の撃破 {fk:4.1f}秒  ボス {bt}  取得 {pk}  取り逃し {ms}")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
SHIP_COL = (0.35, 0.95, 1.0)


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


def draw_ship(ctx, x, vx, t, scale=1.0):
    """自機UFO:上向きの砲口つき。進む向きに少し傾く。"""
    r = SHIP_R * scale
    ctx.save()
    ctx.translate(x, PLAYER_Y)
    ctx.rotate(max(-0.25, min(0.25, vx / 2000)))
    flick = 0.7 + 0.3 * math.sin(t * 40)
    ellipse(ctx, 0, r * 0.45, r * 0.35, r * 0.6 * flick)   # 下の噴射
    ctx.set_source_rgba(1, 0.6, 0.2, 0.7)
    ctx.fill()
    ctx.new_path()
    ctx.rectangle(-6 * scale, -r * 0.95, 12 * scale, r * 0.6)   # 砲口
    ctx.set_source_rgb(0.85, 0.95, 1.0)
    ctx.fill()
    for grow, al in ((r * 0.6, 0.12), (r * 0.3, 0.25)):
        ellipse(ctx, 0, 0, r + grow, (r + grow) * 0.42)
        ctx.set_source_rgba(*SHIP_COL, al)
        ctx.fill()
    ellipse(ctx, 0, -r * 0.2, r * 0.48, r * 0.45, math.pi, 2 * math.pi)
    ctx.set_source_rgba(0.9, 1, 1, 0.9)
    ctx.fill()
    ellipse(ctx, 0, 0, r, r * 0.36)
    ctx.set_source_rgb(*SHIP_COL)
    ctx.fill()
    ctx.restore()


def draw_item(ctx, x, y, kind, t):
    col = ITEM_COLOR[kind]
    pulse = 1 + 0.08 * math.sin(t * 12)
    for rr, al in ((ITEM_R * 1.7 * pulse, 0.15), (ITEM_R * 1.25, 0.3)):
        ctx.new_path()
        ctx.arc(x, y, rr, 0, 2 * math.pi)
        ctx.set_source_rgba(*col, al)
        ctx.fill()
    ctx.new_path()
    ctx.arc(x, y, ITEM_R, 0, 2 * math.pi)
    ctx.set_source_rgb(*col)
    ctx.fill()
    text(ctx, ITEM_TEXT[kind], x, y + 13, 36, rgb=(1, 1, 1), sw=6)


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
    y = 580
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
                burst(particles, rng, x, y, col, 160 if k == "boss" else 36,
                      (100, 900 if k == "boss" else 550), (0.5, 1.3))
                waves.append([et, x, y, col, r])
            elif kind == "hit":
                burst(particles, rng, data[0], data[1], (1, 1, 0.8), 4, (80, 250), (0.15, 0.3))
            elif kind == "boss_hit":
                boss_flash = et
                burst(particles, rng, data[0], data[1], (1, 0.9, 0.5), 5, (100, 300), (0.2, 0.4))
            elif kind == "pickup":
                k, x, y = data
                popups.append([et, x, PLAYER_Y - 60, ITEM_LABEL[k], ITEM_COLOR[k]])
                burst(particles, rng, x, PLAYER_Y, ITEM_COLOR[k], 50, (150, 500), (0.5, 0.9))
            elif kind == "miss_item":
                popups.append([et, data[1], GROUND_Y - 40, "あっ…", (0.8, 0.8, 0.85)])
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
        # 敵(中央に「あと何回で壊れるか」の数字)
        for (ex, ey), r, kind, hue, hp, enraged in fr["enemies"]:
            if kind == "boss":
                pulse = 0.5 + 0.5 * math.sin(t * 10)
                col = (1, 0.25 + 0.2 * pulse, 0.25) if enraged else (0.65, 0.45, 1.0)
                fl = max(0.0, 1 - (t - boss_flash) / 0.08)
                col = tuple(v + (1 - v) * fl * 0.6 for v in col)
                draw_ufo(ctx, ex, ey, r, col)
                bw = 320
                frac = max(0, hp) / BOSS_HP
                ctx.new_path()
                ctx.rectangle(ex - bw / 2, ey - r - 40, bw, 18)
                ctx.set_source_rgba(0, 0, 0, 0.6)
                ctx.fill()
                ctx.new_path()
                ctx.rectangle(ex - bw / 2, ey - r - 40, bw * frac, 18)
                ctx.set_source_rgb(*((1, 0.3, 0.3) if frac < 0.5 else (0.4, 1, 0.5)))
                ctx.fill()
                text(ctx, f"BOSS  HP {max(0, hp)}", ex, ey - r - 52, 34, sw=6)
            else:
                draw_ufo(ctx, ex, ey, r, hue_rgb(hue))
                size = 30 if kind == "mid" else 24
                text(ctx, str(max(0, hp)), ex, ey + size * 0.36, size, sw=6)
        for wv in waves:
            age = t - wv[0]
            if 0 <= age < 0.4:
                k = age / 0.4
                ctx.new_path()
                ctx.arc(wv[1], wv[2], wv[4] + 110 * k, 0, 2 * math.pi)
                ctx.set_source_rgba(*wv[3], 0.8 * (1 - k))
                ctx.set_line_width(10 * (1 - k) + 2)
                ctx.stroke()
        # 弾(攻撃力が上がるほど大きく・赤く)
        bcol = [(1, 1, 0.9), (1, 0.9, 0.5), (1, 0.65, 0.35), (1, 0.4, 0.4)][fr["atk"] - 1]
        brad = BULLET_R * (1 + 0.15 * (fr["atk"] - 1))
        for bx, by, trail in fr["bullets"]:
            for j, (tx, ty) in enumerate(trail):
                a = (j + 1) / max(1, len(trail))
                ctx.new_path()
                ctx.arc(tx, ty, brad * (0.3 + 0.7 * a), 0, 2 * math.pi)
                ctx.set_source_rgba(*bcol, 0.3 * a)
                ctx.fill()
            ctx.new_path()
            ctx.arc(bx, by, brad * 1.8, 0, 2 * math.pi)
            ctx.set_source_rgba(*bcol, 0.3)
            ctx.fill()
            ctx.new_path()
            ctx.arc(bx, by, brad, 0, 2 * math.pi)
            ctx.set_source_rgb(*bcol)
            ctx.fill()
        for ix, iy, kind in fr["items"]:
            draw_item(ctx, ix, iy, kind, t)
        for k, (sx, svx) in enumerate(fr["ships"]):
            draw_ship(ctx, sx, svx, t, 1.0 if k == 0 else 0.8)
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
        for pu in popups:
            age = t - pu[0]
            if 0 <= age < 1.2 and not over:   # 決着後は結果の文字と重ならないよう出さない
                text(ctx, pu[3], min(max(pu[1], 220), W - 220), pu[2] - 70 * age, 60,
                     rgb=pu[4], sw=12, alpha=min(1, 2 * (1.2 - age)))
        for bn in banners:
            age = t - bn[0]
            if 0 <= age < 1.3:
                k = min(1, age / 0.15)
                text(ctx, bn[1], W / 2, 1090, 130 * (1.5 - 0.5 * k), rgb=bn[2], sw=20,
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
        text(ctx, f"{remain:05.2f}", W / 2, 495, 84 * pulse, rgb=tcol, sw=12)
        text(ctx, f"攻撃力×{fr['atk']}", 50, 495, 44, rgb=ITEM_COLOR["atk"], sw=10, align="left")
        text(ctx, f"弾×{fr['shots']}  機×{len(fr['ships'])}", W - 180, 495, 44, sw=10)
        if not over:
            text(ctx, "※失敗すると…アレが出ます", W / 2, 1570, 50, rgb=(1, 0.35, 0.35), sw=10)
        elif fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 1090, 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"ボスのHP あと{res['boss_hp']}", W / 2, 1220, 72, sw=12)
            text(ctx, "あと少しだったのに…", W / 2, 1570, 54, rgb=(0.9, 0.9, 0.95), sw=10)
        else:
            k = min(1.0, (t - end_t) / 0.25)
            text(ctx, "ボス撃破！", W / 2, 1090, 150 * (1.6 - 0.6 * k), rgb=GOLD, sw=20)
            text(ctx, f"残り{TIME_LIMIT - end_t:.2f}秒", W / 2, 1220, 80, sw=12)

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
MIX_GAIN = 0.86  # 通常部分の音量(約 -18dB になるよう調整)


def synth_audio(events, end_t, fail, duration, path):
    rng = np.random.default_rng(0)
    out = np.zeros(int((duration + 3) * SR))

    def add(sig, t0):
        i = int(t0 * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    note_i = 0
    last_tick = -1.0
    for kind, t, data in events:
        if kind == "fire":
            add(tone(midi_hz(MELODY[note_i % len(MELODY)]), 0.3, 0.28, 8), t)
            add(noise(0.05, 0.12, 60, rng, smooth=2), t)
            note_i += 1
        elif kind == "kill":
            big = data[4] == "boss"
            add(noise(1.2 if big else 0.4, 0.6 if big else 0.35, 4 if big else 9, rng, smooth=3), t)
            add(tone(50, 0.8 if big else 0.4, 0.6 if big else 0.35, 4), t)
        elif kind in ("hit", "boss_hit"):
            if t - last_tick > 0.06:
                add(tone(620, 0.08, 0.10, 40) + tone(930, 0.08, 0.06, 40), t)
                last_tick = t
        elif kind == "drop":
            add(tone(midi_hz(88), 0.25, 0.15, 8) + tone(midi_hz(95), 0.25, 0.10, 8), t)
        elif kind == "pickup":
            for k, m in enumerate((72, 76, 79, 84, 88)):
                add(tone(midi_hz(m), 0.3, 0.25, 6), t + k * 0.05)
        elif kind == "miss_item":
            add(tone(midi_hz(60), 0.35, 0.25, 5) + tone(midi_hz(55), 0.35, 0.2, 5), t)
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
