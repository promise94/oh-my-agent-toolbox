# 宿主兼容说明

本 Skill 是 Claude/Codex 的兼容 wrapper，保留 `/codex:setup`、`/codex:rescue` 和 `$CLAUDE_PROJECT_DIR` 等 Claude/Codex 专用调用约定，以保持现有调用入口兼容。

通用审计任务见同一 plugin 的 `planning-workflow` references；OpenCode 或其他宿主应调用 provider-neutral audit 流程，不应直接执行本 wrapper 中的宿主命令。
