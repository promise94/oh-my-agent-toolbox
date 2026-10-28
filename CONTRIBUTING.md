# Contributing

## 目录约定

- `plugins/<plugin>/.claude-plugin/plugin.json`：plugin 元数据；本仓库的公开 plugin 名称是 `oh-my-agent-toolbox`。
- `plugins/<plugin>/skills/<skill>/SKILL.md`：可调用 skill；每个 skill 使用独立目录。
- `plugins/<plugin>/scripts/`：可测试的实现脚本。
- `plugins/<plugin>/hooks/`：bootstrap 安装到项目 `.claude/hooks/` 的 hook 源文件；plugin 本身不注册 Stop hook，门禁只在执行过 bootstrap 的项目中生效。
- `plugins/<plugin>/agents/`：agent 定义或展示元数据。
- `plugins/<plugin>/config-templates/`：不含凭证的配置模板。
- `plugins/<plugin>/tests/`：不依赖网络和用户配置的测试。

## 约束

1. 只维护一份 canonical 实现，不复制脚本到旧目录或多个 plugin。
2. 不提交凭证、个人数据、绝对机器路径或本地 `.claude` 运行时状态。
3. MCP 配置必须 opt-in，明确权限、依赖和 secret 注入方式。
4. hook 不应破坏用户已有配置；配置写入必须幂等并可回滚。
5. 对 skill、plugin manifest、hook、MCP 模板和公共配置契约变化补充测试。

## 文档维护

- 面向用户的安装、更新、卸载、bootstrap 和 Claude/Codex 边界说明维护在 `docs/installation.md`。
- 常见 marketplace、plugin、skill、hook、Codex 和 MCP 问题维护在 `docs/troubleshooting.md`。
- 用户可见版本变更记录在 `CHANGELOG.md`；不要把未执行的 tag、push 或远端发布写成已完成。
- 文档中的公开 marketplace/plugin 名称使用 `oh-my-agent-toolbox`；`plugins/oh-my-skills` 只作为内部目录和 source 路径。
- 复制安装命令前，确认 marketplace 名称和 plugin 名称均为 `oh-my-agent-toolbox`。


```bash
python3 -m unittest discover -s marketplace-tests -v
python3 -m unittest discover -s plugins/oh-my-skills/tests -v
python3 -m py_compile plugins/oh-my-skills/scripts/*.py plugins/oh-my-skills/tests/*.py
python3 plugins/oh-my-skills/scripts/validate-config.py plugins/oh-my-skills/config-templates/*.json
bash -n plugins/oh-my-skills/hooks/phase-gate.sh
git diff --check
```

## 发布检查

- 更新 marketplace/plugin version。
- 确认 marketplace source 是仓库内相对路径。
- 检查 manifest、README 和模板没有本地状态或凭证。
- 在临时 Claude 环境安装本地 marketplace，确认 skill 名称和 hook 能加载。
- 未经明确授权不要执行远端发布、tag、push 或 marketplace 注册。
