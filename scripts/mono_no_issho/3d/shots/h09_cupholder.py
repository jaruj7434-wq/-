"""H09c / カット3-5: 眠る小銭③「車のドリンクホルダー」。夜の車内、センターコンソールの
カップホルダーに小銭が溜まっている。窓の外を街灯が流れ、オレンジの光が周期的に横切る。
カメラはゆっくりホルダーへ寄る(静物)。5秒。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P

FRAMES = 120
HOLES = [(0.0, 0.0), (0.0, 9.5)]
HR, HD = 3.9, 5.5   # ホルダー半径・深さ


def mat_plastic(name, color=(0.012, 0.012, 0.013), rough=0.55, grain=40):
    """シボ加工の黒い樹脂。"""
    return C.principled(name, color, rough=rough, noise_rough=(rough * 0.8, rough * 1.2), bump=0.15, bump_scale=grain)


def build(sc):
    P.world_studio((0.005, 0.006, 0.01), (0.02, 0.025, 0.04), (0.10, 0.12, 0.18), 1.0, camera_color=(0.004, 0.005, 0.008))
    rnd = random.Random(33)
    plastic = mat_plastic("Plastic")
    # コンソール上面(穴あき)
    con = P.box("Console", (20, 34, 12), (0, 4.5, -6), mat=plastic)
    for i, (x, y) in enumerate(HOLES):
        cut = P.cyl(f"Cut{i}", HR, HD * 2, (x, y, 0), verts=64)
        bo = con.modifiers.new(f"b{i}", "BOOLEAN"); bo.object = cut; bo.solver = "EXACT"
        bpy.context.view_layer.objects.active = con
        bpy.ops.object.modifier_apply(modifier=f"b{i}")
        bpy.data.objects.remove(cut, do_unlink=True)
    P.add_mod(con, "BEVEL", width=0.35, segments=3, limit_method="ANGLE")
    bpy.context.view_layer.objects.active = con
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    P.passive_mesh(con, friction=0.6, margin=0.02)
    rubber = C.principled("RubberMat", (0.03, 0.03, 0.035), rough=0.85)
    for i, (x, y) in enumerate(HOLES):
        b = P.cyl(f"HolderBottom{i}", HR + 0.1, 0.5, (x, y, -HD + 0.25), mat=rubber)
        C.rigid(b, False, "CYLINDER", friction=0.7)
        # 内側のゴムのツメ(3方向)
        for k in range(3):
            a = k * math.tau / 3 + 0.4
            P.box(f"Tab{i}{k}", (0.4, 1.4, 2.5), (x + (HR - 0.15) * math.cos(a), y + (HR - 0.15) * math.sin(a), -1.6),
                  (0, 0, a), mat=rubber, bevel=0.15)
            C.rigid(bpy.context.object, False, "BOX", friction=0.6)
    # 小銭(ホルダー1にたまる) — 物理で積もらせて固定
    kinds = ["1"] * 22 + ["10", "10", "100", "5", "1", "50", "10", "1", "10", "5", "100", "1", "1"]
    rnd.shuffle(kinds)
    P.drop_pile(kinds, HOLES[0], 1.6, -3.0, seed=34, friction=0.5)
    P.drop_pile(["1", "10", "1"], HOLES[1], 1.4, -3.0, seed=35, friction=0.5, prefix="Q")
    P.settle(sc, 60)

    # 周囲: シフト周りのパネル(ピアノブラック)、左右の座席、アームレスト
    gloss = C.principled("PianoBlack", (0.01, 0.01, 0.012), rough=0.08, coat=1.0)
    P.box("ShiftPanel", (20, 18, 3), (0, -16, -1.0), (math.radians(-12), 0, 0), gloss, bevel=0.5)
    P.box("ShiftBoot", (5, 7, 4), (0, -17, 1.5), mat=C.principled("BootLeather", (0.03, 0.03, 0.03), rough=0.5, bump=0.3, bump_scale=8), bevel=1.5)
    P.box("Armrest", (19, 26, 8), (0, 36, 2), mat=C.principled("ArmLeather", (0.045, 0.04, 0.038), rough=0.45, bump=0.25, bump_scale=6), bevel=2.5)
    fabric = C.principled("SeatFabric", (0.05, 0.05, 0.055), rough=0.9, bump=0.4, bump_scale=30)
    for s in (-1, 1):
        P.box(f"Seat{s}", (50, 60, 25), (s * 37, 15, -2), mat=fabric, bevel=6)
        P.box(f"Back{s}", (50, 15, 70), (s * 37, 52, 30), (math.radians(-12), 0, 0), fabric, bevel=6)
    # ステッチ(アームレスト)
    thread = C.principled("Stitch", (0.35, 0.33, 0.3), rough=0.7)
    st = P.box("ArmStitch", (0.25, 0.6, 0.1), (-8, 23.4, 6.0), mat=thread)
    P.add_mod(st, "ARRAY", count=40, use_relative_offset=False, use_constant_offset=True, constant_offset_displace=(0.41, 0, 0))

    # 照明: メーター類の淡い青、天井のマップランプ(暖色・弱め)、窓外を流れる街灯(オレンジ)
    C.area_light((0, -60, 25), (70, 0, 0), 40, 3000, (0.35, 0.55, 1.0), "Dash")
    C.area_light((0, 10, 90), (0, 0, 0), 10, 25000, (1.0, 0.85, 0.65), "MapLamp")
    sweep = C.area_light((-120, 30, 60), (0, 0, 0), 30, 50000, (1.0, 0.55, 0.2), "StreetLight")
    C.light_look_at(sweep, (0, 0, 0))
    # 2秒ごとに左前→右後ろへ流れる(車が進んでいる感)
    for f0 in (-20, 28, 76):
        C.key(sweep, "location", f0, (-140, -120, 70))
        C.key(sweep, "location", f0 + 40, (140, 140, 70))
    for fc in P._fcurves(sweep):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    tr = sweep.constraints.new("TRACK_TO"); tr.target = bpy.data.objects["Console"]
    # 強さも通過時だけ上がるように(光の帯)
    L = sweep.data
    for f0 in (-20, 28, 76):
        for df, e in ((0, 0), (12, 50000), (28, 50000), (40, 0)):
            L.energy = e; L.keyframe_insert("energy", frame=f0 + df)

    cam, tgt = C.camera((-6, -22, 30), (0, 2, -2), lens=55, fstop=0.035)  # 実効 F3.5
    P.key_seq(cam, "location", [(1, (-10, -28, 34)), (FRAMES, (-3, -17, 26))])
    P.key_seq(tgt, "location", [(1, (0, 3, -1)), (FRAMES, (0, 0.5, -2))])
    sc.view_settings.exposure = 0.6


if __name__ == "__main__":
    C.run_shot("h09_cupholder", build, FRAMES)
