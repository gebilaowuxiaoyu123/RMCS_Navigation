#!/usr/bin/env python3
"""调参过程可视化图表（容器内 cv2 + freetype 渲染，支持中文）。

数据来源：docs/zh-cn/算法组考核/实验记录.md、导航提交作业.md
"""
import math
import os

import cv2
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "assets", "tuning")
OUT = os.path.abspath(OUT)
# 中文字体：容器里用 `apt-get download fonts-wqy-microhei` 取，解包后指定路径
FONT = os.environ.get(
    "CJK_FONT",
    "/tmp/fonts/y/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")
os.makedirs(OUT, exist_ok=True)

S = 1.6                                     # 全局缩放
INK = (33, 35, 40)
MUTED = (128, 116, 107)
LINE = (235, 232, 230)
BLUE = (219, 100, 47)
ORANGE = (31, 138, 234)
RED = (38, 38, 220)
GREEN = (74, 163, 22)
GRAY = (173, 162, 154)
BG = (255, 255, 255)

FT = cv2.freetype.createFreeType2()
FT.loadFontData(FONT, 0)


def canvas(w, h):
    img = np.full((int(h * S), int(w * S), 3), BG, np.uint8)
    return img


def T(img, s, x, y, size=12.5, color=INK, anchor="l", bold=False):
    fs = int(size * S)
    (tw, th), _ = FT.getTextSize(s, fs, -1)
    X = int(x * S) - (tw // 2 if anchor == "m" else tw if anchor == "r" else 0)
    Y = int(y * S)
    FT.putText(img, s, (X, Y), fs, color, -1, cv2.LINE_AA, False)
    if bold:
        FT.putText(img, s, (X + max(1, int(S * 0.6)), Y), fs, color, -1, cv2.LINE_AA, False)
    return tw / S


def R(img, x, y, w, h, fill, alpha=1.0, outline=None):
    p1, p2 = (int(x * S), int(y * S)), (int((x + w) * S), int((y + h) * S))
    if alpha >= 1.0:
        cv2.rectangle(img, p1, p2, fill, -1)
    else:
        sub = img[p1[1]:p2[1], p1[0]:p2[0]]
        sub[:] = (sub * (1 - alpha) + np.array(fill, np.uint8) * alpha).astype(np.uint8)
    if outline:
        cv2.rectangle(img, p1, p2, outline, max(1, int(S)))


def L(img, x1, y1, x2, y2, color=LINE, w=1.0):
    cv2.line(img, (int(x1 * S), int(y1 * S)), (int(x2 * S), int(y2 * S)),
             color, max(1, int(w * S)), cv2.LINE_AA)


def C(img, x, y, r, fill, outline=(255, 255, 255), ow=1.6):
    cv2.circle(img, (int(x * S), int(y * S)), int(r * S), fill, -1, cv2.LINE_AA)
    if outline:
        cv2.circle(img, (int(x * S), int(y * S)), int(r * S), outline,
                   max(1, int(ow * S)), cv2.LINE_AA)


# ═══════════════ 图 1 · 调参轨迹 ═══════════════
DATES = ["9月28日", "9月29日", "9月30日", "10月1日", "10月2日"]
ROWS = [
    ("全局规划器", {0: "NavFn", 1: "Hybrid", 2: "ThetaStar", 3: "Lattice ★"}),
    ("局部膨胀半径", {0: "0.5", 1: "0.35", 2: "0.2 失败", 3: "回 0.5", 4: "0.38 ★"}),
    ("衰减系数 CSF", {0: "0.5", 1: "1.5", 2: "回 0.5", 3: "1.5", 4: "0.55 ★"}),
    ("critical_cost", {0: "120", 1: "300 ★", 2: "回 120", 3: "300 ★"}),
    ("跟线权重", {0: "0.8", 1: "3.0", 2: "回 0.8", 3: "5.2", 4: "7.5 ★"}),
    ("其它", {3: "xy_goal 0.25", 4: "tolerance 0.25\nmax_time 10.0"}),
]
LW, CW, RH = 156, 150, 60
W1, H1 = LW + CW * 5 + 30, 130 + RH * len(ROWS) + 20
img = canvas(W1, H1)
T(img, "调参轨迹：哪个参数在哪天被改过", 0, 26, 21, INK, bold=True)
T(img, "蓝 = 最后留下的　灰 = 试过又退回、或反复试过好几个值", 0, 48, 12, MUTED)
for i, d in enumerate(DATES):
    T(img, d, LW + CW * i + 8, 78, 14, MUTED, bold=True)
L(img, LW - 8, 88, W1 - 24, 88, (203, 198, 193), 1.2)
for r, (name, cells) in enumerate(ROWS):
    y = 106 + r * RH
    if r % 2:
        R(img, 0, y - 14, W1 - 24, RH - 6, (250, 250, 251))
    T(img, name, 6, y + 8, 14, INK, bold=True)
    for i in range(len(DATES)):
        v = cells.get(i, "")
        if not v:
            continue
        cx = LW + CW * i + 8
        for k, ln in enumerate(v.split("\n")):
            keep = "★" in ln
            T(img, ln, cx, y + 8 + k * 19, 13, BLUE if keep else MUTED, bold=keep)
cv2.imwrite(f"{OUT}/tuning_timeline.png", img)
print("图1 完成", img.shape)

# ═══════════════ 图 2 · 两条硬下限 ═══════════════
W2, H2 = 1560, 470
X0, X1, MAXR = 90, 1500, 0.45
p = lambda v: X0 + (v / MAXR) * (X1 - X0)
img = canvas(W2, H2)
T(img, "inflation_radius 的两条硬下限（由 footprint 决定，不是可调项）", 0, 32, 19, INK, bold=True)
T(img, "本车局部 footprint 0.495 m 见方 ⇒ inscribed 0.258 / circumscribed 0.364160", 0, 58, 12.5, MUTED)
AX = 250
L(img, X0, AX, X1, AX, (198, 192, 186), 2)
for v in [0, 0.1, 0.2, 0.3, 0.4]:
    L(img, p(v), AX, p(v), AX + 9, (198, 192, 186), 1.4)
    T(img, f"{v:.1f}", p(v), AX + 32, 12.5, MUTED, "m")
T(img, "m", X1, AX + 32, 12.5, MUTED, "m")
for v, c, l1, l2 in [(0.258, RED, "inscribed_radius 0.258", "低于它：膨胀层退化成二值图，墙边一圈变自由"),
                     (0.364160, ORANGE, "circumscribed_radius 0.364160",
                      "低于它：CostCritic 逐点全 footprint 检查 ⇒ CPU 爆")]:
    L(img, p(v), AX - 96, p(v), AX, c, 1.6)
    T(img, l1, p(v), AX - 104, 13, c, "m", bold=True)
    T(img, l2, p(v), AX - 88, 11.5, c, "m")
USED = [(0.20, "试过 0.20（不合格）", "膨胀层退化，代价只有 0/99/100", False),
        (0.28, "试过 0.28（不合格）", "触发逐点检查：局部代价图 10 → 8.1 Hz", False),
        (0.37, "上游原版 0.37（合格）", "刚好越过下限", True),
        (0.38, "现值 0.38（合格）", "余量只有 0.016 m", True)]
for i, (v, tag, note, ok) in enumerate(USED):
    y = AX + 78 + i * 62
    c = GREEN if ok else RED
    L(img, p(v), AX, p(v), y - 18, c, 1.4)
    C(img, p(v), y - 18, 5.5, c)
    T(img, tag, p(v), y - 34, 13, c, "m", bold=True)
    T(img, note, p(v), y, 11.5, MUTED, "m")
cv2.imwrite(f"{OUT}/tuning_thresholds.png", img)
print("图2 完成", img.shape)

# ═══════════════ 图 3 · 膨胀带梯度 ═══════════════
W3, H3 = 1560, 520
NEAR = 230
CASES = [(0.28, 0.5, "R=0.28  k=0.5", "曾用值", RED),
         (0.38, 0.55, "R=0.38  k=0.55", "现值（未过）", RED),
         (0.38, 1.5, "R=0.38  k=1.5", "建议下限", GREEN),
         (0.38, 3.0, "R=0.38  k=3.0", "Nav2 默认", GREEN)]
vals = [252 * math.exp(-k * (r - 0.258)) for r, k, _, _, _ in CASES]
img = canvas(W3, H3)
T(img, "膨胀带边缘代价 vs near_collision_cost（230）", 0, 32, 19, INK, bold=True)
T(img, "带边缘一旦 ≥ 230，CostCritic 给整条带加的是「平的 +300」⇒ 局部轨迹零梯度、乱飘", 0, 58, 12.5, MUTED)
BX, BY, BW, BH = 110, 110, 1330, 260
vy = lambda v: BY + BH - (v / 300.0) * BH
L(img, BX, BY + BH, BX + BW, BY + BH, (198, 192, 186), 1.6)
for v in [0, 100, 200, 230, 300]:
    L(img, BX, vy(v), BX + BW, vy(v), LINE, 1)
    T(img, str(v), BX - 12, vy(v) + 5, 12, MUTED, "r")
L(img, BX, vy(NEAR), BX + BW, vy(NEAR), ORANGE, 1.8)
T(img, "near_collision_cost = 230", BX + BW, vy(NEAR) - 10, 12.5, ORANGE, "r", bold=True)
for i, ((r, k, lab, tag, col), v) in enumerate(zip(CASES, vals)):
    x = BX + 90 + i * 320
    R(img, x, vy(v), 132, BY + BH - vy(v), col, alpha=0.88)
    T(img, f"{v:.1f}", x + 66, vy(v) - 14, 15, col, "m", bold=True)
    T(img, lab, x + 66, BY + BH + 30, 13, INK, "m", bold=True)
    T(img, tag, x + 66, BY + BH + 52, 12, col, "m")
    bad = v >= NEAR
    T(img, "零梯度" if bad else "有梯度", x + 66, BY + BH + 78, 13,
      RED if bad else GREEN, "m", bold=True)
T(img, "公式：cost(d) = 252 · e^(−k·(d − r_inscribed))　带边缘 d 取 inflation_radius", 0, H3 - 14, 12, MUTED)
cv2.imwrite(f"{OUT}/tuning_gradient.png", img)
print("图3 完成", img.shape)

# ═══════════════ 图 4 · 实测频率 ═══════════════
W4, H4 = 940, 420
img = canvas(W4, H4)
T(img, "实测频率与配置频率", 0, 30, 21, INK, bold=True)
T(img, "2026年10月2日 实车在线实测（ros2 topic hz）", 0, 52, 12, MUTED)
LX, LY, LH = 90, 110, 210
L(img, LX, LY + LH, LX + 700, LY + LH, (198, 192, 186), 1.6)
BARS = [("局部代价图", 10, 8.13), ("全局代价图", 5, 3.28), ("规划 /plan", 1.0, 0.974)]
for i, (lab, cfg, act) in enumerate(BARS):
    x = LX + 50 + i * 230
    hc, ha = (cfg / 10.0) * LH, (act / 10.0) * LH
    R(img, x, LY + LH - hc, 66, hc, (243, 231, 219))
    R(img, x + 78, LY + LH - ha, 66, ha, BLUE if act >= cfg * 0.97 else ORANGE, alpha=0.9)
    T(img, f"配置 {cfg}", x + 33, LY + LH - hc - 10, 12, MUTED, "m")
    T(img, f"{act}", x + 111, LY + LH - ha - 10, 13, INK, "m", bold=True)
    T(img, lab, x + 72, LY + LH + 26, 12.5, INK, "m", bold=True)
T(img, "Hz", LX, LY - 10, 12, MUTED)
T(img, "浅色 = 配置值　深色 = 实测值", LX, LY + LH + 56, 12, MUTED)
cv2.imwrite(f"{OUT}/tuning_frequency.png", img)
print("图4 完成", img.shape)

# ═══════════════ 图 5 · 大事件（只按时间排列，不做因果连线） ═══════════════
EV = [
    ("9月29日", "窄口三刀", "前两刀毫无反应", ORANGE),
    ("9月30日", "「摆」不在规划层", "改成 normal", RED),
    ("10月1日", "两种「整栈起不来」", "plugin 清空、参数写错", RED),
    ("10月1日", "重定位两个 bug", "初值错 20 m", BLUE),
    ("10月2日", "膨胀半径的连锁", "0.28 改 0.38", GREEN),
]
W5, H5 = 1000, 275
img = canvas(W5, H5)
T(img, "调参期发生的几件事", 0, 26, 21, INK, bold=True)
T(img, "只按时间排列，事件之间没有因果关系", 0, 48, 12, MUTED)
AXIS = 92
L(img, 30, AXIS, 970, AXIS, (203, 198, 193), 1.6)
step = 940.0 / len(EV)
CW5 = step - 16
for i, (d, t1, t2, col) in enumerate(EV):
    x = 30 + step * i
    C(img, x + CW5 / 2, AXIS, 5, col)
    R(img, x, AXIS + 18, CW5, 116, (250, 250, 251), outline=(235, 232, 230))
    R(img, x, AXIS + 18, CW5, 4, col)
    T(img, d, x + 10, AXIS + 44, 12.5, col, bold=True)
    T(img, t1, x + 10, AXIS + 68, 12.5, INK, bold=True)
    for k, ln in enumerate([t2[j:j + 12] for j in range(0, len(t2), 12)]):
        T(img, ln, x + 10, AXIS + 90 + k * 17, 11.5, MUTED)
cv2.imwrite(f"{OUT}/tuning_events.png", img)
print("图5 完成", img.shape)
