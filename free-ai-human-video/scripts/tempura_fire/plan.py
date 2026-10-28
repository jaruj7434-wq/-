"""カット割りと、シミュレーション・3D の両方で使う出来事のタイミング(フレーム)。"""
import json
from pathlib import Path

FPS = 24
TAIL = 0.8
# カット名(セリフの順)
SHOTS = ["hook", "erupt", "section", "spray", "heat", "unattended", "extinguisher", "lid", "mayo", "outro"]
# カット → 使うシミュレーション(None はシミュレーションなし)。unattended は heat の前半(煙だけ)を流用する
SIM_OF = {"hook": "steady", "erupt": "erupt", "spray": "spray", "heat": "heat", "unattended": "heat",
          "extinguisher": "extinguisher", "lid": "lid", "mayo": "steady"}


def windows(timings_path):
    """カットごとの (開始秒, フレーム数)。"""
    t = json.loads(Path(timings_path).read_text())
    L = t["lines"]
    out = {}
    for i, name in enumerate(SHOTS):
        end = L[i + 1]["start"] if i + 1 < len(SHOTS) else t["total"] + TAIL
        out[name] = (L[i]["start"], round((end - L[i]["start"]) * FPS))
    return out


def events(frames):
    """カットのフレーム数から、出来事のフレームを決める。"""
    return {
        "erupt_pour": 6,                      # 水が鍋に入り始める
        "erupt_burst": 12,                    # 火柱が噴き上がる
        "spray_launch": (4, 22),              # 油のしぶきが飛び出す範囲
        "heat_ignite": int(frames["heat"] * 0.78),        # 約370℃で発火
        "ext_spray": int(frames["extinguisher"] * 0.38),  # 消火器の噴射開始(前半はラベルのアップ)
        "lid_knob": int(frames["lid"] * 0.12),            # 火を止める
        "lid_start": int(frames["lid"] * 0.25),           # ふたを下ろし始める
        "lid_end": int(frames["lid"] * 0.45),             # ふたが閉まる
    }


def lid_z(frame, ev):
    """ふたの下面の高さ [m](コンロ天板から)。下ろし始め〜閉まるまでをなめらかに動かす。"""
    top, rest = 0.42, 0.093
    s, e = ev["lid_start"], ev["lid_end"]
    if frame <= s:
        return top
    if frame >= e:
        return rest
    x = (frame - s) / (e - s)
    x = x * x * (3 - 2 * x)
    return top + (rest - top) * x
