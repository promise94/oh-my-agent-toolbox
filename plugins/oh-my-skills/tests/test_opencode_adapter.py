import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "adapters" / "opencode"
INSTALL = ADAPTER / "install.py"


class OpenCodeAdapterTests(unittest.TestCase):
    def test_adapter_files_and_jsonc_shape(self):
        self.assertTrue((ADAPTER / "commands/plan.md").is_file())
        self.assertTrue((ADAPTER / "agents/reviewer.md").is_file())
        config = (ADAPTER / "opencode.jsonc").read_text(encoding="utf-8")
        self.assertIn('"skills"', config)
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", config)

    def test_install_copies_deterministically_and_rejects_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "one"
            second = Path(directory) / "two"
            for target in (first, second):
                result = subprocess.run(
                    [sys.executable, str(INSTALL), "--source-root", str(ROOT / "skills"), "--target", str(target)],
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((target / ".claude").exists())
                self.assertFalse(any(path.is_symlink() for path in target.rglob("*")))
            def digest(root: Path):
                return sorted((str(path.relative_to(root)), hashlib.sha256(path.read_bytes()).hexdigest()) for path in root.rglob("*") if path.is_file())
            self.assertEqual(digest(first), digest(second))
            result = subprocess.run(
                [sys.executable, str(INSTALL), "--source-root", str(ROOT / "skills"), "--target", str(first)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("exists", result.stdout)


if __name__ == "__main__":
    unittest.main()
