# 蚊に刺された瞬間(3DCG雑学ショート・本気版)

すべて無料ツールで作る、約35秒・1080x1920・24fps の縦型動画。台本は `../../prompts/mosquito-bite.md`。

## 必要なもの(すべて無料)

| 用途 | ツール | ライセンス |
|---|---|---|
| 3DCG | Blender(`bpy`、Cycles・CPU) | GPL |
| ナレーション | Style-Bert-VITS2 + JVNV モデル(jvnv-M1-jp) | AGPL / CC BY-SA 4.0 |
| 高画質化 | Real-ESRGAN 軽量版(realesr-general-x4v3) | BSD-3 |
| 合成・BGM・効果音 | FFmpeg(音はすべて FFmpeg 内で合成) | LGPL/GPL |
| フォント | IPAゴシック | IPA フォントライセンス |

```bash
python3 -m venv venv && venv/bin/pip install bpy numpy                      # Blender 用
python3 -m venv ml && CMAKE_POLICY_VERSION_MINIMUM=3.5 ml/bin/pip install style-bert-vits2 spandrel "setuptools<80"
```

## 実行

```bash
BLENDER_PY=venv/bin/python ML_PY=ml/bin/python bash run_all.sh /path/to/work
# 出力: free-ai-human-video/assets/output/mosquito-bite.mp4
```

途中で止まっても、同じコマンドで続きから再開できる(書き出し済みのフレームは飛ばす)。

| ファイル | 役割 |
|---|---|
| `tts.py` | ナレーションと各セリフの時間(`timings.json`) |
| `render_shot.py` | カットを1つ組み立ててレンダリング(`--preview` で確認用の静止画) |
| `shot_surface.py` | 皮膚表面のマクロ(近づく・鞘が曲がる・抜ける) |
| `shot_tip.py` | 6本の針が組織を切り開くクローズアップ |
| `shot_section.py` | 皮膚の断面(血管を探す・かゆみの反応) |
| `shot_vessel.py` | 血管の内部(唾液の注入・吸い上げ) |
| `common.py` | 共通ヘルパー(マテリアル、赤血球の形状、レンダリング設定) |
| `upscale.py` | 540x960 で描いた絵を AI で 1080x1920 に拡大 |
| `compose.py` | 字幕・BGM・効果音を合成して MP4 にする |

## 時間の目安(CPU 4コア・GPUなし)

- レンダリング:1フレーム約15〜25秒(540x960・10サンプル)× 約840フレーム → 4時間前後
- 高画質化:1フレーム約8秒 → 約2時間
- 環境変数で調整できる:`SCALE`(%)、`SAMPLES`、`FRAMES="開始-終了"`

## クレジット表記(概要欄に記載)

音声:Style-Bert-VITS2 / JVNV コーパス(CC BY-SA 4.0)
