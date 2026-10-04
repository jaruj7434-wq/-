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
- v1 自己確認(コマ抜き、取り込み直し media `95d74403-…` 経由で取得): 実写○。①○。雲トランジション→②○(ただしパンツがマスタードより淡いカーキ寄り)。空中ジャンプはあるが、その場で③に変わらず、③は11〜12秒ごろに背中側だけで登場(前向きの見せ場なし)。太陽フレア→④は正面で○。扉→ホワイトアウト→別世界(太陽2つ・惑星・浮遊島の滝)○。階段は「離れた石板」ではなく連続した石段になった。
- メモ: d8j0 の生成物 URL は media_import_url で取り込み直すと d2ol7 から取得でき、こちらでもコマ確認が可能。

## v1 へのユーザー指摘 → v2 方針
- トランジション後のカメラワークと男性の動きが不自然 → カメラは常に背後から追いかける。着替えの瞬間だけカメラが回転して正面へ回り込み(緩急:回り込み中はスロー気味→背後へ戻ると加速)、また背後に戻る。
- 男性は常にまっすぐ階段を駆け上がる(横を向かない・跳ばない・止まらない。扉まで)。
- 雲は階段まわりだけでなく、空全体にまばらに浮かべ、ハイライトを効かせて幻想的に。
- 駆け上がるスピードをもっと速く、引き込まれる速さに。
- (自主修正)②のパンツをはっきりマスタードイエローに。

## 英語プロンプト v2(20秒)
```
A 20-second vertical (9:16) PHOTOREALISTIC live-action fashion film — real person, real light,
shot on a cinema camera; absolutely no anime, no cartoon, no illustration, no CGI look.
ONE CHARACTER ONLY: the young man <<<f6c17cc9-ae3d-4123-a642-79d2882414bd>>> — his face, hair and age
match his reference exactly in every frame, including fast motion; never beautify, reshape or
swap his face, no facial distortion.

THE WORLD: a long staircase of real weathered sandstone steps floating high in the open sky,
climbing in a gentle S-curve from a sheer sea cliff up to a white arched door standing on a cloud
far above. Far below: a deep blue ocean and a tiny coastal town. The WHOLE sky is filled with
scattered, separate cumulus clouds of many sizes floating everywhere — near and far, above and
below the staircase, not only around the stairs — their tops glowing with bright sunlit
highlights and soft golden rim light against a deep saturated blue sky; sun glitter on the sea,
crisp contrast, breathtaking and dreamlike.

HIS MOTION (whole film): he SPRINTS straight up the staircase at a thrilling, very fast speed —
powerful long strides, arms pumping, jacket and trousers whipping in the wind, small stones
crumbling off the steps behind him. He always runs straight forward up the stairs: he never turns
sideways, never jumps off the stairs, never slows down or stops until he reaches the door.

CAMERA RULE: the camera chases him from DIRECTLY BEHIND at back height, close and fast, like a
drone racing right behind a runner, slight shake, wind speed, staircase rushing toward the lens.
ONLY at each outfit change does the camera break away: it swings smoothly in an arc around him to
his FRONT (ease-in, a moment of slow motion as it reaches his front three-quarter side so the
new outfit is clearly visible while he keeps sprinting toward the lens), then whips back around
behind him and speeds up again (ease-out). Body, head and clothes always face the same
direction; never front-facing clothes on a back-turned body.

OUTFITS (the four attached headless outfit images are clothing references only — use only their
clothes, shoes and accessories, never their backgrounds), in this order:
LOOK 1: black leather varsity jacket with white script lettering, brown hoodie, gold cross
necklace, very wide brown jeans with curved seams, wheat nubuck work boots.
LOOK 2: washed navy work jacket with a shearling collar, black zip layer, very baggy jeans in a
strong MUSTARD-YELLOW wash, wheat work boots.
LOOK 3: beige cropped work jacket, white T-shirt, gold pendant necklace, very wide olive camouflage
cargo pants, wheat work boots.
LOOK 4: dark brown leather bomber jacket, grey hoodie layer, very wide light-grey sweatpants, black
leather loafers.

0.0–1.0s — LOOK 1. Tilted high-angle shot from behind his shoulder: he stands at the edge of the sea
cliff, the floating staircase climbing into the cloud-filled sky, the tiny white door far above.
1.0–2.0s — He launches onto the stairs and the camera drops in right behind him.
2.0–4.8s — Fast chase from directly behind as he sprints up; clouds rush past on both sides.
4.8–6.4s — CHANGE 1 "CLOUD CROSSING": he bursts straight through a drifting cloud on the stairs, the
frame washes white for a few frames; as the cloud clears the camera is already arcing around to
his front — he is in LOOK 2, sprinting toward the lens in slow motion for a beat — then the camera
whips back behind him and speed snaps back.
6.4–9.0s — Fast chase from behind, the staircase curving over the ocean, scattered glowing clouds
above and below.
9.0–10.6s — CHANGE 2 "ORBIT WIPE": without breaking his stride, the camera sweeps in a fast 180° arc
around him; as his body passes across the lens and fills the frame for an instant, he changes into
LOOK 3; the camera lands on his front three-quarter side in slow motion showing the new outfit as he
sprints toward it, then whips back behind him.
10.6–12.8s — Fast chase from behind above a sea of clouds; the staircase straightens toward the
glowing white door ahead.
12.8–14.4s — CHANGE 3 "SUN FLARE": the camera arcs low around to his front as the sun lines up
exactly behind his head, a burst of light flares across the frame; as it fades he is in LOOK 4,
the leather bomber gleaming in the light, shown from the front in slow motion; the camera whips
back behind him.
14.4–16.4s — He races up the last steps to the door: a tall white arched door in a white stone frame
with a gold handle, standing on a cloud. Without stopping he grabs the handle and pushes it open;
brilliant white light pours out.
16.4–17.2s — The camera follows him straight into the light; full white-out.
17.2–20.0s — ANOTHER WORLD: medium shot from behind him (LOOK 4), framed by the open door edge on the
right: a golden sunrise sky with two suns and small distant planets, an endless sea of clouds,
floating green islands with waterfalls pouring into the clouds, lens flares. He finally stands
still and takes it in as the camera slowly pushes in.

SOUND: driving, soaring cinematic music, wind rush, fast footsteps on stone, a whoosh on each
outfit change, a door creak and a bright shimmer as the light pours out. No text, no logos, no
watermarks.
```
| v2(480p・20秒) | `1842235c-09d6-4713-852c-7d7453745aa6` | seedance_2_5 omni_reference / 9:16 / 480p / 60クレジット。ref=①②③④、慶太 element。プリセット IN THE DARK は辞退 |

## v2 へのユーザー指摘 → v3 方針
- 1回目の着替えの後、階段がただの坂道になった → 階段と景色は絶対に変えない(全フレームで段のある浮遊石段+空一面の雲+海)。
- 回り込んで服が変わるだけでは面白くない → プロのカメラワークで、動画の雰囲気(空・雲・風・光・スピード)に合ったおしゃれなトランジションに。
  1. 雲突破+バレルロール: 背後から低く追い、雲の壁に突っ込む→白の中で速度が上がり、カメラが360°ロールしながら雲を突き破って出ると②
  2. 足元マッチカット: ブーツが石段を踏む足元のマクロ寄り(スロー)→ 次の一歩で新しい靴が同じ位置に着地 → そのまま一気にティルトアップして全身③を見せ、背後追従へ戻る
  3. ローアングル+ドリーズーム+太陽フレア: 石段のふちすれすれの低い位置から見上げ、ドリーズームで背景の空がうねる中、太陽が頭の後ろに重なり光で白く飛ぶ → ヒーローショットで④、スピードランプで通常速度へ
- 合間は背後からの高速追従(v2のまま)。

## 英語プロンプト v3(20秒)
```
A 20-second vertical (9:16) PHOTOREALISTIC live-action fashion film — real person, real light,
shot on a cinema camera with the editing style of a high-end fashion commercial; absolutely no
anime, no cartoon, no illustration, no CGI look.
ONE CHARACTER ONLY: the young man <<<f6c17cc9-ae3d-4123-a642-79d2882414bd>>> — his face, hair and age
match his reference exactly in every frame, including fast motion; never beautify, reshape or
swap his face, no facial distortion.

ENVIRONMENT LOCK (identical in EVERY frame, from first to last, before and after every outfit
change): a STAIRCASE of separate, real weathered sandstone STEPS — each step a distinct block with
a flat tread and a vertical riser, floating high in the open sky with air visible beneath them —
climbing in a gentle S-curve from a sheer sea cliff up to a white arched door standing on a cloud
far above. It is ALWAYS a staircase with clearly visible individual steps: NEVER a ramp, never a
slope, never a road, never a path, never a bridge. Around it, the WHOLE sky is filled with
scattered, separate cumulus clouds of many sizes floating everywhere — near and far, above and
below the stairs — their tops glowing with bright sunlit highlights and golden rim light against
a deep saturated blue sky; far below, a deep blue ocean glittering in the sun. Breathtaking,
dreamlike, high contrast. The staircase and scenery continue unchanged through every transition.

HIS MOTION: he SPRINTS straight up the steps at a thrilling, very fast speed — powerful long
strides landing on each step, arms pumping, clothes whipping in the wind, small stones crumbling
off the steps. He always runs straight up the stairs; never turns sideways, never leaves the
stairs, never slows or stops until the door.

BASE CAMERA (between transitions): a fast FPV-drone chase from directly behind at back height,
close, slight shake, the steps rushing toward the lens, clouds streaking past.

OUTFITS (the four attached headless outfit images are clothing references only — use only their
clothes, shoes and accessories, never their backgrounds), in this order:
LOOK 1: black leather varsity jacket with white script lettering, brown hoodie, gold cross
necklace, very wide brown jeans with curved seams, wheat nubuck work boots.
LOOK 2: washed navy work jacket with a shearling collar, black zip layer, very baggy jeans in a
strong MUSTARD-YELLOW wash, wheat work boots.
LOOK 3: beige cropped work jacket, white T-shirt, gold pendant necklace, very wide olive camouflage
cargo pants, wheat work boots.
LOOK 4: dark brown leather bomber jacket, grey hoodie layer, very wide light-grey sweatpants, black
leather loafers.
Whenever his front is shown, body, head and clothes face the same direction.

0.0–1.0s — LOOK 1. Tilted high-angle shot from behind his shoulder: he stands at the edge of the sea
cliff; the floating stone staircase climbs into the cloud-filled sky, the tiny white door far above.
1.0–2.0s — He launches onto the first step and the camera drops in right behind him.
2.0–4.6s — Fast FPV chase from behind up the steps.
4.6–6.2s — TRANSITION 1 "CLOUD PUNCH + BARREL ROLL": a wall of glowing cloud drifts across the
staircase ahead; he charges straight into it and the camera follows him into pure white; inside,
the speed ramps up and the camera begins a smooth 360° barrel roll; it bursts out of the cloud
mid-roll, levels out on his front three-quarter side, and he is now in LOOK 2, sprinting up the
steps toward the lens in a brief slow-motion beat — then the camera swings back behind him at full speed.
6.2–8.8s — Fast FPV chase from behind; the staircase curves over the glittering ocean.
8.8–10.6s — TRANSITION 2 "FOOTSTEP MATCH CUT": a low macro shot beside the steps in slow motion: his
wheat work boot slams onto a stone step, dust puffing up; match cut on the very next stride — a boot
of LOOK 3 lands on the next step in the same spot of the frame; the camera then tilts up fast from
his feet to his face in one sweeping move, revealing the full LOOK 3 from the front three-quarter
side as he sprints up the steps, then speed ramps back and the camera returns behind him.
10.6–12.6s — Fast FPV chase from behind, rising above a sea of clouds; the steps continue straight
toward the glowing white door.
12.6–14.4s — TRANSITION 3 "SUN FLARE DOLLY ZOOM": the camera drops to the edge of a step in front of
him, looking up low; a dolly zoom makes the sky and clouds swell behind him as the sun slides
exactly behind his head and a burst of light flashes white across the frame; as the glare fades he
is in LOOK 4, a heroic low-angle slow-motion shot of him sprinting up the steps toward the lens, the
leather bomber gleaming — then a speed ramp and the camera whips back behind him.
14.4–16.4s — He races up the last steps to the door: a tall white arched door in a white stone frame
with a gold handle, standing on a cloud. Without stopping he grabs the handle and pushes it open;
brilliant white light pours out.
16.4–17.2s — The camera follows him straight into the light; full white-out.
17.2–20.0s — ANOTHER WORLD: medium shot from behind him (LOOK 4), framed by the open door edge on the
right: a golden sunrise sky with two suns and small distant planets, an endless sea of clouds,
floating green islands with waterfalls pouring into the clouds, lens flares. He finally stands
still and takes it in as the camera slowly pushes in.

SOUND: driving, soaring cinematic music cut to the beat, wind rush, fast footsteps on stone, a deep
whoosh and riser into each transition, a heavy boot thud on the match cut, a door creak and a
bright shimmer as the light pours out. No text, no logos, no watermarks.
```
| v3(480p・20秒・階段固定+プロのトランジション) | `e3af2072-7db4-464a-91fa-6d0b8df443ac` | seedance_2_5 omni_reference / 9:16 / 480p / 60クレジット。ref=①②③④、慶太 element。プリセット IN THE DARK は辞退 |

## v3 へのユーザー指摘 → v4 方針
- 始まりで扉が近すぎる → 扉は「めちゃくちゃ遠く」。最初は空のかなたの小さな光の点で、3回着替えてからようやく近づく。尺を 25 秒に延ばす(480p 75 / 720p 175)。
- トランジションは「何かに隠れて見えなくなり、また見えたら服が変わっている」形に統一:
  1. 階段に流れてきた雲の中に駆け込んで姿が消える → 雲から飛び出すと②
  2. カメラと彼の間を大きな雲のかたまりが横切って彼を隠す(手前の雲ワイプ) → 雲が抜けると③
  3. 白い鳥の群れが画面いっぱいに横切って彼を隠す → 群れが去ると④
- 階段と景色の固定(v3 の ENVIRONMENT LOCK)はそのまま。

## 英語プロンプト v4(25秒)
```
A 25-second vertical (9:16) PHOTOREALISTIC live-action fashion film — real person, real light,
shot on a cinema camera with the editing rhythm of a high-end fashion commercial; absolutely no
anime, no cartoon, no illustration, no CGI look.
ONE CHARACTER ONLY: the young man <<<f6c17cc9-ae3d-4123-a642-79d2882414bd>>> — his face, hair and age
match his reference exactly in every frame, including fast motion; never beautify, reshape or
swap his face, no facial distortion.

ENVIRONMENT LOCK (identical in EVERY frame, from first to last, before and after every outfit
change): a STAIRCASE of separate, real weathered sandstone STEPS — each step a distinct block with
a flat tread and a vertical riser, floating high in the open sky with air visible beneath them —
climbing in long, gentle S-curves from a sheer sea cliff. It is ALWAYS a staircase with clearly
visible individual steps: NEVER a ramp, never a slope, never a road, never a path, never a bridge.
Around it, the WHOLE sky is filled with scattered, separate cumulus clouds of many sizes floating
everywhere — near and far, above and below the stairs — their tops glowing with bright sunlit
highlights and golden rim light against a deep saturated blue sky; far below, a deep blue ocean
glittering in the sun. Breathtaking, dreamlike, high contrast.

THE DOOR IS EXTREMELY FAR AWAY: the staircase is enormously long, winding on and on up into the sky.
At the start, the white arched door at its very end is only a tiny glinting speck of light high in
the distant sky, barely visible above the clouds. It grows very slowly as he climbs; it is still far
away after the second outfit change, and only becomes large and close in the last part of the film.

HIS MOTION: he SPRINTS straight up the steps at a thrilling, very fast speed — powerful long strides
landing on each step, arms pumping, clothes whipping in the wind, small stones crumbling off the
steps. He always runs straight up the stairs; never turns sideways, never leaves the stairs, never
slows or stops until the door.

BASE CAMERA: a fast FPV-drone chase from directly behind at back height, close, slight shake, the
steps rushing toward the lens, clouds streaking past.

OUTFIT CHANGES — "HIDE AND REVEAL": every change happens while he is completely HIDDEN from view by
something passing in front of him; when he becomes visible again he is already wearing the next
outfit, and the camera briefly arcs to his front three-quarter side so the new outfit is clearly
seen (body, head and clothes facing the same direction), then returns behind him.

OUTFITS (the four attached headless outfit images are clothing references only — use only their
clothes, shoes and accessories, never their backgrounds), in this order:
LOOK 1: black leather varsity jacket with white script lettering, brown hoodie, gold cross
necklace, very wide brown jeans with curved seams, wheat nubuck work boots.
LOOK 2: washed navy work jacket with a shearling collar, black zip layer, very baggy jeans in a
strong MUSTARD-YELLOW wash, wheat work boots.
LOOK 3: beige cropped work jacket, white T-shirt, gold pendant necklace, very wide olive camouflage
cargo pants, wheat work boots.
LOOK 4: dark brown leather bomber jacket, grey hoodie layer, very wide light-grey sweatpants, black
leather loafers.

0.0–1.5s — LOOK 1. Tilted high-angle wide shot from behind his shoulder: he stands at the edge of the
sea cliff; the endless floating staircase winds away into the cloud-filled sky; the door is just a
tiny speck of light impossibly far above.
1.5–2.5s — He launches onto the first step and the camera drops in right behind him.
2.5–6.0s — Fast FPV chase from behind up the steps.
6.0–7.8s — CHANGE 1 "INTO THE CLOUD": a big glowing cloud drifts across the staircase ahead; he sprints
straight into it and disappears completely in the white; a beat later he bursts out of the far side
of the cloud in LOOK 2, wisps trailing off him; the camera arcs to his front three-quarter side in a
short slow-motion beat, then swings back behind him at full speed.
7.8–11.5s — Fast FPV chase from behind; the staircase curves over the glittering ocean; the door is
still a small distant glint.
11.5–13.3s — CHANGE 2 "CLOUD WIPE": a huge soft cloud floats between the camera and him, sliding
across the whole frame and hiding him completely; as it slides away he is revealed in LOOK 3 still
sprinting up the steps, shown from the front three-quarter side for a beat, then the camera returns
behind him.
13.3–17.0s — Fast FPV chase from behind, rising above a sea of clouds; the door is now clearly visible
but still far ahead, growing.
17.0–18.8s — CHANGE 3 "FLOCK OF BIRDS": a large flock of white birds sweeps up from below the stairs
and streams across the frame between the camera and him, wings filling the screen and hiding him;
as the flock scatters into the sky he is revealed in LOOK 4, the leather bomber gleaming in the sun,
seen from the front three-quarter side in slow motion; then the camera whips back behind him.
18.8–21.0s — He races up the last steps to the door, now close and towering: a tall white arched door
in a white stone frame with a gold handle, standing on a cloud. Without stopping he grabs the handle
and pushes it open; brilliant white light pours out.
21.0–21.8s — The camera follows him straight into the light; full white-out.
21.8–25.0s — ANOTHER WORLD: medium shot from behind him (LOOK 4), framed by the open door edge on the
right: a golden sunrise sky with two suns and small distant planets, an endless sea of clouds,
floating green islands with waterfalls pouring into the clouds, lens flares. He finally stands
still and takes it in as the camera slowly pushes in.

SOUND: driving, soaring cinematic music cut to the beat, wind rush, fast footsteps on stone, a soft
whoosh as each cloud swallows him, a burst of wingbeats for the flock, a door creak and a bright
shimmer as the light pours out. No text, no logos, no watermarks.
```
| v4(480p・25秒・扉はるか遠く/隠れて現れる着替え) | `c1112e79-3ae2-45d9-8628-4fa35012d4fd` | seedance_2_5 omni_reference / 9:16 / 480p / 75クレジット。ref=①②③④、慶太 element。プリセット IN THE DARK は辞退 |
- v4 自己確認(取り込み直し media `da22894f-…`、0.5秒ごと): 階段は最後まで段のある石段○。景色(雲・海)○。扉は最初から小さく見えるが「光の点」ほど遠くはなく、階段はほぼ一直線。着替え1(6〜7秒・雲に入って消える→②)○、着替え2(11.5〜12.5秒・雲→③)○ ※手前を横切る雲ではなく再び雲に入る形、着替え3(17.5〜18秒・白い鳥の群れ→④)○。現れた直後の斜め前ショットで、走らずに横向きで立ち止まって見えるコマがある。②のパンツはマスタードではなくクリーム色。扉→ホワイトアウト→別世界○。

## v4 へのユーザー指摘 → v5 方針(15秒)
- 着替えの時に立ち止まらない。ずっと走り続け、着替えの瞬間だけスローモーション(緩急)。
- 3回のカメラワークが一辺倒 → 全部変えて飽きさせない。隠すものは 1 雲 / 2 雷 / 3 大量の鳥。
- 尺は15秒(480p 45 / 720p 105)。
- カメラ設計: 1 雲=背後から雲へ→雲の中でクレーンアップして雲の上を越え、正面上方から見下ろして飛び出す瞬間を捉える / 2 雷=石段の横を並走する低いサイドトラッキング、一瞬空が暗くなり雷光で真っ白→横から③ / 3 鳥=正面はるか前方から空撮ドローンが彼に向かって突っ込み、群れの中を突き抜けて正面アップで④。

## 英語プロンプト v5(15秒)
```
A 15-second vertical (9:16) PHOTOREALISTIC live-action fashion film — real person, real light,
shot on a cinema camera with the editing rhythm of a high-end fashion commercial; absolutely no
anime, no cartoon, no illustration, no CGI look.
ONE CHARACTER ONLY: the young man <<<f6c17cc9-ae3d-4123-a642-79d2882414bd>>> — his face, hair and age
match his reference exactly in every frame, including fast motion; never beautify, reshape or
swap his face, no facial distortion.

ENVIRONMENT LOCK (identical in every frame): a STAIRCASE of separate, real weathered sandstone
STEPS — each step a distinct block with a flat tread and a vertical riser, floating high in the open
sky with air beneath — winding in long S-curves from a sheer sea cliff far up into the sky. ALWAYS a
staircase with visible individual steps: never a ramp, slope, road, path or bridge. The whole sky is
filled with scattered cumulus clouds of many sizes, tops glowing with bright sunlit highlights and
golden rim light against a deep blue sky; far below, a deep blue ocean glittering in the sun.
Breathtaking, dreamlike, high contrast.
THE DOOR IS EXTREMELY FAR AWAY: at the start, the white arched door at the end of the endless
staircase is only a tiny glinting speck high in the distant sky; it grows slowly and only becomes
close after the third outfit change.

HIS MOTION — NEVER STOPS: he sprints up the steps at a thrilling, very fast speed the entire time —
powerful strides, arms pumping, clothes whipping in the wind. He NEVER stops, never stands still,
never pauses, never turns sideways: even during and right after every outfit change his legs keep
running up the steps. The ONLY change of pace is the footage itself: normal fast speed everywhere,
and a brief SLOW-MOTION speed ramp only at the instant of each outfit change, snapping back to full
speed right after.
BASE CAMERA (between changes): a fast FPV-drone chase from directly behind at back height.

OUTFITS (the four attached headless outfit images are clothing references only — use only their
clothes, shoes and accessories, never their backgrounds), in this order:
LOOK 1: black leather varsity jacket with white script lettering, brown hoodie, gold cross
necklace, very wide brown jeans with curved seams, wheat nubuck work boots.
LOOK 2: washed navy work jacket with a shearling collar, black zip layer, very baggy jeans in a
vivid MUSTARD-YELLOW wash (clearly yellow, not cream), wheat work boots.
LOOK 3: beige cropped work jacket, white T-shirt, gold pendant necklace, very wide olive camouflage
cargo pants, wheat work boots.
LOOK 4: dark brown leather bomber jacket, grey hoodie layer, very wide light-grey sweatpants, black
leather loafers.
Each outfit changes only while he is completely hidden, and appears already changed when he is seen
again. Body, head and clothes always face the same direction.

0.0–1.0s — LOOK 1. Tilted high-angle shot from behind: he stands at the edge of the sea cliff, the
endless staircase winding away into the sky, the door a tiny speck; he launches onto the first step.
1.0–3.0s — Fast FPV chase from behind up the steps.
3.0–4.6s — CHANGE 1 "CLOUD" (CRANE-OVER): he sprints straight into a big glowing cloud lying across the
stairs and vanishes in the white; the camera does NOT follow him in — it cranes up and sweeps over
the top of the cloud, then tilts down from high in front of it just as he bursts out of the cloud in
LOOK 2, still running, cloud wisps streaming off him — seen from above and in front in slow motion —
then speed snaps back and the camera drops in behind him again.
4.6–6.3s — Fast FPV chase from behind; the staircase curves over the ocean.
6.3–7.9s — CHANGE 2 "LIGHTNING" (LOW SIDE TRACKING): the camera now races alongside him at step
level, tracking his running profile from the side; a single dark storm cloud flickers overhead and a
crackling bolt of lightning strikes the step he is running on in a blinding white flash that hides
him completely — harmless and magical, sparks of light, no injury — the flash fades in slow motion
and he is in LOOK 3, still sprinting in profile, faint glowing sparks drifting off his jacket; speed
ramps back and the camera swings behind him.
7.9–9.4s — Fast FPV chase from behind, rising above a sea of clouds; the door is now visible ahead.
9.4–11.0s — CHANGE 3 "BIRDS" (HEAD-ON DRONE FLY-THROUGH): cut to a drone far ahead and above him, diving
straight toward him down the staircase; a huge flock of hundreds of white birds erupts from below
the stairs and swarms around him until he is completely hidden; the camera flies right through the
flock and, as the birds burst apart, comes face to face with him in LOOK 4 sprinting toward the lens in
slow motion, the leather bomber gleaming; speed snaps back as the camera whips around behind him.
11.0–12.4s — He races up the last steps to the door, now close and towering: a tall white arched door
in a white stone frame with a gold handle, standing on a cloud. Without stopping he grabs the handle
and pushes it open; brilliant white light pours out.
12.4–13.0s — The camera follows him straight into the light; full white-out.
13.0–15.0s — ANOTHER WORLD: medium shot from behind him (LOOK 4), framed by the open door edge: a golden
sunrise sky with two suns and small distant planets, an endless sea of clouds, floating green
islands with waterfalls, lens flares. He finally stands still and takes it in as the camera slowly
pushes in.

SOUND: driving cinematic music cut to the beat, wind rush, fast footsteps on stone, a soft whoosh into
the cloud, a sharp thunder crack, a roar of wingbeats, a door creak and a bright shimmer. No text,
no logos, no watermarks.
```
| v5(480p・15秒・雲/雷/鳥) | `524fe185-8743-4ab0-a14e-496a04495645` | seedance_2_5 omni_reference / 9:16 / 480p / 45クレジット。ref=①②③④、慶太 element。プリセット IN THE DARK は辞退 |
- v5 自己確認(取り込み直し media `d5ff0d89-…`、0.25秒ごと): 全編走り続ける○(立ち止まりなし)。雲(2.5〜3.8秒)→ 正面やや上からのカメラで雲から飛び出す②○ ※パンツはまたマスタードでなくベージュ。雷(6.5〜8秒)→ 横から並走、暗雲と落雷の白い閃光→③を横から○。鳥(9.5〜11秒)→ 高い位置からの引きで群れが覆い④になる○ ※正面からではなく背後からの見せ方。3回ともカメラ位置が違う○。階段は最後まで石段○。扉は最初から形が見える程度(光の点ほど遠くない)。扉→白→別世界○。

## v5 へのユーザー指摘 → v6 方針(原点回帰)
- 指定しすぎて参考動画からかけ離れた → 参考動画(`06ca390e-…`)を忠実にリアル化することを最優先。
- 着替えのたびに雲をくぐるなどの演出は不要。着替えるタイミングだけ緩急(スロー→速く)をつけてカッコよく。
- 方法: 参考動画を video_references として渡し、カメラワーク・構図・タイミング・景色を写させる(画風はアニメではなく実写)。服は4枚の画像、顔は慶太 element。参考動画の少年の顔・服は使わない。
- 費用: 15秒 480p 45 / 720p 105(動画参照ありでも同額)

## 英語プロンプト v6(15秒・参考動画を参照)
```
Recreate the attached reference video SHOT FOR SHOT as a 15-second vertical (9:16) PHOTOREALISTIC
live-action film — same camera moves, same framing, same timing, same staircase, same clouds, same
door and same final world — but filmed for real with a cinema camera: real person, real stone, real
sky and ocean, natural sunlight. Absolutely no anime, no cartoon, no illustration, no CGI look.
Do NOT copy the boy, his face or his clothes from the reference video.
THE PERSON: the young man <<<f6c17cc9-ae3d-4123-a642-79d2882414bd>>> — his face, hair and age match his
reference exactly in every frame; never beautify, reshape or swap his face, no distortion.

Follow the reference exactly:
0.0–0.6s — tilted high-angle shot from above and behind: he stands at the edge of a sea cliff; a
staircase of separate floating sandstone slabs winds up in an S-curve into a deep blue sky full of
towering white cumulus clouds, toward a small white door on a cloud far above; ocean and coastline
far below.
0.6–2.0s — the camera arcs from his side to directly behind him while leveling out; he leaps onto the
first floating slab and starts running.
2.0–6.5s — tracking right behind him at back height, slightly low, as he sprints up the floating
slabs; small stones crumble and fall; wind; the staircase curves left and right; clouds slide past.
6.5–8.0s — he runs through a cloud, the white fills the frame.
8.0–10.0s — above the clouds the staircase goes straight up toward the door, which glints.
10.0–11.5s — the white arched door with a gold handle, standing on a cloud, grows to fill the frame
as he reaches it.
11.5–12.5s — he grabs the handle and pushes the door open; white light pours out.
12.5–13.3s — white-out as he steps through.
13.3–15.0s — from behind him, the open door frame on the right: another world with a golden sunrise,
several suns and small planets, a sea of clouds and floating green islands with waterfalls; he
stands and looks out; lens flares.

FASHION — THREE OUTFIT CHANGES WHILE HE RUNS (the four attached headless outfit images are clothing
references only — use only their clothes, shoes and accessories, never their backgrounds):
LOOK 1 (start): black leather varsity jacket with white script lettering, brown hoodie, gold cross
necklace, very wide brown jeans, wheat work boots.
LOOK 2 (from about 3.5s): washed navy work jacket with a shearling collar, black zip layer, very
baggy mustard-yellow jeans, wheat work boots.
LOOK 3 (from about 6.0s): beige cropped work jacket, white T-shirt, gold pendant, very wide olive
camouflage cargo pants, wheat work boots.
LOOK 4 (from about 9.0s, through the door and the final world): dark brown leather bomber, grey
hoodie layer, very wide light-grey sweatpants, black leather loafers.
HOW EACH CHANGE LOOKS: nothing covers him and no extra effects are added. He never stops running. At
each change the footage ramps into slow motion for about half a second at the top of a stride — the
outfit snaps to the next look in that instant — then ramps back hard to full speed. The camera keeps
following the reference camera path. Body, head and clothes always face the same direction.

SOUND: soaring cinematic music with a beat hit and whoosh on each slow-motion change, wind, footsteps
on stone, a door creak and a bright shimmer. No text, no logos, no watermarks.
```
| v6(480p・15秒・参考動画を参照して忠実に実写化) | `61df6b03-a136-4bd0-aaa9-d86bd4417aa2` | seedance_2_5 omni_reference / 9:16 / 480p / 45クレジット。video_ref=参考動画 `06ca390e-…`、ref=①②③④、慶太 element。プリセット IN THE DARK は辞退 |
- v6 自己確認(取り込み直し media `8a32c71d-…`、参考動画と上下に並べて0.5秒ごと比較): 構図・カメラ・タイミング・階段・雲・扉・別世界は参考動画とほぼ一致(非常に忠実)。しかし**画風がアニメのまま**で実写になっていない(参考動画の画風に引っ張られた)→ 顔も慶太にならずアニメ顔。服の順番も混ざった(①→③の上着+②寄りのパンツ→②の上着+③のパンツ→④)。
- 結論: 参考動画を video_references に入れると画風まで写る。次は参考動画を渡さず、実写の開始コマ画像(慶太×①、参考動画1コマ目の構図)を作って start_image にし、テキストで参考動画のカット割りを忠実に書く方式を提案。

## v7: 実写の開始コマ → 動画化
| 実写の開始コマ(慶太×①、参考動画1コマ目の構図) | `9599f081-111f-4b93-a35e-b3ba1cf58494` | nano_banana_pro 指定 / 9:16 / 2k / 2クレジット。慶太 element+① `0f9a7480-…`。**失敗: 実写にはなったが人物が慶太ではない別人になった**(①のコーデ写真の人物の手の肌色などに引っ張られたと推定)。取り込み直し media `389eab05-…`(使用しない) |
- 対策案: 顔の見本として、OK済みの実写の慶太全身画像 `452bbba9-…`(慶太×服装②)も参照に加え、「人物の顔・肌・体型は慶太の画像からのみ。コーデ画像の人物の肌や体は無視」と明記。
| 実写の開始コマ 再作成(慶太の実写全身 `452bbba9-…` を顔の見本に追加) | `5bb9aaa6-823a-4242-9e37-089ddd78f59d` | nano_banana_pro / 9:16 / 2k / 2クレジット。**顔を切り出して慶太の参照写真と比較し、慶太(日本人・センター分け・リムレス眼鏡)と確認**。取り込み直し media `3c3cf17c-7315-479e-8644-b7e9d132d20b` |
| v7 動画(480p・15秒・実写開始コマ+参考動画のカット割りをテキストで) | `f176fe78-2c3d-4d7e-a636-1fc3de44eb53` | seedance_2_5 omni_reference / 9:16 / 480p / 45クレジット。start=`3c3cf17c-…`、ref=慶太実写全身 `452bbba9-…`+②③④、慶太 element。参考動画は渡さない |
- v7 自己確認(取り込み直し media `264bbe01-…`、参考動画と比較+顔切り出し): 実写○。顔は冒頭の横顔・8秒の正面とも日本人・リムレス眼鏡・同じ髪型で慶太○(別人化なし)。流れ(断崖→S字浮遊石段→背後追従→雲→扉→白→別世界)は参考動画に近い○。着替えは①→②(4.5秒)→③(7.5秒)→④(10秒)の順○。問題: ③は雲の中で**立ち止まって正面を向いて**現れる(7.5〜9秒)/②のパンツはマスタードでなくベージュ/着替えが「スローで一瞬切り替わる」ほどはっきりしない。

## v7 へのユーザー指摘 → v8 方針(カメラワーク)
- 最初の約2秒は後ろ姿で颯爽と速く走る画角でOK。そこからコーデが3回変わるまでは、カメラが前に回り込み、ずっと前(正面)から写す。最後に扉を開ける時に再び後ろへ戻る。
- v8 プロンプト: v7 をベースに、カメラを「0.6〜2.0秒 背後 → 2.0〜2.8秒 前へ回り込み → 2.8〜10秒 正面から後退しながら先導 → 10〜10.8秒 背後へ戻る → 扉・白・別世界は背後から」に変更。着替えは 3.5/6.0/8.5秒(すべて正面カメラ中)。「立ち止まらない」と「マスタードを強い黄色で」を明記。素材は v7 と同じ。

| v8 動画(480p・15秒・正面先導カメラ) | `6834e732-595d-4262-abd6-bf8deb12fcf3` | seedance_2_5 omni_reference / 9:16 / 480p / 45クレジット。素材は v7 と同じ(start `3c3cf17c-…`、慶太全身 `452bbba9-…`+②③④) |
- v8 自己確認(取り込み直し media `685d7a4f-9d87-4be0-9051-cc5d5b153156`、コンタクトシート+顔切り出し): 実写○。顔は正面4カットとも日本人・リムレス眼鏡・センター分けで慶太○(表情は険しめ、髪はやや膨らむ)。カメラは0〜2秒背後→2.5秒で正面→10.5秒で背後へ戻り扉→白→別世界○。着替えは②約3秒/③約6秒/④約8秒、走り続けたまま○。問題: **正面カメラ中(2.5〜10秒)は景色が変わり、空に浮かぶ石段ではなく、曇り空の下で崖の上の草原沿いの地上の石段になっている**(背景に空と雲がなく、浮遊感が消えた)/②のパンツはまたベージュ/スローの緩急は弱い。

## v8 へのユーザー指摘 → v9 方針(着替えごとに演出を変える)
- 1回目: 階段途中の雲に突っ込み、抜けた瞬間に②。抜けた時にカメラが正面へ回り込む。
- 2回目: 足元のアップ。段に着地した瞬間に③、カメラが引いて正面から全身を見せる。
- 3回目: 空から雷が落ちて④。変わった瞬間に正面へ回り込む。
- 正面に回るのは着替え直後だけ。その後は再び背後から追う。着替え時はスロー・緩急。慶太は常に猛スピードで走り、止まらない。風景・階段は変えない(v8で正面時に地上の草原になった対策として、正面カメラはローアングルで見上げ、背景は空・雲・浮遊石段のみと明記)。

| v9 動画(480p・15秒・雲/足元/雷の3演出) | `28e5b621-31f6-4141-ac17-997cca5528a7` | seedance_2_5 omni_reference / 9:16 / 480p / 45クレジット。素材は v7・v8 と同じ |
- v9 自己確認(取り込み直し media `ce7f4790-b58f-48d7-97f1-a706ffd454bb`、コンタクトシート+顔切り出し): 実写○。顔は横顔3カットとも日本人・リムレス眼鏡・同じ髪型で慶太○。**景色は最後まで青空の浮遊石段のまま○**(v8の草原化は解消)。演出: 雲突入→抜けて②(約3秒)○/足元アップで着地→③(約6秒)○/雷が直撃→④(約9秒)○。各着替え後に背後へ戻る○、走り続ける○、扉→白→別世界○。問題: 着替え後のカメラが**正面ではなく真横(ローアングルの横顔)**/②のパンツは今回もベージュ寄り/中盤の石段がS字でなく真っ直ぐ。
