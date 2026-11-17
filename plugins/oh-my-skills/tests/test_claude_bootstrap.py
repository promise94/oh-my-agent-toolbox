import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "adapters" / "claude"
BOOTSTRAP = ADAPTER / "bootstrap.py"


class ClaudeBootstrapTests(unittest.TestCase):
    def test_adapter_manifest_and_bootstrap_exist(self):
        manifest = json.loads((ADAPTER / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "oh-my-agent-toolbox-claude")
        result = subprocess.run([sys.executable, str(BOOTSTRAP), "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bootstrap_is_idempotent_and_uninstall_preserves_user_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / ".claude/settings.local.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"custom": True}, indent=2) + "\n", encoding="utf-8")
            for _ in range(2):
                result = subprocess.run([sys.executable, str(BOOTSTRAP), "--root", str(root)], text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(settings.read_text(encoding="utf-8"))
            self.assertTrue(data["custom"])
            self.assertEqual(
                sum(
                    1
                    for entry in data["hooks"]["Stop"]
                    for hook in entry.get("hooks", [])
                    if "phase-gate.sh" in hook.get("command", "")
                ),
                1,
            )
            result = subprocess.run([sys.executable, str(BOOTSTRAP), "--root", str(root), "--uninstall"], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(settings.is_file())
            self.assertTrue(json.loads(settings.read_text(encoding="utf-8"))["custom"])

    def test_bootstrap_rejects_conflicting_phase_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / ".claude/settings.local.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(
                json.dumps({"hooks": {"Stop": [{"hooks": [{"command": "bash phase-gate.sh --other"}]}]}}),
                encoding="utf-8",
            )
            result = subprocess.run([sys.executable, str(BOOTSTRAP), "--root", str(root)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("conflicting", result.stdout)

    def test_bootstrap_rejects_invalid_settings_without_writing_hook(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / ".claude/settings.local.json"
            settings.parent.mkdir(parents=True)
            settings.write_text("{invalid", encoding="utf-8")
            result = subprocess.run([sys.executable, str(BOOTSTRAP), "--root", str(root)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Expecting", result.stdout)
            self.assertFalse((root / ".claude/hooks/phase-gate.sh").exists())

    def test_bootstrap_rejects_unwritable_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".claude").write_text("not a directory", encoding="utf-8")
            result = subprocess.run([sys.executable, str(BOOTSTRAP), "--root", str(root)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("BLOCKED", result.stdout)

    def test_bootstrap_rolls_back_all_files_when_rules_install_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / ".claude/settings.local.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"custom": [1]}) + "\n", encoding="utf-8")
            claude_md = root / "CLAUDE.md"
            claude_md.write_text("# existing\n", encoding="utf-8")
            (root / ".claude/rules").write_text("conflict", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(BOOTSTRAP), "--root", str(root), "--with-rules"],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(settings.read_text(encoding="utf-8")), {"custom": [1]})
            self.assertEqual(claude_md.read_text(encoding="utf-8"), "# existing\n")
            self.assertFalse((root / ".claude/hooks/phase-gate.sh").exists())


if __name__ == "__main__":
    unittest.main()
