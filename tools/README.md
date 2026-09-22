# tools

观测、测量与调试用的小工具。

| 文件 | 用途 |
|---|---|
| [`plan_metrics.py`](#plan_metrics-py) | **测量路径质量与更新节奏** —— 判断"卡顿"的仪器 |
| [`costmap_probe.py`](#costmap_probe-py) | **读代价地图**（正确处理 int8）+ 回读参数，检"假生效" |
| [`virtual_chassis.py`](#virtual_chassis-py) | **虚拟底盘**：让静态环境动起来，可在 Foxglove 看动态过程 |

---

## plan_metrics.py

### 为什么需要

"无明显卡顿"听起来很虚，但它可以拆成两个**可测量**的量：

| 卡顿类型 | 测什么 | 指标 |
|---|---|---|
| **规划卡顿** | `/plan` 出得稳不稳 | `dt` 的均值/最大/标准差，空档次数 |
| **路径卡顿** | 路径够不够平滑 | **转折密度**（转折数 / 路径长度，单位 turns/m） |

换规划器前后各跑一次，对比这两组数字，就是"卡顿是否改善"的客观证据。

### 用法

```bash
# 持续观测（Ctrl+C 结束，会打印汇总）
python3 tools/plan_metrics.py

# 只观测 60 秒
python3 tools/plan_metrics.py --duration 60
```

### 输出示例

```
#1   dt=1.01s  pts=823  len= 41.53m  spacing=0.050m  turns=368  turns/m=  8.86
#2   dt=0.99s  pts=823  len= 41.53m  spacing=0.050m  turns=368  turns/m=  8.86

===== 汇总（共 42 条）=====
dt        : mean 0.990s  min 0.960s  max 1.030s  std 0.030s
路径点数  : mean 823.0
路径长度  : mean 41.53 m
转折数    : mean 368.0
转折密度  : mean 8.86 turns/m
空档次数  : 0  (dt > 2.0s)
```

### 怎么读

| 现象 | 含义 |
|---|---|
| `dt` 的 std 大 / 有空档 | **规划卡顿** —— 规划器慢或被阻塞 |
| 转折密度高（> 4 turns/m） | **路径卡顿** —— 跟踪时会在每个转折降速 |
| `spacing` 很小（如 0.05 m） | 路径点密 = 栅格原始输出，未经平滑 |

---

## costmap_probe.py

### 为什么需要

`nav_msgs/OccupancyGrid.data` 是 **`int8[]`**（有符号 8 位），
而 nav2 代价是 **0~254**（无符号语义），所以直接 `echo` 会看到负数：

| 真实代价 | echo 显示 |
|---|---|
| `254`（致命障碍） | `-2` |
| `253`（内切） | `-3` |
| `255`（未知） | `-1` |
| `252 ~ 128` | `-4 ~ -128` |

不知道这点，就会把"致命障碍"和"未知"看混。本工具会**还原成 0~254** 再统计。

### 用法

```bash
# 默认查全局代价地图
python3 tools/costmap_probe.py

# 查局部代价地图
python3 tools/costmap_probe.py --topic /local_costmap/costmap

# 查指定坐标（注意：整串要用引号包住，因为负坐标会被误当选项）
python3 tools/costmap_probe.py --points "-4,0; 0,0; 20,0; 10,0"

# 顺便回读膨胀参数，检"参数假生效"
python3 tools/costmap_probe.py --node /global_costmap/global_costmap
```

### 输出示例

```
代价分布：
  致命         0  (  0.0%)
  内切         0  (  0.0%)
  膨胀     32305  ( 68.7%)
  自由     14707  ( 31.3%)
  未知         0  (  0.0%)
```

### 怎么读

| 现象 | 含义 |
|---|---|
| **自由**占比很低 | 代价地图偏保守，规划器可用的"廉价空间"窄 → 路径容易贴障碍 |
| 起点代价很高 | 起点离障碍近 → 可能触发"起步就贴着膨胀区"的行为 |
| 回读参数 ≠ yaml 里的值 | **参数假生效**，需要排查参数名/嵌套层级 |

---

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
