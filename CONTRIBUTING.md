# Contributing

## 目录约定

- `plugins/<plugin>/.claude-plugin/plugin.json`：plugin 元数据；本仓库的公开 plugin 名称是 `oh-my-agent-toolbox`。
- `plugins/<plugin>/skills/<skill>/SKILL.md`：可调用 skill；每个 skill 使用独立目录。
- `plugins/<plugin>/scripts/`：可测试的实现脚本。
- `plugins/<plugin>/hooks/hooks.json`：plugin hook 声明；命令使用 `${CLAUDE_PLUGIN_ROOT}`。
- `plugins/<plugin>/agents/`：agent 定义或展示元数据。
- `plugins/<plugin>/config-templates/`：不含凭证的配置模板。
- `plugins/<plugin>/tests/`：不依赖网络和用户配置的测试。

## 约束

1. 只维护一份 canonical 实现，不复制脚本到旧目录或多个 plugin。
2. 不提交凭证、个人数据、绝对机器路径或本地 `.claude` 运行时状态。
3. MCP 配置必须 opt-in，明确权限、依赖和 secret 注入方式。
4. hook 不应破坏用户已有配置；配置写入必须幂等并可回滚。
5. 对 skill、plugin manifest、hook、MCP 模板和公共配置契约变化补充测试。

## 提交前验证

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
