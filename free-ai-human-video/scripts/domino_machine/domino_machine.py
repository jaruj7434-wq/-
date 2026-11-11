"""「ドミノとボールの装置で『歓喜の歌』を最後まで演奏できる?」ドミノ・ボール・シーソーをつないだからくり装置の物理ショート。

横から見た装置(右へ進む):
  1. 高い棚の上のドミノ15枚 → 最後の1枚が赤いボールを押す → ボールが坂を転がり落ちる
  2. 赤いボールが2列目のドミノ17枚を倒す → 最後の1枚が鉄球を棚から押し出す → 鉄球がシーソーの片はしに落ちる
  3. シーソーの反対側の金のボールが打ち上がり、穴を飛びこえて向こうの台に着地できるか(ここが運命の分かれ目)
  4. 金のボールが3列目のドミノ(だんだん大きくなる)を倒し、最後の巨大ドミノが鐘を鳴らせば成功(天使)
ドミノが実際に次のドミノ(や鐘)に当たった瞬間に「歓喜の歌」(ベートーヴェン・パブリックドメイン)が1音進む。
物理は重力・衝突・摩擦のまま(ねらい・補正なし)。並べ方が手で置いたように少しずつばらつくので、結果が毎回変わる。

使い方:
    python domino_machine.py search [-n 200]
    python domino_machine.py render --seed N
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

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "ball_escape"))
from ball_escape import midi_hz, text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from angels import DURATION as ANGEL_DUR, AngelShow, holy_music  # noqa: E402
from fail_bgm import fail_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 6
SR = 48000
GRAVITY = 1500.0
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

# 「歓喜の歌」(ハ長調)
_A = [64, 64, 65, 67, 67, 65, 64, 62, 60, 60, 62, 64, 64, 62, 62]
_BR = [62, 62, 64, 60, 62, 64, 65, 64, 60, 62, 64, 65, 64, 62, 60, 62, 55]
_A2 = [64, 64, 65, 67, 67, 65, 64, 62, 60, 60, 62, 64, 62, 60, 60]
RUNS = [_A, _A2, _BR, _A2, _BR, _A2]   # ドミノの列ごとの音(歓喜の歌・94音)。最後の列だけジャンプの先

DOM_H, DOM_T = 60.0, 11.0
GAP = float(os.environ.get("GAP", 0.42))   # すきま(ドミノの高さに対する割合)。せまいほどテンポが速い
JIT = float(os.environ.get("JIT", 0.08))
GROW3 = 1.07                         # 最後の列のドミノが1枚ごとに大きくなる倍率
# 地形
NPRE = 5                                    # ジャンプまでの棚の数
STEP_DY = [0.0, 9.0, -6.0, 0.0, 9.0]        # 棚ごとのドミノの並べ方:0=平ら、+=下り階段、-=上り階段(1枚ごとの段差)
TRANS = ["zigzag", "spring", "valley", "seesaw"]   # 棚と棚のつなぎ:ジグザグのレール・バネの板・谷・シーソー橋
TRANS_DROP = {"zigzag": 600.0, "spring": 410.0, "pegs": 640.0, "valley": 110.0, "seesaw": 160.0}
P2_Y = -480.0                               # 最後の棚(この先がジャンプ台)の高さ


def shelf_heights():
    """最後の棚が P2_Y になるように、上から順に棚の高さを決める。"""
    ys = [0.0]
    for r in range(NPRE - 1):
        y_end = ys[-1] + STEP_DY[r] * (len(RUNS[r]) - 1)
        ys.append(y_end + TRANS_DROP[TRANS[r]])
    y_last_end = ys[-1] + STEP_DY[NPRE - 1] * (len(RUNS[NPRE - 1]) - 1)
    off = P2_Y - y_last_end
    return [y + off for y in ys]


SHELF_Y = shelf_heights()
P0_Y = SHELF_Y[0]
BALL_KINDS = ["rubber", "marble", "soccer", "basket", "bowling"]   # 段ごとのボール
BALL_R = [24.0, 22.0, 28.0, 28.0, 30.0]
BALL_DENS = [0.006, 0.012, 0.004, 0.006, None]
LEAD = 150.0                                # 棚のはじめから1枚目のドミノまで
JUMP_RUN, JUMP_DROP = 420.0, 330.0          # ジャンプ台の下り坂(横の長さ・高さ)
KICK_R, KICK_ANG = 220.0, float(os.environ.get("KICK_ANG", 0.62))   # けり上げ台(半径・角度)
PIT_W = float(os.environ.get("PIT_W", 268.0))   # 穴の幅
P3_Y = float(os.environ.get("P3_Y", -230.0))    # 着地する台の高さ
LAND_RUN = 200.0                             # 着地する台の、穴のふちから1枚目のドミノまで
HB_R, HB_DENS = 30.0, float(os.environ.get("HB_DENS", 0.02))   # 鉄球(ジャンプする)
STOP_WAIT = 3.0
OUTRO = 4.2                                  # 失敗のあと(幽霊のあと)の長さ。しょんぼりBGMが流れる
CT_DOM, CT_BELL, CT_PEG = 3, 4, 5


class Game:
    def __init__(self, seed):
        rng = self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 30
        self.space = sp
        st = sp.static_body
        self.statics = []

        def seg(a, b, r=6, fr=0.8, el=0.1):
            s = pymunk.Segment(st, a, b, r)
            s.friction, s.elasticity = fr, el
            sp.add(s)
            self.statics.append((a, b, r))
            return s
        # ドミノを先に並べて、棚の長さを決める
        self.doms = []          # (body, h, run, k)
        self.idx = {}
        self.hit = {}
        self.events = []
        ys = SHELF_Y
        x0 = -80.0
        ends = []
        self.parts = []        # 見た目のための部品 (種類, 段, データ)
        self.seesaw = None
        self.end_y = []        # 棚ごとの、最後のドミノの足もとの高さ(ボールを置く高さ)
        for r in range(NPRE):   # 棚 → つなぎ → 棚 → …(どの棚も、最後のドミノのすぐ先、棚のはしにボールが1つ)
            foot = self.place_run(r, x0 + (520.0 if r > 0 and TRANS[r - 1] == "spring" else LEAD), ys[r], 1.0, rng, STEP_DY[r])
            br = BALL_R[r]
            x1 = self.run_end(r) + 6 + br + 6   # ボールの中心のすぐ先が棚のはし(少し押されるだけで落ちる)
            # 棚の面:平らなら1本、階段なら1枚ごとに段をつける
            pts = [(x0, foot[0][2] + 6)]
            for k in range(len(foot)):
                xl, xr, y = foot[k]
                if k + 1 < len(foot):
                    xm = (xr + foot[k + 1][0]) / 2
                    pts.append((xm, y + 6))
                    pts.append((xm, foot[k + 1][2] + 6))
                else:
                    pts.append((x1, y + 6))
            pts = [p_ for i_, p_ in enumerate(pts) if i_ == 0 or p_ != pts[i_ - 1]]
            for a_, b_ in zip(pts, pts[1:]):
                seg(a_, b_, 6, 0.8)
            self.parts.append(("shelf", r, pts))
            ends.append(x1)
            self.end_y.append(foot[-1][2])
            if r < NPRE - 1:
                x0 = self.connect(TRANS[r], r, x1, foot[-1][2] + 6, ys[r + 1] + 6, seg)
        p2x1 = ends[-1]
        # ジャンプ台:2段目の棚のはしから、なめらかに下ってから、けり上げ台で上へ
        pts = []
        for k in range(13):
            u = k / 12
            pts.append((p2x1 + JUMP_RUN * u, P2_Y + 6 + (JUMP_DROP) * (1 - math.cos(math.pi * u)) / 2))
        x_b, y_b = pts[-1]
        for k in range(1, 7):
            a = KICK_ANG * k / 6
            pts.append((x_b + KICK_R * math.sin(a), y_b - KICK_R * (1 - math.cos(a))))
        for a, b in zip(pts, pts[1:]):
            seg(a, b, 6, 0.5, 0.05)
        self.kick = pts[-1]
        kx, ky = pts[-1]
        seg((kx, ky), (kx, 6), 6)                                   # ジャンプ台の下(穴の手前のかべ)
        self.pit0 = kx
        self.pit1 = kx + PIT_W
        seg((self.pit0, 900), (self.pit1 + 200, 900))              # 穴の底
        seg((self.pit1, P3_Y + 6), (self.pit1, 900))               # 穴の向こうのかべ
        seg((self.pit1, P3_Y + 6), (self.pit1 + 2500, P3_Y + 6))   # 3段目の台
        seg((-500, 6), (self.pit0, 6))                              # 床
        self.place_run(NPRE, self.pit1 + LAND_RUN, P3_Y, GROW3, rng)
        self.balls = []
        for r in range(NPRE):
            last = r == NPRE - 1
            self.balls.append(self.add_ball(self.run_end(r) + 6 + rng.uniform(-2, 2), self.end_y[r], BALL_R[r],
                                            HB_DENS if last else BALL_DENS[r], BALL_KINDS[r]))
        self.hb = self.balls[-1]
        self.first_idx = [next(i for i, d in enumerate(self.doms) if d[2] == r) for r in range(NPRE + 1)]
        # 鐘(3列目の最後のドミノの先)
        hl = self.doms[-1][1]
        bx = self.run_end(NPRE) + 0.75 * hl + 40
        self.bell_x, self.bell_size = bx, 0.5 * hl
        bs = self.bell_size
        bell = pymunk.Poly(st, [(bx - 0.22 * bs, P3_Y - 1.25 * bs), (bx + 0.22 * bs, P3_Y - 1.25 * bs),
                                (bx + 0.55 * bs, P3_Y - 0.4 * bs), (bx - 0.55 * bs, P3_Y - 0.4 * bs)])
        bell.collision_type = CT_BELL
        sp.add(bell)
        self.bell_hit = None

        def on_dom(arb, space, data):
            a, b = arb.shapes
            ia, ib = self.idx.get(a), self.idx.get(b)
            if ia is None or ib is None:
                return True
            j_ = max(ia, ib)
            if abs(ia - ib) == 1 and j_ not in self.hit:
                self.hit[j_] = self.t
                self.events.append(("hit", self.t, j_))
            return True
        sp.on_collision(CT_DOM, CT_DOM, begin=on_dom)

        def on_ball_dom(arb, space, data):
            for s in arb.shapes:
                i = self.idx.get(s)
                if i is not None and i not in self.hit and self.doms[i][3] == 0:
                    self.hit[i] = self.t
                    self.events.append(("hit", self.t, i))
            return True
        sp.on_collision(1, CT_DOM, begin=on_ball_dom)

        def on_bell(arb, space, data):
            if self.bell_hit is None:
                self.bell_hit = self.t
                self.events.append(("bell", self.t, None))
            return True
        sp.on_collision(CT_DOM, CT_BELL, begin=on_bell)
        b0 = self.doms[0][0]
        b0.apply_impulse_at_local_point((b0.mass * 70, 0), (0, -DOM_H * 0.4))
        self.hit[0] = 0.0
        self.events.append(("hit", 0.0, 0))
        self.t = 0.0
        self.result, self.result_t = None, None
        self.last_move = 0.0
        self.launched = False
        self.landed = None
        self.fell_pit = False

    def connect(self, kind, r, x1, y_top, y_bot, seg):
        """棚と棚のつなぎ。次の棚がはじまる x を返す。"""
        st = self.space.static_body
        if kind == "zigzag":    # ジグザグのレール(右へ → 左へ → 右へ、かべで折り返す)
            rails = [((x1 - 30, y_top + 70), (x1 + 285, y_top + 185)),
                     ((x1 + 355, y_top + 270), (x1 + 48, y_top + 385)),
                     ((x1 - 30, y_top + 470), (x1 + 360, y_bot))]
            walls = [((x1 + 362, y_top + 40), (x1 + 362, y_top + 330)), ((x1 - 38, y_top + 250), (x1 - 38, y_top + 510))]
            for a_, b_ in rails:
                seg(a_, b_, 6, 0.6, 0.2)
            for a_, b_ in walls:
                seg(a_, b_, 6, 0.4, 0.3)
            self.parts.append(("rails", r, rails))
            self.parts.append(("walls", r, walls))
            return x1 + 360
        if kind == "pegs":      # ピンの森 → じょうご → すべり台
            L, R_ = x1 - 40, x1 + 300
            walls = [((L, y_top - 10), (L, y_top + 390)), ((R_, y_top - 10), (R_, y_top + 390))]
            for a_, b_ in walls:
                seg(a_, b_, 6, 0.4, 0.5)
            pegs = []
            for row in range(5):
                yy = y_top + 100 + row * 58
                off = 0 if row % 2 == 0 else 35
                for xx in np.arange(L + 30 + off, R_ - 15, 70):
                    c = pymunk.Circle(st, 6, (xx, yy))
                    c.friction, c.elasticity = 0.3, 1.6
                    c.collision_type = CT_PEG
                    self.space.add(c)
                    pegs.append((xx, yy))
            fun = [((L, y_top + 390), (x1 + 98, y_top + 470)), ((R_, y_top + 390), (x1 + 172, y_top + 470))]
            for a_, b_ in fun:
                seg(a_, b_, 6, 0.3, 0.2)
            chute = ((x1 + 70, y_top + 555), (x1 + 420, y_bot))
            seg(*chute, 6, 0.6)
            self.parts.append(("pegbox", r, (walls, pegs, fun, chute)))
            return x1 + 420
        if kind == "spring":    # バネの板で跳ねて、次の棚へ
            px, py = x1 + 70, y_top + 230
            ang = 0.5
            L = 120.0
            a_ = (px - L / 2 * math.cos(ang), py - L / 2 * math.sin(ang))
            b_ = (px + L / 2 * math.cos(ang), py + L / 2 * math.sin(ang))
            sp_ = pymunk.Segment(st, a_, b_, 7)
            sp_.friction, sp_.elasticity = 0.5, 2.6
            sp_.collision_type = CT_PEG
            self.space.add(sp_)
            self.statics.append((a_, b_, 7))
            self.parts.append(("spring", r, (a_, b_)))
            nx = x1 + 300
            seg((nx, y_bot), (nx, y_bot + 300), 6)
            return nx
        if kind == "valley":    # 深い谷(下って、勢いで向こう側へのぼる)
            L = 520.0
            x1 += 45                     # ボールが乗っている所は平らのまま、少し先から谷になる
            pts = [(x1 - 45, y_top)]
            for k in range(41):
                u = k / 40
                pts.append((x1 + L * u, y_top + (y_bot - y_top) * u + 420 * (1 - u) * math.sin(math.pi * u)))   # 入りは急、出口はなだらか
            for a_, b_ in zip(pts, pts[1:]):
                seg(a_, b_, 6, 0.8, 0.05)
            self.parts.append(("valley", r, pts))
            return x1 + L
        if kind == "seesaw":    # 急な坂 → シーソー橋(ボールが支点をこえると、かたむいて次の棚へ)
            ramp = ((x1, y_top), (x1 + 120, y_top + 140))
            seg(*ramp, 6, 0.6)
            P = (x1 + 290, y_top + 110)
            L = 340.0
            a0 = -0.2
            m = 3.0
            pb = pymunk.Body(m + 2.0, pymunk.moment_for_box(m, (L, 12)) + 2.0 * (L / 2 - 20) ** 2)
            pb.position = P
            pb.angle = a0
            ps = pymunk.Poly.create_box(pb, (L, 12), 1)
            ps.friction, ps.elasticity = 0.8, 0.05
            cw = pymunk.Circle(pb, 8, (-L / 2 + 20, 12))   # 左はしの下のおもり(はじめは左が下がっている)
            cw.mass = 2.0
            self.space.add(pb, ps, cw)
            self.space.add(pymunk.PivotJoint(st, pb, P))
            lim = pymunk.RotaryLimitJoint(st, pb, -0.2, 0.27)
            self.space.add(lim)
            self.seesaw = (pb, L)
            post = ((P[0], P[1] + 8), (P[0], y_bot + 300))
            self.parts.append(("seesaw", r, (ramp, P, post)))
            nx = P[0] + L / 2 * math.cos(0.27) - 6
            return nx
        raise ValueError(kind)

    def run_end(self, r):
        b, h, _, _ = [d for d in self.doms if d[2] == r][-1]
        return b.position.x + DOM_T * h / DOM_H / 2

    def place_run(self, r, x, y0, grow, rng, dy=0.0):
        """ドミノを1列ならべる。dy が 0 でなければ、1枚ごとに段差のある階段の上に置く。足もとの (左, 右, 高さ) を返す。"""
        h = DOM_H
        foot = []
        y = y0
        for k in range(len(RUNS[r])):
            t = DOM_T * h / DOM_H
            m = t * h / 100
            b = pymunk.Body(m, pymunk.moment_for_box(m, (t, h)))
            b.position = (x + t / 2, y - h / 2)
            s = pymunk.Poly.create_box(b, (t, h))
            s.friction, s.elasticity = 0.6, 0.05
            s.collision_type = CT_DOM
            self.space.add(b, s)
            self.idx[s] = len(self.doms)
            self.doms.append((b, h, r, k))
            foot.append((x, x + t, y))
            x += t + h * GAP * (1 + rng.uniform(-JIT, JIT))
            h *= grow
            y += dy
        return foot

    def add_ball(self, x, y, r, dens, kind, raw=False):
        m = dens * math.pi * r * r
        b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, r))
        b.position = (x, y) if raw else (x + r, y - r)
        s = pymunk.Circle(b, r)
        s.friction, s.elasticity = 0.8, 0.3
        s.collision_type = 1
        self.space.add(b, s)
        b.kind = kind
        return b

    def step(self, dt):
        self.t += dt
        self.space.step(dt)
        # 役目を終えたボール(次の列のドミノがもう倒れはじめた)は、転がり抵抗でだんだん止まる(ずっと動き続けないように)
        for r, b in enumerate(self.balls[:-1]):
            if self.first_idx[r + 1] in self.hit:
                b.velocity = b.velocity * (1 - 1.5 * dt)
                b.angular_velocity *= (1 - 1.5 * dt)
        moving = any(abs(b.angular_velocity) > 0.2 for b, *_ in self.doms) or \
            any(b.velocity.length > 15 for b in self.balls)
        if moving:
            self.last_move = self.t
        g = self.hb
        if not self.launched and g.position.x > self.kick[0] - 5:
            self.launched = True
            self.events.append(("launch", self.t, tuple(g.velocity)))
        if self.launched and self.landed is None and g.position.x > self.pit1 and g.position.y > P3_Y - HB_R - 8:
            self.landed = self.t
            self.events.append(("land", self.t, g.position.x - self.pit1))
        if not self.fell_pit and g.position.y > 60 and self.pit0 < g.position.x < self.pit1 + 5:
            self.fell_pit = True
            self.events.append(("pit", self.t, None))
        if self.result is None:
            if self.bell_hit is not None:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.fell_pit and self.t > 0:
                self.result, self.result_t = "fail", self.t + 0.6
                self.events.append(("fail", self.t + 0.6, "pit"))
            elif self.t - self.last_move > STOP_WAIT:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, "stop"))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "doms": [(b.position.x, b.position.y, b.angle) for b, *_ in g.doms],
                           "balls": [(b.position.x, b.position.y, b.angle) for b in g.balls],
                           "seesaw": (g.seesaw[0].position.x, g.seesaw[0].position.y, g.seesaw[0].angle) if g.seesaw else None})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
        if g.t > 90:
            break
    stage = 3 if g.landed else (2 if g.launched else 1)
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "stage": stage,
            "fell": len(g.hit), "n": len(g.doms), "hs": [h for _, h, _, _ in g.doms],
            "info": [(r, k) for _, _, r, k in g.doms], "bell_x": g.bell_x, "bell_size": g.bell_size,
            "statics": g.statics, "hit": dict(g.hit), "parts": g.parts,
            "fail_kind": next((e[2] for e in g.events if e[0] == "fail"), None),
            "land_x": next((e[2] for e in g.events if e[0] == "land"), None), "pit": (g.pit0, g.pit1)}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"] and round(r["result_t"], 1), r["stage"], r["fell"], r["fail_kind"], r["land_x"] and round(r["land_x"])


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    from collections import Counter
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件", sorted(Counter((r[3], r[5]) for r in rs).items(), key=str))
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
NOTE_COLS = {0: (1.0, 0.35, 0.35), 2: (1.0, 0.6, 0.2), 4: (1.0, 0.88, 0.25), 5: (0.45, 0.85, 0.35),
             7: (0.3, 0.75, 1.0), 9: (0.45, 0.45, 1.0), 11: (0.8, 0.45, 1.0)}


def note_col(m):
    return NOTE_COLS.get(m % 12, (0.9, 0.9, 0.9))


THEME_NAMES = ["木の部屋", "氷の世界", "草原", "工場", "お菓子の国", "金のステージ"]
THEME_BG = [((0.98, 0.9, 0.78), (0.9, 0.75, 0.6)), ((0.86, 0.94, 1.0), (0.62, 0.78, 0.95)),
            ((0.5, 0.78, 1.0), (0.85, 0.95, 0.8)), ((0.56, 0.59, 0.65), (0.33, 0.35, 0.4)),
            ((1.0, 0.86, 0.93), (0.98, 0.68, 0.82)), ((0.2, 0.1, 0.3), (0.45, 0.22, 0.38))]
THEME_MAT = [(0.72, 0.5, 0.3), (0.72, 0.9, 1.0), (0.45, 0.32, 0.2), (0.6, 0.62, 0.66), (1.0, 0.55, 0.72), (0.95, 0.75, 0.3)]


def theme_weights(x, bounds):
    """カメラの位置 x での、テーマごとの重み(境目の前後300でなめらかに切りかわる)。"""
    w = [0.0] * len(THEME_BG)
    k = 0
    while k < len(bounds) and x > bounds[k]:
        k += 1
    w[k] = 1.0
    for j, xb in enumerate(bounds):   # 境目の近くは、となりのテーマとまぜる
        u = (x - (xb - 300)) / 600
        if 0 < u < 1:
            u = u * u * (3 - 2 * u)
            w = [0.0] * len(THEME_BG)
            w[j], w[j + 1] = 1 - u, u
    return w


def draw_room(ctx, cx, t, w):
    top = [sum(w[k] * THEME_BG[k][0][c] for k in range(len(w))) for c in range(3)]
    bot = [sum(w[k] * THEME_BG[k][1][c] for k in range(len(w))) for c in range(3)]
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *top)
    g.add_color_stop_rgb(1, *bot)
    ctx.set_source(g)
    ctx.paint()
    rng = np.random.default_rng(1)
    if w[0] > 0.01:   # 木の部屋:かべのしま模様
        off = (cx * 0.3) % 120
        for k in range(-1, 11):
            ctx.rectangle(k * 120 - off, 0, 60, H)
        ctx.set_source_rgba(1, 1, 1, 0.18 * w[0])
        ctx.fill()
    if w[1] > 0.01:   # 氷の世界:雪
        for k in range(70):
            x = (rng.uniform(0, W + 200) - cx * 0.2 + 30 * math.sin(t + k)) % (W + 100) - 50
            y = (rng.uniform(0, H) + t * rng.uniform(60, 140)) % H
            ctx.arc(x, y, rng.uniform(3, 8), 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, 0.8 * w[1])
            ctx.fill()
    if w[2] > 0.01:   # 草原:雲と遠くの丘
        for k in range(5):
            x = (rng.uniform(0, 1600) - cx * 0.15) % 1500 - 200
            y = rng.uniform(450, 900)
            for dx, dy, r in ((0, 0, 60), (55, 10, 50), (-55, 12, 45), (25, -30, 45)):
                ctx.arc(x + dx, y + dy, r, 0, 2 * math.pi)
                ctx.set_source_rgba(1, 1, 1, 0.85 * w[2])
                ctx.fill()
        for k in range(4):
            x = (k * 420 - cx * 0.1) % 1700 - 300
            ctx.arc(x, H + 120, 420, math.pi, 2 * math.pi)
            ctx.set_source_rgba(0.35, 0.7, 0.35, 0.7 * w[2])
            ctx.fill()
    if w[3] > 0.01:   # 工場:パイプと歯車
        for k in range(6):
            y = 500 + k * 230
            ctx.rectangle(0, y, W, 26)
            ctx.set_source_rgba(0.42, 0.45, 0.5, 0.8 * w[3])
            ctx.fill()
        for k in range(4):
            x = (k * 380 - cx * 0.25) % 1500 - 200
            y = 700 + (k % 2) * 520
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(t * (0.8 if k % 2 else -0.8))
            for j in range(10):
                ctx.rotate(math.pi / 5)
                ctx.rectangle(-16, -110, 32, 40)
            ctx.arc(0, 0, 80, 0, 2 * math.pi)
            ctx.set_source_rgba(0.3, 0.32, 0.36, 0.75 * w[3])
            ctx.fill()
            ctx.restore()
    if w[4] > 0.01:   # お菓子の国:水玉
        off = (cx * 0.25) % 160
        for yy in range(0, H + 160, 160):
            for xx in range(-160, W + 160, 160):
                ctx.arc(xx - off + (80 if (yy // 160) % 2 else 0), yy, 26, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.5 * w[4])
        ctx.fill()
    if w[5] > 0.01:   # 金のステージ:きらきら
        for k in range(50):
            x = rng.uniform(0, W)
            y = rng.uniform(0, H)
            a = 0.5 + 0.5 * math.sin(t * 4 + k)
            ctx.arc(x, y, rng.uniform(2, 5), 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.9, 0.5, a * w[5])
            ctx.fill()


def draw_mat(ctx, a, b, th, thick=16):
    """テーマごとの材質の板(木・氷・草・鉄・お菓子・金)。"""
    (x0, y0), (x1, y1) = a, b
    ang = math.atan2(y1 - y0, x1 - x0)
    L = math.hypot(x1 - x0, y1 - y0)
    col = THEME_MAT[th]
    ctx.save()
    ctx.translate(x0, y0)
    ctx.rotate(ang)
    ctx.rectangle(-2, -6, L + 4, thick)
    g = cairo.LinearGradient(0, -6, 0, thick - 6)
    g.add_color_stop_rgb(0, *(min(1, c * 1.15) for c in col))
    g.add_color_stop_rgb(1, *(c * 0.7 for c in col))
    ctx.set_source(g)
    ctx.fill()
    if th == 1:     # 氷:白いつや
        ctx.rectangle(0, -6, L, 4)
        ctx.set_source_rgba(1, 1, 1, 0.8)
        ctx.fill()
    elif th == 2:   # 草:上に緑のしばふ
        ctx.rectangle(-2, -9, L + 4, 7)
        ctx.set_source_rgb(0.3, 0.75, 0.25)
        ctx.fill()
    elif th == 3:   # 鉄:リベット
        for xx in np.arange(8, L, 30):
            ctx.arc(xx, 2, 2.5, 0, 2 * math.pi)
        ctx.set_source_rgba(0.25, 0.25, 0.28, 0.9)
        ctx.fill()
    elif th == 4:   # お菓子:ピンクと白のしま
        for xx in np.arange(0, L, 24):
            ctx.move_to(xx, -6)
            ctx.line_to(xx + 12, -6)
            ctx.line_to(xx + 2, thick - 6)
            ctx.line_to(xx - 10, thick - 6)
            ctx.close_path()
        ctx.set_source_rgba(1, 1, 1, 0.85)
        ctx.fill()
    ctx.restore()


def draw_wood(ctx, a, b, thick=16):
    (x0, y0), (x1, y1) = a, b
    ang = math.atan2(y1 - y0, x1 - x0)
    L = math.hypot(x1 - x0, y1 - y0)
    ctx.save()
    ctx.translate(x0, y0)
    ctx.rotate(ang)
    ctx.rectangle(-4, -6, L + 8, thick)
    g = cairo.LinearGradient(0, -6, 0, thick - 6)
    g.add_color_stop_rgb(0, 0.78, 0.55, 0.32)
    g.add_color_stop_rgb(1, 0.5, 0.32, 0.18)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.3, 0.18, 0.08, 0.8)
    ctx.set_line_width(1.5)
    ctx.stroke()
    ctx.restore()


def draw_domino(ctx, x, y, ang, h, col, glow, giant=False):
    w = DOM_T * h / DOM_H
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    r_ = min(w, h) * 0.18
    ctx.new_path()
    ctx.arc(-w / 2 + r_, -h / 2 + r_, r_, math.pi, 1.5 * math.pi)
    ctx.arc(w / 2 - r_, -h / 2 + r_, r_, 1.5 * math.pi, 2 * math.pi)
    ctx.arc(w / 2 - r_, h / 2 - r_, r_, 0, 0.5 * math.pi)
    ctx.arc(-w / 2 + r_, h / 2 - r_, r_, 0.5 * math.pi, math.pi)
    ctx.close_path()
    g = cairo.LinearGradient(-w / 2, 0, w / 2, 0)
    g.add_color_stop_rgb(0, *(min(1, c * 1.15 + glow * 0.5) for c in col))
    g.add_color_stop_rgb(1, *(min(1, c * 0.7 + glow * 0.5) for c in col))
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(0, 0, 0, 0.5)
    ctx.set_line_width(max(1.2, w * 0.08))
    ctx.stroke()
    ctx.set_source_rgba(1, 1, 1, 0.85)   # ドミノの点
    for py in (-h * 0.28, h * 0.22):
        ctx.arc(0, py, w * 0.16, 0, 2 * math.pi)
        ctx.fill()
    if glow > 0:
        ctx.rectangle(-w, -h / 2 - w, 2 * w, h + 2 * w)
        ctx.set_source_rgba(1, 1, 0.8, 0.25 * glow)
        ctx.fill()
    ctx.restore()


def draw_ball(ctx, x, y, ang, r, kind):
    def shade(base, hi=0.5):
        g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r)
        g.add_color_stop_rgb(0, *(min(1, c + hi) for c in base))
        g.add_color_stop_rgb(0.55, *base)
        g.add_color_stop_rgb(1, *(c * 0.4 for c in base))
        ctx.set_source(g)
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.fill()
    ctx.save()
    if kind == "rubber":        # 赤いゴムボール
        shade((0.9, 0.15, 0.15))
        ctx.translate(x, y)
        ctx.rotate(ang)
        ctx.arc(0, 0, r * 0.98, -0.5, 0.5)
        ctx.set_source_rgba(1, 1, 1, 0.7)
        ctx.set_line_width(r * 0.18)
        ctx.stroke()
    elif kind == "marble":      # ガラス玉(すきとおった青)
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.set_source_rgba(0.35, 0.65, 1.0, 0.45)
        ctx.fill()
        ctx.translate(x, y)
        ctx.rotate(ang)
        ctx.move_to(-r * 0.6, 0)
        ctx.curve_to(-r * 0.2, -r * 0.5, r * 0.2, r * 0.5, r * 0.6, 0)
        ctx.set_source_rgba(0.1, 0.4, 1.0, 0.9)
        ctx.set_line_width(r * 0.22)
        ctx.stroke()
        ctx.rotate(-ang)
        ctx.arc(-r * 0.35, -r * 0.4, r * 0.22, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.fill()
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.set_source_rgba(0.1, 0.3, 0.6, 0.8)
        ctx.set_line_width(2)
        ctx.stroke()
    elif kind == "soccer":      # サッカーボール(どこのメーカーにも似せない、白と黒の模様)
        shade((0.95, 0.95, 0.95), 0.1)
        ctx.translate(x, y)
        ctx.rotate(ang)
        for k in range(6):
            a = k * math.pi / 3
            d = 0 if k == 0 else r * 0.62
            cx_, cy_ = (0, 0) if k == 0 else (d * math.cos(a), d * math.sin(a))
            ctx.new_path()
            for j in range(5):
                b_ = j * 2 * math.pi / 5 + a
                ctx.line_to(cx_ + r * 0.24 * math.cos(b_), cy_ + r * 0.24 * math.sin(b_))
            ctx.close_path()
            ctx.set_source_rgb(0.1, 0.1, 0.1)
            ctx.fill()
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.set_line_width(1.5)
        ctx.stroke()
    elif kind == "basket":      # バスケットボール(オレンジに黒い線)
        shade((0.95, 0.5, 0.12))
        ctx.translate(x, y)
        ctx.rotate(ang)
        ctx.set_source_rgba(0.1, 0.05, 0.02, 0.9)
        ctx.set_line_width(r * 0.07)
        ctx.move_to(-r, 0)
        ctx.line_to(r, 0)
        ctx.move_to(0, -r)
        ctx.line_to(0, r)
        ctx.stroke()
        ctx.arc(-r * 1.25, 0, r * 0.9, -0.95, 0.95)
        ctx.stroke()
        ctx.arc(r * 1.25, 0, r * 0.9, math.pi - 0.95, math.pi + 0.95)
        ctx.stroke()
    else:                       # ボウリングの玉(むらさき・指の穴3つ)
        shade((0.35, 0.15, 0.5), 0.35)
        ctx.translate(x, y)
        ctx.rotate(ang)
        for dx, dy in ((r * 0.25, -r * 0.35), (r * 0.5, -r * 0.1), (r * 0.15, r * 0.15)):
            ctx.arc(dx, dy, r * 0.11, 0, 2 * math.pi)
            ctx.set_source_rgb(0.05, 0.02, 0.08)
            ctx.fill()
    ctx.restore()


def draw_rail(ctx, a, b, w=10):
    """鉄のレール(銀色・2本線)。"""
    ctx.save()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(*a)
    ctx.line_to(*b)
    ctx.set_source_rgb(0.35, 0.37, 0.42)
    ctx.set_line_width(w + 4)
    ctx.stroke()
    ctx.move_to(*a)
    ctx.line_to(*b)
    ctx.set_source_rgb(0.82, 0.84, 0.88)
    ctx.set_line_width(w - 3)
    ctx.stroke()
    ctx.restore()


def draw_parts(ctx, parts, t, seesaw):
    """棚(平ら・階段)と、棚と棚のつなぎ(ジグザグのレール・バネ板・谷・シーソー橋)。"""
    for kind, r, d in parts:
        if kind == "shelf":
            if len(d) > 2:   # 階段の棚:下を木でうめる
                ctx.new_path()
                for p_ in d:
                    ctx.line_to(*p_)
                ctx.line_to(d[-1][0], max(p_[1] for p_ in d) + 30)
                ctx.line_to(d[0][0], max(p_[1] for p_ in d) + 30)
                ctx.close_path()
                ctx.set_source_rgb(0.62, 0.43, 0.25)
                ctx.fill()
            for a_, b_ in zip(d, d[1:]):
                if a_[0] != b_[0]:
                    draw_mat(ctx, a_, b_, 0)
        elif kind == "rails":
            for a_, b_ in d:
                draw_rail(ctx, a_, b_)
        elif kind == "walls":
            for a_, b_ in d:
                draw_rail(ctx, a_, b_, 12)
        elif kind == "valley":
            ctx.new_path()
            for p_ in d:
                ctx.line_to(*p_)
            bottom = max(p_[1] for p_ in d) + 40
            ctx.line_to(d[-1][0], bottom)
            ctx.line_to(d[0][0], bottom)
            ctx.close_path()
            g = cairo.LinearGradient(0, d[0][1], 0, bottom)
            g.add_color_stop_rgb(0, 0.7, 0.5, 0.3)
            g.add_color_stop_rgb(1, 0.5, 0.34, 0.2)
            ctx.set_source(g)
            ctx.fill()
            for a_, b_ in zip(d, d[1:]):
                draw_mat(ctx, a_, b_, 0)
        elif kind == "spring":
            (x0, y0), (x1, y1) = d
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            ctx.set_source_rgb(0.35, 0.36, 0.4)   # バネ(ジグザグ)
            ctx.set_line_width(5)
            ctx.move_to(mx, my + 8)
            for k in range(8):
                ctx.line_to(mx + (14 if k % 2 == 0 else -14), my + 8 + (k + 1) * 14)
            ctx.stroke()
            ctx.rectangle(mx - 30, my + 8 + 8 * 14, 60, 12)
            ctx.fill()
            draw_mat(ctx, d[0], d[1], 3)
            ctx.move_to(x0, y0 - 9)
            ctx.line_to(x1, y1 - 9)
            ctx.set_source_rgb(1.0, 0.55, 0.1)
            ctx.set_line_width(5)
            ctx.stroke()
        elif kind == "seesaw":
            ramp, P, post = d
            draw_mat(ctx, ramp[0], ramp[1], 0)
            ctx.move_to(P[0] - 34, post[1][1])   # 支点の台(三角)
            ctx.line_to(P[0] + 34, post[1][1])
            ctx.line_to(P[0], P[1] + 6)
            ctx.close_path()
            ctx.set_source_rgb(0.45, 0.3, 0.18)
            ctx.fill()
            if seesaw is not None:
                sx, sy, sa = seesaw
                L = 340.0
                a_ = (sx - L / 2 * math.cos(sa), sy - L / 2 * math.sin(sa))
                b_ = (sx + L / 2 * math.cos(sa), sy + L / 2 * math.sin(sa))
                draw_mat(ctx, a_, b_, 4)
                ctx.arc(sx, sy, 9, 0, 2 * math.pi)
                ctx.set_source_rgb(0.3, 0.3, 0.32)
                ctx.fill()


def draw_bell(ctx, x, y_base, s, swing):
    ctx.save()
    ctx.set_source_rgb(0.4, 0.28, 0.15)   # つるす台
    ctx.set_line_width(s * 0.08)
    ctx.move_to(x + s * 0.9, y_base)
    ctx.line_to(x + s * 0.9, y_base - s * 1.7)
    ctx.line_to(x, y_base - s * 1.7)
    ctx.stroke()
    ctx.translate(x, y_base - s * 1.7)
    ctx.rotate(swing)
    ctx.move_to(0, 0)
    ctx.line_to(0, s * 0.4)
    ctx.stroke()
    ctx.translate(0, s * 0.45)
    ctx.move_to(-s * 0.22, 0)
    ctx.line_to(s * 0.22, 0)
    ctx.curve_to(s * 0.3, s * 0.5, s * 0.45, s * 0.7, s * 0.6, s * 0.85)
    ctx.line_to(-s * 0.6, s * 0.85)
    ctx.curve_to(-s * 0.45, s * 0.7, -s * 0.3, s * 0.5, -s * 0.22, 0)
    ctx.close_path()
    g = cairo.LinearGradient(-s * 0.6, 0, s * 0.6, 0)
    g.add_color_stop_rgb(0, 0.75, 0.55, 0.1)
    g.add_color_stop_rgb(0.4, 1, 0.9, 0.45)
    g.add_color_stop_rgb(1, 0.6, 0.42, 0.08)
    ctx.set_source(g)
    ctx.fill()
    ctx.restore()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    hs, info, hit = res["hs"], res["info"], res["hit"]
    pit0, pit1 = res["pit"]
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"domino_machine_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"domino_machine_{seed}.wav")
    final = os.path.join(OUT_DIR, f"domino_machine_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"dm_preview_{pt:.1f}.png"))
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
    angels = AngelShow(W, H, seed) if result == "success" else None
    statics = res["statics"]
    parts = res["parts"]
    bounds = [p_[2][0][0] for p_ in parts if p_[0] == "shelf" and p_[1] > 0] + [pit1 - 150]
    cur_stage, stage_t = 0, -9.0
    launch_t = next((e[1] for e in events if e[0] == "launch"), None)
    land_t = next((e[1] for e in events if e[0] == "land"), None)
    pit_t = next((e[1] for e in events if e[0] == "pit"), None)
    bell_t = next((e[1] for e in events if e[0] == "bell"), None)
    cam_x, cam_y, cam_s = frames[0]["doms"][0][0] + 250, P0_Y - 60, 1.85
    ball_r = BALL_R
    kinds = BALL_KINDS
    run_start = [next(i for i, (r, k) in enumerate(info) if r == rr) for rr in range(NPRE + 1)]
    jump_x0 = max(max(a[0], b[0]) for a, b, r in statics if abs(a[1] - (P2_Y + 6)) < 1 and abs(b[1] - (P2_Y + 6)) < 1)
    for fi, fr in enumerate(frames):
        t = fr["t"]
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0
        # カメラ:いま動いている所(最後に倒れたドミノ・転がっているボール)を追う
        hit_now = [i for i, ht in hit.items() if ht <= t]
        last = max(hit_now, default=0)
        tx, ty = fr["doms"][last][0] + 120, fr["doms"][last][1] - 40
        for bi, (bx, by, ba) in enumerate(fr["balls"]):
            if hit.get(run_start[bi + 1], 1e9) <= t:   # 役目を終えたボールは追わない
                continue
            prev = frames[fi - 1]["balls"][bi] if fi else (bx, by, ba)
            v = math.hypot(bx - prev[0], by - prev[1]) * FPS
            if v > 60 and by < 800:
                tx, ty = bx + 160, by - 40
        if bell_t is not None and t > bell_t - 0.5:
            tx, ty = res["bell_x"] - 100, P3_Y - res["bell_size"] * 1.2
        tgt_s = 1.85
        hbx = fr["balls"][-1][0]
        if pit0 - 650 < hbx < pit1 + 250 and (land_t is None or t < land_t + 0.6):   # ジャンプのあたりは穴が見えるように引く
            tgt_s = 1.2
        elif info[last][0] == NPRE and hit.get(run_start[NPRE], 1e9) <= t:
            tgt_s = 1.85 * (DOM_H / hs[last]) ** 0.6
        cam_x += (tx - cam_x) * 0.07
        cam_y += (ty - cam_y) * 0.07
        cam_s += (tgt_s - cam_s) * 0.04
        tw = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]   # 背景はずっと同じ部屋(変えるのはコースの形)
        draw_room(ctx, cam_x, t, tw)
        st_now = max(range(len(tw)), key=lambda k: tw[k])
        if st_now > cur_stage:   # 新しい段に入ったときだけ名前を出す(もどったときは出さない)
            cur_stage = st_now
            stage_t = t
        ctx.save()
        ctx.translate(W / 2, H * 0.56)
        ctx.scale(cam_s, cam_s)
        ctx.translate(-cam_x, -cam_y)
        # 床・穴
        ctx.rectangle(-3000, 6, pit0 + 3000, 2000)
        ctx.rectangle(pit1, 6, 6000, 2000)
        ctx.set_source_rgb(0.55, 0.38, 0.24)
        ctx.fill()
        g = cairo.LinearGradient(0, 0, 0, 900)
        g.add_color_stop_rgb(0, 0.15, 0.1, 0.08)
        g.add_color_stop_rgb(1, 0.02, 0.02, 0.02)
        ctx.rectangle(pit0, 6, pit1 - pit0, 2000)
        ctx.set_source(g)
        ctx.fill()
        # 着地する台(金のステージ)
        ctx.rectangle(pit1, P3_Y + 6, 6000, -P3_Y)
        g = cairo.LinearGradient(0, P3_Y, 0, 6)
        g.add_color_stop_rgb(0, 0.95, 0.75, 0.3)
        g.add_color_stop_rgb(1, 0.6, 0.42, 0.15)
        ctx.set_source(g)
        ctx.fill()
        # ジャンプ台の下を、床までの木の台でうめる
        jp = sorted({p_ for a, b, r in statics for p_ in (a, b)
                     if a[0] != b[0] and jump_x0 - 1 <= min(a[0], b[0]) and max(a[0], b[0]) <= pit0 + 1 and a[1] < 0})
        if jp:
            ctx.new_path()
            ctx.move_to(jp[0][0], 6)
            for p_ in jp:
                ctx.line_to(*p_)
            ctx.line_to(jp[-1][0], 6)
            ctx.close_path()
            g = cairo.LinearGradient(0, P2_Y, 0, 6)
            g.add_color_stop_rgb(0, 0.7, 0.5, 0.3)
            g.add_color_stop_rgb(1, 0.5, 0.34, 0.2)
            ctx.set_source(g)
            ctx.fill()
        draw_parts(ctx, parts, t, fr.get("seesaw"))
        for a, b, r in statics:   # ジャンプ台(お菓子)
            if a[0] == b[0] or a[1] > 100 or not (jump_x0 - 1 <= min(a[0], b[0]) <= pit0 + 1):
                continue
            draw_mat(ctx, a, b, 0)
        # 棚の脚(棚と同じ材質の色)
        for r in range(NPRE):
            pts_ = [p_[2] for p_ in parts if p_[0] == "shelf" and p_[1] == r][0]
            ctx.set_source_rgb(0.45, 0.3, 0.18)
            for x_, sy in ((pts_[0][0] + 40, pts_[0][1]), (pts_[-1][0] - 40, pts_[-1][1])):
                ctx.rectangle(x_ - 7, sy + 10, 14, -sy - 4)
                ctx.fill()
        # 鐘
        swing = 0.0
        if bell_t is not None and t >= bell_t:
            a_ = t - bell_t
            swing = 0.4 * math.exp(-a_ * 1.2) * math.sin(a_ * 7)
        draw_bell(ctx, res["bell_x"], P3_Y, res["bell_size"] * 1.6, swing)
        # ドミノ
        for i, (x, y, ang) in enumerate(fr["doms"]):
            r_, k_ = info[i]
            m = RUNS[r_][k_]
            ht = hit.get(i)
            glow = max(0.0, 1 - (t - ht) / 0.25) if ht is not None and t >= ht else 0.0
            col = note_col(m)
            if i == len(info) - 1:
                col = (1.0, 0.82, 0.3)
            draw_domino(ctx, x, y, ang, hs[i], col, glow)
        for bi, (bx, by, ba) in enumerate(fr["balls"]):
            draw_ball(ctx, bx, by, ba, ball_r[bi], kinds[bi])
        ctx.restore()
        if angels is not None and over:
            angels.draw(ctx, t - end_t)
        g = cairo.LinearGradient(0, 0, 0, 400)
        g.add_color_stop_rgba(0, 0.25, 0.12, 0.05, 0.85)
        g.add_color_stop_rgba(1, 0.25, 0.12, 0.05, 0.0)
        ctx.rectangle(0, 0, W, 400)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, "ドミノとボールで", W / 2, 120, 76, sw=12)
        text(ctx, "「歓喜の歌」を", W / 2, 230, 96, rgb=GOLD, sw=16)
        text(ctx, "最後まで演奏できる？", W / 2, 335, 80, rgb=GOLD, sw=14)
        n = len(hit_now)
        text(ctx, f"♪ {n} / {len(info)}", W / 2, 1800, 70, sw=12)
        if cur_stage > 0 and 0 <= t - stage_t < 1.5 and not over and not (pit_t is not None and t >= pit_t - 0.3):
            k2 = min(1.0, (t - stage_t) / 0.15)
            text(ctx, THEME_NAMES[cur_stage], W / 2, 780, 96 * (1.25 - 0.25 * k2),
                 rgb=tuple(min(1, c * 1.1 + 0.15) for c in THEME_MAT[cur_stage]), sw=16)
        falling = pit_t is not None and t >= pit_t - 0.3
        if launch_t is not None and 0 <= t - launch_t < 1.4 and not over and not falling:
            k2 = min(1.0, (t - launch_t) / 0.12)
            text(ctx, "ジャンプ!!", W / 2, 520, 110 * (1.25 - 0.25 * k2), rgb=(1, 0.6, 0.2), sw=18)
        if land_t is not None and 0 <= t - land_t < 1.2:
            text(ctx, "着地!!", W / 2, 520, 110, rgb=(0.5, 1, 0.6), sw=18)
        if pit_t is not None and t >= pit_t - 0.3 and not over:
            text(ctx, "あっ…!", W / 2, 520, 110, rgb=(1, 0.4, 0.4), sw=18)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "落ちた…" if res["fail_kind"] == "pit" else "止まった…", W / 2, 900, 130 * (1.3 - 0.3 * k),
                 rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{len(info) - n}音だったのに…", W / 2, 1030, 72, sw=12)
        elif over:
            age = t - end_t
            if age < 0.3:
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.8 * (1 - age / 0.3))
                ctx.fill()
            text(ctx, "演奏成功!!", W / 2, 640, 120, rgb=GOLD, sw=18)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {len(hit)}/{len(info)}音 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
sys.path.insert(0, os.path.join(HERE, "..", "giant_domino"))
import giant_domino as GD  # noqa: E402

HOLY_GAIN = 0.85


def bass_root(m):
    return 36 if m % 12 in (0, 4, 9) else 43   # C か G


def note_sound(r, k, m):
    f = midi_hz(m)
    if r == 0:
        return GD.music_box(f * 2, 0.6)
    if r == 1:
        return GD.mix(GD.music_box(f * 2, 0.45), GD.piano(f, 0.35), GD.piano(midi_hz(bass_root(m) + 12), 0.2))
    if r == 2:
        return GD.mix(GD.piano(f, 0.6), GD.piano(midi_hz(bass_root(m) + 12), 0.25), GD.strings(f, 0.15, 0.4))
    if r < NPRE:
        return GD.mix(GD.piano(f, 0.55), GD.strings(f, 0.25, 0.5), GD.brass(f, 0.18, 0.4), GD.piano(midi_hz(bass_root(m)), 0.3))
    big = k / max(1, len(RUNS[NPRE]) - 1)
    return GD.mix(GD.piano(f, 0.5), GD.strings(f, 0.3 + 0.2 * big, 0.6), GD.brass(f, 0.2 + 0.35 * big, 0.5),
                  GD.brass(midi_hz(bass_root(m)), 0.3 + 0.2 * big, 0.5))


def thud(seed, amp, f=90):
    t = GD._t(0.4)
    n = np.random.default_rng(seed).normal(0, 1, len(t))
    return amp * (np.sin(2 * np.pi * f * t) * np.exp(-t * 14) + 0.4 * np.convolve(n, np.ones(8) / 8, "same") * np.exp(-t * 25))


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    info = res["info"]
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)

    def add(sig, t0, gain=1.0, buf=None):
        b = out if buf is None else buf
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out and j > i:
            b[i:j] += gain * sig[: j - i]

    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.02:
            continue
        if kind == "hit":
            r, k = info[data]
            add(GD.click(30 * res["hs"][data] / DOM_H, data), t, 0.25)
            add(note_sound(r, k, RUNS[r][k]), t)
        elif kind == "launch":
            add(GD.whoosh(0.5), t, 1.0)
        elif kind == "land":
            add(thud(5, 0.9), t)
        elif kind == "pit":
            add(thud(7, 1.0, 60), t)
        elif kind == "bell":
            add(GD.bell_sound(1.2), t)
            for m_, a in ((48, 0.6), (55, 0.45), (60, 0.55), (64, 0.45), (67, 0.4), (72, 0.35)):
                add(GD.mix(GD.brass(midi_hz(m_), a, 2.0), GD.strings(midi_hz(m_), a * 0.6, 2.5)), t + 0.04)
            add(GD.timpani(1.0, 2.2), t)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
        sig = fail_music(SR, OUTRO)   # 幽霊のあとの、しょんぼりBGM
        i0 = int((end_t + SCARE_DUR) * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += 0.6 * sig[:m]
    elif end_t is not None:
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(end_t * SR) + int(1.8 * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += HOLY_GAIN * sig[:m]
    wet = out.copy()
    for dd, g in ((0.047, 0.28), (0.079, 0.2), (0.121, 0.13)):
        k = int(dd * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int((end_t or duration) * SR)]
    rms = np.sqrt(np.mean(body ** 2)) if len(body) else 0
    if rms > 0:
        wet *= min(4.0, 10 ** (-14.0 / 20) / rms)
    wet = wet + (0.95 if fail else 1.0) * extra[: len(wet)]
    mag = np.abs(wet)
    wet = np.where(mag < 0.7, wet, np.sign(wet) * (0.7 + 0.25 * np.tanh((mag - 0.7) / 0.25)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


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
