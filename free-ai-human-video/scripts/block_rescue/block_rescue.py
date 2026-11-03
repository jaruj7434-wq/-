"""「閉じこめられた仲間を助け出せる?」回転するブロックのリングを、まるくなった四角い頭のキャラで壊していく物理ショートを生成する。

- 画面の真ん中のオリに仲間が閉じこめられている。まわりを8重のブロックのリングが互い違いに回転している。
  外側から 土 → 木 → 石 → 銅 → 鉄 → 金 → ダイヤ → 黒い最強合金 の順で、内側ほど硬い(ドット絵はすべてオリジナル)。
- キャラ(四角い頭のオリジナルのドット絵キャラ)は上から次々に入ってきて、真ん中に引っぱられる(中心への重力)。
  ブロックに強く当たるたびにダメージ。回転するリングにはじかれて横へ流されたりもする(ねらい・補正なし)。
- 壊したブロックの数でツルハシが強くなる(素手 → 木 → 石 → 鉄 → ダイヤ)。宝箱ブロックを壊すとキャラが2人増える。
- ブロックを壊すたびに「天国と地獄」(オッフェンバック・パブリックドメイン)が1音ずつ本来のテンポで進む(ピコピコ音)。
- キャラは当たるたびに体力を使い、体力がなくなるか、しばらく何も壊せないと消える。
制限時間内にキャラが仲間のオリにたどり着けば成功(天使)、時間切れなら失敗(幽霊)。

使い方:
    python block_rescue.py search [--want fail|success] [-n 200]
    python block_rescue.py render --seed N
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
SUBSTEPS = 4
SR = 48000

CX, CY = 540.0, 1060.0      # 中心(オリ)
R_WALL = 500.0              # 外側のかべ
CAGE_R = 62.0
BS = 36.0                   # ブロックの大きさ
RING_R0, RING_DR = 120.0, 40.0
G_CENTER = float(os.environ.get("G_CENTER", 900.0))   # 中心への重力
HERO_R = 21.0
HERO_E = float(os.environ.get("HERO_E", 0.85))   # キャラの弾み
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 40.0))
SPAWN_DT = float(os.environ.get("SPAWN_DT", 2.3))     # 新しいキャラが入ってくる間隔
STAMINA = int(os.environ.get("STAMINA", 14))               # キャラの体力(強く当たれる回数)
IDLE_FADE = float(os.environ.get("IDLE_FADE", 3.0))            # これだけ何も壊せない(ダメージを与えない)と消える
V_MIN = float(os.environ.get("V_MIN", 100.0))              # これより弱い当たりはダメージなし
MAX_HEROES = 12
HPK = float(os.environ.get("HPK", 0.6))                # ブロックのかたさの倍率
OUTRO = 2.5

# 素材:名前, かたさ, 色(ベース), 色(模様)
MATS = [
    ("土", 1, (0.53, 0.36, 0.22), (0.40, 0.26, 0.15)),
    ("木", 2, (0.72, 0.53, 0.30), (0.55, 0.38, 0.20)),
    ("石", 4, (0.52, 0.52, 0.52), (0.38, 0.38, 0.40)),
    ("銅", 6, (0.80, 0.47, 0.30), (0.33, 0.62, 0.52)),
    ("鉄", 9, (0.84, 0.84, 0.86), (0.62, 0.62, 0.66)),
    ("金", 12, (0.98, 0.82, 0.22), (0.86, 0.60, 0.10)),
    ("ダイヤ", 16, (0.42, 0.90, 0.90), (0.20, 0.62, 0.70)),
    ("最強合金", 22, (0.24, 0.21, 0.22), (0.38, 0.32, 0.30)),
]
NR = len(MATS)
# ツルハシ:必要な破壊数, 名前, ダメージ, 色
PICKS = [(0, "素手", 1, (0.95, 0.75, 0.6)), (8, "木", 2, (0.72, 0.53, 0.30)), (22, "石", 3, (0.55, 0.55, 0.55)),
         (45, "鉄", 5, (0.85, 0.85, 0.88)), (80, "ダイヤ", 8, (0.42, 0.90, 0.90))]

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")

T_HERO, T_BLOCK, T_CAGE, T_WALL = 1, 2, 3, 4


def ring_radius(k):
    """k=0 が一番外側(土)。"""
    return RING_R0 + RING_DR * (NR - 1 - k)


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        self.rng = rng
        sp = pymunk.Space()
        sp.gravity = (0, 0)
        sp.iterations = 20
        self.space = sp
        # 外側のかべ
        n = 96
        pts = [(CX + R_WALL * math.cos(2 * math.pi * i / n), CY + R_WALL * math.sin(2 * math.pi * i / n)) for i in range(n)]
        for i in range(n):
            s = pymunk.Segment(sp.static_body, pts[i], pts[(i + 1) % n], 4)
            s.elasticity, s.friction = 0.6, 0.4
            s.collision_type = T_WALL
            sp.add(s)
        cage = pymunk.Circle(sp.static_body, CAGE_R, (CX, CY))
        cage.collision_type = T_CAGE
        sp.add(cage)
        # ブロックのリング
        self.rings, self.blocks, self.block_of = [], [], {}
        for k in range(NR):
            r = ring_radius(k)
            body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            body.position = (CX, CY)
            sgn = 1 if (k % 2 == 0) else -1
            if rng.uniform() < 0.5:
                sgn = -sgn
            body.angular_velocity = sgn * rng.uniform(0.25, 0.6)
            sp.add(body)
            self.rings.append(body)
            m = int(round(2 * math.pi * r / RING_DR))
            chest = set(rng.choice(m, 1, replace=False)) if 1 <= k <= 5 else set()
            for j in range(m):
                th = 2 * math.pi * j / m
                c, s_ = math.cos(th), math.sin(th)
                half = BS / 2
                verts = [((r + dx) * c - dy * s_, (r + dx) * s_ + dy * c)
                         for dx, dy in ((-half, -half), (half, -half), (half, half), (-half, half))]
                sh = pymunk.Poly(body, verts)
                sh.elasticity, sh.friction = 0.55, 0.5
                sh.collision_type = T_BLOCK
                sp.add(sh)
                hp = max(1, round(MATS[k][1] * HPK))
                blk = {"ring": k, "th": th, "hp": hp, "hp0": hp, "shape": sh, "alive": True,
                       "chest": j in chest, "id": len(self.blocks)}
                self.block_of[sh] = blk
                self.blocks.append(blk)
        self.heroes = []
        self.hero_of = {}
        self.broken = 0
        self.events = []
        self.t = 0.0
        self.result, self.result_t = None, None
        self.next_spawn = 0.0
        self.to_remove = []
        self.pending_spawn = []
        self.n_spawned = 0
        sp.on_collision(T_HERO, T_BLOCK, begin=self.on_block)
        sp.on_collision(T_HERO, T_CAGE, begin=self.on_cage)

    def pick(self):
        p = PICKS[0]
        for q in PICKS:
            if self.broken >= q[0]:
                p = q
        return p

    def spawn(self, x=None, y=None, v=None):
        if sum(h["alive"] for h in self.heroes) >= MAX_HEROES:
            return
        b = pymunk.Body(1.0, pymunk.moment_for_circle(1.0, 0, HERO_R))
        if x is None:
            x, y = CX + self.rng.uniform(-60, 60), CY - R_WALL + HERO_R + 12
            v = (self.rng.uniform(-120, 120), 60)
        b.position = (x, y)
        b.velocity = v
        b.angular_velocity = self.rng.uniform(-3, 3)

        def vf(body, gravity, damping, dt):
            d = pymunk.Vec2d(CX, CY) - body.position
            dist = max(1.0, d.length)
            pymunk.Body.update_velocity(body, d / dist * G_CENTER, 0.9995, dt)
        b.velocity_func = vf
        s = pymunk.Circle(b, HERO_R)
        s.elasticity, s.friction = HERO_E, 0.6
        s.collision_type = T_HERO
        self.space.add(b, s)
        hero = {"body": b, "shape": s, "alive": True, "stam": STAMINA, "last_dmg": self.t, "born": self.t,
                "dead_t": None, "id": self.n_spawned, "trail": []}
        self.n_spawned += 1
        self.heroes.append(hero)
        self.hero_of[s] = hero
        self.events.append(("spawn", self.t, hero["id"]))

    def on_block(self, arb, space, data):
        hs, bs = arb.shapes
        if hs.collision_type != T_HERO:
            hs, bs = bs, hs
        hero, blk = self.hero_of.get(hs), self.block_of.get(bs)
        if hero is None or blk is None or not blk["alive"] or not hero["alive"]:
            return
        p = arb.contact_point_set.points[0].point_a if arb.contact_point_set.points else hs.body.position
        ring = self.rings[blk["ring"]]
        r = pymunk.Vec2d(p[0] - CX, p[1] - CY)
        vb = pymunk.Vec2d(-ring.angular_velocity * r.y, ring.angular_velocity * r.x)
        vrel = hs.body.velocity - vb
        vn = abs(vrel.dot(arb.normal))
        if vn < V_MIN:
            return
        dmg = self.pick()[2]
        blk["hp"] -= dmg
        hero["stam"] -= 1
        hero["last_dmg"] = self.t
        if blk["hp"] <= 0:
            blk["alive"] = False
            blk["break_t"] = self.t
            self.broken += 1
            self.to_remove.append(bs)
            self.events.append(("break", self.t, blk["id"]))
            if blk["chest"]:   # 宝箱:キャラが2人増える
                pos = hs.body.position
                for sgn in (-1, 1):
                    self.pending_spawn.append((pos.x + sgn * 10, pos.y, (sgn * 220, -150)))
                self.events.append(("chest", self.t, blk["id"]))
            old = self.pick()
            if PICKS.index(old) > 0 and self.broken == old[0]:
                self.events.append(("pick", self.t, PICKS.index(old)))
        else:
            self.events.append(("hit", self.t, blk["id"]))

    def on_cage(self, arb, space, data):
        if self.result is None:
            self.result, self.result_t = "success", self.t
            self.events.append(("rescue", self.t, None))

    def step(self, dt):
        self.t += dt
        if self.result is None and self.t >= self.next_spawn and self.t < TIME_LIMIT - 1.0:
            self.spawn()
            self.next_spawn += SPAWN_DT
        for x, y, v in self.pending_spawn:
            self.spawn(x, y, v)
        self.pending_spawn = []
        self.space.step(dt)
        for sh in self.to_remove:
            if sh in self.space.shapes:
                self.space.remove(sh)
        self.to_remove = []
        for h in self.heroes:
            if h["alive"] and (h["stam"] <= 0 or self.t - h["last_dmg"] > IDLE_FADE):
                h["alive"] = False   # 力つきて消える
                h["dead_t"] = self.t
                h["dead_pos"] = tuple(h["body"].position)
                h["dead_ang"] = h["body"].angle
                self.space.remove(h["body"], h["shape"])
                self.events.append(("fade", self.t, h["id"]))
        if self.result is None and self.t >= TIME_LIMIT:
            self.result, self.result_t = "fail", TIME_LIMIT
            self.events.append(("timeup", self.t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
            if g.result is not None and not record:
                break
        if record:
            frames.append({
                "t": g.t,
                "rings": [b.angle for b in g.rings],
                "heroes": [(h["id"], h["body"].position.x, h["body"].position.y, h["body"].angle, h["stam"])
                           for h in g.heroes if h["alive"]],
                "broken": g.broken,
                "alive": sum(h["alive"] for h in g.heroes),
            })
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
    deepest = max([b["ring"] for b in g.blocks if not b["alive"]], default=-1)
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "broken": g.broken, "deepest": deepest,
            "blocks": [{"ring": b["ring"], "th": b["th"], "hp0": b["hp0"], "chest": b["chest"],
                        "break_t": b.get("break_t")} for b in g.blocks],
            "heroes": [{"id": h["id"], "born": h["born"], "dead_t": h["dead_t"], "dead_pos": h.get("dead_pos"),
                        "dead_ang": h.get("dead_ang")} for h in g.heroes]}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["deepest"], r["broken"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "fail":
        for seed, _, rt, d, b in sorted([r for r in rs if r[1] == "fail"], key=lambda r: -r[3])[:15]:
            print(f"seed={seed:4d}  {d + 1}/{NR} 層目まで  壊した {b} 個")
    else:
        for seed, _, rt, d, b in sorted(succ, key=lambda r: -r[2])[:15]:
            print(f"seed={seed:4d}  救出 {rt:5.2f}秒  壊した {b} 個")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)


def block_tex(k, rng, chest=False):
    """8×8 ドットのブロック(素材ごとのオリジナルの模様)。"""
    name, _, base, pat = MATS[k]
    px = BS / 8
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(BS), int(BS))
    c = cairo.Context(surf)
    for i in range(8):
        for j in range(8):
            col = base
            v = rng.uniform(-0.06, 0.06)
            if name == "土":
                if rng.uniform() < 0.3:
                    col = pat
            elif name == "木":   # 横じまの板
                if j in (2, 5) or (j in (0, 3, 6) and i in (3,)):
                    col = pat
            elif name == "石":
                if rng.uniform() < 0.35:
                    col = pat
            elif name == "銅":   # ところどころ青緑のさび
                if rng.uniform() < 0.22:
                    col = pat
            elif name == "鉄":   # 板を重ねた形
                if j in (0, 7) or i in (0, 7):
                    col = pat
                elif j == 3:
                    col = (0.95, 0.95, 0.97)
            elif name == "金":
                if j in (0, 7) or i in (0, 7):
                    col = pat
                elif (i + j) % 5 == 0:
                    col = (1, 0.95, 0.6)
            elif name == "ダイヤ":   # 宝石の光
                if j in (0, 7) or i in (0, 7):
                    col = pat
                elif (i, j) in ((2, 2), (3, 2), (2, 3), (5, 5), (4, 5), (5, 4)):
                    col = (0.9, 1, 1)
            else:   # 最強合金:黒い板に赤茶のすじ
                if j in (1, 4, 6) and rng.uniform() < 0.6:
                    col = pat
            c.rectangle(i * px, j * px, px + 0.5, px + 0.5)
            c.set_source_rgb(*[min(1, max(0, x + v)) for x in col])
            c.fill()
    if chest:   # 宝箱の絵
        c.rectangle(px * 1, px * 2, px * 6, px * 5)
        c.set_source_rgb(0.62, 0.38, 0.14)
        c.fill()
        c.rectangle(px * 1, px * 3.6, px * 6, px * 0.8)
        c.set_source_rgb(0.35, 0.2, 0.08)
        c.fill()
        c.rectangle(px * 3.4, px * 3.3, px * 1.2, px * 1.6)
        c.set_source_rgb(1, 0.85, 0.2)
        c.fill()
    c.rectangle(0, 0, BS, BS)
    c.set_source_rgba(0, 0, 0, 0.35)
    c.set_line_width(2)
    c.stroke()
    return surf


HAIR = [(0.85, 0.35, 0.10), (0.15, 0.10, 0.08), (0.95, 0.80, 0.30), (0.90, 0.40, 0.60), (0.30, 0.55, 0.95)]
SHIRT = [(0.85, 0.15, 0.20), (0.95, 0.60, 0.10), (0.25, 0.70, 0.30), (0.55, 0.30, 0.80), (0.95, 0.95, 0.95)]


def draw_hero(ctx, x, y, ang, idx, alpha=1.0, pick_col=None, squash=0.0):
    """四角い頭のオリジナルのキャラ(8×8ドット)。玉としてころがる。"""
    hair, shirt = HAIR[idx % len(HAIR)], SHIRT[(idx // len(HAIR)) % len(SHIRT)]
    skin = (0.98, 0.80, 0.62)
    s = HERO_R * 2 * 0.86
    px = s / 8
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.scale(1 + squash, 1 - squash)
    ctx.translate(-s / 2, -s / 2)
    grid = [
        "HHHHHHHH",
        "HHHHHHHH",
        "HSSSSSSH",
        "SWESSEWS",
        "SSSSSSSS",
        "SSSMMSSS",
        "CCCCCCCC",
        "CCCCCCCC",
    ]
    cols = {"H": hair, "S": skin, "W": (1, 1, 1), "E": (0.15, 0.25, 0.55), "M": (0.70, 0.30, 0.30), "C": shirt}
    for j, row in enumerate(grid):
        for i, ch in enumerate(row):
            ctx.rectangle(i * px, j * px, px + 0.4, px + 0.4)
            ctx.set_source_rgba(*cols[ch], alpha)
            ctx.fill()
    ctx.rectangle(0, 0, s, s)
    ctx.set_source_rgba(0, 0, 0, 0.5 * alpha)
    ctx.set_line_width(2)
    ctx.stroke()
    if pick_col is not None:   # 手に持ったツルハシ
        ctx.translate(s, s * 0.55)
        ctx.rotate(-0.6)
        ctx.rectangle(-2, -2, 4, 18)
        ctx.set_source_rgba(0.45, 0.30, 0.15, alpha)
        ctx.fill()
        ctx.move_to(-12, -2)
        ctx.line_to(12, -2)
        ctx.line_to(9, 3)
        ctx.line_to(-9, 3)
        ctx.close_path()
        ctx.set_source_rgba(*pick_col, alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(0, 0, 0, 0.5 * alpha)
        ctx.set_line_width(1.5)
        ctx.stroke()
    ctx.restore()


def draw_friend(ctx, t, freed):
    """真ん中のオリの中の仲間(ピンクの髪のオリジナルキャラ)が泣いている。"""
    s = 64
    px = s / 8
    bob = math.sin(t * 6) * 3
    ctx.save()
    ctx.translate(CX - s / 2, CY - s / 2 + bob)
    grid = ["HHHHHHHH", "HHHHHHHH", "HSSSSSSH", "SWESSEWS", "STSSSSTS", "STSMMSTS", "CCCCCCCC", "CCCCCCCC"]
    if freed:
        grid[4], grid[5] = "SSSSSSSS", "SSMSSMSS"
    cols = {"H": (0.95, 0.55, 0.75), "S": (0.98, 0.82, 0.66), "W": (1, 1, 1), "E": (0.3, 0.2, 0.5),
            "M": (0.75, 0.25, 0.3), "T": (0.45, 0.75, 1.0), "C": (0.40, 0.80, 0.85)}
    for j, row in enumerate(grid):
        for i, ch in enumerate(row):
            ctx.rectangle(i * px, j * px, px + 0.4, px + 0.4)
            ctx.set_source_rgb(*cols[ch])
            ctx.fill()
    ctx.restore()
    if not freed:   # 鉄のオリ
        ctx.arc(CX, CY, CAGE_R, 0, 2 * math.pi)
        ctx.set_source_rgba(0.3, 0.3, 0.35, 0.25)
        ctx.fill()
        for i in range(-3, 4):
            x = CX + i * 17
            hh = math.sqrt(max(0, CAGE_R ** 2 - (i * 17) ** 2))
            ctx.move_to(x, CY - hh)
            ctx.line_to(x, CY + hh)
        ctx.set_source_rgb(0.55, 0.55, 0.6)
        ctx.set_line_width(5)
        ctx.stroke()
        ctx.arc(CX, CY, CAGE_R, 0, 2 * math.pi)
        ctx.set_line_width(7)
        ctx.stroke()


def background():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, H)   # 夜の洞くつ
    g.add_color_stop_rgb(0, 0.07, 0.08, 0.14)
    g.add_color_stop_rgb(1, 0.12, 0.10, 0.12)
    ctx.set_source(g)
    ctx.paint()
    rng = np.random.default_rng(3)
    for _ in range(260):   # 背景の暗いドットの石かべ
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        ctx.rectangle(int(x / 24) * 24, int(y / 24) * 24, 24, 24)
        ctx.set_source_rgba(1, 1, 1, rng.uniform(0.01, 0.04))
        ctx.fill()
    # 円の外かべ
    ctx.arc(CX, CY, R_WALL + 8, 0, 2 * math.pi)
    ctx.set_source_rgb(0.05, 0.05, 0.08)
    ctx.fill()
    ctx.arc(CX, CY, R_WALL + 8, 0, 2 * math.pi)
    ctx.set_source_rgb(0.45, 0.45, 0.5)
    ctx.set_line_width(14)
    ctx.stroke()
    ctx.arc(CX, CY, R_WALL + 8, 0, 2 * math.pi)
    ctx.set_source_rgb(0.30, 0.30, 0.34)
    ctx.set_line_width(14)
    ctx.set_dash([14, 14])
    ctx.stroke()
    ctx.set_dash([])
    return surf


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"block_rescue_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"block_rescue_{seed}.wav")
    final = os.path.join(OUT_DIR, f"block_rescue_{seed}.mp4")
    bg = background()
    rng = np.random.default_rng(seed + 1000)
    texs = [block_tex(b["ring"], rng, b["chest"]) for b in res["blocks"]]
    blocks = res["blocks"]
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    angels = AngelShow(W, H, seed) if result == "success" else None
    hit_t = {}
    debris = []
    popups = []
    shake = 0.0
    pick_banner = None
    ev_i = 0
    drng = np.random.default_rng(seed + 7)
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind in ("hit", "break"):
                hit_t[data] = et
            if kind == "break":
                b = blocks[data]
                ang = fr["rings"][b["ring"]] + b["th"]
                r = ring_radius(b["ring"])
                bx, by = CX + r * math.cos(ang), CY + r * math.sin(ang)
                base, pat = MATS[b["ring"]][2], MATS[b["ring"]][3]
                for _ in range(10):
                    a2 = drng.uniform(0, 2 * math.pi)
                    sp = drng.uniform(80, 380)
                    debris.append([bx, by, math.cos(a2) * sp, math.sin(a2) * sp, et, base if drng.uniform() < 0.6 else pat,
                                   drng.uniform(5, 11)])
                shake = max(shake, 2 + b["ring"] * 0.8)
            elif kind == "chest":
                b = blocks[data]
                ang = fr["rings"][b["ring"]] + b["th"]
                r = ring_radius(b["ring"])
                popups.append((CX + r * math.cos(ang), CY + r * math.sin(ang), et, "×2 なかま!"))
            elif kind == "pick":
                pick_banner = (et, data)
            elif kind == "rescue":
                shake = 22
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0
        shake *= 0.85
        dx, dy = (math.sin(t * 57) * shake, math.cos(t * 49) * shake) if shake > 0.5 else (0, 0)

        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        ctx.save()
        ctx.translate(dx, dy)
        draw_friend(ctx, t, result == "success" and over)
        # ブロック
        for b, tex in zip(blocks, texs):
            if b["break_t"] is not None and t >= b["break_t"]:
                continue
            ang = fr["rings"][b["ring"]] + b["th"]
            r = ring_radius(b["ring"])
            ctx.save()
            ctx.translate(CX + r * math.cos(ang), CY + r * math.sin(ang))
            ctx.rotate(ang)
            ht = hit_t.get(id(b))
            ctx.translate(-BS / 2, -BS / 2)
            ctx.set_source_surface(tex, 0, 0)
            ctx.paint()
            ctx.restore()
        # ヒビ(ダメージ)と光
        for bi, b in enumerate(blocks):
            if b["break_t"] is not None and t >= b["break_t"]:
                continue
            dmg = damage_at(events, bi, t, b["hp0"])
            ht = hit_t.get(bi)
            if dmg <= 0 and (ht is None or t - ht > 0.15):
                continue
            ang = fr["rings"][b["ring"]] + b["th"]
            r = ring_radius(b["ring"])
            ctx.save()
            ctx.translate(CX + r * math.cos(ang), CY + r * math.sin(ang))
            ctx.rotate(ang)
            if dmg > 0:
                ctx.set_source_rgba(0, 0, 0, 0.7)
                ctx.set_line_width(2.5)
                n = 1 + int(dmg * 4)
                cr = np.random.default_rng(bi)
                for _ in range(n):
                    x0, y0 = cr.uniform(-10, 10), cr.uniform(-10, 10)
                    ctx.move_to(x0, y0)
                    for _ in range(3):
                        x0 += cr.uniform(-8, 8)
                        y0 += cr.uniform(-8, 8)
                        ctx.line_to(max(-17, min(17, x0)), max(-17, min(17, y0)))
                ctx.stroke()
            if ht is not None and t - ht < 0.15:
                ctx.rectangle(-BS / 2, -BS / 2, BS, BS)
                ctx.set_source_rgba(1, 1, 1, 0.6 * (1 - (t - ht) / 0.15))
                ctx.fill()
            ctx.restore()
        # 破片
        keep = []
        for d in debris:
            age = t - d[4]
            if age > 0.6:
                continue
            keep.append(d)
            x, y = d[0] + d[2] * age, d[1] + d[3] * age
            ctx.rectangle(x - d[6] / 2, y - d[6] / 2, d[6], d[6])
            ctx.set_source_rgba(*d[5], 1 - age / 0.6)
            ctx.fill()
        debris = keep
        # キャラ
        pk = PICKS[0]
        for q in PICKS:
            if fr["broken"] >= q[0]:
                pk = q
        for hid, x, y, ang, stam in fr["heroes"]:
            draw_hero(ctx, x, y, ang, hid, 1.0, pk[3] if pk[2] > 1 else None)
        for h in res["heroes"]:   # 力つきたキャラは薄くなって消える
            if h["dead_t"] is not None and 0 <= t - h["dead_t"] < 0.5:
                a = 1 - (t - h["dead_t"]) / 0.5
                x, y = h["dead_pos"]
                draw_hero(ctx, x, y - (1 - a) * 30, h["dead_ang"], h["id"], a * 0.8)
        ctx.restore()
        # 宝箱のポップアップ
        for x, y, et, s in popups:
            age = t - et
            if 0 <= age < 1.0:
                text(ctx, s, x, y - 40 - age * 60, 54, rgb=GOLD, sw=10)
        # 仲間の「たすけて!」
        if not over and int(t * 2.5) % 2 == 0:
            text(ctx, "たすけて!", CX, CY - CAGE_R - 10 + (0 if t < 1 else 0), 44, rgb=(1, 0.8, 0.9), sw=9)

        # 文字
        g = cairo.LinearGradient(0, 0, 0, 380)
        g.add_color_stop_rgba(0, 0.04, 0.05, 0.10, 0.85)
        g.add_color_stop_rgba(1, 0.04, 0.05, 0.10, 0.0)
        ctx.rectangle(0, 0, W, 380)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, "閉じこめられた仲間を", W / 2, 150, 76, sw=14)
        text(ctx, "助け出せる？", W / 2, 280, 118, rgb=GOLD, sw=18)
        left = max(0.0, TIME_LIMIT - (end_t if over else t))
        text(ctx, f"のこり {left:4.1f}秒", W / 2, 1660, 70, rgb=(1, 0.5, 0.4) if left < 10 else (1, 1, 1), sw=12)
        text(ctx, f"ツルハシ: {pk[1]}   救助隊 ×{fr['alive']}", W / 2, 1770, 54, sw=10)
        if pick_banner is not None and 0 <= t - pick_banner[0] < 1.2:
            age = t - pick_banner[0]
            k = min(1.0, age / 0.15)
            text(ctx, f"ツルハシ強化!{PICKS[pick_banner[1]][1]}", W / 2, 470, 80 * (1.25 - 0.25 * k), rgb=PICKS[pick_banner[1]][3], sw=14)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 900, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{NR - 1 - res['deepest']}層だったのに…", W / 2, 1030, 70, sw=12)
        elif over:
            age = t - end_t
            if age < 0.3:
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.8 * (1 - age / 0.3))
                ctx.fill()
            if angels is not None:
                angels.draw(ctx, age)
            text(ctx, "助け出した!", W / 2, 520, 110, rgb=GOLD, sw=18)
        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} 壊した{res['broken']}個 / "
          f"{res['deepest'] + 1}/{NR}層 / 長さ {duration:.1f}秒)")


_dmg_cache = {}


def damage_at(events, bi, t, hp0):
    """時刻 t までにブロック bi が受けたダメージの割合(0〜1)。"""
    key = id(events)
    if key not in _dmg_cache:
        d = {}
        broken = 0
        for kind, et, data in events:
            if kind in ("hit", "break"):
                p = PICKS[0]
                for q in PICKS:
                    if broken >= q[0]:
                        p = q
                d.setdefault(data, []).append((et, p[2]))
                if kind == "break":
                    broken += 1
        _dmg_cache.clear()
        _dmg_cache[key] = d
    tot = sum(dm for et, dm in _dmg_cache[key].get(bi, []) if et <= t)
    return min(1.0, tot / hp0)


# ---------------------------------------------------------------- 音
MIX_GAIN = 0.43
HOLY_GAIN = 0.85
BEAT = 0.12   # 16分音符の長さ(秒)
# 「天国と地獄」より序曲のギャロップ(カンカン)(オッフェンバック作・1858年・パブリックドメイン)
_C, _D, _E, _F, _G, _A, _B, _C2 = 72, 74, 76, 77, 79, 81, 83, 84
MELODY = [_C, _D, _F, _E, _D, _G, _G, _G, _A, _E, _F, _D, _D, _D, _F, _E, _D, _C, _C2, _B, _A, _G, _F, _E, _D,
          _C, _D, _F, _E, _D, _G, _G, _G, _A, _E, _F, _D, _D, _D, _F, _E, _D, _C, _G, _D, _E, _C]
DURS = [4, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        4, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 4]
BASS = {_C: 48, _D: 43, _E: 48, _F: 41, _G: 43, _A: 45, _B: 43, _C2: 48}
assert len(MELODY) == len(DURS)


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def square(f, dur, amp, duty=0.5):
    t = _t(dur)
    y = np.where((t * f) % 1.0 < duty, 1.0, -1.0)
    return amp * y * np.exp(-t * 3.0) * np.minimum(1, t / 0.004) * np.minimum(1, (dur - t) / 0.02)


def triangle(f, dur, amp):
    t = _t(dur)
    y = 2 * np.abs(2 * ((t * f) % 1.0) - 1) - 1
    return amp * y * np.minimum(1, (dur - t) / 0.02) * np.minimum(1, t / 0.004)


def noise_hit(dur, amp, seed, decay):
    t = _t(dur)
    return amp * np.random.default_rng(seed).normal(0, 1, len(t)) * np.exp(-t * decay)


def mat_sound(k, broke, seed):
    """素材ごとの当たる音・壊れる音。"""
    name = MATS[k][0]
    a = 1.0 if broke else 0.45
    t = _t(0.5)
    if name == "土":
        y = noise_hit(0.5, 0.5, seed, 40) * (1 + 0 * t)
        y = np.convolve(y, np.ones(12) / 12, mode="same")
    elif name == "木":
        y = np.sin(2 * np.pi * 320 * t) * np.exp(-t * 35) + 0.3 * noise_hit(0.5, 1, seed, 60)
    elif name == "石":
        y = noise_hit(0.5, 0.7, seed, 30) + 0.4 * np.sin(2 * np.pi * 180 * t) * np.exp(-t * 25)
    elif name in ("銅", "鉄", "金"):
        base = {"銅": 620, "鉄": 820, "金": 1040}[name]
        y = sum(np.sin(2 * np.pi * base * r * t) * np.exp(-t * d) for r, d in ((1, 9), (1.52, 12), (2.31, 16))) / 2
        y += 0.2 * noise_hit(0.5, 1, seed, 80)
    elif name == "ダイヤ":
        y = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * 10) for f in (2350, 3520, 4700)) / 2
    else:
        y = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * 7) for f in (210, 330, 495)) / 2 + 0.3 * noise_hit(0.5, 1, seed, 40)
    return a * y


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    blocks = res["blocks"]
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)

    def add(sig, t0, gain=1.0):
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out:
            out[i:j] += gain * sig[: j - i]

    note_i = -1
    next_ok = 0.0
    deepest = -1
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.01 and kind != "rescue":
            continue   # 結果が出たあとはお祝い(または幽霊)の音だけにする
        if kind in ("hit", "break"):
            k = blocks[data]["ring"]
            add(mat_sound(k, kind == "break", data), t, 0.5)
        if kind == "break":
            deepest = max(deepest, blocks[data]["ring"])
            if t >= next_ok:   # 前の音の長さが経っていたら曲が1音進む(本来のテンポ)
                note_i += 1
                m = note_i % len(MELODY)
                f = midi_hz(MELODY[m])
                dur = DURS[m] * BEAT
                add(square(f, dur + 0.05, 0.55, 0.5 if deepest < 4 else 0.25), t)
                if deepest >= 2:   # 低音が加わる
                    add(triangle(midi_hz(BASS[MELODY[m]]), dur + 0.05, 0.6), t)
                if deepest >= 4:   # ハモリ
                    add(square(midi_hz(MELODY[m] - 5), dur + 0.05, 0.25, 0.125), t)
                if deepest >= 6:   # ドラム
                    add(noise_hit(0.12, 0.5, note_i, 45), t)
                next_ok = t + dur - 0.01
        elif kind == "chest":   # 宝箱:ピロリン!
            for j, mm in enumerate((84, 88, 91, 96)):
                add(square(midi_hz(mm), 0.09, 0.4, 0.25), t + j * 0.06)
        elif kind == "pick":   # ツルハシ強化:ジャジャーン
            for j, mm in enumerate((72, 76, 79, 84)):
                add(square(midi_hz(mm), 0.12, 0.4, 0.5), t + j * 0.08)
            add(square(midi_hz(84), 0.5, 0.4, 0.25), t + 0.32)
        elif kind == "spawn":
            add(square(midi_hz(67), 0.06, 0.15, 0.25), t)
            add(square(midi_hz(79), 0.06, 0.15, 0.25), t + 0.05)
        elif kind == "fade":
            for j, mm in enumerate((67, 62, 55)):
                add(square(midi_hz(mm), 0.07, 0.12, 0.5), t + j * 0.06)
        elif kind == "rescue":
            for j, mm in enumerate((72, 76, 79, 84, 88, 91, 96)):
                add(square(midi_hz(mm), 0.1, 0.5, 0.5), t + j * 0.05)
            add(triangle(midi_hz(48), 1.0, 0.8), t + 0.35)
            add(square(midi_hz(84), 1.0, 0.5, 0.5), t + 0.35)
            add(square(midi_hz(88), 1.0, 0.35, 0.25), t + 0.35)
    extra = np.zeros(n_out)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(end_t * SR) + int(1.2 * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += HOLY_GAIN * sig[:m]
    wet = out.copy()
    for d, g in ((0.061, 0.25), (0.113, 0.15)):   # 洞くつの響き
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * MIX_GAIN
    body = wet[: int((end_t or duration) * SR)]
    rms = np.sqrt(np.mean(body ** 2)) if len(body) else 0
    if rms > 0:   # 通常部分の平均音量を約 -18dB にそろえる
        wet *= min(1.6, 10 ** (-18.0 / 20) / rms)
    wet = np.clip(wet + (0.95 if fail else 1.0) * extra[: len(wet)], -0.98, 0.98)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("-n", type=int, default=200)
    ap.add_argument("--want", choices=["fail", "success"], default="fail")
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
