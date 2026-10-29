"""牛の合体進化の素材を集める。

1. Higgs Field で生成した牛の写真5枚(背景透明の PNG)をダウンロードする。
2. Wikimedia Commons から、自由に使える(CC0 / パブリックドメイン / CC BY)本物の牛の鳴き声を探してダウンロードし、
   48kHz の wav に変換する。作者・ライセンスは assets/source/cow/sounds/credits.json と
   docs/licenses/cow_sounds.md に記録する(CC BY は投稿の説明文にクレジット表記が必要)。

必要な通信先: d8j0ntlcm91z4.cloudfront.net / commons.wikimedia.org / upload.wikimedia.org

使い方:
    python fetch_assets.py
"""

import json
import os
import re
import subprocess
import urllib.parse
import urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
IMG_DIR = os.path.join(ROOT, "assets", "source", "cow")
SND_DIR = os.path.join(IMG_DIR, "sounds")
LICENSE_MD = os.path.join(ROOT, "docs", "licenses", "cow_sounds.md")
UA = "DeruPhysicsBot/1.0 (personal video project; contact via repository owner)"

# Higgs Field の生成結果(Seedream 5.0 Pro・背景除去つき・1024x1024)
IMAGES = {
    "cow1.png": "hf_20261029_225027_9bbc373d-b739-484a-a031-3ffc66733e76.png",   # 生まれたての子牛
    "cow2.png": "hf_20261029_225028_0b895b53-680f-4096-9fe5-81c4fdf622f0.png",   # 子牛
    "cow3.png": "hf_20261029_225028_e3e199a4-442b-4f47-abf1-760cbdc53d9a.png",   # 若い牛
    "cow4.png": "hf_20261029_225029_6a2f295b-4acf-49fa-bb3b-689bac9f5c12.png",   # 大人の牛
    "cow5.png": "hf_20261029_225028_560e40d2-b96a-424f-b80a-6ee77db10cb7.png",   # 巨大な雄牛
}
IMG_BASE = "https://d8j0ntlcm91z4.cloudfront.net/user_3IAIfINAmehvTGXEdm9EGpVegmO/"

# 鳴き声の検索語(段階ごと)
SOUND_QUERIES = {
    "calf": ["calf bleat", "calf moo", "calf mooing"],
    "cow": ["cow moo", "cow mooing", "Bos taurus"],
    "bull": ["bull bellow", "bull bellowing", "bull roar"],
}
OK_LICENSE = re.compile(r"^(cc0|public domain|pd|cc by \d|cc-by-\d|cc by-\d)", re.I)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch_images():
    os.makedirs(IMG_DIR, exist_ok=True)
    for name, key in IMAGES.items():
        path = os.path.join(IMG_DIR, name)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(get(IMG_BASE + key))
        print("写真:", name)


def search_sounds(query, limit=8):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"{query} filetype:audio", "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size",
    })
    data = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))
    out = []
    for p in (data.get("query", {}).get("pages", {}) or {}).values():
        ii = p["imageinfo"][0]
        meta = ii.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        if not OK_LICENSE.match(lic.strip()):
            continue
        artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
        out.append({"title": p["title"], "url": ii["url"], "page": ii.get("descriptionurl", ""),
                    "license": lic, "artist": artist, "size": ii.get("size", 0)})
    return out


def fetch_sounds():
    os.makedirs(SND_DIR, exist_ok=True)
    credits = []
    for kind, queries in SOUND_QUERIES.items():
        seen = set()
        n = 0
        for q in queries:
            for s in search_sounds(q):
                if s["title"] in seen or s["size"] > 15_000_000:
                    continue
                seen.add(s["title"])
                ext = os.path.splitext(s["url"])[1]
                raw = os.path.join(SND_DIR, f"{kind}_{n}{ext}")
                wav = os.path.join(SND_DIR, f"{kind}_{n}.wav")
                with open(raw, "wb") as f:
                    f.write(get(s["url"]))
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-ac", "1", "-ar", "48000", wav],
                               check=True)
                os.remove(raw)
                credits.append({"file": os.path.basename(wav), **s})
                print("鳴き声:", os.path.basename(wav), s["title"], s["license"])
                n += 1
                if n >= 5:
                    break
            if n >= 5:
                break
    with open(os.path.join(SND_DIR, "credits.json"), "w") as f:
        json.dump(credits, f, ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(LICENSE_MD), exist_ok=True)
    with open(LICENSE_MD, "w") as f:
        f.write("# 牛の鳴き声の素材(Wikimedia Commons)\n\n"
                "CC BY のものは、投稿の説明文に「作者名 / ライセンス / 出典URL」を書く。\n\n"
                "| ファイル | 元のタイトル | 作者 | ライセンス | 出典 |\n|---|---|---|---|---|\n")
        for c in credits:
            f.write(f"| {c['file']} | {c['title']} | {c['artist']} | {c['license']} | {c['page']} |\n")


if __name__ == "__main__":
    fetch_images()
    fetch_sounds()
