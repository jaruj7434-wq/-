# 動物目線の東京：3D制作ツール

Higgsfield を使わず、Three.js（WebGL）の3Dアニメーションで映像を作る。
ヘッドレスの Chromium で1コマずつ描き、ffmpeg で動画にし、Python で合成した環境音を合わせる。

## 必要なもの
- Node.js、ffmpeg、Playwright の Chromium
- Python 3 ＋ numpy / scipy（`pip install numpy scipy`）

## 作り方（第1話）
```bash
cd tools/animal_tokyo
npm install

# 静止画で確認（秒数をカンマ区切り）
node ep01/render.js --stills 2,7,12,17,22,27,33 --out /tmp/stills

# 映像（音なし）：1080x1920・30fps。1コマ約1.7秒、全体で1時間ほど
node ep01/render.js --from 0 --to 68 --out ../../assets/output/animal_tokyo/ep01_video_noaudio.mp4

# 音
python3 ep01/audio.py ../../assets/output/animal_tokyo/ep01_audio.wav

# 合成（音量を -14 LUFS にそろえる）
ffmpeg -i ../../assets/output/animal_tokyo/ep01_video_noaudio.mp4 -i ../../assets/output/animal_tokyo/ep01_audio.wav \
  -c:v copy -af loudnorm=I=-14:TP=-1.5 -c:a aac -b:a 192k -shortest ../../assets/output/animal_tokyo/ep01_crow_short.mp4
```

## ファイル
| ファイル | 中身 |
|---|---|
| `ep01/timeline.json` | カットの秒数、時刻テロップ、字幕 |
| `ep01/lib.js` | 乱数・ノイズ、ビル・森・葉・ゴミ袋・カラスなどの生成 |
| `ep01/shots.js` | カットごとのシーンとカメラの動き（C1〜C6） |
| `ep01/shots_day.js` | 日中のカット（D1 貯食・D2 水浴び・D3 昼の休息・D4 屋上・D5 集合） |
| `ep01/main.js` | 描画、色調整（ビネット・粒子）、テロップ・字幕、地図カード（C7） |
| `ep01/render.js` | 静止画・動画の書き出し |
| `ep01/audio.py` | 風・カラスの声・はばたき・ビニール・収集車・雑踏・BGM の合成 |

書き出した動画や音は `assets/output/` に置く（git の管理対象外）。
