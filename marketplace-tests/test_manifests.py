import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN = ROOT / "plugins" / "oh-my-skills"


class MarketplaceTests(unittest.TestCase):
    def test_manifests_are_valid_and_point_inside_repo(self):
        marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        plugin = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(marketplace["plugins"][0]["name"], "oh-my-agent-toolbox")
        self.assertEqual(plugin["name"], "oh-my-agent-toolbox")
        self.assertEqual(marketplace["plugins"][0]["source"], "./plugins/oh-my-skills")
        self.assertTrue((ROOT / marketplace["plugins"][0]["source"]).is_dir())
        for value in (marketplace, plugin):
            serialized = json.dumps(value).lower()
            self.assertNotIn("api_key", serialized)
            self.assertNotIn("/users/", serialized)

    def test_plugin_layout_and_templates(self):
        self.assertTrue((PLUGIN / "skills/plan-standard/SKILL.md").is_file())
        self.assertTrue((PLUGIN / "skills/codex-plan-review/SKILL.md").is_file())
        self.assertTrue((PLUGIN / "skills/codex-plan-audit/SKILL.md").is_file())
        self.assertTrue((PLUGIN / "hooks/hooks.json").is_file())
        self.assertTrue((PLUGIN / "agents/openai.yaml").is_file())
        result = subprocess.run(
            [sys.executable, str(PLUGIN / "scripts/validate-config.py"),
             *map(str, (PLUGIN / "config-templates").glob("*.json"))],
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_rejects_non_placeholder_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps({"env": {"API_KEY": "real-secret-value"}}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(PLUGIN / "scripts/validate-config.py"), str(path)],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("credential-like", result.stdout)


if __name__ == "__main__":
    unittest.main()
