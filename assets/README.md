# 演示材料

> 本目录存放验收"效果演示"用的素材。
> 相关文档：[导航提交作业.md](../导航提交作业.md)（报告）、[tools/README.md](../tools/README.md)（制作工具）

## 现有文件

| 文件 | 内容 | 状态 |
|---|---|---|
| `navfn_baseline_path.png` | **NavFn 基线路径图**：地图 + 路径 + 起终点，可见锯齿折线 | ✅ |
| `navfn_baseline_raw.txt` | 该次规划的**原始输出**（含 823 个路径点，用于复现） | ✅ |
| `compare_navfn_vs_smac2d.png` | **NavFn vs Smac2D 对比图**（红=NavFn 锯齿，蓝=Smac2D 平滑） | ✅ |

### `compare_navfn_vs_smac2d.png` —— 验收"效果演示"的主力材料

同一组起终点（`world(0,0)` → `(20,0)`）叠在同一张图上：

| 线 | 规划器 | 长度 | 转折数 | 最大转角 | 急转(>45°) |
|---|---|---|---|---|---|
| **红线** | NavFn | 41.53 m | 368 | **179.8°** | **103 次** |
| **蓝线** | Smac2D | **35.55 m** | 43 | **10.1°** | **0 次** |

视觉上一眼可见：红线**锯齿、贴障碍、绕远**；蓝线**平滑、走通道中间、更短**。

> ⭐这张图还隐含一个关键认知：**转折数少 ≠ 更平滑**。
> ThetaStar 的转折数（35）比 Smac2D（43）还少，但拐得硬（最大 63°）。
> 详见 [实验记录.md](../实验记录.md) 的 9.28 节与
> [任务规划.md](../任务规划.md) 阶段 4.5。

### `navfn_baseline_path.png` 里画的是什么

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
| `theta_star_path.png` | ThetaStar 的路径图（补齐三种对比） | 切到 ThetaStar 跑一次，用 `plot_path.py` 画 |
| `compare_three.png` | **三种画在同一张图** | `plot_path.py` 一次传三条路径 |
| `plan_rate.png` | `/plan` 频率对比截图 | `ros2 topic hz /plan` |
| `costmap.png` | 代价地图分布 | `costmap_probe.py` 输出 |
| `demo_*.mp4` / `.gif` | 运行录屏 | Foxglove |

## 命名规范

```
<规划器>_<内容>.png     例：navfn_baseline_path.png / smac2d_baseline_path.png
<规划器>_<内容>.txt     例：navfn_baseline_raw.txt
compare_<A>_vs_<B>.png  例：compare_navfn_vs_smac2d.png
```

保持 `<规划器>` 前缀一致，报告里就能成对引用。

## 怎么制作路径图

```bash
# ① 跑规划，保存输出
ros2 action send_goal /compute_path_to_pose nav2_msgs/action/ComputePathToPose \
  "{goal: {header: {frame_id: world}, pose: {position: {x: 20.0, y: 0.0, z: 0.0}}}, use_start: false}" \
  > /tmp/plan_navfn.txt

# ② 画图
cd /workspaces/RMCS/docs/zh-cn/算法组考核
python3 tools/plot_path.py assets/navfn_baseline_path.png "NavFn:/tmp/plan_navfn.txt"
```

> **关键**：两次对比必须用**同一组起终点**，否则转折数没有可比性。

## 怎么制作录屏

- **Foxglove**：连 `ws://localhost:8765`（连接方法见 [任务规划.md](../任务规划.md) §3）
- 订阅 `/plan`、`/global_costmap`、`/local_costmap`、`/cmd_vel`
- 建议两版**并排录**，这是验收"效果演示"最有力的材料

## 注意事项

- 视频建议控制在 10 MB 以内；超大可只留 GIF 或关键帧截图。
- 图片是二进制，改了不会在 git diff 里显示 —— 提交时写清"改了什么、为什么"。
