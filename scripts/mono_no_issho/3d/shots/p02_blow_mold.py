"""P02 / カット2-1: ブロー成形の断面図(カットモデル)。金型の奥半分だけを見せ、手前の切断面は
オレンジに塗った「断面」。温められた試験管形のプリフォームが、延伸ロッドで下へ伸び、
空気で一気にふくらんで金型いっぱいのボトルになる。5秒。

- 1〜22f: ほんのり赤く温まったプリフォームが金型の中にぶら下がる
- 22〜40f: 延伸ロッドが下りてプリフォームが細長く伸びる(シェイプキー Stretch)
- 40〜62f: 空気でふくらみ、金型の形に(シェイプキー Blow。Stretch 基準)。赤みが消える
- 62〜120f: 冷えて透明なボトルに。光が表面をなでる。カメラはゆっくり回り込む
透明素材はプリフォーム(=ボトル)1つだけ。
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import bmesh
import common as C
import props as P
import factory_parts as F
import pet_parts as PP
from k06_umbrella_explode import backdrop

FRAMES = 120
STRETCH = (22, 40)
BLOW = (40, 62)
MW, MD = 30.0, 13.0      # 金型(奥半分)の幅・奥行
MZ0 = -2.5               # 金型の下端


def mold_half(steel, section):
    """奥半分の金型(y>=0)。ボトル形の空洞を半分くり抜き、切断面(y=0)に断面色を割り当てる。"""
    blk = P.box("MoldBack", (MW, MD, PP.NECK_Z - MZ0), (0, MD / 2, (PP.NECK_Z + MZ0) / 2))
    cav = PP.lathe_mesh("Cavity", PP.profile("bottle"), "bottle")
    # 空洞用に口を閉じ、少しだけ太らせる
    bm = bmesh.new(); bm.from_mesh(cav.data)
    edges = [e for e in bm.edges if e.is_boundary]
    bmesh.ops.holes_fill(bm, edges=edges)
    for v in bm.verts:
        v.co.x *= 1.012; v.co.y *= 1.012
    bm.to_mesh(cav.data); bm.free()
    bo = blk.modifiers.new("cav", "BOOLEAN"); bo.object = cav; bo.solver = "EXACT"
    bpy.context.view_layer.objects.active = blk
    bpy.ops.object.modifier_apply(modifier="cav")
    bpy.data.objects.remove(cav)
    blk.data.materials.clear()   # ブーリアンが空のスロットを足すので作り直す
    blk.data.materials.append(steel); blk.data.materials.append(section)
    for p in blk.data.polygons:
        if p.normal.y < -0.99 and abs(p.center.y + blk.location.y) < 0.01:   # 面の中心はローカル座標
            p.material_index = 1
        p.use_smooth = not (abs(p.normal.x) > 0.99 or abs(p.normal.y) > 0.99 or abs(p.normal.z) > 0.99)
    P.add_mod(blk, "BEVEL", width=0.15, segments=2, limit_method="ANGLE")
    return blk


def build(sc):
    P.world_studio((0.01, 0.01, 0.012), (0.05, 0.05, 0.055), (0.35, 0.36, 0.38), 0.6, camera_color=(0.03, 0.03, 0.035))
    steel, _ = F.mat_steel("MoldSteel", (0.66, 0.67, 0.69), rough=0.16, streak_axis="Z")
    section = C.principled("Section", (0.8, 0.36, 0.08), rough=0.55, bump=0.02, bump_scale=3)
    mold = mold_half(steel, section)
    # 冷却水の穴(断面に見える丸)
    dark = C.principled("Bore", (0.02, 0.02, 0.02), rough=0.6)
    for x, z in ((-11.0, 3.0), (11.0, 3.0), (-11.0, 13.0), (11.0, 13.0)):
        P.cyl(f"Bore{x}_{z}", 0.8, 0.2, (x, -0.05, z), (math.radians(90), 0, 0), dark, verts=24)
    # 台座・口を支えるネックプレート・ブローノズル
    paint = F.mat_painted("MachinePaint", (0.12, 0.2, 0.28), rough=0.5, wear=0.2, scale=0.1)
    P.box("Base", (MW + 16, MD + 10, 4), (0, MD / 2 - 3, MZ0 - 2), mat=paint, bevel=0.4)
    P.box("NeckPlate", (MW, MD, 1.2), (0, MD / 2, PP.NECK_Z + 0.65), mat=steel, bevel=0.15)
    noz = P.cyl("Nozzle", 2.1, 4.0, (0, 0, PP.TOP_Z + 2.6), mat=steel, verts=40, bevel=0.15)
    P.box("NozzleArm", (6, MD + 2, 3), (0, MD / 2, PP.TOP_Z + 6), mat=paint, bevel=0.3)
    P.cyl("Hose", 0.6, 30, (0, MD / 2 + 4, PP.TOP_Z + 21), mat=C.principled("HoseM", (0.03, 0.03, 0.03), rough=0.6), verts=12)

    # ---- プリフォーム → ボトル(1つのメッシュ、シェイプキー)
    pf = PP.lathe_mesh("Preform", PP.profile("preform"), "preform")
    mat = PP.mat_pet("PreformPET", tint=(0.86, 0.94, 1.0), a_min=0.12, a_max=0.75, glow=0.0001)
    em = next(n for n in mat.node_tree.nodes if n.type == "EMISSION")
    em.inputs["Color"].default_value = (1.0, 0.36, 0.08, 1)
    F.key_socket(em.inputs["Strength"], 1, 0.9)
    F.key_socket(em.inputs["Strength"], STRETCH[0], 0.9)
    F.key_socket(em.inputs["Strength"], BLOW[1], 0.02)
    pf.data.materials.append(mat)
    st = PP.add_shape(pf, "Stretch", PP.lathe_coords(PP.profile("stretched"), "preform"))
    bl = PP.add_shape(pf, "Blow", PP.lathe_coords(PP.profile("bottle"), "bottle"), relative=st)
    PP.key_shape(st, [(1, 0.0), (STRETCH[0], 0.0), (STRETCH[1], 1.0)])
    # ふくらみは最初ゆっくり→一気に→最後にぴたっと(ease in-out)
    PP.key_shape(bl, [(1, 0.0), (BLOW[0], 0.0), (BLOW[1], 1.0)])

    # 延伸ロッド(プリフォームの中を下りる)
    rod = P.cyl("Rod", 0.42, 40, (0, 0, 0), mat=C.principled("RodSteel", (0.8, 0.8, 0.82), metallic=1, rough=0.2), verts=16)
    tip_hi = PP.NECK_Z - 9.5 + 0.9
    P.key_seq(rod, "location", [(1, (0, 0, tip_hi + 20)), (STRETCH[0], (0, 0, tip_hi + 20)), (STRETCH[1], (0, 0, 0.9 + 20)),
                                (BLOW[1] + 4, (0, 0, 0.9 + 20)), (BLOW[1] + 26, (0, 0, PP.TOP_Z + 25))])

    # ---- 照明: 大きなキー(左前上)・右後ろのリム・下からの弱い返し、映り込み用カード
    k = C.area_light((-70, -80, 70), (0, 0, 0), 60, 7e4, (1.0, 0.97, 0.92), "Key"); C.light_look_at(k, (0, 0, 9))
    r1 = C.area_light((60, 50, 40), (0, 0, 0), 40, 1.2e5, (0.8, 0.9, 1.0), "Rim"); C.light_look_at(r1, (0, 0, 9))
    r2 = C.area_light((-50, 40, 30), (0, 0, 0), 30, 6e4, (1.0, 0.9, 0.8), "RimL"); C.light_look_at(r2, (0, 0, 9))
    f = C.area_light((40, -90, 10), (0, 0, 0), 50, 3e4, (0.9, 0.95, 1.0), "Fill"); C.light_look_at(f, (0, 0, 9))
    # 光がボトルの表面をなでる(ハイライトの移動)
    sweep = P.light_card("Sweep", (14, 70), (-60, -40, 10), (0, 0, 10), strength=6.0)
    P.key_seq(sweep, "location", [(1, (-70, -30, 10)), (FRAMES, (40, -70, 10))])
    P.light_card("CardTop", (40, 80), (-20, -30, 70), (0, 0, 10), strength=1.5)
    P.light_card("CardR", (40, 60), (60, -50, 15), (0, 0, 10), strength=1.5)
    P.reflection_probe((0, -10, 10), radius=120, clip_start=0.2)

    # ---- カメラ: やや右前から、ゆっくり回り込む
    cam, tgt = C.camera((34, -72, 20), (0, 2, 9.5), lens=50, fstop=0.04)
    P.key_seq(cam, "location", [(1, (58, -60, 26)), (FRAMES, (36, -72, 20))])
    P.key_seq(tgt, "location", [(1, (0.5, 2, 10)), (FRAMES, (0, 2, 9.5))])
    cam.data.dof.focus_object = None; cam.data.dof.focus_distance = 78
    backdrop(cam, dist=300, top=(0.07, 0.08, 0.1), bottom=(0.012, 0.014, 0.018), glow=(0.12, 0.13, 0.16), glow_center=(0.5, 0.55))
    sc.view_settings.exposure = 0.0


if __name__ == "__main__":
    C.EPISODE = "ep03"
    C.run_shot("p02_blow_mold", build, FRAMES)
