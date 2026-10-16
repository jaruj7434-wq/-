# 再現プロンプト(参考動画なし・犬画像+テキストのみ)

## 生成 #1 の反省
- 幻術(`hf_mult_replace_object`)では顔が人間のまま残った → 元動画を入れずにゼロから生成する方式に切り替え

## 元動画の分析(19秒版、0.5秒刻みのコマ割りで確認)
| 秒 | 内容 | カメラ |
|---|---|---|
| 0.0–1.0 | 崖の上のコンクリート足場。1人目(黒ベスト・青い短パン)がロープの持ち手を握り、足場を蹴って飛び出す | 足場の後ろから手持ち、やや見下ろし |
| 1.0–4.0 | ターコイズの滝つぼの上を大きく振り子のように遠くまで行き、小さく見える | 1人目を追って右へパン、空と木々が入る |
| 4.0–5.5 | 振り戻って足場に近づく | 追従 |
| 5.5–6.5 | 足場に戻ってくる。蛍光グリーンのベスト+紫ヘルメットのガイドが受け止める | 足場に戻る |
| 6.5–8.0 | 足場に4〜5人。ガイドが2人目(白Tシャツ+黒ハーネス・柄短パン)にロープを渡す | 足場の後ろから |
| 8.0–11.5 | 2人目が両手を頭上に上げてロープを握る。周りの仲間も腕を上げて盛り上げる | 固定気味、少し揺れる |
| 11.5–12.5 | 2人目が足場を蹴って飛び出す | 追従 |
| 12.5–13.0 | 空中でロープを離し、滝の近くに落ちる | 下へパン |
| 13.0–19.0 | 大きな水しぶき → 浮かび上がり、ヘルメット姿で泳ぐ | 崖の上から水面を見下ろす |

## 推奨モデル・設定
- `seedance_2_5` / `mode: omni_reference` / 19秒 / 9:16 / 480p / 音声あり → 57 クレジット
- 参照: @Image1 柴犬、@Image2 ゴールデン、@Image3 フレブル、@Image4 ボーダーコリー、@Image5 コーギー

## プロンプト(案)
```
Photorealistic vertical smartphone video, one continuous 19-second handheld take, no cuts. A tropical jungle canyon with a turquoise waterfall plunge pool and white-water cascade, sunny day with scattered clouds, dense green trees. A rough concrete ledge on the cliff edge with a tall green metal pole and a rope swing with a handle bar.

All characters are real dogs, never humans: realistic dog heads, dog faces, muzzles, fur and paws. No human faces, no human hands, no human skin anywhere. The dogs stand upright on their hind legs like people and move with human-like gestures, but their bodies remain clearly canine.
- The Shiba Inu from @Image1 wears a yellow helmet and black life vest with harness.
- The Golden Retriever from @Image2 wears a yellow helmet and black life vest with harness.
- The French Bulldog from @Image3 wears a yellow helmet and black life vest.
- The Border Collie guide from @Image4 wears a lavender helmet and neon yellow-green guide vest.
- The Corgi from @Image5 wears a yellow helmet and black life vest.

0-1s: Camera behind the group on the ledge. The Shiba Inu grips the rope handle with both front paws and pushes off the ledge.
1-4s: The Shiba Inu swings far out over the turquoise pool in a long pendulum arc, becoming small against the jungle; camera pans to follow, sky visible at top.
4-6s: The Shiba Inu swings back toward the ledge and lands; the Border Collie guide catches and steadies him.
6-8s: Five dogs crowd the ledge. The Border Collie hands the rope to the Golden Retriever.
8-11.5s: The Golden Retriever holds the rope handle high above his head with both front paws; the French Bulldog, Corgi and Shiba Inu raise their front paws and cheer, tails wagging.
11.5-13s: The Golden Retriever runs off the ledge, swings out over the water near the waterfall and lets go mid-air.
13-19s: Camera tilts down from the cliff top: big splash in the turquoise water, the Golden Retriever resurfaces with his yellow helmet and dog-paddles happily.

Natural daylight, realistic water physics, slight handheld shake, authentic travel-vlog look, sound of the waterfall, rushing water, excited dog barks.
```
