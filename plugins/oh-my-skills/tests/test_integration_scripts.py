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

    def test_bootstrap_with_rules_upserts_claude_md_block(self):
        directory, root, _ = self.make_root()
        try:
            claude_md = root / "CLAUDE.md"
            claude_md.write_text("# 项目说明\n\n已有内容，不得丢失。\n", encoding="utf-8")
            command = [sys.executable, str(BOOTSTRAP), "--root", str(root), "--with-rules"]
            first = subprocess.run(command, text=True, capture_output=True)
            second = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            text = claude_md.read_text(encoding="utf-8")
            self.assertIn("已有内容，不得丢失。", text)
            self.assertEqual(text.count("oh-my-agent-toolbox:plan-rules:start"), 1)
            self.assertEqual(text.count("oh-my-agent-toolbox:plan-rules:end"), 1)
            self.assertIn("状态只经", text)
            self.assertTrue((root / ".claude" / "rules" / "plan-mode.md").is_file())
        finally:
            directory.cleanup()

    def test_bootstrap_without_rules_does_not_create_claude_md(self):
        directory, root, _ = self.make_root()
        try:
            result = subprocess.run(
                [sys.executable, str(BOOTSTRAP), "--root", str(root)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((root / "CLAUDE.md").exists())
            self.assertFalse((root / ".claude" / "rules").exists())
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

    def test_review_keeps_existing_context(self):
        directory, root, plan = self.make_root()
        try:
            request = root / ".claude/temp/review-request.md"
            context = root / ".claude/temp/review-context.md"
            context.write_text("# 需求摘要\n\n目标：验证需求摘要不会被脚本覆盖。\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(REVIEW), "--root", str(root), "--plan", str(plan),
                 "--request", str(request), "--context", str(context)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("kept existing", result.stdout)
            self.assertIn("目标：验证需求摘要不会被脚本覆盖", context.read_text(encoding="utf-8"))
        finally:
            directory.cleanup()

    def test_review_writes_fallback_context_when_missing(self):
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
            self.assertIn("fallback", result.stdout)
            self.assertIn("需求摘要：未提供", context.read_text(encoding="utf-8"))
        finally:
            directory.cleanup()

    def test_audit_summary_reconciles_plan_phases(self):
        directory, root, plan = self.make_root()
        try:
            (root / "mod.py").write_text("x = 1\n", encoding="utf-8")
            plan.write_text(
                "# plan\n\n## 阶段 1：接口\n\n| 修改 | `mod.py` | 说明 |\n\n"
                "## 阶段 2：收尾\n\n| 新增 | `missing.py` | 说明 |\n",
                encoding="utf-8",
            )
            request = root / ".claude/temp/audit-request.md"
            summary = root / ".claude/temp/summary.md"
            result = subprocess.run(
                [sys.executable, str(AUDIT), "--root", str(root), "--plan", str(plan),
                 "--request", str(request), "--summary", str(summary)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary_text = summary.read_text(encoding="utf-8")
            self.assertIn("### 阶段 1：接口", summary_text)
            self.assertIn("### 阶段 2：收尾", summary_text)
            self.assertIn("| `mod.py` | 是 |", summary_text)
            self.assertIn("| `missing.py` | 否 |", summary_text)
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

    def test_audit_missing_baseline_leaves_no_partial_output(self):
        directory, root, plan = self.make_root()
        try:
            request = root / ".claude/temp/audit-request.md"
            summary = root / ".claude/temp/summary.md"
            result = subprocess.run(
                [sys.executable, str(AUDIT), "--root", str(root), "--plan", str(plan),
                 "--request", str(request), "--summary", str(summary),
                 "--baseline", str(root / "missing.md")],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("baseline summary does not exist", result.stderr)
            self.assertFalse(request.exists(), "request must not be written before validation")
            self.assertFalse(summary.exists(), "summary must not be written before validation")
        finally:
            directory.cleanup()

    def test_audit_request_is_project_agnostic(self):
        directory, root, plan = self.make_root()
        try:
            request = root / ".claude/temp/audit-request.md"
            summary = root / ".claude/temp/summary.md"
            result = subprocess.run(
                [sys.executable, str(AUDIT), "--root", str(root), "--plan", str(plan),
                 "--request", str(request), "--summary", str(summary)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            request_text = request.read_text(encoding="utf-8")
            self.assertNotIn("CLAUDE_PLUGIN_ROOT", request_text)
            format_doc = ROOT / "skills" / "plan-standard" / "references" / "audit-subagent-prompt.md"
            self.assertTrue(format_doc.is_file(), format_doc)
            self.assertIn(str(format_doc.resolve()), request_text)
            self.assertIn(str(plan), request_text)
        finally:
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()
