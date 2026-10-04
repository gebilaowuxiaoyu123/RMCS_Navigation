#!/usr/bin/env python3
"""用地图 PNG 校验每条路径是否压到障碍/未知格（穿墙检查）。

阈值按 map yaml：occupied_thresh 0.65 / free_thresh 0.196（trinary）
  occ = (255-gray)/255 >= 0.65      → 障碍
  unk = free_thresh < occ_val < occupied_thresh
"""
import math
import os
import sys

import cv2
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plot_path import parse_path  # noqa: E402

SRC = os.environ.get(
    "RMCS_MAPS_DIR",
    "/workspaces/RMCS/rmcs_ws/src/rmcs-navigation-deps/rmcs-navigation/maps")
WORK = os.environ.get("PLANCMP_WORK", "/tmp/plancmp")
MAP = os.environ.get("PLANCMP_MAP", "default")


def load(mapname):
    cfg = yaml.safe_load(open(f"{SRC}/{mapname}.yaml", encoding="utf-8"))
    img = cv2.imread(f"{SRC}/{cfg['image']}", cv2.IMREAD_GRAYSCALE)
    return img, float(cfg["resolution"]), float(cfg["origin"][0]), float(cfg["origin"][1])


def classify(img, res, ox, oy, x, y):
    h, w = img.shape
    col = int((x - ox) / res)
    row = (h - 1) - int((y - oy) / res)
    if not (0 <= col < w and 0 <= row < h):
        return "out"
    g = int(img[row, col])
    occ = (255 - g) / 255.0
    if occ >= 0.65:
        return "OCC"
    if occ > 0.196:
        return "UNK"
    return "free"


def check(mapname, tag, path):
    img, res, ox, oy = load(mapname)
    pts = parse_path(open(path, encoding="utf-8").read())
    n_occ = n_unk = 0
    worst = []
    for k in range(1, len(pts)):
        (x0, y0), (x1, y1) = pts[k - 1], pts[k]
        d = math.hypot(x1 - x0, y1 - y0)
        steps = max(1, int(d / (res * 0.25)))          # 每 1/4 格取一点
        for i in range(steps + 1):
            t = i / steps
            c = classify(img, res, ox, oy, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            if c == "OCC":
                n_occ += 1
                if len(worst) < 3:
                    worst.append((round(x0 + (x1 - x0) * t, 2), round(y0 + (y1 - y0) * t, 2)))
            elif c == "UNK":
                n_unk += 1
    flag = "❌ 压障碍" if n_occ else ("⚠ 走未知区" if n_unk else "✅ 全在自由区")
    print(f"{tag:<28}{len(pts):>4} 点  压障碍采样 {n_occ:>5}  未知区 {n_unk:>5}   {flag}"
          + (f"  例:{worst}" if worst else ""))


NAMES = ["navfn", "thetastar", "smac2d", "hybrid", "lattice"]
print("########## 战队（往返拼接）##########")
for n in NAMES:
    check("战队", f"  {n}", f"{WORK}/{MAP}/往返/plan_{n}.txt")
print("########## RMUC ##########")
for n in NAMES:
    check("rmuc", f"  {n}", f"{WORK}/{MAP}/rmuc/plan_{n}.txt")
