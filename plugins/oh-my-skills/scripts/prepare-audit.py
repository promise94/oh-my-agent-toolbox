#!/usr/bin/env python3
"""Prepare request and implementation summary files for a Codex audit."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def require_inside(path: Path, directory: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(directory.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must be inside {directory.resolve()}") from exc
    return resolved


REQUEST_TEMPLATE = """# Codex 最终审计请求

请对当前仓库执行独立、只读的最终审计。

本文件是本次任务唯一 request 文件：`{request_path}`。通过 `/codex:rescue` 收到请求后，必须先读取本文件，再读取下列输入；不要扫描 `.claude/temp/` 猜测其他 request。

## 输入

- 计划：`{plan_path}`
- 仓库：当前仓库根目录
- 实施摘要：`{summary_path}`
- 原始工作树摘要：`{baseline_path}`
- 项目规则：仓库中的 `CLAUDE.md`、`AGENTS.md`（如存在）
- 相关文件：`plugins/oh-my-skills/`、`.claude-plugin/`

## 只读边界

可以读取文件、查看现有 diff/status 和实施摘要。不得修改、删除或创建文件，不得安装依赖、提交或发布，不需要运行测试。不要覆盖 model、provider、effort 或其他 runtime 配置。如果信息无法读取，报告“未读取”，不要发送空工具消息。

## 审计检查

1. 对照计划逐阶段检查文件级变更是否完成。
2. 检查 Codex review 的发现、采纳项和不采纳项是否记录。
3. 检查 `.claude` 状态路径、状态字段、review disposition、phase gate 和 archive 规则是否一致。
4. 检查未计划变更、占位内容、调试输出和文档矛盾。
5. 使用实施摘要中的本地验证结果，不执行命令。

## 输出格式

### 阶段 N：[阶段名称] - PASS|FAIL|PARTIAL
- 验收标准：通过/失败 - [证据]
- 约束：满足/违反 - [实际值与预期值]
- 说明：[偏差或风险]

## 总结
- 审计结论：APPROVED|NEEDS REVISION
- 通过阶段：X/Y
- 通过验收标准：X/Y
- 满足约束：X/Y
- 主要缺口：[具体内容]

不要实施修复，不要重写计划。
"""


def run_git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "未读取"
    if result.returncode != 0:
        return "未读取"
    return result.stdout.strip() or "无"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error("timeout-seconds must be positive")

    root = args.root.resolve()
    plan = args.plan.resolve()
    temp_dir = root / ".claude" / "temp"
    try:
        request = require_inside(args.request, temp_dir, "request")
        summary = require_inside(args.summary, temp_dir, "summary")
        baseline_path = require_inside(args.baseline, root, "baseline") if args.baseline else None
        validation = require_inside(args.validation, root, "validation") if args.validation else None
    except ValueError as exc:
        parser.error(str(exc))
    if not plan.is_file():
        parser.error(f"plan does not exist: {plan}")
    if root not in plan.parents:
        parser.error("plan must be inside repository root")

    request.parent.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)
    request.write_text(
        REQUEST_TEMPLATE.format(
            plan_path=plan,
            summary_path=summary,
            baseline_path=baseline_path if baseline_path else "未提供",
            request_path=request,
        ),
        encoding="utf-8",
    )

    status = run_git(root, "status", "--short")
    diff_stat = run_git(root, "diff", "--stat")
    branch = run_git(root, "branch", "--show-current")
    baseline = "未提供"
    if baseline_path:
        if not baseline_path.is_file():
            parser.error(f"baseline summary does not exist: {baseline_path}")
        baseline = baseline_path.read_text(encoding="utf-8").strip() or "无"
    validation_text = "未提供"
    if validation is not None:
        if not validation.is_file():
            parser.error(f"validation summary does not exist: {validation}")
        validation_text = validation.read_text(encoding="utf-8").strip() or "无"

    summary.write_text(
        "# Codex 实施摘要\n\n"
        "- 计划文件存在：是。\n"
        f"- 当前分支：{branch}\n"
        "- 原始工作树摘要：\n"
        f"  {baseline.replace(chr(10), chr(10) + '  ')}\n"
        "- 当前工作树状态摘要：\n"
        f"  {status.replace(chr(10), chr(10) + '  ')}\n"
        "- 当前变更统计摘要：\n"
        f"  {diff_stat.replace(chr(10), chr(10) + '  ')}\n"
        "- 本地验证由主 agent 提供；Codex 不需要运行测试或其他命令。\n"
        f"- Codex task timeout budget (seconds): {args.timeout_seconds}.\n"
        f"- 本地验证摘要：{validation_text}\n"
        "- 请以计划文件、当前文件内容和现有变更为准，发现无法读取的信息时报告“未读取”。\n",
        encoding="utf-8",
    )
    print(f"PASS: wrote audit request to {request}")
    print(f"PASS: wrote implementation summary to {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
