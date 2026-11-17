#!/usr/bin/env python3
"""Compatibility facade for the provider-neutral phase gate."""

from __future__ import annotations

import os
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from core.phase_gate import main as core_main  # noqa: E402


if "--state-dir" not in sys.argv:
    sys.argv.extend(["--state-dir", os.environ.get("PLAN_STATE_DIR", ".claude")])
raise SystemExit(core_main())
