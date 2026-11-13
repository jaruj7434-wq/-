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
