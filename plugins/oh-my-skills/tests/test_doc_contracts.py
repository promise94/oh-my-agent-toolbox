import subprocess
import sys
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
SCRIPTS = ROOT / "scripts"

CODEX_SKILLS = ("plan-review", "plan-audit")
REGISTRY = SKILLS / "skill-registry.json"


def run_help(script: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), "--help"], text=True, capture_output=True)


class SkillScriptContractTests(unittest.TestCase):
    """入口脚本必须可执行，模板不得残留运行时占位符。"""

    def test_entry_scripts_expose_help(self):
        for name in ("prepare-review.py", "prepare-audit.py", "bootstrap.py", "phase-state.py", "phase-gate.py"):
            with self.subTest(script=name):
                result = run_help(SCRIPTS / name)
                self.assertEqual(result.returncode, 0, f"{name}: {result.stderr}")
                self.assertIn("usage", result.stdout)

    def test_request_templates_have_no_runtime_placeholders(self):
        for name in ("prepare-review.py", "prepare-audit.py"):
            with self.subTest(script=name):
                source = (SCRIPTS / name).read_text(encoding="utf-8")
                self.assertNotIn("CLAUDE_PLUGIN_ROOT", source)
                self.assertNotIn("plugins/oh-my-skills", source)

    def test_reference_documents_exist(self):
        references = SKILLS / "planning-workflow" / "references"
        for name in ("review-subagent-prompt.md", "audit-subagent-prompt.md"):
            with self.subTest(reference=name):
                self.assertTrue((references / name).is_file(), name)

    def test_registry_drives_all_skill_entries(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        discovered = sorted(path.parent.name for path in SKILLS.glob("*/SKILL.md"))
        self.assertEqual(sorted(entry["id"] for entry in registry["skills"]), discovered)
        for skill_id in discovered:
            with self.subTest(skill=skill_id):
                self.assertTrue((SKILLS / skill_id / "SKILL.md").is_file())

    def test_legacy_phase_model_is_not_a_second_state_machine(self):
        source = (SCRIPTS / "phase_model.py").read_text(encoding="utf-8")
        for symbol in ("def gate(", "def load_state(", "def atomic_write("):
            self.assertNotIn(symbol, source)


class CodexDelegationContractTests(unittest.TestCase):
    """Codex 委托必须经 /codex:rescue，由该 command 派 subagent，不在主上下文跑 companion。"""

    def test_delegates_through_rescue_command(self):
        for name in CODEX_SKILLS:
            with self.subTest(skill=name):
                text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("/codex:rescue", text)

    def test_main_agent_does_not_run_companion(self):
        for name in CODEX_SKILLS:
            with self.subTest(skill=name):
                text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
                # 主 agent 直接跑 companion 会被宿主转后台，导致 message 丢失和命令被中断。
                self.assertNotIn("codex-companion.mjs task", text)

    def test_reads_state_file(self):
        for name in CODEX_SKILLS:
            with self.subTest(skill=name):
                text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("phase_state.json", text)

    def test_offers_waiver_before_delegating(self):
        for name in CODEX_SKILLS:
            with self.subTest(skill=name):
                text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("waiver", text.lower())
                self.assertIn("AskUserQuestion", text)

    def test_review_skills_do_not_pin_model_names(self):
        skill_paths = [
            SKILLS / "code-review" / "SKILL.md",
            SKILLS / "plan-review" / "SKILL.md",
            SKILLS / "plan-audit" / "SKILL.md",
        ]
        forbidden = ("haiku", "sonnet", "gpt-5.4")
        for path in skill_paths:
            text = path.read_text(encoding="utf-8").lower()
            for model_name in forbidden:
                with self.subTest(skill=path.parent.name, model=model_name):
                    self.assertNotIn(model_name, text)


if __name__ == "__main__":
    unittest.main()
