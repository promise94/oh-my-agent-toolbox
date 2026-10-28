#!/usr/bin/env python3
"""Check whether the active Claude plan may proceed."""

import os
import sys
from pathlib import Path

from phase_model import gate, load_state


def main() -> int:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd())).resolve()
    state, error = load_state(root / ".claude" / "phase_state.json")
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


if __name__ == "__main__":
    sys.exit(main())
