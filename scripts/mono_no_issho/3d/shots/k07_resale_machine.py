"""K07 / カット5-4: 夜の駅構内。引き取り手のない傘を売り直す自販機風の機械(無名・ロゴ・文字なし)。
ガラス越しに縦の仕切りに1本ずつ立てられた傘(ビニール傘・布傘)が並び、ボタンと無地の価格表示が光る。
柔らかな夜の照明。カメラはゆっくり寄る。5秒。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P
import factory_parts as F
import kasa_parts as K

FRAMES = 120
MW, MD, MH = 118.0, 62.0, 192.0     # 機械の幅・奥行・高さ
FY = -MD / 2                         # 前面
WALL_Y = MD / 2 + 4
WIN = (64.0, 178.0)                  # 陳列窓の下端・上端
COLS = 8


def mat_tile(name, color=(0.78, 0.78, 0.75), grout=(0.35, 0.35, 0.34), size=15.0, rough=0.25, vertical=False):
    """目地のあるタイル(壁・床)。size cm 角。オブジェクト座標。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    br = n.new("ShaderNodeTexBrick")
    br.offset = 0.0
    br.inputs["Color1"].default_value = (*color, 1)
    br.inputs["Color2"].default_value = (color[0] * 0.93, color[1] * 0.93, color[2] * 0.92, 1)
    br.inputs["Mortar"].default_value = (*grout, 1)
    br.inputs["Scale"].default_value = 1.0 / size
    br.inputs["Mortar Size"].default_value = 0.02
    br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0
    if vertical:   # XZ 面(壁)用: z を y に回す
        mp = n.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
        C.link(nt, tc.outputs["Object"], mp.inputs["Vector"]); C.link(nt, mp.outputs["Vector"], br.inputs["Vector"])
    else:
        C.link(nt, tc.outputs["Object"], br.inputs["Vector"])
    p = n.new("ShaderNodeBsdfPrincipled")
    C.link(nt, br.outputs["Color"], p.inputs["Base Color"])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 0.8; mr.inputs["To Max"].default_value = rough
    C.link(nt, br.outputs["Fac"], mr.inputs["Value"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.05; nz.inputs["Detail"].default_value = 6
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    mx = n.new("ShaderNodeMath"); mx.operation = "MULTIPLY_ADD"; mx.inputs[2].default_value = -0.05
    mx.inputs[1].default_value = 0.15
    C.link(nt, nz.outputs["Fac"], mx.inputs[0])
    ad = n.new("ShaderNodeMath"); ad.operation = "ADD"
    C.link(nt, mr.outputs["Result"], ad.inputs[0]); C.link(nt, mx.outputs[0], ad.inputs[1])
    C.link(nt, ad.outputs[0], p.inputs["Roughness"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.3; b.inputs["Distance"].default_value = 0.1
    C.link(nt, br.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    p.inputs["Coat Weight"].default_value = 0.3
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def machine(rnd):
    body_m = C.principled("MachBody", (0.16, 0.3, 0.3), rough=0.35, coat=0.6, noise_rough=(0.25, 0.4))
    trim = C.principled("MachTrim", (0.75, 0.76, 0.77), metallic=1, rough=0.3)
    dark = C.principled("MachDark", (0.02, 0.022, 0.025), rough=0.4)
    glass = C.principled("MachGlass", (0.9, 0.95, 1.0), rough=0.02, alpha=0.07, coat=1.0)
    P.box("Body", (MW, MD, MH), (0, 0, MH / 2 + 5), mat=body_m, bevel=1.2)
    P.box("Plinth", (MW - 6, MD - 6, 5), (0, 0, 2.5), mat=dark)
    # 陳列窓の開口(ブーリアン)
    body = bpy.data.objects["Body"]
    ww = MW - 14
    cut = P.box("WinCut", (ww, 40, WIN[1] - WIN[0]), (0, FY + 12, sum(WIN) / 2))
    bo = body.modifiers.new("win", "BOOLEAN"); bo.object = cut; bo.solver = "EXACT"
    cut.hide_render = True; cut.hide_viewport = True
    # 内部: 奥の明るい背板、床、縦の仕切り
    P.box("Backlight", (ww, 2, WIN[1] - WIN[0]), (0, FY + 30, sum(WIN) / 2),
          mat=C.emissive("BackGlow", temp=5200, strength=0.9))
    P.box("InFloor", (ww, 34, 2), (0, FY + 17, WIN[0] + 1), mat=C.principled("InFloorM", (0.6, 0.6, 0.62), metallic=0.8, rough=0.35))
    P.box("InTop", (ww, 34, 2), (0, FY + 17, WIN[1] - 1), mat=dark)
    for s in (-1, 1):
        P.box(f"InSide{s}", (2, 34, WIN[1] - WIN[0]), (s * ww / 2, FY + 17, sum(WIN) / 2), mat=C.principled("InSideM", (0.85, 0.86, 0.87), rough=0.4))
    colw = ww / COLS
    divm = C.principled("Divider", (0.85, 0.88, 0.9), rough=0.1, alpha=0.35, coat=0.8)
    for i in range(1, COLS):
        x = -ww / 2 + i * colw
        P.box(f"Div{i}", (0.6, 24, WIN[1] - WIN[0] - 14), (x, FY + 20, sum(WIN) / 2 - 3), mat=divm)
    # 上部のLEDライン
    P.box("TopLED", (ww - 4, 2, 1), (0, FY + 6, WIN[1] - 3), mat=C.emissive("TopLEDM", temp=5000, strength=5))
    L = C.area_light((0, FY + 8, WIN[1] - 5), (0, 0, 0), 1, 2500, (1, 0.97, 0.92), "InnerLight").data
    L.shape = "RECTANGLE"; L.size = ww - 6; L.size_y = 6
    # 前面側の照明(ガラス内側の縁に仕込んだ LED 想定): 傘の手前側を照らす
    Lf = C.area_light((0, FY + 4, sum(WIN) / 2), (90, 0, 0), 1, 4000, (1, 0.97, 0.93), "InnerFront").data
    Lf.shape = "RECTANGLE"; Lf.size = ww - 6; Lf.size_y = WIN[1] - WIN[0] - 10
    # 傘(各列1本、石突きを下に立てる。たまに売り切れ)
    vin_tints = [None, None, None, (0.8, 0.9, 1.0), (0.95, 0.9, 0.8), None]
    cloth = ["navy", "black", "burgundy", "green", "beige", "charcoal"]
    for i in range(COLS):
        x = -ww / 2 + (i + 0.5) * colw
        if i == 5:
            continue                        # 売り切れの列
        if i % 3 != 1:
            kw = dict(kind="vinyl", color=rnd.choice(vin_tints), handle=rnd.choice(["white", "clear", "white"]))
        else:
            kw = dict(kind="cloth", color=rnd.choice(cloth), handle=rnd.choice(["black", "wood"]))
        K.make_umbrella(f"Sale{i}", (x + rnd.uniform(-1, 1), FY + 20, WIN[0] + 4), rotation_deg=(rnd.uniform(-2, 2), rnd.uniform(-2, 2), rnd.uniform(70, 110)),
                        state="closed", seed=700 + i, loose=rnd.uniform(0, 0.2), **kw)
    # ガラスと枠
    P.box("Glass", (ww, 0.5, WIN[1] - WIN[0]), (0, FY - 0.2, sum(WIN) / 2), mat=glass)
    for z in WIN:
        P.box(f"WinTrim{z}", (ww + 2, 2.5, 2.5), (0, FY - 0.6, z), mat=trim, bevel=0.4)
    for s in (-1, 1):
        P.box(f"WinTrimV{s}", (2.5, 2.5, WIN[1] - WIN[0] + 2), (s * (ww / 2 + 1), FY - 0.6, sum(WIN) / 2), mat=trim, bevel=0.4)
    # 列ごとの価格表示(無地の白い光)とボタン
    price = C.emissive("PriceGlow", (0.95, 0.95, 0.9), strength=2.2)
    btn = C.emissive("BtnGlow", (0.3, 0.75, 1.0), strength=4)
    btn_off = C.emissive("BtnOff", (1.0, 0.35, 0.2), strength=3)
    for i in range(COLS):
        x = -ww / 2 + (i + 0.5) * colw
        P.box(f"Price{i}", (8, 0.6, 2.2), (x, FY - 0.5, WIN[0] - 4), mat=price)
        P.box(f"Btn{i}", (5, 1.2, 2.6), (x, FY - 0.7, WIN[0] - 8.5), mat=btn_off if i == 5 else btn, bevel=0.4)
    # 上部の無地のヘッダー(柔らかく光る)
    P.box("Header", (MW - 10, 1.0, 9), (0, FY - 0.3, MH - 4), mat=C.emissive("HeaderGlow", (0.85, 0.9, 0.88), strength=1.4))
    # 下部: 操作パネル(読み取り部=黒いガラス、硬貨口)、取り出し口
    P.box("Panel", (30, 1.6, 42), (MW / 2 - 24, FY - 0.6, 32), mat=dark, bevel=0.6)
    P.box("Reader", (14, 1.0, 10), (MW / 2 - 24, FY - 1.6, 44), mat=C.principled("ReaderGlass", (0.01, 0.01, 0.012), rough=0.05, coat=1))
    P.box("ReaderLED", (8, 0.4, 0.6), (MW / 2 - 24, FY - 2.2, 50), mat=C.emissive("RLED", (0.2, 1.0, 0.5), strength=5))
    P.box("CoinPlate", (6, 1.4, 8), (MW / 2 - 24, FY - 1.8, 30), mat=trim, bevel=0.5)
    P.box("CoinSlit", (0.4, 0.4, 3.2), (MW / 2 - 24, FY - 2.6, 31), mat=C.principled("Black", (0, 0, 0), rough=1))
    P.box("Screen", (13, 0.8, 7), (MW / 2 - 24, FY - 1.5, 20), mat=C.emissive("ScreenGlow", (0.15, 0.22, 0.3), strength=1.5))
    # 取り出し口(横長のフラップ)
    P.box("OutletFrame", (70, 3, 26), (-12, FY - 0.8, 30), mat=dark, bevel=1.0)
    P.box("OutletFlap", (64, 1.2, 20), (-12, FY - 2.4, 30), (math.radians(-6), 0, 0), mat=C.principled("Flap", (0.08, 0.09, 0.1), rough=0.2, alpha=0.85, coat=0.6), bevel=0.5)


def build(sc):
    P.world_studio((0.005, 0.005, 0.006), (0.03, 0.03, 0.035), (0.09, 0.09, 0.1), 1.0, camera_color=(0.005, 0.005, 0.006))
    rnd = random.Random(7)
    # 駅構内(夜): タイルの床と壁、柱、天井
    floor_m = mat_tile("FloorTile", (0.42, 0.41, 0.39), (0.22, 0.22, 0.21), size=30, rough=0.18)
    P.plane("Floor", (2000, 1200), (0, -300, 0), mat=floor_m)
    wall_m = mat_tile("WallTile", (0.8, 0.8, 0.77), (0.58, 0.58, 0.56), size=12, rough=0.25, vertical=True)
    P.box("Wall", (2000, 10, 320), (0, WALL_Y + 5, 160), mat=wall_m)
    P.box("WallBase", (2000, 2, 12), (0, WALL_Y - 1, 6), mat=C.principled("Base", (0.12, 0.12, 0.12), rough=0.5))
    P.box("Ceiling", (2000, 1200, 10), (0, -300, 325), mat=C.principled("CeilM", (0.25, 0.25, 0.25), rough=0.7))
    colm = C.principled("ColM", (0.6, 0.6, 0.58), rough=0.5, coat=0.2)
    for x in (-260, 300):
        P.box(f"Pillar{x}", (50, 50, 320), (x, -60, 160), mat=colm, bevel=1.0)
    # 天井のダウンライト(やわらかく)
    for i, x in enumerate((-400, -120, 120, 400)):
        P.cyl(f"Down{i}", 9, 1, (x, -120, 319.5), mat=C.emissive("DownM", temp=3800, strength=25), verts=24)
        l = F.spot((x, -120, 318), (x, -120, 0), 6e5, color=(1.0, 0.86, 0.7), size_deg=80, blend=0.8, radius=8, name=f"DownL{i}")
    # 右奥: 暗い改札方向の光(ボケ)
    for i in range(6):
        P.box(f"FarGlow{i}", (40, 2, 8), (450 + i * 70, -700, 220), mat=C.emissive("FarGlowM", (0.9, 0.92, 1.0), strength=6))
    # 右隣: 無地の掲示枠(空・ガラス越しに白い板)と、左: ゴミ箱風の無地ボックス
    P.box("BoardFrame", (90, 4, 120), (MW / 2 + 90, WALL_Y - 2, 150), mat=C.principled("BoardF", (0.55, 0.56, 0.58), metallic=0.8, rough=0.3), bevel=0.5)
    P.box("BoardFace", (82, 1, 112), (MW / 2 + 90, WALL_Y - 4.2, 150), mat=C.principled("BoardFace", (0.72, 0.72, 0.7), rough=0.6))
    P.box("Bin", (45, 35, 85), (-MW / 2 - 55, WALL_Y - 22, 42.5), mat=C.principled("BinM", (0.62, 0.63, 0.65), metallic=0.9, rough=0.35, noise_rough=(0.25, 0.45)), bevel=2.0)
    P.box("BinTop", (47, 37, 3), (-MW / 2 - 55, WALL_Y - 22, 86), mat=C.principled("BinTopM", (0.08, 0.08, 0.09), rough=0.4), bevel=1.0)
    machine(rnd)
    fill = C.area_light((-60, -260, 180), (0, 0, 0), 150, 5e4, (1.0, 0.9, 0.8), "Fill")
    C.light_look_at(fill, (0, 0, 100))
    P.reflection_probe((0, -100, 120), radius=500)

    cam, tgt = C.camera((-90, -480, 130), (0, 0, 105), lens=35, fstop=0.028)
    P.key_seq(cam, "location", [(1, (-110, -520, 132)), (FRAMES, (-50, -330, 126))])
    P.key_seq(tgt, "location", [(1, (10, 0, 100)), (FRAMES, (0, 0, 112))])
    sc.view_settings.exposure = 0.6
    sc.view_settings.look = "AgX - Medium High Contrast"


if __name__ == "__main__":
    K.set_episode("ep02")
    C.run_shot("k07_resale_machine", build, FRAMES)
