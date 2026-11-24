#!/usr/bin/env python3
"""日本語ナレーション付きショートを作る。

使い方: python3 -I scripts/build_narrated.py <config.json> <元動画.mp4> <出力ディレクトリ>

config の segments は、ナレーション1文ごとに:
  narr: ナレーション音声ファイル(config からの相対パス可)
  clips: [[開始, 終了], ...]  映像の候補区間。ナレーションの長さに合わせて各区間を均等に使う
  game_audio: true/false  元動画の音(ゲーム音)を小さく残すか(元のナレーションが入る区間は false)
  x, free_crop, l1, l2: build_clip.py と同じ(クロップ位置・テロップ)
全体: narr_speed(ナレーションの速さ倍率), gap(文の間の秒数), game_vol(ゲーム音の音量)
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_clip import render, run  # noqa: E402


def dur(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout)


def build(cfg, cfg_dir, src, outdir):
    tmp = tempfile.mkdtemp()
    sw, sh = map(int, run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "csv=p=0", src]).stdout.strip().split(","))
    ch = cfg.get("crop_h", sh)
    speed = cfg.get("narr_speed", 1.0)
    gap = cfg.get("gap", 0.15)
    gvol = cfg.get("game_vol", 0.12)
    parts, times, t = [], [], 0.0
    for i, s in enumerate(cfg["segments"]):
        narr = os.path.join(cfg_dir, s["narr"])
        # ナレーションの前後の無音を詰め、速さを調整
        nw = os.path.join(tmp, f"n{i:02d}.wav")
        run(["ffmpeg", "-v", "error", "-y", "-i", narr, "-af",
             "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
             "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
             f"atempo={speed},aresample=48000", "-ac", "2", nw])
        d = round((dur(nw) + gap) * 30) / 30
        clips = s["clips"]
        each = d / len(clips)
        vparts = []
        for j, (c0, c1) in enumerate(clips):
            ln = min(each, c1 - c0) if j < len(clips) - 1 else d - each * (len(clips) - 1)
            vp = os.path.join(tmp, f"v{i:02d}_{j}.mkv")
            vol = gvol if s.get("game_audio", True) else 0
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{c0:.3f}", "-t", f"{ln:.4f}", "-i", src,
                 "-vf", "fps=30,format=yuv420p",
                 "-af", f"volume={vol},aresample=48000,apad,atrim=0:{ln:.4f},afade=t=in:d=0.05,"
                        f"afade=t=out:st={max(0, ln-0.08):.4f}:d=0.08",
                 "-ac", "2", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "pcm_s16le", vp])
            vparts.append(vp)
        lst = os.path.join(tmp, f"l{i:02d}.txt")
        with open(lst, "w") as f:
            f.writelines(f"file '{p}'\n" for p in vparts)
        vcat = os.path.join(tmp, f"vc{i:02d}.mkv")
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vcat])
        # ゲーム音 + ナレーション(先頭から)を合成し、長さを d に揃える
        p = os.path.join(tmp, f"seg{i:02d}.mkv")
        run(["ffmpeg", "-v", "error", "-y", "-i", vcat, "-i", nw, "-filter_complex",
             f"[0:a][1:a]amix=inputs=2:duration=first:normalize=0,atrim=0:{d:.4f}[a]",
             "-map", "0:v", "-map", "[a]", "-t", f"{d:.4f}", "-c:v", "copy", "-c:a", "pcm_s16le", p])
        parts.append(p)
        times.append((t, t + d, s.get("x", cfg.get("x", 0.5)), s.get("free_crop", False)))
        print(f"seg{i:02d}: {d:.2f}s  clips={clips}")
        t += d
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    master = os.path.join(tmp, "master.mkv")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", master])
    render(cfg, master, times, t, sw, ch, tmp, outdir)


if __name__ == "__main__":
    cfg_path = os.path.abspath(sys.argv[1])
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    build(cfg, os.path.dirname(cfg_path), os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3]))
