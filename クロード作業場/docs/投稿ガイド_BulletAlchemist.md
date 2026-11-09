# Bullet Alchemist(弾丸の調合師)投稿ガイド

対象: **itch.io** と **CrazyGames**(Poki・日本のサイトには出さない方針)

## 投稿用ファイル(作り方)

```bash
cd クロード作業場
python3 tools/build_chougoushi.py      # → dist/bullet-alchemist-web.zip(ゲーム本体)
node tools/capture_chougoushi.js       # → dist/media/(カバー画像・スクショ・動画)
```

| ファイル | 使う場所 |
|---|---|
| `dist/bullet-alchemist-web.zip` | ゲーム本体(両サイト共通。zip の一番上に index.html) |
| `dist/media/cover-landscape-1920x1080.png` | CrazyGames カバー(横 16:9) |
| `dist/media/cover-portrait-800x1200.png` | CrazyGames カバー(縦 2:3) |
| `dist/media/cover-square-800x800.png` | CrazyGames カバー(正方形 1:1) |
| `dist/media/preview-landscape-1920x1080.mp4` | CrazyGames 紹介動画(横・20秒) |
| `dist/media/preview-portrait-1080x1920.mp4` | CrazyGames 紹介動画(縦・20秒) |
| `dist/media/cover-itch-630x500.png` | itch.io カバー画像 |
| `dist/media/screenshot-1〜4.png` | itch.io スクリーンショット |

- ゲーム本体は外部サーバーに一切アクセスしない(フォントも同梱、約88KB)
- ブラウザの言語が日本語なら日本語、それ以外は英語で始まる(右上ボタンで切り替え可)

---

## 1. itch.io(すぐ公開できる・審査なし)

1. https://itch.io にアカウント登録 → 右上メニュー「Upload new project」
2. 入力内容
   - **Title**: `Bullet Alchemist`
   - **Project URL**: `bullet-alchemist`(自動で入る)
   - **Short description or tagline**: 下の「短い説明」を貼る
   - **Classification**: Games
   - **Kind of project**: **HTML**
   - **Pricing**: 「No payments」か「$0 or donate」(投げ銭を受けるなら後者)
   - **Uploads**: `bullet-alchemist-web.zip` をアップロード → 「This file will be played in the browser」にチェック
   - **Embed options**
     - Viewport dimensions: **405 × 720**
     - ✅ Mobile friendly(Orientation: Portrait)
     - ✅ Automatically start on page load は**オフ**のままでよい
     - ✅ Fullscreen button
   - **Details → Description**: 下の「長い説明」を貼る
   - **Genre**: Shooter
   - **Tags**: `shoot-em-up`, `roguelite`, `bullet-hell`, `arcade`, `upgrades`, `short`, `2d`, `singleplayer`
   - **AI generation disclosure**: 正直に答える(コードは AI の補助で作成。画像・音声は AI 生成なし ※2026-11 時点)
   - **Cover image**: `cover-itch-630x500.png`
   - **Screenshots**: `screenshot-1〜4.png`
3. 「Save & view page」で下書き確認 → 問題なければ **Visibility を Public** にして公開

## 2. CrazyGames(お試し公開 → 数字が良ければ本公開)

1. https://developer.crazygames.com で開発者登録
2. 「Submit game」→ HTML5 を選んで `bullet-alchemist-web.zip` をアップロード
3. 入力内容
   - **Game name**: `Bullet Alchemist`
   - **Category**: Shooting(近いものを選ぶ)
   - **Tags**: Shooter, Roguelite, Bullet Hell, Arcade, Upgrade
   - **Description / Controls**: 下の文章を貼る
   - **Orientation**: Portrait、**Mobile**: 対応(スマホ可)
   - **Covers**: landscape / portrait / square の3枚
   - **Preview videos**: 横・縦の mp4 を1本ずつ
4. 提出 → 審査(QA) → **Basic Launch**(一部の利用者に1〜3週間公開。この期間の収益はゼロ)
5. Basic Launch の数字(平均プレイ時間・翌日も遊ぶ人の割合など)が良いと **Full Launch** の案内が来る
   - Full Launch には CrazyGames SDK の組み込み(広告・データ保存)が必要 → その時点で対応する

### 審査で指摘されそうな点(事前に把握)
- タイトル画面で「タップしてスタート」が必要(「すぐゲームが始まること」を求める基準がある)。指摘されたら、タイトルを省いていきなりパーツ選択から始める形に変える
- 画面が縦長なので、PC では左右に黒い余白が出る(縦長ゲームは認められている)

---

## 貼り付け用テキスト(英語)

### 短い説明(tagline)
```
Brew your own bullets! A 5-minute shooter where every wave lets you pick 1 of 3 parts for your shot.
```

### 長い説明(description)
```
Brew your own bullets.

Bullet Alchemist is a short vertical shooter with a roguelite twist. Your ship fires automatically. After every wave, pick 1 of 3 parts and add it to your bullet recipe. Stack Split, Fork, Chain, Blast, Homing and more until a single shot turns into a screen-filling chain reaction. Survive 5 waves, then take down the boss.

FEATURES
- 11 bullet parts that combine in different ways: Split, Rapid, Heavy, Pierce, Bounce, Homing, Frost, Blast, Chain, Fork, Burn
- A new recipe every run, about 5 minutes per run
- Combo multiplier up to x3 for chaining kills
- Plays on PC and mobile (portrait), English / Japanese

TIPS
- Only the white dot in the middle of your ship can be hit
- Fork + Chain + Blast makes every hit spread across the screen
```

### 操作説明(controls)
```
PC: Arrow keys / WASD to move, Shift to move slowly, P to pause, M to toggle sound. Press 1-3 to pick a part.
Mobile: Drag anywhere on the screen to move. Tap a card to pick a part.
Your ship fires automatically.
```

---

## 公開後にやること
- itch.io の閲覧数・プレイ数、CrazyGames の管理画面の数字を週1回メモする
- 感想やコメントは `docs/弾丸の調合師_試遊メモ.md` に追記して、次の調整に使う
