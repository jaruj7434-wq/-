"""おおよその位置の近くで額当てのマーク(明るいプレート上の暗い図形)を自動で見つけ、消して渦巻きに描き直す。
使い方: python3 fix_plate_near.py 入力.png 出力.png x,y[,探す半径] [...]
"""
import sys
import cv2, numpy as np
im = cv2.imread(sys.argv[1])
for spec in sys.argv[3:]:
    p = list(map(int, spec.split(','))); gx, gy = p[0], p[1]; R = p[2] if len(p) > 2 else 90
    x0, y0 = max(0, gx - R), max(0, gy - R)
    win = im[y0:gy + R, x0:gx + R]
    g = cv2.cvtColor(win, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(win, cv2.COLOR_BGR2HSV)
    plate = ((hsv[..., 1] < 70) & (hsv[..., 2] > 110)).astype(np.uint8)
    plate = cv2.morphologyEx(plate, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    bright = np.median(g[plate > 0]) if plate.any() else 180
    dark = ((g < bright * 0.55) & (plate > 0)).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(dark)
    best = None
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 18 < w < 140 and 14 < h < 110 and a > 60:
            d = np.hypot(x + w / 2 - R, y + h / 2 - R)
            if best is None or d < best[0]: best = (d, i)
    if best is None:
        print('見つからない', spec); continue
    i = best[1]; x, y, w, h, a = st[i]
    X, Y = x0 + x + w // 2, y0 + y + h // 2
    m = np.zeros(im.shape[:2], np.uint8)
    m[y0:y0 + win.shape[0], x0:x0 + win.shape[1]][lab == i] = 255
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    im = cv2.inpaint(im, m, 4, cv2.INPAINT_TELEA)
    r = max(w, h) / 2
    t = np.linspace(0, 2.8 * np.pi, 300)
    pts = np.stack([X + (1 + 0.95 * r / (2.8 * np.pi) * t) * np.cos(t), Y + (1 + 0.95 * r / (2.8 * np.pi) * t) * np.sin(t)], 1).astype(np.int32)
    ov = im.copy(); cv2.polylines(ov, [pts], False, (40, 40, 45), max(3, int(r / 7)), cv2.LINE_AA)
    im = cv2.addWeighted(ov, 0.9, im, 0.1, 0)
    print('直した', spec, '→', X, Y, w, h)
cv2.imwrite(sys.argv[2], im)
