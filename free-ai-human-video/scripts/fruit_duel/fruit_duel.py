"""「りんごおじさんはスイカおじさんに勝てる?」円の中で跳ね回るおじさんフルーツ2人が、武器を拾って戦う物理ショート。

- 円の中を、りんごおじさんとスイカおじさん(ep24 と同じ AI 写真)が、重力なし・いつも同じ速さで跳ね回る(かべ・おたがいで弾性衝突)。
- ときどき円の中に武器が出てくる。先にふれたほうが拾い、しばらく使える(ねらいはしない。武器は決まった速さで回るか、進む向きを向くだけ):
    ピコピコハンマー … 持ち主のまわりをぐるぐる回り、当たると1ダメージ+ふっとばす
    巨大フォーク     … 持ち主の進む向きに突き出していて、先が当たると1ダメージ
    種マシンガン     … 持ち主のまわりをゆっくり回りながら、スイカの種を連射(当たると1ダメージ)
  どの武器も1回1ダメージ。当たったあと1秒は無敵(一気にハートが減らない)。当たると、おじさんが低い声で「おぅっ!」「ゔぅっ!」
- ハートは10個ずつ。先に0になったほうの負け。りんごおじさんが勝てば成功(おじさんフィーバー)、負ければ失敗(幽霊)。

使い方:
    python fruit_duel.py search [-n 200]
    python fruit_duel.py render --seed N
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

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "ball_escape"))
from ball_escape import midi_hz, text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from fail_bgm import fail_music  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "blade_split"))
import ojisan as OJ  # noqa: E402
import ojisan_voice as OV  # noqa: E402
import blade_fever as FV  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "giant_domino"))
import giant_domino as GD  # noqa: E402
sys.path.insert(0, HERE)
import grunt as GR  # noqa: E402   ダメージのうめき声

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

CX, CY, R = 540.0, 1090.0, 460.0
FR_R = 60.0                     # おじさんの当たりの大きさ(半径)
SPEED = float(os.environ.get("SPEED", 600.0))
HP0 = 10
KINDS = (0, 5)                  # りんご, スイカ(OJ.NAMES の番号)
NAMES = ("りんごおじさん", "スイカおじさん")
COLS = ((0.95, 0.2, 0.2), (0.25, 0.8, 0.3))
WEAPONS = ["hammer", "fork", "seeds"]   # (ブーメランは使わない)
W_NAMES = {"hammer": "ピコピコハンマー", "fork": "巨大フォーク", "seeds": "種マシンガン", "boomerang": "ブーメラン"}
W_DUR = {"hammer": 9.0, "fork": 9.0, "seeds": 7.0, "boomerang": 4.0}
SPAWN_WAIT = float(os.environ.get("SPAWN_WAIT", 0.2))   # 武器が拾われてから、次の武器が出てくるまで
ITEM_R = 34.0
OUTRO = 4.2
FORK_L = 160.0
HAM_R = 112.0
SEED_CD = float(os.environ.get("SEED_CD", 0.05))
INVULN = float(os.environ.get("INVULN", 1.0))   # 当たったあとの無敵時間(秒)   # 種マシンガンが種を出す間かく(秒)
KO_SHOW = 1.6


class Fighter:
    def __init__(self, i, pos, vel):
        self.i = i
        self.p = np.array(pos, float)
        self.v = np.array(vel, float)
        self.hp = HP0
        self.w = None           # 持っている武器 {type, until, ang, cd, ...}
        self.hit_t = -9.0
        self.rot = 0.0


class Game:
    def __init__(self, seed):
        rng = self.rng = np.random.default_rng(seed)
        self.f = []
        for i in range(2):
            a = rng.uniform(0, 2 * math.pi)
            d = rng.uniform(0, 2 * math.pi)
            pos = (CX + (-1 if i == 0 else 1) * 220 + rng.uniform(-40, 40), CY + rng.uniform(-150, 150))
            self.f.append(Fighter(i, pos, (SPEED * math.cos(d), SPEED * math.sin(d))))
        self.t = 0.0
        self.item = None        # (type, x, y, 出た時刻)
        self.next_item = 0.8
        self.order = list(rng.permutation(WEAPONS))
        self.seeds = []         # [x, y, vx, vy, 持ち主]
        self.events = []
        self.result, self.result_t, self.ko = None, None, None

    def spawn_item(self):
        rng = self.rng
        if not self.order:
            self.order = list(rng.permutation(WEAPONS))
        typ = self.order.pop()
        for _ in range(50):
            a = rng.uniform(0, 2 * math.pi)
            d = (R - 90) * math.sqrt(rng.uniform(0.05, 1))
            x, y = CX + d * math.cos(a), CY + d * math.sin(a)
            if all(np.hypot(x - f.p[0], y - f.p[1]) > 170 for f in self.f):
                break
        self.item = (typ, x, y, self.t)
        self.events.append(("spawn", self.t, typ))

    def damage(self, f, n, src, kb_dir, kb):
        if self.ko is not None or f.hp <= 0:
            return
        if self.t - f.hit_t < INVULN:   # 当たった直後は少しのあいだ無敵(一気にハートが減らないように)
            return
        n = 1                           # どの武器も1回1ダメージ
        f.hp = max(0, f.hp - n)
        f.hit_t = self.t
        f.v = f.v + kb_dir * kb
        self.events.append(("hit", self.t, (f.i, n, src, float(f.p[0]), float(f.p[1]))))
        if f.hp <= 0:
            self.ko = (f.i, self.t)
            self.events.append(("ko", self.t, f.i))

    def step(self, dt):
        self.t += dt
        fs = self.f
        if self.ko is None:
            # 動き(重力なし。ふっとばされて速くなっても、ゆっくりいつもの速さにもどる)
            for f in fs:
                f.p = f.p + f.v * dt
                n = np.linalg.norm(f.v)
                k = 1 - math.exp(-dt / 0.8)
                if n > 1e-6:
                    f.v = f.v * ((n + (SPEED - n) * k) / n)
                f.rot += dt * 1.2 * (1 if f.i == 0 else -1)
                d = f.p - (CX, CY)
                dist = np.linalg.norm(d)
                if dist > R - FR_R:   # かべで弾性反射
                    nrm = d / dist
                    f.p = np.array((CX, CY)) + nrm * (R - FR_R)
                    vn = np.dot(f.v, nrm)
                    if vn > 0:
                        f.v = f.v - 2 * vn * nrm
                        self.events.append(("wall", self.t, f.i))
            a, b = fs
            d = b.p - a.p
            dist = np.linalg.norm(d)
            if dist < 2 * FR_R and dist > 1e-6:   # おたがいに弾性衝突(同じ重さ)
                nrm = d / dist
                rel = np.dot(a.v - b.v, nrm)
                if rel > 0:
                    a.v = a.v - rel * nrm
                    b.v = b.v + rel * nrm
                    self.events.append(("bump", self.t, None))
                over = 2 * FR_R - dist
                a.p = a.p - nrm * over / 2
                b.p = b.p + nrm * over / 2
            # 武器を拾う
            if self.item is None and self.t >= self.next_item:
                self.spawn_item()
            if self.item is not None:
                typ, x, y, _ = self.item
                for f in fs:
                    if np.hypot(x - f.p[0], y - f.p[1]) < FR_R + ITEM_R:
                        self.pick(f, typ)
                        self.item = None
                        self.next_item = self.t + SPAWN_WAIT
                        break
            for f in fs:
                self.use_weapon(f, fs[1 - f.i], dt)
            # 種の弾
            keep = []
            for s in self.seeds:
                s[0] += s[2] * dt
                s[1] += s[3] * dt
                tgt = fs[1 - s[4]]
                if np.hypot(s[0] - tgt.p[0], s[1] - tgt.p[1]) < FR_R + 6:
                    dd = np.array((s[2], s[3]))
                    self.damage(tgt, 1, "seeds", dd / np.linalg.norm(dd), 140)
                    continue
                if np.hypot(s[0] - CX, s[1] - CY) > R:
                    continue
                keep.append(s)
            self.seeds = keep
        if self.result is None and self.ko is not None and self.t >= self.ko[1] + KO_SHOW:
            loser = self.ko[0]
            self.result = "success" if loser == 1 else "fail"
            self.result_t = self.t
            self.events.append((self.result, self.t, None))

    def pick(self, f, typ):
        w = {"type": typ, "until": self.t + W_DUR[typ], "ang": self.rng.uniform(0, 2 * math.pi), "cd": 0.0}
        if typ == "boomerang":   # 進む向きに投げる
            d = f.v / np.linalg.norm(f.v)
            w.update(bp=f.p + d * (FR_R + 20), bv=d * 900, phase="out", t0=self.t)
        f.w = w
        self.events.append(("pick", self.t, (f.i, typ)))

    def use_weapon(self, f, o, dt):
        w = f.w
        if w is None:
            return
        if self.t >= w["until"]:
            f.w = None
            self.events.append(("drop", self.t, f.i))
            return
        w["cd"] -= dt
        typ = w["type"]
        if typ == "hammer":   # まわりをぐるぐる回る
            w["ang"] += 7.0 * dt
            hx, hy = f.p[0] + HAM_R * math.cos(w["ang"]), f.p[1] + HAM_R * math.sin(w["ang"])
            if w["cd"] <= 0 and np.hypot(hx - o.p[0], hy - o.p[1]) < FR_R + 38:
                d = o.p - f.p
                self.damage(o, 1, "hammer", d / np.linalg.norm(d), 520)
                w["cd"] = 0.45
        elif typ == "fork":   # 進む向きに突き出す
            d = f.v / np.linalg.norm(f.v)
            w["ang"] = math.atan2(d[1], d[0])
            base, tip = f.p + d * FR_R, f.p + d * (FR_R + FORK_L)
            q = o.p - base
            u = max(0.0, min(1.0, np.dot(q, tip - base) / np.dot(tip - base, tip - base)))
            if w["cd"] <= 0 and np.linalg.norm(o.p - (base + u * (tip - base))) < FR_R + 8 and u > 0.45:
                self.damage(o, 2, "fork", d, 420)
                w["cd"] = 0.7
        elif typ == "seeds":  # ゆっくり回りながら連射
            w["ang"] += 2.4 * dt
            if w["cd"] <= 0:
                d = np.array((math.cos(w["ang"]), math.sin(w["ang"])))
                p0 = f.p + d * (FR_R + 34)
                self.seeds.append([p0[0], p0[1], d[0] * 900 + f.v[0] * 0.3, d[1] * 900 + f.v[1] * 0.3, f.i])
                w["cd"] = SEED_CD
                self.events.append(("shot", self.t, f.i))
        elif typ == "boomerang":
            w["ang"] += 18 * dt
            bp, bv = w["bp"], w["bv"]
            if w["phase"] == "out":
                bv = bv * (1 - 1.6 * dt)
                if np.linalg.norm(bv) < 120 or self.t - w["t0"] > 1.0:
                    w["phase"] = "back"
            else:   # 持ち主のところへもどる
                d = f.p - bp
                dist = np.linalg.norm(d)
                bv = bv + d / max(1, dist) * 2600 * dt
                sp = np.linalg.norm(bv)
                if sp > 1000:
                    bv = bv / sp * 1000
                if dist < FR_R + 10:
                    f.w = None
                    self.events.append(("catch", self.t, f.i))
                    return
            bp = bp + bv * dt
            dd = bp - (CX, CY)
            if np.linalg.norm(dd) > R - 20:   # かべではね返る
                nrm = dd / np.linalg.norm(dd)
                bp = np.array((CX, CY)) + nrm * (R - 20)
                vn = np.dot(bv, nrm)
                if vn > 0:
                    bv = bv - 2 * vn * nrm
            w["bp"], w["bv"] = bp, bv
            if w["cd"] <= 0 and np.hypot(bp[0] - o.p[0], bp[1] - o.p[1]) < FR_R + 26:
                dv = bv / max(1e-6, np.linalg.norm(bv))
                self.damage(o, 2, "boomerang", dv, 450)
                w["cd"] = 0.5


def snapshot(g):
    return {"t": g.t,
            "f": [(f.p[0], f.p[1], f.rot, f.hp, f.hit_t,
                   None if f.w is None else (f.w["type"], f.w["ang"], tuple(f.w.get("bp", (0, 0))), tuple(f.v / max(1e-6, np.linalg.norm(f.v)))))
                  for f in g.f],
            "item": g.item, "seeds": [(s[0], s[1], s[4], s[2], s[3]) for s in g.seeds]}


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append(snapshot(g))
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else FV.DURATION
            if not record or g.t > g.result_t + extra:
                break
        if g.t > 120:
            break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "ko": g.ko,
            "hp": [f.hp for f in g.f]}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["ko"] and round(r["ko"][1], 1), r["hp"]


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 りんごの勝ち {sum(r[1] == 'success' for r in rs)} 件")
    ts = sorted(r[2] for r in rs if r[2])
    print("決着の時間:", ts[:3], "…", ts[len(ts) // 2], "…", ts[-3:])
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
BG = (0.04, 0.06, 0.12)


def draw_heart(ctx, x, y, s, col, full):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s / 20, s / 20)
    ctx.move_to(0, 6)
    ctx.curve_to(-14, -4, -10, -16, 0, -8)
    ctx.curve_to(10, -16, 14, -4, 0, 6)
    ctx.close_path()
    if full:
        ctx.set_source_rgb(*col)
        ctx.fill_preserve()
    ctx.set_source_rgba(*col, 0.9)
    ctx.set_line_width(1.6)
    ctx.stroke()
    ctx.restore()


def draw_hammer(ctx, x, y, ang, s=1.0):
    """ピコピコハンマー(赤い頭・黄色いふち・持ち手)。"""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.scale(s, s)
    ctx.rectangle(-58, -5, 50, 10)          # 持ち手(持ち主のほうへのびる)
    ctx.set_source_rgb(0.95, 0.85, 0.3)
    ctx.fill()
    ctx.rectangle(-16, -26, 32, 52)
    g = cairo.LinearGradient(-16, 0, 16, 0)
    g.add_color_stop_rgb(0, 1.0, 0.35, 0.35)
    g.add_color_stop_rgb(1, 0.75, 0.1, 0.1)
    ctx.set_source(g)
    ctx.fill()
    for yy in (-26, 18):
        ctx.rectangle(-17, yy, 34, 8)
        ctx.set_source_rgb(1.0, 0.9, 0.2)
        ctx.fill()
    ctx.restore()


def draw_fork(ctx, x, y, ang, L=FORK_L):
    """巨大フォーク(銀色・4本の先)。x, y は持ち主の中心。"""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    g = cairo.LinearGradient(0, -8, 0, 8)
    g.add_color_stop_rgb(0, 0.95, 0.96, 1.0)
    g.add_color_stop_rgb(1, 0.55, 0.58, 0.65)
    ctx.set_source(g)
    ctx.rectangle(FR_R - 30, -5, L * 0.55 + 30, 10)
    ctx.fill()
    x0 = FR_R + L * 0.55
    ctx.move_to(x0, -6)
    ctx.curve_to(x0 + 10, -22, x0 + 18, -22, x0 + 22, -22)
    ctx.line_to(x0 + 22, 22)
    ctx.curve_to(x0 + 18, 22, x0 + 10, 22, x0, 6)
    ctx.close_path()
    ctx.fill()
    for yy in (-19, -7, 5, 17):
        ctx.rectangle(x0 + 20, yy - 2, FR_R + L - x0 - 20, 5)
        ctx.fill()
    ctx.restore()


def draw_seedgun(ctx, x, y, ang):
    """種マシンガン(スイカ色の筒)。"""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.rectangle(FR_R - 10, -13, 52, 26)
    g = cairo.LinearGradient(0, -13, 0, 13)
    g.add_color_stop_rgb(0, 0.35, 0.85, 0.35)
    g.add_color_stop_rgb(1, 0.1, 0.45, 0.12)
    ctx.set_source(g)
    ctx.fill()
    for k in range(3):
        ctx.rectangle(FR_R - 4 + k * 16, -13, 6, 26)
        ctx.set_source_rgba(0.05, 0.3, 0.08, 0.8)
        ctx.fill()
    ctx.rectangle(FR_R + 42, -8, 12, 16)
    ctx.set_source_rgb(0.95, 0.35, 0.4)
    ctx.fill()
    ctx.restore()


def draw_seed(ctx, x, y, ang, vx=0.0, vy=0.0, col=(1, 1, 1)):
    """スイカの種の弾(暗い背景でも見えるように、白いふち・光・うしろに残像)。"""
    sp = math.hypot(vx, vy) or 1.0
    ux, uy = vx / sp, vy / sp
    ctx.save()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(x - ux * 46, y - uy * 46)   # 残像の線
    ctx.line_to(x, y)
    ctx.set_source_rgba(*col, 0.45)
    ctx.set_line_width(9)
    ctx.stroke()
    ctx.translate(x, y)
    ctx.rotate(math.atan2(uy, ux))
    ctx.scale(1.0, 0.62)
    ctx.arc(0, 0, 15, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.1, 0.07, 0.05)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.95)
    ctx.set_line_width(2.5)
    ctx.stroke()
    ctx.arc(x - ux * 4 - 3, y - uy * 4 - 3, 3.5, 0, 2 * math.pi)
    ctx.set_source_rgba(1, 1, 1, 0.8)
    ctx.fill()


def draw_boomerang(ctx, x, y, ang, s=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.scale(s, s)
    ctx.move_to(-30, -22)
    ctx.curve_to(-6, -10, 0, -4, 6, 0)
    ctx.curve_to(0, 4, -6, 10, -30, 22)
    ctx.curve_to(-20, 8, -14, 4, -12, 0)
    ctx.curve_to(-14, -4, -20, -8, -30, -22)
    ctx.close_path()
    ctx.set_source_rgb(1.0, 0.6, 0.15)
    ctx.fill_preserve()
    ctx.set_source_rgb(0.5, 0.25, 0.05)
    ctx.set_line_width(2.5)
    ctx.stroke()
    ctx.restore()


def draw_item_icon(ctx, typ, x, y, t):
    ctx.save()
    ctx.translate(x, y)
    if typ == "hammer":
        draw_hammer(ctx, 10, 0, -0.6 + 0.2 * math.sin(t * 3), 0.8)
    elif typ == "fork":
        ctx.scale(0.55, 0.55)
        draw_fork(ctx, -FR_R - 60, 0, 0, 120)
    elif typ == "seeds":
        draw_seedgun(ctx, -FR_R - 22, 0, 0)
    else:
        draw_boomerang(ctx, 8, 0, t * 4, 0.9)
    ctx.restore()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    ko_i, ko_t = res["ko"]
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"fruit_duel_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"fruit_duel_{seed}.wav")
    final = os.path.join(OUT_DIR, f"fruit_duel_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"fd_preview_{pt:.1f}.png"))
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
    hp_win = res["hp"][1 - ko_i]
    ending = None if fail else FV.FruitFever(W, H, seed, CX, CY, main="りんごの勝利!!", count=f"のこりハート {hp_win} / {HP0}",
                                                  sub="WINNER")
    rng = np.random.default_rng(seed + 9)
    pops = []      # ダメージの数字 [x, y, 文字, 色, 出た時刻]
    sparks = []
    labels = []    # 武器を拾った文字
    shake = 0.0
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "hit":
                i, n, src, x, y = data
                pops.append([x, y - 60, f"-{n}", COLS[1 - i], et])
                for _ in range(14):
                    a = rng.uniform(0, 2 * math.pi)
                    v = rng.uniform(150, 520)
                    sparks.append([x, y, v * math.cos(a), v * math.sin(a), et, COLS[i]])
                shake = max(shake, 9 if n == 1 else 15)
            elif kind == "pick":
                i, typ = data
                labels.append((f"{NAMES[i]}が{W_NAMES[typ]}をゲット!", COLS[i], et))
            elif kind == "ko":
                shake = 30
                x, y = fr["f"][data][0], fr["f"][data][1]
                for _ in range(60):
                    a = rng.uniform(0, 2 * math.pi)
                    v = rng.uniform(200, 900)
                    sparks.append([x, y, v * math.cos(a), v * math.sin(a), et, COLS[data]])
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        if ending is not None and over:
            ending.draw(surf, ctx, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - SCARE_DUR) if over else 0
        shake *= 0.86
        ctx.set_source_rgb(*BG)
        ctx.paint()
        ctx.set_source_rgba(0.3, 0.4, 0.6, 0.12)   # うすいマス目
        ctx.set_line_width(1)
        for x in range(0, W, 54):
            ctx.move_to(x, 0)
            ctx.line_to(x, H)
        for y in range(0, H, 54):
            ctx.move_to(0, y)
            ctx.line_to(W, y)
        ctx.stroke()
        ctx.save()
        if shake > 0.5:
            ctx.translate(math.sin(t * 61) * shake, math.cos(t * 47) * shake)
        g = cairo.RadialGradient(CX, CY, 50, CX, CY, R)
        g.add_color_stop_rgba(0, 0.1, 0.13, 0.25, 0.9)
        g.add_color_stop_rgba(1, 0.05, 0.07, 0.15, 0.9)
        ctx.set_source(g)
        ctx.arc(CX, CY, R, 0, 2 * math.pi)
        ctx.fill()
        for wdt, a in ((26, 0.08), (12, 0.2), (5, 0.95)):
            ctx.arc(CX, CY, R + 6, 0, 2 * math.pi)
            ctx.set_source_rgba(0.6, 0.75, 1.0, a)
            ctx.set_line_width(wdt)
            ctx.stroke()
        # 武器のアイテム
        if fr["item"] is not None:
            typ, x, y, t0 = fr["item"]
            k = min(1.0, (t - t0) / 0.25)
            ctx.arc(x, y, (ITEM_R + 10) * (0.6 + 0.4 * k), 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, 0.12)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.8, 0.9, 1.0, 0.9)
            ctx.set_line_width(4)
            ctx.stroke()
            ctx.arc(x, y, (ITEM_R + 10) * (0.6 + 0.4 * k), t * 3, t * 3 + 1.2)
            ctx.set_source_rgba(1, 1, 1, 0.9)
            ctx.set_line_width(6)
            ctx.stroke()
            draw_item_icon(ctx, typ, x, y, t)
        for x, y, i, vx, vy in fr["seeds"]:
            draw_seed(ctx, x, y, t * 20, vx, vy, COLS[i])
        # おじさんと武器
        for i, (x, y, rot, hp, hit_t, w) in enumerate(fr["f"]):
            if ko_t is not None and t >= ko_t and i == ko_i:
                a = t - ko_t
                if a < 0.6:   # 負けたほうは、ふくらんで、はじける
                    s = 1 + a * 0.8
                    ctx.save()
                    ctx.translate(x, y)
                    ctx.scale(s, s)
                    OJ.draw_fruit(ctx, KINDS[i], 0, 0, FR_R * 1.3, rot, alpha=1 - a / 0.6)
                    ctx.restore()
                continue
            if w is not None:
                typ, ang, bp, vd = w
                if typ == "hammer":
                    draw_hammer(ctx, x + HAM_R * math.cos(ang), y + HAM_R * math.sin(ang), ang, 1.2)
                elif typ == "fork":
                    draw_fork(ctx, x, y, ang)
                elif typ == "seeds":
                    draw_seedgun(ctx, x, y, ang)
                elif typ == "boomerang":
                    draw_boomerang(ctx, bp[0], bp[1], ang)
            a = t - hit_t
            sq = 1 - 0.25 * math.exp(-a * 12) * math.cos(a * 40) if a < 0.4 else 1.0
            ctx.save()
            ctx.translate(x, y)
            ctx.scale(2 - sq, sq)
            OJ.draw_fruit(ctx, KINDS[i], 0, 0, FR_R * 1.3, rot)
            if a < 0.25:   # 当たった瞬間、赤く光る
                ctx.arc(0, 0, FR_R * 1.15, 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.1, 0.1, 0.5 * (1 - a / 0.25))
                ctx.fill()
            ctx.restore()
        keep = []
        for s in sparks:
            a = t - s[4]
            if a < 0.6:
                ctx.arc(s[0] + s[2] * a, s[1] + s[3] * a, 6 * (1 - a / 0.6) + 1, 0, 2 * math.pi)
                ctx.set_source_rgba(*s[5], 1 - a / 0.6)
                ctx.fill()
                keep.append(s)
        sparks = keep
        keep = []
        for p_ in pops:
            a = t - p_[4]
            if a < 0.9:
                text(ctx, p_[2], p_[0], p_[1] - 70 * a, 64, rgb=p_[3], sw=10)
                keep.append(p_)
        pops = keep
        ctx.restore()
        # 上のハート
        for i in range(2):
            y0 = 120 + i * 92
            hp = fr["f"][i][3]
            OJ.draw_fruit(ctx, KINDS[i], 80, y0, 38, 0)
            for k in range(HP0):
                draw_heart(ctx, 150 + k * 86, y0, 34, COLS[i], k < hp)
        text(ctx, "りんごおじさん", W / 2 - 270, 345, 52, rgb=COLS[0], sw=10)
        text(ctx, "VS", W / 2, 345, 60, rgb=(1, 1, 1), sw=10)
        text(ctx, "スイカおじさん", W / 2 + 270, 345, 52, rgb=COLS[1], sw=10)
        text(ctx, "りんごが勝てば成功！", W / 2, 440, 70, rgb=GOLD, sw=12)   # 成功の条件のテロップ
        labels = [l_ for l_ in labels if t - l_[2] < 1.4]
        for j, (s_, col, t0) in enumerate(labels[-2:]):
            k2 = min(1.0, (t - t0) / 0.12)
            text(ctx, s_, W / 2, 530 + 56 * j, 42 * (1.2 - 0.2 * k2), rgb=col, sw=8)
        if ko_t is not None and t >= ko_t:
            k2 = min(1.0, (t - ko_t) / 0.15)
            text(ctx, "K.O.!!", W / 2, 1000, 170 * (1.4 - 0.4 * k2), rgb=GOLD, sw=24)
        text(ctx, "どっちが勝つ？", W / 2, 1700, 80, rgb=(1, 1, 1), sw=12)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "りんごおじさんの負け…", W / 2, 900, 96 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=18)
            text(ctx, "スイカおじさんの勝ち", W / 2, 1030, 70, rgb=COLS[1], sw=12)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} ハート {res['hp']} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def sq_wave(f, d, amp, duty=0.5):
    t = _t(d)
    y = np.where((t * f) % 1 < duty, 1.0, -1.0)
    return amp * y * np.minimum(1, t / 0.005) * np.exp(-t * 4)


def kick(amp):
    t = _t(0.25)
    return amp * np.sin(2 * np.pi * (50 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 12)


def snare(seed, amp):
    t = _t(0.15)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    return amp * (0.8 * n * np.exp(-t * 30) + 0.4 * np.sin(2 * np.pi * 200 * t) * np.exp(-t * 35))


def hat(seed, amp):
    t = _t(0.05)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    return amp * (n - np.convolve(n, np.ones(3) / 3, "same")) * np.exp(-t * 80)


def battle_bgm(dur):
    """戦いのBGM(このプログラムで作ったオリジナル。テンポ150・ラ短調)。"""
    beat = 60 / 150
    out = np.zeros(int((dur + 2) * SR))

    def put(sig, t0, g=1.0):
        i = int(t0 * SR)
        j = min(len(out), i + len(sig))
        if i < len(out):
            out[i:j] += g * sig[: j - i]
    roots = [45, 45, 41, 43]   # Am Am F G
    riff = [69, 72, 76, 72, 74, 72, 69, 67, 69, 72, 76, 79, 76, 74, 72, 74,
            69, 72, 76, 72, 74, 76, 77, 76, 74, 72, 71, 72, 74, 71, 67, 71]
    t = 0.0
    bar = 0
    while t < dur:
        r = roots[bar % 4]
        for b in range(4):
            tb = t + b * beat
            put(kick(0.9), tb) if b in (0, 2) else put(snare(int(tb * 100), 0.5), tb)
            for h in range(2):
                put(hat(int(tb * 1000) + h, 0.25), tb + h * beat / 2)
                put(sq_wave(midi_hz(r - 12 + (0 if h == 0 else 12)), beat / 2 * 0.9, 0.18, 0.5), tb + h * beat / 2)
        for k in range(8):
            m = riff[(bar % 4) * 8 + k]
            put(sq_wave(midi_hz(m), beat / 2 * 0.85, 0.11, 0.25), t + k * beat / 2)
        t += 4 * beat
        bar += 1
    return out[: int(dur * SR)]


def piko(amp):
    t = _t(0.18)
    f = 1800 * np.exp(-t * 8) + 600
    return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)


def stab(seed, amp):
    t = _t(0.25)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    return amp * (0.6 * n * np.exp(-t * 25) + 0.6 * np.sin(2 * np.pi * 900 * t) * np.exp(-t * 20))


def pop_s(amp, f=700):
    t = _t(0.06)
    return amp * np.sin(2 * np.pi * f * t * (1 + 2 * t)) * np.exp(-t * 60)


def kyuin(amp):
    t = _t(0.35)
    f = 500 + 1800 * t / 0.35
    return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.35)


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    ko_i, ko_t = res["ko"]
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)

    def add(sig, t0, gain=1.0, buf=None):
        b = out if buf is None else buf
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out and j > i:
            b[i:j] += gain * sig[: j - i]
    voices = []
    for k in KINDS:
        v = OV.voice(k, SR)
        voices.append(v / np.sqrt(np.mean(v ** 2)) * 0.22)
    bgm = battle_bgm(ko_t)
    fade = np.minimum(1, (len(bgm) - np.arange(len(bgm))) / (0.3 * SR))
    add(bgm * fade, 0.0, 0.55, extra)   # BGMは決着の瞬間に止まる
    last_shot = -1
    n_grunt = [0, 0]
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.02:
            continue
        if kind == "hit":
            i, n, src, x, y = data
            n_grunt[i] += 1   # 当たったおじさんが、渋くて低い声で「おぅっ!」「ゔぅっ!」
            add(GR.grunt(n_grunt[i] * 2 + i, SR, 0.74 if i == 0 else 0.66), t + 0.02, 1.6)
            if src == "hammer":
                add(piko(0.9), t)
            elif src == "seeds":
                add(pop_s(0.7, 500), t)
            else:
                add(stab(int(t * 100), 0.9), t)
            add(GD.click(80, int(t * 1000)), t, 0.6)
        elif kind == "shot":
            if t - last_shot > 0.05:
                add(pop_s(0.25, 1100), t)
                last_shot = t
        elif kind == "pick":
            i, typ = data
            add(kyuin(0.5), t)
            add(voices[i], t + 0.05, 0.75)   # 拾ったおじさんが自分の名前をさけぶ
        elif kind == "wall":
            add(pop_s(0.12, 300), t)
        elif kind == "bump":
            add(pop_s(0.35, 250), t)
        elif kind == "ko":
            add(GD.timpani(1.0, 1.8), t)
            add(GD.click(300, 7), t, 1.4)
            add(voices[1 - data], t + 0.5, 1.3)   # 勝ったおじさんが名前をさけぶ
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
        sig = fail_music(SR, OUTRO)
        i0 = int((end_t + SCARE_DUR) * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += 0.6 * sig[:m]
    elif end_t is not None:
        add(FV.music(SR).mean(axis=1) * 1.6, end_t, 1.0, extra)
    wet = out.copy()
    for dd, g in ((0.047, 0.25), (0.079, 0.18)):
        k = int(dd * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)] + extra[: int(duration * SR)] * 0   # BGMはあとで足す
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    mix = wet + extra[: len(wet)] * 0.0
    bgm_part = np.zeros(len(wet))
    bgm_part[: min(len(bgm), len(wet))] = (bgm * fade)[: len(wet)]
    mix = wet + 0.35 * bgm_part / max(1e-9, np.sqrt(np.mean(bgm ** 2))) * 0.12
    body = mix[: int((ko_t + KO_SHOW) * SR)]
    rms = np.sqrt(np.mean(body ** 2))
    if rms > 0:
        mix *= min(4.0, 10 ** (-14.0 / 20) / rms)
    tail = extra[: len(mix)].copy()
    tail[: int(ko_t * SR) + 1] = 0   # (BGMはすでに mix に入っている)
    mix = mix + (0.95 if fail else 1.0) * tail
    mag = np.abs(mix)
    mix = np.where(mag < 0.7, mix, np.sign(mix) * (0.7 + 0.2 * np.tanh((mag - 0.7) / 0.2)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("-n", type=int, default=100)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
