# oh-my-agent-toolbox

可通过不同宿主 adapter 分发的通用 Agent Skills、hooks、agents、MCP 配置模板和项目流程工具，兼容 Claude、OpenCode 与 ChatGPT/Codex 工作流。

## 名称和安装

公开 marketplace 与 plugin 名称均为 `oh-my-agent-toolbox`；仓库内部目录仍为 `plugins/oh-my-skills`，仅作为 marketplace source 路径。

从 GitHub 安装：

```text
/plugin marketplace add https://github.com/promise94/oh-my-agent-toolbox
/plugin install oh-my-agent-toolbox@oh-my-agent-toolbox
/reload-plugins
/reload-skills
```

从本地或私有 checkout 安装：

```text
/plugin marketplace add /absolute/path/to/oh-my-agent-toolbox
/plugin install oh-my-agent-toolbox@oh-my-agent-toolbox
```

完整安装、更新、卸载和 bootstrap 说明见 [`../../docs/installation.md`](../../docs/installation.md)。故障排查见 [`../../docs/troubleshooting.md`](../../docs/troubleshooting.md)。

## 能力

- `$planning-workflow`：可恢复的分阶段计划、门禁和归档。正文按 Agent Skills 标准编写，不含宿主专有工具名；宿主能力差异由 `skills/planning-workflow/references/host-contract.md` 解析。
- `$plan-review`：通过 Codex plugin 对计划执行独立 review。
- `$plan-audit`：对完成的实施执行独立 audit。
- Stop hook：提示当前计划的 review、phase 和 audit 状态；需在项目内执行 bootstrap 后启用，plugin 本身不注册 hook。
- Rules：`rules/plan-mode.md` 是计划流程硬约束；`bootstrap.py --with-rules` 会把它安装到项目 `.claude/rules/` 并写入 `CLAUDE.md` 的标记块。
- Agents：提供计划流程的展示元数据。
- MCP：`config-templates/mcp.example.json` 仅为 opt-in 示例，不会自动安装、启动或连接 MCP server。
- Settings：`config-templates/settings.local.example.json` 是复制模板，不会自动覆盖用户配置。
- 所有 Skill 平级维护；新增其他 Skill 不需要先调用 `planning-workflow`。统一维护流程见 [`../../docs/skill-maintenance.md`](../../docs/skill-maintenance.md)。
- ChatGPT/Codex portable 包通过 `adapters/chatgpt/export.py` 生成；它不包含 Claude Marketplace、Stop hook 或项目运行时状态。

## 宿主与评审通道

`planning-workflow` 的装载遵循 Agent Skills 开放标准：SKILL.md 加 frontmatter，放到各宿主自己的 skills 目录即可，文件内容不需要改。宿主能力差异（结构化提问、计划模式、Stop hook、状态目录）集中在 `references/host-contract.md`，正文只引用能力编号 C1–C5。

独立评审按可用性降级：外部评审命令（Claude 上的 `/codex:rescue`）优先，其次是无上下文的子 agent，都没有时只能记 `blocked`；用户明确同意跳过才能记 `waived`。本项目不包含或自动安装 Codex plugin，两者都不能伪造为已完成检查。

## 本地开发

在 plugin 根目录运行：

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py tests/*.py
bash -n hooks/phase-gate.sh
python3 scripts/validate-config.py config-templates/*.json
```

首次在目标项目启用阶段门禁时运行：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py"
```

脚本应从任意工作目录可调用；需要项目状态时通过 `--root` 或 `CLAUDE_PROJECT_DIR` 指定项目根目录。运行时状态（`.claude/phase_state.json`、`.claude/temp/` 和 plan history）不属于 plugin 发布内容。

## MCP 安全

MCP 配置示例中的环境变量只表示占位符。请在本地 secret manager、shell 环境或 Claude 的本地配置中注入真实值，不要把 token、password、API key 或私钥提交到 Git。安装第三方 MCP server 前确认其来源、权限和数据范围。

## 版本

marketplace 和 plugin 使用独立的 SemVer 版本；改变 skill、hook、agent、MCP 模板或配置契约时更新 plugin version，并在 [`../../CHANGELOG.md`](../../CHANGELOG.md) 中记录兼容性影响。
