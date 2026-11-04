"""race3d.py で描いた3Dのコマに、文字(タイトル・残り時間・ゴールした数)と音(BGM・効果音)を重ねて動画にする。

- 効果音は Higgs Field(Seedance 2.0 Mini)で作った音つき動画から切り出したもの(assets/source/race3d/sfx_src.wav):
  転がる音(0〜2.8秒)、木に当たる「コツン」(2.9〜5.7秒の6つ)、器に入る「カラカラ」(9.2〜11.7秒)、歓声(13.2秒〜)。
- BGM は Higgs Field(ElevenLabs Music v2)で作ったレースの曲(assets/source/race3d/bgm.mp3)。
- 当たる音は、計算した玉の動き(速さが急に変わった所)から、その瞬間に鳴らす。大きい玉ほど低く大きい音。
- 成功は天使(scripts/common/angels.py)、失敗は幽霊(scripts/common/jumpscare.py)。

    python composite.py --seed 41 [--preview]
"""

import argparse
import json
import math
import os
import subprocess
import sys
import wave

import cairo
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ball_escape"))
from ball_escape import midi_hz, text  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from jumpscare import DURATION as SCARE_DUR, GhostScare, scream  # noqa: E402
from angels import AngelShow, holy_music  # noqa: E402

OUT = os.path.join(HERE, "..", "..", "assets", "output", "race3d")
SRC = os.path.join(HERE, "..", "..", "assets", "source", "race3d")
W, H = 1080, 1920
FPS = 30
SR = 48000
NAMES = ["ハムスター", "ウサギ", "ペンギン", "柴犬", "ブタ", "ゴリラ"]
RADII = [0.04, 0.08, 0.11, 0.13, 0.17, 0.275]
GOLD = (1, 0.86, 0.2)


def load_wav(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
        if w.getnchannels() == 2:
            x = x.reshape(-1, 2).mean(axis=1)
        return x, w.getframerate()


def load_audio(path):
    tmp = os.path.join(OUT, "_tmp.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), tmp], check=True)
    x, _ = load_wav(tmp)
    os.remove(tmp)
    return x


def seg(x, a, b):
    s = x[int(a * SR):int(b * SR)].copy()
    n = min(len(s), int(0.01 * SR))
    s[:n] *= np.linspace(0, 1, n)
    s[-n:] *= np.linspace(1, 0, n)
    return s


def pitch(sig, ratio):
    """再生速度を変えて音の高さを変える(大きい玉ほど低く)。"""
    idx = np.arange(0, len(sig) - 1, ratio)
    return np.interp(idx, np.arange(len(sig)), sig)


def detect_hits(track):
    """玉ごとに速さが急に変わった瞬間(=何かに当たった)を探す。"""
    tr = np.array(track)                       # [フレーム, 玉, xyz]
    v = np.diff(tr, axis=0) * FPS
    dv = np.linalg.norm(np.diff(v, axis=0), axis=2)   # [フレーム, 玉]
    hits = []
    for k in range(tr.shape[1]):
        last = -99
        for f in range(dv.shape[0]):
            if dv[f, k] > 1.6 and f - last > 3:
                hits.append((f + 1, k, float(dv[f, k])))
                last = f
    speed = np.linalg.norm(v, axis=2)          # [フレーム, 玉]
    return hits, speed


def make_audio(pl, duration, path):
    sfx = load_audio(os.path.join(SRC, "sfx_src.mp4"))
    bgm = load_audio(os.path.join(SRC, "bgm.mp3"))
    roll = seg(sfx, 0.1, 2.8)
    clacks = [seg(sfx, t - 0.01, t + 0.22) for t in (2.88, 3.22, 4.04, 4.44, 5.22, 5.72)]
    rattle = seg(sfx, 9.15, 11.8)
    cheer = seg(sfx, 13.2, 15.0)
    n = int((duration + 3) * SR)
    fx = np.zeros(n)

    def add(buf, sig, t, g=1.0):
        i = int(t * SR)
        j = min(n, i + len(sig))
        if 0 <= i < n:
            buf[i:j] += g * sig[: j - i]

    end_t = pl["end_t"]
    hits, speed = detect_hits(pl["track"])
    rng = np.random.default_rng(pl["seed"])
    for f, k, dv in hits:
        t = f / FPS
        if t > end_t + 2:
            continue
        r = RADII[k]
        g = min(1.0, dv / 6) * (0.35 + 1.6 * r)
        add(fx, pitch(clacks[rng.integers(len(clacks))], 1.35 - 1.6 * r), t, g)   # 大きい玉ほど低い
    # 転がる音:動いている玉の速さの合計に合わせて音量を変える
    loop = np.tile(roll, int(n / len(roll)) + 2)[:n]
    env = np.zeros(n)
    tot = (speed * np.array(RADII)[None, :] * 4).sum(axis=1)
    for f, s_ in enumerate(tot):
        env[int(f * SR / FPS):int((f + 1) * SR / FPS)] = min(1.0, s_ / 2.5)
    env = np.convolve(env, np.ones(2400) / 2400, mode="same")
    fx += loop * env * 1.4
    for k, ft in enumerate(pl["finish"]):   # ゴールの受け皿に入った「カラカラ」
        if ft is not None and ft <= end_t + 0.05:
            add(fx, rattle[: int(0.9 * SR)], ft, 0.6 + RADII[k])
    # BGM:結果が出たら止める
    music = np.zeros(n)
    add(music, bgm, 0.0, 1.0)
    i_end = int(end_t * SR)
    fade = int(0.4 * SR)
    music[i_end:i_end + fade] *= np.linspace(1, 0, min(fade, n - i_end))
    music[i_end + fade:] = 0
    mix = 0.55 * music / (np.percentile(np.abs(music[music != 0]), 99.5) + 1e-9) \
        + 0.9 * fx / (np.percentile(np.abs(fx[fx != 0]), 99.7) + 1e-9)
    body = mix[: i_end]
    rms = np.sqrt(np.mean(body ** 2))
    mix *= 10 ** (-18.0 / 20) / rms            # 通常部分は約 -18dB
    extra = np.zeros(n)
    if pl["success"]:
        add(extra, cheer, end_t + 0.05, 0.35)
        h = holy_music(SR, 6.0)
        add(extra, h, end_t + 1.0, 0.85)
    else:
        add(extra, scream(SR), end_t, 0.95)
        sad = end_t + SCARE_DUR + 0.1
        for j, m in enumerate((64, 63, 62, 61)):
            d = 0.42 if j < 3 else 1.4
            tt = np.arange(int(d * SR)) / SR
            add(extra, (np.sin(2 * np.pi * midi_hz(m) * tt) + 0.5 * np.sin(2 * np.pi * midi_hz(m - 12) * tt))
                * np.exp(-tt * 2.5) * 0.25, sad + j * 0.42)
    out = np.clip(mix + extra, -0.98, 0.98)[: int(duration * SR)]
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


def compose(seed, preview):
    with open(os.path.join(OUT, f"plan_{seed}.json")) as fp:
        pl = json.load(fp)
    fdir = os.path.join(OUT, f"frames_{seed}{'_preview' if preview else ''}")
    step = 3 if preview else 1
    n_frames = pl["n_frames"]
    end_t, ok, finish, limit = pl["end_t"], pl["success"], pl["finish"], pl["time_limit"]
    name = f"race3d_{seed}{'_preview' if preview else ''}"
    silent = os.path.join(OUT, name + "_v.mp4")
    wav = os.path.join(OUT, name + ".wav")
    final = os.path.join(OUT, name + ".mp4")
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "18", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    ghost = GhostScare(W, H, seed) if not ok else None
    angels = AngelShow(W, H, seed) if ok else None
    order = sorted([k for k in range(6) if finish[k] is not None and finish[k] <= end_t + 0.01], key=lambda k: finish[k])
    img = None
    for f in range(1, n_frames + 1):
        t = (f - 1) / FPS
        src = 1 + ((f - 1) // step) * step
        p = os.path.join(fdir, f"{src:05d}.png")
        if os.path.exists(p):
            img = cairo.ImageSurface.create_from_png(p)
        over = t >= end_t
        if ghost is not None and over and t - end_t < SCARE_DUR:
            ghost.draw(surf, t - end_t)
            ff.stdin.write(surf.get_data())
            continue
        ctx.save()
        ctx.scale(W / img.get_width(), H / img.get_height())
        ctx.set_source_surface(img, 0, 0)
        ctx.get_source().set_filter(cairo.FILTER_BILINEAR)
        ctx.paint()
        ctx.restore()
        # 上の帯とタイトル
        g = cairo.LinearGradient(0, 0, 0, 420)
        g.add_color_stop_rgba(0, 0.04, 0.05, 0.10, 0.75)
        g.add_color_stop_rgba(1, 0.04, 0.05, 0.10, 0.0)
        ctx.rectangle(0, 0, W, 420)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, f"{int(limit)}秒以内に", W / 2, 130, 70, sw=14)
        text(ctx, "6匹全員ゴールできる？", W / 2, 245, 88, rgb=GOLD, sw=18)
        left = max(0.0, limit - min(t, end_t))
        text(ctx, f"のこり {left:4.1f}秒", W / 2, 350, 62, rgb=(1, 0.45, 0.4) if left < 8 else (1, 1, 1), sw=12)
        # 下:ゴールした動物
        done = [k for k in order if finish[k] <= t]
        g = cairo.LinearGradient(0, H - 330, 0, H)
        g.add_color_stop_rgba(0, 0.04, 0.05, 0.10, 0.0)
        g.add_color_stop_rgba(1, 0.04, 0.05, 0.10, 0.75)
        ctx.rectangle(0, H - 330, W, 330)
        ctx.set_source(g)
        ctx.fill()
        text(ctx, f"ゴール {len(done)} / 6", W / 2, H - 200, 74, rgb=GOLD if len(done) == 6 else (1, 1, 1), sw=14)
        for i, k in enumerate(range(6)):
            x = W / 2 + (i - 2.5) * 170
            fin = k in done
            text(ctx, NAMES[k], x, H - 95, 36 if len(NAMES[k]) <= 3 else 30,
                 rgb=(0.5, 1, 0.55) if fin else (0.75, 0.75, 0.8), sw=7)
            if fin:
                text(ctx, "✔", x, H - 140, 40, rgb=(0.5, 1, 0.55), sw=6)
        for k in done:   # ゴールした瞬間の「〇〇 ゴール!」
            age = t - finish[k]
            if age < 1.0:
                text(ctx, f"{NAMES[k]} ゴール!", W / 2, 520, 80 * (1.15 - 0.15 * min(1, age / 0.15)),
                     rgb=(0.5, 1, 0.55), sw=14)
        if over and ok:
            age = t - end_t
            if age < 0.3:
                ctx.rectangle(0, 0, W, H)
                ctx.set_source_rgba(1, 1, 1, 0.8 * (1 - age / 0.3))
                ctx.fill()
            angels.draw(ctx, age)
            text(ctx, "全員ゴール!", W / 2, 640, 120, rgb=GOLD, sw=20)
        elif over:
            after = t - end_t - SCARE_DUR
            k_ = min(1.0, after / 0.25)
            n_left = 6 - len(done)
            text(ctx, "時間切れ…", W / 2, 880, 110 * (1.12 - 0.12 * k_), rgb=(1, 0.3, 0.3), sw=20)
            text(ctx, f"あと{n_left}匹だったのに…", W / 2, 1010, 66, sw=12)
        ff.stdin.write(surf.get_data())
    ff.stdin.close()
    ff.wait()
    duration = n_frames / FPS
    make_audio(pl, duration, wav)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(silent)
    os.remove(wav)
    print("完成:", os.path.abspath(final), f"({'成功' if ok else '失敗'} / 長さ {duration:.1f}秒)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    compose(a.seed, a.preview)
