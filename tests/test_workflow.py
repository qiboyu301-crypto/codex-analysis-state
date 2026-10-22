"""Behavioral checks executed against the installed distribution."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from codex_analysis_state import data, workspace
from codex_analysis_state._vendor.statem.core import StatemError
from codex_analysis_state.demo import REQUESTS, prepare_turn, run_demo


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="analysis state ")
        self.root = Path(self.temp.name) / "workspace with spaces"
        workspace.create_workspace(self.root, workspace.resources() / "demo/raw")

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, tid=1):
        workspace.begin(self.root, REQUESTS[tid-1])
        prepare_turn(self.root, tid)
        return self.root / "turns" / f"{tid:03}"

    def finish(self):
        for node in ("solve", "retain", "verify", "handoff"):
            workspace.advance(self.root, node)
        workspace.complete(self.root)

    def test_three_turn_demo_preserves_membership_and_expires_temporary_window(self):
        result = run_demo(Path(self.temp.name) / "demo")
        first, second, third = result["turns"]
        self.assertEqual(first["candidate_members"], ["North", "South", "West"])
        self.assertEqual([r["region"] for r in first["leaders"]], ["North", "South"])
        self.assertEqual([r["region"] for r in second["leaders"]], ["North", "West"])
        self.assertEqual(second["membership"]["entered"], [])
        self.assertEqual(second["membership"]["exited"], [])
        self.assertEqual(second["membership"]["current_count"], 3)
        self.assertEqual(second["total_revenue"], 260)
        self.assertEqual(third["window"], "2026-01")
        self.assertEqual(third["total_revenue"], 240)
        self.assertEqual(len(data.read(Path(result["workspace"]) / "data_index.json")), 1)

    def test_init_does_not_overwrite_existing_directory(self):
        with self.assertRaisesRegex(ValueError, "new directory"):
            workspace.create_workspace(self.root, workspace.resources() / "demo/raw")

    def test_cannot_begin_over_an_unfinished_turn(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "Finish the active"):
            workspace.begin(self.root, "Another request")

    def test_cannot_publish_before_handoff(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "handoff"):
            workspace.complete(self.root)
        self.assertEqual(data.read(self.root / "data_index.json"), {})

    def test_missing_plan_blocks_transition(self):
        turn = self.prepare()
        (turn / "plan.md").unlink()
        with self.assertRaises(StatemError):
            workspace.advance(self.root, "solve")
        self.assertEqual(workspace.status(self.root)["current"], "inspect")

    def test_changed_raw_input_invalidates_pinned_selection(self):
        self.prepare()
        workspace.advance(self.root, "solve")
        raw = self.root / "raw/sales.csv"
        raw.write_text(raw.read_text().replace(",100", ",999"))
        with self.assertRaises(StatemError):
            workspace.advance(self.root, "retain")
        self.assertFalse((self.root / "turns/001/publication.json").exists())

    def test_unloaded_historical_input_fails_replay(self):
        self.prepare()
        self.finish()
        turn = self.prepare(2)
        (turn / "solve.py").write_text('print("{\\"total_revenue\\":260}")\n')
        workspace.advance(self.root, "solve")
        workspace.advance(self.root, "retain")
        with self.assertRaises(StatemError) as caught:
            workspace.advance(self.root, "verify")
        self.assertIn("not loaded", json.dumps(caught.exception.details))
        self.assertEqual(workspace.status(self.root)["current"], "retain")

    def test_changed_script_after_replay_cannot_reach_handoff(self):
        turn = self.prepare()
        for node in ("solve", "retain", "verify"):
            workspace.advance(self.root, node)
        with (turn / "solve.py").open("a") as stream:
            stream.write("\n# changed after replay\n")
        with self.assertRaises(StatemError):
            workspace.advance(self.root, "handoff")
        self.assertEqual(data.read(self.root / "data_index.json"), {})

    def test_tables_publish_only_after_verified_handoff(self):
        self.prepare()
        for node in ("solve", "retain", "verify", "handoff"):
            workspace.advance(self.root, node)
        self.assertEqual(data.read(self.root / "data_index.json"), {})
        workspace.complete(self.root)
        self.assertEqual(list(data.read(self.root / "data_index.json")), ["t001_candidates"])
        with self.assertRaisesRegex(ValueError, "already completed"):
            workspace.advance(self.root, "solve")

    def test_raw_path_rejects_an_unselected_input(self):
        turn = self.prepare()
        data.write(turn / "selection.json", {"inputs": [], "notes": "No selected sources."})
        (turn / "solve.py").write_text(
            'from codex_analysis_state import data\nprint(data.raw_path("raw/sales.csv"))\n')
        data.write(turn / "retention.json", {"keep": [], "skip_reason": "No exports."})
        workspace.advance(self.root, "solve")
        workspace.advance(self.root, "retain")
        with self.assertRaises(StatemError) as caught:
            workspace.advance(self.root, "verify")
        self.assertIn("not selected", json.dumps(caught.exception.details))

    def test_request_identity_is_fixed_at_begin(self):
        turn = self.prepare()
        (turn / "request.md").write_text("Changed request")
        with self.assertRaisesRegex(ValueError, "request changed"):
            workspace.advance(self.root, "solve")

    def test_changing_retained_content_breaks_historical_selection(self):
        self.prepare()
        self.finish()
        self.prepare(2)
        table = self.root / "data/t001/candidates.parquet"
        table.write_bytes(table.read_bytes() + b"changed")
        with self.assertRaises(StatemError) as caught:
            workspace.advance(self.root, "solve")
        self.assertIn("content changed", json.dumps(caught.exception.details))

    def test_restore_standing_state_excludes_temporary_override(self):
        changes = [
            {"updates": {"window": {"value": "January", "reason": "Initial request"}}, "temporary": {}},
            {"updates": {"window": {"value": "March", "reason": "New persistent rule"}}, "temporary": {}},
            {"restore_from_turn": 1, "updates": {}, "temporary": {"window": {"value": "April", "reason": "This request only"}}},
            {"updates": {}, "temporary": {}},
        ]
        values = []
        for tid, change in enumerate(changes, 1):
            workspace.begin(self.root, f"Definition test {tid}")
            turn = self.root / "turns" / f"{tid:03}"
            data.write(turn / "analysis.json", {**change, "checks": ["Check the requested window."]})
            data.write(turn / "selection.json", {"inputs": [], "notes": "Inspect definition state only."})
            data.write(turn / "retention.json", {"keep": [], "skip_reason": "No data transformation."})
            (turn / "plan.md").write_text("Read the effective window.")
            (turn / "review.md").write_text("The requested windows are January, March, April, January.")
            (turn / "solve.py").write_text(
                "import json\nfrom codex_analysis_state import data\nprint(json.dumps(data.analysis_context()))\n")
            self.finish()
            values.append(data.read(turn / "answer.json")["window"])
        self.assertEqual(values, ["January", "March", "April", "January"])

    def test_cli_operates_from_workspace_subdirectory(self):
        process = subprocess.run([sys.executable, "-m", "codex_analysis_state", "status"],
                                 cwd=self.root / "raw", capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(process.stdout)["next"], "begin")


class NumericConventionTests(unittest.TestCase):
    def test_average_one_based_rank_with_ties_and_missing(self):
        result = data.rank_percentiles([10, 10, 30, None])
        self.assertEqual(result.iloc[:3].tolist(), [50.0, 50.0, 100.0])
        self.assertTrue(result.isna().iloc[3])

    def test_deduplicate_mapped_groups_before_equal_allocation(self):
        self.assertEqual(data.unique_group_weights(["A", "A", "B"]), {"A": 0.5, "B": 0.5})

    def test_membership_is_computed_before_display(self):
        result = data.membership_change(["North", "South", "West"], ["North", "West", "South"])
        self.assertEqual(result["entered"], [])
        self.assertEqual(result["exited"], [])
        self.assertEqual(result["current_count"], 3)


if __name__ == "__main__":
    unittest.main()
