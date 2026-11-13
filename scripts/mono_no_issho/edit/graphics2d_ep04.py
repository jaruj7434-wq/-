"""第4話「着なくなった服はどこへ行く？」の2D図解。

第1〜3話の graphics2d*.py の部品を流用する。
数字は prompts/mono_no_issho/plan.md の「第4話リサーチ」に基づく。
"""
from PIL import ImageDraw

from graphics2d import (W, H, BG, FG, SUB, SILVER, ACCENT, BLUE, RED, canvas, text, prog, fade,
                        apply_fade, arrow, ease)
from graphics2d_ep02 import TEAL, CARD, footnote, title_card

PINK = (235, 150, 170)
CLOTH = [BLUE, ACCENT, TEAL, PINK, SILVER]   # 服アイコンの色を順に回す
WATER = (110, 180, 230)


def mix(col, a):
    return tuple(int(BG[i] + (col[i] - BG[i]) * a) for i in range(3))


def shirt_icon(d, cx, cy, s, col=BLUE, a=1.0):
    """シンプルなTシャツ。s = 幅の半分。"""
    if a <= 0:
        return
    c = mix(col, a)
    h = s * 1.15
    d.polygon([(cx - s * 0.55, cy - h * 0.5), (cx - s * 1.0, cy - h * 0.25), (cx - s * 0.8, cy + h * 0.02),
               (cx - s * 0.55, cy - h * 0.1), (cx - s * 0.55, cy + h * 0.5), (cx + s * 0.55, cy + h * 0.5),
               (cx + s * 0.55, cy - h * 0.1), (cx + s * 0.8, cy + h * 0.02), (cx + s * 1.0, cy - h * 0.25),
               (cx + s * 0.55, cy - h * 0.5)], fill=c)
    d.ellipse([cx - s * 0.22, cy - h * 0.62, cx + s * 0.22, cy - h * 0.38], fill=BG)


def tub_icon(d, cx, cy, s, a=1.0):
    """浴槽。s = 幅の半分。"""
    if a <= 0:
        return
    d.rounded_rectangle([cx - s, cy - s * 0.45, cx + s, cy + s * 0.35], int(s * 0.25), fill=mix(SILVER, a))
    d.rounded_rectangle([cx - s * 0.85, cy - s * 0.3, cx + s * 0.85, cy + s * 0.2], int(s * 0.2), fill=mix(WATER, a))
    d.rectangle([cx - s * 0.75, cy + s * 0.35, cx - s * 0.6, cy + s * 0.5], fill=mix(SILVER, a))
    d.rectangle([cx + s * 0.6, cy + s * 0.35, cx + s * 0.75, cy + s * 0.5], fill=mix(SILVER, a))


def unworn():
    """1年間一度も着ない服 約25枚。"""
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 170), "この1年で、一度も着なかった服", 60, SUB, anchor="mm", alpha=prog(t, 0.1))
        k = prog(t, 0.4, max(1.0, dur * 0.45))
        n = int(round(25 * k))
        text(d, (W / 2, 340), f"平均 約{n}枚", 150, ACCENT, anchor="mm", alpha=prog(t, 0.3))
        for i in range(n):
            x = 300 + (i % 13) * 110
            y = 560 + (i // 13) * 150
            shirt_icon(d, x, y, 42, CLOTH[i % len(CLOTH)], 0.9)
        footnote(d, t, "1人あたり（年間）。出典：環境省 SUSTAINABLE FASHION（令和2年度 ファッションと環境に関する調査）", 1.2)
        return apply_fade(im, fade(t, dur))
    return f


def footprint():
    """服1着の CO2 と水。浴槽11杯。"""
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "服を1着つくると", 60, alpha=prog(t, 0.1))
        shirt_icon(d, 330, 470, 150, BLUE, prog(t, 0.2))
        a = prog(t, 0.6)
        text(d, (620, 340), "CO2", 56, SUB, anchor="lm", alpha=a)
        text(d, (800, 340), "約25.5kg", 100, FG, anchor="lm", alpha=a)
        b = prog(t, dur * 0.3)
        text(d, (620, 520), "水", 56, SUB, anchor="lm", alpha=b)
        text(d, (800, 520), "約2,300L", 100, WATER, anchor="lm", alpha=b)
        t0 = dur * 0.5
        step = max(0.12, (dur * 0.35) / 11)
        for i in range(11):
            tub_icon(d, 230 + i * 150, 680, 58, prog(t, t0 + i * step, 0.3))
        text(d, (W / 2, 785), "＝ お風呂の浴槽 11杯分", 56, WATER, anchor="mm", alpha=prog(t, t0 + 11 * step, 0.3))
        footnote(d, t, "出典：環境省 令和2年度 ファッションと環境に関する調査（2019年の国内供給量 約35.5億着をもとにした試算）", 1.2)
        return apply_fade(im, fade(t, dur))
    return f


def per_person():
    """1人あたり年間：買う18／手放す12／着ない25。"""
    rows = [("買う", 18, BLUE), ("手放す", 12, ACCENT), ("一度も着ない", 25, RED)]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "1人あたり 1年間の服", 60, alpha=prog(t, 0.1))
        step = max(0.8, (dur - 2.0) / len(rows))
        for i, (s, v, col) in enumerate(rows):
            y = 340 + i * 190
            a = prog(t, 0.3 + i * step, 0.9)
            text(d, (520, y), s, 60, anchor="rm", alpha=prog(t, 0.3 + i * step))
            if a > 0:
                d.rounded_rectangle([570, y - 50, 570 + 42 * v * ease(a), y + 50], 16, fill=col)
            text(d, (600 + 42 * v * ease(a), y), f"約{v}枚", 64, col, anchor="lm", alpha=a)
        footnote(d, t, "出典：環境省 SUSTAINABLE FASHION（令和2年度調査）", 1.2)
        return apply_fade(im, fade(t, dur))
    return f


def closet_share():
    """家にある服：使っている55%／しまい込み45%。"""
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "家にある服のうち", 60, alpha=prog(t, 0.1))
        cx, cy, r = 640, 560, 260
        a = prog(t, 0.6, 1.6)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLUE)
        if a > 0:
            d.pieslice([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * 0.45 * a, fill=SILVER)
        d.ellipse([cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6], fill=BG)
        text(d, (cx, cy), f"{45 * a:.0f}%", 110, SILVER, anchor="mm", alpha=a)
        rows = [("ふだん着ている　55%", BLUE), ("しまい込まれたまま　45%", SILVER)]
        for i, (s, col) in enumerate(rows):
            y = 470 + i * 130
            aa = prog(t, 0.8 + i * 0.6)
            if aa > 0:
                d.rounded_rectangle([1040, y - 26, 1092, y + 26], 8, fill=col)
            text(d, (1120, y), s, 52, anchor="lm", alpha=aa)
        footnote(d, t, "2023年の推計。出典：環境省 サステナブルファッション「ファッションと環境の現状」", 1.2)
        return apply_fade(im, fade(t, dur))
    return f


def discard():
    """家庭から手放される服 約51万トン → 廃棄 約2/3、再活用 約1/3。"""
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 160), "家庭から手放される服（1年間）", 56, SUB, anchor="mm", alpha=prog(t, 0.1))
        n = 51 * prog(t, 0.3, max(1.0, dur * 0.3))
        text(d, (W / 2, 320), f"約{n:.0f}万トン", 150, ACCENT, anchor="mm", alpha=prog(t, 0.2))
        x0, x1, y0, y1 = 200, 1720, 520, 640
        t1 = dur * 0.4
        a = prog(t, t1, 1.0)
        if a > 0:
            d.rectangle([x0, y0, x0 + (x1 - x0) * 0.66 * ease(a), y1], fill=RED)
        b = prog(t, t1 + 1.0, 0.8)
        if b > 0:
            xm = x0 + (x1 - x0) * 0.66
            d.rectangle([xm + 6, y0, xm + 6 + (x1 - xm - 6) * ease(b), y1], fill=TEAL)
        text(d, (x0 + (x1 - x0) * 0.33, 720), "ごみとして燃やす・埋める　約3分の2", 48, RED, anchor="mm", alpha=a)
        text(d, (x0 + (x1 - x0) * 0.83, 720), "もう一度使われる", 44, TEAL, anchor="mm", alpha=b)
        text(d, (x0 + (x1 - x0) * 0.83, 790), "約3分の1", 56, TEAL, anchor="mm", alpha=b)
        footnote(d, t, "出典：環境省 2024年版 衣類のマテリアルフロー（重量）／割合は2022年の推計（環境省資料が引用する矢野経済研究所の試算）", 1.2)
        return apply_fade(im, fade(t, dur))
    return f


def routes():
    """回収 → 古着／ウエス／反毛（約3分の1ずつ）。"""
    nodes = [("古着", "海外などで\nまた着られる", BLUE), ("ウエス", "機械の油を\nふき取る布", ACCENT),
             ("反毛", "ほぐして\n車の防音材などに", TEAL)]

    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 120), "回収された服のゆくえ", 60, anchor="mm", alpha=prog(t, 0.1))
        a0 = prog(t, 0.3)
        if a0 > 0:
            d.rounded_rectangle([760, 210, 1160, 320], 26, fill=CARD, outline=SILVER, width=5)
        text(d, (960, 265), "回収・選別", 52, FG, anchor="mm", alpha=a0, bg=CARD)
        step = max(0.7, (dur - 2.5) / 3)
        xs = [400, 960, 1520]
        for i, (s, sub, col) in enumerate(nodes):
            at = 0.8 + i * step
            arrow(d, (960, 330), (xs[i], 450), prog(t, at - 0.4, 0.4), SUB, 6)
            a = prog(t, at)
            if a > 0:
                d.rounded_rectangle([xs[i] - 230, 460, xs[i] + 230, 790], 28, fill=CARD, outline=col, width=5)
            text(d, (xs[i], 530), s, 66, col, anchor="mm", alpha=a, bg=CARD)
            for j, line in enumerate(sub.split("\n")):
                text(d, (xs[i], 625 + j * 56), line, 42, FG, anchor="mm", alpha=a, bg=CARD)
            text(d, (xs[i], 750), "約3分の1", 40, SUB, anchor="mm", alpha=prog(t, 0.8 + 3 * step), bg=CARD)
        footnote(d, t, "名古屋市の古着回収の例（古着・ウエス・反毛に約3分の1ずつ）。出典：名古屋市「古着・古布のリサイクル」", 1.5)
        return apply_fade(im, fade(t, dur))
    return f


def goal():
    """2030年度までに 廃棄 −25%。"""
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (120, 110), "国の目標：家庭から捨てられる服", 60, alpha=prog(t, 0.1))
        base, y1 = 730, 280
        a = prog(t, 0.4, 0.8)
        h = (base - y1) * ease(a)
        d.rectangle([520, base - h, 760, base], fill=SILVER)
        text(d, (640, base + 50), "2020年度", 46, FG, anchor="mm", alpha=a)
        b = prog(t, 1.4, 1.0)
        h2 = (base - y1) * 0.75 * ease(b)
        d.rectangle([1160, base - h2, 1400, base], fill=TEAL)
        text(d, (1280, base + 50), "2030年度", 46, FG, anchor="mm", alpha=b)
        c = prog(t, 2.2)
        if c > 0:
            arrow(d, (800, 380), (1120, 430), c, ACCENT, 8)
        text(d, (960, 300), "−25%", 110, ACCENT, anchor="mm", alpha=c)
        footnote(d, t, "2030年度までに2020年度比25%削減（家庭から手放される衣類のうち廃棄されるもの）。出典：環境省", 1.2)
        return apply_fade(im, fade(t, dur))
    return f


def next_card():
    def f(t, dur):
        im = canvas(); d = ImageDraw.Draw(im)
        text(d, (W / 2, 380), "次回", 60, SUB, anchor="mm", alpha=prog(t, 0.1))
        text(d, (W / 2, 520), "使い終わった乾電池はどこへ行く？", 96, anchor="mm", alpha=prog(t, 0.4))
        text(d, (W / 2, 720), "モノの一生 #5", 50, ACCENT, anchor="mm", alpha=prog(t, 0.9))
        return apply_fade(im, fade(t, dur, tout=1.0))
    return f


REGISTRY = {
    "title": lambda: title_card("着なくなった服はどこへ行く？", "モノの一生 #4"),
    "unworn": unworn,
    "footprint": footprint,
    "per_person": per_person,
    "closet_share": closet_share,
    "discard": discard,
    "routes": routes,
    "goal": goal,
    "next": next_card,
}
