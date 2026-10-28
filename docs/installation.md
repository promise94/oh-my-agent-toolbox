# 安装与使用

## 名称说明

本项目有三个容易混淆的名称：

- **marketplace 名称**：`oh-my-agent-toolbox`
- **公开 plugin 名称**：`oh-my-agent-toolbox`
- **仓库内部目录**：`plugins/oh-my-skills`

安装命令使用 marketplace 名称，不使用内部目录名：

```text
/plugin install oh-my-agent-toolbox@oh-my-agent-toolbox
```

## 从 GitHub 安装

```text
/plugin marketplace add https://github.com/promise94/oh-my-agent-toolbox
/plugin install oh-my-agent-toolbox@oh-my-agent-toolbox
/reload-plugins
/reload-skills
```

安装后可在 Claude 的 skill 列表中确认 `plan-standard`、`codex-plan-review` 和 `codex-plan-audit` 是否可用。

## 从本地仓库安装

```text
/plugin marketplace add /absolute/path/to/oh-my-agent-toolbox
/plugin install oh-my-agent-toolbox@oh-my-agent-toolbox
```

路径必须指向包含 `.claude-plugin/marketplace.json` 的仓库根目录，而不是 `plugins/oh-my-skills` 子目录。

## 从私有 Git 仓库安装

使用 Claude 支持的私有仓库 URL 或本地 checkout：

```text
/plugin marketplace add <private-repository-url-or-local-path>
/plugin install oh-my-agent-toolbox@oh-my-agent-toolbox
```

私有仓库的认证由 Git/Claude 的现有配置负责。本项目不接收、不保存或要求在命令中传入 token、password 或 API key。

## 更新、重载和卸载

更新已安装 plugin：

```text
/plugin update oh-my-agent-toolbox
/reload-plugins
/reload-skills
```

如果 CLI 版本不支持单独的 update 命令，可重新添加 marketplace 后通过 plugin 管理命令检查版本。当前版本见 plugin manifest 和 [`CHANGELOG.md`](../CHANGELOG.md)。

从 `0.1.0` 升级到 `0.2.0` 时注意：plugin 不再随包注册 Stop hook。已经执行过 bootstrap 的项目会保留原有注册项，无需操作；从未 bootstrap 的项目升级后不会收到任何门禁提示，需要按下一节重新启用。

卸载 plugin：

```text
/plugin uninstall oh-my-agent-toolbox
```

卸载 plugin 不会删除目标项目的 `.claude` 运行时状态，也不会自动删除用户配置。清理项目状态前应先确认其是否仍被其他流程使用。

## 首次启用项目级阶段门禁

安装 plugin 不会自动修改每个项目的 `.claude` 配置。首次在某个目标项目使用 `$plan-standard` 前，在该项目根目录执行：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py"
```

bootstrap 会：

- 从 plugin 安装项目级 `.claude/hooks/phase-gate.sh`；
- 将 Stop hook 幂等合并到优先选择的可写 settings 文件；
- 保留已有 settings，不重复添加同一 hook；
- 在写入前校验 JSON，并使用原子写入；
- 失败时报告 `BLOCKED`，不会假装阶段门禁已经启用。

加上 `--with-rules` 时会额外安装计划流程硬约束：把 `rules/plan-mode.md` 复制到 `.claude/rules/plan-mode.md`，并把带注释标记的约束块写入项目 `CLAUDE.md`。重复执行只会更新该标记块，块外内容保持原样；不带参数时不会创建或修改 `CLAUDE.md`。

它不会修改用户全局 Claude 配置，也不会安装 MCP server。

## Claude 与 Codex 的边界

| 能力 | Claude | Codex |
| --- | --- | --- |
| 安装和加载 marketplace/plugin | 负责 | 不负责本项目的 plugin 加载 |
| 加载 `SKILL.md` | 负责 | 按流程读取 request/context 文件 |
| Stop hook 和阶段门禁 | 负责 | 不适用 |
| 计划状态、临时 request、审计摘要 | 维护项目级文件 | 只读这些文件并返回报告 |
| review/audit | 发起流程、写回 disposition | 在可用时提供独立报告 |
| MCP 模板 | 提供 opt-in 示例 | 按 Codex 自己的配置方式接入 |

本项目不包含或自动安装 Codex plugin。Codex review/audit 不可用时必须记录为 `blocked`；只有用户明确决定跳过当前计划时，才能记录为 `waived`。`blocked` 不能视为通过。

## MCP 与 settings 安全

`config-templates/mcp.example.json` 和 `config-templates/settings.local.example.json` 都是复制模板：

- 不会自动启用或连接 MCP server；
- 不包含真实凭证；
- 不会自动覆盖用户已有配置；
- 真实 secret 应通过本地环境、secret manager 或 Claude 的本地配置注入；
- 使用第三方 MCP server 前应确认来源、权限和数据范围。

## 公开仓库

当前公开仓库：

```text
https://github.com/promise94/oh-my-agent-toolbox
```

内部目录名 `oh-my-skills` 只用于保持当前仓库布局和 source 路径兼容。
