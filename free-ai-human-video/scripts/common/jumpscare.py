"""失敗したときに出す「幽霊のびっくり演出」の映像と叫び声。

幽霊はプログラムで描いたオリジナルの絵(長い黒髪・真っ黒な目・叫ぶ口)。
既存のキャラクターには似せない。

    ghost = GhostScare(W, H, seed)
    ghost.draw(surface, age)        # age = 出現からの経過秒
    sig = scream(sr)                # 叫び声(numpy 配列, -1〜1)
"""

import math

import cairo
import numpy as np

DURATION = 1.25   # 幽霊が出ている秒数


def _ellipse(c, x, y, rx, ry):
    c.save()
    c.translate(x, y)
    c.scale(rx, ry)
    c.arc(0, 0, 1, 0, 2 * math.pi)
    c.restore()


def _face(w, h, rng):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    c = cairo.Context(surf)
    cx, cy = w / 2, h * 0.47
    fw, fh = w * 0.30, h * 0.24

    # 背景:古いテレビのような薄暗い緑灰色 + 周辺減光
    g = cairo.RadialGradient(cx, cy, 50, cx, cy, h * 0.7)
    g.add_color_stop_rgb(0, 0.20, 0.23, 0.21)
    g.add_color_stop_rgb(1, 0.02, 0.025, 0.02)
    c.set_source(g)
    c.paint()

    # 後ろ髪(顔より奥、肩の下まで)
    c.new_path()
    c.move_to(cx - fw * 1.45, h)
    c.curve_to(cx - fw * 1.55, cy - fh * 0.2, cx - fw * 1.3, cy - fh * 1.35, cx, cy - fh * 1.38)
    c.curve_to(cx + fw * 1.3, cy - fh * 1.35, cx + fw * 1.55, cy - fh * 0.2, cx + fw * 1.45, h)
    c.close_path()
    c.set_source_rgb(0.015, 0.012, 0.012)
    c.fill()

    # 顔(青白い肌、ふちほど暗く)
    g = cairo.RadialGradient(cx, cy - fh * 0.15, fw * 0.1, cx, cy, fh * 1.05)
    g.add_color_stop_rgb(0, 0.88, 0.90, 0.88)
    g.add_color_stop_rgb(0.65, 0.66, 0.70, 0.68)
    g.add_color_stop_rgb(1, 0.30, 0.33, 0.32)
    _ellipse(c, cx, cy, fw, fh)
    c.set_source(g)
    c.fill()

    # 目:くぼんだ影 → 真っ黒な目 → 小さな白い瞳
    for sx in (-1, 1):
        ex, ey = cx + sx * fw * 0.38, cy - fh * 0.10
        g2 = cairo.RadialGradient(ex, ey, 10, ex, ey, fw * 0.45)
        g2.add_color_stop_rgba(0, 0.05, 0.03, 0.05, 0.9)
        g2.add_color_stop_rgba(1, 0.05, 0.03, 0.05, 0.0)
        _ellipse(c, ex, ey, fw * 0.45, fw * 0.45)
        c.set_source(g2)
        c.fill()
        _ellipse(c, ex, ey, fw * 0.19, fw * 0.23)
        c.set_source_rgb(0, 0, 0)
        c.fill()
        _ellipse(c, ex - sx * 5, ey + 6, 6, 6)
        c.set_source_rgb(0.95, 0.95, 0.9)
        c.fill()

    # 鼻の影
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(cx - 8, cy + fh * 0.05)
    c.curve_to(cx - 14, cy + fh * 0.18, cx - 6, cy + fh * 0.24, cx + 6, cy + fh * 0.24)
    c.set_source_rgba(0.2, 0.22, 0.22, 0.6)
    c.set_line_width(5)
    c.stroke()

    # 叫ぶ口(縦に大きく開いた暗い穴)
    mx, my = cx, cy + fh * 0.52
    g3 = cairo.RadialGradient(mx, my, 5, mx, my, fw * 0.30)
    g3.add_color_stop_rgb(0, 0, 0, 0)
    g3.add_color_stop_rgb(0.7, 0.04, 0.0, 0.01)
    g3.add_color_stop_rgb(1, 0.35, 0.22, 0.24)
    _ellipse(c, mx, my, fw * 0.20, fh * 0.28)
    c.set_source(g3)
    c.fill()

    # 前髪(眉の高さでまっすぐ切りそろえ、毛先だけ少し乱れる)
    c.new_path()
    c.move_to(cx - fw * 1.1, cy - fh * 0.30)
    c.curve_to(cx - fw * 1.05, cy - fh * 1.1, cx - fw * 0.6, cy - fh * 1.3, cx, cy - fh * 1.3)
    c.curve_to(cx + fw * 0.6, cy - fh * 1.3, cx + fw * 1.05, cy - fh * 1.1, cx + fw * 1.1, cy - fh * 0.30)
    n = 40
    for k in range(n + 1):
        x = cx + fw * 1.1 - fw * 2.2 * k / n
        y = cy - fh * 0.36 + rng.uniform(-6, 10)
        c.line_to(x, y)
    c.close_path()
    c.set_source_rgb(0.015, 0.012, 0.012)
    c.fill()

    # 左右の垂れ髪(顔のふちを覆い、片側は頬までかかる)
    for sx, inner in ((-1, 0.70), (1, 0.55)):
        c.new_path()
        c.move_to(cx + sx * fw * 1.15, cy - fh * 0.5)
        c.curve_to(cx + sx * fw * inner, cy - fh * 0.3, cx + sx * fw * (inner - 0.05), cy + fh * 0.6,
                   cx + sx * fw * (inner + 0.1), h)
        c.line_to(cx + sx * fw * 1.5, h)
        c.close_path()
        c.set_source_rgb(0.015, 0.012, 0.012)
        c.fill()
    # 毛束の細い線でふちを自然に
    for _ in range(160):
        sx = rng.choice([-1, 1])
        inner = 0.70 if sx < 0 else 0.55
        x0 = cx + sx * fw * (inner + rng.uniform(-0.12, 0.05))
        c.move_to(x0, cy - fh * rng.uniform(0.3, 0.4))
        c.curve_to(x0, cy, x0 + rng.uniform(-15, 15), cy + fh * 0.6, x0 + rng.uniform(-30, 30), h)
        c.set_source_rgba(0.015, 0.012, 0.012, rng.uniform(0.5, 0.9))
        c.set_line_width(rng.uniform(1.5, 4))
        c.stroke()

    # ざらつき(古い映像のような粒子)と走査線
    surf.flush()
    arr = np.ndarray((h, w, 4), dtype=np.uint8, buffer=surf.get_data())
    grain = rng.normal(0, 12, (h, w, 1))
    rgb = arr[..., :3].astype(np.int16) + grain
    rgb[::4] -= 18
    arr[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    surf.mark_dirty()
    return surf


class GhostScare:
    def __init__(self, w, h, seed=0):
        self.w, self.h = w, h
        self.rng = np.random.default_rng(seed)
        self.face = _face(w, h, self.rng)

    def draw(self, surf, age):
        w, h = self.w, self.h
        c = cairo.Context(surf)
        # 出た瞬間に大きく → 少しずつ迫ってくる
        zoom = 1.35 - 0.25 * min(1, age / 0.08) + 0.12 * age
        shake = 28 * max(0.25, 1 - age / DURATION)
        dx, dy = self.rng.uniform(-shake, shake, 2)
        c.save()
        c.translate(w / 2 + dx, h * 0.47 + dy)
        c.scale(zoom, zoom)
        c.translate(-w / 2, -h * 0.47)
        c.set_source_surface(self.face, 0, 0)
        c.paint()
        c.restore()
        surf.flush()
        arr = np.ndarray((h, w, 4), dtype=np.uint8, buffer=surf.get_data())
        # 色ずれ(赤と青をずらす)
        off = int(4 + 5 * self.rng.random())
        arr[..., 2] = np.roll(arr[..., 2], off, axis=1)
        arr[..., 0] = np.roll(arr[..., 0], -off, axis=1)
        # 横方向のノイズ帯(映像が乱れる)
        for _ in range(int(self.rng.integers(3, 8))):
            y = int(self.rng.integers(0, h - 40))
            bh = int(self.rng.integers(8, 60))
            arr[y:y + bh] = np.roll(arr[y:y + bh], int(self.rng.integers(-80, 80)), axis=1)
        # 最初の一瞬だけ明るく光る(点滅は1回だけにして光過敏に配慮)
        if age < 0.05:
            arr[..., :3] = np.clip(arr[..., :3].astype(np.int16) * 1.5 + 30, 0, 255).astype(np.uint8)
        surf.mark_dirty()


def scream(sr, dur=DURATION + 0.15, seed=0):
    """叫び声:不協和にずらした複数のノコギリ波 + ノイズ + 低い衝撃音。"""
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    t = np.arange(n) / sr
    out = np.zeros(n)
    for ratio, amp in ((1.0, 1.0), (1.013, 0.8), (0.987, 0.8), (1.41, 0.6), (2.03, 0.35)):
        f = (650 + 520 * np.sqrt(t) + 70 * np.sin(2 * np.pi * 7.5 * t)) * ratio
        phase = np.cumsum(f) / sr
        out += amp * (2 * (phase % 1) - 1)
    nz = np.convolve(rng.standard_normal(n), np.ones(3) / 3, mode="same")
    out += 1.2 * nz
    env = np.minimum(1, t / 0.006) * np.where(t > dur - 0.35, np.maximum(0, (dur - t) / 0.35), 1)
    out = np.tanh(2.5 * out * env / 3.5)
    # ドーンという衝撃
    boom = np.sin(2 * np.pi * 48 * t) * np.exp(-t * 5) + 0.6 * rng.standard_normal(n) * np.exp(-t * 30)
    return np.clip(0.85 * out + 0.6 * boom, -1, 1)
