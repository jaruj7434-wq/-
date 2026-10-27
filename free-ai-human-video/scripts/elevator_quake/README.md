# 地震のとき、エレベーターにいたら?(ライフハック 3DCG ショート)

すべて無料ツールで作る、約47秒・1080x1920・24fps の縦型動画。台本と事実の根拠は `../../prompts/elevator-earthquake.md`。

`mosquito_bite/` の共通ヘルパー(`common.py`)・高画質化(`upscale.py`)・字幕の区切り方(`compose.py`)を使い回している。
必要な環境(Blender 用と音声・拡大用の Python)は `../mosquito_bite/README.md` を参照。

## 実行

```bash
BLENDER_PY=venv/bin/python ML_PY=ml/bin/python bash run_all.sh /path/to/work
# 出力: free-ai-human-video/assets/output/elevator-earthquake.mp4
```

| ファイル | 役割 |
|---|---|
| `tts.py` | テンポを上げたナレーション(1セリフ=1カット) |
| `interior.py` | かごの中(ボタン盤・扉・非常灯・時計・防災キャビネット)8カット |
| `building.py` | ビルの断面(最寄り階に停止・地震感知で自動停止・階の間で停止)3カット |
| `kit.py` | ステンレス・発光素材・日本語テキスト・揺れなどのヘルパー |
| `render_shot.py` | カットを1つ組み立ててレンダリング(`--preview` で確認用の静止画) |
| `compose.py` | 強調テロップ・字幕・効果音(ボタン音・チャイム・ベル等をすべて FFmpeg で合成)・BGM |

既定の画質:720x1280・14サンプル・モーションブラーで描き、AI で 1080x1920 に拡大。

## クレジット表記(概要欄に記載)

音声:Style-Bert-VITS2 / JVNV コーパス(CC BY-SA 4.0)
