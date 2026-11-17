import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import phase_state


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "core" / "schema" / "plan-state.schema.json"


class CoreStateSchemaTests(unittest.TestCase):
    def test_schema_declares_common_fields(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        for field in ("schema_version", "plan_id", "workflow_stage", "review_status", "audit_status"):
            self.assertIn(field, schema["properties"])

    def test_legacy_review_fields_are_normalized_without_loss(self):
        state = {
            "plan_id": "legacy-plan",
            "plan_path": "/tmp/legacy-plan.md",
            "workflow_stage": "planning",
            "codex_review_status": "waived",
            "codex_review_note": "legacy note",
            "audit_status": "pending",
        }
        normalized = phase_state.normalize_state(state)
        self.assertEqual(normalized["review_status"], "waived")
        self.assertEqual(normalized["review_note"], "legacy note")
        self.assertEqual(normalized["codex_review_status"], "waived")
        self.assertEqual(normalized["schema_version"], 2)

    def test_state_dir_can_be_project_relative_or_absolute(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(phase_state.state_file(root, ".plans"), root / ".plans/phase_state.json")
            absolute = root / "state"
            self.assertEqual(phase_state.state_file(root, str(absolute)), absolute / "phase_state.json")


if __name__ == "__main__":
    unittest.main()
