# 大计划模板

适用于多阶段、多模块、架构决策、迁移、部署或其他高风险工作。

> **执行规则：** 每个阶段结束后运行全部 Acceptance Criteria 并检查 Constraints。任何偏差必须先更新同一计划的 Decision Log。计划评审和最终审计使用 Codex；不可用时只能由用户为本计划明确 waiver。

## 背景

[当前状态、问题、期望结果]

## 需求

| # | 问题或需求 | 已确认答案或假设 | 形成的约束 |
| --- | --- | --- | --- |
| 1 | [问题] | [答案或假设] | [约束] |

## 范围

- 包含：[本次处理内容]
- 不包含：[明确排除内容及原因]

## 设计

[架构决策、数据流、复用点、取舍和被否决方案。所有量化主张必须在阶段约束中有对应命令。]

## 阶段 1：[阶段名称]

### 变更

| 操作 | 文件 | 具体修改 |
| --- | --- | --- |
| 新增/修改/删除 | `path/to/file` | [文件级修改] |

### 验收标准

- [ ] `python3 -m unittest discover -s tests -v` - 相关测试全部通过
- [ ] 回归：`git diff --check` - 无空白错误

### 约束

- [可衡量不变量] - 对应 `[command]`

### 完成状态

- 状态：in_progress / PASS / FAIL / DEVIATION / BLOCKED

## 阶段 2：[阶段名称]

[重复阶段 1 的结构；阶段依赖必须明确。]

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
