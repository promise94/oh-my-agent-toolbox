import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "phase-gate.sh"


class PhaseGateShellTests(unittest.TestCase):
    def run_hook(self, state_text):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = root / ".claude" / "phase_state.json"
            state_path.parent.mkdir()
            state_path.write_text(state_text, encoding="utf-8")
            return subprocess.run(
                ["/bin/bash", str(HOOK)],
                cwd=root,
                env={"CLAUDE_PROJECT_DIR": str(root), "PATH": "/usr/bin:/bin"},
                text=True,
                capture_output=True,
            )

    def test_invalid_json_is_reported(self):
        result = self.run_hook("{")
        self.assertEqual(result.returncode, 0)
        self.assertIn("不是合法 JSON", result.stdout)

    def test_no_json_parser_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = root / ".claude" / "phase_state.json"
            state_path.parent.mkdir()
            state_path.write_text("{}", encoding="utf-8")
            result = subprocess.run(
                ["/bin/bash", str(HOOK)],
                cwd=root,
                env={"CLAUDE_PROJECT_DIR": str(root), "PATH": str(root)},
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("需要 jq", result.stdout)

    def test_planning_pending_is_blocked(self):
        result = self.run_hook('{"workflow_stage":"planning","codex_review_status":"pending"}')
        self.assertEqual(result.returncode, 0)
        self.assertIn("尚未完成 Codex review", result.stdout)

    def test_execution_missing_audit_is_reported(self):
        result = self.run_hook(
            '{"workflow_stage":"execution","codex_review_status":"completed",'
            '"current_phase":1,"phase_name":"build","phase_status":"PASS"}'
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("audit_status", result.stdout)

    def test_execution_in_progress_phase_is_reported(self):
        result = self.run_hook(
            '{"workflow_stage":"execution","current_phase":1,"phase_name":"build",'
            '"phase_status":"in_progress","audit_status":"pending"}'
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("尚未通过", result.stdout)


if __name__ == "__main__":
    unittest.main()
