"""ユーザーが用意したロゴ画像(assets/source/gtr/logo/user_logo.jpg)を、最後の演出用に加工する。
- 4倍に拡大してくっきりさせる
- 白い背景をふちから塗りつぶすように透明にする(中の白いクローム部分は残す)
- 色を濃くし(彩度アップ)、クロームの明暗をはっきりさせてメタリックな質感にする
出力: assets/source/gtr/logo/logo.png(背景透明)
"""
import os
from collections import deque

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "source", "gtr", "logo")
im = Image.open(os.path.join(D, "user_logo.jpg")).convert("RGB")
im = im.resize((im.width * 4, im.height * 4), Image.LANCZOS)
im = im.filter(ImageFilter.UnsharpMask(radius=3, percent=120, threshold=2))
a = np.asarray(im).astype(np.float32) / 255
h, w, _ = a.shape
mx, mn = a.max(axis=2), a.min(axis=2)
bright = a.mean(axis=2)
sat = (mx - mn) / np.maximum(mx, 1e-6)
bg_like = (bright > 0.90) & (sat < 0.10)
# ふちからつながっている白だけを背景にする
mask = np.zeros((h, w), bool)
q = deque()
for x in range(w):
    for y in (0, h - 1):
        if bg_like[y, x]:
            mask[y, x] = True
            q.append((y, x))
for y in range(h):
    for x in (0, w - 1):
        if bg_like[y, x] and not mask[y, x]:
            mask[y, x] = True
            q.append((y, x))
while q:
    y, x = q.popleft()
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < h and 0 <= nx < w and not mask[ny, nx] and bg_like[ny, nx]:
            mask[ny, nx] = True
            q.append((ny, nx))
alpha = Image.fromarray(((~mask) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
# 彩度アップ(赤をより鮮やかに)
img = ImageEnhance.Color(im).enhance(1.6)
# メタリック:明暗のメリハリ(Sカーブ)+少しだけコントラスト
arr = np.asarray(img).astype(np.float32) / 255
arr = arr + 0.35 * (arr - 0.5) * (1 - np.abs(2 * arr - 1))   # Sカーブ
arr = np.clip(arr, 0, 1)
img = Image.fromarray((arr * 255).astype(np.uint8))
img = ImageEnhance.Contrast(img).enhance(1.12)
img.putalpha(alpha)
img.save(os.path.join(D, "logo.png"))
print("saved", img.size)
