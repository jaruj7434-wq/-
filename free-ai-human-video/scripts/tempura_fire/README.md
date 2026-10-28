# 天ぷら油の火に水をかけると?(物理シミュレーションの炎を使う 3DCG ショート)

すべて無料ツールで作る、約48秒・1080x1920・24fps の縦型動画。台本と根拠は `../../prompts/tempura-fire.md`。

## 炎について(自作シミュレーター)

Blender 内蔵の Mantaflow は、pip で入る Blender(bpy 4.5〜5.2)では `LevelsetGrid` の継承が壊れていて動かない
(`'LevelsetGrid' object has no attribute 'setConst'`)。そこで同じ考え方の 3D 炎・煙シミュレーターを
`firesim.py` に自前で実装した(numba で高速化)。

- 非圧縮性流体(MAC 格子、赤黒 SOR で圧力を解く)、2次ルンゲ=クッタのセミラグランジュ移流+MacCormack 補正
- 燃焼(燃料 → 熱・炎・すす)、温度による浮力、渦の強調(vorticity confinement)
- 鍋・ふた・天井などの固体、消火器の粉(燃料と熱を奪う)
- 結果は `volume.py` でフレームごとの画像アトラスにし、Blender のボリュームシェーダーで3Dとして読み直して描画する
  (炎=黒体放射、煙=光を遮る煙、粉=白く散乱)

## 実行

```bash
# bpy・numba・pillow を入れた Python と、style-bert-vits2 の Python を指定
BLENDER_PY=venv/bin/python ML_PY=ml/bin/python bash run_all.sh /path/to/work
# 出力: free-ai-human-video/assets/output/tempura-fire.mp4
```

| ファイル | 役割 |
|---|---|
| `tts.py` | ナレーション |
| `plan.py` | カット割りと出来事のタイミング(シミュレーションと 3D で共通) |
| `firesim.py` | 3D 炎・煙シミュレーター |
| `sims.py` | カットごとのシミュレーション(安定した炎・火柱・しぶき・発火・消火器・ふた) |
| `volume.py` | シミュレーション結果を Blender で描画する(アトラス化・ボリューム素材) |
| `kitchen.py` | 台所のセットと天ぷら鍋 |
| `shots.py` | 10カットの 3D シーン |
| `compose.py` | 強調テロップ・字幕・効果音(パチパチ・火柱・噴射音などを FFmpeg で合成) |

## クレジット表記(概要欄に記載)

音声:Style-Bert-VITS2 / JVNV コーパス(CC BY-SA 4.0)
