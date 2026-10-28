import json
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
            PLUGIN / "hooks/hooks.json",
            PLUGIN / "scripts/bootstrap.py",
            PLUGIN / "scripts/phase-gate.py",
            PLUGIN / "scripts/phase-state.py",
            PLUGIN / "scripts/prepare-review.py",
            PLUGIN / "scripts/prepare-audit.py",
            PLUGIN / "config-templates/mcp.example.json",
            PLUGIN / "config-templates/settings.local.example.json",
        ]
        for path in required:
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), path)

    def test_hook_uses_plugin_root(self):
        hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text(encoding="utf-8"))
        command = hooks["hooks"]["Stop"][0]["hooks"][0]["command"]
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", command)
        self.assertNotIn(str(ROOT), command)

    def test_old_top_level_implementation_directories_are_absent(self):
        for name in ("plan-standard", "codex-plan-review", "codex-plan-audit"):
            self.assertFalse((ROOT / name).exists(), name)

    def test_runtime_state_is_not_inside_plugin(self):
        for name in (".claude", "phase_state.json", "plan-history"):
            self.assertFalse((PLUGIN / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
