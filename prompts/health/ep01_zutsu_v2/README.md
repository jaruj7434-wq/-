# #01『頭痛』v2(リアル画像版・約66秒)

- ナレーション:text2speech_v2(elevenlabs)+ Hana、セクション別6本。無音を0.28秒に詰め、1.15倍速
  - job: b60d2d08 / aa42d66b / 4dca5e21 / 4eaa5ef9 / 0a943098 / d6b63c78
- 静止画:gpt_image_2_6(medium・1k・9:16)
  - 頭部 2f2f40e2 / 首肩 0055a2fa / 脳血管 6e5dfdd6 / 頭痛薬 7de4d661 / 危険サイン e164c2f6 / エンド 55c2a558
- 動画クリップ:seedance_2_0 fast 480p 5秒(冒頭 8a8eb3e9、片頭痛 75c93860)
- 合成:`index.html`(静止画・クリップのフレーム+色調・粒子・テロップ)を `render2.js` で30fps書き出し
- `cues.py`:各ナレーションの長さとモーラ数から、テロップの出るタイミングを計算 → `cues.json`
- 注意:Eleven v4(elevenlabs_v4)と Nano Banana は 2026-11-16 時点で生成失敗が続いた
