# tools

观测、测量与调试用的小工具。

| 文件 | 用途 |
|---|---|
| [`plan_metrics.py`](#plan_metrics-py) | **测量路径质量与更新节奏** —— 判断"卡顿"的仪器 |
| [`costmap_probe.py`](#costmap_probe-py) | **读代价地图**（正确处理 int8）+ 回读参数，检"假生效" |
| [`plot_path.py`](#plot_path-py) | **画路径对比图**：把规划结果叠加到地图上，底图参数自动读 yaml |
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

## plot_path.py

### 为什么需要

验收要"效果演示"，而**一张带路径的图**比一堆数字直观得多。
但路径图不是自动产生的：

```
底图（maps/*.png） + 路径（该次运行的规划结果） = 带路径的对比图
      ↑ yaml 决定                                     ↑ 必须跑 + 画
```

⚠️ **改 yaml 只能换底图，不会凭空产生路径** —— 路径是规划器**运行时**算出来的
（`/compute_path_to_pose` 的输出），必须跑一次并保存下来才能画。

### 特点

- **自动读 yaml**：分辨率、原点、图片名都从 `maps/<名字>.yaml` 读。
  所以你改了 yaml（换地图 / 改分辨率），脚本**自动跟随**，不用改代码。
- **多路径叠加**：同一张底图画多条路径，直接对比换规划器前后的差异。
- **自动统计**：输出路径点数、长度、转折数、转折密度（turns/m）。
- **图例可读**：图例/标题带半透明白底，压在黑色障碍上也能看清。
- **可选标题**：`--title` 在底部居中加一行说明（**仅 ASCII**）。
- **坐标网格**：`--grid 2` 叠加每 2 米一条的世界坐标网格，**可以从图上直接读出任意点的 (x, y)**。
- **候选点标注**：`--mark "x1,y1;x2,y2"` 画带序号的黄点，上车前确认目标点没标在障碍上。
- **可只画地图**：不给路径也能跑（`paths` 是可选的）。

### 用法

```bash
# ① 先跑规划，把输出存下来（每换一次规划器都要重跑并另存一份）
ros2 action send_goal /compute_path_to_pose nav2_msgs/action/ComputePathToPose \
  "{goal: {header: {frame_id: world}, pose: {position: {x: 20.0, y: 0.0, z: 0.0}}}, use_start: false}" \
  > /tmp/plan_navfn.txt

# ② 画一张（--title 可选，只能填英文：cv2 画不了中文）
python3 tools/plot_path.py assets/path_navfn.png \
  --title "Global planner: NavFn (baseline)" "NavFn:/tmp/plan_navfn.txt"

# ③ 三种画在同一张图（验收"效果演示"最有力的材料）
#    配色按传参顺序固定：①红 ②蓝 ③绿，所以顺序必须 NavFn → ThetaStar → Smac2D
python3 tools/plot_path.py assets/path_compare_three.png \
  --title "Same start & goal - three global planners compared" \
  "NavFn:/tmp/plan_navfn.txt" "ThetaStar:/tmp/plan_theta.txt" "Smac2D:/tmp/plan_smac2d.txt"

# ④ 换底图（会读对应 yaml 的参数）
python3 tools/plot_path.py assets/plan_zhandui.png --map 战队 "NavFn:/tmp/plan_navfn.txt"

# ⑤ 调放大倍数（默认 3）
python3 tools/plot_path.py out.png --scale 4 "NavFn:/tmp/plan_navfn.txt"

# ⑥ 只要地图 + 世界坐标网格（不给路径也能画，用于挑目标点）
python3 tools/plot_path.py assets/map_rmuc_grid.png --grid 2 --scale 3

# ⑦ 标出候选目标点（带序号的黄点），确认没落在障碍上
python3 tools/plot_path.py assets/map_rmuc_pick.png --grid 2 --scale 3 --mark "1.5,0;18,3"
```

### 输出示例

```
底图      : rmuc-v2.png
几何参数  : resolution=0.1  origin=(-4.3, -8.0)  <- 读自 rmuc.yaml
尺寸      : 292x161 px  ->  世界 29.2 x 16.1 m

  NavFn       823 点   41.53 m   368 转折   8.86 turns/m

已保存: assets/path_navfn.png
```

### 图上元素的含义

| 元素 | 含义 |
|---|---|
| 黑白底图 | `maps/*.png`（黑 = 障碍，白 = 可通行） |
| **绿点** | 路径起点 |
| **红点** | 路径终点 |
| **彩色线** | 规划路径（按传参顺序取 红/蓝/绿/紫/黄） |
| 左上文字 | 图例：路径长度、转折数、转折密度（半透明白底，压在障碍上也看得清） |
| 底部文字 | `--title` 指定的标题（可选） |

> ⚠️ `--title` 和图例**只能用 ASCII**：`cv2.putText` 不支持中文，填中文会变成方块。
> 中文说明请写在 Markdown 图注里。

### 常用地图名

`rmuc`（默认，→ rmuc-v2.png）、`rmul`、`战队`、`empty`

> 地图名写错时会提示可用列表。

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
