import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
SCRIPTS = ROOT / "scripts"

SCRIPT_FLAGS = {
    "prepare-review.py": ["--root", "--plan", "--request", "--context"],
    "prepare-audit.py": [
        "--root",
        "--plan",
        "--request",
        "--summary",
        "--validation",
        "--baseline",
        "--timeout-seconds",
    ],
}

DOCS = {
    "prepare-review.py": SKILLS / "codex-plan-review" / "SKILL.md",
    "prepare-audit.py": SKILLS / "codex-plan-audit" / "SKILL.md",
}


def run_help(script: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), "--help"], text=True, capture_output=True)


class SkillScriptContractTests(unittest.TestCase):
    """SKILL.md 里写出来的命令必须和脚本真实 CLI 一致。"""

    def test_documented_flags_match_script_cli(self):
        for name, flags in SCRIPT_FLAGS.items():
            with self.subTest(script=name):
                result = run_help(SCRIPTS / name)
                self.assertEqual(result.returncode, 0, result.stderr)
                document = DOCS[name].read_text(encoding="utf-8")
                for flag in flags:
                    self.assertIn(flag, result.stdout, f"{name} CLI 缺少文档中提到的 {flag}")
                    self.assertIn(flag, document, f"{DOCS[name].name} 未写明 {flag}")

    def test_documented_commands_point_at_existing_scripts(self):
        for name in SCRIPT_FLAGS:
            with self.subTest(script=name):
                self.assertTrue((SCRIPTS / name).is_file(), name)
                self.assertIn(f"scripts/{name}", DOCS[name].read_text(encoding="utf-8"))

    def test_entry_scripts_expose_help(self):
        for name in ("prepare-review.py", "prepare-audit.py", "bootstrap.py", "phase-state.py"):
            with self.subTest(script=name):
                result = run_help(SCRIPTS / name)
                self.assertEqual(result.returncode, 0, f"{name}: {result.stderr}")
                self.assertIn("usage", result.stdout)

    def test_request_templates_have_no_runtime_placeholders(self):
        for name in SCRIPT_FLAGS:
            with self.subTest(script=name):
                source = (SCRIPTS / name).read_text(encoding="utf-8")
                self.assertNotIn("CLAUDE_PLUGIN_ROOT", source)
                self.assertNotIn("plugins/oh-my-skills", source)

    def test_reference_documents_exist(self):
        references = SKILLS / "plan-standard" / "references"
        for name in ("review-subagent-prompt.md", "audit-subagent-prompt.md"):
            with self.subTest(reference=name):
                self.assertTrue((references / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
