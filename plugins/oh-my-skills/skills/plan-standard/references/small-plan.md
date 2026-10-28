# 小计划模板

适用于单阶段、少于 10 个文件且不涉及架构决策的任务。

> **执行规则：** 完成所有变更后运行每一项验收命令。任何偏差必须先写入同一计划的“决策记录”再继续。计划评审和最终审计使用 Codex；不可用时只能由用户为本计划明确 waiver。

## 背景

[当前问题、现状和期望结果]

## 需求或假设

- 已确认：[用户已确认的决定]
- 假设：[未确认但采用的低风险默认值]

## 范围

- 包含：[本次处理内容]
- 不包含：[明确排除的内容及原因]

## 设计

[选定方案、复用点、取舍和被否决方案]

## 阶段 1：[阶段名称]

### 变更

| 操作 | 文件 | 具体修改 |
| --- | --- | --- |
| 新增/修改/删除 | `path/to/file` | [文件级修改] |

### 验收标准

- [ ] `python3 -m unittest discover -s tests -v` - 相关测试全部通过
- [ ] 回归：`git diff --check` - 无空白错误

### 约束

- [可衡量不变量] - 必须由上面的命令验证

### 完成状态

- 状态：in_progress / PASS / FAIL / DEVIATION / BLOCKED

## 风险

| 风险 | 缓解措施 |
| --- | --- |
| [具体风险] | [措施] |

## 决策记录

| 日期 | 决策或偏差 | 原因 | 影响章节 |
| --- | --- | --- | --- |

## Codex QA Review

- 状态：pending / completed / waived / blocked
- 报告和处理：[报告原文、采纳项或不采纳原因]

## Codex Final Audit

- 状态：pending / completed / waived / blocked
- 结论：pending / approved / needs revision

## 状态归档

- 终态：completed / cancelled / abandoned
- 终止时间：`ISO-8601 timestamp`
- 终止原因：[具体原因]
- 归档命令：`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/phase-state.py" archive`
