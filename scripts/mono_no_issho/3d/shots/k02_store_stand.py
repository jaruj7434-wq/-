"""K02 / カット2-2: 雨の夜、コンビニ風の店先(看板・ロゴなし)。入口脇の金属の傘立てに
ビニール傘がぎっしり。軒の外は雨、濡れたタイルに店内の明かりが映る。カメラはゆっくり寄る。5秒。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from mathutils import Quaternion, Vector
import common as C
import props as P
import umbrella as U
from h15_rain_umbrella import rain

FRAMES = 120
FRONT_Y = 100.0        # 店のガラス面
EAVE_Y = -70.0         # 軒先(これより手前に雨)
STAND = (-35.0, 62.0)  # 傘立ての中心(x, y)


def mat_wet_tiles(name="WetTiles", base=(0.11, 0.11, 0.115), tile=30.0):
    """濡れた床タイル: 目地+水たまり(粗さ・色ムラ)。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    br = n.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 1.0 / tile
    br.inputs["Mortar Size"].default_value = 0.6
    br.inputs["Brick Width"].default_value = tile; br.inputs["Row Height"].default_value = tile
    br.offset = 0.0
    br.inputs["Color1"].default_value = (*base, 1)
    br.inputs["Color2"].default_value = (base[0] * 0.8, base[1] * 0.8, base[2] * 0.82, 1)
    br.inputs["Mortar"].default_value = (0.05, 0.05, 0.05, 1)
    br.inputs["Scale"].default_value = 1.0
    C.link(nt, tc.outputs["Object"], br.inputs["Vector"])
    pud = n.new("ShaderNodeTexNoise"); pud.inputs["Scale"].default_value = 0.012; pud.inputs["Detail"].default_value = 5
    C.link(nt, tc.outputs["Object"], pud.inputs["Vector"])
    pm = n.new("ShaderNodeMapRange"); pm.inputs["From Min"].default_value = 0.42; pm.inputs["From Max"].default_value = 0.55
    C.link(nt, pud.outputs["Fac"], pm.inputs["Value"])
    p = n.new("ShaderNodeBsdfPrincipled")
    dark = n.new("ShaderNodeMix"); dark.data_type = "RGBA"; dark.blend_type = "MULTIPLY"
    C.link(nt, pm.outputs["Result"], dark.inputs["Factor"])
    C.link(nt, br.outputs["Color"], dark.inputs["A"]); dark.inputs["B"].default_value = (0.5, 0.5, 0.52, 1)
    C.link(nt, dark.outputs["Result"], p.inputs["Base Color"])
    rr = n.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.32; rr.inputs["To Max"].default_value = 0.03
    C.link(nt, pm.outputs["Result"], rr.inputs["Value"])
    # 目地は粗いまま
    mo = n.new("ShaderNodeMath"); mo.operation = "MAXIMUM"
    gm = n.new("ShaderNodeMath"); gm.operation = "MULTIPLY"; gm.inputs[1].default_value = 0.0
    C.link(nt, rr.outputs["Result"], mo.inputs[0]); C.link(nt, gm.outputs[0], mo.inputs[1])
    C.link(nt, br.outputs["Fac"], gm.inputs[0])
    C.link(nt, mo.outputs[0], p.inputs["Roughness"])
    bmp = n.new("ShaderNodeBump"); bmp.inputs["Strength"].default_value = 0.25; bmp.invert = True
    C.link(nt, br.outputs["Fac"], bmp.inputs["Height"]); C.link(nt, bmp.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def umbrella_stand(cx, cy, cols=6, rows=2, cell=14.0, h=55.0):
    """よくある金属の傘立て(上段の格子+下の受け皿)。戻り値: 格子セル中心のリスト。"""
    steel = C.principled("StandSteel", (0.55, 0.56, 0.58), metallic=1, rough=0.28, noise_rough=(0.15, 0.45), bump_scale=0.5)
    tray = C.principled("StandTray", (0.32, 0.33, 0.35), metallic=0.9, rough=0.35)
    W, D = cols * cell, rows * cell
    P.open_box("StandTray", (W + 4, D + 4, 6), (cx, cy, 3), wall=0.6, mat=tray, bevel=0.3)
    # 受け皿の水
    P.box("TrayWater", (W + 2.6, D + 2.6, 0.2), (cx, cy, 2.0), mat=C.principled("TrayWaterM", (0.05, 0.06, 0.07), rough=0.02))
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box(f"StandPost{sx}{sy}", (2.2, 2.2, h), (cx + sx * W / 2, cy + sy * D / 2, h / 2), mat=steel, bevel=0.3)
    for z, t in ((h, 1.6), (h * 0.45, 1.2)):
        for sy in (-1, 1):
            P.box(f"RailX{z}{sy}", (W + 2.2, t, t), (cx, cy + sy * D / 2, z), mat=steel, bevel=0.2)
        for sx in (-1, 1):
            P.box(f"RailY{z}{sx}", (t, D + 2.2, t), (cx + sx * W / 2, cy, z), mat=steel, bevel=0.2)
    for i in range(1, cols):
        P.box(f"GridY{i}", (1.0, D, 1.0), (cx - W / 2 + i * cell, cy, h), mat=steel, bevel=0.15)
    for j in range(1, rows):
        P.box(f"GridX{j}", (W, 1.0, 1.0), (cx, cy - D / 2 + j * cell, h), mat=steel, bevel=0.15)
    return [(cx - W / 2 + (i + 0.5) * cell, cy - D / 2 + (j + 0.5) * cell) for i in range(cols) for j in range(rows)], cell, h


def place_umbrella(name, tip, through, yaw_deg, **kw):
    """石突き tip から格子の点 through を通る向きに傘を立てる。"""
    root = U.make(name, tip, **kw)
    d = (Vector(through) - Vector(tip)).normalized()
    q = d.to_track_quat("Z", "Y") @ Quaternion((0, 0, 1), math.radians(yaw_deg))
    root.rotation_mode = "QUATERNION"; root.rotation_quaternion = q
    return root


def storefront(rnd):
    alu = C.principled("Alu", (0.62, 0.63, 0.65), metallic=1, rough=0.3)
    wall = C.principled("FrontWall", (0.16, 0.16, 0.17), rough=0.55, noise_rough=(0.4, 0.7), bump=0.05, bump_scale=0.3)
    # 壁(窓の左右と上)
    P.box("WallL", (300, 20, 320), (-600, FRONT_Y + 10, 160), mat=wall)
    P.box("WallR", (300, 20, 320), (600, FRONT_Y + 10, 160), mat=wall)
    P.box("WallTop", (900, 20, 70), (0, FRONT_Y + 10, 275), mat=wall)
    # ガラス面(窓+自動ドア)とサッシ
    glass = C.principled("Glass", (0.02, 0.025, 0.03), rough=0.02, alpha=0.12, coat=0.0)
    g = P.box("Glass", (900, 1, 240), (0, FRONT_Y, 120), mat=glass)
    g.visible_shadow = False
    for x in (-450, -300, -150, 0, 150, 300, 450):
        P.box(f"Mullion{x}", (6, 8, 240), (x, FRONT_Y, 120), mat=alu)
    for z in (1.5, 240):
        P.box(f"Transom{z}", (906, 8, 4), (0, FRONT_Y, z), mat=alu)
    P.box("Sill", (906, 25, 3), (0, FRONT_Y + 6, 1.5), mat=alu)
    # 店内: 明るい天井・白い床・商品棚(色のブロック、文字なし)
    P.plane("InFloor", (900, 440), (0, FRONT_Y + 220, 0.2), mat=C.principled("InFloorM", (0.7, 0.7, 0.68), rough=0.15))
    P.plane("InCeil", (900, 440), (0, FRONT_Y + 220, 250), rot=(180, 0, 0), mat=C.principled("InCeilM", (0.85, 0.85, 0.85), rough=0.7))
    P.plane("InBack", (900, 260), (0, FRONT_Y + 420, 125), rot=(90, 0, 0), mat=C.principled("InBackM", (0.8, 0.8, 0.78), rough=0.6))
    shelf = C.principled("Shelf", (0.85, 0.85, 0.84), rough=0.4)
    cols = [(0.55, 0.18, 0.14), (0.75, 0.62, 0.3), (0.2, 0.32, 0.55), (0.85, 0.85, 0.82), (0.25, 0.45, 0.3), (0.7, 0.45, 0.22),
            (0.9, 0.9, 0.88), (0.5, 0.5, 0.52), (0.95, 0.93, 0.85)]
    pm = [C.principled(f"Pkg{i}", c, rough=0.35, coat=0.3) for i, c in enumerate(cols)]
    for k, (x0, y0, length) in enumerate(((-300, FRONT_Y + 200, 220), (40, FRONT_Y + 200, 260), (330, FRONT_Y + 200, 200), (0, FRONT_Y + 340, 800))):
        P.box(f"ShelfBody{k}", (length, 40, 150), (x0, y0, 75), mat=shelf)
        for lvl in range(4):
            z = 22 + lvl * 34
            x = x0 - length / 2 + 4
            while x < x0 + length / 2 - 8:
                w = rnd.uniform(4, 9)
                hh = rnd.uniform(8, 20)
                P.box(f"Pk{k}_{lvl}_{int(x)}", (w, 8, hh), (x + w / 2, y0 - 22, z + hh / 2 - 4), mat=rnd.choice(pm))
                x += w + 0.6
            P.box(f"PriceRail{k}_{lvl}", (length, 1, 3), (x0, y0 - 26, z - 5), mat=shelf)
    for i, x in enumerate((-300, -100, 100, 300)):
        L = C.area_light((x, FRONT_Y + 230, 245), (0, 0, 0), 1, 4.5e5, (1.0, 0.98, 0.95), f"InLight{i}").data
        L.shape = "RECTANGLE"; L.size = 150; L.size_y = 300
    for i, x in enumerate(range(-400, 420, 80)):
        P.box(f"InTube{i}", (14, 300, 1), (x, FRONT_Y + 200, 249), mat=C.emissive("InTubeM", temp=5600, strength=5))
    # 店内の光が外へ漏れる(ガラス越しの面光源)
    L = C.area_light((0, FRONT_Y + 30, 140), (90, 0, 0), 1, 8e5, (1.0, 0.97, 0.92), "ShopGlow").data
    L.shape = "RECTANGLE"; L.size = 500; L.size_y = 220
    bpy.data.objects["ShopGlow"].rotation_euler = (math.radians(-90), 0, 0)
    # 軒(ひさし)とダウンライト
    P.box("Eave", (900, FRONT_Y - EAVE_Y, 12), (0, (FRONT_Y + EAVE_Y) / 2, 316), mat=C.principled("EaveM", (0.2, 0.2, 0.21), rough=0.6))
    P.box("EaveFascia", (900, 4, 30), (0, EAVE_Y, 300), mat=C.principled("Fascia", (0.75, 0.76, 0.78), metallic=0.3, rough=0.4))
    dl = C.emissive("DownLight", temp=4200, strength=30)
    for x in (-220, 0, 220):
        bpy.ops.mesh.primitive_cylinder_add(radius=7, depth=1, location=(x, 10, 309.5))
        bpy.context.object.data.materials.append(dl)
        sp = bpy.data.lights.new(f"DL{x}", "SPOT"); sp.energy = 1.1e5; sp.spot_size = math.radians(100); sp.spot_blend = 0.8
        sp.shadow_soft_size = 4; sp.color = (1.0, 0.9, 0.78)
        o = bpy.data.objects.new(f"DL{x}", sp); bpy.context.collection.objects.link(o); o.location = (x, 10, 308)
    # 外の歩道と車道の縁石
    P.box("Curb", (2000, 20, 14), (0, -420, 5), mat=C.principled("CurbM", (0.3, 0.3, 0.29), rough=0.6))


def build(sc):
    rnd = random.Random(2)
    P.world_studio((0.004, 0.005, 0.007), (0.02, 0.025, 0.035), (0.03, 0.035, 0.05), 1.0, camera_color=(0.003, 0.004, 0.006))
    sc.use_gravity = True; sc.gravity = (0, 0, -981.0)
    P.plane("Ground", (3000, 2000), (0, -400, 0), mat=mat_wet_tiles())
    storefront(rnd)

    # 傘立て+ビニール傘(約26本)
    cells, cell, h = umbrella_stand(*STAND)
    n = 0
    tints = [None] * 10 + [(0.82, 0.9, 0.97), (0.95, 0.88, 0.9)]
    for ci, (x, y) in enumerate(cells):
        k = 2 + (rnd.random() < 0.25)
        for j in range(k):
            through = (x + rnd.uniform(-cell * 0.3, cell * 0.3), y + rnd.uniform(-cell * 0.3, cell * 0.3), h)
            tip = (x + rnd.uniform(-cell * 0.45, cell * 0.45) + rnd.uniform(-4, 4), y + rnd.uniform(-cell * 0.45, cell * 0.45), 2.5)
            r = rnd.random()
            if r < 0.09:
                kw = dict(kind="cloth", color=rnd.choice(["navy", "black", "charcoal", "olive"]))
            else:
                kw = dict(kind="vinyl", color=rnd.choice(tints),
                          handle=rnd.choices(["white", "black", "clear"], [7, 2, 2])[0], loose=rnd.choice([0, 0, 0.2, 0.5, 0.9]))
            place_umbrella(f"U{n}", tip, through, rnd.uniform(0, 360), seed=n, **kw)
            n += 1
    print("umbrellas:", n)
    # 傘立ての外に立てかけた1本(手前、ガラスへ)
    place_umbrella("ULean", (STAND[0] + 70, FRONT_Y - 14, 0.5), (STAND[0] + 76, FRONT_Y - 3, 60), 170, kind="vinyl")

    # 雨(軒の外)と軒先からの雨だれ
    rain(sc, (-500, 500), (EAVE_Y - 140, EAVE_Y - 6), top=330, count=55000)
    d = rain(sc, (-500, 500), (EAVE_Y - 4, EAVE_Y - 1), top=298, count=3000); d.name = "Drips"
    for o in bpy.data.objects:
        if o.name.startswith("Streak"):
            o.scale = (0.8, 0.8, 0.6)
    rm = bpy.data.materials["RainM"].node_tree.nodes["Principled BSDF"]
    rm.inputs["Alpha"].default_value = 0.3; rm.inputs["Emission Strength"].default_value = 0.8
    # 街の青い環境光(手前左から)
    C.area_light((-150, -380, 160), (0, 0, 0), 250, 1.4e6, (0.6, 0.72, 1.0), "Street")
    C.light_look_at(bpy.data.objects["Street"], (STAND[0], STAND[1], 40))
    P.reflection_probe((0, 0, 100), radius=600, clip_start=1)

    cam, tgt = C.camera((95, -300, 70), (STAND[0], STAND[1], 55), lens=55, fstop=0.02)
    P.key_seq(cam, "location", [(1, (125, -380, 74)), (FRAMES, (70, -250, 68))])
    P.key_seq(tgt, "location", [(1, (STAND[0] + 5, STAND[1], 58)), (FRAMES, (STAND[0], STAND[1], 60))])
    sc.view_settings.exposure = 0.0
    bpy.ops.ptcache.bake_all(bake=True)


if __name__ == "__main__":
    C.EPISODE = "ep02"
    C.run_shot("k02_store_stand", build, FRAMES)
