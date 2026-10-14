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
