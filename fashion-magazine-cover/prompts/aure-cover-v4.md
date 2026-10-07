# AURE 表紙 v4 — パリ版(v3 #1)の文字崩れ修正(藤川らるむ)

元画像: v3 パリ版 job ebaf0b85-82ae-4f7e-ae7b-0f0fb9a873be を参照し、写真はそのまま・文字だけ組み直す。
モデル: gpt_image_2_5(文字描画・編集に強い)/ quality high / 2k / 3:4 / 2.75クレジット/枚

## 文字崩れ対策
- 文字数を減らす(8本 → 6本)。崩れやすい「小さい日本語の長文」はやめ、日本語は大きめの短いフレーズだけにする
- 小さい文字は英語の短いフレーズに置き換える
- 各テキストを一字一句指定し、それ以外の文字を入れない

## テキスト
| 文言 | デザイン |
|---|---|
| AURE | 中央上の大きなハイコントラスト・セリフ(既存のまま) |
| Soft & Effortless | 最大級の手書きスクリプト・チェリーレッド |
| 藤川らるむ | 大きめの太明朝・白 |
| トープ × アイスブルー | 中サイズのゴシック。「トープ」はトープ色、「アイスブルー」は淡い水色 |
| その抜け感、反則級。 | 太ゴシック・白、チェリーレッドの下線 |
| COLLARBONE · SILVER · SOFT KNIT | 小さめの字間広めサンセリフ大文字 |
| Effortlessly Beautiful | 細い斜体セリフ |

## プロンプト
Keep the photograph exactly the same: same woman, face, hair, makeup, outfit, pose, Paris blue-hour background and lighting. Remove all existing text except the "AURE" masthead, then re-typeset the cover with ONLY the following texts, spelled exactly, crisp and perfectly legible, no other letters anywhere:
1. "AURE" — large elegant high-contrast serif masthead centered at the top, partially behind her head
2. "Soft & Effortless" — largest cover line, flowing handwritten script, cherry red
3. "藤川らるむ" — large bold Japanese mincho, white
4. "トープ × アイスブルー" — medium Japanese gothic; "トープ" in taupe, "アイスブルー" in pale ice blue
5. "その抜け感、反則級。" — bold Japanese gothic, white, with a cherry-red underline
6. "COLLARBONE · SILVER · SOFT KNIT" — small wide-tracked sans-serif caps
7. "Effortlessly Beautiful" — thin italic serif
Strong size contrast, generous spacing, text never overlapping her face, clean luxurious editorial layout.

## 生成記録(count 2、計5.5クレジット)
- 案1: 完成 — job 1f3fd772-7302-4c5f-8f4e-29d517acb1e4
- 案2: 完成 — job 0d3633dc-b49a-4b45-aa2d-76e62c2d560c
