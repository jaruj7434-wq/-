"""浴槽から立ちのぼる湯気のシミュレーション(天ぷら油動画の firesim.py を使い回す)。

使い方: python sims.py <timings.json> <出力フォルダ>   → <出力フォルダ>/steam/f_####.npz と grid.json
湯気は燃料なしの「煙」として計算する。軽く(重さ0)、温かさで上昇し、空気に混ざって消えていく。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tempura_fire"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from firesim import Sim, run  # noqa: E402
from plan import STEAM_SHOTS, TUB_RIM, TUB_X, TUB_Y, WATER_Z, windows  # noqa: E402


def main(timings, out_root):
    win = windows(timings)
    frames = max(win[s][1] for s in STEAM_SHOTS)
    out = Path(out_root) / "steam"
    sim = Sim(shape=(140, 100, 150), h=0.01, origin=(-0.7, -0.5, 0.4), weight=0.0, smoke_fade=0.55, cool=0.8,
              buoy=1.6, vort=4.0)
    # 浴槽のふち(湯面より上の部分)を固体にする
    outer = sim.mask_box(-TUB_X - 0.08, TUB_X + 0.08, -TUB_Y - 0.08, TUB_Y + 0.08, 0.0, TUB_RIM)
    inner = sim.mask_box(-TUB_X, TUB_X, -TUB_Y, TUB_Y, 0.0, TUB_RIM + 0.1)
    sim.solid |= outer & ~inner
    surface = sim.mask_box(-TUB_X + 0.02, TUB_X - 0.02, -TUB_Y + 0.02, TUB_Y - 0.02, WATER_Z - 0.01, WATER_Z + 0.02)

    def events(s, fr, st):
        s.emit(surface, smoke=0.45, temp=0.35, vel=(0, 0, 0.12), jitter=0.95)

    print(f"[steam] grid={sim.shape} frames={frames}", flush=True)
    run(sim, frames, out, events, warmup=48)
    (out / "grid.json").write_text(json.dumps({"shape": sim.shape, "h": sim.h, "origin": sim.origin}))


if __name__ == "__main__":
    main(*sys.argv[1:3])
