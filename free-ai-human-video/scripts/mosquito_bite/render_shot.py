"""1カット分を組み立ててレンダリングする。

使い方: python render_shot.py <カット名> <timings.json> <出力フォルダ> [--preview]
  カット名: surface_approach / surface_bend / tip_closeup / section_search / vessel / section_react / surface_withdraw
  環境変数: SAMPLES(既定12)、SCALE(%・既定67)、FRAMES("開始-終了")
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common import FPS, render  # noqa: E402

# カット名 → 担当するセリフ番号(timings.json の lines の index)
SHOTS = {
    "surface_approach": [0],
    "surface_bend": [1],
    "tip_closeup": [2],
    "section_search": [3],
    "vessel": [4, 5],
    "section_react": [6],
    "surface_withdraw": [7],
}
ORDER = list(SHOTS)
TAIL = 0.8  # 最後のカットの余韻(秒)


def shot_window(name, timings):
    """カットの開始秒・長さ(フレーム)と、セリフごとの開始フレーム(カット内)を返す。"""
    lines = timings["lines"]
    idx = SHOTS[name]
    start = lines[idx[0]]["start"]
    i = ORDER.index(name)
    end = lines[SHOTS[ORDER[i + 1]][0]]["start"] if i + 1 < len(ORDER) else timings["total"] + TAIL
    frames = round((end - start) * FPS)
    cues = [round((lines[k]["start"] - start) * FPS) + 1 for k in idx]
    return start, frames, cues


def build(name, frames, cues):
    if name == "vessel":
        import shot_vessel
        return shot_vessel.build(frames, saliva_at=cues[0] + 12, suck_at=cues[1])
    if name.startswith("surface"):
        import shot_surface
        return shot_surface.build(name.split("_")[1], frames)
    if name == "tip_closeup":
        import shot_tip
        return shot_tip.build(frames)
    if name.startswith("section"):
        import shot_section
        return shot_section.build(name.split("_")[1], frames)
    raise SystemExit(f"unknown shot {name}")


if __name__ == "__main__":
    name, tpath, out = sys.argv[1:4]
    timings = json.loads(Path(tpath).read_text())
    start, frames, cues = shot_window(name, timings)
    print(f"[{name}] start={start:.2f}s frames={frames} cues={cues}")
    scene = build(name, frames, cues)
    if "--preview" in sys.argv:
        picks = sorted({max(1, frames // 5), frames // 2, max(1, frames - 6), *[min(frames, c + 18) for c in cues]})
        render(scene, out, samples=8, scale=40, preview_frames=picks)
    else:
        render(scene, out, motion_blur=os.environ.get("MB", "1") == "1" and name in ("vessel",))
