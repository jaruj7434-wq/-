"""H08 / カット3-1: コンビニのレジ。カルトン(釣り銭トレー)におつりの硬貨が落ちて滑る。顔なし。5秒。

- 1〜18f: レシートが置かれたカルトン。蛍光灯の白い光、奥にボケた棚。
- 18〜34f: 画面上(店員の手の位置・画面外)から硬貨が次々に落ちてトレーに散る(1円玉2〜3枚含む)。
- 40f〜: 硬貨が落ち着き、カメラがゆっくり寄って1円玉に焦点が残る。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P

FRAMES = 120
TW, TD, TH = 18.0, 12.0, 1.4   # カルトン外寸


def mat_tray(name="Tray"):
    """樹脂のカルトン(底に細いリブ=縞のバンプ)。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    wv = n.new("ShaderNodeTexWave"); wv.bands_direction = "X"; wv.inputs["Scale"].default_value = 1.2
    wv.inputs["Distortion"].default_value = 0
    sep = n.new("ShaderNodeVectorMath"); sep.operation = "SCALE"; sep.inputs["Scale"].default_value = 1.0
    C.link(nt, tc.outputs["Object"], sep.inputs[0]); C.link(nt, sep.outputs[0], wv.inputs["Vector"])
    p = n.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (0.02, 0.12, 0.08, 1)
    p.inputs["Roughness"].default_value = 0.35
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.4; b.inputs["Distance"].default_value = 0.05
    C.link(nt, wv.outputs["Fac"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def mat_receipt(name="Receipt"):
    """感熱紙レシート。読めない灰色の行(文字の代わりに途切れた横線)。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 2.2, 1)
    C.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    sep = n.new("ShaderNodeSeparateXYZ"); C.link(nt, mp.outputs["Vector"], sep.inputs["Vector"])
    # 行: y方向の矩形波
    fr = n.new("ShaderNodeMath"); fr.operation = "FRACT"; C.link(nt, sep.outputs["Y"], fr.inputs[0])
    ln = n.new("ShaderNodeMath"); ln.operation = "LESS_THAN"; ln.inputs[1].default_value = 0.35
    C.link(nt, fr.outputs[0], ln.inputs[0])
    # 行内の途切れ(ランダムな長さ)
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3; nz.inputs["Detail"].default_value = 1
    cm = n.new("ShaderNodeCombineXYZ")
    fl = n.new("ShaderNodeMath"); fl.operation = "FLOOR"; C.link(nt, sep.outputs["Y"], fl.inputs[0])
    C.link(nt, sep.outputs["X"], cm.inputs["X"]); C.link(nt, fl.outputs[0], cm.inputs["Y"])
    C.link(nt, cm.outputs["Vector"], nz.inputs["Vector"])
    gt = n.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.47
    C.link(nt, nz.outputs["Fac"], gt.inputs[0])
    # 左右の余白
    ab = n.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; C.link(nt, sep.outputs["X"], ab.inputs[0])
    mg = n.new("ShaderNodeMath"); mg.operation = "LESS_THAN"; mg.inputs[1].default_value = 2.4
    C.link(nt, ab.outputs[0], mg.inputs[0])
    t1 = n.new("ShaderNodeMath"); t1.operation = "MULTIPLY"; C.link(nt, ln.outputs[0], t1.inputs[0]); C.link(nt, gt.outputs[0], t1.inputs[1])
    t2 = n.new("ShaderNodeMath"); t2.operation = "MULTIPLY"; C.link(nt, t1.outputs[0], t2.inputs[0]); C.link(nt, mg.outputs[0], t2.inputs[1])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"
    mx.inputs["A"].default_value = (0.92, 0.92, 0.9, 1); mx.inputs["B"].default_value = (0.25, 0.25, 0.27, 1)
    C.link(nt, t2.outputs[0], mx.inputs["Factor"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.45
    p.inputs["Subsurface Weight"].default_value = 0.1
    C.link(nt, mx.outputs["Result"], p.inputs["Base Color"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def build(sc):
    C.world((0.06, 0.065, 0.07))
    P.physics(sc, FRAMES, time_scale=0.6, substeps=40)
    rnd = random.Random(8)

    # カウンター天板(白い化粧板)と前垂れ
    top = P.box("Counter", (160, 60, 3), (0, 5, -1.5),
                mat=C.principled("Laminate", (0.75, 0.75, 0.73), rough=0.3, noise_rough=(0.2, 0.4), bump=0.02, bump_scale=2))
    C.rigid(top, False, "BOX", friction=0.5)

    # カルトン
    tray = P.open_box("Tray", (TW, TD, TH), (0, 0, TH / 2), wall=0.35, mat=mat_tray(), bevel=0.3)
    P.passive_mesh(tray, friction=0.35, bounce=0.15, margin=0.02)
    tfloor = P.box("TrayFloor", (TW - 0.8, TD - 0.8, 0.2), (0, 0, 0.1), mat=bpy.data.materials["Tray"])
    C.rigid(tfloor, False, "BOX", friction=0.35, bounce=0.15)

    # レシート(少し反って丸まる)
    rc = P.plane("Receipt", (5.8, 10.5), (-5.0, 0.0, 0.24), mat=mat_receipt())
    rc.rotation_euler = (0, 0, math.radians(-8))
    bpy.context.view_layer.objects.active = rc
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.subdivide(number_cuts=20); bpy.ops.object.mode_set(mode="OBJECT")
    P.add_mod(rc, "SIMPLE_DEFORM", deform_method="BEND", angle=math.radians(12), deform_axis="X")
    P.add_mod(rc, "SOLIDIFY", thickness=0.01)
    rc.location.z = 0.45
    # カウンター上の小物: ボケるホットスナックケースと募金箱(無地)
    glass = C.principled("Glass", (0.9, 0.95, 0.95), rough=0.05, transmission=1.0, ior=1.45)
    case = P.box("SnackCase", (40, 30, 35), (-48, 22, 17.5), mat=glass, bevel=0.5)
    P.box("SnackCaseBase", (40, 30, 3), (-48, 22, 1.5), mat=C.principled("Steel", (0.6, 0.6, 0.62), metallic=1, rough=0.3))
    C.point_light((-48, 22, 30), 4000, (1.0, 0.75, 0.45), 5, "Warmer")
    snack = C.principled("Snack", (0.65, 0.35, 0.1), rough=0.6, bump=0.3, bump_scale=2)
    for i in range(6):
        P.box(f"Snack{i}", (8, 5, 3), (-58 + (i % 3) * 10, 18 + (i // 3) * 8, 6 + (i // 3) * 12), mat=snack, bevel=1.5)
    P.box("Display", (14, 10, 18), (30, 20, 9), mat=C.principled("DisplayM", (0.85, 0.2, 0.15), rough=0.4), bevel=0.4)
    reg = P.box("Register", (34, 26, 12), (55, 18, 6), mat=C.principled("RegisterBody", (0.85, 0.86, 0.87), rough=0.4), bevel=1.0)
    P.box("RegisterScreen", (30, 2, 22), (55, 26, 22), (math.radians(-12), 0, 0),
          mat=C.principled("Scr", (0.02, 0.02, 0.03), rough=0.15, emission=(0.4, 0.6, 0.9), emission_strength=0.6), bevel=0.5)

    # 奥の棚(ボケる): 色とりどりの無地パッケージ
    cols = [(0.8, 0.1, 0.1), (0.95, 0.75, 0.1), (0.1, 0.35, 0.75), (0.9, 0.9, 0.9), (0.1, 0.55, 0.25),
            (0.9, 0.45, 0.1), (0.5, 0.2, 0.6), (0.15, 0.15, 0.15)]
    pmats = [C.principled(f"Pkg{i}", c, rough=0.35, coat=0.3) for i, c in enumerate(cols)]
    shelf_m = C.principled("Shelf", (0.85, 0.86, 0.88), rough=0.4)
    wall = P.box("BackWall", (400, 2, 250), (0, 200, 60), mat=C.principled("Wall", (0.8, 0.82, 0.83), rough=0.7))
    for row in range(7):
        z = -60 + row * 30
        P.box(f"Shelf{row}", (300, 40, 2), (0, 185, z), mat=shelf_m)
        x = -150
        while x < 150:
            w = rnd.uniform(5, 12); h = rnd.uniform(10, 26)
            P.box(f"Pkg{row}_{int(x)}", (w, rnd.uniform(6, 14), h), (x + w / 2, 182, z + 1 + h / 2),
                  mat=rnd.choice(pmats), bevel=0.3, segments=1)
            x += w + rnd.uniform(0.5, 2.5)
        # 棚の値札レール(無地の帯)
        P.box(f"Rail{row}", (300, 1, 3), (0, 166, z - 0.5), mat=C.principled("Rail", (0.95, 0.95, 0.9), rough=0.5))

    # 天井の蛍光灯(ライン照明) + 実際の照明
    tube = C.emissive("Tube", (0.9, 0.95, 1.0), strength=12)
    for i in range(4):
        P.box(f"Tube{i}", (220, 6, 1.5), (0, -40 + i * 60, 160), mat=tube)
        C.area_light((0, -40 + i * 60, 158), (0, 0, 0), 1, 150000, (0.88, 0.95, 1.0), f"Ceil{i}").data.shape = "RECTANGLE"
        L = bpy.data.objects[f"Ceil{i}"].data; L.size = 200; L.size_y = 10
    C.area_light((0, -60, 80), (55, 0, 0), 60, 60000, (0.92, 0.97, 1.0), "Front")
    P.light_card("Card", (60, 30), (0, -60, 90), (0, 0, 0), strength=2.0, color=(0.9, 0.95, 1.0))

    # 落ちてくるおつり(画面上・店員の手のあたりから)
    kinds = ["100", "10", "1", "10", "5", "1", "50", "1"]
    for i, k in enumerate(kinds):
        slot = i % 4
        loc = (3.0 + (slot - 1.5) * 2.4 + rnd.uniform(-0.3, 0.3), 1.0 + rnd.uniform(-0.8, 0.8),
               18 + (i % 2) * 3)
        rot = (rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), rnd.uniform(0, 6.28))
        c = P.make_any_coin(k, f"Change{i}", loc, rot)
        s = P.COINS[k]
        C.rigid(c, True, "CYLINDER", mass=s["r"] ** 2 * s["t"], friction=0.3, bounce=0.3)
        P.hold_then_release(c, 18 + i * 2, park=(300 + i * 5, 300, 0))

    cam, tgt = C.camera((0, -30, 12), (1.0, 1.0, 0.5), lens=35, fstop=0.04)  # 1BU=1cm のため実効F値は fstop*100 (=F4)
    P.key_seq(cam, "location", [(1, (-5, -32, 13)), (FRAMES, (1, -24, 10))])
    P.key_seq(tgt, "location", [(1, (0.5, 2.0, 0.5)), (FRAMES, (1.5, 0.5, 0.3))])


if __name__ == "__main__":
    C.run_shot("h08_register", build, FRAMES)
