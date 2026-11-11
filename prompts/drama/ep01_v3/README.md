# 第1話『プリンは、ひとつだけ』(v3)制作記録

- 完成動画 media_id:0a1a40d9-a6ef-4847-9979-872fdbabf321(60.0秒、9:16)
- 方式:声は事前に作らず、Seedance のプロンプトで「cute high-pitched baby voice says '...'」と指示(ネイティブ音声をそのまま使用)。実況なし
- 編集:サンドボックス /home/user/babu-drama/ep01v3/edit.py(カット区間+赤ちゃん語の小さな字幕+タイトル/つづく、BGMは ep01 の共通BGMを音量0.11で)

## プロンプトの共通部分(リアルな動きと表情)
"3D Pixar-style animated feature film shot, vertical. Realistic natural toddler movement with real weight and wobbly balance, highly expressive believable facial acting anyone understands instantly. ... Fully clothed, family-friendly, nobody gets hurt. No music, no narration, no text."

## 学び
- 3人を並べると、人数が増える(6人・9人になる)ことがある → 先に gpt_image_2_6 で「EXACTLY THREE」の開始画像を作り、start_image で動画化すると安定
- 移動の向きは「TOWARD the camera and the pudding」のように、カメラと目的物の位置関係まで書く
- 先生の手のカット(c02)には余計な大人の声が入ったのでミュートした

## ジョブID
| カット | job_id |
|---|---|
| c01 空中で3人が手を伸ばす(冒頭+見せ場) | f5ac7e37-c303-4a7e-ab40-b2d2e88a1025 |
| c02 先生がプリンを置く | b1360df1-da03-4440-a492-faaa5df2e21f |
| c03 3人がのぞく(開始画像 b5b71774-53a5-4231-86e5-bcf23c8ea1ff) | 64ca4373-0cdf-42e5-a850-5ff6ccf69ce1 |
| c04 王子 高速ハイハイ | 6fa80d20-33f9-4c17-bb15-64d7b5a575cb |
| c05 先輩 よだれで王子が滑る | 8b616ed7-cd56-4efb-b264-506be169b585 |
| c06 姫 おしゃぶり投げ縄 | ceb91481-9b0f-42a8-a7e2-77af55ff3772 |
| c08 ねんね 寝たまま横取り | 5dddcfcd-3afa-47f4-a77e-f8396f454f5b |
| c09 プリンが消えた「あえ?」 | 8ffb044b-54b7-4920-9188-1fed3b87a2a7 |
| c10 ねんね「むにゃ、おいち」 | 1f14a40d-8c5b-4412-9bd0-7223d38f522b |
| c11 3人大泣き | d1e9011a-61bb-465e-bee0-f404d20a4743 |
| c12 先生がプリン3個、笑顔 | 57fc9374-6657-4b3b-b55e-1d8bbc00907b |
| c13 ねんね ウインク | b254592f-65c6-41f1-8625-31a6fe823296 |
| 不採用(人数増加/逆向き) | 7086acb1-44cf-4aa7-9a28-319baa3e04ac, d304ab0d-2758-4169-8423-f3fb8bf95a3c, 55b21332-f8c0-4b1c-9c35-647e0c62903a |
