---
name: codex-plan-review
description: 使用 Codex 独立评审当前 plan-standard 计划，并将报告和 disposition 写回同一计划。
argument-hint: [plan-file-path]
allowed-tools: Bash, Read, Write, Glob, Grep, AskUserQuestion, Skill
---

# Codex 计划评审

在用户批准实施前，对同一份计划执行一次独立 Codex review。

## 流程

1. 读取 `$CLAUDE_PROJECT_DIR/.claude/phase_state.json`，或验证用户提供的绝对计划路径；不从最近文件猜测计划。
2. 检查 Codex plugin 和 `/codex:rescue` 是否可用；不可用时将 `codex_review_status=blocked`、写入 `codex_review_note`，并询问用户是否仅为当前计划 waiver。
3. 执行 `/codex:setup` 一次。setup 失败时保留输出、写入 blocked 状态并停止；不得伪造 review 结果。
4. 运行 `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/prepare-review.py"`，由脚本创建 `.claude/temp/codex-review-request-{plan_id}.md` 和 `.claude/temp/codex-plan-context-{plan_id}.md`。脚本只生成审计输入，不写入计划状态。
5. 通过 `/codex:rescue --fresh --wait` 只发送包含当前 request 绝对路径的短单行 prompt，例如：`Read exactly /repo/.claude/temp/codex-review-request-<plan_id>.md and perform the requested read-only review.` Codex 必须读取该文件，不得扫描 `.claude/temp/` 猜测 request。具体路径由准备脚本生成并写入 request 文件；不得把长篇 Markdown、shell 命令、`-m` 参数或命令名 token 拼接到 rescue 参数中。Codex 可以读取文件和现有 diff/status，但不得修改、删除或创建文件，不得安装依赖、提交或发布，也不执行验收命令。不要传入 `--model`、`--effort`、provider、API key 或其他 runtime 覆盖参数。
6. 将 Codex 报告完整展示给用户。若有需要决策的发现，先设 `codex_review_status=needs_input`，通过 `AskUserQuestion` 确认并更新同一计划。
7. 运行 `/codex:status <job-id>` 获取最终状态；只有 `completed` 且包含完整报告时才继续。`running`、`failed`、`cancelled` 或空输出只能标记为 `blocked`，不得视为 review 通过。
8. 将报告、采纳项和不采纳原因追加到同一计划，成功处理后设 `codex_review_status=completed`；用户明确跳过时只能设 `waived` 并记录原因。
9. 清理临时上下文文件。权限、runtime、Codex 失败或写回失败都必须保留 blocked 状态并停止。

## 安装提示

官方 plugin 缺失时提示：

```text
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/reload-plugins
```
