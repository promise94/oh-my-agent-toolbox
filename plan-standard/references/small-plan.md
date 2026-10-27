# 小计划模板

适用于单阶段、少于 10 个文件且不涉及架构决策的任务。

```markdown
# [计划标题]

## 背景

[当前问题和期望结果]

## 需求或假设

- 已确认：[用户已经确认的决定]
- 假设：[采用的低风险默认值]

## 范围

- 包含：[本次处理内容]
- 不包含：[明确排除的内容]

## 设计

[选定方案、复用点和相关取舍]

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

## 风险

| 风险 | 缓解措施 |
| --- | --- |
| [具体风险] | [对应措施] |

## 决策记录

| 日期 | 决策或偏差 | 原因 | 影响章节 |
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
