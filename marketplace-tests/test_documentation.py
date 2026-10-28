import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_documented_version_matches_manifests(self):
        plugin = json.loads(
            (ROOT / "plugins/oh-my-skills/.claude-plugin/plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        version = plugin["version"]
        self.assertEqual(marketplace["metadata"]["version"], version)
        self.assertEqual(marketplace["plugins"][0]["version"], version)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"当前版本均为 `{version}`", readme)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## [{version}]", changelog)

    def test_installation_contract_is_consistent(self):
        documents = [
            ROOT / "README.md",
            ROOT / "CONTRIBUTING.md",
            ROOT / "CHANGELOG.md",
            ROOT / "docs/installation.md",
            ROOT / "docs/troubleshooting.md",
            ROOT / "plugins/oh-my-skills/README.md",
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in documents)
        self.assertIn("https://github.com/promise94/oh-my-agent-toolbox", text)
        self.assertIn(
            "/plugin install oh-my-agent-toolbox@oh-my-agent-toolbox",
            text,
        )
        self.assertNotIn("oh-my-agent-toolbox@oh-my-skills", text)
        self.assertNotIn("https://gitee.com/promise9495/oh-my-skills", text)

    def test_user_documentation_exists(self):
        for relative_path in (
            "docs/installation.md",
            "docs/troubleshooting.md",
            "CHANGELOG.md",
        ):
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_documentation_describes_safety_boundaries(self):
        installation = (ROOT / "docs/installation.md").read_text(encoding="utf-8")
        troubleshooting = (ROOT / "docs/troubleshooting.md").read_text(encoding="utf-8")
        combined = installation + troubleshooting
        for term in ("blocked", "waived", "bootstrap", "token", "MCP"):
            with self.subTest(term=term):
                self.assertIn(term, combined)


if __name__ == "__main__":
    unittest.main()
