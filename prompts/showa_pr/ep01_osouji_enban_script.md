# 第1話「自走式 床掃除機 ― おそうじ円盤」台本(2026-11-16 初稿)

- 尺:約46秒/24fps
- 画面:本編 4:3(1440×1080)。SNS用は 9:16(1080×1920)の中央に 4:3 を置き、上下の黒帯にシリーズ名
- ネタ:ロボット掃除機(一般名詞のみ。実在製品に似た形・ロゴは出さない)
- 笑いの軸:昭和の団地の茶の間に、**今ふうの白い円盤だけがポツンと現代のまま**いる。
  ナレーションはそれを人類の夢として本気で讃える

## 登場するもの(全カット共通。生成時は参照画像で固定する)
- **おそうじ円盤**:直径30cmほどの白い丸い円盤。上面はつるっとしていて、前に小さな黒い窓、緑のランプが1つ。
  ロゴ・文字なし。※あえて現代のデザインのまま(ここがズレの見せ場)
- **一家(4人)**:
  - 父:40歳くらい、七三分け、白いワイシャツに細いネクタイ、黒縁メガネ
  - 母:30代後半、ひざ丈のフレアスカートとカーディガン、パーマの短い髪
  - 長男:8歳くらい、半ズボンとボーダーのTシャツ、坊ちゃん刈り
  - 猫:三毛猫
- **茶の間**:団地の居間。畳の上に絨毯、低いちゃぶ台、ふすま、脚付きのブラウン管テレビ(電源オフ・画面は暗い)、
  花柄のカーテン、長椅子(ソファ)
- **研究所**:白い壁、黒板、製図台、白衣の技術者(30代男性と女性の2人)

## カット割りとナレーション
| # | 時間 | 画(カメラ) | ナレーション | テロップ(画面内) | 音 |
|---|---|---|---|---|---|
| 1 | 0.0–3.5 | 茶の間の床を、円盤がひとりでにスーッと進む。床の高さのローアングル、固定 | 「ご覧ください。この円盤、誰も押しておりません。」 | — | 映写機の回る音から開始 |
| 2 | 3.5–6.5 | **タイトルカード**(編集で作成) | (なし。音楽のジャーン) | 夢見ヶ丘電機 提供/あしたの暮らし 第一回/自走式 床掃除機 | BGM 開始 |
| 3 | 6.5–12.5 | 茶の間の全景。ちゃぶ台を囲む一家が、床を進む円盤を目で追い、母と長男が身を乗り出す。固定のフルショット | 「ここは、ごく普通のお茶の間。近い将来、床のお掃除は、機械の仕事となるのです。」 | — | |
| 4 | 12.5–17.5 | 円盤が壁(ふすま)にコツンと当たり、くるりと向きを変えて進む。斜め上から、固定 | 「壁にぶつかれば、自ら考え、向きを変える。まさに、電子頭脳であります。」 | 電子頭脳 | コツン(効果音) |
| 5 | 17.5–22.5 | 研究所。白衣の技術者2人が、黒板の円盤の図解を指し示しながら頷き合う。ゆっくり右へパン | 「開発したのは、わが社の若き技術陣。三年の歳月を、かけました。」 | 夢見ヶ丘電機 中央研究所 | |
| 6 | 22.5–27.5 | 円盤が長椅子の下にもぐっていく。長男が床にはいつくばって下をのぞきこむ | 「人の入れぬ長椅子の下へも、勇敢に、進んでまいります。」 | — | |
| 7 | 27.5–32.0 | 三毛猫が円盤の上にちょこんと座ったまま、円盤ごと茶の間を横切る。固定 | 「ご家庭の猫も、この通り……ご満悦。」 | — | (少し間をあける=笑いどころ) |
| 8 | 32.0–38.0 | 円盤が部屋のすみの充電台へ自分でゆっくり戻り、緑のランプが点く。ゆっくり寄り | 「そして、仕事を終えると……自分で、おうちへ帰る。なんと健気な機械で、ありましょう。」 | — | |
| 9 | 38.0–41.0 | 父が正座のまま、充電台の円盤に向かって深々とお辞儀する。母と長男も続いてお辞儀 | 「お父さんも、思わず、最敬礼。」 | — | |
| 10 | 41.0–46.0 | **エンドカード**(編集で作成) | 「明るい未来を、あなたのお茶の間へ。夢見ヶ丘電機。」 | 明日を、今日に。 夢見ヶ丘電機工業/(小さく)この映画は 人工知能 によって作られました | BGM 終わり → 映写機の音 → フィルム切れ |

ナレーション合計:約220字。昭和のアナウンサー風に、ややゆっくり・抑揚大きめ・語尾をはっきり。

## Higgsfield で作る素材(すべて、生成前に許可を取る)
AIに作らせるのはカット1・3〜9の **8カット**。タイトル・エンドカード・テロップ・フィルム加工は手元の編集で作る。

### 手順
1. **参照画像を作る(画像 3枚)**:①一家と茶の間の全景 ②おそうじ円盤の単体 ③研究所
2. **各カットの最初のコマを作る(画像 8枚)**:①〜③を参照にして、カットごとの構図を作る(4:3)
3. **動画にする(動画 8本 × 5秒、音なし)**:最初のコマから image-to-video
4. **ナレーション(音声 1本)**:日本語の男性アナウンサー風の声で、上の原稿を読ませる
5. **BGM(音楽 1本)**:オリジナルの、明るく前向きな1960年代風の管弦楽(既存曲に似せない)
→ 届いた素材を `assets/source/showa_pr/ep01/` に置き、`tools/showa_film/` でフィルム加工と編集を行う

### 共通の画づくり指定(英語プロンプトに付ける)
```
Still frame from a 1960s Japanese corporate promotional film, 4:3 composition,
Showa-era danchi apartment, soft natural window light plus flat fill light,
slightly soft lens, muted period colors, static tripod camera, eye-level or low angle,
everyone in early-1960s Japanese clothing and hairstyles.
Clean image: no film grain, no scratches, no text, no subtitles, no logos, no watermark.
```
※粒子・傷・色あせは後から加工で足すので、AIには付けさせない(カットごとに質感がバラつくのを防ぐ)

### 円盤の指定(全カット共通)
```
a modern minimalist round robot vacuum cleaner, plain matte white disc about 30 cm wide,
small black sensor window at the front, one small green indicator light, no logo, no text, no brand
```

### カット別の最初のコマ(英語プロンプト)
- **C1**:floor-level low angle shot across a tatami room covered with a patterned rug; [円盤] glides toward the camera; chabudai table legs and fusuma doors softly out of focus behind
- **C3**:full shot of a Japanese family of three (father in white shirt, thin tie, black-rimmed glasses; mother in cardigan and knee-length flared skirt; 8-year-old son in shorts and striped T-shirt) kneeling around a low chabudai table, amazed, watching [円盤] moving on the rug; a cathode-ray TV on legs (screen off) and floral curtains in the background
- **C4**:high angle shot, [円盤] touching a fusuma sliding door and turning away
- **C5**:1960s laboratory with white walls, a blackboard showing a simple chalk diagram of a round disc with arrows, a drafting table, two young engineers (a man and a woman) in white lab coats pointing at the board and nodding
- **C6**:the son lying flat on the rug, peeking under a 1960s sofa as [円盤] disappears beneath it
- **C7**:a calico cat sitting calmly on top of [円盤] as it slowly crosses the rug
- **C8**:[円盤] reaching a small plain white charging dock in the corner of the room, the green light turning on; slow push-in
- **C9**:the father, kneeling in seiza, bowing deeply toward [円盤] on its dock; the mother and son bow behind him

### 動画化の動きの指定
- 動きは小さく、ゆっくり。カメラは固定(C5のパン、C8の寄りだけ動かす)
- 人数・頭数は最初のコマで固定(大人2・子1・猫1、円盤1台。増やさない)
- 円盤の上面に文字やロゴを出さない

## 未決事項
- シリーズ名(案1「あしたの暮らし」で仮置き)
- 夢見ヶ丘電機工業の同名企業チェック
- ナレーションの声(候補を数人聞き比べてから決定)
