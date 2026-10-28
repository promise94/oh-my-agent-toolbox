# Marketplace 维护

该仓库通过 `.claude-plugin/marketplace.json` 暴露 marketplace，通过 `plugins/oh-my-skills/.claude-plugin/plugin.json` 暴露 `oh-my-agent-toolbox` plugin。

## 安装

```text
/plugin marketplace add /absolute/path/to/oh-my-skills
/plugin install oh-my-agent-toolbox@oh-my-skills
```

## 版本

marketplace 与 plugin 当前版本均为 `0.1.0`。修改 skill、hook、agent、MCP 模板或配置契约时，更新 plugin version；修改 marketplace 索引时更新 marketplace metadata version。

## 验证

```bash
python3 -m unittest discover -s marketplace-tests -v
python3 -m unittest discover -s plugins/oh-my-skills/tests -v
python3 -m py_compile plugins/oh-my-skills/scripts/*.py plugins/oh-my-skills/tests/*.py
python3 plugins/oh-my-skills/scripts/validate-config.py plugins/oh-my-skills/config-templates/*.json
bash -n plugins/oh-my-skills/hooks/phase-gate.sh
git diff --check
```

`.claude/` 中的活动状态、临时文件、用户 settings 和历史归档不属于 marketplace 内容。
