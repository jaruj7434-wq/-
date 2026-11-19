"""額当ての金属プレートを自動で探し、中のマークを消して渦巻きに描き直す。
使い方: python3 fix_plates.py 入力.png 出力.png [最小プレート幅px]
プレート = 彩度が低く明るい横長の領域(縦横比 1.6〜4.5)。
"""
import sys
import cv2, numpy as np

src, dst = sys.argv[1], sys.argv[2]
minw = int(sys.argv[3]) if len(sys.argv) > 3 else 60
im = cv2.imread(src)
hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
mask = ((hsv[..., 1] < 45) & (hsv[..., 2] > 120)).astype(np.uint8) * 255
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
n = 0
for c in cnts:
    x, y, w, h = cv2.boundingRect(c)
    if w < minw or not (1.6 < w / max(h, 1) < 4.5): continue
    if cv2.contourArea(c) < 0.6 * w * h: continue
    # 中央の暗い線(マーク)を消す
    cx, cy = x + w // 2, y + h // 2
    rw, rh = int(w * 0.32), int(h * 0.36)
    x0, y0, x1, y1 = cx - rw, cy - rh, cx + rw, cy + rh
    roi = im[y0:y1, x0:x1].copy()
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(float)
    m = (g < np.percentile(g, 85) * 0.72).astype(np.uint8) * 255
    if m.mean() < 5: continue  # マークがない
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    im[y0:y1, x0:x1] = cv2.inpaint(roi, m, 3, cv2.INPAINT_TELEA)
    r = min(rw, rh) * 0.95
    t = np.linspace(0, 2.8 * np.pi, 300)
    rad = 1 + r / (2.8 * np.pi) * t * 0.95
    pts = np.stack([cx + rad * np.cos(t), cy + rad * np.sin(t)], 1).astype(np.int32)
    ov = im.copy()
    cv2.polylines(ov, [pts], False, (40, 40, 45), max(2, int(w / 40)), cv2.LINE_AA)
    im = cv2.addWeighted(ov, 0.9, im, 0.1, 0)
    n += 1
cv2.imwrite(dst, im)
print(src, '直したプレート数', n)
