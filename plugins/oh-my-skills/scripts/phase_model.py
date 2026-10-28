#!/usr/bin/env python3
"""Shared schema, gate rules, and atomic writes for plan state files."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGES = {"planning", "execution", "completed", "cancelled", "abandoned"}
TERMINAL_STAGES = {"completed", "cancelled", "abandoned"}
DISPOSITION_STATUSES = {"pending", "needs_input", "blocked", "waived", "completed"}
DISPOSED_STATUSES = {"completed", "waived"}
PHASE_STATUSES = {"in_progress", "PASS", "FAIL", "DEVIATION", "BLOCKED"}

INT_FIELDS = {"current_phase"}
STR_FIELDS = {
    "plan_id",
    "plan_path",
    "workflow_stage",
    "phase_name",
    "phase_status",
    "codex_review_status",
    "codex_review_note",
    "audit_status",
    "terminal_at",
    "terminal_reason",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_state(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "not found"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid phase state: {exc}"
    if not isinstance(value, dict):
        return None, "phase state must be a JSON object"
    return value, None


def identity_error(state: dict[str, Any]) -> str | None:
    """结构错误：缺失或非法到无法继续判定的字段。"""
    plan_id = state.get("plan_id")
    plan_path = state.get("plan_path")
    stage = state.get("workflow_stage", "unknown")
    if not isinstance(plan_id, str) or not plan_id.strip():
        return "plan_id is missing"
    if (
        not isinstance(plan_path, str)
        or not plan_path.strip()
        or not Path(plan_path).is_absolute()
        or not Path(plan_path).is_file()
    ):
        return "plan_path does not point to an existing plan"
    if stage not in STAGES:
        return "unknown workflow stage"
    return None


def gate(state: dict[str, Any]) -> tuple[int, list[str]]:
    """返回 (退出码, 输出行)。0 允许继续，1 状态未满足，2 状态非法或缺失。"""
    plan_path = state.get("plan_path", "")
    stage = state.get("workflow_stage", "unknown")
    phase = state.get("current_phase", "-")
    name = state.get("phase_name", "-")
    phase_status = state.get("phase_status", "-")
    lines = [
        f"Plan: {plan_path or '(missing)'}",
        f"Stage: {stage} | Phase: {phase} ({name}) | Status: {phase_status}",
    ]

    error = identity_error(state)
    if error:
        lines.append(f"BLOCKED: {error}")
        return 2, lines

    if stage == "planning":
        review_status = state.get("codex_review_status", "pending")
        if review_status not in DISPOSITION_STATUSES:
            lines.append(f"BLOCKED: invalid codex_review_status ({review_status})")
            return 2, lines
        lines.append(
            f"BLOCKED: planning requires Codex review or waiver (codex_review_status={review_status})"
        )
        return 1, lines

    # 取消/放弃的计划可能发生在 review 之前，只需要终态字段，不要求 review/audit 完成。
    if stage in {"cancelled", "abandoned"}:
        if not state.get("terminal_at") or not state.get("terminal_reason"):
            lines.append(f"BLOCKED: {stage} plan must have terminal_at and terminal_reason")
            return 2, lines
        lines.append(f"PASS: plan is terminal ({stage}); archive before starting another plan")
        return 0, lines

    review_status = state.get("codex_review_status")
    if review_status not in DISPOSED_STATUSES:
        lines.append("BLOCKED: execution requires codex_review_status=completed or waived")
        return 2, lines

    if stage == "completed":
        if not state.get("terminal_at") or not state.get("terminal_reason"):
            lines.append("BLOCKED: completed plan must have terminal_at and terminal_reason")
            return 2, lines
        if phase_status != "PASS":
            lines.append("BLOCKED: completed plan must have phase_status=PASS")
            return 2, lines
        if state.get("audit_status") not in DISPOSED_STATUSES:
            lines.append("BLOCKED: completed plan must have audit_status=completed or waived")
            return 2, lines
        lines.append("PASS: plan completed; archive before starting another plan")
        return 0, lines

    if not isinstance(phase, int) or isinstance(phase, bool) or phase < 1:
        lines.append("BLOCKED: current_phase must be a positive integer")
        return 2, lines
    if not isinstance(name, str) or not name.strip():
        lines.append("BLOCKED: phase_name is missing")
        return 2, lines
    if phase_status not in PHASE_STATUSES:
        lines.append(f"BLOCKED: invalid phase_status ({phase_status})")
        return 2, lines
    audit_status = state.get("audit_status")
    if not isinstance(audit_status, str) or audit_status not in DISPOSITION_STATUSES:
        lines.append(f"BLOCKED: invalid audit_status ({audit_status})")
        return 2, lines

    if phase_status == "PASS":
        lines.append("PASS: current phase passed")
        return 0, lines
    lines.append(f"BLOCKED: current phase requires resolution ({phase_status})")
    return 1, lines
