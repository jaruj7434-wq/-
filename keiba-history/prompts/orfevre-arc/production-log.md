# オルフェーヴル 凱旋門賞 (名前を最後に明かす) — 制作ログ

- 台本: scripts/orfevre-arc/script_v1.md (v5) / 事実確認: docs/research/orfevre-arc.md
- ナレーション (2026-11-09): ElevenLabs v4、Voice Element 谷上-2 (c4548a1f)、stability 0.95 / similarity 1.0、1行1ファイル
  - 読み間違い防止のため数字・難読語はかなで入力 (にせんじゅうに年、ひゃくメートル、にちゃく、はちばしんさ、あんじょう、いけぞえけんいち、さんかん、たづな、ありまきねん、ひんば、きんいろ)
  - 13〜18 は 429 (混雑) で1度失敗 → 再送信
  - job: 01 827d9623 / 02 ac500f8c / 03 6fb10e35 / 04 e30e29da / 05 553dd04f / 06 467af4c7 / 07 9410ebc0 / 08 4c9a807b / 09 a1582e79 / 10 0d59f9fa / 11 b920ccdf / 12 e945ac5c / 13 e3dc49be / 14 4663c389 / 15 a48907e6 / 16 64c9253b / 17 19ce9813 / 18 8118de42
  - つなぎ: edit/orfevre-arc/narration.sh → assets/output/orfevre-arc/vo/narration_full.m4a (97.4秒、各行の前後の無音を削り、行間 0.5〜1.4秒、-16 LUFS)
