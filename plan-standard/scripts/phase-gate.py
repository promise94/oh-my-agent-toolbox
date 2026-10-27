#!/usr/bin/env python3
"""Check whether the active Codex plan may proceed."""

import json
import sys
from pathlib import Path

REVIEW_STATUSES = {"pending", "needs_input", "blocked", "waived", "completed"}
AUDIT_STATUSES = {"pending", "needs_input", "blocked", "waived", "completed"}
PHASE_STATUSES = {"in_progress", "PASS", "FAIL", "DEVIATION", "BLOCKED"}
TERMINAL_STAGES = {"completed", "cancelled", "abandoned"}


def blocked(message: str, exit_code: int = 2) -> int:
    print(f"BLOCKED: {message}")
    return exit_code


def main() -> int:
    state_path = Path.cwd() / ".codex" / "phase_state.json"
    if not state_path.is_file():
        print("BLOCKED: .codex/phase_state.json not found")
        return 2

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: invalid phase state: {exc}")
        return 2
    if not isinstance(state, dict):
        print("BLOCKED: phase state must be a JSON object")
        return 2

    plan_id = state.get("plan_id", "")
    plan_path = state.get("plan_path", "")
    stage = state.get("workflow_stage", "unknown")
    phase = state.get("current_phase", "-")
    name = state.get("phase_name", "-")
    status = state.get("phase_status", "-")
    print(f"Plan: {plan_path or '(missing)'}")
    print(f"Stage: {stage} | Phase: {phase} ({name}) | Status: {status}")

    if not isinstance(plan_id, str) or not plan_id.strip():
        return blocked("plan_id is missing")
    if (
        not isinstance(plan_path, str)
        or not plan_path.strip()
        or not Path(plan_path).is_absolute()
        or not Path(plan_path).is_file()
    ):
        return blocked("plan_path does not point to an existing plan")
    if stage == "planning":
        review_status = state.get("review_status", "pending")
        if not isinstance(review_status, str) or review_status not in REVIEW_STATUSES:
            return blocked(f"invalid review_status ({review_status})")
        if review_status in {"completed", "waived"}:
            print(f"BLOCKED: user approval is still required (review_status={review_status})")
        else:
            print(f"BLOCKED: planning review is incomplete (review_status={review_status})")
        return 1
    if not isinstance(stage, str) or stage not in {"planning", "execution", *TERMINAL_STAGES}:
        return blocked("unknown workflow stage")

    if stage in {"cancelled", "abandoned"}:
        if not state.get("terminal_at") or not state.get("terminal_reason"):
            return blocked(f"{stage} plan must have terminal_at and terminal_reason")
        print(f"PASS: plan is terminal ({stage}); archive before starting another plan")
        return 0

    if not isinstance(phase, int) or isinstance(phase, bool) or phase < 1:
        return blocked("current_phase must be a positive integer")
    if not isinstance(name, str) or not name.strip():
        return blocked("phase_name is missing")
    if not isinstance(status, str) or status not in PHASE_STATUSES:
        return blocked(f"invalid phase_status ({status})")

    audit_status = state.get("audit_status")
    if not isinstance(audit_status, str) or audit_status not in AUDIT_STATUSES:
        return blocked(f"invalid audit_status ({audit_status})")

    if stage == "completed":
        if status != "PASS":
            return blocked("completed plan must have phase_status=PASS")
        if audit_status not in {"completed", "waived"}:
            return blocked("completed plan must have audit_status=completed or waived")
        print("PASS: plan completed; archive before starting another plan")
        return 0

    if status == "PASS":
        print("PASS: current phase passed")
        return 0
    if status in {"FAIL", "BLOCKED", "DEVIATION", "in_progress"}:
        print(f"BLOCKED: current phase requires resolution ({status})")
        return 1
    print("BLOCKED: current phase has not passed its gate")
    return 1


if __name__ == "__main__":
    sys.exit(main())
