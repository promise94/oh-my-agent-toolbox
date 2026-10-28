import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap.py"
REVIEW = ROOT / "scripts" / "prepare-review.py"
AUDIT = ROOT / "scripts" / "prepare-audit.py"


class IntegrationScriptTests(unittest.TestCase):
    def make_root(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        (root / ".claude" / "temp").mkdir(parents=True)
        plan = root / "plan.md"
        plan.write_text("# plan\n", encoding="utf-8")
        return directory, root, plan

    def test_bootstrap_merges_stop_hook_idempotently(self):
        directory, root, _ = self.make_root()
        try:
            settings = root / ".claude" / "settings.local.json"
            settings.write_text(json.dumps({"permissions": {"allow": ["Bash(node *)"]}}), encoding="utf-8")
            command = [sys.executable, str(BOOTSTRAP), "--root", str(root)]
            first = subprocess.run(command, text=True, capture_output=True)
            second = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            value = json.loads(settings.read_text(encoding="utf-8"))
            self.assertEqual(value["permissions"]["allow"], ["Bash(node *)"])
            stop = value["hooks"]["Stop"]
            commands = [hook["command"] for entry in stop for hook in entry["hooks"]]
            self.assertEqual(commands.count('bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/phase-gate.sh'), 1)
            self.assertTrue((root / ".claude/hooks/phase-gate.sh").stat().st_mode & 0o111)
        finally:
            directory.cleanup()

    def test_review_rejects_paths_outside_temp(self):
        directory, root, plan = self.make_root()
        try:
            result = subprocess.run(
                [sys.executable, str(REVIEW), "--root", str(root), "--plan", str(plan),
                 "--request", str(root / "request.md"), "--context", str(root / ".claude/temp/context.md")],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("request must be inside", result.stderr)
        finally:
            directory.cleanup()

    def test_review_writes_request_and_context(self):
        directory, root, plan = self.make_root()
        try:
            request = root / ".claude/temp/review-request.md"
            context = root / ".claude/temp/review-context.md"
            result = subprocess.run(
                [sys.executable, str(REVIEW), "--root", str(root), "--plan", str(plan),
                 "--request", str(request), "--context", str(context)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("KeyError", result.stderr)
            request_text = request.read_text(encoding="utf-8")
            context_text = context.read_text(encoding="utf-8")
            self.assertIn(str(plan), request_text)
            self.assertIn(str(context), request_text)
            self.assertIn(str(request), request_text)
            self.assertNotIn("CLAUDE_PLUGIN_ROOT", request_text)
            format_doc = ROOT / "skills" / "plan-standard" / "references" / "review-subagent-prompt.md"
            self.assertTrue(format_doc.is_file(), format_doc)
            self.assertIn(str(format_doc.resolve()), request_text)
            self.assertIn(str(plan), context_text)
        finally:
            directory.cleanup()

    def test_audit_summary_contains_branch_and_baseline(self):
        directory, root, plan = self.make_root()
        try:
            request = root / ".claude/temp/audit-request.md"
            summary = root / ".claude/temp/summary.md"
            baseline = root / ".claude/baseline.md"
            validation = root / ".claude/validation.md"
            baseline.write_text("baseline status\n", encoding="utf-8")
            validation.write_text("tests passed\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(AUDIT), "--root", str(root), "--plan", str(plan),
                 "--request", str(request), "--summary", str(summary),
                 "--baseline", str(baseline), "--validation", str(validation)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            request_text = request.read_text(encoding="utf-8")
            summary_text = summary.read_text(encoding="utf-8")
            self.assertIn(str(request), request_text)
            self.assertIn(str(baseline), request_text)
            self.assertIn("当前分支：", summary_text)
            self.assertIn("baseline status", summary_text)
            self.assertIn("tests passed", summary_text)
        finally:
            directory.cleanup()

    def test_audit_rejects_summary_outside_temp(self):
        directory, root, plan = self.make_root()
        try:
            result = subprocess.run(
                [sys.executable, str(AUDIT), "--root", str(root), "--plan", str(plan),
                 "--request", str(root / ".claude/temp/request.md"),
                 "--summary", str(root / "summary.md")],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("summary must be inside", result.stderr)
        finally:
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()
