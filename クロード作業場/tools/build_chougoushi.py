#!/usr/bin/env python3
"""「弾丸の調合師(Bullet Alchemist)」の投稿用ファイル一式を作る。

やること
  1. src/chougoushi/index.html を読み、Google Fonts の読み込みをやめて、
     同梱フォント(ゲームで使う文字だけに絞った woff2)を使う形に書き換える
  2. 完全な HTML 文書(doctype・head 付き)として dist/bullet-alchemist/ に書き出す
  3. フォントのライセンス(OFL)を同梱する
  4. dist/bullet-alchemist-web.zip を作る(index.html が zip の一番上に来る形)

使い方:  python3 tools/build_chougoushi.py
必要なもの: fonttools, brotli(pip install fonttools brotli)
"""
import pathlib
import re
import shutil
import string
import urllib.request
import zipfile

from fontTools import subset

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "chougoushi" / "index.html"
FONT_DIR = ROOT / "assets" / "source" / "fonts"
FONT_TTF = FONT_DIR / "DotGothic16-Regular.ttf"
FONT_LICENSE = FONT_DIR / "OFL.txt"
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/dotgothic16/DotGothic16-Regular.ttf"
LICENSE_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/dotgothic16/OFL.txt"
OUT = ROOT / "dist" / "bullet-alchemist"
ZIP = ROOT / "dist" / "bullet-alchemist-web.zip"


def ensure_font():
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for path, url in ((FONT_TTF, FONT_URL), (FONT_LICENSE, LICENSE_URL)):
        if not path.exists():
            print("download", url)
            urllib.request.urlretrieve(url, path)


def build():
    ensure_font()
    html = SRC.read_text(encoding="utf-8")

    # 1. Google Fonts の <link> を外し、同梱フォントの @font-face を足す
    html = re.sub(r'<link rel="preconnect"[^>]*>\n', "", html)
    html = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>\n', "", html)
    assert "googleapis" not in html, "Google Fonts の読み込みが残っています"
    font_face = (
        "@font-face {\n"
        '  font-family: "DotGothic16";\n'
        '  src: url("fonts/DotGothic16-subset.woff2") format("woff2");\n'
        "  font-display: swap;\n"
        "}\n"
    )
    html = html.replace("<style>\n", "<style>\n" + font_face, 1)

    # 2. 完全な HTML 文書にする(投稿サイトは index.html をそのまま開くため)
    m = re.match(r"<title>.*?</title>\n", html)
    assert m, "先頭に <title> が見つかりません"
    body = html[m.end():]
    style_end = body.index("</style>") + len("</style>\n")
    head_extra, body = body[:style_end], body[style_end:]
    doc = (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "<title>Bullet Alchemist</title>\n"
        + head_extra
        + "</head>\n<body>\n"
        + body
        + "</body>\n</html>\n"
    )

    # 3. フォントを、このゲームで使う文字だけに絞る(約2MB → 数十KB)
    chars = set(doc) | set(string.printable) | set("→×♥・、。!?()")
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "fonts").mkdir(parents=True)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    font = subset.load_font(str(FONT_TTF), opts)
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(chars)))
    sub.subset(font)
    subset.save_font(font, str(OUT / "fonts" / "DotGothic16-subset.woff2"), opts)
    shutil.copy(FONT_LICENSE, OUT / "fonts" / "OFL.txt")

    (OUT / "index.html").write_text(doc, encoding="utf-8")

    # 4. zip にまとめる(index.html を一番上に置く)
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(OUT).as_posix())

    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"built {OUT} ({total / 1024:.1f} KB), zip {ZIP.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build()
