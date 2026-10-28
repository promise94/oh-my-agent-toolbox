import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "plan-standard" / "scripts" / "phase-gate.py"


class PhaseGateTests(unittest.TestCase):
    def run_gate(self, state, plan_exists=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "plan.md"
            if plan_exists:
                plan.write_text("# plan\n", encoding="utf-8")
            state["plan_path"] = str(plan)
            state_path = root / ".claude" / "phase_state.json"
            state_path.parent.mkdir()
            state_path.write_text(json.dumps(state), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT)], cwd=root, text=True, capture_output=True
            )

    def test_planning_requires_review_or_waiver(self):
        result = self.run_gate({
            "plan_id": "demo",
            "workflow_stage": "planning",
            "codex_review_status": "pending",
        })
        self.assertEqual(result.returncode, 1)
        self.assertIn("Codex review", result.stdout)

    def test_execution_passes_phase_gate(self):
        result = self.run_gate({
            "plan_id": "demo",
            "workflow_stage": "execution",
            "codex_review_status": "completed",
            "current_phase": 1,
            "phase_name": "build",
            "phase_status": "PASS",
            "audit_status": "pending",
        })
        self.assertEqual(result.returncode, 0)
        self.assertIn("PASS: current phase passed", result.stdout)

    def test_execution_blocks_unresolved_phase(self):
        result = self.run_gate({
            "plan_id": "demo",
            "workflow_stage": "execution",
            "codex_review_status": "completed",
            "current_phase": 1,
            "phase_name": "build",
            "phase_status": "in_progress",
            "audit_status": "pending",
        })
        self.assertEqual(result.returncode, 1)
        self.assertIn("requires resolution", result.stdout)

    def test_execution_requires_review_disposition(self):
        result = self.run_gate({
            "plan_id": "demo",
            "workflow_stage": "execution",
            "current_phase": 1,
            "phase_name": "build",
            "phase_status": "PASS",
            "audit_status": "pending",
        })
        self.assertEqual(result.returncode, 2)
        self.assertIn("codex_review_status", result.stdout)

    def test_unknown_stage_is_blocked(self):
        result = self.run_gate({"plan_id": "demo", "workflow_stage": "unknown"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown workflow stage", result.stdout)

    def test_missing_plan_is_blocked(self):
        result = self.run_gate({
            "plan_id": "demo",
            "workflow_stage": "planning",
            "codex_review_status": "pending",
        }, plan_exists=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("plan_path", result.stdout)

    def test_cancelled_requires_dispositions(self):
        result = self.run_gate({
            "plan_id": "demo",
            "workflow_stage": "cancelled",
            "terminal_at": "2026-10-27T00:00:00Z",
            "terminal_reason": "cancelled",
        })
        self.assertEqual(result.returncode, 2)
        self.assertIn("codex_review_status", result.stdout)

    def test_non_string_status_is_blocked(self):
        result = self.run_gate({
            "plan_id": "demo",
            "workflow_stage": "execution",
            "codex_review_status": "completed",
            "current_phase": 1,
            "phase_name": "build",
            "phase_status": "PASS",
            "audit_status": [],
        })
        self.assertEqual(result.returncode, 2)
        self.assertIn("audit_status", result.stdout)


        result = self.run_gate({
            "plan_id": "demo",
            "workflow_stage": "completed",
            "codex_review_status": "completed",
            "phase_status": "PASS",
            "audit_status": "pending",
            "terminal_at": "2026-10-27T00:00:00Z",
            "terminal_reason": "completed",
            "current_phase": 1,
            "phase_name": "build",
        })
        self.assertEqual(result.returncode, 2)
        self.assertIn("audit_status", result.stdout)

    def test_completed_requires_terminal_fields(self):
        result = self.run_gate({
            "plan_id": "demo",
            "workflow_stage": "completed",
            "codex_review_status": "completed",
            "phase_status": "PASS",
            "audit_status": "completed",
            "current_phase": 1,
            "phase_name": "build",
        })
        self.assertEqual(result.returncode, 2)
        self.assertIn("terminal_at", result.stdout)


if __name__ == "__main__":
    unittest.main()
