# もしも地球が1秒止まったら?(3DCG雑学ショート)

すべて無料ツールで作るテスト動画です。台本は `../../prompts/earth-stops-1sec.md`。

## 必要なもの

- Python 3.13(`bpy` は Python のバージョンに合ったものが入る)
- FFmpeg
- 日本語フォント(IPAゴシック:`/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf`)

```bash
python3 -m venv venv
venv/bin/pip install bpy pyopenjtalk-plus numpy
```

## 実行

```bash
# 確認用の静止画(各カット1枚・低画質)だけ書き出す
PYTHON=venv/bin/python bash run.sh /path/to/work --preview

# 本番(連番PNG → MP4)。出力: free-ai-human-video/assets/output/earth-stops-1sec.mp4
PYTHON=venv/bin/python bash run.sh /path/to/work
```

| ファイル | 役割 |
|---|---|
| `tts.py` | ナレーション音声(pyopenjtalk)と各セリフの時間 `timings.json` を作る |
| `scene.py` | Blender で3DCGシーンを組み、連番PNGに書き出す(Cycles・CPU) |
| `compose.py` | FFmpeg でテロップ・BGM・効果音を合成し、1080x1920 の MP4 にする |

## 画質と時間の目安(CPU 4コア・GPUなし)

- 既定:720x1280 の 75%(540x960)・8サンプル+ノイズ除去 → 約6〜7秒/フレーム、約20秒の動画で70分前後
- 環境変数で調整できる:`SAMPLES=16 SCALE=100`(高画質・遅い)、`FRAMES=100-120`(一部だけ書き出し)
