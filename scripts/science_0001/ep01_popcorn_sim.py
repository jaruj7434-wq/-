"""0.001秒の世界 第1話「ポップコーンが弾ける0.001秒」 シミュレーション試作。

断面図(殻=果皮 / 中=でんぷん+水分子)を 9:16 で描き、
  1) 加熱: 温度上昇 → 水分子が速くなる → 内圧上昇(飽和水蒸気圧)
  2) 限界: 約180℃・約10気圧で殻が震える
  3) 破裂(超スロー): 亀裂 → 蒸気が抜ける → でんぷんが泡になって噴き出し「脚」で床を蹴って跳ぶ
を1本の mp4 に書き出す。

使い方:
  python3 scripts/science_0001/ep01_popcorn_sim.py            # 本番解像度 1080x1920
  python3 scripts/science_0001/ep01_popcorn_sim.py --preview  # 低解像度で高速確認
出力: assets/output/science_0001/ep01_popcorn_sim.mp4 (git管理外)
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import animation, patches
from matplotlib import font_manager

# ---------------------------------------------------------------- フォント
import logging

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for fam in ["Noto Sans CJK JP", "Noto Sans JP", "WenQuanYi Zen Hei", "IPAexGothic"]:
    if any(fam == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = fam
        break

# ---------------------------------------------------------------- 物理
T0, T_OIL, TAU = 25.0, 200.0, 45.0  # 初期温度[℃], 油温[℃], 加熱の時定数[s]
T_POP = 180.0  # 破裂温度 (Virot & Ponomarenko 2015)


def p_sat_atm(T: float) -> float:
    """水の飽和蒸気圧 [atm] (Antoine式, 99〜374℃)。177℃で約9.2atm=135psi。"""
    return 10 ** (8.14019 - 1810.94 / (244.485 + T)) / 760.0


def temp_at(t_real: float) -> float:
    return T_OIL - (T_OIL - T0) * math.exp(-t_real / TAU)


T_POP_TIME = -TAU * math.log((T_OIL - T_POP) / (T_OIL - T0))  # 破裂までの実時間[s]

# ---------------------------------------------------------------- タイムライン(動画秒)
FPS = 30
D_HEAT, D_LIMIT, D_BURST, D_END = 6.0, 2.0, 7.0, 3.0
TOTAL = D_HEAT + D_LIMIT + D_BURST + D_END
BURST_MS = 90.0  # 破裂→花の形になるまで 90ms 未満 (Virot & Ponomarenko 2015)

# ---------------------------------------------------------------- 色
BG = "#0b0f17"
HULL = "#b5651d"
STARCH = "#f3d27a"
WATER = "#5ec8ff"
FOAM = "#fff8e7"
ACCENT = "#ff5a3c"
TEXT = "#f5f5f5"

R = 1.0  # 粒の半径(描画単位)
CRACK_ANGLE = -math.pi / 2 - 0.15
FLOOR = -1.06  # 亀裂の位置(下やや左)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--out", default="assets/output/science_0001/ep01_popcorn_sim.mp4")
    args = ap.parse_args()
    dpi = 100 if args.preview else 200
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(1)

    # 水分子
    n_water = 160
    r0 = np.sqrt(rng.uniform(0, 1, n_water)) * 0.85 * R
    a0 = rng.uniform(0, 2 * math.pi, n_water)
    pos = np.c_[r0 * np.cos(a0), r0 * np.sin(a0)]
    dirs = rng.normal(size=(n_water, 2))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    escaped = np.zeros(n_water, bool)
    esc_vel = np.zeros((n_water, 2))

    # でんぷん粒(背景のつぶつぶ)
    n_grain = 55
    gr = np.sqrt(rng.uniform(0, 1, n_grain)) * 0.82 * R
    ga = rng.uniform(0, 2 * math.pi, n_grain)
    grains = np.c_[gr * np.cos(ga), gr * np.sin(ga)]
    grain_size = rng.uniform(0.07, 0.13, n_grain)

    # 泡(でんぷんが膨らんだもの): 先に出た泡ほど亀裂の正面(=床方向の「脚」)、後ほど周囲へ広がる
    n_foam = 60
    foam_emerge = np.sort(rng.uniform(0, 0.75, n_foam))
    foam_spread = rng.normal(0, 1, n_foam) * (0.25 + 2.2 * foam_emerge / 0.75)
    foam_dist = rng.uniform(0.0, 1.0, n_foam)

    fig = plt.figure(figsize=(5.4, 9.6), dpi=dpi, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])

    def phase(t: float):
        if t < D_HEAT:
            return "heat", t / D_HEAT
        t -= D_HEAT
        if t < D_LIMIT:
            return "limit", t / D_LIMIT
        t -= D_LIMIT
        if t < D_BURST:
            return "burst", t / D_BURST
        return "end", (t - D_BURST) / D_END

    def ease(x: float) -> float:
        x = min(max(x, 0.0), 1.0)
        return 1 - (1 - x) ** 3

    def draw(frame: int):
        nonlocal pos
        t = frame / FPS
        ph, u = phase(t)
        ax.clear()
        ax.set_xlim(-1.6, 1.6)
        ax.set_ylim(-2.9, 3.5)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.add_patch(patches.Rectangle((-2, -3), 4, 7, color=BG, zorder=-10))

        # --- 状態量
        if ph == "heat":
            t_real = u * T_POP_TIME * 0.97
        elif ph == "limit":
            t_real = T_POP_TIME * (0.97 + 0.03 * u)
        else:
            t_real = T_POP_TIME
        T = temp_at(t_real)
        burst_u = u if ph == "burst" else (1.0 if ph == "end" else 0.0)
        ms = BURST_MS * burst_u
        P = p_sat_atm(T) if ph in ("heat", "limit") else max(1.0, p_sat_atm(T) * math.exp(-burst_u * 12))

        # --- 粒の位置(脚で跳ぶ)
        jump = 0.0
        if burst_u > 0.3:  # 脚が床に届いてから跳ぶ
            jump = 0.55 * ease((burst_u - 0.3) / 0.7)
        cx, cy = 0.0, jump
        shake = 0.0
        if ph == "limit":
            shake = 0.02 * u * math.sin(frame * 2.7)
        cx += shake

        # 床
        ax.plot([-1.5, 1.5], [FLOOR, FLOOR], color="#3a4150", lw=2, zorder=0)

        # --- 泡(破裂後)
        grow = ease(burst_u * 1.4) if burst_u > 0 else 0.0
        for i in range(n_foam):
            age = burst_u - foam_emerge[i]
            if burst_u == 0 or age <= 0:
                continue
            g = ease(age / 0.3)
            ang = CRACK_ANGLE + foam_spread[i]
            d = R * (0.85 + (0.25 + 0.35 * foam_dist[i]) * g)
            size = 0.08 + 0.2 * g
            fx = cx + d * math.cos(ang)
            fy = max(cy + d * math.sin(ang), FLOOR + size * 0.8)  # 床に押し付けられる=脚
            ax.add_patch(patches.Circle((fx, fy), size, color=FOAM, alpha=0.95, ec="#e2d3b3", lw=0.6, zorder=3))

        # --- 殻(果皮)
        hull_lw = 7
        if burst_u == 0:
            col = HULL if ph == "heat" else _mix(HULL, ACCENT, u)
            ax.add_patch(patches.Circle((cx, cy), R * (1 + 0.015 * (P / 10) ** 2), fill=False, ec=col, lw=hull_lw, zorder=5))
        else:
            gap = math.degrees(0.15 + 1.6 * grow)
            c = math.degrees(CRACK_ANGLE)
            ax.add_patch(patches.Arc((cx, cy), 2 * R, 2 * R, theta1=c + gap, theta2=c + 360 - gap, ec=HULL, lw=hull_lw, zorder=5))

        # --- でんぷん粒
        if burst_u < 0.6:
            alpha = 0.8 * (1 - burst_u / 0.6)
            for (gx, gy), s in zip(grains, grain_size):
                ax.add_patch(patches.Circle((cx + gx, cy + gy), s, color=STARCH, alpha=alpha * 0.55, lw=0, zorder=1))

        # --- 水分子: 速さ ∝ sqrt(絶対温度)
        speed = 0.012 * math.sqrt((T + 273.15) / 298.15) ** 3  # 見やすさのため誇張
        if ph in ("burst", "end"):
            speed *= 0.6
        pos = pos + dirs * speed
        rr = np.linalg.norm(pos, axis=1)
        out_ = (rr > 0.9 * R) & ~escaped
        if burst_u > 0:
            ang = np.arctan2(pos[:, 1], pos[:, 0])
            near = np.abs(np.angle(np.exp(1j * (ang - CRACK_ANGLE)))) < 0.25 + 1.2 * grow
            go = out_ & near
            escaped[go] = True
            esc_vel[go] = pos[go] / rr[go, None] * 0.06
            out_ &= ~go
        # 壁で反射
        nrm = pos[out_] / rr[out_, None]
        dirs[out_] -= 2 * np.sum(dirs[out_] * nrm, axis=1, keepdims=True) * nrm
        pos[out_] = nrm * 0.9 * R
        pos[escaped] += esc_vel[escaped]
        inside = ~escaped
        hot = min(1, max(0, (T - 100) / 80))
        wcol = _mix(WATER, "#ffffff", hot * 0.6)
        ax.scatter(cx + pos[inside, 0], cy + pos[inside, 1], s=10, c=wcol, zorder=4, lw=0)
        steam = escaped & (np.linalg.norm(pos, axis=1) < 1.7 * R)
        if steam.any():
            ax.scatter(cx + pos[steam, 0], cy + pos[steam, 1], s=26, c="#d8f1ff", alpha=0.45, zorder=6, lw=0)
        if 0 < burst_u < 0.35:
            ax.text(cx + 1.15, cy - 0.75, "蒸気が\n抜ける", color="#d8f1ff", fontsize=11, ha="center")
        if 0.3 < burst_u < 0.75:
            ax.annotate("でんぷんの「脚」が\n床を蹴る", xy=(cx - 0.1, FLOOR + 0.15), xytext=(-1.0, -1.85),
                        color=FOAM, fontsize=11, ha="center", arrowprops=dict(arrowstyle="->", color=FOAM))

        # --- テロップ
        if ph == "heat":
            title = "加熱中"
        elif ph == "limit":
            title = "殻が限界"
        elif ph == "burst":
            title = "破裂（超スロー）"
        else:
            title = "ポン！"
        ax.text(0, 3.15, title, ha="center", va="center", color=TEXT, fontsize=26, weight="bold")

        if ph in ("heat", "limit"):
            clock = f"経過 {t_real:5.1f} 秒"
        else:
            clock = f"破裂から {ms:5.1f} ミリ秒"
        ax.text(0, 2.7, clock, ha="center", color="#aab3c5", fontsize=14)

        _gauge(ax, -1.4, 2.15, "温度", f"{T:5.0f} ℃", (T - T0) / (T_POP - T0))
        _gauge(ax, 0.15, 2.15, "内圧", f"{P:4.1f} 気圧", (P - 1) / 9)

        legend_y = -2.45
        ax.scatter([-1.3], [legend_y], s=30, c=WATER, lw=0)
        ax.text(-1.2, legend_y, "水分子", color=TEXT, fontsize=10, va="center")
        ax.add_patch(patches.Circle((-0.3, legend_y), 0.06, color=STARCH, alpha=0.6, lw=0))
        ax.text(-0.2, legend_y, "でんぷん", color=TEXT, fontsize=10, va="center")
        ax.add_patch(patches.Circle((0.75, legend_y), 0.06, color=FOAM, lw=0))
        ax.text(0.85, legend_y, "泡（白い部分）", color=TEXT, fontsize=10, va="center")

        if ph == "end":
            a = ease(u * 2)
            ax.text(0, -1.75, "跳ねる力は蒸気じゃなく\nでんぷんの「脚」", ha="center", va="center",
                    color=ACCENT, fontsize=19, weight="bold", alpha=a)
        return []

    anim = animation.FuncAnimation(fig, draw, frames=int(TOTAL * FPS), blit=False)
    writer = animation.FFMpegWriter(fps=FPS, codec="libx264", extra_args=["-pix_fmt", "yuv420p", "-crf", "18"])
    anim.save(str(out), writer=writer, savefig_kwargs={"facecolor": BG})
    print(f"wrote {out}  (破裂までの実時間 ≈ {T_POP_TIME:.0f} s, 180℃での内圧 ≈ {p_sat_atm(T_POP):.1f} atm)")


def _mix(c1: str, c2: str, u: float) -> tuple:
    a = np.array(matplotlib.colors.to_rgb(c1))
    b = np.array(matplotlib.colors.to_rgb(c2))
    return tuple(a + (b - a) * min(max(u, 0), 1))


def _gauge(ax, x, y, label, value, frac):
    frac = min(max(frac, 0), 1)
    w, h = 1.25, 0.14
    ax.text(x, y + 0.28, label, color="#aab3c5", fontsize=11)
    ax.text(x + w, y + 0.28, value, color=TEXT, fontsize=15, weight="bold", ha="right")
    ax.add_patch(patches.Rectangle((x, y), w, h, color="#262c38", lw=0))
    ax.add_patch(patches.Rectangle((x, y), w * frac, h, color=_mix("#ffc04d", ACCENT, frac), lw=0))


if __name__ == "__main__":
    main()
