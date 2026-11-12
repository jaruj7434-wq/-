"""H13 / カット5-1: すり減った古い1円玉のマクロ。ゆっくり回転、浅い被写界深度。5秒。"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as C

FRAMES = 120


def build(sc):
    C.world((0.05, 0.045, 0.04))
    # 木の机
    import bpy
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    bpy.context.object.data.materials.append(
        C.principled("Desk", (0.18, 0.11, 0.06), rough=0.55, noise_rough=(0.4, 0.7), bump=0.15, bump_scale=3))
    worn = C.mat_coin("Worn", worn=1.0)
    hero = C.make_coin("Hero", worn, (0, 0, 0.075))
    C.key(hero, "rotation_euler", 1, (0, 0, 0))
    C.key(hero, "rotation_euler", FRAMES, (0, 0, math.radians(35)))
    # 背景にボケる使い古しの1円玉
    for c in C.scatter_coins(10, center=(0, 6, 0), radius=6, seed=3, mat=worn):
        if c.location.y < 3.5:
            c.location.y += 4
    C.area_light((-6, -4, 8), (40, 0, -55), 6, 2500, (1.0, 0.85, 0.7), "Key")
    C.area_light((6, 5, 4), (65, 0, 130), 4, 1200, (0.6, 0.75, 1.0), "Rim")
    cam, tgt = C.camera((0.6, -6.0, 3.6), (0, 0.1, 0.05), lens=60, fstop=2.0)
    C.key(cam, "location", 1, (0.6, -6.0, 3.6))
    C.key(cam, "location", FRAMES, (-0.4, -5.0, 3.0))


if __name__ == "__main__":
    C.run_shot("h13_worn_coin", build, FRAMES)
