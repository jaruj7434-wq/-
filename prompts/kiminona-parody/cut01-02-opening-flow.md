# 冒頭 0〜11秒の流れ(本予告を 4fps で分析)

## 本予告の流れ
| 秒 | カメラ | 映像 |
|---|---|---|
| 2.0–5.5 | 高高度。ゆっくり下を向きながら下降 | 雲海の上の夕暮れ。太陽(点線状の縦・横フレア、淡い虹色のリング)。右上から細い白い線の隕石がほぼ真下へ。後半、手前の雲が暗くなり、右下へオレンジ色の丸いレンズフレアが連なる |
| 5.5–6.0 | そのまま雲の中へ突入 | 手前の巨大な雲が画面を覆い、白〜灰色にかすむ(雲をくぐるトランジション)→ 一瞬、暗い青のぼやけ |
| 6.0–6.75 | 雲の下に抜ける。少女の真後ろ・やや下から | 夜。少女の後ろ姿(黒髪のショートボブ、模様入りの青い和服)が画面下中央に大きく。満天の星空とちぎれ雲。画面左上に、天の川のようなうっすら紫〜ピンクの光の帯 |
| 6.75–8.5 | ゆっくり上へティルト(少女の頭が画面下へ沈んでいく) | 画面右上から、強く光るシアン色の太い光の筋(尾)が差し込む。その下に細い白い線が伸び、先端に赤く光る小さな塊(破片)。カメラが筋を追って上を向く |
| 8.75–10.75 | 引き・あおり。少女は画面右下に小さく、横顔で空を見上げる。髪がなびく | 右上から画面中央へ、シアン〜白の太い光の帯が大きな弧を描き、外側にマゼンタ・ピンク・紫の帯が重なる(一筋のオーロラのような尾)。その下に細い白い線と、先端の赤く光る小さな塊。星空とちぎれ雲 |
| 10.75 | カット | 次の「日常の断片」へ |

## パロディへの置き換え
| 本予告 | デブの名は。 |
|---|---|
| 雲海の上の夕暮れと細い白い線の隕石 | 作成済みの開始画像(先端が小さな唐揚げ)`aa3bc47a-…` |
| 雲をくぐるトランジション | 同じ(カメラが雲に突っ込み、白くかすんで抜ける) |
| 少女の後ろ姿(ショートボブ、青い和服) | **ヒロインの後ろ姿**(ポニーテールに赤いゴム、丸い大きな肩と背中)。衣装は要相談 |
| 満天の星空、紫〜ピンクの光の帯 | 同じ(実写の星空、天の川) |
| シアンの太い光の帯+マゼンタ・紫の帯(一筋のオーロラのような尾) | 同じ(実写のオーロラのような光の帯) |
| 細い白い線と、先端の赤く光る小さな塊 | 細い白い線の先端の、**赤く光る唐揚げ**(大気圏で衣の縁が赤熱) |
| 横顔で空を見上げる少女 | 横顔で空を見上げるヒロイン(汗が星明かりに光る) |

## 制作の分け方(案)
- カットA(2〜6秒): 作成済みの開始画像 → 雲海へ下降し、雲に突っ込んで白くかすむまで
- カットB(6〜10.75秒): 新しい開始画像(ヒロインの真後ろ・やや下からの夜空)→ 上へティルトし、オーロラのような尾と唐揚げを追い、最後は引きでヒロインが右下に小さく横顔
  - 必要なら終了画像(引きの構図)も作り、開始と終了の両方を指定して動きを固定する

## 決定事項と生成記録
- ヒロインの衣装: 制服(黄茶色のノースリーブのニットベスト)
- カットB の終了画像のみ作成(gpt_image_2 / medium / 2k / 16:9、2 クレジット、Element debu-heroine): `217656eb-7234-4462-8219-9ad51787592f`

## 動画(冒頭 約9秒を1本で)— 案(未生成)
- start_image: 雲海と唐揚げの隕石 `aa3bc47a-bc39-4346-8fa4-ce7fe89a2ad5`
- end_image: 星空・オーロラ・横顔のヒロイン `217656eb-7234-4462-8219-9ad51787592f`
- 9秒、16:9。コスト(プレフライト): Cinema Studio Video 2 標準 13.5 / pro 18、Seedance 2.5 720p 63

### プロンプト(英語)
```
Cinematic live-action opening of a romantic fantasy film trailer, 16:9, 9 seconds, one continuous camera move from the first frame to the last frame (the end image), realistic and photographic, calm natural colors, no text.
0-3.5s: Continue from the first frame: high above an endless sea of clouds at dusk, the tiny sun on the horizon with dotted vertical and horizontal lens flares and a faint halo ring. The thin sharp white meteor trail with the small karaage fried-chicken meteor at its tip keeps falling almost straight down toward the horizon. The camera slowly tilts down and descends toward the clouds; the horizon rises in the frame, the foreground clouds grow larger and darker, and a chain of soft orange lens-flare orbs drifts toward the lower right.
3.5-4.2s: The camera plunges straight into a huge cloud mass; the whole frame is engulfed in white-gray mist, then briefly a dark blue blur as it breaks through below the clouds.
4.2-5.0s: Night on the ground. Low angle directly behind the heroine (very large plus-size young woman, long black ponytail with a red hair tie, white blouse and mustard-yellow-brown sleeveless knit vest): the back of her head and her round broad shoulders fill the lower center of the frame. Above her, a starry sky with scattered small clouds and a faint violet-pink Milky Way glow in the upper left.
5.0-6.8s: The camera slowly tilts upward; her head sinks out of the bottom of the frame. From the upper right a brilliant cyan comet band enters the sky, and below it the thin white line with the red-hot glowing karaage at its tip.
6.8-9.0s: The camera settles into a wide low-angle shot: the huge cyan-to-white band arcs across the sky with magenta, pink and violet fringes like a single ribbon of aurora; the heroine stands small in the lower right corner in profile, gazing up in wonder, her ponytail fluttering in the breeze. End exactly on the final frame.
Audio: quiet, mysterious solo piano and high-altitude wind; a soft whoosh as the camera passes through the clouds; calm night ambience. No dialogue.
```
- 生成(Cinema Studio Video 2 / pro / 9秒 / 16:9 / ジャンル spectacle / 音あり / 18 クレジット): `903ae1fe-1a8e-40bc-8c59-844ea7542f7e`
