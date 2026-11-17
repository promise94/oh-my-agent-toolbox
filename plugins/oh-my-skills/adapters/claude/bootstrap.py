#!/usr/bin/env python3
"""Install or remove the Claude project adapter without overwriting user settings."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any


HOOK_COMMAND = 'bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/phase-gate.sh'
PLUGIN_ROOT = Path(__file__).resolve().parents[2]
HOOK_SOURCE = Path(__file__).resolve().parent / "hooks" / "phase-gate.sh"
RULE_SOURCE = PLUGIN_ROOT / "rules" / "plan-mode.md"
RULE_START = "<!-- oh-my-agent-toolbox:plan-rules:start -->"
RULE_END = "<!-- oh-my-agent-toolbox:plan-rules:end -->"
RULES_BLOCK = f"""{RULE_START}
## 计划流程硬约束（由 oh-my-agent-toolbox 维护）

- 状态只经 `phase-state.py start|set|validate|archive` 写入，禁止手改状态文件。
- 没有真实独立评审报告只能记 `blocked`；只有用户明确同意跳过才能记 `waived`。
- 阶段未 PASS 不得前进；`completed` 需 `phase_status=PASS` 且 `audit_status=completed|waived`。
- 一个工作树只有一个活动计划，开始新计划前先归档终态计划。
- 完整规则见 `.claude/rules/plan-mode.md`。
{RULE_END}
"""


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


def load_settings(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("settings JSON must be an object")
    return value


def choose_settings(root: Path) -> Path:
    local = root / ".claude" / "settings.local.json"
    shared = root / ".claude" / "settings.json"
    if local.exists() or not shared.exists():
        return local
    return shared


def stop_entries(settings: dict[str, Any]) -> list[dict[str, Any]]:
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("settings.hooks must be an object")
    stop = hooks.setdefault("Stop", [])
    if not isinstance(stop, list):
        raise ValueError("settings.hooks.Stop must be an array")
    return stop


def snapshot(paths: list[Path]) -> dict[Path, tuple[bool, bytes, int]]:
    result: dict[Path, tuple[bool, bytes, int]] = {}
    for path in paths:
        if path.is_file():
            result[path] = (True, path.read_bytes(), path.stat().st_mode)
        else:
            result[path] = (False, b"", 0)
    return result


def restore(state: dict[Path, tuple[bool, bytes, int]]) -> None:
    for path, (exists, content, mode) in state.items():
        if exists:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            path.chmod(mode)
        elif path.exists():
            path.unlink()


def install(root: Path, with_rules: bool) -> None:
    settings_path = choose_settings(root)
    hook_destination = root / ".claude/hooks/phase-gate.sh"
    rule_destination = root / ".claude/rules/plan-mode.md"
    claude_md = root / "CLAUDE.md"
    before = snapshot([settings_path, hook_destination, rule_destination, claude_md])
    try:
        settings = load_settings(settings_path)
        stop = stop_entries(settings)
        exact = False
        for entry in stop:
            if not isinstance(entry, dict):
                continue
            for hook in entry.get("hooks", []):
                command = hook.get("command") if isinstance(hook, dict) else None
                if command == HOOK_COMMAND:
                    exact = True
                elif isinstance(command, str) and "phase-gate.sh" in command:
                    raise ValueError("conflicting phase-gate Stop hook already exists")
        if not exact:
            stop.append({"matcher": "", "hooks": [{"type": "command", "command": HOOK_COMMAND}]})
        hook_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HOOK_SOURCE, hook_destination)
        hook_destination.chmod(hook_destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        if with_rules:
            rule_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(RULE_SOURCE, rule_destination)
            text = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""
            if RULE_START in text and RULE_END in text:
                head = text.split(RULE_START, 1)[0].rstrip()
                tail = text.split(RULE_END, 1)[1].lstrip("\n")
                text = (head + "\n\n" if head else "") + RULES_BLOCK + ("\n" + tail if tail else "")
            else:
                text = (text.rstrip() + "\n\n" if text.strip() else "") + RULES_BLOCK
            atomic_write(claude_md, text)
        atomic_write(settings_path, json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
    except Exception:
        restore(before)
        raise


def uninstall(root: Path) -> None:
    settings_path = choose_settings(root)
    if settings_path.exists():
        settings = load_settings(settings_path)
        stop = stop_entries(settings)
        kept = []
        for entry in stop:
            if not isinstance(entry, dict):
                kept.append(entry)
                continue
            hooks = [hook for hook in entry.get("hooks", []) if not (isinstance(hook, dict) and hook.get("command") == HOOK_COMMAND)]
            if hooks:
                entry = {**entry, "hooks": hooks}
                kept.append(entry)
        settings.setdefault("hooks", {})["Stop"] = kept
        atomic_write(settings_path, json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
    for path in (root / ".claude/hooks/phase-gate.sh", root / ".claude/rules/plan-mode.md"):
        if path.is_file():
            path.unlink()
    claude_md = root / "CLAUDE.md"
    if claude_md.is_file():
        text = claude_md.read_text(encoding="utf-8")
        if RULE_START in text and RULE_END in text:
            head = text.split(RULE_START, 1)[0].rstrip()
            tail = text.split(RULE_END, 1)[1].lstrip("\n")
            atomic_write(claude_md, (head + "\n\n" if head else "") + (tail if tail else ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd())))
    parser.add_argument("--with-rules", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        uninstall(root) if args.uninstall else install(root, args.with_rules)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}")
        return 2
    print(f"PASS: {'uninstalled' if args.uninstall else 'installed'} Claude adapter for {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
