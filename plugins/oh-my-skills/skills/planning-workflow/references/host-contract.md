# 宿主契约

本文件把 `planning-workflow` 用到的宿主能力集中映射到具体实现。SKILL.md 正文只使用能力编号（C1–C5），不写任何宿主的工具名或路径变量。

这是刻意的：Agent Skills 是开放标准，装载层通用；但正文里出现 `AskUserQuestion`、`ExitPlanMode`、`$CLAUDE_PROJECT_DIR` 这类符号时，换宿主就会静默失效——不报错，只是把状态写到没人读的地方。

## 1. 变量解析

会话开始时解析一次，之后全部复用。

| 名称 | 解析顺序 |
|---|---|
| `project_root` | `$PLAN_PROJECT_DIR` → `$CLAUDE_PROJECT_DIR` → 当前工作目录 |
| `state_dir` | `$PLAN_STATE_DIR` → `.claude` |
| `state_file` | `$project_root/$state_dir/phase_state.json` |
| `PR` | 本 skill 所在 plugin 根目录（skill 目录向上两级） |

`state_dir` 默认为 `.claude` 是为了兼容既有项目；在非 Claude 宿主上建议设为 `.plans` 之类的中性目录，避免和宿主的私有目录混放。

## 2. 能力矩阵

| 编号 | 语义 | Claude Code | 通用实现 | 缺失时降级 |
|---|---|---|---|---|
| C1 | 结构化提问 | `AskUserQuestion` | 一次一条、带选项的普通文本提问 | 同通用实现 |
| C2 | 进入/退出计划模式 | `EnterPlanMode` / `ExitPlanMode` | 无标准；在对话中显式声明"以下为计划，确认后开始实施" | 不切换模式，改为文本确认 |
| C3 | 回复结束时的强制门禁 | `settings.json` 的 `hooks.Stop` | 无跨宿主标准 | 每阶段结束必须手工执行 `phase-state.py validate` 并贴出输出 |
| C4 | 状态目录 | `.claude/` | `PLAN_STATE_DIR` | 默认 `.claude` |
| C5 | 独立评审通道 | `$codex:rescue`（需 Codex 插件） | 新起一个无上下文的子 agent，读 `references/review-subagent-prompt.md` | 取得用户明确同意后记 `waived` |

**不要发明能力。** 宿主没有的工具不要假装调用，也不要用相近名字替代——按上表选一个已实现的降级路径，并在输出里说明走的是哪一条。

## 3. 各宿主安装位置

Agent Skills 标准的装载层是通用的，各宿主只是目录不同。把 `planning-workflow/` 整个目录放到对应位置即可，文件内容不需要改。

| 宿主 | 项目级 | 用户级 | 备注 |
|---|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | 另有 plugin marketplace 分发方式 |
| WorkBuddy | `.workbuddy/skills/` | `~/.workbuddy/skills/` | 支持 `SKILL.md` + frontmatter |
| Codex CLI | `.agents/skills/` | `~/.agents/skills/` | 亦有 `.codex/skills/` 的说法，以当前文档为准 |
| Cursor | `.cursor/skills/`、`.agents/skills/` | `~/.cursor/skills/` | 兼容读 `.claude/skills/` |
| openCode | `.opencode/skills/` | 依版本而定 | 目录名以当前文档为准 |

目录名会变，`SKILL.md` 格式不变。如果宿主能读 `.claude/skills/`，直接用现有位置即可。

## 4. 门禁安装（仅 C3 可用的宿主）

Claude Code：

```bash
python3 "$PR/scripts/bootstrap.py" --root "$project_root" --with-rules
```

这会安装 `$state_dir/hooks/phase-gate.sh`、向 `settings.local.json` 幂等合并 `hooks.Stop`，并在 `CLAUDE.md` 写入带标记的约束块。

其他宿主跳过此步，改用第 5 节的手工模式。

## 5. 手工门禁模式（无 C3 时）

没有 Stop hook，就没有机械强制力。必须用可核查的替代：

1. 每个 Phase 的文件改动完成后，立即运行：
   ```bash
   python3 "$PR/scripts/phase-state.py" validate --root "$project_root"
   ```
2. 把完整输出贴进对话，再逐条对照该 Phase 的 Acceptance Criteria。
3. 全部 PASS 后写入 `phase_status=PASS`，才允许开始下一个 Phase。

**必须在第一次进入执行阶段时明确告知用户当前处于手工门禁模式。** 不要暗示有强制门禁。

## 6. 评审与审计通道

`C5` 的三级链见 SKILL.md 第 6 节。请求文件由脚本生成，脚本会自动引用提示词模板：

```bash
python3 "$PR/scripts/prepare-review.py" --root "$project_root" \
  --plan "<abs-plan>" --request "$state_dir/temp/review-request.md" \
  --context "$state_dir/temp/review-context.md"

python3 "$PR/scripts/prepare-audit.py" --root "$project_root" \
  --plan "<abs-plan>" --request "$state_dir/temp/audit-request.md" \
  --summary "$state_dir/temp/audit-summary.md"
```

子 agent 路径不需要 request 文件，直接把 `references/review-subagent-prompt.md`（或 audit 对应文件）连同计划路径交给它即可。
