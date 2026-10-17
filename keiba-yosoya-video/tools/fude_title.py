"""筆文字タイトル「競馬予想屋 谷上さん」のアニメーション(背景透明)を作るスクリプト。

使い方:
    python3 fude_title.py <フォントファイル> <出力フォルダ> [ink|white]

- フォント:Yuji Syuku(Google Fonts、SIL Open Font License)。
  https://raw.githubusercontent.com/google/fonts/main/ofl/yujisyuku/YujiSyuku-Regular.ttf
- 出力:1080x1920・30fps の PNG 連番(透明)。動画化は ffmpeg で行う(README 参照)。
- 文字は縦書き2列:右に「競馬予想屋」、左に大きく「谷上」+少し小さく「さん」。
- フォントをそのまま使わず、太らせる・縁をにじませる・かすれ(筆の毛の跡)を入れる・
  墨の濃淡をつけることで、筆で書いた質感に近づける。
- 1文字ずつ筆の運び(左上→右下)に近い向きで現れ、「谷」「上」は書き終わりに
  墨の飛沫が飛ぶ。最後は静止で終わる。
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
TOTAL = 4.2  # 秒

font_path, out_dir = sys.argv[1], sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "ink"
os.makedirs(out_dir, exist_ok=True)
random.seed(11)
rng = np.random.default_rng(11)


def blur(a, r):
    img = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
    return np.asarray(img.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def streaks(shape, angle_deg, scale):
    """一方向に伸びたノイズ(筆の毛のかすれ)"""
    h, w = shape
    big = max(h, w) * 2
    n = rng.random((big // 2, big // 6)).astype(np.float32)
    img = Image.fromarray((n * 255).astype(np.uint8)).resize((big, big), Image.BILINEAR)
    img = img.filter(ImageFilter.GaussianBlur(scale)).rotate(angle_deg, resample=Image.BILINEAR)
    a = np.asarray(img, np.float32) / 255.0
    y0, x0 = (big - h) // 2, (big - w) // 2
    a = a[y0:y0 + h, x0:x0 + w]
    return (a - a.mean()) / (a.std() + 1e-6)


def brush_glyph(ch, size):
    font = ImageFont.truetype(font_path, size)
    pad = size // 3
    img = Image.new("L", (size + pad * 2, size + pad * 2), 0)
    ImageDraw.Draw(img).text((pad, pad), ch, font=font, fill=255)
    # 1) 太らせる
    k = max(3, (size // (26 if size >= 300 else 45)) | 1)
    img = img.filter(ImageFilter.MaxFilter(k))
    a = np.asarray(img, np.float32) / 255.0
    # 2) 縁のにじみ・ギザギザ(低周波+高周波ノイズで輪郭を揺らす)
    soft = blur(a, size / 90)
    low = blur(rng.random(a.shape).astype(np.float32), size / 40)
    low = (low - low.mean()) / (low.std() + 1e-6)
    high = rng.random(a.shape).astype(np.float32) - 0.5
    shape = np.clip((soft - 0.5 + low * 0.08 + high * 0.10) * 14 + 0.5, 0, 1)
    # 3) かすれ:縁に近いところほど筆の毛の跡で白く抜ける
    inner = blur(shape, size / 25)
    edge = np.clip(1 - (inner - 0.45) / 0.4, 0, 1)  # 縁ほど1
    st = streaks(shape.shape, random.uniform(-70, -40), 0.6)
    dry = np.clip((st - 1.0) * 2.5, 0, 1) * edge ** 1.5
    alpha = np.clip(shape * (1 - dry * 1.4), 0, 1)
    # 4) 墨の濃淡(色の明るさ)
    dens = blur(rng.random(a.shape).astype(np.float32), size / 18)
    dens = (dens - dens.min()) / (dens.max() - dens.min() + 1e-6)
    tone = 8 + dens * 30 + edge * 20  # 0〜255 の明るさ(黒に近い)
    return alpha, tone, pad


def splash_layer(cx, cy, size, ang_lo, ang_hi, count):
    sp = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(sp)
    for _ in range(count):
        ang = math.radians(random.uniform(ang_lo, ang_hi))
        r = size * random.uniform(0.2, 1.0) ** 0.8
        px, py = cx + math.cos(ang) * r, cy + math.sin(ang) * r
        s = max(1.5, size * 0.04 * (1 - r / size) ** 1.3 * random.uniform(0.25, 1.3))
        if px > 770 and py < 1090:  # 右列(競馬予想屋)にかからないようにする
            continue
        e = random.uniform(1.0, 1.8)
        d.ellipse([px - s * e, py - s, px + s * e, py + s], fill=255)
    return np.asarray(sp.filter(ImageFilter.GaussianBlur(1.0)), np.float32) / 255.0


# 配置
items = []  # (文字, x, y, size, 開始秒, 書く時間)
t = 0.0
SMALL, BIG, SAN = 170, 450, 240
for i, ch in enumerate("競馬予想屋"):
    items.append((ch, 810, 130 + i * (SMALL + 14), SMALL, t, 0.26))
    t += 0.2
t += 0.15
yb = 120
for i, ch in enumerate("谷上"):
    items.append((ch, 250, yb + i * (BIG + 20), BIG, t, 0.5))
    t += 0.5
ys = yb + 2 * (BIG + 20) + 10
for i, ch in enumerate("さん"):
    items.append((ch, 355, ys + i * (SAN + 10), SAN, t, 0.3))
    t += 0.28

glyphs = []
for ch, x, y, size, st, dur in items:
    alpha, tone, pad = brush_glyph(ch, size)
    h, w = alpha.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    order = (yy / h) * 0.7 + (xx / w) * 0.3
    glyphs.append((alpha, tone, x - pad, y - pad, st, dur, order))

# 飛沫:「谷」の右払いの先、「上」の最後の横画の右端
splashes = [
    (splash_layer(250 + BIG * 1.0, yb + BIG + 20 + BIG * 0.92, BIG * 0.85, 0, 110, 170), items[6][4] + 0.42),
]


def ease(v):
    return 1 - (1 - v) ** 3


n = int(TOTAL * FPS)
for f in range(n):
    tt = f / FPS
    A = np.zeros((H, W), np.float32)
    T = np.full((H, W), 20, np.float32)
    for alpha, tone, x, y, st, dur, order in glyphs:
        if tt < st:
            continue
        p = ease(min(1.0, (tt - st) / dur))
        reveal = np.clip((p * 1.25 - order) / 0.1, 0, 1)
        a = alpha * reveal
        h, w = a.shape
        ys0, xs0 = max(0, -y), max(0, -x)
        ye, xe = min(h, H - y), min(w, W - x)
        reg = (slice(y + ys0, y + ye), slice(x + xs0, x + xe))
        sub, subt = a[ys0:ye, xs0:xe], tone[ys0:ye, xs0:xe]
        T[reg] = np.where(sub > A[reg], subt, T[reg])
        A[reg] = np.maximum(A[reg], sub)
    for sp, st in splashes:
        if tt >= st:
            A = np.maximum(A, sp * ease(min(1.0, (tt - st) / 0.12)))
    a8 = (A * 255).astype(np.uint8)
    if mode == "white":
        c = (255 - T * 0.6).astype(np.uint8)
        out = Image.fromarray(np.dstack([c, c, c, a8]), "RGBA")
    else:
        # 墨(黒)+ 暗い背景でも読めるよう、うっすら白いにじみを下に敷く
        halo = np.asarray(Image.fromarray(a8).filter(ImageFilter.GaussianBlur(16)), np.float32) * 0.5
        base = Image.fromarray(np.dstack([np.full((H, W), 250, np.uint8)] * 3 + [halo.astype(np.uint8)]), "RGBA")
        c = T.astype(np.uint8)
        ink = Image.fromarray(np.dstack([c, c, c, a8]), "RGBA")
        out = Image.alpha_composite(base, ink)
    out.save(os.path.join(out_dir, f"f_{f:04d}.png"))
print("frames", n)
