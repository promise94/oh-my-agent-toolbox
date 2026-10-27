---
name: plan-standard
description: 为需要方案决策、跨模块协调、多阶段或跨会话执行、迁移及高风险验证的工作创建、评审、执行和审计持久化计划。用户明确要求计划、计划评审、最终审计或恢复已有计划时也使用。不要仅因修改代码行为就用于只读任务、简单编辑或低风险明显修复。
metadata:
  short-description: 可恢复的 Codex 实施计划
---

# 标准计划流程

当实施工作需要持久化决策、分阶段执行或跨会话恢复时使用本 skill。计划是持续更新的执行记录，实施和验证必须始终与同一份计划对账。

## 输出语言

- 计划正文、章节标题、评审报告和审计报告默认使用中文。
- 用户或项目明确要求其他语言时，遵循其要求。
- 命令、路径、代码标识符、JSON 字段和状态枚举保持英文，不做翻译。

## 判断是否需要计划

文件数量只是参考，决策复杂度和风险优先。

- 无计划：只读排查或审查；文案、注释、格式、配置等简单修改；通常不超过两个文件、局限于一个模块、没有方案选择的低风险明显修复。直接执行并做适度验证。
- 小计划：单阶段、少于 10 个文件、没有架构决策，但持久化协调或恢复记录有明确价值。读取 [references/small-plan.md](references/small-plan.md)。
- 大计划：涉及多个阶段或模块、架构决策、跨仓库工作、公共契约、数据或 schema 迁移、依赖体系、部署发布、安全敏感操作、破坏性操作或难以回滚的变更。读取 [references/large-plan.md](references/large-plan.md)。

用户明确要求计划或继续已有计划时必须使用。不要仅因代码行为发生变化就启用计划。直接执行的任务若范围或风险扩大，应先说明原因，再切换到计划流程。

以下情况必须使用本 Skill 或适用的高风险计划流程：

- 认证、授权、权限扩大或安全设置；
- 资金、支付、费用或其他财务影响；
- 数据删除、数据迁移、批量覆盖或难以恢复的操作；
- 部署、发布、外部写入或公共契约变更；
- 跨模块、跨仓库、依赖体系变更或需要跨会话恢复；
- 用户明确要求方案、计划、分阶段执行、独立 review 或最终 audit。

## 写计划前澄清

在起草前处理会实质影响范围、验收定义、量化约束、依赖、方案选择或现状判断的歧义。集中提出相关问题，并给出低风险默认建议。用户要求直接推进时，把未解决事项记录为明确假设。

## 开始、恢复与切换

只有任务被判断为小计划或大计划后，才在修改实现文件前执行：

1. 检查 `.codex/phase_state.json`。它是当前工作树唯一的活动计划指针，不是计划历史总表。
2. 如果它指向 `planning` 或 `execution` 计划，读取原计划并从 `current_phase` 和 `phase_status` 恢复，不要新建替代计划。
3. 如果它指向 `completed`、`cancelled` 或 `abandoned` 计划，先运行 `python3 ~/.codex/skills/plan-standard/scripts/phase-state.py archive`，将状态移到 `.codex/plan-history/<plan_id>.json`，再开始新计划。
4. 如果没有活动计划，先检查仓库，再编写计划并创建新的 `phase_state.json`。
5. 用户提供已有计划路径时，仅在必要时将其接入仓库的 `plans/` 或 `.codex/plans/`；除非用户明确要求，不修改来源文件。
6. 恢复会话时，说明计划路径、当前阶段、已完成阶段和下一步动作。

同一工作树同一时刻只允许一个活动计划。需要并行执行时，使用独立的 Git worktree；不要让多个会话共享同一个 `.codex/phase_state.json`。

每份计划必须包含“背景”“需求或假设”“范围”“设计”“阶段”“风险”和“决策记录”。每个阶段必须列出文件级变更、可运行的验收标准、可衡量的约束和完成状态。不得使用 `TBD`、`TODO` 或“验证是否正常”之类不可执行描述。

## 状态约定

已有 `plans/` 时将计划存入 `plans/<slug>.md`，否则存入 `.codex/plans/<slug>.md`。`plan_path` 必须是绝对路径，整个流程使用同一文件。

规划状态：

```json
{
  "plan_id": "kebab-case-slug",
  "plan_path": "/absolute/path/to/plan.md",
  "workflow_stage": "planning",
  "review_status": "pending",
  "review_note": "",
  "updated_at": "ISO-8601 timestamp"
}
```

`review_status` 可用值为 `pending`、`needs_input`、`blocked`、`waived`、`completed`。实施前取得用户批准，并写入执行状态：

```json
{
  "plan_id": "kebab-case-slug",
  "plan_path": "/absolute/path/to/plan.md",
  "workflow_stage": "execution",
  "current_phase": 1,
  "phase_name": "实施阶段",
  "phase_status": "in_progress",
  "audit_status": "pending",
  "updated_at": "ISO-8601 timestamp"
}
```

阶段门禁结束后，`phase_status` 只能使用 `PASS`、`FAIL`、`DEVIATION` 或 `BLOCKED`。执行期间，`audit_status` 使用 `pending`、`blocked`、`needs_input`、`waived` 或 `completed`。计划终止时，`workflow_stage` 使用 `completed`、`cancelled` 或 `abandoned`，并写入 `terminal_at` 和 `terminal_reason`；其中 `completed` 必须满足 `phase_status=PASS` 且 `audit_status=completed` 或 `waived`。

计划进入终态后，计划文档和终态状态必须保留用于审计，但不得继续占用活动指针。先更新终态，再运行 `python3 ~/.codex/skills/plan-standard/scripts/phase-state.py archive`；归档成功后，`.codex/phase_state.json` 应不存在。

## 执行约定

1. 阶段开始前写入 `workflow_stage: "execution"`、阶段编号和名称，并将 `phase_status` 设为 `in_progress`。
2. 只实施当前阶段，然后检查 diff。
3. 运行该阶段全部验收命令并检查每项约束。
4. 通过时，将计划中的验收项勾选并进入下一阶段。
5. 失败时修正实现并重新运行阶段门禁。
6. 出现偏差时，先更新“决策记录”和受影响的计划章节，再继续实施。
7. 需要用户输入、授权或外部依赖时，记录阻塞原因并停止。
8. 用户明确放弃或取消计划时，写入对应终态和原因，再运行 `phase-state.py archive`。
9. 最终阶段重新运行相关回归检查并检查完整 diff，再请求审计。

新事实改变范围或使设计失效时，必须先更新同一份计划，并在“决策记录”中说明原因。

## 独立评审与审计

本 skill 自己管理评审和审计，不依赖其他 skill。

- 两种模式都应先让用户选择独立检查或本次豁免。
- 每次评审或审计只使用一个 fresh subagent。主上下文只负责提供客观输入、展示报告和记录处理结果。
- 不向 subagent 传递主上下文的结论、预期问题、实现理由或期望裁决。
- subagent 不可用时，将对应状态设为 `blocked`，并询问用户是否豁免。

批准实施前，使用 [references/review-subagent-prompt.md](references/review-subagent-prompt.md) 进行评审。传入仓库根目录、计划路径以及适用的 `AGENTS.md` 或项目文档路径。不得改变报告实质内容。每项发现都要合入同一计划，或明确记录不采纳原因。只有展示并处理完报告后才能将 `review_status` 设为 `completed`；其他情况使用 `needs_input`、`blocked` 或 `waived`。

全部阶段通过后，使用 [references/audit-subagent-prompt.md](references/audit-subagent-prompt.md) 进行审计。传入仓库根目录、批准后的计划路径、当前分支、原始 `git status --short` 以及适用的 `AGENTS.md` 或项目文档路径。展示报告并在同一计划中记录处理结果后，才能将流程标记为 `completed`，且 `audit_status` 必须为 `completed` 或 `waived`。

## 阶段门禁工具

需要快速检查状态时，在仓库根目录运行：

```bash
python3 ~/.codex/skills/plan-standard/scripts/phase-gate.py
```

该脚本验证计划路径、报告当前阶段，并在规划未完成、当前阶段未通过或状态格式错误时返回非零状态。它不能替代计划中的验收命令。

归档已终止的活动计划：

```bash
python3 ~/.codex/skills/plan-standard/scripts/phase-state.py archive
```

该命令只接受 `completed`、`cancelled` 或 `abandoned` 状态，拒绝归档仍在执行中的计划，并在目标归档文件已存在时停止以避免覆盖历史。
