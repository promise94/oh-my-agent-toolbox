#!/usr/bin/env python3
"""Compatibility facade for the provider-neutral plan CLI."""

from __future__ import annotations

import os
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from core.toolbox import main as core_main  # noqa: E402


if "--state-dir" not in sys.argv:
    sys.argv.extend(["--state-dir", os.environ.get("PLAN_STATE_DIR", ".claude")])
if len(sys.argv) > 1 and sys.argv[1] in {"start", "set", "validate", "archive"}:
    sys.argv.insert(1, "plan")
if "--root" in sys.argv:
    root_index = sys.argv.index("--root") + 1
    if root_index < len(sys.argv):
        from pathlib import Path as _Path
        if _Path.cwd().resolve() != _Path(sys.argv[root_index]).resolve() and _Path(sys.argv[root_index]).resolve() not in _Path.cwd().resolve().parents:
            print(f"WARN: 当前目录 {_Path.cwd().resolve()} 不在 --root {_Path(sys.argv[root_index]).resolve()} 内，确认目标项目是否正确", file=sys.stderr)
raise SystemExit(core_main())
