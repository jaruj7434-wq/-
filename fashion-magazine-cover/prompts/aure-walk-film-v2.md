# AURE 動く表紙 v2 — 歩いてきて最後に表紙になる(藤川らるむ)

- モデル: seedance_2_5 / omni_reference / 480p / 3:4 / 音なし
- end_image: v4 案1(job 1f3fd772-7302-4c5f-8f4e-29d517acb1e4)→ 最後のコマが表紙そのものになる
- 費用: 10秒=30クレジット / 15秒=45クレジット

## プロンプト(10秒版)
Fast-paced fashion film on a Paris street at blue hour, wet cobblestones, glowing café lights. The same young woman as in the end image (long black wavy hair with see-through bangs, pink blush makeup), wearing an off-shoulder taupe knit with long sleeves over her fingertips, light washed denim and a delicate silver necklace. Rhythmic quick cuts:
Shot 1: full-body wide shot, she walks confidently toward the camera down the cobblestone street.
Shot 2: close-up of her collarbone and off-shoulder neckline, the silver necklace catching the light.
Shot 3: close-up of her sleeve-covered fingertips brushing her hair back.
Shot 4: side tracking shot of her full silhouette walking, the denim moving.
Shot 5: waist-up, she turns to the camera, settles into the exact pose of the end image and holds still as the magazine cover.
No text anywhere until the final frame. Cinematic, photorealistic, smooth camera motion.

## 生成記録
- 10秒 / 480p / 30クレジット: 完成 — job 9d8641cf-84bc-4f53-88dd-4db2a11fd6a6
- 生成記録上 end_image は正しく適用済み。multi_shots は false(カット割りはプロンプト任せ)。
  カットが少ない場合は multi_shots / multi_prompt を使った再生成を検討
