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

**完成形: 三面図 v4(ジョブID 3b791203-ebfc-4090-a63e-1a4e5bc5ce92、長コート版)/ 正面単体の完成形は kurama v10(34720423-db5e-4240-944a-eb0445ea184f)**

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
| kurama 三面図 v1(正面・横・後ろ)【非公開・確認用】 | gpt_image_2_6(kurama v10 参照、quality: high / 2k) | 16:9 | 2 クレジット | 434bf83a-c6db-4357-b028-405c03cafee3 | 3方向で金色の衣・角の髪・炎の紐・勾玉の輪・炎模様がそろった。後ろ姿で額当ての結び目から紐が左右に上がる。横向きで太ももポーチが逆の脚(手前=左脚)に付いている |
| kurama 三面図 v2(衣装を長コート版に作り直し)【非公開・確認用】 | gpt_image_2_6(三面図 v1 参照、quality: high / 2k) | 16:9 | 2 クレジット | 2000b838-42ca-47c1-94d1-f099af2d777d | ユーザー提供の参考画像2枚(フィギュア写真、アップロードせず文章で指定)に合わせた。ふくらはぎ丈の金色の長コート(黒の裏地・炎形の裾と袖口)、黒いインナーに金の縦線と同心円マーク、金のズボンに黒の縦線2本、黒ストラップのサンダル。背中に黒い輪と両肩へ広がる黒い曲線。ポーチは削除 |
| kurama 三面図 v3(背中の模様を黒丸+輪+4方向の線に)【非公開・確認用】 | gpt_image_2_6(三面図 v2 参照、quality: high / 2k) | 16:9 | 2 クレジット | 4a13de1d-6b4d-4f3f-ad3f-17231df75e90 | 背中に黒く塗った丸、その外側に黒い輪、輪から上下左右斜めに4本の黒い直線(X字)。参考画像の線は肩に沿って曲がるが、こちらはまっすぐ。正面・横はv2のまま |
| kurama 三面図 v4(背中の4本線を太く、体と服の曲線に沿わせる)【非公開・確認用】 | gpt_image_2_6(三面図 v3 参照、quality: high / 2k) | 16:9 | 2 クレジット | 3b791203-ebfc-4090-a63e-1a4e5bc5ce92 | 4本線が太くなり、上は肩の丸みに沿って回り込み、下はあばらに沿って脇へ流れる自然なカーブに。他はv3のまま。ユーザー判断で **九喇嘛モードナルトの完成形(三面図)** |

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
| 片目万華鏡 v1(額当てを上げ、左目に万華鏡写輪眼・縦の傷、直立ポーズ)【非公開・確認用】 | gpt_image_2_6(カカシ v1 参照、quality: high / 2k) | 9:16 | 2 クレジット | 83f5a27d-c250-4a42-a16d-f1a79fef8d71 | 本をなくし両腕を下ろした正面直立に。額当てがまっすぐになり両目が見える。右目は黒、左目は赤に黒い模様(拡大で見える程度、3枚刃の形はやや不明瞭)。左目の縦の傷は赤く、新しい切り傷のように見える。ユーザー判断で **万華鏡写輪眼カカシの完成形** |

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

**完成形: 三面図 v1(ジョブID 5ff72a67-3636-423e-9e2c-a2d0b0465cd3)/ 正面単体の完成形は v7(5135bb4e-8e02-408c-b4a7-ffea606bb45e)**

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
| v6(サンダルと足を炎色に)【非公開・確認用】 | gpt_image_2_6(ミナト v5 参照) | 9:16 | 0.75 クレジット | 257a82d8-17f2-4a33-9af1-dd325102ffe2 | サンダルと足が金色の炎色に光るように。他はv5のまま。手は肌色のまま |
| v7(両手を炎色に・手の甲に黒い帯と丸の模様)【非公開・確認用】 | gpt_image_2_6(ミナト v6 参照) | 9:16 | 0.75 クレジット | 5135bb4e-8e02-408c-b4a7-ffea606bb45e | 両手が金色になり全身の色がそろった。手首寄りの甲に細い黒の帯と黒丸(参考画像=フィギュア写真、アップロードせず文章で指定)。他はv6のまま。ユーザー判断で **これをミナト完成形とする** |
| 三面図 v1(正面・横・後ろ、羽織の背中に「四代目火影」)【非公開・確認用】 | gpt_image_2_6(ミナト v7 参照、quality: high / 2k) | 16:9 | 2 クレジット | 5ff72a67-3636-423e-9e2c-a2d0b0465cd3 | 3方向で金色の体・羽織・炎の裾・額当ての紐・肩の渦巻き・手の甲の模様がそろった。背中の縦書き「四代目火影」は崩れずに正しい漢字で出た。ユーザー判断で **九喇嘛モードミナトの完成形(三面図)** |

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

#### ミナト v7 プロンプト(v6 を参照して両手のみ編集)

```
Edit this exact image with the smallest possible change. Change ONLY his two hands: make both hands glow in the same bright golden flame chakra color as the rest of his body, and on the back of each hand add a black marking: a thin black horizontal band going across the back of the hand just above the knuckles-to-wrist middle, with a solid filled black circle at the center of the band, like a dot on a line. Keep everything else exactly the same: face, eyes, headband, hair, flame-like headband tails, magatama ring, spirals, the suit pattern, white haori with red flames, golden sandals, pose, background and lighting. No text.
```

## サスケ風(忍界大戦編・両目 永遠の万華鏡写輪眼)

**完成形: 三面図 v2(ジョブID f2522a27-d402-4764-9f57-592609401d3a)/ 正面単体は v4(bfa5a5e0-695d-41e7-9499-b365e77d826e)**

- 17歳くらいの架空の日本人青年、細身で引き締まった体(実在の俳優には似せない)
- 日本人らしい顔立ち、細くまっすぐな眉、冷たく鋭い表情
- ツヤのある黒髪。後ろがツンツンと立ち、長い前髪が顔の両側と額にかかる
- 両目とも永遠の万華鏡写輪眼(赤い瞳に黒い模様)、目の下に血の跡
- 額当てなし
- 濃いグレーのハイネックのファスナー付き長袖シャツ、濃いグレーのズボン、太い紫の縄ベルト(蝶結び)と紺色の腰布、紺色の前腕ガード、黒い忍者サンダル、背中に横向きの刀

### 生成記録

| 版 | モデル | 比率 | 消費 | ジョブID | メモ |
|---|---|---|---|---|---|
| v1(全身正面)【非公開・確認用】 | gpt_image_2_6 | 9:16 | 0.75 クレジット | e9b05490-b879-4873-bbdf-02e5e096d5ea | 衣装・髪・刀はほぼ指定どおり。目は赤く光るが、全身画像では万華鏡写輪眼の模様が小さくはっきりしない。血の跡が「うっすら乾いた」ではなく、両目から長く垂れる血の涙になった |
| v2(血を削除・顔をシャープに・服を薄グレー/青灰/黒に・剣を左腰に斜め差し)【非公開・確認用】 | gpt_image_2_6(サスケ v1 参照) | 9:16 | 0.75 クレジット | 652a484a-0e04-48ee-a800-f18aafdc1cd0 | ユーザー提供の参考画像(原作アニメ絵、アップロードせず文章で指定)に合わせた。血は消え、細面でクールな表情に。薄グレーのVネック・ハイカラー半袖、青灰色の腰布、黒ズボンと黒の前腕ガード。剣は左腰に斜め差し(柄が上向き)。万華鏡写輪眼の模様は小さめ |
| v3(剣を画面左に斜めがけ・髪の前後を自然につなげる)【非公開・確認用】 | gpt_image_2_6(サスケ v2 参照) | 9:16 | 0.75 クレジット | b535f91e-ff62-4093-88b3-96577271e8f4 | 剣が画面左(本人の右腰)に斜めがけ、柄は体の後ろから斜め上へ。髪は前髪と後ろのツンツンが自然につながった。目は赤いが万華鏡の模様がほぼ消え、普通の赤い瞳に見える |
| v4(剣を体の後ろに斜めがけ・万華鏡写輪眼を描き込み)【非公開・確認用】 | gpt_image_2_6(サスケ v3 参照、quality: high / 2k) | 9:16 | 2 クレジット | bfa5a5e0-695d-41e7-9499-b365e77d826e | 剣は体の後ろ側に回り、柄が左肩の後ろから、鞘先が腰布の下から見える。拡大すると赤い瞳に黒い花びら状の模様が見える(原作の六芒星とは少し違う)。画質が上がり全体も鮮明に(1520×2688)。ユーザー判断で **正面の完成形** |
| 三面図 v1(正面・横・後ろ、背中にうちはの家紋)【非公開・確認用】 | gpt_image_2_6(サスケ v4 参照、quality: high / 2k) | 16:9 | 2 クレジット | 4e1a8641-0376-4f73-b94e-a4537145f792 | 3方向で顔・髪・服・色がそろった。後ろ姿の背中上部に赤白のうちわ型の家紋。剣は後ろ姿で右肩側から左腰へ斜め。2688×1520 |
| 三面図 v2(正面・横の剣を一直線に修正)【非公開・確認用】 | gpt_image_2_6(三面図 v1 参照、quality: high / 2k) | 16:9 | 2 クレジット | f2522a27-d402-4764-9f57-592609401d3a | 正面: 柄が左上(右肩の後ろ)、鞘先が右下(左腰の後ろ)で一直線に。横: 柄が首の後ろに少し、鞘先が腰の後ろから斜め下に。後ろ姿はv1のまま。ユーザー判断で **忍界大戦版サスケの完成形** |

#### v1 プロンプト

```
Photorealistic live-action character reference photo, vertical 9:16, full body shot from head to shoes, subject standing straight and facing the camera directly (front view), arms relaxed at sides, centered in frame. A fictional Japanese young man around 17 years old, slim and athletic, original face (not resembling any real actor), clearly Japanese facial features, thin straight eyebrows, cold calm intense expression. Glossy black hair, spiky and sticking up at the back, with long bangs framing both sides of his face and falling over his forehead. BOTH eyes have the Eternal Mangekyo Sharingan from the Naruto anime: glowing deep red irises with an intricate black pinwheel-star pattern (a six-pointed star-flower shape with three curved blades), clearly visible in both eyes, whites of the eyes normal white, a thin trace of dried blood under each eye. No headband. Outfit (Fourth Great Ninja War era): a dark gray long-sleeved high-collared zip-up shirt, dark gray trousers, a thick purple rope belt tied in a bow at the waist with a dark navy cloth hanging over the hips like a short apron, dark navy forearm guards, black open-toe ninja sandals, a straight sword with a plain black hilt and sheath tucked horizontally at his back behind the rope belt. Plain light gray seamless studio background, soft even studio lighting, sharp focus, realistic skin, hair and fabric texture, like a Japanese live-action film costume photo. No text.
```

#### サスケ(忍界大戦編)v2 プロンプト(v1 を参照して編集)

```
Edit this exact image. Keep the same person, hair, front-facing full-body pose, purple rope belt, background and lighting. Make these changes: 1) REMOVE all blood from his face completely — no blood tears, clean skin. Keep both eyes as glowing red Eternal Mangekyo Sharingan with a black pinwheel-star pattern. 2) Face: a slimmer, sharper, handsome face with a calm, cool, slightly confident expression and narrow sharp eyes, thin straight eyebrows. 3) Outfit colors: the shirt becomes LIGHT GRAY, with a high stiff collar standing up around the neck and the front open in a deep V down the chest (no zipper closed, collarbones and upper chest visible), loose sleeves ending just above the elbows; the waist cloth hanging over the hips becomes muted slate blue-gray; the trousers become BLACK; the forearm guards become BLACK; black open-toe sandals. Keep the thick purple rope belt tied in a bow. 4) Sword: instead of horizontal, the black-sheathed sword is tucked diagonally into the rope belt at his LEFT hip, with the hilt near the left side of the waist and the sheath angled down and back behind his left leg. No text.
```

#### サスケ(忍界大戦編)v3 プロンプト(v2 を参照して剣と髪を編集)

```
Edit this exact image. Make ONLY these two changes: 1) Sword: move the black-sheathed sword to the LEFT side of the image (his right hip). It is tucked into the back of the purple rope belt and hangs DIAGONALLY: the black hilt sticks out behind him at the left side of the image near his waist and elbow, angled up and outward, and the sheath slants down and back behind his hip and thigh on the left side of the image. Remove the sword from the right side of the image. 2) Hair: make it one natural continuous hairstyle — the long front bangs and the spiky raised hair at the back of the head blend smoothly into each other with natural volume, layered strands and realistic hair flow, like real styled hair, not a separate spiky piece attached at the back. Keep the same overall look (black hair, spiky back, long bangs framing the face). Keep everything else exactly the same: face, eyes, light gray V-neck high-collar shirt, purple rope belt, slate blue-gray waist cloth, black trousers, black forearm guards, sandals, pose, background and lighting. No text.
```

#### サスケ(忍界大戦編)v4 プロンプト(v3 を参照、quality: high / resolution: 2k)

```
Edit this exact image. Make ONLY these two changes: 1) Sword: keep it on the LEFT side of the image, but tuck it into the BACK of the purple rope belt so the whole sword is clearly BEHIND his body: the black hilt rises diagonally up and outward behind his back/arm on the left side of the image, and the sheath slants diagonally down behind his hip and leg, partly hidden by his body, arm and waist cloth. Nothing of the sword is in front of his body or legs. 2) Eyes: render both eyes in sharp detail as the Eternal Mangekyo Sharingan from the Naruto anime: glowing red irises with a clearly visible black pattern of a six-pointed star made of three curved pinwheel blades overlapping three straight triangular points, with a small black pupil at the center, crisp enough to be recognized when zoomed in. Whites of the eyes natural white, no blood. Keep everything else exactly the same: face, expression, hairstyle, light gray V-neck high-collar shirt, purple rope belt, slate blue-gray waist cloth, black trousers, black forearm guards, sandals, pose, background and lighting. No text.
```

#### サスケ(忍界大戦編)三面図 v1 プロンプト(v4 を参照、quality: high / resolution: 2k、16:9)

character-sheet ワークフローの prompt-built-sheets(ターンアラウンド)の書き方に沿って作成。

```
Character turnaround model sheet of the exact same person in the attached reference photo, three consistent full-body views side by side, evenly spaced: full-body FRONT view on the left (same as the reference), full-body SIDE profile view facing right in the middle, and full-body BACK view on the right. Identical face, hairstyle, outfit, colors, proportions and height in all three panels, standing neutrally with arms relaxed at the sides, full figure in frame head to sandals. Keep every detail of the reference: glossy black hair with long bangs and spiky raised back hair blending naturally, red Eternal Mangekyo Sharingan eyes, light gray high-collar short-sleeve shirt open in a deep V at the front, thick purple rope belt tied in a bow at the front, slate blue-gray waist cloth, black trousers, black forearm guards, black ninja sandals, and the black-sheathed sword tucked diagonally into the back of the rope belt (in the side and back views the sword is clearly visible crossing diagonally behind his hips, hilt rising up toward his right shoulder side). In the back view show the back of the head with the spiky hair, the back of the shirt and collar, and the rope belt knot ends, and on the upper back of the shirt, centered between the shoulder blades just below the collar, the Uchiha clan crest from the Naruto anime: a round paper fan (uchiwa) shape with the upper part red and the lower part white, and a short white handle pointing down, printed cleanly on the fabric. Plain light gray seamless studio background, soft even studio lighting, photorealistic live-action film costume photography, realistic skin, hair and fabric texture, sharp focus. No text, no labels, no watermark, no extra people.
```

#### サスケ(忍界大戦編)三面図 v2 プロンプト(三面図 v1 を参照、剣のみ修正)

```
Edit this exact three-view character sheet. Keep the BACK view (right panel) exactly as it is — there the sword runs in one straight diagonal line from behind his right shoulder (upper right of that panel) down to his left hip (lower left of that panel). Fix ONLY the sword in the FRONT view (left panel) and the SIDE view (middle panel) so they match that same single straight sword behind his back: FRONT view: the black hilt sticks up from behind his right shoulder at the UPPER LEFT of the panel; the sword continues hidden behind his back in one straight diagonal line, and the end of the sheath comes out below the waist cloth at the LOWER RIGHT of the panel (behind his left hip/thigh), on the exact straight extension of the hilt's angle. Remove the sheath end currently at the lower left of the front view. SIDE view (facing right, his left side toward camera): the hilt is only slightly visible rising behind his upper back on the far side, and the sheath end comes out behind his lower back/left hip on the near side, slanting down and back in one straight line with the hilt, behind his body, not in front of his arm or legs. Keep everything else exactly the same: faces, hair, eyes, outfits, rope belts, waist cloths, Uchiha crest, poses, background and lighting. No text.
```

#### ナルト九喇嘛モード 三面図 v1 プロンプト(kurama v10 を参照、quality: high / resolution: 2k、16:9)

```
Character turnaround model sheet of the exact same character in the attached reference image, three consistent full-body views side by side, evenly spaced: full-body FRONT view on the left (same as the reference), full-body SIDE profile view facing right in the middle, and full-body BACK view on the right. Identical face, hairstyle, outfit, colors, glow, proportions and height in all three panels, standing neutrally with arms relaxed at the sides, full figure in frame head to sandals. Keep every detail of the reference: a young Japanese man in Nine-Tails Chakra Mode, his whole body, face, hair, clothes and sandals glowing bright golden like translucent flowing fire light with golden flame aura around him; spiky glowing golden hair with two tufts sticking up like horns; golden headband with the engraved leaf emblem and its two long flame-like golden tails streaming upward and outward from the back of his head; orange eyes with white sclera; three thick black rectangular whisker marks on each cheek; thin eyebrows; open golden jacket over a golden shirt with a black spiral on the stomach; a ring of black magatama marks around the collar; black flame-shaped markings on the arms and legs; thigh pouch with band on his right leg; golden sandals. In the side view show the profile of the face, the horn-like hair, the headband tails flowing up behind his head, and the flame markings along the arm and leg. In the back view show the back of the spiky hair, the headband knot with both flame-like tails rising from it, the magatama ring continuing around the back of the collar, and black flame-shaped markings running down the back of the jacket and legs. Plain light gray seamless studio background, soft even studio lighting, photorealistic live-action film VFX look, realistic skin, hair and fabric texture under the glow, sharp focus. No text, no labels, no watermark, no extra people.
```

#### ナルト九喇嘛モード 三面図 v2 プロンプト(三面図 v1 を参照、衣装のみ作り直し)

```
Edit this exact three-view character sheet. Keep the same person, face, orange eyes, thick black whisker marks, glowing golden horn-like hair, golden headband with emblem and its long flame-like tails, golden flame aura, the three poses (front, side facing right, back), background and lighting. Redesign ONLY the outfit, identically in all three views: 1) a long glowing golden open coat worn over everything, reaching mid-calf, with black lining and black edges along the front opening, loose wide sleeves ending in flame-shaped golden-orange tips, and the hem cut into jagged flame shapes that fade from gold to orange at the bottom; 2) under the open coat, the torso is a fitted BLACK bodysuit with a high black collar showing golden magatama marks in a ring; a thin golden vertical line runs from the collar down the center of the chest to a golden concentric-circle emblem on the stomach (an outer golden ring, an inner golden ring and a solid golden dot in the center), with a golden horizontal band at the waist below it; 3) the legs are glowing golden trousers with two bold black vertical stripes running down the front of each leg from hip to ankle; 4) golden boots/sandals with black straps. Remove the thigh pouch and leg band. BACK view: the back of the long golden coat shows, on the upper back between the shoulder blades, a large black ring outline with a golden center, connected to a black curved line that sweeps outward across both shoulders; the collar ring of black magatama marks continues around the back; the coat flares out behind with jagged flame-shaped hem and small flame flicks along the edges. SIDE view: show the long coat hanging behind with the flame hem, the black inner suit at the front and the black leg stripes. Photorealistic live-action film VFX look, glowing translucent chakra-fire material. No text, no labels, no extra people.
```

#### ナルト九喇嘛モード 三面図 v3 プロンプト(三面図 v2 を参照、後ろ姿の背中の模様のみ)

```
Edit this exact three-view character sheet. Keep the FRONT and SIDE views exactly as they are. In the BACK view (right panel), change ONLY the black emblem on the upper back of the golden coat: replace it with this design — a solid filled BLACK circle in the center between the shoulder blades; around it, separated by a thin golden gap, a black circular ring outline; and from that outer ring, FOUR black lines branch out in four directions: two lines rising up and outward over the left and right shoulders, and two lines going down and outward toward the left and right sides under the arms, like an X centered on the ring. Lines are bold, clean and the same thickness as the ring. Remove the previous emblem and its single curved shoulder line. Keep everything else in the back view the same: hair, headband tails, magatama collar, long golden coat with flame hem, legs, sandals, pose, background and lighting. No text.
```

#### ナルト九喇嘛モード 三面図 v4 プロンプト(三面図 v3 を参照、背中の4本線のみ)

```
Edit this exact three-view character sheet. Keep the FRONT and SIDE views exactly as they are. In the BACK view (right panel), adjust ONLY the four black lines of the back emblem: keep the solid black center circle and the black ring around it in the same place, but make the four lines that branch out from the ring THICKER (noticeably bolder, about 1.5 to 2 times the current width) and no longer perfectly straight — each line follows the natural curves of the body and the coat fabric: the two upper lines curve smoothly up and outward, wrapping over the rounded tops of the shoulders following the shoulder contour; the two lower lines curve smoothly down and outward along the ribcage toward the sides under the arms. The lines bend with the folds and drape of the coat so they look printed on the fabric, with natural perspective and no awkward stiffness. Keep everything else the same: hair, headband tails, magatama collar, long golden coat with flame hem, legs, sandals, pose, background and lighting. No text.
```

#### ミナト 三面図 v1 プロンプト(ミナト v7 を参照、quality: high / resolution: 2k、16:9)

```
Character turnaround model sheet of the exact same character in the attached reference image, three consistent full-body views side by side, evenly spaced: full-body FRONT view on the left (same as the reference), full-body SIDE profile view facing right in the middle, and full-body BACK view on the right. Identical face, hairstyle, outfit, colors, glow, proportions and height in all three panels, standing neutrally with arms relaxed at the sides, full figure in frame head to sandals. Keep every detail of the reference: a Japanese man in Nine-Tails Chakra Mode reanimated by Edo Tensei; glowing golden face, hands and body; black sclera with glowing orange irises; gray cracked patches on his cheeks; spiky glowing golden hair with long bangs hanging down both sides of the face; golden headband with engraved leaf emblem and two long flame-like golden tails rising up from the back of the head; glowing golden one-piece chakra bodysuit with a ring of black magatama marks around the collar, a black spiral on the upper chest, a black spiral on each shoulder, and below the chest spiral one black vertical line meeting a horizontal line that splits into two lines running down the front of each thigh to the knees; black band with a black dot on the back of each hand; golden sandals; over it an open white knee-length short-sleeved haori coat with red-orange flame patterns along the bottom hem. In the side view show the face profile, the bangs, the headband tails flowing behind, the haori hanging from the shoulder with its flame hem. In the back view show the back of the spiky hair and the headband knot with both flame-like tails rising from it, and the back of the white haori: the red-orange flame pattern runs all around the hem, and down the center of the back is written vertically in large bold red Japanese brush-style kanji the four characters 四代目火影 (top to bottom: 四, 代, 目, 火影 as 火 then 影), correctly formed and clearly legible. Plain light gray seamless studio background, soft even studio lighting, photorealistic live-action film VFX look, sharp focus. No other text, no labels, no watermark, no extra people.
```

#### カカシ 片目万華鏡 v1 プロンプト(カカシ v1 を参照、quality: high / resolution: 2k)

```
Edit this photo. Keep the same man, silver hair, navy face mask, outfit, vest, gloves, sandals, background and lighting. Changes: remove the orange book; he stands straight facing the camera with both arms relaxed at his sides. Push the headband up so it sits level on his forehead and BOTH eyes are visible. His right eye is a normal dark eye. His LEFT eye is the Mangekyo Sharingan: glowing red iris with a black pinwheel pattern of three curved scythe-like blades joined around a small black pupil, crisp and recognizable when zoomed in; a thin vertical scar runs straight down through his left eyebrow, eyelid and upper cheek. Sharp calm serious expression. No blood. No text.
```

## 扉間風(穢土転生・二代目)

**完成形: 三面図 v3(ジョブID 48be247f-35c0-4cfd-afb4-4c52e6f7c476)**

- 30歳くらいの架空の日本人男性、長身で肩幅が広い(実在の俳優には似せない)。厳しく冷たい表情
- 短いツンツンの白銀髪。両頬に縦の赤い線、あごに赤い線(計3本)
- 穢土転生: 白目が黒く瞳は赤い。顔と手に灰色のひび割れ、細かい破片が舞う
- 額当て: 紺色の布に木の葉マーク(非公開・確認用)、布が顔の両横まで垂れる
- 紺色のボディスーツ、青みがかったグレーの胸当て・背当て・肩当て・草摺、白い毛皮の襟、紺色のズボン、前腕ガード、黒い忍者サンダル

### 生成記録

| 版 | モデル | 比率 | 消費 | ジョブID | メモ |
|---|---|---|---|---|---|
| 三面図 v1(正面・横・後ろ)【非公開・確認用】 | gpt_image_2_6(参照なし、quality: high / 2k) | 16:9 | 2 クレジット | b5c5e980-cc56-4d7a-9608-819a320f9053 | 3方向で白銀髪・毛皮・鎧・額当てがそろった。黒い白目に赤い瞳、頬とあごの赤い線。ひび割れは顔全体と手に細かく入る |
| 三面図 v2(顔のペイント・額当て・服と鎧の形と色を参考画像に合わせる)【非公開・確認用】 | gpt_image_2_6(三面図 v1 参照、quality: high / 2k) | 16:9 | 2 クレジット | d9449a72-b5a5-41ca-ac5c-2e1e5b019c6a | ユーザー提供の参考画像(原作アニメ絵、アップロードせず文章で指定)に合わせた。頬の細い斜めの赤線とあごの短い赤線、ひびは控えめに。銀灰色の頭巾風額当て、黒っぽいオリーブの長袖とズボン、すねに包帯、青緑の1枚板の胸当て・前垂れ3枚・肩当て(下に薄紫) |
| 三面図 v3(前髪を少し垂らす・眉を細く)【非公開・確認用】 | gpt_image_2_6(三面図 v2 参照、quality: high / 2k) | 16:9 | 2 クレジット | 48be247f-35c0-4cfd-afb4-4c52e6f7c476 | 額当ての上と横に白銀の毛先が少しかかるようになったが、変化は控えめ。眉はわずかに細くなった程度。他はv2のまま。ユーザー判断で **扉間穢土転生verの完成形** |

#### 三面図 v1 プロンプト

```
Character turnaround model sheet, three consistent full-body views of the same man side by side, evenly spaced: full-body FRONT view on the left, full-body SIDE profile view facing right in the middle, full-body BACK view on the right, identical face, hair, outfit, colors, proportions and height in all three panels, standing neutrally with arms relaxed at the sides, full figure in frame head to sandals. A fictional Japanese man around 30 years old, tall and broad-shouldered, original face (not resembling any real actor), clearly Japanese facial features, stern cold serious expression. Short spiky white-silver hair. Three red face-paint markings: one vertical red stripe under each eye on the cheeks and one red stripe on the chin. He is reanimated by the Edo Tensei (Impure World Reincarnation) technique: the whites of his eyes are BLACK (black sclera) with red irises, and his face and hands have gray-beige cracked patches like dry porcelain or ash, with a few tiny dust flakes drifting off. Headband: dark navy cloth covering the forehead with a metal plate engraved with the Hidden Leaf Village symbol from the Naruto anime, the cloth extending down over the sides of the face like cheek guards, tied at the back of the head. Outfit (feudal-era ninja leader armor): a dark navy blue long-sleeved bodysuit; over it a blue-gray lacquered segmented armor chest plate and back plate with shoulder guards, and a matching armored skirt of plates over the hips and thighs (front and back); a thick white fur ruff around the neck and across the shoulders, visible all around from the back; dark navy trousers, dark forearm guards, black open-toe ninja sandals. In the side view show the face profile with the red markings and the armor layering; in the back view show the back of the spiky hair, the headband knot, the fur ruff, the back plate and the rear armored skirt. Plain light gray seamless studio background, soft even studio lighting, sharp focus, realistic skin, hair, metal and fabric texture, like a Japanese live-action film costume photo. No text, no labels, no watermark, no extra people.
```

#### 扉間 三面図 v2 プロンプト(三面図 v1 を参照して編集)

```
Edit this exact three-view character sheet. Keep the same man, his face shape, spiky white-silver hair, black sclera with red irises, the three poses (front, side facing right, back), background and lighting. Change, identically in all three views: 1) FACE PAINT: replace the thick red stripes with thin red lines — one thin red line running from just under each eye diagonally down across the cheek, and one short thin red vertical line on the center of the chin. Reduce the Edo Tensei cracks to only a few subtle thin cracks on the face and hands. 2) HEADBAND: light silver-gray cloth hood that covers the forehead and wraps down over the sides of the face like cheek guards, with the metal plate engraved with the leaf emblem on the forehead. 3) OUTFIT: a dark olive-black long-sleeved high-neck shirt and loose dark olive-black trousers; light gray bandage wraps around the lower shins above the ankles; black open-toe sandals; no forearm guards (bare hands). 4) ARMOR in solid steel-blue/teal color: a single smooth flat steel-blue chest-and-back plate with small lacing loops, no segmented horizontal bands; at the front of the waist only, one hanging apron of three stacked rectangular steel-blue plates covering the groin and upper thighs (in the back view a matching short plate panel at the back); on each shoulder a curved steel-blue shoulder guard with a pale lavender-purple padded layer underneath, partly under the fur. A few fine crack lines on the armor. 5) Keep a big thick white fur ruff around the neck and shoulders. No text, no extra people.
```

#### 扉間 三面図 v3 プロンプト(三面図 v2 を参照、前髪と眉のみ)

```
Edit this exact three-view character sheet with the smallest possible change. Change ONLY these two things, consistently in the front and side views: 1) HAIR: add a few spiky white-silver bangs that hang down over the top edge of the headband onto the forehead area and slightly over the sides near the temples, naturally connected to the rest of his spiky white-silver hair (in the back view keep the hair as it is). 2) EYEBROWS: make both eyebrows much thinner and finer, sharp narrow brows. Keep everything else exactly the same: face, black sclera with red irises, thin red face lines, subtle cracks, silver-gray hood headband with leaf plate, white fur ruff, steel-blue armor with lavender pads, dark olive clothes, bandaged shins, sandals, poses, background and lighting. No text.
```

## 柱間風(穢土転生・初代)

- 30歳くらいの架空の日本人男性、長身でがっしり(実在の俳優には似せない)。穏やかで威厳のある表情、細くまっすぐな眉
- 真ん中分けのまっすぐな長い黒髪(背中の中ほどまで)
- 穢土転生: 白目が黒く瞳はこげ茶(予定)、顔と手に細いひびを少し
- 額当て: 紺色の布に木の葉マーク(非公開・確認用)
- 黒に近い紺色のハイネックのボディスーツとゆったりしたズボン、深い赤の鎧(段のある胸当て・背当て・丸い肩当て・前後の草摺)、前腕ガード、すねに包帯、黒い忍者サンダル

### 生成記録

| 版 | モデル | 比率 | 消費 | ジョブID | メモ |
|---|---|---|---|---|---|
| 三面図 v1(正面・横・後ろ)【非公開・確認用】 | gpt_image_2_6(扉間 三面図 v3 を並べ方の見本として参照、quality: high / 2k) | 16:9 | 2 クレジット | d58c26ff-2799-4125-83f7-b6e7f326bc05 | 顔は扉間と別人。真ん中分けの長い黒髪、深い赤の鎧、黒いスーツ、包帯、サンダルが3方向でそろった。**白目が黒くならず普通の白目のまま**。顔のひびは細く少し |
| 三面図 v2(顔・服・色を参考画像に合わせる)【非公開・確認用】 | gpt_image_2_6(三面図 v1 参照、quality: high / 2k) | 16:9 | 2 クレジット | 4e1f28fb-8360-4dbd-a19e-6d59299d34f2 | ユーザー提供の参考画像(フィギュア写真、アップロードせず文章で指定)に合わせた。白目が黒くなり、ほほえんだ穏やかな顔に細いひび。濃いワインレッドのなめらかな胸当て・大きな肩当て・腰帯・左右だけの草摺・前腕ガード、青みのある濃いチャコールのスーツ、白い包帯、こげ茶のサンダル |
| 三面図 v3(鼻まわりにひびを追加・眉をさらに細く)【非公開・確認用】 | gpt_image_2_6(三面図 v2 参照、quality: high / 2k) | 16:9 | 2 クレジット | 83124c79-9b15-4736-a34a-eff1d7664346 | 鼻すじ・小鼻から頬へのひびがはっきり入った。眉はかなり細くなった。他はv2のまま |
| 三面図 v4(目をキリッと男らしく)【非公開・確認用】 | gpt_image_2_6(三面図 v3 参照、quality: high / 2k) | 16:9 | 2 クレジット | 97e178b1-79c0-4ba8-9dba-f6b80313d125 | 目は細めの切れ長で鋭くなったが、**黒い白目が普通の白目に戻ってしまった**。眉もv3よりやや太く戻った。基準はv3のまま |
| 三面図 v5(白目を黒に戻す・眉を細く・前髪を細い毛束で両サイドに・目を気持ち大きく)【非公開・確認用】 | gpt_image_2_6(三面図 v4 参照、quality: high / 2k) | 16:9 | 2 クレジット | 2d424b45-9803-44a9-8f26-1dc67736df4c | 白目が黒に戻り、キリッとした切れ長の目を少しだけ大きく。眉は細め。額当ての下から細い前髪が顔の両サイドに垂れる。**現時点の基準** |

#### 三面図 v1 プロンプト

```
Use the attached image ONLY as the layout and style reference (three-view turnaround: front on the left, side profile facing right in the middle, back on the right; light gray studio background; photorealistic live-action costume photography). Create a DIFFERENT character with a different face: a fictional Japanese man around 30 years old, tall and well-built, original face (not resembling any real actor and not the reference face), clearly Japanese features, calm gentle but dignified expression, thin straight eyebrows. Very long straight glossy black hair parted in the center, falling past the shoulders down to the middle of the back. Edo Tensei reanimation: black sclera with dark brown irises, a few subtle thin gray cracks on the face and hands. Dark navy cloth headband with a metal plate engraved with the Hidden Leaf Village symbol. Outfit: dark navy-black long-sleeved high-neck bodysuit and loose dark trousers; over it deep crimson-red lacquered armor — segmented chest plate and back plate, rounded shoulder guards, and an armored skirt of red plates hanging over the hips and thighs front and back; dark forearm guards; light gray bandage wraps on the lower shins; black open-toe sandals. In the back view the long black hair falls over the red back plate. Identical character, outfit and proportions in all three views, arms relaxed at sides. No text, no labels, no extra people.
```

#### 柱間 三面図 v2 プロンプト(三面図 v1 を参照して編集)

```
Edit this exact three-view character sheet. Keep the same man, his long center-parted straight black hair, the three poses (front, side facing right, back), background and lighting. Change, identically in all three views: 1) FACE: a slightly tanned warm skin tone, calm relaxed expression with a faint gentle smile; Edo Tensei eyes with the whites of the eyes clearly BLACK (black sclera) and dark brown irises; clearly visible thin gray-beige crack lines on the face and hands like dry porcelain. Headband: light gray cloth with a metal plate engraved with the leaf emblem. 2) BODYSUIT: change the inner suit and trousers to dark charcoal slate-gray (bluish dark gray), long sleeves and high neck; fitted trousers tucked at the shins with white bandage wraps on the lower shins; dark brown-black thong sandals. 3) ARMOR in dark matte burgundy maroon red (deep dark wine-red, not bright crimson), with a few fine crack lines: a smooth chest plate (one main plate with a raised border, only one or two subtle horizontal seams, not many segments) and matching back plate; large curved shoulder guards; a wide dark maroon waist sash/belt; armored tassets of stacked maroon plates hanging at the LEFT and RIGHT sides of the hips (not covering the front center), so the dark gray trousers are visible at the front; dark maroon forearm guards. No text, no extra people.
```

#### 柱間 三面図 v3 プロンプト(三面図 v2 を参照、顔のみ)

```
Edit this exact three-view character sheet with the smallest possible change. Change ONLY his face, consistently in the front and side views: 1) CRACKS: add several clearly visible thin gray-beige crack lines around the NOSE — running down the bridge of the nose, across the nose and from the sides of the nose onto both cheeks, like cracked dry porcelain, in addition to the existing cracks. 2) EYEBROWS: make both eyebrows less than half of their current thickness — very thin, fine, sharp narrow brows, clearly thinner than now. Keep everything else exactly the same: black sclera with dark brown irises, gentle smile, long center-parted black hair, headband, maroon armor, charcoal suit, bandages, sandals, poses, background and lighting. No text.
```

- メモ: 三面図の小さな顔でも「半分以下」「はっきり見える」のように強めに書くと効いた(柱間 v3)。

#### 柱間 三面図 v4 プロンプト(三面図 v3 を参照、目のみ)

```
Edit this exact three-view character sheet with the smallest possible change. Change ONLY his eyes, consistently in the front and side views: make the eyes clearly sharper and more masculine — narrower, longer almond-shaped Japanese eyes with a straight, slightly lowered upper eyelid and slightly upturned outer corners, a strong focused gaze, no round or soft doe-eyed look. Keep the black sclera with dark brown irises. Keep everything else exactly the same: the very thin eyebrows, the cracks around the nose and cheeks, the gentle closed-mouth smile, long center-parted black hair, headband, maroon armor, charcoal suit, bandages, sandals, poses, background and lighting. No text.
```

#### 柱間 三面図 v5 プロンプト(三面図 v4 を参照、頭まわりのみ)

```
Edit this exact three-view character sheet with the smallest possible change. Change ONLY these details of his head, consistently in the front and side views: 1) EYES: keep the sharp, narrow, masculine almond shape, but make the eyes just very slightly larger (about 5 to 10 percent, subtle). The whites of BOTH eyes must be completely BLACK (black sclera, Edo Tensei reanimation) — no white visible anywhere in the eyes — with dark brown irises. 2) EYEBROWS: very thin, fine, sharp narrow brows, less than half of their current thickness. 3) FRONT HAIR: instead of thick chunks, a few thin, fine, wispy strands of black hair hang down loosely from under the headband on both sides of the face, framing the cheeks in a cool, stylish way, while the rest of the long center-parted straight black hair stays the same. Keep everything else exactly the same: face shape, cracks around the nose and cheeks, gentle closed-mouth smile, headband, maroon armor, charcoal suit, bandages, sandals, back view, poses, background and lighting. No text.
```

- メモ: 目の形を変える編集では、黒い白目が普通の白目に戻りやすい(v4)。目をいじるときは毎回「白目は完全に黒、白い部分を残さない」と明記する。
