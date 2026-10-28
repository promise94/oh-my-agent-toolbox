# Changelog

本文件记录公开 marketplace/plugin 的用户可见变更。

## [0.2.0] - 2026-10-28

### Fixed

- `prepare-review.py` 的 request 模板不再内联 `${CLAUDE_PLUGIN_ROOT}`：该占位符与 `str.format` 冲突会抛 `KeyError`，且 Codex 侧无法解析这个运行时变量；改为按脚本位置解析评审格式文档路径。
- `prepare-audit.py` 在写文件前完成全部输入校验，校验失败不再留下半成品 request。
- `prepare-audit.py` 输出逐阶段工作树对账表（计划文件、存在、工作树状态、最近提交），替代只有 `git diff --stat` 的摘要；`git` 执行失败与「无输出」不再折叠成同一个「未读取」。
- audit request 不再硬编码 `plugins/oh-my-skills/`、`.claude-plugin/` 等本仓库路径。
- `phase-state.py` 允许同一 `plan_id` 重复归档，写入 `<plan_id>-2.json` 等序号，不覆盖已有历史。
- 测试修复：`test_phase_state.py` 隔离 `CLAUDE_PROJECT_DIR`，避免在 agent 会话内读到真实仓库状态；三份测试文件中丢失的方法定义已补回。

### Changed

- `cancelled` / `abandoned` 计划只要求 `terminal_at` 和 `terminal_reason`，不再强制 `codex_review_status` 和 `audit_status` 已处置。兼容性影响：此前这类计划必须伪造 `waived` 才能归档，现在不需要。
- 兼容性影响：plugin 不再随包注册 Stop hook（移除 `hooks/hooks.json`）。阶段门禁只通过 `bootstrap.py` 安装到目标项目后生效；此前未 bootstrap 的项目也会收到 plugin hook 提示，升级后不会。
- review/audit 的任务清单与输出格式以 `skills/plan-standard/references/*-subagent-prompt.md` 为唯一来源，request 文件只承载输入路径和只读边界，避免两份清单漂移。
- `prepare-review.py` 不再覆盖已存在的 context 文件，仅在缺失或为空时写入兜底说明，主 agent 可以先写需求摘要。
- `phase-gate.py` 合并重复的状态枚举；`SKILL.md` 明确退出码语义（`0` 继续、`1` 未满足、`2` 非法或缺失）。
- 新增 `.github/workflows/tests.yml` 和 `tests/test_doc_contracts.py`，校验 `SKILL.md` 写出的命令与脚本真实 CLI 一致。

## [0.1.0] - 2026-10-28

### Added

- 初始 Claude marketplace 和 plugin 结构。
- `plan-standard`：可恢复的分阶段计划、状态门禁和归档流程。
- `codex-plan-review`：Codex 独立计划 review 流程。
- `codex-plan-audit`：Codex 独立实施 audit 流程。
- 项目级 Stop hook bootstrap 和阶段状态脚本。
- MCP 和 Claude settings 的 opt-in 安全模板。
- marketplace/plugin manifest、插件布局测试和配置安全校验。

### Changed

- 公开 marketplace 和 plugin 名称统一为 `oh-my-agent-toolbox`。
- 保留内部目录 `plugins/oh-my-skills` 作为 marketplace source，避免破坏现有路径契约。

## 版本约定

- 修改 skill、hook、agent、MCP 模板或配置契约时，递增 plugin 的 SemVer 版本。
- 修改 marketplace 索引、plugin source 或 marketplace 元数据时，递增 marketplace metadata 版本。
- 影响现有调用方式或配置契约的变更应在对应版本条目中说明兼容性影响。
- 本文件只记录仓库中已完成的变更，不代表已经执行 Git tag、push 或其他远端发布操作。
