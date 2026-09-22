# 配置快照说明

本目录存放**配置改动的前后对比**，作为 [导航提交作业.md](../导航提交作业.md) 的证据材料。

## 文件

| 文件 | 说明 |
|---|---|
| `motion.yaml.navfn-baseline` | **改动前**的 `rmcs-navigation/config/motion.yaml`（规划器 = `NavfnPlanner`） |
| `motion.xml.navfn-baseline` | **改动前**的 `rmcs-navigation/config/motion.xml`（行为树，重规划频率 1.0 Hz） |
| `motion.yaml.smac` | ⏳ 待补：改动后的配置（规划器 = `SmacPlanner2D`） |

## 为什么要留快照

1. **可回退**：调参调坏了能对照恢复原始值。
2. **对比证据**：验收"与现有规划器的差异"时，`diff` 两个文件最直观。
3. **跨仓留痕**：代码改动在 `rmcs-navigation` fork 上，此处留一份快照，
   使本提交报告**自包含**——组长只看本仓库即可看到改动内容。

## 改动位置

配置的实际生效文件在依赖栈中（第三方代码，不入本仓库）：

```
rmcs_ws/src/rmcs-navigation-deps/rmcs-navigation/config/motion.yaml
```

> 该目录已在作业仓 `.gitignore` 中，重新拉取方式见 [../任务规划.md](../任务规划.md) §2.3。

## 查看差异

```bash
diff config/motion.yaml.navfn-baseline config/motion.yaml.smac
```
