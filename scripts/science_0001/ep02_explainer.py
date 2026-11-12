"""第2話「スクイーズを揉んだ一瞬、脳では何が起きてる？」の映像合成。

第1話の描画パーツ(ep01_explainer)を使い回す。
  python3 scripts/science_0001/ep02_explainer.py            # → assets/output/science_0001/ep02_video.mp4(無音)
  python3 scripts/science_0001/ep02_explainer.py --still 10 # 確認用の1枚
数字は prompts/science_0001/ep02_squishy.md の出典付きの値のみ。
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import ep01_explainer as E  # noqa: E402
from ep01_explainer import (BLUE, F_BODY, F_HEAD, FPS, H, HOT, INK, W, WHITE, YEL, Shot, appear,  # noqa: E402
                            arrow, bottom_caption, card, chapter, ease, font, frames_of, label_arrow, pause_badge,
                            render_frame, rich, ring, series_badge, spaced)

E.SRC = Path("assets/source/science_0001/ep02")
E.SERIES = "一瞬の世界"
OUT = Path("assets/output/science_0001")


# ------------------------------------------------------------------ 冒頭
def ov_none(d, t, g):
    pass


def ov_hook_pause(d, t, g):
    series_badge(d)
    pause_badge(d, t)
    ring(d, (560, 900), 230, YEL, t)
    rich(d, ["揉んだこの一瞬、", "脳では**何が起きてる？**"], 300, 80, F_HEAD, appear(t, 0.15))


# ------------------------------------------------------------------ 指先
def ov_s1(d, t, g):
    chapter(d, t, 1, "指先は、センサーだらけ", BLUE)
    label_arrow(d, t, 2.6, (300, 1420), (700, 1215), "触覚センサーが反応", BLUE)
    bottom_caption(d, t, ["押された瞬間、いっせいに", "{b}電気の信号{/}を出す"], start=4.2, y=1560)


def ov_s1_pause(d, t, g):
    chapter(d, 9, 1, "指先は、センサーだらけ", BLUE)
    pause_badge(d, t)
    label_arrow(d, 9, 0, (300, 1420), (700, 1215), "触覚センサーが反応", BLUE)
    bottom_caption(d, 9, ["押された瞬間、いっせいに", "{b}電気の信号{/}を出す"], start=0, y=1560)


# ------------------------------------------------------------------ 神経
def nerve_timer(d, t, start, dur):
    a = appear(t, start)
    if a <= 0:
        return
    prog = ease((t - start) / dur)
    ms = 20 * prog
    box = (60, 1500, W - 60, 1790)
    card(d, box, a, YEL)
    d.text((110, 1530), "指先 → 脳 までの時間", font=font(F_BODY, 44), fill=WHITE + (int(255 * a),))
    f = font(F_HEAD, 96)
    s = f"{ms:4.1f}"
    d.text((110, 1590), s, font=f, fill=YEL + (int(255 * a),))
    d.text((110 + d.textlength(s, font=f) + 16, 1630), "ミリ秒", font=font(F_BODY, 50), fill=WHITE + (int(255 * a),))
    d.text((640, 1625), "約0.02秒", font=font(F_HEAD, 44), fill=YEL + (int(255 * a * appear(t, start + dur)),))
    d.rounded_rectangle((110, 1740, W - 110, 1758), radius=9, fill=(60, 64, 80, int(255 * a)))
    d.rounded_rectangle((110, 1740, 110 + (W - 220) * prog, 1758), radius=9, fill=YEL + (int(255 * a),))


def ov_s2(d, t, g):
    chapter(d, t, 2, "信号は、腕を駆け上がる", YEL)
    nerve_timer(d, t, 0.8, 4.0)


def ov_s2_pause(d, t, g):
    chapter(d, 9, 2, "信号は、腕を駆け上がる", YEL)
    nerve_timer(d, 9, 0, 1)


# ------------------------------------------------------------------ 脳の地図
def body_map(d, t, start, box):
    """「脳の地図」の模式図: 体の部位ごとの広さを横棒で。手が特大(相対イメージ、数値なし)。"""
    a = appear(t, start)
    if a <= 0:
        return
    card(d, box, a, HOT)
    x0, y0, x1, y1 = box
    d.text((x0 + 50, y0 + 34), "脳の中の“体の地図”", font=font(F_HEAD, 44), fill=WHITE + (int(255 * a),))
    d.text((x0 + 50, y0 + 96), "（担当エリアの広さのイメージ）", font=font(F_BODY, 30),
           fill=(190, 190, 200, int(255 * a)))
    rows = [("背中", 0.10, (150, 155, 170)), ("足", 0.16, (150, 155, 170)), ("くちびる", 0.62, (150, 155, 170)),
            ("手", 0.95, YEL)]
    for i, (name, v, col) in enumerate(rows):
        k = ease((t - start - 0.4 - i * 0.35) / 0.6)
        y = y0 + 170 + i * 92
        d.text((x0 + 50, y), name, font=font(F_BODY, 40), fill=WHITE + (int(255 * a),))
        bx0, bx1 = x0 + 250, x1 - 60
        d.rounded_rectangle((bx0, y + 8, bx1, y + 44), radius=18, fill=(50, 54, 70, int(255 * a)))
        if k > 0:
            d.rounded_rectangle((bx0, y + 8, bx0 + (bx1 - bx0) * v * k, y + 44), radius=18,
                                fill=col + (int(255 * a),))


def ov_s3(d, t, g):
    chapter(d, t, 3, "脳の中の“体の地図”", HOT)
    label_arrow(d, t, 1.0, (300, 420), (560, 760), "触覚を感じるエリア", HOT)


def ov_s3_pause(d, t, g):
    chapter(d, 9, 3, "脳の中の“体の地図”", HOT)
    pause_badge(d, t)
    body_map(d, t, 0.0, (60, 1180, W - 60, 1720))
    a = appear(t, 1.6)
    if a > 0:
        rich(d, ["手は、地図の中で", "**特大サイズ**"], 330, 66, F_HEAD, a)


def ov_question(d, t, g):
    a = appear(t, 0.2, 0.6)
    rich(d, ["でも、", "**自分で**揉むと…？"], 820, 92, F_HEAD, a)


# ------------------------------------------------------------------ 小脳
def half_meter(d, t, start, box):
    a = appear(t, start)
    if a <= 0:
        return
    card(d, box, a, BLUE)
    x0, y0, x1, y1 = box
    d.text((x0 + 50, y0 + 34), "押す力の“感じ方”", font=font(F_HEAD, 44), fill=WHITE + (int(255 * a),))
    rows = [("人に押される", 1.0, HOT), ("自分で押す", 0.5, BLUE)]
    for i, (name, v, col) in enumerate(rows):
        k = ease((t - start - 0.4 - i * 0.8) / 0.8)
        y = y0 + 120 + i * 110
        d.text((x0 + 50, y), name, font=font(F_BODY, 40), fill=WHITE + (int(255 * a),))
        bx0, bx1 = x0 + 330, x1 - 140
        d.rounded_rectangle((bx0, y + 6, bx1, y + 46), radius=20, fill=(50, 54, 70, int(255 * a)))
        if k > 0:
            d.rounded_rectangle((bx0, y + 6, bx0 + (bx1 - bx0) * v * k, y + 46), radius=20,
                                fill=col + (int(255 * a),))
            lab = "100%" if v == 1.0 else "約50%"
            d.text((bx1 + 16, y + 2), lab, font=font(F_HEAD, 34), fill=col + (int(255 * a * k),))


def ov_s4(d, t, g):
    chapter(d, t, 4, "脳が、感触を“割り引く”", BLUE)
    label_arrow(d, t, 1.0, (300, 1380), (560, 1090), "小脳", BLUE, size=48)
    label_arrow(d, t, 2.2, (800, 420), (640, 720), "触覚のエリア", HOT)
    half_meter(d, t, 4.4, (60, 1480, W - 60, 1800))


def ov_s4_pause(d, t, g):
    chapter(d, 9, 4, "脳が、感触を“割り引く”", BLUE)
    pause_badge(d, t)
    half_meter(d, 9, 0, (60, 1480, W - 60, 1800))
    a = appear(t, 2.8, 0.5)
    if a > 0:
        card(d, (60, 300, W - 60, 560), a, YEL)
        rich(d, ["だから、自分をくすぐっても", "**くすぐったくない**"], 340, 62, F_BODY, a, stroke=0)


# ------------------------------------------------------------------ エンディング
END_CHIPS = ["静電気がバチッとくる瞬間", "シャボン玉が割れる瞬間", "雷が落ちる瞬間", "電子レンジの中"]
END_T = {"punch": 0.3, "ask": 2.6, "chips": 3.6, "cta": 6.0}


def ov_ending(d, t, g):
    a = appear(t, END_T["punch"], 0.6)
    fade = 1 - appear(t, END_T["ask"] - 0.6, 0.5)
    if a * fade > 0:
        rich(d, ["自分の手の感触は、", "脳が**“割り引いて”**いた"], 820, 66, F_HEAD, a * fade)
    k = appear(t, END_T["ask"], 0.6)
    if k <= 0:
        return
    spaced(d, "NEXT", 330 - (1 - k) * 20, 32, YEL, k)
    rich(d, ["次は、どの一瞬を", "のぞいてみたい？"], 400 - (1 - k) * 20, 76, F_HEAD, k)
    for i, txt in enumerate(END_CHIPS):
        c = appear(t, END_T["chips"] + 0.45 * i, 0.5)
        if c <= 0:
            continue
        y = 720 + i * 150 + (1 - c) * 24
        f = font(F_BODY, 50)
        w = d.textlength(txt, font=f)
        x0 = W / 2 - (w + 120) / 2
        d.rounded_rectangle((x0, y, x0 + w + 120, y + 104), radius=52, fill=(255, 255, 255, int(28 * c)),
                            outline=(255, 255, 255, int(150 * c)), width=2)
        d.text((x0 + 60, y + 20), txt, font=f, fill=WHITE + (int(255 * c),))
    e = appear(t, END_T["cta"], 0.6)
    if e > 0:
        f = font(F_BODY, 52)
        txt = "コメントで教えてください"
        w = d.textlength(txt, font=f)
        x = W / 2 - (w + 90) / 2
        y = 1400 - (1 - e) * 20
        d.rounded_rectangle((x, y + 6, x + 64, y + 56), radius=16, fill=YEL + (int(255 * e),))
        d.polygon([(x + 14, y + 52), (x + 30, y + 52), (x + 12, y + 72)], fill=YEL + (int(255 * e),))
        for j in range(3):
            d.ellipse((x + 14 + j * 14, y + 26, x + 22 + j * 14, y + 34), fill=INK + (int(255 * e),))
        d.text((x + 90, y), txt, font=f, fill=YEL + (int(255 * e),))
        d.line((W / 2 - 160, y + 100, W / 2 + 160, y + 100), fill=(255, 255, 255, int(90 * e)), width=2)


SHOTS = [
    Shot("H_squeeze.mp4", 0.0, 3.5, overlay=ov_none, speed=1.4, tag="open"),
    Shot("H_squeeze.mp4", 0.3, 0.9, overlay=ov_none, speed=3.5, reverse=True, vf_extra="tmix=frames=5", tag="rewind"),
    Shot("H_squeeze.mp4", 0.0, 2.5, overlay=E.ov_slow, speed=0.6, interp=True, tag="slow"),
    Shot("H_squeeze.mp4", 1.5, 4.0, freeze=True, overlay=ov_hook_pause, dim=0.25, tag="hook_pause"),
    Shot("S1_finger.mp4", 0.0, 5.0, overlay=ov_s1, tag="s1"),
    Shot("S1_finger.mp4", 4.9, 3.5, freeze=True, overlay=ov_s1_pause, dim=0.2, tag="s1_pause"),
    Shot("S2_nerve.mp4", 0.0, 5.0, overlay=ov_s2, tag="s2"),
    Shot("S2_nerve.mp4", 4.9, 2.6, freeze=True, overlay=ov_s2_pause, dim=0.2, tag="s2_pause"),
    Shot("S3_cortex.mp4", 0.0, 5.0, overlay=ov_s3, tag="s3"),
    Shot("S3_cortex.mp4", 4.9, 4.4, freeze=True, overlay=ov_s3_pause, dim=0.45, tag="s3_pause"),
    Shot("S3_cortex.mp4", 4.9, 5.4, freeze=True, overlay=ov_question, dim=0.65, blur=10, tag="question"),
    Shot("S4_cerebellum.mp4", 0.0, 5.0, overlay=ov_s4, tag="s4"),
    Shot("S4_cerebellum.mp4", 4.9, 7.0, freeze=True, overlay=ov_s4_pause, dim=0.3, tag="s4_pause"),
    Shot("S4_cerebellum.mp4", 4.95, 9.0, freeze=True, overlay=ov_ending, dim=0.6, blur=16, tag="ending"),
]


def timeline():
    t, out = 0.0, {}
    for s in SHOTS:
        if s.tag:
            out[s.tag] = round(t, 3)
        t += s.dur
    out["total"] = round(t, 3)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=float, nargs="*")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.still:
        starts = np.cumsum([0] + [s.dur for s in SHOTS])
        for ts in a.still:
            i = int(np.searchsorted(starts, ts, side="right") - 1)
            s = SHOTS[i]
            lt = ts - starts[i]
            src_t = s.start if s.freeze else (s.start + s.dur * s.speed - lt * s.speed if s.reverse
                                              else s.start + lt * s.speed)
            sub = Shot(**{**s.__dict__, "start": src_t, "dur": 1 / FPS, "speed": 1.0, "reverse": False,
                          "interp": False, "vf_extra": ""})
            render_frame(s, next(frames_of(sub)), lt).save(OUT / f"ep02_still_{ts:05.1f}.png")
        return
    out = OUT / "ep02_video.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                            "-preset", "medium", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    for s in SHOTS:
        for k, base in enumerate(frames_of(s)):
            enc.stdin.write(render_frame(s, base, k / FPS).tobytes())
    enc.stdin.close()
    enc.wait()
    print("wrote", out, timeline())


if __name__ == "__main__":
    main()
