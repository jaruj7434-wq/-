"""1カット分を組み立ててレンダリングする(1セリフ=1カット)。

使い方: python render_shot.py <カット名> <timings.json> <出力フォルダ> [--preview]
  環境変数: SAMPLES、SCALE(%)、FRAMES("開始-終了")
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kit import FPS, render  # noqa: E402

# カット名 → (モジュール, モード)。並び順がセリフの順番
SHOTS = {
    "shake": ("interior", "shake"),
    "buttons": ("interior", "buttons"),
    "nearest": ("building", "nearest"),
    "auto": ("building", "auto"),
    "stuck": ("building", "stuck"),
    "doors_no": ("interior", "doors_no"),
    "bell": ("interior", "bell"),
    "blackout": ("interior", "blackout"),
    "clock": ("interior", "clock"),
    "cabinet": ("interior", "cabinet"),
    "outro": ("interior", "outro"),
}
ORDER = list(SHOTS)
TAIL = 0.8


def shot_window(name, timings):
    lines = timings["lines"]
    i = ORDER.index(name)
    start = lines[i]["start"]
    end = lines[i + 1]["start"] if i + 1 < len(ORDER) else timings["total"] + TAIL
    return start, round((end - start) * FPS)


if __name__ == "__main__":
    name, tpath, out = sys.argv[1:4]
    timings = json.loads(Path(tpath).read_text())
    start, frames = shot_window(name, timings)
    print(f"[{name}] start={start:.2f}s frames={frames}")
    module, mode = SHOTS[name]
    scene = __import__(module).build(mode, frames)
    if "--preview" in sys.argv:
        picks = sorted({max(1, frames // 6), frames // 2, max(1, frames - 4)})
        render(scene, out, samples=8, scale=40, preview_frames=picks)
    else:
        render(scene, out, motion_blur=os.environ.get("MB", "1") == "1")
