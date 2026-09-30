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
