"""LifeRestart ロゴのポップなアウトロ(効果音つき)をローカルで描画する(Higgs Field のクレジット不使用)。

真っ白な画面をオレンジのペンキローラーが横切って帯を塗る → 子どものイラストがぽよんと飛び出す →
「Life Restart」が1文字ずつ弾けて出る(L と R は大きめにバウンド)→ カタカナがすっと上がる →
キャッチコピーが上から落ちてくる → ペンキのしぶきとキラキラが飛ぶ → ふわふわ揺れて終わる。

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

W, H, FPS, DUR = 1080, 1920, 30, 5.5
SR = 48000
UPSCALE = 3
ORANGE = (240, 140, 40)
SPLASH_COLORS = [(240, 140, 40), (230, 70, 50), (255, 205, 70), (120, 190, 240), (150, 210, 120)]


# ---------- イージング ----------
def clamp01(t):
    return min(max(t, 0.0), 1.0)


def prog(t, start, dur):
    return clamp01((t - start) / dur)


def ease_out_back(t, s=2.2):
    t = clamp01(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_out_cubic(t):
    return 1 - (1 - clamp01(t)) ** 3


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


# ---------- ロゴの分解 ----------
def to_rgba(img):
    """白地を透明にした RGBA を返す(色はそのまま)。"""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    dist = (255 * 3 - a.sum(2)) / 3
    alpha = np.clip(dist / 70, 0, 1)
    rgba = np.dstack([a, alpha * 255]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def components(mask):
    h, w = mask.shape
    label = np.zeros((h, w), np.int32)
    comps = []
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not label[y, x]:
                n = len(comps) + 1
                q = deque([(y, x)])
                label[y, x] = n
                xs = []
                while q:
                    cy, cx = q.popleft()
                    xs.append(cx)
                    for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not label[ny, nx]:
                            label[ny, nx] = n
                            q.append((ny, nx))
                comps.append({"id": n, "x0": min(xs), "x1": max(xs), "size": len(xs)})
    return label, comps


def bbox_piece(rgba, sel, ox=0, oy=0):
    arr = np.asarray(rgba).copy()
    arr[..., 3] = np.where(sel, arr[..., 3], 0)
    ys, xs = np.where(arr[..., 3] > 0)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return {"img": Image.fromarray(arr[y0:y1, x0:x1], "RGBA"), "x": ox + x0, "y": oy + y0}


def load_parts(path):
    src = Image.open(path).convert("RGB")
    src = src.resize((src.width * UPSCALE, src.height * UPSCALE), Image.LANCZOS)
    rgba = to_rgba(src)
    alpha = np.asarray(rgba)[..., 3] > 0
    h, w = alpha.shape
    cols = alpha.any(0)

    # イラスト:左端から最初の空白列まで
    gap = next(x for x in range(int(w * 0.15), w) if not cols[x])
    xs_text = gap + 1
    rows_text = alpha[:, xs_text:].any(1)
    ys = np.where(rows_text)[0]
    # 文字エリアを行ごとに分割(キャッチ/メインロゴ/カタカナ)
    bands, start = [], None
    for y in range(ys.min(), ys.max() + 2):
        on = y < h and rows_text[y]
        if on and start is None:
            start = y
        if not on and start is not None:
            bands.append((start, y))
            start = None
    bands = [b for b in bands if b[1] - b[0] > 6]
    tagline, main, kana = bands[0], max(bands, key=lambda b: b[1] - b[0]), bands[-1]

    parts = {"illust": bbox_piece(rgba, np.pad(np.ones((h, gap), bool), ((0, 0), (0, w - gap))))}
    for name, (y0, y1) in (("tagline", tagline), ("kana", kana)):
        sel = np.zeros((h, w), bool)
        sel[y0:y1, xs_text:] = True
        parts[name] = bbox_piece(rgba, sel)

    # メインロゴは1文字ずつ(i の点などは x の重なりでまとめる)
    y0, y1 = main
    region = np.zeros((h, w), bool)
    region[y0:y1, xs_text:] = alpha[y0:y1, xs_text:]
    strong = region & (np.asarray(rgba)[..., 3] > 120)
    label, comps = components(strong)
    comps = sorted([c for c in comps if c["size"] > 30], key=lambda c: c["x0"])
    groups = []
    for c in comps:
        if groups and c["x0"] <= groups[-1]["x1"] - 3:
            groups[-1]["ids"].append(c["id"])
            groups[-1]["x1"] = max(groups[-1]["x1"], c["x1"])
        else:
            groups.append({"ids": [c["id"]], "x0": c["x0"], "x1": c["x1"]})
    letters = []
    arr = np.asarray(rgba)
    for g in groups:
        sel = np.isin(label, g["ids"])
        sel = np.asarray(Image.fromarray((sel * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
        sel &= region
        piece = bbox_piece(rgba, sel)
        r, gch, b = arr[sel][:, :3].mean(0)
        piece["accent"] = r > 150 and r - b > 60  # オレンジの L / R
        letters.append(piece)
    return parts, letters, (w, h)


# ---------- 図形 ----------
def roller_image(scale=1.0):
    s = scale
    im = Image.new("RGBA", (int(260 * s), int(300 * s)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 260 * s, 80 * s), radius=36 * s, fill=ORANGE + (255,))
    d.rounded_rectangle((10 * s, 12 * s, 250 * s, 30 * s), radius=8 * s, fill=(255, 190, 120, 255))
    d.line((250 * s, 40 * s, 285 * s, 40 * s), fill=(110, 110, 110, 255), width=int(10 * s))
    d.line((255 * s, 40 * s, 255 * s, 150 * s), fill=(110, 110, 110, 255), width=int(10 * s))
    d.rounded_rectangle((235 * s, 150 * s, 275 * s, 290 * s), radius=14 * s, fill=(60, 60, 60, 255))
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
    env = np.exp(-t / (dur * 0.35)) * np.clip(t / 0.003, 0, 1)
    return vol * np.sin(2 * np.pi * np.cumsum(f) / SR) * env


def tone_boing(f, dur=0.32, vol=0.5):
    t = np.arange(int(SR * dur)) / SR
    freq = f * (1 + 0.35 * np.exp(-t * 9) * np.sin(2 * np.pi * 18 * t)) * (1 - 0.25 * t / dur)
    env = np.exp(-t * 7) * np.clip(t / 0.004, 0, 1)
    return vol * np.sin(2 * np.pi * np.cumsum(freq) / SR) * env


def tone_roll(dur=0.6, vol=0.35):
    rng = np.random.default_rng(1)
    n = int(SR * dur)
    noise = rng.standard_normal(n)
    # ローラーの「シャーッ」:ノイズを軽くローパスして、少しずつ消える
    k = 40
    smooth = np.convolve(noise, np.ones(k) / k, mode="same")
    t = np.arange(n) / SR
    env = np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.15, 0, 1)
    return vol * smooth / max(1e-6, np.abs(smooth).max()) * env


def tone_whoosh(dur=0.25, vol=0.3):
    t = np.arange(int(SR * dur)) / SR
    f = 300 * (2400 / 300) ** (t / dur)
    env = np.sin(np.pi * t / dur)
    return vol * np.sin(2 * np.pi * np.cumsum(f) / SR) * env * 0.6


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
T_ROLL = (0.1, 0.6)        # ローラーが横切る
T_ILLUST = 0.75
T_LETTER0, T_LETTER_STEP = 1.05, 0.08
T_KANA = 2.15
T_TAG = 2.35
T_SPLASH = 2.95


def build_audio(letters):
    buf = np.zeros(int(SR * DUR))
    mix_at(buf, tone_roll(), T_ROLL[0])
    mix_at(buf, tone_boing(300, 0.35, 0.5), T_ILLUST)
    scale = [523, 587, 659, 784, 880, 988, 1047, 1175, 1319, 1397, 1568]
    for k, l in enumerate(letters):
        at = T_LETTER0 + k * T_LETTER_STEP
        f = scale[k % len(scale)]
        if l["accent"]:
            mix_at(buf, tone_boing(f * 0.6, 0.3, 0.45), at)
        else:
            mix_at(buf, tone_pop(f * 1.6, f * 0.8, 0.1, 0.45), at + 0.01)
    mix_at(buf, tone_whoosh(), T_KANA)
    mix_at(buf, tone_boing(420, 0.3, 0.35), T_TAG + 0.3)
    mix_at(buf, tone_pop(900, 300, 0.12, 0.5), T_SPLASH)
    mix_at(buf, tone_sparkle(), T_SPLASH + 0.05)
    buf = buf / max(1e-6, np.abs(buf).max()) * 0.85
    return (buf * 32767).astype(np.int16)


def render(logo_path, out_path):
    parts, letters, (lw, lh) = load_parts(logo_path)
    scale = min(1.0, (W - 80) / lw)
    ox, oy = (W - lw * scale) / 2, (H - lh * scale) / 2 - 40

    def place(p):
        return ox + p["x"] * scale, oy + p["y"] * scale

    rng = np.random.default_rng(3)
    splashes = [
        {"ang": rng.uniform(0, 2 * math.pi), "dist": rng.uniform(300, 600), "size": rng.uniform(22, 56),
         "col": SPLASH_COLORS[k % len(SPLASH_COLORS)], "star": k % 3 == 0, "rot": rng.uniform(0, 6)}
        for k in range(28)
    ]
    band_y = oy + (lh * scale) / 2
    band_h = lh * scale * 1.25
    roller = roller_image(1.0)

    tmp = tempfile.mkdtemp()
    wav_path = os.path.join(tmp, "sfx.wav")
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(build_audio(letters).tobytes())

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", wav_path, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16",
         "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest", out_path],
        stdin=subprocess.PIPE)

    def paste_scaled(canvas, img, cx, cy, sx, sy=None, rot=0.0, alpha=1.0):
        sy = sx if sy is None else sy
        nw, nh = max(1, int(img.width * scale * sx)), max(1, int(img.height * scale * sy))
        im = img.resize((nw, nh), Image.LANCZOS)
        if rot:
            im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
        if alpha < 1:
            a = np.asarray(im).copy()
            a[..., 3] = (a[..., 3] * alpha).astype(np.uint8)
            im = Image.fromarray(a, "RGBA")
        canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        frame = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        bob = math.sin((t - 3.6) * 2 * math.pi * 0.7) * 8 * prog(t, 3.6, 0.4)

        # 1) ペンキローラーが横切って、うすいオレンジの帯を塗る(帯は後半ふわっと薄くなる)
        rp = ease_out_cubic(prog(t, T_ROLL[0], T_ROLL[1]))
        band_alpha = 0.22 * (1 - 0.6 * prog(t, 3.0, 0.8))
        band_w = int(W * rp)
        if band_w > 0:
            band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(band).rectangle((0, band_y - band_h / 2 + bob, band_w, band_y + band_h / 2 + bob),
                                           fill=ORANGE + (int(255 * band_alpha),))
            frame.alpha_composite(band)
        if 0 < rp < 1 or (t < T_ROLL[0] + T_ROLL[1] + 0.25):
            rx = -260 + (W + 260) * rp + 60 * prog(t, T_ROLL[0] + T_ROLL[1], 0.25)
            frame.alpha_composite(roller, (int(rx), int(band_y - band_h / 2 - 20)))

        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        # 2) イラストがぽよんと飛び出す
        p = prog(t, T_ILLUST, 0.5)
        if p > 0:
            ill = parts["illust"]
            x, y = place(ill)
            s = ease_out_back(p, 3.0)
            paste_scaled(layer, ill["img"], x + ill["img"].width * scale / 2, y + ill["img"].height * scale / 2 + bob,
                         s, rot=(1 - p) * -30)

        # 3) 1文字ずつポップ(L・R は上から落ちてバウンド)
        for k, l in enumerate(letters):
            at = T_LETTER0 + k * T_LETTER_STEP
            x, y = place(l)
            cx, cy = x + l["img"].width * scale / 2, y + l["img"].height * scale / 2
            if l["accent"]:
                p = prog(t, at - 0.15, 0.55)
                if p <= 0:
                    continue
                dy = -(1 - ease_out_bounce(p)) * 380
                land = prog(t, at + 0.12, 0.2)
                sy = 1 - 0.2 * math.sin(land * math.pi) if 0 < land < 1 else 1
                paste_scaled(layer, l["img"], cx, cy + dy + bob + (1 - sy) * l["img"].height * scale / 2,
                             1 + (1 - sy) * 0.7, sy)
            else:
                p = prog(t, at, 0.4)
                if p <= 0:
                    continue
                paste_scaled(layer, l["img"], cx, cy + bob, ease_out_back(p, 3.2), rot=(1 - p) * (20 if k % 2 else -20))

        # 4) カタカナがすっと上がる
        p = prog(t, T_KANA, 0.4)
        if p > 0:
            kp = parts["kana"]
            x, y = place(kp)
            paste_scaled(layer, kp["img"], x + kp["img"].width * scale / 2,
                         y + kp["img"].height * scale / 2 + (1 - ease_out_cubic(p)) * 60 + bob, 1.0, alpha=p)

        # 5) キャッチコピーが上から落ちてくる
        p = prog(t, T_TAG, 0.6)
        if p > 0:
            tg = parts["tagline"]
            x, y = place(tg)
            paste_scaled(layer, tg["img"], x + tg["img"].width * scale / 2,
                         y + tg["img"].height * scale / 2 - (1 - ease_out_bounce(p)) * 300 + bob, 1.0)

        # 6) ペンキのしぶき+キラキラ(ロゴの後ろ)
        sp = prog(t, T_SPLASH, 1.0)
        if 0 < sp < 1:
            fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(fx)
            for s in splashes:
                r = s["dist"] * (1 - (1 - sp) ** 3)
                x = W / 2 + r * math.cos(s["ang"])
                y = band_y + r * math.sin(s["ang"]) * 1.2
                a = int(255 * (1 - sp))
                sz = s["size"] * (1 - 0.5 * sp)
                if s["star"]:
                    d.polygon(star_points(x, y, sz, sz * 0.45, s["rot"] + sp * 3), fill=s["col"] + (a,))
                else:
                    d.ellipse((x - sz / 2, y - sz / 2, x + sz / 2, y + sz / 2), fill=s["col"] + (a,))
            frame.alpha_composite(fx)

        frame.alpha_composite(layer)
        ff.stdin.write(frame.convert("RGB").tobytes())

    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
