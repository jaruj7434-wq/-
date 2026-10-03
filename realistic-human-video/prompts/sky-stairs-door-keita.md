# 空の階段 → 雲上の扉 → 別世界(慶太・実写版)企画案

- 参考: `analysis-sky-stairs-door.md`(アニメ調の元動画)。アニメ要素は消して実写のフォトリアルで再現。人物は慶太(element `f6c17cc9-…`)。
- 追加要素(ユーザー指定): 階段を駆け上がる途中で全身コーデが3回変わる。変わる瞬間はおしゃれなトランジション+引き込まれるカメラワーク(例: 雲をまたいだらコーデが変わる)。
- 尺案: 20秒(元は15秒。着替え3回ぶんの見せ場を足すため)/ 9:16 / 音声あり
- 費用(プレフライト): seedance_2_5 20秒 480p 60 / 720p 140 クレジット

## コーデ案(未確定)
| # | タイミング | コーデ |
|---|---|---|
| 0 | スタート〜 | 元動画へのオマージュ: 白の半袖オープンカラーシャツ、オリーブのカーゴパンツ(裾ロールアップ)、茶色レザーのワークブーツ、茶色レザーのメッセンジャーバッグ |
| 1 | 1回目(雲をまたいだ瞬間) | 空色のデニムセットアップ(カバーオール+ワイドデニム)、白T、白スニーカー |
| 2 | 2回目(石段の間を大ジャンプ、空中で回り込み) | 白のナイロンウインドブレーカー+白のワイドパンツ、シルバーのネックレス、白のボリュームスニーカー |
| 3 | 3回目(太陽のフレアを横切る) | ネイビーのロングコート(風になびく)、白T、黒のワイドスラックス、黒のレザーローファー → この服で扉を開ける |

## トランジション案
1. 雲ワイプ: 背中を追ったまま雲に突っ込み、白で画面が覆われる → 雲を抜けた瞬間にカメラが斜め前へ回り込み、新しいコーデの正面を見せてから背後に戻る
2. 空中オービット: 石段の間を大きく跳ぶ瞬間にスローモーション。カメラが空中で180°回り込み、彼の体が画面を横切った瞬間にコーデが変わる → 着地で通常速度に戻る
3. 太陽フレア: 低い位置から見上げると太陽が彼の背中に重なり、光で一瞬白く飛ぶ → 光が引くと新コーデ。コートの裾が風で大きくなびく
- どの切り替えも、正面(または斜め前)で服がはっきり見える一瞬を必ず入れる(後ろ向きの体に前向きの服を描かせない)

## 構成案(20秒)
| 時間 | 内容 |
|---|---|
| 0.0–1.2 | 傾いた俯瞰: 断崖の縁に立つ慶太(コーデ0)。眼下に海と海岸の街、空へうねる浮遊石の階段、はるか上の雲の上に白い扉 |
| 1.2–2.8 | 横から背後へ回り込みながら水平に戻す。慶太が最初の石段へ跳び移り走り出す |
| 2.8–5.0 | 背後追従で駆け上がる。石段から小石が崩れ落ち、風が髪と服を揺らす |
| 5.0–6.5 | トランジション1(雲ワイプ)→ コーデ1 を斜め前から見せる → 背後に戻る |
| 6.5–9.0 | 階段が大きくカーブ、海と雲を見下ろしながら走る |
| 9.0–10.8 | トランジション2(空中オービット・スロー)→ コーデ2 |
| 10.8–13.0 | 雲の上へ。階段が一直線になり、正面に扉が光る |
| 13.0–14.5 | トランジション3(太陽フレア)→ コーデ3 |
| 14.5–16.5 | 扉に到着、金のノブをつかんで押し開ける。光があふれる |
| 16.5–17.3 | ホワイトアウト、光の中へ |
| 17.3–20.0 | 別世界: 金色の朝焼けに複数の太陽と小さな惑星、雲海、緑の浮遊島から落ちる滝。開いた扉の枠越しに、慶太の背中(コーデ3)が見渡す |

## コーデ確定(ユーザー提供画像・首から下のみ)
| # | media_id | ファイル | 内容 |
|---|---|---|---|
| ①スタート | `0f9a7480-c996-4a70-a928-1d2fdb65d212` | 111.png | 黒レザーのスタジャン(白い筆記体ロゴ)、ブラウンのパーカー、金の十字架ネックレス、ステッチの効いた極太ブラウンデニム、ウィートのワークブーツ |
| ②1回目 | `50bb7733-fc8c-40a4-baa2-5910153c4279` | 2222.png | 色落ちネイビーのワークジャケット(ボア襟)、黒のジップインナー、マスタード色に色落ちした極太デニム、ウィートのワークブーツ |
| ③2回目 | `9305765a-4ecf-44a2-9854-a94dd0cbc779` | 6666.png | ベージュのショート丈ワークジャケット、白T、金のペンダントネックレス、極太のオリーブ迷彩カーゴ、ウィートのワークブーツ |
| ④3回目 | `f16f5fbf-4c4b-4b66-b56f-2d58fcce3a0e` | 55555.png | ダークブラウンのレザーボンバー、グレーのフードインナー、極太ライトグレーのスウェットパンツ、黒のレザーローファー |

## 英語プロンプト v1(20秒)
- medias: image_references = ①②③④(この順)、慶太 element。seedance_2_5 / omni_reference / 20秒 / 9:16。費用 480p 60 / 720p 140
```
A 20-second vertical (9:16) PHOTOREALISTIC live-action fashion film — real people, real
locations, shot on a cinema camera; absolutely no anime, no cartoon, no illustration, no CGI look.
Breathtaking, fantastical, high-contrast scenery with glowing highlights: deep blue sky, towering
white cumulus clouds, sparkling ocean far below.
ONE CHARACTER ONLY: the young man <<<f6c17cc9-ae3d-4123-a642-79d2882414bd>>> — his face, hair and age
match his reference exactly in every frame, including fast motion and profiles; never beautify,
reshape or swap his face, no facial distortion.
OUTFITS: the four attached headless outfit images are clothing references only (use only their
clothes, shoes and accessories, never their backgrounds). He wears them in this order:
LOOK 1 (start): black leather varsity jacket with white script lettering, brown hoodie, gold cross
necklace, very wide brown jeans with curved seams, wheat nubuck work boots.
LOOK 2: washed navy work jacket with a shearling collar, black zip layer, very baggy mustard-yellow
washed jeans, wheat work boots.
LOOK 3: beige cropped work jacket, white T-shirt, gold pendant necklace, very wide olive camouflage
cargo pants, wheat work boots.
LOOK 4 (final): dark brown leather bomber jacket, grey hoodie layer, very wide light-grey
sweatpants, black leather loafers.
Every outfit change happens INSTANTLY inside a transition, and right after each change the camera
swings to his front three-quarter side for a moment so the FRONT of the new outfit is clearly
visible; body, head and clothes always face the same direction (never front-facing clothes on a
back-turned body). The camera keeps moving the whole film; he keeps running until the door.

THE WORLD: a staircase of real weathered sandstone slabs floating in the open sky, each slab
separated by a gap, winding up in a long S-curve from a sheer sea cliff toward a white arched door
standing on top of a cloud high above. Far below: a deep blue ocean and a coastal town.

0.0–1.2s — LOOK 1. Tilted high-angle wide shot (strong dutch angle) from above and behind his right
shoulder: he stands on the grassy edge of the sea cliff, the floating staircase snaking up into the
sky, the tiny white door on a cloud at the top.
1.2–2.8s — The camera arcs from his side to directly behind him while leveling out; he leaps onto
the first floating slab and starts running.
2.8–5.0s — Steady low tracking shot right behind him at back height as he sprints up the slabs;
small stones crumble off the edges and fall toward the sea, wind whips his clothes and hair.
5.0–6.5s — TRANSITION 1 "CLOUD CROSSING": he runs straight into a thick white cloud and the frame
whites out for a few frames; as they burst out of the cloud the camera swings to his front
three-quarter side — he is now in LOOK 2 — then glides back behind him.
6.5–9.0s — The staircase curves wide over the ocean; tracking from behind and slightly to the side,
clouds sliding past, sun glinting on the sea.
9.0–10.8s — TRANSITION 2 "MID-AIR ORBIT": he jumps across a big gap between two slabs; time slows to
slow motion at the top of the jump while the camera orbits 180° around him in mid-air; as his body
crosses the lens the outfit changes to LOOK 3, shown from the front; he lands and real speed snaps back.
10.8–13.0s — Above the clouds: the staircase straightens and climbs toward the glowing white door;
tracking behind him, the door growing ahead.
13.0–14.5s — TRANSITION 3 "SUN FLARE": a low angle looking up as the sun passes exactly behind him,
a burst of light flares across the frame; as the light fades he is in LOOK 4, seen from the front
three-quarter side, the leather bomber gleaming, then the camera returns behind him.
14.5–16.5s — He reaches the door: a tall white arched door in a white stone frame with a gold
handle, standing on a cloud. He grabs the handle and pushes it open; brilliant white light pours out.
16.5–17.3s — The camera follows him into the light; full white-out.
17.3–20.0s — ANOTHER WORLD: medium shot from behind him (LOOK 4), framed by the open door edge on the
right: a golden sunrise sky with two suns and small distant planets, an endless sea of clouds,
floating green islands with waterfalls pouring into the clouds, lens flares. He stands still and
takes it in as the camera slowly pushes in.

SOUND: soaring cinematic music, wind rush, footsteps on stone, a whoosh on each outfit change, a
deep door creak and a bright shimmer as the light pours out. No text, no logos, no watermarks.
```

## 生成ログ
| 内容 | job_id | 備考 |
|---|---|---|
| v1(480p・20秒) | `886bb078-7b3b-4064-b053-63e45fed72a5` | seedance_2_5 omni_reference / 9:16 / 480p / 60クレジット。ref=①②③④、慶太 element。プリセット IN THE DARK は辞退 |
