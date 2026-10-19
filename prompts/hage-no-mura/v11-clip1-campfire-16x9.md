# v11 クリップ1:焚き火(横型 16:9 版)

映画の予告編のような横型に変更。参考動画も 16:9 なので、構図はより参考動画に近づける。
以降のシーンもすべて 16:9 で制作する。

## 開始画像(16:9)

設定: `gpt_image_2` / high / 2k / 16:9。Elements: hage-mouri `ca97db38-…`、hage-hinata `ba9890dc-…`。コスト 6.5 クレジット

```
Cinematic 16:9 widescreen still from a serious Japanese romance reality-show documentary, film trailer look. Two people SITTING SIDE BY SIDE on a rustic wooden bench with a wooden pallet backrest, both seated facing the same direction (toward a campfire in front of them), shoulders almost touching. Tight two-shot at chest height, framed slightly from the front-right. LEFT-CENTER of frame: <<<hage-mouri>>>, the stocky middle-aged Japanese man with a thin black comb-over and visible scalp, red-and-navy checked flannel shirt, his upper body leaning slightly toward her; face in three-quarter view toward camera, eyes red and watery with a tear on his cheek, looking slightly down, lips parted as he speaks softly with emotion. RIGHT foreground, slightly out of focus and partly cut off by the frame edge: <<<hage-hinata>>>, the young Japanese woman with a dark-brown high ponytail and yellow knit cardigan, body and shoulders facing forward, ONLY her head turned toward him, so we see her profile, ear and ponytail as she listens intently. Their faces are close. Outdoors at dusk on an overcast day, soft cool natural light with a warm orange glow from the campfire lighting their faces from below. Background on the left: a shelf of blue glass bottles as large soft bokeh. Telephoto lens, very shallow depth of field, focus on his face, anamorphic cinematic feel. Muted low-saturation documentary color grade, natural skin texture, no beauty filter. Only these two people, no text, no logos, no watermark.
```

## 動画(16:9・18秒)

設定: `seedance_2_5` / omni_reference / 18秒 / 16:9 / 720p / 音声あり。start_image = 上の開始画像。image_references = 毛利・ひなたのシート。コスト 126 クレジット

プロンプトは 9:16 版(`v11-clip1-campfire.md`)の冒頭を次のように差し替える:

```
Cinematic Japanese romance reality-show documentary, 16:9 widescreen film-trailer look, 18 seconds.
```

(以降のショット指示・セリフ・音声は 9:16 版と同じ)

## 生成記録

- 開始画像 16:9(毛利が最初から泣いている): job_id `fd3f385e-2cc7-4a71-a603-a99570800bab`(2026-10-19)
