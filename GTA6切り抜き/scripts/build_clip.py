#!/usr/bin/env python3
"""設定ファイル(JSON)からショート動画(縦型 1080x1920 / 横型 1920x1080)を作る汎用スクリプト。

使い方: python3 -I scripts/build_clip.py <config.json> <元動画.mp4> <出力ディレクトリ>

config 例は 05_meta/*_edit.json を参照。各セグメント:
  v: [開始, 終了]       映像の区間(秒)
  a: 開始秒(省略可)     別の区間の音声を使う場合(長さは映像と同じ)
  x: 0.0〜1.0(省略可)  クロップ位置(0=左端, 0.5=中央, 1=右端)
  l1, l2: テロップ1行目(小・黄色)/2行目(大・白)
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
F_TITLE = os.path.join(ROOT, "fonts", "DelaGothicOne-Regular.ttf")
F_BODY = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


class Envelope:
    """元動画の音量エンベロープ(10ms 単位)。カット点を無音の瞬間に寄せるのに使う。"""

    def __init__(self, src, sr=16000):
        import numpy as np
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                             check=True, capture_output=True).stdout
        x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        hop = sr // 100
        n = len(x) // hop
        rms = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1)) + 1e-6
        self.db = 20 * np.log10(rms)
        self.np = np

    def _quiet(self, t0, t1, need=0.12):
        """[t0,t1] 内で need 秒以上続く静かな区間の候補(中心時刻)を返す。"""
        np = self.np
        i0, i1 = max(0, int(t0 * 100)), min(len(self.db), int(t1 * 100))
        seg = self.db[i0:i1]
        if len(seg) == 0:
            return []
        thr = max(np.percentile(self.db[max(0, i0 - 300):i1 + 300], 20) + 6, -50)
        q = seg < thr
        k = int(need * 100)
        out, run_start = [], None
        for j, v in enumerate(list(q) + [False]):
            if v and run_start is None:
                run_start = j
            elif not v and run_start is not None:
                if j - run_start >= k:
                    out.append((i0 + run_start, i0 + j))
                run_start = None
        return out

    def snap_start(self, t, back=0.6, fwd=0.15):
        c = self._quiet(t - back, t + fwd)
        if not c:
            return max(0.0, t - 0.1)
        s, e = c[-1]  # 開始点より前で一番近い無音
        return max(s / 100, e / 100 - 0.08)  # 語頭の直前(少し余白を残す)

    def snap_end(self, t, back=0.1, fwd=1.0):
        c = self._quiet(t - back, t + fwd, need=0.3)  # 「ください」の「さい」など弱い語尾で切らない
        if not c:
            return t + 0.3
        s, e = c[0]  # 終了点より後で最初の無音
        return min(e / 100, s / 100 + 0.25)  # 語尾の直後(余韻を残す)


def build(cfg, src, outdir):
    tmp = tempfile.mkdtemp()
    sw, sh = map(int, run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "csv=p=0", src]).stdout.strip().split(","))
    ch = cfg.get("crop_h", sh)  # 下部の元テロップを除くための高さ
    env = Envelope(src) if cfg.get("snap", True) else None
    parts, times, t = [], [], 0.0
    for i, s in enumerate(cfg["segments"]):
        v0, v1 = s["v"]
        a0 = s.get("a", v0)
        a1 = a0 + (v1 - v0)
        if env:  # セリフの語頭・語尾を切らないよう、無音の瞬間に合わせて区間を調整
            n0, n1 = env.snap_start(a0), env.snap_end(a1)
            v0, v1 = v0 + (n0 - a0), v1 + (n1 - a1)
            a0, a1 = n0, n1
        d = round((v1 - v0) * 30) / 30  # フレーム境界に揃える(映像と音声の長さを一致させる)
        p = os.path.join(tmp, f"seg{i:02d}.mkv")
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{v0:.3f}", "-t", f"{d:.4f}", "-i", src,
               "-ss", f"{a0:.3f}", "-t", f"{d:.4f}", "-i", src,
               "-map", "0:v", "-map", "1:a", "-vf", "fps=30,format=yuv420p",
               "-af", f"aresample=48000,apad,atrim=0:{d:.4f},afade=t=in:d=0.03,afade=t=out:st={d-0.05:.4f}:d=0.05",
               "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "pcm_s16le", p]
        run(cmd)
        parts.append(p)
        times.append((t, t + d, s.get("x", cfg.get("x", 0.5)), s.get("free_crop", False)))
        print(f"seg{i:02d}: v {v0:.2f}-{v0+d:.2f}  a {a0:.2f}  ({d:.2f}s)")
        t += d
    total = t
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    master = os.path.join(tmp, "master.mkv")  # 音声は PCM のままつなぐ(AAC のつなぎ目の隙間を防ぐ)
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", master])

    # ラウドネス -14 LUFS(コンプ → 2パス loudnorm)
    pre = "acompressor=threshold=0.05:ratio=4:attack=5:release=200:makeup=2"
    r = run(["ffmpeg", "-hide_banner", "-i", master, "-af", pre + ",loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
             "-f", "null", "-"])
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    af = (pre + f",loudnorm=I=-14:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
          f"linear=true,aresample=48000")

    def tf(name, text):
        p = os.path.join(tmp, name + ".txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def dt(textfile, x, y, size, color="white", border=8, enable=None, font=F_BODY, bcolor="black"):
        s = (f"drawtext=fontfile={font}:textfile={textfile}:x={x}:y={y}:fontsize={size}:"
             f"fontcolor={color}:borderw={border}:bordercolor={bcolor}")
        return s + (f":enable='{enable}'" if enable else "")

    # セグメントごとのクロップ位置: x 式を区間ごとの if 連鎖で作る
    def xexpr(cw):
        lo = min(cfg.get("min_x", 0), sw - cw)
        off = lambda x, free=False: max(0 if free else lo, round((sw - cw) * x))
        e = str(off(cfg.get("x", 0.5)))
        for s0, s1, x, free in reversed(times):  # free_crop: その区間は min_x の制限なし
            e = f"if(between(t,{s0:.3f},{s1:.3f}),{off(x, free)},{e})"
        return e

    title = [tf(f"title{j}", l) for j, l in enumerate(cfg["title"])]
    hook = [tf(f"hook{j}", l) for j, l in enumerate(cfg["hook"])]
    outro = [tf(f"outro{j}", l) for j, l in enumerate(cfg["outro"])]
    credit = tf("credit", cfg["credit"])
    def em(text):  # 文字幅の目安(全角=1, 半角=0.55)
        return sum(0.55 if ord(ch) < 0x2E80 else 1.0 for ch in text) or 1

    labels = []
    for i, s in enumerate(cfg["segments"]):
        if s.get("l1") or s.get("l2"):
            labels.append((times[i][0], times[i][1], tf(f"l1_{i}", s.get("l1", "")), tf(f"l2_{i}", s.get("l2", "")),
                           em(s.get("l1", "")), em(s.get("l2", ""))))

    def fit(text, maxw, cap, k=1.0):  # はみ出さない文字サイズ(k: 書体の横幅係数。Dela Gothic は 1.12)
        return min(cap, int(maxw / (em(text) * k)))
    D = 1.12
    hook_en = f"between(t,0.1,{times[0][1]:.3f})"
    outro_en = f"between(t,{total - cfg.get('outro_sec', 4):.3f},{total})"
    pink = "0xE0137A"

    # 縦型: ぼかし背景 + 4:3 クロップ
    cw = round(ch * 4 / 3)
    v = ["[0:v]split[a][b]",
         "[a]scale=-2:1920:flags=bicubic,crop=1080:1920,boxblur=20:2,eq=brightness=-0.18[bg]",
         f"[b]crop={cw}:{ch}:'{xexpr(cw)}':0,scale=1080:810:flags=lanczos,unsharp=5:5:0.8[fg]"]
    o = ["[bg][fg]overlay=0:555"]
    o.append(dt(title[0], "(w-tw)/2", 110, 110, "yellow", 10, font=F_TITLE))
    o.append(dt(title[1], "(w-tw)/2", 270, fit(cfg["title"][1], 1000, 84, D), "white", 10, font=F_TITLE, bcolor=pink))
    if len(title) > 2:
        o.append(dt(title[2], "(w-tw)/2", 395, 60, "white", 8))
    o.append(dt(hook[0], "(w-tw)/2", 1415, fit(cfg["hook"][0], 1000, 92, D), "white", 10, hook_en, F_TITLE))
    o.append(dt(hook[1], "(w-tw)/2", 1540, fit(cfg["hook"][1], 1000, 110, D), "yellow", 12, hook_en, F_TITLE, pink))
    for s0, s1, f1, f2, w1, w2 in labels:
        en = f"between(t,{s0:.3f},{s1:.3f})"
        o.append(dt(f1, "(w-tw)/2", 1410, min(64, int(1000 / (w1 * D))), "yellow", 8, en, F_TITLE))
        o.append(dt(f2, "(w-tw)/2", 1505, min(80, int(960 / w2)), "white", 10, en))
    o.append(dt(outro[0], "(w-tw)/2", 1660, 58, "white", 8, outro_en))
    o.append(dt(outro[1], "(w-tw)/2", 1740, 58, "yellow", 8, outro_en))
    o.append(dt(credit, "(w-tw)/2", 1852, 28, "white", 4))
    vf = ";".join(v) + ";" + ",".join(o) + ",format=yuv420p[v]"
    name = cfg["name"]
    out_v = os.path.join(outdir, f"{name}_vertical.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", master, "-filter_complex", vf, "-map", "[v]", "-map", "0:a",
         "-af", af, "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-r", "30",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_v])

    # 横型: 16:9 クロップ(下部の元テロップを除く)
    hw = round(ch * 16 / 9)
    h = [f"crop={hw}:{ch}:'{xexpr(hw)}':0,scale=1920:1080:flags=lanczos,unsharp=5:5:0.6"]
    h.append(dt(title[0], 40, 30, 80, "yellow", 8, font=F_TITLE))
    h.append(dt(title[1], 40, 130, fit(cfg["title"][1], 1300, 56, D), "white", 7, font=F_TITLE, bcolor=pink))
    h.append(dt(hook[0], "(w-tw)/2", 800, fit(cfg["hook"][0], 1800, 80, D), "white", 9, hook_en, F_TITLE))
    h.append(dt(hook[1], "(w-tw)/2", 905, fit(cfg["hook"][1], 1800, 100, D), "yellow", 10, hook_en, F_TITLE, pink))
    for s0, s1, f1, f2, w1, w2 in labels:
        en = f"between(t,{s0:.3f},{s1:.3f})"
        h.append(dt(f1, "(w-tw)/2", 830, min(56, int(1700 / (w1 * D))), "yellow", 7, en, F_TITLE))
        h.append(dt(f2, "(w-tw)/2", 915, min(76, int(1500 / w2)), "white", 9, en))
    h.append(dt(outro[0], "w-tw-50", 860, 50, "white", 7, outro_en))
    h.append(dt(outro[1], "w-tw-50", 930, 50, "yellow", 7, outro_en))
    h.append(dt(credit, "w-tw-30", 30, 26, "white", 4))
    out_h = os.path.join(outdir, f"{name}_horizontal.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", master, "-vf", ",".join(h) + ",format=yuv420p",
         "-af", af, "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-r", "30",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_h])
    print(f"total {total:.1f} sec\n{out_v}\n{out_h}")


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        cfg = json.load(f)
    build(cfg, os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3]))
