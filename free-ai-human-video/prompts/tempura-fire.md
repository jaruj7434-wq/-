# 天ぷら油の火に水をかけると?(ライフハック・約48秒)

- 形式:3DCG 防災ライフハックショート(顔出しなし・テンポのよいナレーション+強調テロップ)
- 仕様:1080x1920 / 24fps
- 炎・煙は自作の物理シミュレーション(`../scripts/tempura_fire/firesim.py`)で計算したものを描画
- 使用ツール(すべて無料):Blender(bpy・Cycles)、numba、Style-Bert-VITS2(JVNV)、FFmpeg

## 台本とカット割り

| # | ナレーション | 映像 | 強調テロップ |
|---|---|---|---|
| 1 | 天ぷら油に火がついたとき、水をかけたらどうなるか。知ってますか? | 燃える鍋。水の入ったコップが近づく | 水をかけたら? |
| 2 | 答えは、一瞬で、天井まで届く火柱。 | 水が入った瞬間、火柱が天井まで(スローモーション) | 天井まで火柱 |
| 3 | 水は、水蒸気になると、体積が約1700倍にふくらみます。 | 鍋の断面。沈んだ水滴が一気に水蒸気の泡になる | 約1700倍 |
| 4 | その勢いで、燃えている油が細かいしぶきになって飛び散り、一気に燃え広がるんです。 | 燃える油のしぶきが飛び散る | 油が飛び散る |
| 5 | そもそも油は、約370度になると、火を近づけなくても燃え出します。 | 温度計が370℃まで上がり、油が自然発火 | 約370℃で発火 |
| 6 | コンロから目を離した、数分の間に起こることもあります。 | 誰もいない台所で鍋から煙 | 目を離さない |
| 7 | もし火が出たら、黄色いマークの付いた消火器を、少し離れたところから使いましょう。 | 消火器のラベル(黄色の油火災マーク)→噴射して消える | 黄色マークの消火器 |
| 8 | 消火器がないときは、火を止めて、鍋に合ったふたで、空気を断ちます。すぐには開けないこと。 | 火を止め、ふたをかぶせて消える | ふたで空気を断つ |
| 9 | ちなみに、ネットで見かける、マヨネーズを入れる方法は、油が飛び散って危険です。 | マヨネーズに赤い✕ | マヨネーズは✕ |
| 10 | いざという時のために、保存して、家族にも教えてあげてください。 | 安全に揚げ物をしている鍋 | 保存して家族にも |

## 事実確認メモ

- 水をかけると炎が急拡大する(各地の消防局の再現実験):[千葉市消防局](https://www.city.chiba.jp/shobo/somu/somu/kasaijikken.html)、[札幌市消防局](https://www.city.sapporo.jp/shobo/shokai/gakko/labo/movie/konro.html)、[福岡市](https://www.city.fukuoka.lg.jp/syobo/yobo/topics/documents/konrochirasi.pdf)、[神戸新聞(神戸市消防局の実験)](https://www.kobe-np.co.jp/news/sougou/202205/0015276525.shtml)
- 水は水蒸気になると体積が約1700倍(水そのものの性質):[大阪市立科学館](https://www.sci-museum.jp/wp-content/themes/scimuseum2021/pdf/study/research/2015/pb25_077-080.pdf)
- 油は約340〜370℃で発火、目を離した数分で火災になることも:[名古屋市消防局](https://www.city.nagoya.jp/shobo/cmsfiles/contents/0000130/130929/aburanimizu.pdf)、[西宮市消防局](https://www.nishi.or.jp/kurashi/anshin/shobokyoku/kasaiyobo/konrokasai/tenpura-chui.html)、[総務省消防庁](https://www.fdma.go.jp/relocation/e-college/senmon/bosai/main/kyouzai28.pdf)
- 消火器がもっとも確実、油火災は黄色マーク、少し離れて使う:[堺市](https://www.city.sakai.lg.jp/kurashi/bosai/shobo/shimin/kasaiyobo/kikenbutsujiko/kikenbutu/31373920240509084512275.html)、[沼津市](https://city.numazu.shizuoka.jp/kurashi/anshin/bousai/kunren/doc/tenpura_haifu.pdf)
- 火を止めてふたで空気を断ち、すぐ開けない:[沼津市](https://city.numazu.shizuoka.jp/kurashi/anshin/bousai/kunren/doc/tenpura_haifu.pdf)
- マヨネーズは油が飛び散って危険:[神戸新聞(神戸市消防局の実験)](https://www.kobe-np.co.jp/news/sougou/202205/0015276525.shtml)
- 濡れタオルは自治体で見解が分かれる(横浜市は案内、神戸市・東京消防庁は勧めない)ため台本に入れない。

## クレジット表記(概要欄に記載)

- 音声:Style-Bert-VITS2 / JVNV コーパス(CC BY-SA 4.0)
