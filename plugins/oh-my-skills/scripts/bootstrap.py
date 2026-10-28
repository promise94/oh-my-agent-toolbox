#!/usr/bin/env python3
"""Install the project-local Claude phase gate and Stop hook."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

HOOK_COMMAND = 'bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/phase-gate.sh'
STOP_ENTRY = {
    "matcher": "",
    "hooks": [{"type": "command", "command": HOOK_COMMAND}],
}


def fail(message: str) -> int:
    print(f"BLOCKED: {message}")
    return 2


def inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def choose_settings(root: Path) -> Path:
    local = root / ".claude" / "settings.local.json"
    shared = root / ".claude" / "settings.json"
    if local.exists() and os.access(local, os.W_OK):
        return local
    if shared.exists() and os.access(shared, os.W_OK):
        return shared
    return local


def load_settings(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid settings JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("settings JSON must be an object")
    return value


def has_stop_entry(stop: Any) -> bool:
    if not isinstance(stop, list):
        return False
    for entry in stop:
        if not isinstance(entry, dict):
            continue
        for hook in entry.get("hooks", []):
            if isinstance(hook, dict) and hook.get("command") == HOOK_COMMAND:
                return True
    return False


def merge_settings(settings: dict[str, Any]) -> bool:
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("settings.hooks must be an object")
    stop = hooks.setdefault("Stop", [])
    if not isinstance(stop, list):
        raise ValueError("settings.hooks.Stop must be an array")
    if has_stop_entry(stop):
        return False
    stop.append(json.loads(json.dumps(STOP_ENTRY)))
    return True


def atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install_hook(root: Path, source: Path) -> Path:
    if not source.is_file():
        raise ValueError(f"phase gate source does not exist: {source}")
    destination = root / ".claude" / "hooks" / "phase-gate.sh"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or destination.read_bytes() != source.read_bytes():
        shutil.copyfile(source, destination)
    destination.chmod(destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd())))
    args = parser.parse_args()
    root = args.root.resolve()
    source = Path(__file__).resolve().parents[1] / "hooks" / "phase-gate.sh"
    settings_path = choose_settings(root)
    try:
        settings = load_settings(settings_path)
        changed = merge_settings(settings)
        destination = install_hook(root, source)
        if changed or not settings_path.exists():
            atomic_write(settings_path, json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError) as exc:
        return fail(str(exc))
    print(f"PASS: installed phase gate at {destination}")
    print(f"PASS: {'updated' if changed else 'kept'} Stop hook in {settings_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
