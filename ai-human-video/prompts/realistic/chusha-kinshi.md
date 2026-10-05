# 「そこは駐車禁止ですよ!」— 絵コンテ & プロンプト

- ジャンル: リアル実写風コメディ(ショートコント)
- 尺: 約27秒 / 8カット
- アスペクト比: 16:9(シネマ。SNS用に 9:16 版も可)
- ルック: 35mmフィルム、アナモルフィックレンズ、粒子感、やや褪せた色(曇りの夕方)、浅い被写界深度
- 制作方法:
  1. 各カットの「最初のコマ」を静止画で生成(`gpt_image_2_5`)。
     カット1を基準画像にして、以降のカットはこれを参照し、人物・車・場所をそろえる。
  2. 静止画を `kling3_0`(mode: pro、sound: on)で動画化(image-to-video)。
  3. 8カットをつないで1本にする(video-montage)。

## 共通設定(全プロンプトに含める)

```
Shot on 35mm film, anamorphic lens, natural film grain, slightly faded warm color grade,
overcast late afternoon light, shallow depth of field, photorealistic, Japanese rural road
alongside a narrow concrete irrigation canal (about 1.5 m wide) next to rice fields, utility poles.
```

## 登場人物・小道具

- **おばさん**: 60代前半の日本人女性。パーマの短い髪、ベージュのカーディガン、
  花柄のエプロン、サンダル。関西〜西日本の下町のおばちゃん風。
- **おじさん**: 60代後半の日本人男性。白髪混じりの短髪、柔らかい笑顔、
  薄いブルーのポロシャツ。仏のように優しい雰囲気。
- **事故車**: 白い軽自動車(箱型の軽ワゴン)。前輪が用水路に落ち、車体が斜めに傾いている。
  ハザードランプ点滅。
- **おじさんの車**: シルバーの古いセダン。

## カット割り

| # | 尺 | 画角・カメラ | 内容 | 音 |
|---|---|---|---|---|
| 1 | 4秒 | 超ロング / ドローン俯瞰、ゆっくり前進 | 田んぼ沿いの道。白い軽が用水路に斜めに突っ込んでいる。横におばさん | 虫の声、風、ハザードのカチカチ |
| 2 | 3秒 | ミディアム / 手持ち、わずかに揺れ | おばさんが頭を抱えて車を見つめる。「どうしよう…」と小声 | ため息、つぶやき |
| 3 | 4秒 | 望遠・道路の低い位置から / 固定 | 奥からシルバーのセダンが走ってきて、おばさんの横でスッと止まる | エンジン音、ブレーキ |
| 4 | 3秒 | 運転席の窓のクローズアップ / 固定 | 窓がゆっくり下がり、優しい笑顔のおじさんが現れる | パワーウィンドウの音 |
| 5 | 4秒 | おじさんのバストショット(おばさんの肩なめ) | 仏の笑顔で「そこは駐車禁止ですよ!」 | セリフ(穏やか) |
| 6 | 2秒 | おばさんの顔アップ / 固定 | 固まる。目が据わる、口元がピクッ(間) | 無音に近い、カラスが一声 |
| 7 | 3秒 | おばさんの顔アップ / 一気にズームイン | 「わかっとるわぼけぇ!」と大声でキレる | 怒鳴り声 |
| 8 | 4秒 | 引きのワイド / 固定 | 笑顔のまま固まるおじさん。窓が静かに上がる。傾いた軽、田んぼ、夕方の空 | 虫の声だけが戻る |

## 静止画プロンプト(最初のコマ)

1. `Extreme wide high-angle drone shot. A white Japanese kei box car has crashed nose-first into the narrow irrigation canal beside the road, tilted diagonally, front wheels in the canal, rear wheels lifted, hazard lights on. A Japanese woman in her early 60s (short permed hair, beige cardigan, floral apron, sandals) stands next to the car holding her head with both hands.` + 共通設定
2. `Medium shot, handheld. The same woman stands beside the tilted white kei car, holding her head with both hands, worried and exasperated expression, looking at the car.` + 共通設定
3. `Low-angle telephoto shot from road level. In the far background, an old silver sedan approaches along the rural road; in the foreground the tilted white kei car in the canal and the woman.` + 共通設定
4. `Close-up of the driver's side window of an old silver sedan, window closed, reflection of rice fields, a kind-looking Japanese man in his late 60s (short graying hair, soft smile, light blue polo shirt) visible behind the glass.` + 共通設定
5. `Medium close-up over the woman's shoulder. The kind man sits in the driver's seat with the window fully down, gentle Buddha-like smile, looking at her.` + 共通設定
6. `Close-up of the woman's face, frozen, eyes narrowing, mouth corner twitching with suppressed anger.` + 共通設定
7. `Close-up of the woman's face, furious, mouth wide open shouting, veins on forehead.` + 共通設定
8. `Wide static shot. The silver sedan stopped next to the tilted white kei car in the canal, the man still smiling stiffly in the driver's seat, the woman standing with fists clenched, dusk sky over the rice fields.` + 共通設定

## 動画プロンプト(kling3_0)

1. `Slow drone push-in toward the crashed car. Hazard lights blink. Cicadas and wind ambience. No dialogue.`
2. `The woman sighs, shakes her head slowly while holding it, and mutters quietly in Japanese: "どうしよう…". Subtle handheld camera sway.`
3. `The silver sedan drives toward the camera and gently stops right beside the woman. Engine sound, soft brake squeak. Static camera.`
4. `The driver's window slowly rolls down, revealing the kind man smiling warmly. Power window motor sound.`
5. `The man smiles gently and says kindly in Japanese, calm polite voice: "そこは駐車禁止ですよ!" Static camera.`
6. `The woman freezes, her eye twitches, a long awkward silence. A single crow caws in the distance.`
7. `Fast zoom-in. The woman explodes with anger and shouts loudly in Kansai dialect: "わかっとるわぼけぇ!" Her voice echoes over the rice fields.`
8. `Static wide shot. The man keeps his frozen smile, then the car window slowly rolls back up. Only cicadas remain. Comedic silence.`
