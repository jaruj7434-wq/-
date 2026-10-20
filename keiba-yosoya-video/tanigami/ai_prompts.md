# ai_prompts.md — AI 映像制作向け素材(Higgs Field 用)

> **生成は、必ずユーザーの許可を得てから実行する**(`../CLAUDE.md` のルール)。
> 2026-10-14 時点の確認結果:Higgs Field は利用可能(Ultra プラン)。**無制限枠(unlim)は使えない**ため、
> 生成するとクレジットを消費する。実行前に、`get_cost: true` で見積もった費用を提示して承認をもらう。
>
> 前提:本人の写真・声の使用許可は**未確認**。このファイルは「谷上をモデルにしたフィクション表現(仮デザインA)」で書いている。
> 許可が取れて本人の写真が届いたら、人物の記述を本人の参照写真に置き換える。

---

## 0. 使うツール・モデル(候補)

| 工程 | ツール/モデル | 理由 |
|---|---|---|
| 人物の参照シート | `character-sheet` ワークフロー(`get_workflow_instructions` で手順を読む) | 角度・表情の違う画像をまとめて作り、一貫性の基準にする |
| 人物の静止画・キーフレーム | `nano_banana_pro`(参照画像を複数入れられる)/`soul_2`(リアルな人物描写が得意) | どちらも 9:16 に対応。まず両方で1枚ずつ試して比べる |
| 人物の固定 | `show_reference_elements` で参照エレメントとして登録 | 以降のすべてのカットで同じ人物を参照する |
| 動画化 | `seedance_2_5`(`mode: omni_reference`、9:16、4〜30秒、音声生成あり) | 参照画像で人物を保ちながら動かせる |
| 動画化(予備) | `gemini_omni`(9:16、4〜10秒、音声あり)/`minimax_h3`(開始・終了フレーム指定) | 短いカットや手元のカット用 |
| セリフの音声 | 本人の録音(許可がある場合)/許可がなければ、本人に似せない別の声(`list_voices` から選ぶ) | 本人の声の複製は許可がない限り作らない |
| 字幕 | `subtitles` ワークフロー | 焼き込み字幕 |

※モデル名は 2026-10-14 時点の `models_explore` の結果。生成の直前にもう一度確認する。
※日本語のセリフを動画モデルに直接しゃべらせると、口の動きや発音が崩れる場合がある。
  第1話は**セリフの多くを画面外の声や手元のカットにしてある**ので、口元の失敗は少なくて済む。
  正面でしゃべる C5 だけは、音声を別に作り、口の動きに合わせて調整するかを試作で判断する。

---

## 1. 人物デザイン用プロンプト(仮デザインA)

### 日本語の設定(共有用)
60代半ばの日本人男性。短く整えたグレー混じりの髪。自然なシワと適度な日焼け。中肉で背筋がまっすぐ。
ネイビーの無地カーディガンに、白い襟付きシャツ。表情は穏やかで、目元はやわらかく、口角は水平。
落ち着いていて、長年の経験を感じさせる雰囲気。誇張した老人の描写はしない。

### 英語プロンプト(生成用)
```
Photorealistic portrait of a Japanese man in his mid-60s, short neatly trimmed salt-and-pepper hair,
natural wrinkles and light sun-tanned skin with real skin texture, medium build, upright posture.
Wearing a plain navy cardigan over a white collared shirt.
Calm, composed expression, soft eyes, neutral mouth — a quiet, experienced, trustworthy man,
not exaggerated or stereotypical. Soft natural window light, shallow depth of field,
shot on a 50mm lens, documentary photography style, 9:16 vertical.
```

### 参照シート用(character-sheet ワークフローに渡す説明)
```
Character reference sheet of the same Japanese man in his mid-60s (description above).
Views: front neutral, 3/4 left, 3/4 right, profile, close-up of hands holding a red pen.
Expressions: neutral calm, focused (slightly furrowed brow, eyes fixed downward),
mildly puzzled (head tilted slightly, looking at a smartphone), small shy smile.
Same clothing in every view: plain navy cardigan, white collared shirt. Plain light gray background.
```

---

## 2. 同じ人物を複数カットで保つための共通設定

すべてのカットのプロンプトの先頭に、次の**固定ブロック**をそのまま入れる。

```
[CHARACTER: Tanigami] Japanese man, mid-60s, short neatly trimmed salt-and-pepper hair,
natural wrinkles, light sun-tanned skin, medium build, upright posture,
plain navy cardigan over a white collared shirt, simple analog wristwatch with brown leather strap.
Calm and composed demeanor.
```

```
[STYLE] photorealistic, documentary-style vertical video 9:16, warm late-afternoon light,
slightly muted film color grade, natural skin texture, 50mm lens look, shallow depth of field.
```

運用ルール:
- 参照シートが完成したら、**参照エレメントとして登録し、すべてのカットで同じ参照を指定**する。
- 生成に使ったシード値・参照ID・モデル名・プロンプトは、このファイルの末尾の「生成ログ」に記録する。
- 服装・時計・髪型は全カットで同じにする(固定ブロックを書き換えない)。

---

## 3. 第1話 カット別プロンプト

各カットは「① キーフレーム画像 → ② 動画化」の順で作る(静止画で確認してから動かすと失敗が少ない)。
画像は `aspect_ratio: "9:16"`、動画も `aspect_ratio: "9:16"`。

### C1(0:00–0:02)スマホ画面の真上
- 画像:
```
Top-down close-up of an older man's hand holding a smartphone with a plain dark case.
The screen shows a simple fictional social media draft screen with Japanese text "はじめまして"
and a "post" button. His index finger hovers above the button, hesitating.
Wooden café table, warm light. No real app logos or UI. [STYLE]
```
- 動画:`The index finger hovers over the button, stops, and slowly pulls back. Very still camera. Quiet.`(2〜3秒)

### C2(0:02–0:05)喫茶店でスマホを押す
- 画像:
```
[CHARACTER: Tanigami] sitting at a small table in an old, cozy Japanese kissaten café,
holding a smartphone with both hands, pressing the screen with one index finger,
head tilted slightly, mildly puzzled but serious expression. Medium shot, slight angle from the front. [STYLE]
```
- 動画:`He presses the screen carefully with one finger, tilts his head, then gives a small nod. Camera slowly pushes in.`(3〜4秒)

### C3(0:05–0:08)スマホを伏せ、ノートを出す
- 画像:
```
[CHARACTER: Tanigami] placing a smartphone face-down on the café table and taking out
a well-worn notebook with rounded corners and a folded horse racing newspaper (text unreadable, no logos).
He rolls up his sleeve slightly. His gaze becomes focused downward. [STYLE]
```
- 動画:`He turns the phone face down, takes out the worn notebook and newspaper, rolls up his sleeve slightly; his expression shifts from puzzled to focused. Camera tilts from hands up to his face.`(3〜4秒)

### C4(0:08–0:12)赤ペンで印をつける
- 画像:
```
Macro top-down shot of a folded Japanese horse racing newspaper with columns of small print (blurred, unreadable,
no logos, no horse names legible). An older man's hand draws a red circle with a red pen without hesitation,
then a short line on another row. Warm light. [STYLE]
```
- 動画:`The red pen confidently draws a circle and then a line on another row; the pen tip traces numbers in order.`(3〜4秒)

### C5(0:12–0:17)正面で「買わない」と言う
- 画像:
```
[CHARACTER: Tanigami] bust shot, facing the camera at a slight angle, newspaper lowered in front of him,
calm and focused eyes, neutral mouth, speaking quietly. Static frontal camera. [STYLE]
```
- 動画:`He looks up from the newspaper, pauses for a beat, then speaks calmly in a low voice. Minimal head movement. Static camera.`(5秒)
- セリフ:「強い。それは皆わかってる。……でも、このオッズなら、買わない。」
  → 口元の自然さを試作で確認。崩れる場合は、口元を新聞で少し隠す構図にするか、横顔+画面外の声に変える。

### C6(0:17–0:21)肩越しの会話
- 画像:
```
Over-the-shoulder shot from behind a young person's shoulder (face not visible), holding a smartphone in the foreground (out of focus).
[CHARACTER: Tanigami] seen in profile, setting down a red pen on the newspaper. [STYLE]
```
- 動画:`He sets the red pen down and speaks briefly. Camera slowly slides sideways.`(4秒)

### C7(0:21–0:25)ゆっくり入力する
- 画像:
```
Close-up of an older man's hands typing slowly with one finger on a smartphone.
The screen shows a fictional draft with Japanese text "予想の理由を、ここに書いていきます。谷上".
No real app UI or logos. Warm café light. [STYLE]
```
- 動画:`Slow one-finger typing; a slight shy smile is implied by a small pause.`(4秒)
- ※画面内の日本語は崩れやすい → **画面の文字は編集でのせる**(合成)ほうが確実。

### C8(0:25–0:28)投稿して新聞に戻る
- 画像:
```
[CHARACTER: Tanigami] medium shot at the café table, placing the smartphone face down,
looking back at the newspaper with a red circle, tapping the red circle once with his finger. Calm, quiet confidence. [STYLE]
```
- 動画:`He puts the phone down, looks back at the newspaper, and taps the red circle once with his index finger. Camera holds steady.`(3秒)

### 抽象的な競馬場の演出(実際のレース映像が使えない時の差し替え用)
```
Macro shot of morning dew on racetrack turf, a section of white rail fence fading into mist, no signage, no logos, no people. 9:16.
```
```
Silhouette of a horse's mane against a low golden sun, out of focus, unidentifiable location, no jockey visible. 9:16.
```
```
Long shadow of an empty grandstand on the ground at dusk, abstract, no logos or text. 9:16.
```

---

## 4. ネガティブプロンプト・避けたい描写

```
cartoon, anime, plastic skin, over-smoothed face, exaggerated wrinkles, caricature of elderly person,
frail or sickly appearance, angry or shouting expression, flashy gold jewelry, gambling-addict stereotype,
piles of cash, money, betting tickets showing amounts, slot machines,
real racecourse logos, JRA logo, real newspaper mastheads, readable horse names, real jockeys,
real social media app UI or logos, text artifacts, extra fingers, deformed hands,
inconsistent clothing, different hairstyle, glasses (unless reading scene)
```

避ける演出:
- お札・高額な払戻金・ガッツポーズなど、利益や的中を強調する絵
- 「老い」を笑いにする描写(手の震えの強調、操作ミスを大げさに見せる等)
- 実在の SNS 画面の再現、実在の人物に似た顔

---

## 5. 編集時の指示(まとめ)

| 項目 | 指示 |
|---|---|
| 字幕 | 全セリフを焼き込み。谷上=白文字+黒縁、ミズキ=淡い黄色。SNSのUIに被らない位置 |
| テロップ | 1行12文字以内。シリーズ共通の書体を固定 |
| AI 表記 | 画面下の隅に常時「AI生成映像/演出を含みます」 |
| 注意表記 | 最後に「馬券の購入は20歳から。無理のない範囲で。」 |
| BGM | 低いピアノの単音、またはアコースティックギター。ライセンスを確認済みのものだけ |
| 効果音 | タップ音・紙の音・ペンの音・投稿完了音。どれも小さく |
| テンポ | 1カット2〜5秒。C5 だけ長く、カメラを固定して「間」を見せる |
| 色 | 暖色・やや低いコントラストのフィルム調で全カット統一 |

## 6. 顔・服装・年齢感がカットごとに変わらないための注意

1. **最初に参照シートを確定させる。** 承認された1枚を「正解の顔」として、以降すべての参照に使う。
2. **固定ブロック([CHARACTER]・[STYLE])を書き換えない。** 言い回しを変えると顔が変わりやすい。
3. **光の条件をそろえる。** 夕方の暖色光で統一する(光が変わると年齢が違って見える)。
4. **顔の寄りは少なめに。** 手元・肩越し・横顔のカットを多くすると、顔のぶれが目立たない。
5. **年齢がぶれた時の確認ポイント**:髪の白さ、シワの深さ、首まわり。参照シートと並べて比べる。
6. **各カットを作ったら、参照シートと並べて確認する。** 違う人に見えるカットは作り直しの候補にする(作り直しにも許可を取る)。
7. **服装の小物(時計・ペン)も固定。** 左手首に時計、赤ペンは胸ポケット。

---

## 7. 実在の競馬場・レース・馬・騎手について

- 実際のレース映像、競馬場の施設やロゴ、実在の馬・騎手・勝負服を映像に使う場合は、**権利者の利用許諾の確認が必要**(→ `fact_check.md`)。
- 許諾がない場合は、上の「抽象的な競馬場の演出」で代用する。
- 生成の段階で、実在の施設や人物に似た絵が出た場合は使わない。

---

## 生成ログ(生成したら記入)

| 日付 | カット | モデル | シード | 参照ID | 結果・メモ |
|---|---|---|---|---|---|
| 2026-10-14 | 顔のアップ 案A | nano_banana_pro(処理上の表示は nano_banana_2) | — | job `b98c92b1-1e9d-401e-a22a-118d07a36165` | 3:4・2k。正面・シワ強調。2クレジット。**不採用**(年齢・シワを強調しすぎ、顔立ちを独自に指定したため設定書とずれた) |
| 2026-10-14 | 顔のアップ 案B | nano_banana_pro(処理上の表示は nano_banana_2) | — | job `62593b34-8355-4bef-9407-ade1fb701046` | 同じプロンプトの別案。2クレジット |
| 2026-10-14 | 全身4面シート 案A(不採用) | nano_banana_pro(表示は nano_banana_2) | — | job `59256524-eca7-4021-99a1-321bc7cbefb2`(参照:顔 案A) | 16:9・2k。正面/左側面/背面/右側面。2クレジット |
| 2026-10-14 | 全身4面シート 案B(不採用) | nano_banana_pro(表示は nano_banana_2) | — | job `2666aec4-40d6-4bd3-9f2b-91a495e374b6`(参照:顔 案B) | 同上。2クレジット |
| 2026-10-14 | 顔のアップ 第2版 S1 | soul_2 | 466996 | job `7d8d15da-7dcb-4f5f-a12a-7f5eb25f429a` | 3:4(1536×2048)。character.md の外見表どおりに書き直したプロンプト。顔立ちの細部は指定なし |
| 2026-10-14 | 顔のアップ 第2版 S2 | soul_2 | 521616 | job `d2ed9e5f-5248-4a02-9c22-3fe4877e8571` | 同上 |
| 2026-10-14 | 顔のアップ 第2版 N1 | nano_banana_pro(表示は nano_banana_2) | — | job `0a9463ad-be8c-4fc5-828b-a1aa3f541f72` | 同上・3:4・2k |
| 2026-10-14 | 顔のアップ 第2版 N2 | nano_banana_pro(表示は nano_banana_2) | — | job `c0d37641-cfd6-4be6-9a58-dd566160d0ed` | 同上 |
| 2026-10-14 | 顔のアップ 強面案 K1 | soul_2 | 938673 | job `2604da61-3a14-41c8-8d3d-0000e0629e50` | 別方向の案:60代後半〜70歳前後、白髪多め、鋭い目つき・一文字の口元(怒ってはいない)。ユーザー依頼 |
| 2026-10-14 | 顔のアップ 強面案 K2 | soul_2 | 722899 | job `582953e4-d461-4a40-80c2-134c52caaa1e` | 同上 |
| 2026-10-14 | 顔のアップ 強面強化案 K3 | soul_2 | 619077 | job `dd0d6949-be2d-4cec-9bd1-9409609dfc2b` | K案より強面を強化:70歳前後、短く刈った白髪、太く低い眉、上目づかいの鋭い視線、口角やや下がり、角ばったあご、横からの光。傷・刺青なし |
| 2026-10-14 | 顔のアップ 強面強化案 K4 | soul_2 | 676038 | job `97a47d7b-0773-4012-ae2c-62b2a5fc65f7` | 同上 |
| 2026-10-14 | S1/S2 に眼鏡・タバコ追加(失敗) | soul_2(参照画像つき) | 各種 | S1元: `7d56860a…` `de91bb33…` `8e90ad8f…` / S2元: `65168c07…` `9e78a631…` `5b60dd1e…` | **失敗の可能性が高い**:soul_2 に参照画像を渡すと、プロンプトが自動で参照画像の説明文に置き換わり、眼鏡・タバコの指示が消えていた(笑顔・「モデル風」などの記述も追加されていた)。soul_2 の参照画像は編集には使えない |
| 2026-10-14 | 小物パターン S1-① | gpt_image_2_5(画像編集) | — | job `caa1960c-855a-48c3-92d8-83e43d2c136c` | 細い金属フレーム(ガンメタル)。元画像を編集。出力は 880×1168(低画質設定)。0.25クレジット |
| 2026-10-14 | 小物パターン S1-② | gpt_image_2_5(画像編集) | — | job `627a65ce-0533-47fb-bd77-b53a65d68e66` | 黒縁セルフレーム。元画像を編集。出力は 880×1168(低画質設定)。0.25クレジット |
| 2026-10-14 | 小物パターン S1-③ | gpt_image_2_5(画像編集) | — | job `69356d31-7af1-49f4-9cad-8ad09bd5e684` | 金の老眼鏡を鼻にずらし上目づかい。元画像を編集。出力は 880×1168(低画質設定)。0.25クレジット |
| 2026-10-14 | 小物パターン S1-④ | gpt_image_2_5(画像編集) | — | job `1beab7b0-cfe3-49bf-9526-6afe78429e9f` | タバコのみ。元画像を編集。出力は 880×1168(低画質設定)。0.25クレジット |
| 2026-10-14 | 小物パターン S1-⑤ | gpt_image_2_5(画像編集) | — | job `fb3d5c92-1994-4e1e-8fc6-383176ef9036` | 黒縁+タバコ。元画像を編集。出力は 880×1168(低画質設定)。0.25クレジット |
| 2026-10-14 | 小物パターン S1-⑥ | gpt_image_2_5(画像編集) | — | job `162e2262-72bf-4c4d-a826-419bf97a2598` | 昭和風の薄茶レンズ眼鏡+タバコ。元画像を編集。出力は 880×1168(低画質設定)。0.25クレジット |
| 2026-10-14 | 小物パターン S2-① | gpt_image_2_5(画像編集) | — | job `ebfb715c-7286-4186-8b1f-38c2f10f8137` | 細い金属フレーム(ガンメタル)。元画像を編集。出力は 880×1168(低画質設定)。0.25クレジット |
| 2026-10-14 | 小物パターン S2-② | gpt_image_2_5(画像編集) | — | job `5bd6483d-3af6-490d-a3d3-9f91ed365427` | 黒縁セルフレーム。元画像を編集。出力は 880×1168(低画質設定)。0.25クレジット |
| 2026-10-14 | 小物パターン S2-③ | gpt_image_2_5(画像編集) | — | job `44a777f5-df0e-4d1e-9696-cb4332e52cf3` | 金の老眼鏡を鼻にずらし上目づかい。元画像を編集。出力は 880×1168(低画質設定)。0.25クレジット |
| 2026-10-14 | 小物パターン S2-④ | gpt_image_2_5(画像編集) | — | job `f8686a8e-b209-4748-8327-c98cfe75d1c0` | タバコのみ。元画像を編集。出力は 880×1168(低画質設定)。0.25クレジット |
| 2026-10-14 | 小物パターン S2-⑤ | gpt_image_2_5(画像編集) | — | job `d6238920-c805-44dc-967e-d8ee7d2481cb` | 黒縁+タバコ。元画像を編集。出力は 880×1168(低画質設定)。0.25クレジット |
| 2026-10-14 | 小物パターン S2-⑥ | gpt_image_2_5(画像編集) | — | job `1af22a59-9b65-41f0-9c7b-595f7d984431` | 昭和風の薄茶レンズ眼鏡+タバコ。元画像を編集。出力は 880×1168(低画質設定)。0.25クレジット |
| 2026-10-14 | 参考写真ベース R1 | nano_banana_pro(表示は nano_banana_2) | — | job `af8e291f-a00c-44a4-b531-14050808b35b` | 50代半ば・丸眼鏡・歯を見せた笑顔。ユーザーの参考写真(media `804f1c99…`)を添付し「同タイプの別人」を指示。2k・2クレジット |
| 2026-10-14 | 参考写真ベース R2 | nano_banana_pro(表示は nano_banana_2) | — | job `313d4389-f22d-4306-9ec9-be042b265c7e` | 50代半ば・丸眼鏡・落ち着いた顔。ユーザーの参考写真(media `804f1c99…`)を添付し「同タイプの別人」を指示。2k・2クレジット(記録時点で処理中) |
| 2026-10-14 | 参考写真ベース R3 | nano_banana_pro(表示は nano_banana_2) | — | job `4f019b47-6f2b-4d5c-bdb6-c346707a24c0` | 50代半ば・眼鏡なし・落ち着いた顔(少し笑み)。ユーザーの参考写真(media `804f1c99…`)を添付し「同タイプの別人」を指示。2k・2クレジット |
| 2026-10-14 | 参考写真ベース R4 | nano_banana_pro(表示は nano_banana_2) | — | job `54650954-c66f-4993-b039-7a9e249ba135` | 50代後半・白髪多め・丸眼鏡・口を閉じた笑顔。ユーザーの参考写真(media `804f1c99…`)を添付し「同タイプの別人」を指示。2k・2クレジット |
| 2026-10-14 | ハードボイルド案 H1 | soul_2(文章のみ) | 808984 | job `0c53f141-4eaf-49ff-8c34-ce23c0cd09d6` | 50代前半〜半ば・長めのウェーブ髪・黒縁ウェリントン(透明レンズ)・無精ひげ・無表情・カーディガン。ユーザーのイラスト参考画像の特徴を文章化(色味・画風は真似しない、実写) |
| 2026-10-14 | ハードボイルド案 H2 | soul_2(文章のみ) | 732777 | job `07331ecd-12cc-4201-81b6-85ece9a1893b` | 同上・口元を少しゆるめた顔・チャコールのシャツ。ユーザーのイラスト参考画像の特徴を文章化(色味・画風は真似しない、実写) |
| 2026-10-14 | ハードボイルド案 H3 | soul_2(文章のみ) | 275161 | job `a537f7fb-709b-45a4-a7a1-cd8bd85246f9` | 50代後半・白髪半分・無表情・カーディガン。ユーザーのイラスト参考画像の特徴を文章化(色味・画風は真似しない、実写) |
| 2026-10-14 | ハードボイルド案 H4 | soul_2(文章のみ) | 381184 | job `208d03eb-3c15-45ad-b2f9-09cde2a02f0a` | 50代前半〜半ば・髪を後ろで束ねる・無表情・チャコールのシャツ。ユーザーのイラスト参考画像の特徴を文章化(色味・画風は真似しない、実写) |
| 2026-10-14 | H1派生 V1 | gpt_image_2_5(編集・medium・1k) | — | job `7c7557d4-c6c2-4f59-8690-adc7283f524d` | 元:H1(`0c53f141…`、ユーザーが「イメージに近い」と選定)。薄いグレーレンズ(基本)。0.5クレジット |
| 2026-10-14 | H1派生 V2 | gpt_image_2_5(編集・medium・1k) | — | job `4cc1f3e9-1c18-4a39-a412-59e569acee57` | 元:H1(`0c53f141…`、ユーザーが「イメージに近い」と選定)。薄い茶色レンズ(基本)。0.5クレジット |
| 2026-10-14 | H1派生 V3 | gpt_image_2_5(編集・medium・1k) | — | job `c4fa4a3f-c536-458e-96c1-bc8c34433ce8` | 元:H1(`0c53f141…`、ユーザーが「イメージに近い」と選定)。こわめ(眉を寄せ鋭い目)。0.5クレジット |
| 2026-10-14 | H1派生 V4 | gpt_image_2_5(編集・medium・1k) | — | job `4b6cd821-f38b-4698-bfa4-fe7f47203e12` | 元:H1(`0c53f141…`、ユーザーが「イメージに近い」と選定)。かなりこわめ(頬こけ・上目の睨み)。0.5クレジット |
| 2026-10-14 | H1派生 V5 | gpt_image_2_5(編集・medium・1k) | — | job `864123d9-a884-47bc-87a8-a9ca3fccdeb1` | 元:H1(`0c53f141…`、ユーザーが「イメージに近い」と選定)。やさしめ(目元ゆるめ)。0.5クレジット |
| 2026-10-14 | H1派生 V6 | gpt_image_2_5(編集・medium・1k) | — | job `55deed21-846a-4ae8-afce-8108b4231aeb` | 元:H1(`0c53f141…`、ユーザーが「イメージに近い」と選定)。やさしい微笑み・茶レンズ。0.5クレジット |
| 2026-10-14 | H1派生 V7 | gpt_image_2_5(編集・medium・1k) | — | job `797c2a73-a6f5-4e3d-8a06-d2bcc0d7ff81` | 元:H1(`0c53f141…`、ユーザーが「イメージに近い」と選定)。白髪6割。0.5クレジット |
| 2026-10-14 | H1派生 V8 | gpt_image_2_5(編集・medium・1k) | — | job `1b680e35-571f-4acd-9eef-cdd2e696bb77` | 元:H1(`0c53f141…`、ユーザーが「イメージに近い」と選定)。ほぼ黒髪。0.5クレジット |
| 2026-10-14 | H1派生 V9 | gpt_image_2_5(編集・medium・1k) | — | job `0248638d-2150-43de-b337-59c9a8ac6bc5` | 元:H1(`0c53f141…`、ユーザーが「イメージに近い」と選定)。ダークブラウン髪・茶レンズ。0.5クレジット |
| 2026-10-14 | H1派生 V10 | gpt_image_2_5(編集・medium・1k) | — | job `a87ee9a0-c175-4b0a-abec-7d0920a0d683` | 元:H1(`0c53f141…`、ユーザーが「イメージに近い」と選定)。ほぼ銀髪。0.5クレジット |
| 2026-10-14 | H1派生 V11 | gpt_image_2_5(編集・medium・1k) | — | job `117f9860-de65-4583-b87b-57a15dcb3647` | 元:H1(`0c53f141…`、ユーザーが「イメージに近い」と選定)。白髪6割+こわめ。0.5クレジット |
| 2026-10-14 | H1派生 V12 | gpt_image_2_5(編集・medium・1k) | — | job `77a61026-f678-44f5-8b2c-c69d31202bfb` | 元:H1(`0c53f141…`、ユーザーが「イメージに近い」と選定)。ダークブラウン髪+やさしめ・茶レンズ。0.5クレジット |
| 2026-10-14 | 確定顔の角度違い A1 | nano_banana_pro(表示は nano_banana_2) | — | job `c5b1d390-46af-48e9-b771-bec1a0696330` | 元:確定顔(media `a71d9d49-8fb4-42a7-8d4f-623b1a528725`)。正面。3:4・2k・2クレジット |
| 2026-10-14 | 確定顔の角度違い A2 | nano_banana_pro(表示は nano_banana_2) | — | job `80c821b6-dcca-4cc5-9d1c-2e86c48d6658` | 元:確定顔(media `a71d9d49-8fb4-42a7-8d4f-623b1a528725`)。左斜め45度。3:4・2k・2クレジット |
| 2026-10-14 | 確定顔の角度違い A3 | nano_banana_pro(表示は nano_banana_2) | — | job `4fcc6848-d616-4b0c-9d15-fe3406b747b6` | 元:確定顔(media `a71d9d49-8fb4-42a7-8d4f-623b1a528725`)。右斜め45度。3:4・2k・2クレジット |
| 2026-10-14 | 確定顔の角度違い A4 | nano_banana_pro(表示は nano_banana_2) | — | job `34b48611-a9c5-4b78-8f05-e9250baaebe8` | 元:確定顔(media `a71d9d49-8fb4-42a7-8d4f-623b1a528725`)。左の真横。3:4・2k・2クレジット |
| 2026-10-14 | 確定顔の角度違い A5 | nano_banana_pro(表示は nano_banana_2) | — | job `d1603b8d-abef-4ad0-b1d4-344ffaf83d69` | 元:確定顔(media `a71d9d49-8fb4-42a7-8d4f-623b1a528725`)。右の真横。3:4・2k・2クレジット |
| 2026-10-14 | 確定顔の角度違い A6 | nano_banana_pro(表示は nano_banana_2) | — | job `0cb68d4c-13b9-4412-a624-2a646a0d79eb` | 元:確定顔(media `a71d9d49-8fb4-42a7-8d4f-623b1a528725`)。下から見上げる。3:4・2k・2クレジット |
| 2026-10-14 | 確定顔の角度違い A7 | nano_banana_pro(表示は nano_banana_2) | — | job `4736cfe0-da5a-4a49-a72a-d3f51297d663` | 元:確定顔(media `a71d9d49-8fb4-42a7-8d4f-623b1a528725`)。上から見下ろす(新聞を読む目線)。3:4・2k・2クレジット |
| 2026-10-14 | 確定顔の角度違い A8 | nano_banana_pro(表示は nano_banana_2) | — | job `ee8c80d0-f9c1-4b8f-a524-76b233fdbff1` | 元:確定顔(media `a71d9d49-8fb4-42a7-8d4f-623b1a528725`)。斜め後ろから振り返る。3:4・2k・2クレジット |
| 2026-10-14 | 試作動画用キーフレーム(喫茶店・柄シャツ) | nano_banana_pro(表示は nano_banana_2) | — | job `f631a787-f081-4f78-ac31-d7a9b5e7a98f` | 参照:A1・A2・A7。9:16・2k。レトロなペイズリー柄の開襟シャツ、昭和の喫茶店、競馬新聞・赤鉛筆・灰皿のタバコ・コーヒー。2クレジット |
| 2026-10-14 | キーフレーム修正版(灰皿は空) | nano_banana_pro(表示は nano_banana_2) | — | job `4ab75dc6-0705-4764-8bb6-16f724262d58` | 右手に赤鉛筆・左手でタバコを吸う。ユーザーが途中で止めたが送信済みだったため生成された。2クレジット |
| 2026-10-14 | キーフレーム修正版(吸い殻山盛り) | nano_banana_pro(表示は nano_banana_2) | — | job `fa9f3ae0-ff35-492d-8cad-7a9876fc9f58` | 右手に赤鉛筆・左手でタバコを吸う・灰皿に大量の吸い殻。参照:前キーフレーム+A1。2クレジット |
| 2026-10-14 | キーフレーム修正版3(灰皿のタバコ削除・吸い殻さらに増量) | nano_banana_pro(表示は nano_banana_2) | — | job `f91175a5-ad72-493f-8dd0-d032b7cf6eae` | 参照:修正版(`fa9f3ae0…`)+A1。火のついたタバコは左手の1本のみ。2クレジット |
| 2026-10-14 | 試作動画 v1(ドラマ風カット割り) | seedance_2_5(omni_reference・720p・10秒・音声あり) | — | job `d52b4153-b572-49c4-886e-27cc5b723c71` | 参照:キーフレーム修正版3(`f91175a5…`)+A1+A2。4カット:吸って煙を吐く→灰皿に勢いよく押し付けて消す→新聞のアップに赤丸→ティルトアップで顔、日本語セリフ「……1番人気? 強えよ。でもな、このオッズじゃ買わねえ。」。ガムを噛み続ける。約70クレジット |
| 2026-10-14 | 試作動画 v2(ガム常時・低い声・ゆっくり) | seedance_2_5(omni_reference・720p・15秒・音声あり) | — | job `dc04fead-1e0a-4d17-9ba3-c985a4ff9f63` | v1からの変更:最初から最後までくちゃくちゃガムを噛む/非常に低く太い渋い声/ゆっくり貫禄ある話し方で間を長く/セリフ区間を6.5〜15秒に拡大。セリフ「……一番人気か。」「強えよ。」「……でもな。」「このオッズじゃ……買わねえ。」。約105クレジット |
| 2026-10-15 | 服装案 O1(前後左右) | nano_banana_pro(表示は nano_banana_2) | — | job `1efffee3-4628-46f7-b715-54fa72281d51` | レトロなペイズリー柄シャツ+黒スラックス+茶ローファー。参照:A1・A2・A4。16:9・2k・2クレジット |
| 2026-10-15 | 服装案 O2(前後左右) | nano_banana_pro(表示は nano_banana_2) | — | job `d4bdea3d-c925-42c0-b76f-43e72bcda024` | 着古した黒レザージャケット+白T+ジーンズ+エンジニアブーツ。参照:A1・A2・A4。16:9・2k・2クレジット |
| 2026-10-15 | 服装案 O3(前後左右) | nano_banana_pro(表示は nano_banana_2) | — | job `525dbe2d-1caa-41fa-8842-0374b8476786` | グレーのツイードジャケット+黒タートルネック+チャコールパンツ。参照:A1・A2・A4。16:9・2k・2クレジット |
| 2026-10-15 | 服装案 O4(前後左右) | nano_banana_pro(表示は nano_banana_2) | — | job `2e804263-7f0d-46b3-a955-6ce39c2abebe` | ベージュのトレンチコート+柄シャツ+黒スラックス(探偵風)。参照:A1・A2・A4。16:9・2k・2クレジット |
| 2026-10-15 | 服装案 O5(前後左右) | nano_banana_pro(表示は nano_banana_2) | — | job `c441640a-d233-4f87-a5b1-2971afdd24bd` | 黒のレトロ花柄開襟シャツ+ワイドスラックス+金の細いブレスレット(昭和風)。参照:A1・A2・A4。16:9・2k・2クレジット |
| 2026-10-15 | 服装案 O6(前後左右) | nano_banana_pro(表示は nano_banana_2) | — | job `77beb6b0-4bed-422f-90da-b56bc8fccf3e` | オリーブのミリタリージャケット+紺シャンブレーシャツ+チノ+白スニーカー。参照:A1・A2・A4。16:9・2k・2クレジット |
| 2026-10-15 | Soul登録用 T1 | nano_banana_pro(表示は nano_banana_2) | — | job `5d4b374c-2dbc-482b-937c-bb2cd5c333ec` | 顔アップ・正面・無表情・グレー背景。服装O2(黒ライダース+白T+ジーンズ+エンジニアブーツ)。参照:A1/A2等+O2シート。2k・2クレジット |
| 2026-10-15 | Soul登録用 T2 | nano_banana_pro(表示は nano_banana_2) | — | job `cfd50a42-fa6c-48fb-8e28-6ce231106c67` | 顔アップ・左斜め・口の端で笑う・暗い背景。服装O2(黒ライダース+白T+ジーンズ+エンジニアブーツ)。参照:A1/A2等+O2シート。2k・2クレジット |
| 2026-10-15 | Soul登録用 T3 | nano_banana_pro(表示は nano_banana_2) | — | job `1528064a-15b1-4b1e-bc0f-10d0e413999c` | 顔アップ・右斜め・険しい顔・屋外の曇り。服装O2(黒ライダース+白T+ジーンズ+エンジニアブーツ)。参照:A1/A2等+O2シート。2k・2クレジット |
| 2026-10-15 | Soul登録用 T4 | nano_banana_pro(表示は nano_banana_2) | — | job `9df8c192-f286-4e12-8f7d-ba3bf7547635` | 左の横顔。服装O2(黒ライダース+白T+ジーンズ+エンジニアブーツ)。参照:A1/A2等+O2シート。2k・2クレジット |
| 2026-10-15 | Soul登録用 T5 | nano_banana_pro(表示は nano_banana_2) | — | job `08ef0d99-f9b0-4f7c-8788-b83bd2b27f72` | 腰上・正面・腕組み・レンガ壁。服装O2(黒ライダース+白T+ジーンズ+エンジニアブーツ)。参照:A1/A2等+O2シート。2k・2クレジット |
| 2026-10-15 | Soul登録用 T6 | nano_banana_pro(表示は nano_banana_2) | — | job `4c9d601d-ce54-4c8d-8afd-98693f829676` | 胸上・喫茶店・ガムを噛み窓の外を見る。服装O2(黒ライダース+白T+ジーンズ+エンジニアブーツ)。参照:A1/A2等+O2シート。2k・2クレジット |
| 2026-10-15 | Soul登録用 T7 | nano_banana_pro(表示は nano_banana_2) | — | job `75cd7102-45ce-4ff2-97ef-8927e98e4d0a` | 全身・ポケットに手・夕方の商店街(9:16)。服装O2(黒ライダース+白T+ジーンズ+エンジニアブーツ)。参照:A1/A2等+O2シート。2k・2クレジット |
| 2026-10-15 | Soul登録用 T8 | nano_banana_pro(表示は nano_banana_2) | — | job `4aa425cd-a5f2-420e-be36-07a16e819263` | 全身・新聞を脇に歩く・昼の裏通り(9:16)。服装O2(黒ライダース+白T+ジーンズ+エンジニアブーツ)。参照:A1/A2等+O2シート。2k・2クレジット |
| 2026-10-15 | Soul登録用 T9 | nano_banana_pro(表示は nano_banana_2) | — | job `46d25f02-3940-40c1-a2da-dab617343289` | 座って新聞に赤鉛筆・やや上から。服装O2(黒ライダース+白T+ジーンズ+エンジニアブーツ)。参照:A1/A2等+O2シート。2k・2クレジット |
| 2026-10-15 | Soul登録用 T10 | nano_banana_pro(表示は nano_banana_2) | — | job `53f72837-dec4-4480-88fe-176ff5c771c1` | 腰上・下から見上げる・青空。服装O2(黒ライダース+白T+ジーンズ+エンジニアブーツ)。参照:A1/A2等+O2シート。2k・2クレジット |
| 2026-10-15 | Soul登録用 T11 | nano_banana_pro(表示は nano_banana_2) | — | job `e4060716-7a26-497b-ba47-016465b67fe6` | 顔アップ・正面・歯を見せて笑う。服装O2(黒ライダース+白T+ジーンズ+エンジニアブーツ)。参照:A1/A2等+O2シート。2k・2クレジット |
| 2026-10-15 | Soul登録用 T12 | nano_banana_pro(表示は nano_banana_2) | — | job `023f5533-ae4e-4a4b-b392-2d5fde1249c3` | 半身・夜のネオン街。服装O2(黒ライダース+白T+ジーンズ+エンジニアブーツ)。参照:A1/A2等+O2シート。2k・2クレジット |
| 2026-10-15 | 白背景リファレンス W1 | nano_banana_pro(表示は nano_banana_2) | — | job `be001a24-84b9-4418-885b-ae99ade2146c` | 全身・正面。背景は真っ白のみ。服装O2。全身9:16/顔3:4・2k・2クレジット |
| 2026-10-15 | 白背景リファレンス W2 | nano_banana_pro(表示は nano_banana_2) | — | job `5f7a3527-445b-4828-8557-0512f38db778` | 全身・背面。背景は真っ白のみ。服装O2。全身9:16/顔3:4・2k・2クレジット |
| 2026-10-15 | 白背景リファレンス W3 | nano_banana_pro(表示は nano_banana_2) | — | job `f5526e73-f478-4130-be91-d1d05fed74d5` | 全身・左側面。背景は真っ白のみ。服装O2。全身9:16/顔3:4・2k・2クレジット |
| 2026-10-15 | 白背景リファレンス W4 | nano_banana_pro(表示は nano_banana_2) | — | job `6f122945-794f-449f-8667-7f52650bd034` | 全身・右側面。背景は真っ白のみ。服装O2。全身9:16/顔3:4・2k・2クレジット |
| 2026-10-15 | 白背景リファレンス W5 | nano_banana_pro(表示は nano_banana_2) | — | job `16db1d50-8205-4c9c-b3a8-633184ba17ee` | 全身・左斜め45度。背景は真っ白のみ。服装O2。全身9:16/顔3:4・2k・2クレジット |
| 2026-10-15 | 白背景リファレンス W6 | nano_banana_pro(表示は nano_banana_2) | — | job `597e7749-cfb6-4d44-81f2-30a2c746fe86` | 全身・右斜め45度。背景は真っ白のみ。服装O2。全身9:16/顔3:4・2k・2クレジット |
| 2026-10-15 | 白背景リファレンス W7 | nano_banana_pro(表示は nano_banana_2) | — | job `7a79c68e-cc18-4ba3-8e59-3c88a0449c37` | 顔アップ・正面。背景は真っ白のみ。服装O2。全身9:16/顔3:4・2k・2クレジット |
| 2026-10-15 | 白背景リファレンス W8 | nano_banana_pro(表示は nano_banana_2) | — | job `79df8831-8126-48f3-bfe9-3381b2754431` | 顔アップ・背面(後頭部)。背景は真っ白のみ。服装O2。全身9:16/顔3:4・2k・2クレジット |
| 2026-10-15 | 白背景リファレンス W9 | nano_banana_pro(表示は nano_banana_2) | — | job `3283e43d-0a88-4e3d-a48d-869243943230` | 顔アップ・左側面。背景は真っ白のみ。服装O2。全身9:16/顔3:4・2k・2クレジット |
| 2026-10-15 | 白背景リファレンス W10 | nano_banana_pro(表示は nano_banana_2) | — | job `3d9a2e54-3607-45b5-a00d-209cac65a43d` | 顔アップ・右側面。背景は真っ白のみ。服装O2。全身9:16/顔3:4・2k・2クレジット |
| 2026-10-15 | 白背景リファレンス W11 | nano_banana_pro(表示は nano_banana_2) | — | job `6a309490-7aeb-43c2-8dcf-f4a4e9ac2e9a` | 顔アップ・左斜め45度。背景は真っ白のみ。服装O2。全身9:16/顔3:4・2k・2クレジット |
| 2026-10-15 | 白背景リファレンス W12 | nano_banana_pro(表示は nano_banana_2) | — | job `8b1e70f4-796a-4602-b813-50e43d3404ac` | 顔アップ・右斜め45度。背景は真っ白のみ。服装O2。全身9:16/顔3:4・2k・2クレジット |
| 2026-10-15 | 表情 E1 | nano_banana_pro(表示は nano_banana_2) | — | job `1a84fe0c-d385-4928-8349-7df78724dd3c` | 喜(歯を見せて笑う)。白背景・顔アップ3:4・2k。Soul学習用。2クレジット |
| 2026-10-15 | 表情 E2 | nano_banana_pro(表示は nano_banana_2) | — | job `474b9ac0-693c-4995-b2f3-0bcabc6c497c` | 怒(眉間にシワ・睨む)。白背景・顔アップ3:4・2k。Soul学習用。2クレジット |
| 2026-10-15 | 表情 E3 | nano_banana_pro(表示は nano_banana_2) | — | job `09b37772-e2fa-49f1-8340-78e0d7095340` | 哀(目を伏せる)。白背景・顔アップ3:4・2k。Soul学習用。2クレジット |
| 2026-10-15 | 表情 E4 | nano_banana_pro(表示は nano_banana_2) | — | job `e3070460-41ee-42ee-951a-e6ee05ee9079` | 楽(口の端で笑う)。白背景・顔アップ3:4・2k。Soul学習用。2クレジット |
| 2026-10-15 | 表情 E5 | nano_banana_pro(表示は nano_banana_2) | — | job `1e6a8bae-f5e2-4cf2-a0a2-2b590d00d097` | 話している途中。白背景・顔アップ3:4・2k。Soul学習用。2クレジット |
| 2026-10-15 | 表情 E6 | nano_banana_pro(表示は nano_banana_2) | — | job `8a66572c-a3df-49db-9b99-353c81220f16` | ガムを噛んでいる。白背景・顔アップ3:4・2k。Soul学習用。2クレジット |
| 2026-10-15 | Soul キャラクター「谷上」学習開始 | show_characters(soul_2) | — | soul_id `bf3b5939-8514-4b3e-9f79-1c81b0fc8c72` | W1〜W12+E1〜E6の18枚(後ろ姿2枚を含む、ユーザー指定)。学習費用25クレジット(取引履歴で確認) |
| 2026-10-15 | 半生#1 前半A 案1 | soul_2(Soul「谷上」) | — | job `41150956-36ae-46e8-b77b-6d311cc930a2` | 現在の谷上・喫茶店・新聞越しにカメラを見る顔のアップ。9:16 |
| 2026-10-15 | 半生#1 前半A 案2 | soul_2(Soul「谷上」) | — | job `28302862-684e-42c5-a8f6-52abe8ab2ce8` | 同上 |
| 2026-10-15 | 半生#1 後半B 案1 | nano_banana_pro(表示は nano_banana_2) | — | job `df6d16e3-3f7b-483a-902a-87cc3789a3d3` | セピア。昭和の茶の間、テレビの光で口元がゆるむ父の横顔シルエットと見上げる少年(後ろ姿)。9:16・2k・2クレジット |
| 2026-10-15 | 半生#1 後半B 案2 | nano_banana_pro(表示は nano_banana_2) | — | job `49f4830c-9102-4424-8ae9-242b2f5a8343` | 同上 |
| 2026-10-15 | 半生#1 前半A 修正1 | soul_2(Soul「谷上」) | — | job `b9ec879b-abe3-46ad-b961-46f44713b662` | 火のついたタバコをくわえる/日本語の競馬新聞(縦書きの出走表・◎○▲△・赤丸、実在の紙名なし)。9:16 |
| 2026-10-15 | 半生#1 前半A 修正2 | soul_2(Soul「谷上」) | — | job `cadf32b9-1707-405b-adbd-d6cb7e750a9b` | 火のついたタバコをくわえる/日本語の競馬新聞(縦書きの出走表・◎○▲△・赤丸、実在の紙名なし)。9:16 |
| 2026-10-15 | 半生#1 前半A 動画 v1 | seedance_2_5(omni_reference・480p・15秒・音声あり) | — | job `be9269b9-8e3f-4658-8f00-66b9e4ee3e48` | 最初の1コマ:前半A修正案2(`cadf32b9…`)+参照W7。4ショット:今の谷上がタバコを離して煙を吐き「……親父は、笑わねえ男だった。」→セピアの茶の間→震える箸の手「……家じゃ、いつも息が詰まった。」→父がテレビをつける。45クレジット。後半Bはユーザー指示でまだ作らない |
| 2026-10-16 | 半生#1 後半B 動画 v1 | seedance_2_5(omni_reference・480p・15秒・音声あり) | — | job `0c239caf-8b13-456c-b9ad-4cd1bdfef3fc` | 最初の1コマ:後半B案2(`49f4830c…`)+参照:前半A修正案2・W7。4ショット:テレビの光で父の口元がゆるむ「……でもな。競馬を見てる時だけは、違った。」→父の手が少年の頭に→ブラウン管の馬群の光→今の谷上が赤丸「……あの横顔が、俺の始まりだ。」。約45クレジット |
| 2026-10-16 | 本編(life01) S1 最初の1コマ(不採用) | nano_banana_pro | — | job `72b384d5-200e-4e48-87a3-175e1e19e203` | 蹄の超アップ(地面すれすれ)。9:16 |
| 2026-10-16 | 本編(life01) S1 参照(谷上) | soul_2(Soul「谷上」) | — | job `997fdb10-f74d-4da3-a4d1-623a45ad2f8f` | 総立ちの中で一人座る谷上、馬券を指に挟む。9:16 |
| 2026-10-16 | 本編(life01) S2 最初の1コマ | nano_banana_pro | — | job `11bd2915-23cf-4019-928e-e57d74e7c08c` | セピア。子どもの手が父の指を握る。9:16 |
| 2026-10-16 | 本編(life01) S3 最初の1コマ | nano_banana_pro | — | job `ffa78c39-45dd-4d0b-87ea-d82eff3a1826` | 80年代フィルム調。薄い給料袋から千円札を抜く若い手。9:16 |
| 2026-10-16 | 本編(life01) S4 最初の1コマ | nano_banana_pro | — | job `dbd37684-88f1-4c6c-9295-1fa18491558a` | 深夜の机。赤鉛筆が出走表を走る、「けいば」ノートの山。9:16 |
| 2026-10-16 | 本編(life01) S5 最初の1コマ | nano_banana_pro | — | job `d42edb1e-5912-4fe1-ab2d-1bc03f71d8a6` | 夕暮れ、ゴール前の馬の脚(地面すれすれ)。9:16 |
| 2026-10-16 | 本編(life01) S5 参照(谷上) | soul_2(Soul「谷上」) | — | job `9d0999b8-7af3-4db0-8715-cba2caaba270` | 夕暮れの競馬場を去る谷上の後ろ姿。9:16 |
| 2026-10-16 | 本編(life01) ノート表紙テスト | nano_banana_pro | — | job `828ee529-5546-4963-9bf5-324a06ebc98d` | セピア。昭和の学習帳に子どもの字で「けいば 一」。9:16 |
| 2026-10-16 | 本編(life01) 静止画8枚 | — | — | — | **ユーザー判断で全8枚不採用**(出来が良くないため)。以後は画像を使わずプロンプトのみで動画化 |
| 2026-10-16 | 本編(life01) S1 動画 v1(プロンプトのみ) | seedance_2_5(t2v・480p・15秒・音声あり) | — | job `362e9cff-271f-4ab4-959b-b84cb96cbd04` | **差し替え済み(顔が谷上と違う → S1 v2 へ)**。第1幕「今・勝利」#1〜#13。谷上は文章の描写のみ(参照画像なし)。約45クレジット |
| 2026-10-16 | 本編(life01) S2 動画 v1(プロンプトのみ) | seedance_2_5(t2v・480p・15秒・音声あり) | — | job `073d639f-3ec0-4ab2-b658-3749112f344e` | 第2幕「父」。セピア12ショット:父の指を握る手→茶の間→震える箸→テレビ→父の口元がゆるむ→肩車→「脚を見ろ」→並ぶ赤鉛筆→「けいば 一」→夕日を去る父子。モノローグ3行。約45クレジット |
| 2026-10-16 | 本編(life01) S3 動画 v1(プロンプトのみ) | seedance_2_5(t2v・480p・15秒・音声あり) | — | job `57eea0ba-fc89-4934-8c2d-f52b28c0eadd` | **失敗(安全フィルターでnsfw判定)**。第3幕「負け」。80年代フィルム調11ショット:給料袋→改札→窓口→違う馬→握りつぶす→季節の早送り「……負けた。」→夜の電車「……何度も、負けた。」→空の財布→机に外れ馬券→「けいば 一」→新しいノートの1ページ目「……負けにも、理由がある。」。若い谷上の顔は映さない。約45クレジット |
| 2026-10-16 | 本編(life01) S3 動画 v2(プロンプトのみ・再挑戦) | seedance_2_5(t2v・480p・15秒・音声あり) | — | job `f6d1c602-baf4-46b7-8377-7c5125fd273f` | **差し替え(ノートの文字が崩れる → S3 v3 へ)**。v1がnsfw判定のため表現をやわらげて再生成:千円札・窓口でお金を出す描写を「券売り場で紙の券を受け取る」に、給料袋を「薄い封筒」に、年齢を「20代前半」に変更。流れとモノローグは同じ。約45クレジット |
| 2026-10-16 | 本編(life01) S4 動画 v1(プロンプトのみ) | seedance_2_5(t2v・480p・15秒・音声あり) | — | job `15a59b9b-5973-425d-9470-c3dbc003f70c` | **不採用(最後のカットの顔が谷上と大きく違う)**。第4幕「研究」。10ショット:赤鉛筆→レース映像の巻き戻し→馬場の土→掲示板を見上げる目→ノートが積み上がるタイムラプス→白髪が増える→床一面の「けいば」ノート→喫茶店の常連→1番人気に横線・別の馬に赤丸「……人気じゃねえ。」→今の谷上の目「……理由で買う。」。約45クレジット |
| 2026-10-16 | 本編(life01) S4 動画 v2(顔固定) | seedance_2_5(omni_reference・480p・15秒・音声あり) | — | job `0926e61c-3c80-4fa5-9ce5-ca69e80d5ed0` | **差し替え(「じんき」と読まれる → S4 v3 へ)**。確定顔の参照3枚(元画像 `a71d9d49…`・A1・W7)を image_references に入れ、プロンプトに顔の固定指示を追加。内容は v1 と同じ10ショット。約45クレジット |
| 2026-10-16 | 本編(life01) S5 動画 v1(顔固定) | seedance_2_5(omni_reference・480p・15秒・音声あり) | — | job `af0ee795-6a34-4577-a10e-9e6e624460cf` | **差し替え(構成変更 → S5 v2 へ)**。第5幕「答え合わせ」。確定顔の参照3枚つき。5ショット:馬の脚元のスロー→口の端で笑う「……親父。」→夕暮れを去る背中「……今日も、脚を見たぜ。」→スマホが震え眉をひそめる→暗転。約45クレジット |
| 2026-10-16 | 本編(life01) S1 動画 v2(ユーザー修正・顔固定) | seedance_2_5(omni_reference・480p・15秒・音声あり) | — | job `ef1f315a-b504-4ffc-b233-2baa50ba5a17` | **差し替え(実況の読み間違い等 → S1 v3 へ)**。ユーザー修正を反映:実況「1番人気が、まさかの失速!大波乱が起きました!!」/観客の喜び(抱き合う)と怒り(叫ぶ・馬券を破る)/ラストに谷上の決め台詞「……さぁ、今回はいくらになるかな。」/確定顔の参照3枚つき。12ショット(`life01.md` 8章)。約45クレジット |
| 2026-10-16 | 本編(life01) S1 動画 v3(ユーザー修正 第2弾) | seedance_2_5(omni_reference・**720p**・15秒・音声あり) | — | job `d1b8d96f-ab10-4c9a-b560-d29244ac3a74` | v1のカメラワークに戻す/実況はひらがなで「いちばんにんきが、まさかのしっそく!だいはらんがおきました!!」のみ/観客の喜びと怒り/正面から撮り馬券は裏面のみ/「……さあ、いくらになるかな。」→フェードアウト。参照:顔3枚+馬券 `440f1bd7…`。約105クレジット |
| 2026-10-16 | 本編(life01) S2 動画 v2(ユーザー修正) | seedance_2_5(t2v・**720p**・15秒・音声あり) | — | job `c1dbc048-d6ae-4cc8-ab2f-df6dd4b2751f` | **差し替え(父が上半身裸・指だけを握る → S2 v3 へ)**。v1と同じ12ショット。ナレーション「……『けつを見ろ』。それだけ教わった。」/#10 親父が競馬新聞に赤鉛筆で印をつける/#11 表紙を子どもの字で「けいばべんきょうノート」。約105クレジット |
| 2026-10-16 | 本編(life01) S2 動画 v3(ユーザー修正 第2弾) | seedance_2_5(t2v・**720p**・15秒・音声あり) | — | job `fce125b6-cfe7-42ba-bf92-dd12536067b9` | **差し替え(表紙の文字変更 → S2 v4 へ)**。v2の内容に加え、父の服装(グレーのカーディガン+白シャツ、競馬場ではジャケット)を全カットで指定し上半身裸を禁止/#1・#12 を手のひらごとしっかり手をつなぐ形に。台本は `life01_s2_script.md`。約105クレジット |
| 2026-10-16 | 本編(life01) S2 動画 v4(表紙修正) | seedance_2_5(t2v・**720p**・15秒・音声あり) | — | job `1ffe7fc2-32b8-4a5d-ad33-c5c0edaff5a5` | v3と同じ内容で、ノートの表紙を子どもの字の「けいば」だけに(数字・漢字なし)。約105クレジット |
| 2026-10-16 | 本編(life01) S3 動画 v3(ユーザー修正) | seedance_2_5(t2v・**720p**・15秒・音声あり) | — | job `91fe5532-063d-4a15-99e4-4a186d6c2632` | **不採用(ノートの日本語が崩れる → S3 v4 へ)**。v2と同じ流れ。最後のノートに赤鉛筆ではっきり「負けた理由/馬場が重い/外枠で不利/トモが細い」と書く/古いノートの表紙は「けいば」のみ。約105クレジット |
| 2026-10-16 | 本編(life01) S3 動画 v4(字を見せない) | seedance_2_5(t2v・**720p**・15秒・音声あり) | — | job `8ff4ecbf-ba5e-4444-8a48-0e80e8a18e9f` | 書き始めの一画ですぐカット→逆光で書き続けるシルエット(ページは見せない)。ほかはv3のまま。約105クレジット |
| 2026-10-16 | 本編(life01) S4 動画 v3(読み修正) | seedance_2_5(omni_reference・**720p**・15秒・音声あり) | — | job `8414371f-f158-4068-be35-bd47f89bd4de` | v2と同じ10ショット・顔の参照3枚。セリフをひらがな「……にんきじゃねえ。」+読み指定に。約105クレジット |
| 2026-10-16 | 本編(life01) S5 動画 v2(構成変更) | seedance_2_5(omni_reference・480p・15秒・音声あり) | — | job `5d38c423-22b4-41a5-99ec-4258e1d50215` | **差し替え(カット割りをおしゃれに → S5 v3 へ)**。S1の競馬場に戻る7ショット:ゴール→大観衆の中で立つ→「……親父。今日も、けつを見たぜ。」→精算機に馬券→一万円札の束→ニヤッと内ポケットへ→キメの止め絵。顔の参照3枚。約45クレジット |
| 2026-10-16 | 本編(life01) S5 動画 v3(おしゃれなカット割り) | seedance_2_5(omni_reference・**720p**・15秒・音声あり) | — | job `f237ab3f-a5a7-4307-acd4-2a7d1dc56d30` | 9ショット:レンズの映り込み→真上の空撮スピードランプ→観客のホイップパン→ピント送り→寄りで決め台詞→精算機の超アップ→受け口からのローアングル→金属パネルの映り込み→歩きながら白黒へ→振り返って止め絵。顔の参照3枚。約105クレジット |
| 2026-10-18 | 第2話 S1 動画 v1(雨と馬場・冒頭の細かいカット割り) | seedance_2_5(omni_reference・480p・15秒・音声あり) | — | job `cda00b75-7108-4b57-ba30-757977eb81c6` | **差し替え(「あられてる」と読まれる・明太子からいくらが出る → v2 へ)**。episode02.md 第4版 S1 の15カット(明太子→蹄の泥→ビール→雨の窓→泡→泥しぶき→食べる・飲む→全体→荒れた内→目「……内が、荒れてる。」→赤鉛筆→パドック「ほんめいは、もうてっぱんでしょう!」)。顔の参照3枚、ガムなし指定。約45クレジット |
| 2026-10-18 | 第2話 S1 動画 v2(読み・明太子の修正) | seedance_2_5(omni_reference・480p・15秒・音声あり) | — | job `228455eb-3588-4350-9fba-426feed66e4d` | **差し替え(明太子のイメージ違い・実況に意味がない → v3 へ)**。セリフをひらがな「……うちが、あれてる。」+読み指定(arareteru ではない)。明太子を「薄皮に包まれた細かい粒のスケトウダラの卵」と明記し、いくら・大粒の卵を禁止。「粒がほぐれる」表現を削除。約45クレジット |
| 2026-10-18 | 第2話 S1 動画 v3(明太子写真・実況修正) | seedance_2_5(omni_reference・480p・15秒・音声あり) | — | job `81ffff93-1a20-4802-9b4a-ff59666c9c1d` | 参照:顔3枚+ユーザー提供の明太子写真(media `3349a4f8…`、IMG_8693.JPG)。実況「あめのなか、かくばそろってさいごのちょくせんへ!」「うちはくるしい!そとから、そとからのびてくる!」、解説「きょうはおもばば。うちのしばはかなりいたんでいますね」「ほんめいは、もうてっぱんでしょう!」。約45クレジット |
| 2026-10-18 | 第2話 前半30秒(S1雨と馬場+S2パドックと返し馬) | seedance_2_5(omni_reference・480p・30秒・音声あり) | — | job `1a340b30-5d44-4c50-a163-6b9f59be632f` | **差し替え(「くのしてねえ」と読まれる → 720p 版へ)**。60秒版・30秒×2本の前半。カット1〜23。顔の参照3枚+明太子写真。谷上「……うちが、あれてる。」「……いれこんでる。」「……みちわるを、くにしてねえ。」「……にげがさんとう。まえは、つぶれる。」。約90クレジット |
| 2026-10-18 | 第2話 前半30秒 v2(読み修正・720p) | seedance_2_5(omni_reference・**720p**・30秒・音声あり) | — | job `b83f4f53-470e-4f92-9553-7dae25b227e0` | **採用(カット21は差し替えカット `9a80349e` に入れ替える)**。v1 と同じ内容。セリフを「……みちわるを、くに、してねえ。」と区切り、読み ku-NI(ku no ではない)を指定。約210クレジット |
| 2026-10-18 | 第2話 前半30秒 差し替え用セリフ音声 | seed_audio(wav・48kHz・話速 -30) | — | job `3203856d-1a6f-4405-8ee5-a4345114f51b` | **不採用(声質が動画と大きく違う)**。「……みちわるでも、はしれるあしだ。」。声の参考に前半30秒 720p 版(job `b83f4f53…`)の音声を使用。編集でカット21(24〜26秒)の音声と差し替える。約0.2クレジット |
| 2026-10-18 | 第2話 前半 差し替え用カット(4秒) | seedance_2_5(omni_reference・**720p**・4秒・音声あり) | — | job `091bcdac-de32-4f8e-8c00-fa764aa9e12c` | **不採用(服装が前半の動画と違う)**。カット21の差し替え用。谷上の横顔で「……みちわるでも、はしれるあしだ。」。顔の参照3枚。編集で前半30秒の24〜26秒あたりと入れ替える。28クレジット |
| 2026-10-18 | 第2話 前半 差し替え用カット v2(4秒) | seedance_2_5(omni_reference・**720p**・4秒・音声あり) | — | job `9a80349e-a02e-4869-8ea3-ca6cf7c2a7b9` | **採用(ユーザーOK)**。前半30秒 720p 版を動画参照(media `4c075208…`、job `b83f4f53…` を取り込み)に指定し、服装・部屋・光・声を合わせる指示。顔の参照2枚。「……みちわるでも、はしれるあしだ。」。28クレジット |
| 2026-10-18 | 第2話 後半30秒(S3レース+S4鼻ひとつ、届いた) | seedance_2_5(omni_reference・**720p**・30秒・音声あり) | — | job `bf60d5f0-1db2-4db0-9c71-ed035e5ac2c2` | カット24〜39。前半720p版を動画参照(media `4c075208…`)+顔の参照2枚+明太子写真。写真判定で鼻差の的中、「……はなひとつ、とどいたな。」「……きょうのビールは、うめえ。」「……つぎ。」。金額は映さない。約210クレジット |
| 2026-10-19 | 第2話 後半 写真判定のテレビ画面(差し替え用静止画)A | gpt_image_2_5(high・2k・9:16) | — | job `9e94f7d9-8b2b-4b56-9946-190e3d621497` | 後半30秒の写真判定カット(18〜20.5秒)で馬が向かい合ってしまったため、差し替え用に作成。2頭が同じ向き(左→右)で並び、外の馬が鼻差先着。約2.75クレジット |
| 2026-10-19 | 同上 B | gpt_image_2_5(high・2k・9:16) | — | job `023cf423-51c4-44c0-9686-ec1c9cf40d4d` | 同じ指示の別パターン。約2.75クレジット |
| 2026-10-20 | 第3話 前半30秒(S1〜S3) | seedance_2_5(omni_reference・480p・30秒・音声あり) | — | job `d7b535b0-9be1-4d5f-b5e7-a9196393995a` | episode03.md 第5版のカット1〜22。若者の大はしゃぎ→巻き戻し→心の声で読み→「……きょうのさいしゅうは、あれる。」→若者の全部流し→トリガミ→「……おれは、しぼる。」→大波乱のレース。顔の参照3枚。※カット8の読み指定に不要な文言(oikaze ja nee)が混入。約90クレジット |
