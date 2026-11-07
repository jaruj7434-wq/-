"""最新のZができたあとに入れる「高級車CM風」の映像と、その前後のトランジション。

流れ(成功した瞬間 = 0秒):
  0.00〜T_TR   … 光の帯が斜めに走って画面が白くなる(おしゃれなトランジション)
  T_TR〜       … CM風の映像(Higgs Field の Seedance 2.5 で作った5秒の縦型動画 cm.mp4)。白からふわっと始まる
  CMの最後    … Zが画面に突っ込んでくる → 画面のガラスにひびが入り、破片になって飛び散る
  その後       … 割れたガラスの向こうから、いつもの発表会の演出
ひび・破片・光の帯・ガラスの割れる音はすべてプログラムで作る。
"""
import math
import os
import subprocess
import wave

import cairo
import numpy as np

T_TR = 0.45          # トランジションの長さ
CRACK = 0.3          # CMの最後、ひびが入ってから割れるまで
SHATTER = 1.1        # 破片が飛び散る時間


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
        rng = np.random.default_rng(seed + 31337)
        self.cracks = self._make_cracks(rng)
        self.shards = self._make_shards(rng)

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

    # ------------------------------------------------ ひびと破片の形
    def _make_cracks(self, rng):
        cx, cy = self.impact
        lines = []
        for i in range(16):   # 中心から放射状にのびるひび(ジグザグ)
            a = i * 2 * math.pi / 16 + rng.uniform(-0.12, 0.12)
            pts = [(cx, cy)]
            r = 0.0
            while r < 1500:
                r += rng.uniform(60, 140)
                aa = a + rng.uniform(-0.08, 0.08)
                pts.append((cx + r * math.cos(aa), cy + r * math.sin(aa)))
            lines.append(pts)
        rings = [rng.uniform(70, 110), rng.uniform(190, 260), rng.uniform(360, 460)]
        return lines, rings

    def _make_shards(self, rng):
        cx, cy = self.impact
        n_ang = 16
        radii = [0, 90, 220, 400, 650, 950, 1500]
        angs = [i * 2 * math.pi / n_ang + rng.uniform(-0.1, 0.1) for i in range(n_ang)]
        shards = []
        for j in range(len(radii) - 1):
            for i in range(n_ang):
                a0, a1 = angs[i], angs[(i + 1) % n_ang] + (2 * math.pi if i == n_ang - 1 else 0)
                r0, r1 = radii[j], radii[j + 1]
                pts = [(cx + r0 * math.cos(a0), cy + r0 * math.sin(a0)), (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0)),
                       (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1)), (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1))]
                mx = sum(p[0] for p in pts) / 4
                my = sum(p[1] for p in pts) / 4
                d = math.hypot(mx - cx, my - cy) + 1
                sp = rng.uniform(700, 1500) * (0.6 + 0.4 * min(1.0, 300 / d))
                vx, vy = (mx - cx) / d * sp, (my - cy) / d * sp - rng.uniform(100, 400)
                shards.append((pts, mx, my, vx, vy, rng.uniform(-9, 9), rng.uniform(0.0, 0.08)))
        return shards

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
        left = self.len - a
        if left < CRACK:   # ひびが入る
            self._draw_cracks(ctx, 1 - left / CRACK)

    def _draw_cracks(self, ctx, k):
        lines, rings = self.cracks
        cx, cy = self.impact
        ctx.set_line_join(cairo.LINE_JOIN_MITER)
        for w, col in ((5, (0, 0, 0, 0.35)), (2, (1, 1, 1, 0.95))):
            ctx.set_line_width(w)
            ctx.set_source_rgba(*col)
            for pts in lines:
                n = max(2, int(len(pts) * min(1.0, 0.3 + k)))
                ctx.move_to(*pts[0])
                for p in pts[1:n]:
                    ctx.line_to(*p)
                ctx.stroke()
            for r in rings:
                if r < 150 + 400 * k:
                    ctx.arc(cx, cy, r, 0, 2 * math.pi)
                    ctx.stroke()
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, 160)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.9 * k)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g)
        ctx.arc(cx, cy, 160, 0, 2 * math.pi)
        ctx.fill()

    def draw_shatter(self, ctx, age_r):
        """発表会の演出の上で、CMの最後の画面が破片になって飛び散る。"""
        if self.last is None or age_r > SHATTER:
            return
        cx, cy = self.impact
        if age_r < 0.12:   # ぶつかった瞬間の白い光
            ctx.set_source_rgba(1, 1, 1, 0.9 * (1 - age_r / 0.12))
            ctx.paint()
        for pts, mx, my, vx, vy, spin, delay in self.shards:
            a = age_r - delay
            if a < 0:
                a = 0.0
            ox = vx * a
            oy = vy * a + 0.5 * 2600 * a * a
            al = max(0.0, 1 - age_r / SHATTER)
            ctx.save()
            ctx.translate(mx + ox, my + oy)
            ctx.rotate(spin * a)
            sc = max(0.2, 1 - 0.5 * a)
            ctx.scale(sc, sc)
            ctx.translate(-mx, -my)
            ctx.new_path()
            ctx.move_to(*pts[0])
            for p in pts[1:]:
                ctx.line_to(*p)
            ctx.close_path()
            ctx.save()
            ctx.clip_preserve()
            ctx.set_source_surface(self.last, 0, 0)
            ctx.paint_with_alpha(al)
            ctx.restore()
            ctx.set_source_rgba(1, 1, 1, 0.8 * al)   # 破片のふちが光る
            ctx.set_line_width(2.5)
            ctx.stroke()
            ctx.restore()


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


def glass_crash(sr, seed=9):
    """ガラスが割れる「ガシャーン!パリパリ」。"""
    rng = np.random.default_rng(seed)
    n = int(1.6 * sr)
    t = np.arange(n) / sr
    x = rng.normal(0, 1, n)
    hi = x - np.convolve(x, np.ones(3) / 3, "same")
    out = hi * np.exp(-t * 7) * 0.9
    boom = np.sin(2 * np.pi * np.cumsum(60 + 120 * np.exp(-t * 20)) / sr) * np.exp(-t * 6)
    out += boom * 0.8
    for _ in range(70):   # 細かい破片のチリンチリン
        i = int(rng.uniform(0.02, 1.3) * sr)
        f = rng.uniform(2500, 7000)
        m = int(0.08 * sr)
        tt = np.arange(m) / sr
        ping = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 60) * rng.uniform(0.1, 0.35) * np.exp(-i / sr * 1.5)
        out[i:i + m] += ping[: n - i]
    return out / np.abs(out).max()
