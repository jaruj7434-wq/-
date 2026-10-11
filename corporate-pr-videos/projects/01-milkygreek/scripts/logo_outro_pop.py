"""milkygreek ロゴのポップなアウトロ(効果音つき)をローカルで描画する(Higgs Field のクレジット不使用)。

真っ白な画面に肉球がぽこぽこ歩いてくる → 「milky」が1文字ずつぽよんと弾けて出る →
「greek」が上から落ちてきてバウンド → ロゴ全体がぷにっと弾んでキラキラが飛ぶ → ふわふわ揺れて終わる。
効果音は動きのタイミングに合わせて numpy で合成する。

使い方:
    python3 -I logo_outro_pop.py <ロゴ画像(白地)> <出力.mp4>
"""
import math
import os
import subprocess
import sys
import tempfile
import wave
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H, FPS, DUR = 1080, 1920, 30, 5.0
SR = 48000
LOGO_W = 760
BLUE = (42, 98, 152)
PAW = (150, 190, 228)
SPARKLE_COLORS = [(255, 170, 200), (255, 214, 102), (140, 200, 255), (178, 230, 190)]


# ---------- イージング ----------
def clamp01(t):
    return min(max(t, 0.0), 1.0)


def prog(t, start, dur):
    return clamp01((t - start) / dur)


def ease_out_back(t, s=2.2):
    t = clamp01(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_out_bounce(t):
    t = clamp01(t)
    n, d = 7.5625, 2.75
    if t < 1 / d:
        return n * t * t
    if t < 2 / d:
        t -= 1.5 / d
        return n * t * t + 0.75
    if t < 2.5 / d:
        t -= 2.25 / d
        return n * t * t + 0.9375
    t -= 2.625 / d
    return n * t * t + 0.984375


# ---------- ロゴを文字ごとに分解 ----------
def load_letters(path):
    img = Image.open(path).convert("L")
    img = img.resize((LOGO_W, round(img.height * LOGO_W / img.width)), Image.LANCZOS)
    lum = np.asarray(img).astype(np.float32)
    alpha = np.clip((240 - lum) / (240 - 115), 0, 1)
    h, w = alpha.shape

    mask = alpha > 0.35
    label = np.zeros((h, w), np.int32)
    comps = []
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not label[y, x]:
                n = len(comps) + 1
                q = deque([(y, x)])
                label[y, x] = n
                pts = []
                while q:
                    cy, cx = q.popleft()
                    pts.append((cy, cx))
                    for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not label[ny, nx]:
                            label[ny, nx] = n
                            q.append((ny, nx))
                ys = [p[0] for p in pts]
                xs = [p[1] for p in pts]
                comps.append({"id": n, "cy": sum(ys) / len(ys), "x0": min(xs), "x1": max(xs)})

    # 上段/下段に分け、x が重なる成分(i の点など)を1文字にまとめる
    letters = []
    for row in (0, 1):
        cs = sorted([c for c in comps if (c["cy"] >= h / 2) == bool(row)], key=lambda c: c["x0"])
        groups = []
        for c in cs:
            if groups and c["x0"] <= groups[-1]["x1"] - 4:
                groups[-1]["ids"].append(c["id"])
                groups[-1]["x1"] = max(groups[-1]["x1"], c["x1"])
            else:
                groups.append({"ids": [c["id"]], "x0": c["x0"], "x1": c["x1"]})
        for g in groups:
            sel = np.isin(label, g["ids"])
            # アンチエイリアスの縁も含める
            grown = Image.fromarray((sel * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
            grown = np.asarray(grown) > 0
            a = np.where(grown, alpha, 0)
            ys, xs = np.where(a > 0)
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            rgba = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
            rgba[..., 0], rgba[..., 1], rgba[..., 2] = BLUE
            rgba[..., 3] = (a[y0:y1, x0:x1] * 255).astype(np.uint8)
            letters.append({"img": Image.fromarray(rgba, "RGBA"), "x": x0, "y": y0, "row": row})
    return letters, (w, h)


# ---------- 図形 ----------
def paw_image(size, color, alpha):
    s = size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = color + (int(255 * alpha),)
    d.ellipse((s * 0.22, s * 0.42, s * 0.78, s * 0.92), fill=c)
    for cx, cy in ((0.18, 0.36), (0.38, 0.18), (0.62, 0.18), (0.82, 0.36)):
        r = s * 0.11
        d.ellipse((s * cx - r, s * cy - r, s * cx + r, s * cy + r), fill=c)
    return im


def star_points(cx, cy, r_out, r_in, rot):
    pts = []
    for k in range(10):
        r = r_out if k % 2 == 0 else r_in
        a = rot + math.pi / 5 * k - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ---------- 効果音 ----------
def tone_pop(f0, f1, dur, vol=0.6):
    t = np.arange(int(SR * dur)) / SR
    f = f0 * (f1 / f0) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(f) / SR
    env = np.exp(-t / (dur * 0.35)) * np.clip(t / 0.003, 0, 1)
    return vol * np.sin(phase) * env


def tone_boing(f, dur=0.32, vol=0.5):
    t = np.arange(int(SR * dur)) / SR
    freq = f * (1 + 0.35 * np.exp(-t * 9) * np.sin(2 * np.pi * 18 * t)) * (1 - 0.25 * t / dur)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    env = np.exp(-t * 7) * np.clip(t / 0.004, 0, 1)
    return vol * np.sin(phase) * env


def tone_sparkle(dur=0.9, vol=0.35):
    t = np.arange(int(SR * dur)) / SR
    out = np.zeros_like(t)
    for i, f in enumerate((2093, 2637, 3136, 4186, 5274)):
        st = i * 0.05
        tt = np.clip(t - st, 0, None)
        out += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 6) * (t >= st)
    return vol * out / 3


def mix_at(buf, snd, at):
    i = int(at * SR)
    j = min(len(buf), i + len(snd))
    buf[i:j] += snd[: j - i]


# ---------- タイムライン ----------
def build_timeline(letters):
    tl = {"paws": [], "letters": {}, "jelly": 2.75, "sparkle": 2.75}
    for k in range(4):
        tl["paws"].append(0.15 + k * 0.17)
    top = [i for i, l in enumerate(letters) if l["row"] == 0]
    bot = [i for i, l in enumerate(letters) if l["row"] == 1]
    for n, i in enumerate(top):
        tl["letters"][i] = ("pop", 0.95 + n * 0.11)
    for n, i in enumerate(bot):
        tl["letters"][i] = ("drop", 1.65 + n * 0.11)
    return tl


def build_audio(tl, letters):
    buf = np.zeros(int(SR * DUR))
    for k, at in enumerate(tl["paws"]):
        mix_at(buf, tone_pop(420 + 40 * (k % 2), 220, 0.07, 0.45), at)
    scale = [523, 587, 659, 784, 880, 1047]
    n_pop = n_drop = 0
    for i, (kind, at) in sorted(tl["letters"].items(), key=lambda kv: kv[1][1]):
        if kind == "pop":
            f = scale[n_pop % len(scale)]
            mix_at(buf, tone_pop(f * 1.6, f * 0.8, 0.11, 0.55), at + 0.02)
            n_pop += 1
        else:
            # 着地の瞬間に「ぽよん」
            mix_at(buf, tone_boing(330 + 40 * n_drop, 0.28, 0.4), at + 0.24)
            n_drop += 1
    mix_at(buf, tone_boing(220, 0.45, 0.45), tl["jelly"])
    mix_at(buf, tone_sparkle(), tl["sparkle"] + 0.05)
    buf = buf / max(1e-6, np.abs(buf).max()) * 0.85
    return (buf * 32767).astype(np.int16)


def render(logo_path, out_path):
    letters, (lw, lh) = load_letters(logo_path)
    ox, oy = (W - lw) // 2, (H - lh) // 2 - 40
    tl = build_timeline(letters)
    rng = np.random.default_rng(7)
    sparks = [
        {"ang": rng.uniform(0, 2 * math.pi), "dist": rng.uniform(260, 520), "size": rng.uniform(26, 50),
         "col": SPARKLE_COLORS[k % len(SPARKLE_COLORS)], "star": k % 2 == 0, "rot": rng.uniform(0, 6)}
        for k in range(24)
    ]
    paw_pos = [(W * 0.22, H * 0.82), (W * 0.40, H * 0.75), (W * 0.56, H * 0.83), (W * 0.74, H * 0.76)]

    tmp = tempfile.mkdtemp()
    wav_path = os.path.join(tmp, "sfx.wav")
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(build_audio(tl, letters).tobytes())

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", wav_path, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16",
         "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest", out_path],
        stdin=subprocess.PIPE)

    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        frame = Image.new("RGBA", (W, H), (255, 255, 255, 255))

        # 肉球:ぽこぽこ押される → 2.4s からふわっと消える
        fade = 1 - prog(t, 2.4, 0.5)
        for k, at in enumerate(tl["paws"]):
            p = prog(t, at, 0.18)
            if p <= 0 or fade <= 0:
                continue
            size = int(150 * ease_out_back(p, 3.0))
            if size < 4:
                continue
            im = paw_image(size, PAW, fade).rotate(-20 + 12 * (k % 2), expand=True, resample=Image.BICUBIC)
            x, y = paw_pos[k]
            frame.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))

        # ロゴ全体の「ぷにっ」とした弾み(2.75s)と、その後のふわふわ
        jp = prog(t, tl["jelly"], 0.6)
        squash = math.sin(jp * math.pi * 3) * math.exp(-jp * 4) * 0.12 if 0 < jp < 1 else 0
        bob = math.sin((t - 3.3) * 2 * math.pi * 0.8) * 10 * prog(t, 3.3, 0.4)
        logo_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        for i, l in enumerate(letters):
            kind, at = tl["letters"][i]
            img = l["img"]
            cx = ox + l["x"] + img.width / 2
            cy = oy + l["y"] + img.height / 2
            if kind == "pop":
                p = prog(t, at, 0.42)
                if p <= 0:
                    continue
                s = ease_out_back(p, 3.2)
                rot = (1 - p) * 25 * (1 if i % 2 else -1)
                dy = 0
            else:
                p = prog(t, at, 0.55)
                if p <= 0:
                    continue
                s = 1.0
                rot = 0
                dy = -(1 - ease_out_bounce(p)) * 420
                # 着地の瞬間に少しつぶれる
                land = prog(t, at + 0.24, 0.18)
                s_y = 1 - 0.18 * math.sin(land * math.pi) if 0 < land < 1 else 1
            sx = sy = s
            if kind == "drop":
                sx, sy = 1 + (1 - s_y) * 0.6, s_y
            sx *= 1 + squash
            sy *= 1 - squash
            nw, nh = max(1, int(img.width * sx)), max(1, int(img.height * sy))
            im = img.resize((nw, nh), Image.BICUBIC)
            if rot:
                im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
            px = int(cx - im.width / 2)
            # 下段のつぶれは足元基準
            py = int(cy - im.height / 2 + dy + (img.height - nh) / 2 * (kind == "drop"))
            logo_layer.alpha_composite(im, (px, int(py + bob)))

        # キラキラ
        sp = prog(t, tl["sparkle"], 0.9)
        if 0 < sp < 1:
            fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(fx)
            for s in sparks:
                r = s["dist"] * (1 - (1 - sp) ** 3)
                x = W / 2 + r * math.cos(s["ang"])
                y = oy + lh / 2 + r * math.sin(s["ang"]) * 1.1
                a = int(255 * (1 - sp))
                sz = s["size"] * (1 - 0.5 * sp)
                if s["star"]:
                    d.polygon(star_points(x, y, sz, sz * 0.45, s["rot"] + sp * 3), fill=s["col"] + (a,))
                else:
                    d.ellipse((x - sz / 2, y - sz / 2, x + sz / 2, y + sz / 2), fill=s["col"] + (a,))
            frame.alpha_composite(fx)

        # ロゴはキラキラの手前に重ねる
        frame.alpha_composite(logo_layer)

        ff.stdin.write(frame.convert("RGB").tobytes())

    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
