# ハゲの村 キャラクター設定・キャラクターシート用プロンプト

`character-sheet` ワークフロー(photoreal-unretouched プリセット)に沿って作成。
全員 AI 生成の架空の人物・成人。実在の人物に似せない。

## シートの構成

1枚の横長画像(16:9)に以下をまとめる。

- **左**: 顔のアップ(真正面、顔がはっきりわかる証明写真的な構図)
- **右**: 服を着た全身4方向(正面・左側面・右側面・背面)を横一列

## 生成設定

| 項目 | 値 |
|---|---|
| モデル | `gpt_image_2_5` |
| quality / resolution | `high` / `2k` |
| aspect_ratio | `16:9` |
| コスト | 1枚 2.75 クレジット × 10人 = 27.5 クレジット(無制限枠は対象外) |

## 共通プロンプト

`[CHARACTER]` に各キャラクターの記述を入れる。

```
Character reference sheet on a pure white seamless studio background, professional character sheet presentation. Left panel: a large tight close-up headshot of the character's face seen straight from the front, symmetrical frontal view like a passport photo, face fully visible and sharply in focus, neutral relaxed expression, eyes looking directly at the camera. Right panel: four full-body views of the identical original character standing upright in a row, evenly spaced — front view, left side profile, right side profile, and back view — each head-to-toe with both feet visible, not cropped, not sitting, arms relaxed at the sides, same outfit in every view. [CHARACTER] Visible fine skin texture with natural pores, fine lines, subtle asymmetries, slight natural sheen rather than glossy retouched finish, no digital smoothing, no beauty filter, no AI-airbrushed look, matte-to-natural complexion, eyes with naturally muted catchlights and no oversized specular glare. Natural anatomy, soft diffused studio lighting without harsh reflections, high-end but unretouched commercial photography style, cinematic realism, 4K quality, sharp focus on skin texture detail. Only this one character, no other people, no props, no furniture, no background objects, no text, no watermark, no logos, no frame borders, no extra fingers, no distorted anatomy. The character is original and does not resemble any real celebrity or real person.
```

## 女性(5名)

| # | 名前 | 年齢 | 設定 |
|---|---|---|---|
| W1 | さくら | 24 | 保育士。まっすぐで涙もろい。光の頭に一目で心を奪われる |
| W2 | ひなた | 23 | カフェ店員。明るいが芯が強い。毛利の不器用さに惹かれる |
| W3 | 美月(みつき) | 26 | 看護師。クールで落ち着いた大人の女性。剛の頭を「手術室の照明みたいに安心する」と言う |
| W4 | 玲奈(れいな) | 25 | アパレル販売員。おしゃれで素直。晴彦の頭を「季節を感じる」と言う |
| W5 | 梨花(りか) | 27 | 図書館司書。おっとり眼鏡女子。拓海の後退する生え際を「歴史」と呼ぶ |

### W1 さくら
```
A Japanese woman aged 24 with fair warm-toned skin, soft oval face with a gently defined jawline and mature adult bone structure (not a babyface), small straight nose, natural rosy-nude lips with a soft matte finish, warm dark-brown almond eyes, soft natural brows, chest-length light-brown hair with loose soft waves and a natural center parting, light natural makeup, slender body with balanced proportions. Wearing a cream-white chunky cable-knit sweater, light-blue straight-leg jeans, white canvas sneakers, a thin gold necklace with a tiny pendant, no bag.
```

### W2 ひなた
```
A Japanese woman aged 23 with light skin and a few faint freckles across her nose and cheeks, heart-shaped face with defined cheekbones and mature adult proportions (not a babyface), cheerful bright eyes in dark brown with naturally muted catchlights, straight brows, high ponytail of dark-brown hair with a few loose strands framing the face, natural coral lip tint, petite body with balanced proportions. Wearing a mustard-yellow knit cardigan over a white cotton T-shirt, a beige midi-length pleated skirt, white low-top sneakers with white socks, small silver hoop earrings, no bag.
```

### W3 美月
```
A Japanese woman aged 26 with neutral light skin, slim oval face with an elegant defined jawline and high cheekbones, mature adult features, calm narrow almond-shaped dark eyes, straight thin nose, natural mauve lips with a matte finish, straight sleek black hair falling to mid-back with a side parting, minimal natural makeup, tall slender body with balanced proportions. Wearing a charcoal-gray fine-knit turtleneck, a long camel wool coat open at the front, black slim tapered trousers, black leather ankle boots, a small silver watch, no bag.
```

### W4 玲奈
```
A Japanese woman aged 25 with fair pink-toned skin, oval face with defined cheekbones and mature adult proportions (not a babyface), lively dark-brown eyes with subtle brown eyeliner, softly arched brows, chin-length ash-brown bob haircut with a slight inward curl and see-through bangs, rosy-red matte lip tint, slender body with balanced proportions. Wearing a lavender oversized knit vest over a white collared blouse, a black satin midi skirt, black loafers with white socks, small pearl stud earrings, no bag.
```

### W5 梨花
```
A Japanese woman aged 27 with light warm-beige skin, round-oval face with soft but adult defined jaw and mature proportions, gentle dark-brown eyes behind thin round tortoiseshell glasses, soft brows, shoulder-length dark-brown hair with loose airy waves tucked behind one ear, natural peach lips, a small mole near her left eye, average build with balanced proportions. Wearing a sage-green long-sleeve knit dress reaching below the knees, a cream cotton cardigan, brown leather Mary Jane shoes, a thin gold bracelet, no bag.
```

## ハゲ男性(5名)

| # | 名前 | 年齢 | ハゲのタイプ | 設定 |
|---|---|---|---|---|
| M1 | 光(ひかる) | 32 | 完全スキンヘッド | 22歳で全部抜けた。10年間、人前で帽子を脱いだことがない |
| M2 | 毛利 進(もうり すすむ) | 45 | バーコード | 残り少ない髪(タケシ・ヒロシ・マサル…)を守り続ける。不器用で誠実 |
| M3 | 剛(ごう) | 38 | 剃り上げスキンヘッド+あごひげ | 消防士。筋肉質で無口。頭を「消防車より赤くなる」ほど照れ屋 |
| M4 | 晴彦(はるひこ) | 50 | 頭頂部ハゲ+サイドに白髪交じり | 和菓子職人。穏やかで包容力がある。頭頂部を「お月見」と呼んでいる |
| M5 | 拓海(たくみ) | 29 | M字の生え際後退 | ITエンジニア。まだ認めたくない。毎朝、生え際を写真で記録している |

### M1 光
```
A Japanese man aged 32 with light warm-toned skin, completely bald clean-shaven smooth scalp with no hair at all on the head (natural matte scalp with subtle skin texture), well-proportioned oval face with a defined jawline, kind gentle dark-brown eyes, thick natural dark eyebrows, light stubble on the chin and jaw, slim fit body with balanced proportions. Wearing a plain white crew-neck T-shirt, a medium-blue denim jacket, dark indigo straight jeans, white leather sneakers, no hat, no bag.
```

### M2 毛利
```
A Japanese man aged 45 with light olive skin, sturdy square face with a strong jaw and slight jowls, honest earnest dark eyes, thick dark eyebrows, severely thinning hair: a mostly bald scalp with a few long thin strands of black hair carefully combed over from one side across the top of the head in a neat comb-over, visible scalp between the strands, clean-shaven, broad stocky build with a slight belly. Wearing a red-and-navy checked flannel shirt tucked into beige chino pants, a brown leather belt, brown leather lace-up shoes, a simple steel wristwatch, no bag.
```

### M3 剛
```
A Japanese man aged 38 with tanned medium skin, completely shaved bald head with a natural matte scalp, rugged angular face with a strong square jaw, short well-groomed black full beard, intense but kind dark eyes, thick straight eyebrows, a small faint scar on the left eyebrow, very muscular broad-shouldered athletic build. Wearing a fitted dark-navy henley shirt with sleeves pushed up to the forearms, olive-green cargo work pants, black leather work boots, a black rubber sports watch, no hat, no bag.
```

### M4 晴彦
```
A Japanese man aged 50 with light warm skin and natural fine wrinkles, round friendly face with soft but adult features, gentle smiling dark eyes with crow's feet, salt-and-pepper eyebrows, crown-and-top balding: a completely bald round top of the head with short neatly trimmed salt-and-pepper gray hair remaining only on the sides and back in a horseshoe pattern, clean-shaven, average build with a slight middle-age softness. Wearing a navy-blue traditional Japanese samue work jacket and matching trousers, white tabi socks with dark wooden-soled setta sandals, nothing in the hands, no bag.
```

### M5 拓海
```
A Japanese man aged 29 with fair neutral skin, slim oval face with a defined jaw, thoughtful dark eyes behind thin black rectangular glasses, natural dark eyebrows, short black hair with a pronounced M-shaped receding hairline — deep bare temples on both sides with a small tuft remaining at the front center, slightly thin on top, clean-shaven, slim lanky build. Wearing a heather-gray hoodie over a white T-shirt, black slim jeans, gray running sneakers, a black smartwatch, no bag.
```

## 生成結果(2026-10-17、gpt_image_2_5 / high / 2k / 16:9)

| # | 名前 | job_id |
|---|---|---|
| W1 | さくら | 98d9e778-07bd-4d67-8b29-9a81e44d0a17 |
| W2 | ひなた | bec1f6ea-2269-4d84-ba6c-a98b4d97e398 |
| W3 | 美月 | 5334f596-9395-424e-9268-16dd5533eaac |
| W4 | 玲奈 | 94c0569a-2236-44f3-b519-829bdc7c48c1 |
| W5 | 梨花 | 5d0dcfe5-9d5d-48b5-8dc5-f3ae04544ee6 |
| M1 | 光 | 81ce7a7b-3acd-41fd-b8c9-b5702bebef27 |
| M2 | 毛利 | 3ed19639-06bc-4c7a-8e72-7e1a18b0f025 |
| M3 | 剛 | 3ddd46ab-ca5c-40ea-bc93-fcc0f185a085 |
| M4 | 晴彦 | dd804a87-1ffd-4918-9cb8-a67dd5fa9842 |
| M5 | 拓海 | cb446c3f-300c-4641-9b5d-ba0790fa93bf |
