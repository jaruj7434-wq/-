# Desert Duel — 登場人物と単体画像プロンプト

Blender は使わず、「画像生成 → 動画化」で制作する方針に変更(2026-09-30)。

## 登場人物(Soul Cinema)

| 役 | 画面位置 | 登録名 | soul_id | 最初の衣装 |
|---|---|---|---|---|
| 若いボーダーシャツの男性(先に撃つ) | 左 | Chill Nautical Vibes | `07038e56-a229-48fb-8d75-c7529cd978ae` | 登録時のまま(ボーダーシャツ) |
| 青い服のおばあさん(撃ち返す) | 右 | Graceful Cleanup Warrior | `2a7c73bb-6eb4-4777-885a-b57bf47f9989` | 登録時のまま(青い服) |

- Soul は1回の生成に1人しか使えないため、まず1人ずつ単体画像を作る。
- その後、単体画像を参照エレメントとして登録し、二人が向かい合うカットを作る。

## ステップ1: 単体画像

- モデル: `soul_cinematic`(Soul Cinema)/ quality `2k` / `9:16`
- 無制限枠: このモデルは対象外(クレジット消費)

### 男性(左・画面右向き)

```
Cinematic full-body photograph of a young man in his twenties wearing his signature
horizontal-striped Breton shirt and his usual casual outfit, standing on sunbaked desert sand
in a Western-style duel standoff. He is in three-quarter profile facing screen right, feet
shoulder-width apart, right arm extended, gripping an old silver revolver aimed toward the
right edge of the frame. Focused, tense expression, eyes slightly narrowed.
Low warm late-afternoon sun from screen left, long soft shadows on the sand, fine dust in the
air, distant dunes and scattered rocks, pale warm sky. Photorealistic, natural skin texture,
35mm film look, shallow depth of field. Entire body visible from head to shoes.
```

### おばあさん(右・画面左向き)

```
Cinematic full-body photograph of an elderly grandmother wearing her signature blue outfit,
standing on sunbaked desert sand in a Western-style duel standoff. She is in three-quarter
profile facing screen left, feet planted firmly, right arm extended, gripping an old silver
revolver aimed toward the left edge of the frame. Calm, fearless expression with a faint
knowing smile.
Low warm late-afternoon sun from screen left, long soft shadows on the sand, fine dust in the
air, distant dunes and scattered rocks, pale warm sky. Photorealistic, natural skin texture,
35mm film look, shallow depth of field. Entire body visible from head to shoes.
```

## 生成ログ

| 日付 | 対象 | モデル | job_id | seed |
|---|---|---|---|---|
| 2026-09-30 | 男性(左) | soul_cinematic 9:16 | `de70815a-236e-4807-8c98-e15cfb4aa68e` | 534035 |
| 2026-09-30 | おばあさん(右) | soul_cinematic 9:16 | `14a74cc9-eb71-468b-8d11-762388ea2183` | 604836 |

## ステップ1b: 映画的カメラワークの単体カット(案)

- 修正点: おばあさんの服を「鮮やかなコバルトブルー」に強調。映画のワンシーン風に視点を多様化。
- 共通スタイル(各プロンプト末尾に付与):
  `Shot on anamorphic 35mm film, cinematic color grading with warm amber highlights and teal shadows, subtle film grain, photorealistic, natural skin texture, dramatic late-afternoon desert light, fine dust in the air.`
- 相手は画面内ではピンボケの影(シルエット)としてのみ登場させる(Soul は1人ずつのため)。

| # | 人物 | カット | プロンプト要旨 |
|---|---|---|---|
| M1 | 男性 | 足元からの超ローアングル | Extreme low-angle shot from the sand level behind the young man's shoes, looking up past his legs; he stands tall in his horizontal-striped Breton shirt, arm extended with an old silver revolver aimed at a small out-of-focus silhouette far away across the desert; the low sun flares behind him. |
| M2 | 男性 | 目元のクローズアップ | Extreme close-up of the young man's eyes and brow, sweat on his skin, eyes narrowed and locked on his target, hard side light from the low sun, edge of the striped Breton shirt collar visible. |
| M3 | 男性 | 肩越し+銃のピント | Over-the-shoulder shot from behind the young man's right shoulder, his striped Breton shirt sleeve and the revolver in sharp focus in the foreground, a distant blurred silhouette of his opponent on the horizon. |
| M4 | 男性 | 真上からのドローン | High-angle drone shot looking straight down at the young man standing alone on rippled sand, gun raised, his long shadow stretching dramatically across the dunes. |
| G1 | おばあさん | ローアングルのミディアム | Low-angle medium shot of an elderly grandmother dressed head to toe in a vivid, saturated cobalt-blue outfit, the blue strongly contrasting with the golden desert, wind moving her hair and clothes, arm extended with an old silver revolver, calm fearless face. |
| G2 | おばあさん | 口元・目元のクローズアップ | Tight close-up of the grandmother's face, deep wrinkles, a faint knowing smile, eyes sharp, the collar of her vivid cobalt-blue outfit framing her face, warm rim light. |
| G3 | おばあさん | 銃を握る手の接写 | Macro close-up of the grandmother's wrinkled hand gripping an old silver revolver, the cuff of her vivid cobalt-blue sleeve in focus, thumb pulling back the hammer, sand particles glowing in the backlight. |
| G4 | おばあさん | 逆光のワイド+ダッチアングル | Wide dutch-angle shot of the grandmother standing alone on a dune ridge, backlit by the setting sun, her vivid cobalt-blue outfit glowing at the edges, long shadow toward the camera, tumbleweed rolling past. |

### 生成ログ(ステップ1b)

| # | job_id | seed |
|---|---|---|
| M1 | `6a415727-7104-4e7d-a663-a4460d9ec72a` | 972163 |
| M2 | `d542417c-b2e4-48b6-a61f-f7b97a4a335c` | 323823 |
| M3 | `604116f3-4ad4-4c23-ae5a-1ad56d6aa0b6` | 402743 |
| M4 | `d6538008-6e60-4569-9412-92299a00f827` | 956099 |
| G1 | `cf69be10-cbe9-4633-ab7a-1569990f7244` | 887361 |
| G2 | `9aee6d87-7227-433c-97d3-b24394142077` | 218368 |
| G3 | `c53058ab-6e37-4779-a8c5-538abc77f2da` | 236944 |
| G4 | `eed9d86a-b399-4f1a-b9cf-551ce40a050e` | 365451 |

## ステップ2: 二人を同じ画面に入れた統一カット(案)

### 反省点(ステップ1b)
- Soul は「顔」は覚えるが服装・小物は固定されず、プロンプトの言葉で帽子や別の服が足された。
- Soul は1回に1人しか使えないため、奥のぼやけた相手が別人になった。

### 方針
- 登録済みの参照エレメント(登録時の姿=服装込み)を使い、二人を毎カット同時に入れる。
  - 男性: `Chill Nautical Vibes` element `f264355d-52eb-4665-9e9c-a58c36c62a47`
  - おばあさん: `Graceful Cleanup Warrior` element `4f672ef6-b040-4eb9-b178-2cf69c5f931d`
- モデル: `nano_banana_pro`(複数参照の再現性重視)/ 9:16 / 2k / 1枚2クレジット
- 服装の言葉(色・アイテム名)はプロンプトに書かず、「参照画像のまま」と指示して上書きを防ぐ。

### 共通の固定指示(全カット末尾)
```
Both people must look EXACTLY like their reference images: same face, same hairstyle, same
clothing, same colors, same accessories. Do not add hats, jackets or any new clothing or
accessories, and do not change any outfit. The young man stands on the left side of the duel
and the elderly woman on the right side. Photorealistic cinematic film still, anamorphic 35mm
look, warm amber highlights and teal shadows, subtle film grain, low late-afternoon desert
sun, long shadows, fine dust in the air.
```

| # | カット | 構図プロンプト |
|---|---|---|
| S1 | 全景(二人の対峙) | Wide side-on establishing shot in a vast desert: <<<M>>> on the left and <<<G>>> on the right stand about 4 meters apart facing each other, each aiming an old silver revolver at the other, both fully visible head to toe. |
| S2 | 男性の足元から超ローアングル | Extreme low-angle shot from sand level just behind <<<M>>>'s shoes, looking up past his legs as he aims an old silver revolver; in the far background, out of focus but clearly recognizable, <<<G>>> stands aiming back at him. |
| S3 | 男性の目元アップ | Extreme close-up of <<<M>>>'s eyes and brow, sweat on his skin, eyes narrowed; behind him, heavily blurred in the distance, the small figure of <<<G>>> facing him. |
| S4 | 男性の肩越し | Over-the-shoulder shot from behind <<<M>>>'s right shoulder, his sleeve and the old silver revolver sharp in the foreground; <<<G>>> in soft focus in the middle distance, aiming back at him. |
| S5 | 真上からのドローン | Top-down drone shot of the desert: <<<M>>> and <<<G>>> facing each other 4 meters apart with revolvers raised, their long shadows stretching across the rippled sand. |
| S6 | おばあさんのローアングル | Low-angle medium shot of <<<G>>> aiming an old silver revolver, calm fearless face, wind in her hair; <<<M>>> blurred in the background aiming at her. |
| S7 | おばあさんの顔アップ | Tight close-up of <<<G>>>'s face, a faint knowing smile, sharp eyes; <<<M>>> heavily blurred in the distant background. |
| S8 | おばあさんの肩越し+手元 | Over-the-shoulder shot from behind <<<G>>>: her hand gripping an old silver revolver sharp in the foreground, thumb pulling back the hammer; <<<M>>> in soft focus in the distance aiming at her. |

### 生成ログ(ステップ2・テスト)

| # | job_id | 結果 | 備考 |
|---|---|---|---|
| S1 | `2f5d89d6-0f41-4904-aee8-b5bbe5fe78fb` | 完了 | 指定 `nano_banana_pro` だがジョブ記録上のモデルは `nano_banana_2` |
| S2 | `466effdf-8d0e-4b82-81ed-f4d4ae64e329` | NSFW判定で失敗 | 銃口を人物に向ける描写+ローアングルが判定された可能性 |
| S2(再) | `102f2843-907a-46f1-ada2-d1be5c7b656f` | 完了 | 銃を「腰の高さで握る小道具リボルバー」、奥のおばあさんは銃を向けない表現に修正して通過 |
