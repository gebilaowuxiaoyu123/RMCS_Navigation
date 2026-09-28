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
    ap.add_argument('paths', nargs='*', help='格式 "标签:路径文件"，可给多个（也可以不给）')
    ap.add_argument('--map', default='rmuc',
                    help='maps/ 下的地图名（默认 rmuc，会读 rmuc.yaml）')
    ap.add_argument('--scale', type=float, default=3.0, help='放大倍数（默认 3）')
    ap.add_argument('--turn-threshold', type=float, default=5.0,
                    help='算作转折的夹角阈值(度)，默认 5')
    ap.add_argument('--title', default='', help='可选：图片底部居中的标题')
    ap.add_argument('--grid', type=float, default=0.0,
                    help='叠加世界坐标网格，值为间距(米)，如 2 表示每 2 米一条线')
    ap.add_argument('--mark', default='',
                    help='标注候选目标点，格式 "x1,y1;x2,y2"，会画带序号的黄点')
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

    # 世界坐标网格：叠加后可以直接从图上读出任意点的 (x, y)
    if args.grid > 0:
        step = args.grid
        fsc = 0.4 * max(1, s / 3)
        pad = int(4 * max(1, s / 3))

        # 网格线走半透明混合：白底变浅灰、黑障碍变深灰，两边都不糊
        overlay = canvas.copy()
        gx = [math.ceil(ox / step) * step]
        while gx[-1] <= ox + w * res:
            gx.append(round(gx[-1] + step, 9))
        gy = [math.ceil(oy / step) * step]
        while gy[-1] <= oy + h * res:
            gy.append(round(gy[-1] + step, 9))
        for x in gx:
            px, _ = to_px(x, 0)
            cv2.line(overlay, (px, 0), (px, canvas.shape[0]), (60, 60, 60), 1)
        for y in gy:
            _, py = to_px(0, y)
            cv2.line(overlay, (0, py), (canvas.shape[1], py), (60, 60, 60), 1)
        cv2.addWeighted(overlay, 0.40, canvas, 0.60, 0, canvas)

        # 坐标标签垫白底，保证压在障碍上也读得清
        def label(text, anchor, up=True):
            tw, th = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fsc, 1)[0]
            x0 = max(0, min(canvas.shape[1] - tw - 2 * pad, anchor[0] + 2))
            y0 = anchor[1] - th - 2 * pad if up else anchor[1] + pad
            y0 = max(0, min(canvas.shape[0] - th - 2 * pad, y0))
            cv2.rectangle(canvas, (x0, y0), (x0 + tw + 2 * pad, y0 + th + 2 * pad),
                          (255, 255, 255), -1)
            cv2.putText(canvas, text, (x0 + pad, y0 + pad + th),
                        cv2.FONT_HERSHEY_SIMPLEX, fsc, (150, 60, 0), 1, cv2.LINE_AA)

        for x in gx:
            px, _ = to_px(x, 0)
            label(f'{x:g}', (px, 0), up=False)
        for y in gy:
            _, py = to_px(0, y)
            label(f'{y:g}', (0, py), up=True)

        print(f'已叠加坐标网格：间距 {step:g} m，'
              f'x∈[{ox:g}, {ox + w * res:.1f}]  y∈[{oy:g}, {oy + h * res:.1f}]')

    # 候选目标点标注
    if args.mark:
        for i, item in enumerate(args.mark.split(';'), 1):
            item = item.strip()
            if not item:
                continue
            try:
                mx, my = (float(v) for v in item.split(','))
            except ValueError:
                print(f'  ⚠️ 跳过标注 "{item}"（格式应为 x,y）')
                continue
            mp = to_px(mx, my)
            cv2.circle(canvas, mp, int(8 * max(1, s / 3)), (0, 0, 0), 2)
            cv2.circle(canvas, mp, int(4 * max(1, s / 3)), (0, 255, 255), -1)
            cv2.putText(canvas, str(i), (mp[0] + 12, mp[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7 * max(1, s / 3),
                        (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(canvas, str(i), (mp[0] + 12, mp[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7 * max(1, s / 3),
                        (0, 255, 255), 1, cv2.LINE_AA)
            print(f'  标注 {i}: world({mx:g}, {my:g})  ->  像素 {mp}')

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

    # 图例：先铺一层半透明白底，保证压在障碍物上也能看清
    fs = 0.7 * max(1, s / 3)
    lh = int(30 * max(1, s / 3))
    pad = int(8 * max(1, s / 3))
    lines = [(f'{label}: {length:.1f}m  {turns} turns  {density:.2f}/m', color)
             for label, color, npts, length, turns, density in legend]
    if lines:
        tw = max(cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, fs, 2)[0][0]
                 for t, _ in lines)
        bw, bh = tw + 2 * pad, lh * len(lines) + 2 * pad
        roi = canvas[0:bh, 0:bw]
        roi[:] = (roi * 0.25 + 255 * 0.75).astype('uint8')
        cv2.rectangle(canvas, (0, 0), (bw, bh), (0, 0, 0), 1)
        for i, (text, color) in enumerate(lines):
            cv2.putText(canvas, text,
                        (pad, pad + i * lh + int(lh * 0.72)),
                        cv2.FONT_HERSHEY_SIMPLEX, fs, color, 2, cv2.LINE_AA)

    # 标题：底部居中，同样铺白底
    if args.title:
        tfs = 0.8 * max(1, s / 3)
        tw, th = cv2.getTextSize(args.title, cv2.FONT_HERSHEY_SIMPLEX, tfs, 2)[0]
        x0 = max(0, (canvas.shape[1] - tw) // 2 - pad)
        y1 = canvas.shape[0]
        y0 = y1 - th - 3 * pad
        roi = canvas[y0:y1, x0:min(canvas.shape[1], x0 + tw + 2 * pad)]
        roi[:] = (roi * 0.25 + 255 * 0.75).astype('uint8')
        cv2.rectangle(canvas, (x0, y0),
                      (min(canvas.shape[1] - 1, x0 + tw + 2 * pad), y1 - 1),
                      (0, 0, 0), 1)
        cv2.putText(canvas, args.title, (x0 + pad, y1 - 2 * pad),
                    cv2.FONT_HERSHEY_SIMPLEX, tfs, (0, 0, 0), 2, cv2.LINE_AA)

    outdir = os.path.dirname(args.output)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    cv2.imwrite(args.output, canvas)
    print(f'\n已保存: {args.output}')


if __name__ == '__main__':
    main()
