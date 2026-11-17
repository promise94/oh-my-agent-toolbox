import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def read_frontmatter(path: Path) -> tuple[dict[str, str], int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"missing frontmatter: {path}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise AssertionError(f"unterminated frontmatter: {path}") from exc
    values: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip('"')
    return values, len(lines)


class SkillFrontmatterTests(unittest.TestCase):
    def test_every_skill_has_valid_identity_and_size(self):
        skill_paths = sorted(SKILLS.glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skill_paths), 4)
        for path in skill_paths:
            with self.subTest(path=path):
                metadata, line_count = read_frontmatter(path)
                skill_id = path.parent.name
                self.assertEqual(metadata.get("name"), skill_id)
                self.assertTrue(metadata.get("description"), skill_id)
                self.assertRegex(skill_id, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
                self.assertLess(line_count, 500)

    def test_relative_markdown_references_exist(self):
        link_pattern = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)")
        for path in sorted(SKILLS.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            for target in link_pattern.findall(text):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                with self.subTest(path=path, target=target):
                    self.assertTrue((path.parent / target).resolve().is_file(), target)

    def test_plan_standard_core_has_no_host_commands(self):
        files = [
            SKILLS / "planning-workflow" / "SKILL.md",
            SKILLS / "planning-workflow" / "small-plan.md",
            SKILLS / "planning-workflow" / "large-plan.md",
        ]
        forbidden = ("AskUserQuestion", "EnterPlanMode", "ExitPlanMode", "CLAUDE_PROJECT_DIR", "/codex:rescue", "~/.claude")
        for path in files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                with self.subTest(path=path, token=token):
                    self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
