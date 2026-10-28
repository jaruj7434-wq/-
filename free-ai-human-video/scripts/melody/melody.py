"""「この玉、最後まで弾ききれる?」バネの発射台で跳ねるたびにメロディが進む物理ショートを生成する。

- 玉はバネの発射台(鍵盤)に受け止められ、バネが縮んで次の発射台へ放物線で打ち出される。
  受け止めた瞬間に「きらきら星」が1音鳴る。飛ぶ時間は曲のリズム(4分音符・2分音符)に合わせる。
- 打ち出しには毎回少しだけ誤差がある(向き・強さ)。次の発射台に届かなければ落ちて失敗。
- カメラは玉を追って下へスクロールする。
- 展開:15音目からテンポアップ、22音目から発射台が左右に動き出す、最後の6音は発射台が小さくなる、
  最後の1音は金色の発射台。
最後の1音まで弾ききれば成功(天使)、落ちたら曲が止まって失敗(幽霊)。

使い方:
    python melody.py search [--want fail|success]
    python melody.py render --seed N
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
from ball_escape import hue_rgb, midi_hz, text  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from angels import DURATION as ANGEL_DUR, AngelShow, holy_music  # noqa: E402

W, H = 1080, 1920
FPS = 60
SR = 48000

# 「きらきら星」(フランス民謡・パブリックドメイン)。音の高さと長さ(拍)
SONG_TITLE = "きらきら星"
MELODY = [60, 60, 67, 67, 69, 69, 67, 65, 65, 64, 64, 62, 62, 60,
          67, 67, 65, 65, 64, 64, 62, 67, 67, 65, 65, 64, 64, 62,
          60, 60, 67, 67, 69, 69, 67, 65, 65, 64, 64, 62, 62, 60]
BEATS = [1, 1, 1, 1, 1, 1, 2] * 6
CHORD = [48, 48, 48, 48, 53, 53, 48, 53, 53, 48, 48, 55, 55, 48,
         48, 48, 53, 53, 48, 48, 55, 48, 48, 53, 53, 48, 48, 55,
         48, 48, 48, 48, 53, 53, 48, 53, 53, 48, 48, 55, 55, 48]
DOREMI = {60: "ド", 62: "レ", 64: "ミ", 65: "ファ", 67: "ソ", 69: "ラ", 71: "シ"}
N = len(MELODY)

BALL_R = 18
PAD_W, PAD_W_SMALL = 170, 110
PAD_DY = 230
Y0 = 300
X_MIN, X_MAX = 190, W - 190
TEMPO_AT, MOVE_AT, SMALL_FROM = 14, 21, N - 6     # 0始まりの発射台番号(この番号の発射台から変化)
BEAT_SLOW, BEAT_FAST = 0.42, 0.34                 # 1拍の秒数
HOLD = 0.06                                       # バネが縮んでいる時間
GRAVITY = 2600.0
MOVE_AMP, MOVE_W = 70.0, 2.6
AIM_SD = 0.062                                    # 打ち出しの誤差(速さに対する割合)。成功率がおよそ半々になる値
FALL_GRACE = 0.9
OUTRO = 3.0

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "output")


def pad_w(i):
    return PAD_W_SMALL if i >= SMALL_FROM else PAD_W


def beat(i):
    return BEAT_FAST if i >= TEMPO_AT else BEAT_SLOW


def course(seed):
    rng = np.random.default_rng(seed)
    xs = [W / 2]
    for _ in range(1, N):
        while True:
            x = rng.uniform(X_MIN, X_MAX)
            if 150 < abs(x - xs[-1]) < 430:
                break
        xs.append(x)
    ys = [Y0 + 420 + i * PAD_DY for i in range(N)]
    phases = [rng.uniform(0, 2 * math.pi) for _ in range(N)]
    return {"xs": xs, "ys": ys, "phases": phases}


def pad_x(c, i, t):
    x = c["xs"][i]
    if i >= MOVE_AT:
        x += MOVE_AMP * math.sin(MOVE_W * t + c["phases"][i])
    return x


# ---------------------------------------------------------------- シミュレーション
def simulate(seed, record=False):
    c = course(seed)
    rng = np.random.default_rng(seed + 12345)
    ys = c["ys"]
    events = []
    hops = []   # 各ジャンプ:(t0, x0, y0, vx, vy, T) 、T は着地までの時間(落ちた場合は大きい値)
    # 最初は真上から1つめの発射台へ落とす
    t = 0.3
    T0 = math.sqrt(2 * (ys[0] - BALL_R - Y0) / GRAVITY)
    hops.append((t, c["xs"][0], Y0, 0.0, 0.0, T0))
    t += T0
    result, result_t, notes = None, None, 0
    catch_t = []
    for i in range(N):
        # 発射台 i に受け止められる(ここで1音鳴る)
        catch_t.append(t)
        events.append(("note", t, i))
        notes = i + 1
        if i + 1 in (TEMPO_AT, MOVE_AT, SMALL_FROM):
            events.append(({TEMPO_AT: "tempo", MOVE_AT: "move", SMALL_FROM: "small"}[i + 1], t, None))
        if i == N - 1:
            result, result_t = "success", t
            events.append(("success", t, None))
            break
        # バネで次の発射台へ打ち出す(飛ぶ時間 = この音の長さ)
        x0, y0 = pad_x(c, i, t), ys[i] - BALL_R
        t_launch = t + HOLD
        T = BEATS[i] * beat(i) - HOLD
        tx, ty = pad_x(c, i + 1, t_launch + T), ys[i + 1] - BALL_R   # 着く時刻の位置をねらう
        vx = (tx - x0) / T
        vy = (ty - y0 - 0.5 * GRAVITY * T * T) / T
        sp = math.hypot(vx, vy)
        vx += rng.normal(0, AIM_SD) * sp      # 打ち出しの誤差
        vy += rng.normal(0, AIM_SD) * sp
        # 実際に発射台の高さへ戻ってくる時刻と位置
        a, b, cc = 0.5 * GRAVITY, vy, y0 - ty
        Tr = (-b + math.sqrt(b * b - 4 * a * cc)) / (2 * a)
        lx = x0 + vx * Tr
        land_t = t_launch + Tr
        if abs(lx - pad_x(c, i + 1, land_t)) <= pad_w(i + 1) / 2 + BALL_R * 0.4:
            hops.append((t_launch, x0, y0, vx, vy, Tr))
            t = land_t
        else:   # 届かない(または飛び越えた)→ 落ちる
            hops.append((t_launch, x0, y0, vx, vy, 99.0))
            events.append(("miss", land_t, i + 1))
            result, result_t = "fail", land_t + FALL_GRACE
            events.append(("fail", result_t, i + 1))
            break
    out = {"events": events, "result": result, "result_t": result_t, "notes": notes,
           "course": c, "hops": hops, "catch_t": catch_t}
    if record:
        out["frames"] = make_frames(out)
    return out


def ball_at(hops, t):
    for t0, x0, y0, vx, vy, T in reversed(hops):
        if t >= t0:
            dt = min(t - t0, T)
            return x0 + vx * dt, y0 + vy * dt + 0.5 * GRAVITY * dt * dt
    return hops[0][1], hops[0][2]


def make_frames(r):
    end = r["result_t"] + (OUTRO + SCARE_DUR if r["result"] == "fail" else ANGEL_DUR)
    frames = []
    cam = None
    for k in range(int(end * FPS) + 1):
        t = k / FPS
        bx, by = ball_at(r["hops"], t)
        falling = r["result"] == "fail" and t > r["result_t"] - FALL_GRACE
        target = cam if falling else by - 1000   # 落ちていく玉は追わない(画面の外へ消えていく)
        cam = target if cam is None else cam + (target - cam) * 0.12
        frames.append({"t": t, "ball": (bx, by), "cam": cam})
    return frames


def score(seed):
    r = simulate(seed)
    return seed, r["result"], r["result_t"], r["notes"]


def search(n, want):
    with Pool(os.cpu_count()) as p:
        rs = p.map(score, range(n))
    succ = [r for r in rs if r[1] == "success"]
    print(f"{n} シード中 成功 {len(succ)} 件 / 失敗 {n - len(succ)} 件")
    if want == "fail":
        for seed, _, rt, notes in sorted([r for r in rs if r[1] == "fail"], key=lambda r: -r[3])[:15]:
            print(f"seed={seed:4d}  {notes}/{N} 音まで弾いて落下  確定 {rt:5.2f}秒")
    else:
        for seed, _, rt, _ in sorted(succ, key=lambda r: r[2])[:15]:
            print(f"seed={seed:4d}  弾ききった {rt:5.2f}秒")


# ---------------------------------------------------------------- 描画
GOLD = (1, 0.86, 0.2)
NOTE_HUE = {60: 0.0, 62: 0.08, 64: 0.15, 65: 0.33, 67: 0.5, 69: 0.62, 71: 0.78}


def note_col(m, s=0.65):
    return hue_rgb(NOTE_HUE[m], s, 1.0)


def rounded(ctx, x, y, w, h, r):
    ctx.new_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def background(rng):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, 0.05, 0.03, 0.12)
    g.add_color_stop_rgb(1, 0.10, 0.05, 0.18)
    ctx.set_source(g)
    ctx.paint()
    return surf


def draw_pad(ctx, x, sy, i, squash, lit, t):
    """バネの発射台。sy は鍵盤の上面の画面上の高さ。"""
    m = MELODY[i]
    last = i == N - 1
    w = pad_w(i)
    col = GOLD if last else note_col(m, 0.75 if lit else 0.45)
    top = sy + squash
    base = sy + 95
    # バネ(ジグザグ)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.new_path()
    n = 6
    for k in range(n + 1):
        yy = top + 26 + (base - top - 26) * k / n
        ctx.line_to(x + (18 if k % 2 else -18), yy)
    ctx.set_source_rgba(0.75, 0.8, 0.95, 0.8)
    ctx.set_line_width(5)
    ctx.stroke()
    rounded(ctx, x - 34, base - 4, 68, 14, 6)   # 土台
    ctx.set_source_rgb(0.35, 0.4, 0.6)
    ctx.fill()
    # 鍵盤
    glow = 0.35 if lit else 0.15
    for grow, al in ((14, glow * 0.5), (6, glow)):
        rounded(ctx, x - w / 2 - grow, top - grow, w + 2 * grow, 28 + 2 * grow, 12 + grow)
        ctx.set_source_rgba(*col, al)
        ctx.fill()
    rounded(ctx, x - w / 2, top, w, 28, 12)
    ctx.set_source_rgb(*col)
    ctx.fill()
    label = DOREMI[m]
    text(ctx, label, x, top + 23, 26 if w < 150 else 28, rgb=(1, 1, 1), sw=5)
    if last:
        pulse = 1 + 0.08 * math.sin(t * 8)
        text(ctx, "ラスト1音", x, top - 24, 34 * pulse, rgb=GOLD, sw=7)


def render(seed):
    res = simulate(seed, record=True)
    events, frames, result, end_t = res["events"], res["frames"], res["result"], res["result_t"]
    c, catch_t = res["course"], res["catch_t"]
    fail = result == "fail"
    os.makedirs(OUT_DIR, exist_ok=True)
    silent = os.path.join(OUT_DIR, f"melody_{seed}_video.mp4")
    wav = os.path.join(OUT_DIR, f"melody_{seed}.wav")
    final = os.path.join(OUT_DIR, f"melody_{seed}.mp4")
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
    angels = AngelShow(W, H, seed) if result == "success" else None
    floaters = [[rng.uniform(0, W), rng.uniform(0, H), rng.uniform(20, 60), rng.choice(["♪", "♫"]),
                 rng.uniform(0, 1)] for _ in range(26)]
    popups, rings, banners = [], [], []
    trail = []
    ev_i = 0
    played = 0
    for fi, fr in enumerate(frames):
        t = fr["t"]
        cam = fr["cam"]
        while ev_i < len(events) and events[ev_i][1] <= t:
            kind, et, data = events[ev_i]
            if kind == "note":
                i = data
                played = i + 1
                x = pad_x(c, i, et)
                col = GOLD if i == N - 1 else note_col(MELODY[i], 0.8)
                popups.append([et, x, c["ys"][i], DOREMI[MELODY[i]], col])
                rings.append([et, x, c["ys"][i], col])
            elif kind == "tempo":
                banners.append([et, "テンポアップ！", (0.5, 0.95, 1.0)])
            elif kind == "move":
                banners.append([et, "鍵盤が動き出す！", (1, 0.6, 0.3)])
            elif kind == "small":
                banners.append([et, "鍵盤が小さくなる…！", (1, 0.4, 0.5)])
            ev_i += 1
        over = end_t is not None and t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        after = (t - end_t - (SCARE_DUR if fail else 0)) if over else 0

        ctx.set_source_surface(bg, 0, 0)
        ctx.paint()
        # ふわふわ漂う音符(カメラより少しゆっくり動いて奥行きを出す)
        for fl in floaters:
            sy = (fl[1] - cam * 0.3) % (H + 100) - 50
            text(ctx, fl[3], fl[0], sy, fl[2], rgb=hue_rgb(fl[4], 0.4, 1.0), sw=0, alpha=0.18)
        # 発射台
        for i in range(N):
            sy = c["ys"][i] - cam
            if sy < 380 or sy > H + 120:
                continue
            x = pad_x(c, i, t)
            squash = 0.0
            if catch_t[i:i + 1] and catch_t[i] <= t:
                age = t - catch_t[i]
                squash = 22 * max(0.0, 1 - age / 0.18) * (1 if age < HOLD else 0.6)
            lit = i < played
            draw_pad(ctx, x, sy, i, squash, lit, t)
        # 着地の輪
        for rg in rings:
            age = t - rg[0]
            if 0 <= age < 0.4:
                k = age / 0.4
                ctx.new_path()
                ctx.save()
                ctx.translate(rg[1], rg[2] - cam + 14)
                ctx.scale(1, 0.35)
                ctx.arc(0, 0, 60 + 120 * k, 0, 2 * math.pi)
                ctx.restore()
                ctx.set_source_rgba(*rg[3], 0.8 * (1 - k))
                ctx.set_line_width(6 * (1 - k) + 2)
                ctx.stroke()
        # 玉と軌跡
        bx, by = fr["ball"]
        trail.append((bx, by))
        del trail[:-14]
        for j, (tx, ty) in enumerate(trail):
            a = (j + 1) / len(trail)
            ctx.new_path()
            ctx.arc(tx, ty - cam, BALL_R * (0.3 + 0.7 * a), 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.85, 0.5, 0.3 * a)
            ctx.fill()
        ctx.new_path()
        ctx.arc(bx, by - cam, BALL_R * 1.9, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.85, 0.5, 0.3)
        ctx.fill()
        ctx.new_path()
        ctx.arc(bx, by - cam, BALL_R, 0, 2 * math.pi)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        # 鳴った音の名前がふわっと上がる
        for pu in popups:
            age = t - pu[0]
            if 0 <= age < 0.8:
                text(ctx, pu[3], pu[1], pu[2] - cam - 50 - 90 * age, 64, rgb=pu[4], sw=10,
                     alpha=min(1, 2.5 * (0.8 - age)))
        for bn in banners:
            age = t - bn[0]
            if 0 <= age < 1.3 and not over:
                k = min(1, age / 0.15)
                text(ctx, bn[1], W / 2, 1220, 96 * (1.4 - 0.4 * k), rgb=bn[2], sw=18,
                     alpha=min(1, 3 * (1.3 - age)))
        if angels is not None and over:
            angels.draw(ctx, t - end_t)

        # 上の帯(文字を読みやすくする)と文字
        g = cairo.LinearGradient(0, 0, 0, 560)
        g.add_color_stop_rgba(0, 0.03, 0.02, 0.08, 0.95)
        g.add_color_stop_rgba(0.8, 0.03, 0.02, 0.08, 0.85)
        g.add_color_stop_rgba(1, 0.03, 0.02, 0.08, 0.0)
        ctx.rectangle(0, 0, W, 560)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, "この玉、最後まで", W / 2, 195, 82, sw=14)
        text(ctx, "弾ききれる？", W / 2, 320, 120, rgb=GOLD, sw=18)
        text(ctx, "Can the ball play the whole song?", W / 2, 385, 38, rgb=(0.85, 0.85, 0.9), sw=8)
        text(ctx, f"♪ {SONG_TITLE}", 60, 470, 46, sw=10, align="left")
        pcol = (1, 0.3, 0.3) if (fail and over) else ((0.3, 1, 0.5) if over else (1, 1, 1))
        text(ctx, f"{played} / {N}", W - 170, 470, 52, rgb=pcol, sw=10)
        rounded(ctx, 60, 495, W - 120, 18, 9)   # 進み具合のバー
        ctx.set_source_rgba(1, 1, 1, 0.15)
        ctx.fill()
        if played:
            rounded(ctx, 60, 495, (W - 120) * played / N, 18, 9)
            ctx.set_source_rgb(*(GOLD if played == N else (0.5, 0.95, 1.0)))
            ctx.fill()
        if not over:
            text(ctx, "※失敗すると…アレが出ます", W / 2, 1840, 50, rgb=(1, 0.35, 0.35), sw=10)
        elif fail:
            k = min(1.0, after / 0.25)
            text(ctx, "落ちた…", W / 2, 1000, 150 * (1.6 - 0.6 * k), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{N - played}音だったのに…", W / 2, 1130, 72, sw=12)
        else:
            k = min(1.0, (t - end_t) / 0.25)
            text(ctx, "弾ききった！", W / 2, 1000, 140 * (1.6 - 0.6 * k), rgb=GOLD, sw=20)

        ff.stdin.write(surf.get_data())
        if fi % 300 == 0:
            print(f"  描画 {fi}/{len(frames)}", file=sys.stderr)
    ff.stdin.close()
    ff.wait()
    duration = len(frames) / FPS
    synth_audio(res, duration, wav)
    # 叫び声の大きさを残すため、音量の自動調整(loudnorm)はかけない
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(silent)
    os.remove(wav)
    print(f"完成: {os.path.abspath(final)}  ({'失敗' if fail else '成功'} {res['notes']}/{N}音 / 長さ {duration:.1f}秒)")


# ---------------------------------------------------------------- 音
MIX_GAIN = 0.32  # 通常部分の音量(約 -18dB になるよう調整)
HOLY_GAIN = 0.85


def music_box(freq, dur, amp):
    """オルゴールのような音。"""
    t = np.arange(int(dur * SR)) / SR
    y = (np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 6)
         + 0.25 * np.sin(2 * np.pi * freq * 3.01 * t) * np.exp(-t * 9))
    return amp * y * np.exp(-t * 2.2) * np.minimum(1, t / 0.004)


def bass(freq, dur, amp):
    t = np.arange(int(dur * SR)) / SR
    y = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    return amp * y * np.exp(-t * 2.5) * np.minimum(1, t / 0.01)


def synth_audio(res, duration, path):
    events, end_t, fail = res["events"], res["result_t"], res["result"] == "fail"
    out = np.zeros(int((duration + 3) * SR))

    def add(sig, t0):
        i = int(t0 * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    for kind, t, data in events:
        if kind == "note":
            i = data
            dur = BEATS[i] * beat(i) + 0.5
            add(music_box(midi_hz(MELODY[i] + 12), dur, 0.5), t)
            add(bass(midi_hz(CHORD[i]), dur, 0.35), t)
            add(music_box(midi_hz(CHORD[i] + 16), dur, 0.12), t)   # 和音の3度を薄く
        elif kind in ("tempo", "move", "small"):
            for k, m in enumerate((79, 83, 86, 91)):
                add(music_box(midi_hz(m), 0.5, 0.18), t + k * 0.05)
        elif kind == "miss":   # 落ちていく「ヒューッ」
            n = int(0.9 * SR)
            tt = np.arange(n) / SR
            f = 1400 * np.exp(-tt * 1.6)
            add(0.25 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, (0.9 - tt) / 0.2), t)
    extra = np.zeros_like(out)
    if fail:
        sig = scream(SR)
        i0 = int(end_t * SR)
        extra[i0:i0 + len(sig)] += sig[: len(extra) - i0]
        sad_t = end_t + SCARE_DUR + 0.1
        for k, m in enumerate((64, 63, 62)):
            add(music_box(midi_hz(m), 0.6, 0.4) + bass(midi_hz(m - 12), 0.6, 0.3), sad_t + k * 0.42)
        add(music_box(midi_hz(61), 1.5, 0.4) + bass(midi_hz(49), 1.5, 0.3), sad_t + 1.26)
    elif end_t is not None:
        sig = holy_music(SR, ANGEL_DUR)
        i0 = int(end_t * SR)
        extra[i0:i0 + len(sig)] += HOLY_GAIN * sig[: len(extra) - i0]
    wet = out.copy()
    for d, g in ((0.043, 0.3), (0.071, 0.24), (0.113, 0.17)):
        k = int(d * SR)
        wet[k:] += out[:-k] * g
    wet = wet[: int(duration * SR)]
    # 通常部分は軽く圧縮して聞こえやすくし、叫び声との差は約10dBに抑える
    wet = np.tanh(2.5 * wet / max(1e-9, np.max(np.abs(wet)))) / np.tanh(2.5) * MIX_GAIN
    wet = np.clip(wet + (0.95 if fail else 1.0) * extra[: len(wet)], -0.98, 0.98)
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
    ap.add_argument("-n", type=int, default=2000)
    a = ap.parse_args()
    if a.mode == "search":
        search(a.n, a.want)
    else:
        render(a.seed)
