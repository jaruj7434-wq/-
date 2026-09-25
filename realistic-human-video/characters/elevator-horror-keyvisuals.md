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

## Soul 学習用写真(Nano Banana Pro + Element / 3:4 / 2k、計24クレジット)
| # | 人物 | 内容 | job_id |
|---|---|---|---|
| W1 | 女性A | 正面・真顔 | 4abe86e7-0b7f-4135-b863-d1568f7f71ec |
| W2 | 女性A | 斜め45度・微笑み | ac0b08d3-50a3-42a5-bf00-99087587c30d |
| W3 | 女性A | 横顔 | ccc53560-b39f-4177-888f-a62ec5c98858 |
| W4 | 女性A | 顔アップ・不安 | 858dbccd-05b0-4f8d-935a-37d3bcd14c89 |
| W5 | 女性A | 上半身・室内暖色 | 70d73270-9de9-4888-b6dc-34ac72e3824d |
| W6 | 女性A | 下アングル・驚き | f14236fe-5446-448a-9e9e-b18a89e36d41 |
| P1 | 警察官 | 正面・制服・笑み | 8a0be811-2f74-4a8d-83ed-af7910619ea9 |
| P2 | 警察官 | 斜め45度・真顔 | 67bfc2c7-56c3-44db-88b9-85f8e1a90e6a |
| P3 | 警察官 | 横顔 | c803a398-d9f8-4465-819f-460076c8188a |
| P4 | 警察官 | 顔アップ・制帽なし(顔写真用) | abb69087-e248-4531-9d5c-ca5addbd1276 |
| P5 | 警察官 | 私服・正面 | e6345173-aad0-4290-ac1a-95bf126cad96 |
| P6 | 警察官 | 斜め・冷たい目 | 627a7735-00cb-4467-a4fb-3c4d668889fc |
