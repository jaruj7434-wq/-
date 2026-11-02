# CLAUDE.md

このファイルは、Claude Code がこのフォルダー(`ai-human-3d-animation/`)で作業する際のガイドです。
リポジトリ直下の `CLAUDE.md` のルールも引き続き有効で、内容がぶつかる場合はこのファイルを優先します。

## プロジェクト概要

このフォルダーでは **Higgs Field**(MCP ツール群: `mcp__higgs_field__*`)を使って、
次の2種類の動画を制作します。

1. **AIによるリアルな人間の動画**: 実写と見分けがつかないフォトリアルな人物が登場する動画
2. **3Dアニメーション動画**: 3Dシーン・3Dモデル・カメラワークを使ったアニメーション動画
   (フォトリアルな3D人物をシーンに置いた映像も含む)

## 生成の許可: 常時許可(事前確認は不要)

- ユーザーから常時許可を得ているため、Higgs Field で **動画・画像・音声・3Dモデル** を作るときは、
  チャットで事前に許可を求めずにそのまま生成してよい。
  - 対象: `generate_image` / `generate_video` / `generate_audio` / `generate_3d` / `*_batch` /
    `execute_preset` / `ai_influencer_generate` / `motion_control` / `upscale_*` / `reframe` /
    `outpaint_image` / `scene_builder_3d_generate_angles` / `scene_builder_3d_generate_video` など。
  - 台本・プロンプトの修正後の再生成、リトライ、部分的な録り直しも同様に確認不要。
- 生成後は必ず、何を生成したか・使ったモデル・消費したクレジット・ジョブIDを報告する。

## クレジットの扱い

- 可能な限り `use_unlim: true`(無制限/トライアル枠)を使い、通常クレジットを消費しないようにする。
- 無制限枠が使えないとツールから返ってきた場合は、確認を取らずに通常クレジットで生成してよい。

## 作業を始める前に必ず行うこと

- **3Dシーン・カメラアングル・3Dアニメーション**を作る場合は、最初に
  `get_preset_instructions({ preset: "/3d-jutsu" })` を呼んで手順を読み込む。
- 複数ステップの動画制作では、直接 `generate_video` を叩く前に
  `get_workflow_instructions`(引数なし)でカタログを確認し、該当するワークフローを読み込む。
  ワークフロー名は毎回カタログで確認し、憶測で決めない。
- どのモデルが合うか分からないときは `models_explore({ action: "recommend" })` で確認する。

## 3Dアニメーション制作の流れ(目安)

1. 企画: `prompts/` に絵コンテ・カット割り・カメラワークを書く
2. 3D素材の準備:
   - 画像から3Dモデル(GLB)を作る → `generate_3d`
   - 3Dシーンの作成・素材の配置 → `scene_builder_3d_create_project` /
     `scene_builder_3d_search_assets` / `scene_builder_3d_import_asset`
   - シーンの確認 → `scene_builder_3d_show_scene`
3. カメラアングル・映像の生成 → `scene_builder_3d_generate_angles` /
   `scene_builder_3d_generate_video`
4. 仕上げ: 必要に応じて `upscale_video`、字幕は `subtitles` ワークフロー

## リアルな人間の動画制作の流れ(目安)

1. 人物設計: 年齢・雰囲気・服装・ライティングなどを `prompts/characters/` にまとめる
2. 人物の一貫性を保つ:
   - AIインフルエンサー(架空の人物)を作る → `ai_influencer_prepare` で設計と価格を確認してから
     `ai_influencer_generate`
   - 複数アングルの参照シート → `character-sheet` ワークフロー(明示的に頼まれた場合のみ)
   - 同一人物を何度も使う → `show_characters`(Soul: 同一人物の写真5〜20枚が必要)か
     `show_reference_elements`(Elements: すぐに使え、複数人物も可)
3. 静止画で見た目を固める → `generate_image`
4. 動画化 → `generate_video`。動きの転写は `motion_control` など
5. 仕上げ: アップスケール、字幕、音声(`generate_audio`)など

### リアルな人物表現のコツ

- プロンプトには肌の質感、自然光・スタジオ光などの照明、レンズ(例: 35mm、50mm)、
  被写界深度、自然な表情やしぐさを具体的に書く。
- 手・指・歯・目線は破綻しやすいので、生成結果を確認してから次の工程へ進む。

## 権利・倫理のルール

- 実在の人物の顔・声・体を使う生成は、**本人の同意が取れているものだけ**を対象にする。
- 有名人・政治家など実在の人物になりすます動画や、誤解を招くディープフェイクは作らない。
- 生成した人物動画を公開するときは、各プラットフォームのルールに従い、
  必要に応じて「AI生成」であることを明記する。

## 出力形式のデフォルト

- SNSショート動画(Reels / TikTok / Shorts)向けは `aspect_ratio: "9:16"` を明示する。
- 横型(YouTube本編など)が必要な場合のみ `16:9` を指定する。
- 生成前にコストを確認したい場合は `get_cost: true` を付けて事前確認する。

## ローカル素材のアップロード

- ローカルの画像・動画は、ファイルパスを直接渡さずに `media_upload_widget`
  (または `media_upload` → アップロード → `media_confirm`)でアップロードしてから使う。

## フォルダー構成

- `prompts/` — 絵コンテ、台本、生成プロンプト
- `prompts/characters/` — 人物・キャラクターの設定
- `assets/source/` — アップロード元の写真・参照動画・3D素材
- `assets/output/` — 生成された動画・画像・3Dモデルの書き出し先
- `docs/` — 企画書、ガイドライン

実際の作業に合わせて構成は調整してよい。

## 開発上の注意

- 生成物(動画・画像・3Dモデル・音声ファイル)は git 管理対象外とし、`.gitignore` で除外する。
  リポジトリにはプロンプト・スクリプト・設定など、再現できるテキストだけをコミットする。
- ユーザーへの返答はすべて日本語で行う。
