"""C01 / カット1-x: 扉を開けたクローゼットにゆっくり寄る。5秒。

- パイプにハンガーの服(コート2着・ニット・シャツ数枚)、棚にたたんだニット、下に収納ボックス
- 右端のシャツだけ手前に向いていて、袖口に無地の紙の値札(文字・ロゴなし)が付いたまま
- カメラは部屋の中ほどから値札のシャツへ、ゆっくりドリーイン。値札がかすかに揺れる
セットは fuku_parts.build_closet(C08 と共用)。
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P
import fuku_parts as FK

FRAMES = 120


def build(sc):
    P.world_studio((0.08, 0.07, 0.06), (0.3, 0.28, 0.26), (0.55, 0.53, 0.5), 0.5, camera_color=(0.5, 0.48, 0.45))
    cl = FK.build_closet()
    FK.closet_lights(target=(0, 30, 120))
    # 値札をかすかに揺らす
    tag = cl["tag"]
    for f in range(1, FRAMES + 1):
        tag.rotation_euler = (math.radians(4.0 * math.sin(f / 13.0)), math.radians(6.0 * math.sin(f / 21.0 + 1.0)), 0)
        tag.keyframe_insert("rotation_euler", frame=f)
    bpy.context.view_layer.update()
    tw = tag.matrix_world.translation.copy()
    # カメラ: 正面やや右から、値札のシャツへ寄る
    cam, tgt = C.camera((60, -330, 150), (0, 30, 125), lens=35, fstop=0.12)
    P.key_seq(cam, "location", [(1, (55, -330, 150)), (FRAMES, (tw.x + 22, tw.y - 95, tw.z + 4))])
    P.key_seq(tgt, "location", [(1, (5, 30, 122)), (FRAMES, (tw.x - 1, tw.y, tw.z - 6))])
    cam.data.dof.focus_object = tgt
    sc.view_settings.exposure = 0.3


if __name__ == "__main__":
    C.EPISODE = "ep04"
    C.run_shot("c01_closet", build, FRAMES)
