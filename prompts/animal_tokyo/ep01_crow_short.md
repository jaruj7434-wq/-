# 第1話（ショート）：渋谷のカラスの朝ごはん

- 尺：約40秒／縦型 9:16
- 季節：11月（繁殖期の外。縄張り争いは入れない）
- フック：「人間がまだ寝ている時間、渋谷ではもう朝ごはんが始まっている」
- ナレーション：観察者目線。カラスにはしゃべらせない
- 生態の根拠：`plan.md` のリサーチ表

## カット割り

| # | 尺 | 時刻テロップ | 画（カラスの目線） | ナレーション案 | 作り方 |
|---|---|---|---|---|---|
| 1 | 5秒 | AM 5:35 | 暗い森の枝の上。葉の隙間から遠くのビルの灯り。仲間の鳴き声 | 「明治神宮の森。夜のあいだ、人は入れない」 | Higgsfield |
| 2 | 5秒 | AM 5:50 | 樹冠を飛び立ち、夜明け前の青い空へ。下に森、その先に渋谷の高層ビル | 「日の出の30分以上前。カラスはもう起きている」 | Higgsfield |
| 3 | 5秒 | AM 6:05 | 路地の電線にとまり、下を見下ろす。ゴミ集積所にネットと袋 | 「狙うのは、人が出した生ごみ」 | Higgsfield |
| 4 | 5秒 | AM 6:10 | 地面すれすれの低い目線。ネットからはみ出た袋に近づき、くちばしでつつく | 「袋の外から中身が見えると、見逃さない」 | Higgsfield |
| 5 | 5秒 | AM 7:40 | 収集車が近づく音。飛び上がり、上から交差点と人の流れを見下ろす | 「ごみが片づく前に、朝ごはんは終わる」 | Higgsfield |
| 6 | 5秒 | PM 4:30 | 夕焼けの中、群れが森へ戻る。カラスの影がいくつも並ぶ | 「夕方、また森へ帰っていく」 | Higgsfield |
| 7 | 6〜8秒 | — | 地図：明治神宮（ねぐら）→ 渋谷の路地（エサ場）のルート ＋ 豆知識「都内のカラスは2001年度から約8割減」 | 「東京のカラスは、この20年あまりで約8割減った」 | Claude Code |

時刻テロップ・地図・字幕・環境音の足し込み・BGM・つなぎは Claude Code 側で作る。

## Higgsfield カット一覧（案）

共通設定：モデル `seedance_2_5`（テキストから動画、音声あり）／`aspect_ratio: "9:16"`／5秒／720p
共通ルール：看板・ロゴ・読める文字は出さない、人の顔ははっきり映さない

1. **C1 森の枝**
   `First-person POV of a crow perched on a branch deep inside a dense dark forest before dawn, camera at the crow's eye level with slight head-bobbing movements, leaves and branches very close to the lens, through gaps in the canopy distant city skyscraper lights glow faintly, cold blue pre-dawn light, other crows cawing nearby, quiet ambient city hum in the distance, photorealistic, no text, no logos`
2. **C2 飛び立ち**
   `First-person POV of a crow taking off from a forest canopy and gliding upward into a deep blue pre-dawn sky, the dense green forest below and the dense Tokyo-like skyline of high-rise towers ahead, smooth gliding aerial camera with slight wing-beat wobble, wind noise, distant traffic, photorealistic, no text, no logos`
3. **C3 電線から見下ろす**
   `First-person POV of a crow perched on an overhead power line above a narrow Tokyo back street at early dawn, looking down at a curbside garbage collection point with plastic garbage bags under a green bird net, small head tilts and twitches, empty street, distant train sound, photorealistic, no readable signs, no logos`
4. **C4 低い目線でゴミ袋へ**（いちばん難しいカット）
   `Extremely low ground-level first-person POV of a crow hopping along asphalt toward a plastic garbage bag sticking out from under a bird net, jittery short hops, the black beak tip briefly entering the bottom of the frame and pecking the bag, rustling plastic, early morning light, distant cars, photorealistic, no readable text, no logos`
5. **C5 収集車から飛び去る**
   `First-person POV of a crow on a street as a white garbage collection truck approaches with engine and beeping sounds, the crow flies up and the camera rises above a large busy pedestrian crossing in a Tokyo-like district in the morning, crowds walking far below, photorealistic, no readable text, no logos, faces not identifiable`
6. **C6 夕方のねぐら入り**
   `Aerial first-person POV of a crow flying with a flock of crows toward a large dark forest at sunset, orange and purple sky, black crow silhouettes around the camera, city skyline in the background, wind and many crows cawing, photorealistic, no text, no logos`

## クレジット目安（2026-11-12 の見積もり。生成はまだしていない）

- 無制限枠：**使えない**（プラン上 unlim が無効）→ 生成すると通常クレジットを消費する
- 残高：717.77 クレジット（ultra）
- 1カット（5秒・720p）：**35クレジット**
- 1カット（5秒・480p 下書き）：**15クレジット**

| やり方 | 目安 |
|---|---|
| 6カットを720pで1回ずつ | 210クレジット |
| まず C4 だけ下書きで試す | 15クレジット |
| 撮り直しを見込む（6カット×平均1.5回） | 約315クレジット |
