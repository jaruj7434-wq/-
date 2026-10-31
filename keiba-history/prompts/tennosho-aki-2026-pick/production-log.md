# 天皇賞・秋 2026 谷上の本命予想 — 制作ログ

## 谷上の画像 (nano_banana_pro + Element「谷上」b0bf8884-7e0b-4337-a4c7-40db6c805c32)
- A カメラ目線・赤ペン dd0a6f4f / B 新聞を指さす 7c27db56 / C ◎の新聞を見せる 035f2866

## ナレーション v1 (ElevenLabs v4, 谷上-2 c4548a1f, stability 0.95 / similarity 1.0)
- 01 f7198e34 / 02 02796b5f / 03 6b0d023a / 04 c32dd78c / 05 30c6e85a / 06 6039b89b / 07 d0b73c1c / 08 e5fd63b9 / 09 cf3ec670 / 10 21774bb5
- ノイズ床は全行 -85〜-88dB。編集は天皇賞・秋データ編と同じ (速度変更なし、文中の間は最大0.3秒、行間0.25秒、区切り0.45秒)
- 合計 49.6秒 → `assets/output/tennosho-aki-2026-pick/pick_narration_v1.mp3` (Higgs media ddfce177)

## ナレーション v2 — 本命を最後まで伏せる構成 (ユーザー指示)
- 新規: 01「…俺の本命は……最後に発表する。」f9a5d952 / 02「まずはヒントから。その馬は…」40decd9d / 09「…自信を持って推す、俺の本命は……」b66759dd / 10「1枠1番、クロワデュノール。」55259f78
- 03〜08 と 11 (旧10) は v1 の音声を使用。09 の後に1.0秒の間 (ため)
- 合計 54.6秒 → `pick_narration_v2.mp3` (Higgs media 22a4334e)

## クロワデュノールの見た目 (調査)
- 青鹿毛 (ほぼ真っ黒)、顔に白斑なし、後肢の蹄の上にわずかな白。参照: Wikimedia Commons の CC 写真
  - File:Croix du Nord-2026-5-3.jpg (CC BY-SA 4.0, TRJN) → Higgs media 8370e290
  - File:CroixduNord-20240609-tokyorc.jpg (CC BY 4.0, Chabata_k) → Higgs media 9aad91ba
- 実際の写真は素材として使わず、生成の参照のみに使用。騎手は実在の勝負服を使わず白×赤袖の架空の服

## 馬のキーフレーム (nano_banana_pro, 参照写真2枚)
- H1 夜明けのシルエット 0fea1942 / H2 直線の疾走 e4aed8bd / H3 朝の調教 24448d0d / H4 顔のアップ fb6dd9b8 / H5 正面から突進 80aef7be

## 口の動き用の音声 (Wan 2.7 用、先頭0.1秒の無音 + 末尾0.4秒)
- 01 3e19752f / 05 ceb2c07b / 08 036421a0 / 09 dfb233f4 / 11 a4da3580
