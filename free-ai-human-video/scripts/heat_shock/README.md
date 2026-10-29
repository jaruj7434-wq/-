# 冬のヒートショック(注意喚起の 3DCG ショート)

すべて無料ツールで作る、約47秒・1080x1920・24fps の縦型動画。台本と根拠は `../../prompts/heat-shock.md`。

- 湯気は `../tempura_fire/firesim.py`(自作の流体シミュレーター)で燃料なしの煙として計算し、`../tempura_fire/volume.py` で描画する。
- 共通ヘルパーは `../elevator_quake/kit.py`(と `../mosquito_bite/common.py`)、字幕の区切り方は `../mosquito_bite/compose.py` を使う。

```bash
BLENDER_PY=venv/bin/python ML_PY=ml/bin/python bash run_all.sh /path/to/work
# 出力: free-ai-human-video/assets/output/heat-shock.mp4
```

| ファイル | 役割 |
|---|---|
| `tts.py` | ナレーション |
| `plan.py` | カット割りと浴槽の寸法 |
| `sims.py` | 浴槽から立ちのぼる湯気のシミュレーション |
| `house.py` | 浴室・脱衣所・居間・雪の夜の外観 |
| `shots.py` | 12カットの 3D シーン |
| `compose.py` | 強調テロップ・字幕・効果音(風・鼓動・チャイムなど)・BGM |

## クレジット表記(概要欄に記載)

音声:Style-Bert-VITS2 / JVNV コーパス(CC BY-SA 4.0)
