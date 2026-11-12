# モノの一生 — 3Dショット（Blender / bpy）

Higgsfield の代わりに、Blender を Python モジュールとして使い、コードからリアル系の3Dカットを作る。

## 準備
```bash
pip install bpy==5.3.0   # Python 3.13 用ホイール（約430MB）。ffmpeg も使う
python3 scripts/mono_no_issho/3d/coin_textures.py   # 1円玉風の表裏ハイトマップ
```

## ショット
| スクリプト | 台本カット | 内容 |
|---|---|---|
| `shot_melt.py` | 1-3 / 5-3（H02・H14） | 1円玉がるつぼの溶けたアルミに落ち、赤熱して沈む |

```bash
python3 scripts/mono_no_issho/3d/shot_melt.py --still 60 --samples 32 --res 960x540   # 1枚確認
python3 scripts/mono_no_issho/3d/shot_melt.py --samples 64 --res 1920x1080            # 本番
ffmpeg -framerate 24 -i assets/output/mono_no_issho/ep01/shot_melt/f_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 shot_melt.mp4
```
出力先 `assets/output/` は git 管理外。

## レンダリング時間の目安（CPU 4コア、GPUなし）
- 960x540・32サンプル：1フレーム 約25秒（5秒=120フレームで約50分）
- 1920x1080・64サンプル：1フレーム 約3〜4分の見込み（5秒で6〜8時間）
