# 冒頭:鐘を乱暴に鳴らす慶太(16:9・約8秒)— 案(未生成)

参考: 「中さんの鐘鳴らし」0:00–0:08 / 0:59–1:07(`docs/reference-opening-bell.md`)
参考動画で中年男性が鐘を全身で乱暴に連打する部分を、慶太に差し替える。セリフなし(鐘の音のみ)。

人物: 慶太(本人同意済みの登録 Element `f6c17cc9-ae3d-4123-a642-79d2882414bd`、キャラクターシート `38677a4b-ada6-43d0-889d-eb3407ec222f`)
服装: 慶太の通常衣装(白オックスフォードシャツ+ネイビーニット肩掛け、ベージュチノ、縁なし眼鏡)

## カット
| 秒 | 参考の画角 | 内容 |
|---|---|---|
| 0–4 | 引き・ややあおり・手持ち。左に苔むした石柱、上にピンクの鐘、背景は深い森 | 慶太が両腕でロープを全身で引き、鐘を狂ったように連打 |
| 4–8 | 下からあおる顔のアップ・ブレ | 真剣な顔で鐘を見上げ、腕を振り回す。フサフサの髪が激しく揺れる |

## 開始画像(gpt_image_2 / high / 2k / 16:9、各 6.5 クレジット)

### 1. 引き
```
Cinematic 16:9 widescreen still from a Japanese romance reality-show documentary, handheld film look. Lush deep green forest in bright overcast daylight. On the LEFT edge of frame a tall mossy gray stone pillar covered with ivy; from a wooden beam at the top of frame hangs a large pink metal bell with a thin white rope. Slightly low camera angle, medium-wide shot. Below the bell, <<<f6c17cc9-ae3d-4123-a642-79d2882414bd>>>, the Japanese man with voluminous black center-parted hair and rimless glasses, white oxford shirt with a navy knit sweater draped over his shoulders, beige chinos, yanks the rope down hard with one raised arm, the other fist clenched, whole body twisting, intensely serious face looking up at the bell, hair flying. Slight motion blur on his arm, the bell swinging. Natural documentary color grade, natural skin texture. Only this one person, no text, no logos, no watermark.
```

### 2. あおりのアップ
```
Cinematic 16:9 widescreen still from a Japanese romance reality-show documentary, handheld film look. Extreme low-angle close-up from below and in front: <<<f6c17cc9-ae3d-4123-a642-79d2882414bd>>>, the Japanese man with voluminous black center-parted hair and rimless glasses, white oxford shirt with a navy knit sweater draped over his shoulders, glares upward at an unseen bell with a deadly serious, determined face, jaw clenched, one arm raised high pulling a rope, his thick hair whipping wildly, strong motion blur on his raised arm and the edge of the frame. Background: dense green forest leaves, bright overcast daylight. Natural documentary color grade, natural skin texture. Only this one person, no text, no logos, no watermark.
```

## 動画(seedance_2_5 / omni_reference / 4秒×2本 / 16:9 / 720p / 音声あり、各 28 クレジット)
image_references: 慶太のキャラクターシート `38677a4b-…`

### 1. 引き(start_image = 開始画像1)
```
Cinematic Japanese romance reality-show documentary, 16:9 widescreen, 4 seconds, single continuous handheld shot. Keep his face, hair and outfit exactly as in the reference image; only this one person. Continue from the first frame: in a lush green forest beside a mossy stone pillar, KEITA (voluminous black center-parted hair, rimless glasses, white oxford shirt, navy knit over his shoulders) frantically rings the large pink bell above him, yanking the white rope down again and again with his whole body like an engine that has just started, arms flailing, hair flying, face deadly serious. The bell swings wildly. Shaky handheld camera following the motion. Natural daylight, documentary realism, no text. Audio: rapid, loud, continuous bell clanging, forest birds. No dialogue.
```

### 2. あおりのアップ(start_image = 開始画像2)
```
Cinematic Japanese romance reality-show documentary, 16:9 widescreen, 4 seconds, single continuous handheld shot. Keep his face, hair and outfit exactly as in the reference image; only this one person. Continue from the first frame: extreme low-angle close-up of KEITA glaring up at the bell with a deadly serious face while violently pulling the rope over and over, his arm swinging in and out of frame with heavy motion blur, his thick hair whipping back and forth. The camera shakes with each pull. Forest leaves behind, bright overcast daylight, documentary realism, no text. Audio: rapid, loud, continuous bell clanging. No dialogue.
```

## コスト(プレフライト確認済み)
開始画像 6.5×2 = 13 + 動画 28×2 = 56 → **合計 約69 クレジット**

## 生成記録(2026-10-20)

- 方針変更: 動画は 4 秒 1 本のみ(28 クレジット)
- 開始画像1(引き): `2efd6ac0-c806-455f-bbb5-f3655d8aad1c` 完成
- 開始画像2(あおりのアップ): `28868c53-fd75-4b7c-9fe8-4260e03be740` は安全フィルター(nsfw 判定)で失敗。誤判定とみられる
- 動画(4秒・720p・28 クレジット): `01770d12-6b2c-4b12-805a-e2512834d7d3`
  - start_image = 開始画像1。image_references = 慶太の登録写真(Element 元画像 `9e6a89ba-8fd6-4530-b720-06e29d9e7a3a`)+キャラクターシート `38677a4b-…`
  - 顔崩れ・別人化を防ぐため、プロンプト冒頭に IDENTITY LOCK(同一人物・顔はブラさない)を追加
  - → 生成失敗(理由の表示なし)。28 クレジットは返金済み。あおりのアップ画像の 6.5 クレジットも返金済み
  - 推定原因: 慶太の実写の登録写真(`9e6a89ba-…`)を Seedance に直接渡したため、実在人物の顔チェックで弾かれた可能性
- 再生成(B: 同設定のまま再送、ユーザー指定): `b707bf0e-2f76-41e0-b249-44603dc4db47`

## 開始画像の作り直し(2026-10-20、ユーザー指摘: 開始画像の時点で慶太の顔からかけ離れている)

- 慶太の登録写真(`9e6a89ba-…`)を参照画像として直接渡し、Element と併用
- 顔の特徴(卵型の輪郭、センターパートで前髪を両側に流した濃い茶髪、縁なしの四角い眼鏡、銀のテンプルと鼻パッド)をプロンプトで明記
- 顔を大きく、正面寄り(3/4)、ピントを合わせ、ブレなしに変更
- job_id: `e23d230f-bee2-4ee1-a4c5-5b3b39c2219f`(6.5 クレジット)
- 再生成 B `b707bf0e-…` は完成(28 クレジット)。ただし旧開始画像(顔が慶太とかけ離れている)から作ったため不採用候補
- 新しい開始画像 `e23d230f-…` 完成
