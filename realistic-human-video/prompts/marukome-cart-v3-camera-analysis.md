# MARUKOME カート動画 v3 — 参考動画カメラワーク完全分析+英語プロンプト

- キーフレーム画像(v2 の K1〜K3)はユーザー判断で**不採用**。画像も参考動画もモデルに渡さず、テキストと慶太エレメントだけで作る。
- 分析方法: 参考動画を 0.25 秒ごとにコマ抜き+カット自動検出(カット点 4.07 / 5.90 / 6.90 / 7.50 秒。7.5 秒以降は最後までノーカット)。

## カメラワーク分析(15.2秒・9:16・30fps)
| # | 時間 | カメラ位置・レンズ | カメラの動き | 被写体の動き |
|---|---|---|---|---|
| 1 | 0.00–4.07 | カート前端に固定したリグ。広角(24mm程度)、男性の胸の高さからやや見上げ。手前にデニムの脚が大きく入る | カートと一緒に移動(人物はフレーム内で固定、背景のヤシ並木・駐車車両だけが流れる)。路面の細かい振動。左右対称の構図、奥に消失点 | 0–1秒: 頭を後ろに倒し目を閉じてぐったり → 1–2秒: 頭を起こしてレンズを見て何か言う → 2秒前後: 両腕を大きく広げる → 2.5秒〜: 腕をカートの縁に掛け、頭を横に倒して再び脱力 |
| 2 | 4.07–5.90 | 道路中央、路面から約1mの低い位置。望遠寄りの標準(50mm程度)、左右対称のヤシ並木の一点透視 | 完全固定 | 遠くからカートが一直線にこちらへ突進。男性は仰向けで足を前に投げ出す。5.5秒でカートの前輪が浮いてウィリー状態になり、5.8秒でカートがカメラの右上をかすめて飛び越える(画面右上を黒い影が横切る) |
| 3 | 5.90–6.90 | カートの下(底のカゴの真下)に前向きで固定。超広角。画面上1/3に赤いワイヤーのカゴの底、下に前輪キャスター2個、路面にカゴの格子の影 | カートと一体。路面が高速で流れる。後半はモーションブラー | 前方の木製ジャンプ台(合板のキッカー、横に廃材の山)がぐんぐん近づき、6.6秒で車輪がランプに乗り上げる |
| 4 | 6.90–7.50 | 同じカート下リグ | 宙に浮いてわずかに上を向く | キャスターが空中でぶら下がり、はるか下に信号機・ヤシ・道路。高さを感じる一瞬 |
| 5 | 7.50–10.0 | 道路の向かい側から看板を見上げるロングショット。看板は2本の鉄骨脚+キャットウォーク付き。左に男性の全身写真、右に巨大なブランド文字 | 完全固定 | 8.0秒: 空からカートが看板上部に突っ込み、キャットウォークに引っかかる → 8.5–10秒: パンツ(下半身の服)だけがキャットウォークからぶら下がって揺れる。中に人はいない |
| 6 | 10.0–14.6(5 と同じカットのまま) | カメラはそのまま。男性の顔の高さ。背景に看板 | 男性が入ってから手持ち感が少し出る | 10.0秒: 画面下からキャップの頭頂が出る → 10.5–11.5秒: レンズのすぐ前で立ち上がり、キャップのつばを直しながらカメラ目線(ミディアムクローズアップ、看板は肩越し) → 12–13秒: ホッとした顔で小さく何か言い、目を伏せる → 13–14秒: 右肩越しに看板を振り返る → 14.2秒: 正面に戻る |
| 7 | 14.6–15.2 | 同上 | 手がレンズに当たり暗転 | 右手の手のひらをレンズに向けてかざし、画面を覆って黒で終わる |

- 光: 1〜4 はお昼の強い日差し・快晴。5〜7 は原作では夕方の金色の光 → 今回はユーザー指定に合わせて全編お昼。
- 画の質感: 35mmフィルム風、暖色寄り、冒頭はわずかに周辺減光。画面上のクレジット文字は再現しない。

## 英語プロンプト(参考動画・画像なし/慶太エレメントのみ)
```
A 15-second vertical (9:16) photorealistic fashion commercial short film, action-comedy, shot on
35mm film with a warm, clean, high-end look. Location: a long, perfectly straight boulevard lined
with very tall palm trees in a sunny Southern California-style city, parked cars on both sides.
Time: bright midday the whole film — clear blue sky, strong high sun, crisp highlights, vivid
natural colors.

REFERENCES: attached image 1 = the MARUKOME billboard (use it exactly); attached image 2 = the
outfit.
ONE CHARACTER ONLY: the young man <<<f6c17cc9-ae3d-4123-a642-79d2882414bd>>>. His face, hair and
age must match his reference exactly in every shot, including close-ups and fast motion; never
beautify, reshape or swap his face. No cap, no hat. Outfit (the fashion focus): a navy track
jacket with white piping and a half zip, a grey-and-white striped shirt with the hem hanging out
under the jacket, very wide dark navy cargo trousers, black leather loafers.

SHOT 1 (0.0–4.0s) — Cart-mounted front rig
Camera rigidly mounted on the front edge of a red metal shopping cart, 24mm wide lens at his chest
height, tilted slightly up, looking back at him as he sits inside the cart facing the lens. His
wide cargo trousers fill the bottom of the frame in the foreground. The cart rolls slowly down the
middle of the boulevard: he stays fixed in the frame while the palm trees and parked cars slide
past behind him toward a centered vanishing point; subtle road vibration.
0.0–1.0s: head tipped back against the cart, eyes closed, totally limp in the sun.
1.0–2.0s: he lifts his head, looks straight into the lens and mutters something, bored.
2.0–2.5s: he flings both arms out wide in a big lazy gesture.
2.5–4.0s: he hooks his arms over the sides of the cart and lets his head roll to one side,
melting back into a lazy slouch. Hard cut.

SHOT 2 (4.0–5.9s) — Locked-off road-center wide
Camera fixed in the middle of the road about one meter above the asphalt, 50mm lens, perfectly
symmetrical one-point perspective down the palm boulevard. Far away, the red shopping cart comes
racing straight toward the camera at high speed with him lying back inside, legs and loafers
sticking up over the front, jacket flapping. At 5.5s the cart's front wheels lift into a wheelie;
at 5.8s the cart blasts past just over the top-right corner of the lens as a dark blur. Hard cut.

SHOT 3 (5.9–6.9s) — Under-cart rig, approaching the ramp
Camera mounted underneath the cart's basket facing forward, ultra-wide lens: the red wire bottom
of the basket fills the top third of the frame, the two front caster wheels hang in the lower
frame, the asphalt rushes underneath with the basket's grid shadow on it. A wooden plywood jump
ramp, with a pile of scrap lumber beside it, rushes toward the lens; at 6.6s the wheels slam onto
the ramp with heavy motion blur. Hard cut.

SHOT 4 (6.9–7.5s) — Under-cart rig, airborne
Same rig: the cart is flying high in the air. The caster wheels dangle against the blue sky;
far below are the street, a traffic light and palm trees. A brief weightless moment. Hard cut.

SHOT 5 (7.5–10.0s) — Locked-off billboard wide (no cut until the end of the film)
Camera on the opposite sidewalk at head height, looking across the road at the billboard straight
on. The billboard is EXACTLY the one in the first attached image — same wide cream panel, same
half-body photo of him, same navy "MARUKOME" lettering, same steel legs and catwalk — standing on
the roadside verge behind the sidewalk, parallel to the road, never in the road. Its text must
stay exactly "MARUKOME" (M-A-R-U-K-O-M-E) in every frame. At 8.0s the empty shopping cart flies
in from the sky and crashes onto the billboard's catwalk, where it gets stuck. From 8.5s only a
pair of wide navy cargo trousers dangles from the catwalk, swinging — nobody is inside them. The
camera holds perfectly still.

SHOT 6 (10.0–14.6s) — Same shot continues: he pops up
At 10.0s the top of his head rises into the bottom of the frame right in front of the lens. He
stands up into a medium close-up, the billboard behind him over his shoulder, completely unhurt
and fully dressed in the outfit. 10.5–11.5s: he smooths his hair with one hand and looks straight
into the lens with a huge relieved expression. 12.0–13.0s: he breathes out, mutters something,
glances down. 13.0–14.0s: he turns his head and looks back over his right shoulder at the
billboard and the dangling trousers. 14.0–14.6s: he turns back to the camera. Slight handheld
float from here on.

SHOT 7 (14.6–15.0s) — Hand covers the lens
He raises his right hand, open palm toward the camera, and covers the lens; the frame goes dark
and ends on black.

SOUND: shopping-cart wheels rattling on asphalt, wind rush, a wooden ramp thump, a big comedic
metal crash on the billboard, then a quiet relieved exhale; an upbeat music sting at the end.
No captions, no on-screen credits, no text anywhere except "MARUKOME" on the billboard.
```

## 生成ログ
| 内容 | job_id | 備考 |
|---|---|---|
| 看板単体(青ネオンの電光掲示板・MARUKOME・慶太の全身写真・お昼) | `7fa86f01-646f-4b95-9ed0-b1e6edb701f3` | nano_banana_pro 指定(記録上 nano_banana_2)/ 9:16 / 2k / 2クレジット。慶太 element+服装① `b10936fb-…`。動画で看板文字が MARUKUME になったための対策 |
| 看板単体 v2(アメカジ風・ネオンなし・慶太は頭〜太ももの半身・リアルな印刷広告) | `92be1641-26a8-4673-8d72-ca1251de3f79` | nano_banana_pro 指定(記録上 nano_banana_2)/ 9:16 / 2k / 2クレジット。慶太 element+服装① `b10936fb-…` |
| 看板単体 v3(少し横長・ブランド広告風・歩道奥に道路と平行に設置・慶太は半身) | `f669d81c-d333-42e2-8aa3-c96b465325ba` | nano_banana_pro 指定(記録上 nano_banana_2)/ 9:16 / 2k / 2クレジット。慶太 element+服装① `b10936fb-…` |

## 動画生成案(承認待ち)
- seedance_2_5 / omni_reference / 15秒 / 9:16。参照: 看板 `7ea7deb8-1528-4214-a6d2-0a4b58f1d648`(f669d81c を取り込み直し)、服装① `b10936fb-…`、慶太 element
- 費用(プレフライト): 480p 45 / 720p 105 / 1080p 180 クレジット
| 動画(看板画像参照・480p) | `7e0fc637-c17b-4529-ba9c-928402ef565c` | seedance_2_5 omni_reference / 15秒 / 9:16 / 480p / 45クレジット。参照: 看板 `7ea7deb8-…`、服装① `b10936fb-…`、慶太 element。プリセット IN THE DARK は辞退 |
