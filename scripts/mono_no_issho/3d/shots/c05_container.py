"""C05 / カット 5-2: 港の岸壁。扉を開けた無地の海上コンテナに、古着を圧縮した梱包(ベール)が積み込まれていく。5秒。

コンテナの奥はベールの壁(3列×4段)。手前の列の3段目が空いていて、斜めのベルトコンベアを上ってきた
ベールが先端から押し出され、空いた場所へすべり込む(フォークリフト・人は出さない)。
夕方の暖かい日差し、奥に別の無地コンテナが積まれた港(文字・ロゴ・地名なし)。カメラはゆっくり寄る。

軽量化: ベールは pet_parts.bale の形(細分化3+ディスプレイス)を流用し、色はボロノイの布模様マテリアル1種+シード違い。
遠景のコンテナは箱+波板だけ。屈折なし。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from mathutils import Vector
import common as C
import props as P
import factory_parts as F
import pet_parts as PP
import fuku_parts2 as K

FRAMES = 120
BS = (75.0, 55.0, 52.0)          # ベールの寸法(x 幅, y 奥行き, z 高さ)
FLOOR = 15.0                     # コンテナ床の上面
COLS = (-78.0, 0.0, 78.0)
ROW_Y = (192.0, 249.0, 306.0)    # 手前の列 → 奥
# コンベア: 手前の地面から、コンテナ内の 3 段目の高さまで(+Y へ上る)
CONV_A = Vector((0.0, -330.0, 45.0))     # ベルト上面の下端
CONV_B = Vector((0.0, 150.0, FLOOR + 2 * BS[2] + 1.0))   # ベルト上面の上端(3段目の床の高さ)
CONV_W = 82.0


def conv_point(s):
    """ベルト上面の、上端から s cm 手前の点(ベールの底面中心)。"""
    d = (CONV_B - CONV_A).normalized()
    return CONV_B - d * s


def build(sc):
    rnd = random.Random(5)
    F.world_gradient(top=(0.55, 0.62, 0.75), horizon=(0.75, 0.6, 0.45), bottom=(0.12, 0.10, 0.08),
                     strength=1.0, camera_color=(0.62, 0.66, 0.74))
    # --- 岸壁の地面
    ground = P.plane("Ground", (6000, 6000), (0, 600, 0), mat=F.mat_concrete("Quay", (0.42, 0.40, 0.37), rough=0.85, scale=0.004))
    line_m = C.principled("LaneLine", (0.75, 0.6, 0.12), rough=0.6)
    for x in (-260, 300):
        P.plane(f"Lane{x}", (12, 3000), (x, 600, 0.05), mat=line_m)

    # --- コンテナ(手前・扉が開いている)
    floor_m = K.mat_plank("ContFloor")
    K.container("Cont", color=(0.12, 0.33, 0.38), loc=(0, 0, 0), door_deg=252, floor_mat=floor_m)
    # 内側の暗がり用: 奥の壁に少し濃い面(ベールの隙間から見える)
    # --- 背景の積まれたコンテナ(無地・ボケ)
    cols = [(0.55, 0.18, 0.10), (0.30, 0.32, 0.34), (0.70, 0.52, 0.18), (0.12, 0.22, 0.40), (0.62, 0.62, 0.60),
            (0.18, 0.36, 0.25), (0.48, 0.12, 0.12)]
    k = 0
    for bx, by in ((-900, 900), (-900, 1700), (700, 1100), (700, 1900), (-150, 2300)):
        for lvl in range(rnd.choice((2, 3, 3, 4))):
            for j in range(3):
                K.container(f"Bg{k}", color=rnd.choice(cols), loc=(bx + j * 252 + rnd.uniform(-4, 4), by + rnd.uniform(-8, 8), lvl * 259),
                            interior=False, length=606 if rnd.random() < 0.6 else 1219)
                bpy.data.objects[f"Bg{k}"].rotation_euler.z = math.radians(90 if rnd.random() < 0.3 else 0)
                k += 1
    # 遠くのクレーン(シルエット・無地)
    crane_m = F.mat_painted("Crane", (0.55, 0.42, 0.20), rough=0.5, wear=0.05)
    for x in (-1600, 1500):
        for dx in (-250, 250):
            P.box(f"CraneLeg{x}{dx}", (60, 60, 2600), (x + dx, 3600, 1300), mat=crane_m)
        P.box(f"CraneBeam{x}", (700, 70, 90), (x, 3600, 2500), mat=crane_m)
        P.box(f"CraneBoom{x}", (90, 2600, 70), (x, 2800, 2700), mat=crane_m)

    # --- ベール(奥の壁)
    mats = [K.mat_cloth_bale(f"Bale{i}", seed=i * 1.37) for i in range(5)]
    b = 0

    def bale_at(x, y, lvl, name=None):
        nonlocal b
        root = K.cloth_bale(name or f"B{b}", BS, (x + rnd.uniform(-1.5, 1.5), y + rnd.uniform(-2, 2), FLOOR + lvl * BS[2]),
                            seed=b, mat=mats[b % len(mats)], rot_z=math.radians(rnd.choice((0, 180)) + rnd.uniform(-1.5, 1.5)))
        b += 1
        return root
    for r, y in enumerate(ROW_Y):
        for ci, x in enumerate(COLS):
            for lvl in range(4):
                if r == 0 and lvl >= 2 and not (ci == 0 and lvl == 2):
                    continue          # 手前の列: 3段目の中央・右と 4段目は空き(ここに積む)
                if r == 1 and lvl == 3 and ci == 2:
                    continue
                bale_at(x, y, lvl)

    # --- 斜めのベルトコンベア
    d = CONV_B - CONV_A
    Lc = d.length
    ang = math.atan2(d.z, d.y)
    mid = (CONV_A + CONV_B) / 2
    belt_coord = bpy.data.objects.new("BeltCoord", None); bpy.context.collection.objects.link(belt_coord)
    belt = P.box("Belt", (CONV_W - 8, Lc, 4), (0, 0, 0), mat=PP.mat_belt("BeltM", belt_coord))
    frame_m = F.mat_painted("ConvFrame", (0.62, 0.55, 0.20), rough=0.45, wear=0.2)
    rail = []
    for s in (-1, 1):
        rail.append(P.box(f"ConvRail{s}", (5, Lc + 6, 14), (s * (CONV_W / 2 - 2), 0, 3), mat=frame_m, bevel=0.6))
    for o in [belt] + rail:
        o.rotation_euler = (ang, 0, 0)
        nrm = Vector((0, -math.sin(ang), math.cos(ang)))
        o.location = mid - nrm * 2.0
    belt_coord.parent = belt
    belt_coord.rotation_euler = (0, 0, 0)
    # ベルトの流れ(ベルトの座標系で +Y)
    P.key_seq(belt_coord, "location", [(1, (0, 0, 0)), (FRAMES, (0, -150, 0))], interp="LINEAR")
    # 脚(下端側は低く、上端側は高い)
    for t in (0.12, 0.45, 0.8):
        p = CONV_A + d * t
        h = p.z - 6
        for s in (-1, 1):
            P.box(f"ConvLeg{t}{s}", (5, 5, h), (s * (CONV_W / 2 - 6), p.y, h / 2), mat=frame_m)
        P.box(f"ConvCross{t}", (CONV_W - 10, 4, 4), (0, p.y, h * 0.4), mat=frame_m)
    P.cyl("ConvEndRoller", 4.5, CONV_W - 6, (0, CONV_B.y - 1, CONV_B.z - 4.5), rot=(0, math.radians(90), 0),
          mat=C.principled("Roller", (0.6, 0.6, 0.62), metallic=1, rough=0.3), verts=24)

    # --- 動くベール
    slope = math.degrees(ang)
    speed = 2.6                                     # cm/フレーム(ベルトの速さ)
    hy = BS[1] / 2
    slot_m = Vector((COLS[1], ROW_Y[0], FLOOR + 2 * BS[2]))
    slot_r = Vector((COLS[2], ROW_Y[0], FLOOR + 2 * BS[2]))
    # A: 最初から先端にいる → 押し出されて中央の上 → 右の空きへ
    A = K.cloth_bale("BaleA", BS, (0, 0, 0), seed=91, mat=mats[1])
    pA0 = conv_point(hy + 6)
    K.key_multi(A, [(1, tuple(pA0), (slope, 0, 0), "BEZIER"),
                    (16, tuple(slot_m + Vector((0, -6, 1.5))), (0, 0, -1), "BEZIER"),
                    (24, tuple(slot_m + Vector((6, 0, 0.8))), (0, 0, 0), "BEZIER"),
                    (44, tuple(slot_r + Vector((0, 0, 0))), (0, 0, 1.2), "BEZIER")])
    # B: ベルトを上ってきて先端 → 中央の空きへすべり込む
    B = K.cloth_bale("BaleB", BS, (0, 0, 0), seed=92, mat=mats[3])
    t_end = 72
    sB0 = hy + 6 + speed * (t_end - 1)
    K.key_multi(B, [(1, tuple(conv_point(sB0)), (slope, 0, 0), "LINEAR"),
                    (t_end, tuple(conv_point(hy + 6)), (slope, 0, 0), "BEZIER"),
                    (96, tuple(slot_m + Vector((0, 0, 0))), (0, 0, -0.8), "BEZIER")])
    # C: 下からベルトに乗って上ってくる
    Cb = K.cloth_bale("BaleC", BS, (0, 0, 0), seed=93, mat=mats[0])
    sC1 = 170.0
    K.key_multi(Cb, [(1, tuple(conv_point(sC1 + speed * 119)), (slope, 0, 0), "LINEAR"),
                     (FRAMES, tuple(conv_point(sC1)), (slope, 0, 0), "LINEAR")])

    # --- 照明: 夕方の日差し(左後ろ上から、暖色)+空の拡散+コンテナ内の作業灯
    sun = bpy.data.lights.new("Sun", "SUN"); sun.energy = 5.0; sun.color = (1.0, 0.78, 0.55); sun.angle = math.radians(2.5)
    so = bpy.data.objects.new("Sun", sun); bpy.context.collection.objects.link(so)
    so.rotation_euler = (math.radians(66), 0, math.radians(32))
    inner = C.area_light((0, 90, 235), (0, 0, 0), 120, 0.8e5, (1.0, 0.86, 0.68), "ContLamp")
    C.light_look_at(inner, (0, 260, 80))
    fill = C.area_light((250, -450, 260), (0, 0, 0), 300, 4.0e5, (0.75, 0.82, 1.0), "SkyFill")
    C.light_look_at(fill, (0, 100, 80))
    P.reflection_probe((0, 0, 150), radius=900, clip_start=5)

    cam, tgt = C.camera((150, -560, 150), (0, 200, 120), lens=38, fstop=2.8)
    cam.data.dof.focus_object = None; cam.data.dof.focus_distance = 640
    P.key_seq(cam, "location", [(1, (190, -580, 150)), (FRAMES, (168, -525, 145))])
    P.key_seq(tgt, "location", [(1, (10, 200, 118)), (FRAMES, (15, 205, 120))])
    sc.view_settings.exposure = 0.0
    sc.view_settings.look = "AgX - Medium High Contrast"


if __name__ == "__main__":
    C.EPISODE = "ep04"
    C.run_shot("c05_container", build, FRAMES)
