"""湯気のシミュレーション(天ぷら油動画の firesim.py を使い回す)。

使い方: python sims.py <timings.json> <出力フォルダ>
  pour : 冒頭。熱いお湯が当たったガラスと、流れ落ちる筋から湯気が立ちのぼる
  spout: 2カット目。ボンネットに置いたやかんの注ぎ口から出る湯気
湯気は燃料なしの「煙」として計算する(温かさで上昇し、空気に混ざって消える)。
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tempura_fire"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from firesim import Sim, run  # noqa: E402
from plan import IMPACT, SPOUT_TIP, stream_points, windows, ws_normal, ws_point  # noqa: E402

KETTLE_SPOUT_MORNING = (0.52, -1.2, 1.078)   # 2カット目のやかんの注ぎ口(shots.py と共通)


def pour(frames, out):
    p0 = np.array(ws_point(*IMPACT))
    nrm = ws_normal(*IMPACT)
    sim = Sim(shape=(64, 56, 72), h=0.009, origin=(p0[0] - 0.3, p0[1] - 0.3, p0[2] - 0.32), weight=0.0,
              smoke_fade=0.7, cool=1.0, buoy=1.8, vort=5.0)
    rel = np.stack([sim.X - p0[0], sim.Y - p0[1], sim.Z - p0[2]], -1)
    height = rel @ nrm                                 # ガラス面からの高さ(局所的に平面とみなす)
    sim.solid |= height < -0.004
    # ガラス面に沿った座標:下向き(斜面を下る向き)
    down = np.array(ws_point(IMPACT[0], IMPACT[1] - 0.01)) - p0
    down /= np.linalg.norm(down)
    side = np.cross(nrm, down)
    along = rel @ down
    lateral = rel @ side
    pts = stream_points(16)

    def near_stream(r):
        m = np.zeros(sim.shape, bool)
        for a in pts[::2]:
            m |= (sim.X - a[0]) ** 2 + (sim.Y - a[1]) ** 2 + (sim.Z - a[2]) ** 2 < r * r
        return m
    stream = near_stream(0.012)

    def events(s, fr, st):
        tau = max(0.0, (fr + 30) / (frames + 30))
        film = (height >= -0.004) & (height < 0.022)
        pool = film & (along ** 2 + lateral ** 2 < (0.05 + 0.1 * tau) ** 2)
        flow = film & (along > 0) & (along < 0.75 * tau) & (np.abs(lateral + 0.02 * np.sin(along * 13)) < 0.03 + 0.2 * along * tau)
        s.emit(pool, smoke=0.55, temp=0.6, vel=(0, 0, 0.15), jitter=0.9)
        s.emit(flow, smoke=0.35, temp=0.45, jitter=0.9)
        s.emit(stream, smoke=0.25, temp=0.3, jitter=0.9)

    print(f"[pour] grid={sim.shape} frames={frames}", flush=True)
    run(sim, frames, out, events, warmup=30, time_scale=0.8)
    return sim


def spout(frames, out):
    tip = np.array(KETTLE_SPOUT_MORNING)
    sim = Sim(shape=(40, 40, 70), h=0.008, origin=(tip[0] - 0.16, tip[1] - 0.16, tip[2] - 0.03), weight=0.0,
              smoke_fade=0.9, cool=1.2, buoy=1.5, vort=4.0)
    src = sim.mask_sphere(*tip, 0.012)

    def events(s, fr, st):
        s.emit(src, smoke=0.6, temp=0.5, vel=(0.12, 0, 0.1), jitter=0.9)

    print(f"[spout] grid={sim.shape} frames={frames}", flush=True)
    run(sim, frames, out, events, warmup=40)
    return sim


def main(timings, out_root):
    win = windows(timings)
    for name, fn, shot in (("pour", pour, "hook"), ("spout", spout, "morning")):
        out = Path(out_root) / name
        if (out / "grid.json").exists():
            continue
        sim = fn(win[shot][1], out)
        (out / "grid.json").write_text(json.dumps({"shape": sim.shape, "h": sim.h, "origin": sim.origin}))


if __name__ == "__main__":
    main(*sys.argv[1:3])
