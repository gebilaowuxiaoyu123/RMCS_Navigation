#!/usr/bin/env python3
"""把去程 / 回程两条路径拼成「往返轨迹」，写成 plot_path.py 能解析的格式。"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plot_path import parse_path  # noqa: E402

WORK = os.environ.get("PLANCMP_WORK", "/tmp/plancmp")
MAP = os.environ.get("PLANCMP_MAP", "default")      # 每次重跑的整套结果放在 <WORK>/<MAP>/
A2B = f"{WORK}/{MAP}/战队_0x0_to_4x2"          # (0,0) -> (4,2)
B2A = f"{WORK}/{MAP}/战队_4x2_to_0x0"          # (4,2) -> (0,0)
OUT = f"{WORK}/{MAP}/往返"
os.makedirs(OUT, exist_ok=True)

NAMES = ["navfn", "thetastar", "smac2d", "hybrid", "lattice"]


def load(d, n):
    p = f"{d}/plan_{n}.txt"
    if not os.path.exists(p):
        return None
    pts = parse_path(open(p, encoding="utf-8").read())
    return pts if len(pts) > 1 else None


def length(pts):
    return sum(math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1])
               for k in range(1, len(pts)))


def dump(pts, path):
    """写成 ros2 action send_goal 那种带 Result: 的文本，供 plot_path 解析。"""
    lines = ["Result:", "  path:", "    poses:"]
    for x, y in pts:
        lines += ["    - pose:", "        position:",
                  f"          x: {x:.9f}", f"          y: {y:.9f}", "          z: 0.0"]
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


print(f"{'规划器':<13}{'去程(m)':>9}{'回程(m)':>9}{'往返(m)':>9}{'点数':>7}  备注")
print("-" * 62)
for n in NAMES:
    a = load(A2B, n)
    b = load(B2A, n)
    note = ""
    if a and b:
        # 去掉衔接处的重复点
        trip = a + b[1:]
    elif b:
        trip = b
        note = "去程规划失败，仅回程"
    elif a:
        trip = a
        note = "回程规划失败，仅去程"
    else:
        print(f"{n:<13}  —  两个方向都没数据")
        continue
    dump(trip, f"{OUT}/plan_{n}.txt")
    la = f"{length(a):.2f}" if a else "—"
    lb = f"{length(b):.2f}" if b else "—"
    print(f"{n:<13}{la:>9}{lb:>9}{length(trip):>9.2f}{len(trip):>7}  {note}")

print(f"\n往返轨迹已写入 {OUT}/plan_*.txt")
