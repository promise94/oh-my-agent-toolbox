---
name: planning-workflow
description: |
  Plan structure and execution process for non-trivial implementation work.
  Use when: starting multi-phase work, entering plan mode, or user says /planning-workflow.
  Ensures plans are traceable, verifiable, and stay aligned with implementation.
  Portable across Agent Skills hosts; host-specific behavior is resolved through references/host-contract.md.
license: Apache-2.0
compatibility: 需要文件读写与 shell。结构化提问、计划模式、Stop hook 门禁、独立评审在缺失的宿主上按 references/host-contract.md 降级。
metadata:
  version: "2.0.0"
---

# Plan Standard

A plan is an executable contract, not a one-time design document. Once approved, it locks in expectations and is continuously reconciled during execution.

本文档不写任何宿主的专有工具名。所有需要宿主能力的地方用编号（C1–C5），具体映射见 [references/host-contract.md](./references/host-contract.md)。

## 0. 会话开始先解析契约

| 名称 | 取值 |
|---|---|
| `project_root` | `$PLAN_PROJECT_DIR`；未设置时按 host-contract 第 1 节解析 |
| `state_dir` | `$PLAN_STATE_DIR`；未设置时为 `.claude` |
| `state_file` | `$project_root/$state_dir/phase_state.json` |
| `PR` | 本 skill 所在 plugin 根目录（skill 目录向上两级） |

能力编号：

| 编号 | 语义 | 缺失时 |
|---|---|---|
| C1 | 结构化提问 | 文本提问，一次一条 |
| C2 | 计划模式 | 文本确认后实施 |
| C3 | 回复结束时的强制门禁 | 手工 `phase-state.py validate` |
| C4 | 状态目录 | 默认 `.claude` |
| C5 | 独立评审通道 | 子 agent，其次用户批准的 waiver |

宿主是否具备某项能力、缺了怎么降级、装在哪里，一律查 host-contract，不要凭宿主名字推断。

## 1. 选择计划规模

| 信号 | 类型 | 模板 |
|---|---|---|
| 单一阶段、改动 < 10 个文件、无架构决策 | Small | [small-plan.md](./small-plan.md) |
| 多阶段、多模块、架构决策、迁移或部署 | Large | [large-plan.md](./large-plan.md) |
| Bug 修复、单文件改动、用户已给出精确指令 | 不需要 | 直接做 |

## 2. 核心原则

1. **先澄清再动笔**——写计划前用 C1 消除模糊需求，可以多轮
2. **每个 Phase 都有验收标准**——可运行命令加预期输出，不是散文断言
3. **每个 Phase 都有约束**——行数、测试数、尺寸等可量化、可核查的上限
4. **阶段门禁必须执行**——阶段完成 = 跑验收标准 + 查约束，无例外
5. **门禁状态必须显式**——PASS / FAIL / DEVIATION / BLOCKED，不接受"基本完成"
6. **偏离先改计划**——代码与计划不一致时，先更新 Decision Log 和计划段落，再继续
7. **完成前必须终审**——重跑全部验收标准，输出偏离报告

## 3. Phase 0：需求澄清（C1）

写计划前扫描需求中的模糊点。能直接从需求或代码库确认的跳过。

| 类别 | 何时提问 |
|---|---|
| 范围边界 | 某个组件可能包含也可能不包含 |
| 验收定义 | 没有可度量目标时，"完成"是主观的 |
| 量化约束 | 性能、体积、覆盖率目标未给出 |
| 依赖关系 | 不清楚是阻塞别人还是被别人阻塞 |
| 模糊动词 | "优化/清理/改进"没有指标 |
| 现状 | 不确定哪些已完成、哪些坏了、哪些缺失 |

**提问方式**：每轮 2–4 个相关问题，给选项并说明推荐项，低风险项直接给默认值。

**停止条件**：每条需求都能映射到可验证结果，无主观验收项。用户说"直接开始"时，把未解决项写成计划里显式的 **Assumptions**，不要伪装成已确认。

## 4. 计划生命周期

计划写完并自审后，用脚本初始化状态。**状态只经脚本写入，禁止手改 `state_file`。**

```bash
# 开始：进入 planning
python3 "$PR/scripts/phase-state.py" start --root "$project_root" \
  --plan "<绝对计划路径>" [--plan-id "<kebab-case>"]

# 任何状态变更
python3 "$PR/scripts/phase-state.py" set --root "$project_root" \
  --field workflow_stage=execution --field current_phase=1 \
  --field phase_name="Phase 1 名称" --field phase_status=in_progress \
  --field audit_status=pending

# 随时可校验
python3 "$PR/scripts/phase-state.py" validate --root "$project_root"

# 全部完成后归档（不要手删文件）
python3 "$PR/scripts/phase-state.py" archive --root "$project_root"
```

字段约束：

- `plan_id` 区分并发计划（不同 worktree），由计划标题推导，kebab-case
- `plan_path` 必须是指向现存文件的绝对路径，后续 review、disposition、偏离登记都更新同一个文件
- `workflow_stage`：`planning` → `execution` → `completed` / `cancelled` / `abandoned`
- `codex_review_status` 是历史字段名，语义为**独立评审 disposition**：`pending` / `needs_input` / `blocked` / `waived` / `completed`
- `audit_status`：`pending` / `needs_input` / `blocked` / `waived` / `completed`
- `phase_status`：`in_progress` / `PASS` / `FAIL` / `DEVIATION` / `BLOCKED`
- 进入 execution 时字段必须齐备，缺 `audit_status` 或 `phase_name` 会被脚本拒绝
- 阶段门禁通过后更新 `phase_status`、`current_phase`、`phase_name`，并把 `phase_status` 重置为下一阶段的 `in_progress`
- 终态计划（`completed` / `cancelled` / `abandoned`）必须归档后才能开新计划

评审需要用户决策时，保持 `workflow_stage=planning` 并写 `codex_review_status=needs_input`；评审不可用时写 `blocked` 并记录原因。**不要伪造**。

## 5. 执行流程

```
[Phase 0 澄清：C1 循环]
  |
  v
[读现状：代码审计]
  |
  v
[写计划草稿 → 自审]
  |
  v
[写 planning 状态：codex_review_status=pending]
  |
  v
[独立评审 C5]
  |
  +---> NEEDS_INPUT -> C1 确认 -> 更新同一 plan_path -> pending
  |
  +---> BLOCKED ----> 保持 planning，记录原因，不得请求批准
  |
  v
[用户批准]
  |
  v
[写 execution 状态] -> [C2 退出计划模式]
  |
  v
[Phase N：TDD 开发]
  |
  v
[阶段门禁：跑验收标准 + 查约束]
  |
  +---> PASS --------> 写 phase_status=PASS，进入下一阶段
  +---> FAIL --------> 修代码，重跑门禁
  +---> DEVIATION ---> 更新 Decision Log 与计划，重跑门禁
  +---> BLOCKED -----> C1 确认，记入 Decision Log
  |
[全部阶段完成]
  |
  v
[终审 C5：重跑全部，输出报告] -> archive
```

## 6. 独立评审（C5）

计划批准前必须走评审，四级链按可用性选择，**从上到下，用第一个可用的**：

| 优先级 | 通道 | 状态记录 |
|---|---|---|
| 1 | 宿主的外部评审命令（Claude 上有 `$codex:rescue` 时优先使用） | 见下 |
| 2 | 无上下文的子 agent，加载 [references/review-subagent-prompt.md](./references/review-subagent-prompt.md) | 同上 |
| 3 | 主 agent 自审 + 明确告知用户"无独立评审" | `waived`（需用户明确同意） |
| 4 | 三者都不可用 | `blocked` |

执行规则：

- 走通道 1 时用 `prepare-review.py` 生成 request/context 文件，不要手工拼
- 通道 2 必须给全新上下文，不要向子 agent 预告预期结论
- 评审报告要完整展示给用户后，才能写 `codex_review_status=completed`
- 评审暴露的问题合并进**同一份**计划，不要新建计划文件
- 用户明确同意跳过才能写 `waived`，并记录原因
- 终审用同一套链路，提示词换成 [references/audit-subagent-prompt.md](./references/audit-subagent-prompt.md)，状态字段用 `audit_status`

## 7. 阶段门禁状态

每次门禁必须落到且只落到一个状态：

| 状态 | 含义 | 下一步 |
|---|---|---|
| **PASS** | 全部验收标准通过，全部约束成立 | 进入下一阶段 |
| **FAIL** | 有验收标准未通过 | 修代码，重跑门禁 |
| **DEVIATION** | 代码可用但与计划不一致 | 更新 Decision Log 与计划，重跑门禁 |
| **BLOCKED** | 缺少外部输入，无法继续 | C1 确认，记入 Decision Log |

## 8. 门禁强制模式（C3）

两种模式，实际使用哪一种必须让用户知道：

- **hook 模式**：宿主支持回复结束钩子，门禁自动回灌，缺失项会被提示阻断。安装方式见 host-contract 第 4 节。
- **手工模式**：宿主无此能力时，每个 Phase 结束必须执行 `phase-state.py validate` 并贴出完整输出，再开始下一阶段。

第一次进入执行阶段时说明当前模式。**不要在手工模式下暗示存在强制门禁。**

## 9. 自审（批准前）

1. **需求覆盖**：每条需求都映射到 Phase 与 Changes？
2. **验收覆盖**：每个 Phase 都有可运行命令？
3. **约束完整**：Design 里每个量化声明都有对应 Constraint？
4. **无占位符**：没有 TBD、TODO、"同上"？
5. **跨阶段一致**：Phase N 的类型与签名与 Phase N-1 对得上？
6. **澄清已记录**：Phase 0 的问答结论写进 Requirements/Assumptions？

## 10. 集成

- 计划编写：宿主计划模式（C2）
- 实施：每个阶段内用 TDD
- 提交前：`/simplify`（如可用）
- 阶段门禁：计划与代码之间的桥，尽早发现漂移
- 归档：`phase-state.py archive`，历史落在 `$state_dir/plan-history/`

## 11. Windows 兼容

门禁脚本用显式 `bash` 解释器调用，Windows 需安装 Git Bash。如果宿主通过 `cmd.exe` 派发命令而失败，在 `$state_dir/hooks/` 下建包装脚本：

```cmd
@bash "%~dp0phase-gate.sh" %*
```

再把设置里的钩子命令指向该 `.cmd`。
