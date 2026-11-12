# 0.001秒の世界 — plan.md

一瞬で終わる現象を、超スロー・断面図・物理シミュレーションで「中で何が起きているか」まで見せる科学ショートシリーズ。

- 形式: 縦型 9:16 / 30〜50秒（Reels・TikTok・Shorts）
- 分担: Claude Code 8割（台本・事実確認・シミュレーション・テロップ・編集）／Higgsfield 2割（冒頭のリアルなスロー映像 1〜2カット）
- ルール: Higgsfield の生成前に必ず許可を取る（CLAUDE.md）

## 動画の型
1. フック（0〜3秒）: リアルなスロー映像 + 「この0.001秒に何が起きている？」
2. 分解: 断面図・粒子シミュレーションで仕組み
3. 数字: 温度・圧力・時間を大きなテロップで
4. オチ: 意外な一言

---

## 第1話「ポップコーンが弾ける0.001秒」（決定）

### 仕組み（出典付き）

| # | 事実 | 出典 |
|---|---|---|
| 1 | 殻（果皮）が圧力容器の役割をし、中の水分が加熱で蒸気になって内圧が上がる | Hoseney et al. 1983, *J. Cereal Sci.* 1:43-52（CIMMYT 図書目録の要旨）[^hoseney] |
| 2 | 破裂は約177℃、そのときの内圧は約135 psi（≒9.2気圧） | 同上 |
| 3 | 臨界温度は約180℃。粒の大きさ・形によらない | Virot & Ponomarenko 2015, *J. R. Soc. Interface*（DOI 10.1098/rsif.2014.1247）[^virot] |
| 4 | 170℃では34%しか弾けず、180℃では96%が弾ける | 同上（IFLScience 報道）[^ifls] |
| 5 | 殻が割れてから「花」の形になるまで 90ミリ秒未満 | 同上（Phys.org/AFP 報道）[^phys] |
| 6 | 撮影は毎秒2,900コマ（1コマ ≒ 0.00034秒） | 同上（報道）[^abc] |
| 7 | 跳ねる力は蒸気の噴射（ロケット効果）ではない。噴き出たでんぷんの「脚」が床を押して跳ぶ | 同上 [^virot][^abc] |
| 8 | 跳ぶ高さは数mm〜数cm、跳躍のエネルギーは約20μJ、初期加速度は約200 m/s²（約20G） | 同上 [^virot] |
| 9 | 「ポン」という音は殻が割れる音ではなく、中の水蒸気が抜ける音。中の空洞が共鳴器になる | 同上 [^virot][^hal] |
| 10 | 最適な水分量は約13.5〜14%。少なすぎると膨らむ蒸気が足りず、多すぎると殻が弱くなって圧力が早く抜ける | Hoseney らを引用した二次資料 [^carolina] |

**自前の検算**: 水の飽和蒸気圧（Antoine式）で計算すると 177℃ → 9.18気圧 = 135 psi、180℃ → 9.8気圧。Hoseney の数字（#2）と一致するので、テロップは「約180℃・約10気圧」で出せる。

**要注意（まだ使わない数字）**
- 破裂圧を「135〜185 psi」とする資料もあり、値は資料によって幅がある → テロップは「約10気圧」に丸める
- 体積が何倍に膨らむか（よく「40倍」等と言われる）は一次資料を未確認 → 確認するまで使わない
- 0.001秒という単位: 殻が裂け始める瞬間はミリ秒の世界だが、「ちょうど0.001秒で割れる」という出典はない。タイトルはシリーズ名として使い、本文では「90ミリ秒未満」「1コマ0.00034秒」など出典のある数字を使う

### 台本案（約40秒）

| 秒 | 映像 | テロップ / ナレーション |
|---|---|---|
| 0〜3 | 【Higgsfield】フライパンの中で1粒が弾ける超スロー | この0.001秒に何が起きている？ |
| 3〜10 | 【シミュ】断面図。加熱で水分子が速くなり、内圧ゲージが上がる | 粒の中には水分が約14%。熱で蒸気になり、殻の中で逃げ場を失う |
| 10〜14 | 【シミュ】殻が赤くなり震える | 約180℃、内圧 約10気圧（タイヤの約4倍）※比較は要確認 |
| 14〜26 | 【シミュ】破裂の超スロー。蒸気が抜け、でんぷんが泡になって噴き出す | 殻が裂けてから花になるまで 0.09秒未満 |
| 26〜34 | 【シミュ】でんぷんの「脚」が床を蹴って跳ぶ | 跳ぶ瞬間の加速度 約20G |
| 34〜40 | 【Higgsfield or シミュ】弾けた粒がゆっくり舞う | オチ:「ポップコーンは蒸気で飛ぶんじゃない。自分の"脚"でジャンプしている」 |

オチ候補B:「"ポン"は殻が割れる音じゃない。中から蒸気が抜ける音」

### シミュレーション試作
- スクリプト: `scripts/science_0001/ep01_popcorn_sim.py`
- 出力: `assets/output/science_0001/ep01_popcorn_sim.mp4`（1080×1920 / 30fps / 18秒、git管理外）
- 内容: 加熱（温度・内圧ゲージ）→ 殻の限界 → 破裂の超スロー（ミリ秒表示）→ 脚で跳ぶ → オチのテロップ
- 物理: 温度は油温200℃への指数加熱（時定数45秒）、内圧は水の飽和蒸気圧。水分子の速さは温度で増える（見やすさのため誇張）。泡と跳躍は見せ方優先の演出で、定量的な流体計算ではない

### Higgsfield カット
- **生成済み**: カット1（冒頭フック）— Kling 3.0 pro / 9:16 / 5秒 / 音なし / 8.75クレジット（無制限枠はプラン上使えず、許可を得て通常クレジットで生成）
  - job: `6498280a-9160-4f28-8624-706ecb5e047b` → `assets/source/science_0001/ep01_hook_kling.mp4`
  - プロンプト: `Extreme macro, high-speed camera slow motion. A single yellow popcorn kernel on a dark hot frying pan bursts open, white starch foam erupts and the kernel leaps up blooming into popcorn. Black background, rim lighting, ultra realistic, no text.`

案（※カット2は未生成・実行前に許可を取る）
1. **冒頭フック**（3〜4秒, 9:16）: 黒背景、熱したフライパンの上の黄色い粒1つにマクロで寄った超スロー。殻が裂けて白いでんぷんが噴き出し、粒が跳ね上がる。高速度カメラ風
2. **ラスト**（任意, 3秒）: 弾けたポップコーンが空中でゆっくり回転しながら落ちる

### 仮編集
- スクリプト: `scripts/science_0001/ep01_edit.py --hook assets/source/science_0001/ep01_hook_kling.mp4`
- 出力: `assets/output/science_0001/ep01_rough_cut.mp4`（23秒 = フック5秒 + シミュ18秒）
- 効果音は numpy で合成（加熱のジュー音 → 破裂の「ポン」→ 蒸気のシュッ → オチのチャイム）。著作権フリー

### 次にやること
- [ ] シミュ試作の見た目を確認してもらい、修正点を反映
- [ ] 「タイヤの何倍」等の比較テロップの数字を確認
- [x] Higgsfield カット1 生成
- [x] 効果音入りの仮編集（23秒）
- [ ] 台本の「数字」パート（約180℃・約10気圧・90ミリ秒未満・約20G）を大テロップで足して 30〜40秒にする
- [ ] ナレーション（音声）を入れるか決める

[^hoseney]: https://knowledgecenter.cimmyt.org/bib/68087
[^virot]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4345489
[^ifls]: https://www.iflscience.com/why-does-popcorn-pop-27216
[^phys]: https://phys.org/news/2015-02-physics-food-secrets-popcorn.html
[^abc]: https://www.abc.net.au/science/archive/articles/2015/02/11/4177927.htm
[^hal]: https://hal-polytechnique.archives-ouvertes.fr/hal-01178414
[^carolina]: https://knowledge.carolina.com/discipline/physical-science/the-science-of-popcorn/

---

## v2: 説明パートも Higgsfield 実写風で再現（2026-11-12）

ユーザー指示で、説明パートをシミュレーションから Higgsfield の実写風カットに置き換えた。
4本とも Kling 3.0 pro / 9:16 / 5秒 / 音なし。通常クレジット 8.75 × 4 = 35（許可済み）。

| # | ファイル (`assets/source/science_0001/`) | job | 内容 | テロップ |
|---|---|---|---|---|
| フック | ep01_hook_kling.mp4 | 6498280a-9160-4f28-8624-706ecb5e047b | フライパンの1粒が弾ける | この0.001秒に何が起きている？ |
| ① | ep01_s1_cutaway.mp4 | 0f00c278-5d17-429a-aadd-7d16a89348ab | 断面: 中の水分が沸騰 | 水分 約14% / 熱で粒の中の水が蒸気に変わる |
| ② | ep01_s2_pressure.mp4 | 8b1a59bb-4531-4b31-84a9-819a32cde3bc | 殻が内圧で張りつめる | 約180℃・約10気圧 / 殻が圧力鍋のふたになり蒸気を閉じこめる |
| ③ | ep01_s3_rupture.mp4 | 785b52dc-e738-40fa-911b-aef5da1ab37b | 亀裂 → でんぷんが噴き出す・蒸気 | 0.09秒未満 / 殻が裂けて花の形になるまで |
| ④ | ep01_s4_leg.mp4 | e65e0a54-f968-407c-8726-8bf531a653cb | でんぷんの「脚」で床を押して跳ぶ | 約20G / でんぷんの「脚」が床を蹴って跳ぶ |
| オチ | ④の最終フレームを暗くして静止 | — | — | ポップコーンは蒸気で飛ぶんじゃない 自分の「脚」でジャンプする |

プロンプト
- ①: `Scientific cutaway macro: a single popcorn kernel sliced in half, showing translucent amber hull and dense white starch interior. Tiny water droplets inside the starch heat up and begin to boil into small steam bubbles, faint orange heat glow from below. Slow camera push-in, black background, ultra realistic, high-speed camera look, no text.`
- ②: `Extreme macro of a single yellow popcorn kernel on a dark hot frying pan, the glossy hull swells under internal pressure and trembles, surface tension visible, faint wisps of steam, glowing heat shimmer, tense moment right before bursting. Black background, rim lighting, ultra realistic, no text.`
- ③: `Ultra slow motion extreme macro: a crack splits open the hull of a popcorn kernel, a jet of steam escapes and white starch foam erupts out of the crack like expanding lava, turning puffy and white. High-speed phantom camera look, black background, rim lighting, ultra realistic, no text.`
- ④: `Ultra slow motion side view at pan level: white starch foam bursts out of the bottom of a popcorn kernel, forms a leg that presses down against the dark frying pan surface and pushes the kernel up, launching it into the air as it blooms into a popcorn flake. High-speed camera look, black background, rim lighting, ultra realistic, no text.`

編集: `PYTHONPATH=scripts/science_0001 python3 scripts/science_0001/ep01_edit_v2.py` → `assets/output/science_0001/ep01_v2.mp4`（27.5秒）

注意: AI生成の映像なので、断面の見た目は科学的に正確な再現ではなく「イメージ」。必要なら概要欄に「映像はAI生成のイメージです」と入れる。

## 仕上げ: ナレーション + BGM（2026-11-12）

- 声: ElevenLabs v4 Turbo / Julian（男性・落ち着き）`95429266-c0ac-4137-a209-63b8812b0f23`、各行 0.15クレジット
- BGM: ElevenLabs Music v2.5 / 30秒 / インスト、4.36クレジット
  - プロンプト: `Upbeat, optimistic, playful science-show background music, bright plucky synths, light ukulele and marimba, bouncy groove, 120 BPM, curious and cheerful, instrumental, no vocals`
- 合計 約5.3クレジット（許可済み）

| # | 開始 | ナレーション | job |
|---|---|---|---|
| 0 | 0.15s | この一瞬、粒の中で何が起きてる？ | 681ac3b2-14c2-448f-99fd-5f7c6960bebc |
| 1 | 4.15s | 中には、約十四パーセントの水分。熱で蒸気に変わります。 | 7b9c9b73-b238-4d14-8059-8c4ad75212c1 |
| 2 | 9.15s | 殻がフタになって、約百八十度、約十気圧。 | f9786c1b-e778-4400-810a-fe6aa443e6b1 |
| 3 | 14.15s | 限界を超えると殻が裂けて、でんぷんが泡に。 | 689b3621-9912-46e0-8aeb-c1ed862d4e3a |
| 4 | 19.15s | この白い脚で床を蹴って、ジャンプ！ | 425ca687-2378-42e4-a498-5617d3b04ff3 |
| 5 | 24.15s | ポップコーンは、自分の脚で跳んでいたんです。 | fd759442-2832-43c1-b98f-86a770aad9cd |
| BGM | 0s | — | 8f0b8aaf-5b00-44e7-99b7-4751d88a8e30 |

カットより長い行は atempo で必要な分だけ速める（#1 は約1.17倍）。音量: ナレーション 1.6 / 効果音 0.55 / BGM 0.16。
仕上げ: `ep01_edit_v2.py` → `ep01_mix.py` → `assets/output/science_0001/ep01_final.mp4`（28秒）

## v3: 図解強化版（矢印・グラフ・色文字・一時停止）

- 映像: `python3 scripts/science_0001/ep01_explainer.py` → `ep01_v3_video.mp4`（PILで1フレームずつ合成）
- 音: `python3 scripts/science_0001/ep01_mix_v3.py` → `ep01_v3.mp4`（50.3秒）
- フォント: Dela Gothic One（見出し・数字）/ M PLUS Rounded 1c ExtraBold（説明）。npm の Fontsource 分割ファイルを fontTools で結合し `~/.fonts` に置く
- 色のルール: 黄=強調・結論 / 青=水・蒸気 / 赤橙=熱・圧力・力 / 白=本文
- 新規の Higgsfield 生成なし（既存カットを流用）

| 秒 | 内容 | 図解 |
|---|---|---|
| 0–1.2 | フック再生 | 「ポップコーンが弾ける瞬間…」 |
| 1.2–3.4 | ⏸ 一時停止 | 粒を黄色の円で囲む＋「この一瞬、中で何が起きてる？」 |
| 3.4–5.7 | 再生 | 「4つのステップで分解してみよう」 |
| 5.7–10.7 | STEP1 断面 | 矢印ラベル「水分→水蒸気」「でんぷん」「かたい殻」 |
| 10.7–14.7 | ⏸ | ドーナツグラフ 14%「粒の重さの約14%が水」 |
| 14.7–19.7 | STEP2 殻 | 内側から押す赤い矢印×8、温度計 100→180℃ |
| 19.7–25.2 | ⏸ | 温度-圧力グラフ（飽和蒸気圧曲線）、180℃・約10気圧に印、1気圧の基準線 |
| 25.2–29.2 | STEP3 → ⏸ | 「亀裂」「水蒸気が噴き出す」「でんぷんが泡に」 |
| 29.2–33.8 | 再生 | ミリ秒タイマー 0→90ms（実際は0.09秒未満・映像は超スロー） |
| 33.8–36.1 | STEP4 再生 | — |
| 36.1–41.1 | ⏸ | 下向き矢印「脚が床を押す」／上向き「反動で跳ぶ」／「約20G（重力の約20倍）」 |
| 41.1–43.8 | 再生 | 「空中で花が開く！」 |
| 43.8–50.3 | まとめ | 4項目を順に表示 → 「ポップコーンは自分の『脚』で跳んでいた！」 |

ナレーションは既存6行をそのまま配置（一時停止中の説明部分は無言）。

## v4: ナレーション・効果音を追加（2026-11-12）

ナレーション 11行を追加生成（ElevenLabs v4 Turbo / Julian、約1.7クレジット）。ナレーションに合わせて一時停止を延ばし、図解の出るタイミングを台詞に同期。全体 約80秒。

| # | 位置 | セリフ | job |
|---|---|---|---|
| na0 | フック一時停止 | この一瞬、粒の中で何が起きてる？ | 681ac3b2 |
| na10 | フック再生 | 4つのステップで、分解してみよう。 | 39e05572-eaef-465c-982c-62f605052833 |
| na11 | STEP1 | ステップ1。粒の中の水分が、熱で水蒸気に変わります。 | db113a0b-057e-4110-b237-1c672c8ab802 |
| na12 | STEP1 停止 | 水分は、粒の重さの約十四パーセント。これが、膨らむ力のもとです。 | 9b74aa89-c487-455b-bf2d-53f258e69d1f |
| na13 | STEP2 | ステップ2。かたい殻がフタになって、蒸気を外に逃がしません。 | ea65ad3b-6d54-4103-9b59-12b6532c5f90 |
| na14 | STEP2 停止(グラフ) | 温度が上がるほど、中の圧力はぐんぐん上昇。約百八十度で、ふだんの空気の約十倍。ここで、殻が限界をむかえます。 | ac82bcfb-690c-410c-8f93-10b9b2658a5c |
| na15 | STEP3 停止 | ステップ3。ついに殻が裂けて、水蒸気が噴き出し、でんぷんが一気に白い泡にふくらみます。 | 072af456-b5dd-4e96-9f04-3cbd88ec4648 |
| na16 | STEP3 タイマー | ここまで、実際には0.09秒もかかりません。 | 090aaf9d-2a0e-49ea-ade6-fe3c613e7b13 |
| na17 | STEP4 | ステップ4。ポップコーンは、どうやって跳ぶのでしょう？ | f88f6a1d-826a-446a-9d4a-cf73cef03277 |
| na18 | STEP4 停止 | 答えは、この白い脚。でんぷんの脚が床を押して、その反動で跳び上がります。加速度は、なんと約二十ジー。 | a8583bcc-9994-45f0-8a38-babbde86c3e6 |
| na19 | 空中 | そして空中で、花が開きます。 | 4587685a-7be5-4d34-82d2-a86017f9a95b |
| na20 | まとめ | まとめると、水が蒸気になり、圧力で殻が裂け、でんぷんの脚でジャンプ。 | bb2bf878-263d-4223-8905-daefeb70ed45 |
| na5 | まとめ最後 | ポップコーンは、自分の脚で跳んでいたんです。 | fd759442 |

効果音（numpy 合成）: 一時停止「カチッ」/ STEP開始「ピロン」/ 矢印・ラベル「シュッ」/ 沸騰のプツプツ / ドーナツが増える音 / 圧力のドクンドクンと強まるジュー音 / グラフの上昇音と到達の「チーン」/ 破裂「ポン」・亀裂「パキッ」・蒸気「シュー」・泡「ポフッ」/ タイマーのチクタク / 脚「ドン」・跳ぶ「ビヨン」・20G「ドーン」/ 空中のキラキラ / まとめの項目音とチャイム

仕上げ: `ep01_explainer.py` → `ep01_mix_v3.py` → `assets/output/science_0001/ep01_v4.mp4`

## v5: 冒頭を「パーン → 巻き戻し → スロー → 一時停止」に変更

| 秒 | 内容 |
|---|---|
| 0–1.5 | いきなり弾ける（素材 1.05秒〜を1.3倍速）。0.15秒で白フラッシュ＋「パーン！」 |
| 1.5–2.05 | 巻き戻し（逆再生4.7倍速、走査線＋「◀◀ もう一度」） |
| 2.05–4.3 | スローモーション（0.4倍速、minterpolate でフレーム補間）「スローモーションで見てみると…」 |
| 4.3– | 一時停止「この一瞬、中で何が起きてる？」（以降は v4 と同じ） |

効果音: パーン（大）→ 巻き戻し「キュルキュル」→ スロー「ブォン」→ 一時停止「カチッ」。全体 約83秒。
