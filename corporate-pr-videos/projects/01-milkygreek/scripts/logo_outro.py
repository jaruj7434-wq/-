"""milkygreek ロゴのアウトロアニメーションをローカルで描画する(Higgs Field のクレジット不使用)。

真っ白な画面 → 中央に青い点 → 横に伸びて細いライン → 上段「milky」がラインの上からせり上がり、
下段「greek」がラインの下へ降りて現れる → ラインが消えてロゴだけが残り、ゆっくりズーム。

使い方:
    python3 -I logo_outro.py <ロゴ画像(白地)> <出力.mp4>
"""
import subprocess
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

W, H, FPS, DUR = 1080, 1920, 30, 4.5
LOGO_W = 760
BLUE = (42, 98, 152)


def ease_out_expo(t):
    t = min(max(t, 0.0), 1.0)
    return 1.0 if t == 1 else 1 - 2 ** (-10 * t)


def ease_in_out(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def prog(t, start, end):
    return min(max((t - start) / (end - start), 0.0), 1.0)


def load_logo(path):
    """白地のロゴ画像から、ロゴ色で塗った RGBA と上段/下段のマスクを作る。"""
    img = Image.open(path).convert("L")
    scale = LOGO_W / img.width
    img = img.resize((LOGO_W, round(img.height * scale)), Image.LANCZOS)
    lum = np.asarray(img).astype(np.float32)
    alpha = np.clip((240 - lum) / (240 - 115), 0, 1)

    # 連結成分で文字ごとに分け、重心の高さで上段/下段に振り分ける
    mask = alpha > 0.35
    h, w = mask.shape
    label = np.zeros((h, w), np.int32)
    centers = {}
    n = 0
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not label[y, x]:
                n += 1
                q = deque([(y, x)])
                label[y, x] = n
                ys = []
                while q:
                    cy, cx = q.popleft()
                    ys.append(cy)
                    for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not label[ny, nx]:
                            label[ny, nx] = n
                            q.append((ny, nx))
                centers[n] = sum(ys) / len(ys)
    mid = h / 2
    top_ids = [k for k, c in centers.items() if c < mid]
    top = np.isin(label, top_ids)
    # アンチエイリアス部分(mask 外)も近い方の段に含める
    grown = Image.fromarray((top * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))
    top_soft = (np.asarray(grown) > 0) & (alpha > 0)
    bottom_soft = (alpha > 0) & ~top_soft

    def layer(sel):
        a = np.where(sel, alpha, 0)
        rgba = np.zeros((h, w, 4), np.uint8)
        rgba[..., 0], rgba[..., 1], rgba[..., 2] = BLUE
        rgba[..., 3] = (a * 255).astype(np.uint8)
        return Image.fromarray(rgba, "RGBA")

    ys_top = np.where(top_soft.any(1))[0]
    ys_bot = np.where(bottom_soft.any(1))[0]
    return layer(top_soft), layer(bottom_soft), (ys_top.min(), ys_top.max()), (ys_bot.min(), ys_bot.max())


def render(logo_path, out_path):
    top, bottom, (t0, t1), (b0, b1) = load_logo(logo_path)
    lw, lh = top.size
    ox, oy = (W - lw) // 2, (H - lh) // 2
    line_y = oy + (t1 + b0) // 2  # 上段と下段のあいだ

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo",
         "-t", str(DUR), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16",
         "-c:a", "aac", "-shortest", out_path],
        stdin=subprocess.PIPE)

    for i in range(int(DUR * FPS)):
        t = i / FPS
        frame = Image.new("RGB", (W, H), "white")
        canvas = Image.new("RGBA", (W, H), (255, 255, 255, 0))

        # 1) 点 → ライン(0.4〜0.95s で伸び、1.7〜2.2s で消える)
        grow = ease_out_expo(prog(t, 0.4, 0.95))
        fade = 1 - ease_in_out(prog(t, 1.7, 2.2))
        if t >= 0.35 and fade > 0:
            half = max(4, int(lw * 0.55 * grow))
            thick = 4
            a = int(255 * fade * prog(t, 0.35, 0.45))
            bar = Image.new("RGBA", (half * 2, thick), BLUE + (a,))
            canvas.alpha_composite(bar, (W // 2 - half, line_y - thick // 2))

        # 2) 上段はラインの上へせり上がる / 下段はラインの下へ降りる(ライン位置でクリップ)
        for img, start, direction in ((top, 0.85, -1), (bottom, 1.1, 1)):
            p = ease_out_expo(prog(t, start, start + 0.9))
            if p <= 0:
                continue
            travel = lh // 2
            dy = int(direction * -(1 - p) * travel)
            blur = (1 - p) * 6
            layer = img.filter(ImageFilter.GaussianBlur(blur)) if blur > 0.3 else img
            full = Image.new("RGBA", (W, H), (255, 255, 255, 0))
            full.alpha_composite(layer, (ox, oy + dy))
            arr = np.asarray(full).copy()
            # ライン外側は最初は隠し、出切る直前にふわっと見せる(y の払い・k の縦線が急に出ないように)
            keep = ease_in_out(prog(p, 0.75, 1.0))
            if direction < 0:
                arr[line_y:, :, 3] = (arr[line_y:, :, 3] * keep).astype(np.uint8)
            else:
                arr[:line_y, :, 3] = (arr[:line_y, :, 3] * keep).astype(np.uint8)
            canvas.alpha_composite(Image.fromarray(arr, "RGBA"))

        # 3) 全体をゆっくりズーム
        z = 1 + 0.035 * ease_in_out(prog(t, 1.8, DUR))
        if z > 1.0005:
            zw, zh = int(W * z), int(H * z)
            canvas = canvas.resize((zw, zh), Image.LANCZOS).crop(
                ((zw - W) // 2, (zh - H) // 2, (zw - W) // 2 + W, (zh - H) // 2 + H))

        frame.paste(canvas, (0, 0), canvas)
        ff.stdin.write(frame.tobytes())

    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
