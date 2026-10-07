---
name: magazine-pageturn-film
description: ファッション雑誌「AURE」の表紙に写るモデル本人がしゃがんでページをめくり、めくった下ですでに歩いているシーンに切り替わって、アイテム・髪・足元などのアップをおしゃれなカット割りで見せ、最後に少し遠目で微笑んで終わる縦型ショート動画を Higgs Field で制作する手順。「表紙からめくる動画」「ページめくり動画」「雑誌の表紙から歩くシーンへ」「AURE の動く表紙」などの依頼で使う。
---

# 雑誌表紙ページめくり → ウォーキング動画(AURE)

藤川らるむさん案件で確立した制作フロー。新しいモデル・コーデ・街でも同じ型で作る。
すべての返答は日本語。**Higgs Field で生成する前は、毎回内容と費用を伝えて許可を取る**(リポジトリ直下と `fashion-magazine-cover/CLAUDE.md` のルール)。

## 完成形のイメージ(15秒・9:16)

| 秒 | カット |
|---|---|
| 0–3.5 | 表紙(誌名 AURE+説明文)から始まる。**表紙の中のモデル本人**が右側に寄り、ひざをそろえて上品にしゃがみ、右手でページ右下の端をつまむ。左手はスカートの裾を押さえる。立ち上がりながら大きくめくり、ページと一緒に画面外へ |
| (切替) | めくった下は**別シーン**。同じ場所・ポーズで立っているのではなく、**すでに少し先を歩いている**モデルが見え、そのまま歩くシーンへ |
| 3.5–5.5 | 正面の全身ウォーク(カメラ後退ドリー) |
| 5.5–7 | ネックレス・刺繍など上半身アイテムのアップ |
| 7–8.5 | 艶髪がなびくスロー |
| 8.5–10 | 腰の高さでスカート/ボトムスの揺れ |
| 10–11.5 | 足元(靴・ソックス)ローアングル |
| 11.5–13 | 横からの全身シルエット+街の夜景 |
| 13–15 | **少し遠目(膝上の引き)**で立ち止まり、カメラに向かって自然に微笑んで終わる。顔のどアップにしない |

## 手順

### 0. 素材をそろえる(課金なし)
- 顔写真・服装写真は必ず `media_upload_widget` でアップロード。チャット添付は使えない。
- アップロード後は `https://d2ol7oe51mr4n9.cloudfront.net/<user>/<media_id>.png` を curl で取得し、**自分の目で中身を確認**する(以前、チャット画像の順番と Higgs Field 上の写真がずれていて服装を取り違えた)。生成結果のドメイン(d8j0ntlcm91z4)はプロキシで開けないので、生成物の確認はユーザーに依頼する。
- 実在人物は本人同意済みのものだけ。

### 1. 顔を固定する(初回のみ)
- **Soul(soul_2)**:同一人物の顔写真 5〜20 枚で学習(`show_characters` action=train、約10分)。落書き・スタンプ入り写真は外す。画像生成で顔の再現度が最も高い。
- **Element**:動画用。`show_reference_elements` action=create(課金なし)。プロンプトに `<<<element_id>>>` を入れる。※実際に参照されるのは登録した最初の1枚だけなので、一番似ている正面の写真を先頭にする。
- 既存:らるむ Soul `5ebb33c3-451b-47ce-8578-6c7670cf99f9` / Element `1cf5acdf-fc98-48f9-a443-404fa462c940`

### 2. 表紙の写真(文字なし)を作る — soul_2
- `model: soul_2`, `soul_id`, `aspect_ratio: 9:16`, `quality: 2k`, `enhance_prompt: false`
- **参照画像は渡さない**。渡すと自動補正でプロンプトが参照写真の説明文に書き換わり、背景・構図が無視される。服装は文章で全アイテムを細かく書く。
- 髪は「long glossy silky jet-black hair like a hair-care commercial model」。背景は普通では行けないおしゃれな海外の夜の街(例:モナコ・モンテカルロの港)。頭上に誌名用の余白を空ける。
- 費用目安:約0.12クレジット

### 3. 文字を重ねて表紙にする — gpt_image_2_5(Flare)
- `variant: flare`, `quality: high`, `resolution: 4k`(4.25クレジット)/ 2k(2.75)
- 参照に手順2の写真を渡し、「写真は一切変えず文字だけ追加」と指示。
- 文字:中央上に大きく **AURE**(Didone セリフ・固定)/ モデル名(明朝+ゴールド下線)/ ローマ字名 / 筆記体の英語キャッチ / 服装の説明・褒め言葉を3〜5本。フォント・サイズ・色(シャンパンゴールド、ダスティピンク)を混ぜる。号数・バーコードなど実在誌っぽい文言は入れない。
- 文字は顔・体に重ねない。

### 4. 動画 — cinematic_studio_3_0(Cinema Studio Video 3.0)
- `medias`: `start_image` = 手順3の表紙、`image` = 手順2の文字なし写真
- プロンプト冒頭で `<<<element_id>>>` を指定し、「全ショットで顔を同一に、変形・別人化禁止」。服装は表紙と同一と明記。
- `duration: 15`, `aspect_ratio: 9:16`, `generate_audio: false`
- 費用:15秒 480p=52.5 / 720p=75 / 1080p=150、10秒 1080p=100
- **まず 480p で動きを確認 → OK なら 1080p**。
- Higgs Field がプリセット(例「IN THE DARK」「DROWN IN MUSIC」)を勧めてきても、ユーザーの指示どおりに作るなら `declined_preset_id` で辞退して literal 生成する。
- 完成待ちは `send_later` で10〜12分後に確認を予約し、記録を `fashion-magazine-cover/prompts/` に残してコミット・プッシュ。

## 失敗から学んだ注意点

| 症状 | 対策(プロンプトの書き方) |
|---|---|
| 画面外から大きな手が出てめくる | "the woman INSIDE the cover performs the page turn herself. NO other hands, NO giant hand from outside the frame. Natural human scale." |
| めくった後に白いページ→人物が出現 | "Underneath the turning page the live next scene is ALREADY visible … NO blank page, NO white page" |
| めくった後も同じ場所に立っている | "the page beneath is a DIFFERENT scene — she is already mid-stride further down the promenade, walking toward the camera. NO standing still after the page turn." |
| しゃがむとスカートの中が見えそう | "crouches modestly, knees together, body angled sideways; RIGHT hand pinches the page corner while LEFT hand holds the hem of her dress down in front of her thighs" |
| ラストが顔のどアップ | "medium-wide shot from a few meters away, knees-up framing … gentle natural smile … no face close-up" |
| 顔が変わる | Soul 写真を `image` で渡す+Element+表紙の3重で固定。参照写真に別の服を着た画像を混ぜない(服装が引きずられる) |
| nsfw 判定で止まる | Seedance 2.5 は露出の多い服や本人写真の参照で止まりやすかった。Cinema Studio 3.0 / Kling 3.0 / MiniMax H3 では通った。失敗分は返金される(transactions で確認) |
| 1080p 指定でも記録が 768×1344 | Cinema Studio の記録表示の可能性。実画質をユーザーに確認してもらう |

## プロンプト雛形(Cinema Studio 3.0)

```
Photorealistic luxury fashion commercial, vertical 9:16, 15 seconds. The video opens exactly on the start image: the "AURE" magazine cover filling the whole screen, the woman standing at <PLACE> at night.
CHARACTER: the woman is <<<ELEMENT_ID>>>, exactly the same face as in the start image and the reference photo in every single shot — <FACE/HAIR DETAILS>. No face change, no morphing, no different person, realistic skin.
OUTFIT (identical to the cover in every shot): <ALL ITEMS>.
Shot 1 (0-3.5s) PAGE TURN BY HERSELF: the woman INSIDE the cover comes alive and performs the page turn herself. There are NO other hands and NO giant hand from outside the frame. She steps toward the right side of the cover and crouches down modestly and elegantly, knees kept together, body angled slightly sideways. With her RIGHT hand she pinches the bottom-right corner edge of the magazine page; at the same time her LEFT hand holds the hem of her dress down in front of her thighs so that nothing under the skirt is ever visible. Then she stands up gracefully while lifting the page corner high and pulling it across in one big sweeping motion, turning the whole page toward the top-left, and she leaves the frame together with the turned cover page.
TRANSITION: the page beneath is a DIFFERENT scene — she is NOT standing in the same place or pose as on the cover. Underneath the turning page we already see her mid-stride further down <PLACE>, already walking toward the camera. NO blank page, NO white page, NO standing still after the page turn.
Shot 2 (3.5-5.5s): Full-body front shot walking toward the camera, camera slowly dollies backward.
Shot 3 (5.5-7s): Close-up of <TOP ACCESSORY / DETAIL>.
Shot 4 (7-8.5s): Slow-motion close-up of her glossy hair swinging.
Shot 5 (8.5-10s): Waist-level tracking shot of <BOTTOMS / HEM>.
Shot 6 (10-11.5s): Low-angle shot of <SHOES>.
Shot 7 (11.5-13s): Side tracking shot of her full silhouette with <LANDMARKS>.
Shot 8 (13-15s) FINAL: medium-wide shot from a few meters away, knees-up framing. She stops, turns toward the camera and gives a gentle, natural smile. Only a very slight push-in — no face close-up. The video ends on this framing.
Style: high-end luxury commercial, realistic, cinematic night lighting, shallow depth of field, sparkling bokeh, smooth gimbal moves, slight slow motion. Tasteful. No text after the page turn.
```

## 参考になる過去の記録
- `fashion-magazine-cover/prompts/rarumu-pageturn-cinema.md`(このフローの全履歴と job ID)
- `fashion-magazine-cover/prompts/soul-rarumu.md`(Soul / Element の作成記録)
