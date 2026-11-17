#!/usr/bin/env python3
"""Validate marketplace configuration templates without exposing credentials."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SECRET_KEY = re.compile(r"(api[_-]?key|token|password|secret|private[_-]?key)", re.I)
PLACEHOLDER = re.compile(r"^(set-|your-|replace-|example|<|\$)", re.I)


def inspect(value: object, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if SECRET_KEY.search(key) and isinstance(child, str) and child and not PLACEHOLDER.search(child):
                errors.append(f"credential-like value at {child_path}")
            errors.extend(inspect(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(inspect(child, f"{path}[{index}]"))
    elif isinstance(value, str) and value.startswith("/"):
        errors.append(f"absolute path at {path}")
    return errors


def validate(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {path}: {exc}")
        return 2
    errors = inspect(data)
    if errors:
        for error in errors:
            print(f"BLOCKED: {path}: {error}")
        return 2
    print(f"PASS: {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    return max(validate(path) for path in args.paths)


if __name__ == "__main__":
    sys.exit(main())
