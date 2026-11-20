#!/usr/bin/env python3
"""GTA6切り抜き: LunarGaming「15 Helicopter & Plane Spawn Locations」からショートを作る。

使い方:
  python3 -I scripts/build_short.py <元動画.mp4> <出力ディレクトリ> <名前>
縦型 (1080x1920) と横型 (1920x1080) の両方を書き出す。音量は -14 LUFS (2パス loudnorm)。
"""
import json
import os
import subprocess
import sys
import tempfile

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

# (開始秒, 終了秒, 1行目ラベル, 2行目ラベル) — 元動画のチャプター(郡)に合わせたラベル
SEGMENTS = [
    (0.0, 5.1, None, None),  # フック: 夜のバイスシティ空撮 + 「全部のヘリと飛行機の場所を見せる」ナレーション
    (65.0, 69.0, "No.1  マリアナ郡", "海沿いのヘリポート"),
    (86.5, 90.5, "No.2  マリアナ郡", "街中のヘリポート"),
    (119.0, 123.0, "No.3  マリアナ郡", "草地の複葉機"),
    (145.0, 149.0, "No.4  マリアナ郡", "滑走路のスタント機"),
    (184.0, 188.0, "No.5  マリアナ郡", "格納庫前の水上飛行機"),
    (210.0, 214.0, "No.6  ケリー郡", "荒れ地のヘリポート"),
    (235.5, 239.5, "No.7  ケリー郡", "原っぱの小型機"),
    (293.0, 297.0, "No.8  ラモックス郡", "夜のヘリポート"),
    (374.0, 380.0, "No.9  レオナード郡", "水上ヘリ"),
]

TITLE = ["GTA6", "ヘリ&飛行機が", "タダで手に入る場所"]
HOOK = ["手配度ゼロで", "乗り放題!"]
OUTRO = ["全15か所は", "概要欄の元動画で!"]
CREDIT = "素材: LunarGaming (YouTube / CC BY)"


def run(cmd):
    print("+", " ".join(cmd[:6]), "...", flush=True)
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def write_text(tmp, name, text):
    p = os.path.join(tmp, name + ".txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def dt(textfile, x, y, size, color="white", border=8, enable=None):
    s = (f"drawtext=fontfile={FONT}:textfile={textfile}:x={x}:y={y}:fontsize={size}:"
         f"fontcolor={color}:borderw={border}:bordercolor=black")
    if enable:
        s += f":enable='{enable}'"
    return s


def build(src, outdir, name):
    tmp = tempfile.mkdtemp()
    # 1) 各カットを切り出して連結(テキストなしのマスター 640x360)
    parts = []
    starts = []  # マスター上での各カット開始時刻
    t = 0.0
    for i, (a, b, *_rest) in enumerate(SEGMENTS):
        d = b - a
        p = os.path.join(tmp, f"seg{i:02d}.mp4")
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-i", src, "-t", str(d),
             "-vf", "fps=30,format=yuv420p",
             "-af", f"afade=t=in:d=0.04,afade=t=out:st={d-0.06}:d=0.06,aresample=48000",
             "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", p])
        parts.append(p)
        starts.append((t, t + d))
        t += d
    total = t
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    master = os.path.join(tmp, "master.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", master])

    # 2) loudnorm 1パス目(計測)。冒頭ナレーションと静かな環境音の差が大きいので先にコンプで均す
    pre = "acompressor=threshold=0.03:ratio=6:attack=5:release=200:makeup=3"
    r = run(["ffmpeg", "-hide_banner", "-i", master, "-af",
             pre + ",loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"])
    js = r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1]
    m = json.loads(js)
    af = (pre + f",loudnorm=I=-14:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']}:linear=true,aresample=48000")

    # テキストファイル
    tf = {}
    for k, lines in (("title", TITLE), ("hook", HOOK), ("outro", OUTRO)):
        for j, l in enumerate(lines):
            tf[f"{k}{j}"] = write_text(tmp, f"{k}{j}", l)
    tf["credit"] = write_text(tmp, "credit", CREDIT)
    tf["title_h"] = write_text(tmp, "title_h", TITLE[1] + TITLE[2])
    labels = []
    for i, (_a, _b, l1, l2) in enumerate(SEGMENTS):
        if l1:
            labels.append((starts[i], write_text(tmp, f"l1_{i}", l1), write_text(tmp, f"l2_{i}", l2)))
    hook_en = "between(t,0.15,5.1)"
    outro_en = f"between(t,{starts[-1][0]+2.5},{total})"

    # 3) 縦型 1080x1920: ぼかし背景 + 中央 4:3 クロップ(主役は画面中央)
    v = []
    v.append("[0:v]split[a][b]")
    v.append("[a]scale=-2:1920:flags=bicubic,crop=1080:1920,boxblur=20:2,eq=brightness=-0.15[bg]")
    v.append("[b]crop=480:360:80:0,scale=1080:810:flags=lanczos,unsharp=5:5:0.8[fg]")
    o = ["[bg][fg]overlay=0:555"]
    o.append(dt(tf["title0"], "(w-tw)/2", 120, 120, "yellow", 10))
    o.append(dt(tf["title1"], "(w-tw)/2", 270, 92))
    o.append(dt(tf["title2"], "(w-tw)/2", 385, 92))
    o.append(dt(tf["hook0"], "(w-tw)/2", 1420, 100, "white", 10, hook_en))
    o.append(dt(tf["hook1"], "(w-tw)/2", 1550, 120, "yellow", 12, hook_en))
    for (s, e), f1, f2 in labels:
        en = f"between(t,{s},{e})"
        o.append(dt(f1, "(w-tw)/2", 1420, 72, "yellow", 8, en))
        o.append(dt(f2, "(w-tw)/2", 1520, 96, "white", 10, en))
    o.append(dt(tf["outro0"], "(w-tw)/2", 1660, 64, "white", 8, outro_en))
    o.append(dt(tf["outro1"], "(w-tw)/2", 1745, 64, "yellow", 8, outro_en))
    o.append(dt(tf["credit"], "(w-tw)/2", 1850, 30, "white", 4))
    vf = ";".join(v) + ";" + ",".join(o) + ",format=yuv420p[v]"
    out_v = os.path.join(outdir, f"{name}_vertical.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", master, "-filter_complex", vf, "-map", "[v]", "-map", "0:a",
         "-af", af, "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-r", "30",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_v])

    # 4) 横型 1920x1080
    h = ["scale=1920:1080:flags=lanczos,unsharp=5:5:0.6"]
    h.append(dt(tf["title0"], 50, 40, 90, "yellow", 9))
    h.append(dt(tf["title_h"], 50, 145, 64))  # 「ヘリ&飛行機がタダで手に入る場所」
    h.append(dt(tf["hook0"], "(w-tw)/2", 820, 80, "white", 9, hook_en))
    h.append(dt(tf["hook1"], "(w-tw)/2", 920, 100, "yellow", 10, hook_en))
    for (s, e), f1, f2 in labels:
        en = f"between(t,{s},{e})"
        h.append(dt(f1, "(w-tw)/2", 840, 60, "yellow", 7, en))
        h.append(dt(f2, "(w-tw)/2", 920, 84, "white", 9, en))
    h.append(dt(tf["outro0"], "w-tw-60", 860, 56, "white", 7, outro_en))
    h.append(dt(tf["outro1"], "w-tw-60", 935, 56, "yellow", 7, outro_en))
    h.append(dt(tf["credit"], "w-tw-30", 30, 28, "white", 4))
    out_h = os.path.join(outdir, f"{name}_horizontal.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", master, "-vf", ",".join(h) + ",format=yuv420p",
         "-af", af, "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-r", "30",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_h])
    print("total", round(total, 2), "sec")
    print(out_v)
    print(out_h)


if __name__ == "__main__":
    build(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), sys.argv[3])
