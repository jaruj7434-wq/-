"""P04 / カット5-1: リサイクル工場。つぶして四角く固めたペットボトルの塊(ベール)が、
針金でしばられてベルトコンベアで右へ運ばれていく。奥には積み上げたベールの山。5秒。

ベールはボトルを1本ずつ作らず、凸凹の箱+「つぶれたボトル」のボロノイ模様(不透明)で表現する。
透明素材は使わない(描画を軽く)。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P
import factory_parts as F
import pet_parts as PP

FRAMES = 120
SPEED = 30.0          # cm/s(ベルトの速さ)
BELT_H = 70.0         # ベルト上面の高さ
BALE = (100.0, 95.0, 80.0)
GAP = 190.0           # ベールの間隔


def build(sc):
    rnd = random.Random(4)
    F.world_gradient(top=(0.5, 0.48, 0.45), horizon=(0.12, 0.11, 0.1), bottom=(0.03, 0.03, 0.03), strength=0.8,
                     camera_color=(0.03, 0.03, 0.035), strips=6.0)
    F.factory_hall(size=(5000, 2400, 900), center=(0, 700, 0), floor_mat=F.mat_concrete("FloorC", (0.17, 0.17, 0.16), rough=0.6), wall_color=(0.16, 0.17, 0.18),
                   lamp_rows=[(200, 8), (700, 8), (1200, 8)], lamp_strength=30.0, lamp_temp=4800)

    # ベルトの模様を流すための基準 Empty(ベルトと同じ速さで -X へ動かす → 模様は +X へ流れる)
    flow = bpy.data.objects.new("BeltFlow", None); bpy.context.collection.objects.link(flow)
    dist = SPEED * FRAMES / C.FPS
    P.key_seq(flow, "location", [(1, (0, 0, 0)), (FRAMES, (-dist, 0, 0))], interp="LINEAR")
    PP.conveyor("Conv", 1800, 120, BELT_H, (0, 0, 0), belt_mat=PP.mat_belt("BeltM", flow))
    # 床の黄色ライン(通路の区切り)
    P.box("FloorLine", (1400, 10, 0.2), (0, -175, 0.1), mat=C.principled("LineM", (0.8, 0.6, 0.05), rough=0.6))

    # ---- コンベア上のベール(右へ流れる)
    mats = [PP.mat_bale(f"BaleM{i}", seed=i * 1.7) for i in range(3)]
    for i in range(6):
        x0 = -760 + i * GAP + rnd.uniform(-10, 10)
        size = (BALE[0] + rnd.uniform(-6, 6), BALE[1] + rnd.uniform(-4, 4), BALE[2] + rnd.uniform(-5, 5))
        b = PP.bale(f"Bale{i}", size, (x0, rnd.uniform(-4, 4), BELT_H), seed=i, mat=mats[i % 3], surface=55)
        b.rotation_euler = (0, 0, math.radians(rnd.uniform(-3, 3)))
        P.key_seq(b, "location", [(1, (x0, b.location.y, BELT_H)), (FRAMES, (x0 + dist, b.location.y, BELT_H))], interp="LINEAR")

    # ---- 奥: 積み上げたベールの山(静止)
    k = 0
    for col in range(5):
        for row in range(3 if col % 2 == 0 else 2):
            x = -500 + col * 115 + rnd.uniform(-6, 6)
            b = PP.bale(f"Stack{k}", (105, 95, 82), (x, 400 + rnd.uniform(-8, 8), row * 84), seed=10 + k, mat=mats[k % 3], straps=3, surface=25)
            b.rotation_euler = (0, 0, math.radians(rnd.uniform(-4, 4)))
            k += 1
    for col in range(3):
        x = 200 + col * 115
        for row in range(2):
            b = PP.bale(f"StackR{col}_{row}", (105, 95, 82), (x, 430, row * 84), seed=30 + col * 2 + row, mat=mats[(col + row) % 3], straps=3, surface=25)
    # 鉄骨の柱(手前と奥)
    beam = F.mat_painted("Beam", (0.2, 0.32, 0.4), rough=0.5, wear=0.2, scale=0.03)
    for x in (-700, 700):
        P.box(f"BeamF{x}", (35, 35, 900), (x, 160, 450), mat=beam)

    # ---- 照明: 天井の照明(大きなエリア)+ 右手前からのキー + 奥のリム
    top = C.area_light((0, 100, 700), (0, 0, 0), 900, 2.0e6, (1.0, 0.97, 0.92), "Top")
    key = C.area_light((-650, -260, 260), (0, 0, 0), 200, 2.4e6, (1.0, 0.93, 0.82), "Key"); C.light_look_at(key, (0, 0, 90))   # 左から斜めに当てて凹凸を出す
    rim = C.area_light((-300, 450, 300), (0, 0, 0), 300, 1.2e6, (0.8, 0.88, 1.0), "Rim"); C.light_look_at(rim, (0, 0, 110))
    fill = C.area_light((400, -500, 200), (0, 0, 0), 300, 3e5, (0.85, 0.9, 1.0), "Fill"); C.light_look_at(fill, (0, 0, 100))
    P.reflection_probe((0, 0, 150), radius=900, clip_start=2)

    # ---- カメラ: ライン右手前の低い位置から上流を見る(ベールがこちらへ向かってくる)
    cam, tgt = C.camera((260, -400, 165), (-60, 0, 100), lens=35, fstop=0.05)
    P.key_seq(cam, "location", [(1, (250, -410, 168)), (FRAMES, (290, -385, 160))])
    P.key_seq(tgt, "location", [(1, (-80, 0, 102)), (FRAMES, (-30, 0, 98))])
    cam.data.dof.focus_object = None; cam.data.dof.focus_distance = 460
    sc.view_settings.exposure = 0.0


if __name__ == "__main__":
    C.EPISODE = "ep03"
    C.run_shot("p04_bale_conveyor", build, FRAMES)
