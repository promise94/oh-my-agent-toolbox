---
name: codex-plan-audit
description: 使用 Codex 独立审计已完成计划的实现，并将报告和 disposition 写回同一计划。
argument-hint: [plan-file-path]
allowed-tools: Bash, Read, Write, Glob, Grep, AskUserQuestion, Skill
---

# Codex 实施审计

全部阶段通过后，对实际工作树执行一次独立 Codex audit。

## 流程

1. 读取 `$CLAUDE_PROJECT_DIR/.claude/phase_state.json`，或验证用户提供的绝对计划路径；不从最近文件猜测计划。
2. 确认计划中的所有阶段已通过；未通过时停止，不开始 audit。
3. 询问用户选择 audit 或仅为当前计划 waiver。waiver 必须写入同一计划和状态。
4. 执行 `/codex:setup` 一次。setup 失败时将 `audit_status=blocked`、写入原因并停止。
5. 运行准备脚本生成审计输入。脚本三个必填参数加三个可选参数，`--root` 必须是仓库根目录，`--request` 和 `--summary` 必须落在 `.claude/temp/` 内，`--baseline` 和 `--validation` 必须落在仓库内：

    ```bash
    PLAN_ID="$(basename "$PLAN_PATH" .md)"
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/prepare-audit.py" \
      --root "$CLAUDE_PROJECT_DIR" \
      --plan "$PLAN_PATH" \
      --request "$CLAUDE_PROJECT_DIR/.claude/temp/codex-audit-request-${PLAN_ID}.md" \
      --summary "$CLAUDE_PROJECT_DIR/.claude/temp/codex-plan-impl-${PLAN_ID}.md" \
      --validation "$CLAUDE_PROJECT_DIR/.claude/temp/local-validation-summary.txt" \
      --timeout-seconds 900
    ```

    `--baseline` 可选，用于传入实施前的工作树快照；省略时摘要标记为「未提供」。`--timeout-seconds` 只作为 Codex 任务预算写进摘要，不强制中止。脚本创建 `.claude/temp/codex-plan-impl-{plan_id}.md` 和 `.claude/temp/codex-audit-request-{plan_id}.md`，生成不含验收命令原文的逐阶段工作树对账表；所有输入校验在写文件之前完成，校验失败不会留下半成品。脚本只写入审计输入文件，不写入计划状态。脚本非零退出时保留原始输出、写入 blocked 状态并停止。

6. 通过 `/codex:rescue --fresh --wait` 只发送包含当前 request 绝对路径的短单行 prompt，例如：`Read exactly /repo/.claude/temp/codex-audit-request-<plan_id>.md and perform the requested read-only audit.` Codex 必须读取该文件，不得扫描 `.claude/temp/` 猜测 request。具体路径由准备脚本生成并写入 request 文件；不得把长篇 Markdown 直接拼接到 rescue 参数中。Codex 可以读取文件、查看现有 diff/status 和审计摘要，但不得修改、删除或创建文件，不得安装依赖、提交或发布，也不需要运行测试；本地验证由 Claude 在调用前完成并写入摘要。如果某项信息无法读取，报告“未读取”，不要发送空命令。不要传入 `--model`、`--effort`、provider、API key 或其他 runtime 覆盖参数；模型和 provider 必须保持 Codex/用户现有配置。
7. 将完整报告展示给用户。若任务在配置的超时窗口内没有结果，先通过 `/codex:status <job-id>` 获取最终状态；只有 `completed` 且包含完整报告时才继续。`running`、`failed`、`cancelled` 或空输出均记录为 `blocked`，不得视为 audit 通过。
8. 将报告和 disposition 追加到同一计划，确认结果后设 `audit_status=completed`；明确 waiver 时设 `audit_status=waived`。
9. 只有 `phase_status=PASS` 且 `audit_status=completed|waived` 时，才将计划设为 `completed` 并运行：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/phase-state.py" archive
```

10. 清理临时实施摘要。权限、runtime、Codex 失败或写回失败都必须保留 blocked 状态并停止。
