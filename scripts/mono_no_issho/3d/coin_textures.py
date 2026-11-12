"""1円玉風コインの表裏ハイトマップ(PNG, 16bit相当のグレースケール)を生成する。

実物の図柄の完全な複製ではなく、マクロ撮影で「1円玉らしく」見える程度の
様式化デザイン(若木の枝/「1」の数字と外周リム)。
"""
import math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 2048
C = S / 2


def _rim(d):
    d.ellipse([0, 0, S - 1, S - 1], fill=0)
    d.ellipse([S * .01, S * .01, S * .99, S * .99], fill=235)   # 外周リム(高い)
    d.ellipse([S * .07, S * .07, S * .93, S * .93], fill=90)    # フィールド(低い)


def _font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def front(path):
    """表: 中央の若木(幹と左右の葉)"""
    im = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(im)
    _rim(d)
    hi = 200
    # 幹
    d.line([(C, S * .80), (C, S * .30)], fill=hi, width=int(S * .022))
    # 葉(左右交互に楕円を回転して貼る)
    for i, t in enumerate([.70, .60, .50, .40, .33]):
        for side in (-1, 1):
            leaf = Image.new("L", (int(S * .22), int(S * .08)), 0)
            ld = ImageDraw.Draw(leaf)
            ld.ellipse([0, 0, leaf.width - 1, leaf.height - 1], fill=hi)
            ld.line([(leaf.width * .05, leaf.height / 2), (leaf.width * .95, leaf.height / 2)], fill=150, width=6)
            ang = side * (35 - i * 3)
            leaf = leaf.rotate(ang, expand=True, resample=Image.BICUBIC)
            x = C + side * S * .11 - leaf.width / 2
            y = S * t - leaf.height / 2
            im.paste(Image.new("L", leaf.size, hi), (int(x), int(y)), leaf)
    # 頂芽
    d.ellipse([C - S * .03, S * .25, C + S * .03, S * .33], fill=hi)
    return im


def back(path):
    """裏: 大きな「1」と年号風の小さな刻み"""
    im = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(im)
    _rim(d)
    f = _font(int(S * .55))
    bb = d.textbbox((0, 0), "1", font=f)
    d.text((C - (bb[2] + bb[0]) / 2, C - (bb[3] + bb[1]) / 2 - S * .02), "1", font=f, fill=200)
    # 下部に年号を思わせる短い刻み(読める文字にはしない)
    for k in range(4):
        x = C - S * .09 + k * S * .06
        d.rectangle([x, S * .80, x + S * .035, S * .83], fill=170)
    return im


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in (("coin_front.png", front), ("coin_back.png", back)):
        im = fn(None).filter(ImageFilter.GaussianBlur(S * .0025))  # 角を少し丸める
        im.save(out / name)
        print("wrote", out / name)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "assets/output/mono_no_issho/ep01/tex")
