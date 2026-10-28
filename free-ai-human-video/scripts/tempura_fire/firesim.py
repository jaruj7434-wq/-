"""自作の3D 炎・煙シミュレーター(numba で高速化)。

Blender 内蔵の Mantaflow は pip 版 Blender で動かない(LevelsetGrid の継承が壊れている)ため、同じ考え方
(非圧縮性流体+浮力+燃焼+渦の強調)を自前で実装した。結果はフレームごとに .npz(煙・炎・温度)で保存する。

格子は (x, y, z) の順で z が上、1マス h[m]。速度は面に置く MAC 格子
(u: x面 (nx+1,ny,nz)、v: y面、w: z面)。セル中心の座標を (i, j, k) とすると、u[i] は (i-0.5, j, k) にある。
外周は、床(と ceiling=True なら天井)が壁、それ以外は開放(圧力 0)。
"""
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numba import njit, prange


# ---------------------------------------------------------------- 補間・移流
@njit(cache=True, fastmath=True)
def _sample(f, x, y, z):
    """配列の添字座標 (x, y, z) で三線形補間(範囲外は端の値)。"""
    nx, ny, nz = f.shape
    x = min(max(x, 0.0), nx - 1.0001)
    y = min(max(y, 0.0), ny - 1.0001)
    z = min(max(z, 0.0), nz - 1.0001)
    i, j, k = int(x), int(y), int(z)
    fx, fy, fz = x - i, y - j, z - k
    c00 = f[i, j, k] * (1 - fx) + f[i + 1, j, k] * fx
    c10 = f[i, j + 1, k] * (1 - fx) + f[i + 1, j + 1, k] * fx
    c01 = f[i, j, k + 1] * (1 - fx) + f[i + 1, j, k + 1] * fx
    c11 = f[i, j + 1, k + 1] * (1 - fx) + f[i + 1, j + 1, k + 1] * fx
    return (c00 * (1 - fy) + c10 * fy) * (1 - fz) + (c01 * (1 - fy) + c11 * fy) * fz


@njit(cache=True, fastmath=True)
def _vel(u, v, w, x, y, z):
    """セル中心座標 (x, y, z) での速度 [マス/秒 × h]。"""
    return (_sample(u, x + 0.5, y, z), _sample(v, x, y + 0.5, z), _sample(w, x, y, z + 0.5))


@njit(parallel=True, cache=True, fastmath=True)
def advect(dst, src, u, v, w, dt_h, ox, oy, oz):
    """セミラグランジュ法。src[i,j,k] がセル中心座標 (i+ox, j+oy, k+oz) にある配列を運ぶ。"""
    nx, ny, nz = src.shape
    for i in prange(nx):
        for j in range(ny):
            for k in range(nz):
                x, y, z = i + ox, j + oy, k + oz
                a, b, c = _vel(u, v, w, x, y, z)
                # 2次のルンゲ=クッタで逆にたどる
                mx, my, mz = x - 0.5 * dt_h * a, y - 0.5 * dt_h * b, z - 0.5 * dt_h * c
                a, b, c = _vel(u, v, w, mx, my, mz)
                px, py, pz = x - dt_h * a, y - dt_h * b, z - dt_h * c
                dst[i, j, k] = _sample(src, px - ox, py - oy, pz - oz)


@njit(parallel=True, cache=True, fastmath=True)
def clamp_mc(dst, src, fwd, back, u, v, w, dt_h):
    """MacCormack 補正(スカラー用)。行き過ぎは元の近傍の範囲に制限する。"""
    nx, ny, nz = src.shape
    for i in prange(nx):
        for j in range(ny):
            for k in range(nz):
                val = fwd[i, j, k] + 0.5 * (src[i, j, k] - back[i, j, k])
                a, b, c = _vel(u, v, w, i, j, k)
                x = min(max(i - dt_h * a, 0.0), nx - 1.0001)
                y = min(max(j - dt_h * b, 0.0), ny - 1.0001)
                z = min(max(k - dt_h * c, 0.0), nz - 1.0001)
                p, q, r = int(x), int(y), int(z)
                lo = src[p, q, r]
                hi = lo
                for dp in range(2):
                    for dq in range(2):
                        for dr in range(2):
                            s = src[p + dp, q + dq, r + dr]
                            lo = min(lo, s)
                            hi = max(hi, s)
                dst[i, j, k] = min(max(val, lo), hi)


# ---------------------------------------------------------------- 圧力(非圧縮)
@njit(parallel=True, cache=True, fastmath=True)
def zero_solid_faces(u, v, w, solid, ceiling):
    nx, ny, nz = solid.shape
    for i in prange(nx + 1):
        for j in range(ny):
            for k in range(nz):
                if (i > 0 and solid[i - 1, j, k]) or (i < nx and solid[i, j, k]):
                    u[i, j, k] = 0.0
    for i in prange(nx):
        for j in range(ny + 1):
            for k in range(nz):
                if (j > 0 and solid[i, j - 1, k]) or (j < ny and solid[i, j, k]):
                    v[i, j, k] = 0.0
        for j in range(ny):
            for k in range(nz + 1):
                if (k > 0 and solid[i, j, k - 1]) or (k < nz and solid[i, j, k]) or k == 0 or (ceiling and k == nz):
                    w[i, j, k] = 0.0


@njit(parallel=True, cache=True, fastmath=True)
def divergence(div, u, v, w, solid):
    nx, ny, nz = solid.shape
    for i in prange(nx):
        for j in range(ny):
            for k in range(nz):
                div[i, j, k] = 0.0 if solid[i, j, k] else (u[i + 1, j, k] - u[i, j, k] + v[i, j + 1, k] - v[i, j, k]
                                                           + w[i, j, k + 1] - w[i, j, k])


@njit(parallel=True, cache=True, fastmath=True)
def pressure_rb(p, div, solid, color, omega, ceiling):
    """赤黒 SOR を1色分。固体の隣はノイマン(数に入れない)、領域の外は開放(圧力 0)。"""
    nx, ny, nz = p.shape
    for i in prange(nx):
        for j in range(ny):
            for k in range(nz):
                if (i + j + k) % 2 != color or solid[i, j, k]:
                    continue
                s = 0.0
                cnt = 0.0
                # x
                if i == 0:
                    cnt += 1.0
                elif not solid[i - 1, j, k]:
                    s += p[i - 1, j, k]
                    cnt += 1.0
                if i == nx - 1:
                    cnt += 1.0
                elif not solid[i + 1, j, k]:
                    s += p[i + 1, j, k]
                    cnt += 1.0
                # y
                if j == 0:
                    cnt += 1.0
                elif not solid[i, j - 1, k]:
                    s += p[i, j - 1, k]
                    cnt += 1.0
                if j == ny - 1:
                    cnt += 1.0
                elif not solid[i, j + 1, k]:
                    s += p[i, j + 1, k]
                    cnt += 1.0
                # z(床は常に壁、上は ceiling で切り替え)
                if k > 0 and not solid[i, j, k - 1]:
                    s += p[i, j, k - 1]
                    cnt += 1.0
                if k == nz - 1:
                    if not ceiling:
                        cnt += 1.0
                elif not solid[i, j, k + 1]:
                    s += p[i, j, k + 1]
                    cnt += 1.0
                if cnt > 0:
                    new = (s - div[i, j, k]) / cnt
                    p[i, j, k] += omega * (new - p[i, j, k])


@njit(parallel=True, cache=True, fastmath=True)
def subtract_gradient(u, v, w, p, solid, ceiling):
    nx, ny, nz = solid.shape
    for i in prange(nx + 1):
        for j in range(ny):
            for k in range(nz):
                pl = p[i - 1, j, k] if i > 0 else 0.0
                pr = p[i, j, k] if i < nx else 0.0
                u[i, j, k] -= pr - pl
    for i in prange(nx):
        for j in range(ny + 1):
            for k in range(nz):
                pl = p[i, j - 1, k] if j > 0 else 0.0
                pr = p[i, j, k] if j < ny else 0.0
                v[i, j, k] -= pr - pl
        for j in range(ny):
            for k in range(1, nz + 1):
                pl = p[i, j, k - 1]
                pr = p[i, j, k] if k < nz else 0.0
                w[i, j, k] -= pr - pl
    zero_solid_faces(u, v, w, solid, ceiling)


# ---------------------------------------------------------------- 力・燃焼
@njit(parallel=True, cache=True, fastmath=True)
def cell_velocity(cu, cv, cw, u, v, w):
    nx, ny, nz = cu.shape
    for i in prange(nx):
        for j in range(ny):
            for k in range(nz):
                cu[i, j, k] = 0.5 * (u[i, j, k] + u[i + 1, j, k])
                cv[i, j, k] = 0.5 * (v[i, j, k] + v[i, j + 1, k])
                cw[i, j, k] = 0.5 * (w[i, j, k] + w[i, j, k + 1])


@njit(parallel=True, cache=True, fastmath=True)
def vorticity_force(cu, cv, cw, fu, fv, fw, eps_dt):
    """渦の強調(vorticity confinement):細かい渦巻きを保つ。結果はセル中心の加速度。"""
    nx, ny, nz = cu.shape
    wx = np.zeros_like(cu)
    wy = np.zeros_like(cu)
    wz = np.zeros_like(cu)
    mag = np.zeros_like(cu)
    for i in prange(1, nx - 1):
        for j in range(1, ny - 1):
            for k in range(1, nz - 1):
                wx[i, j, k] = 0.5 * ((cw[i, j + 1, k] - cw[i, j - 1, k]) - (cv[i, j, k + 1] - cv[i, j, k - 1]))
                wy[i, j, k] = 0.5 * ((cu[i, j, k + 1] - cu[i, j, k - 1]) - (cw[i + 1, j, k] - cw[i - 1, j, k]))
                wz[i, j, k] = 0.5 * ((cv[i + 1, j, k] - cv[i - 1, j, k]) - (cu[i, j + 1, k] - cu[i, j - 1, k]))
                mag[i, j, k] = math.sqrt(wx[i, j, k] ** 2 + wy[i, j, k] ** 2 + wz[i, j, k] ** 2)
    for i in prange(2, nx - 2):
        for j in range(2, ny - 2):
            for k in range(2, nz - 2):
                gx = 0.5 * (mag[i + 1, j, k] - mag[i - 1, j, k])
                gy = 0.5 * (mag[i, j + 1, k] - mag[i, j - 1, k])
                gz = 0.5 * (mag[i, j, k + 1] - mag[i, j, k - 1])
                ln = math.sqrt(gx * gx + gy * gy + gz * gz) + 1e-6
                gx, gy, gz = gx / ln, gy / ln, gz / ln
                fu[i, j, k] = eps_dt * (gy * wz[i, j, k] - gz * wy[i, j, k])
                fv[i, j, k] = eps_dt * (gz * wx[i, j, k] - gx * wz[i, j, k])
                fw[i, j, k] = eps_dt * (gx * wy[i, j, k] - gy * wx[i, j, k])


@njit(parallel=True, cache=True, fastmath=True)
def add_cell_force(u, v, w, fu, fv, fw):
    nx, ny, nz = fu.shape
    for i in prange(1, nx):
        for j in range(ny):
            for k in range(nz):
                u[i, j, k] += 0.5 * (fu[i - 1, j, k] + fu[i, j, k])
    for i in prange(nx):
        for j in range(1, ny):
            for k in range(nz):
                v[i, j, k] += 0.5 * (fv[i, j - 1, k] + fv[i, j, k])
        for j in range(ny):
            for k in range(1, nz):
                w[i, j, k] += 0.5 * (fw[i, j, k - 1] + fw[i, j, k])


@njit(parallel=True, cache=True, fastmath=True)
def combust(fuel, temp, smoke, flame, w, dt, burn_rate, ignite, heat, soot, buoy, weight, cool, smoke_fade):
    """燃焼:燃料が燃えて熱・炎・煙(すす)になる。熱は浮力、煙は重さとして w に効く。"""
    nx, ny, nz = fuel.shape
    for i in prange(nx):
        for j in range(ny):
            for k in range(nz):
                f = fuel[i, j, k]
                t = temp[i, j, k]
                b = 0.0
                if f > 1e-4 and t > ignite:
                    b = min(f, f * burn_rate * dt + 0.05 * dt)
                    fuel[i, j, k] = f - b
                    temp[i, j, k] = t + heat * b
                    smoke[i, j, k] += soot * b
                flame[i, j, k] = flame[i, j, k] * math.exp(-10.0 * dt) + b / dt * 0.1
                temp[i, j, k] *= math.exp(-cool * dt)
                smoke[i, j, k] *= math.exp(-smoke_fade * dt)
    for i in prange(nx):
        for j in range(ny):
            for k in range(1, nz):
                tb = 0.5 * (temp[i, j, k - 1] + temp[i, j, k])
                sb = 0.5 * (smoke[i, j, k - 1] + smoke[i, j, k])
                w[i, j, k] += dt * (buoy * tb - weight * sb)


# ---------------------------------------------------------------- シミュレーション本体
@dataclass
class Sim:
    shape: tuple          # (nx, ny, nz)
    h: float              # 1マスの大きさ [m]
    origin: tuple         # 格子の角の世界座標 [m]
    burn_rate: float = 3.0
    ignite: float = 0.2
    heat: float = 2.5
    soot: float = 0.6
    buoy: float = 2.2     # 温度1あたりの上向き加速度 [m/s^2]
    weight: float = 0.3
    cool: float = 1.4
    smoke_fade: float = 0.2
    vort: float = 6.0     # 渦の強調の強さ
    ceiling: bool = False
    iters: int = 60

    def __post_init__(self):
        nx, ny, nz = self.shape
        self.u = np.zeros((nx + 1, ny, nz), np.float32)
        self.v = np.zeros((nx, ny + 1, nz), np.float32)
        self.w = np.zeros((nx, ny, nz + 1), np.float32)
        z = lambda: np.zeros(self.shape, np.float32)
        self.fuel, self.temp, self.smoke, self.flame = z(), z(), z(), z()
        self.powder = z()  # 消火器の粉(白い煙として描画。ここでは燃料と熱を奪う)
        self.p, self.div = z(), z()
        self.solid = np.zeros(self.shape, np.bool_)
        self.t = 0.0
        self.rng = np.random.default_rng(1)
        ii, jj, kk = np.meshgrid(*[np.arange(n, dtype=np.float32) for n in self.shape], indexing="ij")
        self.X = self.origin[0] + (ii + 0.5) * self.h
        self.Y = self.origin[1] + (jj + 0.5) * self.h
        self.Z = self.origin[2] + (kk + 0.5) * self.h

    # --- 形状(世界座標で指定)
    def mask_cylinder(self, cx, cy, z0, z1, r, r_inner=None):
        d = np.hypot(self.X - cx, self.Y - cy)
        m = (d <= r) & (self.Z >= z0) & (self.Z <= z1)
        if r_inner is not None:
            m &= d >= r_inner
        return m

    def mask_sphere(self, cx, cy, cz, r):
        return (self.X - cx) ** 2 + (self.Y - cy) ** 2 + (self.Z - cz) ** 2 <= r * r

    def mask_box(self, x0, x1, y0, y1, z0, z1):
        return (self.X >= x0) & (self.X <= x1) & (self.Y >= y0) & (self.Y <= y1) & (self.Z >= z0) & (self.Z <= z1)

    def emit(self, mask, fuel=0.0, temp=0.0, smoke=0.0, vel=None, jitter=0.0, powder=0.0):
        """mask の場所に燃料・熱・煙を与え、速度を設定する(毎ステップ呼ぶ)。jitter で炎のゆらぎを入れる。"""
        if not mask.any():
            return
        n = int(mask.sum())
        rnd = lambda: (1.0 + jitter * (self.rng.random(n, dtype=np.float32) - 0.5) * 2).astype(np.float32)
        for name, val in (("fuel", fuel), ("temp", temp), ("smoke", smoke), ("powder", powder)):
            if val:
                f = getattr(self, name)
                f[mask] = np.maximum(f[mask], val * rnd())
        if vel is not None:
            vx, vy, vz = vel
            # セルの値を両側の面に配る
            if vx:
                self.u[:-1][mask] = vx
                self.u[1:][mask] = vx
            if vy:
                self.v[:, :-1][mask] = vy
                self.v[:, 1:][mask] = vy
            if vz:
                vz_arr = (vz * rnd()).astype(np.float32)
                self.w[:, :, :-1][mask] = vz_arr
                self.w[:, :, 1:][mask] = vz_arr

    def emit_radial(self, mask, cx, cy, cz, speed, up=0.0):
        """mask の場所に、中心から外向きの速度(爆発的な広がり)を与える。"""
        dx, dy, dz = self.X[mask] - cx, self.Y[mask] - cy, self.Z[mask] - cz
        ln = np.sqrt(dx * dx + dy * dy + dz * dz) + 1e-6
        self.u[:-1][mask] = speed * dx / ln
        self.u[1:][mask] = speed * dx / ln
        self.v[:, :-1][mask] = speed * dy / ln
        self.v[:, 1:][mask] = speed * dy / ln
        self.w[:, :, :-1][mask] = speed * dz / ln + up
        self.w[:, :, 1:][mask] = speed * dz / ln + up

    def remove(self, mask, keep=0.2):
        """消火:mask の場所の燃料と熱を減らす(消火剤・ふた)。"""
        self.fuel[mask] *= keep
        self.temp[mask] *= keep

    def step(self, dt):
        dt_h = dt / self.h
        combust(self.fuel, self.temp, self.smoke, self.flame, self.w, dt, self.burn_rate, self.ignite, self.heat,
                self.soot, self.buoy, self.weight, self.cool, self.smoke_fade)
        if self.vort:
            cu, cv, cw = (np.empty(self.shape, np.float32) for _ in range(3))
            cell_velocity(cu, cv, cw, self.u, self.v, self.w)
            fu, fv, fw = (np.zeros(self.shape, np.float32) for _ in range(3))
            vorticity_force(cu, cv, cw, fu, fv, fw, self.vort * dt)
            add_cell_force(self.u, self.v, self.w, fu, fv, fw)
        self.project()
        u0, v0, w0 = self.u.copy(), self.v.copy(), self.w.copy()
        advect(self.u, u0, u0, v0, w0, dt_h, -0.5, 0.0, 0.0)
        advect(self.v, v0, u0, v0, w0, dt_h, 0.0, -0.5, 0.0)
        advect(self.w, w0, u0, v0, w0, dt_h, 0.0, 0.0, -0.5)
        f1, f2 = np.empty_like(self.fuel), np.empty_like(self.fuel)
        neg = (-u0, -v0, -w0)
        for f in (self.fuel, self.temp, self.smoke, self.flame, self.powder):
            src = f.copy()
            advect(f1, src, u0, v0, w0, dt_h, 0.0, 0.0, 0.0)
            advect(f2, f1, *neg, dt_h, 0.0, 0.0, 0.0)
            clamp_mc(f, src, f1, f2, u0, v0, w0, dt_h)
        self.project()
        if self.powder.any():  # 粉が濃いところは燃料と熱を奪って火を消す
            k = np.exp(-self.powder * 25.0 * dt).astype(np.float32)
            self.fuel *= k
            self.temp *= k
            self.powder *= np.float32(math.exp(-0.35 * dt))
        for f in (self.fuel, self.temp, self.smoke, self.flame, self.powder):
            f[self.solid] = 0.0
        self.t += dt

    def project(self):
        zero_solid_faces(self.u, self.v, self.w, self.solid, self.ceiling)
        divergence(self.div, self.u, self.v, self.w, self.solid)
        for _ in range(self.iters):
            pressure_rb(self.p, self.div, self.solid, 0, 1.75, self.ceiling)
            pressure_rb(self.p, self.div, self.solid, 1, 1.75, self.ceiling)
        subtract_gradient(self.u, self.v, self.w, self.p, self.solid, self.ceiling)

    def save(self, path):
        np.savez_compressed(path, smoke=self.smoke.astype(np.float16), flame=self.flame.astype(np.float16),
                            temp=self.temp.astype(np.float16), powder=self.powder.astype(np.float16))


def run(sim, frames, out_dir, events, fps=24, substeps=3, time_scale=1.0, log=True, warmup=0):
    """events(sim, frame, substep) を毎ステップ呼び、フレームごとに保存する。time_scale<1 でスローモーション。
    warmup: 保存を始める前に空回しするフレーム数(最初から火が安定して燃えている状態にする)。events には frame<=0 で渡す。"""
    import time
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dt = time_scale / fps / substeps
    for fr in range(1 - warmup, 1):
        for s in range(substeps):
            events(sim, fr, s)
            sim.step(1.0 / fps / substeps)
    for fr in range(1, frames + 1):
        t0 = time.time()
        for s in range(substeps):
            events(sim, fr, s)
            sim.step(dt)
        sim.save(out / f"f_{fr:04d}.npz")
        if log and (fr % 10 == 0 or fr == 1):
            print(f"frame {fr}/{frames} {time.time() - t0:.2f}s flame={float(sim.flame.max()):.2f} "
                  f"smoke={float(sim.smoke.max()):.2f} temp={float(sim.temp.max()):.2f}", flush=True)
