"""第2話（作り直し）「スクイーズを揉んだときの"脳汁"の正体」— Blender 素材にテロップ・図解を重ねる。

  python3 scripts/science_0001/blender/ep02_scenes.py <scene>   # 4シーンをレンダリング(15fps PNG)
  python3 scripts/science_0001/ep02b_explainer.py --clips       # PNG → 30fps/1080x1920 の mp4(補間+光のにじみ)
  python3 scripts/science_0001/ep02b_explainer.py               # 映像(無音) → ep02b_video.mp4
  python3 scripts/science_0001/ep02b_mix.py                     # 音 → ep02b.mp4
クレジット不使用(ナレーション5行のみ、許可を得て ElevenLabs で生成済み)。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import ep01_explainer as E  # noqa: E402
from ep01_explainer import (BLUE, F_BODY, F_HEAD, FPS, H, HOT, INK, W, WHITE, YEL, Shot, appear,  # noqa: E402
                            card, chapter, ease, font, frames_of, label_arrow, pause_badge, render_frame, rich, ring,
                            series_badge, spaced)

ROOT = Path(__file__).resolve().parents[2]
RENDER = ROOT / "assets/output/science_0001/ep02_blender"
CLIPS = ROOT / "assets/output/science_0001/ep02_clips"
OUT = ROOT / "assets/output/science_0001"
E.SRC = CLIPS
E.SERIES = "一瞬の世界"
GOLD = (255, 190, 60)


def build_clips():
    """15fps の PNG 連番 → 30fps に補間、1080x1920 に拡大、明るい所をふんわり光らせる。"""
    CLIPS.mkdir(parents=True, exist_ok=True)
    for name in ("squishy", "nerve", "reward", "dopamine"):
        src = RENDER / name
        # 光のにじみは RGB で計算する(YUV のまま screen 合成すると色が紫にずれる)
        fc = ("[0:v]minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:vsbmc=1,"
              "scale=1080:1920:flags=lanczos,format=gbrp,split[a][b];"
              "[b]colorlevels=rimin=0.62:gimin=0.62:bimin=0.62,gblur=sigma=24[g];"
              "[a][g]blend=all_mode=screen:all_opacity=0.5,format=yuv420p[v]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "15", "-i", str(src / "%04d.png"),
                        "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-crf", "16",
                        str(CLIPS / f"{name}.mp4")], check=True)
        print("clip", name)


# ------------------------------------------------------------------ 冒頭
def ov_none(d, t, g):
    pass


def ov_hook_pause(d, t, g):
    series_badge(d)
    pause_badge(d, t)
    ring(d, (540, 1180), 230, YEL, t)
    rich(d, ["揉んだこの一瞬、", "脳では**何が起きてる？**"], 300, 80, F_HEAD, appear(t, 0.15))


# ------------------------------------------------------------------ 信号
def signal_timer(d, t, start, dur):
    a = appear(t, max(0.0, start - 0.3))
    if a <= 0:
        return
    prog = ease(min(max((t - start) / dur, 0), 1))
    box = (60, 1500, W - 60, 1790)
    card(d, box, a, YEL)
    d.text((110, 1530), "指先 → 脳 までの時間", font=font(F_BODY, 44), fill=WHITE + (int(255 * a),))
    f = font(F_HEAD, 96)
    s = f"{20 * prog:4.1f}"
    d.text((110, 1590), s, font=f, fill=YEL + (int(255 * a),))
    d.text((110 + d.textlength(s, font=f) + 16, 1630), "ミリ秒", font=font(F_BODY, 50), fill=WHITE + (int(255 * a),))
    k = appear(t, start + dur)
    d.text((660, 1625), "約0.02秒", font=font(F_HEAD, 44), fill=YEL + (int(255 * a * k),))
    d.rounded_rectangle((110, 1740, W - 110, 1758), radius=9, fill=(60, 64, 80, int(255 * a)))
    d.rounded_rectangle((110, 1740, 110 + (W - 220) * prog, 1758), radius=9, fill=YEL + (int(255 * a),))


def ov_signal(d, t, g):
    chapter(d, t, 1, "信号は、約0.02秒で脳へ", YEL)
    signal_timer(d, t, 0.3, 2.3)


def ov_signal_hold(d, t, g):
    chapter(d, 9, 1, "信号は、約0.02秒で脳へ", YEL)
    signal_timer(d, 9, 0.3, 2.3)


# ------------------------------------------------------------------ ごほうびエリア
def ov_reward(d, t, g):
    chapter(d, t, 2, "“気持ちいい”をキャッチ", HOT)
    label_arrow(d, t, 1.4, (330, 1420), g.extra.get("ofc", (840, 1190)), "ごほうびに関わるエリア", HOT)


def ov_reward_hold(d, t, g):
    chapter(d, 9, 2, "“気持ちいい”をキャッチ", HOT)
    label_arrow(d, 9, 0, (330, 1420), g.extra.get("ofc", (840, 1190)), "ごほうびに関わるエリア", HOT)


# ------------------------------------------------------------------ 脳汁
def ov_dopa(d, t, g):
    chapter(d, t, 3, "これが“脳汁”の正体", GOLD)
    a = appear(t, 2.2, 0.5)
    if a > 0:
        rich(d, ["ドーパミン"], 330 - (1 - a) * 20, 110, F_HEAD, a)
        spaced(d, "DOPAMINE", 480, 30, GOLD, a)
    label_arrow(d, t, 1.0, (300, 1460), g.extra.get("src", (505, 1060)), "脳の奥から", GOLD)


def ov_dopa_hold(d, t, g):
    chapter(d, 9, 3, "これが“脳汁”の正体", GOLD)
    rich(d, ["ドーパミン"], 330, 110, F_HEAD, 1)
    spaced(d, "DOPAMINE", 480, 30, GOLD, 1)


def ov_question(d, t, g):
    a = appear(t, 0.2, 0.6)
    rich(d, ["でも実は", "ドーパミンって…"], 820, 92, F_HEAD, a)


def two_cards(d, t):
    """liking(気持ちいい) と wanting(もっとほしい) を並べる。"""
    rows = [
        (0.2, "“気持ちいい”", "LIKING", "別のしくみが担当", (150, 155, 175)),
        (1.2, "“もっとほしい”", "WANTING", "ドーパミンが担当", GOLD),
    ]
    for i, (st, title, en, sub, col) in enumerate(rows):
        a = appear(t, st, 0.5)
        if a <= 0:
            continue
        y = 640 + i * 330 + (1 - a) * 24
        card(d, (60, y, W - 60, y + 280), a, col)
        spaced_left(d, en, 110, y + 36, 28, col, a)
        d.text((110, y + 80), title, font=font(F_HEAD, 70), fill=WHITE + (int(255 * a),))
        d.text((110, y + 186), sub, font=font(F_BODY, 44), fill=col + (int(255 * a),))


def spaced_left(d, text, x, y, size, color, a, track=0.3):
    f = font(F_BODY, size)
    for c in text:
        d.text((x, y), c, font=f, fill=color + (int(255 * a),))
        x += d.textlength(c, font=f) + track * size


def ov_punch(d, t, g):
    a = appear(t, 0.0, 0.4)
    rich(d, ["ドーパミンの正体は"], 340, 64, F_BODY, a)
    two_cards(d, t)
    b = appear(t, 4.4, 0.6)
    if b > 0:
        rich(d, ["だから、つい", "**もう1回**揉みたくなる"], 1420, 74, F_HEAD, b)
        d.text((W / 2 - 170, 1640), "（と考えられています）", font=font(F_BODY, 34),
               fill=(200, 200, 210, int(255 * b)))


# ------------------------------------------------------------------ エンディング
END_CHIPS = ["静電気がバチッとくる瞬間", "シャボン玉が割れる瞬間", "雷が落ちる瞬間", "電子レンジの中"]
END_T = {"punch": 0.3, "ask": 2.6, "chips": 3.6, "cta": 6.0}


def ov_ending(d, t, g):
    a = appear(t, END_T["punch"], 0.6)
    fade = 1 - appear(t, END_T["ask"] - 0.6, 0.5)
    if a * fade > 0:
        rich(d, ["“脳汁”の正体は", "**「もっとほしい」**"], 820, 70, F_HEAD, a * fade)
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


SHOTS = [
    Shot("squishy.mp4", 0.0, 3.1, overlay=ov_none, speed=1.5, tag="open"),
    Shot("squishy.mp4", 0.0, 0.8, overlay=ov_none, speed=5.75, reverse=True, vf_extra="tmix=frames=5", tag="rewind"),
    Shot("squishy.mp4", 0.0, 2.3, overlay=E.ov_slow, speed=0.35, interp=True, tag="slow"),
    Shot("squishy.mp4", 0.8, 4.0, freeze=True, overlay=ov_hook_pause, dim=0.25, tag="hook_pause"),
    Shot("nerve.mp4", 0.0, 5.0, overlay=ov_signal, tag="signal"),
    Shot("nerve.mp4", 4.85, 0.6, freeze=True, overlay=ov_signal_hold, tag="signal_hold"),
    Shot("reward.mp4", 0.0, 4.0, overlay=ov_reward, tag="reward"),
    Shot("reward.mp4", 3.85, 1.6, freeze=True, overlay=ov_reward_hold, tag="reward_hold"),
    Shot("dopamine.mp4", 0.0, 5.0, overlay=ov_dopa, tag="dopa"),
    Shot("dopamine.mp4", 4.85, 0.6, freeze=True, overlay=ov_dopa_hold, tag="dopa_hold"),
    Shot("dopamine.mp4", 3.0, 5.0, freeze=True, overlay=ov_question, dim=0.65, blur=10, tag="question"),
    Shot("dopamine.mp4", 3.0, 8.6, freeze=True, overlay=ov_punch, dim=0.72, blur=16, tag="punch"),
    Shot("squishy.mp4", 4.5, 9.0, freeze=True, overlay=ov_ending, dim=0.6, blur=16, tag="ending"),
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
    ap.add_argument("--clips", action="store_true")
    a = ap.parse_args()
    if a.clips:
        build_clips()
        return
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
            render_frame(s, next(frames_of(sub)), lt).save(OUT / f"ep02b_still_{ts:05.1f}.png")
        return
    out = OUT / "ep02b_video.mp4"
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
