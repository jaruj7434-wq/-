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
