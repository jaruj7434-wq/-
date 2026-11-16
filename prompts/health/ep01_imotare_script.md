# 体のサイン図鑑 #01『胃もたれ』台本(約42秒・9:16)

構成:3D体内映像+リアルな再現映像+ナレーション(固定キャラなし)
トーン:落ち着いた解説。最後は安心させる。怖がらせない。

## カット表
| # | 秒 | 映像 | テロップ | ナレーション |
|---|---|---|---|---|
| 1 | 0–1.5 | **[V1]** 暗い背景に浮かぶ胃の3D。ゆっくり回り込む | **胃もたれ**(画面中央に特大) | (固定のオープニング効果音) |
| 2 | 1.5–5 | **[R1]** 再現映像:昼食後のオフィスで、胃のあたりを手でさすって小さくため息をつく人 | 原因は食べすぎ“だけ”じゃない | 「その胃もたれ、原因は食べすぎ“だけ”じゃありません」 |
| 3 | 5–11 | **[V2]** 食べ物が胃に入り、胃の壁がゆっくり波打つ → 動きが鈍くなり、中身が滞る | 胃の動きが落ちると、食べ物が長く残る | 「胃は、食べたものを動かして腸へ送り出しています。この動きが落ちると、食べ物が長く残って重たく感じるんです」 |
| 4 | 11–18 | **[V3]** 脳から胃へ光の信号が届き、途中で弱まる | 原因①脂っこい物・食べすぎ ②ストレス・睡眠不足 ③早食い・年齢による変化 | 「よくある原因は3つ。脂っこい物や食べすぎ。ストレスや睡眠不足で、胃を動かす神経のバランスが乱れること。そして早食いや、年齢による胃の働きの変化です」 |
| 5 | 18–22 | [V1] 再利用(色味を変える) | 検査で異常がないのに続く →「機能性ディスペプシア」という病気のことも | 「検査で異常がないのに続くときは、『機能性ディスペプシア』という病気のこともあります」 |
| 6 | 22–31 | **[R2]** 再現映像:夕食をゆっくり噛んで食べる人(別の性別・年代)。テロップはチェックリスト | 今日からできる対策 ✅よく噛んで腹八分目 ✅寝る2〜3時間前までに食べ終える ✅食後すぐ横にならない | 「今日からできるのは、よく噛んで腹八分目。寝る2〜3時間前までに食べ終えること。食後すぐに横にならないことです」 |
| 7 | 31–38 | [V2] をぼかして背景に使い、「受診の目安」を表示(落ち着いた赤系のアクセント) | こんな時は早めに消化器内科へ:体重が減ってきた/黒っぽい便/飲み込みにくい/吐き気・嘔吐が続く/症状が長く続く・くり返す | 「ただし、体重が減ってきた、便が黒っぽい、飲み込みにくい。こんなサインがあるときや、長く続くときは、早めに消化器内科で相談してください」 |
| 8 | 38–42 | 固定のエンドカード(シリーズ名+番号) | 体のサイン図鑑 #01/いくつ当てはまった?コメントで | 「体は、ちゃんとサインを出しています。いくつ当てはまったか、コメントで教えてください」 |

- 画面下部に常時、小さく出典を表示:「参考:日本消化器病学会 患者さんとご家族のためのガイド(機能性ディスペプシア)/国立がん研究センター がん情報サービス」
- 再現映像のカットには「※イメージ映像(AI生成)」を小さく表示
- 概要欄:「情報は公的機関等の公開情報をもとにしています。気になる症状は医療機関に相談してください。※映像はAIで制作したイメージです」
- 字幕:ナレーションとテロップは重複させない。テロップは要点だけにする
- **投稿前の確認**:出典ページの最新版で、対策と受診目安の記述が一致しているかチェックする

## 生成リスト
### 動画(Seedance 2.0 fast・9:16・720p・5秒・音なし 想定=各12.5クレジット)
- **[V1] 胃の全体像(素材ライブラリ:胃-01)**
  > Medical 3D CG visualization of a human stomach floating in a dark navy background, semi-transparent glossy tissue with soft warm inner glow, slow orbiting camera move, clean scientific style, no blood, no gore, vertical 9:16.
- **[V2] 胃の動きと停滞(素材ライブラリ:胃-02)**
  > Medical 3D CG animation inside a semi-transparent human stomach: food particles enter from the top, the stomach wall moves in gentle peristaltic waves, then the waves slow down and the contents stay heavy at the bottom. Soft lighting, clean educational style, no blood, no gore, vertical 9:16.
- **[V3] 脳から胃への神経信号(素材ライブラリ:神経-01)**
  > Medical 3D CG animation: a glowing blue nerve signal travels from a stylized semi-transparent brain down a vagus-nerve-like pathway to the stomach; midway the light flickers and weakens. Dark background, clean scientific style, vertical 9:16.
- **[R1] 再現:食後に胃をさする**
  > Realistic cinematic footage of a Japanese office worker in their 30s sitting at a desk after lunch, gently rubbing the upper stomach with one hand and letting out a small tired sigh, natural daylight from a window, shallow depth of field, handheld smartphone-style framing, vertical 9:16.
- **[R2] 再現:ゆっくり噛んで食べる**
  > Realistic cinematic footage of a Japanese person in their 50s eating a simple home-cooked dinner slowly at a wooden dining table, chewing calmly with a relaxed expression, warm evening light, close-medium shot, vertical 9:16.

### 音声
- ナレーション:固定の声を `create_voice` で作成 → `generate_audio` で読み上げ

### 編集
- CapCut 等でカットをつなぎ、タイトル・テロップ・効果音・BGMを入れる → 必要なら `subtitles` で字幕を焼き込み

## コスト見積もり(目安)
- 動画5カット:12.5 × 5 = **62.5クレジット**(撮り直しを含めると約100〜125)
- ナレーション:生成前に `get_cost` で確認してから提示する
