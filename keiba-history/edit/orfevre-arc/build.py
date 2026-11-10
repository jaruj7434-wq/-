#!/usr/bin/env python3
"""オルフェーヴル凱旋門賞 (名前を最後に明かす) — 完成版の書き出し。

前提: edit/orfevre-arc/narration.sh を先に実行 (vo/line_XX.mp3 と narration_full.m4a ができる)
素材: assets/output/orfevre-arc/clips/ (Higgs Field の job は prompts/orfevre-arc/production-log.md)
  V01..V19 = 再現 (Kling) / T03 T08 T10 T12 T16 = 谷上の口の動き (Wan 2.7、音声は先頭0.1秒の無音つき)
  bgm.m4a / title.png (最後の「金色の怪物 オルフェーヴル」)
映像は各行のナレーションの長さ (行間の間を含む) に合わせて並べる。谷上の動画は等速で使う。
"""
import subprocess, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "assets/output/orfevre-arc"
VO, CL = ROOT / "vo", ROOT / "clips"
OUT = ROOT / "orfevre_arc_v1.mp4"
# narration.sh と同じ行間
GAPS = [0.4, 1.0, 0.6, 0.5, 0.5, 0.9, 0.5, 0.8, 0.9, 0.6, 0.8, 0.6, 0.6, 0.8, 0.6, 0.8, 1.4, 1.0]
TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse")
# 行 → (クリップ, 種類)  kling / wan / memory
SHOTS = {1: ("V01", "kling"), 2: ("V02", "kling_white"), 3: ("T03", "wan"), 4: ("V04", "kling"),
         5: ("V05", "kling"), 6: ("V06", "kling"), 7: ("V07", "kling"), 8: ("T08", "wan"),
         9: ("V09", "kling"), 10: ("T10", "wan"), 11: ("V11", "kling"), 12: ("T12", "wan"),
         13: ("V13", "kling"), 14: ("V14", "kling"), 15: ("V15", "kling"), 16: ("T16", "wan"),
         17: ("V01", "memory"), 18: ("V18", "kling")}
TAIL = ("V19", 3.0)  # 谷上が本を閉じる (セリフなし)

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]).decode().strip())

def trimmed_len(p):
    tmp = VO / "_t.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-af", TRIM, str(tmp)], check=True)
    d = dur(tmp); tmp.unlink(); return d

segs, t, starts = [], 0.0, {}
for i in range(1, 19):
    L = trimmed_len(VO / f"line_{i:02d}.mp3") + GAPS[i - 1]
    starts[i] = t; segs.append((i, L)); t += L
narr_total = t
total = narr_total + TAIL[1]

args, chains, n = [], [], 0
def add(name, kind, L):
    global n
    src = CL / f"{name}.mp4"
    ss = 0.1 if kind == "wan" else 0.0
    args.extend(["-ss", str(ss), "-i", str(src)])
    f = f"[{n}:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=30,format=yuv420p"
    if kind == "memory":   # 思い出: ゆっくり・淡い色・周辺減光
        f += ",setpts=1.6*PTS,eq=saturation=0.55:brightness=0.03,vignette=angle=PI/4,gblur=sigma=0.6"
    f += f",tpad=stop_mode=clone:stop_duration={L},trim=duration={L:.3f},setpts=PTS-STARTPTS"
    if kind == "kling_white":  # つかみ: 白く止まる
        f += f",fade=t=out:st={max(0, L - 0.6):.2f}:d=0.6:color=white"
    if kind == "memory":
        f += f",fade=t=in:st=0:d=0.3:color=white,fade=t=out:st={L - 0.3:.2f}:d=0.3:color=white"
    chains.append(f + f"[v{n}]"); n += 1

for i, L in segs:
    add(*SHOTS[i], L)
add(TAIL[0], "kling", TAIL[1])
vin = "".join(f"[v{k}]" for k in range(n))
title_i, narr_i, bgm_i = n, n + 1, n + 2
args += ["-loop", "1", "-t", f"{total:.2f}", "-i", str(CL / "title.png"),
         "-i", str(VO / "narration_full.m4a"), "-i", str(CL / "bgm.m4a")]
t18 = starts[18]
fc = (";".join(chains) + f";{vin}concat=n={n}:v=1:a=0[cat];"
      f"[{title_i}:v]format=rgba,fade=t=in:st={t18 + 0.3:.2f}:d=0.8:alpha=1[ttl];"
      f"[cat][ttl]overlay=0:0:enable='gte(t,{t18 + 0.3:.2f})',fade=t=in:st=0:d=0.5,"
      f"fade=t=out:st={total - 1.0:.2f}:d=1.0[vout];"
      f"[{narr_i}:a]aresample=48000,apad,atrim=0:{total:.2f}[na];"
      f"[{bgm_i}:a]aresample=48000,apad,atrim=0:{total:.2f},volume=0.20,"
      f"afade=t=in:st=0:d=1.0,afade=t=out:st={total - 3:.2f}:d=3[bg];"
      f"[na][bg]amix=inputs=2:duration=first:normalize=0[aout]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex", fc,
                "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-crf", "20", "-preset", "medium",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.2f}", str(OUT)], check=True)
print(json.dumps({"out": str(OUT), "total": round(total, 2), "reveal_at": round(t18, 2)}, ensure_ascii=False))
