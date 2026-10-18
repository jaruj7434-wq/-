# 焚き火シーン(一本もの動画)プロンプト

参考動画の焚き火シーン(0:00–0:24)のカット割り・尺を再現し、人物を毛利とひなたに置き換えたもの。

## 推奨設定

| 項目 | 値 |
|---|---|
| モデル | Seedance 2.5(`seedance_2_5`, mode: `omni_reference`) |
| 尺 | 24秒 |
| 比率 | 9:16 |
| 解像度 | 480p(試作)→ 良ければ 1080p |
| 音声 | あり(generate_audio: true) |
| 参照 | start_image = 開始画像 `fa5c07a2-b5af-4273-b3ed-330867688c05` / image_references = 毛利のシート `3ed19639-06bc-4c7a-8e72-7e1a18b0f025`、ひなたのシート `bec1f6ea-2269-4d84-ba6c-a98b4d97e398` |
| コスト目安 | 480p で 72 クレジット(3/秒) |

## プロンプト(英語)

```
A serious, emotional Japanese romance reality-show documentary scene, vertical 9:16, 24 seconds, multi-shot edit with hard cuts. Muted low-saturation documentary color grade, telephoto lens, very shallow depth of field, slightly handheld static camera, natural skin texture, realistic acting, no comedic tone, no on-screen text, no subtitles, no logos.

Characters (keep faces, hair and outfits exactly as in the reference images, the first frame continues from the start image):
- MOURI: stocky middle-aged Japanese man with a thin black comb-over and visible scalp, red-and-navy checked flannel shirt.
- HINATA: young Japanese woman with a dark-brown high ponytail and yellow knit cardigan.
Only these two people appear. No other people.

Setting: outdoors at dusk on an overcast day. They sit side by side on a rustic wooden bench with a wooden pallet backrest, a brick fire pit with a small campfire in front of them. Soft cool natural light with a warm orange glow from the fire lighting their faces from below. Behind them, a shelf of blue glass bottles as large soft bokeh.

Shot 1 (0-5s): Tight two-shot from the front. MOURI on the left, his body leaning slightly toward HINATA, eyes red and watery, looking down, speaking softly with a trembling voice. HINATA in the right foreground, out of focus, body facing forward, only her head turned toward him, listening. MOURI says in Japanese: 「何をしても、何もしなくても…髪は、抜ける」

Shot 2 (5-7s): Close-up of HINATA in three-quarter profile, body facing forward, head turned toward him, listening silently with a gentle, empathetic expression. Only soft sad piano.

Shot 3 (7-10s): Same tight two-shot as shot 1. MOURI lowers his eyes and a single tear rolls down his cheek. MOURI says in Japanese: 「だから…残ってる髪と、毎日を楽しく過ごしたいんです」

Shot 4 (10-12s): Close-up of HINATA over MOURI's shoulder (his comb-over and shoulder blurred in the left foreground). She turns to him and speaks gently in Japanese: 「ハゲるって…」

Shot 5 (12-14s): Medium-wide shot from in front of the fire pit: both sitting side by side on the bench holding hands, smoke rising from the campfire across the lens, small flames in the foreground, out-of-focus green leaves in the left foreground. HINATA's voice continues in Japanese: 「…勲章だよ」

Shot 6 (14-20s): Close two-shot seen through drifting purple-tinted campfire smoke. HINATA leans her face close to MOURI and says in Japanese: 「ハゲるってことは…それだけ長く、悩んで生きてきたってことだから」. MOURI, holding back tears, nods and answers in a choked voice in Japanese: 「…うん。そうだね」

Shot 7 (20-21s): Medium-wide shot again, the two sitting close together on the bench in the smoke, the fire flickering in the foreground. No dialogue.

Shot 8 (21-24s): Extreme close-up of glowing red-orange campfire embers and charred wood, small sparks rising. Sound of crackling fire.

Audio: quiet, melancholic solo piano throughout, very soft; crackling campfire ambience; intimate, soft-spoken Japanese dialogue only as written above.
```

## メモ

- 1回の生成で8カットを指示しているため、カットの切り替えや秒数が指示どおりにならない可能性がある。崩れた場合は、ショット1–3、4–7、8 の3本に分けて生成し、編集でつなぐ
- start_image を使うと、1コマ目が開始画像と同じ構図になる
