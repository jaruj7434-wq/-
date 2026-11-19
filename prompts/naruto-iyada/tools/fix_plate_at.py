"""指定した位置の額当てプレートのマークを消して渦巻きに描き直す。
使い方: python3 fix_plate_at.py 入力.png 出力.png 中心x,中心y,半幅,半高さ [...]
"""
import sys
import cv2, numpy as np
im = cv2.imread(sys.argv[1])
for spec in sys.argv[3:]:
    X, Y, bw, bh = map(int, spec.split(','))
    x0, y0, x1, y1 = X - bw - 12, Y - bh - 12, X + bw + 12, Y + bh + 12
    roi = im[y0:y1, x0:x1].copy(); g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(float)
    m = np.zeros(g.shape, np.uint8); inner = g[12:-12, 12:-12]
    m[12:-12, 12:-12] = (inner < np.percentile(inner, 80) * 0.70).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((3, 3), np.uint8)); m[:10, :] = 0; m[-10:, :] = 0; m[:, :10] = 0; m[:, -10:] = 0
    im[y0:y1, x0:x1] = cv2.inpaint(roi, m, 3, cv2.INPAINT_TELEA)
    r = min(bw, bh) + 2
    t = np.linspace(0, 2.8 * np.pi, 300)
    pts = np.stack([X + (1 + 0.6 * r / (2.8 * np.pi) * t) * np.cos(t), Y + (1 + 0.6 * r / (2.8 * np.pi) * t) * np.sin(t)], 1).astype(np.int32)
    ov = im.copy(); cv2.polylines(ov, [pts], False, (40, 40, 45), max(3, r // 7), cv2.LINE_AA)
    im = cv2.addWeighted(ov, 0.9, im, 0.1, 0)
cv2.imwrite(sys.argv[2], im)
