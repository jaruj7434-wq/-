# 馬の名前の大きな銀色の文字 (参考動画の流れる太い文字の雰囲気。映画の文字そのものはまねない)
# 実行場所: Higgs のサンドボックス ~/gate3 (~/.fonts/DelaGothicOne-Regular.ttf がある)
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
F = os.path.expanduser('~/.fonts/DelaGothicOne-Regular.ttf')
def chrome(text, size=112, out='n.png'):
    f = ImageFont.truetype(F, size)
    l, t, r, b = f.getbbox(text)
    w, h = r - l + 60, b - t + 60
    mask = Image.new('L', (w, h), 0); ImageDraw.Draw(mask).text((30 - l, 30 - t), text, font=f, fill=255)
    # 縦の金属グラデーション (上が明るく、中ほどで一度暗く、下でまた光る)
    grad = Image.new('RGB', (1, h))
    stops = [(0.0, (250, 250, 252)), (0.42, (200, 204, 210)), (0.5, (110, 114, 122)), (0.62, (215, 218, 224)), (1.0, (150, 154, 160))]
    for y in range(h):
        p = y / (h - 1)
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= p <= p1:
                k = (p - p0) / (p1 - p0); grad.putpixel((0, y), tuple(int(c0[i] + (c1[i] - c0[i]) * k) for i in range(3))); break
    grad = grad.resize((w, h))
    txt = Image.new('RGBA', (w, h), (0, 0, 0, 0)); txt.paste(grad, (0, 0), mask)
    edge = mask.filter(ImageFilter.MaxFilter(5))
    outline = Image.new('RGBA', (w, h), (25, 25, 30, 0)); outline.putalpha(edge.point(lambda v: int(v * 0.85)))
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sh.putalpha(mask.filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * 0.7)))
    im = Image.new('RGBA', (w + 20, h + 20), (0, 0, 0, 0))
    im.alpha_composite(sh, (14, 18)); im.alpha_composite(outline, (10, 10)); im.alpha_composite(txt, (10, 10))
    # 少し斜体にして勢いを出す
    im = im.transform(im.size, Image.AFFINE, (1, 0.18, -0.18 * im.size[1] / 2, 0, 1, 0), Image.BICUBIC)
    im.save(out); print(out, im.size)
chrome('ディープインパクト', size=100, out='name_deep.png')
chrome('トウカイテイオー', out='name_teio.png')
chrome('サイレンススズカ', out='name_suzuka.png')
