#!/usr/bin/env python3
"""ディープインパクト紹介ショート動画(縦型 1080x1920 / 30fps / 約21秒)を合成する。

参考動画(メンズファッション紹介)のテンポを再現:
  0-2.5s  顔アップ → 全身へズームアウト + タイトル
  2.5-14.5s アイテム6点を2秒ごとにポップイン + 下部テロップ(カメラは各アイテム側へ寄る)
  14.5-18.3s 全体を引きで見せて POINT まとめ
  18.3-21s 保存CTA + 次回予告

使い方:
  python3 make_deep_impact.py <素材ディレクトリ> <出力mp4>
素材ディレクトリには horse.png / item1.png〜item6.png を置く(Higgs Field で生成)。
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, DUR = 1080, 1920, 30, 21.0
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"

INK = (34, 30, 26)
ACCENT = (120, 98, 52)   # ゴールド寄りのブラウン(参考動画のオリーブ見出し色の置き換え)
SUB = (130, 124, 116)

TITLE = ["ディープインパクトが", "“英雄”と呼ばれる理由"]

# (見出し, 英字サブ, 一言テロップ, 配置中心x, 配置中心y, 表示サイズ)
ITEMS = [
    ("01 主な勝ち鞍", "TRIPLE CROWN 2005", "無敗で三冠を制覇", 905, 560, 330),
    ("02 通算成績", "14 RACES  12 WINS", "14戦12勝、G1は7勝", 170, 640, 300),
    ("03 セリ値", "SELECT SALE 2002", "当歳時に7000万円で落札", 180, 1010, 320),
    ("04 獲得賞金", "TOTAL EARNINGS", "14億5455万円を稼ぐ", 180, 1360, 330),
    ("05 歴代記録", "TENNO SHO (SPRING) 3:13.4", "天皇賞(春)で日本レコード", 905, 930, 300),
    ("06 種牡馬成績", "LEADING SIRE 2012-2022", "11年連続リーディングサイアー", 905, 1320, 340),
]
POINTS = ["① 無敗で三冠", "② 規格外のレコード", "③ 父としても頂点"]
CTA = ("保存して推し馬の参考に", "次回:オルフェーヴル")

T_ITEM0, T_STEP = 2.5, 2.0
T_POINT, T_CTA = 14.5, 18.3


def font(size):
    return ImageFont.truetype(FONT, size)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out_back(x):
    x = min(max(x, 0.0), 1.0)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def cutout(img, lo=10.0, hi=38.0):
    """単色クリーム背景を透過にする(影は半透明で残す)。"""
    rgb = np.asarray(img.convert("RGB")).astype(np.float32)
    corners = np.concatenate([rgb[:8, :8].reshape(-1, 3), rgb[:8, -8:].reshape(-1, 3),
                              rgb[-8:, :8].reshape(-1, 3), rgb[-8:, -8:].reshape(-1, 3)])
    bg = np.median(corners, axis=0)
    d = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    a = np.clip((d - lo) / (hi - lo), 0, 1)
    alpha = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    out = img.convert("RGBA")
    out.putalpha(alpha)
    return out, tuple(int(v) for v in bg)


def text_bold(draw, xy, text, size, fill, anchor="mm", stroke=1):
    draw.text(xy, text, font=font(size), fill=fill, anchor=anchor,
              stroke_width=stroke, stroke_fill=fill)


def rounded_panel(canvas, box, alpha=235, radius=26):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = box
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 8, x1, y1 + 8), radius, fill=(60, 50, 40, 40))
    sh = sh.filter(ImageFilter.GaussianBlur(12))
    canvas.alpha_composite(sh)
    d.rounded_rectangle(box, radius, fill=(255, 255, 255, alpha))
    canvas.alpha_composite(layer)


def with_opacity(img, op):
    if op >= 0.999:
        return img
    r, g, b, a = img.split()
    a = a.point(lambda v: int(v * op))
    return Image.merge("RGBA", (r, g, b, a))


def build_overlay(kind, payload):
    """画面固定のテロップレイヤー(RGBA)を作る。"""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    if kind == "title":
        rounded_panel(ov, (90, 120, W - 90, 380))
        text_bold(d, (W // 2, 200), TITLE[0], 66, INK, stroke=2)
        text_bold(d, (W // 2, 300), TITLE[1], 74, INK, stroke=2)
        d.rounded_rectangle((W // 2 - 260, 345, W // 2 + 260, 353), 4, fill=ACCENT + (255,))
    elif kind == "label":
        head, eng, line = payload
        rounded_panel(ov, (110, 1585, W - 110, 1800))
        text_bold(d, (W // 2, 1635), head, 46, ACCENT, stroke=1)
        d.text((W // 2, 1682), eng, font=font(26), fill=SUB, anchor="mm")
        text_bold(d, (W // 2, 1745), line, 54, INK, stroke=1)
    elif kind == "point":
        rounded_panel(ov, (150, 110, W - 150, 470))
        text_bold(d, (W // 2, 170), "POINT", 44, ACCENT, stroke=1)
        for i, p in enumerate(POINTS):
            text_bold(d, (W // 2, 260 + i * 80), p, 54, INK, stroke=1)
    elif kind == "cta":
        rounded_panel(ov, (110, 120, W - 110, 360))
        text_bold(d, (W // 2, 205), CTA[0], 66, INK, stroke=2)
        text_bold(d, (W // 2, 300), CTA[1], 44, ACCENT, stroke=1)
    return ov


def lerp(a, b, t):
    return a + (b - a) * t


def camera(t):
    """(zoom, center_x, center_y) を返す。world 座標 = 出力座標(1080x1920)。"""
    full = (1.0, W / 2, H / 2)
    head = (2.3, 640, 640)
    if t < 0.5:
        return head
    if t < 2.2:
        k = ease((t - 0.5) / 1.7)
        return tuple(lerp(a, b, k) for a, b in zip(head, full))
    if t < T_POINT:
        i = min(int((t - T_ITEM0) / T_STEP), 5) if t >= T_ITEM0 else -1
        target = full
        if i >= 0:
            _, _, _, ix, iy, _ = ITEMS[i]
            target = (1.07, lerp(W / 2, ix, 0.2), lerp(H / 2, iy, 0.2))
        prev = full
        if i >= 1:
            _, _, _, px, py, _ = ITEMS[i - 1]
            prev = (1.07, lerp(W / 2, px, 0.2), lerp(H / 2, py, 0.2))
        start = T_ITEM0 + max(i, 0) * T_STEP
        k = ease((t - start) / 0.6)
        return tuple(lerp(a, b, k) for a, b in zip(prev, target))
    # 引きの全体図
    _, _, _, px, py, _ = ITEMS[5]
    last = (1.07, lerp(W / 2, px, 0.2), lerp(H / 2, py, 0.2))
    if t < T_CTA:
        k = ease((t - T_POINT) / 0.8)
        wide = (0.80, W / 2, H / 2)
        return tuple(lerp(a, b, k) for a, b in zip(last, wide))
    k = ease((t - T_CTA) / (DUR - T_CTA))
    return (lerp(0.80, 0.86, k), W / 2, lerp(H / 2, H / 2 - 60, k))


def main():
    src = Path(sys.argv[1])
    out = sys.argv[2]

    horse_raw = Image.open(src / "horse.png")
    horse, bg = cutout(horse_raw, lo=8, hi=30)
    hs = 1180 / horse.height
    horse = horse.resize((int(horse.width * hs), 1180), Image.LANCZOS)
    hx, hy = (W - horse.width) // 2 + 10, 390

    items = []
    for n in range(1, 7):
        im, _ = cutout(Image.open(src / f"item{n}.png"))
        size = ITEMS[n - 1][5]
        bbox = im.getbbox()
        im = im.crop(bbox)
        s = size / max(im.size)
        items.append(im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS))

    base = Image.new("RGBA", (W, H), bg + (255,))
    base.alpha_composite(horse, (hx, hy))

    overlays = {"title": build_overlay("title", None),
                "point": build_overlay("point", None),
                "cta": build_overlay("cta", None)}
    labels = [build_overlay("label", it[:3]) for it in ITEMS]

    ff = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "18",
        "-movflags", "+faststart", out], stdin=subprocess.PIPE)

    nframes = int(DUR * FPS)
    for f in range(nframes):
        t = f / FPS
        world = base.copy()
        for i, im in enumerate(items):
            t0 = T_ITEM0 + i * T_STEP
            if t < t0:
                continue
            p = (t - t0) / 0.35
            sc = 0.55 + 0.45 * ease_out_back(p)
            op = ease(p * 1.6)
            w2, h2 = max(1, int(im.width * sc)), max(1, int(im.height * sc))
            im2 = with_opacity(im.resize((w2, h2), Image.BILINEAR), op)
            cx, cy = ITEMS[i][3], ITEMS[i][4]
            world.alpha_composite(im2, (int(cx - w2 / 2), int(cy - h2 / 2)))

        z, cx, cy = camera(t)
        cw, ch = W / z, H / z
        x0, y0 = cx - cw / 2, cy - ch / 2
        if z >= 1.0:
            x0 = min(max(x0, 0), W - cw)
            y0 = min(max(y0, 0), H - ch)
            frame = world.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
        else:
            # 引き(zoom<1)は背景色で余白を埋める
            small = world.resize((int(W * z), int(H * z)), Image.BICUBIC)
            frame = Image.new("RGBA", (W, H), bg + (255,))
            frame.alpha_composite(small, (int((W - small.width) / 2 - (cx - W / 2) * z),
                                          int((H - small.height) / 2 - (cy - H / 2) * z)))

        def fade(start, end, fin=0.25, fout=0.2):
            if t < start or t >= end:
                return 0.0
            return min(1.0, (t - start) / fin, (end - t) / fout)

        op = fade(0.25, T_ITEM0)
        if op > 0:
            frame.alpha_composite(with_opacity(overlays["title"], op))
        for i in range(6):
            t0 = T_ITEM0 + i * T_STEP + 0.15
            t1 = T_ITEM0 + (i + 1) * T_STEP + 0.1 if i < 5 else T_POINT
            op = fade(t0, t1, 0.2, 0.15)
            if op > 0:
                frame.alpha_composite(with_opacity(labels[i], op))
        op = fade(T_POINT + 0.4, T_CTA)
        if op > 0:
            frame.alpha_composite(with_opacity(overlays["point"], op))
        op = fade(T_CTA + 0.1, DUR + 1)
        if op > 0:
            frame.alpha_composite(with_opacity(overlays["cta"], op))

        ff.stdin.write(frame.convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    main()
