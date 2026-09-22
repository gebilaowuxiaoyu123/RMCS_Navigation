#!/usr/bin/env python3
"""虚拟底盘：把"静态"导航环境变成可观察的闭环仿真。

## 为什么需要它

`static.launch.yaml` 里 `odom -> base_link` 是**静态 TF**，机器人永远停在原点。
结果是：路径规划能跑，但机器人不动 -> 看不到代价地图滚动、MPPI 跟踪、路径重规划
等**动态行为**，无法在 Foxglove 里观察"卡顿"到底长什么样。

本节点订阅 `/cmd_vel`（局部控制器 MPPI 的速度指令），按质点+全向模型积分出位姿，
再发布**动态的** `odom -> base_link` TF，从而闭合"规划 -> 控制 -> 运动 -> 感知"回路。

## 用法

    # ① 先杀掉静态的 odom->base_link 发布者（否则 TF 冲突、位置抖动）
    pkill -f "static_transform_publisher 0 0 0 0 0 0 odom base_link"

    # ② 启动本节点
    python3 tools/virtual_chassis.py                 # 默认：积分 /cmd_vel
    python3 tools/virtual_chassis.py --speed 0.6     # 沿全局路径匀速走（确定性）

    # ③ 另开终端发送目标点
    ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \\
      "{pose: {header: {frame_id: world}, pose: {position: {x: 20.0, y: 0.0, z: 0.0}}}}"

    # ④ 在 Foxglove 观察

## 两种模式

- `--mode cmd_vel`（默认）：积分 `/cmd_vel`。**最忠实**——机器人按控制器指令运动，
  能看到"控制器输出 -> 实际运动"的完整闭环，也最能暴露跟踪问题。
- `--mode plan`：沿 `/plan` 的全局路径匀速推进。**确定性**，不受控制器输出影响，
  适合只想看路径与代价地图变化时使用。
"""
import argparse
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from geometry_msgs.msg import TransformStamped, Twist, Quaternion, PoseStamped
from nav_msgs.msg import Odometry, Path
from tf2_ros import TransformBroadcaster


def yaw_to_quat(yaw):
    return Quaternion(x=0.0, y=0.0, z=math.sin(yaw / 2.0), w=math.cos(yaw / 2.0))


class VirtualChassis(Node):
    def __init__(self, mode, speed, rate, frame_odom, frame_base):
        super().__init__('virtual_chassis')
        self.mode = mode
        self.speed = speed
        self.dt = 1.0 / rate
        self.frame_odom = frame_odom
        self.frame_base = frame_base

        # 位姿（在 odom 系下）
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0

        # cmd_vel 模式
        self.cmd = Twist()

        # plan 模式
        self.path = []
        self.seg = 0
        self.seg_consumed = 0.0

        self.br = TransformBroadcaster(self)

        # /cmd_vel 由 controller_server 以可靠 QoS 发布
        self.create_subscription(Twist, '/cmd_vel', self.on_cmd, 10)

        # /plan 由 planner_server 发布（reliable, volatile, depth 1）
        plan_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.create_subscription(Path, '/plan', self.on_plan, plan_qos)

        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.timer = self.create_timer(self.dt, self.on_timer)

        self.last_log = time.time()
        self.get_logger().info(
            f'虚拟底盘已启动 | 模式={mode} 速度={speed} m/s 频率={rate} Hz\n'
            f'  发布 TF: {frame_odom} -> {frame_base}\n'
            f'  ⚠️ 请确认静态 odom->base_link 发布者已停止，否则位置会抖动'
        )

    # ---------------- 回调 ----------------

    def on_cmd(self, msg):
        self.cmd = msg

    def on_plan(self, msg):
        self.path = [(p.pose.position.x, p.pose.position.y) for p in msg.poses]
        self.seg = 0
        self.seg_consumed = 0.0
        self.get_logger().info(f'收到新路径：{len(self.path)} 个点')

    # ---------------- 主循环 ----------------

    def on_timer(self):
        if self.mode == 'cmd_vel':
            self.step_cmd()
        else:
            self.step_plan()
        self.publish()

    def step_cmd(self):
        """全向底盘：vx/vy 直接积分（wz 接近 0，配置里已锁死不让旋转）"""
        vx = self.cmd.linear.x
        vy = self.cmd.linear.y
        wz = self.cmd.angular.z
        # 速度指令在 base_link 系，需旋转到 odom 系
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        self.x += (c * vx - s * vy) * self.dt
        self.y += (s * vx + c * vy) * self.dt
        self.yaw += wz * self.dt

    def step_plan(self):
        """沿全局路径匀速推进（确定性）"""
        if len(self.path) < 2:
            return
        budget = self.speed * self.dt
        while budget > 0 and self.seg < len(self.path) - 1:
            x0, y0 = self.path[self.seg]
            x1, y1 = self.path[self.seg + 1]
            seg_len = math.hypot(x1 - x0, y1 - y0)
            if seg_len <= 1e-9:
                self.seg += 1
                self.seg_consumed = 0.0
                continue
            remain = seg_len - self.seg_consumed
            if budget >= remain:
                budget -= remain
                self.seg += 1
                self.seg_consumed = 0.0
            else:
                self.seg_consumed += budget
                budget = 0.0
        if self.seg >= len(self.path) - 1:
            # 到终点：停在终点，等待新路径
            self.seg = len(self.path) - 1
            self.x, self.y = self.path[-1]
            return
        x0, y0 = self.path[self.seg]
        x1, y1 = self.path[self.seg + 1]
        seg_len = math.hypot(x1 - x0, y1 - y0)
        t = self.seg_consumed / seg_len if seg_len > 1e-9 else 0.0
        self.x = x0 + (x1 - x0) * t
        self.y = y0 + (y1 - y0) * t
        self.yaw = math.atan2(y1 - y0, x1 - x0)

    def publish(self):
        now = self.get_clock().now().to_msg()
        q = yaw_to_quat(self.yaw)

        t = TransformStamped()
        t.header.stamp = now
        t.header.frame_id = self.frame_odom
        t.child_frame_id = self.frame_base
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation = q
        self.br.sendTransform(t)

        od = Odometry()
        od.header.stamp = now
        od.header.frame_id = self.frame_odom
        od.child_frame_id = self.frame_base
        od.pose.pose.position.x = self.x
        od.pose.pose.position.y = self.y
        od.pose.pose.orientation = q
        od.twist.twist = self.cmd
        self.odom_pub.publish(od)

        # 每秒打一次状态，便于命令行确认
        if time.time() - self.last_log > 1.0:
            self.last_log = time.time()
            if self.mode == 'cmd_vel':
                self.get_logger().info(
                    f'位姿 ({self.x:7.3f}, {self.y:7.3f}) 偏航 {math.degrees(self.yaw):6.1f}° '
                    f'| cmd_vel vx={self.cmd.linear.x:+.3f} vy={self.cmd.linear.y:+.3f}'
                )
            else:
                self.get_logger().info(
                    f'位姿 ({self.x:7.3f}, {self.y:7.3f}) | 段 {self.seg + 1}/{max(len(self.path) - 1, 1)}'
                )


def main():
    ap = argparse.ArgumentParser(description='虚拟底盘：把静态导航环境变成闭环仿真')
    ap.add_argument('--mode', choices=['cmd_vel', 'plan'], default='cmd_vel',
                    help='cmd_vel=积分控制器输出(默认) | plan=沿全局路径匀速')
    ap.add_argument('--speed', type=float, default=0.6, help='plan 模式速度 m/s')
    ap.add_argument('--rate', type=float, default=30.0, help='TF 发布频率 Hz')
    ap.add_argument('--frame-odom', default='odom')
    ap.add_argument('--frame-base', default='base_link')
    args = ap.parse_args()

    rclpy.init()
    node = VirtualChassis(args.mode, args.speed, args.rate,
                          args.frame_odom, args.frame_base)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
