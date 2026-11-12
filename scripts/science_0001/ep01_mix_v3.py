"""第1話 解説強化版の音: 効果音(合成) + ナレーション + BGM を映像に重ねる。

  python3 scripts/science_0001/ep01_explainer.py   # → ep01_v4_video.mp4
  python3 scripts/science_0001/ep01_mix_v3.py      # → ep01_v4.mp4
効果音はすべて numpy で合成(著作権フリー)。図解(矢印・グラフ)の出るタイミングに合わせて鳴らす。
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from ep01_edit import SR, _lowpass, _noise, write_wav  # noqa: E402
from ep01_explainer import ROW_T, timeline  # noqa: E402

SRC = Path("assets/source/science_0001")
OUT = Path("assets/output/science_0001")
VIDEO = OUT / "ep01_v4_video.mp4"
FINAL = OUT / "ep01_v4.mp4"
SFX_VOL, BGM_VOL, NA_VOL = 0.55, 0.13, 1.6

# (ナレーション番号, タイムラインのタグ, タグからの秒) — 文言は plan.md
NARRATION = [
    (0, "hook_pause", 0.3),     # この一瞬、粒の中で何が起きてる？
    (10, "hook_play2", 0.2),    # 4つのステップで、分解してみよう。
    (11, "step1", 0.2),         # ステップ1。粒の中の水分が、熱で水蒸気に変わります。
    (12, "step1_pause", 0.8),   # 水分は、粒の重さの約14%。これが、膨らむ力のもとです。
    (13, "step2", 0.2),         # ステップ2。かたい殻がフタになって、蒸気を外に逃がしません。
    (14, "step2_pause", 0.7),   # 温度が上がるほど…約180度で、ふだんの空気の約10倍。ここで殻が限界を…
    (15, "step3", 0.3),         # ステップ3。ついに殻が裂けて、水蒸気が噴き出し、でんぷんが一気に白い泡に…
    (16, "step3_play", 0.2),    # ここまで、実際には0.09秒もかかりません。
    (17, "step4", 0.1),         # ステップ4。ポップコーンは、どうやって跳ぶのでしょう？
    (18, "step4_pause", 2.1),   # 答えは、この白い脚。…加速度は、なんと約20G。
    (19, "step4_end", 0.1),     # そして空中で、花が開きます。
    (20, "summary", 0.6),       # まとめると、水が蒸気になり、圧力で殻が裂け、でんぷんの脚でジャンプ。
    (5, "summary", 7.3),        # ポップコーンは、自分の脚で跳んでいたんです。
]


def env(n, tau):
    return np.exp(-np.arange(n) / SR / tau)


def tone(f, d, tau, amp=0.5):
    n = int(d * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t) * env(n, tau) * amp


def sweep(f0, f1, d, amp=0.3):
    n = int(d * SR)
    t = np.arange(n) / SR
    ph = 2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * d))
    return np.sin(ph) * np.sin(np.pi * t / d) * amp


def build_sfx(tl):
    rng = np.random.default_rng(0)
    total = tl["total"]
    out = np.zeros(int((total + 1) * SR))

    def put(sig, t):
        i = int(t * SR)
        out[i:i + len(sig)] += sig[: max(0, len(out) - i)]

    def noise(d, a=0.5):
        return _lowpass(_noise(int(d * SR), rng), a)

    def tick():  # 一時停止「カチッ」
        return tone(1800, 0.2, 0.012, 0.6) + noise(0.3, 0.5) * env(int(0.3 * SR), 0.06) * 0.2

    def swish():  # 矢印・ラベルが出る「シュッ」
        n = int(0.25 * SR)
        return noise(0.25, 0.6) * np.sin(np.pi * np.arange(n) / n) * 0.25 + tone(1200, 0.12, 0.03, 0.15)

    def popsnd(a=0.8):
        n = int(0.5 * SR)
        s = tone(180, 0.5, 0.06, 0.9) + tone(520, 0.5, 0.06, 0.4)
        return (s + _noise(n, rng) * env(n, 0.01) * 0.8) * a

    def hiss(d=1.5, a=0.35):
        return noise(d, 0.35) * env(int(d * SR), d / 3.5) * a

    def chapter():  # STEP 開始の「ピロン」
        return np.r_[tone(784, 0.12, 0.08, 0.35), tone(1175, 0.35, 0.12, 0.35)]

    def thud():
        return tone(70, 0.5, 0.12, 0.9) + noise(0.15, 0.3) * env(int(0.15 * SR), 0.03) * 0.5

    def boing():
        n = int(0.6 * SR)
        t = np.arange(n) / SR
        return np.sin(2 * np.pi * (220 + 500 * t + 60 * np.sin(2 * np.pi * 12 * t)) * t) * env(n, 0.2) * 0.4

    def impact():
        return thud() * 0.8 + tone(880, 0.6, 0.15, 0.25) + tone(1320, 0.6, 0.15, 0.2)

    def ding():
        return tone(1568, 1.0, 0.3, 0.3) + tone(2093, 1.0, 0.25, 0.15)

    # --- フック
    put(popsnd(), 1.1)
    put(tick(), tl["hook_pause"])
    put(sweep(300, 900, 0.5, 0.15), tl["hook_play2"])
    # --- STEP1: 章 + ラベル + ぶくぶく(沸騰)
    s1 = tl["step1"]
    put(chapter(), s1)
    for k in (0.8, 1.6, 2.4):
        put(swish(), s1 + k)
    for c in rng.uniform(0.3, 5.0, 40):
        put(tone(rng.uniform(300, 700), 0.08, 0.02, 0.18), s1 + c)  # 泡のプツプツ
    p1 = tl["step1_pause"]
    put(tick(), p1)
    for i in range(14):  # ドーナツが1%ずつ増える音
        put(tone(600 + 40 * i, 0.06, 0.02, 0.15), p1 + 0.2 + i * 0.07)
    put(swish(), p1 + 4.0)
    # --- STEP2: 章 + ジュー音(強まる) + 圧力のドクンドクン
    s2 = tl["step2"]
    put(chapter(), s2)
    d = tl["step2_pause"] - s2
    n = int(d * SR)
    t = np.arange(n) / SR
    put(np.diff(np.r_[0, _noise(n, rng)]) * 0.35 * (0.05 + 0.25 * (t / d) ** 2), s2)
    for k in np.arange(0.8, 5.0, 0.6):
        put(tone(55, 0.25, 0.08, 0.6), s2 + k)
    put(swish(), s2 + 1.2)
    p2 = tl["step2_pause"]
    put(tick(), p2)
    put(sweep(200, 900, 4.5, 0.18), p2 + 1.0)  # グラフの曲線が伸びる上昇音
    put(ding(), p2 + 6.0)  # 180℃・10気圧に到達
    put(swish(), p2 + 8.0)
    # --- STEP3: 破裂 + 一時停止中のラベル音 + タイマーのチクタク
    s3 = tl["step3"]
    put(chapter(), s3)
    put(popsnd(), s3 + 0.2)
    put(hiss(), s3 + 0.25)
    p3 = tl["step3_pause"]
    put(tick(), p3 + 0.05)
    put(tone(2500, 0.15, 0.01, 0.5) + noise(0.15, 0.7) * env(int(0.15 * SR), 0.01) * 0.6, p3 + 2.2)  # 亀裂「パキッ」
    put(hiss(1.2, 0.3), p3 + 3.8)  # 蒸気「シュー」
    put(tone(300, 0.3, 0.1, 0.3) + noise(0.3, 0.2) * env(int(0.3 * SR), 0.08) * 0.3, p3 + 5.4)  # 泡「ポフッ」
    pp = tl["step3_play"]
    for k in np.arange(0.0, 4.4, 0.15):
        put(tone(3000, 0.03, 0.005, 0.2), pp + k)
    put(ding(), pp + 4.4)
    # --- STEP4: 章 + ? + 脚ドン + 跳ぶビヨン + 20G ドーン
    s4 = tl["step4"]
    put(chapter(), s4)
    put(sweep(400, 700, 0.3, 0.15), s4 + 2.6)  # 「でしょう？」の問いかけ
    p4 = tl["step4_pause"]
    put(tick(), p4)
    put(thud(), p4 + 4.0)
    put(boing(), p4 + 5.8)
    put(impact(), p4 + 9.0)
    put(swish(), p4 + 1.0)
    e4 = tl["step4_end"]
    put(sweep(300, 1200, 0.6, 0.2), e4 + 0.1)
    for k in range(6):  # キラキラ
        put(tone(2000 + 300 * k, 0.3, 0.1, 0.08), e4 + 0.5 + 0.08 * k)
    # --- まとめ
    sm = tl["summary"]
    put(chapter(), sm)
    for i, rt in enumerate(ROW_T):
        put(tone(660 + 110 * i, 0.25, 0.06, 0.3), sm + rt)
    put(sum(tone(f, 2.0, 0.5, 0.12) for f in (880, 1320, 1760)), sm + 7.2)
    return out[: int(total * SR)] / (np.abs(out).max() / 0.8)


def main():
    tl = timeline()
    total = tl["total"]
    wav = OUT / "ep01_v4_sfx.wav"
    write_wav(wav, build_sfx(tl))
    inputs = ["-i", str(VIDEO), "-i", str(wav)]
    fc, mix = [f"[1:a]volume={SFX_VOL}[sfx]"], ["[sfx]"]
    idx = 2
    for n, tag, off in NARRATION:
        inputs += ["-i", str(SRC / f"ep01_na{n}.mp3")]
        d = int((tl[tag] + off) * 1000)
        fc.append(f"[{idx}:a]volume={NA_VOL},adelay={d}|{d}[n{idx}]")
        mix.append(f"[n{idx}]")
        idx += 1
    # BGM(30秒)を3回つないで尺に合わせる
    bgm = SRC / "ep01_bgm.mp3"
    inputs += ["-i", str(bgm), "-i", str(bgm), "-i", str(bgm)]
    fc.append(f"[{idx}:a][{idx + 1}:a]acrossfade=d=3[b01];[b01][{idx + 2}:a]acrossfade=d=3,atrim=0:{total},"
              f"volume={BGM_VOL},afade=t=in:d=0.5,afade=t=out:st={total - 2}:d=2[bgm]")
    mix.append("[bgm]")
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{total},"
              "alimiter=limit=0.95[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(FINAL)],
                   check=True)
    print(f"wrote {FINAL} ({total:.1f}s)")


if __name__ == "__main__":
    main()
