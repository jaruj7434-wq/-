"""「鉄球の振り子でブロックを全部けずれる?」(参考動画の形)
上からつるした3本の棒の振り子(多重振り子)の先に、重い鉄球がついている(最初の版は回るノコギリ)。振り子は物理どおりにでたらめに(カオス的に)ゆれ、
ノコギリが通った所の虹色のブロックがけずれていく。つり下げている点は、クレーンのように左右にゆっくり行ったり来たりしながら(振り子をゆらし続ける力)、残っているブロックのいちばん上に合わせてゆっくり下がっていく(残りの上のほうがだいたいけずれたら下がる)。
制限時間内にブロックを全部けずれたら成功、けずれなければ失敗。

- 重力あり。振り子の棒どうしは自由に回るピンでつながっている(ねらい・補正なし)。
- 鉄球がブロックにぶつかると、その所がくだける。くだくたびに、くだいた量に応じてほんの少しブレーキがかかる(当たっても速くはならない)。
- ノコギリがブロックの下のほうをほったときは、その上にあった所もいっしょにくずれて消える(ブロックはいつも上の面だけの形)。
- 下の床(ブロックの底)とつながっていない破片は、支えがないので落ちる。
- 成功ならパチンコの大当たり風の演出、失敗なら幽霊 → 暗くなって「Failed...」。

使い方:
    python saw_pendulum.py search [-n 80]
    python saw_pendulum.py render --seed N
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
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ball_escape"))
from ball_escape import midi_hz  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from fail_bgm import fail_music  # noqa: E402
from pachinko import RainbowFever, hsv, kyuin_music  # noqa: E402
from flashy import PALETTE, chic, draw_ball as shiny_ball, giragira, horror, kyuin_one  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "glass_spiral"))
import jackpot_end as JP  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 8
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

BX0, BX1 = float(os.environ.get("BX0", 160.0)), float(os.environ.get("BX1", 920.0))            # ブロックの左右
BY0, BY1 = float(os.environ.get("BY0", 760.0)), float(os.environ.get("BY1", 1400.0))          # ブロックの上下
CELL = 4.0
NX, NY = int((BX1 - BX0) / CELL), int((BY1 - BY0) / CELL)
PIV_X = W / 2
PIV_Y0 = float(os.environ.get("PIV_Y0", 420.0))   # つり下げ点のはじめの高さ
PIV_Y1 = float(os.environ.get("PIV_Y1", 1200.0))   # ここまで下がる
HEIGHTFIELD = os.environ.get("HEIGHTFIELD", "1") == "1"
MODE = os.environ.get("MODE", "high")
HIGH_Q = float(os.environ.get("HIGH_Q", 75.0))
TOP_Q = float(os.environ.get("TOP_Q", 0.3))
FOLLOW = float(os.environ.get("FOLLOW", 180.0))   # つり下げ点はブロックのいちばん上よりこれだけ上
PIV_V = float(os.environ.get("PIV_V", 21.0))      # 下がる速さ(px/秒)
LINKS = [float(x) for x in os.environ.get("LINKS", "200,185,170").split(",")]
START = os.environ.get("START", "lift")
DOUBLE = os.environ.get("DOUBLE", "1") == "1"   # カクカクの紐(二重振り子)
D_L1 = float(os.environ.get("D_L1", 280.0))
D_L2 = float(os.environ.get("D_L2", 240.0))
M1 = float(os.environ.get("M1", 1.0))
M2 = float(os.environ.get("M2", 3.0))
# 関節をふやしたカクカクの紐(多重振り子)。棒の長さと、各関節/先のおもりの重さ
N_LEN = [float(x) for x in os.environ.get("N_LEN", "150,135,125,110").split(",")]
N_MASS = [float(x) for x in os.environ.get("N_MASS", "1,1,1,3").split(",")]
N_ADD = [float(x) for x in os.environ.get("N_ADD", "10,60").split(",")]
SINGLE = os.environ.get("SINGLE", "1") == "1"   # 1本の紐の鉄球(ふつうの振り子)
L0 = float(os.environ.get("L0", 380.0))
L_MAX = float(os.environ.get("L_MAX", 1060.0))
L_V = float(os.environ.get("L_V", 12.0))        # 紐がのびる速さ(px/秒)
DIG = float(os.environ.get("DIG", 30.0))
TH0_MIN = float(os.environ.get("TH0_MIN", 50.0))
TH0_MAX = float(os.environ.get("TH0_MAX", 88.0))
KEEP_E = os.environ.get("KEEP_E", "1") == "1"
SWAY_A = float(os.environ.get("SWAY_A", 0.0))   # つり下げ点が左右に動くはば(片側)
SWAY_T = float(os.environ.get("SWAY_T", 2.4))     # 1往復の秒数
SAW_R = float(os.environ.get("SAW_R", 56.0))
KICK = float(os.environ.get("KICK", 0.0))       # 回る刃がブロックをけって進む強さ(1マスあたり)
BOUNCE = float(os.environ.get("BOUNCE", 0.0))
DRAG = float(os.environ.get("DRAG", 0.000005))      # けずった1マスごとのブレーキ(速さの割合)
GRAVITY = float(os.environ.get("GRAVITY", 650.0))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 44.9))
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG
OFFS = [(dx, dy) for dx in range(-int(SAW_R / CELL) - 1, int(SAW_R / CELL) + 2)
        for dy in range(-int(SAW_R / CELL) - 1, int(SAW_R / CELL) + 2)]


class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 30
        self.space = sp
        self.pivot = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.sway_ph = rng.uniform(0, 2 * math.pi)
        self.pivot.position = (PIV_X + SWAY_A * math.sin(self.sway_ph), PIV_Y0)
        sp.add(self.pivot)
        # はじめは棒を少しずつちがう角度で横にもち上げて、はなす
        prev, prev_pt = self.pivot, (0, 0)
        x, y = self.pivot.position
        self.links = []
        for k, L in enumerate(LINKS):
            if START == "straight":   # まっすぐ横にのばしてはなす(角度はほんの少しずつシードごとにちがう)
                a = math.radians(rng.uniform(-6, 6) - 8)
            else:
                a = math.radians(rng.uniform(-20, 20) + (-10 if k % 2 == 0 else -170))   # ほぼ横にもち上げてはなす(高い所から落ちる)
            ex, ey = x + L * math.cos(a), y + L * math.sin(a)
            m = 1.0 if k < len(LINKS) - 1 else 2.0
            b = pymunk.Body(m, pymunk.moment_for_segment(m, (0, 0), (ex - x, ey - y), 2))
            b.position = (x, y)
            s = pymunk.Segment(b, (0, 0), (ex - x, ey - y), 2)
            s.filter = pymunk.ShapeFilter(categories=0, mask=0)
            sp.add(b, s)
            j = pymunk.PivotJoint(prev, b, (x, y))
            j.collide_bodies = False
            sp.add(j)
            self.links.append((b, (ex - x, ey - y)))
            prev = b
            x, y = ex, ey
        self.grid = np.ones((NY, NX), bool)
        self.total = NX * NY
        self.left = self.total
        self.t = 0.0
        self.events = []
        self.result, self.result_t = None, None
        self.cut_now = 0
        self.spin = 0.0
        self.top_y = BY0
        if DOUBLE:   # はじめは2本ともななめにもち上げてからはなす(角度はシードごとにちがう)
            sgn = rng.choice([-1, 1])
            a = rng.uniform(TH0_MIN, TH0_MAX)
            ths = [a]
            for _ in N_LEN[1:]:   # 先の棒ほど少しずつ大きくもち上げる
                ths.append(ths[-1] + rng.uniform(*N_ADD) / (len(N_LEN) - 1))
            self.th_n = np.radians(ths) * sgn
            self.w_n = np.zeros(len(N_LEN))
            self.l_n = np.array(N_LEN)
            m = np.array(N_MASS)
            self.mu = np.array([[m[max(i, j):].sum() for j in range(len(m))] for i in range(len(m))])
        if SINGLE:   # はじめは紐をななめにもち上げてからはなす(角度はシードごとにちがう)
            self.L = L0
            self.th = math.radians(rng.uniform(TH0_MIN, TH0_MAX)) * rng.choice([-1, 1])
            self.om = 0.0
        self.e_target = None
        self.next_drop_chk = 0.0
        self.fallen = []

    def energy(self):
        """つり下げ点から見た、振り子の力学的エネルギー(運動+位置)。"""
        pv, py = self.pivot.velocity, self.pivot.position.y
        ke = pe = 0.0
        for b, _ in self.links:
            v = b.velocity - pv
            ke += 0.5 * b.mass * v.dot(v) + 0.5 * b.moment * b.angular_velocity ** 2
            pe += b.mass * GRAVITY * (py - b.position.y)
        return ke, pe

    def fix_energy(self):
        """計算の誤差(数値のまさつ)で減ったエネルギーだけを元にもどす。ブロックをくだいて使った分は、もどさない。"""
        ke, pe = self.energy()
        if self.e_target is None:
            self.e_target = ke + pe
            return
        want_ke = self.e_target - pe
        if ke > 1e-6 and want_ke > 0:
            k = math.sqrt(want_ke / ke)
            pv = self.pivot.velocity
            for b, _ in self.links:
                b.velocity = pv + (b.velocity - pv) * k
                b.angular_velocity *= k

    def chain_pts(self):
        px, py = self.pivot.position
        xs = px + np.concatenate([[0], np.cumsum(self.l_n * np.sin(self.th_n))])
        ys = py + np.concatenate([[0], np.cumsum(self.l_n * np.cos(self.th_n))])
        return [(float(x), float(y)) for x, y in zip(xs, ys)]

    def saw_pos(self):
        if DOUBLE:
            return self.chain_pts()[-1]
        if SINGLE:
            px, py = self.pivot.position
            return (px + self.L * math.sin(self.th), py + self.L * math.cos(self.th))
        b, end = self.links[-1]
        return b.local_to_world(end)

    def step_single(self, dt):
        """1本の紐の鉄球(ふつうの振り子)。紐は固定した点からたれていて、クレーンが少しずつ紐をのばす。
        θ'' = -(g/L)·sinθ - 2(L'/L)·θ'(紐がのびるときの振り子の式)を、細かい時間で計算する。"""
        self.t += dt
        px, py = self.pivot.position
        want = L_MAX   # クレーンは一定の速さで紐をのばしていく
        dL = min(want - self.L, L_V * dt) if want > self.L else 0.0
        Ld = dL / dt
        acc = -(GRAVITY / self.L) * math.sin(self.th) - 2 * (Ld / self.L) * self.om
        self.om += acc * dt
        self.th += self.om * dt
        self.L += dL
        self.cut_and_check()

    def cut_and_check(self):
        if self.result is not None:
            return
        sx, sy = self.saw_pos()
        j0 = max(0, int((sx - SAW_R - BX0) / CELL))
        j1 = min(NX - 1, int((sx + SAW_R - BX0) / CELL))
        n = 0
        for j in range(j0, j1 + 1):
            xc = BX0 + (j + 0.5) * CELL
            dx = xc - sx
            if abs(dx) > SAW_R:
                continue
            ybot = sy + math.sqrt(SAW_R * SAW_R - dx * dx)   # 鉄球の下のふち
            col = self.grid[:, j]
            top = NY - int(col.sum())                       # 上の面の行
            ytop = BY0 + top * CELL
            if ybot > ytop:
                newtop = min(NY, int((ybot - BY0) / CELL) + 1)
                if newtop > top:
                    col[top:newtop] = False
                    n += newtop - top
        if n:
            self.left -= n
            self.cut_now += n
            f = max(0.0, 1 - DRAG * n)   # くだいた分だけ、ほんの少しおそくなる
            if DOUBLE:
                self.w_n *= f
            else:
                self.om *= f
        if self.t >= self.next_drop_chk:
            self.next_drop_chk = self.t + 0.2
            colh = self.grid.sum(axis=0)
            self.top_y = BY1 - float(np.percentile(colh, HIGH_Q)) * CELL
        if self.left <= 0:
            self.result, self.result_t = "success", self.t
            self.events.append(("success", self.t, None))
        elif self.t >= TIME_LIMIT:
            self.result, self.result_t = "fail", self.t
            self.events.append(("fail", self.t, None))

    def np_acc(self, th, w):
        """多重振り子(点のおもりを棒でつないだもの)の角加速度。ラグランジュの運動方程式 M·θ'' = F を解く。"""
        l, g = self.l_n, GRAVITY
        d = th[:, None] - th[None, :]
        ll = l[:, None] * l[None, :] * self.mu
        M = ll * np.cos(d)
        F = -(ll * np.sin(d)) @ (w * w) - np.diag(self.mu) * g * l * np.sin(th)
        return np.linalg.solve(M, F)

    def step_double(self, dt):
        """カクカクの紐(関節のある多重振り子)。つり下げ点は真下へ一定の速さでおりる(横には動かない)。RK4で計算。"""
        self.t += dt
        px, py = self.pivot.position
        self.pivot.position = (px, min(PIV_Y1, py + PIV_V * dt))
        th, w = self.th_n, self.w_n
        a1 = self.np_acc(th, w)
        a2 = self.np_acc(th + w * dt / 2, w + a1 * dt / 2)
        a3 = self.np_acc(th + (w + a1 * dt / 2) * dt / 2, w + a2 * dt / 2)
        a4 = self.np_acc(th + (w + a2 * dt / 2) * dt, w + a3 * dt)
        v1, v2, v3, v4 = w, w + a1 * dt / 2, w + a2 * dt / 2, w + a3 * dt
        self.th_n = th + dt / 6 * (v1 + 2 * v2 + 2 * v3 + v4)
        self.w_n = w + dt / 6 * (a1 + 2 * a2 + 2 * a3 + a4)
        self.cut_and_check()

    def step(self, dt):
        if DOUBLE:
            return self.step_double(dt)
        if SINGLE:
            return self.step_single(dt)
        self.t += dt
        # つり下げ点は、残っているブロックのいちばん上より FOLLOW だけ上の高さまで、ゆっくり下がる(上がりはしない)
        want = min(PIV_Y1, max(PIV_Y0, self.top_y - FOLLOW))
        if MODE == "const":   # クレーンが一定の速さでおろしていく
            want = PIV_Y1
        cur = self.pivot.position.y
        if MODE == "center":   # 残っているブロックのまん中の高さに合わせて、上にも下にもゆっくり動く(クレーン)
            py = cur + max(-PIV_V * dt, min(PIV_V * dt, want - cur))
        else:
            py = min(want, cur + PIV_V * dt) if want > cur else cur
        # つり下げ点はクレーンのように左右にゆっくり行ったり来たりする(振り子をゆらし続ける力)
        w = 2 * math.pi / SWAY_T
        vx = SWAY_A * w * math.cos(w * self.t + self.sway_ph)
        self.pivot.velocity = (vx, (py - cur) / dt)
        self.space.step(dt)
        if KEEP_E:
            self.fix_energy()
        if self.result is not None:
            return
        sx, sy = self.saw_pos()
        cx, cy = int((sx - BX0) / CELL), int((sy - BY0) / CELL)
        if -6 <= cx < NX + 6 and -6 <= cy < NY + 6:
            n = 0
            mx = my = 0.0
            for dx, dy in OFFS:
                i, j = cy + dy, cx + dx
                if 0 <= i < NY and 0 <= j < NX and self.grid[i, j]:
                    px, py_ = BX0 + (j + 0.5) * CELL, BY0 + (i + 0.5) * CELL
                    if (px - sx) ** 2 + (py_ - sy) ** 2 <= SAW_R * SAW_R:
                        self.grid[i, j] = False
                        n += 1
                        mx += px
                        my += py_
                        if HEIGHTFIELD:   # 下をほったら、その上にあった所もいっしょにくずれる(ブロックは上の面だけの形)
                            above = int(self.grid[:i, j].sum())
                            if above:
                                self.grid[:i, j] = False
                                self.left -= above
                                self.cut_now += above
            if n:
                self.left -= n
                cnt = self.grid.sum(axis=1)
                cum = np.cumsum(cnt)
                if MODE == "center" and cum[-1] > 0:
                    self.top_y = BY0 + float((cnt * np.arange(NY)).sum() / cum[-1]) * CELL
                elif cum[-1] > 0:   # 残っているブロックの上から TOP_Q の量のところ(小さなかけらにひっぱられない)
                    r_ = int(np.searchsorted(cum, cum[-1] * TOP_Q))
                    self.top_y = BY0 + r_ * CELL
                self.cut_now += n
                b, end = self.links[-1]
                mx, my = mx / n, my / n               # けずった所のまん中
                nx_, ny_ = sx - mx, sy - my
                ln = math.hypot(nx_, ny_) or 1.0
                nx_, ny_ = nx_ / ln, ny_ / ln         # けずった所からノコギリへの向き
                tx_, ty_ = -ny_, nx_                  # 回るノコギリの刃が、けずった所をけって進む向き
                v = b.velocity_at_world_point((sx, sy))
                vn = v.x * nx_ + v.y * ny_
                f = min(0.5, DRAG * n)
                ix = -v.x * f + KICK * n * tx_ / 100
                iy = -v.y * f + KICK * n * ty_ / 100
                if vn < 0:                            # かたいブロックにめりこむ向きの速さは少しはね返す
                    ix -= BOUNCE * vn * nx_
                    iy -= BOUNCE * vn * ny_
                b.apply_impulse_at_world_point((ix * b.mass, iy * b.mass), (sx, sy))
                if KEEP_E and self.e_target is not None:   # くだいた分だけエネルギーを使う
                    ke, pe = self.energy()
                    self.e_target -= ke * min(0.5, DRAG * n) * 2
        if self.t >= self.next_drop_chk:   # 下の床(ブロックの底)とつながっていない破片は、支えがないので落ちる
            self.next_drop_chk = self.t + 0.2
            cnt = self.grid.sum(axis=1)   # 残っているブロックの高さを見直す(破片が落ちたあとも)
            cum = np.cumsum(cnt)
            if cum[-1] > 0:
                if MODE == "high":   # 上の面の高い所(高いほうから HIGH_Q の所)に合わせる:高い所が残っているうちは下がらない
                    colh = self.grid.sum(axis=0)
                    self.top_y = BY1 - float(np.percentile(colh, HIGH_Q)) * CELL
                elif MODE == "surface":   # 上の面の高さの平均
                    colh = self.grid.sum(axis=0)
                    self.top_y = BY1 - float(colh.mean()) * CELL
                elif MODE == "center":
                    self.top_y = BY0 + float((cnt * np.arange(NY)).sum() / cum[-1]) * CELL
                else:
                    self.top_y = BY0 + int(np.searchsorted(cum, cum[-1] * TOP_Q)) * CELL
            lab, nlab = ndimage.label(self.grid)
            if nlab > 1 or (nlab == 1 and not self.grid[-1].any()):
                keep = set(np.unique(lab[-1])) - {0}
                loose = (lab > 0) & ~np.isin(lab, list(keep))
                nl = int(loose.sum())
                if nl:
                    ys, xs = np.nonzero(loose)
                    self.fallen.append((self.t, xs.astype(np.int16), ys.astype(np.int16)))
                    self.grid[loose] = False
                    self.left -= nl
                    self.events.append(("fall", self.t, nl))
        if self.left <= 0:
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
        g.cut_now = 0
        for _ in range(SUBSTEPS):
            g.step(dt)
        sx, sy = g.saw_pos()
        if g.cut_now:
            g.events.append(("cut", g.t, (sx, sy, g.cut_now)))
        if record:
            if DOUBLE:
                pts = g.chain_pts()
            elif SINGLE:
                pts = [tuple(g.pivot.position), g.saw_pos()]
            else:
                pts = [tuple(g.pivot.position)] + [tuple(b.local_to_world(e)) for b, e in g.links]
            frames.append({"t": g.t, "pts": pts, "left": g.left, "grid": g.grid.copy() if g.cut_now or not frames else None,
                           "cut": g.cut_now})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "left": g.left, "total": g.total, "fallen": g.fallen}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), r["left"], round(1 - r["left"] / r["total"], 4)


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    shiny_ball(ctx, x, y, r * 0.8, PALETTE[(kind * 12 // 7) % 12])


def failed_text(ctx, s, x, y, size, alpha):
    """失敗の文字:Playfair Display の斜体。暗い赤で、うっすら赤黒くにじむ。"""
    if alpha <= 0:
        return
    ctx.select_font_face("Playfair Display", cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    e = ctx.text_extents(s)
    if e.width > W * 0.86:
        size *= W * 0.86 / e.width
        ctx.set_font_size(size)
        e = ctx.text_extents(s)
    tx = x - e.width / 2 - e.x_bearing
    for wd, al in ((30, 0.10), (16, 0.18)):
        ctx.move_to(tx, y)
        ctx.text_path(s)
        ctx.set_source_rgba(0.45, 0.02, 0.05, al * alpha)
        ctx.set_line_width(wd)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    g = cairo.LinearGradient(0, y - size * 0.8, 0, y + size * 0.1)
    g.add_color_stop_rgba(0, 0.85, 0.25, 0.28, alpha)
    g.add_color_stop_rgba(1, 0.45, 0.05, 0.08, alpha)
    ctx.move_to(tx, y)
    ctx.text_path(s)
    ctx.set_source(g)
    ctx.fill()


def draw_iron(ctx, x, y, r):
    """つやのある鉄球。"""
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.05, x, y, r)
    g.add_color_stop_rgb(0, 0.97, 0.98, 1.0)
    g.add_color_stop_rgb(0.25, 0.7, 0.73, 0.78)
    g.add_color_stop_rgb(0.7, 0.32, 0.34, 0.38)
    g.add_color_stop_rgb(1, 0.12, 0.13, 0.15)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source_rgba(0.85, 0.9, 1.0, 0.35)
    ctx.set_line_width(1.5)
    ctx.stroke()


def draw_saw(ctx, x, y, r, ang):
    n = 14
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.new_path()
    for k in range(n * 2):
        a = math.pi * k / n
        rr = r if k % 2 == 0 else r * 0.72
        ctx.line_to(rr * math.cos(a), rr * math.sin(a))
    ctx.close_path()
    g = cairo.RadialGradient(-r * 0.3, -r * 0.3, 1, 0, 0, r)
    g.add_color_stop_rgb(0, 0.97, 0.98, 1.0)
    g.add_color_stop_rgb(1, 0.55, 0.62, 0.72)
    ctx.set_source(g)
    ctx.fill()
    ctx.arc(0, 0, r * 0.36, 0, 2 * math.pi)
    ctx.set_source_rgb(0.25, 0.3, 0.38)
    ctx.fill()
    ctx.arc(0, 0, r * 0.14, 0, 2 * math.pi)
    ctx.set_source_rgb(0.95, 0.95, 1)
    ctx.fill()
    ctx.restore()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"saw_pendulum_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"saw_pendulum_{seed}.wav")
    final = os.path.join(OUT_DIR, f"saw_pendulum_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"sp_preview_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, W / 2, (BY0 + BY1) / 2, reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=("Congratulations!!", "COMPLETE", ""), font="Playfair Display", slim=True)
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    # 虹色のブロック(横に虹のグラデーション)
    rainbow = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    rc = cairo.Context(rainbow)
    g_ = cairo.LinearGradient(BX0, 0, BX1, 0)
    for k in range(13):
        r_, gg, b_ = colorsys.hsv_to_rgb(0.83 * k / 12, 0.95, 0.62)
        g_.add_color_stop_rgb(k / 12, r_, gg, b_)
    rc.rectangle(BX0, BY0, BX1 - BX0, BY1 - BY0)
    rc.set_source(g_)
    rc.fill()
    mask = cairo.ImageSurface(cairo.FORMAT_A8, NX, NY)
    mstride = mask.get_stride()
    prng = np.random.default_rng(seed + 9)
    parts = []
    grid = frames[0]["grid"]
    spin = 0.0
    frozen = None
    fall_i, falling = 0, []
    for fi, fr in enumerate(frames):
        t = fr["t"]
        if fr["grid"] is not None:
            grid = fr["grid"]
        while fall_i < len(res["fallen"]) and res["fallen"][fall_i][0] <= t:
            falling.append(res["fallen"][fall_i])
            fall_i += 1
        over = end_t is not None and t >= end_t
        win_b = (t - end_t) if (ending is not None and over) else -1.0
        if win_b >= PRE:
            ending.draw(surf, ctx, win_b - PRE + JP.T_BIG)
            giragira(ctx, win_b - PRE, fever, glints, W, H, WIN_DUR)
            ff.stdin.write(surf.get_data())
            continue
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        if fail and over:
            if frozen is None:
                frozen = (fr, grid)
            fr, grid = frozen
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        ctx.set_source_rgb(0.035, 0.04, 0.07)
        ctx.paint()
        # ブロック(残っている所だけ)
        buf = np.zeros((NY, mstride), np.uint8)
        buf[:, :NX] = grid.astype(np.uint8) * 255
        mask.get_data()[:] = buf.tobytes()
        mask.mark_dirty()
        mp = cairo.SurfacePattern(mask)
        m = cairo.Matrix()
        m.scale(1 / CELL, 1 / CELL)
        m.translate(-BX0, -BY0)
        mp.set_matrix(m)
        mp.set_filter(cairo.FILTER_BILINEAR)
        ctx.set_source_surface(rainbow, 0, 0)
        ctx.mask(mp)
        # 上の面のふちを白くうっすら光らせる
        colh = grid.sum(axis=0)
        if colh.any():
            ctx.new_path()
            for j in range(NX):
                y_ = BY1 - colh[j] * CELL
                ctx.line_to(BX0 + (j + 0.5) * CELL, y_)
            for wd, al in ((8, 0.12), (2.5, 0.75)):
                ctx.set_source_rgba(0.85, 0.95, 1.0, al)
                ctx.set_line_width(wd)
                ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                ctx.stroke_preserve()
            ctx.new_path()
        # 支えがなくなって落ちる破片
        keepf = []
        for t0, xs, ys in falling:
            age = t - t0
            if age > 1.6:
                continue
            dy = 0.5 * 1800 * age * age
            for x_, y_ in zip(xs[::2], ys[::2]):
                X = BX0 + x_ * CELL
                Y = BY0 + y_ * CELL + dy
                if Y > H:
                    continue
                ctx.rectangle(X, Y, CELL * 1.4, CELL * 1.4)
                ctx.set_source_rgba(*colorsys.hsv_to_rgb(0.83 * x_ / NX, 0.95, 0.62), max(0.0, 1 - age / 1.6))
                ctx.fill()
            keepf.append((t0, xs, ys))
        falling = keepf
        # 削りかす
        sx, sy = fr["pts"][-1]
        if fr["cut"] and not over:
            hue = (sx - BX0) / (BX1 - BX0) * 0.83
            for _ in range(min(30, fr["cut"] // 2 + 3)):
                a = prng.uniform(0, 2 * math.pi)
                v = prng.uniform(150, 700)
                parts.append([sx, sy, v * math.cos(a), v * math.sin(a) - 200, t, hue + prng.uniform(-0.05, 0.05),
                              prng.uniform(0, 6.3), prng.uniform(4, 12)])
        keep = []
        for p in parts:
            age = t - p[4]
            if age > 1.2 or age < 0:
                continue
            x = p[0] + p[2] * age
            y = p[1] + p[3] * age + 900 * age * age
            L = p[7]
            ctx.move_to(x - L * math.cos(p[6]) / 2, y - L * math.sin(p[6]) / 2)
            ctx.line_to(x + L * math.cos(p[6]) / 2, y + L * math.sin(p[6]) / 2)
            ctx.set_source_rgba(*colorsys.hsv_to_rgb(p[5] % 1, 0.7, 1.0), max(0.0, 1 - age / 1.2))
            ctx.set_line_width(2)
            ctx.stroke()
            keep.append(p)
        parts = keep[-2500:]
        # つり糸と振り子
        pts = fr["pts"]
        ctx.move_to(pts[0][0], 0)
        ctx.line_to(*pts[0])
        ctx.set_source_rgba(0.8, 0.85, 1.0, 0.35)
        ctx.set_line_width(1.5)
        ctx.stroke()
        for wd, al in ((12, 0.12), (4, 0.9)):
            ctx.move_to(*pts[0])
            for p in pts[1:]:
                ctx.line_to(*p)
            ctx.set_source_rgba(0.75, 0.88, 1.0, al)
            ctx.set_line_width(wd)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()
        ctx.arc(*pts[0], 7, 0, 2 * math.pi)
        ctx.set_source_rgb(0.95, 0.98, 1)
        ctx.fill()
        for p in pts[1:-1]:
            ctx.arc(*p, 5, 0, 2 * math.pi)
            ctx.set_source_rgb(0.1, 0.12, 0.18)
            ctx.fill_preserve()
            ctx.set_source_rgb(0.75, 0.88, 1.0)
            ctx.set_line_width(2)
            ctx.stroke()
        if not over:
            spin += 0.5
        draw_iron(ctx, sx, sy, SAW_R)
        # 文字
        chic(ctx, "全部けずれる？", W / 2, 200, 62, rgb=(1, 0.88, 0.6))
        pct = int((1 - fr["left"] / res["total"]) * 100)
        chic(ctx, f"{pct}%", W / 2 - 110, 310, 84, rgb=(1, 1, 1), weight="Medium")
        tt = min(t, end_t) if end_t is not None else t
        left = max(0.0, TIME_LIMIT - tt)
        chic(ctx, f"{left:4.1f}", W / 2 + 130, 305, 44, rgb=(1, 0.45, 0.45) if left < 5 else (0.7, 0.75, 0.85), weight="Medium")
        if not over:
            # 鉄球が下まで来たときは、文字が重ならないようにうすく消す
            ha = min(1.0, max(0.0, (1480 - sy) / 90))
            if ha > 0:
                ctx.push_group()
                horror(ctx, "失敗したら…", W / 2, 1620, 74, t)
                ctx.pop_group_to_source()
                ctx.paint_with_alpha(ha)
        if over and fail:
            ctx.set_operator(cairo.OPERATOR_HSL_SATURATION)
            ctx.set_source_rgba(0.5, 0.5, 0.5, min(1.0, after / 0.8))
            ctx.paint()
            ctx.set_operator(cairo.OPERATOR_OVER)
            ctx.set_source_rgba(0, 0, 0, 0.6 * min(1.0, after / 1.2))
            ctx.paint()
            vg = cairo.RadialGradient(W / 2, H / 2, 300, W / 2, H / 2, 1150)
            vg.add_color_stop_rgba(0, 0, 0, 0, 0)
            vg.add_color_stop_rgba(1, 0, 0, 0, 0.85 * min(1.0, after / 1.2))
            ctx.set_source(vg)
            ctx.paint()
            k = min(1.0, max(0.0, (after - 0.2) / 1.4))
            k = k * k * (3 - 2 * k)
            failed_text(ctx, "Failed...", W / 2, 1010 + 40 * (1 - k), 160, k)
        if win_b >= 0:
            k = win_b / PRE
            ph_ = (win_b * (8 + 14 * k)) % 1.0
            ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*hsv(win_b * 4), (0.25 + 0.4 * k) * (1 - ph_) ** 2)
            ctx.paint()
            ctx.set_operator(cairo.OPERATOR_OVER)
            if k > 0.75:
                ctx.set_source_rgba(1, 1, 1, ((k - 0.75) / 0.25) ** 2)
                ctx.paint()
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
    pct = 100 * (1 - res["left"] / res["total"])
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {pct:.1f}% / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)
    rng = np.random.default_rng(5)
    # けずる「ジャリジャリ」:けずった量に応じた大きさの、こすれる音(フレームごと)
    fl = int(SR / FPS)
    tt = _t(1 / FPS * 2)
    for kind, t, data in events:
        if kind != "cut" or t > end_t + 0.01:
            continue
        n = data[2]
        amp = min(1.0, 0.25 + n / 40)
        nz = rng.normal(0, 1, len(tt))
        hp = nz - np.convolve(nz, np.ones(3) / 3, "same")
        f0 = 900 + 30 * min(n, 60)
        buzz = np.sign(np.sin(2 * np.pi * f0 * tt)) * 0.25
        sig = amp * (0.7 * hp + buzz) * np.hanning(len(tt))
        i = int(t * SR)
        j = min(n_out, i + len(sig))
        if i < n_out:
            out[i:j] += sig[: j - i]
    wet = out.copy()
    for dd, g_ in ((0.043, 0.18), (0.071, 0.12)):
        kk = int(dd * SR)
        wet[kk:] += out[:-kk] * g_
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int(end_t * SR)]
    rms = np.sqrt(np.mean(body ** 2))
    if rms > 0:
        wet *= min(6.0, 10 ** (-15.0 / 20) / rms)
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
        b_ = JP.music(SR, 3)
        b_ = b_.mean(axis=1) if b_.ndim == 2 else b_
        b_ = b_[int(JP.T_BIG * SR) - int(0.05 * SR):]
        n = int(WIN_DUR * SR)
        mus = np.zeros(n)
        mus[:min(n, len(b_))] += b_[:n] / (np.abs(b_).max() + 1e-9)
        a_ = kyuin_music(SR, WIN_DUR)
        mus[:min(n, len(a_))] += 0.8 * a_[:n]
        t2 = 0.0
        while t2 < WIN_DUR - 0.5:
            ky = kyuin_one(1.0 + 0.15 * ((int(t2 / 0.3)) % 3))
            i = int(t2 * SR)
            m = min(len(ky), n - i)
            mus[i:i + m] += 0.4 * ky[:m]
            t2 += 0.3
        tb = np.arange(int(1.5 * SR)) / SR
        boom = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-tb * 6) + 35) / SR) * np.exp(-tb * 2.5)
        mus[:len(boom)] += 0.9 * boom
        mus *= np.minimum(1, (WIN_DUR - np.arange(n) / SR) / 0.6)
        mus = np.tanh(1.6 * mus / (np.abs(mus).max() + 1e-9)) / np.tanh(1.6)
        i0 = int((end_t + PRE) * SR)
        m = min(len(mus), n_out - i0)
        extra[i0:i0 + m] += 1.1 * mus[:m]
        t2 = 0.0
        while t2 < PRE - 0.05:
            k = t2 / PRE
            ky = kyuin_one(1.0 + 0.6 * k)
            i = int((end_t + t2) * SR)
            m = min(len(ky), n_out - i)
            extra[i:i + m] += (0.35 + 0.35 * k) * ky[:m]
            t2 += 0.11 - 0.05 * k
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
