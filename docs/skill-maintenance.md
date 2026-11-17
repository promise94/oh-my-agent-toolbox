# Skill 维护流程

本仓库中的所有 Skill 平级维护，`planning-workflow` 不属于其他 Skill 的前置入口。新增、修改或废弃任意 Skill 都遵循同一套目录、元数据、测试和发布规则。

## Canonical 源

每个 Skill 的唯一可编辑源位于：

```text
plugins/oh-my-skills/skills/<skill-id>/
├── SKILL.md
├── references/   # 可选
├── scripts/      # 可选
├── assets/       # 可选
└── tests/        # 有脚本或公共契约时添加
```

`SKILL.md` 使用 Agent Skills frontmatter，目录名必须与 `name` 相同。正文描述触发条件、输入、输出、流程、边界和验证方式。Claude、OpenCode、ChatGPT/Codex 的安装路径、Hook、command、agent 和权限配置放在对应 adapter 中，不在 canonical Skill 里维护三份正文。

## 新增 Skill

1. 创建小写 kebab-case 的 `skills/<skill-id>/` 和 `SKILL.md`。
2. 在 `skills/skill-registry.json` 增加同名条目，填写版本、支持宿主、依赖和隐式调用策略。
3. 需要脚本或公共契约时，先写测试，再添加 `scripts/` 或测试文件。
4. 检查相对引用、宿主边界、凭证和本机绝对路径。
5. 更新与用户可见行为相关的 README、CHANGELOG 和版本号。

新增 Skill 不需要先调用 `planning-workflow`。只有当维护工作涉及跨模块架构、状态协议、迁移、宿主适配或发布风险时，才把 `planning-workflow` 作为本次仓库改造的工作流。

## 修改和废弃

- 文案、引用和局部流程修正：补丁版本，运行定向 Skill 校验和测试。
- 新增兼容能力或新宿主适配：次版本，更新 registry、adapter 和文档。
- 删除、重命名或改变输入输出：主版本；先保留旧 Skill ID 的兼容 wrapper 至少一个版本周期，并写迁移说明。
- 不直接删除用户运行时状态、计划文件、MCP 配置或宿主全局配置。

## 宿主导出

- Claude 使用 Marketplace/plugin adapter。
- OpenCode 使用 `.opencode/skills`、commands、agents 和权限配置。
- ChatGPT/Codex 使用 portable Plugin/Skill 包，可选 MCP 和本地 CLI。

adapter 的导出产物由脚本生成，不作为第二份可编辑 Skill 源。没有真实宿主运行环境时，只能报告结构或导出验证，不能称为运行时验证。

## 验证

```bash
python3 -m unittest discover -s plugins/oh-my-skills/tests -v
python3 -m unittest discover -s marketplace-tests -v
python3 -m py_compile plugins/oh-my-skills/scripts/*.py plugins/oh-my-skills/tests/*.py
python3 plugins/oh-my-skills/scripts/validate-config.py plugins/oh-my-skills/config-templates/*.json
git diff --check
```

发布前还要确认 registry 与 `skills/*/SKILL.md` 集合完全一致，所有 adapter 导出确定性一致，且产物不含 token、password、API key、个人路径或 `.claude` 运行时状态。
