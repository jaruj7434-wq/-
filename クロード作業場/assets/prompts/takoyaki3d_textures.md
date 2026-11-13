# たこ焼き返し 3D:質感テクスチャ(Higgsfield 生成)

- 生成日: 2026-11-13
- モデル: gpt_image_2_6(1枚 0.25 クレジット、合計 1.25 クレジット。通常クレジットで生成)
- 置き場所: 元画像 `assets/source/higgsfield/takoyaki/*.png`(git 管理外)
  → ゲーム用に JPG 化して `src/takoyaki3d/tex/*.jpg`(git 管理外。公開時に同梱する)
- 画像が無い場合、ゲームはプログラムで作った簡易な質感で動く

| ファイル | 比率 | job_id | プロンプト |
|---|---|---|---|
| iron.jpg | 1:1 | 5d477121-b5ba-4263-bccc-31b0c16e34ae | Seamless tileable texture, straight top-down view of a well-seasoned black cast iron griddle surface. Dark matte charcoal iron with a subtle thin oil sheen, fine sand-cast pitting and tiny specks, very slight warm brown patina in places. Even soft lighting, no shadows, no holes, no objects, no text. Photorealistic material scan, edges tile seamlessly. |
| crust.jpg | 1:1 | 41a89c6f-bf51-41eb-b035-e18e5a77c20c | Seamless tileable texture, extreme close-up top-down of the crispy outer crust of a perfectly cooked takoyaki ball: even golden-brown fox color, fine crunchy bubbly texture with tiny darker toasted spots and lighter golden ridges. Even soft lighting, no sauce, no toppings, no shadows, no text. Photorealistic food material scan, edges tile seamlessly. |
| batter.jpg | 1:1 | cb2a86e4-fa7e-4466-bb71-cd7975b2cee4 | Seamless tileable texture, top-down close-up of raw pale cream takoyaki batter surface just poured, glossy and slightly bubbly, sprinkled with small chopped green onion pieces, red pickled ginger bits and crunchy tenkasu tempura flakes, evenly scattered. Even soft lighting, no shadows, no text. Photorealistic food material scan, edges tile seamlessly. |
| wood.jpg | 1:1 | f00b6b35-4257-4fde-b960-4300ffc41ffe | Seamless tileable texture, top-down view of a well-used dark wooden food stall counter: warm brown cedar planks running horizontally, visible grain, small scratches and worn spots, slight varnish sheen. Even soft lighting, no objects, no text. Photorealistic wood material scan, edges tile seamlessly. |
| bg.jpg | 9:16 | 6f20f68c-8221-40a5-ab69-71d6aae77268 | Vertical background for a mobile game: a Japanese street food stall (yatai) at night, seen from the customer side, heavily out of focus. Warm glowing red paper lanterns as soft bokeh near the top, dark wooden stall frame, dim warm orange light, deep dark brown shadows in the lower half. No people, no readable text or logos, no food in focus. Cinematic, photorealistic, shallow depth of field. |

## 注意
- Steam などで販売する場合、プレイヤーが目にする画像に生成AIを使っているため、AI利用の申告が必要。
- Higgsfield の商用利用条件は、販売前にプランの規約を確認すること。
