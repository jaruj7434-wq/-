# 共同生活シーン(16:9・テンポ重視・約8秒)

参考動画 0:23–0:33 の画角・カット割りを再現し、作業シーンをハゲネタに置き換え。

| 秒 | カット | 参考動画の画角 | 人物 | セリフ |
|---|---|---|---|---|
| 0–2 | 木の門を押し開ける | ローアングルの引き。門が画面左〜中央、女性たちは下中央で後ろ姿・横向き。右に木と赤い納屋 | さくら・ひなた・玲奈・梨花 | 「せーの!」 |
| 2–4 | 乾杯 | テーブル高さの手持ちミドル。キッチンの島を囲み身を乗り出す | 光・毛利・拓海(手前)、さくら・ひなた・玲奈(奥) | 「かんぱーい!」 |
| 4–6 | A1 頭を磨く(元:木を切る) | 木のテラスの下のミドルアップ。左に柱、背景に草原と白い柵 | 美月・剛 | 美月「…ピカピカ!」 |
| 6–8 | B2 姿見を運ぶ(元:テーブル運び) | やや俯瞰のミドル。明るい木の床の部屋 | 晴彦・拓海・玲奈・梨花 | 「えっほ、えっほ、えっほ」 |

A1(美月・剛)と B2(晴彦・拓海・玲奈・梨花)は人物が重ならない。

## 開始画像(gpt_image_2 / high / 2k / 16:9、2026-10-19)

| カット | job_id |
|---|---|
| 門 | `79bfabfa-73e6-41ed-8379-9193c8395c82` |
| 乾杯 | `9d84ae47-b75e-40f5-9d62-cf268e373b38` |
| A1 頭を磨く | `98e99029-6596-4c34-8799-6fd8c0920b02` |
| B2 姿見を運ぶ | `818c5b2f-de91-48bd-8c80-e2af6d219d03` |

## 動画プロンプト(各4秒・編集で約2秒に切り詰め)

共通設定: `seedance_2_5` / omni_reference / 4秒 / 16:9 / 720p / 音声あり。各 28 クレジット × 4 = 112 クレジット

### 1. 門(start_image `79bfabfa-…`、参照: さくら・ひなた・玲奈・梨花のシート)
```
Cinematic Japanese romance reality-show documentary, 16:9 widescreen, 4 seconds, single continuous shot. Continue from the first frame: low-angle wide shot of four young Japanese women pushing open a massive rustic wooden village gate with carved animal silhouettes on the arch, under a vivid blue sky, red barn on the right. Keep faces and outfits as in the reference images. They shout together cheerfully in Japanese: 「せーの!」 and the heavy gate doors swing open as they lean into them. Bright sunlight, natural documentary realism, no other people, no text. Audio: the women's shout, creaking wooden gate, upbeat acoustic guitar music starting.
```

### 2. 乾杯(start_image `9d84ae47-…`、参照: 光・毛利・拓海・さくら・ひなた・玲奈のシート)
```
Cinematic Japanese romance reality-show documentary, 16:9 widescreen, 4 seconds, single continuous handheld shot. Continue from the first frame: in a rustic farmhouse kitchen with green cabinets, six people lean over a wooden kitchen island and clink their glasses together in the center, laughing. The three bald men in the foreground and three young women facing the camera keep their faces and outfits as in the reference images; each person appears only once. They all shout together in Japanese: 「かんぱーい!」 Sunlight from the windows glints on the men's scalps. Natural documentary realism, no other people, no text. Audio: everyone's cheer, clinking glasses, laughter, upbeat acoustic guitar music.
```

### 3. A1 頭を磨く(start_image `98e99029-…`、参照: 美月・剛のシート)
```
Cinematic Japanese romance reality-show documentary, 16:9 widescreen, 4 seconds, single continuous medium close-up. Continue from the first frame: under a rustic wooden patio, GOU (muscular bald Japanese man with a short black beard, navy henley, purple work gloves) bends over a wooden workbench with his shaved head lowered, and MITSUKI (young woman with long straight black hair, red work gloves) carefully polishes the top of his bald head with a soft cloth in circular motions, like polishing wood. Keep faces and outfits as in the reference images. She leans in to check the shine, sees her reflection, and says brightly in Japanese: 「…ピカピカ!」 They both burst out laughing. Natural daylight, green field and white fence in the background, documentary realism, only these two people, no text. Audio: soft rubbing sound, her line, their laughter, upbeat acoustic guitar music.
```

### 4. B2 姿見を運ぶ(start_image `818c5b2f-…`、参照: 晴彦・拓海・玲奈・梨花のシート)
```
Cinematic Japanese romance reality-show documentary, 16:9 widescreen, 4 seconds, single continuous slightly high-angle medium shot. Continue from the first frame: in a bright farmhouse room with light wooden floors, HARUHIKO (bald crown, gray hair on the sides, navy samue), TAKUMI (M-shaped receding hairline, glasses, gray hoodie), REINA (ash-brown bob, lavender knit vest) and RIKA (round glasses, sage-green knit dress) carry a very large full-length mirror in a wooden frame together, walking in step and chanting in rhythm in Japanese: 「えっほ、えっほ、えっほ」 Keep faces and outfits as in the reference images; each person appears only once. Focused but happy, documentary realism, no other people, no text. Audio: their rhythmic chant, footsteps on wooden floor, upbeat acoustic guitar music.
```

## 生成記録(2026-10-19、各 720p・16:9・4秒、合計 112 クレジット)

| カット | job_id |
|---|---|
| 門 | `61778987-d791-456b-9e78-3d309abb837d` |
| 乾杯 | `2be5aed7-5242-4ec5-afdb-633c022e77da` |
| A1 頭を磨く | `aa45f2d4-0327-4538-bd6a-ce662c254042` |
| B2 姿見を運ぶ | `7993407d-a768-4120-845c-532f96101220` |
