"""「最後のドミノまで倒れる?」剛体物理(倒れる・回転・摩擦・運動量の受け渡し)のショートを生成する。

ドミノは画面を5段にジグザグで並ぶ。段の終わりでは最後のドミノがボールを押し出し、
ボールが坂を転がって次の段の最初のドミノに当たる。金色のゴールドミノが倒れたら成功。
途中で連鎖が止まったら失敗(幽霊が出る)。

使い方:
    python domino.py search [--want fail|success]
    python domino.py render --seed N
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
from ball_escape import hue_rgb, midi_hz, noise, text, tone  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 6
SR = 48000
GRAVITY = 1500.0

ROWS = 5
FLOOR_Y0, FLOOR_DY = 640, 190
X_LEFT, X_RIGHT = 150, 930          # 各段のドミノを並べる範囲
DOM_W, DOM_H = 14, 84
SPACING = 54.0                      # 標準の間隔
SPACING_SD = 4.0
N_RISKY = 2                         # 「間隔が広くて危ない」箇所の数
RISKY_RANGE = (86.0, 100.0)         # 倒れたドミノが届く距離(約91px)の前後。届くかどうかギリギリ
BALL_R = 22
START_INSET = 130                   # 2段目以降は、上から落ちてくるボール用の坂の分だけ内側から並べる

STOP_WAIT = 1.4                     # 何も倒れない時間がこれだけ続いたら失敗確定
MAX_T = 40.0
OUTRO = 3.0

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


def floor_y(row):
    return FLOOR_Y0 + row * FLOOR_DY


# ---------------------------------------------------------------- コース作り
def build(seed):
    rng = np.random.default_rng(seed)
    space = pymunk.Space()
    space.gravity = (0, GRAVITY)
    space.iterations = 30
    static = space.static_body
    shapes = []

    def seg(a, b, r=4):
        s = pymunk.Segment(static, a, b, r)
        s.friction = 1.2
        s.elasticity = 0.1
        space.add(s)
        shapes.append((a, b))

    # ドミノの位置を決める(危ない箇所をいくつか混ぜる)
    xs_per_row = []
    for row in range(ROWS):
        xs = []
        x = X_LEFT + 20 + (START_INSET if row > 0 else 0)
        while x < X_RIGHT - 20:
            xs.append(x)
            x += SPACING + rng.normal(0, SPACING_SD)
        xs_per_row.append(xs)
    gaps = [(r, i) for r in range(ROWS) for i in range(1, len(xs_per_row[r]))]
    risky = set(map(tuple, rng.permutation(gaps)[:N_RISKY].tolist()))
    row_pos = []
    for row in range(ROWS):
        xs = xs_per_row[row]
        pos = [xs[0]]
        for i in range(1, len(xs)):
            d = rng.uniform(*RISKY_RANGE) if (row, i) in risky else xs[i] - xs[i - 1]
            pos.append(pos[-1] + d)
        pos = [p for p in pos if p <= W - 90 - 105]   # 段の終わりのボールが壁から 90px 以上離れるようにする
        if row % 2 == 1:
            pos = [W - p for p in pos]   # 右から左へ並べる
        row_pos.append(pos)

    # 段の終わりのボール位置(最後のドミノの先)。床はボールの真下で終わらせ、少し押されたら落ちるようにする
    # 倒れたドミノの先端がボールの中心の高さに当たり、横に押し出せる距離(約105px)に置く
    ball_x = [row_pos[r][-1] + 105 * (1 if r % 2 == 0 else -1) for r in range(ROWS - 1)]

    # 段ごとの床と、段の間をつなぐ坂
    for row in range(ROWS):
        y = floor_y(row)
        rightward = row % 2 == 0
        x0 = 40 if row == 0 else 60
        if row == ROWS - 1:
            seg((x0, y), (1000, y) if rightward else (1040, y))
        elif rightward:
            seg((x0, y), (ball_x[row] + 3, y))
        else:
            seg((ball_x[row] - 3, y), (1040, y))
        if row > 0:
            # 上の段から落ちてきたボールを受け止め、最初のドミノへ転がす坂
            bx_prev, first_x = ball_x[row - 1], row_pos[row][0]
            # 坂は壁ぎわから始める。上の段の床の端との間にボールが挟まらないよう、
            # 坂の上端は上の床より 70px 下げてすき間を空ける
            top = y - FLOOR_DY + 70
            if rightward:
                seg((12, top), (first_x - 70, y))
            else:
                seg((W - 12, top), (first_x + 70, y))
    # 画面の左右の壁(ボールが外へ飛び出さないように)
    seg((6, floor_y(0) - 260), (6, floor_y(ROWS - 1)))
    seg((1074, floor_y(0) - 260), (1074, floor_y(ROWS - 1)))
    # スタートの坂(左上からボールが転がってくる)
    seg((30, floor_y(0) - 170), (90, floor_y(0) - 8))

    dominos = []
    for row in range(ROWS):
        for p in row_pos[row]:
            body = pymunk.Body(1.0, pymunk.moment_for_box(1.0, (DOM_W, DOM_H)))
            body.position = (p, floor_y(row) - 4 - DOM_H / 2)
            box = pymunk.Poly.create_box(body, (DOM_W, DOM_H))
            box.friction = 1.0
            box.elasticity = 0.0
            space.add(body, box)
            dominos.append({"body": body, "row": row, "fallen_t": None})

    balls = []
    for row in range(ROWS - 1):
        b = pymunk.Body(1.5, pymunk.moment_for_circle(1.5, 0, BALL_R))
        b.position = (ball_x[row], floor_y(row) - 4 - BALL_R)
        c = pymunk.Circle(b, BALL_R)
        c.friction = 0.25   # 低めにして、倒れたドミノとボールが摩擦で噛み合って止まらないようにする
        c.elasticity = 0.2
        space.add(b, c)
        balls.append(b)
    # スタートのボール
    sb = pymunk.Body(0.8, pymunk.moment_for_circle(0.8, 0, BALL_R))
    sb.position = (36, floor_y(0) - 190)
    sc = pymunk.Circle(sb, BALL_R)
    sc.friction = 0.9
    space.add(sb, sc)
    balls.insert(0, sb)
    return space, dominos, balls, shapes


def settled(dominos, balls):
    """すべてのボールとドミノがほぼ止まっているか。"""
    if any(b.velocity.length > 12 for b in balls):
        return False
    return all(abs(d["body"].angular_velocity) < 0.08 and d["body"].velocity.length < 12 for d in dominos)


def simulate(seed, record=False):
    space, dominos, balls, shapes = build(seed)
    dt = 1 / FPS / SUBSTEPS
    t = 0.0
    events = []
    frames = []
    last_fall_t = 0.0
    result, result_t = None, None
    goal = dominos[-1]
    while t < MAX_T:
        for _ in range(SUBSTEPS):
            space.step(dt)
            t += dt
        for i, d in enumerate(dominos):
            if d["fallen_t"] is None and abs(d["body"].angle) > math.radians(25):
                d["fallen_t"] = t
                last_fall_t = t
                events.append(("fall", t, i))
        if result is None:
            if goal["fallen_t"] is not None:
                result, result_t = "success", goal["fallen_t"]
                events.append(("success", t, len(dominos) - 1))
            elif t - last_fall_t > STOP_WAIT and t > 2.5 and settled(dominos, balls):
                result, result_t = "fail", t
                events.append(("fail", t, None))
        if record:
            frames.append((t, [(d["body"].position.x, d["body"].position.y, d["body"].angle) for d in dominos],
                           [(b.position.x, b.position.y) for b in balls]))
        if result is not None and t > result_t + (OUTRO + (SCARE_DUR if result == "fail" else 0)):
            break
        if result is not None and not record:
            break
    fallen = sum(1 for d in dominos if d["fallen_t"] is not None)
    return {"dominos": dominos, "shapes": shapes, "events": events, "frames": frames,
            "result": result, "result_t": result_t, "fallen": fallen, "total": len(dominos)}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["fallen"], r["total"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "fail":
        good = sorted([r for r in rs if r[1] == "fail"], key=lambda r: r[4] - r[3])
        for seed, _, rt, fa, to in good[:15]:
            print(f"seed={seed:4d}  {fa}/{to} 本倒れて停止(残り {to - fa} 本)  確定 {rt:5.2f}秒")
    else:
        for seed, _, rt, fa, to in sorted(succ, key=lambda r: -r[2])[:15]:
            print(f"seed={seed:4d}  成功 {rt:5.2f}秒  {to} 本")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.82, 0.25)


def rounded(ctx, x, y, w, h, r):
    ctx.new_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def background(shapes):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.RadialGradient(W / 2, 1000, 50, W / 2, 1000, 1300)
    g.add_color_stop_rgb(0, 0.09, 0.07, 0.20)
    g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
    ctx.set_source(g)
    ctx.paint()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for a, b in shapes:
        for wdt, al in ((22, 0.07), (12, 0.16), (6, 0.9)):
            ctx.new_path()
            ctx.move_to(*a)
            ctx.line_to(*b)
            ctx.set_source_rgba(0.55, 0.62, 1.0, al)
            ctx.set_line_width(wdt)
            ctx.stroke()
    return surf


def render(seed):
    res = simulate(seed, record=True)
    dominos, events, frames = res["dominos"], res["events"], res["frames"]
    result, end_t, total = res["result"], res["result_t"], res["total"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"domino_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"domino_{seed}.wav")
    final = os.path.join(OUT_DIR, f"domino_{seed}.mp4")

    bg = background(res["shapes"])
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    rng = np.random.default_rng(seed + 999)
    particles = []
    fall_t = {}
    ev_i = 0
    gx0, gy0, _ = frames[0][1][-1]   # ゴールドミノの最初の位置
    for fi, (t, doms, balls) in enumerate(frames):
        dt = 1 / FPS
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, idx = events[ev_i]
            if kind == "fall":
                fall_t[idx] = et
            elif kind == "success":
                for _ in range(260):
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
        # ゴールの目印
        text(ctx, "GOAL", gx0, gy0 - DOM_H / 2 - 20, 40, rgb=GOLD, sw=8)

        # ドミノ
        for i, (x, y, ang) in enumerate(doms):
            goal = i == total - 1
            col = GOLD if goal else hue_rgb((i / total) * 0.85)
            flash = max(0.0, 1 - (t - fall_t.get(i, -9)) / 0.15)
            if fail and over and goal:   # 最後まで立っていたゴールを赤く点滅
                pulse = 0.5 + 0.5 * math.sin(after * 10)
                col = (1, 0.25 + 0.3 * pulse, 0.25 + 0.3 * pulse)
            c2 = tuple(v + (1 - v) * flash * 0.7 for v in col)
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(ang)
            for grow, al in ((10, 0.10), (5, 0.20)):
                rounded(ctx, -DOM_W / 2 - grow, -DOM_H / 2 - grow, DOM_W + 2 * grow, DOM_H + 2 * grow, 6 + grow)
                ctx.set_source_rgba(*c2, al)
                ctx.fill()
            rounded(ctx, -DOM_W / 2, -DOM_H / 2, DOM_W, DOM_H, 4)
            ctx.set_source_rgba(*c2, 1)
            ctx.fill()
            ctx.restore()

        # ボール
        for bx, by in balls:
            for rr, al in ((BALL_R * 2.0, 0.12), (BALL_R * 1.45, 0.25)):
                ctx.new_path()
                ctx.arc(bx, by, rr, 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.4, 0.7, al)
                ctx.fill()
            ctx.new_path()
            ctx.arc(bx, by, BALL_R, 0, 2 * math.pi)
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill()

        # 紙吹雪
        alive = []
        for p in particles:
            p[4] += dt
            if p[4] >= p[5]:
                continue
            p[3] += GRAVITY * 0.5 * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            ctx.new_path()
            ctx.rectangle(p[0] - 7, p[1] - 4, 14, 8)
            ctx.set_source_rgba(*p[6], 1 - p[4] / p[5])
            ctx.fill()
            alive.append(p)
        particles = alive

        # 文字
        fallen = sum(1 for k in fall_t if fall_t[k] <= t)
        text(ctx, "最後のドミノまで", W / 2, 200, 84, sw=14)
        text(ctx, "倒れる？", W / 2, 320, 120, rgb=(1, 0.86, 0.2), sw=18)
        text(ctx, "Will the last domino fall?", W / 2, 385, 40, rgb=(0.85, 0.85, 0.9), sw=8)
        text(ctx, f"{fallen} / {total}", W / 2, 490, 86, rgb=(1, 0.3, 0.3) if (fail and over) else (1, 1, 1), sw=12)
        if not over:
            text(ctx, "※失敗すると…アレが出ます", W / 2, 1530, 50, rgb=(1, 0.35, 0.35), sw=10)
        elif fail:
            k = min(1.0, after / 0.25)
            left = total - fallen
            text(ctx, "止まった…", W / 2, 1000, 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"ゴールまで あと{left}本", W / 2, 1130, 70, sw=12)
            text(ctx, "あと少しだったのに…", W / 2, 1530, 56, rgb=(0.9, 0.9, 0.95), sw=10)
        else:
            k = min(1.0, (t - end_t) / 0.25)
            text(ctx, "全部たおれた！", W / 2, 1000, 130 * (1.6 - 0.6 * k), rgb=(1, 0.86, 0.2), sw=20)
            text(ctx, f"{end_t:.2f}秒", W / 2, 1130, 90, sw=14)

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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['fallen']}/{total} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
# ベートーヴェン「エリーゼのために」(1810年・パブリックドメイン)冒頭の旋律
MELODY = [76, 75, 76, 75, 76, 71, 74, 72, 69, 60, 64, 69, 71, 64, 68, 71, 72,
          64, 76, 75, 76, 75, 76, 71, 74, 72, 69, 60, 64, 69, 71, 64, 72, 71, 69]


def synth_audio(events, end_t, fail, duration, path):
    rng = np.random.default_rng(0)
    out = np.zeros(int((duration + 3) * SR))

    def add(sig, t0):
        i = int(t0 * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    note_i = 0
    for kind, t, idx in events:
        if kind == "fall":
            m = MELODY[note_i % len(MELODY)]
            add(tone(midi_hz(m), 0.6, 0.40, 5), t)
            add(noise(0.03, 0.25, 90, rng, smooth=2), t)   # カチッという当たる音
            note_i += 1
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
            add(tone(midi_hz(69 + iv), 2.5, 0.25, 1.2), end_t)
        add(noise(1.5, 0.25, 2.5, rng, smooth=2), end_t)
    wet = out.copy()
    for d, g in ((0.043, 0.3), (0.071, 0.24), (0.113, 0.17)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    # 通常部分は軽く圧縮して聞こえやすくし、叫び声との差は約10dBに抑える
    # (ドミノは音が密に鳴るので、ほかの回より控えめの 0.42 にする)
    wet = np.tanh(2.5 * wet / max(1e-9, np.max(np.abs(wet)))) / np.tanh(2.5) * 0.42
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
    ap.add_argument("--want", choices=["fail", "success"], default="fail")
    ap.add_argument("-n", type=int, default=200)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
