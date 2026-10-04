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
DATES = ["09-28", "09-29", "09-30", "10-01", "10-02"]
ROWS = [
    ("全局规划器 plugin", {1: [("NavFn → SmacHybrid", "churn")], 2: [("→ ThetaStar", "churn")],
                        3: [("→ SmacLattice  ★ 定案", "keep")]}),
    ("inflation_radius（全局）", {1: [("0.5 → 0.35", "back")], 2: [("回 0.5", "back")],
                              3: [("0.5 → 0.30", "keep")], 4: [("→ 0.28", "keep")]}),
    ("inflation_radius（局部）", {1: [("0.5 → 0.35", "back")], 2: [("回 0.5", "back")],
                              3: [("0.5 → 0.20（失败）膨胀层退化", "back")], 4: [("0.38（余量 0.016）", "keep")]}),
    ("cost_scaling_factor", {1: [("0.5 → 3.0 → 1.5", "churn")], 2: [("1.5 → 1.2 → 0.5", "back")],
                             3: [("局部 1.5 → 0.5", "back")],
                             4: [("全局 → 1.0 / 局部 0.55", "keep")]}),
    ("CostCritic.critical_cost", {1: [("120 → 300", "keep")], 2: [("回 120", "back")],
                                  3: [("120 → 300 ★ 定案", "keep")]}),
    ("PathAlignCritic.cost_weight", {1: [("0.8 → 3.0", "churn")], 2: [("回 0.8", "back")],
                                     3: [("0.8 → 5.2", "keep")], 4: [("→ 7.5", "keep")]}),
    ("non_straight_penalty", {3: [("1.05 → 1.5", "keep")], 4: [("1.5 → 2.0 → 2.4", "keep")]}),
    ("同一批的其它改动", {2: [("smoother 是死配置，整批回退", "back")],
                    3: [("xy_goal_tol 0.1→0.25", "keep"), ("tolerance 0.5→0.25", "keep"),
                        ("footprint 试探后回退", "back")],
                    4: [("retrospective 0.04", "keep"), ("max_planning_time → 10.0", "keep")]}),
]
CW, LWD, RH = 244, 340, 78
W1, H1 = LWD + CW * len(DATES) + 30, 124 + RH * len(ROWS) + 56
img = canvas(W1, H1)
T(img, "调参轨迹：谁在哪天被改过、改成了什么", 0, 30, 19, INK, bold=True)
T(img, "灰 = 试过之后回退　橙 = 反复试值　蓝 = 定案保留　★ = 最终进 motion.yaml　"
        "（数据来源：实验记录.md / 导航提交作业.md）", 0, 56, 12.5, MUTED)
T(img, "09-28 基线：plugin=NavFn　全局 inflation 0.5　CSF 0.5　critical_cost 120　"
        "PathAlign 0.8　xy_goal_tol 0.1　non_straight 1.05", 0, 78, 11.5, (150, 143, 137))
for i, d in enumerate(DATES):
    T(img, d, LWD + CW * i + 16, 116, 13.5, MUTED, bold=True)
L(img, LWD - 16, 128, W1 - 30, 128, (203, 198, 193), 1.2)
for r, (name, cells) in enumerate(ROWS):
    y = 146 + r * RH
    if r % 2:
        R(img, 0, y - 16, W1 - 30, RH - 8, (250, 250, 251))
    T(img, name, 0, y + 6, 13, INK, bold=True)
    for i in range(len(DATES)):
        if i not in cells:
            continue
        cx = LWD + CW * i + 16
        items = cells[i]
        show = items[:2]
        yy = y - 14
        for txt, st in show:
            col, bg = {"keep": (BLUE, (246, 240, 235)), "back": (GRAY, (245, 245, 246)),
                       "churn": (ORANGE, (240, 248, 253))}[st]
            tw = 0
            for ln in txt.split("\n"):
                (w_, _), _ = FT.getTextSize(ln, int(11.5 * S), -1)
                tw = max(tw, w_ / S)
            R(img, cx, yy, tw + 20, 26, bg)
            R(img, cx, yy, 4, 26, col)
            T(img, txt, cx + 12, yy + 18, 11.5, col)
            yy += 32
        if len(items) > 2:
            T(img, f"…共 {len(items)} 项", cx + 4, yy + 14, 11, MUTED)
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

# ═══════════════ 图 4 · 频率 / 过载 ═══════════════
W4, H4 = 1560, 500
img = canvas(W4, H4)
T(img, "「卡顿」的实测证据：不是频率配高了，是系统追不上", 0, 32, 19, INK, bold=True)
T(img, "2026-10-02 实车在线实测（ros2 topic hz / ps）", 0, 58, 12.5, MUTED)
LX, LY, LH = 90, 120, 250
L(img, LX, LY + LH, LX + 620, LY + LH, (198, 192, 186), 1.6)
BARS = [("局部代价图", 10, 8.13), ("全局代价图", 5, 3.28), ("/plan", 1.0, 0.974)]
for i, (lab, cfg, act) in enumerate(BARS):
    x = LX + 60 + i * 200
    hc, ha = (cfg / 10.0) * LH, (act / 10.0) * LH
    R(img, x, LY + LH - hc, 62, hc, (243, 231, 219))
    R(img, x + 70, LY + LH - ha, 62, ha, BLUE if act >= cfg * 0.97 else ORANGE,
      alpha=0.9)
    T(img, f"配置 {cfg}", x + 31, LY + LH - hc - 10, 12, MUTED, "m")
    T(img, f"{act}", x + 101, LY + LH - ha - 10, 13, INK, "m", bold=True)
    T(img, lab, x + 66, LY + LH + 26, 12.5, INK, "m", bold=True)
T(img, "Hz", LX, LY - 10, 12, MUTED)
T(img, "灰 = 配置值　蓝/橙 = 实测值　⚠ 两个代价图都没追上配置", LX + 620, LY + LH + 56, 12, MUTED, "r")
texts = [("rmcs_local_map 每帧全量重算 402×402（16.1 m @ 0.04）", 0)]
RX, RY = 810, 130
T(img, "同机 CPU 占用（ps 排序，%CPU）", RX, RY - 12, 13.5, INK, bold=True)
CPU = [("rmcs_executor", 36.3, BLUE), ("python3 (foxglove 等)", 27.9, GRAY),
       ("rmcs_local_map", 27.2, ORANGE), ("livox_ros_driver", 12.8, GRAY),
       ("pointlio_mapping", 8.7, GRAY)]
for i, (n, v, c) in enumerate(CPU):
    y = RY + 12 + i * 44
    T(img, n, RX, y + 14, 12.5, INK)
    R(img, RX + 250, y, (v / 40.0) * 380, 22, c, alpha=0.9)
    T(img, f"{v}%", RX + 250 + (v / 40.0) * 380 + 10, y + 17, 12, MUTED)
T(img, "⇒ 结论：不是把频率配高，而是系统过载、追不上配的频率", 0, H4 - 18, 13, INK, bold=True)
cv2.imwrite(f"{OUT}/tuning_frequency.png", img)
print("图4 完成", img.shape)

# ═══════════════ 图 5 · 大事件时间轴 ═══════════════
EV = [("09-29", ["窄口三刀", "inflation → CSF → critical_cost"], ["前两刀毫无反应", "第三刀才撞出真正的耦合"], ORANGE),
      ("09-30", ["「摆」不在规划层", "smoother 是死配置"], ["整批调参回退", "改为先定机制再定参数"], RED),
      ("10-01", ["两种「整栈起不来」", "plugin 被清空 / 参数写成整数"], ["从 unconfigured 倒查", "此后改完先扫参数类型"], RED),
      ("10-01", ["重定位两个 bug 叠加", "fitness 0.2832 → 0.0361"], ["ICP 只搜 yaw", "初值错 20 m 必滑向假解"], BLUE),
      ("10-02", ["三道硬阈值定案", "inflation 两条下限 + CSF 上限"], ["一个参数同时造成", "掉频与零梯度"], GREEN),
      ("10-03", ["Lattice 默认参数穿墙", "残留进程会「抢答」实验"], ["裸算法对比先做", "「只有一个 action 服务器」"], BLUE)]
W5, H5 = 1560, 520
img = canvas(W5, H5)
T(img, "调参期「大事件」时间轴", 0, 32, 19, INK, bold=True)
T(img, "每个事件的 现象 / 后果 / 原因 / 对后续调参的影响，详见正文 §4.2", 0, 58, 12.5, MUTED)
AXIS = 265
L(img, 60, AXIS, 1520, AXIS, (198, 192, 186), 2.2)
step = 1460 / len(EV)
for i, (d, title, impact, col) in enumerate(EV):
    x = 60 + step * (i + 0.5)
    up = i % 2 == 0
    C(img, x, AXIS, 7, col)
    T(img, d, x, AXIS + 26, 12, MUTED, "m", bold=True)
    h_title, h_imp, gap = len(title) * 22, len(impact) * 19, 8
    block = h_title + gap + h_imp
    if up:
        y0 = AXIS - 78 - block          # 文字块顶
        L(img, x, AXIS, x, y0 + block + 10, col, 1.4)
        for j, s in enumerate(title):
            T(img, s, x, y0 + 16 + j * 22, 13, INK, "m", bold=(j == 0))
        for j, s in enumerate(impact):
            T(img, s, x, y0 + h_title + gap + 15 + j * 19, 11.5, MUTED, "m")
    else:
        y0 = AXIS + 78
        L(img, x, AXIS, x, y0 - 12, col, 1.4)
        for j, s in enumerate(title):
            T(img, s, x, y0 + 16 + j * 22, 13, INK, "m", bold=(j == 0))
        for j, s in enumerate(impact):
            T(img, s, x, y0 + h_title + gap + 15 + j * 19, 11.5, MUTED, "m")
cv2.imwrite(f"{OUT}/tuning_events.png", img)
print("图5 完成", img.shape)
