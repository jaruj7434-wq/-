"""「20発で10体のUFOを全部撃ち落とせる?」放物運動 + 空気抵抗 + 風のシューティング物理ショートを生成する。

画面下の砲台が、空を動き回るUFOを砲弾で撃つ。砲弾は重力で放物線を描き、空気抵抗と
数秒ごとに変わる風で流される。砲台は「UFOの動きは読むが、風と空気抵抗は読まない」狙い方なので、
外れることがある。弾切れの時点でUFOが残っていたら失敗(幽霊が出る)。

使い方:
    python shooter.py search [--want success|fail]
    python shooter.py render --seed N
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
SUBSTEPS = 4
SR = 48000

CANNON = (540.0, 1420.0)
GROUND_Y = 1460
SKY_TOP, SKY_BOTTOM = 560, 1180
GRAVITY = 900.0
SHELL_SPEED = 1350.0
DRAG = 0.5                  # 空気抵抗(風に対する相対速度に比例)
WIND_MAX = 520.0
WIND_EVERY = 4.0
N_UFO = 10
UFO_R = 34
SHELL_R = 9
AMMO = 20
FIRE_EVERY = 1.05
FIRST_SHOT = 1.0
AIM_JITTER_DEG = 2.0
OUTRO = 3.0
MAX_T = 45.0

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


# ---------------------------------------------------------------- シミュレーション
def make_ufos(rng):
    ufos = []
    for i in range(N_UFO):
        ufos.append({
            "x": rng.uniform(120, W - 120),
            "y0": rng.uniform(SKY_TOP + 40, SKY_BOTTOM - 40),
            "vx": rng.uniform(90, 230) * rng.choice([-1, 1]),
            "bob_a": rng.uniform(10, 40), "bob_f": rng.uniform(0.4, 1.0), "bob_p": rng.uniform(0, 6.28),
            "alive": True, "hue": i / N_UFO,
        })
    return ufos


def ufo_pos(u, t):
    return u["x"], u["y0"] + u["bob_a"] * math.sin(u["bob_f"] * 2 * math.pi * t + u["bob_p"])


def step_ufo(u, dt):
    u["x"] += u["vx"] * dt
    if u["x"] < 80:
        u["x"], u["vx"] = 80, abs(u["vx"])
    if u["x"] > W - 80:
        u["x"], u["vx"] = W - 80, -abs(u["vx"])


def predict_x(u, T):
    """壁での跳ね返りも含めて T 秒後の x を予測する。"""
    x, vx = u["x"], u["vx"]
    lo, hi = 80, W - 80
    x += vx * T
    span = hi - lo
    k = (x - lo) % (2 * span)
    return lo + (k if k <= span else 2 * span - k)


def aim(u, t, ufo_bob_t):
    """UFOの未来位置に向けた発射角(重力のみ考慮、空気抵抗と風は無視)。届かなければ None。"""
    cx, cy = CANNON
    T = 0.6
    ang = None
    for _ in range(6):
        tx = predict_x(u, T)
        _, ty = ufo_pos({**u, "x": tx}, ufo_bob_t + T)
        dx, h = tx - cx, cy - ty
        v2 = SHELL_SPEED ** 2
        if abs(dx) < 1:
            ang = math.pi / 2
            T = (SHELL_SPEED - math.sqrt(max(0, v2 - 2 * GRAVITY * h))) / GRAVITY
            continue
        disc = v2 * v2 - GRAVITY * (GRAVITY * dx * dx + 2 * h * v2)
        if disc < 0:
            return None, None
        th = math.atan((v2 - math.sqrt(disc)) / (GRAVITY * abs(dx)))   # 低い弾道
        ang = th if dx > 0 else math.pi - th
        T = abs(dx) / (SHELL_SPEED * math.cos(th))
    return ang, T


def simulate(seed, record=False):
    rng = np.random.default_rng(seed)
    ufos = make_ufos(rng)
    winds = [rng.uniform(-WIND_MAX, WIND_MAX) for _ in range(int(MAX_T / WIND_EVERY) + 2)]
    shells = []
    events = []
    frames = []
    ammo = AMMO
    next_fire = FIRST_SHOT
    cannon_ang = math.pi / 2
    target_ang = cannon_ang
    last_fire_t = -9.0
    t = 0.0
    dt = 1 / FPS / SUBSTEPS
    result, result_t = None, None
    while t < MAX_T:
        for _ in range(SUBSTEPS):
            t += dt
            wind = winds[int(t // WIND_EVERY)]
            for u in ufos:
                if u["alive"]:
                    step_ufo(u, dt)
            # 発射
            if result is None and ammo > 0 and t >= next_fire:
                alive = [u for u in ufos if u["alive"]]
                best = None
                for u in alive:
                    a, T = aim(u, t, t)
                    if a is not None and (best is None or T < best[2]):
                        best = (u, a, T)
                if best is not None:
                    a = best[1] + math.radians(rng.normal(0, AIM_JITTER_DEG))
                    target_ang = a
                    shells.append({"x": CANNON[0] + math.cos(a) * 70, "y": CANNON[1] - math.sin(a) * 70,
                                   "vx": SHELL_SPEED * math.cos(a), "vy": -SHELL_SPEED * math.sin(a),
                                   "trail": []})
                    ammo -= 1
                    last_fire_t = t
                    events.append(("fire", t, a))
                next_fire += FIRE_EVERY
            # 砲弾(重力 + 風に対する空気抵抗)
            for s in shells:
                s["vx"] += (-DRAG * (s["vx"] - wind)) * dt
                s["vy"] += (GRAVITY - DRAG * s["vy"]) * dt
                s["x"] += s["vx"] * dt
                s["y"] += s["vy"] * dt
                for u in ufos:
                    if not u["alive"]:
                        continue
                    ux, uy = ufo_pos(u, t)
                    if (s["x"] - ux) ** 2 + (s["y"] - uy) ** 2 < (UFO_R + SHELL_R) ** 2:
                        u["alive"] = False
                        s["dead"] = True
                        events.append(("hit", t, (ux, uy, u["hue"])))
                        break
                if s["y"] > GROUND_Y or s["x"] < -50 or s["x"] > W + 50:
                    s["dead"] = True
            shells = [s for s in shells if not s.get("dead")]
            if result is None:
                if all(not u["alive"] for u in ufos):
                    result, result_t = "success", t
                    events.append(("success", t, None))
                elif ammo == 0 and not shells:
                    result, result_t = "fail", t
                    events.append(("fail", t, None))
        # 砲台はなめらかに目標角度へ向く
        cannon_ang += (target_ang - cannon_ang) * 0.35
        if record:
            for s in shells:
                s["trail"].append((s["x"], s["y"]))
                del s["trail"][:-14]
            frames.append({
                "t": t, "wind": winds[int(t // WIND_EVERY)], "ammo": ammo, "ang": cannon_ang,
                "recoil": max(0.0, 1 - (t - last_fire_t) / 0.18),
                "ufos": [(ufo_pos(u, t), u["alive"], u["hue"]) for u in ufos],
                "shells": [(s["x"], s["y"], list(s["trail"])) for s in shells],
            })
        if result is not None:
            extra = OUTRO + (SCARE_DUR if result == "fail" else 0)
            if not record or t > result_t + extra:
                break
    left = sum(u["alive"] for u in ufos)
    return {"events": events, "frames": frames, "result": result, "result_t": result_t,
            "ammo_left": ammo, "ufo_left": left}


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["ammo_left"], r["ufo_left"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "success":
        for seed, _, rt, am, _ in sorted(succ, key=lambda r: (r[3], -r[2]))[:15]:
            print(f"seed={seed:4d}  成功 {rt:5.2f}秒  残り弾 {am}")
    else:
        fails = sorted([r for r in rs if r[1] == "fail"], key=lambda r: r[4])
        for seed, _, rt, _, ul in fails[:15]:
            print(f"seed={seed:4d}  失敗 {rt:5.2f}秒  残りUFO {ul}")


# ---------------------------------------------------------------- 描画
def background(rng):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, 0.02, 0.02, 0.07)
    g.add_color_stop_rgb(0.6, 0.08, 0.06, 0.20)
    g.add_color_stop_rgb(1, 0.02, 0.02, 0.05)
    ctx.set_source(g)
    ctx.paint()
    for _ in range(140):   # 星
        ctx.new_path()
        ctx.arc(rng.uniform(0, W), rng.uniform(420, GROUND_Y - 40), rng.uniform(0.8, 2.4), 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, rng.uniform(0.2, 0.7))
        ctx.fill()
    for wdt, al in ((24, 0.08), (12, 0.18), (5, 0.9)):   # 地面
        ctx.new_path()
        ctx.move_to(0, GROUND_Y)
        ctx.line_to(W, GROUND_Y)
        ctx.set_source_rgba(0.55, 0.62, 1.0, al)
        ctx.set_line_width(wdt)
        ctx.stroke()
    return surf


def draw_ufo(ctx, x, y, col):
    for grow, al in ((22, 0.10), (12, 0.22)):
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(UFO_R + grow, (UFO_R + grow) * 0.42)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(*col, al)
        ctx.fill()
    ctx.save()   # ドーム
    ctx.translate(x, y - UFO_R * 0.22)
    ctx.scale(UFO_R * 0.5, UFO_R * 0.45)
    ctx.arc(0, 0, 1, math.pi, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(0.75, 0.95, 1.0, 0.85)
    ctx.fill()
    ctx.save()   # 円盤
    ctx.translate(x, y)
    ctx.scale(UFO_R, UFO_R * 0.36)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(*col)
    ctx.fill()
    for k in (-2, -1, 0, 1, 2):   # 光る窓
        ctx.new_path()
        ctx.arc(x + k * UFO_R * 0.36, y + 2, 3.5, 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 0.85)
        ctx.fill()


def draw_cannon(ctx, ang, recoil):
    cx, cy = CANNON
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(-ang)
    back = 16 * recoil
    for grow, al in ((10, 0.12), (0, 1.0)):
        ctx.new_path()
        ctx.rectangle(-back - grow, -14 - grow, 78 + 2 * grow, 28 + 2 * grow)
        ctx.set_source_rgba(0.75, 0.8, 0.95, al)
        ctx.fill()
    if recoil > 0.5:   # 発射の光
        ctx.new_path()
        ctx.arc(78 - back + 16, 0, 26 * recoil, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.85, 0.4, 0.8 * recoil)
        ctx.fill()
    ctx.restore()
    ctx.new_path()
    ctx.arc(cx, cy + 6, 50, math.pi, 2 * math.pi)
    ctx.close_path()
    ctx.set_source_rgb(0.35, 0.4, 0.6)
    ctx.fill()


def draw_wind(ctx, wind, t, streaks):
    # 空を流れる風の筋
    for st in streaks:
        st[0] = (st[0] + wind * 1.4 / FPS) % (W + 200)
        x = st[0] - 100
        ctx.new_path()
        ctx.move_to(x, st[1])
        ctx.line_to(x - wind * 0.12, st[1])
        ctx.set_source_rgba(0.8, 0.9, 1.0, 0.10 + 0.25 * min(1, abs(wind) / WIND_MAX))
        ctx.set_line_width(2)
        ctx.stroke()
    # 風の向きと強さ
    y = 548
    text(ctx, "風", W / 2 - 150, y + 16, 44, sw=8)
    ln = 140 * wind / WIND_MAX
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.new_path()
    ctx.move_to(W / 2 + 30 - ln / 2, y)
    ctx.line_to(W / 2 + 30 + ln / 2, y)
    ctx.set_source_rgb(0.6, 0.9, 1.0)
    ctx.set_line_width(10)
    ctx.stroke()
    if abs(ln) > 8:
        d = 1 if ln > 0 else -1
        tip = W / 2 + 30 + ln / 2
        ctx.new_path()
        ctx.move_to(tip + d * 18, y)
        ctx.line_to(tip - d * 6, y - 18)
        ctx.line_to(tip - d * 6, y + 18)
        ctx.close_path()
        ctx.fill()


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"shooter_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"shooter_{seed}.wav")
    final = os.path.join(OUT_DIR, f"shooter_{seed}.mp4")
    rng = np.random.default_rng(seed + 999)
    bg = background(rng)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if fail else None
    particles, waves = [], []
    streaks = [[rng.uniform(0, W + 200), rng.uniform(600, GROUND_Y - 80)] for _ in range(40)]
    ev_i = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        dt = 1 / FPS
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "hit":
                ux, uy, hue = data
                col = hue_rgb(hue)
                for _ in range(60):
                    a = rng.uniform(0, 2 * math.pi)
                    sp = rng.uniform(100, 700)
                    particles.append([ux, uy, math.cos(a) * sp, math.sin(a) * sp, 0, rng.uniform(0.5, 1.1), col])
                waves.append([et, ux, uy, col])
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
        draw_wind(ctx, fr["wind"], t, streaks)
        for (ux, uy), alive, hue in fr["ufos"]:
            if alive:
                draw_ufo(ctx, ux, uy, hue_rgb(hue))
        for wv in waves:
            age = t - wv[0]
            if 0 <= age < 0.4:
                k = age / 0.4
                ctx.new_path()
                ctx.arc(wv[1], wv[2], 30 + 110 * k, 0, 2 * math.pi)
                ctx.set_source_rgba(*wv[3], 0.8 * (1 - k))
                ctx.set_line_width(10 * (1 - k) + 2)
                ctx.stroke()
        for sx, sy, trail in fr["shells"]:
            for j, (tx, ty) in enumerate(trail):
                a = (j + 1) / max(1, len(trail))
                ctx.new_path()
                ctx.arc(tx, ty, SHELL_R * (0.3 + 0.7 * a), 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.8, 0.3, 0.35 * a)
                ctx.fill()
            ctx.new_path()
            ctx.arc(sx, sy, SHELL_R * 1.9, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.8, 0.3, 0.3)
            ctx.fill()
            ctx.new_path()
            ctx.arc(sx, sy, SHELL_R, 0, 2 * math.pi)
            ctx.set_source_rgb(1, 1, 0.9)
            ctx.fill()
        draw_cannon(ctx, fr["ang"], fr["recoil"])
        alive_p = []
        for p in particles:
            p[4] += dt
            if p[4] >= p[5]:
                continue
            p[3] += GRAVITY * 0.5 * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            ctx.new_path()
            ctx.rectangle(p[0] - 5, p[1] - 5, 10, 10)
            ctx.set_source_rgba(*p[6], 1 - p[4] / p[5])
            ctx.fill()
            alive_p.append(p)
        particles = alive_p

        # 文字
        ufo_left = sum(1 for _, alive, _ in fr["ufos"] if alive)
        text(ctx, "20発で全部", W / 2, 200, 84, sw=14)
        text(ctx, "撃ち落とせる？", W / 2, 320, 112, rgb=(1, 0.86, 0.2), sw=18)
        text(ctx, "Can it shoot down all 10 UFOs with 20 shots?", W / 2, 385, 36, rgb=(0.85, 0.85, 0.9), sw=8)
        last = fr["ammo"] <= 1 and ufo_left > 0 and not over
        acol = (1, 0.3, 0.3) if (last or (fail and over)) else (1, 1, 1)
        text(ctx, f"残り弾 {fr['ammo']}", 60, 480, 64, rgb=acol, sw=12, align="left")
        text(ctx, f"UFO {ufo_left}/{N_UFO}", W - 340, 480, 64, sw=12, align="left")
        if last:
            pulse = 1 + 0.12 * max(0, 1 - (t % 0.6) / 0.2)
            msg = "ラスト1発！" if fr["ammo"] == 1 else "これが最後の弾…"
            text(ctx, msg, W / 2, 1290, 70 * pulse, rgb=(1, 0.3, 0.3), sw=14)
        if not over:
            text(ctx, "※失敗すると…アレが出ます", W / 2, 1560, 50, rgb=(1, 0.35, 0.35), sw=10)
        elif fail:
            k = min(1.0, after / 0.25)
            text(ctx, "弾切れ…", W / 2, 1000, 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"UFOが{ufo_left}体残った", W / 2, 1130, 70, sw=12)
        else:
            k = min(1.0, (t - end_t) / 0.25)
            text(ctx, "全部撃ち落とした！", W / 2, 1000, 110 * (1.6 - 0.6 * k), rgb=(1, 0.86, 0.2), sw=20)
            sub = "ラスト1発で決めた！！" if res["ammo_left"] == 0 else f"{res['ammo_left']}発残して成功"
            text(ctx, sub, W / 2, 1130, 70, sw=12)

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
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} 残り弾 {res['ammo_left']} / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
# ワーグナー「ワルキューレの騎行」(1870年・パブリックドメイン)の主題(分散和音の動き)
MELODY = [66, 71, 66, 71, 74, 71, 74, 78, 74, 78, 81, 78,
          69, 74, 69, 74, 78, 74, 73, 78, 73, 78, 81, 78]


def synth_audio(events, end_t, fail, duration, path):
    rng = np.random.default_rng(0)
    out = np.zeros(int((duration + 3) * SR))

    def add(sig, t0):
        i = int(t0 * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    note_i = 0
    for kind, t, _ in events:
        if kind == "fire":
            add(tone(70, 0.3, 0.6, 10) + noise(0.3, 0.3, 18, rng, smooth=8), t)   # ドン
            for k in range(2):   # 1発ごとに主題を2音ずつ進める
                m = MELODY[note_i % len(MELODY)]
                add(tone(midi_hz(m), 0.4, 0.35, 6), t + k * 0.16)
                note_i += 1
        elif kind == "hit":
            add(noise(0.6, 0.5, 7, rng, smooth=3), t)            # 爆発
            add(tone(55, 0.6, 0.5, 5), t)
            for k, iv in enumerate((0, 4, 7)):
                add(tone(midi_hz(83 + iv), 0.3, 0.15, 8), t + k * 0.03)
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
        for iv in (0, 4, 7, 12, 16):   # Bメジャーで解決
            add(tone(midi_hz(59 + iv), 2.5, 0.25, 1.2), end_t)
        add(noise(1.5, 0.25, 2.5, rng, smooth=2), end_t)
    wet = out.copy()
    for d, g in ((0.043, 0.3), (0.071, 0.24), (0.113, 0.17)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    # 通常部分は軽く圧縮して聞こえやすくし、叫び声との差は約10dBに抑える
    wet = np.tanh(2.5 * wet / max(1e-9, np.max(np.abs(wet)))) / np.tanh(2.5) * 0.85
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
    ap.add_argument("--want", choices=["success", "fail"], default="success")
    ap.add_argument("-n", type=int, default=300)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
