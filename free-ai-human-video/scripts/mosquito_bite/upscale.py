"""連番PNGを Real-ESRGAN(無料・BSD-3)で拡大し、1080x1920 に整える。

使い方: python upscale.py <入力フォルダ> <出力フォルダ> [モデル]
  モデルの既定は Real-ESRGAN の軽量版 realesr-general-x4v3(4倍に拡大してから 1080x1920 に縮小)。初回は Hugging Face から重みを自動でダウンロードする。
"""
import sys
import time
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import hf_hub_download
from PIL import Image
from spandrel import ModelLoader

MODELS = {
    "compact": ("clavidk/realesr-general-x4v3", "realesr-general-x4v3.pth"),  # 軽量版(CPU でも速い)
    "x2": ("hlky/RealESRGAN_x2plus", "diffusion_pytorch_model.safetensors"),
    "x4": ("Comfy-Org/Real-ESRGAN", "RealESRGAN_x4plus.safetensors"),
}
TARGET = (1080, 1920)


def main(src, dst, which="compact"):
    torch.set_num_threads(4)
    repo, fname = MODELS[which]
    model = ModelLoader().load_from_file(hf_hub_download(repo, fname)).eval()
    out = Path(dst)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(Path(src).glob("f_*.png"))
    for i, f in enumerate(files):
        target = out / f.name
        if target.exists():
            continue
        t0 = time.time()
        img = np.asarray(Image.open(f).convert("RGB"), dtype=np.float32) / 255.0
        x = torch.from_numpy(img).permute(2, 0, 1)[None]
        with torch.inference_mode():
            y = model(x)[0].clamp(0, 1).permute(1, 2, 0).numpy()
        im = Image.fromarray((y * 255 + 0.5).astype(np.uint8))
        if im.size != TARGET:
            im = im.resize(TARGET, Image.LANCZOS)
        im.save(target)
        print(f"{i + 1}/{len(files)} {f.name} {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])
