#!/usr/bin/env python3
"""Manage the active Claude plan state: start, set, validate, archive."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from phase_model import (
    INT_FIELDS,
    STR_FIELDS,
    TERMINAL_STAGES,
    atomic_write,
    gate,
    load_state,
    now,
)

PLAN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def fail(message: str) -> int:
    print(f"ERROR: {message}")
    return 2


def state_file(root: Path) -> Path:
    return root / ".claude" / "phase_state.json"


def archive(root: Path) -> int:
    state, error = load_state(state_file(root))
    if state is None:
        if error == "not found":
            print("PASS: no active plan state to archive")
            return 0
        return fail(error or "invalid phase state")

    plan_id = state.get("plan_id")
    stage = state.get("workflow_stage")
    if not isinstance(plan_id, str) or not plan_id.strip():
        return fail("plan_id is missing")
    if not PLAN_ID_PATTERN.fullmatch(plan_id):
        return fail("plan_id must use kebab-case and contain only lowercase letters, digits, and hyphens")
    if stage not in TERMINAL_STAGES:
        return fail(f"only terminal plans can be archived (workflow_stage={stage})")
    if stage == "completed":
        if not state.get("terminal_at") or not state.get("terminal_reason"):
            return fail("completed plan must have terminal_at and terminal_reason")
        if state.get("phase_status") != "PASS":
            return fail("completed plan must have phase_status=PASS")
        if state.get("codex_review_status") not in {"completed", "waived"}:
            return fail("completed plan must have codex_review_status=completed or waived")
        if state.get("audit_status") not in {"completed", "waived"}:
            return fail("completed plan must have audit_status=completed or waived")
    # 取消/放弃计划可能发生在 review 之前，只要求终态字段，不强制 review/audit 处置。
    if stage in {"cancelled", "abandoned"}:
        if not state.get("terminal_at") or not state.get("terminal_reason"):
            return fail(f"{stage} plan must have terminal_at and terminal_reason")

    history_dir = root / ".claude" / "plan-history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = history_dir / f"{plan_id}.json"
    if history_path.exists():
        # 不覆盖已有历史：同 plan_id 再次归档时追加序号。
        index = 2
        while (history_dir / f"{plan_id}-{index}.json").exists():
            index += 1
        history_path = history_dir / f"{plan_id}-{index}.json"

    try:
        atomic_write(history_path, _dump(state))
        state_file(root).unlink()
    except OSError as exc:
        if history_path.exists():
            history_path.unlink()
        return fail(f"could not release active plan state: {exc}")

    print(f"PASS: archived {plan_id} to {history_path}")
    return 0


def _dump(state: dict[str, Any]) -> str:
    return json.dumps(state, ensure_ascii=False, indent=2) + "\n"


def _write_state(root: Path, state: dict[str, Any], action: str) -> int:
    code, lines = gate(state)
    if code == 2:
        print("ERROR: 拒绝写入：状态不合法")
        for line in lines[2:]:
            print(line)
        return 2
    try:
        atomic_write(state_file(root), _dump(state))
    except OSError as exc:
        return fail(f"could not write phase state: {exc}")
    print(f"PASS: {action} -> {state_file(root)}")
    print(f"  stage={state.get('workflow_stage')} phase={state.get('current_phase', '-')} "
          f"phase_status={state.get('phase_status', '-')} "
          f"review={state.get('codex_review_status', '-')} audit={state.get('audit_status', '-')}")
    return 0


def start(root: Path, plan: Path, plan_id: str | None) -> int:
    plan = plan.resolve()
    if not plan.is_file():
        return fail(f"plan does not exist: {plan}")
    if root not in plan.parents:
        return fail(f"plan must be inside {root}: {plan}")
    candidate = plan_id or plan.stem
    if not PLAN_ID_PATTERN.fullmatch(candidate):
        return fail(
            f"plan_id must use kebab-case (lowercase letters, digits, hyphens): {candidate}; "
            "rename the plan file or pass --plan-id"
        )

    existing, _ = load_state(state_file(root))
    if existing is not None:
        stage = existing.get("workflow_stage")
        if stage in TERMINAL_STAGES:
            return fail(f"terminal plan not archived yet (workflow_stage={stage}); run archive first")
        return fail(f"active plan already exists (workflow_stage={stage}); archive it before starting a new plan")

    state = {
        "plan_id": candidate,
        "plan_path": str(plan),
        "workflow_stage": "planning",
        "codex_review_status": "pending",
        "codex_review_note": "",
        "updated_at": now(),
    }
    return _write_state(root, state, "started planning state")


def set_fields(root: Path, fields: list[str]) -> int:
    state, error = load_state(state_file(root))
    if state is None:
        return fail(f"no active plan state: {error}")

    updates: dict[str, Any] = {}
    for item in fields:
        if "=" not in item:
            return fail(f"field must use KEY=VALUE: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if key in INT_FIELDS:
            try:
                updates[key] = int(value)
            except ValueError:
                return fail(f"{key} must be an integer: {value}")
        elif key in STR_FIELDS:
            updates[key] = value
        else:
            allowed = ", ".join(sorted(INT_FIELDS | STR_FIELDS))
            return fail(f"unsupported field: {key}; allowed fields: {allowed}")

    if not updates:
        return fail("no --field given")

    merged = {**state, **updates, "updated_at": now()}
    return _write_state(root, merged, "updated phase state")


def validate(root: Path) -> int:
    state, error = load_state(state_file(root))
    if state is None:
        if error == "not found":
            print("BLOCKED: .claude/phase_state.json not found")
        else:
            print(f"BLOCKED: {error}")
        return 2
    code, lines = gate(state)
    for line in lines:
        print(line)
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "set", "validate", "archive"))
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd())))
    parser.add_argument("--plan", type=Path, help="start: 计划文件路径")
    parser.add_argument("--plan-id", help="start: 覆盖由文件名推导的 plan_id")
    parser.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="set: 要写入的状态字段，可重复",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    if args.command in {"start", "set", "archive"}:
        cwd = Path.cwd().resolve()
        if cwd != root and root not in cwd.parents:
            # 防止在临时目录里跑命令却写进 CLAUDE_PROJECT_DIR 指向的真实仓库。
            print(f"WARN: 当前目录 {cwd} 不在 --root {root} 内，确认目标项目是否正确", file=sys.stderr)

    if args.command == "start":
        if args.plan is None:
            parser.error("start requires --plan")
        return start(root, args.plan, args.plan_id)
    if args.command == "set":
        if not args.field:
            parser.error("set requires at least one --field")
        return set_fields(root, args.field)
    if args.command == "validate":
        return validate(root)
    return archive(root)


if __name__ == "__main__":
    sys.exit(main())
