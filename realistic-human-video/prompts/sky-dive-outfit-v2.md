# 宇宙ダイブ着替え動画 v2(作り直し)

## 素材(Higgs Field media_id)
| 用途 | media_id | 備考 |
|---|---|---|
| 男性の顔(顔の参考のみ。服は無視) | `8225976c-539b-4625-810e-2be0b9a9639a` | 慶太くん顔.PNG |
| 完成コーデの全身(=動画の最後のコマ) | `47219cff-0261-4ed9-a060-5644d0cf8fcc` | IMG_8409.PNG |

- 元動画は未アップロード。カメラの降下ルートはプロンプトで指定する。

## 仕様
- 10秒 / 9:16
- 最初の服装: 白のタンクトップ+黒のボクサーパンツ、裸足
- 飛んでくる服: 黒の長袖(胸に白い文字)、グレーのワイドデニム、白黒のスニーカー(完成画像のもの)

## ステップA: 最初のコマ画像(nano_banana_pro / 9:16 / 2k / 2クレジット)
参照: 完成コーデ画像(服の見本として)

```
Vertical 9:16 photorealistic cinematic frame, view from low Earth orbit: the curved horizon of
planet Earth with a thin glowing blue atmosphere line and a sunrise glint, black space above.
Floating right in front of the camera, weightless and sharply in focus, are three clothing
items taken exactly from the outfit in the reference image: the black long-sleeve top with the
white text print on the chest, the grey washed wide-leg denim trousers, and the pair of
chunky white-and-black sneakers. The garments are spread out as if caught mid-flight, sleeves
and trouser legs fluttering, all pointing down toward the Earth, ready to dive. No person in
the frame. Ultra-detailed fabric textures, realistic lighting from the sun on the left.
```

## ステップB: 動画(minimax_h3 / 10秒 / 9:16 / 2K / 20クレジット)
- start_image: ステップAの画像
- end_image: `47219cff-…`(完成コーデの全身)
- image_references: `8225976c-…`(顔)

```
One continuous 10-second vertical shot with no cuts, photorealistic, cinematic.
0-1s: Low Earth orbit. The black long-sleeve top, grey wide-leg denim trousers and chunky
white-and-black sneakers float right in front of the camera.
1-5s: The camera and the three garments dive together at extreme speed straight down toward
Earth. The garments stay in frame just ahead of the lens the whole time, flapping violently in
the wind: through the glowing atmosphere, punching through a thick layer of white clouds,
then down over a sprawling modern city at dusk with streetlights coming on, weaving between
glass skyscrapers, and leveling out just above a white elevated pedestrian bridge.
5-7s: On the bridge stands the young man from the face reference image (same face, same
hairstyle, same glasses), wearing only a plain white tank top and black boxer briefs, barefoot,
facing the camera and waiting. The garments shoot past the camera toward him.
7-9s: The garments fly into him one after another and dress him instantly: the grey denim
trousers zip up over his legs, the sneakers snap onto his feet, the black long-sleeve top drops
over his head and slides down onto his body, with a gust of wind and a whoosh.
9-10s: The outfit is complete, exactly as in the end image. He puts his hands in his pockets
and smiles at the camera. The camera slowly pushes in.
Keep his face identical to the face reference in every frame. Smooth, realistic motion,
natural fabric physics, no distortion.
```

## 生成ログ
| ステップ | job_id | 備考 |
|---|---|---|
| A(最初のコマ) | `da3e5df0-ccab-4938-a072-42b2baa60564` | 完了。ジョブ記録上のモデルは `nano_banana_2` |
| B(動画)1回目 | ― | 422エラーで未実行(MiniMax H3 は start/end_image と image_references を併用不可)。クレジット消費なし |
| B(動画)案A | `c140a802-1be2-41bf-8b1e-2bac764f7f9d` | 完了(2026-10-01、1440×2560)。minimax_h3 / 10秒 / 9:16。start=`da3e5df0-…`、end=`47219cff-…` のみ(顔参照なし)。プリセット ELEVATE は辞退 |

## v3 改善案(服が最後まで映らなかった問題への対応)

### v2 の問題(ユーザー確認)
- 宇宙〜地球到達までは服が映るが、ビルや男性が見えてくる頃には服が画面から消えていた。

### 方針
- 10秒を1回で作ると途中で服が消えやすいため、**中間のコマ画像**を作り、5秒×2本に分ける。
  - 中間コマ: 画面手前に服3点(長袖・デニム・スニーカー)が大きく映り、その奥の歩道橋に
    白タンクトップ+黒ボクサーパンツ・裸足の男性が立っている(=服が男性に飛び込む直前)
  - 前半(5秒): start=宇宙コマ `da3e5df0-…` → end=中間コマ
  - 後半(5秒): start=中間コマ → end=完成コーデ `47219cff-…`
- プロンプトで「服3点は常に画面下1/3〜中央の手前に固定され、一度もフレームから出ない」と明記。
- 2本の結合はローカルで ffmpeg(ユーザーが2本をチャットに添付)または編集アプリで行う。

### 中間コマ画像(nano_banana_pro / 9:16 / 2k / 2クレジット)
参照: 顔 `8225976c-…`、完成コーデ `47219cff-…`(服の見本と歩道橋の背景)

```
Vertical 9:16 photorealistic cinematic frame, a moment frozen in a high-speed fly-through
shot over a white elevated pedestrian bridge between glass skyscrapers at dusk.
FOREGROUND (large, sharp, filling the lower and middle part of the frame, motion-blurred edges):
the three garments from the outfit reference image flying toward the man at high speed —
the black long-sleeve top with the white text print, the grey washed wide-leg denim trousers,
and the pair of chunky white-and-black sneakers.
BACKGROUND (center, about 15 meters ahead, in focus): on the bridge stands the young man from
the face reference image (same face, hairstyle and glasses), wearing only a plain white tank
top and black boxer briefs, barefoot, standing still, facing the camera and waiting with a
calm smile. Same bridge, railings and glass buildings as in the outfit reference image.
Strong speed lines, wind, realistic lighting.
```

### 前半動画(minimax_h3 / 5秒 / 10クレジット)
```
One continuous 5-second vertical shot, no cuts. The camera dives at extreme speed from low
Earth orbit straight down to a city. The black long-sleeve top, grey wide-leg denim trousers
and chunky sneakers fly together right in front of the lens the ENTIRE time: they stay locked
in the lower-middle foreground of the frame and never leave the frame, flapping in the wind,
through the glowing atmosphere, through white clouds, over the dusk city, between glass
skyscrapers, and leveling out above a white elevated pedestrian bridge where a young man in a
white tank top and black boxer briefs stands waiting, exactly as in the end image.
```

### 後半動画(minimax_h3 / 5秒 / 10クレジット)
```
One continuous 5-second vertical shot, no cuts. The garments in the foreground keep flying
straight toward the young man on the bridge and stay visible until they hit him: the grey
denim trousers wrap onto his legs, the sneakers snap onto his bare feet, and the black
long-sleeve top drops over his head and slides down over the tank top, with a gust of wind.
The outfit is now complete exactly as in the end image; he puts his hands in his pockets and
smiles at the camera as the camera slows and gently pushes in. Same face in every frame,
realistic fabric physics, no distortion.
```
