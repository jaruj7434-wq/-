"""「ピンクが勝てば成功!」ピンク vs ミントの陣取り合戦(マス目の陣地をボールが削り合う物理ショート)。

- 画面はマス目。左半分がピンクの陣地、右半分がミントの陣地。
- ピンクのボールはピンクの陣地の中を、ミントのボールはミントの陣地の中を、いつも同じ速さで跳ね回る。
  相手の色のマスに当たると、そのマスを自分の色に変えて跳ね返る(わくでも跳ね返る)。ねらいはしない(補正なし)。
- ときどきアイテムが出る。ボールがふれると取れる:
    ダッシュ  … 5秒間、速さが1.5倍
    巨大化    … 5秒間、ボールが2.4倍の大きさになって、一気に削る
    分身      … 7秒間、ボールが3つに分かれる
    バクダン  … 取った場所のまわりのマスを、まとめて自分の色にする
- 60秒たった時点で陣地が広いほうの勝ち。ピンクが勝てば成功(天使)、ミントが勝てば失敗(幽霊)。

使い方:
    python territory_war.py search [-n 100]
    python territory_war.py render --seed N
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
from ball_escape import text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from angels import DURATION as ANGEL_DUR, AngelShow, holy_music  # noqa: E402
from fail_bgm import fail_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 8
SR = 48000
OUT_DIR = os.path.join(HERE, "..", "..", "assets", "output")

COLS, ROWS = 24, 28
CELL = 37.5
BX0 = (W - COLS * CELL) / 2          # 盤の左上(画面の位置)
BY0 = 440.0
BW_, BH_ = COLS * CELL, ROWS * CELL
BALL_R = 20.0
SPEED = float(os.environ.get("SPEED", 560.0))
TIME_LIMIT = float(os.environ.get("TIME_LIMIT", 60.0))
TEAM_NAMES = ("ピンク", "ミント")
TERR = ((1.0, 0.72, 0.84), (0.66, 0.94, 0.86))     # 陣地の色(うすい)
BALLC = ((0.85, 0.08, 0.45), (0.0, 0.55, 0.45))    # ボールの色(こい)
ITEMS = ["dash", "big", "split", "bomb"]
ITEM_NAMES = {"dash": "ダッシュ", "big": "巨大化", "split": "分身", "bomb": "バクダン"}
BOMB_R = 6.0   # バクダンの範囲(マス)
ITEM_EVERY = float(os.environ.get("ITEM_EVERY", 2.6))
ITEM_MAX = 3
ITEM_R = 44.0
OUTRO = 4.2


class Ball:
    def __init__(self, team, x, y, ang, life=None):
        self.team = team
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(ang), math.sin(ang)   # 向き(長さ1)
        self.life = life          # 分身のボールは時間で消える
        self.dash_until = -1.0
        self.big_until = -1.0

    def r(self, t):
        return BALL_R * (2.4 if t < self.big_until else 1.0)

    def speed(self, t):
        return SPEED * (1.5 if t < self.dash_until else 1.0)


class Game:
    def __init__(self, seed):
        self.rng = rng = np.random.default_rng(seed)
        self.grid = np.zeros((ROWS, COLS), np.int8)
        self.grid[:, COLS // 2:] = 1
        self.balls = [Ball(0, BW_ * 0.25, BH_ * rng.uniform(0.3, 0.7), rng.uniform(-1, 1) + math.pi * rng.integers(0, 2)),
                      Ball(1, BW_ * 0.75, BH_ * rng.uniform(0.3, 0.7), rng.uniform(-1, 1) + math.pi * rng.integers(0, 2))]
        self.items = []           # [種類, x, y, 出た時刻]
        self.next_item = 1.5
        self.t = 0.0
        self.events = []
        self.result, self.result_t = None, None

    def cell_of(self, x, y):
        c, r = int(x // CELL), int(y // CELL)
        if 0 <= c < COLS and 0 <= r < ROWS:
            return r, c
        return None

    def flip(self, r, c, team):
        if self.grid[r, c] != team:
            self.grid[r, c] = team
            self.events.append(("flip", self.t, team))
            return True
        return False

    def move(self, b, dt):
        sp = b.speed(self.t)
        rad = b.r(self.t)
        b.x += b.vx * sp * dt
        b.y += b.vy * sp * dt
        # わく
        if b.x < rad:
            b.x, b.vx = rad, abs(b.vx)
        if b.x > BW_ - rad:
            b.x, b.vx = BW_ - rad, -abs(b.vx)
        if b.y < rad:
            b.y, b.vy = rad, abs(b.vy)
        if b.y > BH_ - rad:
            b.y, b.vy = BH_ - rad, -abs(b.vy)
        # 相手の色のマスに当たったら、自分の色に変えて跳ね返る(ボールのふちの点で調べる)
        hit_x = hit_y = False
        n = 16 if rad > BALL_R else 8
        for k in range(n):
            a = 2 * math.pi * k / n
            px, py = b.x + rad * math.cos(a), b.y + rad * math.sin(a)
            rc = self.cell_of(px, py)
            if rc is None or self.grid[rc] == b.team:
                continue
            self.flip(rc[0], rc[1], b.team)
            if rad > BALL_R:   # 巨大化中は跳ね返らずに突き進む
                continue
            if abs(math.cos(a)) > abs(math.sin(a)):
                hit_x = True if (math.cos(a) * b.vx > 0) else hit_x
            else:
                hit_y = True if (math.sin(a) * b.vy > 0) else hit_y
        if hit_x:
            b.vx = -b.vx
        if hit_y:
            b.vy = -b.vy

    def use_item(self, b, kind):
        t = self.t
        self.events.append(("item", t, (b.team, kind, b.x, b.y)))
        if kind == "dash":
            b.dash_until = t + 5.0
        elif kind == "big":
            b.big_until = t + 5.0
        elif kind == "split":
            a0 = math.atan2(b.vy, b.vx)
            for d in (2.1, -2.1):
                nb = Ball(b.team, b.x, b.y, a0 + d, life=t + 7.0)
                self.balls.append(nb)
        elif kind == "bomb":
            rc = self.cell_of(b.x, b.y)
            if rc is not None:
                for r in range(ROWS):
                    for c in range(COLS):
                        if (r - rc[0]) ** 2 + (c - rc[1]) ** 2 <= BOMB_R ** 2:
                            self.flip(r, c, b.team)

    def step(self, dt):
        self.t += dt
        if self.result is None:
            for b in list(self.balls):
                if b.life is not None and self.t > b.life:
                    self.balls.remove(b)
                    continue
                self.move(b, dt)
            # アイテム
            if self.t >= self.next_item and len(self.items) < ITEM_MAX:
                kind = ITEMS[int(self.rng.integers(0, len(ITEMS)))]
                x = self.rng.uniform(1.5, COLS - 1.5) * CELL
                y = self.rng.uniform(1.5, ROWS - 1.5) * CELL
                self.items.append([kind, x, y, self.t])
                self.next_item = self.t + ITEM_EVERY
            for it in list(self.items):
                for b in self.balls:
                    if math.hypot(b.x - it[1], b.y - it[2]) < b.r(self.t) + ITEM_R:
                        self.items.remove(it)
                        self.use_item(b, it[0])
                        break
            if self.t >= TIME_LIMIT:
                pink = int((self.grid == 0).sum())
                self.final = (pink, ROWS * COLS - pink)
                self.result = "success" if pink > ROWS * COLS - pink else "fail"
                self.result_t = self.t
                self.events.append((self.result, self.t, self.final))


def simulate(seed, record=False):
    g = Game(seed)
    frames = []
    dt = 1 / FPS / SUBSTEPS
    while True:
        for _ in range(SUBSTEPS):
            g.step(dt)
        if record:
            frames.append({"t": g.t, "grid": g.grid.copy(),
                           "balls": [(b.team, b.x, b.y, b.r(g.t), b.life is not None, g.t < b.dash_until) for b in g.balls],
                           "items": [tuple(it) for it in g.items]})
        if g.result is not None:
            extra = OUTRO + SCARE_DUR if g.result == "fail" else ANGEL_DUR
            if not record or g.t > g.result_t + extra:
                break
    return {"events": g.events, "frames": frames, "result": g.result, "result_t": g.result_t, "final": g.final}


def score(seed):
    r = simulate(seed)
    p, m = r["final"]
    return seed, r["result"], p, m


def search(n):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    print(f"{n} シード中 ピンクの勝ち {sum(r[1] == 'success' for r in rs)} 件")
    for r in rs:
        print(r)


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
VIEW_S = 0.82
BG = (0.07, 0.06, 0.1)


def draw_icon(ctx, kind, x, y, s, t):
    """アイテムの絵。中身がひと目でわかる絵+下に名前。"""
    if s <= 0.5:
        return
    s *= 1 + 0.06 * math.sin(t * 6)
    u = s / 2
    ctx.save()
    ctx.translate(x, y)
    # 下地の白い丸(盤の色と区別するため)
    ctx.arc(0, 0, u * 1.25, 0, 2 * math.pi)
    ctx.set_source_rgba(1, 1, 1, 0.92)
    ctx.fill_preserve()
    ctx.set_source_rgb(0.15, 0.15, 0.2)
    ctx.set_line_width(3)
    ctx.stroke()
    dark = (0.15, 0.15, 0.2)
    if kind == "dash":   # 走るボール+うしろに速さの線+前向きの矢印
        ctx.set_source_rgb(1.0, 0.6, 0.0)
        ctx.arc(0.3 * u, 0, 0.42 * u, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(*dark)
        ctx.set_line_width(max(2.0, 0.12 * u))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for dy, l in ((-0.32, 0.55), (0, 0.75), (0.32, 0.55)):
            ctx.move_to(-0.25 * u, dy * u)
            ctx.line_to(-(0.25 + l) * u, dy * u)
            ctx.stroke()
    elif kind == "big":  # 小さいボール→大きいボール(外向きの矢印)
        ctx.set_source_rgb(0.55, 0.35, 1.0)
        ctx.arc(0, 0, 0.5 * u, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(*dark)
        ctx.set_line_width(max(2.0, 0.1 * u))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            cx_, cy_ = math.cos(a), math.sin(a)
            ctx.move_to(0.62 * u * cx_, 0.62 * u * cy_)
            ctx.line_to(1.02 * u * cx_, 1.02 * u * cy_)
            ctx.stroke()
            for da in (-0.5, 0.5):   # 矢印の先
                ctx.move_to(1.02 * u * cx_, 1.02 * u * cy_)
                ctx.line_to(1.02 * u * cx_ - 0.22 * u * math.cos(a + da), 1.02 * u * cy_ - 0.22 * u * math.sin(a + da))
                ctx.stroke()
    elif kind == "split":  # 1個のボールから2個の分身(うすい色)
        ctx.set_source_rgba(0.2, 0.6, 1.0, 0.45)
        ctx.arc(-0.5 * u, -0.38 * u, 0.3 * u, 0, 2 * math.pi)
        ctx.fill()
        ctx.arc(-0.5 * u, 0.38 * u, 0.3 * u, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(0.2, 0.6, 1.0)
        ctx.arc(0.35 * u, 0, 0.38 * u, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(*dark)
        ctx.set_line_width(max(2.0, 0.08 * u))
        ctx.set_dash([0.12 * u, 0.1 * u])
        ctx.move_to(0.0, -0.1 * u)
        ctx.line_to(-0.3 * u, -0.3 * u)
        ctx.move_to(0.0, 0.1 * u)
        ctx.line_to(-0.3 * u, 0.3 * u)
        ctx.stroke()
        ctx.set_dash([])
    else:  # バクダン(黒い玉+導火線+火花)
        ctx.set_source_rgb(0.08, 0.08, 0.1)
        ctx.arc(-0.08 * u, 0.15 * u, 0.6 * u, 0, 2 * math.pi)
        ctx.fill()
        ctx.rectangle(0.12 * u, -0.6 * u, 0.3 * u, 0.25 * u)
        ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.6)
        ctx.arc(-0.3 * u, -0.05 * u, 0.13 * u, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(0.55, 0.4, 0.2)
        ctx.set_line_width(max(2.0, 0.09 * u))
        ctx.move_to(0.27 * u, -0.6 * u)
        ctx.curve_to(0.35 * u, -0.95 * u, 0.7 * u, -0.8 * u, 0.7 * u, -1.0 * u)
        ctx.stroke()
        f = 1 + 0.5 * abs(math.sin(t * 15))
        ctx.set_source_rgb(1, 0.5, 0.1)
        ctx.arc(0.7 * u, -1.02 * u, 0.2 * u * f, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(1, 0.95, 0.3)
        ctx.arc(0.7 * u, -1.02 * u, 0.1 * u * f, 0, 2 * math.pi)
        ctx.fill()
    ctx.restore()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"territory_war_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"territory_war_{seed}.wav")
    final = os.path.join(OUT_DIR, f"territory_war_{seed}.mp4")
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
                        surf.write_to_png(os.path.join(OUT_DIR, f"tw_preview_{pt:.1f}.png"))
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
    angels = AngelShow(W, H, seed) if not fail else None
    changed = np.full((ROWS, COLS), -9.0)   # マスの色が変わった時刻(光らせる)
    prev = None
    labels = []
    booms = []
    trails = []
    ev_i = 0
    pink_final, mint_final = res["final"]
    for fi, fr in enumerate(frames):
        t = fr["t"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "item":
                team, it, x, y = data
                labels.append((f"{TEAM_NAMES[team]}が{ITEM_NAMES[it]}!", BALLC[team], et))
                if it == "bomb":
                    booms.append((x, y, et))
            ev_i += 1
        grid = fr["grid"]
        if prev is not None:
            changed[grid != prev] = t
        prev = grid
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - SCARE_DUR) if (fail and over) else 0
        ctx.set_source_rgb(*BG)
        ctx.paint()
        ctx.save()   # 見た目だけ縮小(TikTokの下の文字が隠れないように)
        ctx.translate(W / 2, BY0)
        ctx.scale(VIEW_S, VIEW_S)
        ctx.translate(-W / 2, -BY0)
        # 盤
        for team in (0, 1):
            ctx.set_source_rgb(*TERR[team])
            rr, cc = np.nonzero(grid == team)
            for r, c in zip(rr, cc):
                ctx.rectangle(BX0 + c * CELL, BY0 + r * CELL, CELL + 0.6, CELL + 0.6)
            ctx.fill()
        rr, cc = np.nonzero(t - changed < 0.25)   # 色が変わったばかりのマスは白く光る
        for r, c in zip(rr, cc):
            a = 1 - (t - changed[r, c]) / 0.25
            ctx.rectangle(BX0 + c * CELL, BY0 + r * CELL, CELL, CELL)
            ctx.set_source_rgba(1, 1, 1, 0.6 * a)
            ctx.fill()
        ctx.rectangle(BX0 - 3, BY0 - 3, BW_ + 6, BH_ + 6)
        ctx.set_source_rgba(1, 1, 1, 0.8)
        ctx.set_line_width(4)
        ctx.stroke()
        for kind, x, y, t0 in ([] if over else fr["items"]):   # 終了後はアイテムを消して結果を読みやすく
            draw_icon(ctx, kind, BX0 + x, BY0 + y, 2 * ITEM_R / 1.25 * min(1.0, (t - t0) / 0.2), t)
        keep = []
        for x, y, t0 in booms:
            a = t - t0
            if a < 0.5:
                ctx.arc(BX0 + x, BY0 + y, 30 + (BOMB_R * CELL - 30) * min(1.0, a / 0.3), 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.6, 0.2, 0.8 * (1 - a / 0.5))
                ctx.set_line_width(12)
                ctx.stroke()
                keep.append((x, y, t0))
        booms = keep
        trails.append(fr["balls"])
        trails = trails[-8:]
        for k, bs in enumerate(trails[:-1]):   # ダッシュ中は残像
            for team, x, y, r, clone, dash in bs:
                if dash:
                    ctx.arc(BX0 + x, BY0 + y, r * (0.5 + 0.5 * k / 8), 0, 2 * math.pi)
                    ctx.set_source_rgba(*BALLC[team], 0.08 * k)
                    ctx.fill()
        for team, x, y, r, clone, dash in fr["balls"]:
            ctx.arc(BX0 + x, BY0 + y, r, 0, 2 * math.pi)
            ctx.set_source_rgba(*BALLC[team], 0.75 if clone else 1.0)
            ctx.fill_preserve()
            ctx.set_source_rgba(1, 1, 1, 0.9)
            ctx.set_line_width(3)
            ctx.stroke()
        ctx.restore()
        if angels is not None and over:
            angels.draw(ctx, t - end_t)
        # 文字
        text(ctx, "ピンク", W / 2 - 220, 235, 84, rgb=BALLC[0], sw=12)
        text(ctx, "VS", W / 2, 235, 70, rgb=(1, 1, 1), sw=12)
        text(ctx, "ミント", W / 2 + 220, 235, 84, rgb=BALLC[1], sw=12)
        text(ctx, "ピンクが勝てば成功！", W / 2, 345, 70, rgb=GOLD, sw=12)
        labels = [l_ for l_ in labels if t - l_[2] < 1.3]
        for j, (s_, col, t0) in enumerate(labels[-1:]):
            k2 = min(1.0, (t - t0) / 0.12)
            text(ctx, s_, W / 2, 410, 46 * (1.2 - 0.2 * k2), rgb=(1, 1, 1), sw=8)
        # 陣地の割合のバー
        pink = int((grid == 0).sum())
        tot = ROWS * COLS
        bx, by, bw, bh = 90, BY0 + BH_ * VIEW_S + 30, W - 180, 44
        ctx.rectangle(bx, by, bw * pink / tot, bh)
        ctx.set_source_rgb(*BALLC[0])
        ctx.fill()
        ctx.rectangle(bx + bw * pink / tot, by, bw * (1 - pink / tot), bh)
        ctx.set_source_rgb(*BALLC[1])
        ctx.fill()
        ctx.rectangle(bx, by, bw, bh)
        ctx.set_source_rgb(1, 1, 1)
        ctx.set_line_width(3)
        ctx.stroke()
        ctx.move_to(bx + bw / 2, by - 8)
        ctx.line_to(bx + bw / 2, by + bh + 8)
        ctx.stroke()
        text(ctx, f"{100 * pink / tot:.1f}%", bx + 85, by + bh + 52, 46, rgb=BALLC[0], sw=8)
        text(ctx, f"{100 * (tot - pink) / tot:.1f}%", bx + bw - 85, by + bh + 52, 46, rgb=BALLC[1], sw=8)
        left = max(0.0, TIME_LIMIT - min(t, end_t if end_t is not None else t))
        text(ctx, f"残り {left:4.1f}秒", W / 2, by + bh + 52, 50, rgb=(1, 0.4, 0.4) if left < 10 else (0.95, 0.95, 0.95), sw=8)
        if over:   # 結果の文字のうしろに暗い帯
            ctx.rectangle(0, 790 if fail else 660, W, 300)
            ctx.set_source_rgba(0, 0, 0, 0.55)
            ctx.fill()
        if over and fail:
            k = min(1.0, after / 0.25)
            text(ctx, "ミントの勝ち…", W / 2, 900, 110 * (1.3 - 0.3 * k), rgb=BALLC[1], sw=18)
            text(ctx, f"ピンク {pink_final}マス ・ ミント {mint_final}マス", W / 2, 1030, 56, sw=10)
        elif over:
            text(ctx, "ピンクの勝ち!!", W / 2, 760, 120, rgb=BALLC[0], sw=18)
            text(ctx, "成功!!", W / 2, 900, 110, rgb=GOLD, sw=18)
        text(ctx, "ピンクが負けたら・・・", W / 2, 1530, 64, rgb=(1, 1, 1), sw=12)
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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} ピンク{pink_final} ミント{mint_final} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
def _t(d):
    return np.arange(int(d * SR)) / SR


def pop(f, amp):
    t = _t(0.07)
    return amp * np.sin(2 * np.pi * f * t * (1 + 1.5 * t)) * np.exp(-t * 55)


def chime(amp):
    t = _t(0.5)
    y = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * 6) * (t >= d) for f, d in ((1320, 0), (1760, 0.06), (2640, 0.12)))
    return amp * y


def whoosh_up(amp, dur=0.4):
    t = _t(dur)
    f = 300 + 1500 * (t / dur) ** 2
    return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / dur)


def boom(amp, seed=1):
    t = _t(1.0)
    n = np.convolve(np.random.default_rng(seed).normal(0, 1, len(t)), np.ones(10) / 10, "same")
    return amp * (np.sin(2 * np.pi * 55 * t) * np.exp(-t * 4) + 1.4 * n * np.exp(-t * 6))


def tick(amp):
    t = _t(0.05)
    return amp * np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 80)


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
    rng = np.random.default_rng(3)
    last = [-1.0, -1.0]
    for kind, t, data in events:
        if end_t is not None and t > end_t + 0.01:
            continue
        if kind == "flip":   # マスを取る「ポコッ」(ピンクは高め、ミントは低め)
            if t - last[data] > 0.03:
                add(pop((900 if data == 0 else 600) * rng.uniform(0.95, 1.08), 0.5), t)
                last[data] = t
        elif kind == "item":
            team, it, x, y = data
            add(chime(0.5), t)
            if it == "dash":
                add(whoosh_up(0.6), t + 0.05)
            elif it == "big":
                add(whoosh_up(0.6, 0.7)[::-1], t + 0.05)
            elif it == "split":
                for k, f in enumerate((700, 900, 1100)):
                    add(pop(f, 0.8), t + 0.06 * k)
            else:
                add(boom(1.0), t)
    for k in range(5, 0, -1):   # 最後の5秒はカウントダウン
        add(tick(0.8), TIME_LIMIT - k)
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
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(end_t * SR) + int(0.3 * SR)
        m = min(len(sig), n_out - i0)
        extra[i0:i0 + m] += 0.85 * sig[:m]
    wet = out.copy()
    for dd, g in ((0.043, 0.2), (0.071, 0.13)):
        k = int(dd * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    loud = np.abs(wet[np.abs(wet) > 1e-4])
    ref = np.percentile(loud, 99.5) if len(loud) else 1.0
    wet = np.tanh(1.5 * wet / max(1e-9, ref)) / np.tanh(1.5) * 0.7
    body = wet[: int(end_t * SR)]
    rms = np.sqrt(np.mean(body ** 2))
    if rms > 0:
        wet *= min(6.0, 10 ** (-14.0 / 20) / rms)
    wet = wet + (0.95 if fail else 1.0) * extra[: len(wet)]
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
    ap.add_argument("-n", type=int, default=100)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
