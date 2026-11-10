"""おじさん顔のフルーツ(Higgs Field の Seedream 5.0 Pro で生成した背景透明の写真 6種類)の絵。
fruit_fever と同じ形の関数(KINDS / draw_fruit / draw_cut)もそろえる。"""
import math
import os

import cairo

IMG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "source", "ojisan_fruit")
NAMES = ["りんご", "オレンジ", "レモン", "いちご", "もも", "スイカ"]
COLORS = [(0.85, 0.1, 0.1), (1.0, 0.55, 0.05), (1.0, 0.9, 0.2), (0.9, 0.1, 0.2), (1.0, 0.65, 0.6), (0.2, 0.6, 0.2)]
KINDS = [(n, c, c, 0.5) for n, c in zip(NAMES, COLORS)]
_IMG = {}


def _load(k):
    if k not in _IMG:
        img = cairo.ImageSurface.create_from_png(os.path.join(IMG_DIR, f"fruit{k + 1}.png"))
        # 透明でない部分の大きさ(切り抜いた本体の半径)を調べておく
        w, h = img.get_width(), img.get_height()
        import numpy as np
        a = np.ndarray((h, w, 4), np.uint8, img.get_data(), strides=(img.get_stride(), 4, 1))[:, :, 3]
        ys, xs = np.nonzero(a > 100)
        cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
        rad = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2
        _IMG[k] = (img, cx, cy, rad)
    return _IMG[k]


def draw_fruit(ctx, kind, x, y, r, rot=0.0, alpha=1.0):
    img, cx, cy, rad = _load(kind)
    s = r / rad
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(s, s)
    ctx.translate(-cx, -cy)
    ctx.set_source_surface(img, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def draw_cut(ctx, kind, r):
    draw_fruit(ctx, kind, 0, 0, r)
