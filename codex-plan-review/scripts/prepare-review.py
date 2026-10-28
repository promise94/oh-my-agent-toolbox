#!/usr/bin/env python3
"""Prepare request and context files for a Codex plan review."""

from __future__ import annotations

import argparse
from pathlib import Path


def require_inside(path: Path, directory: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(directory.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must be inside {directory.resolve()}") from exc
    return resolved


REQUEST_TEMPLATE = """# Codex 计划评审请求

请对当前仓库执行独立、只读的计划评审。

本文件是本次任务唯一 request 文件：`{request_path}`。通过 `/codex:rescue` 收到请求后，必须先读取本文件，再读取下列输入；不要扫描 `.claude/temp/` 猜测其他 request。

## 输入

- 计划：`{plan_path}`
- 需求与上下文：`{context_path}`
- 仓库：当前仓库根目录
- 项目规则：仓库中的 `CLAUDE.md`、`AGENTS.md`（如存在）

## 只读边界

可以读取文件和现有 diff/status。不得修改、删除或创建文件，不得安装依赖、提交或发布，不需要执行验收命令。不要覆盖 model、provider、effort 或其他 runtime 配置。无法读取的信息报告“未读取”，不要发送空工具消息。

## 检查项

1. 每项需求是否对应明确阶段和文件级变更。
2. 验收标准是否可执行、约束是否可衡量。
3. 阶段依赖、错误处理、回滚、边界和文档是否完整。
4. 是否存在范围漂移、未记录假设或与现有代码冲突。

## 输出

按仓库中的 `plan-standard/references/review-subagent-prompt.md` 格式输出完整报告。不要实施修复，不要重写计划。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    plan = args.plan.resolve()
    temp_dir = root / ".claude" / "temp"
    try:
        request = require_inside(args.request, temp_dir, "request")
        context = require_inside(args.context, temp_dir, "context")
    except ValueError as exc:
        parser.error(str(exc))
    if not plan.is_file():
        parser.error(f"plan does not exist: {plan}")
    if root not in plan.parents:
        parser.error("plan must be inside repository root")

    request.parent.mkdir(parents=True, exist_ok=True)
    context.parent.mkdir(parents=True, exist_ok=True)
    request.write_text(
        REQUEST_TEMPLATE.format(plan_path=plan, context_path=context, request_path=request), encoding="utf-8"
    )
    context.write_text(
        "# Codex 计划上下文\n\n"
        f"- 计划文件：`{plan}`\n"
        "- 目标：独立检查计划是否自包含、可执行、可验证。\n"
        "- 主 agent 结论：未提供；请独立读取计划和相关代码。\n"
        "- 本文件不包含 shell 命令或 runtime 配置。\n",
        encoding="utf-8",
    )
    print(f"PASS: wrote review request to {request}")
    print(f"PASS: wrote review context to {context}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
