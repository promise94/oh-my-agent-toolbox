"""Provider-neutral plan lifecycle, install, and diagnostic CLI."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .phase_state import DISPOSED, STAGES, gate, load, normalize_state, state_file
except ImportError:  # direct execution: python core/toolbox.py
    from phase_state import DISPOSED, STAGES, gate, load, normalize_state, state_file

PLAN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def dump(state: dict[str, Any]) -> str:
    return json.dumps(state, ensure_ascii=False, indent=2) + "\n"


def write_state(path: Path, state: dict[str, Any], action: str) -> int:
    state = normalize_state({**state, "updated_at": now()})
    code, lines = gate(state)
    if code == 2:
        print("ERROR: 拒绝写入：状态不合法")
        print("\n".join(lines[2:]))
        return 2
    atomic_write(path, dump(state))
    print(f"PASS: {action} -> {path}")
    print(f"  stage={state.get('workflow_stage')} phase={state.get('current_phase', '-')} phase_status={state.get('phase_status', '-')} review={state.get('review_status', '-')} audit={state.get('audit_status', '-')}")
    return 0


def resolve_state_path(root: Path, state_dir: str | None) -> Path:
    return state_file(root.resolve(), state_dir)


def start_plan(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    plan = args.plan.resolve()
    if not plan.is_file():
        print(f"ERROR: plan does not exist: {plan}")
        return 2
    if root not in plan.parents:
        print(f"ERROR: plan must be inside {root}: {plan}")
        return 2
    plan_id = args.plan_id or plan.stem
    if not PLAN_ID_PATTERN.fullmatch(plan_id):
        print(f"ERROR: plan_id must use kebab-case: {plan_id}")
        return 2
    path = resolve_state_path(root, args.state_dir)
    existing, _ = load(path)
    if existing is not None:
        if existing.get("workflow_stage") in {"completed", "cancelled", "abandoned"}:
            print("ERROR: terminal plan not archived yet; run archive first")
            return 2
        print(f"ERROR: active plan already exists: {existing.get('plan_id')}")
        return 2
    state = {
        "schema_version": 2,
        "plan_id": plan_id,
        "plan_path": str(plan),
        "workflow_stage": "planning",
        "review_status": "pending",
        "review_provider": "none",
        "review_note": "",
        "codex_review_status": "pending",
        "codex_review_note": "",
        "audit_status": "pending",
        "audit_provider": "none",
    }
    return write_state(path, state, "started planning state")


def set_plan(args: argparse.Namespace) -> int:
    path = resolve_state_path(args.root, args.state_dir)
    state, error = load(path)
    if state is None:
        print(f"ERROR: no active plan state: {error}")
        return 2
    updates: dict[str, Any] = {}
    for item in args.field:
        if "=" not in item:
            print(f"ERROR: field must use KEY=VALUE: {item}")
            return 2
        key, value = item.split("=", 1)
        if key in {"current_phase", "schema_version"}:
            try:
                updates[key] = int(value)
            except ValueError:
                print(f"ERROR: {key} must be an integer: {value}")
                return 2
        elif key in {"plan_id", "plan_path", "workflow_stage", "phase_name", "phase_status", "review_status", "review_provider", "review_note", "codex_review_status", "codex_review_note", "audit_status", "audit_provider", "terminal_at", "terminal_reason"}:
            updates[key] = value
        else:
            print(f"ERROR: unsupported field: {key}")
            return 2
    merged = {**state, **updates}
    if "review_status" in updates and "codex_review_status" not in updates: merged["codex_review_status"] = updates["review_status"]
    if "codex_review_status" in updates and "review_status" not in updates: merged["review_status"] = updates["codex_review_status"]
    return write_state(path, merged, "updated phase state")


def validate_plan(args: argparse.Namespace) -> int:
    path = resolve_state_path(args.root, args.state_dir)
    state, error = load(path)
    if state is None:
        print(f"BLOCKED: {error}")
        return 2
    code, lines = gate(state)
    print("\n".join(lines))
    return code


def transition_plan(args: argparse.Namespace) -> int:
    path = resolve_state_path(args.root, args.state_dir); state, error = load(path)
    if state is None: print(f"ERROR: no active plan state: {error}"); return 2
    if state.get("workflow_stage") != "execution" or state.get("current_phase") != args.from_phase or state.get("phase_status") != "PASS":
        print("ERROR: transition requires matching current phase with phase_status=PASS"); return 2
    if state.get("review_status") != state.get("codex_review_status"):
        print("ERROR: review fields must match"); return 2
    updated = {**state, "current_phase": args.to_phase, "phase_name": args.phase_name, "phase_status": "in_progress"}
    return write_state(path, updated, f"transitioned phase {args.from_phase} -> {args.to_phase}")

def complete_plan(args: argparse.Namespace) -> int:
    path = resolve_state_path(args.root, args.state_dir); state, error = load(path)
    if state is None: print(f"ERROR: no active plan state: {error}"); return 2
    if state.get("workflow_stage") != "execution" or state.get("phase_status") != "PASS" or state.get("review_status") not in DISPOSED or state.get("review_status") != state.get("codex_review_status"):
        print("ERROR: complete requires execution, PASS phase, disposed matching review fields"); return 2
    if args.audit_status not in DISPOSED or not args.audit_provider or not args.terminal_at or not args.terminal_reason:
        print("ERROR: complete requires audit disposition/provider and terminal fields"); return 2
    updated = {**state, "workflow_stage": "completed", "audit_status": args.audit_status, "audit_provider": args.audit_provider, "terminal_at": args.terminal_at, "terminal_reason": args.terminal_reason}
    return write_state(path, updated, "completed plan")

def archive_plan(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    path = resolve_state_path(root, args.state_dir)
    state, error = load(path)
    if state is None:
        print("PASS: no active plan state to archive" if error == "not found" else f"ERROR: {error}")
        return 0 if error == "not found" else 2
    stage = state.get("workflow_stage")
    if stage not in {"completed", "cancelled", "abandoned"}:
        print(f"ERROR: only terminal plans can be archived (workflow_stage={stage})")
        return 2
    if not isinstance(state.get("plan_id"), str) or not PLAN_ID_PATTERN.fullmatch(state.get("plan_id", "")):
        print("ERROR: plan_id must use kebab-case")
        return 2
    if not state.get("terminal_at") or not state.get("terminal_reason"):
        print(f"ERROR: {stage} plan must have terminal_at and terminal_reason")
        return 2
    if stage == "completed" and (state.get("phase_status") != "PASS" or state.get("review_status") not in DISPOSED or state.get("audit_status") not in DISPOSED):
        print(f"ERROR: completed plan requires PASS phase, review disposition, and audit_status disposition (audit_status={state.get('audit_status')})")
        return 2
    history = path.parent / "plan-history"
    target = history / f"{state['plan_id']}.json"
    index = 2
    while target.exists():
        target = history / f"{state['plan_id']}-{index}.json"
        index += 1
    atomic_write(target, dump(state))
    path.unlink()
    print(f"PASS: archived {state['plan_id']} to {target}")
    return 0


def install(args: argparse.Namespace) -> int:
    print(f"PASS: provider-neutral install is available for host={args.host}; use the host adapter for filesystem changes")
    return 0


def doctor(args: argparse.Namespace) -> int:
    print(f"host={args.host}")
    print("cli=available")
    print("state=available")
    print("gate=manual")
    print("review=provider-dependent")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="namespace", required=True)
    plan = subparsers.add_parser("plan")
    plan_sub = plan.add_subparsers(dest="command", required=True)
    common = {"root": ("--root",), "state_dir": ("--state-dir",)}
    start = plan_sub.add_parser("start")
    start.add_argument("--root", type=Path, default=Path.cwd()); start.add_argument("--state-dir"); start.add_argument("--plan", type=Path, required=True); start.add_argument("--plan-id")
    update = plan_sub.add_parser("set")
    update.add_argument("--root", type=Path, default=Path.cwd()); update.add_argument("--state-dir"); update.add_argument("--field", action="append", required=True)
    validate = plan_sub.add_parser("validate")
    validate.add_argument("--root", type=Path, default=Path.cwd()); validate.add_argument("--state-dir")
    transition = plan_sub.add_parser("transition"); transition.add_argument("--root", type=Path, default=Path.cwd()); transition.add_argument("--state-dir"); transition.add_argument("--from-phase", type=int, required=True); transition.add_argument("--to-phase", type=int, required=True); transition.add_argument("--phase-name", required=True)
    complete = plan_sub.add_parser("complete"); complete.add_argument("--root", type=Path, default=Path.cwd()); complete.add_argument("--state-dir"); complete.add_argument("--audit-status", required=True); complete.add_argument("--audit-provider", required=True); complete.add_argument("--terminal-at", required=True); complete.add_argument("--terminal-reason", required=True)
    archive = plan_sub.add_parser("archive")
    archive.add_argument("--root", type=Path, default=Path.cwd()); archive.add_argument("--state-dir")
    install_parser = subparsers.add_parser("install"); install_parser.add_argument("--host", required=True)
    doctor_parser = subparsers.add_parser("doctor"); doctor_parser.add_argument("--host", required=True)
    args = parser.parse_args()
    if args.namespace == "plan":
        return {"start": start_plan, "set": set_plan, "validate": validate_plan, "transition": transition_plan, "complete": complete_plan, "archive": archive_plan}[args.command](args)
    return install(args) if args.namespace == "install" else doctor(args)


if __name__ == "__main__":
    raise SystemExit(main())
