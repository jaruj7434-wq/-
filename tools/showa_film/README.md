# showa_film — 昭和16mmフィルム風の仕上げツール

```bash
bash tools/showa_film/fetch_fonts.sh                          # 初回のみ:フォント取得
python3 tools/showa_film/film.py prompts/showa_pr/ep01_edl.json   # 本番
python3 tools/showa_film/film.py prompts/showa_pr/ep01_edl.json --preview  # 速い確認用
```

- 入力:EDL(JSON)。カット(動画 / タイトルカード / 単色)、画面内テロップ、縦型用字幕、音声トラックを書く
- 出力:`master_4x3.mp4`(1440×1080)と `vertical_9x16.mp4`(1080×1920)
- 46秒の動画で、4コアで約3分
- 質感の数値は `film.py` の `DEFAULT_LOOK`、意味は `prompts/showa_pr/look_spec.md`
