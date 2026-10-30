"""カット割り(1セリフ=1カット)と、フロントガラスの形(3D・霜のマップ・湯気のシミュレーションで共通)。

座標:地面が z=0、車の中心が原点、車の前が -y。単位は m。
フロントガラスは (u, v) で表す:u は左右(-1〜1)、v は下(ボンネット側 0)〜上(屋根側 1)。
"""
import json
from pathlib import Path

import numpy as np

FPS = 24
TAIL = 0.8
SHOTS = ["hook", "morning", "stopwatch", "layers", "thermal", "chip", "lukewarm", "wiper", "defroster", "spray",
         "cover", "drive"]

IMPACT = (0.15, 0.62)        # お湯が当たる場所 (u, v)
SLANT = 0.886                # ガラスの下端から上端までの長さ [m]
SPOUT_TIP = (0.15, -0.20, 1.60)  # 冒頭のやかんの注ぎ口の先(お湯はここから IMPACT へ落ちる)


def ws_point(u, v):
    """フロントガラス(外側の面)上の点。u, v は数値でも numpy 配列でもよい。"""
    hw = 0.72 - 0.08 * v
    s = np.sin(np.pi * v)
    return (u * hw,
            -0.55 + 0.80 * v + 0.12 * u * u - 0.03 * s,
            1.02 + 0.38 * v - 0.04 * u * u + 0.02 * s)


def ws_normal(u, v, e=1e-4):
    """外向き(車の前・上向き)の法線。"""
    p = np.array(ws_point(u, v))
    du = np.array(ws_point(u + e, v)) - p
    dv = np.array(ws_point(u, v + e)) - p
    n = np.cross(du, dv)
    n = n / np.linalg.norm(n)
    return n if n[2] > 0 else -n


def to_uv(X, Y):
    """ガラス面上の長さ [m](X: 横、Y: 下端から斜面に沿って)→ (u, v)。"""
    v = Y / SLANT
    return X / (0.72 - 0.08 * v), v


def stream_points(n=24):
    """注ぎ口から当たる場所までのお湯の流れ(放物線)。"""
    a = np.array(SPOUT_TIP)
    b = np.array(ws_point(*IMPACT))
    s = np.linspace(0, 1, n)
    pts = a[None, :] + (b - a)[None, :] * s[:, None]
    pts[:, 2] = a[2] + (b[2] - a[2]) * s ** 2
    return pts


def windows(timings_path):
    t = json.loads(Path(timings_path).read_text())
    L = t["lines"]
    out = {}
    for i, name in enumerate(SHOTS):
        end = L[i + 1]["start"] if i + 1 < len(SHOTS) else t["total"] + TAIL
        out[name] = (L[i]["start"], round((end - L[i]["start"]) * FPS))
    return out


if __name__ == "__main__":
    import sys
    for k, (s, n) in windows(sys.argv[1]).items():
        print(f"{k:10s} {s:6.2f}s {n:4d}f")
    print("impact", [round(float(c), 3) for c in ws_point(*IMPACT)], "normal", ws_normal(*IMPACT).round(3))
