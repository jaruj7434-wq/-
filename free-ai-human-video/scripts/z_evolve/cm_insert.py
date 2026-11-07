"""最新のZができたあとに入れる「高級車CM風」の映像と、その前後のトランジション。

流れ(成功した瞬間 = 0秒):
  0.00〜T_TR   … 光の帯が斜めに走って画面が白くなる(おしゃれなトランジション)
  T_TR〜       … CM風の映像(Higgs Field の Seedance 2.5 で作った5秒の縦型動画 cm.mp4)。白からふわっと始まる
  CMの最後    … Zが画面に突っ込んでくる → ヘッドライトがまぶしく光り、画面が真っ白になる
  その後       … 白い光がすっと引いて、いつもの発表会の演出
光の帯・ライトのまぶしさ・音はすべてプログラムで作る。
"""
import math
import os
import subprocess
import wave

import cairo
import numpy as np

T_TR = 0.45          # トランジションの長さ
GLARE = 0.75         # CMの最後、ライトがまぶしくなって真っ白になるまで
WHITE_OUT = 0.8      # 発表会の演出の最初、白い光が引いていく時間


def cm_length(path):
    if not os.path.exists(path):
        return 0.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout
    return float(out)


class CM:
    def __init__(self, path, W, H, fps, seed):
        self.path, self.W, self.H, self.fps = path, W, H, fps
        self.len = cm_length(path)
        self.reveal_off = T_TR + self.len           # 発表会の演出が始まる時刻(成功からの秒数)
        self.proc = None
        self.last = None
        self.impact = (W / 2, H * 0.52)             # 車がぶつかる場所(画面の真ん中あたり)

    # ------------------------------------------------ CMの映像を1コマずつ読む
    def _open(self):
        vf = (f"fps={self.fps},scale={self.W}:{self.H}:force_original_aspect_ratio=increase,"
              f"crop={self.W}:{self.H},format=bgra")
        self.proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", self.path, "-vf", vf,
                                      "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=subprocess.PIPE)

    def frame(self):
        if self.proc is None:
            self._open()
        n = self.W * self.H * 4
        buf = self.proc.stdout.read(n)
        if len(buf) == n:
            data = bytearray(buf)
            self.last = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, self.W, self.H, self.W * 4)
            self._keep = data   # 画像のメモリを持っておく
        return self.last


    # ------------------------------------------------ 描画
    def draw_transition(self, ctx, age):
        """成功の瞬間 → CM: 光の帯が斜めに走り、最後は真っ白に。"""
        W, H = self.W, self.H
        k = age / T_TR
        x = -W + 3 * W * k
        g = cairo.LinearGradient(x - 500, 0, x + 500, H * 0.4)
        g.add_color_stop_rgba(0, 1, 1, 1, 0)
        g.add_color_stop_rgba(0.5, 1, 0.98, 0.92, 0.95)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g)
        ctx.paint()
        ctx.set_source_rgba(1, 1, 1, k ** 3)
        ctx.paint()

    def draw_cm(self, ctx, age):
        """CMの映像。白からふわっと始まり、上下に細い黒帯(映画のような雰囲気)。最後はひびが入る。"""
        W, H = self.W, self.H
        a = age - T_TR
        img = self.frame()
        left = self.len - a
        if img is not None:
            ctx.set_source_surface(img, 0, 0)
            ctx.paint()
        if a < 0.35:
            ctx.set_source_rgba(1, 1, 1, 1 - a / 0.35)
            ctx.paint()
        bar = 70 * min(1.0, a / 0.4)
        ctx.set_source_rgb(0, 0, 0)
        ctx.rectangle(0, 0, W, bar)
        ctx.rectangle(0, H - bar, W, bar)
        ctx.fill()
        if left < GLARE:   # ライトがまぶしく光って真っ白に
            self._glare(ctx, 1 - left / GLARE)

    def _glare(self, ctx, k):
        W, H = self.W, self.H
        cx, cy = self.impact
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_ADD)
        r = 250 + 1500 * k ** 1.3   # 中心からあふれる光
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
        g.add_color_stop_rgba(0, 1, 1, 1, min(1.0, 0.4 + 0.8 * k))
        g.add_color_stop_rgba(0.35, 0.85, 0.92, 1, 0.55 * k)
        g.add_color_stop_rgba(1, 0.6, 0.75, 1, 0)
        ctx.set_source(g)
        ctx.paint()
        for sy, a in ((0.05, 0.9), (0.012, 1.0)):   # 横に長い光の筋(アナモルフィックフレア)
            ctx.save()
            ctx.translate(cx, cy)
            ctx.scale(1.0, sy)
            rr = 300 + 1300 * k
            g = cairo.RadialGradient(0, 0, 0, 0, 0, rr)
            g.add_color_stop_rgba(0, 0.9, 0.95, 1, a * k)
            g.add_color_stop_rgba(1, 0.4, 0.6, 1, 0)
            ctx.set_source(g)
            ctx.arc(0, 0, rr, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()
        ctx.restore()
        ctx.set_source_rgba(1, 1, 1, k ** 2.5)   # 最後は真っ白
        ctx.paint()

    def draw_whiteout(self, ctx, age_r):
        """発表会の演出の最初:真っ白な光がすっと引いていく。"""
        if age_r < WHITE_OUT:
            k = age_r / WHITE_OUT
            ctx.set_source_rgba(1, 1, 1, (1 - k) ** 1.6)
            ctx.paint()


# ---------------------------------------------------------------- 音
def cm_audio(path, sr):
    """CMの音(エンジン音)を取り出す。モノラル・sr Hz。"""
    if not os.path.exists(path):
        return None
    tmp = path + ".wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sr), tmp], check=False)
    if not os.path.exists(tmp):
        return None
    with wave.open(tmp) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    os.remove(tmp)
    return x


def whoosh(sr, dur=T_TR + 0.1, seed=5):
    """トランジションの「シュワッ」。高くなっていく風の音。"""
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    t = np.arange(n) / sr
    x = rng.normal(0, 1, n)
    out = np.zeros(n)
    k0 = 40
    for i in range(0, n, 2400):   # だんだん高い音を残す(移動平均の幅を小さくしていく)
        k = max(2, int(k0 * (1 - i / n)))
        seg = x[i:i + 2400]
        out[i:i + 2400] = seg - np.convolve(seg, np.ones(k) / k, "same")
    return out * (t / dur) ** 2 * 0.6


def light_swell(sr, dur=GLARE + 0.5, seed=9):
    """ライトがまぶしくなるときの「フワーン」と高くなる光の音と、真っ白になった瞬間のやわらかい「シャーン」。"""
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    t = np.arange(n) / sr
    k = np.minimum(1, t / GLARE)
    f = 400 + 2600 * k ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / sr) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / sr)
    noise = rng.normal(0, 1, n)
    air = noise - np.convolve(noise, np.ones(4) / 4, "same")
    swell = (0.35 * tone + 0.6 * air) * k ** 2.5 * np.where(t < GLARE, 1.0, np.exp(-(t - GLARE) * 6))
    i0 = int(GLARE * sr)   # 真っ白になった瞬間
    m = n - i0
    tt = np.arange(m) / sr
    shine = sum(np.sin(2 * np.pi * f0 * tt) * np.exp(-tt * 4) for f0 in (1568, 2093, 2637, 3136)) * 0.25
    swell[i0:] += shine
    return swell / np.abs(swell).max()
