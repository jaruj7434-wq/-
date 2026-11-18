"""アカウント画像 第2版（おしゃれ版）。PILのみ・クレジット不要。

2つの方向性を作る:
  edit = エディトリアル（生成り色の紙・明朝・細い線・写真カード）
  pop  = グラデーション（夕焼け色・太いゴシック・軌道リング）

  python3 scripts/mono_no_issho/branding/make_brand2.py

出力: assets/output/mono_no_issho/brand/v2/
  icon_edit.png / icon_pop.png               1080x1080
  header_youtube_edit.png / _pop.png         2560x1440（中央 1546x423 が安全範囲）
  header_x_edit.png / _pop.png               1500x500
  preview.png                                 丸切り抜き・安全範囲の確認用
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "assets/output/mono_no_issho"
OUT = SRC / "brand/v2"
SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
SERIF_R = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
SANS_R = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

PAPER = (244, 239, 230)
INK = (34, 32, 36)
INK2 = (110, 104, 98)
TERRA = (214, 106, 64)
POP_A = (255, 168, 76)    # グラデーション上
POP_B = (240, 88, 120)    # グラデーション下
POP_C = (120, 70, 190)

CARDS = [("01", "1円玉", "ep01/3d/h13_worn_coin"), ("02", "傘", "ep02/3d/k02_store_stand"),
         ("03", "ペットボトル", "ep03/3d/p03_cap_label"), ("04", "服", "ep04/3d/c01_closet")]


def F(path, size):
    return ImageFont.truetype(path, int(size), index=0)


def grain(im, amt=10, seed=1):
    """紙・フィルムっぽい粒子を足す。"""
    random.seed(seed)
    n = Image.effect_noise(im.size, 40).convert("L")
    n = n.point(lambda v: 128 + (v - 128) * amt / 40)
    return ImageChops.add(ImageChops.subtract(im, Image.merge("RGB", [n] * 3).point(lambda v: max(0, 128 - v))),
                          Image.merge("RGB", [n] * 3).point(lambda v: max(0, v - 128)))


def spaced(d, xy, s, font, fill, track, anchor="l"):
    """字間を空けて横書き。anchor: l/m/r（縦は中央）。"""
    w = sum(d.textlength(c, font=font) for c in s) + track * (len(s) - 1)
    x, y = xy
    if anchor == "m":
        x -= w / 2
    elif anchor == "r":
        x -= w
    for c in s:
        d.text((x, y), c, font=font, fill=fill, anchor="lm")
        x += d.textlength(c, font=font) + track
    return w


def vertical(d, x, y, s, font, fill, gap=0.0):
    """縦書き（上から下へ）。x は列の中心。"""
    size = font.size
    for c in s:
        d.text((x, y + size / 2), c, font=font, fill=fill, anchor="mm")
        y += size * (1 + gap)
    return y


def gradient(size, c1, c2, c3=None, angle=35):
    w, h = size
    g = Image.new("RGB", size)
    px = g.load()
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    L = abs(w * dx) + abs(h * dy)
    step = 2
    small = Image.new("RGB", (w // step + 1, h // step + 1))
    sp = small.load()
    for y in range(small.height):
        for x in range(small.width):
            t = ((x * step) * dx + (y * step) * dy) / L
            t = min(1, max(0, t))
            if c3 is None:
                col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            elif t < 0.6:
                u = t / 0.6
                col = tuple(int(c1[i] + (c2[i] - c1[i]) * u) for i in range(3))
            else:
                u = (t - 0.6) / 0.4
                col = tuple(int(c2[i] + (c3[i] - c2[i]) * u) for i in range(3))
            sp[x, y] = col
    return small.resize(size, Image.BILINEAR)


def orbit(d, cx, cy, r, w, col, dot_deg=-40, dot_r=None):
    """細い円＋その上を回る点（ものの一生の循環）。"""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=w)
    a = math.radians(dot_deg)
    dr = dot_r or w * 3.2
    x, y = cx + r * math.cos(a), cy + r * math.sin(a)
    d.ellipse([x - dr, y - dr, x + dr, y + dr], fill=col)


def rounded_photo(path, w, h, rad):
    im = Image.open(path).convert("RGB")
    sc = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * sc) + 1, int(im.height * sc) + 1), Image.LANCZOS)
    l, t = (im.width - w) / 2, (im.height - h) / 2
    im = im.crop((int(l), int(t), int(l) + w, int(t) + h))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], rad, fill=255)
    return im, m


def shadow(base, box, rad, blur, alpha=70, off=(0, 0)):
    m = Image.new("L", base.size, 0)
    x0, y0, x1, y1 = box
    ImageDraw.Draw(m).rounded_rectangle([x0 + off[0], y0 + off[1], x1 + off[0], y1 + off[1]], rad, fill=alpha)
    m = m.filter(ImageFilter.GaussianBlur(blur))
    base.paste(Image.new("RGB", base.size, (0, 0, 0)), (0, 0), m)


# ---------------- アイコン ----------------
def icon_edit():
    S = 2160
    im = Image.new("RGB", (S, S), PAPER)
    d = ImageDraw.Draw(im)
    c = S / 2
    orbit(d, c, c, 760, 8, TERRA, dot_deg=-35, dot_r=34)
    # 明朝の縦書き「モノの一生」：右列「一生」大、左列「モノの」小
    vertical(d, c + 140, c - 560, "一生", F(SERIF, 500), INK, gap=-0.02)
    vertical(d, c - 250, c - 560, "モノの", F(SERIF, 230), INK, gap=0.06)
    d.line([(c - 250, c + 230), (c - 250, c + 330)], fill=TERRA, width=8)
    spaced(d, (c, c + 560), "LIFE OF THINGS", F(SANS_R, 62), INK2, 22, anchor="m")
    im = grain(im, 7)
    return im.resize((1080, 1080), Image.LANCZOS)


def icon_pop():
    S = 2160
    im = gradient((S, S), POP_A, POP_B, POP_C, angle=60)
    d = ImageDraw.Draw(im)
    c = S / 2
    orbit(d, c, c, 780, 12, (255, 255, 255), dot_deg=-38, dot_r=40)
    d.text((c, c - 250), "モノの", font=F(SANS, 250), fill=(255, 255, 255), anchor="mm")
    d.text((c, c + 120), "一生", font=F(SANS, 560), fill=(255, 255, 255), anchor="mm")
    spaced(d, (c, c + 500), "LIFE OF THINGS", F(SANS, 64), (255, 240, 235), 20, anchor="m")
    im = grain(im, 8)
    return im.resize((1080, 1080), Image.LANCZOS)


# ---------------- ヘッダー ----------------
def header(w, h, sw, sh, style, cx=None):
    """sw, sh = 安全範囲。中身はすべて安全範囲の中に置く。"""
    S = 2
    W, H, SW, SH = w * S, h * S, sw * S, sh * S
    if style == "edit":
        im = Image.new("RGB", (W, H), PAPER)
        ink, ink2, acc, cardline = INK, INK2, TERRA, (220, 212, 200)
    else:
        im = gradient((W, H), POP_A, POP_B, POP_C, angle=20)
        ink, ink2, acc, cardline = (255, 255, 255), (255, 236, 230), (255, 255, 255), (255, 255, 255)
    d = ImageDraw.Draw(im)
    x0, y0 = ((cx * S if cx else W / 2) - SW / 2), (H - SH) / 2
    # 背景の大きな軌道（安全範囲の外にはみ出してよい飾り）
    orbit(d, x0 + SW * 0.16, H / 2, SH * 1.25, 3 * S, acc if style == "edit" else (255, 255, 255, ), dot_deg=-50,
          dot_r=10 * S)
    # 左：タイトル
    tx = x0 + SW * 0.02
    title = F(SERIF if style == "edit" else SANS, SH * 0.30)
    d.text((tx, y0 + SH * 0.36), "モノの一生", font=title, fill=ink, anchor="lm")
    tw = d.textlength("モノの一生", font=title)
    spaced(d, (tx + 4 * S, y0 + SH * 0.62), "LIFE OF THINGS", F(SANS_R, SH * 0.065), ink2, SH * 0.025)
    d.line([(tx, y0 + SH * 0.73), (tx + SH * 0.18, y0 + SH * 0.73)], fill=acc, width=3 * S)
    d.text((tx, y0 + SH * 0.84), "身近なモノは、どこから来て、どこへ行く？",
           font=F(SERIF_R if style == "edit" else SANS_R, SH * 0.075), fill=ink, anchor="lm")
    # 右：各話のカード
    n = len(CARDS)
    area_x0 = tx + max(tw, SH * 1.55) + SH * 0.18
    area_x1 = x0 + SW
    gap = SH * 0.06
    cw = int((area_x1 - area_x0 - gap * (n - 1)) / n)
    ch = int(SH * 0.62)
    cy0 = int(y0 + SH * 0.08)
    rad = int(SH * 0.05)
    for i, (no, name, p) in enumerate(CARDS):
        cx0 = int(area_x0 + i * (cw + gap))
        box = (cx0, cy0, cx0 + cw, cy0 + ch)
        shadow(im, box, rad, 14 * S, alpha=55 if style == "edit" else 70, off=(0, 6 * S))
        ph, m = rounded_photo(SRC / p / "still_0060.png", cw, ch, rad)
        im.paste(ph, (cx0, cy0), m)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle(box, rad, outline=cardline, width=2 * S)
        ly = cy0 + ch + SH * 0.09
        d.text((cx0, ly), f"#{no}", font=F(SANS, SH * 0.05), fill=acc if style == "edit" else ink2, anchor="lm")
        if cw >= SH * 0.32:   # カードが細い時（X用）は名前を省いて番号だけ
          d.text((cx0, ly + SH * 0.1), name, font=F(SERIF if style == "edit" else SANS, SH * 0.065), fill=ink,
                 anchor="lm")
    im = grain(im, 6 if style == "edit" else 7)
    return im.resize((w, h), Image.LANCZOS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    icons = {"edit": icon_edit(), "pop": icon_pop()}
    for k, im in icons.items():
        im.save(OUT / f"icon_{k}.png")
    heads = {}
    for k in ("edit", "pop"):
        yt = header(2560, 1440, 1546, 423, k)
        yt.save(OUT / f"header_youtube_{k}.png")
        x = header(1500, 500, 1080, 380, k, cx=1500 - 1080 / 2 - 50)   # 左下はXのアイコンが重なるので右寄せ
        x.save(OUT / f"header_x_{k}.png")
        heads[k] = (yt, x)
    # 確認用プレビュー
    P = Image.new("RGB", (2400, 1700), (255, 255, 255))
    for i, k in enumerate(("edit", "pop")):
        ic = icons[k].resize((500, 500))
        m = Image.new("L", (500, 500), 0); ImageDraw.Draw(m).ellipse([0, 0, 499, 499], fill=255)
        P.paste(ic, (20, 20 + i * 840), m)
        yt = heads[k][0].resize((1280, 720)).copy()
        ImageDraw.Draw(yt).rectangle([(1280 - 773) / 2, (720 - 211.5) / 2, (1280 + 773) / 2, (720 + 211.5) / 2],
                                    outline=(255, 0, 0), width=2)
        P.paste(yt, (560, 20 + i * 840))
        P.paste(heads[k][1].resize((540, 180)), (20, 560 + i * 840))
    P.save(OUT / "preview.png")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
