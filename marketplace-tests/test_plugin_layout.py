import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "oh-my-skills"


class PluginLayoutTests(unittest.TestCase):
    def test_required_plugin_entries_exist(self):
        required = [
            PLUGIN / ".claude-plugin/plugin.json",
            PLUGIN / "skills/plan-standard/SKILL.md",
            PLUGIN / "skills/codex-plan-review/SKILL.md",
            PLUGIN / "skills/codex-plan-audit/SKILL.md",
            PLUGIN / "agents/plan-standard.md",
            PLUGIN / "hooks/phase-gate.sh",
            PLUGIN / "scripts/bootstrap.py",
            PLUGIN / "scripts/phase-gate.py",
            PLUGIN / "scripts/phase-state.py",
            PLUGIN / "scripts/phase_model.py",
            PLUGIN / "scripts/prepare-review.py",
            PLUGIN / "scripts/prepare-audit.py",
            PLUGIN / "config-templates/mcp.example.json",
            PLUGIN / "config-templates/settings.local.example.json",
        ]
        for path in required:
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), path)

    def test_plugin_ships_no_stop_hook(self):
        """门禁只通过 bootstrap 装到项目里，plugin 自身不注册 Stop hook。"""
        self.assertFalse((PLUGIN / "hooks" / "hooks.json").exists())
        source = (PLUGIN / "hooks" / "phase-gate.sh").read_text(encoding="utf-8")
        self.assertIn("CLAUDE_PROJECT_DIR", source)
        self.assertNotIn(str(ROOT), source)

    def test_old_top_level_implementation_directories_are_absent(self):
        for name in ("plan-standard", "codex-plan-review", "codex-plan-audit"):
            self.assertFalse((ROOT / name).exists(), name)

    def test_runtime_state_is_not_inside_plugin(self):
        for name in (".claude", "phase_state.json", "plan-history"):
            self.assertFalse((PLUGIN / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
