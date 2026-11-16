# こんな忍者はまじでやだ(「こんなナルトは嫌だ」パロディ)

## 全体の構成
- 縦型 9:16、4〜5ネタで1本、テンポ重視(全体 30〜40秒)
- 冒頭: 曲調のジングル「こんな忍者は〜 まじでやだ〜♪」(約2.5秒)
- 各ネタ: 回答テロップ → 実写コント(5〜7秒)→ オチ → 短い効果音・ジングルで次へ
- 主役: AI で作る架空の若い男性の忍者(金髪ツンツン、オレンジの忍者服、額当てのマークはラーメンの「なると」の渦巻き)。木ノ葉マーク・公式デザインは使わない
- 投稿時の表記: パロディ/AI生成/公式とは無関係

## ネタ1: 影分身が全員ドパガキ(ユーザー指定: セリフなし、短い動画のみ)
ドパガキ = スマホをずっと見ている若者(最近の流行語)

- 約4秒、9:16、セリフなし
- 0〜1秒: 忍者が印を結ぶ → ボフン!と煙
- 1〜4秒: 煙が晴れると分身が8人。全員スマホに夢中(縦スワイプでリール動画、横持ちでゲーム、寝転がって見る、イヤホンで笑う)。顔が画面の光に照らされる

### 制作
1. 開始画像: 屋上で印を結ぶ忍者(gpt_image_2 / medium / 9:16)
2. 動画化: 開始画像から煙 → 分身全員スマホ(Cinema Studio Video 2 / pro / 4秒 / 9:16)

## キャラ作成(主役の忍者)
- 顔: 慶太(本人同意済みの写真 media `9e6a89ba-8fd6-4530-b720-06e29d9e7a3a` を参照)
- 髪型・服装: ユーザー指定で、なるべく元ネタに寄せる(コスプレ風)
- 額当てのマークだけは、木ノ葉マークの代わりにラーメンの「なると」の渦巻きにする
- 予定: gpt_image_2 / medium / 9:16、全身・正面、白背景に近いシンプルな屋外
- プロンプト案:
```
Photorealistic full-body photo, 9:16, of the young Japanese man in the reference photo (keep his face exactly), cosplaying a classic anime ninja hero: bright spiky blond hair sticking out in all directions, a black cloth forehead protector with a polished metal plate engraved with a single spiral swirl like the narutomaki fish-cake pattern (no leaf symbol), three thin whisker-like marks painted on each cheek, an orange-and-black tracksuit-style ninja jumpsuit with a black upper chest and shoulders, a white collar, orange sleeves and orange pants, a kunai holster strapped to the right thigh, blue ninja sandals. He stands facing the camera with a confident grin, fists on hips. Simple Japanese rooftop at daytime, soft natural light, realistic skin and fabric, no text, no logo.
```
- 生成: gpt_image_2 / medium / 2k / 9:16 / 2クレジット、job `3a5a7394-1df3-4e8e-a2a3-0f127caf1d71`(`assets/output/naruto-iyada/ninja-keita-character.png`)
- 額当てに木ノ葉マークが出てしまったため、ローカルで消して渦巻きの刻印に差し替え → `ninja-keita-character-v2.png`(採用候補)
- 慶太の写真どおりメガネあり
- キャラ参照(額当て修正版)アップロード: media `13c30c66-8502-4555-9f60-64d0e7ba3eae`(md5 一致を確認)
- ネタ1 構図変更(ユーザー指定): 森の広場、分身数百人が輪になって広場を埋める+木の上にも、全員正面向き、文字なし
- 開始画像: gpt_image_2 / medium / 2k / 9:16、job `030fa170-5834-49cb-88f9-2a67a89883ab`(`bit1-start.png`)
- 終了画像: 同上、job `e9583ac7-570f-4be1-abc5-8ad222439691`(`bit1-end.png`)。手前の分身の額当てに木ノ葉風マークが出ている
- 終了画像 v2(ユーザー指定: 本物の慶太は印のポーズのまま残る): gpt_image_2 / medium / 2k、終了画像+開始画像を参照、job `88bdccc5-cc6f-4e75-9328-b4cdb7866ff8`。本物は左上の枝で印のまま呆然
- v3: 手前5人の額当てのマークをローカルで渦巻きに描き直し(`bit1-end-v3.png`、採用候補)

## ネタ1 動画の流れ(ユーザー指定で変更)
1. 開始画像で慶太が「影分身の術!」と大声で叫ぶ(慶太のクローン声 `888113e6`、elevenlabs_v4、タグなし sim 1 / stab 0.6)
2. ボフン!と煙 → 終了画像 v3(分身全員スマホ、本物は枝で印のまま)
3. 本物の慶太が周りを見渡し、スマホに夢中の分身たちに怒る
- 動画は2本に分ける: A = 開始画像 → 終了画像 v3(4秒)、B = 終了画像 v3 から、本物に寄りながら見渡して怒る(4秒)
- 終了画像 v3 アップロード: media `c1e27993-5179-4222-b0fe-91c5bf596b05`(md5 一致)
- ネタ1 の結末は「怒る」から「深いため息」に変更(ユーザー指定)
- 声: elevenlabs_v4 / 慶太-1、sim 1 / stab 0.6
  - 「影分身の術!!」(タグなし) job `6ab3e9c2-324e-4464-952b-b63fc6a74078`(1.28秒)
  - 「[sighs] はぁ〜……」 job `0e2fbf2f-e15e-45f0-9eed-dae3e49b993c`(ため息2回 → 1回目だけ使用)
- 動画A(開始画像 → 終了画像 v3、4秒、pro、8クレジット) job `de89e035-18ba-4761-a7e4-a9b35347045c`
- 動画B(終了画像 v3 から寄り → 見渡して深いため息、4秒、pro、8クレジット) job `c925a02b-e058-41f7-a864-245f66044481`
- 編集 `bit1-kagebunshin.mp4`(8.51秒):
  - 動画Aの最初の0.85秒を1.5倍スローにして、叫び(1.28秒)を口の動きに合わせた
  - 動画Aの元の音声に英語の「シャドウクローン!」が入っていたので、0.95秒より前を消し、ボフン以降の効果音だけ使用
  - 動画Bの元の音声のため息(別人の声)は2.75秒でフェードアウトし、慶太のため息を B の2.75秒から重ねた
  - 叫び・ため息は CLEAR_M で処理

## ネタ2: ラーメン好きじゃなくてパスタ好き
- 構成案: ラーメン屋台を素通り → イタリアンのテラス席でフォークとスプーンでパスタを優雅に食べる → 「ボーノ!」
- イルカ先生役(架空の AI 人物): 濃い茶髪の高いポニーテール、鼻すじに横一文字の傷、紺の忍者服に緑のベスト、額当ては渦巻きマーク
- 画像(慶太がパスタを優雅に食べ、後ろの屋台でイルカ先生役がドン引き): gpt_image_2 / medium / 2k / 9:16 / 2クレジット、慶太キャラ `13c30c66` を参照、job `0764313e-b701-40fe-bd9f-3233101a5f39`(`bit2-pasta-end.png`)
- v2: イルカ先生役の額当てのマークを渦巻きに、鼻の傷が薄かったので描き足し(`bit2-pasta-end-v2.png`)
- 一楽の店内版(ユーザー指定: 一楽と親父を実写で登場): gpt_image_2 / medium / 2k / 9:16 / 2クレジット、慶太キャラ `13c30c66` と前の画像 `0764313e` を参照、job `e4862c7d-84e1-4502-a0e9-b8783629be55`(`bit2-ichiraku.png`)
  - 慶太はカウンターでパスタをフォーク+スプーン、隣でイルカ先生役がラーメンを持ってドン引き、奥で白い調理服の親父が呆れ顔
  - のれんは無地(文字は未定)。親父の目は糸目になっていない
- v2: イルカ先生役の額当てのマークを渦巻きに修正(`bit2-ichiraku-v2.png`)
- v3: のれんの中央2枚に「一」「楽」をローカル合成(Noto Serif CJK Black、黒、布の陰影に合わせて乗算)→ `bit2-ichiraku-v3.png`
