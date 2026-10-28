import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "phase-state.py"


def isolated_env(root: Path) -> dict[str, str]:
    """Keep CLAUDE_PROJECT_DIR from leaking the real repository into the test."""
    return dict(os.environ, CLAUDE_PROJECT_DIR=str(root))


class PhaseStateTests(unittest.TestCase):
    def run_archive(self, state):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        state_path = root / ".claude" / "phase_state.json"
        state_path.parent.mkdir()
        state_path.write_text(json.dumps(state), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "archive"],
            cwd=root,
            env=isolated_env(root),
            text=True,
            capture_output=True,
        )
        return directory, root, result

    def test_completed_plan_is_archived(self):
        directory, root, result = self.run_archive({
            "plan_id": "demo",
            "workflow_stage": "completed",
            "codex_review_status": "completed",
            "phase_status": "PASS",
            "audit_status": "completed",
            "terminal_at": "2026-10-27T00:00:00Z",
            "terminal_reason": "completed",
        })
        try:
            self.assertEqual(result.returncode, 0)
            self.assertFalse((root / ".claude" / "phase_state.json").exists())
            self.assertTrue((root / ".claude" / "plan-history" / "demo.json").exists())
        finally:
            directory.cleanup()

    def test_active_plan_cannot_be_archived(self):
        directory, _, result = self.run_archive({"plan_id": "demo", "workflow_stage": "execution"})
        try:
            self.assertEqual(result.returncode, 2)
            self.assertIn("only terminal", result.stdout)
        finally:
            directory.cleanup()

    def test_completed_plan_requires_audit(self):
        directory, _, result = self.run_archive({
            "plan_id": "demo",
            "workflow_stage": "completed",
            "codex_review_status": "completed",
            "phase_status": "PASS",
            "audit_status": "pending",
            "terminal_at": "2026-10-27T00:00:00Z",
            "terminal_reason": "completed",
        })
        try:
            self.assertEqual(result.returncode, 2)
            self.assertIn("audit_status", result.stdout)
        finally:
            directory.cleanup()

    def test_completed_requires_terminal_fields(self):
        directory, _, result = self.run_archive({
            "plan_id": "demo",
            "workflow_stage": "completed",
            "codex_review_status": "completed",
            "phase_status": "PASS",
            "audit_status": "completed",
        })
        try:
            self.assertEqual(result.returncode, 2)
            self.assertIn("terminal_at", result.stdout)
        finally:
            directory.cleanup()

    def test_cancelled_requires_terminal_fields(self):
        directory, _, result = self.run_archive({"plan_id": "demo", "workflow_stage": "cancelled"})
        try:
            self.assertEqual(result.returncode, 2)
            self.assertIn("terminal_at", result.stdout)
        finally:
            directory.cleanup()

    def test_invalid_plan_id_is_rejected(self):
        directory, _, result = self.run_archive({
            "plan_id": "Bad ID",
            "workflow_stage": "cancelled",
            "terminal_at": "2026-10-27T00:00:00Z",
            "terminal_reason": "cancelled",
        })
        try:
            self.assertEqual(result.returncode, 2)
            self.assertIn("kebab-case", result.stdout)
        finally:
            directory.cleanup()

    def test_abandoned_archives_without_review_or_audit(self):
        directory, root, result = self.run_archive({
            "plan_id": "demo",
            "workflow_stage": "abandoned",
            "terminal_at": "2026-10-27T00:00:00Z",
            "terminal_reason": "abandoned",
        })
        try:
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue((root / ".claude" / "plan-history" / "demo.json").exists())
        finally:
            directory.cleanup()

    def test_invalid_json_is_rejected(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        state_path = root / ".claude" / "phase_state.json"
        state_path.parent.mkdir()
        state_path.write_text("{", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "archive"],
            cwd=root,
            env=isolated_env(root),
            text=True,
            capture_output=True,
        )
        try:
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid phase state", result.stdout)
        finally:
            directory.cleanup()

    def test_archive_appends_suffix_for_duplicate_history(self):
        directory, root, first = self.run_archive({
            "plan_id": "demo",
            "workflow_stage": "completed",
            "codex_review_status": "completed",
            "phase_status": "PASS",
            "audit_status": "waived",
            "terminal_at": "2026-10-27T00:00:00Z",
            "terminal_reason": "waived",
        })
        try:
            self.assertEqual(first.returncode, 0)
            state_path = root / ".claude" / "phase_state.json"
            state_path.write_text(json.dumps({
                "plan_id": "demo",
                "workflow_stage": "completed",
                "codex_review_status": "completed",
                "phase_status": "PASS",
                "audit_status": "waived",
                "terminal_at": "2026-10-27T00:00:00Z",
                "terminal_reason": "waived",
            }), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "archive"],
                cwd=root,
                env=isolated_env(root),
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue((root / ".claude" / "plan-history" / "demo.json").exists())
            self.assertTrue((root / ".claude" / "plan-history" / "demo-2.json").exists())
            self.assertFalse((root / ".claude" / "phase_state.json").exists())
        finally:
            directory.cleanup()


class PhaseStateCommandTests(unittest.TestCase):
    """start / set / validate 三个写入与校验入口。"""

    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        (self.root / ".claude").mkdir()
        self.plan = self.root / "demo-plan.md"
        self.plan.write_text("# plan\n", encoding="utf-8")
        self.state_path = self.root / ".claude" / "phase_state.json"

    def tearDown(self):
        self._directory.cleanup()

    def run_cmd(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root,
            env=isolated_env(self.root),
            text=True,
            capture_output=True,
        )

    def write_state(self, state):
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

    def read_state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def test_start_writes_planning_state(self):
        result = self.run_cmd("start", "--plan", str(self.plan))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        state = self.read_state()
        self.assertEqual(state["plan_id"], "demo-plan")
        self.assertEqual(state["workflow_stage"], "planning")
        self.assertEqual(state["codex_review_status"], "pending")
        self.assertTrue(state["updated_at"])

    def test_start_rejects_non_kebab_plan_name(self):
        plan = self.root / "Demo Plan.md"
        plan.write_text("# plan\n", encoding="utf-8")
        result = self.run_cmd("start", "--plan", str(plan))
        self.assertEqual(result.returncode, 2)
        self.assertIn("kebab-case", result.stdout)
        self.assertFalse(self.state_path.exists())

    def test_start_refuses_second_active_plan(self):
        self.write_state({"plan_id": "old", "plan_path": str(self.plan), "workflow_stage": "execution"})
        result = self.run_cmd("start", "--plan", str(self.plan))
        self.assertEqual(result.returncode, 2)
        self.assertIn("active plan already exists", result.stdout)
        self.assertEqual(self.read_state()["plan_id"], "old")

    def test_start_refuses_unarchived_terminal_plan(self):
        self.write_state({"plan_id": "old", "plan_path": str(self.plan), "workflow_stage": "completed"})
        result = self.run_cmd("start", "--plan", str(self.plan))
        self.assertEqual(result.returncode, 2)
        self.assertIn("run archive first", result.stdout)

    def test_set_cannot_skip_review(self):
        self.write_state({
            "plan_id": "demo-plan",
            "plan_path": str(self.plan),
            "workflow_stage": "planning",
            "codex_review_status": "pending",
        })
        result = self.run_cmd("set", "--field", "workflow_stage=execution")
        self.assertEqual(result.returncode, 2)
        self.assertIn("codex_review_status", result.stdout)
        self.assertEqual(self.read_state()["workflow_stage"], "planning")

    def test_set_updates_execution_state_and_validates(self):
        self.write_state({
            "plan_id": "demo-plan",
            "plan_path": str(self.plan),
            "workflow_stage": "planning",
            "codex_review_status": "completed",
        })
        result = self.run_cmd(
            "set",
            "--field", "workflow_stage=execution",
            "--field", "current_phase=1",
            "--field", "phase_name=实施阶段",
            "--field", "phase_status=PASS",
            "--field", "audit_status=pending",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.read_state()["current_phase"], 1)
        checked = self.run_cmd("validate")
        self.assertEqual(checked.returncode, 0, checked.stdout)
        self.assertIn("PASS: current phase passed", checked.stdout)

    def test_set_rejects_non_integer_phase(self):
        self.write_state({"plan_id": "demo-plan", "plan_path": str(self.plan), "workflow_stage": "planning"})
        result = self.run_cmd("set", "--field", "current_phase=two")
        self.assertEqual(result.returncode, 2)
        self.assertIn("must be an integer", result.stdout)

    def test_set_rejects_unknown_field(self):
        self.write_state({"plan_id": "demo-plan", "plan_path": str(self.plan), "workflow_stage": "planning"})
        result = self.run_cmd("set", "--field", "surprise=1")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported field", result.stdout)

    def test_warns_when_cwd_is_outside_target_root(self):
        self.write_state({"plan_id": "demo-plan", "plan_path": str(self.plan), "workflow_stage": "planning"})
        with tempfile.TemporaryDirectory() as elsewhere:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "set", "--root", str(self.root),
                 "--field", "codex_review_note=检查目标"],
                cwd=elsewhere,
                env=isolated_env(self.root),
                text=True,
                capture_output=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("WARN", result.stderr)
        self.assertEqual(self.read_state()["codex_review_note"], "检查目标")

    def test_validate_reports_planning_as_blocked(self):
        self.write_state({
            "plan_id": "demo-plan",
            "plan_path": str(self.plan),
            "workflow_stage": "planning",
            "codex_review_status": "pending",
        })
        result = self.run_cmd("validate")
        self.assertEqual(result.returncode, 1)
        self.assertIn("planning requires Codex review", result.stdout)


if __name__ == "__main__":
    unittest.main()
