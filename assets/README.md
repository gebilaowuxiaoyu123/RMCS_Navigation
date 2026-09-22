# 演示材料

本目录存放验收"效果演示"用的素材。

## 计划内容

| 文件（建议命名） | 内容 | 状态 |
|---|---|---|
| `baseline_navfn_plan.png` | NavFn 基线的规划路径截图 | ⏳ |
| `smac2d_plan.png` | SmacPlanner2D 的规划路径截图 | ⏳ |
| `plan_rate_compare.png` | 两者 `/plan` 输出频率对比（`ros2 topic hz`） | ⏳ |
| `costmap_before_after.png` | 代价地图对比（膨胀范围） | ⏳ |
| `demo_baseline.mp4` / `.gif` | NavFn 基线运行录屏 | ⏳ |
| `demo_smac2d.mp4` / `.gif` | SmacPlanner2D 运行录屏 | ⏳ |
| `cross_field.mp4` | 跨场导航演示 | ⏳ |

## 采集方式

- **截图 / 录屏**：Foxglove（连 `ws://localhost:8765`），订阅 `/plan`、`/global_costmap`、`/local_costmap`、`/cmd_vel`
- **频率数据**：`ros2 topic hz /plan` 截图
- **路径数据**：`ros2 topic echo /plan` 或保存为 rosbag 便于量化对比

## 注意事项

- 视频文件较大，建议控制在 10 MB 以内；超大可只保留 GIF 或关键帧截图。
- 截图统一命名前缀 `baseline_` / `smac2d_`，便于报告里成对引用。
