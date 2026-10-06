# Soul キャラクター — 藤川らるむ(本人同意済み)

- 学習用写真: 20枚(2026-10-06 アップロード、すべて本人の顔アップ・単独)
  f3b1550a, 8d66fad0, ea85a170, c745cc84, bc90bc5c, 0270f3e4, 51b35141, ff65d28e, 6c427f74, 1720cfe2,
  54c9faf6, 9ce5cf64, 454b8e68, 04a1a4ba, 7c34f85e, 30d0da77, e1a5f20e, d7e287d2, 6be8ea23, 5c907705
- 確認メモ: #2 に水色の落書き(イヤホン線)、#6 に星スタンプあり。#1/#4/#16 は小さめ・低解像度。
- 使い方: Soul は soul_2 / soul_cinematic の画像生成専用 → 画像を start_image にして MiniMax H3 等で動画化。

## 学習
- 2026-10-06: #2・#6 を除いた18枚で学習開始 — soul_id 5ebb33c3-451b-47ce-8578-6c7670cf99f9(soul_2)
- 2026-10-06: 学習完了(status: ready)
- 費用目安: soul_2 / 9:16 / 2k / 服装写真1枚を参照 — 約0.12クレジット/枚(表示上は1)

## Soul V2 キービジュアル(9:16 / 2k / 服装写真1枚を参照)
- A ソーホー(bee6a614 レオパード): 完成 — job 2f79e8e8-5327-4709-bb88-db24a6737f1a
- B ロンドン(1ff34c7f ファーコート): 完成 — job 7e79d0e5-3f59-4bfa-8e47-5e3d69466538
- 注意: Soul V2 の enhance_prompt(自動プロンプト補正)が有効で、こちらのプロンプトが参照写真の説明文に置き換わった。
  → 背景がソーホー/ロンドンではなく元写真の東京の街、構図も全身ではなくミディアムショットになった可能性が高い。
  次回は参照画像なし(服装は文章で指定)+ enhance_prompt: false で生成する。

## 動画用キャラクター(Elements)
- Soul は動画モデルで使えないため、動画用に Reference Element を作成(課金なし)
  - element_id 1cf5acdf-fc98-48f9-a443-404fa462c940(名前: rarumu)— 顔写真4枚 1720cfe2 / 04a1a4ba / 51b35141 / 9ce5cf64
  - 対応動画モデル: Cinema Studio Video 3.0 / Seedance 2.0(画像なしで使える)、Kling 3.0(start_image 必須)
  - 使い方: プロンプト内に <<<1cf5acdf-fc98-48f9-a443-404fa462c940>>> を入れる
- 費用(15秒 / 9:16 / 音なし): Cinema Studio 3.0 720p=75・480p=52.5 / Seedance 2.0 720p=67.5
- 動画A ソーホー(Cinema Studio Video 3.0 / 15秒 / 480p / 9:16 / 音なし / 52.5クレジット / Element rarumu): 送信 — job e2b56161-5b04-4602-ab35-5d4ebc3da44f
