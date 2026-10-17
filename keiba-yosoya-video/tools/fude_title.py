"""筆文字タイトル「競馬予想屋 谷上」のアニメーション(背景透明)を作るスクリプト。

使い方:
    python3 fude_title.py <フォントファイル> <出力フォルダ> [ink|white]

- フォント:Yuji Syuku(Google Fonts、SIL Open Font License)。
  https://raw.githubusercontent.com/google/fonts/main/ofl/yujisyuku/YujiSyuku-Regular.ttf
- 出力:1080x1920・30fps の PNG 連番(透明)。動画化は ffmpeg で行う(README 参照)。
- 文字は縦書き2列:右に小さめの「競馬予想屋」、左に大きい「谷上」。
- 1文字ずつ、筆の運びに近い向き(左上→右下)でにじみながら現れる。
  「谷上」が書き終わると墨の飛沫が散り、最後は静止で終わる。
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
TOTAL = 3.6  # 秒

font_path, out_dir = sys.argv[1], sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "ink"
os.makedirs(out_dir, exist_ok=True)
random.seed(7)

# 配置(右列:競馬予想屋、左列:谷上)
SMALL, BIG = 160, 380
chars = []  # (文字, x, y, size, 開始秒, 書く時間)
x_small, y0 = 800, 150
t = 0.0
for i, ch in enumerate("競馬予想屋"):
    chars.append((ch, x_small, y0 + i * (SMALL + 12), SMALL, t, 0.28))
    t += 0.22
t += 0.15
x_big = 340
for i, ch in enumerate("谷上"):
    chars.append((ch, x_big, 200 + i * (BIG + 40), BIG, t, 0.45))
    t += 0.42
SPLASH_T = t + 0.05


def glyph_mask(ch, size):
    font = ImageFont.truetype(font_path, size)
    pad = size // 4
    img = Image.new("L", (size + pad * 2, size + pad * 2), 0)
    ImageDraw.Draw(img).text((pad, pad), ch, font=font, fill=255)
    a = np.asarray(img, dtype=np.float32) / 255.0
    # 墨のにじみ:少しぼかして縁をざらつかせる
    noise = np.random.default_rng(len(ch) + size).random(a.shape).astype(np.float32)
    rough = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6)), dtype=np.float32) / 255.0
    a = np.clip((rough - 0.35 + (noise - 0.5) * 0.25) * 3.0, 0, 1) * np.maximum(a, rough)
    return a, pad


glyphs = []
for ch, x, y, size, st, dur in chars:
    a, pad = glyph_mask(ch, size)
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    order = (yy / h) * 0.75 + (xx / w) * 0.25  # 左上→右下
    glyphs.append((a, x - pad, y - pad, st, dur, order))

# 墨の飛沫:「上」の最後の横画の右端から、筆を払った勢いで右下〜下へ飛ぶ
sp = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(sp)
ex, ey = x_big + int(BIG * 0.95), 200 + BIG + 40 + int(BIG * 0.88)
for _ in range(55):
    ang = random.uniform(math.radians(-25), math.radians(110))
    r = random.uniform(10, BIG * 0.75) ** 1.0
    px, py = ex + math.cos(ang) * r, ey + math.sin(ang) * r
    s = max(1.5, 13 * (1 - r / (BIG * 0.8)) * random.uniform(0.4, 1.0))
    if px > 760:  # 右列(競馬予想屋)にかからないようにする
        continue
    d.ellipse([px - s, py - s, px + s * random.uniform(1, 1.8), py + s], fill=255)
splash = np.asarray(sp.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255.0
dist = None


def ease(v):
    return 1 - (1 - v) ** 3


n = int(TOTAL * FPS)
for f in range(n):
    tt = f / FPS
    alpha = np.zeros((H, W), np.float32)
    for a, x, y, st, dur, order in glyphs:
        if tt < st:
            continue
        p = min(1.0, (tt - st) / dur)
        p = ease(p)
        reveal = np.clip((p * 1.25 - order) / 0.12, 0, 1)  # 筆先のにじみ幅
        h, w = a.shape
        x0, y0_ = max(0, x), max(0, y)
        sub = (a * reveal)[y0_ - y:H - y if y + h > H else h, x0 - x:W - x if x + w > W else w]
        alpha[y0_:y0_ + sub.shape[0], x0:x0 + sub.shape[1]] = np.maximum(alpha[y0_:y0_ + sub.shape[0], x0:x0 + sub.shape[1]], sub)
    if tt >= SPLASH_T:
        k = ease(min(1.0, (tt - SPLASH_T) / 0.18))
        alpha = np.maximum(alpha, splash * k)
    a8 = (alpha * 255).astype(np.uint8)
    if mode == "white":
        rgba = np.dstack([np.full((H, W), 245, np.uint8)] * 3 + [a8])
        out = Image.fromarray(rgba, "RGBA")
    else:
        # 墨(黒)+ 暗い背景でも読めるよう、うっすら白いにじみを下に敷く
        halo = Image.fromarray(a8).filter(ImageFilter.GaussianBlur(14))
        halo_a = (np.asarray(halo, np.float32) * 0.55).astype(np.uint8)
        base = Image.fromarray(np.dstack([np.full((H, W), 250, np.uint8)] * 3 + [halo_a]), "RGBA")
        ink = Image.fromarray(np.dstack([np.full((H, W), 12, np.uint8)] * 3 + [a8]), "RGBA")
        out = Image.alpha_composite(base, ink)
    out.save(os.path.join(out_dir, f"f_{f:04d}.png"))
print("frames", n)
