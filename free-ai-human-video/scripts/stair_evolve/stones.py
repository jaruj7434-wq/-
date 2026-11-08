"""成功演出(フィーバー)で噴き出す石の絵。fruit_fever と同じ形の関数(KINDS / draw_fruit / draw_cut)。"""
import numpy as np

import space_items as S

KINDS = [("小石", (0.62, 0.6, 0.57), (0.62, 0.6, 0.57), 0.5), ("岩", (0.55, 0.45, 0.35), (0.55, 0.45, 0.35), 0.5)] * 3
_POLY = [S.rock_poly(np.random.default_rng(k + 40), 1.0) for k in range(len(KINDS))]


def draw_fruit(ctx, kind, x, y, r, rot=0.0):
    S.draw_stage(ctx, kind % 2, x, y, rot, r, [(px * r, py * r) for px, py in _POLY[kind]])


def draw_cut(ctx, kind, r):
    draw_fruit(ctx, kind, 0, 0, r, 0.0)
