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


FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
TITLE_FONT = os.path.join(FONT_DIR, "DelaGothicOne-Regular.ttf")
SUB_FONT = os.path.join(FONT_DIR, "RocknRollOne-Regular.ttf")


def styled_text(s, size, font=TITLE_FONT, top=(255, 255, 255), bottom=(120, 235, 255),
                stroke=(224, 19, 122), stroke_w=None, glow=(255, 60, 170), shear=0.18):
    """グラデーション塗り+縁取り+ネオン光彩+斜体の文字を RGBA で返す(余白は切り詰め済み)。"""
    f = ImageFont.truetype(font, size)
    sw = stroke_w if stroke_w is not None else max(2, size // 12)
    pad = sw * 4 + size // 3
    l, t, r, b = f.getbbox(s, stroke_width=sw)
    W, H = r - l + pad * 2, b - t + pad * 2
    org = (pad - l, pad - t)
    fill_m = Image.new("L", (W, H)); ImageDraw.Draw(fill_m).text(org, s, font=f, fill=255)
    out_m = Image.new("L", (W, H)); ImageDraw.Draw(out_m).text(org, s, font=f, fill=255, stroke_width=sw, stroke_fill=255)
    ys = np.linspace(0, 1, H)[:, None, None]
    grad = (np.array(top) * (1 - ys) + np.array(bottom) * ys) * np.ones((1, W, 1))
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if glow:
        g = out_m.filter(ImageFilter.GaussianBlur(sw * 1.6))
        glow_im = Image.new("RGBA", (W, H), glow + (0,)); glow_im.putalpha(g.point(lambda v: min(255, int(v * 1.4))))
        canvas.alpha_composite(glow_im)
    st = Image.new("RGBA", (W, H), stroke + (0,)); st.putalpha(out_m); canvas.alpha_composite(st)
    fi = Image.fromarray(np.dstack([grad, np.zeros((H, W))]).astype(np.uint8), "RGBA"); fi.putalpha(fill_m)
    canvas.alpha_composite(fi)
    if shear:
        ext = int(H * shear)
        canvas = canvas.transform((W + ext, H), Image.AFFINE, (1, shear, -ext, 0, 1, 0), Image.BICUBIC)
    return canvas.crop(canvas.getbbox())


def stack_center(base, items, cx, cy, gap):
    """items(RGBA画像)を縦に並べ、ブロック全体の中心を (cx, cy) にぴったり合わせる。"""
    total = sum(i.height for i in items) + gap * (len(items) - 1)
    y = round(cy - total / 2)
    for i in items:
        base.alpha_composite(i, (round(cx - i.width / 2), y))
        y += i.height + gap


def collage_header(bg_path, logo, out_path):
    W, H = 2560, 1440
    bg = fit_cover(Image.open(bg_path).convert("RGB"), W, H).filter(ImageFilter.UnsharpMask(2, 60, 2)).convert("RGBA")
    lg = logo.resize((round(logo.width * 150 / logo.height), 150), Image.LANCZOS)
    title = styled_text("バイス切り抜き", 150)
    sub = styled_text("GTA6の神シーン&攻略小ネタを毎日お届け", 40, font=SUB_FONT, top=(255, 236, 120),
                      bottom=(255, 200, 60), stroke=(0, 0, 0), stroke_w=5, glow=None, shear=0)
    stack_center(bg, [lg, title, sub], W / 2, H / 2, 12)
    bg.convert("RGB").save(out_path, optimize=True)


def collage_icon(src, logo, out_path, logo_w, cy, sub=None, sub_size=60, gap=6):
    S = 800
    im = fit_cover(Image.open(src).convert("RGB"), S, S).convert("RGBA")
    items = [logo.resize((logo_w, round(logo.height * logo_w / logo.width)), Image.LANCZOS)]
    if sub:
        items.append(styled_text(sub, sub_size))
    stack_center(im, items, S / 2, cy, gap)
    im.convert("RGB").save(out_path, optimize=True)


def main_collage(base):
    raw = os.path.join(base, "raw")
    logo = key_black(Image.open(os.path.join(raw, "logo_gta6_a.png")))
    collage_header(os.path.join(raw, "collage_header_a.png"), logo, os.path.join(base, "header_c_collage.png"))
    collage_header(os.path.join(raw, "collage_header_b.png"), logo, os.path.join(base, "header_d_collage.png"))
    collage_icon(os.path.join(raw, "collage_icon_a.png"), logo, os.path.join(base, "icon_e_collage.png"),
                 270, 400, "バイス切り抜き", 40)
    collage_icon(os.path.join(raw, "collage_icon_b.png"), logo, os.path.join(base, "icon_f_bike.png"),
                 470, 650, "バイス切り抜き", 64)


if __name__ == "__main__":
    (main_collage if len(sys.argv) > 2 and sys.argv[2] == "collage" else main)(os.path.abspath(sys.argv[1]))
