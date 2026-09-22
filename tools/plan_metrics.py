#!/usr/bin/env python3
"""测量 /plan 的路径质量与更新节奏 —— 判断"卡顿"的仪器。

## 为什么需要它

"无明显卡顿"这个要求听起来很虚，其实可以拆成两个**可测**的量：

1. **规划卡顿**：`/plan` 多久出一次？有没有长空档？
   -> 看 `dt`（相邻两条路径的时间间隔）的稳定性
2. **路径卡顿**：路径够不够平滑？
   -> 看**转折密度**（每米路径有多少个转折）

换规划器前后各跑一次，对比这两组数字，就是"卡顿是否改善"的客观证据。

## 用法

    # 持续观测（Ctrl+C 结束，会打印汇总）
    python3 tools/plan_metrics.py

    # 只观测 60 秒
    python3 tools/plan_metrics.py --duration 60

    # 换个话题
    python3 tools/plan_metrics.py --topic /plan

## 输出示例

    #1   dt=1.01s  pts=823  len=41.53m  spacing=0.05m  turns=368  turns/m=8.86
    #2   dt=0.99s  pts=823  len=41.53m  spacing=0.05m  turns=368  turns/m=8.86

    ===== 汇总（共 42 条）=====
    dt        : mean 0.99s  min 0.96s  max 1.03s  std 0.03s   <- 越大越不稳
    路径点数  : mean 823
    路径长度  : mean 41.53 m
    转折数    : mean 368
    转折密度  : mean 8.86 turns/m                            <- 越小越平滑
    空档次数  : 0  (dt > 2x 期望值)
"""
import argparse
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from nav_msgs.msg import Path


def heading(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])


def measure(path_msg, turn_threshold_deg):
    """返回 (点数, 长度m, 平均点距m, 转折数)"""
    pts = [(p.pose.position.x, p.pose.position.y) for p in path_msg.poses]
    if len(pts) < 2:
        return len(pts), 0.0, 0.0, 0

    length = 0.0
    for i in range(1, len(pts)):
        length += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])

    turns = 0
    for i in range(2, len(pts)):
        a1 = heading(pts[i - 2], pts[i - 1])
        a2 = heading(pts[i - 1], pts[i])
        d = abs(math.degrees(a2 - a1))
        d = min(d, 360.0 - d)
        if d > turn_threshold_deg:
            turns += 1

    spacing = length / (len(pts) - 1) if len(pts) > 1 else 0.0
    return len(pts), length, spacing, turns


class PlanMetrics(Node):
    def __init__(self, topic, turn_threshold_deg, expected_dt):
        super().__init__('plan_metrics')
        self.turn_threshold_deg = turn_threshold_deg
        self.expected_dt = expected_dt

        self.count = 0
        self.last_time = None
        self.dts = []
        self.gaps = 0
        self.points = []
        self.lengths = []
        self.turns = []
        self.densities = []

        # BEST_EFFORT + VOLATILE 的订阅能兼容可靠/尽力、易失/暂存的发布者
        qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.create_subscription(Path, topic, self.on_plan, qos)
        self.get_logger().info(f'订阅 {topic}，等待路径…（转折判据 >{turn_threshold_deg}°）')

    def on_plan(self, msg):
        now = time.monotonic()
        dt = (now - self.last_time) if self.last_time is not None else float('nan')
        self.last_time = now
        self.count += 1

        npts, length, spacing, turns = measure(msg, self.turn_threshold_deg)
        density = (turns / length) if length > 0 else 0.0

        self.points.append(npts)
        self.lengths.append(length)
        self.turns.append(turns)
        self.densities.append(density)

        gap_flag = ''
        if dt == dt:  # 非 nan
            self.dts.append(dt)
            if dt > 2.0 * self.expected_dt:
                self.gaps += 1
                gap_flag = '  <-- 空档!'

        dt_s = f'{dt:5.2f}s' if dt == dt else '  --  '
        print(
            f'#{self.count:<4d} dt={dt_s}  pts={npts:<5d} len={length:7.2f}m  '
            f'spacing={spacing:5.3f}m  turns={turns:<5d} turns/m={density:6.2f}{gap_flag}',
            flush=True,
        )

    def summary(self):
        if not self.points:
            print('\n没收到任何路径。检查：话题名对不对？导航栈起了吗？')
            return
        print(f'\n===== 汇总（共 {self.count} 条）=====')
        if self.dts:
            mean = sum(self.dts) / len(self.dts)
            var = sum((d - mean) ** 2 for d in self.dts) / len(self.dts)
            print(
                f'dt        : mean {mean:.3f}s  min {min(self.dts):.3f}s  '
                f'max {max(self.dts):.3f}s  std {math.sqrt(var):.3f}s'
            )
        else:
            print('dt        : （只收到 1 条，无法统计）')
        print(f'路径点数  : mean {sum(self.points) / len(self.points):.1f}')
        print(f'路径长度  : mean {sum(self.lengths) / len(self.lengths):.2f} m')
        print(f'转折数    : mean {sum(self.turns) / len(self.turns):.1f}')
        print(f'转折密度  : mean {sum(self.densities) / len(self.densities):.2f} turns/m')
        print(f'空档次数  : {self.gaps}  (dt > {2.0 * self.expected_dt:.1f}s)')
        print()
        print('怎么读：')
        print('  dt 的 std 大 / 有空档 -> 规划卡顿（规划器慢或被阻塞）')
        print('  转折密度高（>4）      -> 路径卡顿（跟踪时会反复降速）')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--topic', default='/plan')
    ap.add_argument('--duration', type=float, default=0.0, help='观测秒数，0=一直跑')
    ap.add_argument('--turn-threshold', type=float, default=5.0, help='算作转折的夹角阈值(度)')
    ap.add_argument('--expected-dt', type=float, default=1.0, help='期望的更新周期(秒)')
    args = ap.parse_args()

    rclpy.init()
    node = PlanMetrics(args.topic, args.turn_threshold, args.expected_dt)
    t0 = time.monotonic()
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            if args.duration > 0 and time.monotonic() - t0 > args.duration:
                break
    except KeyboardInterrupt:
        pass
    finally:
        node.summary()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
