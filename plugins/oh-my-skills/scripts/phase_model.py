#!/usr/bin/env python3
"""Compatibility facade for the provider-neutral phase state module."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from core.phase_state import (  # noqa: E402
    DISPOSED,
    DISPOSITIONS,
    PHASE_STATUSES,
    STAGES,
    gate,
    load,
    state_file,
)

DISPOSED_STATUSES = DISPOSED
DISPOSITION_STATUSES = DISPOSITIONS
TERMINAL_STAGES = {"completed", "cancelled", "abandoned"}


def project_root(override: Path | None = None) -> Path:
    if override is not None:
        return override.resolve()
    raw = os.environ.get("PLAN_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(raw).resolve() if raw else Path.cwd().resolve()


def state_dir(root: Path) -> Path:
    return state_file(root.resolve()).parent


load_state = load
