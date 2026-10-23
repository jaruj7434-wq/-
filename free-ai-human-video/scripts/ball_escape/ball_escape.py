"""「30秒以内に10重リングを全部脱出できる?」物理シミュレーションショートを生成する。

使い方:
    python ball_escape.py search            # 盛り上がる結末になるシードを探す
    python ball_escape.py render --seed N   # 指定シードで動画を書き出す

必要なもの(すべて無料): Python3, numpy, pycairo, ffmpeg
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

# ---------------------------------------------------------------- 基本設定
W, H = 1080, 1920
FPS = 60
SUBSTEPS = 10
CX, CY = W / 2, 960
N_RINGS = 10
R_INNER = 130
R_STEP = 36
RING_WIDTH = 10
BALL_R = 16
GRAVITY = 1800.0
SPEED_MIN, SPEED_MAX = 850.0, 1500.0
TIME_LIMIT = 30.0
OUTRO = 2.8
SR = 48000

FONT = "IPAGothic"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


def hue_rgb(h, s=0.85, v=1.0):
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i]


# ---------------------------------------------------------------- シミュレーション
def make_rings(rng):
    rings = []
    for i in range(N_RINGS):
        rings.append({
            "r": R_INNER + i * R_STEP,
            "gap": math.radians(rng.uniform(30, 42)),
            "a0": rng.uniform(0, 2 * math.pi),
            "w": rng.uniform(0.7, 1.6) * (1 if i % 2 == 0 else -1),
            "color": hue_rgb(i / N_RINGS),
        })
    return rings


def angle_diff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def simulate(seed, record=False):
    """シミュレーションを実行し、イベント列と(record時は)フレームごとの状態を返す。"""
    rng = np.random.default_rng(seed)
    rings = make_rings(rng)
    ang = rng.uniform(0, 2 * math.pi)
    px, py = CX, CY
    vx, vy = 900 * math.cos(ang), 900 * math.sin(ang)
    cur = 0          # 今閉じ込められているリング
    passing = False  # すき間を通過中か
    events = []
    frames = []
    dt = 1 / FPS / SUBSTEPS
    t = 0.0
    escape_t = None
    total_frames = int((TIME_LIMIT + OUTRO) * FPS)

    for f in range(total_frames):
        for _ in range(SUBSTEPS):
            vy += GRAVITY * dt
            px += vx * dt
            py += vy * dt
            t += dt
            if cur >= N_RINGS:
                continue
            ring = rings[cur]
            dx, dy = px - CX, py - CY
            d = math.hypot(dx, dy)
            R = ring["r"] - RING_WIDTH / 2
            phi = math.atan2(dy, dx)
            gap_c = ring["a0"] + ring["w"] * t
            in_gap = abs(angle_diff(phi, gap_c)) < ring["gap"] / 2 - (BALL_R / R) * 0.6
            if passing:
                if d - BALL_R > ring["r"] + RING_WIDTH / 2:
                    events.append(("break", t, cur, px, py))
                    cur += 1
                    passing = False
                    if cur >= N_RINGS:
                        escape_t = t
                        events.append(("escape", t, cur - 1, px, py))
                elif d + BALL_R < R:
                    passing = False
                elif not in_gap and d < ring["r"]:
                    # すき間が回転して閉じた: 内側へ押し戻す
                    passing = False
                    nx, ny = dx / d, dy / d
                    dot = vx * nx + vy * ny
                    if dot > 0:
                        vx, vy = vx - 2 * dot * nx, vy - 2 * dot * ny
                    px, py = CX + nx * (R - BALL_R), CY + ny * (R - BALL_R)
                    events.append(("bounce", t, cur, px, py))
                continue
            if d + BALL_R >= R:
                if in_gap:
                    passing = True
                    continue
                nx, ny = dx / d, dy / d
                dot = vx * nx + vy * ny
                if dot > 0:
                    vx, vy = vx - 2 * dot * nx, vy - 2 * dot * ny
                    # 周期軌道にはまらないよう、ほんの少し向きを揺らす
                    jitter = math.radians(rng.uniform(-4, 4))
                    c, s = math.cos(jitter), math.sin(jitter)
                    vx, vy = vx * c - vy * s, vx * s + vy * c
                    sp = math.hypot(vx, vy)
                    sp2 = min(max(sp, SPEED_MIN), SPEED_MAX)
                    vx, vy = vx * sp2 / sp, vy * sp2 / sp
                    events.append(("bounce", t, cur, px, py))
                px, py = CX + nx * (R - BALL_R), CY + ny * (R - BALL_R)
        if record:
            frames.append((t, px, py, cur))
        if escape_t is None and t > TIME_LIMIT and not record:
            break
        if escape_t is not None and t > escape_t + OUTRO:
            break
    return {"seed": seed, "rings": rings, "events": events,
            "escape_t": escape_t, "frames": frames}


def score(seed):
    res = simulate(seed)
    et = res["escape_t"]
    if et is None:
        return seed, None, None
    breaks = [e[1] for e in res["events"] if e[0] == "break"]
    last_wait = breaks[-1] - breaks[-2]
    return seed, et, last_wait


def search(n=800):
    with Pool(os.cpu_count()) as p:
        results = p.map(score, range(n))
    good = [r for r in results if r[1] and 27.8 <= r[1] <= 29.7 and r[2] >= 4.0]
    good.sort(key=lambda r: -r[1])
    print(f"候補 {len(good)} 件 / {n} シード中")
    for seed, et, lw in good[:15]:
        print(f"seed={seed:4d}  脱出 {et:6.2f}秒  最後のリングで {lw:5.2f}秒 粘った")


# ---------------------------------------------------------------- 描画
def text(ctx, s, x, y, size, rgb=(1, 1, 1), stroke=(0, 0, 0), sw=10, align="center", alpha=1.0):
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    ext = ctx.text_extents(s)
    tx = x - ext.width / 2 - ext.x_bearing if align == "center" else x
    ctx.move_to(tx, y)
    ctx.text_path(s)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    if sw:
        ctx.set_source_rgba(*stroke, alpha)
        ctx.set_line_width(sw)
        ctx.stroke_preserve()
    ctx.set_source_rgba(*rgb, alpha)
    ctx.fill()


def background():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.RadialGradient(CX, CY, 50, CX, CY, 1300)
    g.add_color_stop_rgb(0, 0.09, 0.07, 0.20)
    g.add_color_stop_rgb(1, 0.01, 0.01, 0.03)
    ctx.set_source(g)
    ctx.paint()
    return surf


def render(seed):
    res = simulate(seed, record=True)
    rings, events, frames, et = res["rings"], res["events"], res["frames"], res["escape_t"]
    assert et is not None, "このシードは時間内に脱出しません"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"ball_escape_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"ball_escape_{seed}.wav")
    final = os.path.join(OUT_DIR, f"ball_escape_{seed}.mp4")

    bg = background()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)

    rng = np.random.default_rng(seed + 999)
    particles = []   # [x, y, vx, vy, life, max_life, rgb, kind]
    shockwaves = []  # [t0, r, rgb]
    last_hit = [-9.0] * N_RINGS
    trail = []
    ev_i = 0

    for fi, (t, px, py, cur) in enumerate(frames):
        dt = 1 / FPS
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et_, ri, ex, ey = events[ev_i]
            if kind == "bounce":
                last_hit[ri] = et_
            elif kind == "break":
                R = rings[ri]["r"]
                for _ in range(70):
                    a = rng.uniform(0, 2 * math.pi)
                    sp = rng.uniform(150, 650)
                    particles.append([CX + R * math.cos(a), CY + R * math.sin(a),
                                      math.cos(a) * sp, math.sin(a) * sp - 200,
                                      0, rng.uniform(0.7, 1.4), rings[ri]["color"], "shard"])
                shockwaves.append([et_, R, rings[ri]["color"]])
            elif kind == "escape":
                for _ in range(260):
                    a = rng.uniform(0, 2 * math.pi)
                    sp = rng.uniform(300, 1400)
                    particles.append([CX, CY - 150, math.cos(a) * sp, math.sin(a) * sp - 500,
                                      0, rng.uniform(1.5, 2.8), hue_rgb(rng.uniform()), "confetti"])
            ev_i += 1

        shake = 0.0
        for sw_ in shockwaves:
            age = t - sw_[0]
            if age < 0.15:
                shake = max(shake, 9 * (1 - age / 0.15))
        sx, sy = rng.uniform(-shake, shake), rng.uniform(-shake, shake)

        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        ctx.save()
        ctx.translate(sx, sy)

        # リング
        for i in range(cur, N_RINGS):
            ring = rings[i]
            gap_c = ring["a0"] + ring["w"] * t
            a1, a2 = gap_c + ring["gap"] / 2, gap_c - ring["gap"] / 2 + 2 * math.pi
            flash = max(0.0, 1 - (t - last_hit[i]) / 0.18)
            r_, g_, b_ = ring["color"]
            col = (r_ + (1 - r_) * flash * 0.8, g_ + (1 - g_) * flash * 0.8, b_ + (1 - b_) * flash * 0.8)
            dim = 1.0 if i == cur else 0.55
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            for wdt, al in ((34, 0.08), (22, 0.16), (RING_WIDTH, 1.0)):
                ctx.new_path()
                ctx.arc(CX, CY, ring["r"], a1, a2)
                ctx.set_source_rgba(*col, al * dim)
                ctx.set_line_width(wdt + flash * 6)
                ctx.stroke()

        # 衝撃波
        for sw_ in shockwaves:
            age = t - sw_[0]
            if 0 <= age < 0.45:
                k = age / 0.45
                ctx.new_path()
                ctx.arc(CX, CY, sw_[1] + 160 * k, 0, 2 * math.pi)
                ctx.set_source_rgba(*sw_[2], 0.7 * (1 - k))
                ctx.set_line_width(14 * (1 - k) + 2)
                ctx.stroke()

        # 軌跡とボール
        bcol = rings[min(cur, N_RINGS - 1)]["color"]
        trail.append((px, py))
        trail = trail[-16:]
        for k, (tx, ty) in enumerate(trail):
            a = (k + 1) / len(trail)
            ctx.new_path()
            ctx.arc(tx, ty, BALL_R * (0.4 + 0.6 * a), 0, 2 * math.pi)
            ctx.set_source_rgba(*bcol, 0.35 * a)
            ctx.fill()
        for rr, al in ((BALL_R * 2.4, 0.12), (BALL_R * 1.6, 0.25)):
            ctx.new_path()
            ctx.arc(px, py, rr, 0, 2 * math.pi)
            ctx.set_source_rgba(*bcol, al)
            ctx.fill()
        ctx.new_path()
        ctx.arc(px, py, BALL_R, 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()

        # 破片・紙吹雪
        alive = []
        for p in particles:
            p[4] += dt
            if p[4] >= p[5]:
                continue
            p[3] += GRAVITY * 0.6 * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            a = 1 - p[4] / p[5]
            ctx.new_path()
            if p[7] == "shard":
                ctx.move_to(p[0], p[1])
                ctx.line_to(p[0] - p[2] * 0.02, p[1] - p[3] * 0.02)
                ctx.set_line_width(5)
                ctx.set_source_rgba(*p[6], a)
                ctx.stroke()
            else:
                ctx.rectangle(p[0] - 7, p[1] - 4, 14, 8)
                ctx.set_source_rgba(*p[6], a)
                ctx.fill()
            alive.append(p)
        particles = alive
        ctx.restore()

        # 文字(HUD)
        escaped = t >= et
        shown_t = min(t, et)
        remain = N_RINGS - cur
        text(ctx, "30秒以内に", CX, 200, 84, sw=14)
        text(ctx, "全部脱出できる？", CX, 310, 104, rgb=(1, 0.86, 0.2), sw=16)
        text(ctx, "Can it escape all 10 rings in 30s?", CX, 372, 40, rgb=(0.85, 0.85, 0.9), sw=8)
        danger = shown_t >= 25 and not escaped
        pulse = 1 + (0.12 * max(0, 1 - (shown_t % 1) / 0.25) if danger else 0)
        tcol = (1, 0.25, 0.25) if danger else (1, 1, 1)
        if escaped:
            tcol = (0.3, 1, 0.5)
        text(ctx, f"{shown_t:05.2f}", CX, 470, 92 * pulse, rgb=tcol, sw=12)
        if not escaped:
            text(ctx, f"残り {remain} リング", CX, 1500, 70, sw=12)
        else:
            k = min(1.0, (t - et) / 0.25)
            scale = 1.6 - 0.6 * k
            text(ctx, "脱出成功！", CX, 1020, 150 * scale, rgb=(1, 0.86, 0.2), sw=20)
            text(ctx, f"{et:.2f}秒", CX, 1170, 96, sw=14)
            text(ctx, "あと少しで失敗だった…", CX, 1500, 56, rgb=(0.9, 0.9, 0.95), sw=10)

        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)

    ff.stdin.close()
    ff.wait()
    duration = len(frames) / FPS
    synth_audio(events, et, duration, wav)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "copy", "-c:a", "aac",
         "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", final],
        check=True)
    os.remove(silent)
    os.remove(wav)
    print(f"完成: {os.path.abspath(final)}  (脱出 {et:.2f}秒 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
# 「山の魔王の宮殿にて」(グリーグ, 1875年・パブリックドメイン)の主題
MELODY = [59, 61, 62, 64, 66, 62, 66, 65, 61, 65, 64, 60, 64,
          59, 61, 62, 64, 66, 62, 66, 71, 69, 66, 62, 66, 69]


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tone(freq, dur, amp=0.5, decay=5.0):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    y = np.zeros(n)
    for k, a in ((1, 1.0), (2, 0.45), (3, 0.22), (4, 0.1)):
        y += a * np.sin(2 * np.pi * freq * k * tt) * np.exp(-tt * decay * (1 + 0.6 * k))
    attack = np.minimum(1, tt / 0.004)
    return amp * y * attack


def noise(dur, amp, decay, rng, smooth=1):
    n = int(dur * SR)
    y = rng.standard_normal(n)
    if smooth > 1:
        y = np.convolve(y, np.ones(smooth) / smooth, mode="same")
    return amp * y * np.exp(-np.arange(n) / SR * decay)


def synth_audio(events, et, duration, path):
    rng = np.random.default_rng(0)
    out = np.zeros(int((duration + 2) * SR))

    def add(sig, t0):
        i = int(t0 * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    note_i = 0
    for kind, t, ri, _, _ in events:
        if kind == "bounce":
            loop, pos = divmod(note_i, len(MELODY))
            m = MELODY[pos] + min(loop, 5)  # 1周ごとに半音ずつ上げて緊張感を出す
            add(tone(midi_hz(m), 0.7, 0.45) + tone(midi_hz(m - 12), 0.7, 0.18, 7), t)
            note_i += 1
        elif kind == "break":
            base = MELODY[note_i % len(MELODY)] + 12
            for k, iv in enumerate((0, 4, 7, 12)):
                add(tone(midi_hz(base + iv), 0.5, 0.22, 6), t + k * 0.035)
            add(noise(0.4, 0.35, 9, rng, smooth=6), t)
            add(tone(55, 0.5, 0.6, 6), t)
        elif kind == "escape":
            for iv in (0, 4, 7, 12, 16, 19):   # Bメジャーの和音で解決
                add(tone(midi_hz(59 + iv), 2.5, 0.25, 1.2), t)
            add(noise(1.5, 0.25, 2.5, rng, smooth=2), t)
    # 残り5秒の秒読み
    for s in range(25, 30):
        if s < et:
            add(noise(0.06, 0.5, 60, rng) + tone(1800, 0.06, 0.2, 40), s)
    # 簡易リバーブ
    wet = out.copy()
    for d, g in ((0.043, 0.35), (0.071, 0.28), (0.113, 0.2), (0.167, 0.14)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    wet /= max(1e-9, np.max(np.abs(wet))) / 0.9
    pcm = (wet * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["search", "render"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("-n", type=int, default=800)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n)
    else:
        render(a.seed)
