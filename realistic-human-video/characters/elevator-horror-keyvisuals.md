# 「エレベーターの男」人物キービジュアル v1(Soul 2.0 / 9:16 / 2k)

| # | 人物 | job_id | seed |
|---|---|---|---|
| 1 | 女性A 案1 | 0e4e4da8-099a-44fc-a31a-1cf08e8f859f | 978142 |
| 2 | 女性A 案2 | 52614f86-1ec3-4ef2-8031-170715ba9490 | 893251 |
| 3 | 帽子の男 案1 | 35b143c3-04ab-4995-9bc2-f2ba1de11b7a | 134517 |
| 4 | 帽子の男 案2 | 396366f6-c15a-4eea-91bb-25e3ecf7d12a | 488610 |
| 5 | 警察官 案1 | fc68b6f6-2763-4d5f-8a7a-8c68cf085a23 | 797260 |
| 6 | 警察官 案2 | 5e2f2e5c-7de4-4e6d-a0c6-6b9f06ce15fb | 281380 |

## プロンプト
- 女性A: Photorealistic candid photo of a beautiful Japanese actress around 30 years old, pretty and cute face, long straight black hair, wearing a beige trench coat with a shoulder bag, standing in the lobby of a Japanese apartment building at night after work, slightly tired natural expression, soft fluorescent lobby lighting, natural skin texture with visible pores, subtle makeup, shot on smartphone, 35mm, shallow depth of field, realistic, unretouched
- 帽子の男: Photorealistic cinematic still of a creepy Japanese man in his 40s standing in the back corner of a dim apartment elevator at night, black baseball cap pulled down very low, head bowed, his face completely hidden in deep shadow so no facial features are visible, dark navy work jacket, black gloves, hands at his sides, flickering cold fluorescent light, eerie tense atmosphere, Japanese horror film look, realistic, film grain
- 警察官: Photorealistic bust shot of a Japanese man in his 40s wearing a Japanese police officer uniform and police cap, standing in front of an apartment front door in daytime, facing the camera, polite gentle smile but his eyes are cold and not smiling, unsettling calm, natural skin texture with visible pores, slight stubble, realistic, unretouched, shot on 50mm lens

## 採用(すべて案1)と参照エレメント
| 人物 | 採用 job_id | Element 名 | Element ID |
|---|---|---|---|
| 女性A | 0e4e4da8-099a-44fc-a31a-1cf08e8f859f | elevator-woman-A | 90b9cd77-0643-44cf-8bfb-5d6de6cd1941 |
| 帽子の男 | 35b143c3-04ab-4995-9bc2-f2ba1de11b7a | elevator-cap-man | dc341f95-3e7d-4458-a692-6b57d36fe8fe |
| 警察官 | fc68b6f6-2763-4d5f-8a7a-8c68cf085a23 | elevator-police-officer | 8bfeb915-6e00-4e12-86b1-0350f63a3596 |

- プロンプト内で `<<<Element ID>>>` と書くと参照される。
- Elements 対応モデル:画像=nano_banana_pro / nano_banana_2 / gpt_image_2 / seedream 系 / cinematic_studio_2_5、動画=Kling 3.0 / Seedance 2.0 など。**Soul 2.0 は非対応**。
