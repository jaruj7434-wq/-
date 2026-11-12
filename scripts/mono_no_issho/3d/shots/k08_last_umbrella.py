"""K08 / カット6-1: 晴れた日。店先の傘立てに、一本だけ残ったビニール傘。
木漏れ日がやわらかく揺れ、カメラはゆっくり横へ流れる。締めの静かなカット。5秒。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P
import umbrella as U
import factory_parts as F
from k02_store_stand import umbrella_stand, place_umbrella, FRONT_Y

FRAMES = 120
STAND = (-400.0, 62.0)   # 日の当たる外壁の前(右にガラス戸)


def mat_pavers(name="Pavers", base=(0.42, 0.40, 0.37), tile=30.0):
    """乾いたコンクリート平板(目地+色ムラ+細かいざらつき)。"""
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    br = n.new("ShaderNodeTexBrick"); br.offset = 0.5
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.5
    br.inputs["Brick Width"].default_value = tile * 2; br.inputs["Row Height"].default_value = tile
    br.inputs["Color1"].default_value = (*base, 1)
    br.inputs["Color2"].default_value = (base[0] * 0.88, base[1] * 0.88, base[2] * 0.9, 1)
    br.inputs["Mortar"].default_value = (base[0] * 0.55, base[1] * 0.55, base[2] * 0.55, 1)
    C.link(nt, tc.outputs["Object"], br.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.02; nz.inputs["Detail"].default_value = 8
    C.link(nt, tc.outputs["Object"], nz.inputs["Vector"])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "OVERLAY"; mx.inputs["Factor"].default_value = 0.35
    C.link(nt, br.outputs["Color"], mx.inputs["A"]); C.link(nt, nz.outputs["Color"], mx.inputs["B"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.85
    C.link(nt, mx.outputs["Result"], p.inputs["Base Color"])
    fine = n.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 3.0
    C.link(nt, tc.outputs["Object"], fine.inputs["Vector"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.2
    add = n.new("ShaderNodeMath"); add.operation = "ADD"
    inv = n.new("ShaderNodeMath"); inv.operation = "MULTIPLY"; inv.inputs[1].default_value = 0.6
    C.link(nt, br.outputs["Fac"], inv.inputs[0])
    C.link(nt, fine.outputs["Fac"], add.inputs[0]); C.link(nt, inv.outputs[0], add.inputs[1])
    C.link(nt, add.outputs[0], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def leaf_gobo(rnd, x_range=(-1150, 50), y_range=(-820, -180), z=350.0, clusters=34, per=70):
    """画面外の「木の葉」(小さな楕円板の集まり)。影だけ落として木漏れ日を作る。
    太陽(仰角約38°、+X+Y方向へ)なので、z=350 の葉の影は (+224, +388) ずれて地面に落ちる。"""
    import bmesh
    bm = bmesh.new()
    for c in range(clusters):
        cx, cy = rnd.uniform(*x_range), rnd.uniform(*y_range)
        cr = rnd.uniform(40, 110)
        for k in range(per):
            r = cr * math.sqrt(rnd.random()); a = rnd.uniform(0, math.tau)
            px, py, pz = cx + r * math.cos(a), cy + r * math.sin(a), z + rnd.uniform(-30, 30)
            lw, ll, rot = rnd.uniform(3, 6), rnd.uniform(7, 13), rnd.uniform(0, math.pi)
            vs = []
            for t in range(8):
                u = math.tau * t / 8
                ex, ey = ll * math.cos(u), lw * math.sin(u)
                vs.append(bm.verts.new((px + ex * math.cos(rot) - ey * math.sin(rot),
                                        py + ex * math.sin(rot) + ey * math.cos(rot), pz)))
            bm.faces.new(vs)
    me = bpy.data.meshes.new("LeafGobo"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("LeafGobo", me); bpy.context.collection.objects.link(o)
    o.data.materials.append(C.principled("LeafGoboM", (0.05, 0.08, 0.03), rough=0.8))
    o.visible_camera = False
    for attr in ("visible_glossy", "visible_diffuse"):
        if hasattr(o, attr):
            setattr(o, attr, False)
    return o


def shrub(name, loc, r, rnd, mat):
    """植え込みの低木(ノイズで変形した葉の塊を数個)。"""
    for i in range(5):
        off = (rnd.uniform(-r, r) * 0.8, rnd.uniform(-r, r) * 0.4, rnd.uniform(0, r * 0.4))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=r * rnd.uniform(0.55, 0.8),
                                              location=(loc[0] + off[0], loc[1] + off[1], loc[2] + off[2]))
        o = bpy.context.object; o.name = f"{name}{i}"
        tx = bpy.data.textures.new(f"{name}Tx{i}", "CLOUDS"); tx.noise_scale = r * 0.25
        d = o.modifiers.new("d", "DISPLACE"); d.texture = tx; d.strength = r * 0.35
        bpy.ops.object.shade_smooth()
        o.data.materials.append(mat)


def mat_leaves(name="Leaves"):
    m, nt, out = C.node_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord")
    vz = n.new("ShaderNodeTexVoronoi"); vz.inputs["Scale"].default_value = 0.6
    C.link(nt, tc.outputs["Object"], vz.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (0.015, 0.04, 0.01, 1); cr.color_ramp.elements[1].color = (0.12, 0.22, 0.05, 1)
    C.link(nt, vz.outputs["Distance"], cr.inputs["Fac"])
    p = n.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = 0.5
    C.link(nt, cr.outputs["Color"], p.inputs["Base Color"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.8
    C.link(nt, vz.outputs["Distance"], b.inputs["Height"]); C.link(nt, b.outputs["Normal"], p.inputs["Normal"])
    if "Subsurface Weight" in p.inputs:
        p.inputs["Subsurface Weight"].default_value = 0.0
    C.link(nt, p.outputs["BSDF"], out.inputs["Surface"])
    return m


def build(sc):
    rnd = random.Random(8)
    P.world_studio((0.2, 0.18, 0.15), (0.7, 0.72, 0.74), (0.4, 0.55, 0.85), 0.35, camera_color=(0.6, 0.66, 0.74))
    P.plane("Ground", (3000, 2000), (0, -400, 0), mat=mat_pavers())

    # 店の正面: 明るい外壁+ガラス戸(中はやや暗い)
    wall = C.principled("SunWall", (0.66, 0.6, 0.5), rough=0.75, bump=0.08, bump_scale=0.4)
    alu = C.principled("Alu", (0.62, 0.63, 0.65), metallic=1, rough=0.3)
    P.box("WallL", (400, 20, 320), (-480, FRONT_Y + 10, 160), mat=wall)
    P.box("WallR", (400, 20, 320), (480, FRONT_Y + 10, 160), mat=wall)
    P.box("WallTop", (600, 20, 80), (0, FRONT_Y + 10, 280), mat=wall)
    glass = C.principled("Glass", (0.01, 0.012, 0.015), rough=0.02, alpha=0.6, coat=1.0)
    g = P.box("Glass", (560, 1, 240), (0, FRONT_Y, 120), mat=glass)
    for x in (-280, -140, 0, 140, 280):
        P.box(f"Mullion{x}", (6, 8, 240), (x, FRONT_Y, 120), mat=alu)
    for z in (1.5, 240):
        P.box(f"Transom{z}", (566, 8, 4), (0, FRONT_Y, z), mat=alu)
    P.plane("InFloor", (560, 400), (0, FRONT_Y + 200, 0.2), mat=C.principled("InFloorM", (0.35, 0.35, 0.34), rough=0.3))
    P.plane("InBack", (560, 260), (0, FRONT_Y + 300, 125), rot=(90, 0, 0), mat=C.principled("InBackM", (0.3, 0.3, 0.29), rough=0.6))
    P.box("InCeil", (560, 300, 4), (0, FRONT_Y + 150, 244), mat=C.principled("InCeilM", (0.2, 0.2, 0.2), rough=0.8))
    for k, x0 in enumerate((-160, 160)):
        P.box(f"InShelf{k}", (200, 40, 140), (x0, FRONT_Y + 200, 70), mat=C.principled(f"InShelfM{k}", (0.12, 0.12, 0.12), rough=0.5))
    # 庇(ガラス上部に影を落とす)
    P.box("Awning", (620, 70, 6), (0, FRONT_Y - 35, 262), mat=C.principled("AwningM", (0.75, 0.75, 0.74), metallic=0.4, rough=0.35))
    # 植え込み(右手前)
    planter = C.principled("Planter", (0.3, 0.29, 0.27), rough=0.8, bump=0.1, bump_scale=0.5)
    P.box("PlanterBox", (160, 50, 45), (STAND[0] - 190, FRONT_Y - 35, 22.5), mat=planter, bevel=1.0)
    P.box("Soil", (154, 44, 2), (STAND[0] - 190, FRONT_Y - 35, 44), mat=C.principled("SoilM", (0.06, 0.04, 0.03), rough=0.95))
    lm = mat_leaves()
    for i, x in enumerate((STAND[0] - 240, STAND[0] - 190, STAND[0] - 145)):
        shrub(f"Shrub{i}_", (x, FRONT_Y - 35, 60), 28, rnd, lm)

    # 傘立て(空)+一本だけ残ったビニール傘(右奥の隅のセルに、少し傾いて)
    cells, cell, h = umbrella_stand(*STAND)
    bpy.data.objects.remove(bpy.data.objects["TrayWater"])
    x, y = cells[-1]
    place_umbrella("LastUmb", (x - 4, y + 3, 2.5), (x + 4.5, y - 3, h), 140, kind="vinyl", loose=0.15, seed=3)

    # 日差し(午後、左手前上から)+木漏れ日
    bpy.ops.object.light_add(type="SUN")
    sun = bpy.context.object; sun.name = "Sun"
    sun.data.energy = 9.0; sun.data.angle = math.radians(1.5); sun.data.color = (1.0, 0.9, 0.76)
    sun.rotation_euler = (math.radians(52), 0, math.radians(-30))
    gobo = leaf_gobo(rnd)
    P.key_seq(gobo, "location", [(1, (0, 0, 0)), (FRAMES, (10, 4, 0))])
    F.set_interp(gobo, "LINEAR")
    # 空からの柔らかい補助光(影側を青く持ち上げる)
    C.area_light((100, -300, 400), (0, 0, 0), 600, 1e5, (0.8, 0.88, 1.0), "SkyFill")
    C.light_look_at(bpy.data.objects["SkyFill"], (STAND[0], STAND[1], 40))
    # 向かいの建物と街路樹(カメラの後ろ。ガラスに映り込む)
    opp = C.principled("OppFacade", (0.7, 0.66, 0.58), rough=0.7)
    P.plane("OppFacade", (2400, 900), (0, -700, 450), rot=(90, 0, 0), mat=opp)
    win = C.principled("OppWin", (0.05, 0.07, 0.09), rough=0.1)
    for i in range(-5, 6):
        for j in range(3):
            P.plane(f"OppWin{i}_{j}", (120, 90), (i * 200, -698, 140 + j * 220), rot=(90, 0, 0), mat=win)
    for i, x in enumerate((-420, 60, 520)):
        shrub(f"Tree{i}_", (x, -560, 420), 140, rnd, lm)
        P.cyl(f"Trunk{i}", 12, 420, (x, -560, 210), mat=C.principled("Bark", (0.12, 0.09, 0.07), rough=0.9), verts=12)
    for o in bpy.data.objects:     # 映り込み専用: 影は落とさない(木漏れ日は LeafGobo が担当)
        if o.name.startswith(("Opp", "Tree", "Trunk")):
            o.visible_shadow = False
    P.reflection_probe((0, 0, 100), radius=500, clip_start=1)

    # カメラ: 低めから、ゆっくり右へ流れる
    cam, tgt = C.camera((STAND[0] - 100, -330, 72), (STAND[0] + 30, STAND[1], 60), lens=45, fstop=0.035)
    P.key_seq(cam, "location", [(1, (STAND[0] - 100, -330, 72)), (FRAMES, (STAND[0] - 55, -318, 68))])
    P.key_seq(tgt, "location", [(1, (STAND[0] + 30, STAND[1], 62)), (FRAMES, (STAND[0] + 36, STAND[1], 60))])
    sc.view_settings.exposure = 0.1


if __name__ == "__main__":
    C.EPISODE = "ep02"
    C.run_shot("k08_last_umbrella", build, FRAMES)
