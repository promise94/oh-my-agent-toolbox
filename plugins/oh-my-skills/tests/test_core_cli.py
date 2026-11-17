import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLBOX = ROOT / "core" / "toolbox.py"


class CoreCliTests(unittest.TestCase):
    def run_tool(self, root: Path, *args: str):
        return subprocess.run(
            [sys.executable, str(TOOLBOX), *args, "--root", str(root)],
            text=True,
            capture_output=True,
        )

    def test_validate_missing_state_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_tool(Path(directory), "plan", "validate")
            self.assertEqual(result.returncode, 2)
            self.assertIn("BLOCKED", result.stdout)

    def test_legacy_state_validate_uses_new_review_field(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "plan.md"
            plan.write_text("# plan\n", encoding="utf-8")
            state_dir = root / ".plans"
            state_dir.mkdir()
            (state_dir / "phase_state.json").write_text(
                json.dumps({
                    "plan_id": "legacy-plan",
                    "plan_path": str(plan),
                    "workflow_stage": "execution",
                    "current_phase": 1,
                    "phase_name": "one",
                    "phase_status": "PASS",
                    "codex_review_status": "waived",
                    "audit_status": "waived",
                }),
                encoding="utf-8",
            )
            result = self.run_tool(root, "plan", "validate", "--state-dir", ".plans")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Review: waived", result.stdout)

    def test_full_lifecycle_supports_both_state_dirs(self):
        for state_dir in (".plans", ".claude"):
            with self.subTest(state_dir=state_dir), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                plan = root / "plan.md"
                plan.write_text("# plan\n", encoding="utf-8")
                started = self.run_tool(root, "plan", "start", "--plan", str(plan), "--state-dir", state_dir)
                self.assertEqual(started.returncode, 0, started.stderr + started.stdout)
                updated = self.run_tool(
                    root,
                    "plan", "set",
                    "--state-dir", state_dir,
                    "--field", "workflow_stage=execution",
                    "--field", "current_phase=1",
                    "--field", "phase_name=build",
                    "--field", "phase_status=PASS",
                    "--field", "review_status=waived",
                    "--field", "audit_status=waived",
                )
                self.assertEqual(updated.returncode, 0, updated.stderr + updated.stdout)
                validated = self.run_tool(root, "plan", "validate", "--state-dir", state_dir)
                self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)
                terminal = self.run_tool(
                    root,
                    "plan", "set", "--state-dir", state_dir,
                    "--field", "workflow_stage=completed",
                    "--field", "terminal_at=2026-11-11T00:00:00Z",
                    "--field", "terminal_reason=test",
                )
                self.assertEqual(terminal.returncode, 0, terminal.stdout + terminal.stderr)
                archived = self.run_tool(root, "plan", "archive", "--state-dir", state_dir)
                self.assertEqual(archived.returncode, 0, archived.stdout + archived.stderr)
                self.assertTrue((root / state_dir / "plan-history").is_dir())

    def test_install_and_doctor_are_exposed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for command in (("install", "--host", "opencode"), ("doctor", "--host", "chatgpt")):
                result = subprocess.run([sys.executable, str(TOOLBOX), *command], text=True, capture_output=True, cwd=root)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

class PhaseTransitionCommandTests(CoreCliTests):
    def setup_state(self, root: Path, phase=1, status='PASS', stage='execution', review='completed', codex='completed'):
        plan=root/'plan.md'; plan.write_text('# plan\n')
        d=root/'.claude'; d.mkdir(); (d/'phase_state.json').write_text(json.dumps({'plan_id':'demo','plan_path':str(plan),'workflow_stage':stage,'current_phase':phase,'phase_name':'phase','phase_status':status,'review_status':review,'codex_review_status':codex,'audit_status':'waived'}))
    def test_transition_requires_execution_pass_and_matching_review(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.setup_state(root,stage='planning',review='pending',codex='pending')
            before=(root/'.claude/phase_state.json').read_bytes(); r=self.run_tool(root,'plan','transition','--from-phase','1','--to-phase','2','--phase-name','audit','--state-dir','.claude')
            self.assertEqual(r.returncode,2); self.assertEqual(before,(root/'.claude/phase_state.json').read_bytes())
    def test_transition_and_complete(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.setup_state(root)
            r=self.run_tool(root,'plan','transition','--from-phase','1','--to-phase','2','--phase-name','audit','--state-dir','.claude'); self.assertEqual(r.returncode,0,r.stdout)
            self.run_tool(root,'plan','set','--state-dir','.claude','--field','phase_status=PASS')
            r=self.run_tool(root,'plan','complete','--state-dir','.claude','--audit-status','completed','--audit-provider','codex','--terminal-at','2026-11-17T00:00:00Z','--terminal-reason','done'); self.assertEqual(r.returncode,0,r.stdout)
            self.assertEqual(json.loads((root/'.claude/phase_state.json').read_text())['workflow_stage'],'completed')
