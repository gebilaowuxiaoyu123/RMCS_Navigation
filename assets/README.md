# 演示材料

> 本目录存放验收"效果演示"用的素材。
> 相关文档：[导航提交作业.md](../导航提交作业.md)（报告）、[tools/README.md](../tools/README.md)（制作工具）

## 现有文件

### ⭐ 主力素材：五规划器演示套图（两张地图各一套）

2026-10-03 重画。**两张地图**各一套，每套 6 张
（1 张五台叠画 + 5 张单图），风格统一，可直接放进报告。

**配色全文统一**：红 = NavFn ｜ 蓝 = ThetaStar ｜ 绿 = Smac2D ｜ 紫 = SmacHybrid ｜ 黄 = SmacLattice

#### `rmuc/` —— RMUC 比赛场地（`maps/rmuc-v2.png`）

起终点 `(0, 0)` → `(20, 0)`（沿用原来那组）。画法：`--map rmuc --scale 4 --grid 4`（全图 1168×644）。

| 文件 | 内容 | 关键数字 |
|---|---|---|
| `path_compare_all.png` | **五台叠在同一张图**（主力材料） | — |
| `path_navfn.png` | NavFn 单图（基线，已禁用） | **35.55 m / 173 转弯 / 4.87 turns·m⁻¹ / 曲率 32.91·m⁻¹** |
| `path_thetastar.png` | ThetaStar 单图 | 34.09 m / 25 / 0.73 / 8.24·m⁻¹ |
| `path_smac2d.png` | Smac2D 单图 | **34.06 m / 46 / 1.35 / 1.53·m⁻¹** |
| `path_hybrid.png` | SmacHybrid 单图（阿克曼，仅对比） | 37.29 m / 50 / 1.34 / 2.00·m⁻¹ |
| `path_lattice.png` | **SmacLattice 单图（最终选中）** | 39.95 m / 115 / 2.88 / 15.22·m⁻¹ |

#### `zhandui/` —— 战队训练场（`maps/战队.png`）

起终点 `(6.30, 4.40)` → `(1.80, -1.00)`。
画法：`--map 战队 --scale 5 --grid 2 --crop=-3.5,-4.2,7.5,7.2 --legend-pos br --font-scale 0.45`。

> ⚠️ **这张扫描图是「未完扫」的：右半边（x > 12）是空白，真实结构只在 `x ∈ [-10, 12]`。**
> 起终点和配图都取在 **`x ∈ [-3.5, 7.5]`** 这块结构区里。
> **千万别把右半边空白当自由区** —— 那儿没障碍，clearance 分析会误判成「最通畅」，
> 从而把起终点全选到没扫到的地方（这个坑已踩过，图画出来完全不像我们的场地）。

| 文件 | 内容 | 关键数字 |
|---|---|---|
| `path_compare_all.png` | **五台叠在同一张图** | — |
| `path_navfn.png` | NavFn 单图 | **19.58 m / 194 转弯 / 9.91 turns·m⁻¹ / 132 次急转** |
| `path_thetastar.png` | ThetaStar 单图 | **12.56 m / 15 / 1.19** |
| `path_smac2d.png` | Smac2D 单图 | 13.26 m / 27 / 2.04 |
| `path_hybrid.png` | SmacHybrid 单图 | 16.86 m / 52 / 3.08 |
| `path_lattice.png` | **SmacLattice 单图（最终选中）** | 17.54 m / 58 / 3.31 |

### 🗺️ 标点用底图

| 文件 | 内容 |
|---|---|
| `map_zhandui_grid.png` | **`战队.png`（现场验收图）带世界坐标网格**，每 2 m 一格，格线上标注世界坐标 |

用途：**上车前挑两个目标点，并确认没标在障碍上**。做法见
[任务规划.md](../任务规划.md) §十「怎么在地图上标目标点」。

```bash
cd /workspaces/RMCS/docs/zh-cn/算法组考核
# ① 生成带网格的底图（上边数字 = x，左边数字 = y）
python3 tools/plot_path.py assets/map_zhandui_grid.png --map 战队 --grid 2 --scale 3
# ② 换成你自己选的两个点，标出来确认（坐标因人而异，这个输出不入库）
python3 tools/plot_path.py /tmp/zd_pick.png --map 战队 --grid 2 --scale 3 --mark "14,0;23,0"
```

> `战队.png` 是**实扫半场图**（343×110 px @ 0.1 m，世界 x∈[-10, 24.3] y∈[-4, 7.0]）。
> 左边噪点多、很挤；**右边 x≈10~24 是开阔区**，挑点优先往右挑。

视觉上一眼可见：

- **NavFn 红线**：锯齿折线（一格一格拐）、贴障碍、绕远 —— 41.53 m 最长
- **ThetaStar 蓝线**：直线段拼接，段少但拐得硬（有 63° 急转角）
- **Smac2D 绿线**：平滑、走通道中间、最短

> ⭐ 这组图隐含一个关键认知：**转折数少 ≠ 更平滑**。
> ThetaStar 的转折数（35）比 Smac2D（43）**还少**，但拐得硬（最大 63.4°，1 次急转）；
> Smac2D 最大仅 10.1°、**0 次急转**。对跟踪而言**急转才是顿挫来源**。
> 详见 [实验记录.md](../实验记录.md) 的 9.28 节与
> [任务规划.md](../任务规划.md) 阶段 4.5。

### 早期素材（过程留痕，风格未统一）

| 文件 | 内容 | 说明 |
|---|---|---|
| `navfn_baseline_path.png` | NavFn 基线路径图 | 与 `path_navfn.png` **同一次运行**，无标题栏，是 9.22 首测留下的 |
| `compare_navfn_vs_smac2d.png` | NavFn vs Smac2D 两图对比 | 已删的 `path_compare_three.png` 的**两规划器前身**（未含 ThetaStar） |
| `navfn_baseline_raw.txt` | NavFn 规划的**原始输出**（823 个路径点，用于复现） | 唯一需要保留的原始数据 |

> 报告里统一引用 `path_*` 套图；这三个保留以示"迭代过程"。

### `path_navfn.png` 里画的是什么

它不是导航栈自动产生的，而是用 [tools/plot_path.py](../tools/plot_path.py) 画的：

```
底图（maps/rmuc-v2.png）  +  路径（运行时规划结果）  =  你看到的图
```

| 元素 | 含义 |
|---|---|
| 黑白底图 | `rmuc-v2.png`（RMUC 场地，292×161 px @ 0.1 m，放大 3 倍） |
| **绿点** | 起点 `world(0,0)`（机器人初始位置） |
| **红点** | 终点 `world(20,0)` |
| **红线** | NavFn 输出的路径：**41.53 m、368 个转折** |
| 左上文字 | 图例（脚本自动加） |

**用途**：作为"换规划器前"的对照。放大看路径明显是**锯齿折线**（一格一格拐），
这正是选 `SmacPlanner2D` 的直观证据。

> ⚠️ **改 yaml 不能生成这种图**。`maps/*.yaml` 只管底图（图片名、分辨率、原点），
> 路径是规划器**运行时**算出来的，必须跑一次规划 + 用脚本画。

## 待补文件

| 建议命名 | 内容 | 怎么来 |
|---|---|---|
| `plan_rate.png` | `/plan` 频率对比截图 | `ros2 topic hz /plan` |
| `costmap.png` | 代价地图分布 | `costmap_probe.py` 输出 |
| `tuned_compare.png` | **调参前 vs 调参后**路径对比 | 阶段 6 调参后再跑一次，用 `plot_path.py` 叠图 |
| `demo_*.mp4` / `.gif` | 运行录屏 | Foxglove |

## 命名规范

```
rmuc/  zhandui/             按地图分子目录（2026-10-03 起）
  path_<规划器>.png        演示套图单张   例：zhandui/path_navfn.png
  path_compare_all.png     演示套图汇总   五台叠图
  path_theta_star.png      ThetaStar 单张（带下划线，和其他单图风格不同）
compare_<A>_vs_<B>.png       两两对比（早期）例：compare_navfn_vs_smac2d.png
<规划器>_<内容>.txt         原始数据       例：navfn_baseline_raw.txt
```

**演示套图统一用 `path_` 前缀、按地图分子目录**，保证同一张地图的图在文件列表里挨在一起、风格一致。

## 怎么制作路径图

```bash
# ① 跑规划，保存输出（每换一次规划器都要重跑并另存一份）
ros2 action send_goal /compute_path_to_pose nav2_msgs/action/ComputePathToPose \
  "{goal: {header: {frame_id: world}, pose: {position: {x: 20.0, y: 0.0, z: 0.0}}}, use_start: false}" \
  > /tmp/plan_navfn.txt

# ② 画单张（--title 可选，只能填英文：cv2 画不了中文）
#    --color N 强制用第 N 色（1红2蓝3绿4紫5黄），单图配色与汇总图一致
cd /workspaces/RMCS/docs/zh-cn/算法组考核
python3 tools/plot_path.py assets/zhandui/path_lattice.png \
  --color 5 --title "SmacPlannerLattice - omni (CHOSEN)" \
  "SmacLattice:/tmp/plancmp/战队/plan_lattice.txt"

# ③ 画汇总（一次传多条路径即可叠加；配色按传参顺序 ①红②蓝③绿④紫⑤黄）
python3 tools/plot_path.py assets/zhandui/path_compare_all.png \
  --map 战队 --legend-pos br --font-scale 0.4 \
  --title "Zhandui - five planners" \
  "NavFn:/tmp/plancmp/战队/plan_navfn.txt" \
  "ThetaStar:/tmp/plancmp/战队/plan_thetastar.txt" \
  "Smac2D:/tmp/plancmp/战队/plan_smac2d.txt" \
  "SmacHybrid:/tmp/plancmp/战队/plan_hybrid.txt" \
  "SmacLattice:/tmp/plancmp/战队/plan_lattice.txt"

# ④ 裁剪 + 图例位置 + 字号（地图大、路径只占一小块时用）
#    --crop       世界坐标矩形 "x0,y0,x1,y1"（米）；以负号开头时必须写 --crop=…
#    --legend-pos tl|tr|bl|br（图例放哪，标题会自动放到另一侧）
#    --font-scale 字号缩放（裁剪后画布变小、图例占屏太多就调小）
python3 tools/plot_path.py assets/zhandui/path_lattice.png \
  "SmacLattice:/tmp/plancmp/战队/plan_lattice.txt" \
  --map 战队 --scale 5 --grid 2 --crop=6.0,-4.4,18.0,7.0 \
  --legend-pos br --font-scale 0.4 --color 5 \
  --title "SmacPlannerLattice - omni (CHOSEN)"
```

**配色是固定的**，按传参顺序取：①红 ②蓝 ③绿 ④紫 ⑤黄；
单图想和汇总图对得上就用 `--color N` 指定。
所以传参顺序**必须固定为 NavFn → ThetaStar → Smac2D**，否则图文对不上。

> **关键**：三次对比必须用**同一组起终点**，否则转折数没有可比性。

> ⚠️ 图例/标题的中文会变成方块 —— `cv2.putText` 只支持 ASCII。
> 中文说明写在 Markdown 图注里，不要塞进图片。

## 怎么制作录屏

- **Foxglove**：连 `ws://localhost:8765`（连接方法见 [任务规划.md](../任务规划.md) §3）
- 订阅 `/plan`、`/global_costmap`、`/local_costmap`、`/cmd_vel`
- 建议两版**并排录**，这是验收"效果演示"最有力的材料

## 注意事项

- 视频建议控制在 10 MB 以内；超大可只留 GIF 或关键帧截图。
- 图片是二进制，改了不会在 git diff 里显示 —— 提交时写清"改了什么、为什么"。
