"""アカウント用のアイコンとヘッダー画像を作る（PILのみ。クレジット不要）。

  python3 scripts/mono_no_issho/branding/make_brand.py

出力: assets/output/mono_no_issho/brand/
  icon_a.png      1080x1080 「モノの一生」文字＋循環の矢印
  icon_b.png      1080x1080 循環の矢印の上に 1円玉・傘・ボトル・服 のアイコン
  header_youtube.png  2560x1440（中央 1546x423 がどの端末でも見える範囲）
  header_x.png        1500x500（X・note など）
  header_youtube_guide.png  安全範囲の枠を重ねた確認用
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/output/mono_no_issho/brand"
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

BG = (14, 18, 28)
BG2 = (24, 30, 44)
FG = (240, 242, 245)
SUB = (150, 160, 178)
ACCENT = (255, 150, 60)
BLUE = (90, 170, 255)
TEAL = (70, 200, 180)
SILVER = (205, 210, 216)
COPPER = (225, 170, 120)
CLEAR = (170, 215, 235)

STILLS = [  # ヘッダーに並べる各話の3D（第1話〜第4話）
    "ep01/3d/h09_piggy", "ep02/3d/k03_train_seat", "ep03/3d/p08_new_bottles", "ep04/3d/c01_closet",
]


def font(size, bold=True):
    return ImageFont.truetype(FB if bold else FR, size, index=0)   # index 0 = JP


def ring_arrow(d, cx, cy, r, w, col, start=-60, span=300):
    """太い円弧＋矢じり（時計回り）。"""
    d.arc([cx - r, cy - r, cx + r, cy + r], start, start + span, fill=col, width=w)
    a = math.radians(start + span)
    ex, ey = cx + (r - w / 2) * math.cos(a), cy + (r - w / 2) * math.sin(a)
    tx, ty = -math.sin(a), math.cos(a)          # 進行方向
    nx, ny = math.cos(a), math.sin(a)           # 外向き
    L, Wd = w * 1.5, w * 1.25
    d.polygon([(ex + tx * L, ey + ty * L), (ex + nx * Wd, ey + ny * Wd), (ex - nx * Wd, ey - ny * Wd)], fill=col)


# ---- 小さなアイコン（中心 cx,cy、大きさ s） ----
def coin(d, cx, cy, s):
    d.ellipse([cx - s, cy - s, cx + s, cy + s], fill=SILVER)
    d.ellipse([cx - s * 0.78, cy - s * 0.78, cx + s * 0.78, cy + s * 0.78], outline=(150, 156, 165), width=max(2, int(s * 0.08)))
    d.text((cx, cy), "1", font=font(int(s * 1.0)), fill=(120, 126, 136), anchor="mm")


def umbrella(d, cx, cy, s):
    d.pieslice([cx - s, cy - s * 0.85, cx + s, cy + s * 0.85], 180, 360, fill=BLUE)
    for k in (-0.5, 0, 0.5):   # 骨の切れ込み
        d.ellipse([cx + k * s - s * 0.25, cy - s * 0.12, cx + k * s + s * 0.25, cy + s * 0.12], fill=BG2)
    w = max(3, int(s * 0.09))
    d.line([(cx, cy - s * 0.95), (cx, cy + s * 0.7)], fill=FG, width=w)
    d.arc([cx - s * 0.32, cy + s * 0.45, cx, cy + s * 0.95], 0, 180, fill=FG, width=w)


def bottle(d, cx, cy, s):
    w = s * 0.42
    d.rounded_rectangle([cx - w, cy - s * 0.45, cx + w, cy + s], int(w * 0.5), fill=CLEAR)
    d.polygon([(cx - w, cy - s * 0.35), (cx - w * 0.45, cy - s * 0.78), (cx + w * 0.45, cy - s * 0.78),
               (cx + w, cy - s * 0.35)], fill=CLEAR)
    d.rectangle([cx - w * 0.42, cy - s, cx + w * 0.42, cy - s * 0.78], fill=ACCENT)
    d.rectangle([cx - w, cy - s * 0.05, cx + w, cy + s * 0.35], fill=BLUE)


def shirt(d, cx, cy, s, col=TEAL):
    h = s * 1.15
    d.polygon([(cx - s * 0.55, cy - h * 0.5), (cx - s * 1.0, cy - h * 0.25), (cx - s * 0.8, cy + h * 0.02),
               (cx - s * 0.55, cy - h * 0.1), (cx - s * 0.55, cy + h * 0.5), (cx + s * 0.55, cy + h * 0.5),
               (cx + s * 0.55, cy - h * 0.1), (cx + s * 0.8, cy + h * 0.02), (cx + s * 1.0, cy - h * 0.25),
               (cx + s * 0.55, cy - h * 0.5)], fill=col)
    d.ellipse([cx - s * 0.22, cy - h * 0.62, cx + s * 0.22, cy - h * 0.38], fill=BG2)


ICONS = [coin, umbrella, bottle, shirt]


def radial_bg(size, inner=BG2, outer=BG):
    w, h = size
    im = Image.new("RGB", size, outer)
    m = Image.new("L", size, 0)
    md = ImageDraw.Draw(m)
    r = int(min(w, h) * 0.55)
    md.ellipse([w / 2 - r, h / 2 - r, w / 2 + r, h / 2 + r], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(r * 0.45))
    im.paste(Image.new("RGB", size, inner), (0, 0), m)
    return im


def icon_a():
    S = 2160   # 2倍で描いて縮小（なめらかに）
    im = radial_bg((S, S)); d = ImageDraw.Draw(im)
    c = S / 2
    ring_arrow(d, c, c, 820, 110, ACCENT, start=-70, span=300)
    d.text((c, c - 210), "モノの", font=font(260), fill=FG, anchor="mm")
    d.text((c, c + 150), "一生", font=font(520), fill=FG, anchor="mm")
    return im.resize((1080, 1080), Image.LANCZOS)


def icon_b():
    S = 2160
    im = radial_bg((S, S)); d = ImageDraw.Draw(im)
    c = S / 2
    r = 700
    d.ellipse([c - r, c - r, c + r, c + r], outline=ACCENT, width=70)
    for k in range(4):   # アイコンの間に時計回りの矢じり
        a = math.radians(-45 + k * 90)
        x, y = c + r * math.cos(a), c + r * math.sin(a)
        tx, ty = -math.sin(a), math.cos(a); nx, ny = math.cos(a), math.sin(a)
        L, Wd = 95, 90
        d.polygon([(x + tx * L, y + ty * L), (x - tx * 30 + nx * Wd, y - ty * 30 + ny * Wd),
                   (x - tx * 30 - nx * Wd, y - ty * 30 - ny * Wd)], fill=ACCENT)
    for k, fn in enumerate(ICONS):   # 上・右・下・左
        a = math.radians(-90 + k * 90)
        x, y = c + r * math.cos(a), c + r * math.sin(a)
        d.ellipse([x - 230, y - 230, x + 230, y + 230], fill=BG2, outline=ACCENT, width=24)
        fn(d, x, y + (20 if fn is not umbrella else 30), 140)
    d.text((c, c - 110), "モノの", font=font(170), fill=FG, anchor="mm")
    d.text((c, c + 120), "一生", font=font(330), fill=FG, anchor="mm")
    return im.resize((1080, 1080), Image.LANCZOS)


def still_strip(w, h, gap):
    """各話の3Dを横に並べた帯（暗めに）。"""
    n = len(STILLS)
    tw = (w - gap * (n - 1)) / n
    strip = Image.new("RGB", (w, h), BG)
    for i, s in enumerate(STILLS):
        p = ROOT / "assets/output/mono_no_issho" / s / "still_0060.png"
        im = Image.open(p).convert("RGB")
        sc = max(tw / im.width, h / im.height)
        im = im.resize((int(im.width * sc) + 1, int(im.height * sc) + 1), Image.LANCZOS)
        l = (im.width - tw) / 2; t = (im.height - h) / 2
        im = im.crop((int(l), int(t), int(l + tw), int(t + h)))
        strip.paste(im, (int(i * (tw + gap)), 0))
    return strip


def darken(im, a):
    return Image.blend(im, Image.new("RGB", im.size, BG), a)


def header(w, h, safe_w, safe_h, title_px, tag_px, icon_px):
    bg = darken(still_strip(w, h, max(4, w // 400)), 0.3)
    # 中央に向かって暗くする帯（文字を読みやすく）
    m = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(m)
    md.rounded_rectangle([w / 2 - safe_w * 0.55, h / 2 - safe_h * 0.62, w / 2 + safe_w * 0.55, h / 2 + safe_h * 0.62],
                         int(safe_h * 0.2), fill=235)
    m = m.filter(ImageFilter.GaussianBlur(safe_h * 0.18))
    bg.paste(Image.new("RGB", (w, h), BG), (0, 0), m)
    d = ImageDraw.Draw(bg)
    cx, cy = w / 2, h / 2
    ft = font(title_px)
    tw = d.textlength("モノの一生", font=ft)
    x0 = cx - tw / 2 + icon_px * 0.55
    # 左に小さな循環マーク
    ring_arrow(d, x0 - icon_px * 0.95, cy - tag_px * 0.55, icon_px * 0.42, max(6, int(icon_px * 0.09)), ACCENT,
               start=-70, span=300)
    d.text((x0, cy - tag_px * 0.55), "モノの一生", font=ft, fill=FG, anchor="lm")
    ly = cy - tag_px * 0.55 + title_px * 0.62
    d.line([(x0, ly), (x0 + tw, ly)], fill=ACCENT, width=max(3, title_px // 30))
    d.text((cx + icon_px * 0.08, ly + tag_px * 1.1), "身近なモノは、どこから来て、どこへ行く？",
           font=font(tag_px, bold=False), fill=SILVER, anchor="mm")
    return bg


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    icon_a().save(OUT / "icon_a.png")
    icon_b().save(OUT / "icon_b.png")
    yt = header(2560, 1440, 1546, 423, 150, 52, 150)
    yt.save(OUT / "header_youtube.png")
    g = yt.copy(); gd = ImageDraw.Draw(g)
    gd.rectangle([(2560 - 1546) / 2, (1440 - 423) / 2, (2560 + 1546) / 2, (1440 + 423) / 2], outline=(255, 0, 0), width=4)
    g.save(OUT / "header_youtube_guide.png")
    header(1500, 500, 1100, 360, 120, 40, 120).save(OUT / "header_x.png")
    # 丸く切り抜かれた時の見え方（確認用）
    prev = Image.new("RGB", (1080 * 2 + 60, 1080), (255, 255, 255))
    for i, n in enumerate(("icon_a", "icon_b")):
        im = Image.open(OUT / f"{n}.png")
        m = Image.new("L", im.size, 0); ImageDraw.Draw(m).ellipse([0, 0, 1079, 1079], fill=255)
        prev.paste(im, (i * 1140, 0), m)
    prev.save(OUT / "icon_preview_circle.png")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
