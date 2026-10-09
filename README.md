# 算法组考核 · 导航方向

> 《2027赛季算法组培训考核作业细则》**§3 导航方向**的提交与过程记录。
> 本文件夹挂到独立仓库 `RMCS_Navigation`（过程中提交此处，最终版回 `RMCS_Test`）。

## 文档

几份 md 各有分工（怎么配合见 [任务规划.md](任务规划.md) §8.4）：

| 文件 | 性质 | 什么时候改 |
|---|---|---|
| **[导航提交作业.md](导航提交作业.md)** | **提交报告**（飞书大作业的正文同步在此）：按验收三问组织，语言凝炼 | **有实质进展时**才改，没进展就不动 |
| **[接手指南.md](接手指南.md)** | **交接文档**（换人/换设备先看这个）：任务现状、仓库地图、环境搭建、待办清单、硬结论速查、红线 | 人员或环境变动时 |
| **[任务规划.md](任务规划.md)** | **教学指南**：认知准备、环境启动、Foxglove 观测教学、分阶段计划、调参教学、命令速查、**真车上车流程**、**怎么标目标点**、**参数手册** | 每次操作有变化时补对应教学（尽量通俗） |
| **[实验记录.md](实验记录.md)** | **日志**：时间 + 执行 + 结果 + 问题 + 结论 | **每次实验后**追加一节 |
| **[飞书正文.md](飞书正文.md)** | 与提交报告同内容（写入飞书时用的副本） | 随提交报告一起改 |
| **[飞书交付指南.md](飞书交付指南.md)** / **[提交草稿.md](提交草稿.md)** | 飞书写入流程与草稿归档 | 仅在需要改那篇飞书文档时看 |

辅助目录：

| 目录 | 内容 |
|---|---|
| [config/](config/) | 配置快照（切换前的 NavFn 基线，作为报告证据） |
| [tools/](tools/) | 取数与绘图工具（`plancmp/` 五规划器对比链路、`charts/` 调参可视化、`feishu/` 文档写入；另有 `plot_path.py`、`plan_metrics.py`、`costmap_probe.py`、`virtual_chassis.py`） |
| [assets/](assets/) | 演示材料（`rmuc/` `zhandui/` 路径对比图各 6 张、`tuning/` 调参可视化、`tables/` 文档用表格图） |
| `blog.txt` | 个人日志（**由作者本人维护**） |

## 一页速览

> 下表的 § 均指 [导航提交作业.md](导航提交作业.md) 的章节。

| 细则要求 | 我们的答案 | 详见 |
|---|---|---|
| 换掉现在的全局规划器 | 换成 `nav2_smac_planner::SmacPlannerLattice`，配自建的 **10 cm 全向原语** | §3.3、`config/motion.yaml` |
| 讲清选型理由与现规划器的差异 | 五个候选在两张图上各跑同一起终点，比长度 / 转弯 / 曲率 | §3.1 ～ §3.4 |
| 调参做到无明显卡顿 | 逐项核对参数是否真正生效，把膨胀层调到能用 | §4.3、§4.4 |
| 讲调参思路 | 先确认「这个参数到底生不生效」，再决定改不改 | §4.1、§4.2 |
| 实际场地跨场导航 | 静态验证、重定位、手动导航，链路已打通 | §5、§6 |

一句话：这一轮真正花时间的不是「选哪个规划器」，而是搞清楚**哪些参数其实根本没生效**。

### 选型：为什么是 SmacPlannerLattice

1. **只有它能表达「全向」这件事。** 本车是舵轮全向底盘，能横着走、斜着走。`SmacPlannerHybrid` 这类插件是为车式底盘设计的（有最小转弯半径），拿来跑全向等于凭空给车加了个转弯半径，窄口更进不去。而 Lattice 的运动能力由**原语文件**决定 —— 原语是一张预先算好的表，里面是一条条小车实际能做的动作（直行、斜着走、原地转、拐弧线），把原语做成全向的，它就真能横着走。
2. **原语文件是自己写的，能对上代价图。** 官方 demo 是 5 cm 分辨率的阿克曼原语，本车代价图分辨率是 0.1 m，两者对不上（原语比格子还细）。自己做了 **10 cm / 16 航向 / 136 条原语**的版本（`lattice/omni_10cm.json`），与代价图一一对应。
3. **它是五个里表现最稳的那个。** `Smac2D` 的最大转角 8.7° 最漂亮，但它是纯栅格搜索、没有运动学概念；Lattice 的长度和转角都处在中间，没有明显短板。

> 必须显式给 `lattice_filepath`：默认值是 ackermann 那份，而且静默生效、不报错。

### 实测数据（五个规划器、两张图、各自同一起终点）

**RMUC `(0,0)` → `(20,0)`（单程）**

| 规划器 | 长度 | 转弯数（>5°） | 转弯密度 | 最大转角 |
|---|---|---|---|---|
| NavFn（现网基线） | 34.79 m | 91 | 2.62 次/m | 94.1° |
| ThetaStar | 34.09 m | 25 | 0.73 次/m | 49.8° |
| Smac2D | 34.06 m | 46 | 1.35 次/m | 8.7° |
| SmacHybrid | 34.06 m | 43 | 1.26 次/m | 23.3° |
| SmacLattice | 37.99 m | 74 | 1.95 次/m | 116.3° |

**战队 `(0,0)` 往返 `(4,2)`**

| 规划器 | 往返全长 | 转弯数 | 转弯密度 | 去程 / 回程 |
|---|---|---|---|---|
| NavFn | 30.27 m | 216 | 7.14 次/m | 14.29 / 15.96 |
| ThetaStar | 26.11 m | 39 | 1.49 次/m | 13.09 / 13.03 |
| Smac2D | 24.83 m | 87 | 3.50 次/m | 12.43 / 12.40 |
| SmacHybrid | 24.55 m | 77 | 3.14 次/m | 12.16 / 12.40 |
| SmacLattice | 27.37 m | 88 | 3.22 次/m | 13.96 / 13.41 |

> 对比全部用 Nav2 上游**默认参数**，只有 Lattice 改了一处：`change_penalty` 0.05 → 1.0（默认值会给出穿墙路径，见 §4.7）。
> 实车那套 `motion.yaml` 是反复调出来的，与静态对比刻意分开。

- **最后一轮调参定稿**：只动局部代价图两项 —— `inflation_radius` 0.28 → **0.38**（必须大于车体外接圆半径 0.364160）、`PathAlignCritic.cost_weight` 5.2 → **7.5**；`cost_scaling_factor` 保留 0.55。
- **改动位置**：`rmcs-navigation/config/motion.yaml`（纯 yaml 配置，不改 C++）。

## 完成情况

**已落地**（每项都有落盘证据）：

- 依赖栈 + 环境搭建、真车链路修复（补编译 `rmcs_localization`，治 `base_link` 断链）
- 基线确认、地图确认、无机器人测试环境（`static.launch.yaml`）
- 五规划器横向实测（RMUC + 战队两张图、同一起终点）+ 候选可行性核验
- `SmacPlannerLattice` + 自建 10 cm 全向原语落盘（`lattice/omni_10cm.json`，136 条）
- 底盘类型纠正（舵轮而非固定全向）、重定位链路与配准修复、`train.lua` 端点适配
- 实车「点两个点能到」验收
- 调参两条硬下限（膨胀半径 / 代价等级）定位 + 最后一轮定稿
- 调参期问题全量归类（23 类根因，见 [导航提交作业.md](导航提交作业.md) §7 附录）
- 「无法稳定上坡」定位到机制层（**上坡不走 Nav2**，见报告 §6）

**尚未完成**：

- [ ] 换规划器后 `/plan` 与 `/cmd_vel` 同屏录屏（Foxglove）
- [ ] 跨场导航完整跑通录像
- [ ] `ros2 param get /planner_server GridBased.plugin` 回读截图
- [ ] 本轮 `motion.yaml` 的 diff 截图

前 4 项就是提交报告 §5.3 的「待补材料」。此外**上坡问题已定位但未实测验证**，详见报告 §6 与本文末「注意」。

> **初步完成判据**：实车上启用导航后，重定位稳定成功（`fitness ≈ 0.03`，阈值 0.05），
> `world→odom` 正确发布，在 Foxglove 里点两个点车能到达。
> 完整过程见 [实验记录.md](实验记录.md) 2026-10-01 各条。

## 仓库结构

```
RMCS_Navigation/                  ← 本仓库
├── README.md                     ← 本文件
├── 导航提交作业.md                ← 提交报告（飞书大作业正文同步在此）
├── 接手指南.md                    ← 交接文档（换人/换设备先看）
├── 任务规划.md                    ← 教学指南（含 Foxglove 观测教学）
├── 实验记录.md                    ← 实验日志（时间 + 执行 + 结果 + 问题 + 结论）
├── 飞书正文.md                    ← 与提交报告同内容（写入飞书用副本）
├── 飞书交付指南.md / 提交草稿.md   ← 飞书写入流程与草稿
├── blog.txt                      ← 个人日志（由作者本人维护）
├── config/                       ← 配置快照
│   ├── motion.yaml.navfn-baseline   切换前的 NavFn 基线
│   ├── motion.xml.navfn-baseline    行为树基线
│   └── README.md                    快照说明
├── tools/                        ← 取数与绘图工具
│   ├── README.md                    工具说明
│   ├── plot_path.py                 路径取数与绘制
│   ├── plan_metrics.py              路径指标（长度 / 转弯 / 曲率）
│   ├── costmap_probe.py             代价图探查
│   ├── virtual_chassis.py           虚拟底盘（让静态环境动起来）
│   ├── plancmp/                     五规划器对比链路（run_all.py 等）
│   ├── charts/mkcharts_cv.py        调参可视化
│   └── feishu/                      飞书文档写入
└── assets/                       ← 演示材料
    ├── rmuc/                      RMUC 图：1 张五规划器汇总 + 5 张单图
    ├── zhandui/                   战队图：1 张五规划器汇总 + 5 张单图
    ├── tuning/                    调参可视化（轨迹 / 事件 / 频次）
    ├── tables/                    文档用表格渲染图
    ├── map_zhandui_grid.png       标点用：战队.png（现场图）带世界坐标网格
    ├── navfn_baseline_path.png    早期素材：9.22 首测基线图（RMUC 底图）
    ├── compare_navfn_vs_smac2d.png 早期素材：两规划器对比（前身，RMUC 底图）
    ├── navfn_baseline_raw.txt     基线原始输出（823 路径点，可复现）
    └── README.md                  材料清单
```

## 相关仓库

| 仓库 | 内容 |
|---|---|
| `gebilaowuxiaoyu123/RMCS_Navigation`（本仓库） | 提交报告、过程规划、配置快照 |
| `gebilaowuxiaoyu123/rmcs-navigation` | 代码改动（分支 `feat/nav-on-zlq8-5`，基线 `dev/zlq-8-5` + 补 `rmcs_description` 依赖） |
| `Alliance-Algorithm/rmcs-navigation` | 上游官方（remote 名 `upstream`，仅拉更新） |
| `gebilaowuxiaoyu123/RMCS_Test` | 作业主仓（最终版提交回此处） |

## 工作流

- **过程中**：改动提交到本仓库（`RMCS_Navigation`）
- **最终版**：同步回 `RMCS_Test`
- **飞书提交（已完成）**：《Alliance算法组大作业》
  `https://fa4g5no1b1f.feishu.cn/wiki/ISJowRRZkiBLvykxXdTc6GiLnhb`
  正文与 [导航提交作业.md](导航提交作业.md) 同源（副本见 [飞书正文.md](飞书正文.md)）。
- **要求原文**：《2027赛季算法组培训考核作业细则》
  `https://fa4g5no1b1f.feishu.cn/docx/GTwtdj07Nou7nLxWF5zcJufHnyf` §3 导航方向
  —— 「使用 `rmcs-navigation-deps` 控制哨兵，选用**非 `NavfnPlanner`** 的全局规划器实现**跨场导航**，
  验收需说明**规划器选型逻辑、调参思路**，完成**效果演示**并提交代码至 **GitHub**」

详细流程见 [任务规划.md](任务规划.md) §8。

## 注意

- 依赖栈 `rmcs_ws/src/rmcs-navigation-deps/` 是第三方代码，**不入任何作业仓**（已在 `.gitignore` 中）。
- **规划器候选受「运动学模型」硬限制，但两种 Smac 不一样，别混为一谈**：
  - `SmacPlannerHybrid` 的运动模型**写死在插件里**，只有 `DUBIN` / `REEDS_SHEPP`（阿克曼）
    ⇒ 全向底盘**不能用**。报错原文：
    `Invalid motion model for Hybrid A*. Please select between Dubin (Ackermann forward only), Reeds-Shepp (Ackermann forward and back).`
  - `SmacPlannerLattice` 的运动模型**写在 `lattice_filepath` 指向的文件里**
    （`lattice_metadata.motion_model` 可为 `diff` / `omni` / `ackermann`）
    ⇒ **用 omni 那份就能原生跑全向**。默认是 ackermann 那份，且**静默生效、不报错**。
  详见 [实验记录.md](实验记录.md) 2026-09-30 条（含该条目的自我修正）。
- **真车 `sensor.launch.yaml` 硬依赖 `rmcs_localization`**。该包不在默认单包编译范围内，
  漏编会**整个 sensor 栈起不来** —— 表现就是「无 TF / 无 costmap / 无 `/plan`」、`base_link` 断链。
  修法与验证见 [实验记录.md](实验记录.md) 2026-09-29 条。
- **实车导航入口不带 `foxglove_bridge`**（只有 `static` / `recall` 带），
  所以「Foxglove 里没数据」不等于「导航没跑」。详见 [任务规划.md](任务规划.md) §3.7。
- **地图与实际场地有出入（未解决）**：队长给的扫描图 `maps/战队.png` 有**一处后来放了障碍**，
  但图上仍是自由区 ⇒ **全局代价图没有 obstacle 层**，会把路径规划穿过去；
  而局部代价图挂的是 `/local_map`（实时障碍），车开到跟前会被挡。
  **位置待标注**（可用 `assets/map_zhandui_grid.png`，带世界坐标网格）。
  详见 [实验记录.md](实验记录.md) 2026-10-01 收尾条目 §二①。
- **「无法稳定上坡」不是 Nav2 的问题（已定位，未解决）**：哨兵上坡**不走导航**，
  而是一条独立流程 —— `map/train.lua` 的图边 → `action:blocking_cross_step()` →
  `/rmcs_navigation/request/{cross_direction,is_climb}` → `rmcs-core` 的 `SentryClimber` 状态机
  → `/chassis/climber/{direction,speed,status}` → `ChassisController`。
  而**手动点目标走 `navigate_to_pose`，绕开了这张图** ⇒ 爬坡请求从未发出 ⇒ 状态机全程空闲。
  ⇒ **在 `motion.yaml` 里怎么调都调不出上坡，方向就是错的。**
  判据：`ros2 topic echo /chassis/climber/status`（一直是 `0` = 请求没发）。
  详见 [导航提交作业.md](导航提交作业.md) §6。
- **`sentry.yaml` 里有新标定的舵轮零位**（`left_front 5919` / `left_back 5260` /
  `right_back 3058` / `right_front 5167`）—— **不要把整个文件回退到旧版本**，会丢掉标定。
- **实车跑通有 4 个隐藏前提**（静态栈全绿 ≠ 实车能跑）：端点要选会调 `relocalize()` 的、
  重定位要成功、不能有小陀螺、目标转发要开。清单见 [任务规划.md](任务规划.md) §四 阶段 8。