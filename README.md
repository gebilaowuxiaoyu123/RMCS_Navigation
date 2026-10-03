# 算法组考核 · 导航方向

> 《2027赛季算法组培训考核作业细则》**§3 导航方向**的提交与过程记录。
> 本文件夹挂到独立仓库 `RMCS_Navigation`（过程中提交此处，最终版回 `RMCS_Test`）。

## 文档

三个 md 各有分工（怎么配合见 [任务规划.md](任务规划.md) §8.4）：

| 文件 | 性质 | 什么时候改 |
|---|---|---|
| **[导航提交作业.md](导航提交作业.md)** | ⭐ **提交报告（验收用）**：按验收三问组织，语言凝炼 | **有实质进展时**才改，没进展就不动 |
| **[任务规划.md](任务规划.md)** | 📘 **教学指南**：认知准备、环境启动、Foxglove 观测教学、分阶段计划、调参教学、命令速查、**真车上车流程**、**怎么标目标点**、**参数手册** | 每次操作有变化时补对应教学（尽量通俗） |
| **[实验记录.md](实验记录.md)** | 📋 **日志**：时间 + 执行 + 结果 + 问题 + 结论 | **每次实验后**追加一节 |

辅助目录：

| 目录 | 内容 |
|---|---|
| [config/](config/) | 配置快照（改动前后对比，作为报告证据） |
| [tools/](tools/) | 观测工具（`virtual_chassis.py`：让静态环境动起来） |
| [assets/](assets/) | 演示材料（路径可视化、原始输出、录屏） |
| `blog.txt` | 个人日志（**由作者本人维护**） |

## 一页速览

- **任务**：换掉全局规划器（细则禁用 `NavfnPlanner`），调参做到导航无明显卡顿，实现实际场地跨场导航。
- **选型**：`nav2_smac_planner::SmacPlannerLattice`，`lattice_filepath` 指向**本车自建的 10cm 全向原语**
  `lattice/omni_10cm.json`（`motion_model: omni` / `grid_resolution: 0.1` / 16 航向 / **136 条原语**）。
  ⚠️ **不用** Nav2 自带的 `sample_primitives` 那份 —— 它是 `grid_resolution = 0.05`，
  与本场代价图（10cm）对不上。官方 `lattice_primitives/README.md` 原话：
  “grid_resolution … **This should be the same as your costmap resolution.**”
- **理由**：
  1. **约束收紧后的唯一可行解**。NavFn 被细则禁用、`SmacPlanner2D` 被追加排除、ThetaStar 弃用；
     而 `SmacPlannerHybrid` 实测**只支持 `DUBIN` / `REEDS_SHEPP` 两种阿克曼模型**，报错原文：
     `Invalid motion model for Hybrid A*. Please select between Dubin (Ackermann forward only), Reeds-Shepp (Ackermann forward and back).`
     ⇒ 用在全向哨兵上等于**强行加转弯半径**。
  2. **Lattice 的运动模型由 lattice 文件自身决定，而 Nav2 官方就带了 `omni` 原语**：
     `sample_primitives/5cm_resolution/{0.5m,1m}_turning_radius/omni/output.json`，
     其 `lattice_metadata.motion_model = "omni"`
     ⇒ **库存里唯一能原生跑全向的合规候选**。
     ⚠️ 必须显式给 `lattice_filepath` —— 默认值是 `ackermann` 那份，而且**静默生效、不报错**。
  3. ~~**代价（待解决）**：lattice 是 5cm 网格、本场代价图是 10cm，Nav2 官方要求两者一致~~
     ⇒ **已解决**：自己用官方 `generate_motion_primitives.py` 生成了 **10cm** 版本
     （`lattice/omni_10cm.json`，136 条原语），与代价图分辨率对齐。
     生成配置与复现步骤见 `lattice/README.md`。
- **参考数据（三种规划器同一起终点实测）**：长度 NavFn 41.53 m / ThetaStar 35.68 m / Smac2D 35.55 m；
  转折数 368 / 35 / 43；最大转角 179.8° / 63.4° / 10.1°。NavFn 与 ThetaStar 均已排除，数据留作对比。
- **改动位置**：`rmcs-navigation/config/motion.yaml`（纯 yaml 配置，不改 C++）。

## 完成度

| 项 | 状态 |
|---|---|
| 依赖栈 + 环境搭建（补齐缺失依赖） | ✅ |
| 真车链路修复（补编译 `rmcs_localization`，治 `base_link` 断链） | ✅ |
| 基线确认（现用 `NavfnPlanner`） | ✅ |
| 地图确认（`rmuc-v2.png`，29.2 × 16.1 m） | ✅ |
| 无机器人测试环境（`static.launch.yaml`，5 节点 `active`） | ✅ |
| **基线跑通 + 效果观察**（368 转折、`/plan` 0.99 Hz） | ✅ |
| 三种规划器横向实测（NavFn / ThetaStar / Smac2D） | ✅ |
| 候选可行性核验（`strings` 实测插件支持的 motion model） | ✅ |
| 方案选型论证（→ `SmacPlannerLattice` + omni 原语） | ✅ |
| 规划器切换实施（`plugin` / `motion_model` / `lattice_filepath` 三行） | ✅ |
| 自建 **10cm** omni 原语（`lattice/omni_10cm.json`，136 条） | ✅ |
| 代价图未知区与 `critical_cost` 排查（“白区能到、灰区不动”） | ✅ |
| `no valid path found` 死循环定位 | ✅ |
| lattice ↔ 代价图分辨率对齐（5cm → **10cm**） | ✅ |
| **底盘类型纠正**（舵轮而非固定全向，影响 footprint 与运动模型） | ✅ |
| **重定位链路修复**（`rmcs-localization` submodule 版本对齐 → FIFO 触发打通） | ✅ |
| **重定位配准修复**（`blue` 初值错 20 m → 改为场地原点） | ✅ |
| **`train.lua` 端点**（含 `relocalize` / 关小陀螺 / 关自动巡逻） | ✅ |
| **实车「点两个点能到」验收** | ✅ |
| **调参期问题全量归类**（23 类根因，见 [导航提交作业.md](导航提交作业.md) §3.6） | ✅ |
| **「最后一次调参」清单定稿**（5 项改动 + 6 条判据 + 7 项不做，见 §3.7） | ✅ |
| **「无法稳定上坡」定位到机制层**（**上坡不走 Nav2**，见 §3.6.2） | ✅ 已定位 / ❌ **未解决** |
| 「最后一次调参」执行 | ⏳ |
| 调参消除卡顿（已有 3 组已知坑的参数记录） | ⏳ |
| 对比录屏 | ⏳ |

详见 [导航提交作业.md](导航提交作业.md) §4.1。

> **初步完成判据**：实车上启用导航后，重定位稳定成功（`fitness ≈ 0.03`，阈值 0.05），
> `world→odom` 正确发布，在 Foxglove 里点两个点车能到达。
> 完整过程见 [实验记录.md](实验记录.md) 2026-10-01 各条。

## 仓库结构

```
RMCS_Navigation/                  ← 本仓库
├── README.md                     ← 本文件
├── 导航提交作业.md                ← 提交报告（验收用，凝炼）
├── 任务规划.md                    ← 教学指南（含 Foxglove 观测教学）
├── 实验记录.md                    ← 实验日志（时间+执行+结果+问题+结论）
├── blog.txt                      ← 个人日志（由作者本人维护）
├── config/                       ← 配置快照
│   ├── motion.yaml.navfn-baseline   切换前的 NavFn 基线
│   ├── motion.xml.navfn-baseline    行为树基线
│   └── README.md                    快照说明
├── tools/                        ← 观测工具
│   ├── virtual_chassis.py           虚拟底盘（让静态环境动起来）
│   └── README.md                    工具说明
└── assets/                       ← 演示材料
    ├── path_compare_all.png        ⭐ 演示套图：五台规划器汇总对比（主力材料，战队图）
    ├── path_navfn.png              ⭐ 演示套图：NavFn 单张（基线，已禁用）
    ├── path_theta_star.png         ⭐ 演示套图：ThetaStar 单张
    ├── path_smac2d.png             ⭐ 演示套图：Smac2D 单张（已排除，留作对比）
    ├── path_smac_hybrid.png        ⭐ 演示套图：SmacHybrid 单张（阿克曼，仅对比）
    ├── path_smac_lattice.png       ⭐ 演示套图：SmacLattice 单张（最终选中）
    ├── map_zhandui_grid.png         🗺️ 标点用：战队.png（现场图）带世界坐标网格
    ├── navfn_baseline_path.png      早期素材：9.22 首测基线图（RMUC 底图）
    ├── compare_navfn_vs_smac2d.png  早期素材：两规划器对比（前身，RMUC 底图）
    ├── navfn_baseline_raw.txt       基线原始输出（823 路径点，可复现）
    └── README.md                    材料清单
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
- ✅ **飞书提交（已完成）**：《Alliance算法组大作业》
  `https://fa4g5no1b1f.feishu.cn/wiki/ISJowRRZkiBLvykxXdTc6GiLnhb`
  正文由 [提交草稿.md](提交草稿.md) 写入（已配图/表格，含目录）。
- 📄 **要求原文**：《2027赛季算法组培训考核作业细则》
  `https://fa4g5no1b1f.feishu.cn/docx/GTwtdj07Nou7nLxWF5zcJufHnyf` §3 导航方向
  —— 「使用 `rmcs-navigation-deps` 控制哨兵，选用**非 `NavfnPlanner`** 的全局规划器实现**跨场导航**，
  验收需说明**规划器选型逻辑、调参思路**，完成**效果演示**并提交代码至 **GitHub**」

详细流程见 [任务规划.md](任务规划.md) §8。

## 注意

- 依赖栈 `rmcs_ws/src/rmcs-navigation-deps/` 是第三方代码，**不入任何作业仓**（已在 `.gitignore` 中）。
- ⚠️ **规划器候选受「运动学模型」硬限制，但两种 Smac 不一样，别混为一谈**：
  - `SmacPlannerHybrid` 的运动模型**写死在插件里**，只有 `DUBIN` / `REEDS_SHEPP`（阿克曼）
    ⇒ 全向底盘**不能用**。报错原文：
    `Invalid motion model for Hybrid A*. Please select between Dubin (Ackermann forward only), Reeds-Shepp (Ackermann forward and back).`
  - `SmacPlannerLattice` 的运动模型**写在 `lattice_filepath` 指向的文件里**
    （`lattice_metadata.motion_model` 可为 `diff` / `omni` / `ackermann`）
    ⇒ **用 omni 那份就能原生跑全向**。默认是 ackermann 那份，且**静默生效、不报错**。
  详见 [实验记录.md](实验记录.md) 2026-09-30 条（含该条目的自我修正）。
- ⚠️ **真车 `sensor.launch.yaml` 硬依赖 `rmcs_localization`**。该包不在默认单包编译范围内，
  漏编会**整个 sensor 栈起不来** —— 表现就是“无 TF / 无 costmap / 无 `/plan`”、
  `base_link` 断链。修法与验证见 [实验记录.md](实验记录.md) 2026-09-29 条。
- ⚠️ **实车导航入口不带 `foxglove_bridge`**（只有 `static` / `recall` 带），
  所以“Foxglove 里没数据”不等于“导航没跑”。详见 [任务规划.md](任务规划.md) §3.7。- 🔴 **地图与实际场地有出入（未解决）**：队长给的扫描图 `maps/战队.png` 有
  **一处后来放了障碍**，但图上仍是自由区 ⇒ **全局代价图没有 obstacle 层**，
  会把路径规划穿过去；而局部代价图挂的是 `/local_map`（实时障碍），车开到跟前会被挡。
  **位置待标注**（可用 `assets/map_zhandui_grid.png`，带世界坐标网格）。
  详见 [实验记录.md](实验记录.md) 2026-10-01 收尾条目 §二①。
- 🔴 **「无法稳定上坡」不是 Nav2 的问题（已定位，未解决）**：哨兵上坡**不走导航**，
  而是一条独立流程 —— `map/train.lua` 的图边 → `action:blocking_cross_step()` →
  `/rmcs_navigation/request/{cross_direction,is_climb}` → `rmcs-core` 的 **`SentryClimber` 状态机**
  → `/chassis/climber/{direction,speed,status}` → `ChassisController`。
  而**手动点目标走 `navigate_to_pose`，绕开了这张图** ⇒ 爬坡请求从未发出 ⇒ 状态机全程空闲。
  ⇒ **在 `motion.yaml` 里怎么调都调不出上坡，方向就是错的。**
  判据：`ros2 topic echo /chassis/climber/status`（一直是 `0` = 请求没发）。
  详见 [导航提交作业.md](导航提交作业.md) §3.6.2、[任务规划.md](任务规划.md) §11.7。
- ⚠️ **`sentry.yaml` 里有新标定的舵轮零位**（`left_front 5919` / `left_back 5260` /
  `right_back 3058` / `right_front 5167`）—— **不要把整个文件回退到旧版本**，会丢掉标定。
- ⚠️ **实车跑通有 4 个隐藏前提**（静态栈全绿 ≠ 实车能跑）：端点要选会调 `relocalize()` 的、
  重定位要成功、不能有小陀螺、目标转发要开。清单见 [任务规划.md](任务规划.md) §四 阶段 8。