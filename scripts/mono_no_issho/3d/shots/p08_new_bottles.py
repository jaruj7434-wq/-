"""P08 / カット(ラスト): お店の棚に並んだ新しい透明ボトル(中身は水、ラベルなし/無地のラベル、文字・ロゴなし)。
白い棚が3段、各段に奥まで4列。斜めから見て、カメラはゆっくり横へドリーしながら少し寄る。5秒。第3話のラスト。

軽量化: 屈折する透明マテリアルは中段の最前列・画面に入る範囲の 24 本だけ。他は「透明っぽく見える」
不透明マテリアル(屈折・半透明なし)で、ボケの中に並ぶ。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from mathutils import Vector
import common as C
import props as P
import factory_parts as F
import pet_parts2 as Q

FRAMES = 120
SHELF_Z = (35.0, 76.0, 117.0)       # 棚板の上面
DEPTH = 46.0
PITCH = 7.3
COLS = 34
ROWS = 4
FILL_Z = 16.2
N_REFRACT_MAX = 30
# 商品グループ(4〜5本ずつ同じ見た目): (キャップ色, ラベル色 or None)
GROUPS = [((0.92, 0.93, 0.94), None), ((0.25, 0.55, 0.85), (0.80, 0.90, 0.97)), ((0.35, 0.7, 0.45), (0.86, 0.95, 0.88)),
          ((0.92, 0.93, 0.94), (0.97, 0.97, 0.95)), ((0.2, 0.35, 0.6), None), ((0.95, 0.75, 0.3), (0.98, 0.93, 0.8))]


def shelf_unit(white, grey, tag_m, led_m):
    W = COLS * PITCH + 16
    # 背板(有孔ボード風)
    peg, nt, out = C.node_mat("Pegboard")
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
    C.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    vo = n.new("ShaderNodeTexVoronoi"); vo.feature = "F1"; vo.inputs["Scale"].default_value = 1 / 2.5
    vo.inputs["Randomness"].default_value = 0.0
    C.link(nt, mp.outputs["Vector"], vo.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.1; cr.color_ramp.elements[0].color = (0.12, 0.13, 0.15, 1)
    cr.color_ramp.elements[1].position = 0.14; cr.color_ramp.elements[1].color = (0.42, 0.47, 0.52, 1)
    C.link(nt, vo.outputs["Distance"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.45
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"]); C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    P.box("Back", (W, 1.5, 175), (0, DEPTH / 2 + 1, 175 / 2 - 5), mat=peg)
    for i, z in enumerate(SHELF_Z):
        P.box(f"Shelf{i}", (W, DEPTH + 2, 1.6), (0, 0, z - 0.8), mat=white, bevel=0.2)
        # 前縁のレール(値札は無地)
        P.box(f"Rail{i}", (W, 1.2, 4.2), (0, -DEPTH / 2 - 1.4, z - 1.6), mat=grey, bevel=0.2)
        for k in range(0, COLS, 5):
            x = (k - COLS / 2 + 2.5) * PITCH
            P.box(f"Tag{i}_{k}", (6.5, 0.3, 3.2), (x, -DEPTH / 2 - 2.1, z - 1.6), mat=tag_m, bevel=0.1)
        # 上の棚板の裏に LED(下の段の商品を照らす)
        if i > 0:
            P.box(f"LED{i}", (W - 4, 1.0, 0.4), (0, -DEPTH / 2 + 2, z - 1.8), mat=led_m)
            l = C.area_light((0, -DEPTH / 2 + 4, z - 2.5), (0, 0, 0), 1, 2.2e4, (1.0, 0.97, 0.92), f"ShelfLight{i}")
            l.data.shape = "RECTANGLE"; l.data.size = W - 10; l.data.size_y = 6
            l.rotation_euler = (math.radians(25), 0, 0)
    # 側板
    for s in (-1, 1):
        P.box(f"Side{s}", (2.0, DEPTH + 4, 175), (s * (W / 2 + 1), 0, 175 / 2 - 5), mat=white, bevel=0.3)
    P.box("Kick", (W, 2, 30), (0, -DEPTH / 2, 15), mat=grey)
    P.box("TopHeader", (W, DEPTH + 4, 4), (0, 0, 170), mat=white)


def build(sc):
    rnd = random.Random(8)
    P.world_studio((0.05, 0.05, 0.05), (0.25, 0.25, 0.24), (0.9, 0.9, 0.88), 1.0, camera_color=(0.2, 0.2, 0.2))
    white = C.principled("ShelfWhite", (0.86, 0.87, 0.87), rough=0.35, coat=0.2)
    grey = C.principled("RailGrey", (0.55, 0.57, 0.6), rough=0.4)
    tag_m = C.principled("TagBlank", (0.95, 0.95, 0.93), rough=0.6)
    led_m = C.emissive("LEDM", temp=5200, strength=12)
    shelf_unit(white, grey, tag_m, led_m)
    # 店の床・向かいの棚(ボケ)
    P.plane("Floor", (2000, 2000), (0, -400, -5), mat=C.principled("StoreFloor", (0.5, 0.5, 0.48), rough=0.2, coat=0.4))
    P.plane("Ceil", (2000, 2000), (0, -400, 260), rot=(180, 0, 0), mat=C.principled("StoreCeil", (0.7, 0.7, 0.7), rough=0.8))
    lamp = C.emissive("CeilLamp", temp=4800, strength=8)
    for i in range(-3, 4):
        P.box(f"CeilLamp{i}", (120, 18, 2), (i * 180, -120, 258), mat=lamp)

    # --- ボトル
    meshes = Q.bottle_meshes(fill_z=FILL_Z)
    clear = Q.mat_clear_pet("PETClear", rough=0.02, thickness=0.04)
    water = Q.mat_clear_pet("PETWater", tint=(0.95, 0.98, 1.0), rough=0.01, ior=1.33, slab=False, thickness=6.0)
    surf = Q.mat_clear_pet("WaterSurf", tint=(0.95, 0.98, 1.0), rough=0.02, ior=1.33, thickness=0.05)
    fake_top = Q.mat_fake_clear("FakeEmpty", tint=(0.5, 0.55, 0.58), edge=(0.05, 0.06, 0.07))
    fake_fill = Q.mat_fake_clear("FakeFill", tint=(0.42, 0.5, 0.55), edge=(0.04, 0.05, 0.07))
    caps = {}
    labels = {}
    for gi, (cc, lc) in enumerate(GROUPS):
        caps[gi] = C.principled(f"Cap{gi}", cc, rough=0.35, coat=0.2)
        if lc:
            labels[gi] = C.principled(f"Label{gi}", lc, rough=0.5, coat=0.3)
    cam_x = (-75.0, 140.0)   # 中段最前列で画面に入る範囲(x)
    n_ref = 0
    for ti, z in enumerate(SHELF_Z):
        for c in range(COLS):
            gi = (c // 5 + ti * 2) % len(GROUPS)
            x = (c - COLS / 2 + 0.5) * PITCH
            for r in range(ROWS):
                if ti == 2 and r == 0 and c in (9, 10):   # 少し売れている(上段の手前が空き)
                    continue
                y = -DEPTH / 2 + 4.5 + r * (PITCH + 0.6)
                refract = (ti == 1 and r == 0 and cam_x[0] <= x <= cam_x[1] and n_ref < N_REFRACT_MAX)
                if refract:
                    n_ref += 1
                    mats, wm = [clear, water], surf
                else:
                    mats, wm = [fake_top, fake_fill], None
                jit = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0))
                Q.make_bottle(f"B{ti}_{c}_{r}", Vector((x, y, z)) + jit, mats, cap_mat=caps[gi],
                              label_mat=labels.get(gi), meshes=meshes, rot_z=rnd.uniform(0, math.tau), water=wm)
    print(f"[p08] refractive bottles={n_ref}")

    # --- 照明: 店の天井光(前上の大きな面光源)+左右から斜めの光(ボトルの縁に映り込み)
    key = C.area_light((-60, -260, 230), (0, 0, 0), 300, 1.6e6, (1.0, 0.94, 0.86), "Key"); C.light_look_at(key, (0, 0, 80))
    side = C.area_light((-300, -80, 110), (0, 0, 0), 100, 4e5, (0.9, 0.95, 1.0), "SideL"); C.light_look_at(side, (0, 0, 85))
    side2 = C.area_light((300, -120, 120), (0, 0, 0), 100, 3e5, (1.0, 0.95, 0.9), "SideR"); C.light_look_at(side2, (0, 0, 85))
    P.light_card("CardA", (220, 60), (-80, -200, 140), (0, 0, 85), strength=3.0)
    P.light_card("CardB", (60, 200), (160, -160, 90), (0, 0, 85), strength=2.0)
    P.reflection_probe((0, -40, 90), radius=300, clip_start=1)

    cam, tgt = C.camera((-70, -80, 88), (20, -12, 86), lens=45, fstop=0.02)
    cam.data.dof.focus_object = None
    P.key_seq(cam, "location", [(1, (-84, -86, 89)), (FRAMES, (-44, -74, 87))])
    P.key_seq(tgt, "location", [(1, (6, -12, 86)), (FRAMES, (40, -12, 85.5))])
    # ピントは中段の最前列(カメラからの距離をフレームごとに合わせる)
    fr = list(range(1, FRAMES + 1, 4)) + [FRAMES]
    vals = []
    for f in fr:
        sc.frame_set(f)
        bpy.context.view_layer.update()
        cp = cam.matrix_world.translation
        fwd = (tgt.matrix_world.translation - cp).normalized()
        vals.append((((-DEPTH / 2 + 4.5) - cp.y) / fwd.y,))     # 視線が最前列の面に当たる距離
    for f, (v,) in zip(fr, vals):
        cam.data.dof.focus_distance = v
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    sc.frame_set(1)
    sc.view_settings.exposure = 0.3
    sc.view_settings.look = "AgX - Medium High Contrast"


if __name__ == "__main__":
    C.EPISODE = "ep03"
    C.run_shot("p08_new_bottles", build, FRAMES)
