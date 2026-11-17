#!/usr/bin/env python3
"""Compatibility facade for the Claude adapter bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from adapters.claude.bootstrap import main as adapter_main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(adapter_main())
