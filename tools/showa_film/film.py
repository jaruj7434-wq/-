#!/usr/bin/env python3
"""昭和16mmフィルム風 仕上げツール

EDL(JSON)に書いたカット・タイトルカード・テロップ・音声から、
  - master_4x3.mp4   (1440x1080, 24fps, モノラル音声)
  - vertical_9x16.mp4 (1080x1920, 4:3を中央に置き上下にシリーズ名と字幕)
を書き出す。

使い方:
  python3 tools/showa_film/film.py prompts/showa_pr/ep01_edl.json
  python3 tools/showa_film/film.py edl.json --preview   # 低画質で速く確認

必要: ffmpeg, numpy, Pillow, フォント(tools/showa_film/fetch_fonts.sh で取得)
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
FONTS = {
    "mincho": os.path.join(FONT_DIR, "ShipporiMinchoB1-ExtraBold.ttf"),
    "mincho_regular": os.path.join(FONT_DIR, "ShipporiMinchoB1-Regular.ttf"),
    "gothic": os.path.join(FONT_DIR, "DelaGothicOne-Regular.ttf"),
}

# 作業解像度(ゆらぎ用に少し大きく取る) → 中央 720x540 を切り出し → 1440x1080 に拡大
PAD_W, PAD_H = 752, 564
WORK_W, WORK_H = 720, 540
OUT_W, OUT_H = 1440, 1080

DEFAULT_LOOK = {
    "mode": "color",        # color(色あせたカラーフィルム) / mono(白黒)
    "saturation": 0.62,
    "lift": [0.075, 0.06, 0.08],     # 黒の浮き(R,G,B)
    "gain": [0.97, 0.91, 0.80],      # 白の上限(R,G,B) → 青が抜けて赤紫寄りに
    "gamma": [0.94, 1.0, 1.07],
    "grain": 0.075,          # 粒子の強さ
    "grain_size": 1.6,       # 粒子の大きさ(大きいほど粗い)
    "flicker": 0.035,        # 明るさのゆらぎ
    "weave": 1.4,            # 画面のゆれ(px, 720幅基準)
    "dust_per_frame": 1.3,   # ゴミの平均個数/コマ
    "hair_prob": 0.012,      # 毛が映りこむ確率/コマ
    "scratch_prob": 0.02,    # 縦傷が始まる確率/コマ
    "vignette": 0.38,
    "halation": 0.18,        # ハイライトのにじみ
    "softness": 0.55,        # レンズの甘さ(ぼかし半径)
    "seed": 1962,
}


def run(cmd, **kw):
    print("+", " ".join(cmd[:6]), "..." if len(cmd) > 6 else "", file=sys.stderr)
    if os.environ.get("SHOWA_DEBUG"):
        print("FULL:", cmd, file=sys.stderr)
    subprocess.run(cmd, check=True, **kw)


def font(name, size):
    path = FONTS[name]
    if not os.path.exists(path):
        sys.exit(f"フォントがありません: {path}\n  bash tools/showa_film/fetch_fonts.sh を実行してください")
    return ImageFont.truetype(path, size)


# ---------------------------------------------------------------- 文字の描画
def draw_text_center(draw, cx, y, text, fnt, fill, shadow=None, spacing=0, stroke=0):
    """1行を中央揃えで描く。spacing は字間(px)、stroke は縁取りの太さ(縁の色は shadow)"""
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        if shadow:
            for dx, dy in ((2, 2), (1, 2), (2, 1)):
                draw.text((x + dx, y + dy), ch, font=fnt, fill=shadow)
        if stroke and shadow:
            draw.text((x, y), ch, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=shadow)
        else:
            draw.text((x, y), ch, font=fnt, fill=fill)
        x += w + spacing


CREAM = (248, 238, 214)
INK = (18, 14, 12)


def render_card(spec, w=PAD_W, h=PAD_H):
    """タイトルカード/エンドカードの画像を作る"""
    bg = tuple(spec.get("bg", (22, 20, 30)))
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    cx = w / 2
    # 飾り枠(二重線)
    m = 46
    d.rectangle([m, m, w - m, h - m], outline=CREAM, width=3)
    d.rectangle([m + 9, m + 9, w - m - 9, h - m - 9], outline=CREAM, width=1)
    for line in spec["lines"]:
        fnt = font(line.get("font", "mincho"), line.get("size", 40))
        draw_text_center(d, cx, line["y"], line["text"], fnt, CREAM,
                         spacing=line.get("spacing", 4))
        if line.get("rule"):
            ry = line["y"] + line.get("size", 40) + 14
            d.line([cx - 150, ry, cx + 150, ry], fill=CREAM, width=2)
    if spec.get("emblem"):
        draw_emblem(d, cx, spec["emblem"]["y"], spec["emblem"].get("r", 34))
    return img


def draw_emblem(d, cx, cy, r):
    """架空の社章:二重丸の中に三本線の日の出(実在の社章に似せない簡単な図形)"""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=CREAM, width=4)
    d.ellipse([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8], outline=CREAM, width=2)
    d.pieslice([cx - r * 0.5, cy - r * 0.25, cx + r * 0.5, cy + r * 0.75], 180, 360, fill=CREAM)
    for i, a in enumerate((-50, -90, -130)):
        rad = math.radians(a)
        d.line([cx + math.cos(rad) * r * 0.62, cy + r * 0.25 + math.sin(rad) * r * 0.62,
                cx + math.cos(rad) * r * 0.8, cy + r * 0.25 + math.sin(rad) * r * 0.8],
               fill=CREAM, width=3)


def render_telop(text, size=40, pos="lower", fnt_name="mincho", color=None, xy=None,
                 stroke=True, angle=0):
    """画面内テロップ(RGBA, 作業解像度)
    - 既定:クリーム色の明朝+黒い縁取り(昭和の映画字幕風)
    - fnt_name: mincho / gothic、color: [R,G,B]
    - xy: [x, y] を画面の割合(0〜1)で指定すると、その位置を中心に置く(フリップや封筒の文字用)
    - stroke=False で縁取りなし(紙に書いた文字用)、angle で傾ける
    """
    fill = tuple(color) if color else CREAM
    layer = Image.new("RGBA", (PAD_W, PAD_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    fnt = font(fnt_name, size)
    lines = text.split("\n")
    line_h = size * 1.35
    if xy:
        y0 = xy[1] * PAD_H - line_h * len(lines) / 2
        cx = xy[0] * PAD_W
    else:
        y0 = PAD_H - 78 - line_h * len(lines) if pos == "lower" else 70
        cx = PAD_W / 2
    for i, ln in enumerate(lines):
        if stroke:
            draw_text_center(d, cx, y0 + i * line_h, ln, fnt, fill + (255,),
                             shadow=INK + (235,), spacing=3, stroke=2)
        else:
            draw_text_center(d, cx, y0 + i * line_h, ln, fnt, fill + (235,), spacing=2)
    if angle:
        layer = layer.rotate(angle, resample=Image.BICUBIC, center=(cx, y0 + line_h * len(lines) / 2))
    return layer


# ---------------------------------------------------------------- 素材の正規化
def normalize_clip(src, t_in, dur, out, fps, preview):
    """任意の動画 → 4:3(PAD_W x PAD_H)、指定fps、無音、指定尺"""
    vf = (f"fps={fps},scale={PAD_W}:{PAD_H}:force_original_aspect_ratio=increase,"
          f"crop={PAD_W}:{PAD_H},setsar=1,format=rgb24")
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", str(t_in), "-i", src, "-t", str(dur),
           "-vf", vf, "-an"]
    cmd += ["-c:v", "libx264", "-crf", "16" if not preview else "26", "-preset", "veryfast",
            "-pix_fmt", "yuv444p", out]
    run(cmd)


def still_clip(img, dur, out, fps, preview):
    tmp = out + ".png"
    img.save(tmp)
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(fps), "-i", tmp,
         "-t", str(dur), "-vf", f"fps={fps},format=rgb24",
         "-c:v", "libx264", "-crf", "16" if not preview else "26", "-preset", "veryfast",
         "-pix_fmt", "yuv444p", out])


# ---------------------------------------------------------------- フィルム加工
def smooth_noise(rng, n, smooth):
    x = rng.standard_normal(n + smooth * 4)
    k = np.hanning(smooth * 2 + 1)
    k /= k.sum()
    y = np.convolve(x, k, mode="same")[smooth * 2: smooth * 2 + n]
    return y / (y.std() + 1e-6)


class FilmLook:
    def __init__(self, look, n_frames):
        self.L = {**DEFAULT_LOOK, **(look or {})}
        L = self.L
        self.rng = np.random.default_rng(L["seed"])
        rng = self.rng
        n = n_frames
        # ゆらぎ・ゆれは、ゆっくりした成分 + コマごとの細かい成分
        self.flick = 1 + L["flicker"] * (0.6 * smooth_noise(rng, n, 3) + 0.4 * rng.standard_normal(n))
        self.dx = L["weave"] * (0.7 * smooth_noise(rng, n, 6) + 0.35 * rng.standard_normal(n))
        self.dy = L["weave"] * 1.3 * (0.7 * smooth_noise(rng, n, 5) + 0.35 * rng.standard_normal(n))
        yy, xx = np.mgrid[0:WORK_H, 0:WORK_W].astype(np.float32)
        r = np.sqrt(((xx - WORK_W / 2) / (WORK_W / 2)) ** 2 + ((yy - WORK_H / 2) / (WORK_H / 2)) ** 2)
        self.vig = np.clip(1 - L["vignette"] * (r / 1.41) ** 2.2, 0, 1)[..., None]
        # 映写窓(角の丸い枠)
        gate = Image.new("L", (WORK_W, WORK_H), 0)
        ImageDraw.Draw(gate).rounded_rectangle([3, 2, WORK_W - 4, WORK_H - 3], radius=18, fill=255)
        self.gate = (np.asarray(gate.filter(ImageFilter.GaussianBlur(2.2)), np.float32) / 255)[..., None]
        self.scratches = []  # [x, 残りコマ, 濃さ, 太さ, 揺れ速度]
        self.hair = None

    def color(self, img):
        L = self.L
        lum = img @ np.array([0.299, 0.587, 0.114], np.float32)
        if L["mode"] == "mono":
            base = lum[..., None]
            img = np.concatenate([base * 1.0, base * 0.985, base * 0.955], axis=2)
            lift, gain, gamma = [0.06] * 3, [0.95, 0.94, 0.92], [1.0, 1.0, 1.02]
        else:
            img = lum[..., None] + (img - lum[..., None]) * L["saturation"]
            lift, gain, gamma = L["lift"], L["gain"], L["gamma"]
        img = np.clip(img, 0, 1)
        out = np.empty_like(img)
        for c in range(3):
            out[..., c] = lift[c] + (gain[c] - lift[c]) * np.power(img[..., c], gamma[c])
        return out

    def process(self, i, frame):
        """frame: uint8 (PAD_H, PAD_W, 3) → uint8 (WORK_H, WORK_W, 3)"""
        L, rng = self.L, self.rng
        im = Image.fromarray(frame)
        if L["softness"] > 0:
            im = im.filter(ImageFilter.GaussianBlur(L["softness"]))
        # ゆれ(サブピクセル移動して中央を切り出す)
        ox = (PAD_W - WORK_W) / 2 + self.dx[i]
        oy = (PAD_H - WORK_H) / 2 + self.dy[i]
        im = im.transform((WORK_W, WORK_H), Image.AFFINE, (1, 0, ox, 0, 1, oy), resample=Image.BILINEAR)
        img = np.asarray(im, np.float32) / 255

        # ハレーション(明部のにじみ、少し赤み)
        if L["halation"] > 0:
            hi = np.clip((img.mean(axis=2) - 0.72) / 0.28, 0, 1)
            small = Image.fromarray((hi * 255).astype(np.uint8)).resize((WORK_W // 4, WORK_H // 4))
            glow = np.asarray(small.filter(ImageFilter.GaussianBlur(5)).resize((WORK_W, WORK_H)), np.float32) / 255
            img = img + L["halation"] * glow[..., None] * np.array([1.0, 0.75, 0.55], np.float32)

        img = self.color(np.clip(img, 0, 1))
        img *= self.flick[i]

        # 粒子(低解像度のノイズを拡大して粒を粗くし、中間調ほど強く)
        gs = L["grain_size"]
        gh, gw = int(WORK_H / gs), int(WORK_W / gs)
        g = rng.standard_normal((gh, gw, 3)).astype(np.float32)
        g = 0.75 * g[..., :1] + 0.25 * g  # 主に輝度の粒、少しだけ色の粒
        g = np.asarray(Image.fromarray(((g * 0.18 + 0.5).clip(0, 1) * 255).astype(np.uint8))
                       .resize((WORK_W, WORK_H), Image.BILINEAR), np.float32) / 255
        g = (g - 0.5) / 0.18
        lum = img.mean(axis=2, keepdims=True)
        img = img + L["grain"] * g * (0.35 + 2.2 * lum * (1 - lum))

        img = self.damage(img)
        img = img * self.vig * self.gate
        return (np.clip(img, 0, 1) * 255).astype(np.uint8)

    def damage(self, img):
        """ゴミ・毛・縦傷"""
        L, rng = self.L, self.rng
        mask_dark = Image.new("L", (WORK_W, WORK_H), 0)
        mask_lite = Image.new("L", (WORK_W, WORK_H), 0)
        dd, dl = ImageDraw.Draw(mask_dark), ImageDraw.Draw(mask_lite)
        for _ in range(rng.poisson(L["dust_per_frame"])):
            x, y = rng.uniform(0, WORK_W), rng.uniform(0, WORK_H)
            r = rng.uniform(0.6, 2.6)
            pts = [(x + rng.uniform(-r, r) * 1.6, y + rng.uniform(-r, r) * 1.6) for _ in range(5)]
            (dd if rng.random() < 0.7 else dl).polygon(pts, fill=int(rng.uniform(150, 255)))
        if self.hair is None and rng.random() < L["hair_prob"]:
            x, y = rng.uniform(40, WORK_W - 40), rng.uniform(40, WORK_H - 40)
            pts = [(x, y)]
            ang = rng.uniform(0, 2 * math.pi)
            for _ in range(14):
                ang += rng.uniform(-0.5, 0.5)
                x += math.cos(ang) * 6
                y += math.sin(ang) * 6
                pts.append((x, y))
            self.hair = [pts, int(rng.integers(2, 6))]
        if self.hair:
            dd.line(self.hair[0], fill=220, width=1)
            self.hair[1] -= 1
            if self.hair[1] <= 0:
                self.hair = None
        if rng.random() < L["scratch_prob"]:
            self.scratches.append([rng.uniform(20, WORK_W - 20), int(rng.integers(8, 60)),
                                   rng.uniform(0.25, 0.7), rng.choice([1, 1, 2]), rng.uniform(-0.4, 0.4)])
        alive = []
        for s in self.scratches:
            s[0] += s[4] + rng.normal(0, 0.25)
            if rng.random() > 0.12:  # ときどき途切れる
                y0 = 0 if rng.random() < 0.8 else rng.uniform(0, WORK_H * 0.6)
                dl.line([s[0], y0, s[0] + rng.normal(0, 0.4), WORK_H], fill=int(255 * s[2]), width=int(s[3]))
            s[1] -= 1
            if s[1] > 0:
                alive.append(s)
        self.scratches = alive
        md = np.asarray(mask_dark.filter(ImageFilter.GaussianBlur(0.6)), np.float32)[..., None] / 255
        ml = np.asarray(mask_lite.filter(ImageFilter.GaussianBlur(0.5)), np.float32)[..., None] / 255
        img = img * (1 - 0.92 * md)
        img = img + (0.95 - img) * ml * 0.8
        return img


# ---------------------------------------------------------------- 音
def projector_noise(path, dur, sr=48000, seed=7):
    """映写機の回転音(24Hzのカタカタ)+ ヒスノイズ + プチプチ"""
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    t = np.arange(n) / sr
    hiss = rng.standard_normal(n) * 0.012
    # カタカタ:24Hzの短いパルスを帯域通過っぽく
    clicks = np.zeros(n)
    period = sr / 24
    for k in range(int(dur * 24)):
        p = int(k * period + rng.normal(0, 20))
        if 0 <= p < n - 200:
            clicks[p:p + 200] += np.exp(-np.arange(200) / 30) * rng.uniform(0.6, 1.0) * np.sin(np.arange(200) * 0.9)
    rumble = 0.02 * np.sin(2 * np.pi * 24 * t) * (1 + 0.3 * np.sin(2 * np.pi * 0.3 * t))
    pops = np.zeros(n)
    for p in rng.integers(0, n - 50, int(dur * 3)):
        pops[p:p + 40] += rng.uniform(-1, 1) * np.exp(-np.arange(40) / 6) * 0.5
    y = hiss + clicks * 0.05 + rumble + pops * 0.3
    y = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(y.tobytes())


# 昭和の光学録音っぽく:帯域を狭め、中域を持ち上げ、ゆっくりした音程ゆれ(ワウ)と細かいゆれ(フラッター)
RETRO_VOICE = ("highpass=f=220,lowpass=f=3600,equalizer=f=1600:t=q:w=1.2:g=5,"
               "acompressor=threshold=0.1:ratio=4:attack=5:release=120,"
               "vibrato=f=0.7:d=0.012,vibrato=f=9:d=0.006,asoftclip=type=tanh")
RETRO_MUSIC = ("highpass=f=160,lowpass=f=4800,equalizer=f=2500:t=q:w=1:g=3,"
               "vibrato=f=0.5:d=0.02,vibrato=f=8:d=0.008,asoftclip=type=tanh")


def build_audio(edl, total, tmp, base):
    A = edl.get("audio", {})
    inputs, chains, labels = [], [], []
    noise = os.path.join(tmp, "projector.wav")
    projector_noise(noise, total + 1)
    inputs += ["-i", noise]
    chains.append(f"[0:a]volume={A.get('projector_gain', 0.55)}[pj]")
    labels.append("[pj]")
    idx = 1
    for item in A.get("tracks", []):
        p = os.path.join(base, item["src"])
        inputs += ["-i", p]
        delay = int(item.get("start", 0) * 1000)
        chain = RETRO_VOICE if item.get("kind") == "voice" else RETRO_MUSIC
        end = f":duration={item['dur']}" if item.get("dur") else ""
        chains.append(f"[{idx}:a]aformat=channel_layouts=mono,atrim=start={item.get('in', 0)}{end},"
                      f"asetpts=PTS-STARTPTS,{chain},volume={item.get('gain', 1.0)},"
                      f"adelay={delay}|{delay}[a{idx}]")
        labels.append(f"[a{idx}]")
        idx += 1
    total = round(total, 3)  # 足し算の誤差(59.30000000000001 等)で afade が全体を消すのを防ぐ
    chains.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest,"
                  f"atrim=0:{total},afade=t=out:st={max(round(total - 0.4, 3), 0)}:d=0.4,"
                  "aresample=22050,aresample=48000,loudnorm=I=-15:TP=-1.5[out]")
    out = os.path.join(tmp, "mix.wav")
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(chains),
         "-map", "[out]", "-ac", "1", "-ar", "48000", out])
    return out


# ---------------------------------------------------------------- 縦型(9:16)
def vertical_overlays(edl, tmp):
    """上帯(シリーズ名)と下帯(字幕)の画像を作る。戻り値:[(png, start, end)]"""
    W, H = 1080, 1920
    frame_h = 810
    top = (H - frame_h) // 2
    items = []
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(band)
    v = edl.get("vertical", {})
    if v.get("top_small"):
        draw_text_center(d, W / 2, top - 250, v["top_small"], font("mincho", 40), CREAM + (255,), spacing=6)
    if v.get("top_title"):
        draw_text_center(d, W / 2, top - 185, v["top_title"], font("gothic", 92), CREAM + (255,), spacing=8)
    if v.get("bottom_note"):
        draw_text_center(d, W / 2, H - 130, v["bottom_note"], font("mincho_regular", 30),
                         (200, 190, 170, 255), spacing=2)
    p = os.path.join(tmp, "band.png")
    band.save(p)
    items.append((p, 0, 9999))
    for k, s in enumerate(edl.get("subtitles", [])):
        im = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
        dd = ImageDraw.Draw(im)
        for j, ln in enumerate(s["text"].split("\n")):
            draw_text_center(dd, W / 2, 20 + j * 76, ln, font("mincho", 54), CREAM + (255,), spacing=1)
        p = os.path.join(tmp, f"sub{k:02d}.png")
        im.save(p)
        items.append((p, s["start"], s["end"]))
    return items, top + frame_h + 60


def make_vertical(master, edl, tmp, out):
    items, sub_y = vertical_overlays(edl, tmp)
    inputs = ["-i", master]
    for p, _, _ in items:
        inputs += ["-i", p]
    f = ["[0:v]scale=1080:810:flags=lanczos,pad=1080:1920:0:555:color=0x0b0a09[v0]"]
    last = "v0"
    for k, (p, a, b) in enumerate(items, start=1):
        y = 0 if k == 1 else sub_y
        f.append(f"[{last}][{k}:v]overlay=0:{y}:enable='between(t,{a},{b})'[v{k}]")
        last = f"v{k}"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(f),
         "-map", f"[{last}]", "-map", "0:a?", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out])


# ---------------------------------------------------------------- 本体
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--preview", action="store_true", help="低画質で速く確認")
    ap.add_argument("--keep-tmp", action="store_true")
    a = ap.parse_args()

    with open(a.edl, encoding="utf-8") as fh:
        edl = json.load(fh)
    edl_dir = os.path.dirname(os.path.abspath(a.edl))
    base = os.path.abspath(os.path.join(edl_dir, edl.get("base_dir", ".")))  # EDL の置き場所から見た相対パス
    out_dir = os.path.join(base, edl.get("out_dir", "out"))
    os.makedirs(out_dir, exist_ok=True)
    fps = edl.get("fps", 24)
    tmp = tempfile.mkdtemp(prefix="showa_")

    # 1) カットを 4:3 にそろえてつなぐ
    clips, t, clip_audio = [], 0.0, []
    for k, c in enumerate(edl["cuts"]):
        out = os.path.join(tmp, f"c{k:02d}.mp4")
        if "card" in c:
            still_clip(render_card(c["card"]), c["dur"], out, fps, a.preview)
        elif "color" in c:
            still_clip(Image.new("RGB", (PAD_W, PAD_H), tuple(c["color"])), c["dur"], out, fps, a.preview)
        else:
            normalize_clip(os.path.join(base, c["src"]), c.get("in", 0), c["dur"], out, fps, a.preview)
        clips.append(out)
        if c.get("audio") and "src" in c:  # カットの動画の音声(セリフなど)をそのまま使う
            clip_audio.append({"src": os.path.join(base, c["src"]), "kind": c.get("audio_kind", "voice"),
                               "start": t, "in": c.get("in", 0), "dur": c["dur"],
                               "gain": c.get("audio_gain", 1.0)})
        t += c["dur"]
    total = round(t, 3)
    n_frames = int(round(total * fps))
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{p}'\n" for p in clips)
    joined = os.path.join(tmp, "joined.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])

    # 2) テロップを用意
    telops = [(render_telop(x["text"], x.get("size", 40), x.get("pos", "lower"), x.get("font", "mincho"),
                            x.get("color"), x.get("xy"), x.get("stroke", True), x.get("angle", 0)),
               x["start"], x["end"])
              for x in edl.get("telops", [])]

    # 3) 1コマずつフィルム加工
    look = FilmLook(edl.get("look"), n_frames)
    silent = os.path.join(tmp, "film.mp4")
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", joined, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{WORK_W}x{WORK_H}", "-r", str(fps), "-i", "-",
                            "-vf", f"scale={OUT_W}:{OUT_H}:flags=lanczos",
                            "-c:v", "libx264", "-crf", "15" if not a.preview else "26",
                            "-preset", "medium" if not a.preview else "ultrafast",
                            "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    fsize = PAD_W * PAD_H * 3
    i = 0
    while True:
        buf = dec.stdout.read(fsize)
        if len(buf) < fsize:
            break
        fr = np.frombuffer(buf, np.uint8).reshape(PAD_H, PAD_W, 3)
        tt = i / fps
        for im, s, e in telops:
            if s <= tt < e:
                base_im = Image.fromarray(fr)
                base_im.paste(im, (0, 0), im)
                fr = np.asarray(base_im)
        enc.stdin.write(look.process(min(i, n_frames - 1), fr).tobytes())
        i += 1
        if i % 48 == 0:
            print(f"  フィルム加工 {i}/{n_frames} コマ", file=sys.stderr)
    enc.stdin.close()
    enc.wait()
    dec.wait()

    # 4) 音
    edl.setdefault("audio", {}).setdefault("tracks", [])
    edl["audio"]["tracks"] = edl["audio"]["tracks"] + clip_audio
    mix = build_audio(edl, total, tmp, base)
    vd = subprocess.run(["ffmpeg", "-v", "info", "-i", mix, "-af", "volumedetect", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    if "max_volume: -9" in vd or "max_volume: -inf" in vd:  # 無音(-90dB台)なら止める
        sys.exit(f"音声が無音になっています。作業フォルダを確認してください: {tmp}")
    master = os.path.join(out_dir, "master_4x3.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", mix, "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", master])

    # 5) 縦型
    vertical = os.path.join(out_dir, "vertical_9x16.mp4")
    make_vertical(master, edl, tmp, vertical)

    if a.keep_tmp:
        print("作業フォルダ:", tmp)
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    print("書き出し:", master)
    print("書き出し:", vertical)


if __name__ == "__main__":
    main()
