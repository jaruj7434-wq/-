# 凍ったフロントガラスにお湯はNG(ライフハックの 3DCG ショート)

約52秒・1080x1920・24fps の縦型動画。台本と根拠は `../../prompts/frozen-windshield.md`。

- 空と環境光は Poly Haven の HDRI(CC0、Hugging Face の `leodriesch/open-hdri-1k` から取得)。
- 霜は「溶ける時刻のマップ」(`maps.py`)としきい値の比較で、溶ける・再び凍る様子を描く。
- お湯の湯気は `../tempura_fire/firesim.py`(自作の流体シミュレーター)で計算し、`../tempura_fire/volume.py` で描画する。
- 共通ヘルパーは `../elevator_quake/kit.py`(と `../mosquito_bite/common.py`)、字幕の区切り方は `../mosquito_bite/compose.py` を使う。

```bash
BLENDER_PY=venv/bin/python ML_PY=ml/bin/python bash run_all.sh /path/to/work
# ナレーションを差し替える場合は、セリフごとの 00.mp3〜11.mp3 を置いたフォルダを NARRATION_DIR に指定する
# (公開版は Higgsfield の Eleven v4 で生成。ユーザーの許可を得てクレジットを消費して作成した)
# 出力: free-ai-human-video/assets/output/frozen-windshield.mp4
```

| ファイル | 役割 |
|---|---|
| `tts.py` | ナレーション(1本目は頭の無音を削って 0 秒目から話す) |
| `plan.py` | カット割りと、フロントガラスの形 (u, v) |
| `maps.py` | 霜が溶ける/再凍結する時刻のマップ |
| `sims.py` | お湯・やかんの湯気のシミュレーション |
| `car.py` | 車・フロントガラス・霜・ヒビ・ワイパー・雪の地面・HDRI |
| `shots.py` | 12カットの 3D シーン |
| `fit_narration.py` | 差し替え用ナレーション(Higgsfield の Eleven v4・声 Julian で生成)をカット割りに合わせて並べる |
| `compose.py` | テロップ・字幕・「答えまで あと◯秒」・タイマー・効果音・BGM |

## クレジット表記(概要欄に記載)

公開版のナレーションは Higgsfield(ElevenLabs Eleven v4)で生成したため、Style-Bert-VITS2 のクレジットは不要。
`tts.py` だけで作る場合は「音声:Style-Bert-VITS2 / JVNV コーパス(CC BY-SA 4.0)」と記載する。
