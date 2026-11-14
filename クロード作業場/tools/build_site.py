#!/usr/bin/env python3
"""ゆびさき工房のサイトを site/ に作る(そのまま Cloudflare Pages などで公開できる静的サイト)。

- ゲームの情報は下の GAMES に書く。ここに足すだけで、トップの一覧・ゲームページ・遊ぶページが増える
- 各ゲームの本体は src/ から site/play/<slug>/ にコピーし、完全な HTML 文書の形にする
- サムネイル画像は tools/capture_site_thumbs.js で site/img/ に作る

使い方:  python3 tools/build_site.py
"""
import html
import pathlib
import re
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

BRAND = "ゆびさき工房"
BRAND_EN = "Yubisaki Kobo"
TAGLINE = "指先ひとつで遊べる、ちいさな手しごとのゲーム。"
# 独自ドメインを取ったら書く(例: "https://yubisaki-kobo.com")。空なら相対パスで動く
SITE_URL = "https://yubisaki-kobo-games.pages.dev"
LINKS = {
    "x": "",       # 例: "https://x.com/yubisaki_kobo"
    "ofuse": "",   # 例: "https://ofuse.me/xxxx"
    "contact": "",  # 例: "yubisaki.kobo@example.com"
}

# 新しいゲームほど上に書く
GAMES = [
    {
        "slug": "softcream",
        "title": "ソフトクリーム巻き",
        "genre": "シミュレーション",
        "color": "#f08aa6",
        "is_new": True,
        "release": "2026.11.13",
        "catch": "くるくる回るコーンに、注文どおりの高さで巻き上げる。",
        "lead": "長押しでクリームをしぼり、指を左右にずらしてコーンを動かす。外側から少しずつ真ん中へ寄せて渦を巻き上げ、注文の高さで最後にツノを立てる。中心がずれると、傾いて倒れる。",
        "time": "約30秒",
        "controls": "長押ししながら左右にずらす",
        "device": "スマホ / パソコン(3D表示)",
        "how": [
            ("注文を見る", "お客さんの注文(味と高さ)を確認。右の物差しの緑の帯が目標の高さです。"),
            ("しぼる", "画面を長押しするとクリームが出ます。押したまま指を左右に動かすと、コーンが動きます。"),
            ("巻き上げる", "外側から始めて、少しずつ真ん中へ。一周ごとに少し内側に寄せるのがコツ。"),
            ("ツノを立てる", "注文の高さに近づいたら真ん中でしぼってツノを作り、指を離して「できあがり!」。"),
        ],
        "tips": [
            "「かたむき」のゲージが赤くなったら危険。真ん中に寄せすぎず、ずれすぎず。",
            "コーンの外にしぼると、クリームがこぼれて減点されます。",
            "高さは右の物差しで確認。注文の±0.5cm以内なら満点です。",
        ],
        "src": "src/softcream/index.html",
        "extra_dirs": ["src/softcream/tex"],
        "share_tag": "#ソフトクリーム巻き",
    },
    {
        "slug": "takoyaki",
        "title": "たこ焼き返し",
        "genre": "シミュレーション",
        "color": "#f2b544",
        "is_new": False,
        "release": "2026.11.13",
        "catch": "生地を混ぜて、流して、くるっと返す。",
        "lead": "小麦粉をはかって、たまごを割って、だしを注ぐ。鉄板に油をひき、生地を流してタコを入れたら、ふちがきつね色になった瞬間に返す。たこ焼きを一から焼く、1回1分の職人ゲーム。",
        "time": "約1分",
        "controls": "タップ・長押し・なぞる",
        "device": "スマホ / パソコン(3D表示)",
        "how": [
            ("はかる", "長押しで小麦粉 100g、だし 350ml。押すほど勢いが増すので、最後は小刻みに。たまごはゲージが緑のときにタップ。"),
            ("混ぜる", "ボウルの中をぐるぐるなぞる。早くなめらかにするほど高得点。"),
            ("油・流す・タコ", "鉄板をなぞって油をひき、穴の上で長押しして生地を流す。穴をタップしてタコを入れる。"),
            ("焼く", "ふちがきつね色になったらタップで返す。もう一回タップでお皿へ。"),
        ],
        "tips": [
            "油をひき忘れた穴は、返すときにくっついて形が崩れます。",
            "だしが少ない固めの生地は早く焼けます。配合も腕の見せどころ。",
            "焼ける速さは1個ずつ違います。全部の穴から目を離さないこと。",
        ],
        "src": "src/takoyaki3d/index.html",
        "extra_dirs": ["src/takoyaki3d/tex"],
        "share_tag": "#たこ焼き返し",
    },
    {
        "slug": "bullet-alchemist",
        "title": "弾丸の調合師",
        "genre": "シューティング",
        "color": "#5ef2d6",
        "is_new": False,
        "release": "2026.11.09",
        "catch": "ウェーブごとにパーツを選んで、自分だけの弾を作る。",
        "lead": "自機は自動で撃ち続ける。ウェーブを越えるたびに3枚のパーツから1枚を選び、分裂・連鎖・炸裂などを組み合わせて弾を調合していく、1回5分の縦シューティング。",
        "time": "約5分",
        "controls": "ドラッグ / 矢印キー",
        "device": "スマホ / パソコン",
        "how": [
            ("動かす", "スマホは画面のどこでもドラッグ、パソコンは矢印キーか WASD。ショットは自動で出ます。"),
            ("選ぶ", "ウェーブを越えるたびに、3枚のパーツから1枚を選んで弾に組み込む。同じパーツでレベルアップ。"),
            ("倒す", "6ウェーブ目のボスを倒せばクリア。白い点だけが当たり判定です。"),
        ],
        "tips": [
            "分岐 + 連鎖 + 炸裂で、1発当たるだけで画面中に広がります。",
            "残機が少ないときは「修理」が出ることがあります。",
        ],
        "src": "src/chougoushi/index.html",
        "extra_dirs": [],
        "share_tag": "#弾丸の調合師",
    },
]

TOPICS = [
    ("2026.11.13", "新作", "新作「ソフトクリーム巻き」を公開しました。"),
    ("2026.11.13", "お知らせ", "ゆびさき工房のサイトを公開しました。"),
    ("2026.11.13", "新作", "新作「たこ焼き返し」を公開しました。"),
    ("2026.11.09", "新作", "「弾丸の調合師」を公開しました。"),
]

esc = html.escape


# ---------------------------------------------------------------- 共通部品
def page(title, body, depth, desc=TAGLINE, og_image="img/og.jpg"):
    base = "../" * depth
    full_title = f"{title} | {BRAND}" if title != BRAND else f"{BRAND} — 無料のブラウザゲーム"
    og = (SITE_URL + "/" + og_image) if SITE_URL else base + og_image
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:image" content="{esc(og)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#121318">
<link rel="icon" href="{base}img/icon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Maru+Gothic:wght@500;700&display=swap">
<link rel="stylesheet" href="{base}assets/site.css">
</head>
<body>
<header class="site-head">
  <div class="wrap head-in">
    <a class="logo" href="{base}index.html" aria-label="{BRAND} トップへ">
      <svg class="mark" viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="6" fill="currentColor"/><circle cx="20" cy="20" r="12" fill="none" stroke="currentColor" stroke-width="2.5" opacity=".55"/><circle cx="20" cy="20" r="18" fill="none" stroke="currentColor" stroke-width="2" opacity=".25"/></svg>
      <span>{BRAND}</span>
    </a>
    <nav class="nav" aria-label="サイト内">
      <a href="{base}index.html#works">ゲーム一覧</a>
      <a href="{base}index.html#topics">お知らせ</a>
      <a href="{base}about/index.html">工房について</a>
    </nav>
  </div>
</header>
<main>
{body}
</main>
<footer class="site-foot">
  <div class="wrap foot-in">
    <p class="foot-brand">{BRAND}<span>{BRAND_EN}</span></p>
    <nav class="foot-nav" aria-label="サイト情報">
      <a href="{base}about/index.html">運営者情報・クレジット</a>
      <a href="{base}guidelines/index.html">実況・配信ガイドライン</a>
      <a href="{base}privacy/index.html">プライバシーポリシー</a>
    </nav>
    <p class="copy">© 2026 {BRAND}</p>
  </div>
</footer>
</body>
</html>
"""


def thumb(g, base):
    return f'{base}img/{g["slug"]}.jpg'


def link_or_soon(url, label):
    if url:
        return f'<a class="btn ghost" href="{esc(url)}" target="_blank" rel="noopener">{label}</a>'
    return f'<span class="btn ghost is-soon" aria-disabled="true">{label}(準備中)</span>'


# ---------------------------------------------------------------- トップ
def build_index():
    feat = GAMES[0]
    cards = []
    for i, g in enumerate(GAMES, 1):
        cards.append(f"""
      <article class="card" style="--gc:{g['color']}">
        <a class="card-img" href="games/{g['slug']}/index.html">
          <img src="{thumb(g, '')}" alt="{esc(g['title'])} のプレイ画面" loading="lazy" width="600" height="800">
          {'<span class="badge">NEW</span>' if g['is_new'] else ''}
          <span class="num">{i:02d}</span>
        </a>
        <div class="card-body">
          <h3><a href="games/{g['slug']}/index.html">{esc(g['title'])}</a></h3>
          <p class="genre">{esc(g['genre'])}</p>
          <p class="catch">{esc(g['catch'])}</p>
          <div class="actions">
            <a class="btn play" href="play/{g['slug']}/index.html">▶ あそぶ</a>
            <a class="text-link" href="games/{g['slug']}/index.html">遊び方</a>
          </div>
        </div>
      </article>""")
    cards.append("""
      <article class="card soon">
        <div class="soon-in">
          <p class="soon-title">次の作品を<br>つくっています</p>
          <p>出来上がったら、ここに入ります。</p>
        </div>
      </article>""")
    topics = "\n".join(f'<li><time>{d}</time><span class="tag">{esc(t)}</span><p>{esc(s)}</p></li>' for d, t, s in TOPICS)
    body = f"""
<section class="hero">
  <div class="wrap hero-in" style="--gc:{feat['color']}">
    <div class="hero-text">
      <p class="eyebrow">{'NEW ・ ' if feat['is_new'] else ''}{esc(feat['genre'])}</p>
      <h1>{esc(feat['title'])}</h1>
      <p class="hero-catch">{esc(feat['catch'])}</p>
      <p class="hero-lead">{esc(feat['lead'])}</p>
      <div class="actions">
        <a class="btn play big" href="play/{feat['slug']}/index.html">▶ いますぐ あそぶ</a>
        <a class="text-link" href="games/{feat['slug']}/index.html">遊び方を見る</a>
      </div>
      <p class="free">インストール・会員登録なし。URL を開くだけで、スマホでもパソコンでも遊べます。</p>
    </div>
    <a class="hero-img" href="play/{feat['slug']}/index.html" aria-label="{esc(feat['title'])} をあそぶ">
      <img src="{thumb(feat, '')}" alt="{esc(feat['title'])} のプレイ画面" width="600" height="800">
    </a>
  </div>
</section>

<section class="section" id="works">
  <div class="wrap">
    <div class="sec-head"><h2>WORKS</h2><p>ゲーム一覧</p></div>
    <div class="grid">{''.join(cards)}
    </div>
  </div>
</section>

<section class="section" id="topics">
  <div class="wrap narrow">
    <div class="sec-head"><h2>TOPICS</h2><p>お知らせ</p></div>
    <ul class="topics">{topics}</ul>
  </div>
</section>

<section class="section" id="about">
  <div class="wrap narrow">
    <div class="sec-head"><h2>ABOUT</h2><p>工房について</p></div>
    <p class="about">{BRAND}は、指先ひとつで遊べる小さなゲームを作っている個人の工房です。日常のちょっとした手しごとを、1回数十秒〜数分で遊べるゲームにしています。すべて無料のブラウザゲームで、インストールも会員登録もいりません。感想や不具合の報告をお待ちしています。</p>
    <div class="actions">
      {link_or_soon(LINKS['x'], 'X で新作のお知らせを受け取る')}
      {link_or_soon(LINKS['ofuse'], 'OFUSE で応援する')}
    </div>
  </div>
</section>
"""
    (SITE / "index.html").write_text(page(BRAND, body, 0), encoding="utf-8")


# ---------------------------------------------------------------- ゲームページ
def build_game_page(g):
    base = "../../"
    steps = "\n".join(f'<li><h3>{esc(t)}</h3><p>{esc(d)}</p></li>' for t, d in g["how"])
    tips = "\n".join(f"<li>{esc(t)}</li>" for t in g["tips"])
    share_text = f'{g["title"]}|{BRAND} {g["share_tag"]}'
    body = f"""
<section class="game-hero" style="--gc:{g['color']}">
  <div class="wrap hero-in">
    <div class="hero-text">
      <p class="eyebrow"><a href="{base}index.html#works">ゲーム一覧</a> / {esc(g['genre'])}</p>
      <h1>{esc(g['title'])}</h1>
      <p class="hero-catch">{esc(g['catch'])}</p>
      <p class="hero-lead">{esc(g['lead'])}</p>
      <div class="actions">
        <a class="btn play big" href="{base}play/{g['slug']}/index.html">▶ あそぶ</a>
      </div>
      <dl class="spec">
        <div><dt>1回のプレイ</dt><dd>{esc(g['time'])}</dd></div>
        <div><dt>操作</dt><dd>{esc(g['controls'])}</dd></div>
        <div><dt>対応</dt><dd>{esc(g['device'])}</dd></div>
        <div><dt>公開日</dt><dd>{esc(g['release'])}</dd></div>
        <div><dt>価格</dt><dd>無料</dd></div>
      </dl>
    </div>
    <a class="hero-img" href="{base}play/{g['slug']}/index.html" aria-label="{esc(g['title'])} をあそぶ">
      <img src="{thumb(g, base)}" alt="{esc(g['title'])} のプレイ画面" width="600" height="800">
    </a>
  </div>
</section>

<section class="section">
  <div class="wrap narrow">
    <div class="sec-head"><h2>HOW TO PLAY</h2><p>遊び方</p></div>
    <ol class="steps">{steps}</ol>
    <h3 class="tips-head">コツ</h3>
    <ul class="tips">{tips}</ul>
  </div>
</section>

<section class="section">
  <div class="wrap narrow">
    <div class="sec-head"><h2>SHARE</h2><p>友だちに教える</p></div>
    <div class="actions">
      <a class="btn ghost" href="https://twitter.com/intent/tweet?text={html.escape(share_text)}{('&url=' + SITE_URL + '/games/' + g['slug'] + '/') if SITE_URL else ''}" target="_blank" rel="noopener">X でシェア</a>
      <a class="text-link" href="{base}guidelines/index.html">実況・配信は自由です(ガイドライン)</a>
    </div>
  </div>
</section>
"""
    out = SITE / "games" / g["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page(g["title"], body, 2, desc=g["catch"], og_image=f"img/{g['slug']}.jpg"), encoding="utf-8")


# ---------------------------------------------------------------- ゲーム本体のコピー
def build_play(g):
    src = (ROOT / g["src"]).read_text(encoding="utf-8")
    src = re.sub(r'^<meta charset="utf-8">\n', "", src)
    m = re.match(r"<title>(.*?)</title>\n", src)
    assert m, g["src"] + " の先頭に <title> がありません"
    rest = src[m.end():]
    end = rest.index("</style>") + len("</style>\n")
    head, body = rest[:end], rest[end:]
    # シェア文に、このページの URL が入るようにする
    body = body.replace("const GAME_URL = '';", "const GAME_URL = location.origin + location.pathname;")
    doc = (
        "<!doctype html>\n<html lang=\"ja\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
        f"<title>{esc(g['title'])} | {BRAND}</title>\n"
        f"<meta name=\"description\" content=\"{esc(g['catch'])}\">\n"
        "<link rel=\"icon\" href=\"../../img/icon.svg\" type=\"image/svg+xml\">\n"
        + head + "</head>\n<body>\n"
        + "<a class=\"yk-home\" href=\"../../games/" + g["slug"] + "/index.html\" aria-label=\"遊び方と作品ページへ\">"
        + "<svg viewBox=\"0 0 40 40\" aria-hidden=\"true\"><circle cx=\"20\" cy=\"20\" r=\"6\" fill=\"currentColor\"/><circle cx=\"20\" cy=\"20\" r=\"12\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"3\" opacity=\".6\"/></svg></a>\n"
        + "<style>.yk-home{position:fixed;left:calc(8px + env(safe-area-inset-left,0px));bottom:calc(8px + env(safe-area-inset-bottom,0px));z-index:50;width:36px;height:36px;display:grid;place-items:center;border-radius:50%;background:rgba(0,0,0,.45);color:#f1ece2;border:1px solid rgba(255,255,255,.25)}.yk-home svg{width:22px;height:22px}</style>\n"
        + body + "</body>\n</html>\n"
    )
    out = SITE / "play" / g["slug"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "index.html").write_text(doc, encoding="utf-8")
    for d in g["extra_dirs"]:
        p = ROOT / d
        if p.exists():
            shutil.copytree(p, out / p.name)
        else:
            print("  (素材なし)", d, "— 素材なしでも動く作りのため続行")


# ---------------------------------------------------------------- 固定ページ
def build_static():
    contact = esc(LINKS["contact"]) if LINKS["contact"] else "準備中(決まりしだい掲載します)"
    x = f'<a href="{esc(LINKS["x"])}" target="_blank" rel="noopener">{esc(LINKS["x"])}</a>' if LINKS["x"] else "準備中"
    about = f"""
<section class="section doc">
  <div class="wrap narrow">
    <div class="sec-head"><h2>ABOUT</h2><p>運営者情報・クレジット</p></div>
    <dl class="table">
      <div><dt>名称</dt><dd>{BRAND}({BRAND_EN})</dd></div>
      <div><dt>運営</dt><dd>個人で運営しています</dd></div>
      <div><dt>内容</dt><dd>無料のブラウザゲームの制作・公開</dd></div>
      <div><dt>お問い合わせ</dt><dd>{contact}</dd></div>
      <div><dt>X</dt><dd>{x}</dd></div>
    </dl>
    <h3>クレジット</h3>
    <ul class="plain">
      <li>フォント:Dela Gothic One、Zen Maru Gothic、DotGothic16(いずれも SIL Open Font License 1.1)</li>
      <li>3D 表示:three.js(MIT License)</li>
      <li>一部のゲームの質感画像は、画像生成サービス Higgsfield で作成しています。</li>
      <li>ゲームのプログラムは、AI(Claude)の補助を受けて制作しています。</li>
    </ul>
  </div>
</section>"""
    privacy = f"""
<section class="section doc">
  <div class="wrap narrow">
    <div class="sec-head"><h2>PRIVACY</h2><p>プライバシーポリシー</p></div>
    <p>{BRAND}(以下「当工房」)は、当サイトで公開するゲームとページ(以下「本サイト」)における利用者の情報の扱いを、次のとおり定めます。</p>
    <h3>1. 取得する情報</h3>
    <p>本サイトは会員登録を行わず、氏名やメールアドレスなどの個人情報をゲーム内で入力していただくことはありません。</p>
    <h3>2. 端末に保存する情報</h3>
    <p>ハイスコア、音のオン・オフ、遊んだ回数などの設定を、ブラウザの保存領域(localStorage)に保存します。これらは利用者の端末の中だけに保存され、当工房に送られることはありません。ブラウザの設定から削除できます。</p>
    <h3>3. アクセス解析</h3>
    <p>サイトの改善のため、アクセス解析ツールを使う場合があります。その場合でも、個人を特定する情報は取得しません。導入した場合は、ツール名をこのページに記載します。</p>
    <h3>4. 広告について</h3>
    <p>今後、第三者配信の広告サービスを利用する場合があります。その場合、広告配信事業者が Cookie などを使って、利用者の興味に応じた広告を表示することがあります。導入時は、サービス名と、Cookie を無効にする方法をこのページに記載します。</p>
    <h3>5. 外部サービスへのリンク</h3>
    <p>本サイトには X などの外部サービスへのリンクがあります。リンク先での情報の扱いは、各サービスの方針によります。</p>
    <h3>6. お問い合わせ</h3>
    <p>本ポリシーについてのお問い合わせ先:{contact}</p>
    <h3>7. 改定</h3>
    <p>本ポリシーは、必要に応じて改定することがあります。改定した場合は、このページでお知らせします。</p>
    <p class="date">制定:2026年11月13日</p>
  </div>
</section>"""
    guidelines = f"""
<section class="section doc">
  <div class="wrap narrow">
    <div class="sec-head"><h2>GUIDELINES</h2><p>実況・配信ガイドライン</p></div>
    <p>{BRAND}のゲームは、<strong>個人・法人を問わず、実況・配信・動画投稿を自由に行っていただけます</strong>。事前の連絡は不要です。</p>
    <h3>できること</h3>
    <ul class="plain">
      <li>YouTube、Twitch、ニコニコ動画、TikTok などでの実況・配信・動画投稿</li>
      <li>動画や配信での収益化(広告収入・投げ銭・メンバーシップなど)</li>
      <li>切り抜き動画、サムネイルへのゲーム画面の使用</li>
    </ul>
    <h3>お願い</h3>
    <ul class="plain">
      <li>概要欄などに、ゲーム名と本サイトの URL を書いていただけるとうれしいです(任意)。</li>
      <li>X でハッシュタグ(例:#たこ焼き返し)を付けて投稿していただけると、見に行きます。</li>
    </ul>
    <h3>ご遠慮ください</h3>
    <ul class="plain">
      <li>ゲームそのもののファイルを、別のサイトにアップロードして公開すること</li>
      <li>当工房の作品であると誤解させるような改変版の配布</li>
      <li>公序良俗に反する内容での使用</li>
    </ul>
    <p class="date">制定:2026年11月13日</p>
  </div>
</section>"""
    notfound = """
<section class="section doc">
  <div class="wrap narrow">
    <div class="sec-head"><h2>404</h2><p>ページが見つかりません</p></div>
    <p>お探しのページは、移動したか削除された可能性があります。</p>
    <div class="actions"><a class="btn play" href="/index.html">トップへ戻る</a></div>
  </div>
</section>"""
    for name, title, body in (("about", "運営者情報・クレジット", about), ("privacy", "プライバシーポリシー", privacy), ("guidelines", "実況・配信ガイドライン", guidelines)):
        d = SITE / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page(title, body, 1), encoding="utf-8")
    (SITE / "404.html").write_text(page("ページが見つかりません", notfound, 0), encoding="utf-8")


def build():
    SITE.mkdir(exist_ok=True)
    (SITE / "img").mkdir(exist_ok=True)
    (SITE / "assets").mkdir(exist_ok=True)
    build_index()
    for g in GAMES:
        build_game_page(g)
        build_play(g)
    build_static()
    print("built", SITE)


if __name__ == "__main__":
    build()
