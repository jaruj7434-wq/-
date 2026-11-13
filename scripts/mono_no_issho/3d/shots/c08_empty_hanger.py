"""C08 / カット 7-1(ラスト): C01 と同じクローゼット。値札付きのシャツが掛かっていた場所に、
空のハンガーが1本だけ残って、ゆっくり揺れている。カメラはそのハンガーの近くから、ゆっくり引いていく。5秒。

セットは fuku_parts.build_closet(C01 と共用)をそのまま使い、値札のシャツ(と値札)だけ取り除く
(layout を変えると他の服の位置が少しずれるため)。揺れは fuku_parts.swing(パイプ回りの減衰振動)。
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P
import fuku_parts as FK

FRAMES = 120


def remove_tree(o):
    for ch in list(o.children):
        remove_tree(ch)
    bpy.data.objects.remove(o, do_unlink=True)


def build(sc):
    P.world_studio((0.08, 0.07, 0.06), (0.3, 0.28, 0.26), (0.55, 0.53, 0.5), 0.5, camera_color=(0.5, 0.48, 0.45))
    cl = FK.build_closet()
    FK.closet_lights(target=(0, 30, 120))
    i = cl["slots"].index("tag")
    hg = cl["hangers"][i]
    remove_tree(cl["garments"][i])            # シャツ(子の値札ごと)を外す → 空のハンガー
    # 服の重みがなくなって、少しこちらを向いたまま揺れる(誰かが服を取っていった直後の余韻)
    FK.swing(hg, -24, 7.0, period=40.0, decay=90.0, end=FRAMES)   # f1 ではもう揺れている
    bpy.context.view_layer.update()
    hw = hg.matrix_world.translation.copy()
    # カメラ: 空のハンガーの近く(C01 の終わりに近い位置)から、部屋の中ほどへ引く
    cam, tgt = C.camera((hw.x + 24, hw.y - 105, hw.z - 8), (hw.x - 1, hw.y, hw.z - 14), lens=35, fstop=0.12)
    P.key_seq(cam, "location", [(1, (hw.x + 24, hw.y - 105, hw.z - 8)), (FRAMES, (45, -320, 150))])
    P.key_seq(tgt, "location", [(1, (hw.x - 1, hw.y, hw.z - 14)), (FRAMES, (12, 30, 122))])
    # ピントはハンガーに置いたまま(引くにつれてハンガー以外もだんだん合う)
    foc = bpy.data.objects.new("Focus", None); bpy.context.collection.objects.link(foc)
    foc.location = hw; cam.data.dof.focus_object = foc
    sc.view_settings.exposure = 0.3


if __name__ == "__main__":
    C.EPISODE = "ep04"
    C.run_shot("c08_empty_hanger", build, FRAMES)
