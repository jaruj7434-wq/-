# Desert Duel — コマ送り絵コンテ(全カット作り直し版)

動画のコマ送りとして一続きになる画像セット。これまでの S1〜S8・T3/T6 の反省を反映する。

## 反省点
- 人物がカメラ目線になる/相手の方を向いていない/片方が銃を持っていない、など一続きの映像として不自然なカットがあった。

## 全カット共通ルール(イマジナリーライン固定)
- 男性は **常に画面左側で右向き**、おばあさんは **常に画面右側で左向き**。二人は常に向かい合う。
  - 肩越しカットでも左右は入れ替えない(男性の肩越し=男性の背中が画面左手前、おばあさんが右奥でこちらを向く)。
- 二人とも **常に右手にリボルバーを持っている**(画面に手が入るカットでは必ず見える)。
- **カメラ目線は禁止**(最後の F16 のおばあさんだけ例外)。視線は常に相手に向ける。
- 立ち位置・背景(砂丘・岩・太陽の位置=画面左からの低い夕日)は全カット共通。
- 衣装:
  - 変身前 = 参照エレメントのまま(男性: Chill Nautical Vibes / おばあさん: Graceful Cleanup Warrior)
  - 変身後 = T3(`950cd934-…`)のおばあさん、T6(`2dfc5986-…`)の男性の服装を参照画像として固定
- 発砲・命中は「本物の銃のような火花と硝煙、飛ぶ銃弾」。命中してもケガ・血は一切なく、服だけが変わる。

共通英語指示(各プロンプト末尾):
```
Continuity rules: this is one frame of a continuous film sequence. The young man is always on
the LEFT side of the frame facing RIGHT, the elderly woman is always on the RIGHT side facing
LEFT; they always face each other and look at each other, never at the camera. Both always hold
an antique Western prop revolver in their right hand. Faces, hairstyles and outfits exactly as
in the references. Same desert location, low late-afternoon sun from the left, long shadows.
Playful and harmless: no injury, no blood, no wound. Photorealistic cinematic film still,
anamorphic 35mm look, warm amber highlights and teal shadows, subtle film grain.
```

## コマ割り(16カット)

| # | 場面 | カット | 男性 | おばあさん |
|---|---|---|---|---|
| F01 | にらみ合い | 横からの全景(二人とも全身) | 変身前・銃を構える | 変身前・銃を構える |
| F02 | にらみ合い | 男性の肩越し(男性の背中が左手前、おばあさんが右奥) | 変身前 | 変身前 |
| F03 | にらみ合い | おばあさんの肩越し(おばあさんの背中が右手前、男性が左奥) | 変身前 | 変身前 |
| F04 | にらみ合い | 男性の横顔アップ(右を見る、奥にぼけたおばあさん) | 変身前 | 変身前 |
| F05 | にらみ合い | おばあさんの横顔アップ(左を見る、奥にぼけた男性) | 変身前 | 変身前 |
| F06 | 男性が撃つ | 横からのミディアム:引き金、火花と硝煙 | 変身前 | 変身前 |
| F07 | 銃弾 | 二人の間を飛ぶ銃弾のアップ(左右にぼけた二人) | 変身前 | 変身前 |
| F08 | 命中 | おばあさんに命中、当たった所から服がクリーム白に変わっていく途中 | 変身前 | 変身途中 |
| F09 | 変身完了 | おばあさん全身(左を向き男性を見る)、奥で驚く男性 | 変身前 | 変身後 |
| F10 | 構え直し | 横からの全景 | 変身前・銃を構える | 変身後・銃を構える |
| F11 | おばあさんが撃つ | 横からのミディアム:引き金、火花と硝煙 | 変身前 | 変身後 |
| F12 | 命中 | 男性に命中、服が黒のレザーコーデに変わっていく途中 | 変身途中 | 変身後 |
| F13 | 変身完了 | 男性全身(右を向きおばあさんを見る) | 変身後 | 変身後 |
| F14 | 敗北の予感 | 男性が自分のコーデを見下ろす横顔(感服した表情) | 変身後 | 変身後 |
| F15 | 倒れる | 横からの全景:男性が前のめりに砂へ倒れ込む(コメディ調)、おばあさんは立ったまま | 変身後 | 変身後 |
| F16 | 決め | おばあさんがカメラ目線で銃口の煙をふっと吹く(唯一のカメラ目線)、奥に倒れた男性 | 変身後 | 変身後 |

- モデル: `nano_banana_pro` / 9:16 / 2k / 1枚2クレジット → 16枚で32クレジット
- 判定リスクが高いカット: F06・F07・F08・F11・F12・F15(止まった場合は言い回しを調整して再提案)
