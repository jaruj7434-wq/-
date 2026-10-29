"""カット割り(1セリフ=1カット)と、浴槽まわりの寸法(シミュレーションと 3D で共通)。"""
import json
from pathlib import Path

FPS = 24
TAIL = 0.8
SHOTS = ["exterior", "bath", "heatshock", "thermo", "pressure", "five", "heater", "temp_timer", "handrail",
         "food", "one_word", "exterior_end"]
STEAM_SHOTS = ("bath", "temp_timer", "handrail")  # 湯気のシミュレーションを使うカット

# 浴槽(床が z=0、浴槽の中心が原点)
TUB_X, TUB_Y = 0.55, 0.36     # 内側の半分の長さ・幅
TUB_RIM = 0.55                # ふちの高さ
WATER_Z = 0.46                # 湯面の高さ


def windows(timings_path):
    t = json.loads(Path(timings_path).read_text())
    L = t["lines"]
    out = {}
    for i, name in enumerate(SHOTS):
        end = L[i + 1]["start"] if i + 1 < len(SHOTS) else t["total"] + TAIL
        out[name] = (L[i]["start"], round((end - L[i]["start"]) * FPS))
    return out
