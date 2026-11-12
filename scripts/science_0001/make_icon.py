"""「一瞬の世界」アカウント用の丸アイコンを作る(PILで描画、生成AI不使用)。

  python3 scripts/science_0001/make_icon.py
出力: assets/output/science_0001/icon_*.png (1024x1024, 丸く切り抜かれても収まるデザイン)
  icon_a.png        ストップウォッチの目盛り + 「一瞬」+「の世界」
  icon_b.png        目盛り + 「一瞬」だけを大きく(小さく表示されても読める版)
  *_circle.png      丸く切り抜いたプレビュー
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 1024
OUT = Path("assets/output/science_0001")
FD = Path.home() / ".fonts"
HEAD = str(FD / "DelaGothicOne-Regular.ttf")
BODY = str(FD / "MPLUSRounded1c-ExtraBold.ttf")
YEL = (255, 201, 77)
HOT = (255, 106, 61)
BG0, BG1 = (30, 34, 52), (8, 9, 14)


def background():
    img = Image.new("RGB", (S, S), BG1)
    d = ImageDraw.Draw(img)
    for r in range(S // 2 + 200, 0, -4):  # 中心が少し明るい放射グラデーション
        k = r / (S / 2 + 200)
        c = tuple(int(BG0[i] * (1 - k) + BG1[i] * k) for i in range(3))
        d.ellipse((S / 2 - r, S / 2 - r, S / 2 + r, S / 2 + r), fill=c)
    return img


def dial(img, r=400):
    """ストップウォッチの目盛りと、ほんの一瞬だけ進んだ黄色い針の弧。"""
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    c = S / 2
    for i in range(120):
        a = -math.pi / 2 + i * 2 * math.pi / 120
        long = i % 10 == 0
        r0 = r - (34 if long else 16)
        w = 6 if long else 3
        col = (255, 255, 255, 220 if long else 90)
        d.line((c + r0 * math.cos(a), c + r0 * math.sin(a), c + r * math.cos(a), c + r * math.sin(a)), fill=col,
               width=w)
    # 12時の位置から少しだけ進んだ黄色い弧(=0.001秒)
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    box = (c - r - 22, c - r - 22, c + r + 22, c + r + 22)
    g.arc(box, -90, -62, fill=YEL + (255,), width=26)
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    lay = Image.alpha_composite(glow, lay)
    d = ImageDraw.Draw(lay)
    d.arc(box, -90, -62, fill=YEL + (255,), width=14)
    a = math.radians(-62)
    tx, ty = c + (r + 22) * math.cos(a), c + (r + 22) * math.sin(a)
    d.ellipse((tx - 16, ty - 16, tx + 16, ty + 16), fill=(255, 255, 255, 255))
    return Image.alpha_composite(img.convert("RGBA"), lay)


def center_text(d, text, y, size, fnt, fill, track=0):
    f = ImageFont.truetype(fnt, size)
    if track == 0:
        w = d.textlength(text, font=f)
        d.text((S / 2 - w / 2, y), text, font=f, fill=fill)
        return
    ws = [d.textlength(ch, font=f) for ch in text]
    tot = sum(ws) + track * (len(text) - 1)
    x = S / 2 - tot / 2
    for ch, w in zip(text, ws):
        d.text((x, y), ch, font=f, fill=fill)
        x += w + track


def circle_preview(img, path):
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, S, S), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    out.save(path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # A: 一瞬 + の世界
    a = dial(background())
    d = ImageDraw.Draw(a)
    center_text(d, "一瞬", 330, 230, HEAD, (255, 255, 255), track=10)
    center_text(d, "の世界", 610, 84, BODY, YEL, track=18)
    a = a.convert("RGB")
    a.save(OUT / "icon_a.png")
    circle_preview(a, OUT / "icon_a_circle.png")
    # B: 「一瞬」だけを最大に(小さいアイコン表示向け)
    b = dial(background())
    d = ImageDraw.Draw(b)
    center_text(d, "一瞬", 365, 280, HEAD, (255, 255, 255), track=10)
    b = b.convert("RGB")
    b.save(OUT / "icon_b.png")
    circle_preview(b, OUT / "icon_b_circle.png")
    print("wrote", OUT / "icon_a.png", OUT / "icon_b.png")


if __name__ == "__main__":
    main()
