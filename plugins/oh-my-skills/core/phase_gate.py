"""CLI wrapper for provider-neutral phase gate evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .phase_state import gate, load, state_file
except ImportError:  # direct execution: python core/phase_gate.py
    from phase_state import gate, load, state_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--state-dir")
    args = parser.parse_args()
    state, error = load(state_file(args.root.resolve(), args.state_dir))
    if state is None:
        print(f"BLOCKED: {error}")
        return 2
    code, lines = gate(state)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
