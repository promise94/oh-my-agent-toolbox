# 计划流程硬约束

本文件由 `oh-my-agent-toolbox` 维护，作用于使用 `plan-standard`、`codex-plan-review`、`codex-plan-audit` 的项目。冲突时以本文件为准。

1. **状态只经脚本写入**：`phase-state.py start|set|validate|archive`。禁止手改 `.claude/phase_state.json`，脚本会拒绝非法字段和非法状态转移。
2. **不得伪造 review/audit**：没有真实 Codex 报告时只能记 `blocked`；只有用户明确同意跳过，才能记 `waived`；`completed` 必须在报告已完整展示给用户之后才写。
3. **阶段未 PASS 不得前进**：`completed` 必须同时满足 `phase_status=PASS` 和 `audit_status=completed|waived`。
4. **不要为归档伪造处置**：`cancelled` / `abandoned` 只需要 `terminal_at` 和 `terminal_reason`，不需要也不允许补 review/audit。
5. **一个工作树只有一个活动计划**：开始新计划前，先 `archive` 已处于终态的计划。
6. **计划必须可执行**：验收标准是可运行命令，约束可衡量；禁止 `TBD`、`TODO`、"验证是否正常"。
7. **不越界**：不修改用户全局配置，不提交凭证，不把本机绝对路径写入配置或计划。
