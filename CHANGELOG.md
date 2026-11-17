# Changelog

## [1.0.1] - 2026-11-19

这是当前仓库的初始版本，记录已实现的公开功能。

### Skills

- `planning-workflow`：提供可恢复的分阶段计划、Phase 状态、验收门禁、归档流程和大小计划模板。
- `plan-review`：通过 Codex 独立评审计划，支持 request/context 输入、评审结果回传、阻塞和用户授权跳过。
- `plan-audit`：对已完成实施执行独立终审，按计划阶段、文件变更、验收标准和约束输出审计结果。
- `code-review`：面向 GitLab Merge Request 的资格检查、上下文发现、变更摘要、并行审查、问题评分和结果发布流程。

### 宿主适配与分发

- 提供 Claude Marketplace/plugin 结构、项目级 bootstrap、可选计划规则和 Stop hook 阶段门禁。
- 提供 OpenCode 的 canonical Skill 安装、plan/review/audit commands、只读 reviewer agent 和权限配置。
- 提供 ChatGPT/Codex portable plugin 导出、portable Skill 子集、manifest、marketplace 和 opt-in MCP 配置。
- 通过 Skill registry 维护 canonical Skill、版本、宿主支持范围、依赖和 portable 导出范围。

### 状态与脚本工具

- 提供 `phase-state.py` 的计划启动、状态更新、校验和归档命令，并通过统一状态模型和 Schema 校验状态转移。
- 提供 `phase-gate.py`、项目根目录和状态目录环境变量覆盖，以及 Claude hook 和非 Claude 宿主的手工门禁模式。
- 提供 `prepare-review.py` 和 `prepare-audit.py`，生成只读 request、上下文和逐阶段实施摘要。
- 提供 Skill、配置、JSON/JSONC、adapter 边界、导出确定性和文档契约校验脚本与测试。

### 安全与维护边界

- MCP 和 settings 仅提供 opt-in 模板，不自动连接服务、不携带真实凭证，也不覆盖用户配置。
- 发布产物排除项目运行时状态、计划临时文件、凭证、个人路径和非 canonical 的宿主运行文件。
- 提供安装、更新、卸载、bootstrap、故障排查、Skill 维护和发布检查文档。

## 版本约定

- 修改 Skill、hook、agent、MCP 模板或配置契约时递增 plugin 的 SemVer 版本。
- 修改 marketplace 索引、plugin source 或 marketplace 元数据时递增 marketplace metadata 版本。
- 本文件只记录仓库中已完成的功能，不代表已经执行 Git tag、push 或其他远端发布操作。
