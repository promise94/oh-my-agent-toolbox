# oh-my-agent-toolbox

该仓库提供名为 `oh-my-agent-toolbox` 的 Agent Skills 工具箱，集中维护可复用的 skills、hooks、agents、MCP 配置模板及项目流程工具，并通过 Claude、OpenCode、ChatGPT/Codex adapter 分发。

内部目录仍使用 `plugins/oh-my-skills` 作为 marketplace source；这是仓库布局名称，不是公开 marketplace 或 plugin 名称。

## 快速安装

Claude 可从公开 GitHub 仓库添加 marketplace：

```text
/plugin marketplace add https://github.com/promise94/oh-my-agent-toolbox
/plugin install oh-my-agent-toolbox@oh-my-agent-toolbox
/reload-plugins
/reload-skills
```

本地或私有仓库安装、更新、卸载和安装确认请参阅 [`docs/installation.md`](docs/installation.md)。

## 能力

- `$planning-workflow`：可恢复的分阶段计划、门禁和归档。
- `$plan-review`：通过 Codex plugin 对计划执行独立 review。
- `$plan-audit`：对完成的实施执行独立 audit。
- Stop hook：提示当前计划的 review、phase 和 audit 状态；需在项目内执行 bootstrap 后启用，plugin 本身不注册 hook。
- Rules：`rules/plan-mode.md` 是计划流程硬约束；`bootstrap.py --with-rules` 会把它安装到项目 `.claude/rules/` 并写入 `CLAUDE.md` 的标记块。
- Agents：提供计划流程的展示元数据。
- MCP：提供 opt-in 配置模板，不会自动安装、启动或连接 MCP server。
- Settings：提供项目级复制模板，不会自动覆盖用户全局配置。
- Skill 维护：所有 Skill 平级维护，新增任意 Skill 不要求先调用 `planning-workflow`；维护流程见 [`docs/skill-maintenance.md`](docs/skill-maintenance.md)。

Claude、OpenCode、ChatGPT/Codex 的职责边界、bootstrap/导出流程和安全约束见 [`docs/installation.md`](docs/installation.md) 与 [`docs/skill-maintenance.md`](docs/skill-maintenance.md)。常见安装、加载和审计问题见 [`docs/troubleshooting.md`](docs/troubleshooting.md)。

## 版本

marketplace 与 plugin 当前版本均为 `1.0.1`。修改 skill、hook、agent、MCP 模板或配置契约时，更新 plugin version；修改 marketplace 索引时更新 marketplace metadata version。变更记录见 [`CHANGELOG.md`](CHANGELOG.md)。

## 验证

```bash
python3 -m unittest discover -s marketplace-tests -v
python3 -m unittest discover -s plugins/oh-my-skills/tests -v
python3 -m py_compile plugins/oh-my-skills/scripts/*.py plugins/oh-my-skills/tests/*.py
python3 plugins/oh-my-skills/scripts/validate-config.py plugins/oh-my-skills/config-templates/*.json
git diff --check
```

`.claude/` 中的活动状态、临时文件、用户 settings 和历史归档不属于 marketplace 内容。
