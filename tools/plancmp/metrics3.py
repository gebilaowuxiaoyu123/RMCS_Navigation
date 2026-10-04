#!/usr/bin/env python3
"""两张地图的 5 规划器指标对比（战队图用往返轨迹）。"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plot_path import parse_path  # noqa: E402

WORK = os.environ.get("PLANCMP_WORK", "/tmp/plancmp")
MAP = os.environ.get("PLANCMP_MAP", "default")

NAMES = ["navfn", "thetastar", "smac2d", "hybrid", "lattice"]
LABEL = {"navfn": "NavFn", "thetastar": "ThetaStar", "smac2d": "Smac2D",
         "hybrid": "SmacHybrid", "lattice": "SmacLattice"}


def dedup(p):
    o = []
    for q in p:
        if o and math.hypot(q[0] - o[-1][0], q[1] - o[-1][1]) < 1e-4:
            continue
        o.append(q)
    return o


def angs(pts):
    a = []
    for k in range(2, len(pts)):
        a1 = math.atan2(pts[k - 1][1] - pts[k - 2][1], pts[k - 1][0] - pts[k - 2][0])
        a2 = math.atan2(pts[k][1] - pts[k - 1][1], pts[k][0] - pts[k - 1][0])
        d = math.degrees(a2 - a1)
        while d > 180:
            d -= 360
        while d < -180:
            d += 360
        a.append(abs(d))
    return a


def curv(pts):
    ks = []
    for k in range(1, len(pts) - 1):
        x1, y1 = pts[k - 1]
        x2, y2 = pts[k]
        x3, y3 = pts[k + 1]
        a = math.hypot(x2 - x1, y2 - y1)
        b = math.hypot(x3 - x2, y3 - y2)
        c = math.hypot(x3 - x1, y3 - y1)
        if a < 1e-6 or b < 1e-6 or c < 1e-6:
            continue
        area = abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)) / 2
        ks.append(4 * area / (a * b * c))
    return sorted(ks)


MAPS = [("RMUC  (0,0) -> (20,0)  单程", f"{WORK}/{MAP}/rmuc"),
        ("战队  (0,0) <-> (4,2)  往返", f"{WORK}/{MAP}/往返")]

for title, d in MAPS:
    print(f"\n##### {title} #####")
    print(f"{'规划器':<12}{'长度(m)':>9}{'转弯':>6}{'转弯/m':>9}"
          f"{'最大转角':>10}{'转角总和':>10}{'急转>45':>8}{'曲率max':>11}{'曲率P95':>11}")
    print("-" * 88)
    for n in NAMES:
        # 与图例口径一致：不做去重（去重会让 Lattice 少算 1 次转弯）
        pts = parse_path(open(f"{d}/plan_{n}.txt", encoding="utf-8").read())
        a = angs(pts)
        ks = curv(pts)
        L = sum(math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1])
                for k in range(1, len(pts)))
        t = sum(1 for x in a if x > 5)
        sh = sum(1 for x in a if x > 45)
        print(f"{LABEL[n]:<12}{L:>9.2f}{t:>6}{t / L if L else 0:>9.2f}"
              f"{(max(a) if a else 0):>9.1f}°{sum(a):>9.0f}°{sh:>8}"
              f"{(ks[-1] if ks else 0):>10.2f}/m{(ks[int(len(ks) * 0.95)] if ks else 0):>10.2f}/m")
print("\n注：五个规划器均为 Nav2 默认参数，只有 Lattice 改了一处 change_penalty: 0.05 -> 1.0")
print("    （默认值下 Lattice 会给出穿墙路径，详见文档；其余参数与四个规划器全部默认）")
print("    往返表的『最大转角』含终点掉头本身（去程→回程必然反向），属真实工况。")
