#!/usr/bin/env python3
"""Prepare request and implementation summary files for a Codex audit."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
AUDIT_FORMAT_DOC = PLUGIN_ROOT / "skills" / "plan-standard" / "references" / "audit-subagent-prompt.md"

PHASE_HEADING = re.compile(r"^#{2,4}\s*(?:阶段\s*(\d+)|Phase\s*(\d+))\s*[:：]?\s*(.*)$", re.IGNORECASE)
TICKED = re.compile(r"`([^`\n]+)`")
MAX_FILES_PER_PHASE = 20
PATH_SUFFIXES = (".py", ".sh", ".md", ".json", ".toml", ".yaml", ".yml", ".txt", ".js", ".ts", ".vue")


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
- 实施摘要（逐阶段对账表）：`{summary_path}`
- 原始工作树摘要：`{baseline_path}`
- 项目规则：仓库中的 `CLAUDE.md`、`AGENTS.md`（如存在）

## 只读边界

可以读取文件、查看现有 diff/status 和实施摘要。不得修改、删除或创建文件，不得安装依赖、提交或发布，不需要运行测试。不要覆盖 model、provider、effort 或其他 runtime 配置。如果信息无法读取，报告“未读取”，不要发送空工具消息。

## 任务与输出

完整执行 `{audit_format_path}` 中的任务清单与输出格式。该文件是审计任务和输出格式的唯一来源；本文件只提供输入路径和只读边界。不要实施修复，不要重写计划。
"""


def run_git(root: Path, *args: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return False, f"git 不可用：{exc}"
    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()
        reason = detail[-1] if detail else "无输出"
        return False, f"git {' '.join(args)} 失败（exit {result.returncode}）：{reason}"
    return True, result.stdout.strip() or "无"


def looks_like_path(token: str) -> bool:
    if not token or " " in token:
        return False
    if any(char in token for char in "{}<>$*|"):
        return False
    if token.startswith(("http://", "https://")):
        return False
    # 绝对路径和斜杠命令（/codex:setup、/codex:rescue）不是仓库相对路径，不参与对账。
    if token.startswith("/"):
        return False
    if "/" in token:
        return True
    return token.endswith(PATH_SUFFIXES)


def extract_phases(plan_text: str) -> list[dict[str, object]]:
    """Collect per-phase file paths declared in the plan."""
    phases: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in plan_text.splitlines():
        heading = PHASE_HEADING.match(line)
        if heading:
            number = heading.group(1) or heading.group(2)
            title = heading.group(3).strip(" ：:")
            current = {"label": f"阶段 {number}" + (f"：{title}" if title else ""), "paths": []}
            phases.append(current)
            continue
        if current is None:
            continue
        paths = current["paths"]
        assert isinstance(paths, list)
        for token in TICKED.findall(line):
            candidate = token.strip()
            while candidate.startswith("./"):
                candidate = candidate[2:]
            if looks_like_path(candidate) and candidate not in paths:
                paths.append(candidate)
    return phases


def cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "；")


def describe_path(root: Path, relative: str) -> tuple[str, str, str]:
    target = root / relative
    if not target.exists():
        return "否", "—", "—"
    _, porcelain = run_git(root, "status", "--porcelain", "--", relative)
    if porcelain.startswith("git "):
        worktree = porcelain
    else:
        worktree = "未变更" if porcelain == "无" else porcelain
    _, log = run_git(root, "log", "--oneline", "-2", "--", relative)
    return "是", cell(worktree), cell(log)


def build_phase_tables(root: Path, plan_text: str) -> tuple[str, int, int, int]:
    phases = extract_phases(plan_text)
    if not phases:
        return "未识别到阶段标题：请直接读取计划逐阶段核对，本摘要不做阶段映射。\n", 0, 0, 0
    blocks: list[str] = []
    file_total = 0
    missing_total = 0
    for phase in phases:
        paths = phase["paths"]
        assert isinstance(paths, list)
        blocks.append(f"### {phase['label']}\n")
        if not paths:
            blocks.append("计划本阶段未声明文件路径。\n")
            continue
        blocks.append("| 计划文件 | 存在 | 工作树状态 | 最近提交 |\n| --- | --- | --- | --- |")
        shown = paths[:MAX_FILES_PER_PHASE]
        file_total += len(shown)
        for relative in shown:
            exists, worktree, log = describe_path(root, relative)
            if exists == "否":
                missing_total += 1
            blocks.append(f"| `{relative}` | {exists} | {worktree} | {log} |")
        if len(paths) > MAX_FILES_PER_PHASE:
            blocks.append(f"\n其余 {len(paths) - MAX_FILES_PER_PHASE} 个路径未列入表格，请直接读取计划。\n")
        blocks.append("")
    return "\n".join(blocks).rstrip() + "\n", len(phases), file_total, missing_total


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

    # 所有输入校验在使用/写盘之前完成，避免失败时留下半成品 request。
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
    plan_text = plan.read_text(encoding="utf-8")

    _, status = run_git(root, "status", "--short")
    _, diff_stat = run_git(root, "diff", "--stat")
    _, branch = run_git(root, "branch", "--show-current")
    phase_tables, phase_count, file_count, missing_count = build_phase_tables(root, plan_text)

    request.parent.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)
    request.write_text(
        REQUEST_TEMPLATE.format(
            plan_path=plan,
            summary_path=summary,
            baseline_path=baseline_path if baseline_path else "未提供",
            request_path=request,
            audit_format_path=AUDIT_FORMAT_DOC,
        ),
        encoding="utf-8",
    )
    summary.write_text(
        "# Codex 实施摘要\n\n"
        f"- 计划文件：`{plan}`\n"
        f"- 当前分支：{branch}\n"
        f"- 计划阶段数：{phase_count}；对账表覆盖路径数：{file_count}\n"
        "- 对账表数据来源：计划中的路径声明 + `git status --porcelain` + `git log --oneline -2`。\n"
        "- 对账表只陈述客观状态，不代表实现质量结论；请自行读取文件核对。\n"
        "- 路径按计划声明原样检查；`存在=否` 既可能是计划路径过期或目录重构，也可能表示未实施，请在报告中区分。\n"
        f"- `存在=否` 的路径数：{missing_count}。\n"
        f"- Codex task timeout budget (seconds): {args.timeout_seconds}.\n\n"
        "## 逐阶段对账表\n\n"
        f"{phase_tables}\n"
        "## 全局工作树\n\n"
        "- 原始工作树摘要：\n"
        f"  {baseline.replace(chr(10), chr(10) + '  ')}\n"
        "- 当前工作树状态摘要：\n"
        f"  {status.replace(chr(10), chr(10) + '  ')}\n"
        "- 当前变更统计摘要：\n"
        f"  {diff_stat.replace(chr(10), chr(10) + '  ')}\n\n"
        "## 本地验证\n\n"
        "- 本地验证由主 agent 提供；Codex 不需要运行测试或其他命令。\n"
        f"- 本地验证摘要：{validation_text}\n"
        "- 请以计划文件、当前文件内容和现有变更为准，发现无法读取的信息时报告“未读取”。\n",
        encoding="utf-8",
    )
    print(f"PASS: wrote audit request to {request}")
    print(f"PASS: wrote implementation summary to {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
