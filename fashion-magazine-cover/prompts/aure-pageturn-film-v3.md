# AURE 動く表紙 v3 — 表紙スタート → ページをめくってCM風ウォーキングへ(藤川らるむ)

- モデル: seedance_2_5 / omni_reference / 10秒 / 480p / 3:4 / 音なし — 30クレジット
- start_image: v4 案1(job 1f3fd772-7302-4c5f-8f4e-29d517acb1e4)→ 1コマ目が表紙そのもの
- image_references: 本人写真3枚(fca702f0…, bee6a614…, 1ff34c7f…)→ 全カットで顔を固定

## プロンプト
Luxury fashion commercial. The video opens exactly on the start image: a magazine cover with the "AURE" masthead and cover lines, the woman standing in Paris at blue hour.
0-2.5s: The cover comes alive. She smiles softly, blinks, tilts her head, then reaches toward the camera with her sleeve-covered hand and grabs the corner of the magazine page. She turns the page toward the viewer; the paper curls and flips across the whole frame with a realistic page-turn transition.
2.5-4.5s: Behind the turned page, a cinematic full-body wide shot: she walks confidently toward the camera down a wet Paris cobblestone street, glowing café lights, Haussmann buildings, Eiffel Tower softly in the distance.
4.5-6s: Slow-motion close-up of her collarbone and off-shoulder taupe knit neckline, the delicate silver necklace sparkling.
6-7.5s: Close-up of her sleeve-covered fingertips brushing her long black wavy hair back, hair flowing.
7.5-10s: Elegant side tracking shot of her full silhouette walking, light washed denim moving, ending with her glancing over her shoulder at the camera.
Style: high-end luxury brand commercial, anamorphic cinematic look, shallow depth of field, soft bokeh, warm highlights with cool blue shadows, smooth gimbal and dolly camera moves, slight slow motion, elegant rhythm.
Identity: keep her face exactly identical to the reference photos in every shot — same eyes, see-through bangs, pink blush makeup, lips; no face distortion, no morphing. Same outfit in every shot. No extra text after the page turn.

## 生成記録
- 9:16 / 480p / 10秒: 失敗(status: nsfw)— job 7b8ebf92-6e6e-4aa8-91db-2d6532573fa2
  - 前回成功した v2(表紙のみ参照)との差分は「本人写真3枚の追加」と「9:16」。
    写真1枚目(脚の露出が多い)が判定に影響した可能性が高い。
- 再試行(写真1を除外・鎖骨表現を削除): 再び失敗(status: nsfw)— job 3d8a8d3e-9b27-452b-a773-53bbc7c0ea9b
  - 1回目の失敗分30クレジットは返金済みを確認。
  - 残る差分は「写真2・3の参照」「start_image 指定」「9:16」。成功した v2 は表紙のみ参照。
- 3回目(9:16表紙 v5 のみを start_image、本人写真なし): 再び失敗(status: nsfw)— job 8a2eba46-30f9-47f9-a3b2-806a825f1e9e
  - Seedance 2.5 の start_image 経由ではこの表紙が通らない模様。次案: Kling 3.0(9:16ネイティブ)で試す
