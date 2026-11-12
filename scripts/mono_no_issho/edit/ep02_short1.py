"""第2話ショート①「なくした傘、どこへ行く？」(9:16・約40秒)

本編の素材(3Dクリップ・2D図解・ElevenLabs ナレーション)を切り出して縦型に組み直す。
- ナレーションは 1.15 倍速、行間を詰めてテンポ重視
- 字幕はフレーズごとに大きく表示、キーワードを黄色で強調
- 最後は「持ち主が現れなかった傘は、」で音声を切り、静止画＋「フルはコメント欄から！」で本編へ誘導

  python3 scripts/mono_no_issho/edit/ep02_short1.py
"""
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ep01_build as B   # 第2話の設定は __main__ で ep02_build を読み込んで差し替える

SR, FPS = B.SR, B.FPS
VW, VH = 1080, 1920
TEMPO = 1.15
GAP = 0.08
# 出力先などは configure() で決める(他の話数のショートは configure を呼んでから main())
WORK = OUTF = NAR = None


def configure(name):
    global WORK, OUTF, NAR
    WORK = B.WORK / name
    OUTF = B.OUT / "shorts" / f"{B.OUT.name}_{name}.mp4"
    NAR = B.WORK / "el_tts"

TITLE = ["なくした傘、", "どこへ行く？"]

# (映像, ナレーション行番号, 音声の切り出し範囲(秒,原速), 2D図解の頭飛ばし(秒), 強調語[, 字幕の差し替え])
SEGS = [
    ("3d:k01_station_bench", 1, None, 0, ["傘をなくした"]),
    ("2d:counter", 2, None, 0, ["約28万本"]),
    ("3d:k03_train_seat", 3, None, 0, ["帰りません"]),
    ("2d:return_rate", 15, None, 5, ["約1%"]),
    ("2d:storage_rule", 17, None, 0, ["3か月"]),
    ("3d:k04_lost_storage", 18, None, 0, ["数が多くて", "安い"]),
    ("2d:storage_rule", 19, None, 4, ["2週間", "売ったり処分したり"]),
    ("3d:k05_cart_out", 22, (0.0, 2.20), 0, ["持ち主が現れなかった傘"]),
]
CTA_DUR = 3.6
CTA = ["2週間後、傘が向かう", "{\\c&H00D7FF&}“最後の場所”{\\c&HFFFFFF&}とは…？"]
CTA2 = ["フルはコメント欄から！", "▼ 本編で答え合わせ"]
CTA_AT = None   # 締めに止める映像の位置(秒)。None なら最後のカットの最終フレーム
CAPS = {22: ["持ち主が現れなかった傘は…"]}   # 字幕を差し替える行(音声を途中で切る行など)


def run(cmd):
    subprocess.run(cmd, check=True)


def load_line(i, rng):
    f = NAR / f"{i:02d}.mp3"
    af = []
    if rng:
        af.append(f"atrim={rng[0]}:{rng[1]},afade=t=out:st={rng[1] - 0.06}:d=0.06")
    af.append(f"atempo={TEMPO}")
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(f), "-af", ",".join(af), "-ac", "1",
                          "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    nz = np.where(np.abs(x) > 0.01)[0]
    return x[max(0, nz[0] - int(0.02 * SR)):min(len(x), nz[-1] + int(0.05 * SR))].copy()


def line_text(i):
    import json
    m = json.load(open(B.HF_MANIFEST, encoding="utf-8"))
    return B.subtitle_text(m[i]["line"])


def phrases(text):
    """読点・句点で区切ってフレーズにする(短すぎるものは次とまとめる)。"""
    parts = [p for p in re.split(r"(?<=[、。？])", text) if p]
    out = []
    for p in parts:
        if out and len(out[-1].rstrip("、。")) < 5:
            out[-1] += p
        else:
            out.append(p)
    return [p.rstrip("、。") for p in out]


def wrap(s, n=11):
    """1行 n 文字までに折る。真ん中に近い助詞・読点の後ろで切る。"""
    if "\\N" in s:          # 手で改行を指定した字幕はそのまま
        return s.split("\\N")
    if len(s) <= n:
        return [s]
    k = -(-len(s) // n)
    step = len(s) / k
    cuts, last = [], 0
    for j in range(1, k):
        mid = round(step * j)
        c = [i for i in range(last + 3, min(len(s) - 2, last + n) + 1) if s[i - 1] in "はがをにでともの、"]
        i = min(c, key=lambda i: abs(i - mid)) if c else min(mid, last + n)
        cuts.append(i); last = i
    b = [0] + cuts + [len(s)]
    return [s[b[j]:b[j + 1]] for j in range(len(b) - 1)]


def hl(s, words):
    for w in words:
        s = s.replace(w, "{\\c&H00D7FF&}" + w + "{\\c&HFFFFFF&}")
    return s


# ------------------------------------------------------------------ 効果音・BGM
def whoosh():
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(1).standard_normal(n).astype(np.float32)
    k = np.linspace(60, 6, n).astype(int)
    out = np.array([noise[max(0, j - kk):j + 1].mean() for j, kk in enumerate(k)], np.float32)
    env = np.sin(np.pi * t / t[-1]) ** 2
    return out * env * 0.9


def stop_sfx():
    """テープストップ風: 高い音がすっと下がって止まる。"""
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 900 * (1 - t / t[-1]) ** 2 + 40
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sign(np.sin(ph)) * 0.12 * (1 - t / t[-1])).astype(np.float32)


def ding():
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    out = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((1318.5, 0.25), (1975.5, 0.12), (2637, 0.06)))
    return (out * np.exp(-t * 3.5)).astype(np.float32)


def beat(total):
    """自作の軽いビート(120BPM): キック＋ハイハット＋ベース。"""
    n = int(total * SR)
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(7)
    q = int(0.5 * SR)
    kt = np.arange(int(0.18 * SR)) / SR
    kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 18)
    hat = rng.standard_normal(int(0.04 * SR)) * np.exp(-np.arange(int(0.04 * SR)) / SR * 120)
    hat = np.diff(hat, prepend=0)
    bass_notes = [45, 45, 41, 43]
    for b in range(int(total / 0.5) + 1):
        s = b * q
        if s >= n:
            break
        e = min(n, s + len(kick)); out[s:e] += kick[:e - s] * 0.55
        h = s + q // 2; e = min(n, h + len(hat))
        if h < n:
            out[h:e] += hat[:e - h] * 0.12
        f = 440 * 2 ** ((bass_notes[(b // 4) % 4] - 69) / 12)
        bt = np.arange(min(q, n - s)) / SR
        out[s:s + len(bt)] += np.sin(2 * np.pi * f * bt) * np.exp(-bt * 4) * 0.18
    return out


# ------------------------------------------------------------------ 映像
def compose(src, dur, kind, path, dark=False):
    """1920x1080 の素材を 1080x1920 に。背景はぼかし、3D は 4:5 で大きく、2D は横幅いっぱい。"""
    zoom = f"1+0.06*t/{dur:.3f}"
    if kind == "3d":
        fg = (f"crop=864:1080,scale=w='1080*({zoom})':h=-2:eval=frame,crop=1080:1350")
        y = 330
    else:
        fg = f"crop=1760:1080:40:0,scale=w='1080*({zoom})':h=-2:eval=frame,crop=1080:663"
        y = 560
    post = ",eq=brightness=-0.18:saturation=0.6" if dark else ""
    vf = (f"[0:v]split[a][b];[a]scale=-2:1920,crop=1080:1920,boxblur=24:2,eq=brightness=-0.22[bg];"
          f"[b]{fg}[fg];[bg][fg]overlay=0:{y},fps={FPS},format=yuv420p{post}[v]")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", vf, "-map", "[v]",
         "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(path)])


def ass_header():
    return ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
            "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Title,Noto Sans CJK JP,96,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,0,0,1,7,0,8,40,40,110,1\n"
            "Style: Sub,Noto Sans CJK JP,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8,2,2,60,60,330,1\n"
            "Style: Big,Noto Sans CJK JP,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,8,0,5,40,40,0,1\n"
            "Style: CTA,Noto Sans CJK JP,84,&H00FFFFFF,&H00FFFFFF,&H001E8CF0,&H001E8CF0,-1,0,0,0,100,100,0,0,3,18,0,2,60,60,360,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")


def ev(style, a, b, text, layer=0):
    return f"Dialogue: {layer},{B.ass_time(a)},{B.ass_time(b)},{style},,0,0,0,,{text}\n"


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    OUTF.parent.mkdir(parents=True, exist_ok=True)
    pop = "{\\fscx78\\fscy78\\t(0,90,\\fscx100\\fscy100)}"

    # 1) 音声と尺
    segs, t = [], 0.0
    for vis, i, rng, skip, words, *cap in SEGS:
        x = load_line(i, rng)
        d = math.ceil((len(x) / SR + GAP) * FPS) / FPS   # フレーム単位に揃えて映像と字幕のズレを防ぐ
        segs.append(dict(vis=vis, i=i, x=x, start=t, dur=d, skip=skip, words=words, cap=cap[0] if cap else None))
        t += d
    end_nar = t
    total = end_nar + CTA_DUR
    print(f"short: {total:.1f}s")

    # 2) 映像
    parts = []
    for k, s in enumerate(segs):
        kind, _, key = s["vis"].partition(":")
        src = WORK / f"src_{k:02d}.mp4"
        if kind == "3d":
            B.render_3d(key, s["dur"], src)
        else:
            tmp = WORK / f"raw_{k:02d}.mp4"
            B.render_2d(key, s["dur"] + s["skip"], tmp)
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(s["skip"]), "-i", str(tmp), "-t", f"{s['dur']:.3f}",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(src)])
        p = WORK / f"v_{k:02d}.mp4"
        compose(src, s["dur"], kind, p)
        parts.append(p)
        print("video", k, s["vis"])
    # 締め: 最後のフレームで止めて暗くする
    last = WORK / "last.png"
    seek = ["-ss", str(CTA_AT)] if CTA_AT is not None else ["-sseof", "-0.1"]
    run(["ffmpeg", "-y", "-loglevel", "error", *seek, "-i", str(WORK / f"src_{len(segs) - 1:02d}.mp4"),
         "-frames:v", "1", "-update", "1", str(last)])
    cta_src = WORK / "cta_src.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(last), "-t", f"{CTA_DUR}", "-r", str(FPS),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(cta_src)])
    p = WORK / "v_cta.mp4"
    compose(cta_src, CTA_DUR, "3d", p, dark=True)
    parts.append(p)
    lst = WORK / "concat.txt"
    lst.write_text("".join(f"file '{q}'\n" for q in parts))
    vid = WORK / "video.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vid)])

    # 3) 字幕
    ass = ass_header()
    ass += ev("Title", 0, end_nar, f"{TITLE[0]}\\N{{\\c&H1E8CF0&}}{TITLE[1]}")
    for s in segs:
        ph = phrases(line_text(s["i"]))
        if s["cap"]:
            ph = s["cap"]
        elif s["i"] in CAPS:
            ph = CAPS[s["i"]]
        n = sum(len(q) for q in ph)
        a = s["start"]
        span = s["dur"] - GAP
        for q in ph:
            b = a + span * len(q) / n
            ass += ev("Sub", a, b + (GAP if q == ph[-1] else 0), pop + "\\N".join(hl(L, s["words"]) for L in wrap(q)))
            a = b
    c0 = end_nar
    ass += ev("Big", c0 + 0.15, total, pop + "{\\pos(540,700)}" + CTA[0])
    ass += ev("Big", c0 + 0.45, total, pop + "{\\pos(540,830)}" + CTA[1])
    ass += ev("CTA", c0 + 1.1, total,
              "{\\fscx70\\fscy70\\t(0,120,\\fscx105\\fscy105)\\t(120,200,\\fscx100\\fscy100)}" + CTA2[0])
    ass += ev("Big", c0 + 1.5, total, "{\\fs60\\pos(540,1700)\\c&H00D7FF&}" + CTA2[1])
    (WORK / "subs.ass").write_text(ass, encoding="utf-8")

    # 4) 音
    mix = np.zeros(int((total + 0.5) * SR), np.float32)
    def put(x, at, g=1.0):
        a = int(at * SR); b = min(len(mix), a + len(x)); mix[a:b] += x[:b - a] * g
    for s in segs:
        put(s["x"], s["start"])
    wh = whoosh()
    for s in segs[1:]:
        put(wh, s["start"] - 0.1, 0.25)
    bt = beat(end_nar)
    bt *= np.clip(np.arange(len(bt)) / SR / 0.3, 0, 1)
    put(bt, 0, 0.35)
    put(stop_sfx(), end_nar - 0.05, 0.9)
    put(ding(), c0 + 1.1, 0.5)
    mix = mix[:int(total * SR)]
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    wav = WORK / "mix.wav"
    B.write_wav(wav, mix)

    subs = str(WORK / "subs.ass").replace(":", r"\:")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vid), "-i", str(wav), "-vf", f"ass={subs}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(OUTF)])
    print("wrote", OUTF)


if __name__ == "__main__":
    import ep02_build  # noqa: F401  (B のグローバルを第2話用に差し替える)
    configure("short1_kasa")
    main()
