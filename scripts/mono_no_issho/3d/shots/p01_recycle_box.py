"""P01 / カット1-1: 昼下がりの歩道。無地の自販機(ロゴなし)の横に、ボトル回収ボックス。
上から透明なペットボトルが一本落ちてきて、丸い投入口に「コトン」と入る。カメラはゆっくり寄る。5秒。

- 1〜48f: 自販機と回収ボックスのミディアム(ゆっくりドリーイン)
- 48〜63f: 画面上からボトル(キャップ・ラベルなし)が落ちてくる(少し傾き→まっすぐ)
- 63〜70f: 投入口に吸い込まれ、ボックスがわずかに揺れる
透明素材はボトル1本と自販機の窓だけ。
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P
import factory_parts as F
import pet_parts as PP
from k08_last_umbrella import mat_pavers

FRAMES = 120
VM_X = -58.0
BOX_X = 30.0
ENTER = 63          # ボトルの底が投入口のフチを通る
G = 420.0           # 見やすいよう少しスロー(実重力 981 cm/s^2 の約0.43倍)


def build(sc):
    P.world_studio((0.12, 0.11, 0.1), (0.55, 0.58, 0.62), (0.45, 0.6, 0.85), 0.6, camera_color=(0.55, 0.62, 0.72))
    P.plane("Ground", (3000, 2000), (0, -300, 0), mat=mat_pavers("Pavers", base=(0.46, 0.44, 0.41)))
    P.box("Curb", (3000, 18, 12), (0, -330, 6), mat=F.mat_concrete("CurbM", (0.5, 0.49, 0.47)))
    # 背後の塀(ブロック目地)
    wall = C.principled("BlockWall", (0.58, 0.56, 0.52), rough=0.9, bump=0.25, bump_scale=0.3)
    P.box("Wall", (3000, 15, 180), (0, 55, 90), mat=wall)
    jm = C.principled("JointM", (0.38, 0.37, 0.35), rough=0.9)
    for i in range(1, 10):
        P.box(f"Joint{i}", (3000, 0.6, 0.8), (0, 47.3, i * 19.5), mat=jm)
    P.box("WallCap", (3000, 18, 4), (0, 55, 182), mat=F.mat_concrete("CapM2", (0.55, 0.54, 0.52)))

    fy = PP.vending_machine(VM_X, 0.0, body_color=(0.86, 0.87, 0.88), accent=(0.12, 0.38, 0.62), glow=1.6)
    # 回収ボックス2台(手前の緑ふた=ペットボトル、右の青ふた=缶)。前面を自販機とそろえる
    hole = PP.recycle_box(BOX_X, fy + 20, lid_color=(0.1, 0.45, 0.28))
    bpy.data.objects["RBHoleIn"].location.z = hole[2] - 7 - 20
    box_objs = [o for o in bpy.data.objects if o.name.startswith("RB")]
    # 2台目(名前を付け替えて複製を避け、別色で作る)
    for o in box_objs:
        o.name = "P" + o.name
    PP.recycle_box(BOX_X + 52, fy + 20, lid_color=(0.1, 0.28, 0.6), hole_r=4.6)
    for o in [o for o in bpy.data.objects if o.name.startswith("RB")]:
        if o.name == "RBHoleIn":
            o.location.z = 88 - 7 - 20

    # ---- ボトル(キャップ・ラベルなし)。底が原点
    b = PP.bottle("Bottle", (0, 0, 0), cap=False, label=False, mat=PP.mat_pet("PET", a_min=0.1, a_max=0.8, glow=0.25))
    body = b["body"]
    z_rim = hole[2]
    z0 = 175.0
    t_hit = math.sqrt(2 * (z0 - z_rim) / G)
    f0 = ENTER - t_hit * C.FPS
    for f in range(int(f0) - 1, ENTER + 9):
        t = max(0.0, (f - f0) / C.FPS)
        z = z0 - 0.5 * G * t * t
        u = min(1.0, max(0.0, (f - f0) / (ENTER - f0)))
        x = hole[0] + 6.0 * (1 - u) ** 2
        y = hole[1] - 2.0 * (1 - u) ** 2
        tilt = math.radians(-16) * (1 - u) ** 1.5
        body.location = (x, y, z)
        body.rotation_euler = (math.radians(4) * (1 - u), tilt, math.radians(30))
        body.keyframe_insert("location", frame=f); body.keyframe_insert("rotation_euler", frame=f)
    F.set_interp(body, "LINEAR")
    body.hide_render = True; body.keyframe_insert("hide_render", frame=1)
    body.hide_render = False; body.keyframe_insert("hide_render", frame=int(f0))
    body.hide_render = True; body.keyframe_insert("hide_render", frame=ENTER + 9)
    F.set_interp(body, "CONSTANT", path="hide_render")

    # ボトルが底に当たる「コトン」: ボックスがわずかに揺れる
    pivot = bpy.data.objects.new("BoxPivot", None); bpy.context.collection.objects.link(pivot)
    pivot.location = (BOX_X, fy + 20, 0)
    bpy.context.view_layer.update()
    for o in [o for o in bpy.data.objects if o.name.startswith("PRB")]:
        if o.parent is None:
            mw = o.matrix_world.copy(); o.parent = pivot; o.matrix_world = mw
    for f, a in ((1, 0), (ENTER + 6, 0), (ENTER + 8, 0.6), (ENTER + 11, -0.35), (ENTER + 15, 0.15), (ENTER + 20, 0)):
        pivot.rotation_euler = (math.radians(a), 0, 0); pivot.keyframe_insert("rotation_euler", frame=f)

    # ---- 照明: 午後の日差し(右手前上から。自販機の影は左の塀へ)+ 空の補助光
    bpy.ops.object.light_add(type="SUN")
    sun = bpy.context.object; sun.name = "Sun"
    sun.data.energy = 4.5; sun.data.angle = math.radians(2.0); sun.data.color = (1.0, 0.92, 0.8)
    sun.rotation_euler = (math.radians(52), 0, math.radians(38))
    fill = C.area_light((150, -320, 260), (0, 0, 0), 300, 4.0e5, (0.85, 0.9, 1.0), "SkyFill")
    C.light_look_at(fill, (BOX_X, fy, 80))
    rim = C.area_light((120, 40, 200), (0, 0, 0), 80, 1.2e5, (1.0, 0.96, 0.9), "BottleRim")
    C.light_look_at(rim, (hole[0], hole[1], 115))
    P.light_card("Card", (120, 120), (140, -200, 180), (hole[0], hole[1], 110), strength=1.5)
    P.reflection_probe((0, -60, 100), radius=400, clip_start=1)

    # ---- カメラ: ミディアム → 投入口へゆっくり寄る(左に自販機の窓を残す)
    cam, tgt = C.camera((95, -300, 150), (-5, -10, 100), lens=40, fstop=0.06)
    P.key_seq(cam, "location", [(1, (95, -290, 215)), (FRAMES, (58, -175, 178))])
    P.key_seq(tgt, "location", [(1, (-2, -12, 92)), (FRAMES, (16, -18, 94))])
    cam.data.dof.focus_object = None
    cam.data.dof.focus_distance = 280
    cam.data.keyframe_insert("dof.focus_distance", frame=1)
    cam.data.dof.focus_distance = 195
    cam.data.keyframe_insert("dof.focus_distance", frame=FRAMES)
    sc.view_settings.exposure = 0.0


if __name__ == "__main__":
    C.EPISODE = "ep03"
    C.run_shot("p01_recycle_box", build, FRAMES)
