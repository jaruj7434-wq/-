"""『デブの名は。』の文字カード・タイトルを作る(参考予告の淡い水色とピンクの背景+黒い明朝体)
usage: python3 text_cards.py OUTDIR [--stills]
"""
import sys, os, math, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 24
SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-%s.ttc"
INK = (26, 26, 32)
def font(sz, w="Medium"): return ImageFont.truetype(SERIF % w, sz, index=0)

# 参考カードの 3x3 の色(実測)
GRID = np.array([[[220,217,232],[232,243,249],[185,214,232]],
                 [[229,210,239],[240,241,250],[211,228,242]],
                 [[231,201,232],[248,234,250],[219,215,231]]], np.float32)
def base_bg():
    g = Image.fromarray(GRID.astype(np.uint8)).resize((W, H), Image.BICUBIC)
    return np.array(g.filter(ImageFilter.GaussianBlur(60))).astype(np.float32)
BASE = base_bg()
rng = np.random.default_rng(7)
BOKEH = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(20, 70), rng.uniform(0.03, 0.08),
          rng.uniform(-18, 18), rng.uniform(-10, 10)) for _ in range(26)]
def background(t):
    img = Image.fromarray(np.clip(BASE, 0, 255).astype(np.uint8))
    lay = Image.new("L", (W, H), 0); d = ImageDraw.Draw(lay)
    for x, y, r, a, vx, vy in BOKEH:
        cx, cy = x + vx * t, y + vy * t
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(255 * a))
    lay = lay.filter(ImageFilter.GaussianBlur(10))
    img.paste(Image.new("RGB", (W, H), (255, 255, 255)), (0, 0), lay)
    return img

def htext(d, text, cx, top, f, pitch=None, fill=INK):
    """横書き。pitch を指定すると1文字ずつ等間隔に置く"""
    if pitch is None:
        w = d.textlength(text, font=f); d.text((cx - w / 2, top), text, font=f, fill=fill); return
    n = len(text); x0 = cx - pitch * n / 2
    for i, ch in enumerate(text):
        cw = d.textlength(ch, font=f); d.text((x0 + i * pitch + (pitch - cw) / 2, top), ch, font=f, fill=fill)

VROT = set("ー")          # 縦書きで回す文字
VSMALL = set("、。")      # 縦書きで右上に寄せる文字
def vtext(img, text, cx, top, size, pitch, fill=INK, w="Medium"):
    f = font(size, w)
    for i, ch in enumerate(text):
        y = top + i * pitch
        tile = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0)); td = ImageDraw.Draw(tile)
        cw = td.textlength(ch, font=f)
        td.text((size - cw / 2, size / 2), ch, font=f, fill=fill + (255,))
        if ch in VROT: tile = tile.rotate(-90, resample=Image.BICUBIC)
        dx, dy = (int(size * 0.62), -int(size * 0.62)) if ch in VSMALL else (0, 0)
        img.paste(tile, (int(cx - size + dx), int(y - size / 2 + dy)), tile)

def card_still(kind, t=0.0):
    img = background(t); d = ImageDraw.Draw(img)
    if kind == "c1":   # 参考 15.02-16.27:小さい行 + 大きい名前 + 監督最新作
        htext(d, "『秒速5キロカロリー』『言の葉の丼』", 945, 276, font(34, "Bold"))
        htext(d, "マルコメ", 945, 368, font(176, "SemiBold"))
        htext(d, "監督最新作", 945, 640, font(132, "SemiBold"))
    elif kind == "c2": # 参考 24.52-26.44:横書き2行
        htext(d, "千年ぶりの食べ放題の", 950, 352, font(112), pitch=112)
        htext(d, "来訪を控えた、日本。", 950, 571, font(112), pitch=112)
    elif kind == "c3": # 参考 54.10-55.14:縦書き2列(右から)
        vtext(img, "痩せることのない", 1055, 200, 92, 99)
        vtext(img, "二人の出逢い。", 828, 314, 92, 99)
    elif kind == "c4": # 参考 63.31-64.11:縦書き2列
        vtext(img, "動き出した、", 1065, 108, 90, 96)
        vtext(img, "奇跡のリバウンド。", 855, 108, 90, 96)
    elif kind == "end":# 参考 89.38-91.09:キャッチコピー + 公開日 + クレジット
        htext(d, "この秋、日本中がおかわりする。", 966, 128, font(92), pitch=103)
        date = Image.new("L", (W, H), 0); dd = ImageDraw.Draw(date)
        htext(dd, "8·29 焼肉の日", 960, 300, font(190, "SemiBold"), fill=255)
        htext(dd, "全国ロードショー", 960, 545, font(92, "SemiBold"), fill=255)
        grad = np.zeros((H, W, 3), np.float32); xs = np.linspace(0, 1, W)[None, :, None]
        grad[:] = np.array([110, 150, 215]) * (1 - xs) + np.array([205, 130, 200]) * xs
        img.paste(Image.fromarray(grad.astype(np.uint8)), (0, 0), date)
        f = font(30, "Bold"); f2 = font(22, "Bold")
        for i, line in enumerate(["監督/脚本 マルコメ",
                                  "作画監督 油野 揚男　　キャラクターデザイン 満腹 太",
                                  "慶太　　ふとみ",
                                  "音楽 ハラペコーズ"]):
            htext(d, line, 960, 740 + i * 52, f)
        htext(d, "制作 カロリー・ウェーブ・フィルム　　©「デブの名は。」製作委員会", 960, 968, f2)
    return img

def title_frame(t, dur):
    """白く飛んだ画面から、ぼけた題字がはっきりしてくる。ピンクと水色の糸が流れる"""
    img = Image.blend(background(t), Image.new("RGB", (W, H), (252, 250, 255)), 0.45)
    th = Image.new("RGBA", (W, H), (0, 0, 0, 0)); td = ImageDraw.Draw(th)
    for k, (col, x0, x1, ph, wd) in enumerate([((235,105,205),-200,1500,0.0,6),((185,150,240),300,2100,1.4,5),
                                                ((245,140,215),-400,1200,2.3,4),((160,175,240),600,2300,3.1,5)]):
        pts = []
        for i in range(70):
            u = i / 69
            x = x0 + (x1 - x0) * u + 40 * math.sin(t * 1.3 + ph)
            y = -120 + (H + 240) * u + 90 * math.sin(u * math.pi * 2.2 + ph + t * 1.6)
            pts.append((x, y))
        td.line(pts, fill=col + (235,), width=wd, joint="curve")
    glow = th.filter(ImageFilter.GaussianBlur(10))
    img.paste(glow, (0, 0), glow); th = th.filter(ImageFilter.GaussianBlur(1.5)); img.paste(th, (0, 0), th)
    txt = Image.new("L", (W, H), 0); dd = ImageDraw.Draw(txt)
    htext(dd, "デブの名は。", 940, 382, font(170, "Regular"), pitch=212, fill=255)
    htext(dd, "your weight.", 940, 612, ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26), pitch=44, fill=255)
    p = min(1.0, t / 0.7); blur = 14 * (1 - p) ** 2
    if blur > 0.3: txt = txt.filter(ImageFilter.GaussianBlur(blur))
    txt = txt.point(lambda v: int(v * (0.25 + 0.75 * p)))
    grad = np.zeros((H, W, 3), np.float32); xs = np.linspace(0, 1, W)[None, :, None]
    grad[:] = np.array([120, 60, 115]) * (1 - xs) + np.array([80, 95, 130]) * xs
    img.paste(Image.fromarray(grad.astype(np.uint8)), (0, 0), txt)
    if t < 0.3:  # 白から入る
        a = 1 - t / 0.3; img = Image.blend(img, Image.new("RGB", (W, H), (255, 255, 255)), a)
    return img

CARDS = [("c1", 1.25), ("c2", 1.92), ("c3", 1.04), ("c4", 0.80), ("title", 2.38), ("end", 1.71)]

def write(out, kind, dur):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-vf", "scale=1280:720",
                          "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    n = round(dur * FPS)
    for i in range(n):
        t = i / FPS
        im = title_frame(t, dur) if kind == "title" else card_still(kind, t)
        p.stdin.write(np.array(im.convert("RGB")).tobytes())
    p.stdin.close(); p.wait()

if __name__ == "__main__":
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    if "--stills" in sys.argv:
        for k, d in CARDS:
            (title_frame(1.2, d) if k == "title" else card_still(k, 0.5)).save(f"{out}/{k}.png")
    else:
        for k, d in CARDS: write(f"{out}/card_{k}.mp4", k, d)
