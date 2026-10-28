---
name: plan-standard
description: 为复杂或可恢复的实施工作创建、评审、执行和审计持久化计划，并在 Claude 中通过 Codex plugin 进行独立 review 与 audit。
metadata:
  short-description: Claude/Codex 可恢复实施计划
---

# 标准计划流程

本 skill 面向需要持久化决策、分阶段执行或跨会话恢复的工作。计划是持续更新的执行记录；实施、验证、Codex review 和最终 audit 必须始终与同一份计划对账。

## 输出语言

- 计划正文、章节标题、评审报告和审计报告默认使用中文。
- 用户或项目明确要求其他语言时，遵循其要求。
- 命令、路径、代码标识符、JSON 字段和状态枚举保持英文。

## 判断是否需要计划

- 无计划：只读排查、文案、格式或低风险明显修复。
- 小计划：单阶段、少于 10 个文件、没有架构决策，但需要持久化协调或恢复记录。
- 大计划：多阶段或多模块、架构决策、跨仓库、公共契约、迁移、依赖体系、部署发布、安全敏感或难以回滚的变更。
- 用户明确要求计划、评审、审计或恢复已有计划时必须使用本 skill。

## Claude 初始化

在首次开始计划执行前，在仓库根目录运行 bootstrap：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py"
```

bootstrap 会将本 skill 的 `phase-gate.sh` 安装到 `$CLAUDE_PROJECT_DIR/.claude/hooks/phase-gate.sh`，设置执行权限，并将以下 `hooks.Stop` 项幂等合并到优先选择的可写 settings 文件：

```json
{
  "matcher": "",
  "hooks": [{
    "type": "command",
    "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/phase-gate.sh"
  }]
}
```

已有配置和 Stop hook 不覆盖、不重复添加。settings JSON 非法、结构冲突或 hook 安装失败时记录为 `BLOCKED`，不要假装门禁已启用。

## 开始、恢复与路径

- 当前工作树唯一活动计划指针：`$CLAUDE_PROJECT_DIR/.claude/phase_state.json`。
- 计划存入已有的 `plans/<slug>.md`，否则存入 `.claude/plans/<slug>.md`。
- 历史终态存入 `.claude/plan-history/<plan_id>.json`。
- 若状态指向 `planning` 或 `execution`，读取原计划并从当前阶段恢复，不新建替代计划。
- 若状态为 `completed`、`cancelled` 或 `abandoned`，先运行 `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/phase-state.py" archive`，再开始新计划。
- 同一工作树同一时刻只允许一个活动计划；并行工作使用独立 worktree。

每份计划必须包含“背景”“需求或假设”“范围”“设计”“阶段”“风险”和“决策记录”。每阶段必须有文件级变更、可运行验收标准、可衡量约束和完成状态，禁止 `TBD`、`TODO` 或“验证是否正常”等不可执行描述。

## 状态约定

规划状态：

```json
{
  "plan_id": "kebab-case-slug",
  "plan_path": "/absolute/path/to/plan.md",
  "workflow_stage": "planning",
  "codex_review_status": "pending",
  "codex_review_note": "",
  "updated_at": "ISO-8601 timestamp"
}
```

执行状态：

```json
{
  "plan_id": "kebab-case-slug",
  "plan_path": "/absolute/path/to/plan.md",
  "workflow_stage": "execution",
  "current_phase": 1,
  "phase_name": "实施阶段",
  "phase_status": "in_progress",
  "codex_review_status": "completed",
  "codex_review_note": "",
  "audit_status": "pending",
  "updated_at": "ISO-8601 timestamp"
}
```

`codex_review_status` 和 `audit_status` 可为 `pending`、`needs_input`、`blocked`、`waived` 或 `completed`。阶段状态为 `in_progress`、`PASS`、`FAIL`、`DEVIATION` 或 `BLOCKED`。终态为 `completed`、`cancelled` 或 `abandoned`，并必须有 `terminal_at` 和 `terminal_reason`；`completed` 还必须满足 `phase_status=PASS` 且 `audit_status=completed|waived`。

## 执行流程

1. 澄清会实质影响范围、验收、约束、依赖或方案的歧义；无法澄清的内容记录为假设。
2. 检查仓库、项目规则和当前工作树，编写并自审计划。
3. 创建 planning state，然后调用 `$codex-plan-review`；该 skill 负责询问本计划的 review/waiver、执行 `/codex:setup`、生成上下文并通过 `/codex:rescue --fresh --wait` 调用 Codex。
4. 将 Codex 报告完整展示给用户；发现需要决策时设为 `needs_input`，更新同一计划后再继续。每项发现都要采纳，或记录明确的不采纳原因。完成处理后设为 `completed`。
5. 用户批准后，在调用 `ExitPlanMode` 前写入 execution state，阶段从 `in_progress` 开始。
6. 每次只实施当前阶段，检查 diff，逐条运行该阶段全部验收命令和约束；通过后将阶段标记为 `PASS` 并进入下一阶段。失败修正后重跑；偏差先更新同一计划的决策记录。
7. 全部阶段通过后调用 `$codex-plan-audit`；该 skill 负责询问 audit/waiver、执行 `/codex:setup`、生成实施摘要并通过 `/codex:rescue --fresh --wait` 调用 Codex。
8. 展示 Codex audit 并处理所有发现；将 `audit_status` 设为 `completed` 或经用户明确同意设为 `waived`，再写入终态并归档。

## Codex review/audit 约定

本 skill 不实现 Codex plugin。需要官方 `codex@openai-codex` plugin 和 `/codex:setup`、`/codex:rescue` skill。review/audit 默认不传入 `--model`、`--effort`、provider、API key 或其他 runtime 覆盖参数，必须保持 Codex/用户现有的 model 和 provider 配置。若 plugin 缺失、未认证、权限失败或 companion runtime 失败：

- 将对应状态设为 `blocked` 并保存简短原因；
- 向用户提供安装提示或失败输出；
- 询问仅针对当前计划的 waiver；
- 未获得明确 waiver 前不得批准计划或宣布完成。

review 使用 `${CLAUDE_PLUGIN_ROOT}/skills/plan-standard/references/review-subagent-prompt.md`，audit 使用 `${CLAUDE_PLUGIN_ROOT}/skills/plan-standard/references/audit-subagent-prompt.md`。Claude 先在本地运行计划中的验收命令，再运行对应 skill 提供的准备脚本，将不含 shell 命令原文、`-m` 参数或命令名 token 的结果摘要写入 `.claude/temp/`。准备脚本必须将 request/context/summary 写入仓库 `.claude/temp/`，并在 request 中标记当前 request 是唯一输入。随后只向 `/codex:rescue` 发送包含该 request 绝对路径的短单行读取请求；不得让 Codex 扫描临时目录猜测文件，也不得把长篇 Markdown 直接拼接到 rescue 参数中。Codex 可以读取文件、查看现有 diff/status 和审计摘要，但不得修改、删除或创建文件，不得安装依赖、提交或发布，也不需要运行测试；如果某项信息无法读取，报告“未读取”，不要发送空命令。Codex 任务必须有超时和状态轮询：`running`、`failed`、`cancelled` 或空输出只能标记为 `blocked`，不得视为 audit 通过。报告完成后清理临时文件；waiver 时保留阻塞证据并记录清理结果。不得向 Codex 传递主 agent 的预期结论。

`phase-gate.py` 是严格校验器，返回非零表示当前状态不允许继续；`.claude/hooks/phase-gate.sh` 是 Stop hook 提示器，只报告状态，不修改计划或自动推进阶段。

## 阶段门禁与归档

在仓库根目录运行：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/phase-gate.py"
```

Claude Stop hook 会自动提示未完成的 review、phase gate 或 audit，但不替代计划中的验收命令。终态计划归档：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/phase-state.py" archive
```

归档成功后 `.claude/phase_state.json` 必须不存在，历史状态保留在 `.claude/plan-history/`，且不得覆盖已有历史。
