import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "phase-state.py"


class PhaseStateTests(unittest.TestCase):
    def run_archive(self, state):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        state_path = root / ".claude" / "phase_state.json"
        state_path.parent.mkdir()
        state_path.write_text(json.dumps(state), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "archive"], cwd=root, text=True, capture_output=True
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

    def test_abandoned_requires_dispositions(self):
        directory, _, result = self.run_archive({
            "plan_id": "demo",
            "workflow_stage": "abandoned",
            "terminal_at": "2026-10-27T00:00:00Z",
            "terminal_reason": "abandoned",
        })
        try:
            self.assertEqual(result.returncode, 2)
            self.assertIn("codex_review_status", result.stdout)
        finally:
            directory.cleanup()

    def test_invalid_json_is_rejected(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        state_path = root / ".claude" / "phase_state.json"
        state_path.parent.mkdir()
        state_path.write_text("{", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "archive"], cwd=root, text=True, capture_output=True
        )
        try:
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid phase state", result.stdout)
        finally:
            directory.cleanup()


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
                [sys.executable, str(SCRIPT), "archive"], cwd=root, text=True, capture_output=True
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("archive already exists", result.stdout)
        finally:
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()
