# 第1話 編集パイプライン(サンドボックス /home/user/babu-drama/ep01/)

1. `build.py`:clips/ の素材を区間で切り出し、1080x1920・30fps に揃えて連結 → build/cut.mp4(無音)。タイムラインは build/timeline.json に出力
2. `finish.py`:テロップ(drawtext:Noto Sans JP / しっぽり明朝 / Dela Gothic One)、セリフ音声、効果音、BGM を重ねる → babu_ep01.mp4(63.2秒)
   - セリフは ElevenLabs のきれいな音源を使い、動画内の発話区間に合わせて atempo で伸縮(最大1.25倍)して配置する
   - loudnorm I=-14 LUFS
3. アップロード:media_upload → curl PUT → media_confirm(video)→ show_result(content_factory_video)

完成動画 media_id:d16431d0-1368-4ee4-b4da-8b57fdec9090

## 使用ジョブID
| 用途 | job_id |
|---|---|
| c01 空中まくら衝突(冒頭フック+見せ場) | 03f5695d-646d-49b5-993b-4f8fb22a68ee |
| c02 MCバブ 冒頭実況 | 8064007a-8fa1-4200-96de-e61dfdf4c7ec |
| c03 姫 おしゃぶり(かわいい) | 1286b225-7c82-4a83-b93a-5f020fdb5693 |
| c04 王子 セリフ | f6bbaa8b-a7c2-4b6b-a94b-a937b52bf489 |
| c04b 王子 ドリフト | f11768c6-d58e-43cc-a6ff-c7edcd19258f |
| c05 先輩 セリフ | c9aba77e-809a-493a-8660-ab0c248d0d1f |
| c06 姫 セリフ | 538b2cbe-9d88-497b-8014-00ea89b67054 |
| c08 ねんね 睡拳 | 82692d16-2d0b-4360-bcd0-f61289309e56 |
| c09 転がる2人 | 27f1a5dd-6af5-46ac-bdc4-0e202d3d1a93 |
| c10 ねんね「その布団、私のよ」 | 71d90e21-4d51-4528-ba69-06cb8eaa1def |
| c11a 名札(画像) | d96974eb-941d-45ca-a129-c81ad97c8d6b |
| c11b 気まずい2人 | fe464bc3-8be3-4920-8d36-a731ba6e1b96 |
| c12 先生の手と寝落ち | a73ab9eb-5e7d-49a3-a815-d2a6f21774cf |
| c13 ねんね「次は、プリンね」 | 2d7846ac-f31d-42c1-a5c6-e0c9406057f2 |
| c14 MCバブ 次回予告 | 3e6f9fa5-b656-45a2-be89-9bc5f9a7fde8 |
| BGM(シリーズ共通、62秒) | 4b2b43ab-f195-4ac7-b41d-7d91da38d140 |
| 効果音 impact/rewind/drift/crow/swish/bonk | 5aa2c4e9 / e02cc2e2 / 8c0d129b / da657734 / b66bff54 / 25db006c |
| 声:バブ冒頭/次回、先生、先輩寝言、ねんねプリン | 6dca043a / 47b18ada / 73ff14e0 / 5d359646 / 5c086d36 |
