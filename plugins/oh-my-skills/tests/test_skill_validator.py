import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts/validate-skills.py"


class SkillValidatorTests(unittest.TestCase):
    def test_security_checks_are_active(self):
        result = subprocess.run([sys.executable, str(VALIDATOR), "--check-jsonc", "--check-mcp"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_rejects_credential_like_adapter_file(self):
        adapter = ROOT / "plugins/oh-my-skills/adapters/opencode/temporary-test.json"
        adapter.write_text(json.dumps({"env": {"API_KEY": "real-value"}}), encoding="utf-8")
        try:
            result = subprocess.run([sys.executable, str(VALIDATOR)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("credential-like", result.stdout)
        finally:
            adapter.unlink()

    def test_validator_rejects_text_credentials_and_absolute_paths(self):
        adapter = ROOT / "plugins/oh-my-skills/adapters/opencode/temporary-test.py"
        adapter.write_text('API_KEY = "real-value"\nHOME = "/Users/example/private"\n', encoding="utf-8")
        try:
            result = subprocess.run([sys.executable, str(VALIDATOR)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("credential-like", result.stdout)
            self.assertIn("absolute path", result.stdout)
        finally:
            adapter.unlink()


if __name__ == "__main__":
    unittest.main()
