"""「はねるたびに小さくなるボール、○回はねられる?」(参考動画「Each bounce SHRINKS the ball and builds a CAGE around it」の形)
丸いわくの中をボールがはね回る。ボールが壁に当たるたびに、ボールは少し小さくなり、当たった場所の壁からオレンジのとげが内側へのびる(カゴがだんだん閉じていく)。
制限時間内に円が完全にふさがったら(すき間がボールのまわりだけ=ボールの面積の FREE_K 倍か FREE_A 以下)成功(実際のすき間で判定。うめる演出はしない)。
ボールははね返るたびに少しずつ速くなる(ACCEL 倍・V_MAX まで)。ボールがとげにかこまれて閉じこめられ、STALL 秒たってもほとんどうまらなくなったら失敗。

- 重力あり。ボールは壁(とげを含む)で弾性的にはね返る(エネルギーは減らない・ねらい・補正なし)。
- 壁は中心からの放射状の線(N_RAY 本)でできていて、1本ずつ長さが変わる。とげは当たった場所でいちばん長く、まわりほど短い三角形。
  のびたとげはボールにめりこまない所で止まる。
- カゴがせまくなるほど、はねる回数が速く増える。
- 成功ならパチンコの大当たり風の演出、失敗なら幽霊。

使い方:
    python cage_bounce.py search [-n 80]
    python cage_bounce.py render --seed N
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
SUBSTEPS = 6
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

CX, CY, R = 540.0, 1010.0, 440.0
N_RAY = 720
CORE = float(os.environ.get("CORE", 8.0))   # とげはまん中のこの半径より内側にはのびない
R0 = float(os.environ.get("R0", 34.0))            # はじめのボールの半径
SHRINK = float(os.environ.get("SHRINK", 0.985))   # 1回はねるごとの大きさ
R_MIN = float(os.environ.get("R_MIN", 2.5))   # ボールはこれより小さくならない
SPEED = float(os.environ.get("SPEED", 1600.0))
SPIKE_U = float(os.environ.get("SPIKE_U", 12.0))   # とげの大きさの単位(px)
SPIKE_D = float(os.environ.get("SPIKE_D", 6.0))   # とげの深さ(SPIKE_U の何倍か)
SPIKE_WR = float(os.environ.get("SPIKE_WR", 2.5))  # とげの根もとの半分のはば(SPIKE_U の何倍か)
GROW_V = 1800.0                                   # とげがのびる速さ(px/秒)
FREE_A = float(os.environ.get("FREE_A", 0.0))   # すき間の面積がこれ以下(px²)でも「完全にふさがった」
FREE_K = float(os.environ.get("FREE_K", 4.0))
MAX_GAP = float(os.environ.get("MAX_GAP", 12.0))   # どの線もまん中の軸からこれ以内までのびきったら「完全にふさがった」(細いすき間も残さない)   # すき間がボールの面積のこの倍以下=円が完全にふさがった
ACCEL = float(os.environ.get("ACCEL", 1.004))   # はね返るたびに速さがこの倍に
V_MAX = float(os.environ.get("V_MAX", 4000.0))
GRAVITY = float(os.environ.get("GRAVITY", 2500.0))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 41.0))
STALL = float(os.environ.get("STALL", 10.0))   # この秒数ほとんどうまらなければ「閉じこめられた」
OUTRO = 4.2
PRE = 0.7
WIN_DUR = JP.DURATION - JP.T_BIG
ANG = np.arange(N_RAY) * 2 * math.pi / N_RAY
COS, SIN = np.cos(ANG), np.sin(ANG)


# ---------------------------------------------------------------- シミュレーション
class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        self.rad = np.full(N_RAY, R)       # 壁の位置(中心からのきょり)
        self.target = np.full(N_RAY, R)    # とげがのびていく先
        self.flash = np.full(N_RAY, -9.0)  # その線がのびはじめた時刻(光らせる)
        a = rng.uniform(0, 2 * math.pi)
        d = rng.uniform(0, 150)
        self.x, self.y = CX + d * math.cos(a), CY + d * math.sin(a)
        va = rng.uniform(0, 2 * math.pi)
        self.vx, self.vy = SPEED * math.cos(va), SPEED * math.sin(va)
        self.r = R0
        self.bounces = 0
        self.t = 0.0
        self.events = []
        self.result, self.result_t = None, None
        self.last_hit = -1.0
        self.hist = []
        self.trapped = False

    def wall_xy(self, idx):
        return CX + self.rad[idx] * COS[idx], CY + self.rad[idx] * SIN[idx]

    def step(self, dt):
        self.t += dt
        self.vy += GRAVITY * dt   # 重力
        self.x += self.vx * dt
        self.y += self.vy * dt
        # とげをのばす(ボールにめりこまない所まで)
        grow = self.target < self.rad - 0.01
        if grow.any():
            idx = np.nonzero(grow)[0]
            new = np.maximum(self.target[idx], self.rad[idx] - GROW_V * dt)
            dx, dy = self.x - CX, self.y - CY
            proj = dx * COS[idx] + dy * SIN[idx]
            perp2 = (dx * dx + dy * dy) - proj * proj
            hit = (perp2 < self.r * self.r) & (proj > 0)
            far = proj + np.sqrt(np.maximum(0.0, self.r * self.r - perp2)) + 1.5
            new = np.where(hit, np.maximum(new, np.minimum(self.rad[idx], far)), new)
            self.rad[idx] = new
        # 壁との当たり判定(近くの線分だけ調べる)
        dx, dy = self.x - CX, self.y - CY
        phi = math.atan2(dy, dx) % (2 * math.pi)
        i0 = int(phi / (2 * math.pi) * N_RAY)
        rho = math.hypot(dx, dy)
        # はみ出し防止:ボールの中心が壁の外に出ていたら内側へもどす
        k_ = int(round(phi / (2 * math.pi) * N_RAY)) % N_RAY
        if rho > self.rad[k_] - 0.5:
            back = max(1.0, self.rad[k_] - self.r * 0.5)
            self.x, self.y = CX + dx / rho * back, CY + dy / rho * back
            vr = (self.vx * dx + self.vy * dy) / rho
            if vr > 0:
                self.vx -= 2 * vr * dx / rho
                self.vy -= 2 * vr * dy / rho
            dx, dy = self.x - CX, self.y - CY
        win = 70 if rho > 260 else N_RAY // 2   # まん中近くでは、まわり全部のとげを調べる
        idx = (np.arange(i0 - win, i0 + win + 1)) % N_RAY
        px = CX + self.rad[idx] * COS[idx]
        py = CY + self.rad[idx] * SIN[idx]
        ax, ay, bx, by = px[:-1], py[:-1], px[1:], py[1:]
        ex, ey = bx - ax, by - ay
        l2 = ex * ex + ey * ey + 1e-9
        u = np.clip(((self.x - ax) * ex + (self.y - ay) * ey) / l2, 0, 1)
        qx, qy = ax + u * ex, ay + u * ey
        dd = (self.x - qx) ** 2 + (self.y - qy) ** 2
        j = int(np.argmin(dd))
        dist = math.sqrt(dd[j])
        if dist < self.r:
            nx, ny = self.x - qx[j], self.y - qy[j]
            ln = math.hypot(nx, ny)
            if ln < 1e-6:
                nx, ny = -dx, -dy
                ln = math.hypot(nx, ny)
            nx, ny = nx / ln, ny / ln
            vn = self.vx * nx + self.vy * ny
            self.x += nx * (self.r - dist + 0.5)
            self.y += ny * (self.r - dist + 0.5)
            if vn < 0:
                self.vx -= 2 * vn * nx
                self.vy -= 2 * vn * ny
                if self.t - self.last_hit > 0.012:
                    self.bounce(int(idx[j]), qx[j], qy[j])
                    self.last_hit = self.t

    def bounce(self, k, hx, hy):
        """はねた:ボールが小さくなり、当たった所の壁からとげがのびる。"""
        if self.result is not None:
            return
        depth = SPIKE_D * SPIKE_U
        base = math.hypot(hx - CX, hy - CY)
        half_px = SPIKE_WR * SPIKE_U                       # とげの根もとの半分のはば(ボールの大きさに比例)
        nw = max(2, min(int(0.3 / (2 * math.pi) * N_RAY), int(half_px / max(base, 20.0) / (2 * math.pi) * N_RAY)))
        for o in range(-nw, nw + 1):                      # 当たった所の線ほど大きく縮む三角形のとげ
            i = (k + o) % N_RAY
            want = self.rad[i] - depth * (1 - abs(o) / (nw + 1))
            if want < self.target[i]:
                self.target[i] = max(CORE, want)
                self.flash[i] = self.t
        self.r = max(R_MIN, self.r * SHRINK)
        sp = math.hypot(self.vx, self.vy)   # はね返るたびに少しずつ速くなる(上限あり)
        if sp > 1e-6 and sp < V_MAX:
            k = min(ACCEL, V_MAX / sp)
            self.vx *= k
            self.vy *= k
        self.bounces += 1
        self.events.append(("bounce", self.t, (hx, hy, self.bounces, self.r)))

    def fill(self):
        """カゴがどれだけうまったか(0〜1)。まん中の小さな空き(CORE)は数えない。"""
        return 1.0 - float(np.sum(self.rad ** 2 - CORE ** 2)) / (N_RAY * (R ** 2 - CORE ** 2))

    def check(self):
        f = self.fill()
        free = (1.0 - f) * math.pi * (R ** 2 - CORE ** 2)   # 残っているすき間の面積
        if self.result is None and free <= max(FREE_K * math.pi * self.r ** 2, FREE_A) and float(self.rad.max()) <= CORE + MAX_GAP:   # ボールのまわり以外、全部ふさがった
            self.result, self.result_t = "success", self.t
            self.events.append(("success", self.t, None))
        # ボールがとげにかこまれて閉じこめられ、STALL 秒たってもほとんどうまらなくなったら失敗
        self.hist.append((self.t, f))
        while self.hist and self.hist[0][0] < self.t - STALL:
            self.hist.pop(0)
        if self.result is None and self.t > STALL + 2 and f - self.hist[0][1] < 0.002:
            self.result, self.result_t = "fail", self.t
            self.trapped = True
            self.events.append(("fail", self.t, None))
        if self.result is None and self.t >= TIME_LIMIT:
            self.result, self.result_t = "fail", self.t
            self.events.append(("fail", self.t, None))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            if g.result is None:
                g.step(dt)
            else:
                g.t += dt
        g.check()
        if record:
            frames.append({"t": g.t, "x": g.x, "y": g.y, "r": g.r, "n": g.bounces, "fill": g.fill(),
                           "rad": g.rad.astype(np.float32).copy(), "flash": g.flash.astype(np.float32).copy()})
        if g.result is not None:
            extra = (OUTRO + SCARE_DUR) if g.result == "fail" else (PRE + WIN_DUR)
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "n": g.bounces, "fill": g.fill(), "trapped": g.trapped}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], round(r["result_t"], 1), r["n"], round(r["fill"], 4)


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 成功 {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
ORANGE = (0.95, 0.38, 0.22)
CREAM = (1.0, 0.92, 0.8)


def reel_ball(ctx, kind, x, y, ang, r, t, alpha=1.0, rng=None):
    shiny_ball(ctx, x, y, r * 0.8, PALETTE[(kind * 12 // 7) % 12])


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"cage_bounce_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"cage_bounce_{seed}.wav")
    final = os.path.join(OUT_DIR, f"cage_bounce_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"cb_preview_{pt:.1f}.png"))
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
                                          texts=("Congratulations!!", "COMPLETE", ""))
    fever = RainbowFever(W, H, seed)
    grng = np.random.default_rng(seed + 5)
    glints = [(grng.uniform(0, W), grng.uniform(0, H), grng.uniform(0, 1), grng.uniform(1.5, 3.5), grng.uniform(30, 90))
              for _ in range(40)]
    trail = []
    frozen = None
    for fi, fr in enumerate(frames):
        t = fr["t"]
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
                frozen = fr
            fr = frozen
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        ctx.set_source_rgb(0.02, 0.02, 0.04)
        ctx.paint()
        rad, fl = fr["rad"], fr["flash"]
        # 虹色のカゴ(外の円と、のびた放射状の線のあいだ)
        ctx.arc(CX, CY, R + 3, 0, 2 * math.pi)
        ctx.close_path()
        ctx.move_to(CX + rad[0] * COS[0], CY + rad[0] * SIN[0])
        for i in range(N_RAY - 1, -1, -1):
            ctx.line_to(CX + rad[i] * COS[i], CY + rad[i] * SIN[i])
        ctx.close_path()
        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        ctx.save()
        ctx.clip()   # うまった所を虹色に(中心から見た向きで色が変わる)
        nseg = 180
        for k in range(nseg):
            a0 = 2 * math.pi * k / nseg
            a1 = a0 + 2 * math.pi / nseg + 0.004
            ctx.move_to(CX, CY)
            ctx.arc(CX, CY, R + 5, a0, a1)
            ctx.close_path()
            ctx.set_source_rgb(*colorsys.hsv_to_rgb(k / nseg, 0.62, 0.95))
            ctx.fill()
        ctx.restore()
        ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
        # のびたばかりの所はクリーム色に光る
        age = t - fl
        hot = np.nonzero((age < 0.8) & (rad < R - 1))[0]
        for i in hot:
            k = 1 - age[i] / 0.8
            j = (i + 1) % N_RAY
            ctx.move_to(CX + R * COS[i], CY + R * SIN[i])
            ctx.line_to(CX + rad[i] * COS[i], CY + rad[i] * SIN[i])
            ctx.line_to(CX + rad[j] * COS[j], CY + rad[j] * SIN[j])
            ctx.line_to(CX + R * COS[j], CY + R * SIN[j])
            ctx.close_path()
            ctx.set_source_rgba(*CREAM, 0.45 * k)
            ctx.fill()
        # 放射状の細い線(4本に1本)
        for i in range(0, N_RAY, 4):
            if rad[i] < R - 1:
                ctx.move_to(CX + R * COS[i], CY + R * SIN[i])
                ctx.line_to(CX + rad[i] * COS[i], CY + rad[i] * SIN[i])
        ctx.set_source_rgba(0.25, 0.05, 0.0, 0.55)
        ctx.set_line_width(1.0)
        ctx.stroke()
        ctx.arc(CX, CY, R + 3, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.85)
        ctx.set_line_width(4)
        ctx.stroke()
        # まん中の軸(とげが集まる中心の小さな丸。ここはすき間に数えない)
        ctx.arc(CX, CY, CORE + 2, 0, 2 * math.pi)
        ctx.set_source_rgb(0.92, 0.92, 0.95)
        ctx.fill()
        # ボール(白く光る・短い尾)
        if not over:
            trail.append((fr["x"], fr["y"]))
            trail = trail[-8:]
        for j in range(1, len(trail)):
            a = j / len(trail)
            ctx.move_to(*trail[j - 1])
            ctx.line_to(*trail[j])
            ctx.set_source_rgba(1, 1, 1, 0.35 * a)
            ctx.set_line_width(max(1.0, fr["r"] * 0.5 * a))
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()
        gr_ = max(26.0, fr["r"] * 2.4)   # 見失わないように、まわりに光の輪(当たり判定は本当の大きさのまま)
        g_ = cairo.RadialGradient(fr["x"], fr["y"], fr["r"], fr["x"], fr["y"], gr_)
        g_.add_color_stop_rgba(0, 1, 1, 1, 0.55)
        g_.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.arc(fr["x"], fr["y"], gr_, 0, 2 * math.pi)
        ctx.set_source(g_)
        ctx.fill()
        ctx.arc(fr["x"], fr["y"], fr["r"], 0, 2 * math.pi)
        cyc = hsv(win_b * 3) if win_b >= 0 else (1, 1, 1)
        ctx.set_source_rgb(*cyc)
        ctx.fill()
        # 文字(少なめ)
        chic(ctx, "円を完全にふさげる？", W / 2, 300, 66, rgb=(1, 0.88, 0.6))
        pct = int(fr["fill"] * 100)
        chic(ctx, f"{pct}%", W / 2, 420, 100, rgb=(1, 1, 1), weight="Medium")
        tt = min(t, end_t) if end_t is not None else t
        left = max(0.0, TIME_LIMIT - tt)
        chic(ctx, f"{left:4.1f}", W / 2, 490, 40, rgb=(1, 0.45, 0.45) if left < 5 else (0.7, 0.75, 0.85), weight="Medium")
        if not over:
            horror(ctx, "失敗したら…", W / 2, 1610, 74, t)
        if over and fail:
            k = min(1.0, after / 0.25)
            if res["trapped"]:
                chic(ctx, "閉じこめられた…", W / 2, 1000, 96 * (1.2 - 0.2 * k), rgb=(1, 0.4, 0.4))
            chic(ctx, f"{int(res['fill'] * 100)}%", W / 2, 1130, 90 * (1.2 - 0.2 * k), rgb=(1, 0.4, 0.4))
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['n']}回 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


PENTA = [0, 2, 4, 7, 9]


def boing(n, r):
    """はねた「ポン」+とげがのびる「シュッ」。ボールが小さくなるほど高い音。"""
    idx = min(19, int(n / 150 * 20))
    m = 55 + 12 * (idx // 5) + PENTA[idx % 5]
    f = midi_hz(m)
    t = _t(0.3)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 14) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 22)
    y += 0.3 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 30)
    nz = np.random.default_rng(n).normal(0, 1, len(t))
    y += 0.25 * (nz - np.convolve(nz, np.ones(5) / 5, "same")) * np.exp(-t * 35)
    return 0.5 * y * np.minimum(1, t / 0.002)


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    n_out = int((duration + 5) * SR)
    out = np.zeros(n_out)
    extra = np.zeros(n_out)

    def add(sig, t0, gain=1.0, buf=None):
        b = out if buf is None else buf
        i = int(t0 * SR)
        j = min(n_out, i + len(sig))
        if i < n_out and j > i:
            b[i:j] += gain * sig[: j - i]
    rb = []
    for kind, t, data in events:
        if t > end_t + 0.01:
            continue
        if kind == "bounce":
            rb = [x for x in rb if t - x < 0.04]
            if len(rb) >= 2:
                continue
            rb.append(t)
            add(boing(data[2], data[3]), t)
    wet = out.copy()
    for dd, g_ in ((0.043, 0.22), (0.071, 0.15), (0.113, 0.1)):
        kk = int(dd * SR)
        wet[kk:] += out[:-kk] * g_
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int(end_t * SR)]
    rms = np.sqrt(np.mean(body ** 2))
    if rms > 0:
        wet *= min(6.0, 10 ** (-14.0 / 20) / rms)
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
        tt = 0.0
        while tt < WIN_DUR - 0.5:
            ky = kyuin_one(1.0 + 0.15 * ((int(tt / 0.3)) % 3))
            i = int(tt * SR)
            m = min(len(ky), n - i)
            mus[i:i + m] += 0.4 * ky[:m]
            tt += 0.3
        tb = np.arange(int(1.5 * SR)) / SR
        boom = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-tb * 6) + 35) / SR) * np.exp(-tb * 2.5)
        mus[:len(boom)] += 0.9 * boom
        mus *= np.minimum(1, (WIN_DUR - np.arange(n) / SR) / 0.6)
        mus = np.tanh(1.6 * mus / (np.abs(mus).max() + 1e-9)) / np.tanh(1.6)
        i0 = int((end_t + PRE) * SR)
        m = min(len(mus), n_out - i0)
        extra[i0:i0 + m] += 1.1 * mus[:m]
        tt = 0.0
        while tt < PRE - 0.05:
            k = tt / PRE
            ky = kyuin_one(1.0 + 0.6 * k)
            i = int((end_t + tt) * SR)
            m = min(len(ky), n_out - i)
            extra[i:i + m] += (0.35 + 0.35 * k) * ky[:m]
            tt += 0.11 - 0.05 * k
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
