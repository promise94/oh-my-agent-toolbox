# 故障排查

## `Marketplace not found`

### 现象

```text
Marketplace "oh-my-skills" not found
```

### 原因

`oh-my-skills` 是仓库内部目录名，不是 marketplace 名称。公开 marketplace 名称是 `oh-my-agent-toolbox`。

### 处理

```text
/plugin marketplace add https://github.com/promise94/oh-my-agent-toolbox
/plugin install oh-my-agent-toolbox@oh-my-agent-toolbox
```

### 验证

重新运行：

```text
/reload-plugins
/reload-skills
```

## `Invalid marketplace schema`

### 现象

```text
Invalid marketplace schema
```

### 处理

确认添加的是仓库 URL，而不是 README 页面、raw 文件片段、错误输出拼接后的 URL 或 `plugins/oh-my-skills` 子目录：

```text
https://github.com/promise94/oh-my-agent-toolbox
```

本地安装时，路径必须指向包含 `.claude-plugin/marketplace.json` 的仓库根目录：

```text
/plugin marketplace add /absolute/path/to/oh-my-agent-toolbox
```

如果问题仍在，检查 marketplace 文件是否是 JSON object，且包含 `name` 和 `plugins` 字段。

## HTTP `403` 或下载失败

### 现象

```text
HTTP 403 error while downloading marketplace
```

### 原因

远程 Git 服务、WAF、访问权限或 Claude 当前网络环境可能拒绝 marketplace 下载。错误不一定表示仓库文件不存在。

### 处理

优先使用 GitHub 地址：

```text
/plugin marketplace add https://github.com/promise94/oh-my-agent-toolbox
```

如果仓库是私有仓库，先确认 Claude/Git 已经具备访问权限；也可以使用本地 checkout：

```text
/plugin marketplace add /absolute/path/to/oh-my-agent-toolbox
```

不要把 token、password 或 API key 拼接到命令、URL 或文档中。

## Plugin 已安装但 skill 没有出现

按顺序执行：

```text
/reload-plugins
/reload-skills
```

然后确认安装的是：

```text
oh-my-agent-toolbox@oh-my-agent-toolbox
```

需要确认的 skill 名称是：

```text
plan-standard
codex-plan-review
codex-plan-audit
```

如果仍未出现，检查 marketplace 是否来自预期仓库和版本，并确认 plugin manifest 中的 `skills/` 目录没有被打包遗漏。

## Hook 没有生效

### 先确认 plugin hook 已加载

重新加载 plugin：

```text
/reload-plugins
```

### 再确认目标项目已 bootstrap

在目标项目根目录运行：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py"
```

检查以下文件是否存在：

```text
.claude/hooks/phase-gate.sh
.claude/settings.local.json
```

bootstrap 失败时应查看命令输出中的 `BLOCKED` 原因。常见原因包括 settings JSON 非法、配置结构冲突或目标目录不可写。

安装 plugin 本身不会自动修改所有项目的 settings；必须在需要阶段门禁的项目中单独 bootstrap。

## `CLAUDE_PLUGIN_ROOT` 不可用

`CLAUDE_PLUGIN_ROOT` 由 Claude plugin 运行环境提供。不要把它改成固定的本机路径，也不要把 `/Users/...` 等绝对路径提交到配置。

如果直接从 shell 调试脚本，可显式指定项目根目录：

```bash
CLAUDE_PROJECT_DIR=/absolute/path/to/project \
python3 /path/to/plugin/scripts/phase-gate.py
```

## Codex review/audit 不可用

如果 Codex plugin、setup、rescue 或 status 失败：

- 将对应状态记录为 `blocked`；
- 保留失败原因和必要的输出；
- 不得把 `blocked` 当作 review/audit 通过；
- 不得伪造 Codex 报告。

只有用户明确选择跳过当前计划时，才能将当前计划记录为 `waived`，并在计划和状态中写明原因。`waived` 只表示当前计划获得明确例外，不表示 Codex 已完成检查。

如果 Codex 能力恢复，应从同一份活动计划继续，不要新建替代计划。

## 计划状态异常或中断

检查项目状态：

```text
.claude/phase_state.json
.claude/plans/
.claude/temp/
```

活动计划应从 `phase_state.json` 指向的计划恢复。不要根据 `.claude/temp/` 中“最近修改”的文件猜测 request。

如果计划已经处于 `completed`、`cancelled` 或 `abandoned`，按照 `$plan-standard` 的流程先归档，再开始新计划。

## MCP server 无法连接

本项目只提供示例配置，不负责安装或启动第三方 MCP server。请单独确认：

1. server 来源和版本可信；
2. 本地命令和依赖已安装；
3. secret 已通过本地安全方式注入；
4. MCP 权限和数据范围符合项目要求；
5. 配置通过 `validate-config.py`，且没有提交真实凭证。

不要把 server token、password、API key 或私钥写入 Git。
