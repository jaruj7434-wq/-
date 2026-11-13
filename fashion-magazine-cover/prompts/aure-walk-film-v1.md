# AURE 動く表紙 — パリ・ウォーキング ファッションフィルム(藤川らるむ)

元: v4 案1(job 1f3fd772-7302-4c5f-8f4e-29d517acb1e4)

## 方針(文字崩れ対策)
AI動画に文字を描かせると、カットが変わるたびに文字が歪む・消える。
→ 映像は文字なしで生成し、AURE と説明文は後から本物のフォントで重ねる(Higgsedit / sandbox)。
  文字は崩れず固定。カットごとに映っているアイテムの説明文を出し分けられる。

## 手順と費用
1. キービジュアル(文字なし・全身・9:16): gpt_image_2_5 で v4 案1 を編集 — 2.75クレジット
2. 動画: kling3_0 pro / 15秒 / 9:16 / 音なし / マルチショット — 26.25クレジット
3. 文字合成: Higgsedit(生成クレジットなし)

## ステップ1 プロンプト(キービジュアル)
Using the reference image, create a full-body 9:16 fashion photograph of the same woman (same face, hair, makeup) standing on the same Paris blue-hour cobblestone street. Remove ALL text, letters and logos. Outfit head to toe: off-shoulder taupe knit with long sleeves covering fingertips, light washed wide-leg denim, black leather belt with a silver star buckle and a thin silver chain, delicate silver necklace, small black leather shoulder bag, black pointed ankle boots. Photorealistic, 35mm lens, editorial fashion photography, no text.

## ステップ2 ショットリスト(15秒)
| # | 秒 | カット | 重ねる文字 |
|---|---|---|---|
| 1 | 0-2.5 | 全身。カメラに向かって石畳を歩き出す(正面・引き) | AURE / Soft & Effortless |
| 2 | 2.5-4.5 | 胸元アップ。オフショルダーと鎖骨、シルバーネックレスがきらめく | 鎖骨が主役のオフショルダー |
| 3 | 4.5-6.5 | 手元アップ。萌え袖の指先で髪をかき上げる | 萌え袖ニットで、甘さは指先だけ |
| 4 | 6.5-8.5 | 腰まわり。スターバックルのベルトとチェーンが揺れる | 華奢なシルバーで、肌に光をひとさじ |
| 5 | 8.5-11 | 横から追いかける全身シルエット。ワイドデニムが揺れる | トープ × アイスブルー |
| 6 | 11-12.5 | 足元ローアングル。濡れた石畳を歩くブーツ | Effortlessly Beautiful |
| 7 | 12.5-15 | 振り返ってカメラ目線、表紙のポーズで静止 | AURE / 藤川らるむ / その抜け感、反則級。 |
