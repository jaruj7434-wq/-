# ナルト風 実写化パロディ — キャラクター設定

## 主人公(ナルト風の忍者青年)

- 幼少期版: 12歳くらいの架空の日本人の男の子(実在の俳優・子役には似せない)※v2以降の基準
- 青年版: 18歳くらい(v1)
- ツンツンの明るい金髪、両頬に3本ずつのヒゲ風フェイスペイント
- 少し着古したオレンジと黒のジャージ風の忍者服
- 紺色の布の額当て。紋章は「箸入りラーメンどんぶり」(公式の木の葉マーク・渦巻きは使わない)
  - 渦巻きと指定すると公式マークに寄ってしまうため、v2 からどんぶりに変更

### 生成記録

| 版 | モデル | 比率 | 消費 | ジョブID | メモ |
|---|---|---|---|---|---|
| v1 | gpt_image_2_6 | 9:16 | 0.75 クレジット | 312e5960-df37-4432-b1ad-e28746af33f6 | 雰囲気は良い。ただし額当ての紋章が公式マークに近く、ヒゲ線が片頬にしか出ていない → 要修正 |
| v2(幼少期・全身正面) | gpt_image_2_6 | 9:16 | 0.75 クレジット | 7e8b0bb0-7236-4eb8-ac01-cacea04fb696 | 全身・正面・グレー背景。両頬にヒゲ線、ラーメン紋章もOK。紋章がラーメンなので差し替え |
| v3(v2の紋章のみ編集) | gpt_image_2_6(v2参照) | 9:16 | 0.75 クレジット | 957dcbb8-d016-4d5c-97ba-f4057545d575 | 顔・服・ポーズはv2を維持。紋章がカナダ国旗風のもみじになった → 葉の形を再検討中 |
| v4(v3の紋章のみ編集)【非公開・確認用】 | gpt_image_2_6(v3参照) | 9:16 | 0.75 クレジット | 7ac3e63e-2ec7-4022-bb22-eeca14f92936 | ユーザー指示で公式の木の葉マークに。CLAUDE.md の例外として**公開動画には使わない** |
| v5(v4の頬線のみ編集)【非公開・確認用】 | gpt_image_2_6(v4参照) | 9:16 | 0.75 クレジット | 91102967-3356-492a-8446-aa8ed1c64ff3 | 頬線を黒ペン風→赤茶の肌なじみ線に。ペン感は減ったが、やや引っかき傷っぽさが残る |

#### v1 プロンプト

```
Photorealistic live-action film still, vertical 9:16. A fictional Japanese young man around 18, original face (not resembling any real actor), spiky messy bright blond hair, three faint thin whisker-like face-paint lines on each cheek, wearing a slightly worn bright orange and black zip-up tracksuit-style ninja outfit, a dark blue cloth forehead protector with a small metal plate engraved with an original spiral-swirl emblem. Confident grin, thumb pointing at himself. Standing on an ordinary Japanese suburban street in the morning, cinematic natural lighting, shallow depth of field, 35mm film look, realistic skin texture. No text, no logos.
```

#### v2 プロンプト(幼少期・全身正面)

```
Photorealistic live-action character reference photo, vertical 9:16, full body shot from head to shoes, subject standing straight and facing the camera directly (front view), arms relaxed at sides, centered in frame. A fictional Japanese boy around 12 years old, original face (not resembling any real actor), spiky messy bright blond hair, exactly three thin whisker-like face-paint lines drawn on BOTH cheeks (left and right, symmetrical). Wearing a slightly oversized bright orange and black zip-up tracksuit-style ninja outfit with matching orange pants, dark blue sandals-style shoes. Dark blue cloth headband with a small plain metal plate engraved with a simple cartoon ramen bowl emblem (a bowl with chopsticks), clearly a ramen bowl, no leaf shape, no spiral. Mischievous confident grin. Plain light gray seamless studio background, soft even studio lighting, sharp focus, realistic skin and fabric texture. No text, no logos.
```

#### v3 プロンプト(v2 を参照画像にして紋章のみ編集)

```
Edit this exact photo. Keep everything identical: the same boy, same face, same expression, same blond hair, same whisker lines on both cheeks, same orange and black outfit, same pants, pouch and leg band, same sandals, same front-facing full-body pose, same plain light gray studio background, same lighting and framing. Change ONLY the engraving on the metal plate of the dark blue headband: remove the ramen bowl and replace it with a simple engraved outline of a single plain maple-style leaf with pointed lobes and a short stem, drawn as clean engraved lines. The leaf must NOT contain any spiral or swirl and must not be a rounded teardrop leaf shape. No text, no logos.
```

- メモ: "maple-style leaf" と指定するとカナダ国旗のもみじになりやすい。

#### v4 プロンプト(v3 を参照画像にして紋章のみ編集・非公開確認用)

```
Edit this exact photo. Keep everything identical: the same boy, same face, same expression, same blond hair, same whisker lines on both cheeks, same orange and black outfit, same pants, pouch and leg band, same sandals, same front-facing full-body pose, same plain light gray studio background, same lighting and framing. Change ONLY the engraving on the metal plate of the dark blue headband: replace the maple leaf with the Hidden Leaf Village symbol from the Naruto anime (a stylized leaf outline with a spiral swirl inside and a small triangular point at the top), cleanly engraved into the metal. No text.
```

#### v5 プロンプト(v4 を参照画像にして頬線のみ編集・非公開確認用)

```
Edit this exact photo. Keep everything identical: the same boy, same face shape, same expression, same blond hair, same headband and its engraved emblem, same orange and black outfit, same pants, pouch and leg band, same sandals, same front-facing full-body pose, same plain light gray studio background, same lighting and framing. Change ONLY the three lines on each cheek: they currently look like black pen or marker drawings. Make them look like natural, realistic skin marks instead — three soft, thin, slightly darker brownish-pink birthmark-like lines on each cheek, blended into the skin with realistic skin texture and pores visible through them, subtle and not glossy, slightly irregular edges, symmetrical on both cheeks. No ink, no drawn look. No text.
```

### 九喇嘛モード(変身形態)

| 版 | モデル | 比率 | 消費 | ジョブID | メモ |
|---|---|---|---|---|---|
| kurama v1(幼少期・全身正面)【非公開・確認用】 | gpt_image_2_6(ナルト v5 参照) | 9:16 | 0.75 クレジット | 3fe3e862-01c1-4c55-b5b9-6fa49edf9e52 | 金色のチャクラの衣・黒い炎模様・首の勾玉・お腹の渦巻き・角のような髪・オレンジの目、いずれも出た。瞳孔は横長というより丸っこい |

```
Using this photo as the character reference, keep the same boy: same face, same age, same spiky blond hair, same natural whisker marks on both cheeks, same headband with its engraved emblem, same front-facing full-body standing pose, same plain light gray studio background and framing. Transform him into Naruto's Nine-Tails Chakra Mode (Kurama mode) as a photorealistic live-action film VFX shot: his whole body is wrapped in a bright glowing golden-yellow chakra cloak like translucent flowing fire light, with black flame-shaped markings across his torso, arms and legs, a ring of black magatama-like marks around the collar and a black spiral mark on the stomach. His hair glows golden and two tufts stick up like small horns. His eyes are glowing orange with horizontal black pupils. Golden light softly illuminates his skin and the floor around him, faint sparks and heat haze in the air. Serious determined expression. Cinematic, realistic skin and fabric under the glow. No text.
```

## サスケ風の忍者少年(幼少期)

- 12歳くらいの架空の日本人の男の子(実在の俳優・子役には似せない)
- クールで真面目な表情、黒い瞳
- ツヤのある黒髪。後ろがツンツンと立ち、長めの前髪が顔の両側にかかる
- 紺色のハイカラー半袖シャツ、白いひざ丈ショートパンツ、グレーのアームウォーマー
- 右太ももに黒い忍具ポーチ(白い包帯巻き)、紺色の忍者サンダル
- 額当て: 木の葉マーク(ナルト v5 にそろえた非公開・確認用)

### 生成記録

| 版 | モデル | 比率 | 消費 | ジョブID | メモ |
|---|---|---|---|---|---|
| v1(幼少期・全身正面)【非公開・確認用】 | gpt_image_2_6 | 9:16 | 0.75 クレジット | d45cf7c0-e5e0-4c4a-8e4c-3bb3cfb5cb98 | 指定どおりの全身正面。ナルト v5 と同じ形式で並べられる |

#### v1 プロンプト

```
Photorealistic live-action character reference photo, vertical 9:16, full body shot from head to shoes, subject standing straight and facing the camera directly (front view), arms relaxed at sides, centered in frame. A fictional Japanese boy around 12 years old, original face (not resembling any real actor), cool calm serious expression with a slight frown, dark eyes. Natural glossy black hair, spiky and sticking up at the back, with long bangs framing both sides of his face. Wearing a dark navy blue short-sleeved shirt with a high wide collar, white knee-length shorts, light gray arm warmers on both forearms, a black ninja tool pouch strapped to his right thigh with white bandage wrap, dark blue open-toe ninja sandals. Dark blue cloth headband with a metal plate engraved with the Hidden Leaf Village symbol from the Naruto anime (a stylized leaf outline with a spiral swirl inside and a small triangular point at the top). Plain light gray seamless studio background, soft even studio lighting, sharp focus, realistic skin and fabric texture, looks like a real child actor in a live-action film costume. No text.
```

## サクラ風の忍者少女(幼少期)

- 12歳くらいの架空の日本人の女の子(実在の俳優・子役には似せない)
- 明るく元気な笑顔、緑の瞳、少し広めのおでこ
- 肩より長いストレートのパステルピンクの髪、前髪は左右に分ける
- 赤いノースリーブのハイカラー・チャイナ風トップス(白い丸の模様、えりにファスナー)、濃い緑のひざ丈ショートパンツ
- 右太ももに黒い忍具ポーチ(白い包帯巻き)、紺色の忍者サンダル
- 額当て: 頭の上にカチューシャのように着ける。木の葉マーク(非公開・確認用)

### 生成記録

| 版 | モデル | 比率 | 消費 | ジョブID | メモ |
|---|---|---|---|---|---|
| v1(幼少期・全身正面)【非公開・確認用】 | gpt_image_2_6 | 9:16 | 0.75 クレジット | 214133fb-c10e-45ba-903d-c5297db4d8db | 衣装・髪・額当ては指定どおり。顔立ちがやや欧米系寄り(そばかすあり)で、日本人らしさが弱い |
| v2(v1の顔のみ編集)【非公開・確認用】 | gpt_image_2_6(v1参照) | 9:16 | 0.75 クレジット | 23b9f972-b275-4b85-81e5-f0573ab907cc | **失敗**: 顔がほぼ変わらず、欧米系の顔立ちとそばかすが残った。参照編集では顔の大きな変更が効きにくい |

#### v1 プロンプト

```
Photorealistic live-action character reference photo, vertical 9:16, full body shot from head to shoes, subject standing straight and facing the camera directly (front view), arms relaxed at sides, centered in frame. A fictional Japanese girl around 12 years old, original face (not resembling any real actor), bright cheerful confident smile, green eyes, a slightly wide forehead. Natural-looking straight long pastel pink hair reaching past her shoulders, with bangs parted to the sides. Wearing a red sleeveless high-collar qipao-style top with a white circle emblem on the front and a zipper at the collar, dark green knee-length shorts underneath, a black ninja tool pouch strapped to her right thigh with white bandage wrap, dark blue open-toe ninja sandals. The dark blue cloth headband is worn on top of her head like a hairband, with a metal plate engraved with the Hidden Leaf Village symbol from the Naruto anime (a stylized leaf outline with a spiral swirl inside and a small triangular point at the top). Plain light gray seamless studio background, soft even studio lighting, sharp focus, realistic skin, hair and fabric texture, looks like a real child actor in a live-action film costume. Age-appropriate modest costume. No text.
```

- メモ: 参照画像を使った編集では、顔立ちを大きく変える指示がほとんど反映されなかった(v2)。顔を変えたいときは参照なしで新規生成する方がよい。

## カカシ風の忍者先生

- 26歳くらいの架空の日本人男性、長身で細身(実在の俳優には似せない)
- 片側に流れて逆立った銀白色のツンツン頭
- 紺色の布マスクで鼻から下を覆う。額当てを斜めに着けて左目を隠し、見えている右目は眠たげ
- 紺色の長袖シャツ、オリーブ色のベスト、紺色のズボン、右すねに白い包帯、右太ももに忍具ポーチ
- 金属プレート付きの指なしグローブ、紺色の忍者サンダル
- 無地のオレンジ色の文庫本を片手で読む(原作の小説タイトルは入れない)
- 額当て: 木の葉マーク(非公開・確認用)

### 生成記録

| 版 | モデル | 比率 | 消費 | ジョブID | メモ |
|---|---|---|---|---|---|
| v1(全身正面・本を読むポーズ)【非公開・確認用】 | gpt_image_2_6 | 9:16 | 0.75 クレジット | 0d430021-d3b7-40c9-9e8a-d509b8eb42c0 | ほぼ指定どおり。両肩に赤い渦巻きワッペン、グローブにも木の葉マークが自動で付いた |

#### v1 プロンプト

```
Photorealistic live-action character reference photo, vertical 9:16, full body shot from head to shoes, subject standing straight and facing the camera directly (front view), centered in frame. A fictional Japanese man around 26 years old, tall and slim, original face (not resembling any real actor), East Asian Japanese features. Natural-looking spiky silver-white hair swept up and slanting to one side. A dark navy fabric face mask covering his nose, mouth and chin up to just under the eyes. Dark blue cloth headband with a metal plate engraved with the Hidden Leaf Village symbol from the Naruto anime (a stylized leaf outline with a spiral swirl inside and a small triangular point at the top), worn tilted so it covers his left eye; his visible right eye looks relaxed, sleepy and bored. Wearing a dark navy long-sleeved shirt, an olive green padded tactical flak vest with front pockets, dark navy trousers with white bandage wrap at the lower right leg and a black tool pouch on the right thigh, fingerless dark gloves with metal plates on the backs, dark blue open-toe ninja sandals. Holding a small plain orange paperback book open in one hand at chest height, the other hand in his pocket. Plain light gray seamless studio background, soft even studio lighting, sharp focus, realistic skin, hair and fabric texture, like a Japanese live-action film costume photo. No text.
```
