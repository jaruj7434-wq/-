"""第1話の仮編集: 冒頭フック(Higgsfield) + シミュレーション + 効果音 を1本にまとめる。

  python3 scripts/science_0001/ep01_edit.py --hook <冒頭クリップ.mp4>

入力:
  --hook  Higgsfield で生成した冒頭のスロー映像(縦型)
  --sim   ep01_popcorn_sim.py の出力 (既定: assets/output/science_0001/ep01_popcorn_sim.mp4)
出力: assets/output/science_0001/ep01_rough_cut.mp4
効果音は numpy で合成(著作権フリー): 加熱のジュー音 → 破裂の「ポン」 → 蒸気のシュッ。
"""
from __future__ import annotations

import argparse
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT_DIR = Path("assets/output/science_0001")
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

# シミュ動画のタイムライン(ep01_popcorn_sim.py と合わせる)
SIM_BURST_AT = 8.0
SIM_TOTAL = 18.0


def _noise(n, rng):
    return rng.normal(0, 1, n)


def _lowpass(x, a):
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def synth_sfx(hook_len: float, total: float) -> np.ndarray:
    rng = np.random.default_rng(0)
    out = np.zeros(int(total * SR))

    def put(sig, t):
        i = int(t * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    # フック中: 低いうなり → 終わりに小さな「ポン」
    n = int(hook_len * SR)
    t = np.arange(n) / SR
    put(0.08 * np.sin(2 * np.pi * 55 * t) * np.minimum(1, t / 0.5), 0)

    # 加熱: だんだん強くなるジュー音(フィルタしたノイズ+パチパチ)
    heat_len = SIM_BURST_AT
    n = int(heat_len * SR)
    t = np.arange(n) / SR
    sizzle = np.diff(np.r_[0, _noise(n, rng)]) * 0.5  # 高域寄りのノイズ
    env = 0.03 + 0.17 * (t / heat_len) ** 2
    crackle = np.zeros(n)
    for c in rng.uniform(0, heat_len, 60):
        k = int(c * SR)
        crackle[k:k + 200] += rng.normal(0, 0.5, len(crackle[k:k + 200])) * np.exp(-np.arange(len(crackle[k:k + 200])) / 40)
    put(sizzle * env + crackle * (t / heat_len), hook_len)

    # 破裂: 「ポン」= 鋭い立ち上がり + 共鳴(空洞が共鳴器になる)
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    pop = (np.sin(2 * np.pi * 180 * t) * 0.9 + np.sin(2 * np.pi * 520 * t) * 0.4) * np.exp(-t / 0.06)
    pop += _noise(n, rng) * np.exp(-t / 0.01) * 0.8
    put(pop * 0.9, hook_len + SIM_BURST_AT)

    # 蒸気: シュッ(ノイズ, 0.8秒でフェード)
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    hiss = _lowpass(_noise(n, rng), 0.35) * np.exp(-t / 0.35) * 0.35
    put(hiss, hook_len + SIM_BURST_AT + 0.05)

    # オチ: 軽いチャイム
    n = int(1.5 * SR)
    t = np.arange(n) / SR
    chime = sum(np.sin(2 * np.pi * f * t) for f in (880, 1320)) * np.exp(-t / 0.4) * 0.12
    put(chime, hook_len + SIM_TOTAL - 3.0)

    out /= max(1e-6, np.abs(out).max()) / 0.8
    return out


def write_wav(path: Path, x: np.ndarray):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hook", required=True)
    ap.add_argument("--sim", default=str(OUT_DIR / "ep01_popcorn_sim.mp4"))
    ap.add_argument("--out", default=str(OUT_DIR / "ep01_rough_cut.mp4"))
    a = ap.parse_args()
    hook, sim, out = Path(a.hook), Path(a.sim), Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    hook_len = duration(hook)
    total = hook_len + duration(sim)
    sfx = OUT_DIR / "ep01_sfx.wav"
    write_wav(sfx, synth_sfx(hook_len, total))

    telop = "この0.001秒に\n何が起きている？"
    vf_hook = (
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1,"
        f"drawtext=fontfile={FONT}:text='{telop}':fontsize=84:fontcolor=white:borderw=6:bordercolor=black:"
        "x=(w-text_w)/2:y=h*0.12:line_spacing=18:enable='gte(t,0.3)'"
    )
    fc = (
        f"[0:v]{vf_hook}[h];"
        "[1:v]scale=1080:1920,fps=30,setsar=1[s];"
        "[h][s]concat=n=2:v=1:a=0[v]"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(hook), "-i", str(sim), "-i", str(sfx),
        "-filter_complex", fc, "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out),
    ], check=True)
    print(f"wrote {out} ({total:.1f}s)")


if __name__ == "__main__":
    main()
