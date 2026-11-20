#!/usr/bin/env python3
"""チャンネルアート合成: 生成画像(文字なし背景・メタリックロゴ)にチャンネル名を重ねる。

使い方: python3 -I scripts/compose_channel_art.py <assets_channel ディレクトリ>
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def key_black(img, lo=12, hi=40):
    """黒背景を透明化し、余白を切り詰める。"""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    m = a.max(axis=2)
    alpha = np.clip((m - lo) / (hi - lo), 0, 1) * 255
    rgba = np.dstack([a, alpha]).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")
    return out.crop(out.getbbox())


def text(draw, xy_center, s, size, fill, stroke, stroke_w):
    f = ImageFont.truetype(FONT, size)
    w = draw.textlength(s, font=f)
    x, y = xy_center
    draw.text((x - w / 2, y), s, font=f, fill=fill, stroke_width=stroke_w, stroke_fill=stroke)


def header(bg_path, logo, out_path):
    W, H = 2560, 1440
    bg = Image.open(bg_path).convert("RGB")
    s = max(W / bg.width, H / bg.height)
    bg = bg.resize((round(bg.width * s), round(bg.height * s)), Image.LANCZOS)
    bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
    bg = bg.filter(ImageFilter.UnsharpMask(2, 60, 2)).convert("RGBA")
    # セーフエリア(1546x423, y=508-931)の背面を少し暗く
    band = Image.new("RGBA", (W, 440), (0, 0, 0, 0))
    grad = np.zeros((440, W, 4), np.uint8)
    rows = np.concatenate([np.linspace(0, 120, 60), np.full(320, 120), np.linspace(120, 0, 60)])
    grad[..., 3] = rows[:, None].astype(np.uint8)
    band = Image.fromarray(grad, "RGBA")
    bg.alpha_composite(band, (0, 500))
    # メタリック GTA6
    lh = 160
    lg = logo.resize((round(logo.width * lh / logo.height), lh), Image.LANCZOS)
    bg.alpha_composite(lg, ((W - lg.width) // 2, 512))
    d = ImageDraw.Draw(bg)
    text(d, (W / 2, 655), "バイス切り抜き部", 140, "white", (224, 19, 122), 12)
    text(d, (W / 2, 852), "GTA6の神シーン&攻略小ネタを毎日お届け", 50, (255, 225, 77), "black", 6)
    bg.convert("RGB").save(out_path, optimize=True)


def icon(src, out_path, size=800):
    im = Image.open(src).convert("RGB")
    side = min(im.size)
    im = im.crop(((im.width - side) // 2, (im.height - side) // 2, (im.width + side) // 2, (im.height + side) // 2))
    im.resize((size, size), Image.LANCZOS).save(out_path, optimize=True)


def main(base):
    raw = os.path.join(base, "raw")
    logo = key_black(Image.open(os.path.join(raw, "logo_gta6_a.png")))
    for v in ("a", "b"):
        header(os.path.join(raw, f"header_{v}.png"), logo, os.path.join(base, f"header_{v}_logo.png"))
    icon(os.path.join(raw, "logo_ch_a.png"), os.path.join(base, "icon_c_logo.png"))
    icon(os.path.join(raw, "logo_ch_b.png"), os.path.join(base, "icon_d_badge.png"))
    logo.save(os.path.join(base, "logo_gta6_metal.png"))


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
