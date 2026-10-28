#!/usr/bin/env python3
"""Prepare request and context files for a Codex plan review."""

from __future__ import annotations

import argparse
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REVIEW_FORMAT_DOC = PLUGIN_ROOT / "skills" / "plan-standard" / "references" / "review-subagent-prompt.md"


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

## 任务与输出

完整执行 `{review_format_path}` 中的任务清单、检查清单和输出格式。该文件是 review 任务和输出格式的唯一来源；本文件只提供输入路径和只读边界。不要实施修复，不要重写计划。
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
        REQUEST_TEMPLATE.format(
            plan_path=plan,
            context_path=context,
            request_path=request,
            review_format_path=REVIEW_FORMAT_DOC,
        ),
        encoding="utf-8",
    )
    if context.is_file() and context.read_text(encoding="utf-8").strip():
        context_note = f"kept existing review context at {context}"
    else:
        context.write_text(
            "# Codex 计划上下文（兜底）\n\n"
            f"- 计划文件：`{plan}`\n"
            "- 需求摘要：未提供。主 agent 应在运行本脚本前写入 5-8 句需求摘要，覆盖目标、约束、Phase 0 决策和假设。\n"
            "- 主 agent 结论：未提供；请独立读取计划和相关代码。\n"
            "- 本文件不包含 shell 命令或 runtime 配置。\n",
            encoding="utf-8",
        )
        context_note = f"wrote fallback review context to {context}"
    print(f"PASS: wrote review request to {request}")
    print(f"PASS: {context_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
