import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(root: Path):
    return sorted((str(path.relative_to(root)), hashlib.sha256(path.read_bytes()).hexdigest()) for path in root.rglob("*") if path.is_file())


class ExportDeterminismTests(unittest.TestCase):
    def test_opencode_and_chatgpt_exports_are_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for adapter, script, extra in (
                ("opencode", ROOT / "adapters/opencode/install.py", []),
                ("chatgpt", ROOT / "adapters/chatgpt/export.py", []),
            ):
                first = base / f"{adapter}-one"
                second = base / f"{adapter}-two"
                args = ["--source-root", str(ROOT / "skills")]
                for target in (first, second):
                    result = subprocess.run([sys.executable, str(script), *args, "--target", str(target), *extra], text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(digest(first), digest(second))

    def test_chatgpt_export_matches_registry_portable_hosts(self):
        registry = json.loads((ROOT / "skills/skill-registry.json").read_text(encoding="utf-8"))
        expected = sorted(entry["id"] for entry in registry["skills"] if "chatgpt" in entry.get("portable_hosts", []))
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "chatgpt"
            result = subprocess.run(
                [sys.executable, str(ROOT / "adapters/chatgpt/export.py"), "--source-root", str(ROOT / "skills"), "--target", str(target)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(sorted(path.name for path in (target / "skills").iterdir()), expected)


if __name__ == "__main__":
    unittest.main()
