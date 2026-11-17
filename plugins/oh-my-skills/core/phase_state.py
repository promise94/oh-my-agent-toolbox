"""Provider-neutral state loading, normalization, and gate evaluation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

STAGES = {"planning", "execution", "completed", "cancelled", "abandoned"}
DISPOSITIONS = {"pending", "needs_input", "blocked", "waived", "completed"}
DISPOSED = {"completed", "waived"}
PHASE_STATUSES = {"in_progress", "PASS", "FAIL", "DEVIATION", "BLOCKED"}


def state_file(root: Path, state_dir: str | None = None) -> Path:
    raw = Path(state_dir or os.environ.get("PLAN_STATE_DIR", ".plans"))
    return (raw if raw.is_absolute() else root / raw) / "phase_state.json"


def normalize_state(state: dict[str, Any]) -> dict[str, Any]:
    """Add v2 fields while preserving legacy fields and unknown metadata."""
    normalized = dict(state)
    normalized.setdefault("schema_version", 2)
    if "review_status" not in normalized:
        normalized["review_status"] = normalized.get("codex_review_status", "pending")
    if "review_note" not in normalized:
        normalized["review_note"] = normalized.get("codex_review_note", "")
    normalized.setdefault("review_provider", "codex" if "codex_review_status" in state else "none")
    normalized.setdefault("audit_provider", "none")
    normalized.setdefault("audit_status", "pending")
    normalized.setdefault("codex_review_status", normalized["review_status"])
    normalized.setdefault("codex_review_note", normalized["review_note"])
    return normalized


def load(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "not found"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid phase state: {exc}"
    if not isinstance(value, dict):
        return None, "phase state must be a JSON object"
    return normalize_state(value), None


def gate(state: dict[str, Any]) -> tuple[int, list[str]]:
    state = normalize_state(state)
    stage = state.get("workflow_stage", "unknown")
    phase = state.get("current_phase", "-")
    phase_name = state.get("phase_name", "-")
    phase_status = state.get("phase_status", "-")
    review = state.get("review_status")
    lines = [
        f"Plan: {state.get('plan_path', '(missing)')}",
        f"Stage: {stage} | Phase: {phase} ({phase_name}) | Status: {phase_status}",
        f"Review: {state.get('review_status')} | Audit: {state.get('audit_status')}",
    ]
    if not state.get("plan_id") or not isinstance(state.get("plan_path"), str) or not state.get("plan_path"):
        return 2, lines + ["BLOCKED: plan_path does not point to an existing plan"]
    if not Path(state["plan_path"]).is_file():
        return 2, lines + ["BLOCKED: plan_path does not point to an existing plan"]
    if state.get("review_status") != state.get("codex_review_status"):
        return 2, lines + ["BLOCKED: review_status and codex_review_status must match"]
    if stage not in STAGES:
        return 2, lines + ["BLOCKED: unknown workflow stage"]
    if stage == "planning":
        if review not in DISPOSITIONS:
            return 2, lines + [f"BLOCKED: invalid review_status ({review})"]
        return 1, lines + [f"BLOCKED: planning requires independent review or waiver (review_status={review})"]
    if stage in {"cancelled", "abandoned"}:
        if not state.get("terminal_at") or not state.get("terminal_reason"):
            return 2, lines + [f"BLOCKED: {stage} plan must have terminal_at and terminal_reason"]
        return 0, lines + [f"PASS: plan is terminal ({stage}); archive before starting another plan"]
    if review not in DISPOSED:
        return 2, lines + ["BLOCKED: execution requires review_status=completed or waived (legacy codex_review_status)"]
    if stage == "completed":
        if not state.get("terminal_at") or not state.get("terminal_reason"):
            return 2, lines + ["BLOCKED: completed plan must have terminal_at and terminal_reason"]
        audit_status = state.get("audit_status")
        if phase_status != "PASS" or not isinstance(audit_status, str) or audit_status not in DISPOSED:
            return 2, lines + [f"BLOCKED: completed plan requires phase_status=PASS and audit_status=completed or waived (audit_status={audit_status})"]
        return 0, lines + ["PASS: plan completed; archive before starting another plan"]
    if not isinstance(phase, int) or phase < 1 or not phase_name:
        return 2, lines + [f"BLOCKED: current_phase/phase_name is missing or invalid (current_phase={phase})"]
    if not isinstance(phase_status, str) or phase_status not in PHASE_STATUSES:
        return 2, lines + [f"BLOCKED: invalid phase_status ({phase_status})"]
    audit_status = state.get("audit_status")
    if not isinstance(audit_status, str) or audit_status not in DISPOSITIONS:
        return 2, lines + [f"BLOCKED: invalid audit_status ({audit_status})"]
    if phase_status == "PASS":
        return 0, lines + ["PASS: current phase passed"]
    return 1, lines + [f"BLOCKED: current phase requires resolution ({phase_status})"]
