"""「30秒で全部こわせる?」ブロック崩し型の物理シミュレーションショートを生成する。

ブロックの数字は耐久値。ボールが当たるたびに1減り、0で壊れる。
「+2」ブロックを壊すとボールが2つ増える。

使い方:
    python block_break.py search [--want fail|success]   # 結末の条件に合うシードを探す
    python block_break.py render --seed N                # 指定シードで動画を書き出す
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ball_escape"))
from ball_escape import hue_rgb, midi_hz, noise, text, tone  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402

W, H = 1080, 1920
FPS = 60
SUBSTEPS = 8
TIME_LIMIT = 30.0
OUTRO = 3.0 + 1.25   # 失敗時は幽霊の出ている時間ぶん長くする
SCARE = True        # 失敗したときに幽霊を出すか
SR = 48000

AX0, AX1, AY0, AY1 = 70, 1010, 540, 1420   # 枠
COLS, ROWS = 8, 6
GAP = 10
BX0, BY0 = AX0 + 20, AY0 + 30
CW = (AX1 - AX0 - 40 - GAP * (COLS - 1)) / COLS
CH = 62
BALL_R = 14
SPEED = 1050.0
N_PLUS = 6
HP_BASE = 1
START_BALLS = 2
PLUS_BALLS = 2   # 「+N」ブロックを壊したときに増えるボール数

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


# ---------------------------------------------------------------- シミュレーション
def make_bricks(rng):
    bricks = []
    plus_cells = set(rng.choice(COLS * ROWS, N_PLUS, replace=False).tolist())
    for row in range(ROWS):
        for col in range(COLS):
            idx = row * COLS + col
            x = BX0 + col * (CW + GAP)
            y = BY0 + row * (CH + GAP)
            if idx in plus_cells:
                hp, plus = 1, True
            else:
                hp, plus = int(rng.integers(1, 4)) + HP_BASE + (ROWS - 1 - row) // 2, False
            bricks.append({"x": x, "y": y, "hp": hp, "hp0": hp, "plus": plus, "col": col, "row": row})
    return bricks


def launch(rng, x, y):
    a = math.radians(rng.uniform(-150, -30))
    return [x, y, SPEED * math.cos(a), SPEED * math.sin(a)]


def collide_brick(b, br):
    """円と長方形の衝突。当たったら速度を反射して押し出し、True を返す。"""
    x, y, vx, vy = b
    nx_ = min(max(x, br["x"]), br["x"] + CW)
    ny_ = min(max(y, br["y"]), br["y"] + CH)
    dx, dy = x - nx_, y - ny_
    d2 = dx * dx + dy * dy
    if d2 > BALL_R * BALL_R:
        return False
    if d2 > 1e-9:
        d = math.sqrt(d2)
        nx, ny = dx / d, dy / d
        pen = BALL_R - d
    else:  # 中心が中に入った: 一番浅い面から押し出す
        cands = [(x - br["x"], -1, 0), (br["x"] + CW - x, 1, 0),
                 (y - br["y"], 0, -1), (br["y"] + CH - y, 0, 1)]
        pen, nx, ny = min(cands)
        pen += BALL_R
    dot = vx * nx + vy * ny
    if dot < 0:
        b[2], b[3] = vx - 2 * dot * nx, vy - 2 * dot * ny
    b[0] += nx * pen
    b[1] += ny * pen
    return True


def simulate(seed, record=False):
    rng = np.random.default_rng(seed)
    bricks = make_bricks(rng)
    balls = [launch(rng, W / 2, AY1 - 60) for _ in range(START_BALLS)]
    events = []
    frames = []
    dt = 1 / FPS / SUBSTEPS
    t = 0.0
    clear_t = None
    total = int((TIME_LIMIT + OUTRO) * FPS)
    for f in range(total):
        running = t < TIME_LIMIT and clear_t is None
        if running:
            for _ in range(SUBSTEPS):
                t += dt
                new_balls = []
                for b in balls:
                    b[0] += b[2] * dt
                    b[1] += b[3] * dt
                    if b[0] < AX0 + BALL_R:
                        b[0], b[2] = AX0 + BALL_R, abs(b[2])
                    if b[0] > AX1 - BALL_R:
                        b[0], b[2] = AX1 - BALL_R, -abs(b[2])
                    if b[1] < AY0 + BALL_R:
                        b[1], b[3] = AY0 + BALL_R, abs(b[3])
                    if b[1] > AY1 - BALL_R:
                        b[1], b[3] = AY1 - BALL_R, -abs(b[3])
                        events.append(("wall", t, b[0], b[1], None))
                    col = int((b[0] - BX0) // (CW + GAP))
                    row = int((b[1] - BY0) // (CH + GAP))
                    for rr in (row - 1, row, row + 1):
                        for cc in (col - 1, col, col + 1):
                            if not (0 <= rr < ROWS and 0 <= cc < COLS):
                                continue
                            br = bricks[rr * COLS + cc]
                            if br["hp"] <= 0 or not collide_brick(b, br):
                                continue
                            br["hp"] -= 1
                            if br["hp"] == 0:
                                events.append(("break", t, br["x"] + CW / 2, br["y"] + CH / 2, rr * COLS + cc))
                                if br["plus"]:
                                    new_balls.extend(launch(rng, br["x"] + CW / 2, br["y"] + CH / 2) for _ in range(PLUS_BALLS))
                                    events.append(("plus", t, br["x"] + CW / 2, br["y"] + CH / 2, None))
                            else:
                                events.append(("hit", t, br["x"] + CW / 2, br["y"] + CH / 2, rr * COLS + cc))
                    # 速さを一定に保つ(押し出しでの誤差を補正)
                    sp = math.hypot(b[2], b[3])
                    b[2], b[3] = b[2] * SPEED / sp, b[3] * SPEED / sp
                    # ほぼ水平・ほぼ垂直の往復にはまらないよう補正
                    if abs(b[3]) < SPEED * 0.15:
                        b[3] = math.copysign(SPEED * 0.15, b[3] or 1)
                    if abs(b[2]) < SPEED * 0.08:
                        b[2] = math.copysign(SPEED * 0.08, b[2] or 1)
                balls.extend(new_balls)
                if all(br["hp"] <= 0 for br in bricks):
                    clear_t = t
                    events.append(("clear", t, 0, 0, None))
                    break
            if t >= TIME_LIMIT and clear_t is None:
                events.append(("timeup", TIME_LIMIT, 0, 0, None))
        else:
            t += 1 / FPS
        if record:
            frames.append((t, [tuple(b[:2]) for b in balls], [br["hp"] for br in bricks]))
        elif not running:
            break
    return {"bricks": bricks, "events": events, "frames": frames, "clear_t": clear_t}


def score(seed):
    res = simulate(seed)
    left = [br for br in res["bricks"] if br["hp"] > 0]
    breaks = [e[1] for e in res["events"] if e[0] == "break"]
    return seed, res["clear_t"], len(left), sum(b["hp"] for b in left), (breaks[-1] if breaks else 0)


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    clears = [r for r in rs if r[1] is not None]
    print(f"{n} シード中 クリア {len(clears)} 件 / 時間切れ {n - len(clears)} 件")
    if want == "fail":
        good = [r for r in rs if r[1] is None and r[2] == 1 and r[3] == 1 and r[4] >= 20]
        good.sort(key=lambda r: -r[4])
        for seed, _, _, _, lb in good[:15]:
            print(f"seed={seed:4d}  残り1ブロック(耐久1)で時間切れ  最後に壊したのは {lb:5.2f}秒")
    else:
        good = sorted([r for r in clears if 27.5 <= r[1] <= 29.8], key=lambda r: -r[1])
        for seed, ct, *_ in good[:15]:
            print(f"seed={seed:4d}  クリア {ct:5.2f}秒")


# ---------------------------------------------------------------- 描画
def hp_color(hp, hp_max=12):
    return hue_rgb(0.62 - 0.62 * min(hp, hp_max) / hp_max, 0.75, 1.0)


def rounded(ctx, x, y, w, h, r):
    ctx.new_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def background():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.RadialGradient(W / 2, 980, 50, W / 2, 980, 1300)
    g.add_color_stop_rgb(0, 0.09, 0.07, 0.20)
    g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
    ctx.set_source(g)
    ctx.paint()
    for wdt, al in ((26, 0.08), (14, 0.18), (5, 0.9)):
        rounded(ctx, AX0 - 6, AY0 - 6, AX1 - AX0 + 12, AY1 - AY0 + 12, 22)
        ctx.set_source_rgba(0.55, 0.6, 1.0, al)
        ctx.set_line_width(wdt)
        ctx.stroke()
    return surf


def render(seed):
    res = simulate(seed, record=True)
    bricks, events, frames, clear_t = res["bricks"], res["events"], res["frames"], res["clear_t"]
    end_t = clear_t if clear_t is not None else TIME_LIMIT
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"block_break_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"block_break_{seed}.wav")
    final = os.path.join(OUT_DIR, f"block_break_{seed}.mp4")

    bg = background()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)

    rng = np.random.default_rng(seed + 999)
    ghost = GhostScare(W, H, seed) if SCARE and clear_t is None else None
    particles = []
    last_hit = {}
    trails = {}
    ev_i = 0
    for fi, (t, balls, hps) in enumerate(frames):
        dt = 1 / FPS
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, ex, ey, idx = events[ev_i]
            if kind in ("hit", "break"):
                last_hit[idx] = et
            if kind == "break":
                col = (0.3, 1, 0.5) if bricks[idx]["plus"] else hp_color(bricks[idx]["hp0"])
                for _ in range(28):
                    a = rng.uniform(0, 2 * math.pi)
                    sp = rng.uniform(120, 520)
                    particles.append([ex, ey, math.cos(a) * sp, math.sin(a) * sp, 0, rng.uniform(0.4, 0.9), col])
            ev_i += 1

        over = t >= end_t
        fail = over and clear_t is None
        if ghost is not None and 0 <= t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = t - end_t - (SCARE_DUR if ghost is not None else 0)  # 結果表示が始まってからの秒数
        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()

        # ブロック
        for i, br in enumerate(bricks):
            hp = hps[i]
            if hp <= 0:
                continue
            flash = max(0.0, 1 - (t - last_hit.get(i, -9)) / 0.12)
            col = (0.3, 1, 0.5) if br["plus"] else hp_color(hp)
            if fail:  # 最後に残ったブロックを点滅で強調
                pulse = 0.5 + 0.5 * math.sin(after * 12)
                col = (1, 0.25 + 0.3 * pulse, 0.25 + 0.3 * pulse)
            c2 = tuple(v + (1 - v) * flash * 0.8 for v in col)
            rounded(ctx, br["x"], br["y"], CW, CH, 12)
            ctx.set_source_rgba(*c2, 0.22)
            ctx.fill_preserve()
            ctx.set_source_rgba(*c2, 1)
            ctx.set_line_width(4)
            ctx.stroke()
            label = f"+{PLUS_BALLS}" if br["plus"] else str(hp)
            text(ctx, label, br["x"] + CW / 2, br["y"] + CH / 2 + 15, 42, rgb=(1, 1, 1), sw=6)

        # 破片
        alive = []
        for p in particles:
            p[4] += dt
            if p[4] >= p[5]:
                continue
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            ctx.new_path()
            ctx.rectangle(p[0] - 5, p[1] - 5, 10, 10)
            ctx.set_source_rgba(*p[6], 1 - p[4] / p[5])
            ctx.fill()
            alive.append(p)
        particles = alive

        # ボール(時間切れ後は灰色にして止める)
        for k, (bx, by) in enumerate(balls):
            tr = trails.setdefault(k, [])
            if not over:
                tr.append((bx, by))
                del tr[:-10]
            bcol = (0.5, 0.5, 0.55) if fail else hue_rgb((k * 0.17) % 1)
            for j, (tx, ty) in enumerate(tr):
                a = (j + 1) / len(tr)
                ctx.new_path()
                ctx.arc(tx, ty, BALL_R * (0.4 + 0.6 * a), 0, 2 * math.pi)
                ctx.set_source_rgba(*bcol, 0.3 * a * (0 if over else 1))
                ctx.fill()
            for rr, al in ((BALL_R * 2.3, 0.12), (BALL_R * 1.6, 0.25)):
                ctx.new_path()
                ctx.arc(bx, by, rr, 0, 2 * math.pi)
                ctx.set_source_rgba(*bcol, al)
                ctx.fill()
            ctx.new_path()
            ctx.arc(bx, by, BALL_R, 0, 2 * math.pi)
            ctx.set_source_rgb(*((0.75, 0.75, 0.78) if fail else (1, 1, 1)))
            ctx.fill()

        # 文字
        shown_t = min(t, end_t)
        remain = sum(1 for hp in hps if hp > 0)
        text(ctx, "30秒で", W / 2, 200, 84, sw=14)
        text(ctx, "全部こわせる？", W / 2, 310, 104, rgb=(1, 0.86, 0.2), sw=16)
        text(ctx, "Can it break every block in 30s?", W / 2, 372, 40, rgb=(0.85, 0.85, 0.9), sw=8)
        danger = shown_t >= 25 and not over
        pulse = 1 + (0.12 * max(0, 1 - (shown_t % 1) / 0.25) if danger else 0)
        tcol = (1, 0.25, 0.25) if (danger or fail) else ((0.3, 1, 0.5) if over else (1, 1, 1))
        text(ctx, f"{shown_t:05.2f}", W / 2, 480, 92 * pulse, rgb=tcol, sw=12)
        text(ctx, f"ボール ×{len(balls)}", AX0 + 10, 1500, 52, sw=10, align="left")
        if not over:
            text(ctx, f"残り {remain} ブロック", W / 2 + 150, 1500, 60, sw=12)
            if ghost is not None or (SCARE and clear_t is not None):
                text(ctx, "※失敗すると…アレが出ます", W / 2, 1590, 50, rgb=(1, 0.35, 0.35), sw=10)
        elif fail:
            k = min(1.0, after / 0.25)
            text(ctx, "時間切れ…", W / 2, 1180, 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            left_hp = sum(hp for hp in hps if hp > 0)
            text(ctx, f"残り{remain}ブロック、耐久あと{left_hp}", W / 2, 1310, 64, sw=12)
            text(ctx, f"あと{left_hp}回当たっていれば…", W / 2, 1590, 54, rgb=(0.9, 0.9, 0.95), sw=10)
        else:
            k = min(1.0, (t - end_t) / 0.25)
            text(ctx, "全部こわせた！", W / 2, 1180, 130 * (1.6 - 0.6 * k), rgb=(1, 0.86, 0.2), sw=20)
            text(ctx, f"{end_t:.2f}秒", W / 2, 1310, 90, sw=14)

        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)

    ff.stdin.close()
    ff.wait()
    duration = len(frames) / FPS
    synth_audio(events, end_t, clear_t is None, duration, wav)
    # 叫び声の大きさを残すため、音量の自動調整(loudnorm)はかけない
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
         "-c:v", "copy", "-c:a", "aac",
         "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", final],
        check=True)
    os.remove(silent)
    os.remove(wav)
    result = "時間切れ" if clear_t is None else f"クリア {clear_t:.2f}秒"
    print(f"完成: {os.path.abspath(final)}  ({result} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
# モーツァルト「トルコ行進曲」(1783年頃・パブリックドメイン)冒頭の旋律
MELODY = [71, 69, 68, 69, 72, 74, 72, 71, 72, 76, 77, 76, 75, 76, 83, 81, 80, 81,
          83, 81, 80, 81, 84, 81, 84, 83, 81, 79, 81, 83, 81, 79, 81, 83, 81, 79, 78, 76]


def synth_audio(events, end_t, fail, duration, path):
    rng = np.random.default_rng(0)
    out = np.zeros(int((duration + 3) * SR))

    def add(sig, t0):
        i = int(t0 * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    note_i = 0
    last_note_t = -1.0
    for kind, t, _, _, _ in events:
        if kind in ("hit", "break"):
            if t - last_note_t >= 0.06:  # 音が詰まりすぎないよう間引く
                m = MELODY[note_i % len(MELODY)]
                add(tone(midi_hz(m), 0.35, 0.40, 9), t)
                note_i += 1
                last_note_t = t
            else:
                add(tone(2400, 0.04, 0.05, 60), t)
        if kind == "break":
            add(noise(0.15, 0.25, 25, rng, smooth=4), t)
            add(tone(90, 0.25, 0.35, 14), t)
        elif kind == "plus":
            for k, m in enumerate((84, 88, 91)):
                add(tone(midi_hz(m), 0.25, 0.20, 10), t + k * 0.04)
    for s in range(25, 30):
        if s < end_t:
            add(noise(0.06, 0.5, 60, rng) + tone(1800, 0.06, 0.2, 40), s)
    scare = np.zeros_like(out)
    if fail:
        sad_t = end_t
        if SCARE:
            sig = scream(SR)
            scare[int(end_t * SR):int(end_t * SR) + len(sig)] += sig[: len(scare) - int(end_t * SR)]
            sad_t = end_t + SCARE_DUR + 0.1
        else:
            n = int(0.6 * SR)
            tt = np.arange(n) / SR
            add(0.35 * np.sign(np.sin(2 * np.pi * 110 * tt)) * np.exp(-tt * 2.5), end_t)
            sad_t = end_t + 0.55
        # 下がっていく「残念」の音
        for k, m in enumerate((64, 63, 62)):
            add(tone(midi_hz(m), 0.45, 0.35, 3) + tone(midi_hz(m - 12), 0.45, 0.25, 3), sad_t + k * 0.42)
        add(tone(midi_hz(61), 1.4, 0.35, 1.5) + tone(midi_hz(49), 1.4, 0.25, 1.5), sad_t + 1.26)
    else:
        for iv in (0, 4, 7, 12, 16):
            add(tone(midi_hz(69 + iv), 2.5, 0.25, 1.2), end_t)
        add(noise(1.5, 0.25, 2.5, rng, smooth=2), end_t)
    wet = out.copy()
    for d, g in ((0.043, 0.3), (0.071, 0.24), (0.113, 0.17)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    # 通常部分は軽く圧縮して聞こえやすくし、叫び声との差は約10dBに抑える(驚かせつつ耳に痛くない)
    wet = np.tanh(2.5 * wet / max(1e-9, np.max(np.abs(wet)))) / np.tanh(2.5) * 0.7
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
    ap.add_argument("-n", type=int, default=400)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
