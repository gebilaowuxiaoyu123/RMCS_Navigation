# 演示材料

> 本目录存放验收"效果演示"用的素材。
> 相关文档：[导航提交作业.md](../导航提交作业.md)（报告）、[tools/README.md](../tools/README.md)（制作工具）

## 现有文件

### ⭐ 主力素材：三种规划器演示套图（统一风格）

四张图**同一组起终点**（`world(0,0)` → `(20,0)`）、**同一张底图**、**同一套画法**，
可直接放进报告。数据来自 `/tmp/plan_*.txt`（各规划器默认参数实测输出）。

| 文件 | 内容 | 关键数字 |
|---|---|---|
| `path_navfn.png` | NavFn 单图（现状基线） | 41.53 m / 368 转折 / 8.86 turns·m⁻¹ |
| `path_theta_star.png` | ThetaStar 单图 | 35.68 m / 35 转折 / 0.98 turns·m⁻¹ |
| `path_smac2d.png` | Smac2D 单图（选中） | 35.55 m / 43 转折 / 1.21 turns·m⁻¹ |
| `path_compare_three.png` | **三种叠在同一张图**（红=NavFn 蓝=ThetaStar 绿=Smac2D） | 同上三行 |

### 🗺️ 标点用底图

| 文件 | 内容 |
|---|---|
| `map_rmuc_grid.png` | **带世界坐标网格的场地底图**（每 2 m 一格，格线上标注世界坐标） |

用途：**上车前挑两个目标点，并确认没标在障碍上**。做法见
[任务规划.md](../任务规划.md) §十「怎么在地图上标目标点」。

```bash
cd /workspaces/RMCS/docs/zh-cn/算法组考核
# ① 生成带网格的底图（上边数字 = x，左边数字 = y）
python3 tools/plot_path.py assets/map_rmuc_grid.png --grid 2 --scale 3
# ② 换成你自己选的两个点，标出来确认（坐标因人而异，这个输出不入库）
python3 tools/plot_path.py assets/map_rmuc_pick.png --grid 2 --scale 3 --mark "1.5,0;18,3"
```

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
| `compare_navfn_vs_smac2d.png` | NavFn vs Smac2D 两图对比 | `path_compare_three.png` 的**两规划器前身**（未含 ThetaStar） |
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
path_<规划器>.png          演示套图单张   例：path_navfn.png / path_smac2d.png
path_compare_<数量>.png    演示套图汇总   例：path_compare_three.png
compare_<A>_vs_<B>.png     两两对比（早期）例：compare_navfn_vs_smac2d.png
<规划器>_<内容>.txt        原始数据       例：navfn_baseline_raw.txt
```

**演示套图统一用 `path_` 前缀**，保证四种规划器的图在文件列表里挨在一起、风格一致。

## 怎么制作路径图

```bash
# ① 跑规划，保存输出（每换一次规划器都要重跑并另存一份）
ros2 action send_goal /compute_path_to_pose nav2_msgs/action/ComputePathToPose \
  "{goal: {header: {frame_id: world}, pose: {position: {x: 20.0, y: 0.0, z: 0.0}}}, use_start: false}" \
  > /tmp/plan_navfn.txt

# ② 画单张（--title 可选，只能填英文：cv2 画不了中文）
cd /workspaces/RMCS/docs/zh-cn/算法组考核
python3 tools/plot_path.py assets/path_navfn.png \
  --title "Global planner: NavFn (baseline)" \
  "NavFn:/tmp/plan_navfn.txt"

# ③ 画汇总（一次传多条路径即可叠加）
python3 tools/plot_path.py assets/path_compare_three.png \
  --title "Same start & goal - three global planners compared" \
  "NavFn:/tmp/plan_navfn.txt" \
  "ThetaStar:/tmp/plan_theta.txt" \
  "Smac2D:/tmp/plan_smac_default.txt"
```

**配色是固定的**，按传参顺序取：①红 ②蓝 ③绿 ④紫 ⑤黄。
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
