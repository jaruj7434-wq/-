"""第1話の2D図解(テロップ・地図・グラフ)を PIL でフレーム生成する。

各グラフィックは draw(t, dur) -> PIL.Image(1920x1080) を返す関数を作るファクトリ。
数字は prompts/mono_no_issho/plan.md の出典付きリサーチに基づく。
"""
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
BG = (14, 18, 28)
BG2 = (24, 30, 44)
FG = (240, 242, 245)
SUB = (150, 160, 178)
SILVER = (205, 210, 216)
ACCENT = (255, 150, 60)     # 炉の色
BLUE = (90, 170, 255)
RED = (255, 90, 80)

_FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
_FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
_cache = {}


def font(size, bold=True):
    k = (size, bold)
    if k not in _cache:
        _cache[k] = ImageFont.truetype(_FB if bold else _FR, size, index=0)
    return _cache[k]


# ------------------------------------------------------------------ 補助
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def prog(t, start, length=0.6):
    return ease((t - start) / length)


def canvas():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    # うっすら縦グラデーション
    for y in range(0, H, 4):
        k = y / H
        c = tuple(int(BG[i] * (1 - k) + BG2[i] * k) for i in range(3))
        d.rectangle([0, y, W, y + 4], fill=c)
    return im


def text(d, xy, s, size, fill=FG, anchor="la", bold=True, alpha=1.0, bg=BG):
    if alpha <= 0:
        return
    col = tuple(int(bg[i] + (fill[i] - bg[i]) * alpha) for i in range(3))
    d.text(xy, s, font=font(size, bold), fill=col, anchor=anchor)


def fade(t, dur, tin=0.4, tout=0.4):
    return clamp(t / tin) * clamp((dur - t) / tout)


def coin_icon(im, cx, cy, r, label="1", worn=False):
    """1円玉アイコン(銀の円+「1」)。"""
    d = ImageDraw.Draw(im)
    base = (170, 172, 175) if worn else SILVER
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=base, outline=(120, 124, 130), width=max(1, r // 12))
    d.ellipse([cx - r * .82, cy - r * .82, cx + r * .82, cy + r * .82], outline=(150, 154, 160), width=max(1, r // 18))
    d.text((cx, cy + r * .05), label, font=font(int(r * 1.1)), fill=(110, 114, 120), anchor="mm")


def apply_fade(im, a):
    if a >= 1:
        return im
    return Image.blend(Image.new("RGB", im.size, (0, 0, 0)), im, clamp(a))


# ------------------------------------------------------------------ 日本地図(簡略)
_JAPAN = {
    "hokkaido": [(141.0, 41.4), (140.0, 42.3), (139.8, 42.6), (140.3, 43.3), (141.4, 43.3), (141.6, 45.3), (142.0, 45.5),
                 (143.5, 44.2), (145.3, 44.3), (145.8, 43.4), (145.3, 43.0), (143.9, 42.9), (143.3, 42.0), (141.8, 42.6), (141.0, 41.8)],
    "honshu": [(141.4, 41.4), (141.5, 40.5), (142.0, 39.6), (141.6, 38.3), (141.0, 38.0), (140.9, 36.9), (140.6, 36.0),
               (140.9, 35.7), (140.4, 35.1), (139.8, 34.9), (139.7, 35.3), (139.2, 35.2), (138.8, 34.6), (138.2, 34.6),
               (137.0, 34.6), (136.9, 34.3), (136.0, 33.5), (135.2, 33.8), (135.4, 34.6), (134.0, 34.6), (133.0, 34.4),
               (132.0, 34.0), (131.0, 33.9), (130.9, 34.3), (131.4, 34.5), (132.5, 35.4), (133.5, 35.6), (135.0, 35.7),
               (135.9, 35.6), (136.0, 36.0), (136.7, 36.9), (137.3, 37.0), (137.4, 36.8), (138.5, 37.4), (139.4, 38.2),
               (139.9, 39.0), (140.0, 40.2), (140.3, 41.2), (141.0, 41.2)],
    "shikoku": [(132.4, 33.3), (132.6, 34.0), (133.5, 34.3), (134.6, 34.2), (134.7, 33.8), (134.2, 33.3), (133.0, 32.8), (132.5, 32.9)],
    "kyushu": [(129.8, 33.3), (130.4, 33.9), (131.0, 33.9), (131.6, 33.6), (131.9, 32.6), (131.4, 31.4), (130.7, 31.0),
               (130.2, 31.3), (130.3, 32.2), (130.0, 32.8), (129.7, 33.0)],
}
PLACES = {"大阪": (135.52, 34.70), "広島": (132.42, 34.40), "東京": (139.77, 35.69)}


def proj(lon, lat, zoom=1.0, center=(136.0, 37.5)):
    k = 95 * zoom
    return (W / 2 + (lon - center[0]) * k, H / 2 + (center[1] - lat) * k * 1.2)


def draw_japan(im, zoom=1.0, center=(136.0, 37.5), fill=(40, 52, 72), outline=(80, 98, 128)):
    d = ImageDraw.Draw(im)
    for poly in _JAPAN.values():
        d.polygon([proj(lo, la, zoom, center) for lo, la in poly], fill=fill, outline=outline)


def pin(d, xy, label, a=1.0, color=ACCENT, below=False):
    x, y = xy
    r = 14
    d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    d.ellipse([x - r * 2.2 * a, y - r * 2.2 * a, x + r * 2.2 * a, y + r * 2.2 * a], outline=color, width=3)
    text(d, (x, y + (44 if below else -40)), label, 40, anchor="mm", alpha=a)


def arrow(d, p0, p1, k, color=ACCENT, width=8):
    """p0→p1 を k(0..1) まで描く矢印。"""
    if k <= 0:
        return
    x = p0[0] + (p1[0] - p0[0]) * k; y = p0[1] + (p1[1] - p0[1]) * k
    d.line([p0, (x, y)], fill=color, width=width)
    ang = math.atan2(y - p0[1], x - p0[0])
    s = 26
    d.polygon([(x, y), (x - s * math.cos(ang - .45), y - s * math.sin(ang - .45)),
               (x - s * math.cos(ang + .45), y - s * math.sin(ang + .45))], fill=color)


# ------------------------------------------------------------------ 各グラフィック
def title(main, sub=""):
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        a = prog(t, 0.2, 0.8)
        text(d, (W / 2, H / 2 - 40 - 20 * (1 - a)), main, 120, anchor="mm", alpha=a)
        if sub:
            text(d, (W / 2, H / 2 + 80), sub, 54, SUB, anchor="mm", alpha=prog(t, 0.6))
        d.line([(W / 2 - 300 * a, H / 2 + 20), (W / 2 + 300 * a, H / 2 + 20)], fill=ACCENT, width=4)
        return apply_fade(im, fade(t, dur))
    return f


def big_numbers(items, note=""):
    """items: [(上の小見出し, 大きい数字)] を順に表示し矢印でつなぐ。"""
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        n = len(items)
        for i, (cap, num) in enumerate(items):
            a = prog(t, 0.3 + i * 1.2)
            x = W * (i + 1) / (n + 1) + (i - (n - 1) / 2) * 160
            text(d, (x, H / 2 - 110), cap, 48, SUB, anchor="mm", alpha=a)
            text(d, (x, H / 2 + 10), num, 130, ACCENT if i == n - 1 else FG, anchor="mm", alpha=a)
            if i:
                px = W * i / (n + 1) + (i - 1 - (n - 1) / 2) * 160
                l0 = font(130).getlength(items[i - 1][1]) / 2; l1 = font(130).getlength(num) / 2
                arrow(d, (px + l0 + 30, H / 2 + 10), (x - l1 - 30, H / 2 + 10), prog(t, 0.3 + i * 1.2 - .4), SUB, 6)
        if note:
            text(d, (W / 2, H - 230), note, 34, SUB, anchor="mm", alpha=prog(t, 1.5), bold=False)
        return apply_fade(im, fade(t, dur))
    return f


def spec_card():
    rows = [("正式名", "一円アルミニウム貨"), ("発行開始", "1955年（昭和30年）"), ("素材", "アルミニウム"),
            ("重さ", "1 g"), ("直径", "20 mm")]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        coin_icon(im, 470, H // 2, int(230 * prog(t, 0.1, 0.8)) + 1)
        for i, (k, v) in enumerate(rows):
            a = prog(t, 0.6 + i * 0.9)
            y = 260 + i * 130
            text(d, (860, y), k, 44, SUB, alpha=a)
            text(d, (1130, y - 8), v, 60, alpha=a)
            d.line([(860, y + 80), (860 + 900 * a, y + 80)], fill=(50, 60, 80), width=2)
        return apply_fade(im, fade(t, dur))
    return f


def map_mint():
    def f(t, dur):
        im = canvas(); z = 1.0 + 0.6 * ease(t / max(dur, 1))
        center = (136.0 - 2.0 * ease(t / dur), 37.5 - 2.5 * ease(t / dur))
        draw_japan(im, z, center)
        d = ImageDraw.Draw(im)
        pin(d, proj(*PLACES["大阪"], z, center), "大阪（本局）", prog(t, 0.8))
        pin(d, proj(*PLACES["広島"], z, center), "広島（支局）", prog(t, 1.6), below=True)
        text(d, (80, 80), "造幣局", 64, alpha=prog(t, 0.2))
        text(d, (80, 170), "通常の硬貨は主に大阪と広島でつくられる", 40, SUB, alpha=prog(t, 0.4), bold=False)
        return apply_fade(im, fade(t, dur))
    return f


PROCESS = ["溶解", "圧延", "圧穿", "圧縁・焼鈍", "圧印", "検査", "計数・袋詰め"]


def process_flow(hi):
    """工程フロー。hi 番目(0始まり)までを順に点灯。"""
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        n = len(PROCESS); bw = 220; gap = 40; x0 = (W - (n * bw + (n - 1) * gap)) / 2; y = H / 2 - 70
        text(d, (W / 2, 220), "1円玉ができるまで", 64, anchor="mm", alpha=prog(t, 0.1))
        for i, name in enumerate(PROCESS):
            x = x0 + i * (bw + gap)
            lit = i <= hi and t > 0.4 + i * 0.25
            cur = i == hi
            col = ACCENT if cur else ((70, 86, 110) if lit else (40, 48, 64))
            d.rounded_rectangle([x, y, x + bw, y + 140], 18, fill=col)
            text(d, (x + bw / 2, y + 70), name, 38 if len(name) < 5 else 32, FG if lit else SUB, anchor="mm")
            if i < n - 1:
                d.polygon([(x + bw + 8, y + 60), (x + bw + 30, y + 70), (x + bw + 8, y + 80)], fill=SUB)
        text(d, (W / 2, y + 260), "※ 打ち抜いた直後の模様のない板を「円形（えんけい）」と呼ぶ", 34, SUB, anchor="mm",
             alpha=prog(t, 1.5), bold=False)
        return apply_fade(im, fade(t, dur))
    return f


def node_flow(nodes, title_s, reverse=False, color=ACCENT):
    """横一列のノードを矢印で順につなぐ(造幣局→日銀→銀行→お店 など)。"""
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 200), title_s, 60, anchor="mm", alpha=prog(t, 0.1))
        n = len(nodes)
        xs = [W * (i + 1) / (n + 1) for i in range(n)]
        order = list(range(n))[::-1] if reverse else list(range(n))
        step = max(0.6, (dur - 1.0) / n)
        for j, i in enumerate(order):
            a = prog(t, 0.3 + j * step)
            d.rounded_rectangle([xs[i] - 150, H / 2 - 70, xs[i] + 150, H / 2 + 70], 24,
                                fill=(46, 58, 80) if a > 0 else BG, outline=SUB if a > 0 else BG, width=3)
            text(d, (xs[i], H / 2), nodes[i], 46, anchor="mm", alpha=a, bg=(46, 58, 80))
            if j:
                p = order[j - 1]
                sgn = 1 if i > p else -1
                arrow(d, (xs[p] + sgn * 160, H / 2), (xs[i] - sgn * 165, H / 2), prog(t, 0.3 + j * step - 0.5, 0.5), color)
        # 移動する1円玉
        k = clamp((t - 0.3) / (step * (n - 1) + 0.3))
        pos = k * (n - 1); a_i = int(min(pos, n - 2)); fr = pos - a_i
        i0, i1 = order[a_i], order[a_i + 1]
        cx = xs[i0] + (xs[i1] - xs[i0]) * fr
        coin_icon(im, int(cx), int(H / 2 + 170), 40)
        return apply_fade(im, fade(t, dur))
    return f


def wander():
    """街を転々とする1円玉(店→家→店…)。"""
    spots = [("お店", 360, 360), ("家", 820, 720), ("お店", 1250, 330), ("家", 1600, 760), ("お店", 1000, 480)]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        for x in range(0, W, 160):
            d.line([(x, 0), (x, H)], fill=(30, 38, 54), width=2)
        for y in range(0, H, 160):
            d.line([(0, y), (W, y)], fill=(30, 38, 54), width=2)
        k = clamp(t / (dur - 0.5)) * (len(spots) - 1)
        for i, (name, x, y) in enumerate(spots):
            a = 1.0 if k >= i - 0.2 else 0.25
            d.rounded_rectangle([x - 90, y - 50, x + 90, y + 50], 16, fill=(46, 58, 80))
            text(d, (x, y), name, 42, anchor="mm", alpha=a, bg=(46, 58, 80))
        pts = [(x, y) for _, x, y in spots]
        i = int(min(k, len(pts) - 2)); fr = k - i
        for j in range(i + 1):
            d.line([pts[j], pts[j + 1] if j < i else (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * fr,
                                                      pts[i][1] + (pts[i + 1][1] - pts[i][1]) * fr)], fill=ACCENT, width=6)
        cx = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * fr; cy = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * fr
        coin_icon(im, int(cx), int(cy - 90), 44)
        return apply_fade(im, fade(t, dur))
    return f


def bar_circulation():
    data = [("1円", 364, ACCENT), ("10円", 187, (196, 120, 80))]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "硬貨の流通枚数（2024年12月）", 60, alpha=prog(t, 0.1))
        maxv = 400; x0 = 380; x1 = 1700
        for i, (lab, v, col) in enumerate(data):
            y = 380 + i * 260
            a = prog(t, 0.4 + i * 0.6, 1.2)
            text(d, (x0 - 40, y + 60), lab, 64, anchor="rm", alpha=prog(t, 0.3))
            d.rounded_rectangle([x0, y, x0 + (x1 - x0) * v / maxv * a + 2, y + 120], 14, fill=col)
            text(d, (x0 + (x1 - x0) * v / maxv * a + 30, y + 60), f"{int(v * a)}億枚", 64, anchor="lm", alpha=a)
        text(d, (120, H - 230), "出典：日本銀行「通貨流通高」（野村證券コラムより）", 30, SUB, alpha=prog(t, 1), bold=False)
        return apply_fade(im, fade(t, dur))
    return f


def per_capita():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 230), "日本人 1人あたり", 64, SUB, anchor="mm", alpha=prog(t, 0.1))
        n = int(300 * prog(t, 0.4, max(1.0, dur - 1.5)))
        text(d, (W / 2, 400), f"約 {n} 枚", 150, ACCENT, anchor="mm")
        # 小さな1円玉を並べる(30x10)
        for i in range(min(n, 300)):
            cx = 330 + (i % 30) * 44; cy = 560 + (i // 30) * 44
            d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=SILVER)
        text(d, (W / 2, H - 230), "364億枚 ÷ 約1.24億人", 32, SUB, anchor="mm", bold=False, alpha=prog(t, 1))
        return apply_fade(im, fade(t, dur))
    return f


def vending_diagram():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 90), "自販機に1円玉が使えない理由（メーカー担当者の説明）", 50, anchor="mm", alpha=prog(t, 0.1))
        k = prog(t, dur * 0.45, 1.5)   # 1円用の筒が増える
        for side, (ox, ttl) in enumerate([(300, "いま"), (1100, "1円も使えるようにすると")]):
            text(d, (ox + 260, 185), ttl, 44, SUB, anchor="mm", alpha=prog(t, 0.3 + side * dur * 0.4))
            if side == 1 and t < dur * 0.4:
                continue
            d.rounded_rectangle([ox, 230, ox + 520, 830], 20, outline=SUB, width=4)
            tubes = [("500", 60), ("100", 60), ("50", 50), ("10", 50)]
            if side == 1:
                tubes += [("1", 50)]
            x = ox + 30
            for lab, w in tubes:
                grow = k if (side == 1 and lab == "1") else 1
                ww = w * grow
                d.rectangle([x, 580, x + ww, 810], fill=ACCENT if lab == "1" else (90, 104, 130))
                if grow > 0.5:
                    text(d, (x + ww / 2, 560), lab, 30, anchor="mm")
                x += ww + 12
            # 商品スペース(1円筒が増えると狭くなる)
            shrink = (62 * k) if side == 1 else 0
            d.rectangle([ox + 30, 260, ox + 490 - shrink, 520], fill=(50, 120, 90))
            text(d, (ox + 260 - shrink / 2, 390), "商品", 60, anchor="mm", bg=(50, 120, 90))
            text(d, (ox + 260, 860), "釣り銭ストッカー", 30, SUB, anchor="mm", bold=False)
        return apply_fade(im, fade(t, dur))
    return f


def rumor():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        a = prog(t, 0.2)
        text(d, (W / 2, 260), "よく聞く噂", 54, SUB, anchor="mm", alpha=a)
        text(d, (W / 2, 420), "1円玉を作るのに", 90, anchor="mm", alpha=prog(t, 0.6))
        s = 1 + 0.15 * math.sin(clamp(t - 1.2) * math.pi)
        text(d, (W / 2, 620), "3円？", int(200 * s), ACCENT, anchor="mm", alpha=prog(t, 1.2))
        return apply_fade(im, fade(t, dur))
    return f


def cost():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 130), "1円玉1枚の製造コスト", 64, anchor="mm", alpha=prog(t, 0.1))
        text(d, (W / 2, 220), "国は「偽造を助長するおそれ」があるとして非公表", 42, RED, anchor="mm", alpha=prog(t, 0.6))
        k = prog(t, dur * 0.4, 1.5)
        x0, x1, y = 300, 1620, 480
        tot = 3.1
        mat_w = (x1 - x0) * 0.3 / tot
        d.rectangle([x0, y, x0 + mat_w * k, y + 160], fill=SILVER)
        d.rectangle([x0 + mat_w, y, x0 + mat_w + (x1 - x0 - mat_w) * clamp(k * 1.2 - 0.2), y + 160], fill=ACCENT)
        text(d, (x0 + mat_w / 2, y + 220), "材料 約0.3円", 40, anchor="mm", alpha=k)
        text(d, (x0 + mat_w + (x1 - x0 - mat_w) / 2, y + 80), "人件費・設備など", 46, anchor="mm", alpha=clamp(k * 1.2 - 0.2), bg=ACCENT)
        text(d, (x1, y - 40), "合計 約3.1円（試算）", 50, anchor="rm", alpha=prog(t, dur * 0.4 + 1.5))
        d.line([(x0 + (x1 - x0) / tot, y - 20), (x0 + (x1 - x0) / tot, y + 180)], fill=FG, width=3)
        text(d, (x0 + (x1 - x0) / tot, y + 220), "額面 1円", 36, anchor="mm", alpha=k)
        text(d, (W / 2, H - 230), "※ 民間試算（三菱UFJ信託銀行・2018年頃）。公式の数字ではありません", 32, SUB, anchor="mm",
             bold=False, alpha=prog(t, 1))
        return apply_fade(im, fade(t, dur))
    return f


def production_chart():
    """製造枚数の推移(対数目盛)。主要年のみ。"""
    pts = [(1990, 27e8), (1997, 7.83e8), (2013, 5.54e5), (2014, 1.24e8), (2016, 5e5), (2025, 5e5)]
    labels = {1990: "約27億枚", 1997: "約7.8億枚", 2013: "約55万枚", 2014: "約1.24億枚\n消費税8%"}

    def X(yr): return 260 + (yr - 1988) / (2028 - 1988) * 1460
    def Y(v): return 790 - (math.log10(v) - 5) / (10 - 5) * 620

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 70), "1円玉の製造枚数（年・年度）", 56, alpha=prog(t, 0.1))
        for e, lab in ((5, "10万"), (6, "100万"), (7, "1000万"), (8, "1億"), (9, "10億"), (10, "100億")):
            y = Y(10 ** e); d.line([(260, y), (1720, y)], fill=(40, 50, 68), width=2)
            text(d, (240, y), lab, 28, SUB, anchor="rm", bold=False)
        for yr in (1990, 2000, 2010, 2020):
            text(d, (X(yr), 815), str(yr), 30, SUB, anchor="mt", bold=False)
        k = clamp((t - 0.6) / max(1.0, dur - 3.0)) * (len(pts) - 1)
        for i in range(len(pts) - 1):
            if k <= i:
                break
            fr = clamp(k - i)
            (x0, v0), (x1, v1) = pts[i], pts[i + 1]
            p0 = (X(x0), Y(v0))
            p1 = (X(x0 + (x1 - x0) * fr), Y(10 ** (math.log10(v0) + (math.log10(v1) - math.log10(v0)) * fr)))
            d.line([p0, p1], fill=ACCENT, width=7)
        for i, (yr, v) in enumerate(pts):
            if k >= i:
                x, y = X(yr), Y(v)
                d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=ACCENT)
                if yr in labels:
                    d.multiline_text((x + 22, y - 70 if yr != 2013 else y + 10), labels[yr], font=font(36), fill=FG, spacing=4)
        if k >= len(pts) - 1.2:
            d.rectangle([X(2016), Y(5e5) - 40, X(2025), Y(5e5) + 40], outline=BLUE, width=3)
            text(d, ((X(2016) + X(2025)) / 2, Y(5e5) + 80), "販売用の貨幣セット分のみ", 32, BLUE, anchor="mm")
        if t > dur - 2.2:
            x = X(2026); d.line([(x, 150), (x, 790)], fill=RED, width=4)
            text(d, (x - 10, 175), "2026年 量産再開", 40, RED, anchor="rm")
        text(d, (1800, 70), "主要年のみ・対数目盛。出典：造幣局資料を引用した各報道", 26, SUB, anchor="ra", bold=False)
        return apply_fade(im, fade(t, dur))
    return f


def quote_post():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        a = prog(t, 0.2)
        d.rounded_rectangle([260, 260, 1660, 820], 30, fill=(30, 38, 54), outline=(70, 84, 110), width=3)
        text(d, (320, 320), "造幣局 公式アカウント（2026年7月14日）", 40, SUB, alpha=a, bg=(30, 38, 54))
        s = "「現在、平成27年度以来11年ぶりに、\n　1円の量産を行っています」"
        n = int(len(s) * prog(t, 1.0, max(1.0, dur - 2)))
        d.multiline_text((320, 450), s[:n], font=font(66), fill=FG, spacing=24)
        text(d, (W / 2, 860), "※ 投稿文面を引用", 30, SUB, anchor="mm", bold=False, alpha=prog(t, 1))
        return apply_fade(im, fade(t, dur))
    return f


def law_20():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 200), "同じ硬貨が使えるのは 一度に20枚まで", 70, anchor="mm", alpha=prog(t, 0.1))
        n = int(26 * prog(t, 0.5, max(1.0, dur - 1.5)))
        for i in range(n):
            cx = 330 + (i % 13) * 105; cy = 470 + (i // 13) * 170
            coin_icon(im, cx, cy, 44)
            if i >= 20:
                d.line([(cx - 50, cy - 50), (cx + 50, cy + 50)], fill=RED, width=10)
                d.line([(cx + 50, cy - 50), (cx - 50, cy + 50)], fill=RED, width=10)
        text(d, (W / 2, H - 230), "通貨の単位及び貨幣の発行等に関する法律 第7条（額面の20倍まで）", 34, SUB, anchor="mm",
             bold=False, alpha=prog(t, 1))
        return apply_fade(im, fade(t, dur))
    return f


def loop():
    steps = ["誕生", "旅", "回収", "溶解"]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        cx, cy, R = W / 2, H / 2, 330
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(60, 72, 96), width=6)
        ang = -math.pi / 2 + t / dur * math.tau * 1.0
        d.arc([cx - R, cy - R, cx + R, cy + R], -90, math.degrees(ang), fill=ACCENT, width=10)
        for i, s in enumerate(steps):
            a = -math.pi / 2 + i * math.tau / 4
            x, y = cx + R * math.cos(a), cy + R * math.sin(a)
            d.ellipse([x - 95, y - 95, x + 95, y + 95], fill=(46, 58, 80))
            text(d, (x, y), s, 50, anchor="mm", bg=(46, 58, 80))
        coin_icon(im, int(cx + R * math.cos(ang)), int(cy + R * math.sin(ang)), 40)
        return apply_fade(im, fade(t, dur))
    return f


def law_damage():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 260), "貨幣損傷等取締法", 80, anchor="mm", alpha=prog(t, 0.1))
        text(d, (W / 2, 430), "硬貨を溶かす・傷つける・穴を開ける → 禁止", 56, anchor="mm", alpha=prog(t, 0.7))
        text(d, (W / 2, 600), "1年以下の拘禁刑 または 20万円以下の罰金", 64, RED, anchor="mm", alpha=prog(t, 1.4))
        text(d, (W / 2, 820), "1円玉の一生を終わらせられるのは、国だけ", 54, ACCENT, anchor="mm", alpha=prog(t, dur * 0.55))
        return apply_fade(im, fade(t, dur))
    return f


def next_card():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 380), "次回", 60, SUB, anchor="mm", alpha=prog(t, 0.1))
        text(d, (W / 2, 520), "なくした傘はどこへ行く？", 110, anchor="mm", alpha=prog(t, 0.4))
        text(d, (W / 2, 720), "モノの一生 #2", 50, ACCENT, anchor="mm", alpha=prog(t, 0.9))
        return apply_fade(im, fade(t, dur, tout=1.0))
    return f


def placeholder(name):
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, H / 2), f"[3D {name} 制作中]", 70, SUB, anchor="mm")
        return im
    return f


REGISTRY = {
    "title": lambda: title("1円玉の一生", "モノの一生 #1"),
    "counter": lambda: big_numbers([("1990年", "27億枚"), ("2016年〜", "100万枚以下")],
                                   "1円玉の年間製造枚数（造幣局資料を引用した報道より）"),
    "spec": spec_card, "map_mint": map_mint,
    "flow_edge": lambda: process_flow(3),
    "route": lambda: node_flow(["造幣局", "日本銀行", "銀行", "お店"], "1円玉の旅のはじまり"),
    "wander": wander, "bar": bar_circulation, "per_capita": per_capita, "vending": vending_diagram,
    "rumor": rumor, "cost": cost, "chart": production_chart, "quote": quote_post, "law20": law_20,
    "return": lambda: node_flow(["造幣局", "日本銀行", "銀行", "お店"], "最期の旅：回収", reverse=True, color=BLUE),
    "loop": loop, "law_damage": law_damage, "next": next_card,
}
