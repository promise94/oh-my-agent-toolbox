# oh-my-skills

可通过 Claude marketplace 安装的通用 skills、hooks、agents、MCP 配置模板和项目流程工具。

## 安装

从本地或私有 Git 仓库添加 marketplace：

```text
/plugin marketplace add /absolute/path/to/oh-my-skills
```

公开仓库可使用仓库 URL：

```text
/plugin marketplace add https://github.com/OWNER/REPOSITORY
```

然后安装 plugin：

```text
/plugin install oh-my-skills@oh-my-skills
```

本仓库当前只提供 marketplace/plugin 结构和本地实现，未执行远端发布。

公开仓库当前位于：

```text
https://gitee.com/promise9495/oh-my-skills
```

## 能力

- `$plan-standard`：可恢复的分阶段计划、门禁和归档。
- `$codex-plan-review`：通过 Codex plugin 对计划执行独立 review。
- `$codex-plan-audit`：对完成的实施执行独立 audit。
- Stop hook：提示当前计划的 review、phase 和 audit 状态。
- Agents：提供计划流程的展示元数据。
- MCP：`config-templates/mcp.example.json` 仅为 opt-in 示例，不会自动安装、启动或连接 MCP server。
- Settings：`config-templates/settings.local.example.json` 是复制模板，不会自动覆盖用户配置。

## 本地开发

在 plugin 根目录运行：

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py tests/*.py
bash -n hooks/phase-gate.sh
python3 scripts/validate-config.py config-templates/*.json
```

脚本应从任意工作目录可调用；需要项目状态时通过 `--root` 或 `CLAUDE_PROJECT_DIR` 指定项目根目录。运行时状态（`.claude/phase_state.json`、`.claude/temp/` 和 plan history）不属于 plugin 发布内容。

## MCP 安全

MCP 配置示例中的环境变量只表示占位符。请在本地 secret manager、shell 环境或 Claude 的本地配置中注入真实值，不要把 token、password、API key 或私钥提交到 Git。安装第三方 MCP server 前确认其来源、权限和数据范围。

## 版本

marketplace 和 plugin 使用独立的 SemVer 版本；改变 skill、hook、agent、MCP 模板或配置契约时更新 plugin version，并在 release notes 中记录兼容性影响。
