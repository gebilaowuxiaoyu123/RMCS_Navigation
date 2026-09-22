# 算法组考核 · 导航方向

> 《2027赛季算法组培训考核作业细则》**§3 导航方向**的提交与过程记录。
> 本文件夹挂到独立仓库 `RMCS_Navigation`（过程中提交此处，最终版回 `RMCS_Test`）。

## 文档

| 文件 | 用途 |
|---|---|
| **[导航提交作业.md](导航提交作业.md)** | ⭐ **提交报告（验收用）**：任务要求、方案选型论证、实施过程、结果数据、问题与解决、提交信息 |
| [任务规划.md](任务规划.md) | 过程规划与操作教程：认知准备、环境准备、五阶段执行计划、命令速查、检查清单 |
| [config/](config/) | 配置快照（改动前后对比，作为报告证据） |
| `assets/` | 演示材料（录屏/截图，待补） |

## 一页速览

- **任务**：换掉全局规划器（细则禁用 `NavfnPlanner`），调参做到导航无明显卡顿，实现实际场地跨场导航。
- **选型**：`nav2_smac_planner::SmacPlanner2D`。
- **理由**：内置路径平滑（治折线转折降速）+ 多分辨率降采样（治大地图规划耗时）+ 显式障碍代价 `cost_penalty`（路径走通道中间）。
- **改动位置**：`rmcs-navigation/config/motion.yaml`（纯 yaml 配置，不改 C++）。

## 完成度

| 项 | 状态 |
|---|---|
| 依赖栈 + 环境搭建（补齐缺失依赖） | ✅ |
| 基线确认（现用 `NavfnPlanner`） | ✅ |
| 地图确认（`rmuc-v2.png`，29.2 × 16.1 m） | ✅ |
| 无机器人测试环境（`static.launch.yaml`，4 节点 `active`） | ✅ |
| 方案选型论证（选 `SmacPlanner2D`） | ✅ |
| 规划器切换实施 | ⏳ |
| 调参消除卡顿 | ⏳ |
| 跨场验证 | ⏳ |
| 基线 / 对比 录屏 | ⏳ |

详见 [导航提交作业.md](导航提交作业.md) §0.2。

## 仓库结构

```
RMCS_Navigation/                  ← 本仓库
├── README.md                     ← 本文件
├── 导航提交作业.md                ← 提交报告（验收用）
├── 任务规划.md                    ← 过程规划与教程
├── config/                       ← 配置快照
│   ├── motion.yaml.navfn-baseline   切换前的 NavFn 基线
│   ├── motion.xml.navfn-baseline    行为树基线
│   └── README.md                    快照说明
└── assets/                       ← 演示材料（录屏/截图，待补）
```

## 相关仓库

| 仓库 | 内容 |
|---|---|
| `gebilaowuxiaoyu123/RMCS_Navigation`（本仓库） | 提交报告、过程规划、配置快照 |
| `gebilaowuxiaoyu123/rmcs-navigation` | 代码改动（分支 `feat/smac-global-planner`） |
| `Alliance-Algorithm/rmcs-navigation` | 上游官方（remote 名 `upstream`，仅拉更新） |
| `gebilaowuxiaoyu123/RMCS_Test` | 作业主仓（最终版提交回此处） |

## 工作流

- **过程中**：改动提交到本仓库（`RMCS_Navigation`）
- **最终版**：同步回 `RMCS_Test`

详细流程见 [任务规划.md](任务规划.md) §8。

## 注意

- 依赖栈 `rmcs_ws/src/rmcs-navigation-deps/` 是第三方代码，**不入任何作业仓**（已在 `.gitignore` 中）。
