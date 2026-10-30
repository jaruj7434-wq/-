"""霜が溶ける時刻・再び凍る時刻のマップ(フロントガラスの UV 上、0〜1 の値)を numpy で作って 16bit PNG に保存する。

値が 1 の場所はそのカットの間ずっと霜のまま。カットの中ではしきい値を 0→1 へ動かす。
使い方: python maps.py <出力フォルダ>
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from plan import IMPACT, SLANT

W, H = 768, 512
U, V = np.meshgrid(np.linspace(-1, 1, W), np.linspace(0, 1, H))   # 行=v(下から)、列=u
HW = 0.72 - 0.08 * V
X, Y = U * HW, V * SLANT                                             # ガラス上の長さ [m]


def noise(scale_px, seed, octaves=4):
    """なめらかなノイズ(-1〜1 くらい)。scale_px はいちばん大きな模様の大きさ(画素)。"""
    rng = np.random.default_rng(seed)
    out = np.zeros((H, W))
    amp, s, total = 1.0, scale_px, 0.0
    for _ in range(octaves):
        gh, gw = max(2, int(H / s) + 2), max(2, int(W / s) + 2)
        g = rng.standard_normal((gh, gw))
        yi = np.linspace(0, gh - 1.001, H)
        xi = np.linspace(0, gw - 1.001, W)
        y0, x0 = yi.astype(int), xi.astype(int)
        fy, fx = (yi - y0)[:, None], (xi - x0)[None, :]
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        a = g[y0][:, x0] * (1 - fx) + g[y0][:, x0 + 1] * fx
        b = g[y0 + 1][:, x0] * (1 - fx) + g[y0 + 1][:, x0 + 1] * fx
        out += amp * (a * (1 - fy) + b * fy)
        total += amp
        amp *= 0.5
        s /= 2
    return out / total


def first_time(mask_at, steps=240):
    """mask_at(τ) が初めて真になる τ(ならなければ 1)。"""
    t = np.ones((H, W))
    for tau in np.linspace(0, 1, steps):
        m = mask_at(tau) & (t >= 1)
        t[m] = tau
    return t


def flow_mask(x0, y0, speed, spread, seed, pool=0.05, pool_grow=0.1, wobble=0.035):
    """(x0, y0) から下へ流れるお湯で溶ける範囲。"""
    n1 = noise(90, seed)
    n2 = noise(25, seed + 1)
    below = y0 - Y
    xc = x0 + wobble * np.sin(below * 13 + 1.0) + 0.02 * n1
    r = np.hypot(X - x0, Y - y0)

    def at(tau):
        R = pool + pool_grow * tau
        front = speed * tau
        width = 0.03 + spread * np.clip(below, 0, None) * tau + 0.015 * n2
        stream = (below > -0.01) & (below < front) & (np.abs(X - xc) < width)
        return (r < R * (1 + 0.25 * n2)) | stream
    return at


def save(path, a):
    a = np.clip(a, 0, 1)
    Image.fromarray((a[::-1] * 65535).astype(np.uint16)).save(path)  # 画像は上が v=1


def grow_steps(melted, max_steps=60):
    """溶けた場所の、まだ凍っている場所からの距離(画素の段数)。"""
    d = np.full(melted.shape, max_steps, float)
    frontier = ~melted
    d[frontier] = 0
    cur = frontier.copy()
    for k in range(1, max_steps):
        nb = cur.copy()
        nb[1:] |= cur[:-1]
        nb[:-1] |= cur[1:]
        nb[:, 1:] |= cur[:, :-1]
        nb[:, :-1] |= cur[:, 1:]
        new = nb & ~cur
        d[new] = k
        cur = nb
    return d


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    x0 = IMPACT[0] * (0.72 - 0.08 * IMPACT[1])
    y0 = IMPACT[1] * SLANT
    # 冒頭:熱いお湯。当たった所から広がり、下へ筋になって流れる
    save(out / "hook_melt.png", first_time(flow_mask(x0, y0, speed=0.75, spread=0.35, seed=1)))
    # ぬるま湯:前半で溶け、後半に縁から内側へ厚い氷になる
    m = first_time(flow_mask(x0 - 0.05, y0, speed=0.9, spread=0.3, seed=7, pool=0.06, pool_grow=0.12))
    melt = np.where(m < 1, m * 0.35, 1.0)
    melted = melt < 1
    d = grow_steps(melted, 70)
    freeze = np.where(melted, 0.42 + d / 70 * 0.5 + 0.06 * noise(30, 9), 1.0)
    save(out / "lukewarm_melt.png", melt)
    save(out / "lukewarm_freeze.png", freeze)
    # デフロスター:下の吹き出し口から溶けて上へ広がる(運転席側・助手席側の2つのふくらみ)
    lobes = 0.22 * (np.exp(-((U + 0.45) / 0.32) ** 2) + np.exp(-((U - 0.45) / 0.32) ** 2))
    defrost = 0.05 + V * 0.95 - lobes * (1 - V) + 0.06 * noise(60, 3) + 0.08 * np.abs(U) ** 3
    save(out / "defrost_melt.png", np.clip(defrost, 0.02, 1.2))
    # 解氷スプレー:吹きかけた場所が数秒で一気に溶ける(右上→左下へ往復しながら吹く)
    n = noise(40, 5)
    t = np.ones((H, W))
    for tau in np.linspace(0, 0.55, 120):
        ph = tau / 0.55
        cu = 0.55 - 1.1 * ph
        cv = 0.68 - 0.36 * ph + 0.1 * np.sin(ph * 9)
        cx, cy = cu * 0.68, cv * SLANT
        dist = np.hypot(X - cx, Y - cy) * (1 + 0.3 * n)
        hit = tau + dist / 0.9
        t = np.minimum(t, np.where(dist < 0.3, hit, 1.0))
    save(out / "spray_melt.png", t)
    print("maps ->", out)


if __name__ == "__main__":
    main(sys.argv[1])
