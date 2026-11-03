"""「閉じこめられた仲間を助け出せる?」うずまきの通路に並んだブロックを、剣が転がりながら壊していく物理ショートを生成する。

- 12本目のうずまき(真上から見た水平な盤)を4重にして通路を広くし、通路いっぱいの大きなドット絵ブロックを並べた。
  外側から 土 → 木 → 石 → 銅 → 鉄 → 金 → ダイヤ → 黒い最強合金 の順で、内側ほど硬い(ドット絵はすべてオリジナル)。
- 玉の代わりは剣(オリジナルのドット絵)。前の剣が全部消えたら次の剣が落ちてくる:
  木の剣1本 → 石の剣2本 → 鉄の剣3本 → 金の剣3本 → ダイヤの剣4本。強い剣ほど1回で与えるダメージが大きい。
- 剣はうずまきの外側の口から落ちてきて通路を転がる。ブロックに強く当たるとダメージ。こわれたら突き抜けるが、そのぶん遅くなる。
  こわれなければはね返る。転がり抵抗でも少しずつ遅くなり、勢いがなくなった剣は薄くなって消える(ねらい・補正なし)。
- ブロックを壊すたびに「天国と地獄」(オッフェンバック・パブリックドメイン)が1音ずつ本来のテンポで進む(ピコピコ音)。
真ん中のオリまでのブロックを全部壊せば成功(天使)、剣が尽きたら失敗(幽霊)。

使い方:
    python sword_spiral.py search [--want fail|success] [-n 200]
    python sword_spiral.py render --seed N
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "block_rescue"))
from block_rescue import (MATS, MELODY, DURS, BASS, BEAT, square, triangle, noise_hit,  # noqa: E402
                          mat_sound, MIX_GAIN, HOLY_GAIN)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from angels import DURATION as ANGEL_DUR, AngelShow, holy_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000

CX, CY = 540.0, 930.0
TURNS = 4
R_IN, R_OUT = 84.0, 444.0
TH_END = TURNS * 2 * math.pi
B = (R_OUT - R_IN) / TH_END
LANE = 2 * math.pi * B                 # 通路の幅(90px)
BLOCK_LEN = 86.0                       # ブロック1個の通路方向の長さ(px)
TH_B0 = 0.6                            # ブロックを並べ始める位置(内側)
TH_B1 = TH_END - 2 * math.pi - 0.5     # ブロックを並べ終える位置(外側の入口は少し空ける)
MATS = list(MATS)
# 一番奥の最強合金は、紫がかった黒っぽい金属(ドット絵はオリジナル)
MATS[7] = ("最強合金", 22, (0.24, 0.19, 0.27), (0.34, 0.26, 0.40))
NR = len(MATS)

BLOCK_E = float(os.environ.get("BLOCK_E", 0.75))                        # こわれなかったときのはね返り
ABSORB = float(os.environ.get("ABSORB", 0.10))   # ブロックをこわして突き抜けるときに失う速さの割合
V_REF = float(os.environ.get("V_REF", 490.0))   # この速さで当たると剣の標準ダメージ
V_MIN = float(os.environ.get("V_MIN", 150.0))                         # これより弱い当たりはダメージなし
AIR_DAMP = float(os.environ.get("AIR_DAMP", 0.75))   # 盤面で1秒あたりに残る速さの割合(転がり抵抗)
A_SLOPE = float(os.environ.get("A_SLOPE", 500.0))
V_CRIT = float(os.environ.get("V_CRIT", 1700.0))   # これより速く当たるとクリティカル   # 中心へ向かう下り坂の強さ(px/秒²)
V_DIE = 200.0                          # これより遅くなった剣は消えていく
FADE = 0.5
WALL_E = 1.0
BALL_R = 22
GRAVITY = 2600.0
DROP_X = CX + R_OUT - LANE / 2
DROP_Y = CY - 600
CHUTE_L, CHUTE_R = CX + R_OUT - LANE, CX + R_OUT
CHUTE_TOP = DROP_Y - 60
HPK = float(os.environ.get("HPK", 1.0))
# 剣:名前, 本数, ダメージ, 刃の色, 刃のふちの色
SWORDS = [("木", 1, 1, (0.72, 0.53, 0.30), (0.45, 0.30, 0.15)),
          ("石", 2, 2, (0.62, 0.62, 0.62), (0.35, 0.35, 0.38)),
          ("鉄", 3, 3, (0.92, 0.92, 0.95), (0.55, 0.55, 0.60)),
          ("金", 4, 4, (1.00, 0.85, 0.25), (0.75, 0.52, 0.08)),
          ("ダイヤ", 10, 7, (0.45, 0.95, 0.95), (0.15, 0.55, 0.60))]
# ダメージ=1回当たるとブロックの「あと何回」がいくつ減るか。木1・石2・鉄3・金4(石ブロックを1回で)・ダイヤ7(ダイヤブロックを1回で)
if os.environ.get("SWORD_N"):   # 調整用:波ごとの本数
    SWORDS = [(w[0], int(n), w[2], w[3], w[4]) for w, n in zip(SWORDS, os.environ["SWORD_N"].split(","))]
if os.environ.get("SWORD_D"):   # 調整用:剣の強さ
    SWORDS = [(w[0], w[1], int(d), w[3], w[4]) for w, d in zip(SWORDS, os.environ["SWORD_D"].split(","))]
N_SWORDS = sum(s[1] for s in SWORDS)
# 剣の耐久(何回ブロックに当たったら折れるか):木・石・鉄・金・ダイヤ。金は強いが折れやすい
SWORD_DUR = [int(x) for x in os.environ.get("SWORD_DUR", "2,3,3,2,4").split(",")]
BLOCK_HP = [int(x) for x in os.environ.get("BLOCK_HP", "1,2,3,4,5,6,7,8").split(",")]
# こわれるまでに木の剣で当たる回数:土1・木2・石3・銅4・鉄5・金6・ダイヤ7・最強合金8
WAVE_GAP = 0.6
DROP_EVERY = 0.35
FAIL_WAIT = 0.8
MAX_T = 90.0
OUTRO = 2.5

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


def r_of(th):
    return R_IN + B * th


def phi_of(th):
    return TH_END - th


def wall_pt(th, dr=0.0):
    r, p = r_of(th) + dr, phi_of(th)
    return CX + r * math.cos(p), CY + r * math.sin(p)


def outside_board(x, y):
    dx, dy = x - CX, y - CY
    phi = math.atan2(dy, dx) % (2 * math.pi)
    return math.hypot(dx, dy) > R_OUT - B * phi + 2


def board_physics(body, gravity, damping, dt):
    x, y = body.position
    if outside_board(x, y):
        pymunk.Body.update_velocity(body, gravity, 1.0, dt)
    else:   # 盤はうずまきに沿って中心へ向かうゆるい下り坂(すべり台)
        a = math.atan2(y - CY, x - CX)
        fwd = (-math.sin(a) * A_SLOPE, math.cos(a) * A_SLOPE)
        pymunk.Body.update_velocity(body, fwd, AIR_DAMP ** dt, dt)


def block_lines():
    """ブロックの外側の面の位置(th)。外側(入口)から内側へ。"""
    ths = []
    th = TH_B1
    while th - BLOCK_LEN / (r_of(th) + LANE / 2) > TH_B0 - 1e-6:
        ths.append(th)
        th -= BLOCK_LEN / (r_of(th) + LANE / 2)
    ths.append(th)   # 一番内側のブロックの内側の面(ここは壁ではない)
    return ths


LINES = block_lines()
N_BLOCKS = len(LINES) - 1


def mat_of(k):
    """k=0 が一番外側。8種類をほぼ同じ数ずつ。"""
    return min(NR - 1, k * NR // N_BLOCKS)


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 20
        self.space = sp
        st = sp.static_body
        n = int(TH_END / 0.025)
        pts = [wall_pt(TH_END * k / n) for k in range(n + 1)]
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            s = pymunk.Segment(st, a, b, 3)
            s.elasticity, s.friction = WALL_E, 0.0
            s.set_neighbors(pts[max(i - 1, 0)], pts[min(i + 2, n)])
            sp.add(s)
        for x in (CHUTE_L, CHUTE_R):
            seg = pymunk.Segment(st, (x, CY), (x, CHUTE_TOP), 3)
            seg.elasticity, seg.friction = WALL_E, 0.0
            sp.add(seg)
        # ブロック:通路を横切る外側の面(当たり判定)。両側の面を持たせる
        self.blocks = []
        self.block_of = {}
        for k in range(N_BLOCKS):
            m = mat_of(k)
            hp = max(1, round(BLOCK_HP[m] * HPK))
            shapes = []
            for th in (LINES[k], LINES[k + 1]):
                s = pymunk.Segment(st, wall_pt(th, 5), wall_pt(th + 2 * math.pi, -5), 3)
                s.elasticity, s.friction = BLOCK_E, 0.0
                s.collision_type = 4
                sp.add(s)
                self.block_of[s] = k
                shapes.append(s)
            self.blocks.append({"k": k, "mat": m, "hp": hp, "hp0": hp, "alive": True, "shapes": shapes,
                                "break_t": None})
        sp.on_collision(1, 4, begin=self._hit)
        self.balls = []
        self.events = []
        self.cleared = 0
        self.t = 0.0
        self.result, self.result_t = None, None
        self.wave = -1
        self.queue = []
        self.next_wave_t = 0.5
        self.dropped = 0
        self.all_gone_t = None
        self.to_break = []

    def _hit(self, arb, space, data):
        if self.result is not None:
            return
        k = self.block_of.get(arb.shapes[1])
        body = arb.shapes[0].body
        bl = self.ball_of.get(body)
        if k is None or bl is None:
            return
        blk = self.blocks[k]
        if not blk["alive"]:
            arb.process_collision = False
            return
        n = arb.normal
        v = body.velocity
        vn = abs(v.dot(n))
        if vn < V_MIN:
            return   # 弱すぎる当たりはただはね返るだけ
        d = SWORDS[bl["kind"]][2]   # 剣の強さのぶんだけ「あと何回」が減る
        crit = vn > V_CRIT
        if crit:   # 勢いよく当たるとクリティカル(1.5倍)
            d = math.ceil(d * 1.5)
        blk["hp"] -= d
        bl["dur"] -= 1
        if bl["dur"] <= 0:   # 剣の耐久がなくなった:はね返らずにその場で折れて消える
            arb.process_collision = False
            self.to_shatter.append(bl)
        if blk["hp"] <= 0:   # こわれた:突き抜ける(そのぶん遅くなる)
            arb.process_collision = False
            blk["alive"] = False
            blk["break_t"] = self.t
            self.to_break.append(k)
            body.velocity = v * (1 - ABSORB)
            self.cleared += 1
            self.events.append(("break", self.t, (k, bl["kind"], d)))
        else:
            self.events.append(("hit", self.t, (k, bl["kind"], d)))
        if crit:
            x, y = body.position
            self.events.append(("crit", self.t, (x, y)))

    def drop(self, kind):
        m = 1.0
        b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, BALL_R))
        b.position = (DROP_X + self.rng.uniform(-20, 20), DROP_Y - self.rng.uniform(0, 120))
        b.velocity = (self.rng.uniform(-150, 150), 0)
        b.velocity_func = board_physics
        c = pymunk.Circle(b, BALL_R)
        c.elasticity, c.friction = 1.0, 0.0
        c.collision_type = 1
        self.space.add(b, c)
        bl = {"id": self.dropped, "body": b, "shape": c, "kind": kind, "dur": SWORD_DUR[kind]}
        self.dropped += 1
        self.balls.append(bl)
        self.ball_of[b] = bl
        self.events.append(("drop", self.t, (bl["id"], kind)))

    ball_of = None

    def step(self, dt):
        if self.ball_of is None:
            self.ball_of = {}
        self.t += dt
        if self.result is None and not self.balls and not self.queue and self.next_wave_t is not None \
                and self.t >= self.next_wave_t and self.wave + 1 < len(SWORDS):
            self.wave += 1
            self.queue = [(self.t + j * DROP_EVERY, self.wave) for j in range(SWORDS[self.wave][1])]
            self.next_wave_t = None
            self.events.append(("wave", self.t, self.wave))
        while self.queue and self.queue[0][0] <= self.t:
            self.drop(self.queue.pop(0)[1])
        self.to_break = []
        self.to_shatter = []
        self.space.step(dt)
        for bl in self.to_shatter:
            if bl in self.balls:
                b = bl["body"]
                self.space.remove(b, bl["shape"])
                self.balls.remove(bl)
                self.ball_of.pop(b, None)
                self.events.append(("shatter", self.t, (bl["id"], b.position.x, b.position.y, bl["kind"], b.angle)))
        for k in self.to_break:
            for s in self.blocks[k]["shapes"]:
                if s in self.space.shapes:
                    self.space.remove(s)
        for bl in list(self.balls):
            b = bl["body"]
            x, y = b.position
            slow = b.velocity.length < V_DIE and not outside_board(x, y)
            if slow or y > H + 200 or x < -200 or x > W + 200:
                self.space.remove(b, bl["shape"])
                self.balls.remove(bl)
                self.ball_of.pop(b, None)
                self.events.append(("die", self.t, (bl["id"], x, y, bl["kind"], b.angle)))
        if self.result is None:
            if self.cleared == N_BLOCKS:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif not self.balls and not self.queue:
                if self.wave + 1 < len(SWORDS):
                    if self.next_wave_t is None:
                        self.next_wave_t = self.t + WAVE_GAP
                else:
                    if self.all_gone_t is None:
                        self.all_gone_t = self.t
                    if self.t >= self.all_gone_t + FAIL_WAIT:
                        self.result, self.result_t = "fail", self.t
                        self.events.append(("fail", self.t, None))
            if self.result is None and self.t >= MAX_T:
                self.result, self.result_t = "fail", self.t


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "cleared": g.cleared, "dropped": g.dropped,
                           "balls": [(b["id"], b["body"].position.x, b["body"].position.y, b["kind"],
                                      b["body"].velocity.x, b["body"].velocity.y) for b in g.balls]})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "cleared": g.cleared, "blocks": [{"mat": b["mat"], "hp0": b["hp0"], "break_t": b["break_t"]}
                                             for b in g.blocks]}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["cleared"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件(ブロック {N_BLOCKS} 個)")
    if want == "fail":
        for seed, _, _, c in sorted([r for r in rs if r[1] == "fail"], key=lambda r: -r[3])[:15]:
            print(f"seed={seed:4d}  {c}/{N_BLOCKS} 個で剣が尽きた")
    else:
        for seed, _, rt, _ in sorted(succ, key=lambda r: -r[2])[:15]:
            print(f"seed={seed:4d}  救出 {rt:5.2f}秒")


# ---------------------------------------------------------------- 描画
OFFSET_Y = 90
GOLD = (1, 0.86, 0.2)


def block_tex(m, rng):
    """8×8 ドットのブロック(素材ごとのオリジナルの模様)。8px のドットで描き、あとで拡大する。"""
    name, _, base, pat = MATS[m]
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 8, 8)
    c = cairo.Context(surf)
    for i in range(8):
        for j in range(8):
            col = base
            v = rng.uniform(-0.06, 0.06)
            if name == "土":
                if rng.uniform() < 0.3:
                    col = pat
            elif name == "木":
                if j in (2, 5) or (j in (0, 3, 6) and i == 3):
                    col = pat
            elif name == "石":
                if rng.uniform() < 0.35:
                    col = pat
            elif name == "銅":
                if rng.uniform() < 0.22:
                    col = pat
            elif name == "鉄":
                if j in (0, 7) or i in (0, 7):
                    col = pat
                elif j == 3:
                    col = (0.95, 0.95, 0.97)
            elif name == "金":
                if j in (0, 7) or i in (0, 7):
                    col = pat
                elif (i + j) % 5 == 0:
                    col = (1, 0.95, 0.6)
            elif name == "ダイヤ":
                if j in (0, 7) or i in (0, 7):
                    col = pat
                elif (i, j) in ((2, 2), (3, 2), (2, 3), (5, 5), (4, 5), (5, 4)):
                    col = (0.9, 1, 1)
            else:   # 最強合金:紫がかった黒い金属。ふちは暗く、ななめに明るいすじ
                if j in (0, 7) or i in (0, 7):
                    col = (0.15, 0.11, 0.17)
                elif (i + j) in (5, 6) or (i + j) == 10:
                    col = (0.46, 0.36, 0.52)
                elif rng.uniform() < 0.4:
                    col = pat
            c.rectangle(i, j, 1, 1)
            c.set_source_rgb(*[min(1, max(0, x + v)) for x in col])
            c.fill()
    return surf


SWORD_GRID = [
    "...........EE",
    "..........EBE",
    ".........EBE.",
    "........EBE..",
    ".......EBE...",
    "......EBE....",
    ".....EBE.....",
    "..GG.BE......",
    "...GGE.......",
    "...HGG.......",
    "..H..G.......",
    ".H...........",
    "P............",
]


def draw_sword(ctx, x, y, ang, kind, size, alpha=1.0):
    """オリジナルのドット絵の剣。"""
    _, _, _, blade, edge = SWORDS[kind]
    cols = {"B": blade, "E": edge, "G": (0.35, 0.25, 0.18), "H": (0.55, 0.38, 0.22), "P": (0.35, 0.25, 0.18)}
    n = len(SWORD_GRID)
    px = size / n
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.translate(-size / 2, -size / 2)
    for j, row in enumerate(SWORD_GRID):   # 黒いふち
        for i, ch in enumerate(row):
            if ch != ".":
                ctx.rectangle(i * px - px * 0.35, j * px - px * 0.35, px * 1.7, px * 1.7)
    ctx.set_source_rgba(0.08, 0.06, 0.06, alpha)
    ctx.fill()
    for j, row in enumerate(SWORD_GRID):
        for i, ch in enumerate(row):
            if ch != ".":
                ctx.rectangle(i * px, j * px, px + 0.3, px + 0.3)
                ctx.set_source_rgba(*cols[ch], alpha)
                ctx.fill()
    ctx.restore()


def draw_friend(ctx, t, freed):
    """真ん中のオリの中の仲間(ピンクの髪のオリジナルキャラ)。"""
    s = 72
    px = s / 8
    bob = math.sin(t * 6) * 3 if not freed else -abs(math.sin(t * 8)) * 14
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
    if not freed:
        rr = R_IN - 12
        for i in range(-3, 4):
            x = CX + i * 18
            hh = math.sqrt(max(0, rr ** 2 - (i * 18) ** 2))
            ctx.move_to(x, CY - hh)
            ctx.line_to(x, CY + hh)
        ctx.set_source_rgb(0.55, 0.55, 0.6)
        ctx.set_line_width(5)
        ctx.stroke()
        ctx.arc(CX, CY, rr, 0, 2 * math.pi)
        ctx.set_line_width(7)
        ctx.stroke()


def draw_static():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, H)   # 夜の洞くつ
    g.add_color_stop_rgb(0, 0.08, 0.09, 0.15)
    g.add_color_stop_rgb(1, 0.13, 0.11, 0.13)
    ctx.set_source(g)
    ctx.paint()
    rng = np.random.default_rng(3)
    for _ in range(300):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        ctx.rectangle(int(x / 30) * 30, int(y / 30) * 30, 30, 30)
        ctx.set_source_rgba(1, 1, 1, rng.uniform(0.01, 0.04))
        ctx.fill()
    ctx.translate(0, OFFSET_Y)
    ctx.arc(CX, CY, R_OUT + 34, 0, 2 * math.pi)   # 盤(暗い石の床)
    ctx.set_source_rgb(0.16, 0.15, 0.17)
    ctx.fill()
    # 通路の床(ドットの石畳)
    n = int(TH_END / 0.02)
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    for th0 in np.arange(0, TH_END - 2 * math.pi, 0.02):
        a = wall_pt(th0 + 1 * math.pi, 0)
        _ = a
    lines = [[wall_pt(TH_END * k / n) for k in range(n + 1)],
             [(CHUTE_L, CY), (CHUTE_L, CHUTE_TOP)], [(CHUTE_R, CY), (CHUTE_R, CHUTE_TOP)]]
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for pts in lines:   # 石のかべ
        for width, col in ((14, (0.25, 0.24, 0.27)), (8, (0.55, 0.54, 0.58))):
            ctx.move_to(*pts[0])
            for p in pts[1:]:
                ctx.line_to(*p)
            ctx.set_source_rgb(*col)
            ctx.set_line_width(width)
            ctx.stroke()
    ctx.arc(CX, CY, R_IN - 4, 0, 2 * math.pi)
    ctx.set_source_rgb(0.22, 0.20, 0.24)
    ctx.fill()
    return surf


def block_geom(k):
    """ブロック k の中心・向き・大きさ(画面座標、OFFSET_Y なし)。"""
    th = (LINES[k] + LINES[k + 1]) / 2
    rm = r_of(th) + LANE / 2
    p = phi_of(th)
    ln = (LINES[k] - LINES[k + 1]) * rm
    return CX + rm * math.cos(p), CY + rm * math.sin(p), p + math.pi / 2, ln


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    blocks = res["blocks"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"sword_spiral_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"sword_spiral_{seed}.wav")
    final = os.path.join(OUT_DIR, f"sword_spiral_{seed}.mp4")
    static = draw_static()
    rng = np.random.default_rng(seed + 1000)
    texs = [block_tex(b["mat"], rng) for b in blocks]
    geoms = [block_geom(k) for k in range(len(blocks))]
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    angels = AngelShow(W, H, seed) if result == "success" else None
    dmg = [0.0] * len(blocks)
    hit_t = {}
    debris, dying = [], []
    spin = {}
    shake = 0.0
    wave_banner = None
    ev_i = 0
    drng = np.random.default_rng(seed + 7)
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind in ("hit", "break"):
                k, sk, dd = data
                dmg[k] = min(1.0, dmg[k] + dd / blocks[k]["hp0"])
                hit_t[k] = et
            if kind == "break":
                x, y, _, _ = geoms[k]
                base, pat = MATS[blocks[k]["mat"]][2], MATS[blocks[k]["mat"]][3]
                for _ in range(14):
                    a2 = drng.uniform(0, 2 * math.pi)
                    sp = drng.uniform(80, 420)
                    debris.append([x, y, math.cos(a2) * sp, math.sin(a2) * sp, et,
                                   base if drng.uniform() < 0.6 else pat, drng.uniform(7, 15)])
                shake = max(shake, 3 + blocks[k]["mat"] * 1.0)
            elif kind == "die":
                dying.append(data + (et,))
            elif kind == "crit":   # クリティカル:星が飛び散る
                x, y = data
                for j in range(10):
                    a2 = drng.uniform(0, 2 * math.pi)
                    sp = drng.uniform(150, 380)
                    debris.append([x, y, math.cos(a2) * sp, math.sin(a2) * sp, et,
                                   (1, 1, 0.75) if j % 2 else (1, 0.85, 0.3), drng.uniform(5, 9)])
            elif kind == "shatter":   # 剣が折れて、ドットのかけらが飛び散る
                bid, x, y, sk, _ = data
                _, _, _, blade, edge = SWORDS[sk]
                for j in range(16):
                    a2 = drng.uniform(0, 2 * math.pi)
                    sp = drng.uniform(120, 460)
                    col = blade if j < 9 else (edge if j < 13 else (0.55, 0.38, 0.22))
                    debris.append([x, y, math.cos(a2) * sp, math.sin(a2) * sp, et, col, drng.uniform(6, 12)])
            elif kind == "wave":
                wave_banner = (et, data)
            elif kind == "success":
                shake = 20
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0
        shake *= 0.85
        dx, dy = (math.sin(t * 57) * shake, math.cos(t * 49) * shake) if shake > 0.5 else (0, 0)
        ctx.save()
        ctx.translate(dx, dy)
        ctx.set_source_surface(static, 0, 0)
        ctx.paint()
        ctx.translate(0, OFFSET_Y)
        draw_friend(ctx, t, result == "success" and over)
        # ブロック
        for k, b in enumerate(blocks):
            if b["break_t"] is not None and t >= b["break_t"]:
                continue
            x, y, ang, ln = geoms[k]
            w_, h_ = ln - 4, LANE - 10
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(ang)
            ctx.save()
            ctx.translate(-w_ / 2, -h_ / 2)
            ctx.scale(w_ / 8, h_ / 8)
            pat = cairo.SurfacePattern(texs[k])
            pat.set_filter(cairo.FILTER_NEAREST)
            ctx.set_source(pat)
            ctx.rectangle(0, 0, 8, 8)
            ctx.fill()
            ctx.restore()
            ctx.rectangle(-w_ / 2, -h_ / 2, w_, h_)
            ctx.set_source_rgba(0, 0, 0, 0.45)
            ctx.set_line_width(3)
            ctx.stroke()
            if dmg[k] > 0:   # ヒビ
                cr = np.random.default_rng(k)
                ctx.set_source_rgba(0, 0, 0, 0.75)
                ctx.set_line_width(3)
                for _ in range(1 + int(dmg[k] * 5)):
                    x0, y0 = cr.uniform(-w_ / 4, w_ / 4), cr.uniform(-h_ / 4, h_ / 4)
                    ctx.move_to(x0, y0)
                    for _ in range(3):
                        x0 = max(-w_ / 2, min(w_ / 2, x0 + cr.uniform(-14, 14)))
                        y0 = max(-h_ / 2, min(h_ / 2, y0 + cr.uniform(-14, 14)))
                        ctx.line_to(x0, y0)
                ctx.stroke()
            ht = hit_t.get(k)
            if ht is not None and t - ht < 0.15:
                ctx.rectangle(-w_ / 2, -h_ / 2, w_, h_)
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
            ctx.rectangle(d[0] + d[2] * age - d[6] / 2, d[1] + d[3] * age - d[6] / 2, d[6], d[6])
            ctx.set_source_rgba(*d[5], 1 - age / 0.6)
            ctx.fill()
        debris = keep
        # 剣(転がる向きにくるくる回る)
        for bid, x, y, kind, vx, vy in fr["balls"]:
            sp_ = math.hypot(vx, vy)
            spin[bid] = spin.get(bid, 0.0) + sp_ / FPS / BALL_R * 0.5
            draw_sword(ctx, x, y, spin[bid], kind, BALL_R * 4.2)
        keep = []
        for bid, x, y, kind, ang, et in dying:
            age = t - et
            if age < FADE:
                keep.append((bid, x, y, kind, ang, et))
                draw_sword(ctx, x, y - age * 40, spin.get(bid, 0.0), kind, BALL_R * 4.2, 1 - age / FADE)
        dying = keep
        ctx.restore()

        # 文字
        g = cairo.LinearGradient(0, 0, 0, 360)
        g.add_color_stop_rgba(0, 0.04, 0.05, 0.10, 0.85)
        g.add_color_stop_rgba(1, 0.04, 0.05, 0.10, 0.0)
        ctx.rectangle(0, 0, W, 360)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, "閉じこめられた仲間を", W / 2, 130, 72, sw=14)
        text(ctx, "助け出せる？", W / 2, 250, 110, rgb=GOLD, sw=18)
        if not over and int(t * 2.5) % 2 == 0:
            text(ctx, "たすけて!", CX, CY + OFFSET_Y - R_IN - 4, 46, rgb=(1, 0.8, 0.9), sw=9)
        text(ctx, f"ブロック {fr['cleared']} / {len(blocks)}", W / 2, 1610, 64, sw=12)
        # 残りの剣の列
        gap = min(70.0, (W - 90) / max(1, N_SWORDS - 1))
        x0 = W / 2 - (N_SWORDS - 1) * gap / 2
        i = 0
        for sk, (_, cnt, _, _, _) in enumerate(SWORDS):
            for _ in range(cnt):
                used = i < fr["dropped"]
                draw_sword(ctx, x0 + i * gap, 1730, 0.0, sk, 56, 0.25 if used else 1.0)
                i += 1
        if wave_banner is not None and 0 <= t - wave_banner[0] < 1.3 and not over:
            age = t - wave_banner[0]
            k = min(1.0, age / 0.15)
            name, cnt = SWORDS[wave_banner[1]][0], SWORDS[wave_banner[1]][1]
            text(ctx, f"{name}の剣 ×{cnt}!", W / 2, 400, 84 * (1.25 - 0.25 * k), rgb=SWORDS[wave_banner[1]][3], sw=14)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "剣が尽きた…", W / 2, 880, 130 * (1.3 - 0.3 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{len(blocks) - res['cleared']}個だったのに…", W / 2, 1010, 70, sw=12)
        elif over:
            age = t - end_t
            if age < 0.3:
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.8 * (1 - age / 0.3))
                ctx.fill()
            if angels is not None:
                angels.draw(ctx, age)
            text(ctx, "助け出した!", W / 2, 470, 110, rgb=GOLD, sw=18)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['cleared']}/{len(blocks)}個 / "
          f"長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def item_break(seed):
    """道具が折れる「パキッ」という短い音(ノイズと短い高い音で合成したオリジナル)。"""
    rng = np.random.default_rng(seed + 50)
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    lp = np.convolve(noise, np.ones(6) / 6, mode="same")
    crack = (noise - lp) * np.exp(-t * 38)                 # 高い「パキッ」
    body = lp * np.exp(-t * 22) * 0.8                      # 低めの「ガシャ」
    pops = np.zeros(n)                                      # 細かく割れるプチプチ
    for _ in range(9):
        i = int(rng.uniform(0, 0.07) * SR)
        pops[i:i + 40] += rng.uniform(-1, 1) * np.exp(-np.arange(min(40, n - i)) / 8)
    f0 = rng.uniform(1700, 2100)
    ping = np.sin(2 * np.pi * f0 * t * (1 - 0.35 * t / 0.22)) * np.exp(-t * 45) * 0.5
    y = crack + body + pops * 1.5 + ping
    return y / (np.max(np.abs(y)) + 1e-9) * 0.9


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
        if end_t is not None and t > end_t + 0.01:
            continue
        if kind in ("hit", "break"):
            k, sk, _ = data
            add(mat_sound(blocks[k]["mat"], kind == "break", k), t, 0.6)
        if kind == "break":
            deepest = max(deepest, blocks[k]["mat"])
            if t >= next_ok:   # 前の音の長さが経っていたら曲が1音進む(本来のテンポ)
                note_i += 1
                m = note_i % len(MELODY)
                dur = DURS[m] * BEAT
                add(square(midi_hz(MELODY[m]), dur + 0.05, 0.55, 0.5 if deepest < 4 else 0.25), t)
                if deepest >= 2:
                    add(triangle(midi_hz(BASS[MELODY[m]]), dur + 0.05, 0.6), t)
                if deepest >= 4:
                    add(square(midi_hz(MELODY[m] - 5), dur + 0.05, 0.25, 0.125), t)
                if deepest >= 6:
                    add(noise_hit(0.12, 0.5, note_i, 45), t)
                next_ok = t + dur - 0.01
        elif kind == "wave":   # 新しい剣:シャキーン
            for j, mm in enumerate((79, 84, 91)):
                add(square(midi_hz(mm), 0.08, 0.3, 0.25), t + j * 0.05)
        elif kind == "drop":
            add(sum(np.sin(2 * np.pi * f * np.arange(int(0.25 * SR)) / SR) for f in (2600, 3900))
                * np.exp(-np.arange(int(0.25 * SR)) / SR * 14) * 0.15, t)
        elif kind == "shatter":
            add(item_break(data[0]), t, 1.0)
        elif kind == "crit":   # クリティカルの「シャキン」
            tt = np.arange(int(0.12 * SR)) / SR
            add(np.sin(2 * np.pi * 3200 * tt) * np.exp(-tt * 30) * 0.25, t)
        elif kind == "die":
            for j, mm in enumerate((67, 62, 55)):
                add(square(midi_hz(mm), 0.07, 0.12, 0.5), t + j * 0.06)
        elif kind == "success":
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
    for d, g in ((0.061, 0.25), (0.113, 0.15)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * MIX_GAIN
    body = wet[: int((end_t or duration) * SR)]
    rms = np.sqrt(np.mean(body ** 2)) if len(body) else 0
    if rms > 0:
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
