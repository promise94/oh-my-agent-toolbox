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

RULES_MARKER_START = "<!-- oh-my-agent-toolbox:plan-rules:start -->"
RULES_MARKER_END = "<!-- oh-my-agent-toolbox:plan-rules:end -->"
RULES_BLOCK = f"""{RULES_MARKER_START}
## 计划流程硬约束（由 oh-my-agent-toolbox 维护）

- 状态只经 `phase-state.py start|set|validate|archive` 写入，禁止手改 `.claude/phase_state.json`。
- 没有真实 Codex 报告只能记 `blocked`；只有用户明确同意跳过才能记 `waived`。
- 阶段未 PASS 不得前进；`completed` 需 `phase_status=PASS` 且 `audit_status=completed|waived`。
- 一个工作树只有一个活动计划，开始新计划前先归档终态计划。
- 完整规则见 `.claude/rules/plan-mode.md`。
{RULES_MARKER_END}
"""


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


def install_rules(root: Path, source: Path) -> tuple[Path, Path, bool]:
    """复制规则文件，并把带标记的约束块幂等写入项目 CLAUDE.md。"""
    if not source.is_file():
        raise ValueError(f"rules source does not exist: {source}")
    destination = root / ".claude" / "rules" / "plan-mode.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or destination.read_bytes() != source.read_bytes():
        shutil.copyfile(source, destination)

    claude_md = root / "CLAUDE.md"
    text = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""
    if RULES_MARKER_START in text and RULES_MARKER_END in text:
        head = text.split(RULES_MARKER_START, 1)[0].rstrip()
        tail = text.split(RULES_MARKER_END, 1)[1].lstrip("\n")
        updated = (head + "\n\n" if head else "") + RULES_BLOCK + ("\n" + tail if tail else "")
    else:
        updated = (text.rstrip() + "\n\n" if text.strip() else "") + RULES_BLOCK
    changed = updated != text
    if changed:
        atomic_write(claude_md, updated)
    return destination, claude_md, changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd())))
    parser.add_argument(
        "--with-rules",
        action="store_true",
        help="同时把 rules/plan-mode.md 安装到 .claude/rules/ 并写入项目 CLAUDE.md 的约束块",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    plugin_root = Path(__file__).resolve().parents[1]
    source = plugin_root / "hooks" / "phase-gate.sh"
    settings_path = choose_settings(root)
    try:
        settings = load_settings(settings_path)
        changed = merge_settings(settings)
        destination = install_hook(root, source)
        if changed or not settings_path.exists():
            atomic_write(settings_path, json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
        rules = None
        if args.with_rules:
            rules = install_rules(root, plugin_root / "rules" / "plan-mode.md")
    except (OSError, ValueError) as exc:
        return fail(str(exc))
    print(f"PASS: installed phase gate at {destination}")
    print(f"PASS: {'updated' if changed else 'kept'} Stop hook in {settings_path}")
    if rules is not None:
        rules_file, claude_md, rules_changed = rules
        print(f"PASS: installed plan rules at {rules_file}")
        print(f"PASS: {'updated' if rules_changed else 'kept'} rules block in {claude_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
