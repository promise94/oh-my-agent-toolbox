import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTERS = ROOT / "adapters"


class HostMatrixTests(unittest.TestCase):
    def test_each_adapter_has_expected_entrypoint(self):
        expected = {
            "claude": ".claude-plugin/plugin.json",
            "opencode": "opencode.jsonc",
            "chatgpt": "plugin.json",
        }
        for name, relative in expected.items():
            with self.subTest(adapter=name):
                self.assertTrue((ADAPTERS / name / relative).is_file())

    def test_non_claude_adapters_do_not_ship_claude_project_runtime(self):
        for name in ("opencode", "chatgpt"):
            for path in (ADAPTERS / name).rglob("*"):
                if path.is_file():
                    self.assertNotIn("CLAUDE_PROJECT_DIR", path.read_text(encoding="utf-8", errors="ignore"))


if __name__ == "__main__":
    unittest.main()
