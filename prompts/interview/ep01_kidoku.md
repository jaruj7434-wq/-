# 第1話「既読スルー」台本案 v3(人生2周目バブ君)

- 尺: 約25秒 / 9:16 / 街頭インタビュー風の手持ちカメラ、夕方の駅前
- ゲスト: 20代OL(3D Pixar風・架空)。スマホを握りしめている

| # | 秒 | 画 | セリフ | 声 |
|---|---|---|---|---|
| 1 | 0–3 | バブがマイクを構えて寄り | バブ君「おねえちゃん、なにか悩んでまちゅか?」 | バブ |
| 2 | 3–8 | 2ショット。OLがスマホ画面を見つめる | OL「彼氏に既読スルーされて…もう3日なんです」 | OL |
| 3 | 8–11 | バブ寄り。首をかしげる | バブ「ほうほう。それで、ちみはどうしたいでちゅか?」 | バブ |
| 4 | 11–15 | OL寄り。無理に笑う | OL「…忙しいだけだと思うんです。きっと」 | OL |
| 5 | 15–20 | バブがおしゃぶりを外し、真顔で寄り。BGMが止まる | バブ「おねえちゃん。…返事がないのも、返事でちゅよ」 | バブ |
| 6 | 20–23 | OLが固まる。手からスマホが少し下がる | (無音) | — |
| 7 | 23–25 | バブがおしゃぶりを戻してカメラ目線 | バブ「…ばぶ。」 | バブ |

## 声
- バブ: ElevenLabs v4 / Pixie(preset, stability 0.4)、「[幼い子どものように、かわいく]」+ピッチ1.3倍処理。
  核心ツッコミ(#5)のみ「[静かに、落ち着いて]」にして、かわいさの中に重みを出す
- OL: ElevenLabs の20代女性ボイス(自然・少し弱々しい)。候補は試聴して選定

## 試作メモ(2026-11-11)
- OL声候補: Hana `c25f78a0-714e-42af-8da3-a399cef94968`(推奨) / Naomi / Luna。elevenlabs_v4、冒頭に「[ため息まじりに、弱々しく]」
- 口パク方式の比較(最初の約10秒)
  - A: intone 480p(character_images=バブ君+OL、audio_references=バブ加工音声+OL音声)→ 30cr。2ショット+OL寄りの2カットを自動構成
  - B: seedance_2_0_mini 720p(start_image+audio_references、generate_audio false)4s+5s → 9cr。音声は後から ffmpeg で合成

## 本番(v1 完成 2026-11-11)— 27.6秒 / 720x1280
| カット | 内容 | 方式 | job_id |
|---|---|---|---|
| S1 | 2ショット→OL寄り(L1 バブ質問 / L2 OL悩み) | intone 480p(試作Aを流用) | 9573f419-01ba-4320-8011-5a8cee5a6160 |
| S2 | バブ寄り L3「ほうほう。それで、ちみは…」 | seedance_2_0_mini 4s | 09d46f44-409d-4b71-ae16-6c7af4c217a5 |
| S3 | OL寄り L4「…忙しいだけだと思うんです。きっと」 | seedance_2_0_mini 4s(start=intoneのフレーム) | 3aac909e-b592-4eb7-bfa1-5bd742703e50 |
| S4 | バブ真顔 L5「おねえちゃん。…返事がないのも、返事でちゅよ」 | seedance_2_0_mini 5s(start=真顔画像 706a9874) | ba6c957a-a6af-4b9b-aa36-854c76b3cfcd |
| S5 | OL固まる(無音、1.0〜4.0s使用) | seedance_2_0_mini 4s | 45f1c5e2-f4e8-4c63-8f7a-c271b516cdd4 |
| S6 | バブ カメラ目線 L7「…ばぶ。」(1.0〜4.0s使用) | seedance_2_0_mini 4s(0.6秒の音声参照は失敗→音声参照なしで再生成) | f38de7de-ed91-419d-a25c-d92b3f74985d |

- 音声: L3 47509177 / L4 4aa787a2 / L5 f9124e30(1回目は演技指示の「でも」が読まれたため撮り直し)/ L7 cd83445e
- 注意: elevenlabs の [演技指示] に「でも」等の普通の語を入れると読み上げられることがある
- 編集: サンドボックス /home/user/babu-interview/ep01/edit/build.sh(ffmpeg で連結・音声ミックス・Noto Sans JP 字幕、loudnorm -14 LUFS)
- 完成 media_id: 9233eb54-47c2-4906-8de7-e25a0fc54647

## v2(立ち姿・音声は動画生成時にネイティブ生成)2026-11-11 — 27.4秒
すべて seedance_2_0_mini 720p / generate_audio:true。声質はプロンプトで固定文言を使う:
- バブ君: "in a very high-pitched, cute, babyish little-boy voice with baby talk"
- OL: "in a soft, sad, young adult female voice"
| カット | 使用範囲 | job_id |
|---|---|---|
| S1 2ショット L1+L2(8s) | 0–8.0 | 6b8c33a7-804a-404b-8f22-45f1b38ca363 |
| S2 バブ立ち寄り L3(4s) | 0–4.0 | 081dc237-fd46-4ea6-94d1-2b31f7f81403 |
| S3 OL寄り L4(4s) | 0–4.0 | 723dff0e-5ce3-4fc0-bcc8-baba7aa95acd |
| S4 バブ真顔 L5(5s) | 0–5.0 | 129d763b-89f7-4587-afa3-04bc257755dd |
| S5 OL固まる(無言・風音)(4s) | 0.8–4.0 | 7872be3e-a1ca-4c85-abc1-00ad3b5efa1d |
| S6 バブ「…ばぶ。」(4s) | 0.8–4.0 | ee12ef7a-2188-433b-a245-26d9f2beafc2 |
- 編集: サンドボックス /home/user/babu-interview/ep01/native/build2.py + cfg.json(各カットの音声をそのまま連結、字幕、loudnorm)
- 完成 media_id: 1023d962-80e6-4b46-9f31-c71b5bd11f2e
