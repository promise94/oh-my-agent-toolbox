import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
REGISTRY = SKILLS / "skill-registry.json"


def frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"missing frontmatter: {path}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise AssertionError(f"unterminated frontmatter: {path}") from exc
    values: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip('"')
    return values


class SkillRegistryTests(unittest.TestCase):
    def test_registry_lists_each_skill_once(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        entries = registry["skills"]
        ids = [entry["id"] for entry in entries]
        discovered = sorted(path.parent.name for path in SKILLS.glob("*/SKILL.md"))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sorted(ids), discovered)

    def test_registry_metadata_matches_frontmatter(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        by_id = {entry["id"]: entry for entry in registry["skills"]}
        for skill_path in SKILLS.glob("*/SKILL.md"):
            skill_id = skill_path.parent.name
            metadata = frontmatter(skill_path)
            self.assertEqual(metadata.get("name"), skill_id)
            self.assertTrue(metadata.get("description"), skill_id)
            entry = by_id[skill_id]
            self.assertRegex(entry["version"], r"^\d+\.\d+\.\d+$")
            self.assertIsInstance(entry["hosts"], list)
            self.assertTrue(entry["hosts"], skill_id)
            self.assertIsInstance(entry["dependencies"], list)
            self.assertIsInstance(entry["allow_implicit_invocation"], bool)

    def test_portable_hosts_are_registry_owned(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        by_id = {entry["id"]: entry for entry in registry["skills"]}
        self.assertEqual(by_id["code-review"]["portable_hosts"], ["chatgpt", "codex", "opencode"])
        self.assertNotIn("portable_hosts", by_id["planning-workflow"])


if __name__ == "__main__":
    unittest.main()
