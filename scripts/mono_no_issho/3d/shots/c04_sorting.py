"""C04 / カット5-1: 古着の選別工場。コンベアの上を服が流れ、押し出しの板で、色ちがいのかごに仕分けられる。5秒。

- ベルトは +X へ 45cm/s。手前に4つのかご(青・緑・黄・橙)、各かごの向かい側に押し出し板(エアシリンダ)
- 服(平たいTシャツ・丸めた服)が、自分のかごの前に来ると板に押され、手前のシュートを滑ってかごに落ちる
- 人は出さない。文字・ロゴなし。透明素材なし
服の動きは解析的に毎フレームキー(物理ベイクなし)。メッシュは数種類を共有し、色はオブジェクト側のマテリアル。
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from mathutils import Vector
import common as C
import props as P
import factory_parts as F
import pet_parts as PP
import fuku_parts as FK

FRAMES = 120
SPEED = 45.0 / C.FPS          # cm/フレーム
BELT_Z = 85.0
BELT_W = 70.0
BINS = [(-190.0, (0.12, 0.35, 0.7)), (-70.0, (0.15, 0.55, 0.3)), (50.0, (0.9, 0.7, 0.12)), (170.0, (0.9, 0.42, 0.12))]
BIN_Y = -88.0
BIN_SIZE = (78.0, 62.0, 58.0)
G = 981.0 / C.FPS ** 2        # cm/フレーム^2


def mat_crate(name, color):
    m = F.mat_painted(name, color, rough=0.45, wear=0.08, scale=0.05)
    return m


def flat_items(rnd):
    """ベルトに載る平たい服のメッシュ(Tシャツ2種・シャツ1種)。XY に寝かせて原点=中心。"""
    meshes = []
    for k, kind in enumerate(("tee", "tee", "knit")):
        g, _ = FK.garment(f"ItemSrc{k}", kind, None, seed=40 + k, collar=False, buttons=False,
                          sleeve_deg=(35 if kind == "tee" else 60))
        me = g.data
        # 吊り(XZ)→ 平置き(XY)。厚みを少しつぶす
        for v in me.vertices:
            x, y, z = v.co
            v.co = Vector((x, z + 34.0 if kind == "tee" else z + 32.0, -y * 0.6))
        me.update()
        bpy.data.objects.remove(g, do_unlink=True)
        meshes.append(me)
    return meshes


def item_obj(name, me, mat, scale):
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if len(me.materials) == 0:
        me.materials.append(mat)
    o.material_slots[0].link = "OBJECT"; o.material_slots[0].material = mat
    o.scale = (scale, scale, scale)
    return o


def build(sc):
    rnd = random.Random(11)
    F.world_gradient(top=(0.55, 0.53, 0.5), horizon=(0.14, 0.13, 0.12), bottom=(0.04, 0.04, 0.04), strength=0.8,
                     camera_color=(0.05, 0.05, 0.055), strips=6.0)
    F.factory_hall(size=(3000, 2000, 700), center=(0, 500, 0), floor_mat=F.mat_concrete("FloorC", (0.3, 0.3, 0.28), rough=0.6),
                   wall_color=(0.55, 0.56, 0.54), lamp_rows=[(100, 7), (500, 7), (900, 7)], lamp_strength=30.0, lamp_temp=4800)
    # 通路の線
    P.box("FloorLine", (1400, 8, 0.2), (0, -150, 0.1), mat=C.principled("LineM", (0.85, 0.65, 0.08), rough=0.6))

    # ---- コンベア(手前の側板は外し、低い縁とシュートを付ける)
    flow = bpy.data.objects.new("BeltFlow", None); bpy.context.collection.objects.link(flow)
    P.key_seq(flow, "location", [(1, (0, 0, 0)), (FRAMES, (-SPEED * (FRAMES - 1), 0, 0))], interp="LINEAR")
    PP.conveyor("Conv", 1300, BELT_W, BELT_Z, (-150, 0, 0), belt_mat=PP.mat_belt("BeltM", flow),
                frame_mat=F.mat_painted("ConvFrame", (0.2, 0.42, 0.38), rough=0.45, wear=0.2, scale=0.05))
    bpy.data.objects.remove(bpy.data.objects["Conv_Side-1"], do_unlink=True)
    steel = F.mat_steel("ChuteSteel", (0.72, 0.72, 0.74), rough=0.25)[0]
    P.box("Lip", (1300, 3, 4), (-150, -BELT_W / 2 - 1.5, BELT_Z - 2), mat=steel)
    for x, col in BINS:
        # シュート(ベルトの縁からかごの縁へ斜めに下りる板)
        y_a, z_a = -BELT_W / 2 - 1, BELT_Z - 2.5
        y_b, z_b = BIN_Y + BIN_SIZE[1] / 2 - 6, 10 + BIN_SIZE[2] + 1
        ang = math.atan2(z_a - z_b, y_a - y_b)
        ln = math.hypot(y_a - y_b, z_a - z_b)
        cy, cz = (y_a + y_b) / 2, (z_a + z_b) / 2
        P.box(f"Chute{x}", (56, ln, 1.2), (x, cy, cz), (ang, 0, 0), mat=steel, bevel=0.3)
        for s_ in (-1, 1):
            P.box(f"ChuteSide{x}{s_}", (1.2, ln, 7), (x + s_ * 28, cy, cz + 3), (ang, 0, 0), mat=steel)
    # ---- かご(キャスター付きの樹脂かご)と中の服
    item_mats = [FK.mat_cloth(f"ItemM{i}", c, c2, pt, scale=0.6, sheen=0.12, vary=0.2) for i, (c, c2, pt) in enumerate([
        ((0.85, 0.15, 0.15), None, None), ((0.95, 0.95, 0.92), None, None), ((0.1, 0.2, 0.5), None, None),
        ((0.95, 0.75, 0.15), None, None), ((0.3, 0.6, 0.35), None, None), ((0.9, 0.9, 0.88), (0.2, 0.35, 0.7), "stripe"),
        ((0.1, 0.45, 0.5), None, None), ((0.9, 0.35, 0.5), None, None), ((0.35, 0.55, 0.85), None, None),
        ((0.92, 0.9, 0.84), (0.75, 0.2, 0.2), "check"), ((0.25, 0.25, 0.27), None, None), ((0.72, 0.58, 0.4), None, None)])]
    wheel = C.principled("CasterM", (0.05, 0.05, 0.05), rough=0.5)
    pile_top = {}
    k = 0
    for bi, (x, col) in enumerate(BINS):
        bm_ = mat_crate(f"Crate{bi}", col)
        bx, by, bz = BIN_SIZE
        P.open_box(f"Bin{bi}", (bx, by, bz), (x, BIN_Y, 10 + bz / 2), wall=1.6, mat=bm_, bevel=0.6)
        for sx in (-1, 1):
            for sy in (-1, 1):
                P.cyl(f"Caster{bi}{sx}{sy}", 4.5, 3.5, (x + sx * (bx / 2 - 8), BIN_Y + sy * (by / 2 - 8), 4.5),
                      (0, math.radians(90), 0), mat=wheel, verts=16)
        # かごの中の山(丸めた服を数段)
        top = 10 + bz * 0.78
        for j in range(26):
            px = x + rnd.uniform(-bx / 2 + 12, bx / 2 - 12)
            py = BIN_Y + rnd.uniform(-by / 2 + 11, by / 2 - 11)
            pz = 10 + 8 + (j / 26) * (top - 18) + rnd.uniform(-2, 2)
            w = FK.cloth_wad(f"BinWad{k}", (rnd.uniform(11, 14), rnd.uniform(9, 11), rnd.uniform(4, 5.5)), rnd,
                             item_mats[rnd.randrange(len(item_mats))], subdiv=2)
            w.location = (px, py, pz); w.rotation_euler = (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), rnd.uniform(0, math.tau))
            k += 1
        pile_top[bi] = top + 5.0

    # ---- 押し出し板(向こう側のエアシリンダ)
    pm = F.mat_painted("PusherM", (0.85, 0.85, 0.82), rough=0.4, wear=0.1)
    pushers = {}
    for bi, (x, col) in enumerate(BINS):
        P.box(f"PushHouse{bi}", (16, 20, 14), (x, BELT_W / 2 + 18, BELT_Z + 8), mat=pm, bevel=0.6)
        rod_root = bpy.data.objects.new(f"Pusher{bi}", None); bpy.context.collection.objects.link(rod_root)
        rod_root.location = (x, 0, 0)
        plate = P.box(f"PushPlate{bi}", (40, 2.5, 12), (0, BELT_W / 2 + 6, BELT_Z + 8), mat=mat_crate(f"PlateM{bi}", col), bevel=0.4)
        rod = P.cyl(f"PushRod{bi}", 1.4, 22, (0, BELT_W / 2 + 18, BELT_Z + 8), (math.radians(90), 0, 0), mat=steel, verts=16)
        plate.parent = rod_root; rod.parent = rod_root
        pushers[bi] = rod_root

    # ---- 流れる服: 55cm おきに並べ、届くかごを順に割り当てる(同じかごの押し出しは 18 フレーム以上あける)
    meshes = flat_items(rnd)
    push_frames = {i: [] for i in range(len(BINS))}
    use = [0] * len(BINS)
    items = []
    for i in range(20):
        x_start = 235.0 - 55.0 * i + rnd.uniform(-6, 6)
        cands = []
        for b_, (bx_, _) in enumerate(BINS):
            fp_ = 1 + (bx_ - x_start) / SPEED
            if 10 <= fp_ <= 104 and all(abs(fp_ - q) >= 18 for q in push_frames[b_]):
                cands.append((use[b_], fp_, b_))
        bi = fp = None
        if cands and i % 5 != 3:
            _, fp, bi = min(cands)
            fp = int(round(fp)); push_frames[bi].append(fp); use[bi] += 1
        mat = item_mats[(i * 5 + 2) % len(item_mats)]
        if i % 3 == 2:
            o = FK.cloth_wad(f"ItemWad{i}", (15, 11, 4.0), rnd, mat, subdiv=2)
            thick = 6.0
        else:
            o = item_obj(f"Item{i}", meshes[i % len(meshes)], mat, 0.72)
            thick = 2.0
        rz0 = math.radians(rnd.uniform(-20, 20)) + (math.pi / 2 if i % 2 else 0)
        y0 = rnd.uniform(-6, 6)
        z_belt = BELT_Z + thick / 2
        if bi is not None:
            n_in = len(push_frames[bi])
            land = Vector((BINS[bi][0] + rnd.uniform(-14, 14), BIN_Y + rnd.uniform(-6, 10), pile_top[bi] + 2.5 * n_in))
            rx_land = math.radians(rnd.uniform(-12, 12)); ry_land = math.radians(rnd.uniform(-10, 10))
            rz_land = rz0 + rnd.uniform(-0.6, 0.6)
        T = 10
        for f in range(1, FRAMES + 1):
            if bi is None or f <= fp:
                loc = (x_start + SPEED * (f - 1), y0, z_belt); rot = (0, 0, rz0)
            elif f <= fp + 4:                      # 板に押されて縁へ
                u = (f - fp) / 4.0
                loc = (BINS[bi][0] + SPEED * (f - fp) * 0.5, y0 + (-BELT_W / 2 - 3 - y0) * u, z_belt)
                rot = (math.radians(-6 * u), 0, rz0)
            else:                                  # シュートを滑ってかごへ落ちる
                t = f - fp - 4
                u = min(1.0, t / T)
                p0 = Vector((BINS[bi][0] + SPEED * 2, -BELT_W / 2 - 3, z_belt))
                y = p0.y + (land.y - p0.y) * (1 - (1 - u) ** 1.6)
                z = p0.z + (land.z - p0.z) * u ** 1.5
                x = p0.x + (land.x - p0.x) * u
                if t > T:                          # 着地後の小さな弾み
                    z = land.z + 1.5 * math.exp(-(t - T) / 2.0) * abs(math.sin((t - T) * 1.2))
                loc = (x, y, z)
                tilt = math.sin(math.pi * u) * math.radians(-38)
                rot = (tilt + rx_land * u, ry_land * u, rz0 + (rz_land - rz0) * u)
            o.location = loc; o.rotation_euler = rot
            o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_euler", frame=f)
        F.set_interp(o, "LINEAR")
        items.append(o)
    for bi, frames in push_frames.items():
        r = pushers[bi]
        r.location.y = 0; r.keyframe_insert("location", index=1, frame=1)
        for fp in frames:
            for df, yy in ((-3, 0), (0, 0), (4, -BELT_W + 8), (7, -BELT_W + 8), (14, 0)):
                if 1 <= fp + df <= FRAMES:
                    r.location.y = yy; r.keyframe_insert("location", index=1, frame=fp + df)
        F.set_interp(r, "LINEAR")

    # ---- 奥: フレコンバッグ(大きな布袋)に入った服の山
    canvas = F.mat_canvas("BulkBag", (0.82, 0.8, 0.74), weave=3.0)
    for j, x in enumerate((-260, -150, -40, 70, 180)):
        P.open_box(f"Bulk{j}", (90, 90, 95), (x, 230, 47.5), wall=1.0, mat=canvas, bevel=1.0)
        for q in range(7):
            w = FK.cloth_wad(f"BulkWad{j}_{q}", (rnd.uniform(16, 22), rnd.uniform(14, 18), rnd.uniform(6, 9)), rnd,
                             item_mats[rnd.randrange(len(item_mats))], subdiv=2)
            w.location = (x + rnd.uniform(-25, 25), 230 + rnd.uniform(-25, 25), 92 + rnd.uniform(0, 10))
            w.rotation_euler = (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, math.tau))

    # ---- 照明
    top = C.area_light((0, 0, 520), (0, 0, 0), 900, 2.4e6, (1.0, 0.97, 0.92), "Top")
    key = C.area_light((-420, -320, 300), (0, 0, 0), 220, 1.6e6, (1.0, 0.92, 0.8), "Key"); C.light_look_at(key, (0, -40, 70))
    rim = C.area_light((200, 400, 300), (0, 0, 0), 300, 1.0e6, (0.8, 0.88, 1.0), "Rim"); C.light_look_at(rim, (0, 0, 90))
    fill = C.area_light((420, -420, 200), (0, 0, 0), 300, 4e5, (0.85, 0.9, 1.0), "Fill"); C.light_look_at(fill, (0, -50, 70))
    P.reflection_probe((0, -40, 150), radius=900, clip_start=2)

    # ---- カメラ: ライン手前右の高い位置から、上流を斜めに見下ろす。ゆっくり横移動
    cam, tgt = C.camera((300, -360, 250), (-20, -40, 70), lens=36, fstop=0.08)
    P.key_seq(cam, "location", [(1, (320, -360, 255)), (FRAMES, (250, -345, 240))])
    P.key_seq(tgt, "location", [(1, (-10, -45, 55)), (FRAMES, (-40, -45, 52))])
    cam.data.dof.focus_object = None; cam.data.dof.focus_distance = 460
    sc.view_settings.exposure = -0.45


if __name__ == "__main__":
    C.EPISODE = "ep04"
    C.run_shot("c04_sorting", build, FRAMES)
