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




# --- コラージュ版(オリジナルイラストのパネル構成) ---------------------------
def fit_cover(im, W, H):
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def collage_header(bg_path, logo, out_path, cx):
    """cx: 中央の空きパネルの中心 x(2560幅基準)"""
    W, H = 2560, 1440
    bg = fit_cover(Image.open(bg_path).convert("RGB"), W, H).filter(ImageFilter.UnsharpMask(2, 60, 2)).convert("RGBA")
    lh = 170
    lg = logo.resize((round(logo.width * lh / logo.height), lh), Image.LANCZOS)
    bg.alpha_composite(lg, (round(cx - lg.width / 2), 520))
    d = ImageDraw.Draw(bg)
    text(d, (cx, 670), "バイス切り抜き部", 130, "white", (224, 19, 122), 11)
    text(d, (cx, 855), "GTA6の神シーン&攻略小ネタを毎日お届け", 46, (255, 225, 77), "black", 6)
    bg.convert("RGB").save(out_path, optimize=True)


def collage_icon(src, logo, out_path, logo_w, logo_cy, sub=None, sub_y=None, sub_size=70):
    S = 800
    im = fit_cover(Image.open(src).convert("RGB"), S, S).convert("RGBA")
    lg = logo.resize((logo_w, round(logo.height * logo_w / logo.width)), Image.LANCZOS)
    im.alpha_composite(lg, ((S - lg.width) // 2, round(logo_cy - lg.height / 2)))
    if sub:
        d = ImageDraw.Draw(im)
        text(d, (S / 2, sub_y), sub, sub_size, "white", (224, 19, 122), 8)
    im.convert("RGB").save(out_path, optimize=True)


def main_collage(base):
    raw = os.path.join(base, "raw")
    logo = key_black(Image.open(os.path.join(raw, "logo_gta6_a.png")))
    collage_header(os.path.join(raw, "collage_header_a.png"), logo, os.path.join(base, "header_c_collage.png"), 1250)
    collage_header(os.path.join(raw, "collage_header_b.png"), logo, os.path.join(base, "header_d_collage.png"), 1350)
    collage_icon(os.path.join(raw, "collage_icon_a.png"), logo, os.path.join(base, "icon_e_collage.png"),
                 300, 375, "切り抜き部", 412, 46)
    collage_icon(os.path.join(raw, "collage_icon_b.png"), logo, os.path.join(base, "icon_f_bike.png"),
                 520, 630)


if __name__ == "__main__":
    (main_collage if len(sys.argv) > 2 and sys.argv[2] == "collage" else main)(os.path.abspath(sys.argv[1]))
