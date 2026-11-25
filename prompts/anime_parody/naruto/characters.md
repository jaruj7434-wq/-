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

**完成形: kurama v10(ジョブID 34720423-db5e-4240-944a-eb0445ea184f)**

| 版 | モデル | 比率 | 消費 | ジョブID | メモ |
|---|---|---|---|---|---|
| kurama v1(幼少期・全身正面)【非公開・確認用】 | gpt_image_2_6(ナルト v5 参照) | 9:16 | 0.75 クレジット | 3fe3e862-01c1-4c55-b5b9-6fa49edf9e52 | 金色のチャクラの衣・黒い炎模様・首の勾玉・お腹の渦巻き・角のような髪・オレンジの目、いずれも出た。瞳孔は横長というより丸っこい |
| kurama v2(成人・ファスナー開け・全身金色)【非公開・確認用】 | gpt_image_2_6(kurama v1 参照) | 9:16 | 0.75 クレジット | 325e5c63-e3b0-478f-845f-2e44900a8052 | 20歳くらいの大人に。上着の前が開き、黒シャツにも渦巻きと炎模様。顔・肌・髪・額当てまで全部金色。目は金色寄りで瞳孔は横長になっていない。頬線は再び濃い線 |
| kurama v3(成人・眉細め・日本人顔・角張った頬線)【非公開・確認用】 | gpt_image_2_6(kurama v2 参照) | 9:16 | 0.75 クレジット | 1808c9e0-e257-43e6-a2fc-f9cad765e2cb | 眉が細く、切れ長の目の日本人顔に。頬線は太い長方形の角張った黒い線(かなり太め)。体・衣装はv2を維持 |
| kurama v4(額当ての紐を炎のように長く)【非公開・確認用】 | gpt_image_2_6(kurama v3 参照) | 9:16 | 0.75 クレジット | b0d39889-db06-498a-952c-b1f00668cb94 | 額当ての紐が金色の炎のように長く、頭上へ左右に大きくなびく。顔の右横に元の短い紐も少し残る |
| kurama v5(眉さらに細く・オレンジの目に十字の瞳孔・黒アイシャドウ)【非公開・確認用】 | gpt_image_2_6(kurama v4 参照) | 9:16 | 0.75 クレジット | 67c23762-0267-468b-b913-07d15cdfcd30 | オレンジの目に黒い十字の瞳孔、目の上に黒いアイシャドウ(目じりに跳ね上げ)が出た。眉はほぼ見えないほど細い。頬線は再び太め。右横の短い紐は残ったまま |
| kurama v6(白目は白・黒目だけオレンジ・十字を極小・アイシャドウ控えめ)【非公開・確認用】 | gpt_image_2_6(kurama v5 参照) | 9:16 | 0.75 クレジット | dcb79774-351f-41c6-a621-9b440d448a29 | 白目が白に戻り、黒目だけオレンジ。十字は細く小さくなった。アイシャドウは細い線程度に。ただし黒目が大きく、目を見開いたような印象に |
| kurama v7(目を自然な大きさに戻す)【非公開・確認用】 | gpt_image_2_6(kurama v6 + v3 参照) | 9:16 | 0.75 クレジット | 00273570-b376-4321-ad8a-6593ab67a9b7 | **ほぼ失敗**: 目は少し落ち着いたが黒目はまだ大きい。頬の線がにじんで崩れた(片側2本半に見える)。基準は v4〜v6 のまま |
| kurama v8(v4 の黒目をオレンジにするだけ)【非公開・確認用】 | gpt_image_2_6(kurama v4 参照) | 9:16 | 0.75 クレジット | 0363eb1e-8fa6-4a9a-9259-c676ad7cc520 | 目の大きさ・形はv4の自然なまま、黒目だけオレンジ。白目も自然。頬線もきれい |
| kurama v9(v8 の眉毛だけ細く)【非公開・確認用】 | gpt_image_2_6(kurama v8 参照) | 9:16 | 0.75 クレジット | aa7338da-8a21-4a4d-86d7-ef752f3b9957 | 眉が細く薄くなった。目・頬線・体はv8のまま |
| kurama v10(眉さらに細く・目の間隔を縮める・鼻の穴を目立たなく・小顔・目を少し大きく)【非公開・確認用】 | gpt_image_2_6(kurama v9 参照) | 9:16 | 0.75 クレジット | 34720423-db5e-4240-944a-eb0445ea184f | **変化がほとんど出なかった**。全身画像で顔が小さく、品質設定が既定の low のため細かい顔の編集が効きにくいと考えられる。ユーザー判断で **これを九喇嘛モード完成形とする** |

```
Using this photo as the character reference, keep the same boy: same face, same age, same spiky blond hair, same natural whisker marks on both cheeks, same headband with its engraved emblem, same front-facing full-body standing pose, same plain light gray studio background and framing. Transform him into Naruto's Nine-Tails Chakra Mode (Kurama mode) as a photorealistic live-action film VFX shot: his whole body is wrapped in a bright glowing golden-yellow chakra cloak like translucent flowing fire light, with black flame-shaped markings across his torso, arms and legs, a ring of black magatama-like marks around the collar and a black spiral mark on the stomach. His hair glows golden and two tufts stick up like small horns. His eyes are glowing orange with horizontal black pupils. Golden light softly illuminates his skin and the floor around him, faint sparks and heat haze in the air. Serious determined expression. Cinematic, realistic skin and fabric under the glow. No text.
```

kurama v2 プロンプト:

```
Use this photo as the style and costume reference for a NEW image. Keep: the Nine-Tails Chakra Mode look (bright glowing golden-yellow chakra cloak like translucent flowing fire light, black flame-shaped markings on torso, arms and legs, ring of black magatama marks around the collar, black spiral mark on the stomach), two hair tufts sticking up like horns, the front-facing full-body standing pose with arms relaxed at sides, plain light gray studio background, framing and cinematic VFX lighting. Change: make him a fictional ADULT Japanese man around 20 years old, taller, broader shoulders and a more mature, sharper adult face with a strong jawline (original face, not resembling any real actor), serious determined expression, glowing orange eyes with horizontal black pupils, three whisker marks on both cheeks. His jacket is UNZIPPED and open at the front, showing a fitted black shirt underneath that also glows with golden chakra. Make EVERYTHING on him golden: his entire face and skin glow bright golden-yellow chakra light, his hair is glowing gold, and the headband cloth and its metal plate are also fully glowing gold with the engraved emblem as a darker gold line. No text.
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

#### kurama v3 プロンプト(kurama v2 を参照して顔まわりのみ編集)

```
Edit this exact image. Keep everything else identical: the golden glowing Nine-Tails Chakra Mode cloak, the open jacket with black shirt and spiral mark, the black flame markings and magatama ring, the horn-like hair tufts, the golden headband with emblem, the golden glowing skin, the front-facing full-body pose, background, framing and lighting. Change ONLY his face: give him a clearly Japanese face of a man around 20 — noticeably thinner, finer and straighter eyebrows, single or subtle double eyelids with narrower almond-shaped East Asian eyes, a softer lower nose bridge, a slightly flatter and smoother face shape, typical of a Japanese actor in a live-action film (original face, not resembling any real person). Keep the serious determined expression. Also redraw the whisker marks: exactly three marks on EACH cheek, each mark a THICK, LONG, straight, hard-edged rectangular bar with square angular ends (not thin, not tapered, not curved), dark black, evenly spaced and parallel, symmetrical on both cheeks. No text.
```

#### kurama v4 プロンプト(kurama v3 を参照して額当ての紐のみ編集)

```
Edit this exact image. Keep everything else identical: his face, eyebrows, eyes, the thick rectangular whisker marks, the horn-like hair tufts, the golden glowing headband plate with emblem, the golden chakra cloak, open jacket, black shirt with spiral, flame markings, magatama ring, the front-facing full-body pose, background, framing and lighting. Change ONLY the headband tails (the tied cloth ends of the headband): make the two tails much LONGER, glowing golden like chakra flames, streaming and fluttering dramatically UPWARD and outward from behind his head like rising fire, as if blown by a powerful updraft of chakra, reaching well above the top of his hair, with flame-like wispy edges and soft sparks. No text.
```

#### kurama v5 プロンプト(kurama v4 を参照して目まわりのみ編集)

```
Edit this exact image. Keep everything else identical: his face shape, nose, mouth, the rectangular whisker marks, the horn-like hair tufts, the golden headband plate with emblem and the long flame-like headband tails rising upward, the golden chakra cloak, open jacket, black shirt with spiral, flame markings, magatama ring, the front-facing full-body pose, background, framing and lighting. Change ONLY the eye area: 1) make his eyebrows very thin, sharp and fine. 2) Make the irises vivid glowing orange, and inside each iris put a black cross-shaped pupil (a black plus-sign / cross pattern) clearly visible in both eyes. 3) Add dark black shading on the upper eyelids like heavy black eyeshadow, extending slightly outward toward the outer corners, giving a fierce beast-like look. Keep the serious determined expression. No text.
```

#### kurama v6 プロンプト(kurama v5 を参照して目のみ編集)

```
Edit this exact image. Keep everything else identical: his face shape, very thin eyebrows, nose, mouth, the rectangular whisker marks, the horn-like hair tufts, the golden headband plate with emblem and the long flame-like headband tails, the golden chakra cloak, open jacket, black shirt with spiral, flame markings, magatama ring, the front-facing full-body pose, background, framing and lighting. Change ONLY the eyes: 1) The whites of the eyes (sclera) must be clean natural WHITE, not orange or gold. Only the round iris is vivid glowing orange. 2) Inside each orange iris, the black cross-shaped pupil must be as SMALL as possible — a tiny thin black plus sign at the very center of the iris, much smaller than now. 3) Greatly reduce the black eyeshadow: only a thin, subtle dark line along the upper eyelid, with a very slight short flick at the outer corner, no large black wings. Keep the serious determined expression. No text.
```

- メモ: 目の編集を重ねるほど、頬の線など周りが崩れやすい(v7)。直すときは「目の形と大きさは一切変えず、色だけ変える」のように変更を最小にする方がよい。

#### kurama v8 プロンプト(kurama v4 を参照して黒目の色のみ変更)

```
Edit this exact image with the smallest possible change. Do NOT change the size, shape or openness of the eyes, irises or eyelids at all — keep the eyes exactly as they are now (natural, slightly narrow, calm, normal-sized irises). Keep everything else identical too: face, eyebrows, whisker marks, hair, golden headband and flame-like tails, golden chakra cloak, body, pose, background, lighting. Change ONLY the color of the irises to vivid orange, with a normal round black pupil in the center. The whites of the eyes stay natural white. No crosses, no extra makeup. No text.
```

#### kurama v9 プロンプト(kurama v8 を参照して眉毛のみ編集)

```
Edit this exact image with the smallest possible change. Change ONLY the eyebrows: make both eyebrows much thinner — narrow, fine, neatly shaped straight brows, about one third of their current thickness, same position and same length. Do NOT change the eyes at all (keep the same size, shape, openness and the orange irises with white sclera), and keep everything else identical: face, whisker marks, hair, golden headband and flame-like tails, golden chakra cloak, body, pose, background, lighting. No text.
```

- メモ: 「変える部位を1か所にしぼり、他は一切変えない」と書くと崩れにくい(v8・v9 で確認)。

- メモ: `gpt_image_2_6` の既定は quality: low / resolution: 1k。全身画像の小さな顔を細かく直すなら quality: high / resolution: 2k(1枚 2 クレジット)を検討する。

## ミナト風(穢土転生・九喇嘛モード)

- 24歳くらいの架空の日本人男性、長身で細身。穏やかで芯のある真剣な表情(実在の俳優には似せない)
- 頬の線なし。ツンツンの金髪で、長い前髪が顔の両側に垂れる
- 額当て: 木の葉マーク(非公開・確認用)
- 九喇嘛モード: 金色のチャクラの衣、黒い炎の模様、首の勾玉。その上に、裾に赤い炎模様が入った白いひざ丈の半袖羽織(前開き)
- 穢土転生: 白目が黒く、黒目はオレンジ。顔と手に灰色がかったひび割れ

### 生成記録

| 版 | モデル | 比率 | 消費 | ジョブID | メモ |
|---|---|---|---|---|---|
| v1(全身正面)【非公開・確認用】 | gpt_image_2_6(ナルト kurama v10 を画風の見本として参照) | 9:16 | 0.75 クレジット | 0972b9de-3a0c-4f28-b9de-1b561f5476e5 | 顔はナルトと別人に。長い前髪・炎の羽織・黒い白目にオレンジの瞳・頬と手のひび割れが出た。参照元から炎のような額当ての紐も引き継がれた |
| v2(顔と額当てを髪と同じ金色の炎色に)【非公開・確認用】 | gpt_image_2_6(ミナト v1 参照) | 9:16 | 0.75 クレジット | 9b2471ee-0c3a-40d1-9046-77e1d4e5c6cc | 顔全体と額当てが金色に。黒い白目・オレンジの瞳は維持。頬のひび割れは銀灰色の斑点としてかえって目立つ。手は元の肌色のまま |
| v3(胴の渦巻きを勾玉の輪のすぐ下へ、周りの模様を細い縦線に)【非公開・確認用】 | gpt_image_2_6(ミナト v2 参照) | 9:16 | 0.75 クレジット | e4ee91d3-b3f0-4de1-87d2-c007d1d8fe16 | 渦巻きが胸の上(勾玉の輪の直下)へ。下に細い黒の縦線3本。胴の太い炎模様は消えた。他はv2のまま |
| v4(両肩に渦巻き・前腕と羽織の胸の黒い線を消す・インナーを上下つなぎに)【非公開・確認用】 | gpt_image_2_6(ミナト v3 参照) | 9:16 | 0.75 クレジット | c2d1f62f-9d9b-40df-ad26-328fe96e7d0b | 両肩に渦巻きが入り、前腕と羽織の胸の黒い線は消えた。上下つなぎは不十分で、腰に上着の裾のような境目がまだ見える |
| v5(渦巻きの下を「Π」形の模様に・脚の炎模様を削除・腰の境目を消す)【非公開・確認用】 | gpt_image_2_6(ミナト v4 参照) | 9:16 | 0.75 クレジット | 6abeb498-5723-422b-a540-f9a1fab571ff | ユーザー提供の参考画像(フィギュア写真、アップロードはせず文章で指定)どおり、中央の縦線→横線→両太ももの前を下る線に。脚の炎模様も消え、腰の境目もほぼ目立たない |
| v6(サンダルと足を炎色に)【非公開・確認用】 | gpt_image_2_6(ミナト v5 参照) | 9:16 | 0.75 クレジット | 257a82d8-17f2-4a33-9af1-dd325102ffe2 | サンダルと足が金色の炎色に光るように。他はv5のまま。手は肌色のまま。**現時点のミナト基準** |

#### v1 プロンプト

```
Use this image ONLY as the style reference (photorealistic live-action VFX look, glowing golden chakra cloak, plain light gray studio background, front-facing full-body standing pose, framing and lighting). Create a DIFFERENT character: a fictional Japanese man around 24 years old, tall and slim, calm gentle but serious expression, original face (not resembling any real actor and not the same face as the reference), NO whisker marks. Hair: spiky bright blond hair with long bangs hanging down on both sides of his face, glowing gold. Headband with metal plate engraved with the Hidden Leaf Village symbol from the Naruto anime. He is in Nine-Tails Chakra Mode: his body is wrapped in a glowing golden-yellow chakra cloak like translucent flowing fire with black flame markings and a ring of black magatama marks around the collar, and over it he wears a white knee-length short-sleeved haori coat with red-orange flame patterns along the bottom hem, open at the front. He is reanimated by the Edo Tensei (Impure World Reincarnation) technique: the WHITES of his eyes are BLACK (black sclera) with glowing orange irises, and his face and hands have subtle gray-beige cracked patches like dry porcelain or ash, as if his body is made of crumbling dust, with a few tiny flakes drifting off. Faint sparks and heat haze. No text.
```

#### ミナト v2 プロンプト(v1 を参照して顔と額当ての色のみ変更)

```
Edit this exact image with the smallest possible change. Change ONLY the color of his face and his headband: make his entire face and skin, and the whole headband (both the cloth and the metal plate, with the engraved emblem kept as a darker gold line), glow in the same bright golden flame color as his hair, like the golden chakra light. Keep the black sclera with orange irises, the gray cracked patches on his cheeks, his facial features and expression, hair, flame-like headband tails, white haori with red flames, chakra cloak, hands, body, pose, background and lighting exactly the same. No text.
```

#### ミナト v3 プロンプト(v2 を参照して胴の模様のみ編集)

```
Edit this exact image. Change ONLY the black markings on the glowing golden chest and torso (the area visible between the open white haori): 1) move the black spiral mark UP so it sits on the upper chest, directly below the ring of black magatama marks around the collar; 2) replace the thick black flame-shaped markings that currently surround the spiral with a few THIN black lines that run straight downward from below the spiral toward the stomach, like thin vertical stripes. The rest of the torso is plain glowing gold. Keep everything else exactly the same: golden face and headband, black sclera with orange irises, cracks, hair, flame-like headband tails, magatama ring, white haori with red flames, the markings on the arms and legs, hands, pose, background and lighting. No text.
```

#### ミナト v4 プロンプト(v3 を参照して3か所を編集)

```
Edit this exact image. Make ONLY these three changes: 1) Add a black spiral mark on each shoulder (one on the left shoulder and one on the right shoulder), the same style as the spiral on his chest, clearly visible on the outer layer at the top of each shoulder. 2) Remove the black jagged lightning-like flame markings on the forearms of the glowing inner layer, and remove the black jagged lightning-like markings on both chest sides of the white haori coat, leaving those areas plain. 3) Make the glowing golden inner garment ONE continuous piece from chest to ankles, like a one-piece bodysuit/jumpsuit, with no waistband or visible separation between the top and the trousers. Keep everything else exactly the same: golden face and headband, black sclera with orange irises, cracks, hair, flame-like headband tails, magatama ring, chest spiral with the thin vertical lines below it, white haori with red flames at the hem, the leg markings, hands, pose, background and lighting. No text.
```

#### ミナト v5 プロンプト(v4 を参照して胴〜脚の模様を編集)

```
Edit this exact image. Change ONLY the black markings on the glowing golden one-piece inner suit below the chest spiral, and remove the waist seam: 1) Remove the three thin vertical lines under the chest spiral and remove ALL the black flame-shaped markings on the legs and trousers. 2) Draw this new pattern in solid dark black-navy lines of medium thickness: a single straight vertical line running down the center from just below the chest spiral to the lower stomach; there it meets a short horizontal line, forming an upside-down U (like the Greek letter Π); from both ends of that horizontal line, a line curves slightly outward and then runs straight down the front of each thigh to just above each knee. The rest of the suit is plain glowing gold. 3) The inner suit is one continuous piece from chest to ankles with no waistband, hem or seam at the waist. Keep everything else exactly the same: golden face and headband, black sclera with orange irises, cracks, hair, flame-like headband tails, magatama ring, chest spiral, shoulder spirals, white haori with red flames at the hem, hands, pose, background and lighting. No text.
```

#### ミナト v6 プロンプト(v5 を参照して足元の色のみ変更)

```
Edit this exact image with the smallest possible change. Change ONLY the sandals/shoes and his visible feet: make them glow in the same bright golden flame chakra color as the rest of his suit and hair, with soft golden glow. Keep everything else exactly the same: face, eyes, headband, hair, flame-like headband tails, magatama ring, spirals, the suit pattern, white haori with red flames, hands, pose, background and lighting. No text.
```
