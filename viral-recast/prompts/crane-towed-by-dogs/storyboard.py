"""クレーン企画の絵コンテを描く(Pillow のみ・無料)。

使い方: python3 storyboard.py <出力PNGパス>
"""
import math
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
W, H = 540, 960          # 1コマ(9:16)
CAP = 330                # コマ下の説明欄の高さ
SLOPE = 24               # 坂の角度(度)

SKY = (205, 210, 215)
GROUND = (150, 115, 80)
GROUND_D = (115, 85, 55)
YELLOW = (240, 190, 30)
DARK = (40, 40, 40)
CABLE = (70, 70, 80)
RED = (220, 40, 40)
ORANGE = (255, 140, 0)
ARROW = (0, 110, 230)


def font(size):
    return ImageFont.truetype(FONT, size)


def slope_y(x, x0, y0):
    """坂の地面の y(右へ行くほど高い=y が小さい)。"""
    return y0 - (x - x0) * math.tan(math.radians(SLOPE))


def draw_ground(d, x0, y0):
    pts = [(0, slope_y(0, x0, y0)), (W, slope_y(W, x0, y0)), (W, H), (0, H)]
    d.polygon(pts, fill=GROUND)
    # 凸凹(轍と石)
    for i in range(0, W, 45):
        y = slope_y(i, x0, y0)
        d.ellipse([i, y + 8, i + 18, y + 16], fill=GROUND_D)
        d.ellipse([i + 20, y + 40, i + 30, y + 48], fill=(120, 120, 120))


def arrow(d, p1, p2, color=ARROW, width=8, label=None, f=None):
    d.line([p1, p2], fill=color, width=width)
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    for s in (-1, 1):
        a = ang + math.pi + s * math.radians(28)
        d.line([p2, (p2[0] + 26 * math.cos(a), p2[1] + 26 * math.sin(a))], fill=color, width=width)
    if label and f:
        d.text((p1[0], p1[1] + 14), label, fill=color, font=f)


def crane_sprite(scale=1.0):
    """右向きのクレーン(横から)。右が前・運転席側。長い伸縮ブーム付き。"""
    w, h = int(620 * scale), int(260 * scale)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = scale
    base = 200 * s
    # 車体(キャリア)
    d.rectangle([20 * s, base - 70 * s, 560 * s, base - 10 * s], fill=YELLOW, outline=DARK, width=3)
    # 運転席(前・右)
    d.polygon([(470 * s, base - 70 * s), (560 * s, base - 70 * s), (590 * s, base - 10 * s), (470 * s, base - 10 * s)],
              fill=YELLOW, outline=DARK)
    d.rectangle([480 * s, base - 125 * s, 565 * s, base - 70 * s], fill=YELLOW, outline=DARK, width=3)
    d.rectangle([495 * s, base - 115 * s, 555 * s, base - 80 * s], fill=(150, 190, 220))
    # 上部旋回体+オペレーター室(中央やや後ろ)
    d.rectangle([90 * s, base - 120 * s, 250 * s, base - 70 * s], fill=YELLOW, outline=DARK, width=3)
    d.rectangle([200 * s, base - 150 * s, 250 * s, base - 120 * s], fill=(150, 190, 220), outline=DARK)
    # ブーム(太く長い・運転席の前まで突き出す)
    d.polygon([(70 * s, base - 145 * s), (610 * s, base - 160 * s), (610 * s, base - 135 * s), (70 * s, base - 115 * s)],
              fill=(250, 205, 40), outline=DARK)
    for k in range(4):  # 伸縮段の継ぎ目
        x = (170 + k * 110) * s
        d.line([(x, base - 150 * s), (x, base - 120 * s)], fill=DARK, width=2)
    d.rectangle([590 * s, base - 135 * s, 610 * s, base - 105 * s], fill=DARK)  # フックブロック
    # タイヤ(5軸)
    for x in (70, 160, 250, 400, 500):
        d.ellipse([(x - 33) * s, base - 45 * s, (x + 33) * s, base + 21 * s], fill=DARK)
        d.ellipse([(x - 13) * s, base - 25 * s, (x + 13) * s, base + 1 * s], fill=(130, 130, 130))
    # ハザードランプ
    for x in (25, 585):
        d.ellipse([(x - 9) * s, base - 60 * s, (x + 9) * s, base - 42 * s], fill=ORANGE)
    # 前部けん引フック
    d.ellipse([588 * s, base - 30 * s, 606 * s, base - 12 * s], outline=DARK, width=4)
    # 煙
    for i, (x, y, r) in enumerate([(300, 90, 18), (320, 60, 24), (345, 25, 30)]):
        d.ellipse([(x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s], fill=(170, 170, 170, 150))
    return im, (598 * s, base - 21 * s), (70 * s, base + 21 * s)


def paste_rotated(img, sprite, anchor_px, angle, hook, wheel):
    """sprite を坂の角度に回転し、左下付近を anchor_px に合わせて貼る。前部フックの座標を返す。"""
    rot = sprite.rotate(angle, expand=True, resample=Image.BICUBIC)
    sw, sh = sprite.size
    cx, cy = sw / 2, sh / 2
    a = math.radians(angle)

    def tr(p):
        x, y = p[0] - cx, p[1] - cy
        return (x * math.cos(a) + y * math.sin(a) + rot.size[0] / 2,
                -x * math.sin(a) + y * math.cos(a) + rot.size[1] / 2)

    rear = tr(wheel)
    off = (int(anchor_px[0] - rear[0]), int(anchor_px[1] - rear[1]))
    img.paste(rot, off, rot)
    hk = tr(hook)
    return hk[0] + off[0], hk[1] + off[1]


def dog_side(d, x, y, s=1.0, color=(200, 150, 90)):
    """右(坂の上)へ引っ張る犬を横から。"""
    d.ellipse([x - 22 * s, y - 14 * s, x + 22 * s, y + 10 * s], fill=color, outline=DARK)
    d.ellipse([x + 16 * s, y - 26 * s, x + 36 * s, y - 6 * s], fill=color, outline=DARK)
    d.polygon([(x + 30 * s, y - 26 * s), (x + 36 * s, y - 36 * s), (x + 36 * s, y - 22 * s)], fill=color)
    for lx in (-14, -4, 8, 16):
        d.line([(x + lx * s, y + 6 * s), (x + (lx + 8) * s, y + 22 * s)], fill=DARK, width=3)
    d.line([(x - 10 * s, y - 12 * s), (x + 10 * s, y - 12 * s)], fill=RED, width=3)  # ハーネス


def dog_front(d, x, y, s=1.0, color=(200, 150, 90)):
    """カメラに向かって登ってくる犬を正面から。"""
    d.ellipse([x - 30 * s, y - 10 * s, x + 30 * s, y + 40 * s], fill=color, outline=DARK)
    d.ellipse([x - 26 * s, y - 50 * s, x + 26 * s, y], fill=color, outline=DARK)
    d.polygon([(x - 24 * s, y - 40 * s), (x - 18 * s, y - 64 * s), (x - 6 * s, y - 46 * s)], fill=color, outline=DARK)
    d.polygon([(x + 24 * s, y - 40 * s), (x + 18 * s, y - 64 * s), (x + 6 * s, y - 46 * s)], fill=color, outline=DARK)
    d.ellipse([x - 13 * s, y - 34 * s, x - 5 * s, y - 26 * s], fill=DARK)
    d.ellipse([x + 5 * s, y - 34 * s, x + 13 * s, y - 26 * s], fill=DARK)
    d.ellipse([x - 6 * s, y - 20 * s, x + 6 * s, y - 12 * s], fill=DARK)
    d.ellipse([x - 5 * s, y - 8 * s, x + 5 * s, y + 6 * s], fill=(230, 100, 120))  # 舌
    d.line([(x - 28 * s, y + 6 * s), (x + 28 * s, y + 6 * s)], fill=RED, width=max(2, int(4 * s)))


DOG_COLORS = [(200, 150, 90), (90, 90, 95), (230, 190, 110), (210, 120, 60), (240, 240, 235), (170, 130, 90)]


def mini_map(d, cam_x, cam_dir, show_dogs, f):
    """右上の位置関係図:坂(横から)・クレーン・犬・カメラ。"""
    x0, y0, w, h = W - 200, 20, 180, 120
    d.rectangle([x0, y0, x0 + w, y0 + h], fill=(255, 255, 255), outline=DARK, width=2)
    d.text((x0 + 6, y0 + 4), "位置関係(横から)", fill=DARK, font=f)
    gx0, gy0, gx1, gy1 = x0 + 10, y0 + h - 12, x0 + w - 10, y0 + 40
    d.line([(gx0, gy0), (gx1, gy1)], fill=GROUND_D, width=4)
    d.text((gx1 - 34, gy1 - 26), "上↑", fill=DARK, font=f)

    def on(t):
        return gx0 + (gx1 - gx0) * t, gy0 + (gy1 - gy0) * t

    cx, cy = on(0.28)
    d.rectangle([cx - 18, cy - 14, cx + 18, cy], fill=YELLOW, outline=DARK)
    d.line([on(0.38), on(0.85)], fill=CABLE, width=2)
    if show_dogs:
        for t in (0.6, 0.7, 0.8):
            px, py = on(t)
            d.ellipse([px - 4, py - 8, px + 4, py], fill=(200, 150, 90))
    px, py = on(cam_x)
    d.rectangle([px - 9, py - 30, px + 9, py - 18], fill=ARROW)
    d.polygon([(px + 9 * cam_dir, py - 24), (px + 18 * cam_dir, py - 30), (px + 18 * cam_dir, py - 18)], fill=ARROW)


def caption(img, y, lines, f_title, f_body):
    d = ImageDraw.Draw(img)
    d.rectangle([0, y, W, y + CAP], fill=(255, 255, 255))
    d.text((16, y + 10), lines[0], fill=DARK, font=f_title)
    for i, t in enumerate(lines[1:]):
        d.text((16, y + 58 + i * 38), t, fill=DARK, font=f_body)


def panel1(f):
    img = Image.new("RGB", (W, H + CAP), SKY)
    d = ImageDraw.Draw(img)
    x0, y0 = 0, 860
    draw_ground(d, x0, y0)
    sprite, hook, wheel = crane_sprite(0.78)
    rear_x = 60
    hk = paste_rotated(img, sprite, (rear_x, slope_y(rear_x, x0, y0) + 4), SLOPE, hook, wheel)
    d = ImageDraw.Draw(img)
    end = (W + 10, hk[1] - (W + 10 - hk[0]) * math.tan(math.radians(SLOPE)) - 14)
    d.line([hk, end], fill=CABLE, width=6)
    arrow(d, (110, 300), (330, 200), label="坂の上へ", f=f["small"])
    d.text((W - 150, end[1] - 50), "先は画面外", fill=DARK, font=f["small"])
    mini_map(d, 0.12, 1, False, f["tiny"])
    caption(img, H, ["カット1  0〜4秒  動けないクレーン",
                     "画角: 真横・少し下から。左=坂の下、右=坂の上",
                     "ブームが車体の上で運転席の前まで突き出す",
                     "ハザード点滅・薄い煙。ワイヤーは右上の画面外へ",
                     "カメラ: ほぼ固定→ゆっくり右(坂の上)へ寄る",
                     "音: 苦しそうなエンジン音、ワイヤーのきしみ",
                     "犬はまだ一切映さない"], f["title"], f["body"])
    return img


def panel2(f):
    img = Image.new("RGB", (W, H + CAP), SKY)
    d = ImageDraw.Draw(img)
    x0, y0 = 0, 900
    draw_ground(d, x0, y0)
    # 大きなタイヤと車体側面のアップ
    sprite, hook, wheel = crane_sprite(1.9)
    paste_rotated(img, sprite, (-300, slope_y(-300, x0, y0) + 6), SLOPE, hook, wheel)
    d = ImageDraw.Draw(img)
    for i in range(12):  # 飛び散る土
        x, y = 160 + i * 25, slope_y(160 + i * 25, x0, y0) - 20 - (i % 3) * 25
        d.ellipse([x, y, x + 10, y + 10], fill=GROUND_D)
    arrow(d, (90, 170), (330, 70), label="カメラ並走", f=f["small"])
    d.text((300, 600), "空転するタイヤ", fill=(255, 255, 255), font=f["small"])
    mini_map(d, 0.3, 1, False, f["tiny"])
    caption(img, H, ["カット2  4〜8秒  少しずつ登る",
                     "画角: 車体側面とタイヤのアップ",
                     "頭上にブームの底面が見える",
                     "土の凸凹でタイヤが空転、土が飛ぶ",
                     "カメラ: 坂の上へクレーンと並走",
                     "音: タイヤが土をかく音",
                     "まだ何が引いているかは見せない"], f["title"], f["body"])
    return img


def panel3(f):
    img = Image.new("RGB", (W, H + CAP), SKY)
    d = ImageDraw.Draw(img)
    x0, y0 = 0, 1000
    draw_ground(d, x0, y0)
    sprite, hook, wheel = crane_sprite(0.9)
    hk = paste_rotated(img, sprite, (-300, slope_y(-300, x0, y0) + 4), SLOPE, hook, wheel)
    d = ImageDraw.Draw(img)
    # 稜線(坂の上の盛り上がり)
    crest_x = 470
    cy = slope_y(crest_x, x0, y0)
    d.ellipse([crest_x - 160, cy - 40, crest_x + 160, cy + 60], fill=GROUND)
    d.line([hk, (crest_x - 20, cy - 30)], fill=CABLE, width=7)
    arrow(d, (150, 560), (360, 470), label="ワイヤーを追う", f=f["small"])
    d.text((crest_x - 170, cy - 110), "稜線の向こうは見えない", fill=DARK, font=f["small"])
    mini_map(d, 0.5, 1, False, f["tiny"])
    caption(img, H, ["カット3  8〜11秒  ワイヤーの先を追う",
                     "画角: 左下にクレーンの運転席とブーム先端",
                     "右上へ伸びるワイヤーが稜線で途切れる",
                     "カメラ: ワイヤーに沿って坂の上へ移動、",
                     "      少し上を向く",
                     "音: 遠くからかすかに犬の息づかい"], f["title"], f["body"])
    return img


def panel4(f):
    img = Image.new("RGB", (W, H + CAP), SKY)
    d = ImageDraw.Draw(img)
    # 坂の上から下を見下ろす:地面が画面のほとんど、奥(上)が坂の下
    d.polygon([(0, 260), (W, 260), (W, H), (0, H)], fill=GROUND)
    # 奥(坂の下)のクレーン正面とブーム
    d.rectangle([200, 200, 340, 290], fill=YELLOW, outline=DARK, width=3)
    d.rectangle([215, 215, 325, 250], fill=(150, 190, 220))
    d.rectangle([248, 150, 292, 198], fill=(250, 205, 40), outline=DARK, width=3)  # 手前に突き出たブーム先端
    d.rectangle([262, 198, 278, 214], fill=DARK)  # フックブロック
    d.ellipse([205, 262, 220, 277], fill=ORANGE)
    d.ellipse([320, 262, 335, 277], fill=ORANGE)
    # ワイヤー(手前の犬たちへ)
    d.line([(270, 290), (270, 760)], fill=CABLE, width=6)
    # 2列の犬(奥ほど小さい)
    rows = [(330, 0.45), (400, 0.55), (480, 0.68), (580, 0.85), (700, 1.05), (850, 1.4)]
    for i, (y, s) in enumerate(rows):
        for j, dx in enumerate((-70, 70)):
            dog_front(d, 270 + dx * s, y, s, DOG_COLORS[(i * 2 + j) % len(DOG_COLORS)])
    arrow(d, (60, 560), (60, 380), label="", f=None)
    d.text((14, 600), "犬は\nカメラに\n向かって\n登ってくる", fill=ARROW, font=f["small"])
    d.text((330, 222), "奥=坂の下", fill=DARK, font=f["small"])
    mini_map(d, 0.95, -1, True, f["tiny"])
    caption(img, H, ["カット4  11〜15秒  オチ:犬たち!",
                     "画角: 犬たちの正面・坂の上側から見下ろす",
                     "手前に先頭の犬の顔、奥にクレーンとブーム",
                     "約20匹・2列・ハーネス・犬種ミックス",
                     "カメラ: ゆっくり後ろへ下がり、",
                     "      先頭の犬の得意げな顔に寄って終わる",
                     "音: 犬のハァハァという息、元気な鳴き声"], f["title"], f["body"])
    return img


def main(out):
    f = {"title": font(26), "body": font(22), "small": font(22), "tiny": font(14)}
    panels = [panel1(f), panel2(f), panel3(f), panel4(f)]
    gap = 16
    sheet = Image.new("RGB", (W * 4 + gap * 5, H + CAP + 90 + gap), (60, 60, 60))
    d = ImageDraw.Draw(sheet)
    d.text((gap, 20), "絵コンテ v2:故障クレーンを犬20匹が登り坂で引き上げる(15秒・9:16・1カット長回し)",
           fill=(255, 255, 255), font=font(36))
    for i, p in enumerate(panels):
        sheet.paste(p, (gap + i * (W + gap), 90))
    sheet.save(out)


if __name__ == "__main__":
    main(sys.argv[1])
