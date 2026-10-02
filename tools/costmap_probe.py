#!/usr/bin/env python3
"""读代价地图 + 回读膨胀参数 —— 用于调 inflation 时看清实际效果。

## ⚠️ 取值域：发布出来的是 0~100，不是 0~254（2026-10-02 修正）

Nav2 内部代价是 0~254，但 `Costmap2DPublisher` 在**发布前会折到
`nav_msgs/OccupancyGrid` 的 0~100 标度**，并把两个特殊值钉死：

    内部 254（致命障碍 LETHAL_OBSTACLE）        -> 发布 100
    内部 253（内切 INSCRIBED_INFLATED_OBSTACLE）-> 发布  99
    内部   0                                     -> 发布   0
    未知                                         -> 发布  -1
    其余内部代价 c                               -> 发布 round(c / 255 * 100)

**本文件早期版本误用了 254 / 253 做判定**，于是永远匹配不上，
报出「致命 0 / 内切 0」—— 会让人**误以为地图上没有障碍**。已修正。

（`ros2 topic echo` 看到的就是 `int8[]`：-1 = 未知，0~100 = 代价。
 早期说明里“254 显示成 -2”是错的 —— 那是**内部**表示，不是发布值。）

实测（2026-10-02，全局代价图 37730 格）：
`min=0  max=100  取值集合 {0, 89, 92, 93, 96, 99, 100}`

## 怎么判断“膨胀层有没有梯度”（本工具的主要用途）

看输出的「取值集合」：
  - **只有 0 / 99 / 100** ⇒ 膨胀层**退化成二值图**（没有梯度）
  - **有一串中间值**（如 89 92 93 96）⇒ 梯度正常

## 用法

    # 默认查全局代价地图
    python3 tools/costmap_probe.py

    # 查局部代价地图
    python3 tools/costmap_probe.py --topic /local_costmap/costmap

    # 查指定坐标（世界系，可给多个）
    python3 tools/costmap_probe.py --points 0,0 20,0 10,0 -3,0

    # 顺便回读膨胀参数（检"参数假生效"）
    python3 tools/costmap_probe.py --node /global_costmap/global_costmap
"""
import argparse
import struct
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from nav_msgs.msg import OccupancyGrid

# ⚠️ 这是【发布后】的 OccupancyGrid 标度（0~100），不是 Nav2 内部 0~254！
LETHAL = 100        # 内部 254（LETHAL_OBSTACLE）
INSCRIBED = 99      # 内部 253（INSCRIBED_INFLATED_OBSTACLE）
NO_INFO = -1        # 未知
# 内部值 <-> 发布值 的换算（两个特殊值被钉死，不能用它反推）
COST_SCALE = 100 / 255.0

# 默认查询点：(x, y, 说明)
DEFAULT_POINTS = [
    (0.0, 0.0, '机器人初始位置'),
    (20.0, 0.0, '之前的候选终点'),
    (10.0, 0.0, '场地中央'),
    (12.0, 3.0, '候选点'),
    (12.0, -3.0, '候选点'),
    (-3.0, 0.0, '左侧'),
]


def decode(raw):
    """rclpy 的 `int8[]` 给到的是 `array('b')`（有符号）。

    但 Nav2 发布时**已经折到 0~100**：未知 = -1，代价 = 0~100。
    ⇒ 直接返回即可。（早期版本在这里 `+256` 还原成 0~254，是错的。）
    """
    return raw


def classify(cost):
    if cost == NO_INFO:
        return '未知'
    if cost == LETHAL:
        return '致命障碍'
    if cost == INSCRIBED:
        return '内切（必撞区）'
    if cost == NO_INFO:
        return '未知'
    if cost == 0:
        return '完全自由'
    return f'膨胀区'


class CostmapProbe(Node):
    def __init__(self, topic):
        super().__init__('costmap_probe')
        self.done = False
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.create_subscription(OccupancyGrid, topic, self.cb, qos)
        self.topic = topic

    def cb(self, msg):
        w, h = msg.info.width, msg.info.height
        res = msg.info.resolution
        ox = msg.info.origin.position.x
        oy = msg.info.origin.position.y

        print(f'--- {self.topic} ---')
        print(f'  尺寸 {w}x{h} @ {res:.3f} m/cell   origin ({ox:.2f}, {oy:.2f})   '
              f'frame={msg.header.frame_id}')
        print()

        # 统计（注意 int8 -> 无符号）
        data = [decode(v) for v in msg.data]
        stat = {'致命': 0, '内切': 0, '膨胀': 0, '自由': 0, '未知': 0}
        for c in data:
            if c == LETHAL:
                stat['致命'] += 1
            elif c == INSCRIBED:
                stat['内切'] += 1
            elif c == NO_INFO:
                stat['未知'] += 1
            elif c == 0:
                stat['自由'] += 1
            else:
                stat['膨胀'] += 1

        total = w * h
        print('  代价分布：')
        for k, v in stat.items():
            print(f'    {k:<4s} {v:>7d}  ({v / total * 100:5.1f}%)')
        print()

        # ★ 取值集合 —— 判断“膨胀层有没有梯度”的关键（见文件头说明）
        from collections import Counter
        cnt = Counter(data)
        vals = sorted(cnt)
        print(f'  取值集合（{len(vals)} 种）：')
        print('    ' + '  '.join(f'{v}({cnt[v]})' for v in vals[:24])
              + ('  …' if len(vals) > 24 else ''))
        if set(vals) <= {0, INSCRIBED, LETHAL, NO_INFO}:
            print('    ⚠️ 只有 0/99/100 ⇒ 膨胀层【退化成二值图】，没有梯度！')
            print('       多半是 inflation_radius <= footprint 的 inscribed_radius')
        else:
            print('    ✅ 有中间值 ⇒ 膨胀层有梯度')
        print()

        # 指定坐标
        print(f"  {'世界(x,y)':>16} {'像素':>12} {'代价':>6}  {'判定'}")
        for x, y, note in self.points:
            px = int(round((x - ox) / res))
            py = h - 1 - int(round((y - oy) / res))
            if 0 <= px < w and 0 <= py < h:
                c = data[py * w + px]
                print(f'  {str((x, y)):>16} {str((px, py)):>12} {c:>6}  {classify(c)} — {note}')
            else:
                print(f'  {str((x, y)):>16} {str((px, py)):>12} {"越界":>6}  {note}')
        print()

        # 反推：从代价估算到障碍的距离（用于校验 inflation 参数是否生效）
        #   cost = 252 * exp(-k * (d - r_in))   =>   d = r_in + ln(252/cost)/k
        print('  按公式 cost = 252·exp(-k·(d - r_in)) 反推（k 需已知）：')
        print('    若 k=0.5、r_in=0.1：（发布值先折回内部：internal = pub / 100 * 255）')
        for x, y, note in self.points[:3]:
            px = int(round((x - ox) / res))
            py = h - 1 - int(round((y - oy) / res))
            if 0 <= px < w and 0 <= py < h:
                pub = data[py * w + px]
                internal = pub / COST_SCALE if pub > 0 else pub
                if 0 < internal < 252:
                    import math
                    d = 0.1 + math.log(252 / internal) / 0.5
                    print(f'      {str((x, y)):>12}  发布 {pub:>3d}(内部 {internal:6.1f})  ->  距障碍约 {d:4.2f} m')
                else:
                    print(f'      {str((x, y)):>12}  发布 {pub:>3d}  ->  （不在膨胀区，无法反推）')
        print('    ⚠️ 若反推距离 > inflation_radius，说明 k 与 r_in 不是上面假设的值')
        print('       -> 用 --node 回读真实参数，或 ros2 param get 手动确认')
        print()

        self.done = True


def read_params(node_name, params):
    """回读节点参数（用于检"参数假生效"）"""
    from rclpy.parameter import Parameter
    from rclpy.parameter_client import AsyncParameterClient

    class Tmp(Node):
        pass

    n = Tmp('costmap_param_reader')
    client = AsyncParameterClient(n, node_name)
    if not client.wait_for_services(timeout_sec=3.0):
        print(f'  ⚠️ 连不上参数服务 {node_name}（节点名对吗？）')
        n.destroy_node()
        return
    fut = client.get_parameters(params)
    rclpy.spin_until_future_complete(n, fut, timeout_sec=3.0)
    res = fut.result()
    if res is None:
        print(f'  ⚠️ 读取 {node_name} 参数超时')
    else:
        print(f'--- {node_name} 实际参数 ---')
        for p in res.values:
            print(f'  {p.name} = {p.value}')
        print()
    n.destroy_node()


def parse_points(spec):
    """解析查询点。

    用**单个字符串**而不是 nargs，是为了支持负坐标：
    若写成 `--points -4,0 -3,0`，argparse 会把 `-4,0` 误当作选项名。
    所以约定：整串用引号包起来，点之间用空格或分号分隔。
        例：--points "-4,0; -3,0; 0,0; 20,0"
    """
    pts = []
    for chunk in spec.replace(';', ' ').split():
        x, _, y = chunk.partition(',')
        pts.append((float(x), float(y), ''))
    return pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--topic', default='/global_costmap/costmap')
    ap.add_argument('--points', default=None,
                    help='世界坐标查询点，整体用引号包住，点间用空格或分号分隔。'
                         '例：--points "-4,0; 0,0; 20,0"')
    ap.add_argument('--node', default=None,
                    help='额外回读该节点的膨胀参数，如 /global_costmap/global_costmap')
    args = ap.parse_args()

    pts = parse_points(args.points) if args.points else DEFAULT_POINTS

    rclpy.init()

    if args.node:
        read_params(args.node, [
            'inflation_layer.inflation_radius',
            'inflation_layer.cost_scaling_factor',
            'resolution',
        ])

    node = CostmapProbe(args.topic)
    node.points = pts
    for _ in range(200):
        rclpy.spin_once(node, timeout_sec=0.05)
        if node.done:
            break
    if not node.done:
        print(f'没收到 {args.topic} 的消息。检查：服务起了吗？话题名对吗？')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
