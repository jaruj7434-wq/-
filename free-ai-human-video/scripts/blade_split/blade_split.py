"""「おじさんフルーツを350人に増やせる?」円形の場所で2枚の刃が逆向き・別の速さで回り、刃と刃にはさまれると増殖する物理ショート。

- 円の中を、顔のついたおじさんフルーツ(Higgs Field で生成した写真6種類)が、かべや刃に当たりながら跳ね返り続ける
  (重力なし・止まらずに同じ速さで飛び回る)。
- まん中の軸から2枚の刃がのびていて、1枚は時計回り、もう1枚は反時計回りに、ちがう速さで回る(一定の速さ)。
- 2枚の刃が近づいて重なるとき、そのあいだ(せまくなっていくすきま)にはさまれたおじさんは見えなくなり、
  刃が重なり終わると2人に増えて内側と外側へはじき出される(1人なら2人、5人なら10人)。ねらってはさむことはしない(補正なし)。
- 制限時間内に TARGET 人になれば成功(おじさんフィーバー)、ならなければ失敗(幽霊)。

使い方:
    python blade_split.py search [--want fail|success] [-n 200]
    python blade_split.py render --seed N
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
from ball_escape import text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
sys.path.insert(0, HERE)
import ojisan as OJ  # noqa: E402
import blade_fever as FV  # noqa: E402
import ojisan_voice as OV  # noqa: E402   増殖した瞬間のおじさんの声
sys.path.insert(0, os.path.join(HERE, "..", "press_split"))
from press_split import note_hz, pop, hiss  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 4
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

# ---------------------------------------------------------------- 物理の設定
TARGET = int(os.environ.get("TARGET", 350))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 29.9))
OBJ_R = float(os.environ.get("OBJ_R", 20.0))            # おじさんの大きさ(半径)
SPEED = float(os.environ.get("SPEED", 300.0))           # 飛び回る速さ(ずっと同じ)
CX, CY = W / 2, 1150.0                                  # 円の中心
R = 470.0                                               # 円の半径
HUB = 46.0                                              # まん中の軸の半径
W_A = float(os.environ.get("W_A", 2.2))                 # 刃A の回る速さ(ラジアン/秒・時計回り)
W_B = float(os.environ.get("W_B", -1.3))                # 刃B の回る速さ(反時計回り)
# 増殖するたびに変わるフルーツの順番(OJ.NAMES の番号): りんご → もも → オレンジ → いちご → レモン → スイカ → …
ROUND_KINDS = [0, 4, 1, 3, 2, 5]
START_KIND = 5   # 最初の1人(スイカのおじさん)
SPAWN_DELAY = 0.0 
BLADE_CAT, FRUIT_CAT = 0b10, 0b01
PASS_MASK = pymunk.ShapeFilter.ALL_MASKS() ^ BLADE_CAT
HELD_MASK = pymunk.ShapeFilter.ALL_MASKS() ^ BLADE_CAT ^ FRUIT_CAT   # はさまれ中は、刃ともほかのおじさんともぶつからない
HOLD_GAP = float(os.environ.get("HOLD_GAP", 0.35))      # すきまがこの角度(ラジアン)よりせまくなったら、中のおじさんは閉じこめられる   # はさまれたおじさんは少しのあいだ刃をすり抜ける(刃にくっつかない)                                      # 刃が重なってから、増えたおじさんが出てくるまで
MAX_OBJ = TARGET + 40
OUTRO = 2.5


class Game:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        sp = pymunk.Space()
        sp.gravity = (0, 0)
        sp.iterations = 20
        self.space = sp
        st = sp.static_body
        n = 96
        pts = [(CX + (R + 14) * math.cos(2 * math.pi * k / n), CY + (R + 14) * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
        for a, b in zip(pts, pts[1:]):
            s = pymunk.Segment(st, a, b, 14)
            s.elasticity, s.friction = 1.0, 0.0
            s.collision_type = 2
            sp.add(s)
        hub = pymunk.Circle(st, HUB, (CX, CY))
        hub.elasticity, hub.friction = 1.0, 0.0
        hub.collision_type = 2
        sp.add(hub)
        # 2枚の刃(軸のまわりを回る)
        self.blades = []
        for w, a0 in ((W_A, 0.0), (W_B, math.pi)):
            b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            b.position = (CX, CY)
            b.angle = a0
            b.angular_velocity = w
            s = pymunk.Segment(b, (HUB, 0), (R - 4, 0), 7)
            s.filter = pymunk.ShapeFilter(categories=BLADE_CAT)
            s.elasticity, s.friction = 1.0, 0.0
            s.collision_type = 3
            sp.add(b, s)
            self.blades.append(b)
        sp.on_collision(1, 2, post_solve=self._bump)
        sp.on_collision(1, 1, post_solve=self._bump)
        sp.on_collision(1, 3, post_solve=self._bump)
        self.objs = {}
        self.next_id = 0
        self.t = 0.0
        self.events = []
        self.trapped = []
        self.spawn_at = None
        self.result, self.result_t = None, None
        a = self.rng.uniform(0, 2 * math.pi)
        rr = self.rng.uniform(150, 350)
        d = self.rng.uniform(0, 2 * math.pi)
        self.rng.integers(0, len(OJ.NAMES))   # (乱数の順番をそろえるために1回引く)
        self.round = 0   # 何回目の増殖か(増殖するたびにフルーツが変わる)
        self.add_obj((CX + rr * math.cos(a), CY + rr * math.sin(a)), (SPEED * math.cos(d), SPEED * math.sin(d)), START_KIND)

    def add_obj(self, pos, vel, kind):
        m = 1.0
        b = pymunk.Body(m, pymunk.moment_for_circle(m, 0, OBJ_R))
        b.position = pos
        b.velocity = vel
        b.angular_velocity = self.rng.uniform(-2.5, 2.5)
        s = pymunk.Circle(b, OBJ_R)
        s.elasticity, s.friction = 1.0, 0.0
        s.collision_type = 1
        s.filter = pymunk.ShapeFilter(categories=FRUIT_CAT)
        self.space.add(b, s)
        self.objs[b] = {"id": self.next_id, "shape": s, "kind": kind}
        self.next_id += 1

    def _bump(self, arb, space, data):
        """当たった瞬間を記録する(音と、ぷよっとつぶれる見た目のため)。"""
        if not arb.is_first_contact:
            return
        n = arb.normal
        for sh in arb.shapes:
            info = self.objs.get(sh.body)
            if info is not None:
                info["hit"] = (self.t, math.atan2(n.y, n.x))
        if len(self.events) < 300000:
            self.events.append(("bump", self.t, None))

    def gap(self):
        """刃A から進む向きに見た、刃B までの角度(これがせまくなってゼロになると重なる)。"""
        a, b = self.blades[0].angle, self.blades[1].angle
        return (b - a) % (2 * math.pi)

    def step(self, dt):
        g0 = self.gap()
        self.t += dt
        self.space.step(dt)
        g1 = self.gap()
        k = 1 - math.exp(-dt / 1.2)
        for b in self.objs:   # 摩擦も重力もない世界。回る刃に弾かれて速くなっても、ゆっくりいつもの速さに戻る
            v = b.velocity
            n = v.length
            if n > 1e-6:
                b.velocity = v * ((n + (SPEED - n) * k) / n)
        aA = self.blades[0].angle
        # はさまれて刃をすり抜けていたおじさんは、少したったら元にもどる
        for b, info in self.objs.items():
            if info.get("pass_until") is not None and self.t >= info["pass_until"]:
                info["pass_until"] = None
                info["shape"].filter = pymunk.ShapeFilter(categories=FRUIT_CAT)
        # せまくなっていくすきまにいるおじさんは、はさまれる(消えずにそのまま。重なり終わると新しいフルーツが1人ずつ追加される)
        caught = []
        if g1 < HOLD_GAP and g1 < g0:   # すきまが十分せまくなったら、中にいるおじさんはもう外へ出られない
            for b, info in self.objs.items():
                if info.get("pass_until") is not None:
                    continue
                dx, dy = b.position.x - CX, b.position.y - CY
                rho = math.hypot(dx, dy)
                al = (math.atan2(dy, dx) - aA) % (2 * math.pi)   # 刃A から見た角度
                if al < g1 and rho > HUB:
                    caught.append((b, rho, al / g1))
        for b, rho, f in caught:
            info = self.objs[b]
            info["pass_until"] = self.t + 10.0   # 増えるまで刃の中に収まったまま(刃・ほかのおじさんとはぶつからない)
            info["shape"].filter = pymunk.ShapeFilter(categories=FRUIT_CAT, mask=HELD_MASK)
            info["hold"] = (rho, f)
            self.trapped.append((b, rho, info["kind"]))
        # はさまれているおじさんは、2枚の刃のあいだに収まったまま、すきまといっしょに細くなっていく
        if self.trapped:
            aB = self.blades[1].angle
            for ob, _, _ in self.trapped:
                info = self.objs.get(ob)
                if info is None or "hold" not in info:
                    continue
                rho, f = info["hold"]
                if self.spawn_at is None:
                    a = aA + f * g1
                else:   # 重なり終わってから増えるまでの一瞬は、2枚の刃のまんなかにとどまる
                    d = (aB - aA + math.pi) % (2 * math.pi) - math.pi
                    a = aA + d / 2
                ob.position = (CX + rho * math.cos(a), CY + rho * math.sin(a))
                w = W_A + (W_B - W_A) * f
                ob.velocity = (-w * rho * math.sin(a), w * rho * math.cos(a))
        if caught:
            self.events.append(("squash", self.t, len(caught)))
        # 刃が重なった(すきまがゼロをこえて大きくなった)
        if g1 > g0 + math.pi:
            self.events.append(("cross", self.t, aA))
            if self.trapped:
                self.spawn_at = (self.t + SPAWN_DELAY, aA)
        if self.spawn_at is not None and self.t >= self.spawn_at[0]:
            _, a_cross = self.spawn_at
            self.spawn_at = None
            k = 0
            # 重なった場所(2枚の刃のまんなかの向き)から、内側と外側へはじき出す
            # 2枚の刃は重なった所から離れていく。そのあいだ(今ひらいたすきま)のまんなかから出す(刃にくっつかないように)
            d_ab = (self.blades[1].angle - self.blades[0].angle + math.pi) % (2 * math.pi) - math.pi
            mid = self.blades[0].angle + d_ab / 2
            nk = ROUND_KINDS[self.round % len(ROUND_KINDS)]   # この回に追加されるフルーツ
            for ob, rho, kind in self.trapped:
                if ob not in self.objs:
                    continue
                # はさまれていたおじさんはそのまま残って内側へ、新しいフルーツのおじさんが1人追加されて外側へ
                for sgn in (-1, 1):
                    rr = min(R - OBJ_R - 4, max(HUB + OBJ_R + 4, rho + sgn * OBJ_R * 0.6))
                    px, py = CX + rr * math.cos(mid), CY + rr * math.sin(mid)
                    d = mid + (0 if sgn > 0 else math.pi) + self.rng.uniform(-0.4, 0.4)
                    vel = (SPEED * math.cos(d), SPEED * math.sin(d))
                    if sgn < 0:
                        ob.position = (px, py)
                        ob.velocity = vel
                        self.objs[ob]["pass_until"] = self.t + 0.3
                        self.objs[ob].pop("hold", None)
                        self.objs[ob]["shape"].filter = pymunk.ShapeFilter(categories=FRUIT_CAT, mask=PASS_MASK)
                    elif len(self.objs) < MAX_OBJ:
                        self.add_obj((px, py), vel, nk)
                        nb = list(self.objs)[-1]
                        self.objs[nb]["pass_until"] = self.t + 0.3
                        self.objs[nb]["shape"].filter = pymunk.ShapeFilter(categories=FRUIT_CAT, mask=PASS_MASK)
                k += 1
            self.trapped = []
            self.events.append(("split", self.t, (k, len(self.objs), ROUND_KINDS[self.round % len(ROUND_KINDS)])))
            self.round += 1
        for b in list(self.objs):   # 円の外へ抜けたもの(めったにない)は消す
            if math.hypot(b.position.x - CX, b.position.y - CY) > R + 30:
                info = self.objs.pop(b)
                self.space.remove(b, info["shape"])
        if self.result is None:
            if len(self.objs) >= TARGET:
                self.result, self.result_t = "success", self.t
                self.events.append(("success", self.t, None))
            elif self.t >= TIME_LIMIT:
                self.result, self.result_t = "fail", self.t
                self.events.append(("fail", self.t, None))


def squeeze(info, gap):
    """刃のあいだに閉じこめられたおじさんの、すきまの向きのつぶれ具合(1 = つぶれていない)。"""
    if "hold" not in info:
        return 1.0
    rho, _ = info["hold"]
    w = rho * min(gap, 2 * math.pi - gap) - 10   # すきまの幅(刃の太さぶんを引く)
    return max(0.12, min(1.0, w / (2 * OBJ_R * 1.25)))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "aA": g.blades[0].angle, "aB": g.blades[1].angle, "n": len(g.objs),
                           "objs": [(b.position.x, b.position.y, b.angle, info["kind"], info["id"], info.get("hit"),
                                     squeeze(info, g.gap()))
                                    for b, info in g.objs.items()]})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else FV.DURATION
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "n": len(g.objs)}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["n"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    pick = succ if want == "success" else [r for r in rs if r[1] != "success"]
    pick.sort(key=lambda r: -r[2] if want == "success" else -r[3])
    for r in pick[:15]:
        print(f"seed={r[0]:4d}  {r[1]}  {r[2]:5.2f}秒  {r[3]}人")


# ---------------------------------------------------------------- 描画
BG = (0.03, 0.025, 0.05)
GOLD = (1, 0.86, 0.2)


def draw_ring(ctx):
    for wdt, a in ((28, 0.08), (12, 0.2), (6, 0.95)):
        ctx.arc(CX, CY, R + 8, 0, 2 * math.pi)
        ctx.set_source_rgba(0.6, 0.75, 0.95, a)
        ctx.set_line_width(wdt)
        ctx.stroke()


def draw_blade(ctx, ang, col_edge):
    """刃:根元が太く先が細い、光る鋼の刃(片側に刃先のきらめき)。"""
    ctx.save()
    ctx.translate(CX, CY)
    ctx.rotate(ang)
    ctx.new_path()
    ctx.move_to(HUB - 6, -16)
    ctx.line_to(R - 30, -9)
    ctx.line_to(R - 2, 0)
    ctx.line_to(R - 30, 9)
    ctx.line_to(HUB - 6, 16)
    ctx.close_path()
    g = cairo.LinearGradient(0, -16, 0, 16)
    g.add_color_stop_rgb(0, 0.95, 0.97, 1.0)
    g.add_color_stop_rgb(0.45, 0.7, 0.74, 0.8)
    g.add_color_stop_rgb(1, 0.35, 0.38, 0.44)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(*col_edge, 0.9)
    ctx.set_line_width(2.5)
    ctx.stroke()
    ctx.restore()


def draw_hub(ctx, t):
    g = cairo.RadialGradient(CX - 12, CY - 12, 4, CX, CY, HUB)
    g.add_color_stop_rgb(0, 0.95, 0.95, 1.0)
    g.add_color_stop_rgb(1, 0.3, 0.32, 0.38)
    ctx.set_source(g)
    ctx.arc(CX, CY, HUB, 0, 2 * math.pi)
    ctx.fill()
    for k in range(6):
        a = k * math.pi / 3 + t * 0.5
        ctx.arc(CX + 26 * math.cos(a), CY + 26 * math.sin(a), 5, 0, 2 * math.pi)
        ctx.set_source_rgb(0.25, 0.27, 0.3)
        ctx.fill()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"blade_split_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"blade_split_{seed}.wav")
    final = os.path.join(OUT_DIR, f"blade_split_{seed}.mp4")
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    ending = None if fail else FV.FruitFever(W, H, seed, CX, CY, main=f"{TARGET}人達成!!", count=f"{TARGET} / {TARGET}")
    born = {}
    sparks = []
    rng = np.random.default_rng(seed + 7)
    last_cross = -9.0
    ev_i = 0
    prev_n = 1
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "cross":
                last_cross = et
                for _ in range(30):   # 刃が重なった所に火花
                    rr = rng.uniform(HUB, R)
                    a = rng.uniform(0, 2 * math.pi)
                    sparks.append([CX + rr * math.cos(data), CY + rr * math.sin(data), math.cos(a) * rng.uniform(100, 500),
                                   math.sin(a) * rng.uniform(100, 500), et])
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
        ctx.set_source_rgb(*BG)
        ctx.paint()
        g = cairo.RadialGradient(CX, CY, 50, CX, CY, R + 100)
        g.add_color_stop_rgba(0, 0.16, 0.13, 0.25, 0.9)
        g.add_color_stop_rgba(1, 0.05, 0.04, 0.08, 0.9)
        ctx.set_source(g)
        ctx.arc(CX, CY, R, 0, 2 * math.pi)
        ctx.fill()
        draw_ring(ctx)
        for x, y, ang, kind, oid, hit, sq in fr["objs"]:
            if oid not in born:
                born[oid] = t
            a = t - born[oid]
            k = 1.0 if a > 0.15 else 0.7 + 0.3 * a / 0.15 + 0.25 * math.sin(math.pi * a / 0.15)
            ctx.save()
            if hit is not None and t - hit[0] < 0.25:   # 当たった瞬間、ぷよっとつぶれて戻る
                e = math.exp(-(t - hit[0]) * 14) * math.cos((t - hit[0]) * 40)
                ctx.translate(x, y)
                ctx.rotate(hit[1])
                ctx.scale(1 - 0.28 * e, 1 + 0.18 * e)
                ctx.rotate(-hit[1])
                ctx.translate(-x, -y)
            if sq < 1.0:   # 刃のあいだで押しつぶされる(すきまの向きに細くなる)
                tg = math.atan2(y - CY, x - CX) + math.pi / 2
                ctx.translate(x, y)
                ctx.rotate(tg)
                ctx.scale(sq, 1 + 0.25 * (1 - sq))
                ctx.rotate(-tg)
                ctx.translate(-x, -y)
            OJ.draw_fruit(ctx, kind, x, y, OBJ_R * 1.25 * k, ang * 0.3)
            ctx.restore()
        draw_blade(ctx, fr["aA"], (1.0, 0.5, 0.4))
        draw_blade(ctx, fr["aB"], (0.4, 0.75, 1.0))
        draw_hub(ctx, t)
        if t - last_cross < 0.25:
            fl = 1 - (t - last_cross) / 0.25
            g = cairo.RadialGradient(CX, CY, 10, CX, CY, R)
            g.add_color_stop_rgba(0, 1, 0.95, 0.7, 0.45 * fl)
            g.add_color_stop_rgba(1, 1, 0.9, 0.5, 0)
            ctx.set_source(g)
            ctx.arc(CX, CY, R, 0, 2 * math.pi)
            ctx.fill()
        keep = []
        for s in sparks:
            a = t - s[4]
            if a < 0.35:
                ctx.arc(s[0] + s[2] * a, s[1] + s[3] * a, 3.5 * (1 - a / 0.35) + 0.5, 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.95, 0.6, 1 - a / 0.35)
                ctx.fill()
                keep.append(s)
        sparks = keep
        text(ctx, "おじさんフルーツを", W / 2, 170, 74, sw=12)
        text(ctx, f"{TARGET}人に増やせる？", W / 2, 300, 104, rgb=GOLD, sw=16)
        n = fr["n"]
        pop_ = 1.0 + (0.25 if n > prev_n else 0.0)
        prev_n = n
        text(ctx, f"{min(n, TARGET)}", W / 2 - 50, 500, 100 * pop_, rgb=(1, 1, 1), sw=12)
        text(ctx, f"/ {TARGET} 人", W / 2 + 180, 500, 46, rgb=(0.8, 0.85, 0.9), sw=6)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, 1780, 60, rgb=(1, 0.4, 0.4) if left < 8 else (0.9, 0.9, 0.92), sw=8)
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 1080, 130 * (1.15 - 0.15 * k), rgb=(1, 0.3, 0.3), sw=18)
            text(ctx, f"あと{TARGET - res['n']}人だったのに…", W / 2, 1210, 72, sw=12)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['n']}人 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def shing(seed):
    """刃と刃が重なる「シャキーン」(金属がこすれて鳴る高い音)。"""
    rng = np.random.default_rng(seed)
    t = np.arange(int(0.7 * SR)) / SR
    n = rng.normal(0, 1, len(t))
    scrape = (n - np.convolve(n, np.ones(2) / 2, "same")) * np.exp(-((t - 0.03) / 0.03) ** 2)
    ring = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in ((2200, 1, 6), (3350, 0.6, 8), (5100, 0.3, 11)))
    return 0.6 * scrape + 0.4 * ring * np.minimum(1, t / 0.01)


def boing(f0, seed):
    """おじさんが増えて飛び出す、間の抜けた「ボヨン」(ビブラートつき)。"""
    t = np.arange(int(0.3 * SR)) / SR
    f = f0 * (1 + 0.7 * np.exp(-t * 25)) * (1 + 0.08 * np.sin(2 * np.pi * 13 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.minimum(1, t / 0.003) * np.exp(-t * 9)


VOICE_GAIN = 1.0   # おじさんの声の大きさ(効果音より少し前に出る)


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 3) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)

    def add(sig, t0, g=1.0, buf=None):
        b = out if buf is None else buf
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out:
            b[i:j] += g * sig[: j - i]

    voices = []
    for k in range(6):   # 早回しはせず、言葉を最後まで言い切らせる
        v = OV.voice(k, SR)
        voices.append(v / np.sqrt(np.mean(v ** 2)) * 0.22)
    last_b = -1.0
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.01:
            continue
        if kind == "bump":
            if t - last_b > 0.05:
                add(pop(note_hz(int(t * 7) % 5) * 0.5, 0) * 0.5, t, 0.08)   # 当たったときの小さな「ポコッ」
                last_b = t
        elif kind == "cross":
            add(shing(int(t * 100)), t, 0.4)
        elif kind == "squash":
            add(hiss(int(t * 100))[: int(0.12 * SR)], t, 0.12)
        elif kind == "split":
            k, total, rk = data
            # 1回目ははっきり大きく(聞き取れるように1人だけ)。増えた数だけ、うしろで小さく「わいわい」重なる
            add(voices[rk], t, VOICE_GAIN)
            if k > 1:
                crowd = min(k - 1, 40)
                for j in range(crowd):
                    add(voices[rk], t + 0.25 + 0.9 * j / max(1, crowd), VOICE_GAIN * 0.5 / (1 + crowd ** 0.6))
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += sig[:m]
    elif end_t is not None:
        add(FV.music(SR).mean(axis=1) * 1.6, end_t, 1.0, extra)
    wet = out.copy()
    for d, g in ((0.043, 0.25), (0.071, 0.18), (0.113, 0.12)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    ref = np.percentile(np.abs(wet[np.abs(wet) > 1e-4]), 99.5)
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int((end_t or duration) * SR)]
    rms = np.sqrt(np.mean(body ** 2))
    if rms > 0:
        wet *= min(6.0, 10 ** (-14.0 / 20) / rms)   # 小さすぎないよう、通常部分を約 -14dB に
    wet = wet + (0.95 if fail else 1.0) * extra[: len(wet)]
    mag = np.abs(wet)
    wet = np.where(mag < 0.7, wet, np.sign(wet) * (0.7 + 0.1 * np.tanh((mag - 0.7) / 0.1)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((wet * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--want", choices=["fail", "success"], default="success")
    ap.add_argument("-n", type=int, default=200)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
