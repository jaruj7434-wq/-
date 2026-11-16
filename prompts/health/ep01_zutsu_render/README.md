# #01『頭痛』無料CGレンダリング一式

- `index.html`:Three.js のシーン+テロップ。`renderAt(t)` で任意の時刻を描画(`T` に各カットの開始秒)
- `render.js`:Playwright で 30fps のフレームを書き出す(`node render.js frames 44.3`)
- `mora.py` / `align.py`:ナレーションの無音区間と台本のモーラ数から、各セクションの開始秒を推定
- ナレーション:Higgs Field seed_audio(プリセット声 Hana)、2.8クレジット。job 951d5f8b-55ce-498f-91a1-8d3f7d30a9cb
- 映像はナレーションより1.2秒遅らせて開始(冒頭にタイトル+効果音)
- 必要なもの:`npm i three@0.169.0 @fontsource/noto-sans-jp@5.1.0`、`pip install pyopenjtalk`、ffmpeg
- 書き出した動画は `assets/output/`(git管理外)
