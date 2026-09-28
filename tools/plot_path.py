#!/usr/bin/env python3
"""把规划器输出的路径叠加到场地地图上，生成对比图。

## 它做什么

    底图（maps/*.png）  +  路径（规划器运行结果）  =  带路径的对比图

⚠️ 底图由 `maps/<名字>.yaml` 决定，但**路径必须来自实际运行**
（`ros2 action send_goal /compute_path_to_pose ...` 的输出）。
改 yaml 只能换底图，不会凭空产生路径。

## 特点

- **自动读 yaml**：分辨率、原点、图片名都从 `maps/xxx.yaml` 读，
  所以你改了 yaml（换地图/改分辨率），本脚本**自动跟随**，不用改代码。
- **支持多路径叠加**：同一张底图上画多条路径，便于换规划器前后对比。

## 用法

    # 先跑规划，把输出存下来
    ros2 action send_goal /compute_path_to_pose nav2_msgs/action/ComputePathToPose \\
      "{goal: {header: {frame_id: world}, pose: {position: {x: 20.0, y: 0.0, z: 0.0}}}, use_start: false}" \\
      > /tmp/plan_navfn.txt

    # 画一张
    python3 tools/plot_path.py assets/plan_navfn.png "NavFn:/tmp/plan_navfn.txt"

    # 换规划器后再存一份，两张并排画在一起对比
    python3 tools/plot_path.py assets/plan_compare.png \\
      "NavFn:/tmp/plan_navfn.txt" "Smac2D:/tmp/plan_smac2d.txt"

    # 换地图底图（会读对应 yaml 的参数）
    python3 tools/plot_path.py assets/plan_zhandui.png --map 战队 "NavFn:/tmp/plan.txt"

    # 调放大倍数
    python3 tools/plot_path.py out.png --scale 4 "NavFn:/tmp/plan.txt"
"""
import argparse
import math
import os
import re

import cv2

# 依赖栈里的 maps 目录
MAPS_DIR = ('/workspaces/RMCS/rmcs_ws/src/rmcs-navigation-deps/'
            'rmcs-navigation/maps')

# 依次用于多条路径的颜色（BGR）
COLORS = [
    (60, 60, 220),    # 红
    (220, 160, 40),   # 蓝
    (40, 180, 60),    # 绿
    (200, 40, 200),   # 紫
    (0, 200, 200),    # 黄
]


def read_map_yaml(name):
    """从 maps/<name>.yaml 读取底图与几何参数。

    返回 (png路径, resolution, origin_x, origin_y)
    """
    yml = os.path.join(MAPS_DIR, f'{name}.yaml')
    if not os.path.exists(yml):
        avail = sorted(f[:-5] for f in os.listdir(MAPS_DIR) if f.endswith('.yaml'))
        raise SystemExit(f'找不到 {yml}\n可用的地图名: {", ".join(avail)}')

    cfg = {}
    for line in open(yml, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        k, _, v = line.partition(':')
        cfg[k.strip()] = v.strip()

    png = os.path.join(MAPS_DIR, cfg['image'])
    if not os.path.exists(png):
        raise SystemExit(f'{yml} 指向的图片不存在: {png}')

    origin = cfg['origin'].strip('[]').split(',')
    return png, float(cfg['resolution']), float(origin[0]), float(origin[1])


def parse_path(txt):
    """从 `ros2 action send_goal` 的输出里提取 result.path.poses"""
    idx = txt.find('Result:')
    body = txt[idx:] if idx >= 0 else txt
    pts = []
    for m in re.finditer(
        r'position:\s*\n\s*x:\s*([-\d.eE+]+)\s*\n\s*y:\s*([-\d.eE+]+)', body
    ):
        pts.append((float(m.group(1)), float(m.group(2))))
    # 第一个 position 是 goal 本身，后面才是 path.poses
    return pts[1:] if len(pts) > 1 else pts


def path_stats(pts, turn_deg=5.0):
    length = sum(
        math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1])
        for k in range(1, len(pts))
    )
    turns = 0
    for k in range(2, len(pts)):
        a1 = math.atan2(pts[k - 1][1] - pts[k - 2][1], pts[k - 1][0] - pts[k - 2][0])
        a2 = math.atan2(pts[k][1] - pts[k - 1][1], pts[k][0] - pts[k - 1][0])
        d = abs(math.degrees(a2 - a1))
        if min(d, 360 - d) > turn_deg:
            turns += 1
    density = turns / length if length > 0 else 0.0
    return length, turns, density


def main():
    ap = argparse.ArgumentParser(
        description='把规划路径叠加到场地地图上（底图参数自动从 yaml 读）')
    ap.add_argument('output', help='输出的 PNG 路径')
    ap.add_argument('paths', nargs='+', help='格式 "标签:路径文件"，可给多个')
    ap.add_argument('--map', default='rmuc',
                    help='maps/ 下的地图名（默认 rmuc，会读 rmuc.yaml）')
    ap.add_argument('--scale', type=float, default=3.0, help='放大倍数（默认 3）')
    ap.add_argument('--turn-threshold', type=float, default=5.0,
                    help='算作转折的夹角阈值(度)，默认 5')
    args = ap.parse_args()

    png, res, ox, oy = read_map_yaml(args.map)
    print(f'底图      : {os.path.basename(png)}')
    print(f'几何参数  : resolution={res}  origin=({ox}, {oy})  <- 读自 {args.map}.yaml')

    img = cv2.imread(png, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f'读不了图片: {png}')
    h, w = img.shape
    print(f'尺寸      : {w}x{h} px  ->  世界 {w*res:.1f} x {h*res:.1f} m')

    s = args.scale
    canvas = cv2.resize(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR),
                        (int(w * s), int(h * s)),
                        interpolation=cv2.INTER_NEAREST)

    def to_px(x, y):
        return int(round((x - ox) / res * s)), int(round((h - 1 - (y - oy) / res) * s))

    print()
    legend = []
    for i, item in enumerate(args.paths):
        label, _, pf = item.partition(':')
        if not pf:
            print(f'  ⚠️ 跳过 "{item}"（格式应为 标签:路径文件）')
            continue
        if not os.path.exists(pf):
            print(f'  ⚠️ 跳过 {label}（文件不存在: {pf}）')
            continue

        pts = parse_path(open(pf, encoding='utf-8', errors='replace').read())
        if not pts:
            print(f'  ⚠️ 跳过 {label}（未解析出路径点）')
            continue

        color = COLORS[i % len(COLORS)]
        length, turns, density = path_stats(pts, args.turn_threshold)

        px = [to_px(x, y) for x, y in pts]
        for j in range(1, len(px)):
            cv2.line(canvas, px[j - 1], px[j], color, 2, cv2.LINE_AA)
        cv2.circle(canvas, px[0], 7, (0, 200, 0), -1)      # 起点 绿
        cv2.circle(canvas, px[-1], 7, (0, 0, 255), -1)     # 终点 红

        legend.append((label, color, len(pts), length, turns, density))
        print(f'  {label:<10s} {len(pts):>4d} 点  {length:6.2f} m  '
              f'{turns:>4d} 转折  {density:5.2f} turns/m')

    # 图例
    for i, (label, color, npts, length, turns, density) in enumerate(legend):
        cv2.putText(canvas, f'{label}: {length:.1f}m  {turns} turns  {density:.2f}/m',
                    (10, int(25 + i * 30 * max(1, s / 3))),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7 * max(1, s / 3),
                    color, 2, cv2.LINE_AA)

    outdir = os.path.dirname(args.output)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    cv2.imwrite(args.output, canvas)
    print(f'\n已保存: {args.output}')


if __name__ == '__main__':
    main()
