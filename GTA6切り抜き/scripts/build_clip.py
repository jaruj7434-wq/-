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


def build(cfg, src, outdir):
    tmp = tempfile.mkdtemp()
    sw, sh = map(int, run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "csv=p=0", src]).stdout.strip().split(","))
    ch = cfg.get("crop_h", sh)  # 下部の元テロップを除くための高さ
    parts, times, t = [], [], 0.0
    for i, s in enumerate(cfg["segments"]):
        a, b = s["v"]
        d = b - a
        p = os.path.join(tmp, f"seg{i:02d}.mp4")
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(d), "-i", src]
        amap = "0:a"
        if "a" in s:
            cmd += ["-ss", str(s["a"]), "-t", str(d), "-i", src]
            amap = "1:a"
        cmd += ["-map", "0:v", "-map", amap, "-vf", "fps=30,format=yuv420p",
                "-af", f"afade=t=in:d=0.04,afade=t=out:st={d-0.06:.3f}:d=0.06,aresample=48000",
                "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", p]
        run(cmd)
        parts.append(p)
        times.append((t, t + d, s.get("x", 0.5)))
        t += d
    total = t
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    master = os.path.join(tmp, "master.mp4")
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
        e = str(round((sw - cw) * 0.5))
        for s0, s1, x in reversed(times):
            e = f"if(between(t,{s0:.3f},{s1:.3f}),{round((sw - cw) * x)},{e})"
        return e

    title = [tf(f"title{j}", l) for j, l in enumerate(cfg["title"])]
    hook = [tf(f"hook{j}", l) for j, l in enumerate(cfg["hook"])]
    outro = [tf(f"outro{j}", l) for j, l in enumerate(cfg["outro"])]
    credit = tf("credit", cfg["credit"])
    labels = []
    for i, s in enumerate(cfg["segments"]):
        if s.get("l1") or s.get("l2"):
            labels.append((times[i][0], times[i][1], tf(f"l1_{i}", s.get("l1", "")), tf(f"l2_{i}", s.get("l2", ""))))
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
    o.append(dt(title[1], "(w-tw)/2", 270, 84, "white", 10, font=F_TITLE, bcolor=pink))
    if len(title) > 2:
        o.append(dt(title[2], "(w-tw)/2", 395, 60, "white", 8))
    o.append(dt(hook[0], "(w-tw)/2", 1415, 92, "white", 10, hook_en, F_TITLE))
    o.append(dt(hook[1], "(w-tw)/2", 1540, 110, "yellow", 12, hook_en, F_TITLE, pink))
    for s0, s1, f1, f2 in labels:
        en = f"between(t,{s0:.3f},{s1:.3f})"
        o.append(dt(f1, "(w-tw)/2", 1410, 64, "yellow", 8, en, F_TITLE))
        o.append(dt(f2, "(w-tw)/2", 1505, 80, "white", 10, en))
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
    h.append(dt(title[1], 40, 130, 56, "white", 7, font=F_TITLE, bcolor=pink))
    h.append(dt(hook[0], "(w-tw)/2", 800, 80, "white", 9, hook_en, F_TITLE))
    h.append(dt(hook[1], "(w-tw)/2", 905, 100, "yellow", 10, hook_en, F_TITLE, pink))
    for s0, s1, f1, f2 in labels:
        en = f"between(t,{s0:.3f},{s1:.3f})"
        h.append(dt(f1, "(w-tw)/2", 830, 56, "yellow", 7, en, F_TITLE))
        h.append(dt(f2, "(w-tw)/2", 915, 76, "white", 9, en))
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
