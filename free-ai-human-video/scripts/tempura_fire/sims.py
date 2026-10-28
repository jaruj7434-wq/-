"""カットごとの炎・煙シミュレーション。

使い方: python sims.py <シミュレーション名> <timings.json> <出力フォルダ>
  名前: steady / erupt / spray / heat / extinguisher / lid
  出力: <出力フォルダ>/<名前>/f_####.npz と grid.json(格子の位置・大きさ)、spray は droplets.json も
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from firesim import Sim, run  # noqa: E402
from plan import SIM_OF, events, lid_z, windows  # noqa: E402

OIL_Z = 0.065
POT_R = 0.12


def add_pot(sim):
    """鍋の壁と底を固体にする。"""
    sim.solid |= sim.mask_cylinder(0, 0, 0.0, 0.092, POT_R + 0.006, r_inner=POT_R - 0.005)
    sim.solid |= sim.mask_cylinder(0, 0, 0.0, 0.006, POT_R + 0.006)


def oil_mask(sim):
    return sim.mask_cylinder(0, 0, OIL_Z - 0.006, OIL_Z + 0.012, POT_R - 0.012)


def pot_fire(sim, oil, strength=1.0):
    sim.emit(oil, fuel=1.0 * strength, temp=1.0, vel=(0, 0, 0.25), jitter=0.75)


def frames_needed(name, win):
    shots = [s for s, sim in SIM_OF.items() if sim == name]
    return max(win[s][1] for s in shots)


def make(name, timings, out_root):
    win = windows(timings)
    frames = {k: v[1] for k, v in win.items()}
    ev = events(frames)
    n = frames_needed(name, win)
    out = Path(out_root) / name
    if name in ("steady", "heat", "lid"):
        sim = Sim(shape=(100, 100, 200), h=0.005, origin=(-0.25, -0.25, 0.0))
    elif name == "extinguisher":
        sim = Sim(shape=(160, 110, 170), h=0.0055, origin=(-0.33, -0.36, 0.0))
    elif name == "erupt":
        sim = Sim(shape=(192, 120, 186), h=1.55 / 186, origin=(-0.8, -0.5, 0.0), ceiling=True, vort=8.0,
                  burn_rate=7.0, soot=0.9)  # 油の霧は一気に燃え尽きる
    else:  # spray
        sim = Sim(shape=(160, 110, 140), h=0.0075, origin=(-0.6, -0.41, 0.0), vort=8.0)
    add_pot(sim)
    oil = oil_mask(sim)
    base_solid = sim.solid.copy()
    rng = np.random.default_rng(4)
    extra = {}
    time_scale, warm = 1.0, 36

    if name == "steady":
        def ev_fn(s, fr, st):
            pot_fire(s, oil)

    elif name == "erupt":
        time_scale = 0.45  # スローモーション
        burst = ev["erupt_burst"]

        def ev_fn(s, fr, st):
            pot_fire(s, oil, 1.0 if fr < burst else 1.6)
            if burst <= fr < burst + 4:  # 水が一気に気化して、燃える油の霧が噴き上がる
                k = (fr - burst) + st / 3
                ball = s.mask_sphere(0, 0, 0.12 + 0.06 * k, 0.07 + 0.03 * k)
                s.emit(ball, fuel=1.6, temp=2.0, jitter=0.6)
                s.emit_radial(ball, 0, 0, 0.05, speed=2.5, up=6.0)

    elif name == "spray":
        time_scale = 0.35
        lo, hi = ev["spray_launch"]
        drops = []
        for i in range(34):  # しぶき1粒ずつの打ち上げ時刻・位置・速度
            a = rng.uniform(0, math.tau)
            sp = rng.uniform(1.0, 2.6)
            drops.append({"t0": rng.uniform(lo, hi) / 24 * time_scale,
                          "p": [0.09 * math.cos(a), 0.09 * math.sin(a), OIL_Z + 0.02],
                          "v": [sp * math.cos(a), sp * math.sin(a) * 0.7, rng.uniform(2.0, 3.6)],
                          "r": float(rng.uniform(0.005, 0.011))})
        track = {}

        def pos(d, t):
            dt = t - d["t0"]
            if dt < 0:
                return None
            return (d["p"][0] + d["v"][0] * dt, d["p"][1] + d["v"][1] * dt, d["p"][2] + d["v"][2] * dt - 4.9 * dt * dt)

        def ev_fn(s, fr, st):
            pot_fire(s, oil, 1.3)
            if fr <= 0:
                return
            t = s.t - warm / 24  # ウォームアップ後からの時間(シミュレーション内の秒)
            for i, d in enumerate(drops):
                p = pos(d, t)
                if p is None or p[2] < 0.0:
                    continue
                s.emit(s.mask_sphere(*p, 0.016), fuel=2.0, temp=1.6, jitter=0.4)
                if st == 0:
                    track.setdefault(fr, []).append([i, *p, d["r"]])
        extra["droplets"] = track

    elif name == "heat":
        ign = ev["heat_ignite"]

        def ev_fn(s, fr, st):
            if fr < ign:  # 発火前:油から白っぽい煙が立ちのぼる(熱いが火はない)
                s.emit(oil, smoke=0.35 + 0.4 * max(fr, 0) / ign, temp=0.12, vel=(0, 0, 0.15), jitter=0.9)
            else:  # 約370℃で自然発火:炎が油面全体に広がっていく
                k = min(1.0, (fr - ign + st / 3) / 10)
                sub = s.mask_cylinder(0.04, 0.02, OIL_Z - 0.006, OIL_Z + 0.012, 0.02 + 0.09 * k)
                s.emit(sub & oil, fuel=1.0, temp=1.0, smoke=0.5, vel=(0, 0, 0.25), jitter=0.75)

    elif name == "extinguisher":
        spray_at = ev["ext_spray"]
        nozzle = np.array([0.36, -0.3, 0.36])
        aim = np.array([0.0, 0.0, 0.1]) - nozzle
        aim /= np.linalg.norm(aim)

        def ev_fn(s, fr, st):
            k = 1.0 if fr < spray_at else max(0.0, 1.0 - (fr - spray_at) / 30)
            if k > 0:
                pot_fire(s, oil, k)
            if fr >= spray_at:
                jet = s.mask_sphere(*nozzle, 0.03)
                s.emit(jet, powder=1.0, vel=tuple(aim * 7.0), jitter=0.3)

    elif name == "lid":
        knob, close = ev["lid_knob"], ev["lid_end"]
        inside = s_inside = None

        def ev_fn(s, fr, st):
            nonlocal s_inside
            z = lid_z(fr + st / 3, ev)
            lid = s.mask_cylinder(0, 0, z, z + 0.01, POT_R + 0.018)
            s.solid[:] = base_solid | lid
            if fr < close:
                pot_fire(s, oil, 1.0 if fr < knob else 0.9)
            else:  # ふたで空気が断たれ、中の炎は消えていく
                if s_inside is None:
                    s_inside = s.mask_cylinder(0, 0, 0.0, 0.1, POT_R)
                s.remove(s_inside, keep=0.82)

    else:
        raise SystemExit(f"unknown sim {name}")

    out.mkdir(parents=True, exist_ok=True)
    print(f"[{name}] grid={sim.shape} h={sim.h:.4f} frames={n} time_scale={time_scale}", flush=True)
    run(sim, n, out, ev_fn, time_scale=time_scale, warmup=warm)
    (out / "grid.json").write_text(json.dumps({"shape": sim.shape, "h": sim.h, "origin": sim.origin,
                                               "time_scale": time_scale}))
    if "droplets" in extra:
        (out / "droplets.json").write_text(json.dumps(extra["droplets"]))


if __name__ == "__main__":
    make(*sys.argv[1:4])
