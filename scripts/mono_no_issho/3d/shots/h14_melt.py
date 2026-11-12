"""H14 / カット5-3(と1-3 / H02): 1円玉がるつぼで溶ける。10秒。shot_melt.py のシーンを EEVEE で書き出す。"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import common as C
import shot_melt as S

S.FRAMES = 240

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=int); ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=S.FRAMES); ap.add_argument("--res", default="960x540")
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--step", type=int, default=1)
    a = ap.parse_args()
    w, h = map(int, a.res.split("x"))
    sc = S.build((w, h), 16)
    sc.render.engine = "BLENDER_EEVEE"; sc.eevee.taa_render_samples = a.samples
    sc.render.use_motion_blur = False
    out = C.OUT_ROOT / "h14_melt"; out.mkdir(parents=True, exist_ok=True)
    if a.still:
        sc.frame_set(a.still); sc.render.filepath = str(out / f"still_{a.still:04d}.png")
        bpy.ops.render.render(write_still=True)
    else:
        sc.frame_start, sc.frame_end = a.start, a.end
        sc.frame_step = a.step
        sc.render.filepath = str(out / "f_")
        bpy.ops.render.render(animation=True)
