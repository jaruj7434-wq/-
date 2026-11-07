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
CRACK = 0.22         # CMの最後、ひびが入ってから割れるまで
SHATTER = 1.4        # 破片が飛び散る時間


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
        if img is not None and left < CRACK:   # ひびが入る(画面がガラスの破片に分かれて少しずれる)
            self._draw_cracked(ctx, img, 1 - left / CRACK)
        elif img is not None:
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

    # ------------------------------------------------ 破片の形(ボロノイ分割:ぶつかった所ほど細かく、外ほど大きい)
    def _make_shards(self, rng):
        W, H = self.W, self.H
        cx, cy = self.impact
        pts = [(cx + rng.uniform(-4, 4), cy + rng.uniform(-4, 4))]
        while len(pts) < 150:
            r = 1500 * rng.uniform(0, 1) ** 1.9
            a = rng.uniform(0, 2 * math.pi)
            x, y = cx + r * math.cos(a), cy + r * math.sin(a) * 1.15
            if -40 < x < W + 40 and -40 < y < H + 40:
                pts.append((x, y))
        rect = [(-30, -30), (W + 30, -30), (W + 30, H + 30), (-30, H + 30)]
        shards = []
        for i, p in enumerate(pts):
            poly = rect
            for j, q in enumerate(pts):
                if i == j:
                    continue
                nx, ny = q[0] - p[0], q[1] - p[1]
                mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
                poly = _clip(poly, nx, ny, nx * mx + ny * my)
                if len(poly) < 3:
                    break
            if len(poly) < 3:
                continue
            gx = sum(v[0] for v in poly) / len(poly)
            gy = sum(v[1] for v in poly) / len(poly)
            d = math.hypot(gx - cx, gy - cy)
            ux, uy = ((gx - cx) / d, (gy - cy) / d) if d > 1 else (0.0, -1.0)
            near = max(0.0, 1 - d / 1400)
            shards.append({
                "poly": poly, "g": (gx, gy), "d": d, "u": (ux, uy),
                # ひびが入ったときの小さなずれ(中心ほど大きい)
                "jit": (rng.normal(0, 1.5 + 3 * near), rng.normal(0, 1.5 + 3 * near)),
                "jrot": rng.normal(0, 0.004 + 0.01 * near), "tint": rng.uniform(-0.06, 0.1),
                # 割れたあとの動き:手前(カメラ側)へ飛んでくる速さ、外向きの速さ、回転、3Dの傾き
                "vz": rng.uniform(0.5, 1.6) + 1.2 * near, "vr": rng.uniform(80, 380) * (0.4 + near),
                "spin": rng.normal(0, 1.8), "tilt": rng.uniform(1.5, 6.0) * rng.choice([-1, 1]),
                "axis": rng.uniform(0, math.pi), "ph": rng.uniform(0, 2 * math.pi),
                "delay": d / 5200.0,   # 割れが中心から外へ広がる
            })
        shards.sort(key=lambda s: s["vz"])   # 遠い(ゆっくり近づく)破片から描く
        dust = [(rng.uniform(0, 2 * math.pi), rng.uniform(200, 1400), rng.uniform(0.8, 2.6), rng.uniform(0, 1))
                for _ in range(260)]
        return shards, dust

    @staticmethod
    def _path(ctx, poly):
        ctx.new_path()
        ctx.move_to(*poly[0])
        for v in poly[1:]:
            ctx.line_to(*v)
        ctx.close_path()

    def _draw_cracked(self, ctx, img, k):
        """ひびが入った瞬間:画面がガラスの破片に分かれ、わずかにずれて光る(まだ飛ばない)。ひびは中心から外へ一気に走る。"""
        shards, _ = self.shards
        front = 120 + 1500 * k ** 1.4   # ひびの先が中心から外へ走る
        ctx.set_source_surface(img, 0, 0)
        ctx.paint()
        for s in shards:
            if s["d"] > front:
                continue
            gx, gy = s["g"]
            ctx.save()
            self._path(ctx, s["poly"])
            ctx.clip()
            ctx.translate(gx + s["jit"][0], gy + s["jit"][1])
            ctx.rotate(s["jrot"])
            ctx.translate(-gx, -gy)
            ctx.set_source_surface(img, 0, 0)
            ctx.paint()
            if s["tint"] > 0:   # 破片ごとに光の当たり方が少し違う
                ctx.set_source_rgba(1, 1, 1, s["tint"])
                ctx.paint()
            ctx.restore()
            self._path(ctx, s["poly"])
            ctx.set_source_rgba(0, 0, 0, 0.35)
            ctx.set_line_width(2.4)
            ctx.stroke_preserve()
            ctx.set_source_rgba(0.92, 0.96, 1, 0.75 * max(0.0, 1 - s["d"] / 1700))
            ctx.set_line_width(1.0)
            ctx.stroke()
        cx, cy = self.impact   # ぶつかった所は細かく砕けて白っぽい
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, 120)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.55 * k)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g)
        ctx.paint()

    def draw_shatter(self, ctx, age_r):
        """発表会の演出の上で、CMの最後の画面のガラスが割れ、破片がこちらへ飛んでくる(カメラがガラスを突き抜ける感じ)。
        破片はスローモーションのようにだんだんゆっくりになり、傾くたびに光を反射する。"""
        if self.last is None or age_r > SHATTER:
            return
        shards, dust = self.shards
        cx, cy = self.impact
        for s in shards:
            a = max(0.0, age_r - s["delay"])
            e = (1 - math.exp(-a * 3.2)) / 3.2          # だんだんゆっくり(スロー)になる時間
            sc = 1 + s["vz"] * e * 2.2                    # 手前へ近づくほど大きく
            gx, gy = s["g"]
            ux, uy = s["u"]
            px = cx + (gx - cx) * sc + ux * s["vr"] * e
            py = cy + (gy - cy) * sc + uy * s["vr"] * e + 420 * a * a
            al = max(0.0, min(1.0, 1 - (sc - 2.2) / 1.2)) * max(0.0, 1 - max(0.0, age_r - SHATTER * 0.45) / (SHATTER * 0.55))
            if al <= 0.01:
                continue
            tl = s["tilt"] * e
            ctx.save()
            ctx.translate(px, py)
            ctx.rotate(s["spin"] * e)
            ctx.rotate(s["axis"])
            ctx.scale(max(0.08, abs(math.cos(tl))), 1.0)   # 3Dで傾く(横につぶれて見える)
            ctx.rotate(-s["axis"])
            ctx.scale(sc, sc)
            ctx.translate(-gx, -gy)
            self._path(ctx, s["poly"])
            ctx.save()
            ctx.clip_preserve()
            ctx.set_source_surface(self.last, 0, 0)
            ctx.paint_with_alpha(al)
            spec = max(0.0, math.sin(tl + s["ph"])) ** 16   # 傾いた瞬間にキラッと光る
            if spec > 0.02:
                ctx.set_source_rgba(1, 1, 1, 0.4 * spec * al)
                ctx.paint()
            ctx.set_source_rgba(0.6, 0.75, 0.85, 0.08 * al)   # ガラスの厚みの青み
            ctx.paint()
            ctx.restore()
            ctx.set_source_rgba(1, 1, 1, 0.7 * al)          # 切り口が光る
            ctx.set_line_width(1.6 / sc)
            ctx.stroke()
            ctx.restore()
        for ang, v, sz, ph in dust:   # 細かいガラスの粉がキラキラ飛ぶ
            if age_r > 0.9:
                break
            d = v * (1 - math.exp(-age_r * 3)) / 3
            x, y = cx + d * math.cos(ang), cy + d * math.sin(ang) + 300 * age_r * age_r
            tw = 0.5 + 0.5 * math.sin(age_r * 40 + ph * 20)
            ctx.set_source_rgba(1, 1, 1, tw * (1 - age_r / 0.9))
            ctx.arc(x, y, sz, 0, 2 * math.pi)
            ctx.fill()
        if age_r < 0.06:   # ぶつかった瞬間だけ、ごく短く光る
            ctx.set_source_rgba(1, 1, 1, 0.45 * (1 - age_r / 0.06))
            ctx.paint()


def _clip(poly, nx, ny, c):
    """多角形を半平面 nx*x + ny*y <= c で切る。"""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        dp = nx * p[0] + ny * p[1] - c
        dq = nx * q[0] + ny * q[1] - c
        if dp <= 0:
            out.append(p)
        if (dp <= 0) != (dq <= 0):
            t = dp / (dp - dq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


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
