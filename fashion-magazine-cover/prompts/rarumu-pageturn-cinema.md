# らるむ 表紙→ページめくり→ウォーキング(Cinema Studio Video 3.0)計画

## 手順
1. 新しい AURE 表紙(9:16): nano_banana_pro / 2k — 2クレジット
   - 顔: Element rarumu(1cf5acdf…)/ 服: コーデ2 写真(0d9d648e)/ 背景: 夜のパリ
   - 誌名 AURE 固定+服装の説明文(大きく短い日本語+英語)
2. 動画: cinematic_studio_3_0 / start_image=1の表紙 / 9:16 / 音なし
   - 15秒 1080p=150 / 15秒 720p=75 / 10秒 1080p=100
   - めくった下に最初から歩くシーンが映っている(白紙ページ禁止)

## 既存表紙を使う場合
- 表紙 v5(6eda80c8…)は Soul/Element 導入前の顔・服(トープのニット)なので非推奨

## 指定コーデ(a2b1f859-21bf-42fe-9146-6912fd5c01d1)
- オフホワイトのリブ素材ノースリーブ・タンクミニワンピース(胸元に小さな黒のクロス刺繍)
- 細いシルバーのネックレス
- グレーのニット(フード付きジップアップ)— 手に持つ/肩掛け
- 黒のクルーソックス
- 黒×シルバーのボリュームスニーカー(ロゴなしで再現)
- 雰囲気: スポーティー×フェミニンなストリート

## 表紙(生成済み)
- nano_banana_pro / 9:16 / 2k / Element rarumu + 服装写真 a2b1f859 / ソウル・聖水洞の昼 / グレーパーカーは肩掛け
- 1回目 e8a4d3ea…: 失敗(返金済み)/ 2回目: 完成 — job d4bc85ea-e13a-4c21-802e-abc5ad5b7e85(2クレジット)
- 文字: AURE / Sporty Muse / 白×グレーの抜け感 / CLEAN & COOL

## 表紙 v2(GPT Image 2.5 Flare / high / 2k / 9:16 / 2.75クレジット)
- 参照: 表紙 d4bc85ea(顔・写真)+ 服装写真 a2b1f859。写真はそのまま、文字だけ組み直し
- 文字: AURE(Didoneセリフ)/ 藤川らるむ(明朝・ピンク下線)/ RARUMU FUJIKAWA / Sporty Muse(筆記体・ダスティピンク)
  / 白×グレー、引き算の抜け感。/ リブミニに、肩掛けパーカーで大人スポーティー / Silver & Sneakers / CLEAN & COOL(ピンクのラベル)
- 完成 — job a817172a-dce7-48cb-a933-023e9e3d4269

## 表紙 v3(顔の忠実度アップ+モナコの夜)
- 手順1 写真: soul_2 + soul_id 5ebb33c3(学習済みSoul)/ 9:16 / 参照画像なし・服は文章で指定 / enhance_prompt=false が反映
  - 背景: モナコ・モンテカルロの夜の港(ヨット、ヤシ並木、ベル・エポック建築の灯り)— job ce49a090-f90d-4af4-af86-740bee93f8dc(約0.12クレジット)
- 手順2 文字入れ: gpt_image_2_5 flare / high / 2k(写真は変更しないよう指示)— job 26e9999e-fff0-4cc6-899a-41d13807e6e3(2.75クレジット)
  - 文字: AURE / 藤川らるむ(ゴールド下線)/ RARUMU FUJIKAWA / Monaco Nights(ゴールド筆記体)/ 白×グレー、引き算の抜け感。
    / リブミニに、肩掛けパーカーで大人スポーティー / Silver & Sneakers / CLEAN & COOL

## 表紙 v4(パーカーなし・艶髪・4K)
- 写真: soul_2 + soul_id 5ebb33c3 / 2k / 白リブミニのみ(パーカー削除)/ 艶のあるモデル級の黒髪 / モナコの夜 — job 5ade589c-9cba-4577-8fcb-51584b40e02e
- 文字入れ: gpt_image_2_5 flare / high / 4k / 4.25クレジット — job 1e65273d-c990-4032-87d5-c26ea7cf736e
  - 文字: AURE / 藤川らるむ / RARUMU FUJIKAWA / Pure White Night / 白のリブミニ一枚で、夜景をひとりじめ。
    / 細リブが描く、美しいボディライン / 胸元のクロス刺繍が、さりげない主役 / Effortlessly Stunning / その白、反則級。

## 動画(表紙 v4 → ページめくり → モナコの港を歩く)
- cinematic_studio_3_0 / 15秒 / 480p / 9:16 / 音なし / 52.5クレジット
- start_image: 表紙 v4(1e65273d)/ image: 文字なし写真(5ade589c)/ 顔: Element rarumu
- 完成 — job 0faae199-b221-44af-863b-891c50bd9e80
