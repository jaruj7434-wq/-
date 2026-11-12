"""第2話「なくした傘はどこへ行く？」の2D図解。

第1話の graphics2d.py の部品(canvas/text/prog/fade/arrow…)を流用する。
数字は prompts/mono_no_issho/plan.md の「第2話リサーチ」に基づく。
"""
import math
from PIL import ImageDraw

from graphics2d import (W, H, BG, FG, SUB, SILVER, ACCENT, BLUE, RED, canvas, text, prog, fade,
                        apply_fade, arrow, clamp, ease, title, font)

TEAL = (80, 200, 190)
CARD = (46, 58, 80)


def umbrella_icon(d, cx, cy, s, col=SILVER, a=1.0):
    """シンプルな傘アイコン(開いた状態)。s = 半径。"""
    if a <= 0:
        return
    c = tuple(int(BG[i] + (col[i] - BG[i]) * a) for i in range(3))
    d.pieslice([cx - s, cy - s * 0.8, cx + s, cy + s * 0.8], 180, 360, fill=c)
    # 生地の波(下端のスカラップ)
    n = 4
    for i in range(n):
        x0 = cx - s + 2 * s * i / n
        d.ellipse([x0, cy - s * 0.12, x0 + 2 * s / n, cy + s * 0.12], fill=BG)
    d.line([(cx, cy - s * 0.85), (cx, cy + s * 0.75)], fill=c, width=max(3, int(s * 0.07)))
    d.arc([cx - s * 0.28, cy + s * 0.55, cx + 0.02 * s, cy + s * 0.95], 0, 180, fill=c, width=max(3, int(s * 0.07)))


def footnote(d, t, s, at=1.0):
    text(d, (120, H - 230), s, 30, SUB, alpha=prog(t, at), bold=False)


def counter_tokyo():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 260), "東京で落とし物として警察に届いた傘", 56, SUB, anchor="mm", alpha=prog(t, 0.1))
        n = int(280763 * prog(t, 0.4, max(1.0, dur * 0.5)))
        text(d, (W / 2, 470), f"{n:,} 本", 170, ACCENT, anchor="mm", alpha=prog(t, 0.3))
        text(d, (W / 2, 620), "1年間（2022年）", 50, FG, anchor="mm", alpha=prog(t, 0.8))
        k = prog(t, 0.6, 2.5)
        for i in range(int(28 * k)):
            umbrella_icon(d, 330 + i * 46, 730, 18, SILVER, 0.9)
        footnote(d, t, "出典：警視庁「遺失物取扱状況」（nippon.com まとめ）", 1.2)
        return apply_fade(im, fade(t, dur))
    return f


def consumption():
    data = [("傘 全体", 1.25, SILVER, "約1.2〜1.3億本"), ("うち ビニール傘", 0.8, BLUE, "約8,000万本")]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "日本で1年間に使われる傘", 60, alpha=prog(t, 0.1))
        x0, x1, maxv = 560, 1560, 1.4
        for i, (lab, v, col, s) in enumerate(data):
            y = 360 + i * 240
            a = prog(t, 0.4 + i * 0.8, 1.2)
            text(d, (x0 - 40, y + 60), lab, 56, anchor="rm", alpha=prog(t, 0.3 + i * 0.8))
            d.rounded_rectangle([x0, y, x0 + (x1 - x0) * v / maxv * a + 2, y + 120], 14, fill=col)
            text(d, (x0 + (x1 - x0) * v / maxv * a + 30, y + 60), s, 54, anchor="lm", alpha=a)
        footnote(d, t, "※業界推計（Business Insider Japan の報道より）。正確な統計ではありません", 1.6)
        return apply_fade(im, fade(t, dur))
    return f


def history():
    items = [("1950年代", "東京で誕生", SILVER), ("1964年", "東京五輪 → NYで人気", BLUE),
             ("1980年代〜", "安い輸入品が主流に", ACCENT), ("いま", "「使い捨て」のイメージ", RED)]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "ビニール傘は日本生まれ", 60, alpha=prog(t, 0.1))
        x0, x1, y = 240, 1680, 560
        d.line([(x0, y), (x0 + (x1 - x0) * prog(t, 0.2, dur * 0.6), y)], fill=SUB, width=5)
        step = max(1.0, (dur - 1.5) / len(items))
        for i, (yr, s, col) in enumerate(items):
            x = x0 + (x1 - x0) * i / (len(items) - 1)
            a = prog(t, 0.3 + i * step)
            if a > 0:
                d.ellipse([x - 18, y - 18, x + 18, y + 18], fill=col)
            text(d, (x, y - 90), yr, 50, col, anchor="mm", alpha=a)
            text(d, (x, y + 90), s, 40, FG, anchor="mm", alpha=a)
        umbrella_icon(d, W / 2, 330, 70, SILVER, prog(t, 0.2))
        footnote(d, t, "※誕生年は資料により1955年・1958年とされる（nippon.com、和楽web ほか）", 1.5)
        return apply_fade(im, fade(t, dur))
    return f


def return_rate():
    data = [("忘れ物 全体", 0.30, SILVER, "約3割", "鉄道会社"), ("傘", 0.10, ACCENT, "約1割", "鉄道会社"),
            ("警察に届いた傘", 0.01, RED, "約1%", "報道")]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "持ち主のもとに戻る割合", 60, alpha=prog(t, 0.1))
        step = max(1.0, (dur - 2.0) / 3)
        for i, (lab, v, col, s, src) in enumerate(data):
            cx = 420 + i * 540; cy = 540; r = 170
            a = prog(t, 0.4 + i * step, 1.4)
            text(d, (cx, 290), lab, 50, anchor="mm", alpha=prog(t, 0.3 + i * step))
            text(d, (cx, cy + r + 50), f"（{src}）", 32, SUB, anchor="mm", alpha=prog(t, 0.3 + i * step), bold=False)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=CARD)
            if a > 0:
                d.pieslice([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * v * a, fill=col)
            d.ellipse([cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62], fill=BG)
            text(d, (cx, cy), s, 70, col, anchor="mm", alpha=a)
        footnote(d, t, "出典：JR東日本 プレスリリース（2019年、2017年度の状況）／週刊女性PRIME（警察に届いた傘）", 1.6)
        return apply_fade(im, fade(t, dur))
    return f


def storage_rule():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "落とし物の保管期間", 60, alpha=prog(t, 0.1))
        x0, x1 = 520, 1700
        days = 90
        rows = [("ふつうの落とし物", 90, SILVER, "3か月"),
                ("傘など\n安くて大量の物", 14, ACCENT, "2週間で売却・処分できる")]
        for i, (lab, v, col, s) in enumerate(rows):
            y = 340 + i * 260
            a = prog(t, 0.5 + i * 1.6, 1.4)
            for j, line in enumerate(lab.split("\n")):
                text(d, (x0 - 40, y + 30 + j * 56 - (len(lab.split("\n")) - 1) * 28), line, 50, anchor="rm",
                     alpha=prog(t, 0.4 + i * 1.6))
            d.rounded_rectangle([x0, y, x1, y + 100], 14, outline=(70, 84, 110), width=3)
            d.rounded_rectangle([x0, y, x0 + (x1 - x0) * v / days * a + 2, y + 100], 14, fill=col)
            text(d, (x0 + (x1 - x0) * v / days * a + 24 if v < 60 else x0 + 30, y + 50), s, 46,
                 FG if v < 60 else BG, anchor="lm", alpha=a, bg=BG if v < 60 else col)
        # 目盛り
        for m, lab in ((0, "拾った日"), (14, "2週間"), (30, "1か月"), (90, "3か月")):
            x = x0 + (x1 - x0) * m / days
            d.line([(x, 720), (x, 740)], fill=SUB, width=3)
            text(d, (x, 772), lab, 30, SUB, anchor="mm", alpha=prog(t, 0.3), bold=False)
        footnote(d, t, "遺失物法（特例施設占有者：一定の公共交通機関など）。各都道府県警察の案内より", 2.5)
        return apply_fade(im, fade(t, dur))
    return f


def fate_flow():
    """駅で保管 → 売却 / 廃棄 → 再利用 / 金属回収・焼却 の分岐図。"""
    def box(d, cx, cy, s, a, col=CARD, w=300):
        if a <= 0:
            return
        d.rounded_rectangle([cx - w / 2, cy - 62, cx + w / 2, cy + 62], 22, fill=col, outline=SUB, width=3)
        text(d, (cx, cy), s, 42, anchor="mm", alpha=a, bg=col)

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 140), "持ち主が見つからなかった傘のゆくえ", 60, anchor="mm", alpha=prog(t, 0.1))
        step = max(0.8, (dur - 1.5) / 4)
        A = (330, 520); B1 = (900, 360); B2 = (900, 680); C1 = (1520, 360); C2 = (1520, 680)
        box(d, *A, "駅で保管", prog(t, 0.3))
        for p, q, k, col in ((A, B1, 1, ACCENT), (A, B2, 1, SUB), (B1, C1, 2, TEAL), (B2, C2, 2, SUB)):
            arrow(d, (p[0] + 160, p[1]), (q[0] - 165, q[1]), prog(t, 0.3 + k * step - 0.5, 0.5), col, 7)
        box(d, *B1, "業者に売却", prog(t, 0.3 + step))
        box(d, *B2, "廃棄", prog(t, 0.3 + step))
        box(d, *C1, "中古・再販売", prog(t, 0.3 + 2 * step), w=320)
        box(d, *C2, "分別して処理", prog(t, 0.3 + 2 * step), w=320)
        umbrella_icon(d, A[0], A[1] - 150, 50, SILVER, prog(t, 0.3))
        footnote(d, t, "※扱いは施設・自治体によって異なります", 1.5)
        return apply_fade(im, fade(t, dur))
    return f


def materials():
    rows = [("骨・軸", "金属（鉄・アルミなど）", "回収されることも", TEAL),
            ("生地", "プラスチック・布", "燃やされることが多い", RED),
            ("持ち手", "プラスチック・木", "燃やされることが多い", RED)]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "傘は「素材のかたまり」", 60, alpha=prog(t, 0.1))
        for i, (part, mat, fate_s, col) in enumerate(rows):
            y = 330 + i * 170
            a = prog(t, 0.5 + i * 0.9, 0.8)
            d.rounded_rectangle([120, y - 60, 1800, y + 60], 20, fill=CARD if a > 0 else BG)
            text(d, (170, y), part, 50, anchor="lm", alpha=a, bg=CARD)
            text(d, (480, y), mat, 46, SUB, anchor="lm", alpha=a, bg=CARD)
            text(d, (1760, y), fate_s, 46, col, anchor="rm", alpha=prog(t, 0.9 + i * 0.9, 0.8), bg=CARD)
        footnote(d, t, "素材が混ざっていて分別しにくい（Business Insider Japan の報道より）", 3.0)
        return apply_fade(im, fade(t, dur))
    return f


def title_card(main, sub):
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        a = prog(t, 0.2, 0.8)
        text(d, (W / 2, H / 2 - 60 - 20 * (1 - a)), main, 110, anchor="mm", alpha=a)
        d.line([(W / 2 - 360 * a, H / 2 + 30), (W / 2 + 360 * a, H / 2 + 30)], fill=ACCENT, width=4)
        text(d, (W / 2, H / 2 + 100), sub, 54, SUB, anchor="mm", alpha=prog(t, 0.6))
        return apply_fade(im, fade(t, dur))
    return f


def next_card():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 380), "次回", 60, SUB, anchor="mm", alpha=prog(t, 0.1))
        text(d, (W / 2, 520), "ペットボトルは何に生まれ変わる？", 100, anchor="mm", alpha=prog(t, 0.4))
        text(d, (W / 2, 720), "モノの一生 #3", 50, ACCENT, anchor="mm", alpha=prog(t, 0.9))
        return apply_fade(im, fade(t, dur, tout=1.0))
    return f


REGISTRY = {
    "title": lambda: title_card("なくした傘はどこへ行く？", "モノの一生 #2"),
    "counter": counter_tokyo,
    "consumption": consumption,
    "history": history,
    "return_rate": return_rate,
    "storage_rule": storage_rule,
    "fate_flow": fate_flow,
    "materials": materials,
    "next": next_card,
}
