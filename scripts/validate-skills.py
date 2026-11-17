#!/usr/bin/env python3
"""Validate canonical Skills, registry membership, and adapter boundaries."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "oh-my-skills"
SECRET_KEY = re.compile(r"(api[_-]?key|token|password|secret|private[_-]?key)", re.I)
PLACEHOLDER = re.compile(r"^(set-|your-|replace-|example|<|\$)", re.I)
SECRET_ASSIGNMENT = re.compile(r"\b(api[_-]?key|token|password|secret|private[_-]?key)\b\s*[:=]\s*[\"']?([^\s\"'`,}]+)", re.I)
ABSOLUTE_TEXT_PATH = re.compile(r"(?<![A-Za-z0-9])/(?:Users|home|tmp|var|private|opt|etc)/[^\s\"'`)>]+")


def skill_ids(plugin: Path) -> set[str]:
    return {path.parent.name for path in (plugin / "skills").glob("*/SKILL.md")}


def frontmatter(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---": return values
    for line in lines[1:]:
        if line.strip() == "---": break
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line.strip())
        if m: values[m.group(1)] = m.group(2).strip().strip("\"\'")
    return values

def frontmatter_name(path: Path) -> str | None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^name:\s*([a-z0-9-]+)\s*$", line.strip())
        if match:
            return match.group(1)
    return None


def parse_jsonc(path: Path) -> object:
    source = path.read_text(encoding="utf-8")
    output: list[str] = []
    in_string = False
    escaped = False
    index = 0
    while index < len(source):
        char = source[index]
        if char == '"' and not escaped:
            in_string = not in_string
        if not in_string and char == "/" and index + 1 < len(source) and source[index + 1] == "/":
            newline = source.find("\n", index)
            if newline == -1:
                break
            output.append("\n")
            index = newline + 1
            escaped = False
            continue
        output.append(char)
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
        index += 1
    text = "".join(output)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return json.loads(text)


def inspect_value(value: object, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if SECRET_KEY.search(str(key)) and isinstance(child, str) and child and not PLACEHOLDER.search(child):
                errors.append(f"credential-like value at {child_path}")
            inspect_value(child, child_path, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            inspect_value(child, f"{path}[{index}]", errors)
    elif isinstance(value, str) and value.startswith("/") and not value.startswith(("http://", "https://")):
        errors.append(f"absolute path at {path}")


def inspect_text(text: str, path: str, errors: list[str]) -> None:
    for match in SECRET_ASSIGNMENT.finditer(text):
        value = match.group(2).rstrip(".;")
        if value and not PLACEHOLDER.search(value):
            errors.append(f"credential-like value at {path}")
    for match in ABSOLUTE_TEXT_PATH.finditer(text):
        value = match.group(0).rstrip(".,;:)")
        if not value.startswith(("/http://", "/https://")):
            errors.append(f"absolute path at {path}")


def validate(check_jsonc: bool = False, check_mcp: bool = False, opencode: Path | None = None, root: Path | None = None, registry_override: Path | None = None, check_aliases: bool = False) -> list[str]:
    errors: list[str] = []
    scan_root = (root or ROOT).resolve()
    plugin = scan_root / "plugins" / "oh-my-skills"
    ids = skill_ids(plugin)
    registry_path = (registry_override or (plugin / "skills/skill-registry.json")).resolve()
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"registry: {exc}"]
    entries = registry.get("skills", [])
    registry_ids = [entry.get("id") for entry in entries if isinstance(entry, dict)]
    canonical_ids = set(registry_ids)
    if len(registry_ids) != len(canonical_ids): errors.append("registry contains duplicate skill ids")
    if canonical_ids != ids:
        errors.append(f"registry ids do not match skills: registry={sorted(canonical_ids)} skills={sorted(ids)}")
    for path in sorted((plugin / "skills").glob("*/SKILL.md")):
        fm=frontmatter(path)
        if fm.get("name") != path.parent.name: errors.append(f"frontmatter name does not match directory: {path}")
        if "alias_for" in fm: errors.append(f"aliases are not supported: {path}")
    for adapter in (plugin / "adapters").glob("*"):
        if adapter.is_dir():
            for path in adapter.rglob("*"):
                if path.is_symlink():
                    errors.append(f"symlink is not allowed in adapter publish tree: {path}")
                if path.is_file() and path.suffix in {".md", ".json", ".jsonc", ".py", ".sh"}:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    inspect_text(text, str(path.relative_to(ROOT)), errors)
                    if adapter.name != "claude" and "CLAUDE_PROJECT_DIR" in text:
                        errors.append(f"Claude runtime token in non-Claude adapter: {path}")
                    if any(token in str(path) for token in (".claude/phase_state.json", ".claude/temp", "plan-history")):
                        errors.append(f"runtime state in adapter publish tree: {path}")
            if adapter.name != "claude":
                for path in adapter.rglob("*"):
                    if path.is_file() and path.suffix in {".json", ".jsonc"}:
                        try:
                            inspect_value(parse_jsonc(path), str(path.relative_to(ROOT)), errors)
                        except (OSError, json.JSONDecodeError) as exc:
                            errors.append(f"invalid JSON/JSONC {path}: {exc}")
    if check_jsonc:
        config = plugin / "adapters/opencode/opencode.jsonc"
        try:
            parse_jsonc(config)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid OpenCode JSONC: {exc}")
    if check_mcp:
        for path in (plugin / "config-templates").glob("*.json"):
            try:
                inspect_value(json.loads(path.read_text(encoding="utf-8")), str(path.relative_to(ROOT)), errors)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid config template {path}: {exc}")
        mcp = plugin / "adapters/chatgpt/mcp.json"
        try:
            inspect_value(json.loads(mcp.read_text(encoding="utf-8")), str(mcp.relative_to(ROOT)), errors)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid ChatGPT MCP: {exc}")
    if opencode:
        try:
            parse_jsonc(opencode)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid OpenCode config {opencode}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-jsonc", action="store_true")
    parser.add_argument("--check-mcp", action="store_true")
    parser.add_argument("--check-opencode")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--check-aliases", action="store_true")
    args = parser.parse_args()
    errors = validate(args.check_jsonc, args.check_mcp, Path(args.check_opencode) if args.check_opencode else None, args.root, args.registry, args.check_aliases)
    if errors:
        for error in errors:
            print(f"BLOCKED: {error}")
        return 2
    print("PASS: Skills, registry, and adapter boundaries are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
