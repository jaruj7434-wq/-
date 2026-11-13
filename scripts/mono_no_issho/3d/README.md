# モノの一生 — 3Dショット（Blender / bpy）

Higgsfield の代わりに、Blender を Python モジュールとして使い、コードからリアル系の3Dカットを作る。

## 準備
```bash
pip install bpy==5.3.0   # Python 3.13 用ホイール（約430MB）。ffmpeg も使う
python3 scripts/mono_no_issho/3d/coin_textures.py   # 1円玉風の表裏ハイトマップ
```

## ショット
| スクリプト | 台本カット | 内容 |
|---|---|---|
| `shot_melt.py` | 1-3 / 5-3（H02・H14） | 1円玉がるつぼの溶けたアルミに落ち、赤熱して沈む |

```bash
python3 scripts/mono_no_issho/3d/shot_melt.py --still 60 --samples 32 --res 960x540   # 1枚確認
python3 scripts/mono_no_issho/3d/shot_melt.py --samples 64 --res 1920x1080            # 本番
ffmpeg -framerate 24 -i assets/output/mono_no_issho/ep01/shot_melt/f_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 shot_melt.mp4
```
出力先 `assets/output/` は git 管理外。

## レンダリング時間の目安（CPU 4コア、GPUなし）
- 960x540・32サンプル：1フレーム 約25秒（5秒=120フレームで約50分）
- 1920x1080・64サンプル：1フレーム 約3〜4分の見込み（5秒で6〜8時間）

## 第2話（傘）
- 話数の切替: ショットの `__main__` で `C.EPISODE = "ep02"` を設定すると `assets/output/mono_no_issho/ep02/3d/<name>/` に出力
  （環境変数 `EP` でも可。既定 ep01）。`render_queue.sh` はショット内の `C.EPISODE = "..."` 行を読んで出力先を合わせる。
- 傘の小道具: `umbrella.py` の `umbrella.make(name, location, rotation_deg, state="closed"|"open", kind="vinyl"|"cloth", color, tag)`。
  子メッシュ `<name>_Canopy / _Frame / _Handle (/ _Tag)` に分かれる（`umbrella.parts(root)`）。

| スクリプト | 台本カット | 内容 |
|---|---|---|
| `shots/k02_store_stand.py` | 2-2 | 雨の夜の店先、傘立てにぎっしりのビニール傘（ゆっくり寄る） |
| `shots/k06_umbrella_explode.py` | 5-2 | 傘の分解図（生地・骨・持ち手が離れて回る。左側は文字用の余白） |
| `shots/k08_last_umbrella.py` | 6-1 | 晴れた日、傘立てに一本だけ残ったビニール傘（木漏れ日・横移動） |

```bash
SAMPLES=32 scripts/mono_no_issho/3d/render_queue.sh k02_store_stand k06_umbrella_explode k08_last_umbrella
```
ビニールは半透明(BLENDED)で 8 サンプルだと粒状ノイズが出やすい。本番は `--samples 32` 以上推奨。

## 第3話（ペットボトル）
- 出力先は `assets/output/mono_no_issho/ep03/3d/<name>/`（各ショットで `C.EPISODE = "ep03"`）。
- P01〜P04 の小道具は `shots/pet_parts.py`：ボトル/プリフォーム（同じ頂点構成の回転体なのでシェイプキーで膨らむ）、
  透明PET（BLENDED のフレネル・アルファ。屈折なしで軽い）、架空ラベル（文字なし）、ベール（ボロノイ模様＋つぶれたボトルの共有メッシュ）、
  ロゴなし自販機・回収ボックス・コンベア。
- 透明素材は各ショット数個まで。透明(BLENDED)は深度を書かないので、DOF をかけると背景の深度でぼける（P03 は DOF なし）。

| スクリプト | 台本カット | 内容 | 960x540・8サンプル |
|---|---|---|---|
| `shots/p01_recycle_box.py` | 1-1 | 自販機横の回収ボックスに、透明ボトルが上から落ちて入る（ゆっくり寄る） | 約25秒/フレーム |
| `shots/p02_blow_mold.py` | 2-1 | 金型の断面図。温まったプリフォームが延伸ロッドで伸び、空気でボトルにふくらむ | 約20〜30秒/フレーム |
| `shots/p03_cap_label.py` | 4-1 | 食卓のボトル。キャップが回って外れて浮き、ラベルがほどけて飛び、透明ボトルだけ残る | 約22秒/フレーム |
| `shots/p04_bale_conveyor.py` | 5-1 | リサイクル工場。針金でしばったベールがコンベアで流れる（奥にベールの山） | 約42秒/フレーム |

```bash
SAMPLES=16 scripts/mono_no_issho/3d/render_queue.sh p01_recycle_box p02_blow_mold p03_cap_label p04_bale_conveyor
```

P05〜P08 の補助は `shots/pet_parts2.py`：フレーク/ペレットのメッシュ（光沢＋Translucent の不透明マテリアル、屈折なし）、
`bake_keys`（数百個の粒を毎フレーム位置キー。着地したら沈めて口へ戻し使い回す）、`growing_pile`（点群＋ジオメトリノードで
小粒を数千個インスタンスし、円錐の山が育つ。表面付近の粒だけ表示）、新品ボトル（中身の水・無地ラベル・キャップ）、卵パック、たたんだTシャツ、
下から光る境目で現れるディゾルブ `add_reveal`。

| スクリプト | 台本カット | 内容 | 960x540・8サンプル |
|---|---|---|---|
| `shots/p05_flakes.py` | P05 | 工場のホッパーの口から透明・水色のフレークがひらひら落ち、トレーの山が育つ | 約23秒/フレーム |
| `shots/p06_pellets.py` | P06 | 斜めのシュートから乳白のペレットが帯になって流れ落ち、容器の中で山になる | 約20〜26秒/フレーム |
| `shots/p07_reborn.py` | P07 | スタジオ。ペレットの山から粒が舞い上がり、ボトル・卵パック・Tシャツが順に形になって並ぶ（分解図風） | 約35〜42秒/フレーム |
| `shots/p08_new_bottles.py` | P08（ラスト） | 店の棚に並ぶ新しい透明ボトル（文字なし）。斜めからゆっくりドリー。屈折は最前列27本だけ | 約42秒/フレーム |

```bash
SAMPLES=16 scripts/mono_no_issho/3d/render_queue.sh p05_flakes p06_pellets p07_reborn p08_new_bottles
```

## 第4話（服）
- 出力先は `assets/output/mono_no_issho/ep04/3d/<name>/`（各ショットで `C.EPISODE = "ep04"`）。
- C05〜C07 の補助は `shots/fuku_parts2.py`：古着ベール（押しつぶした布の層のボロノイ模様＋PPバンド。形は `pet_parts.bale` を流用）、
  無地の海上コンテナ（波板・観音扉。ロゴ・文字なし）、ウエス（格子メッシュ＋決定的なしわ、無地/ボーダー/ギンガム/水玉の綿）、
  歯車メッシュ、油汚れ→ふくと光る金属（`"Wipe"` 値ノードをキー。映り込みは `fake_env`）、
  反毛の繊維（くるっと曲がった細い管）と `fluff_object`（点ごとに「服→綿雲→板」の3位置と区間を属性に持ち、GN＋シーン時間で補間。キー・物理なし）。
- C08 は `fuku_parts.build_closet`（C01 と共用）をそのまま組み、値札のシャツだけ取り除いて空のハンガーを `swing` で揺らす。

| スクリプト | 台本カット | 内容 | 960x540・8サンプル |
|---|---|---|---|
| `shots/c05_container.py` | 5-2 | 港の岸壁。扉を開けた無地のコンテナの奥にベールの壁、斜めのコンベアを上ってきたベールが空きにすべり込む（ゆっくり寄る） | 約25秒/フレーム |
| `shots/c06_wiping_rag.py` | 5-3 | 作業台。ウエスの山から1枚が浮き、油で黒い歯車の上をなでると、通った所から鋼が光る（手なし） | 約11秒/フレーム |
| `shots/c07_hanmo.py` | 5-4 | スタジオ。宙のTシャツが上からほどけて繊維9000本の綿雲になり、渦を巻いて台へ降り、フェルトの板に固まる | 約35〜40秒/フレーム（繊維が多い中盤） |
| `shots/c08_empty_hanger.py` | 7-1（ラスト） | C01 と同じクローゼット。値札のシャツがあった所で空のハンガーが揺れ、カメラはゆっくり引く | 約25秒/フレーム |

```bash
EP=ep04 scripts/mono_no_issho/3d/render_queue.sh c05_container c06_wiping_rag c07_hanmo c08_empty_hanger
```

## 第4話（服）
- 出力先は `assets/output/mono_no_issho/ep04/3d/<name>/`（各ショットで `C.EPISODE = "ep04"`）。
- C01〜C04 の部品は `shots/fuku_parts.py`：布マテリアル `mat_cloth`（無地／ストライプ／ギンガム／ニットのうね）、
  吊るした服 `garment`（シャツ・コート・Tシャツ・ニット。身頃と袖の板をボクセルリメッシュで一体化し、縦じわは頂点で足す。物理なし）、
  ハンガー `hanger`、値札 `price_tag`（無地の紙＋糸。文字なし）、丸めた服 `cloth_wad`、
  クローゼット一式 `build_closet(layout=...)`（扉を開けたワードローブ・パイプの服・棚のたたんだニット・下の収納ボックス・部屋）と
  照明 `closet_lights`、ハンガーの減衰振動 `swing`。C01 と C08 は同じ `build_closet()` のセット。
- 透明素材は C03 の袋1つだけ（BLENDED、透過影なし）。C03 は金属がないので反射プローブも置かない。

| スクリプト | 台本カット | 内容 | 960x540・8サンプル |
|---|---|---|---|
| `shots/c01_closet.py` | C01 | 扉を開けたクローゼットへゆっくり寄る。手前に向いた淡いピンクのシャツに無地の値札 | 約24秒/フレーム |
| `shots/c02_fabric_cut.py` | C02 | 裁断台のギンガムの布。門型の自動裁断機がシャツの形をなぞり、切り抜きが起き上がって襟・ボタン・ポケットの付いたシャツになる（手なし） | 約18秒/フレーム |
| `shots/c03_garbage_bag.py` | C03（4-1） | ブロック塀の前のごみ集積所。ネットをかけた白い袋の横に、服の詰まった透明な袋が下りてきて落ち着く | 約45秒/フレーム |
| `shots/c04_sorting.py` | C04（5-1） | 選別工場。コンベアの服が押し出し板でシュートへ押され、青・緑・黄・橙のかごに落ちる（人なし） | 約24秒/フレーム |

（時間は別ショットの並列レンダリングと CPU を分け合った状態での実測。単独ならもう少し速い）

```bash
SAMPLES=16 scripts/mono_no_issho/3d/render_queue.sh c01_closet c02_fabric_cut c03_garbage_bag c04_sorting
```
