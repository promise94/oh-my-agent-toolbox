# Changelog

本文件记录公开 marketplace/plugin 的用户可见变更。

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
