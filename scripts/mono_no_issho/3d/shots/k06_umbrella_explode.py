"""K06 / カット5-2: 傘の分解図。スタジオで開いたビニール傘が、生地(プラスチック)・骨と中棒(金属)・
持ち手(樹脂)に分かれて空中で離れ、ゆっくり回る。背景は無地のグラデーション。
傘は画面右寄り、左側は後で文字(素材の内訳)を載せる余白。5秒。
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import props as P
import umbrella as U

FRAMES = 120
SPLIT = (14, 66)        # 分かれ始め〜分かれ終わり
CANOPY_UP = 26.0        # 生地が上へ
HANDLE_DOWN = 22.0      # 持ち手が下へ
FRAME_UP = 4.0


def backdrop(cam, dist=900.0, top=(0.10, 0.12, 0.15), bottom=(0.018, 0.022, 0.028), glow=(0.15, 0.17, 0.21),
             glow_center=(0.66, 0.55)):
    """カメラに固定した背景板(縦グラデーション+傘の後ろだけ少し明るい)。"""
    w = 2 * dist * 18 / cam.data.lens * 1.15
    o = P.plane("Backdrop", (w, w * 9 / 16), (0, 0, -dist))
    o.parent = cam
    o.visible_shadow = False
    for attr in ("visible_glossy", "visible_diffuse"):
        if hasattr(o, attr):
            setattr(o, attr, False)
    m, nt, out = C.node_mat("BackdropM")
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ")
    C.link(nt, tc.outputs["Generated"], sep.inputs["Vector"])
    cr = n.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*bottom, 1); cr.color_ramp.elements[1].color = (*top, 1)
    C.link(nt, sep.outputs["Y"], cr.inputs["Fac"])
    # 右寄りの柔らかい光だまり
    vec = n.new("ShaderNodeVectorMath"); vec.operation = "SUBTRACT"
    vec.inputs[1].default_value = (*glow_center, 0)
    C.link(nt, tc.outputs["Generated"], vec.inputs[0])
    sc_ = n.new("ShaderNodeVectorMath"); sc_.operation = "MULTIPLY"; sc_.inputs[1].default_value = (1.0, 0.5625, 0)
    C.link(nt, vec.outputs[0], sc_.inputs[0])
    ln = n.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; C.link(nt, sc_.outputs[0], ln.inputs[0])
    gm = n.new("ShaderNodeMapRange"); gm.inputs["From Min"].default_value = 0.0; gm.inputs["From Max"].default_value = 0.45
    gm.inputs["To Min"].default_value = 1.0; gm.inputs["To Max"].default_value = 0.0
    gm.interpolation_type = "SMOOTHSTEP"
    C.link(nt, ln.outputs["Value"], gm.inputs["Value"])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "SCREEN"
    C.link(nt, gm.outputs["Result"], mx.inputs["Factor"])
    C.link(nt, cr.outputs["Color"], mx.inputs["A"]); mx.inputs["B"].default_value = (*glow, 1)
    em = n.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0
    C.link(nt, mx.outputs["Result"], em.inputs["Color"]); C.link(nt, em.outputs["Emission"], out.inputs["Surface"])
    o.data.materials.append(m)
    return o


def build(sc):
    P.world_studio((0.03, 0.03, 0.035), (0.15, 0.16, 0.18), (0.9, 0.92, 0.95), 1.0, camera_color=(0.05, 0.055, 0.065))

    # 傘(開いた状態)。原点=手元の下端なので、全体の中心が原点付近に来るよう下げる
    pivot = bpy.data.objects.new("Pivot", None); bpy.context.collection.objects.link(pivot)
    pivot.location = (0, 0, 0)
    root = U.make("Umb", (0, 0, -48), rotation_deg=(0, 0, 0), state="open", kind="vinyl")
    root.parent = pivot
    parts = U.parts(root)
    # 部品は body(上下反転)の子: ローカル -Z が上
    for key, dz in (("canopy", -CANOPY_UP), ("frame", -FRAME_UP), ("handle", HANDLE_DOWN)):
        o = parts[key]
        P.key_seq(o, "location", [(1, (0, 0, 0)), (SPLIT[0], (0, 0, 0)), (SPLIT[1], (0, 0, dz))])
    # 全体: 少し手前に傾けて、ゆっくり回す
    pivot.rotation_euler = (math.radians(14), math.radians(-6), 0)
    pivot.keyframe_insert("rotation_euler", frame=1)
    pivot.rotation_euler = (math.radians(14), math.radians(-6), math.radians(75))
    pivot.keyframe_insert("rotation_euler", frame=FRAMES)
    import factory_parts as F
    F.set_interp(pivot, "LINEAR")

    # 照明: 大きなキー(左上前)、左右後ろのリム(ビニールの縁を光らせる)、上から
    k = C.area_light((-260, -300, 200), (0, 0, 0), 220, 1.5e6, (1.0, 0.98, 0.95), "Key"); C.light_look_at(k, (0, 0, 0))
    r1 = C.area_light((-260, 260, 120), (0, 0, 0), 120, 2.5e6, (0.85, 0.92, 1.0), "RimL"); C.light_look_at(r1, (0, 0, 10))
    r2 = C.area_light((280, 220, 60), (0, 0, 0), 120, 2.5e6, (1.0, 0.95, 0.9), "RimR"); C.light_look_at(r2, (0, 0, 0))
    t = C.area_light((0, 0, 330), (0, 0, 0), 200, 3.0e5, (1, 1, 1), "Top"); C.light_look_at(t, (0, 0, 0))
    P.light_card("CardL", (300, 200), (-350, -50, 80), (0, 0, 20), strength=3.0)
    P.light_card("CardR", (200, 300), (300, -150, 150), (0, 0, 20), strength=2.0)
    P.reflection_probe((0, 0, 0), radius=400, clip_start=1)

    # カメラ: 傘を右 1/3 に置く(注視点を左へずらす)
    cam, tgt = C.camera((0, -420, 40), (-58, 0, 2), lens=50, fstop=0.08)
    tgt.location = (-58, 0, 2)
    cam.data.dof.focus_object = None; cam.data.dof.focus_distance = 420
    P.key_seq(cam, "location", [(1, (10, -440, 46)), (FRAMES, (-6, -405, 34))])
    backdrop(cam)
    sc.view_settings.exposure = 0.0


if __name__ == "__main__":
    C.EPISODE = "ep02"
    C.run_shot("k06_umbrella_explode", build, FRAMES)
