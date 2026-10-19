# それぞれの悩みと恋シーン(16:9)— 参考動画 0:33–1:10 の画角分析と開始画像

| # | 参考(秒) | 参考動画の画角 | ハゲの村での置き換え | セリフ(2026-10-19 改訂) | 開始画像 job_id |
|---|---|---|---|---|---|
| 1 | 0:33–0:38 | 告白インタビュー。椅子に座るミドル、固定。左に木の板壁と棚、右にレンガ壁、壁掛けランプ。→ 広い食卓にひとりの俯瞰 → 頬を押さえて泣くアップ | 晴彦 | 晴彦「50歳になって、何も生えてない痛みが…本当に、出てきて、、」 | `27e87615-288a-4ff6-a7a6-dd48a650eadd` |
| 2 | 0:38–0:41 | 背の高い草むらの屋外ミドル2ショット。左の人物が毛布を羽織り不安げに話し、右の人物が横顔で聞く | 拓海(話す)・梨花(聞く) | 拓海「俺の魅力って…はげ以外で、何なんだろう」 | `37359db2-43a3-43c3-a3ed-89a503597e61` |
| 3 | 0:41–0:46 | ススキを背景にした肩越しアップ。胸に手を当てて話す。左手前に聞き手の後頭部 → 茂みで作業 | 剛(話す)・美月(手前) | 剛「なんでもできちゃうのハゲだから。嫌なんですよ、卵に見られる」 | `a0e1cce5-1f0e-4c08-af45-7e17ab52faaf` |
| 4 | 0:46–0:50 | 墓前に立つ後ろ姿の引き(石柱の間から)→ 白黒で祈る手のアップ | 毛利(小さな祠に変更) | 毛利「一度ハゲてるのに…また生やそうとするのって…」 | `fb089bc2-8805-4d15-a60c-4fee64a20404` |
| 5 | 0:50–0:53 | ススキ野原のベンチを正面から引き。左の男性は前を見つめ、右の女性が顔を覆って泣く | 毛利・ひなた | 毛利「…不義理なのかなって。。。」 | `b76bff98-dc83-42b2-aa9d-7e7bf7f73398` |
| 6 | 1:00–1:01 | 夜の食卓の俯瞰。10人で夕食 | 10人全員 | ― | `4e37d52c-9666-4092-a09b-cdcfc0f182bb` |
| 7 | 1:03–1:05 | 暖色の暗い部屋、ソファの2ショット。左の女性が聞き、右の男性が話す | ひなた(聞く)・毛利(話す) | 毛利「みんなじゃなくて二人きりで育毛剤を塗り合いたいなと思って」 | `d5cf0527-3c96-4c2a-bc31-6ef52c910af2` |
| 8 | 1:05–1:08 | 木のテラスの屋根の下から引き。奥に富士山。男性が女性の手を引いて外へ | 拓海・梨花 | ― | `3fbbbd95-af78-40d4-b710-b8371ca1aaf8` |
| 9 | 1:08–1:10 | 台所の俯瞰。男性が箸で女性に食べさせる | 剛・美月 | 剛「はーげ」 美月「…おいしい!」 | `eea3424b-e6d5-4909-9611-b842c064e8aa` |

開始画像: gpt_image_2 / high / 2k / 16:9(2026-10-19、9枚 約58.5 クレジット)
参考動画のスタジオ(コメンテーター)のカットは v11 方針どおり除外。

セリフ改訂(2026-10-19・ユーザー指定): 1・2・3・5・7・9 を差し替え。4 は据え置き。
動画プロンプトでは「はげ」「はーげ」をひらがなで書き、発音指定(ha-ge / haa-ge, hard G)を付ける。

## 動画プロンプト(英語)

共通設定: `seedance_2_5` / omni_reference / 16:9 / 720p / 音声あり / use_unlim false。
start_image = 上表の開始画像、image_references = 登場人物のキャラクターシート。
コスト(プレフライト確認済み): 4秒 = 28 クレジット、5秒 = 35 クレジット。

| # | 尺 | 参照シート | コスト |
|---|---|---|---|
| 1 | 5秒 | 晴彦 | 35 |
| 2 | 4秒 | 拓海・梨花 | 28 |
| 3 | 5秒 | 剛・美月 | 35 |
| 4 | 4秒 | 毛利 | 28 |
| 5 | 4秒 | 毛利・ひなた | 28 |
| 6 | 4秒 | 10人全員 | 28 |
| 7 | 5秒 | 毛利・ひなた | 35 |
| 8 | 4秒 | 拓海・梨花 | 28 |
| 9 | 4秒 | 剛・美月 | 28 |
| 合計 | 39秒 | | **273** |

共通の冒頭(STYLE):
```
Cinematic Japanese romance reality-show documentary, 16:9 widescreen film-trailer look, single continuous shot. Keep every face and outfit exactly as in the reference images; each person appears only once, no other people. Telephoto lens, shallow depth of field, muted low-saturation documentary color grade, natural skin texture, realistic sincere emotional acting, no comedic tone, no text, no subtitles.
```

### 1. 晴彦の告白インタビュー(5秒)
```
[STYLE] 5 seconds. Continue from the first frame: confessional interview, static medium shot. HARUHIKO (50, bald crown with short salt-and-pepper hair on the sides, navy samue) sits on a chair in a dim room, wooden wall and shelf on the left, brick wall on the right, warm wall lamp. Eyes glistening, voice breaking, he looks slightly off-camera and says slowly in Japanese: 「50歳になって、何も生えてない痛みが…本当に、出てきて、、」 He trails off, presses his lips together and blinks back tears. Audio: soft sad piano, room tone, only his line.
```

### 2. 草むらの拓海と梨花(4秒)
```
[STYLE] 4 seconds. Continue from the first frame: outdoor medium two-shot in tall dry grass at dusk. On the left TAKUMI (M-shaped receding hairline, glasses, gray hoodie, a blanket over his shoulders) looks down anxiously and says quietly in Japanese: 「俺の魅力って…はげ以外で、何なんだろう」 (pronounce はげ clearly as "ha-ge" with a hard G; never "habe"). On the right RIKA (round glasses, sage-green knit dress) listens in profile with a worried, tender look. Audio: wind in the grass, soft piano, only his line.
```

### 3. 剛の打ち明け(5秒)
```
[STYLE] 5 seconds. Continue from the first frame: over-the-shoulder close-up with pampas grass behind. GOU (muscular, completely shaved bald head, short black beard, navy henley) places a hand on his chest and speaks earnestly, a little hurt, in Japanese: 「なんでもできちゃうのハゲだから。嫌なんですよ、卵に見られる」 (pronounce ハゲ clearly as "ha-ge" with a hard G). The back of MITSUKI's head (long straight black hair) is blurred in the left foreground. Audio: soft wind, gentle piano, only his line.
```

### 4. 祠の前の毛利(4秒)
```
[STYLE] 4 seconds. Continue from the first frame: wide shot from behind, framed between stone pillars. MOURI (stocky, thin black comb-over, red-and-navy flannel shirt) stands alone in front of a small stone shrine, head bowed, and says quietly in Japanese, voice trembling: 「一度ハゲてるのに…また生やそうとするのって…」 (pronounce ハゲ as "ha-ge" with a hard G). In the last second, cut to a black-and-white close-up of his hands pressed together in prayer. Audio: wind, distant birds, soft sad piano, only his line.
```

### 5. ススキ野原のベンチ(4秒)
```
[STYLE] 4 seconds. Continue from the first frame: static frontal wide shot of a bench in a field of silver pampas grass. MOURI on the left stares ahead into the distance and murmurs in Japanese: 「…不義理なのかなって。。。」 HINATA (dark-brown high ponytail, yellow knit cardigan) on the right covers her face with both hands and cries silently, shoulders shaking. Audio: wind through the pampas, soft piano, only his line.
```

### 6. 夜の夕食・俯瞰(4秒)
```
[STYLE] 4 seconds. Continue from the first frame: overhead top-down shot of a long wooden dinner table at night, warm pendant light. The ten cast members (five bald men, five young women, exactly as in the first frame) pass dishes, smile and talk; the light reflects softly on the men's scalps. Slow subtle camera drift. No dialogue. Audio: warm indistinct chatter, clinking dishes, gentle acoustic guitar.
```

### 7. ソファの毛利とひなた(5秒)
```
[STYLE] 5 seconds. Continue from the first frame: warm dim room, two-shot on a sofa. HINATA on the left listens with shy, hopeful eyes. MOURI on the right turns to her, nervous and sincere, and says softly in Japanese: 「みんなじゃなくて二人きりで育毛剤を塗り合いたいなと思って」 HINATA lowers her eyes and smiles, blushing. Audio: quiet room tone, soft romantic piano, only his line.
```

### 8. 富士山とテラス(4秒)
```
[STYLE] 4 seconds. Continue from the first frame: wide shot from under a wooden patio roof, Mt. Fuji in the distance. TAKUMI gently takes RIKA's hand and leads her out from under the roof into the sunlight; she follows, smiling. No dialogue. Audio: birds, light breeze, hopeful acoustic guitar.
```

### 9. 台所の剛と美月(4秒)
```
[STYLE] 4 seconds. Continue from the first frame: high-angle shot in a farmhouse kitchen. GOU holds food with chopsticks to MITSUKI's mouth and says gently in Japanese, in the tone of "aaah-n": 「はーげ」 (pronounce clearly as "haa-ge" with a hard G). She takes the bite, chews, her eyes light up and she says in Japanese: 「…おいしい!」 They smile at each other. Audio: kitchen sounds, warm acoustic guitar, only their lines.
```

※ [STYLE] は共通の冒頭文に置き換えて送信する。
