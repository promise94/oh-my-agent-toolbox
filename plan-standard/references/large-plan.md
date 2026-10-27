# 大计划模板

适用于多阶段、多模块、架构决策、迁移或存在发布风险的任务。

```markdown
# [计划标题]

## 背景

[当前状态、问题和期望结果]

## 需求

| # | 问题或需求 | 已确认答案或假设 | 形成的约束 |
| --- | --- | --- | --- |
| 1 | [问题或需求] | [用户确认，或明确假设] | [对实现的约束] |

## 范围

- 包含：[本次处理内容]
- 不包含：[明确排除的内容及原因]

## 设计

[选定方案、数据流、复用点、被否决的替代方案及取舍]

## 阶段 1：[阶段名称]

### 变更

| 操作 | 文件 | 具体修改 |
| --- | --- | --- |
| 新增/修改/删除 | `path/to/file` | [明确的文件级修改] |

### 验收标准

- [ ] `command` - [预期结果]
- [ ] 回归：`command` - [预期结果]

### 约束

- [可衡量的不变量] - 对应 `[command]`

### 完成状态

- 状态：in_progress / PASS / FAIL / DEVIATION / BLOCKED

## 阶段 2：[阶段名称]

### 变更

| 操作 | 文件 | 具体修改 |
| --- | --- | --- |
| 新增/修改/删除 | `path/to/file` | [明确的文件级修改] |

### 验收标准

- [ ] `command` - [预期结果]
- [ ] 回归：`command` - [预期结果]

### 约束

- [可衡量的不变量] - 对应 `[command]`

### 完成状态

- 状态：in_progress / PASS / FAIL / DEVIATION / BLOCKED

## 风险

| 风险 | 缓解措施 |
| --- | --- |
| [具体风险] | [对应措施] |

## 决策记录

| 日期 | 决策 | 原因 | 影响章节 |
| --- | --- | --- | --- |

## 评审处理

- Codex 计划评审：pending / completed / waived
- 发现处理：[已合入，或记录明确的不采纳原因]

## 最终审计

- Codex 计划审计：pending / completed / waived
- 结论：pending / approved / needs revision

## 状态归档

- 终态：completed / cancelled / abandoned
- 终止时间：`ISO-8601 timestamp`
- 终止原因：[完成、取消或放弃的具体原因]
- 归档命令：`python3 ~/.codex/skills/plan-standard/scripts/phase-state.py archive`
```
