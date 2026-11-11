"""冒頭の架空配給会社ロゴ「デブ株式会社」を合成する。
使い方: python3 studio_logo.py 背景.png 出力.png
背景は AI 生成の放射状の光(文字なし)。文字・円はすべてここで描く。"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
CX, CY, R = 960, 410, 182          # 紋章の円(参考画像の比率から換算)
SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"


def background(path):
    bg = Image.open(path).convert("RGB")
    # 光の中心(画像中央)を紋章の中心へ移すため、少し拡大してずらす
    s = max(W * 1.18 / bg.width, (H + 2 * (H // 2 - CY) + 4) / bg.height)
    bg = bg.resize((round(bg.width * s), round(bg.height * s)), Image.LANCZOS)
    ox = bg.width // 2 - CX
    oy = bg.height // 2 - CY
    bg = bg.crop((ox, oy, ox + W, oy + H))
    a = np.asarray(bg).astype(np.float32)
    # 参考に寄せて少し暗く・青緑寄りに
    a *= 0.85
    a[..., 0] *= 0.92
    a[..., 2] *= 1.04
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def glyph_layer(draw_fn, blur=0):
    lay = Image.new("L", (W, H), 0)
    draw_fn(ImageDraw.Draw(lay))
    return lay.filter(ImageFilter.GaussianBlur(blur)) if blur else lay


def paste_color(img, mask, rgb):
    col = Image.new("RGB", (W, H), rgb)
    img.paste(col, (0, 0), mask)


def main(src, out):
    img = background(src)

    # 中心の白い光(円の背後)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot(xx - CX, yy - CY)
    glow = np.exp(-(d / 150.0) ** 2) * 70
    a = np.asarray(img).astype(np.float32) + glow[..., None] * np.array([0.9, 1.0, 1.0])
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

    # 白い円(リング)
    ring_w = 20
    def ring(d):
        d.ellipse((CX - R, CY - R, CX + R, CY + R), outline=255, width=ring_w)
    # 円の中の「デ」「ブ」(縦並び、円に接するくらい大きく)
    f = ImageFont.truetype(SANS, 168)
    def kana(d):
        for ch, cy in (("デ", CY - 76), ("ブ", CY + 80)):
            d.text((CX, cy), ch, font=f, fill=255, anchor="mm")
    shadow = glyph_layer(lambda d: (ring(d), kana(d)), blur=10)
    paste_color(img, shadow.point(lambda v: min(255, v * 1.6)), (6, 14, 24))
    paste_color(img, glyph_layer(lambda d: (ring(d), kana(d))), (255, 255, 255))

    # 金色の社名
    fj = ImageFont.truetype(SANS, 92)
    def corp(d):
        txt = "デブ株式会社"
        sp = 104
        x0 = CX - sp * (len(txt) - 1) / 2
        for i, ch in enumerate(txt):
            d.text((x0 + sp * i, 745), ch, font=fj, fill=255, anchor="mm")
    m = glyph_layer(corp)
    # 黒い縁取り+影
    edge = m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2))
    paste_color(img, edge.point(lambda v: v * 0.8), (20, 12, 0))
    # 縦グラデーションの金
    g = np.zeros((H, W, 3), np.float32)
    t = np.clip((yy - 700) / 90.0, 0, 1)[..., None]
    g[:] = (1 - t) * np.array([250, 228, 90]) + t * np.array([214, 172, 30])
    goldimg = Image.fromarray(g.astype(np.uint8))
    img.paste(goldimg, (0, 0), m)

    # 英字(セリフ体、字間広め)
    fe = ImageFont.truetype(SERIF, 46)
    txt = "DEBU CO., LTD."
    track = 7
    widths = [fe.getlength(c) + track for c in txt]
    x = CX - (sum(widths) - track) / 2
    def eng(d):
        xx_ = x
        for c, w_ in zip(txt, widths):
            d.text((xx_, 828), c, font=fe, fill=255, anchor="lm")
            xx_ += w_
    me = glyph_layer(eng)
    paste_color(img, me.filter(ImageFilter.GaussianBlur(3)).point(lambda v: v * 0.6), (0, 0, 0))
    paste_color(img, me, (246, 240, 220))

    img.save(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
