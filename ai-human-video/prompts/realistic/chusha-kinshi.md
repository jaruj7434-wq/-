# 「そこは駐車禁止ですよ!」— 絵コンテ & プロンプト

- ジャンル: リアル実写風コメディ(ショートコント)
- 尺: 約34秒 / 10カット
- アスペクト比: 16:9(シネマ。SNS用に 9:16 版も可)
- ルック: 35mmフィルム、アナモルフィックレンズ、粒子感、やや褪せた色(曇りの夕方)、浅い被写界深度
- 制作方法:
  1. 各カットの「最初のコマ」を静止画で生成(`gpt_image_2_5`)。
     カット1を基準画像にして、以降のカットはこれを参照し、人物・車・場所をそろえる。
  2. 静止画を `kling3_0`(mode: pro、sound: on)で動画化(image-to-video)。
  3. 10カットをつないで1本にする(video-montage)。

## 演出メモ

- 笑いの構造は「絶望 → 助けが来た!(期待)→ 優しく心配そうな顔で的外れな一言 → 間 → 爆発」。
- おばさんの**期待顔**(カット4)をしっかり見せることで、その後の裏切りが効く。
- おじさんは**本気で心配している優しい顔**で言う。悪気がないのがポイント。
- オチは、キレられたおじさんが何事もなかったように窓を閉めながら走り去り、おばさんが一人取り残されること。
- 効果音は最小限。カラスなどの動物の声は入れない(虫の声・風のみ)。

## 共通設定(全プロンプトに含める)

```
Shot on 35mm film, anamorphic lens, natural film grain, slightly faded warm color grade,
overcast late afternoon light, shallow depth of field, photorealistic, Japanese rural road
alongside a narrow concrete irrigation canal (about 1.5 m wide) next to rice fields, utility poles.
```

## 登場人物・小道具

- **おばさん**: 60代前半の日本人女性。パーマの短い髪、ベージュのカーディガン、
  花柄のエプロン、サンダル。関西〜西日本の下町のおばちゃん風。
- **おじさん**: 60代後半の日本人男性。白髪混じりの短髪、柔らかく優しい顔立ち、
  薄いブルーのポロシャツ。人の良さがにじみ出る雰囲気。
- **事故車**: 白い軽自動車(箱型の軽ワゴン)。前輪が用水路に落ち、車体が斜めに傾いている。
  ハザードランプ点滅。
- **おじさんの車**: シルバーの古いセダン。

## カット割り

| # | 尺 | 画角・カメラ | 内容 | 音 |
|---|---|---|---|---|
| 1 | 4秒 | 超ロング / ドローン俯瞰、ゆっくり前進 | 田んぼ沿いの道。白い軽が用水路に斜めに突っ込んでいる。横におばさん | 虫の声、風、ハザードのカチカチ |
| 2 | 3秒 | ミディアム / 手持ち、わずかに揺れ | おばさんが頭を抱えて車を見つめる。「どうしよう…」と小声 | ため息、つぶやき |
| 3 | 4秒 | 望遠・道路の低い位置から / 固定 | 奥からシルバーのセダンが走ってくる | 遠くからのエンジン音 |
| 4 | 3秒 | おばさんの顔アップ / ゆっくり寄る | 車に気づき、顔がパッと明るくなる。「助かった…!」という少し期待した表情 | エンジン音が近づく |
| 5 | 4秒 | おばさんの背中なめ / 固定 | セダンがおばさんの横でスッと止まる | ブレーキ音 |
| 6 | 4秒 | 運転席の窓のアップ / 固定 | 窓がゆっくり下がり、心配そうな優しい顔のおじさんが現れ、身を乗り出す | パワーウィンドウの音 |
| 7 | 4秒 | おじさんのバストショット(おばさんの肩なめ) | 眉を下げた心配顔で、優しく「そこは駐車禁止ですよ!」 | セリフ(穏やか・心配そう) |
| 8 | 3秒 | おばさんの顔アップ / 固定 → 一気にズームイン | 期待顔が固まり、目が据わる(間)→「わかっとるわぼけぇ!」と大声でキレる | 一瞬の無音 → 怒鳴り声 |
| 9 | 4秒 | 運転席の窓のミディアム / 固定 | 一瞬キョトンとしたおじさんが、窓をスーッと閉めながら車を発進させる | パワーウィンドウの音、発進音 |
| 10 | 4秒 | 引きのワイド / 固定 | セダンが静かに走り去り、傾いた軽の横におばさんだけがポツンと取り残される | 遠ざかるエンジン音 → 虫の声だけ |

## 静止画プロンプト(最初のコマ)

1. `Extreme wide high-angle drone shot. A white Japanese kei box car has crashed nose-first into the narrow irrigation canal beside the road, tilted diagonally, front wheels in the canal, rear wheels lifted, hazard lights on. A Japanese woman in her early 60s (short permed hair, beige cardigan, floral apron, sandals) stands next to the car holding her head with both hands.` + 共通設定
2. `Medium shot, handheld. The same woman stands beside the tilted white kei car, holding her head with both hands, worried and exasperated expression, looking at the car.` + 共通設定
3. `Low-angle telephoto shot from road level. In the far background, an old silver sedan approaches along the rural road; in the foreground, out of focus, the tilted white kei car in the canal.` + 共通設定
4. `Close-up of the woman's face, she has just noticed a car approaching, her worried face starting to brighten with hope and relief, eyebrows lifting, slight hopeful smile.` + 共通設定
5. `Over-the-shoulder shot from behind the woman. An old silver sedan pulls up and stops right beside her on the road, next to the tilted kei car.` + 共通設定
6. `Close-up of the driver's side window of the old silver sedan, window closed, reflection of rice fields, a kind-looking Japanese man in his late 60s (short graying hair, gentle face, light blue polo shirt) behind the glass with a concerned expression.` + 共通設定
7. `Medium close-up over the woman's shoulder. The kind man sits in the driver's seat with the window fully down, leaning slightly toward her, eyebrows raised in sincere concern, gentle caring expression.` + 共通設定
8. `Close-up of the woman's face, her hopeful expression frozen, eyes narrowing, mouth corner twitching with suppressed anger.` + 共通設定
9. `Medium shot of the silver sedan's open driver's window from the woman's side. The kind man in the driver's seat with a slightly puzzled, blank expression, hands on the steering wheel.` + 共通設定
10. `Wide static shot. The rural road beside the canal, the tilted white kei car in the canal, the woman standing alone with fists clenched, the silver sedan driving away in the distance, dusk sky over the rice fields.` + 共通設定

## 動画プロンプト(kling3_0)

全カット共通: `No animal sounds, no crows, no birds.`

1. `Slow drone push-in toward the crashed car. Hazard lights blink. Cicadas and wind ambience only. No dialogue.`
2. `The woman sighs, shakes her head slowly while holding it, and mutters quietly in Japanese: "どうしよう…". Subtle handheld camera sway.`
3. `The silver sedan drives slowly toward the camera along the rural road. Distant engine sound. Static camera.`
4. `Slow push-in on the woman's face. She notices the approaching car, lowers her hands from her head, and her face lights up with hope and relief, a small expectant smile. Engine sound getting closer.`
5. `The silver sedan gently stops right beside the woman. Soft brake squeak. Static camera.`
6. `The driver's window slowly rolls down, revealing the kind man with a worried, caring expression, leaning toward the window. Power window motor sound.`
7. `The man looks at her with sincere concern, eyebrows raised, and says softly and kindly in Japanese, in a worried gentle voice: "そこは駐車禁止ですよ!" Static camera.`
8. `The woman's hopeful face freezes, a beat of silence, her eye twitches, then a fast zoom-in as she explodes with anger and shouts loudly in Kansai dialect: "わかっとるわぼけぇ!"`
9. `The man blinks with a puzzled face, then calmly rolls the window up while the car starts moving forward and pulls away out of frame. Power window motor sound, engine starting. Static camera.`
10. `Static wide shot. The silver sedan calmly drives away down the rural road into the distance, leaving the woman standing alone next to her tilted car in the canal. Engine sound fading, then only cicadas. Comedic silence.`

## 生成済み静止画(2026-10-05、gpt_image_2_5 / 16:9 / quality low / 1k)

A版はカット1-A、B版はカット1-B を参照画像にして生成。

| カット | A版 job_id | B版 job_id |
|---|---|---|
| 1 | 9cc0f231-82ea-49e9-a7b8-ffd84558f09d | 3ac390e4-ae6e-4614-b876-8262700a4979 |
| 2 | 76e5f50d-fbf0-4f6f-a817-0c9938a0a492 | fdb53f70-f941-49cf-a6a3-10e3c3bdf689 |
| 3 | 62dde0d1-de8e-4ff5-9b7f-8fa0d90c3ba1 | e9014573-1c89-4a91-822a-cd6bca516ee8 |
| 4 | d5afccb8-02e2-49f9-919e-5ea3305a533f | 80d8450b-c56d-48a5-95e2-4d8c853bb7ec |
| 5 | 5c36cf59-186a-4352-a405-32907df899f0 | 2c88be97-2e61-434c-8f32-6615e81ccdfc |
| 6 | c779e79a-242e-4a31-8e68-27cbb6225f17 | 292c269d-d10a-4949-8e79-f771b04ca303 |
| 7 | 637a242d-174f-4637-ac12-7021aa98e4dd | d217598b-9ee1-44a4-a69a-8e7512950a87 |
| 8 | a20e6732-2923-4bd7-816c-19bbe99c7426 | 845b8e6a-2c3a-49d0-8024-fad716d93214 |
| 9 | 41d55b69-25a0-4539-a6a9-6f5d71affd3c | e7baf614-a20e-4383-a0f2-9d4a1d6e201f |
| 10 | 0eee368c-7ff5-4f20-980e-f63b774cc000 | 7b0e5398-e7e7-46a6-a9b6-58eb3158ebf0 |

## Seedance 2.5 版(画像を使わない text-to-video・1本30秒)

- model: `seedance_2_5` / mode: `t2v` / duration: 30 / resolution: 480p / aspect_ratio: 16:9 / generate_audio: true
- 1本の動画の中でカットを切り替える(人物・車の見た目がそろいやすい)

```
A 30-second cinematic Japanese comedy short film, multiple shots with hard cuts, shot on 35mm film with an anamorphic lens, natural film grain, slightly faded warm color grade, overcast late afternoon light, shallow depth of field, photorealistic. Location: a quiet rural road in Japan running alongside a narrow concrete irrigation canal (about 1.5 m wide), rice fields and utility poles. No animal sounds, no crows, no birds. No background music. No subtitles or on-screen text.

Characters (keep identical in every shot):
- THE WOMAN: Japanese, early 60s, short permed hair, beige cardigan, floral apron, sandals. Her white Japanese kei box car has slid nose-first into the irrigation canal and is tilted diagonally, front wheels in the canal, rear wheels lifted, hazard lights blinking.
- THE MAN: Japanese, late 60s, short graying hair, gentle kind face, light blue polo shirt, driving an old silver sedan.

Shot 1 (0-3s): Extreme wide high-angle drone shot slowly pushing in. The white kei car tilted in the canal, hazard lights blinking, the woman standing beside it holding her head with both hands. Cicadas and wind only.
Shot 2 (3-6s): Medium handheld shot. The woman sighs, shakes her head while holding it, and mutters quietly in Japanese: "どうしよう…"
Shot 3 (6-9s): Low-angle telephoto shot from road level. The old silver sedan approaches slowly from the far end of the road. Distant engine sound.
Shot 4 (9-12s): Slow push-in close-up on the woman's face. She notices the approaching car, lowers her hands, and her face lights up with hope and relief, a small expectant smile.
Shot 5 (12-14s): Over-the-shoulder shot from behind the woman. The silver sedan gently stops right beside her. Soft brake squeak.
Shot 6 (14-17s): Close-up of the sedan's driver window. The window slowly rolls down, revealing the kind man with a worried, caring expression, leaning toward her.
Shot 7 (17-20s): Medium close-up of the man over the woman's shoulder. With sincere concern and a soft, gentle, kind voice, he says in Japanese: "そこは駐車禁止ですよ!"
Shot 8 (20-24s): Close-up of the woman. Her hopeful face freezes, a beat of silence, her eye twitches, then a fast zoom-in as she explodes and shouts loudly in Kansai dialect Japanese: "わかっとるわぼけぇ!"
Shot 9 (24-27s): Medium shot of the man in the driver's seat. He blinks with a puzzled face, then calmly rolls the window up while the car starts moving and pulls away. Power window sound, engine starting.
Shot 10 (27-30s): Static wide shot. The silver sedan calmly drives away into the distance, leaving the woman standing alone with clenched fists next to her tilted car in the canal. Engine sound fades, only cicadas remain.
```

### 監督版プロンプト(実際に生成に使用)

```
A 30-second cinematic Japanese deadpan comedy short film, ten shots joined by hard cuts, directed like an arthouse film. Shot on 35mm Kodak film with vintage anamorphic lenses, natural film grain, soft halation, slightly faded warm color grade, overcast late afternoon light, shallow depth of field, photorealistic, 2.39:1 framing feel inside 16:9. Location: a quiet rural road in Japan running alongside a narrow concrete irrigation canal (about 1.5 m wide), rice fields, utility poles, distant mountains. Sound: diegetic only, cicadas and light wind. No animal calls, no crows, no birds. No background music. No subtitles or on-screen text.

Characters (keep identical in every shot):
- THE WOMAN: Japanese, early 60s, short permed hair, beige cardigan, floral apron, sandals. Her white Japanese kei box car has slid nose-first into the irrigation canal and is tilted diagonally, front wheels in the canal, rear wheels lifted, hazard lights blinking.
- THE MAN: Japanese, late 60s, short graying hair, gentle kind face, light blue polo shirt, driving an old silver sedan.

Shot 1 (0-3s) ESTABLISHING: Extreme wide high-angle drone shot, slow crane-down and push-in toward the tilted white kei car in the canal, hazard lights blinking, the tiny figure of the woman beside it holding her head. Calm, still, almost beautiful. Cicadas and wind.
Shot 2 (3-6s): Medium shot, 50mm handheld, slight breathing movement. The woman holds her head with both hands, sighs, and mutters quietly in Japanese: "どうしよう…"
Shot 3 (6-9s): Low-angle 200mm telephoto shot from road level, heat shimmer on the asphalt, the out-of-focus tilted car in the foreground edge. Far down the straight road, the old silver sedan slowly appears and approaches. Distant engine hum.
Shot 4 (9-12s): Slow dolly-in close-up on the woman's face, 85mm. She hears the car, lowers her hands, and her face slowly lights up with hope and relief, a small expectant smile, eyes shining.
Shot 5 (12-14s): Over-the-shoulder shot from behind the woman, 35mm, locked off. The silver sedan glides into frame and gently stops right beside her. Soft brake squeak.
Shot 6 (14-17s): Tight insert close-up on the sedan's driver window from outside, rice fields reflected in the glass. The window slowly rolls down with a power window whir, revealing the kind man with a worried, caring expression, leaning toward her.
Shot 7 (17-20s): Reverse shot, medium close-up of the man framed in the open window, 50mm, static. With sincere concern, soft eyebrows, and a gentle, warm, kind voice, he says in Japanese: "そこは駐車禁止ですよ!"
Shot 8 (20-24s): Close-up of the woman, static. Her hopeful smile freezes, one second of dead silence, her eye twitches, then a sudden crash zoom into her face as she explodes and shouts loudly in Kansai dialect Japanese: "わかっとるわぼけぇ!" Her voice echoes over the rice fields.
Shot 9 (24-27s): Medium shot of the man in the driver's seat through the open window, static. He blinks once with a blank puzzled face, then calmly rolls the window up while the car starts moving and pulls out of frame. Power window whir, engine starting.
Shot 10 (27-30s): Locked-off extreme wide shot, symmetrical composition, slowly craning up. The silver sedan calmly drives away down the long straight road into the distance, leaving the tiny figure of the woman standing alone with clenched fists next to her tilted car in the canal. Engine sound fades away, only cicadas remain. Deadpan comedic silence.
```

- 生成ジョブ(2026-10-05): `779ca46b-dd95-49c4-944c-42689e04f692`(seedance_2_5 / t2v / 30秒 / 480p / 16:9 / 音声あり / 90クレジット)

## 20秒版(Seedance 2.5 ドラフト)

- 生成ジョブ(2026-10-05): `710fc4c8-f2a9-4155-b610-057f30ffb7ec`(seedance_2_5 / t2v / 20秒 / 480p / draft: true / 16:9 / 音声あり / 60クレジット)
- 30秒版からの変更: 8カットに圧縮(「どうしよう…」は空撮に重ねる、停車と窓下げを1カットに)、事故車の屋根に何もない普通の軽自動車であることを明記(30秒版では屋根にパトランプ状のものが出てしまった)
- OKなら `draft_job_id` を指定して 1080p に仕上げる
