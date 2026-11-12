"""第1話 編集 v2: 説明パートも Higgsfield の実写風カットでつなぐ版。

  python3 scripts/science_0001/ep01_edit_v2.py

素材 (assets/source/science_0001/, git管理外):
  ep01_hook_kling.mp4      冒頭フック
  ep01_s1_cutaway.mp4      ① 断面: 水分が沸騰して蒸気に
  ep01_s2_pressure.mp4     ② 殻が内圧で張りつめる
  ep01_s3_rupture.mp4      ③ 亀裂 → でんぷんが噴き出す
  ep01_s4_leg.mp4          ④ でんぷんの「脚」で跳ぶ
出力: assets/output/science_0001/ep01_v2.mp4
テロップの数字は plan.md の出典付きの値のみ使う。
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np

from ep01_edit import SR, _lowpass, _noise, write_wav

SRC = Path("assets/source/science_0001")
OUT = Path("assets/output/science_0001")
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
ACCENT = "0xFFC04D"

# (ファイル, 使う秒数, 大きい数字, 説明テロップ)
SEGMENTS = [
    ("ep01_hook_kling.mp4", 4.0, "", "この0.001秒に\n何が起きている？"),
    ("ep01_s1_cutaway.mp4", 5.0, "水分 約14%", "熱で粒の中の水が\n蒸気に変わる"),
    ("ep01_s2_pressure.mp4", 5.0, "約180℃・約10気圧", "殻が圧力鍋のふたになり\n蒸気を閉じこめる"),
    ("ep01_s3_rupture.mp4", 5.0, "0.09秒未満", "殻が裂けて\n花の形になるまで"),
    ("ep01_s4_leg.mp4", 5.0, "約20G", "でんぷんの「脚」が\n床を蹴って跳ぶ"),
]
END_LEN = 3.5
END_TEXT = "ポップコーンは\n蒸気で飛ぶんじゃない\n自分の「脚」でジャンプする"
POP_OFFSET_IN_S3 = 0.2  # ③で殻が裂ける瞬間(秒)


def sfx(total: float, starts: list[float]) -> np.ndarray:
    rng = np.random.default_rng(0)
    out = np.zeros(int(total * SR))

    def put(sig, t):
        i = int(t * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    # 冒頭: 低いうなり
    n = int(starts[1] * SR)
    t = np.arange(n) / SR
    put(0.08 * np.sin(2 * np.pi * 55 * t) * np.minimum(1, t / 0.5), 0)
    # ①②: 強くなっていくジュー音
    a, b = starts[1], starts[3] + POP_OFFSET_IN_S3
    n = int((b - a) * SR)
    t = np.arange(n) / SR
    put(np.diff(np.r_[0, _noise(n, rng)]) * 0.5 * (0.03 + 0.2 * (t / (b - a)) ** 2), a)
    # ③: ポン + シュッ
    pop_t = b
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    pop = (np.sin(2 * np.pi * 180 * t) * 0.9 + np.sin(2 * np.pi * 520 * t) * 0.4) * np.exp(-t / 0.06)
    pop += _noise(n, rng) * np.exp(-t / 0.01) * 0.8
    put(pop, pop_t)
    n = int(1.5 * SR)
    t = np.arange(n) / SR
    put(_lowpass(_noise(n, rng), 0.35) * np.exp(-t / 0.4) * 0.35, pop_t + 0.05)
    # ④: 跳ぶ瞬間の軽いヒュッ
    n = int(0.8 * SR)
    t = np.arange(n) / SR
    put(np.sin(2 * np.pi * (300 + 900 * t) * t) * np.exp(-t / 0.25) * 0.15, starts[4] + 2.6)
    # オチ: チャイム
    n = int(2.0 * SR)
    t = np.arange(n) / SR
    put(sum(np.sin(2 * np.pi * f * t) for f in (880, 1320)) * np.exp(-t / 0.5) * 0.15, starts[5])
    return out / (np.abs(out).max() / 0.8)


def _lines(tmp: Path, key: str, text: str, size: int, color: str, y0: int, extra: str) -> str:
    """複数行テロップを1行ずつ中央ぞろえで描く。"""
    f = ""
    for j, line in enumerate(text.split("\n")):
        (tmp / f"{key}_{j}.txt").write_text(line)
        f += (f",drawtext=fontfile={FONT}:textfile={tmp}/{key}_{j}.txt:expansion=none:fontsize={size}:"
              f"fontcolor={color}:borderw=6:bordercolor=black:x=(w-text_w)/2:y={y0 + j * int(size * 1.35)}:{extra}")
    return f


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    inputs, fc, labels, starts = [], [], [], [0.0]
    for i, (f, dur, big, cap) in enumerate(SEGMENTS):
        inputs += ["-t", str(dur), "-i", str(SRC / f)]
        (tmp / f"b{i}.txt").write_text(big)
        v = f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1"
        if big:
            v += (f",drawtext=fontfile={FONT}:textfile={tmp}/b{i}.txt:expansion=none:fontsize=104:fontcolor={ACCENT}:"
                  "borderw=7:bordercolor=black:x=(w-text_w)/2:y=h*0.10:enable='gte(t,0.3)'")
        y0 = 190 if not big else 340
        size = 84 if not big else 66
        v += _lines(tmp, f"c{i}", cap, size, "white", y0, "enable='gte(t,0.3)'")
        fc.append(v + f"[v{i}]")
        labels.append(f"[v{i}]")
        starts.append(starts[-1] + dur)
    # エンドカード: ④ の最後のフレームを暗くしてオチ
    k = len(SEGMENTS)
    inputs += ["-sseof", "-0.1", "-i", str(SRC / SEGMENTS[-1][0])]
    fc.append(
        f"[{k}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,"
        f"loop=loop=-1:size=1,trim=duration={END_LEN},fps=30,eq=brightness=-0.25,"
        + _lines(tmp, "end", END_TEXT, 76, "white", 1180, "alpha='min(1,t/0.4)'").lstrip(",") + "[vend]"
    )
    labels.append("[vend]")
    total = starts[-1] + END_LEN
    wav = OUT / "ep01_v2_sfx.wav"
    write_wav(wav, sfx(total, starts))
    inputs += ["-i", str(wav)]
    fc.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[v]")
    out = OUT / "ep01_v2.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc),
                    "-map", "[v]", "-map", f"{k + 1}:a", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    print(f"wrote {out} ({total:.1f}s)")


if __name__ == "__main__":
    main()
