# 发布检查清单

- 更新 `.claude-plugin/marketplace.json`、plugin manifest、portable adapter manifest 和 `CHANGELOG.md` 的版本。
- 运行 `python3 scripts/validate-skills.py --check-jsonc --check-mcp`。
- 运行 Marketplace 与 plugin 全部测试、Python 编译和 `git diff --check`。
- 在空临时目录分别导出 OpenCode、ChatGPT/Codex 包，比较文件清单和 SHA-256。
- 扫描发布产物，确认没有 token、password、API key、个人绝对路径、`.claude/phase_state.json`、`.claude/temp` 或 plan-history。
- 确认 Claude adapter 的 Bootstrap 幂等、冲突保护和卸载测试通过。
- 只在用户明确授权后执行 tag、push、Marketplace 发布或外部写入。
