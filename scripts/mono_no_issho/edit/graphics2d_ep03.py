"""第3話「ペットボトルは何に生まれ変わる？」の2D図解。

第1話の graphics2d.py の部品を流用する。
数字は prompts/mono_no_issho/plan.md の「第3話リサーチ」に基づく。
"""
from PIL import ImageDraw

from graphics2d import (W, H, BG, FG, SUB, SILVER, ACCENT, BLUE, RED, canvas, text, prog, fade,
                        apply_fade, arrow, ease)
from graphics2d_ep02 import TEAL, CARD, footnote, title_card

CLEAR = (170, 215, 235)   # ペットボトルの色


def bottle_icon(d, cx, cy, s, col=CLEAR, a=1.0):
    """シンプルなペットボトル。s = 高さの半分。"""
    if a <= 0:
        return
    c = tuple(int(BG[i] + (col[i] - BG[i]) * a) for i in range(3))
    w = s * 0.42
    d.rounded_rectangle([cx - w, cy - s * 0.45, cx + w, cy + s], int(w * 0.5), fill=c)
    d.polygon([(cx - w, cy - s * 0.35), (cx - w * 0.45, cy - s * 0.78), (cx + w * 0.45, cy - s * 0.78),
               (cx + w, cy - s * 0.35)], fill=c)
    d.rectangle([cx - w * 0.42, cy - s, cx + w * 0.42, cy - s * 0.78], fill=tuple(int(v * 0.8) for v in c))
    d.rectangle([cx - w, cy - s * 0.05, cx + w, cy + s * 0.35], fill=tuple(int(BG[i] + (BLUE[i] - BG[i]) * a * 0.8)
                                                                            for i in range(3)))


def quiz():
    opts = [("A", "またペットボトル", CLEAR), ("B", "お弁当のフタ・トレー", ACCENT), ("C", "シャツ（服）", TEAL)]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 170), "この1本、次は何になる？", 76, anchor="mm", alpha=prog(t, 0.1))
        step = max(0.6, (dur - 2.0) / 4)
        for i, (k, s, col) in enumerate(opts):
            y = 380 + i * 170
            a = prog(t, 0.4 + i * step, 0.5)
            if a <= 0:
                continue
            x = 360 + 60 * (1 - ease(a))
            d.rounded_rectangle([x, y - 62, x + 1200, y + 62], 24, fill=CARD)
            d.ellipse([x + 26, y - 44, x + 114, y + 44], fill=col)
            text(d, (x + 70, y), k, 52, BG, anchor="mm", alpha=a, bg=col)
            text(d, (x + 160, y), s, 58, anchor="lm", alpha=a, bg=CARD)
        a = prog(t, 0.4 + 3 * step, 0.5)
        if a > 0:
            text(d, (W / 2, 920), "答え：ぜんぶ正解", 70, ACCENT, anchor="mm", alpha=a)
        return apply_fade(im, fade(t, dur))
    return f


def history():
    items = [("1977年", "醤油の容器で初登場", SILVER), ("1982年", "清涼飲料もOKに\n（小型は自主規制）", BLUE),
             ("1996年", "自主規制なくなる\n500mlが一気に普及", ACCENT)]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "日本のペットボトルの歩み", 60, alpha=prog(t, 0.1))
        x0, x1, y = 340, 1580, 560
        d.line([(x0, y), (x0 + (x1 - x0) * prog(t, 0.2, dur * 0.6), y)], fill=SUB, width=5)
        step = max(1.0, (dur - 1.5) / len(items))
        for i, (yr, s, col) in enumerate(items):
            x = x0 + (x1 - x0) * i / (len(items) - 1)
            a = prog(t, 0.3 + i * step)
            if a > 0:
                d.ellipse([x - 18, y - 18, x + 18, y + 18], fill=col)
            text(d, (x, y - 90), yr, 56, col, anchor="mm", alpha=a)
            for j, line in enumerate(s.split("\n")):
                text(d, (x, y + 90 + j * 56), line, 42, FG, anchor="mm", alpha=a)
            bottle_icon(d, x, y - 220, 60 + 15 * i, CLEAR, a)
        footnote(d, t, "出典：キッコーマン ニュースリリース／nippon.com（全国清涼飲料連合会 資料より）", 1.5)
        return apply_fade(im, fade(t, dur))
    return f


def amount():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 230), "日本で1年間に売られるペットボトル", 56, SUB, anchor="mm", alpha=prog(t, 0.1))
        n = int(65.2 * prog(t, 0.4, max(1.0, dur * 0.4)) * 10) / 10
        text(d, (W / 2, 420), f"約{n:.1f}万トン", 160, ACCENT, anchor="mm", alpha=prog(t, 0.3))
        text(d, (W / 2, 560), "（2024年度）", 46, FG, anchor="mm", alpha=prog(t, 0.6))
        a = prog(t, dur * 0.5, 0.6)
        text(d, (W / 2, 680), "本数にすると 年 200億本以上", 64, FG, anchor="mm", alpha=a)
        k = prog(t, 0.6, 2.5)
        for i in range(int(30 * k)):
            bottle_icon(d, 300 + i * 45, 790, 30, CLEAR, 0.9)
        footnote(d, t, "出典：PETボトルリサイクル推進協議会 年次報告書2025（販売量）／本数は2017年度 約227億本（同協議会）", 1.2)
        return apply_fade(im, fade(t, dur))
    return f


def lightweight():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "ボトルはどんどん軽く", 60, alpha=prog(t, 0.1))
        a = prog(t, 0.6, 1.6)
        bottle_icon(d, 620, 500, 230, SILVER, prog(t, 0.3))
        text(d, (620, 790), "基準の年", 46, SUB, anchor="mm", alpha=prog(t, 0.3))
        s = 230 * (1 - 0.281 * a) ** 0.5
        bottle_icon(d, 1300, 500 + (230 - s), s, CLEAR, prog(t, 0.6))
        text(d, (1300, 790), "いま", 46, SUB, anchor="mm", alpha=prog(t, 0.6))
        text(d, (1640, 420), f"−{28.1 * a:.1f}%", 96, ACCENT, anchor="mm", alpha=prog(t, 0.8))
        text(d, (1640, 520), "プラスチック量", 40, FG, anchor="mm", alpha=prog(t, 1.0))
        footnote(d, t, "軽量化率 28.1%（2024年度、指定PETボトル）。出典：PETボトルリサイクル推進協議会 年次報告書2025", 1.2)
        return apply_fade(im, fade(t, dur))
    return f


def rb_trash():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "自販機横のリサイクルボックスの中身", 60, alpha=prog(t, 0.1))
        cx, cy, r = 640, 560, 260
        a = prog(t, 0.6, 1.6)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=CLEAR)
        if a > 0:
            d.pieslice([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * 0.3 * a, fill=RED)
        d.ellipse([cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6], fill=BG)
        text(d, (cx, cy), "約3割", 96, RED, anchor="mm", alpha=a)
        rows = [("空き容器", CLEAR), ("それ以外のごみ（異物）", RED)]
        for i, (s, col) in enumerate(rows):
            y = 440 + i * 120
            aa = prog(t, 0.8 + i * 0.6)
            if aa > 0:
                d.rounded_rectangle([1060, y - 26, 1112, y + 26], 8, fill=col)
            text(d, (1140, y), s, 50, anchor="lm", alpha=aa)
        text(d, (1060, 720), "カップ・食べ残し・たばこ など", 40, SUB, anchor="lm", alpha=prog(t, 1.8), bold=False)
        footnote(d, t, "全国清涼飲料連合会の調査（平成30年、福岡市資料より）。大阪府の2022年度実証では平均26.6%", 1.2)
        return apply_fade(im, fade(t, dur))
    return f


def process():
    nodes = [("ボトル", CLEAR), ("ベール\n（圧縮）", SILVER), ("フレーク\n（粉砕・洗浄）", BLUE), ("ペレット\n（溶かして粒に）", ACCENT)]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 130), "ペットボトルが材料に戻るまで", 60, anchor="mm", alpha=prog(t, 0.1))
        step = max(0.7, (dur - 2.5) / 5)
        xs = [250, 710, 1170, 1630]
        y = 480
        for i, (s, col) in enumerate(nodes):
            a = prog(t, 0.3 + i * step)
            if a > 0:
                d.rounded_rectangle([xs[i] - 180, y - 110, xs[i] + 180, y + 110], 26, fill=CARD, outline=col, width=5)
            lines = s.split("\n")
            for j, line in enumerate(lines):
                text(d, (xs[i], y - (len(lines) - 1) * 32 + j * 64), line, 52 if j == 0 else 36,
                     col if j == 0 else SUB, anchor="mm", alpha=a, bg=CARD)
            if i:
                arrow(d, (xs[i - 1] + 190, y), (xs[i] - 190, y), prog(t, 0.3 + i * step - 0.4, 0.4), SUB, 7)
        # ケミカルリサイクル(別ルート)
        a = prog(t, 0.3 + 4.2 * step)
        if a > 0:
            d.rounded_rectangle([520, 740, 1400, 860], 26, fill=CARD, outline=TEAL, width=4)
        text(d, (960, 800), "化学的に分解して、原料まで戻す方法も", 44, TEAL, anchor="mm", alpha=a, bg=CARD)
        footnote(d, t, "メカニカル（マテリアル）リサイクルとケミカルリサイクル。容器包装リサイクル協会・プラスチック循環利用協会の資料より", 1.5)
        return apply_fade(im, fade(t, dur))
    return f


def uses():
    data = [("ボトル", 57.7, CLEAR), ("シート（卵パック・トレーなど）", 25.5, ACCENT), ("成形品", 6.8, BLUE),
            ("繊維・その他", 10.0, TEAL)]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "国内で生まれ変わる先（2024年度）", 60, alpha=prog(t, 0.1))
        x0, x1, y0, y1 = 160, 1760, 300, 420
        x = x0
        step = max(0.6, (dur - 2.0) / len(data))
        for i, (s, v, col) in enumerate(data):
            a = prog(t, 0.4 + i * step, 0.8)
            w = (x1 - x0) * v / 100
            if a > 0:
                d.rectangle([x, y0, x + w * a, y1], fill=col)
            ly = 500 + i * 80
            if a > 0:
                d.rounded_rectangle([x0, ly - 24, x0 + 48, ly + 24], 8, fill=col)
            text(d, (x0 + 80, ly), s, 48, anchor="lm", alpha=a)
            text(d, (1100, ly), f"{v:.1f}%" if i < 3 else f"約{v:.0f}%", 52, col, anchor="lm", alpha=a)
            x += w
        footnote(d, t, "再生PET樹脂の国内用途（重量）。出典：PETボトルリサイクル推進協議会 年次報告書2025 ※繊維の内訳は要確認", 1.2)
        return apply_fade(im, fade(t, dur))
    return f


def rates(both=False):
    """both=False: リサイクル率だけ。True: リサイクル率は表示済みで、ボトルtoボトルと目標を出す。"""
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 140), "ペットボトルのリサイクル（2024年度）", 60, anchor="mm", alpha=prog(t, 0.1))
        items = [("リサイクル率", 85.1, TEAL, -9 if both else 0.4)]
        if both:
            items.append(("ボトル → ボトル", 37.7, ACCENT, 0.5))
        for i, (lab, v, col, at) in enumerate(items):
            cx, cy, r = (460 + i * 620 if both else W / 2), 520, 220
            a = prog(t, at, 1.4)
            text(d, (cx, 270), lab, 54, anchor="mm", alpha=prog(t, at - 0.2))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=CARD)
            if a > 0:
                d.pieslice([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * v / 100 * a, fill=col)
            d.ellipse([cx - r * 0.64, cy - r * 0.64, cx + r * 0.64, cy + r * 0.64], fill=BG)
            text(d, (cx, cy), f"{v * a:.1f}%", 80, col, anchor="mm", alpha=a)
        a = prog(t, dur * 0.55, 0.8) if both else 0
        if a > 0:
            d.rounded_rectangle([1420, 400, 1780, 640], 30, fill=CARD, outline=ACCENT, width=4)
        text(d, (1600, 470), "2030年度 目標", 44, FG, anchor="mm", alpha=a, bg=CARD)
        text(d, (1600, 570), "50%", 96, ACCENT, anchor="mm", alpha=a, bg=CARD)
        if a > 0:
            arrow(d, (1310, 520), (1410, 520), a, ACCENT, 7)
        footnote(d, t, "出典：PETボトルリサイクル推進協議会 年次報告書2025／目標は清涼飲料業界（日本食糧新聞の報道より）", 1.2)
        return apply_fade(im, fade(t, dur))
    return f


def next_card():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 380), "次回", 60, SUB, anchor="mm", alpha=prog(t, 0.1))
        text(d, (W / 2, 520), "着なくなった服はどこへ行く？", 100, anchor="mm", alpha=prog(t, 0.4))
        text(d, (W / 2, 720), "モノの一生 #4", 50, ACCENT, anchor="mm", alpha=prog(t, 0.9))
        return apply_fade(im, fade(t, dur, tout=1.0))
    return f


REGISTRY = {
    "title": lambda: title_card("ペットボトルは何に生まれ変わる？", "モノの一生 #3"),
    "quiz": quiz,
    "history": history,
    "amount": amount,
    "lightweight": lightweight,
    "rb_trash": rb_trash,
    "process": process,
    "uses": uses,
    "rates": rates,
    "rates_b2b": lambda: rates(True),
    "next": next_card,
}
