"""各話のサムネイル（本編 1280x720／ショート 1080x1920）を作る。PILのみ・クレジット不要。

背景は各話の3Dを高解像度で描き直した静止画（Blender の --still --res で書き出したもの）。
  python3 scripts/mono_no_issho/branding/make_thumbs.py

出力: assets/output/mono_no_issho/thumbs/
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "assets/output/mono_no_issho"
OUT = SRC / "thumbs"
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

WHITE = (255, 255, 255)
INK = (20, 20, 26)
ACC = (255, 138, 60)       # チャンネルのアクセント（オレンジ）
YEL = (255, 214, 64)

# lines: 1行 = [(文字, 強調?) ...]。強調はオレンジの帯に白文字
LONG = [
    dict(name="ep01_thumb", ep="#1", bg="ep01/3d/h13_worn_coin/still_0061.png", focus=0.72,
         lines=[[("10年間ほぼ", 0)], [("作られなかった", 0)], [("1円玉", 1)]], badge="11年ぶりに量産"),
    dict(name="ep02_thumb", ep="#2", bg="ep02/3d/k03_train_seat/still_0061.png", focus=0.57, zoom=1.25, fy=0.62,
         lines=[[("なくした", 0), ("傘", 1), ("は", 0)], [("どこへ行く？", 0)]], badge="東京だけで年28万本"),
    dict(name="ep03_thumb", ep="#3", bg="ep03/3d/p03_cap_label/still_0061.png", focus=0.55, zoom=1.3, fy=0.56,
         lines=[[("ペットボトルは", 0)], [("何に", 0)], [("生まれ変わる？", 1)]], badge="リサイクル率85%"),
    dict(name="ep04_thumb", ep="#4", bg="ep04/3d/c01_closet/still_0100.png", focus=0.72,
         lines=[[("一度も着ない服", 0)], [("平均", 0), ("25枚", 1)]], badge="手放した服のゆくえ"),
]
SHORT = [
    dict(name="ep01_short_cover", ep="#1", bg="ep01/3d/h10_vending/still_0024.png",
         lines=[[("1円玉が", 0)], [("自販機で", 0)], [("使えない", 1)], [("理由", 0)]]),
    dict(name="ep02_short_cover", ep="#2", bg="ep02/3d/k03_train_seat/still_0062.png",
         lines=[[("なくした傘", 0)], [("2週間後", 1)], [("どこへ？", 0)]]),
    dict(name="ep03_short_cover", ep="#3", bg="ep03/3d/p03_cap_label/still_0063.png",
         lines=[[("ペットボトルの", 0)], [("次の姿", 1), ("は？", 0)]], quiz=True),
]


def F(size, bold=True):
    return ImageFont.truetype(BOLD if bold else REG, int(size), index=0)


def cover(im, w, h, fx=0.5, fy=0.5, zoom=1.0):
    """画面いっぱいに拡大して切り抜く。fx, fy = 残す中心（0〜1）。"""
    sc = max(w / im.width, h / im.height) * zoom
    im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    l = min(max(0, im.width * fx - w / 2), im.width - w)
    t = min(max(0, im.height * fy - h / 2), im.height - h)
    return im.crop((int(l), int(t), int(l) + w, int(t) + h))


def shade(im, side="left", strength=0.8):
    """文字側を暗くするグラデーション。"""
    w, h = im.size
    g = Image.linear_gradient("L")   # 256x256 上→下 0→255
    if side == "left":
        g = g.rotate(-90, expand=True)     # 左ほど255（暗くする量が多い）
        g = g.resize((w, h))
        g = g.point(lambda v: int(min(255, max(0, (v - 70) * 1.6)) * strength))
    elif side == "top":
        g = g.rotate(180).resize((w, h))
        g = g.point(lambda v: int(min(255, max(0, (v - 60) * 1.4)) * strength))
    dark = Image.new("RGB", (w, h), (10, 10, 16))
    im.paste(dark, (0, 0), g)
    return im


def text_with_shadow(base, xy, s, font, fill, anchor="ls", blur=8, off=4):
    sh = Image.new("L", base.size, 0)
    ImageDraw.Draw(sh).text((xy[0] + off, xy[1] + off), s, font=font, fill=200, anchor=anchor)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    base.paste(Image.new("RGB", base.size, (0, 0, 0)), (0, 0), sh)
    ImageDraw.Draw(base).text(xy, s, font=font, fill=fill, anchor=anchor)


def draw_lines(im, lines, x, y, size, lead, align="left", maxw=None):
    """lines を描く。強調語はオレンジの帯の上に白文字。y はいちばん上の行のベースライン。"""
    d = ImageDraw.Draw(im)
    for row in lines:
        f = F(size)
        widths = [d.textlength(s, font=f) + (size * 0.36 if hi else 0) for s, hi in row]
        tw = sum(widths)
        if maxw and tw > maxw:      # はみ出す行は縮める
            f = F(size * maxw / tw)
            widths = [w * maxw / tw for w in widths]
            tw = maxw
        cx = x - tw / 2 if align == "center" else x
        for (s, hi), w in zip(row, widths):
            if hi:
                pad = f.size * 0.18
                box = [cx, y - f.size * 0.98, cx + w, y + f.size * 0.2]
                sh = Image.new("L", im.size, 0)
                ImageDraw.Draw(sh).rounded_rectangle([box[0] + 6, box[1] + 8, box[2] + 6, box[3] + 8], int(f.size * 0.14), fill=150)
                im.paste(Image.new("RGB", im.size, (0, 0, 0)), (0, 0), sh.filter(ImageFilter.GaussianBlur(10)))
                d = ImageDraw.Draw(im)
                d.rounded_rectangle(box, int(f.size * 0.14), fill=ACC)
                d.text((cx + pad, y), s, font=f, fill=WHITE, anchor="ls")
            else:
                text_with_shadow(im, (cx, y), s, f, WHITE)
                d = ImageDraw.Draw(im)
            cx += w
        y += lead * size
    return y


def tag(im, x, y, ep, size):
    """左上の「モノの一生 #N」タグ（軌道の点つき）。"""
    d = ImageDraw.Draw(im)
    f = F(size)
    s = f"モノの一生 {ep}"
    w = d.textlength(s, font=f)
    r = size * 0.42
    pad = size * 0.5
    box = [x, y, x + r * 2 + pad * 2.4 + w, y + size * 1.7]
    d.rounded_rectangle(box, int(size * 0.85), fill=(16, 16, 22))
    cy = (box[1] + box[3]) / 2
    cx = x + pad + r
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACC, width=max(2, int(size * 0.1)))
    d.ellipse([cx + r * 0.55 - size * 0.12, cy - r * 0.8 - size * 0.12, cx + r * 0.55 + size * 0.12, cy - r * 0.8 + size * 0.12], fill=ACC)
    d.text((cx + r + pad * 0.6, cy), s, font=f, fill=WHITE, anchor="lm")


def badge(im, x, y, s, size):
    d = ImageDraw.Draw(im)
    f = F(size)
    w = d.textlength(s, font=f)
    box = [x, y, x + w + size * 1.2, y + size * 1.6]
    d.rounded_rectangle(box, int(size * 0.3), fill=YEL)
    d.text((x + size * 0.6, (box[1] + box[3]) / 2), s, font=f, fill=INK, anchor="lm")


def long_thumb(c):
    W, H = 1280, 720
    src = Image.open(SRC / c["bg"]).convert("RGB")
    if c.get("flip"):   # 被写体を文字と反対側（右）へ
        src = src.transpose(Image.FLIP_LEFT_RIGHT)
    im = cover(src, W, H, fx=c.get("focus", 0.7) - 0.2, fy=c.get("fy", 0.5), zoom=c.get("zoom", 1.0))
    im = shade(im, "left", 0.92)
    tag(im, 44, 40, c["ep"], 30)
    n = len(c["lines"])
    size = 118 if n <= 2 else 104
    y0 = H / 2 - (n - 1) * size * 1.18 / 2 + size * 0.38
    draw_lines(im, c["lines"], 56, y0, size, 1.18, maxw=W * 0.62)
    if c.get("badge"):
        badge(im, 58, H - 118, c["badge"], 38)
    return im


def short_cover(c):
    W, H = 1080, 1920
    im = cover(Image.open(SRC / c["bg"]).convert("RGB"), W, H)
    im = shade(im, "top", 0.9)
    tag(im, W / 2 - 230, 250, c["ep"], 40)
    n = len(c["lines"])
    size = 150
    draw_lines(im, c["lines"], W / 2, 560, size, 1.22, align="center", maxw=W - 120)
    if c.get("quiz"):
        d = ImageDraw.Draw(im)
        y = 560 + n * size * 1.22 + 40
        for i, (k, s) in enumerate((("A", "ボトル"), ("B", "フタ"), ("C", "シャツ"))):
            x = W / 2 + (i - 1) * 310
            d.rounded_rectangle([x - 140, y - 60, x + 140, y + 60], 30, fill=(16, 16, 22))
            d.ellipse([x - 120, y - 40, x - 40, y + 40], fill=ACC)
            d.text((x - 80, y), k, font=F(50), fill=WHITE, anchor="mm")
            d.text((x + 40, y), s, font=F(48), fill=WHITE, anchor="mm")
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ok = []
    for c in LONG:
        if (SRC / c["bg"]).exists():
            long_thumb(c).save(OUT / f"{c['name']}.png"); ok.append(c["name"])
    for c in SHORT:
        if (SRC / c["bg"]).exists():
            short_cover(c).save(OUT / f"{c['name']}.png"); ok.append(c["name"])
    print("wrote", ok)


if __name__ == "__main__":
    main()
