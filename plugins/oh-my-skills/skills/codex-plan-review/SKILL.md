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
4. 运行准备脚本生成 review 输入。运行前先自己写需求摘要：把 5-8 句需求上下文写入 `--context` 指定的文件，覆盖目标、约束、Phase 0 已定决策、假设和范围外事项；不要写入主 agent 的预期结论或疑似发现。脚本不会覆盖已存在的 context，只在文件缺失或为空时写入兜底说明。

   脚本四个参数全部必填，`--root` 必须是仓库根目录，`--request` 和 `--context` 必须落在 `.claude/temp/` 内（越界会被拒绝）：

    ```bash
    PLAN_ID="$(basename "$PLAN_PATH" .md)"
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/prepare-review.py" \
      --root "$CLAUDE_PROJECT_DIR" \
      --plan "$PLAN_PATH" \
      --request "$CLAUDE_PROJECT_DIR/.claude/temp/codex-review-request-${PLAN_ID}.md" \
      --context "$CLAUDE_PROJECT_DIR/.claude/temp/codex-plan-context-${PLAN_ID}.md"
    ```

    脚本创建 `.claude/temp/codex-review-request-{plan_id}.md` 和 `.claude/temp/codex-plan-context-{plan_id}.md`。context 文件若已存在则保持内容不变，仅在缺失时写入兜底说明，因此先写入需求摘要再运行脚本。脚本只生成 review 输入，不写入计划状态。脚本非零退出时保留原始输出、写入 blocked 状态并停止。

5. 委托 Codex 执行 review，必须**前台**调用。prompt 只允许这一句模板，路径替换为实际路径：

    ```text
    Read exactly <request 绝对路径> and perform the requested read-only review.
    ```

    规则：

    - 只发送上面这一句。不得拼接插件或宿主的操作说明（如「Use one Bash call…」「Do not inspect files yourself…」），不得拼接长篇 Markdown、shell 命令、`-m` 参数或命令名 token。
    - 不得让该 Bash 调用进入后台：不加 `--background`，不使用后台执行方式。后台队列路径可能丢失 message，表现为 Codex 侧 `message must not be empty`。
    - `/codex:rescue` 的参数与 companion `task` 的参数不是一回事；`task` 只支持 `--background` / `--write` / `--resume-last|--resume|--fresh` / `--model` / `--effort`，**没有 `--wait`**。不确定时不要透传任何额外参数。
    - 前台调用可直接用 companion：`node <codex plugin>/scripts/codex-companion.mjs task '<上面的单句>'`；如果宿主仍把命令转入后台或 message 被吞，改用 `--prompt-file` 兜底：先把单句写入 `.claude/temp/codex-prompt-{plan_id}.txt`，再 `task --prompt-file <.claude/temp 下的相对路径>`。
    - 不要传入 `--model`、`--effort`、provider、API key 或其他 runtime 覆盖参数。

    Codex 可以读取文件和现有 diff/status，但不得修改、删除或创建文件，不得安装依赖、提交或发布，也不执行验收命令。
6. 判定结果。前台调用没有 job id，直接看返回内容：只有拿到完整报告才继续；出现 `message must not be empty`、`sandbox_apply`、其他 runtime 错误或空输出，一律记 `blocked` 并附原始输出，不得视为 review 通过。只有确实走了后台队列时才用 `/codex:status <job-id>` 查：`running`、`failed`、`cancelled` 或空输出同样只能记 `blocked`。
7. 将 Codex 报告完整展示给用户。若有需要决策的发现，先设 `codex_review_status=needs_input`，通过 `AskUserQuestion` 确认并更新同一计划。
8. 将报告、采纳项和不采纳原因追加到同一计划，成功处理后设 `codex_review_status=completed`；用户明确跳过时只能设 `waived` 并记录原因。
9. 清理临时上下文文件和 `--prompt-file` 兜底文件。权限、runtime、Codex 失败或写回失败都必须保留 blocked 状态并停止。

## 安装提示

官方 plugin 缺失时提示：

```text
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/reload-plugins
```
