# tools

观测与调试用的小工具。

| 文件 | 用途 |
|---|---|
| `virtual_chassis.py` | **虚拟底盘**：订阅 `/cmd_vel` 积分出运动，发布动态 `odom -> base_link` TF，把静态导航环境变成可观察的闭环仿真 |

## virtual_chassis.py

### 为什么需要

`static.launch.yaml` 的 `odom -> base_link` 是静态 TF，机器人**永远不动**，
导致在 Foxglove 里看不到代价地图滚动、MPPI 跟踪、路径重规划等动态行为。

### 用法

```bash
# ① 先杀掉静态的 odom->base_link（否则 TF 冲突 → 画面抖动）
pkill -f "static_transform_publisher 0 0 0 0 0 0 odom base_link"

# ② 启动
python3 /workspaces/RMCS/docs/zh-cn/算法组考核/tools/virtual_chassis.py
```

### 两种模式

| 模式 | 行为 | 何时用 |
|---|---|---|
| `--mode cmd_vel`（默认） | 积分 `/cmd_vel`（控制器实际输出） | **推荐**：看完整闭环，最能暴露跟踪问题 |
| `--mode plan` | 沿 `/plan` 全局路径匀速推进（确定性） | 只想看路径与代价地图变化 |

```bash
python3 tools/virtual_chassis.py --mode plan --speed 0.6   # 匀速 0.6 m/s
python3 tools/virtual_chassis.py --rate 50                 # TF 提到 50 Hz
```

### 输出

- TF：`odom -> base_link`（30 Hz，可调）
- `/odom`：`nav_msgs/Odometry`
- 终端日志：每秒一行位姿

### 模型与局限

- **质点 + 全向运动学**：只积分速度，无惯性、无摩擦、无打滑
- 适合观察**几何行为**（路径形状、跟踪偏差、代价地图滚动）
- **不能替代实车**：动力学效果（加减速、打滑、震动）测不出来

### 详细说明

观测流程（连接 Foxglove、面板配置、怎么看卡顿）见
[../任务规划.md](../任务规划.md) §3 与文末「附：虚拟底盘脚本说明」。
