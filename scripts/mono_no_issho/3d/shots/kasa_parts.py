"""第2話(傘)の K 系ショット用の補助。単位 1BU=1cm。

傘そのものは共通モジュール umbrella.py(umbrella.make)を使う。
ここには室内の照明器具・紙タグ・紐など、K03〜K07 で使い回す小物を置く。
"""
import math, random

import bpy
from mathutils import Vector

import common as C
import props as P
try:
    import umbrella as U
except ImportError:  # 共通モジュールが無い環境向けの簡易版(第1話 H15 の閉じた傘)
    U = None


def make_umbrella(name, location, rotation_deg=(0, 0, 0), state="closed", kind="vinyl", color=None, tag=False, **kw):
    if U is not None:
        return U.make(name, location, rotation_deg=rotation_deg, state=state, kind=kind, color=color, tag=tag, **kw)
    from h15_rain_umbrella import umbrella
    root = umbrella(location, lean_deg=0, yaw_deg=0)
    root.rotation_euler = tuple(math.radians(a) for a in rotation_deg)
    root.name = name
    return root


def set_episode(ep="ep02"):
    """common の出力先をエピソード別に切り替える(common 側に仕組みがあればそれを使う)。"""
    if hasattr(C, "set_episode"):
        C.set_episode(ep)
    elif hasattr(C, "EPISODE"):
        C.EPISODE = ep


def fluorescent(name, loc, length=120, axis="X", strength=10.0, temp=5200, housing=None):
    """天井直付けの蛍光灯(白い筐体+発光管)。"""
    sx, sy = (length, 14) if axis == "X" else (14, length)
    hm = housing or bpy.data.materials.get("FluoHousing") or C.principled("FluoHousing", (0.82, 0.82, 0.8), rough=0.4)
    tube = bpy.data.materials.get(f"FluoTube{temp}") or C.emissive(f"FluoTube{temp}", temp=temp, strength=strength)
    P.box(name + "H", (sx + 6, sy, 5), (loc[0], loc[1], loc[2] + 2.5), mat=hm, bevel=0.6)
    r = 1.6
    rot = (0, math.radians(90), 0) if axis == "X" else (math.radians(90), 0, 0)
    t = P.cyl(name + "T", r, length, (loc[0], loc[1], loc[2] - r), rot=rot, mat=tube, verts=12)
    t.visible_shadow = False
    return t


def string_mat():
    return bpy.data.materials.get("StringM") or C.principled("StringM", (0.72, 0.62, 0.45), rough=0.9, bump=0.3, bump_scale=8)


def tie(name, center, radius, rot=(0, 0, 0), thick=0.25):
    """束ねる紐(細いトーラス)。rot は度。"""
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=thick, major_segments=32, minor_segments=6,
                                     location=center, rotation=tuple(math.radians(a) for a in rot))
    o = bpy.context.object; o.name = name
    o.data.materials.append(string_mat())
    bpy.ops.object.shade_smooth()
    return o


def paper_tag(name, loc, rot=(0, 0, 0), size=(4.5, 7.5), color=(0.86, 0.83, 0.74)):
    """紙の荷札(文字なし、穴の位置に赤い補強リング風の点)。rot は度。"""
    m = bpy.data.materials.get("TagPaper") or C.principled("TagPaper", color, rough=0.8, bump=0.05, bump_scale=40)
    o = P.box(name, (size[0], 0.06, size[1]), loc, tuple(math.radians(a) for a in rot), mat=m)
    return o
