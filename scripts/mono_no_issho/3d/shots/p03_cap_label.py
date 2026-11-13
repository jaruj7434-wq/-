"""P03 / カット4-1: 食卓の上のペットボトル(架空ラベル・文字なし)。手は出さずに、
キャップがくるくる回って外れて浮かび上がり、ラベルが継ぎ目からはがれてほどけ、ふわりと飛んでいく。
最後に透明なボトルだけが残る。5秒。

- 1〜12f: 静止(窓からのやわらかい光)
- 12〜40f: キャップが反時計回りに回りながら外れる → 40〜70f で上へ浮かぶ(ゆっくり回転)
- 44〜84f: ラベルが継ぎ目からほどける(シェイプキーを段階的に切り替え)
- 84〜112f: ラベルは右へ、キャップは左上へ、画面の外へ流れていく
- 112〜120f: 透明なボトルだけ
透明素材はボトル1本だけ。
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P
import factory_parts as F
import pet_parts as PP
from k06_umbrella_explode import backdrop

FRAMES = 120
UNSCREW = (12, 40)
FLOAT = (40, 70)
PEEL = (44, 84)
AWAY = (84, 112)
SEAM_DEG = 54.0      # ラベルの継ぎ目の向き(はがれ途中で印刷面がカメラを向き、右へほどける)


def build(sc):
    P.world_studio((0.05, 0.045, 0.04), (0.25, 0.23, 0.2), (0.75, 0.75, 0.72), 0.5, camera_color=(0.1, 0.09, 0.08))
    # 食卓(木)
    P.box("Table", (240, 140, 4), (0, 20, -2), mat=P.mat_wood("TableWood", base=(0.3, 0.19, 0.1), dark=(0.17, 0.1, 0.05), scale=0.05, rough=0.8))

    # ボトル(キャップ・ラベル付き)
    lab = PP.mat_label("Label", base=(0.06, 0.42, 0.36), stripe=(0.96, 0.95, 0.9), accent=(0.95, 0.72, 0.15))
    b = PP.bottle("Bottle", (0, 0, 0), (0, 0, 0), mat=PP.mat_pet("PET", a_min=0.08, a_max=0.7, glow=0.02),
                  cap_color=(0.95, 0.5, 0.08), label_mat=lab)
    body, cap, label = b["body"], b["cap"], b["label"]

    # ---- キャップ: 回して外す → 浮かぶ → 左上へ
    cz = PP.TOP_Z - 1.45
    keys = [(1, (0, 0, cz), (0, 0, 0)),
            (UNSCREW[0], (0, 0, cz), (0, 0, 0)),
            (UNSCREW[1], (0, 0, cz + 1.7), (0, 0, math.tau * 2.25)),
            (FLOAT[1], (-3.5, 0.5, cz + 7.5), (math.radians(-18), math.radians(-14), math.tau * 2.9)),
            (AWAY[0], (-6.0, 1.0, cz + 9.0), (math.radians(-26), math.radians(-20), math.tau * 3.25)),
            (AWAY[1], (-26.0, 3.0, cz + 18.0), (math.radians(-40), math.radians(-30), math.tau * 3.9))]
    for f, loc, rot in keys:
        C.key(cap, "location", f, loc); C.key(cap, "rotation_euler", f, rot)
    C.ease_all(cap, "BEZIER")

    # ---- ラベル: 継ぎ目からほどける(段階シェイプキー)→ 右へ飛ぶ
    label.rotation_euler = (0, 0, math.radians(SEAM_DEG))
    n = 12
    ps, fr = [], []
    for i in range(n + 1):
        u = i / n
        ps.append(u)
        e = 0.5 - 0.5 * math.cos(math.pi * u)          # ease in-out
        fr.append(round(PEEL[0] + (PEEL[1] - PEEL[0]) * e) if 0 < i < n else (PEEL[0] if i == 0 else PEEL[1]))
    for i in range(1, len(fr)):                          # 同じフレームが続かないように
        if fr[i] <= fr[i - 1]:
            fr[i] = fr[i - 1] + 1
    coords = [PP.label_coords(p, curl=0.25 + 0.5 * p) for p in ps]
    PP.stage_keys(label, coords, fr, prefix="Peel")
    sd = math.radians(SEAM_DEG)
    C.key(label, "location", 1, (0, 0, 0)); C.key(label, "location", AWAY[0], (0, 0, 0))
    C.key(label, "rotation_euler", 1, (0, 0, sd)); C.key(label, "rotation_euler", AWAY[0], (0, 0, sd))
    C.key(label, "location", AWAY[1], (34, -6, 10))
    C.key(label, "rotation_euler", AWAY[1], (math.radians(25), math.radians(-35), sd + math.radians(40)))
    C.ease_all(label, "BEZIER")

    # ---- 照明: 左の窓からの大きな柔らかい光 + 右奥のリム(透明ボトルの輪郭) + 手前の弱い補助
    win = C.area_light((-90, -30, 60), (0, 0, 0), 80, 1.2e5, (1.0, 0.95, 0.88), "Window"); C.light_look_at(win, (0, 0, 10))
    rim = C.area_light((45, 70, 35), (0, 0, 0), 30, 1.2e5, (0.85, 0.92, 1.0), "Rim"); C.light_look_at(rim, (0, 0, 12))
    rim2 = C.area_light((-45, 70, 30), (0, 0, 0), 30, 9e4, (1.0, 0.95, 0.9), "Rim2"); C.light_look_at(rim2, (0, 0, 12))
    fill = C.area_light((30, -90, 30), (0, 0, 0), 60, 1.5e4, (0.95, 0.97, 1.0), "Fill"); C.light_look_at(fill, (0, 0, 12))
    P.light_card("WinCard", (40, 60), (-60, -20, 30), (0, 0, 12), strength=2.0)
    P.light_card("BackCard", (30, 50), (25, 60, 20), (0, 0, 12), strength=1.5)
    P.reflection_probe((0, 0, 12), radius=120, clip_start=0.2)

    # ---- カメラ: 目線よりやや上から、ほんの少し寄る
    cam, tgt = C.camera((14, -84, 22), (0, 0, 13.5), lens=50)
    P.key_seq(cam, "location", [(1, (16, -88, 23)), (FRAMES, (9, -76, 20))])
    # 透明(BLENDED)のボトルは深度を書かないので、被写界深度をかけると背景の深度でぼけてしまう → DOF なし
    cam.data.dof.use_dof = False
    backdrop(cam, dist=250, top=(0.1, 0.09, 0.08), bottom=(0.035, 0.03, 0.026), glow=(0.16, 0.14, 0.12), glow_center=(0.2, 0.65))
    sc.view_settings.exposure = 0.0


if __name__ == "__main__":
    C.EPISODE = "ep03"
    C.run_shot("p03_cap_label", build, FRAMES)
