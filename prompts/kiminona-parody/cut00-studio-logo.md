# カット0: 冒頭の配給会社ロゴ(パロディ)

- 元ネタ: 実在する配給会社の、放射状の光+円の紋章+金色の社名ロゴ。実在ロゴは使わず、架空の「デブ株式会社」にする。
- 紋章: 白い円の中に「デ」「ブ」を縦に並べる。社名は金色の「デブ株式会社」、英字は「DEBU CO., LTD.」(セリフ体)。
- 背景: gpt_image_2 / medium / 16:9 / 1クレジット、job `6923edf7-b292-4965-8389-b0e6d312141c`(文字なしの放射状の光)
  - プロンプト: Cinematic film studio opening background: deep dark navy-black space, an explosive radial burst of countless thin colorful light streaks shooting outward from the exact center like hyperspace warp speed, streak colors teal, cyan, emerald green, yellow, orange, magenta, pink and white, bright soft white glow at the center, streaks longer and more blurred toward the edges, subtle film grain. Absolutely no text, no letters, no logo, no emblem, no circle shape.
- 合成: `tools/studio_logo.py bg_rays.png debu_logo.png`(1920x1080)。参考画像から換算して、円は中心 (960,410)・半径 182、社名は y=745、英字は y=828。光の中心が円の中心に来るよう背景をずらしている。
- 出力: `assets/output/kiminona/logo/debu_logo.png`
