# Foxglove 观测指南

> 教你怎么在自己的 Foxglove 里**看到导航的动态过程**，以及怎么用这个工具看出"卡顿"。
> 相关：[任务规划.md](任务规划.md)（执行计划）、[实验记录.md](实验记录.md)（实测数据）

---

## 一、先理解：为什么需要"虚拟底盘"

`static.launch.yaml` 的 `odom -> base_link` 是**静态 TF**（`0 0 0 0 0 0 odom base_link`），
意味着**机器人永远停在原点**。后果：

| 能看到 | 看不到 |
|---|---|
| ✅ 路径被规划出来（`/plan`，1 Hz 更新） | ❌ 机器人**移动** |
| ✅ 全局代价地图（固定） | ❌ 局部代价地图**滚动** |
| ✅ `/cmd_vel` 被算出来 | ❌ MPPI **跟踪**效果 |

**要让画面动起来，必须让 `base_link` 动。** 两种办法：

| 办法 | 做法 | 代价 |
|---|---|---|
| **轻量（本指南用）** | 杀掉静态 TF，用 `tools/virtual_chassis.py` 积分 `/cmd_vel` 发布动态 TF | 零依赖，秒级启动 |
| 重量 | 上 Gazebo 仿真 | 需装仿真包、建模型、配插件，工作量大 |

> ⚠️ `static.launch.yaml` 是**静态回归测试**环境，**本身不是仿真器**——
> 它只能验证"规划链路 + 参数加载 + 规划耗时"，验证不了运动。

---

## 二、四步跑起来

### 步骤 0 · 清理残留（每次必做）

导航进程极易遗留，不清会出**节点重复实例**和**端口占用**。

```bash
pkill -f 'ros2 launch rmcs-navigation'; sleep 2
for p in nav2_lifecycle_manager nav2_bt_navigator nav2_planner \
         nav2_controller nav2_map_server foxglove_bridge static_transform_publisher; do
  pkill -f "$p"
done
sleep 2
ps aux | grep -E 'nav2|ros2 launch|foxglove' | grep -v grep | wc -l   # 应输出 0
```

### 步骤 1 · 启动导航栈（**终端 A**）

```bash
bash -lc 'cd /workspaces/RMCS/rmcs_ws && source install/setup.bash \
  && ros2 launch rmcs-navigation static.launch.yaml'
```

期望看到 `foxglove_bridge` 打印 `Server listening on port 8765`。

### 步骤 2 · 换成动态 TF（**终端 B**）

```bash
# ① 杀掉静态的 odom->base_link（world->odom 保留即可）
pkill -f "static_transform_publisher 0 0 0 0 0 0 odom base_link"

# ② 启动虚拟底盘
bash -lc 'cd /workspaces/RMCS/rmcs_ws && source install/setup.bash \
  && python3 /workspaces/RMCS/docs/zh-cn/算法组考核/tools/virtual_chassis.py'
```

期望看到每秒一行位姿日志：

```
[INFO] [virtual_chassis]: 虚拟底盘已启动 | 模式=cmd_vel 速度=0.6 m/s 频率=30.0 Hz
[INFO] [virtual_chassis]: 位姿 (  0.000,   0.000) 偏航    0.0° | cmd_vel vx=+0.000 vy=+0.000
```

> **不杀静态 TF 会怎样**：两个发布者同时发 `odom->base_link`，
> 位置会在两个值之间跳 —— 表现为画面**抖动**。

### 步骤 3 · 发送目标点（**终端 C**）

```bash
bash -lc 'cd /workspaces/RMCS/rmcs_ws && source install/setup.bash \
  && ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: world}, pose: {position: {x: 20.0, y: 0.0, z: 0.0}}}}"'
```

或者**在 Foxglove 里点**（更直观）：3D 面板左上角工具栏选 **Publish**，
topic 选 `/goal_pose`（`geometry_msgs/PoseStamped`），在地图上点一下即可下发目标。

---

## 三、Foxglove 连接

**用你本机的 Foxglove 桌面端**（不是网页版）：

1. 打开 Foxglove → **Open connection**
2. 选 **Rosbridge / Foxglove WebSocket**
3. URL 填 `ws://localhost:8765`
4. 连接

> 容器是 `network_mode: host`，宿主机可直接访问容器的 8765 端口。
> 若连不上，先在终端确认：`netstat -tln | grep 8765`（应看到 `LISTEN`）。

---

## 四、面板与话题配置

### 4.1 3D 面板（主视图，看空间关系）

按这个顺序添加，**图层顺序 = 叠放顺序**（后加的在上面）：

| 话题 | 类型 | 作用 | 建议设置 |
|---|---|---|---|
| `/map` | OccupancyGrid | 静态场地地图 | Color mode: `map`，Alpha 0.6 |
| `/global_costmap/costmap` | OccupancyGrid | **全局代价地图**（看膨胀范围） | Color mode: `costmap`，Alpha 0.5 |
| `/local_costmap/costmap` | OccupancyGrid | **局部代价地图**（会随车滚动） | Color mode: `costmap`，Alpha 0.4 |
| `/plan` | Path | **全局路径** ★ | Color: 亮绿；Line width 3 |
| `/global_costmap/published_footprint` | PolygonStamped | 机器人轮廓 | 换醒目颜色 |
| `/tf`、`/tf_static` | FrameTransform | 坐标系（可选显示） | 只勾 `world`/`odom`/`base_link` |

**Fixed frame** 设为 `world`（面板左上角）。

### 4.2 Plot 面板（**看"卡顿"的关键**）

| 系列 | 话题 | 字段 | 看什么 |
|---|---|---|---|
| 线速度 | `/cmd_vel` | `linear.x` | 是否**平滑**；有无规律性**锯齿/骤降** |
| 横向速度 | `/cmd_vel` | `linear.y` | 全向底盘是否各向均衡 |
| 角速度 | `/cmd_vel` | `angular.z` | 配置里锁死为 ~0.001 |

> **"跟踪卡顿"在 Plot 里的样子**：曲线出现**周期性凹陷**——
> 每当路径转弯，控制器就要减速转向，速度掉下去再爬起来。
> 路径转折越多（NavFn 有 368 个），这种凹陷就越密集，看起来就是"一顿一顿"。

### 4.3 其他有用面板

| 面板 | 用途 |
|---|---|
| **Raw Messages** | 看 `/plan` 的 `poses` 数组长度（= 路径点数）、看 `/odom` |
| **Topic Graph** | 一眼看出话题连接关系与频率异常 |
| **Diagnostics** | `/diagnostics` 里的健康信息 |

---

## 五、要看什么：把"卡顿"看出来的三个证据

### 证据 1 · 路径是锯齿（3D 面板）

在 3D 面板里放大看 `/plan`：NavFn 输出的是**格子级阶梯折线**，
一格一格拐，而不是平滑曲线。**转折点越密，跟踪越容易顿。**

对照：[实验记录.md](实验记录.md) §3.2 实测 368 个转折。

### 证据 2 · 速度曲线周期性凹陷（Plot 面板）

Plot 里看 `/cmd_vel.linear.x`：机器人每经过一个转折，速度就要掉一次。
**把路径转折数降下来（换 Smac2D 的平滑器），凹陷应显著减少。**

### 证据 3 · 控制环丢帧（终端日志 + Raw Messages）

`controller_server` 终端会打印：

```
Control loop missed its desired rate of 20.0000 Hz. Current loop rate is 15.5~15.9 Hz.
```

表示局部控制器**算不过来**（MPPI 负载高）。这不是规划器问题，但属于"卡顿"成分之一。

---

## 六、切换规划器后怎么对比

同一套观测流程，改完 `motion.yaml` 重启后，**重点对比**：

| 观察项 | 在哪个面板 | NavFn 基线 | Smac2D 预期 |
|---|---|---|---|
| 路径形状 | 3D `/plan` | 锯齿、转折密 | **平滑、转折少** |
| 转折点数 | Raw Messages 数 `poses` | 368 | 显著减少 |
| 速度曲线 | Plot `/cmd_vel.linear.x` | 凹陷密集 | **凹陷减少** |
| 路径长度 | Raw Messages | 41.53 m | 相近或略变 |

**建议录屏**：两个版本各跑同一组起终点，录下来并排放，这是验收"效果演示"最有力的材料。

---

## 七、仿真环境怎么选

| 方案 | 机器人会动 | 搭建成本 | 适合 |
|---|---|---|---|
| `static.launch.yaml` 裸跑 | ❌ | 0 | 只验证规划器参数是否生效、规划耗时 |
| **+ `virtual_chassis.py`（本指南）** | ✅ | 极低 | **看动态过程、调参对比**（推荐起点） |
| Gazebo 仿真 | ✅ | 高（需仿真包 + 模型 + 插件） | 需要真实物理/传感器噪声时 |
| 实车 | ✅ | — | 最终验收 |

> 本指南的虚拟底盘是**质点运动学模型**（无惯性、无摩擦、无传感器噪声），
> 足够观察"规划与跟踪的几何行为"，但**不能替代实车验证动力学效果**。

---

## 八、命令速查

```bash
# —— 清理 ——
pkill -f 'ros2 launch rmcs-navigation'; sleep 2
for p in nav2_lifecycle_manager nav2_bt_navigator nav2_planner nav2_controller \
         nav2_map_server foxglove_bridge static_transform_publisher; do pkill -f "$p"; done

# —— 启动栈（终端A）——
bash -lc 'cd /workspaces/RMCS/rmcs_ws && source install/setup.bash \
  && ros2 launch rmcs-navigation static.launch.yaml'

# —— 动态 TF（终端B）——
pkill -f "static_transform_publisher 0 0 0 0 0 0 odom base_link"
bash -lc 'cd /workspaces/RMCS/rmcs_ws && source install/setup.bash \
  && python3 /workspaces/RMCS/docs/zh-cn/算法组考核/tools/virtual_chassis.py'

# —— 发目标（终端C）——
bash -lc 'cd /workspaces/RMCS/rmcs_ws && source install/setup.bash \
  && ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: world}, pose: {position: {x: 20.0, y: 0.0, z: 0.0}}}}"'

# —— 换终点（试不同路径）——
#   把 x/y 改成别的空闲点，如 (12,-3) (-3,0) (20,0)
#   地图空闲区参考：世界范围 x[-4.3,24.9] y[-8.0,8.1]

# —— 检查 ——
bash -lc 'cd /workspaces/RMCS/rmcs_ws && source install/setup.bash && \
  ros2 node list && ros2 param get /planner_server GridBased.plugin'
```

---

## 九、常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| Foxglove 连不上（红点） | 栈没起 / 端口被占 | 检查终端 A 是否有 `Server listening on port 8765`；`netstat -tln \| grep 8765` |
| 画面位置**抖动** | 静态 TF 与虚拟底盘同时发 `odom->base_link` | 执行步骤 2 的 `pkill` |
| 机器人**不动** | 没发目标点；或 `/cmd_vel` 为 0 | 发目标点；看终端 B 的位姿日志 |
| 节点**重复**出现 | 残留进程 | 执行步骤 0 清理 |
| `Goal failed` 反复出现 | 静态环境下进度检查判无进展 | 用虚拟底盘让车真的动起来 |
