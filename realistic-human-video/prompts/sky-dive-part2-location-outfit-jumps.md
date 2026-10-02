# 宇宙ダイブ着替え動画 Part 2 — 場所と服が1秒ごとに切り替わる(企画)

- 前作: `sky-dive-outfit-v2.md` の v3(`5fd39ab5-…`)。最後は歩道橋の上で完成コーデ(黒長袖・グレーワイドデニム・白黒スニーカー)の男性がポケットに手を入れて笑う。
- 人物: 慶太(element `f6c17cc9-ae3d-4123-a642-79d2882414bd`)
- 尺: 8秒 / 9:16 / 音声あり(ビートに合わせたカット)

## 構成(約1秒ごとにマッチカット)
| 時間 | 場所 | 服装(ファッションの見せ場) |
|---|---|---|
| 0.0–1.5 | 歩道橋(前作のラスト) | 前作の完成コーデ(黒長袖・グレーワイドデニム・白黒スニーカー) |
| 1.5–2.7 | 草原 | 生成りのリネンシャツ+ベージュのワイドパンツ+茶色のレザーサンダル |
| 2.7–3.9 | 海(砂浜) | 紺地に白柄の開襟シャツ+白のショートパンツ+白スニーカー |
| 3.9–5.1 | 山(稜線) | オレンジのマウンテンパーカー+黒のカーゴパンツ+トレッキングブーツ |
| 5.1–6.3 | 滝(滝つぼの岩場) | 黒のナイロンセットアップ+白T+黒のスポーツサンダル |
| 6.3–8.0 | 神社(朱色の鳥居の前) | 藍色の羽織+白T+黒のワイドパンツ+雪駄。最後にカメラ目線で決めポーズ |

- カメラ: 全カット同じ構図(正面・全身・中央、目線の高さで固定)。場所と服だけが切り替わり、慶太の立ち位置は変わらない「ジャンプカット/マッチカット」。切り替え時に一瞬の白フラッシュ+風。
- 顔: 全カット慶太で固定。

## 手順
1. キーフレーム画像5枚(草原・海・山・滝・神社 × 各服装、同じ構図の全身)— nano_banana_pro / 9:16 / 2k / 各2クレジット(計10)
2. 動画: seedance_2_5 omni_reference / 8秒。開始コマ=前作の完成コーデ画像 `47219cff-…`、参照=キーフレーム5枚+慶太 element。費用: 480p 24 / 720p 56 クレジット(プレフライト)

## 方針追加(ユーザー指定)
- 風景は「コントラストの効いた幻想的で美しい場所」にする(草原=金色の逆光と光の粒、海=夕焼けが濡れた砂に映る、山=雲海とアルペングロー、滝=虹と光の筋、神社=朱の鳥居・灯籠・桜吹雪)。

## 生成ログ
| 内容 | job_id | 備考 |
|---|---|---|
| K1 草原 | `b6ba4d76-477a-484d-8037-15b4edce9545` | nano_banana_pro 指定(記録上 nano_banana_2)/ 9:16 / 2k / 2クレジット。慶太 element |
| K2 海 | `44c64716-93fb-486f-ae00-9eaf28f10b38` | 同上 |
| K3 山 | `890d11fa-20d3-4d51-9f95-2465da8a4806` | 同上 |
| K4 滝 | `ca17a1bd-6557-4847-aec8-c99c5422a1ab` | 同上 |
| K5 神社 | `289ace11-ad89-4964-b7fb-2287b849629c` | 同上 |

## 変更(ユーザー指定): 服装はユーザー提供の5枚のコーデ画像に差し替え
- 上の K1〜K5 は服装案が仮のため使わない。場所と風景(幻想的・高コントラスト)はそのまま、服を以下に変更。顔は慶太(element)。
| 場所 | 服装画像 | 服の内容 |
|---|---|---|
| 草原 | ①(ユーザー画像1) | 濃紺の生デニムのジップアップワークジャケット(短丈・ステッチ・胸ポケット・襟裏ペイズリー)、白の襟付きシャツ、黒レザーベルト(シルバーの星バックル)、シルバーのウォレットチェーン2本(1本はパール)、極太の濃紺生デニム、茶色のワークブーツ、シルバーリング |
| 海 | ②(ユーザー画像2) | 紺のサテンのスタジャン(胸に黄色の筆記体ロゴ・黄ラインのリブ)、ライトグレーのジップパーカー、ライトグレーのワイドスウェットパンツ、グレー×白スニーカー |
| 山 | ③(ユーザー画像3) | ダークオリーブのオイルドジャケット(茶色コーデュロイ襟)、白×青ストライプのボタンダウンシャツ(裾出し)、黒リュック、中濃色のワイドデニム(タック入り)、黒×グレー×白スニーカー |
| 滝 | ④(ユーザー画像4) | 中色ブルーのオーバーサイズデニムジャケット(短丈)、極太の色落ちブルーデニム、シルバーのカラビナキーホルダー、白のボリュームスニーカー |
| 神社 | ⑤(ユーザー画像5) | コバルトブルーのフリースジップパーカー、白のグラフィックT、金の四角いペンダントネックレス、シルバーリング、白×グレーのスノーカモ柄ワイドカーゴ、コバルトブルーのスニーカー |
- 手順: 5枚を media_upload_widget でアップロード → 各画像を参照に、慶太 element+場所のプロンプトで全身キーフレームを作り直し(nano_banana_pro / 2k / 各2クレジット、計10)。生成はユーザーの許可後。
- プロンプト共通: "<<<慶太>>> wearing EXACTLY the outfit in the attached image (the image has no head — use only the clothes, shoes and accessories; the face comes only from his reference)"
- アップロード済み(中身を確認して対応付け): 草原① `60cd028b-36d0-4401-9f5a-9a138039f490`(11.png)/ 海② `38e6db50-1b17-48db-ab6c-0d862e729956`(22.png)/ 山③ `55ce8cba-417c-4be3-a895-43f0f7934a98`(33.png)/ 滝④ `29c3be30-1cb6-4b95-832f-714388a3ca59`(44.png)/ 神社⑤ `ea41ff23-d5be-4ff8-84cc-f10d2b4fb063`(55.png)

## 動画プロンプト(キーフレーム画像なし・コーデ画像を直接参照)
- seedance_2_5 / omni_reference / 8秒 / 9:16 / 音声あり。費用: 480p 24 / 720p 56(プレフライト)
- medias: start_image=前作の完成コーデ `47219cff-…`、image_references(順番固定)= 1:草原① `60cd028b-…` 2:海② `38e6db50-…` 3:山③ `55ce8cba-…` 4:滝④ `29c3be30-…` 5:神社⑤ `ea41ff23-…`、慶太 element

```
An 8-second vertical (9:16) photorealistic fashion film — a "location jump" outfit-change edit.
ONE CHARACTER ONLY: the young man <<<f6c17cc9-ae3d-4123-a642-79d2882414bd>>>. His face, hair and age
match his reference exactly in every frame; never beautify, reshape or swap his face, no facial
distortion. The five attached outfit images are headless clothing references — use ONLY their
clothes, shoes and accessories, never their backgrounds; his face comes only from his reference.

CAMERA (identical in every location): locked-off, straight-on, eye level, 35mm lens. He stands
in the center of the frame facing the camera, full body head to toe, always the same size and
the same position in the frame. Only the location and his outfit change; he never moves out of
place. Every change happens on the beat as a hard match cut with a 2-frame white light flash, a
gust of wind and a few floating light particles. Every location is breathtaking, fantastical and
beautiful, with strong contrast and glowing specular highlights: rim light on his hair and
shoulders, sparkling highlights on fabric, metal and water, deep rich shadows, vivid saturated
colors, cinematic HDR look.

0.0–1.4s — WHITE PEDESTRIAN BRIDGE AT DUSK (continuing from the first frame): he stands in the
outfit of the first frame — black long-sleeve top with white chest text, grey wide-leg denim,
chunky white-and-black sneakers — hands in pockets, smiling. Glass towers glitter behind him.
1.4s — FLASH CUT.
1.4–2.7s — GOLDEN MEADOW: an endless rolling meadow of tall glowing grass and wildflowers, low
golden sun backlighting him, god rays through towering clouds, sparkling pollen. Outfit = attached
image 1: dark raw-denim cropped zip-up work jacket with contrast stitching, white collared shirt,
black leather belt with a silver star buckle, two silver wallet chains (one pearl), very wide
dark raw-denim jeans, brown lace-up work boots, silver rings.
2.7s — FLASH CUT.
2.7–4.0s — SUNSET SEA: a pure white-sand beach at the water's edge, crystal turquoise waves,
a violet-pink-gold sunset sky mirrored on the wet sand, sun glitter on the sea. Outfit = attached
image 2: navy satin varsity jacket with yellow script lettering on the chest and yellow-striped
ribbed cuffs and hem, light heather-grey zip hoodie, light-grey wide sweatpants, grey-and-white
sneakers.
4.0s — FLASH CUT.
4.0–5.3s — MOUNTAIN RIDGE ABOVE A SEA OF CLOUDS: jagged snow peaks glowing pink and orange in
alpenglow, a deep indigo sky with the first stars, crisp cold light. Outfit = attached image 3:
dark-olive waxed cotton jacket with a brown corduroy collar, white-and-blue striped button-down
shirt with the hem out, black backpack, wide pleated mid-blue denim, black-grey-white sneakers.
5.3s — FLASH CUT.
5.3–6.6s — GIANT WATERFALL: he stands on a dark wet rock in front of a towering waterfall falling
into an emerald pool, a vivid rainbow in the glowing mist, sunbeams piercing the spray, lush
jungle. Outfit = attached image 4: oversized cropped mid-blue denim trucker jacket, very baggy
faded blue jeans with a silver carabiner keychain, chunky white sneakers.
6.6s — FLASH CUT.
6.6–8.0s — JAPANESE SHRINE: a towering vermilion torii gate behind him, a stone path lined with
glowing stone lanterns, giant cedars, cherry-blossom petals drifting in golden light and soft
mist. Outfit = attached image 5: cobalt-blue fleece zip hoodie, white graphic T-shirt, gold
rectangular pendant necklace, silver rings, white-and-grey snow-camo baggy cargo pants, cobalt-blue
sneakers. Final beat: he looks straight into the lens with a cool confident smile, the camera
pushes in slightly, freeze on the last frame.

SOUND: a punchy beat with a whoosh and shimmer on every cut; wind, waves, waterfall roar and a
temple bell layered softly under each location. No text, no captions, no watermarks.
```

## 動画 生成ログ
| 内容 | job_id | 備考 |
|---|---|---|
| Part2 動画(480p) | `4efa4837-972b-446f-96c5-76f431096446` | seedance_2_5 omni_reference / 8秒 / 9:16 / 480p / 24クレジット。プリセット IN THE DARK は辞退。注意: 受付記録では start_image も reference_images の先頭に並んでいたため、「attached image 1〜5」の番号が1つずれて解釈される可能性あり |
- 4efa4837 結果(ユーザー): 服装・風景は良い。ただし男性が突っ立ったまま切り替わるだけでつまらない → カメラが回転しながら風景を見せ、服も変わっていく案へ。

## v2 案: 回り込みカメラ(オービット)+ 隠しトランジション(12秒)
- カメラは最初から最後まで止まらず時計回りに彼の周りを回り続ける。回り込みの途中で「彼の背中/手前の草・波しぶき・雲・滝の霧・桜吹雪」が画面を一瞬覆った瞬間に、場所と服が切り替わる(ワンカット風)。
- 場所ごとに高さと動きを変える(低い位置→上昇→ドローン的な俯瞰→水面すれすれ→正面に着地して寄る)。彼も歩く・振り返る・襟を直すなど動く。
- 服は番号ではなく特徴で指定(参照番号のずれ対策)。
- 費用: 480p 36 / 720p 84 クレジット(12秒、プレフライト)

```
A 12-second vertical (9:16) photorealistic fashion film shot as ONE continuous, unbroken orbiting
camera move — an outfit-and-location change edit with invisible transitions.
ONE CHARACTER ONLY: the young man <<<f6c17cc9-ae3d-4123-a642-79d2882414bd>>>. His face, hair and age
match his reference exactly in every frame, including profiles and fast motion; never beautify,
reshape or swap his face, no facial distortion. The attached headless outfit images are clothing
references only — use only their clothes, shoes and accessories, never their backgrounds.

CAMERA RULE: the camera NEVER stops. It keeps circling him clockwise on a smooth gimbal/drone
orbit for the whole film, with speed ramps (fast whip through each transition, easing into slow
motion as each new location is revealed). Each location change is an INVISIBLE TRANSITION: as the
camera sweeps behind him, his back or a foreground element (grass, wave spray, cloud, waterfall
mist, cherry petals) fills the frame for a few frames, and when it clears, the location AND his
whole outfit have changed while the orbit continues seamlessly. Every location is breathtaking,
fantastical and beautiful with strong contrast and glowing highlights: rim light on his hair and
shoulders, sparkling highlights on fabric, metal and water, deep rich shadows, vivid colors.

0.0–2.0s — WHITE PEDESTRIAN BRIDGE AT DUSK (from the first frame): he stands in the black
long-sleeve top with white chest text, grey wide-leg denim and chunky white-and-black sneakers,
hands in pockets, smiling. The camera starts orbiting to the right at chest height; glass towers
and city lights slide past behind him. He pulls his hands out of his pockets. The camera whips
behind his back — transition.
2.0–4.0s — GOLDEN MEADOW: the camera comes around low, skimming through tall glowing grass in the
foreground, the low golden sun flaring behind him, god rays through towering clouds, sparkling
pollen. ORIENTATION LOCK: here the camera stays IN FRONT of him, orbiting only between his
front-left and front-right three-quarter angles (never behind him), so the FRONT of his outfit is
clearly visible the whole time — jacket zip, collar, belt buckle and wallet chains facing the
camera. His body, head and clothes always face the same direction together: his face and chest
toward the camera; the outfit is never shown front-facing on a back-turned body. He walks slowly
toward the camera through the grass. Outfit: dark raw-denim cropped zip-up work jacket with
contrast stitching, white collared shirt, black belt with a silver star buckle, two silver wallet
chains (one pearl), very wide dark raw-denim jeans, brown lace-up work boots.
Tall grass sweeps across the lens — transition.
4.0–6.0s — SUNSET SEA: the orbit continues while the camera rises slightly; a pure white-sand beach,
turquoise waves, a violet-pink-gold sunset mirrored on the wet sand. He spins on his heel to face
the camera, sand kicking up. Outfit: navy satin varsity jacket with yellow script lettering and
yellow-striped ribbed cuffs and hem, light-grey zip hoodie, light-grey wide sweatpants,
grey-and-white sneakers. A burst of wave spray fills the frame — transition.
6.0–8.0s — MOUNTAIN RIDGE ABOVE A SEA OF CLOUDS: the camera soars up and circles him from above like
a drone, revealing jagged snow peaks glowing pink and orange in alpenglow and an endless sea of
clouds under an indigo sky. He looks out over the view, wind in his hair. Outfit: dark-olive waxed
cotton jacket with a brown corduroy collar, white-and-blue striped button-down shirt with the hem
out, black backpack, wide pleated mid-blue denim, black-grey-white sneakers. The camera dives
through a cloud — transition.
8.0–10.0s — GIANT WATERFALL: the camera sweeps around him low, just above the water's surface, a
towering waterfall behind him, a vivid rainbow in the glowing mist, sunbeams through the spray.
He stands on a wet rock and flips up his jacket collar. Outfit: oversized cropped mid-blue denim
trucker jacket, very baggy faded blue jeans with a silver carabiner keychain, chunky white
sneakers. Mist washes over the lens — transition.
10.0–12.0s — JAPANESE SHRINE: the orbit slows and lands in front of him; a towering vermilion torii
gate, glowing stone lanterns, giant cedars, cherry-blossom petals swirling around him in golden
light. Outfit: cobalt-blue fleece zip hoodie, white graphic T-shirt, gold rectangular pendant
necklace, white-and-grey snow-camo baggy cargo pants, cobalt-blue sneakers. The camera pushes in
as he looks straight into the lens with a cool confident smile. Freeze on the last frame.

SOUND: a driving beat; a whoosh on every transition; wind, waves, waterfall and a temple bell
layered softly under each location. No text, no captions, no watermarks.
```
| Part2 v2 回り込みカメラ(480p・12秒) | `ff84fa5e-1ab5-455f-80b5-2ccd3c3fd377` | seedance_2_5 omni_reference / 12秒 / 9:16 / 480p / 36クレジット。参照は前回と同じ。プリセット IN THE DARK は辞退 |
- ff84fa5e 結果(ユーザー): 惜しい。草原で男性が後ろ向きなのに服が前向きになった → 草原はカメラを前側(斜め前〜斜め前)に限定し、体・顔・服の向きを一致させる指示を追加。他はOK。
| Part2 v3(720p・12秒・草原の向き修正) | `506e9a87-8942-4dd5-94cb-3fc56731ffcd` | seedance_2_5 omni_reference / 12秒 / 9:16 / 720p / 84クレジット。参照は前回と同じ。プリセット IN THE DARK は辞退 |
