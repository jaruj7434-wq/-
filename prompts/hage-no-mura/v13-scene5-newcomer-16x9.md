# 最終シーン(16:9)— 改訂版:新メンバー設定なし・慶太の鐘で締める(未生成)

ユーザー指定(2026-10-20):
- 新メンバーが入る設定は無し
- 最後は、冒頭の「慶太が鐘を乱暴に鳴らす」場面を遠目から見た画角に差し替える
- 驚く場面のセリフは「えー!ハゲてない!」「髪あるじゃん!」「フサフサ!」を同時に騒ぐ形に
- なるべくテンポ良く短く

参考動画 1:41–1:54 の画角(鐘のあおり → 驚く顔 → 暗転 → 遠景)を流用。

| # | 尺(編集後) | 画角 | 内容 | セリフ | 生成 |
|---|---|---|---|---|---|
| 1 | 1.5秒 | 真下からあおる鐘のアップ。左に苔むした石柱、斜めの木の梁、ピンクの鐘(冒頭と同じ鐘) | 鐘が突然ガシャンガシャン激しく鳴り出す | (鐘の連打) | 4秒 |
| 2 | 2秒 | 木の壁の室内。手前に男女2人、後ろに2人がぼけて重なる。全員が一点を見て目を見開く | 拓海・玲奈(手前)、毛利・ひなた(奥) | 全員が同時に「えー!ハゲてない!」「髪あるじゃん!」 | 4秒 |
| 3 | 1.5秒 | 木の小屋の戸口に立つミドル。両手で口を押さえる | さくら | 「フサフサ!」 | 4秒 |
| 4 | 1秒 | 赤い板壁の前のアップ。目を見開き、手で顔を覆う | 剛 | ― | 4秒 |
| 5 | 3秒 | 冒頭と同じ森の鐘を、遠く離れた場所から望遠で。木々の間に小さく、慶太が全身で狂ったように鐘を連打している | 慶太 | (鐘の連打) | 4秒 |
| 6 | 3秒 | タイトル「ハゲの村 〜Hage Village〜」 | | | 編集 |

合計 約12秒。驚く人物は拓海・玲奈・毛利・ひなた・さくら・剛で重複なし。

## コスト見込み
- 開始画像: gpt_image_2 / high / 2k / 16:9 × 5枚 = 約 32.5 クレジット
- 動画: seedance_2_5 / 720p / 4秒 × 5本 = 140 クレジット

## 改訂2:8秒1本にまとめる(ユーザー指定、タイトルは別途作成のため除外)

クレジット節約のため、5カットを Seedance 2.5 の8秒1本(カット割りをプロンプトで指定)で生成する。
人物の参照が多すぎると不安定になるため、2 の奥の2人(毛利・ひなた)は外し、手前の拓海・玲奈だけにする。

- 開始画像(1枚): 鐘のあおりのアップ(gpt_image_2 / high / 2k / 16:9、6.5 クレジット)
- 動画: seedance_2_5 / omni_reference / 8秒 / 16:9 / 720p / 音声あり(56 クレジット、プレフライト確認済み)
- image_references: 拓海 `cb446c3f-…`、玲奈 `94c0569a-…`、さくら `98d9e778-…`、剛 `3ddd46ab-…`、慶太シート `38677a4b-…`、慶太の登録写真 `9e6a89ba-…`
- 合計 約 62.5 クレジット

### 開始画像プロンプト
```
Cinematic 16:9 widescreen still from a Japanese romance reality-show documentary. Extreme low-angle shot looking straight up from directly below a pink metal bell: on the LEFT a tall mossy gray stone pillar with ivy, a thick dark wooden beam crossing diagonally from it toward the upper right, and the pink bell hanging from the beam with a thin white rope dangling down, tilted mid-swing. Behind it, deep green forest canopy and a bright overcast sky. Natural documentary color grade. No people, no text, no logos, no watermark.
```

### 動画プロンプト(8秒)
```
Cinematic Japanese romance reality-show trailer, 16:9 widescreen, 8 seconds, five quick cuts with hard cuts between them. Keep every face, hair and outfit exactly as in the reference images; each person appears only in their own cut, never duplicated. Realistic acting, documentary look, no text, no subtitles.

CUT 1 (0-1.2s): continue from the first frame, low angle under the pink bell by the mossy stone pillar: the bell suddenly starts clanging violently, swinging wildly, the rope jerking hard from below.
CUT 2 (1.2-3.2s): hard cut indoors against a wooden wall, handheld medium two-shot: TAKUMI (M-shaped receding hairline, thin black glasses, gray hoodie) and REINA (ash-brown bob, lavender knit vest) stand side by side staring at the same point off-screen, eyes wide in total shock, and both shout at the same time, overlapping, in Japanese: TAKUMI 「えー!はげてない!」 REINA 「髪あるじゃん!」 (pronounce はげ as "ha-ge" with a hard G).
CUT 3 (3.2-4.6s): hard cut to a medium shot of SAKURA (long light-brown wavy hair, cream cable-knit sweater) standing in the doorway of a wooden cabin, both hands flying up to her mouth, and she screams in Japanese: 「フサフサ!」
CUT 4 (4.6-5.4s): hard cut to a close-up of GOU (shaved bald head, short black beard, navy henley) in front of a red plank wall, eyes wide in disbelief, slowly covering his face with one hand.
CUT 5 (5.4-8s): hard cut to an extreme long telephoto shot from far away across the forest: the same mossy stone pillar and pink bell are small in the distance between the trees, and KEITA (voluminous dark-brown center-parted hair, rimless glasses, white oxford shirt, navy knit over his shoulders) is a small figure frantically yanking the rope with his whole body, his thick hair bouncing, the bell swinging wildly. Slight handheld telephoto shake.

Audio: loud frantic metallic bell clanging through cuts 1 and 5 (distant and echoing in cut 5), the overlapping shocked shouts in cuts 2 and 3, a dramatic music sting under cut 4. Only the Japanese lines above.
```
- 開始画像 job_id: `879d9a06-67ab-4f2d-bd93-04a432e96616`(2026-10-20)
- 動画(8秒・720p・56 クレジット): `6ef5e729-bdec-4cfc-9431-3b52f2cb40e4`
