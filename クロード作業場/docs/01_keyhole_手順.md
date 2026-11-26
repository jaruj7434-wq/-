# 「鍵穴を通り抜ける金の球」制作手順(すべて無料)

## 必要なもの(無料)
1. **Blender 4.2 以降**(推奨 5.x): https://www.blender.org/download/
2. **FFmpeg**: https://ffmpeg.org/download.html(Windows は「gyan.dev」のビルドが簡単)
3. **Python 3**(compose.py を使う場合): https://www.python.org/

## ステップ1: シーンを開いて確認する(任意)
```bash
blender -b -P scripts/keyhole_scene.py -- --soft 75 --save soft075.blend
```
保存された `soft075.blend` を Blender で開き、再生(スペースキー)すると動きを確認できます。
カメラ・ライト・素材は GUI で自由に調整できます。

## ステップ2: 5段階をレンダリングする
`--frames` は段階ごとの尺です(30fps)。
```bash
blender -b -P scripts/keyhole_scene.py -- --soft 0   --frames 120 --render render/s0/f_
blender -b -P scripts/keyhole_scene.py -- --soft 25  --frames 120 --render render/s25/f_
blender -b -P scripts/keyhole_scene.py -- --soft 50  --frames 150 --render render/s50/f_
blender -b -P scripts/keyhole_scene.py -- --soft 75  --frames 180 --render render/s75/f_
blender -b -P scripts/keyhole_scene.py -- --soft 100 --frames 150 --render render/s100/f_
```
- 既定は 1080×1920、192サンプル(Cycles)です。NVIDIA などの GPU があれば自動で使います
- 時間がかかる場合は `--samples 96` に下げてください(ノイズ除去が入るので十分きれいです)
- まず1枚だけ試すなら `--still 60` を付けます

## ステップ3: 文字入れと連結
```bash
python scripts/compose.py render keyhole_final.mp4
```
効果音を付ける場合は、DaVinci Resolve(無料)で音を並べて書き出した wav を指定します。
```bash
python scripts/compose.py render keyhole_final.mp4 --audio sfx.wav
```

## 調整のコツ
| やりたいこと | 変更する場所(keyhole_scene.py) |
|---|---|
| 柔らかさの挙動を変える | `table = [...]`(硬さ k / 空気圧 p / 曲げ b) |
| 球の色を変える(ローズゴールドなど) | `mat_gold("GoldPolished", ...)` の Base Color |
| 背景色を変える | `mat_backdrop()` の Base Color |
| 大理石の模様 | `mat_black_marble()` の wave / ramp の値 |
| よりリアルな大理石にする | Poly Haven(無料・CC0)の大理石テクスチャに差し替える |
| カメラの位置 | `cam.location` と `cd.lens` |

## シミュレーションの仕組み
- 0%: 剛体(Rigid Body)
- 25〜100%: 布シミュレーション + 内部の空気圧(Cloth + Pressure)
  - 標準の Soft Body より安定していて、「ぷるん」とした質感を出しやすい
  - 内部スプリングを入れると通り抜けなくなるので、オフにしている
