#!/usr/bin/env python3
"""Archive the terminal plan state and release the active plan pointer."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


TERMINAL_STAGES = {"completed", "cancelled", "abandoned"}
PLAN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def fail(message: str) -> int:
    print(f"ERROR: {message}")
    return 2


def archive(root: Path) -> int:
    state_path = root / ".codex" / "phase_state.json"
    if not state_path.is_file():
        print("PASS: no active plan state to archive")
        return 0

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"invalid phase state: {exc}")
    if not isinstance(state, dict):
        return fail("phase state must be a JSON object")

    plan_id = state.get("plan_id")
    stage = state.get("workflow_stage")
    if not isinstance(plan_id, str) or not plan_id.strip():
        return fail("plan_id is missing")
    if not PLAN_ID_PATTERN.fullmatch(plan_id):
        return fail("plan_id must use kebab-case and contain only lowercase letters, digits, and hyphens")
    if stage not in TERMINAL_STAGES:
        return fail(f"only terminal plans can be archived (workflow_stage={stage})")
    if stage == "completed":
        if state.get("phase_status") != "PASS":
            return fail("completed plan must have phase_status=PASS")
        if state.get("audit_status") not in {"completed", "waived"}:
            return fail("completed plan must have audit_status=completed or waived")
    elif not state.get("terminal_at") or not state.get("terminal_reason"):
        return fail(f"{stage} plan must have terminal_at and terminal_reason")
    if not state.get("terminal_at"):
        state["terminal_at"] = datetime.now(timezone.utc).isoformat()

    history_dir = root / ".codex" / "plan-history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = history_dir / f"{plan_id}.json"
    if history_path.exists():
        return fail(f"archive already exists: {history_path}")

    try:
        history_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        state_path.unlink()
    except OSError as exc:
        if history_path.exists():
            history_path.unlink()
        return fail(f"could not release active plan state: {exc}")

    print(f"PASS: archived {plan_id} to {history_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("archive",))
    args = parser.parse_args()
    if args.command == "archive":
        return archive(Path.cwd())
    return 2


if __name__ == "__main__":
    sys.exit(main())
