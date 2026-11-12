"""第1話「1円玉の一生」を通しで組み立てる(3Dクリップ + 2D図解 + ナレーション + 字幕 + BGM)。

  python3 scripts/mono_no_issho/edit/ep01_build.py            # 全体を書き出し
  python3 scripts/mono_no_issho/edit/ep01_build.py --list     # カット表と尺だけ表示

3Dクリップは assets/output/mono_no_issho/ep01/clips/<shot>.mp4 (render_queue.sh で作る)。
未完成の3Dカットは「制作中」プレースホルダーになる。
"""
import argparse, hashlib, json, math, re, subprocess, sys, wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graphics2d as G

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/output/mono_no_issho/ep01"
CLIPS = OUT / "clips"
WORK = OUT / "edit_work"
FPS = 24
SR = 48000

# ------------------------------------------------------------------ カット表
# (映像, [ナレーション行...], 最低秒数)
#   映像: "3d:<shot>" / "3d:<shot>@<開始秒>-<終了秒>" / "2d:<REGISTRYキー>"
EDL = [
    # 1. フック
    ("3d:h01_wallet", ["あなたの財布に、たぶん今も入っている1円玉。"], 4),
    ("2d:counter", ["実はこの1円玉、10年間ほとんど作られていませんでした。"], 5),
    ("3d:h14_melt@0-5", ["そして、この旅の終わりには……溶かされます。"], 4),
    ("2d:title", [], 3.5),
    # 2. 誕生
    ("2d:spec", ["1円玉の正式な名前は「一円アルミニウム貨」。生まれたのは1955年。",
                 "素材はアルミニウム。重さはちょうど1グラム、直径は2センチ。"], 6),
    ("2d:map_mint", ["作っているのは独立行政法人・造幣局。主に大阪と広島の工場です。"], 5),
    ("3d:h03_furnace", ["まず、材料を電気炉で溶かして金属の塊にします。"], 4),
    ("3d:h04_rolling", ["これを決まった厚さの板にのばし、"], 4),
    ("3d:h05_blanking", ["丸く打ち抜く。この段階ではまだ模様のない、ただの丸い板。「円形（えんけい）」と呼ばれます。"], 5),
    ("2d:flow_edge", ["縁を盛り上げ、熱を加えて柔らかくしたら、"], 4),
    ("3d:h06_press", ["いよいよプレス機で、表と裏に模様を刻みます。"], 4),
    ("3d:h07_bagging", ["検査をくぐり抜けたものだけが、数えられ、袋に詰められて、日本銀行へ。"], 5),
    ("2d:route", ["ここから、1円玉の旅が始まります。"], 5),
    # 3. 旅
    ("3d:h08_register", ["銀行を出た1円玉は、お店のレジへ。"], 4),
    ("2d:wander", ["おつりとして誰かの財布に入り、また別のお店へ。"], 5),
    ("2d:bar", ["今、日本には約364億枚の1円玉が出回っています。硬貨の中で、ダントツの1位。"], 6),
    ("2d:per_capita", ["日本人1人あたり、およそ300枚です。"], 5),
    ("3d:h09_piggy", ["……でも、そんなにどこにあるんでしょう？", "答えの一つは、「家の中」。"], 4),
    ("3d:h09_drawer", ["貯金箱、引き出し、車のドリンクホルダー。"], 4),
    ("3d:h09_cupholder", ["1円玉は、旅の途中で長い眠りにつきがちです。"], 4),
    ("3d:h10_vending", ["そして1円玉には、行けない場所があります。自動販売機です。"], 5),
    ("2d:vending", ["あるメーカーの担当者によると、理由は「スペース」。",
                    "1円玉を入れられるようにすると、おつり用の1円玉をしまう場所が必要になる。",
                    "その分、機械を大きくするか、商品を減らすしかないんだそうです。"], 8),
    # 4. 意外な事実
    ("2d:rumor", ["ここで、よく聞く噂を一つ。「1円玉は、作るのに3円かかる」。"], 5),
    ("2d:cost", ["実は、国は1円玉の製造コストを公表していません。偽造を助長するおそれがあるからです。",
                 "3円というのは、民間の試算による数字。材料のアルミだけなら0.3円ほどですが、人件費や機械を含めると、額面を上回ると言われています。"], 10),
    ("2d:chart", ["では、どれくらい作られているのか。",
                  "1990年、1年で約27億枚。ところが2013年度には、たった55万枚。",
                  "一度だけ、急に増えた年があります。2014年度、1億2千万枚。消費税が8%に上がり、端数が一気に増えたからです。",
                  "そして2016年からの10年間、1円玉は記念の貨幣セット用にしか作られなくなりました。"], 20),
    ("2d:quote", ["ところが2026年の夏。造幣局の公式アカウントが、こう投稿しました。",
                  "「現在、平成27年度以来11年ぶりに、1円の量産を行っています」。"], 8),
    ("3d:h11_factory_line", [], 5),
    ("3d:h12_counter_pile", ["ちなみに、1円玉ばかりで払おうとしても、お店は断ることができます。"], 4),
    ("2d:law20", ["法律で、同じ硬貨は一度に20枚まで、と決まっているからです。"], 5),
    # 5. 最期
    ("3d:h13_worn_coin", ["長い旅の果て。すり減ったり、傷ついたりした1円玉は、銀行を通じて日本銀行へ戻ってきます。"], 5),
    ("2d:return", ["国の指示で回収された硬貨は、再び造幣局へ。そして、溶かされます。"], 5),
    ("3d:h14_melt", ["生まれた場所で、生まれた時と同じように、炉の中へ。", "そして、次の硬貨の材料になります。"], 8),
    ("2d:loop", [], 4),
    ("2d:law_damage", ["ちなみに、私たちが1円玉を溶かしたり、穴を開けたりするのは法律で禁止。1年以下の拘禁刑か、20万円以下の罰金です。",
                       "1円玉の一生を終わらせられるのは、国だけなんです。"], 8),
    # 6. 締め
    ("3d:h01_wallet", ["あなたの財布の1円玉。それは何年前に生まれて、どんな旅をしてきたのでしょう。"], 5),
    ("3d:h15_rain_umbrella", ["次回、「なくした傘はどこへ行く？」"], 4),
    ("2d:next", [], 4),
]

GAP = 0.25        # 行間
PAD = 0.45        # カット頭とお尻の余白


def tts_text(s):
    """読み上げ用に整形(読み仮名の括弧を消す等)。字幕には元の文を使う。"""
    s = re.sub(r"（[ぁ-ん]+）", "", s)
    return s.replace("——", "、").replace("8%", "8パーセント")


def subtitle_text(s):
    return s


# ------------------------------------------------------------------ 音声
VOICE = "openjtalk"   # --voice hf: Higgsfield Seed Audio / --voice el: ElevenLabs v4
HF_DIRS = {"hf": (WORK / "hf_tts", "wav"), "el": (WORK / "el_tts", "mp3")}
HF_MANIFEST = ROOT / "prompts/mono_no_issho/ep01_narration_lines.json"


def tts_hf(line):
    """Higgsfield(Seed Audio)で生成済みの行音声を読み込み、前後の無音を詰める。"""
    idx = {o["line"]: o["i"] for o in json.load(open(HF_MANIFEST, encoding="utf-8"))}
    d, ext = HF_DIRS[VOICE]
    f = d / f"{idx[line]:02d}.{ext}"
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(f), "-ac", "1",
                          "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    nz = np.where(np.abs(x) > 0.01)[0]
    a, b = max(0, nz[0] - int(0.03 * SR)), min(len(x), nz[-1] + int(0.08 * SR))
    return x[a:b].copy()


def tts(line):
    if VOICE in HF_DIRS:
        return tts_hf(line)
    import pyopenjtalk
    WORK.mkdir(parents=True, exist_ok=True)
    h = hashlib.md5(line.encode()).hexdigest()[:12]
    p = WORK / f"tts_{h}.npy"
    if p.exists():
        return np.load(p)
    x, sr = pyopenjtalk.tts(tts_text(line), speed=1.05)
    assert sr == SR
    x = (x / 32768.0).astype(np.float32)
    np.save(p, x)
    return x


def bgm(total_s):
    """著作権フリーの自作アンビエント: Am - F - C - G のゆっくりしたパッド。"""
    t = np.arange(int(total_s * SR)) / SR
    chords = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]
    bar = 6.0
    out = np.zeros_like(t, dtype=np.float32)
    for i in range(int(total_s / bar) + 1):
        s0 = int(i * bar * SR); s1 = min(len(t), int((i + 1) * bar * SR + 1.5 * SR))
        if s0 >= len(t):
            break
        tt = t[s0:s1] - i * bar
        env = np.clip(tt / 1.5, 0, 1) * np.clip((bar + 1.5 - tt) / 1.5, 0, 1)
        for n in chords[i % 4]:
            f = 440 * 2 ** ((n - 69) / 12)
            for det in (-0.6, 0.6):
                out[s0:s1] += (np.sin(2 * np.pi * (f + det) * tt) * env * 0.05).astype(np.float32)
            out[s0:s1] += (np.sin(2 * np.pi * f / 2 * tt) * env * 0.03).astype(np.float32)
    # ゆるいローパス(移動平均)
    k = 40
    out = np.convolve(out, np.ones(k) / k, mode="same").astype(np.float32)
    fade = np.clip(t / 3, 0, 1) * np.clip((total_s - t) / 4, 0, 1)
    return out * fade * 0.5


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


# ------------------------------------------------------------------ 映像
def ffprobe_dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def render_2d(key, dur, path):
    f = G.REGISTRY[key]() if key in G.REGISTRY else G.placeholder(key)
    n = int(round(dur * FPS))
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{G.W}x{G.H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                          "-crf", "18", "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(f(i / FPS, dur).tobytes())
    p.stdin.close(); p.wait()


def render_3d(spec, dur, path):
    shot, _, rng = spec.partition("@")
    src = CLIPS / f"{shot}.mp4"
    if not src.exists():
        render_2d_placeholder(shot, dur, path)
        return f"(未完成) {shot}"
    a, b = 0.0, ffprobe_dur(src)
    if rng:
        a, b = map(float, rng.split("-"))
    length = b - a
    factor = min(2.0, max(1.0, dur / length))   # 足りなければ最大2倍までスロー、それでも足りなければ最終フレーム保持
    vf = (f"trim={a}:{b},setpts=(PTS-STARTPTS)*{factor:.4f},fps={FPS},"
          f"scale={G.W}:{G.H}:flags=lanczos,tpad=stop_mode=clone:stop_duration={dur},trim=0:{dur},setpts=PTS-STARTPTS")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", vf, "-an", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(path)], check=True)
    return f"{shot} x{factor:.2f}"


def render_2d_placeholder(shot, dur, path):
    G.REGISTRY.setdefault("_ph_" + shot, lambda: G.placeholder(shot))
    render_2d("_ph_" + shot, dur, path)


def ass_time(s):
    h = int(s // 3600); m = int(s % 3600 // 60); sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def wrap_jp(s, n=30):
    """長い字幕を2行に。読点・句点の近くで折る。"""
    if len(s) <= n:
        return s
    mid = len(s) // 2
    cands = [i for i, c in enumerate(s) if c in "、。」？" and 6 < i < len(s) - 4]
    i = min(cands, key=lambda i: abs(i - mid)) + 1 if cands else mid
    return s[:i] + r"\N" + s[i:]


# ------------------------------------------------------------------ メイン
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--voice", choices=["openjtalk", "hf", "el"], default="openjtalk")
    a = ap.parse_args()
    global VOICE
    VOICE = a.voice
    if a.out is None:
        a.out = str(OUT / (f"{OUT.name}_draft.mp4" if VOICE == "openjtalk" else f"{OUT.name}_draft_{VOICE}.mp4"))
    WORK.mkdir(parents=True, exist_ok=True)

    # 1) ナレーション → 各カットの尺
    cuts = []
    t = 0.0
    for idx, (vis, lines, mind) in enumerate(EDL):
        auds = [tts(l) for l in lines]
        nar = sum(len(x) / SR for x in auds) + GAP * max(0, len(auds) - 1)
        dur = max(mind, nar + 2 * PAD) if lines else mind
        dur = math.ceil(dur * FPS) / FPS
        cuts.append(dict(i=idx, vis=vis, lines=lines, auds=auds, start=t, dur=dur))
        t += dur
    total = t
    for c in cuts:
        print(f"{c['i']:02d} {c['start']:7.2f}s {c['dur']:5.2f}s  {c['vis']:24s} {c['lines'][0][:24] if c['lines'] else ''}")
    print(f"total {total:.1f}s ({total / 60:.1f} min)")
    if a.list:
        return

    # 2) 映像(カットごと)
    listfile = WORK / "concat.txt"
    with open(listfile, "w") as lf:
        for c in cuts:
            p = WORK / f"cut_{c['i']:02d}.mp4"
            kind, spec = c["vis"].split(":", 1)
            info = render_3d(spec, c["dur"], p) if kind == "3d" else (render_2d(spec, c["dur"], p) or spec)
            print("video", c["i"], info, flush=True)
            lf.write(f"file '{p}'\n")
    video = WORK / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listfile),
                    "-c", "copy", str(video)], check=True)

    # 3) 音声: ナレーション配置 + BGM
    nar = np.zeros(int((total + 1) * SR), dtype=np.float32)
    events = []
    for c in cuts:
        s = c["start"] + PAD
        for line, x in zip(c["lines"], c["auds"]):
            i0 = int(s * SR); nar[i0:i0 + len(x)] += x
            events.append((s, s + len(x) / SR, line))
            s += len(x) / SR + GAP
    peak = np.abs(nar).max() or 1
    nar = nar / peak * 0.85
    mix = nar + bgm(len(nar) / SR)
    audio = WORK / "audio.wav"
    write_wav(audio, mix)

    # 4) 字幕(ASS)
    ass = WORK / "subs.ass"
    with open(ass, "w") as f:
        f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
                "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
                "MarginR, MarginV, Encoding\n"
                "Style: Default,Noto Sans CJK JP,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,80,80,60,1\n\n"
                "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        for s, e, line in events:
            f.write(f"Dialogue: 0,{ass_time(s)},{ass_time(e + 0.15)},Default,,0,0,0,,{wrap_jp(subtitle_text(line))}\n")

    # 5) 合成
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio),
                    "-vf", f"ass={ass}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", a.out], check=True)
    json.dump([{k: c[k] for k in ("i", "vis", "start", "dur", "lines")} for c in cuts],
              open(WORK / "timeline.json", "w"), ensure_ascii=False, indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
