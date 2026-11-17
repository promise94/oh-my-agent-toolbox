import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "adapters" / "chatgpt"
EXPORT = ADAPTER / "export.py"


class ChatGptAdapterTests(unittest.TestCase):
    def test_portable_manifest_and_mcp_are_safe(self):
        manifest = json.loads((ADAPTER / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "oh-my-agent-toolbox")
        self.assertTrue((ADAPTER / "mcp.json").is_file())
        serialized = (ADAPTER / "mcp.json").read_text(encoding="utf-8").lower()
        self.assertNotIn("real-secret", serialized)
        self.assertNotIn("claude_plugin_root", serialized)

    def test_export_is_deterministic_and_contains_no_claude_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "one"
            second = Path(directory) / "two"
            for target in (first, second):
                result = subprocess.run(
                    [sys.executable, str(EXPORT), "--source-root", str(ROOT / "skills"), "--target", str(target)],
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((target / ".claude").exists())
                for path in target.rglob("*"):
                    if path.is_file():
                        text = path.read_text(encoding="utf-8", errors="ignore")
                        self.assertNotIn("CLAUDE_PROJECT_DIR", text)
                        self.assertNotIn("phase_state.json", text)
                self.assertTrue((target / "marketplace.json").is_file())
            self.assertEqual(
                sorted(str(p.relative_to(first)) for p in first.rglob("*") if p.is_file()),
                sorted(str(p.relative_to(second)) for p in second.rglob("*") if p.is_file()),
            )

    def test_export_reads_portable_subset_from_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "export"
            result = subprocess.run(
                [sys.executable, str(EXPORT), "--source-root", str(ROOT / "skills"), "--target", str(target)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                sorted(path.name for path in (target / "skills").iterdir()),
                ["code-review"],
            )

    def test_export_rejects_conflicting_existing_files_without_partial_write(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "export"
            target.mkdir()
            (target / "plugin.json").write_text('{"user":true}\n', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(EXPORT), "--source-root", str(ROOT / "skills"), "--target", str(target)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("target conflict", result.stdout)
            self.assertEqual((target / "plugin.json").read_text(encoding="utf-8"), '{"user":true}\n')
            self.assertFalse((target / "skills").exists())


if __name__ == "__main__":
    unittest.main()
