"""「玉を食べて大きくなるキャラ、全部食べられる?」(参考動画「balls eaten」の形)
カプセル形(スタジアム形)のわくの中に小さな玉がぎっしりならんでいる。1個のボールが一定の速さでまっすぐ進み、わくのかべで反射する。
ボールにふれた小さな玉は食べられて消え、食べた分だけボールが大きくなる(面積を GROW の割合で足す)。
小さな玉にぶつかったときは、弾性衝突の反動でボールの進む向きが物理どおりに変わる(速さは一定のまま)。
はじめはボールが小さいので向きがよく変わり、大きくなるほど重くなってまっすぐ進む。
TIME_LIMIT 秒以内に全部食べたら成功(大当たり演出)、残ったら失敗(幽霊 → 暗くなって「Failed...」+ 残った玉を赤い輪で表示)。

- ねらい・補正なし。はじめの位置と向きだけがシードで変わる。
- かべは鏡のような反射(入る角度 = 出る角度)。わくをカプセル形にしているのは、まんまるのわくだと反射の軌道が
  まん中から一定のきょりのまま回り続けてしまい(まん中に永久にとどかない)、結果が最初の向きだけで決まってしまうため。
  カプセル形の中の反射はカオスになり、同じ所を回り続けない。

使い方:
    python ball_eat.py search [-n 80]
    python ball_eat.py render --seed N
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
SUBSTEPS = int(os.environ.get("SUBSTEPS", 6))
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

CX, CY = 540.0, 1010.0
R = float(os.environ.get("R", 380.0))           # わく(カプセル形)の半円の半径 = 横はばの半分
HS = float(os.environ.get("HS", 120.0))         # まん中のまっすぐな部分の長さの半分(0 なら円)
RS = float(os.environ.get("RS", 4.5))            # 小さな玉の半径
R0 = float(os.environ.get("R0", 9.0))            # はじめのボールの半径
GROW = float(os.environ.get("GROW", 0.045))      # 食べた玉の面積のこの割合だけボールの面積がふえる
SPEED = float(os.environ.get("SPEED", 2000.0))    # ボールの速さ(一定)
M_K = float(os.environ.get("M_K", 1.0))          # 小さな玉の重さ(面積あたり、ボールとの比)
START_R = float(os.environ.get("START_R", 250.0))   # はじめの位置はまん中からこの半径の中
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 43.7))
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG


def seg_dist(x, y):
    """まん中の線分(たて)までのきょりと、いちばん近い点。"""
    cy = min(CY + HS, max(CY - HS, y))
    return math.hypot(x - CX, y - cy), CX, cy


def lattice():
    """六角形にぎっしりならべた小さな玉の位置(わくの中に入るものだけ)。"""
    s = 2 * RS
    pts = []
    rows = int((R + HS) / (s * math.sqrt(3) / 2)) + 2
    for j in range(-rows, rows + 1):
        y = j * s * math.sqrt(3) / 2
        off = (s / 2) if j % 2 else 0.0
        for i in range(-int(R / s) - 2, int(R / s) + 3):
            x = i * s + off
            if seg_dist(CX + x, CY + y)[0] <= R - RS - 0.5:
                pts.append((CX + x, CY + y))
    return np.array(pts)


PTS = lattice()
NB = len(PTS)


class Game:
    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        a = rng.uniform(0, 2 * math.pi)
        d = min(START_R, R - 60) * math.sqrt(rng.uniform(0, 1))
        self.x, self.y = CX + d * math.cos(a), CY + d * math.sin(a)
        b = rng.uniform(0, 2 * math.pi)
        self.vx, self.vy = SPEED * math.cos(b), SPEED * math.sin(b)
        self.r = R0
        self.alive = np.ones(NB, bool)
        self.left = NB
        self.t = 0.0
        self.events = []
        self.result, self.result_t = None, None
        self.eat_now = 0
        self.bounce_now = False
        # はじめの位置に重なっている玉は、はじめから食べたことにはしない(ふれた時に食べる)

    def step(self, dt):
        if self.result is not None:
            self.t += dt
            return
        self.t += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        # かべで反射(鏡のように)
        dd, qx, qy = seg_dist(self.x, self.y)
        lim = R - self.r
        if dd > lim:
            nx, ny = (self.x - qx) / dd, (self.y - qy) / dd
            vn = self.vx * nx + self.vy * ny
            if vn > 0:
                self.vx -= 2 * vn * nx
                self.vy -= 2 * vn * ny
                self.bounce_now = True
            self.x, self.y = qx + nx * lim, qy + ny * lim
        # 食べる:ボールにふれた玉
        reach = self.r + RS
        cand = np.nonzero(self.alive & (np.abs(PTS[:, 0] - self.x) < reach) & (np.abs(PTS[:, 1] - self.y) < reach))[0]
        if len(cand):
            qx, qy = PTS[cand, 0] - self.x, PTS[cand, 1] - self.y
            dist = np.hypot(qx, qy)
            hit = dist < reach
            if hit.any():
                idx = cand[hit]
                qx, qy, dist = qx[hit], qy[hit], dist[hit]
                order = np.argsort(dist)
                for k in order:
                    # 弾性衝突の反動で向きが変わる(玉は止まっている。ぶつかる向きに進んでいるときだけ)
                    nx, ny = qx[k] / max(dist[k], 1e-6), qy[k] / max(dist[k], 1e-6)
                    vn = self.vx * nx + self.vy * ny
                    if vn > 0:
                        M = self.r * self.r
                        m = M_K * RS * RS
                        f = 2 * m / (M + m)
                        self.vx -= f * vn * nx
                        self.vy -= f * vn * ny
                    self.r = math.sqrt(self.r * self.r + GROW * RS * RS)
                self.alive[idx] = False
                n = len(idx)
                self.left -= n
                self.eat_now += n
                sp = math.hypot(self.vx, self.vy) or 1.0   # 速さは一定
                self.vx *= SPEED / sp
                self.vy *= SPEED / sp
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
        g.eat_now = 0
        g.bounce_now = False
        for _ in range(SUBSTEPS):
            g.step(dt)
        if g.eat_now:
            g.events.append(("eat", g.t, (g.x, g.y, g.eat_now, g.r, NB - g.left)))
        if g.bounce_now:
            g.events.append(("bounce", g.t, (g.x, g.y)))
        if record:
            frames.append({"t": g.t, "x": g.x, "y": g.y, "r": g.r, "left": g.left, "vx": g.vx, "vy": g.vy,
                           "alive": g.alive.copy() if (g.eat_now or not frames) else None, "eat": g.eat_now})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t,
            "left": g.left, "total": NB, "r_end": g.r}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), r["left"], round(1 - r["left"] / r["total"], 4)


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件 (玉 {NB} 個)")
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


# 小さな玉の色:まん中からの向きで虹色(色相 HB 段階)
HB = 36
_ANG = (np.arctan2(PTS[:, 1] - CY, PTS[:, 0] - CX) / (2 * math.pi)) % 1.0
HUE_BIN = (_ANG * HB).astype(int) % HB


def capsule(ctx, r):
    ctx.new_path()
    ctx.arc(CX, CY - HS, r, math.pi, 2 * math.pi)
    ctx.arc(CX, CY + HS, r, 0, math.pi)
    ctx.close_path()


def draw_hero(ctx, x, y, r, ang, mouth, t):
    """食べるキャラ:まんまるの体に目とほっぺ。進む向きに大きな口をあけて、食べるたびにパクパクする。
    ang:進む向き、mouth:口のあき具合(0〜1)。左向きのときは左右反転して、顔がさかさまにならないようにする。"""
    for k, al in ((2.4, 0.06), (1.7, 0.12), (1.25, 0.22)):   # まわりの光
        g = cairo.RadialGradient(x, y, r * 0.6, x, y, r * k)
        g.add_color_stop_rgba(0, 1.0, 0.85, 0.4, al)
        g.add_color_stop_rgba(1, 1.0, 0.7, 0.2, 0)
        ctx.arc(x, y, r * k, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
    ctx.save()
    ctx.translate(x, y)
    flip = math.cos(ang) < 0
    if flip:
        ctx.scale(-1, 1)
        ang = math.pi - ang
    ctx.rotate(ang)
    ctx.scale(r, r)
    # 体
    g = cairo.RadialGradient(-0.35, -0.45, 0.05, 0, 0, 1)
    g.add_color_stop_rgb(0, 1.0, 0.98, 0.85)
    g.add_color_stop_rgb(0.4, 1.0, 0.8, 0.3)
    g.add_color_stop_rgb(1, 0.92, 0.45, 0.08)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    # 口(進む向きにあく)
    mo = 0.12 + 0.88 * mouth
    mx, my = 0.5, 0.18
    rw, rh = 0.42, 0.42 * mo
    ctx.save()
    ctx.translate(mx, my)
    ctx.scale(rw, max(0.02, rh))
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.35, 0.05, 0.08)
    ctx.fill_preserve()
    ctx.save()
    ctx.clip()
    ctx.arc(mx + 0.05, my + rh * 0.9, 0.3, 0, 2 * math.pi)   # 舌
    ctx.set_source_rgb(1.0, 0.45, 0.55)
    ctx.fill()
    for tx_ in (mx - 0.16, mx + 0.1):                         # 上の歯
        ctx.rectangle(tx_, my - rh - 0.02, 0.11, 0.07 + 0.08 * mo)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
    ctx.restore()
    ctx.save()
    ctx.translate(mx, my)
    ctx.scale(rw, max(0.02, rh))
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.55, 0.2, 0.05)
    ctx.set_line_width(0.05)
    ctx.stroke()
    # 目(白目+黒目+光)
    blink = (t % 3.1) < 0.1
    for ex, ey, er in ((0.12, -0.42, 0.2), (0.55, -0.36, 0.17)):
        if blink:
            ctx.move_to(ex - er, ey)
            ctx.line_to(ex + er, ey)
            ctx.set_source_rgb(0.2, 0.08, 0.05)
            ctx.set_line_width(0.06)
            ctx.stroke()
            continue
        ctx.arc(ex, ey, er, 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        ctx.arc(ex + er * 0.35, ey + er * 0.05, er * 0.6, 0, 2 * math.pi)
        ctx.set_source_rgb(0.1, 0.06, 0.05)
        ctx.fill()
        ctx.arc(ex + er * 0.45, ey - er * 0.25, er * 0.22, 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
    # ほっぺ
    ctx.save()
    ctx.translate(-0.2, 0.15)
    ctx.scale(0.2, 0.12)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(1.0, 0.4, 0.45, 0.55)
    ctx.fill()
    ctx.restore()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"ball_eat_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"ball_eat_{seed}.wav")
    final = os.path.join(OUT_DIR, f"ball_eat_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"be_preview_{seed}_{pt:.1f}.png"))
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
    ending = None if fail else JP.Jackpot(W, H, seed, CX, CY, reel_ball, n_kinds=7, win=6, shake=22,
                                          texts=("Congratulations!!", "COMPLETE", ""), font="Playfair Display", slim=True)
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    cols = [colorsys.hsv_to_rgb(k / HB, 0.85, 1.0) for k in range(HB)]
    prng = np.random.default_rng(seed + 9)
    parts = []   # 食べたときに飛びちる光のつぶ
    alive = frames[0]["alive"]
    frozen = None
    trail = []
    face_ang, munch, chomp_ph = None, 0.0, 0.0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        if fr["alive"] is not None:
            prev_alive = alive
            alive = fr["alive"]
            gone = np.nonzero(prev_alive & ~alive)[0]
            for k in gone[:: max(1, len(gone) // 12)]:
                a = prng.uniform(0, 2 * math.pi)
                sp = prng.uniform(80, 320)
                parts.append([PTS[k, 0], PTS[k, 1], sp * math.cos(a), sp * math.sin(a), 0.0, HUE_BIN[k]])
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
                frozen = (fr, alive)
            fr, alive = frozen
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        ctx.set_source_rgb(0.03, 0.035, 0.06)
        ctx.paint()
        hx, hy, hr = fr["x"], fr["y"], fr["r"]
        # わく(白く光る輪)
        for wd, al in ((18, 0.08), (8, 0.18), (3, 0.9)):
            capsule(ctx, R + 2)
            ctx.set_source_rgba(0.85, 0.95, 1.0, al)
            ctx.set_line_width(wd)
            ctx.stroke()
        # 小さな玉(ボールに近いほど明るく光る)
        near = np.hypot(PTS[:, 0] - hx, PTS[:, 1] - hy) < hr + 150
        for k in range(HB):
            sel = alive & (HUE_BIN == k)
            if not sel.any():
                continue
            c = cols[k]
            for lit in (False, True):
                ss = sel & (near if lit else ~near)
                if not ss.any():
                    continue
                for px, py in PTS[ss]:
                    ctx.new_sub_path()
                    ctx.arc(px, py, RS - 0.35, 0, 2 * math.pi)
                f = 1.0 if lit else 0.72
                ctx.set_source_rgb(min(1, c[0] * f + (0.25 if lit else 0)), min(1, c[1] * f + (0.25 if lit else 0)),
                                   min(1, c[2] * f + (0.25 if lit else 0)))
                ctx.fill()
        # 残りわずかになったら、残っている玉をやさしく光らせて見やすくする(見た目だけ)
        nleft = int(alive.sum())
        if 0 < nleft <= 80 and not over:
            pul = 0.5 + 0.5 * math.sin(t * 7)
            for k in np.nonzero(alive)[0]:
                px, py = PTS[k]
                c = cols[HUE_BIN[k]]
                g = cairo.RadialGradient(px, py, 1, px, py, 22 + 6 * pul)
                g.add_color_stop_rgba(0, *c, 0.65)
                g.add_color_stop_rgba(1, *c, 0)
                ctx.arc(px, py, 22 + 6 * pul, 0, 2 * math.pi)
                ctx.set_source(g)
                ctx.fill()
                ctx.arc(px, py, RS + 1.5, 0, 2 * math.pi)
                ctx.set_source_rgb(min(1, c[0] + 0.3), min(1, c[1] + 0.3), min(1, c[2] + 0.3))
                ctx.fill()
        # 光のつぶ
        keep = []
        for p in parts:
            p[4] += 1 / FPS
            if p[4] > 0.6:
                continue
            p[0] += p[2] / FPS
            p[1] += p[3] / FPS
            p[2] *= 0.93
            p[3] *= 0.93
            c = cols[p[5]]
            ctx.arc(p[0], p[1], 2.4, 0, 2 * math.pi)
            ctx.set_source_rgba(*c, 1 - p[4] / 0.6)
            ctx.fill()
            keep.append(p)
        parts = keep[-900:]
        # ボール
        if not over or fail:
            trail.append((hx, hy, hr))
            trail = trail[-10:]
            for i, (tx_, ty_, tr_) in enumerate(trail[:-1]):
                ctx.arc(tx_, ty_, tr_ * 0.9, 0, 2 * math.pi)
                ctx.set_source_rgba(1.0, 0.75, 0.3, 0.05 + 0.02 * i)
                ctx.fill()
            want = math.atan2(fr["vy"], fr["vx"])
            if face_ang is None:
                face_ang = want
            dang = (want - face_ang + math.pi) % (2 * math.pi) - math.pi
            face_ang += dang * 0.35                      # 向きはなめらかにふりむく
            if fr["eat"]:
                munch = min(1.0, munch + 0.5)
            else:
                munch = max(0.0, munch - 0.05)
            chomp_ph += 0.55 * munch
            mouth = (0.85 if munch < 0.05 else 0.5 + 0.5 * math.cos(chomp_ph))   # 食べている間はパクパク
            draw_hero(ctx, hx, hy, hr, face_ang, mouth, t)
        # 文字
        chic(ctx, "全部たべられる？", W / 2, 200, 62, rgb=(1, 0.88, 0.6))
        pct = int((1 - fr["left"] / NB) * 100)
        chic(ctx, f"{pct}%", W / 2 - 110, 310, 84, rgb=(1, 1, 1), weight="Medium")
        tt = min(t, end_t) if end_t is not None else t
        lft = max(0.0, TIME_LIMIT - tt)
        chic(ctx, f"{lft:4.1f}", W / 2 + 130, 305, 44, rgb=(1, 0.45, 0.45) if lft < 5 else (0.7, 0.75, 0.85), weight="Medium")
        if not over:
            horror(ctx, "失敗したら…", W / 2, 1620, 74, t)
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
            # 食べのこした玉を赤い輪で示す(小さいので見えにくいため。結果はそのまま)
            pul = 0.5 + 0.5 * math.sin(after * 6)
            a_ = min(1.0, after / 0.6)
            for px, py in PTS[alive][:60]:
                for wd, al in ((10, 0.18), (3, 0.9)):
                    ctx.arc(px, py, 20 + 5 * pul, 0, 2 * math.pi)
                    ctx.set_source_rgba(1.0, 0.15, 0.2, al * a_)
                    ctx.set_line_width(wd)
                    ctx.stroke()
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {pct:.2f}% / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


SCALE = [0, 2, 4, 7, 9]   # ペンタトニック


def pop(f, amp):
    """食べた「ポッ」:やわらかいマリンバ風の短い音。"""
    tt = _t(0.22)
    env = np.minimum(1, tt / 0.003) * np.exp(-tt / 0.06)
    y = np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 4 * f * tt) * np.exp(-tt / 0.02)
    return amp * y * env


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)
    last = -1.0
    for kind, t, data in events:
        if t > end_t + 0.01:
            continue
        if kind == "eat":
            if t - last < 0.045:
                continue
            last = t
            frac = data[4] / NB
            step = int(frac * 30)            # 食べた量が多いほど音が上がっていく
            m = 60 + 12 * (step // 5) + SCALE[step % 5]
            sig = pop(midi_hz(m), min(1.0, 0.45 + data[2] / 25))
        elif kind == "bounce":
            tt = _t(0.12)
            sig = 0.5 * np.sin(2 * np.pi * 180 * tt) * np.exp(-tt / 0.03)
        else:
            continue
        i = int(t * SR)
        j = min(n_out, i + len(sig))
        if i < n_out:
            out[i:j] += sig[: j - i]
    wet = out.copy()
    for dd, g_ in ((0.083, 0.22), (0.131, 0.14), (0.197, 0.08)):
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
