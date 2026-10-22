"""Deterministic worked example, not an agent evaluation or accuracy claim."""

from pathlib import Path
import shutil

from . import data, workspace

REQUESTS = [
    "Use January 2026. Retain every region with revenue at least 60 as the original candidate group; display only the top two by revenue, breaking ties by region name.",
    "For this request only, measure February revenue for the complete original candidate group. Keep its membership fixed, report entrants/exits and total revenue, and display the top two by February revenue.",
    "Using the standing analysis window again, report the original candidate group's membership, size and total revenue.",
]


def prepare_turn(root, tid):
    """Install a hand-written solution after begin; no model is involved."""
    turn = root / "turns" / f"{tid:03}"
    updates = {key: {"value": value, "reason": "Specified by the first request."} for key, value in {
        "window": "2026-01", "minimum_revenue": 60, "display_limit": 2,
        "membership_source": "t001_candidates",
    }.items()} if tid == 1 else {}
    temporary = {"window": {"value": "2026-02", "reason": "February applies to this request only."}} if tid == 2 else {}
    data.write(turn / "analysis.json", {
        "updates": updates, "temporary": temporary,
        "checks": ["Preserve the complete candidate membership separately from displayed leaders.",
                   "Check revenue totals against hand sums of the source rows."],
    })
    inputs = []
    if tid != 1:
        inputs.append({"data_id": "t001_candidates", "role": "historical_result",
                       "purpose": "Original complete group", "reason": "The user explicitly reuses the original membership."})
    if tid != 3:
        inputs.append({"file": "raw/sales.csv", "purpose": "Monthly revenue",
                       "reason": "The request needs the raw month-specific measurements."})
    data.write(turn / "selection.json", {"inputs": inputs})
    data.write(turn / "retention.json", {
        "keep": [{"name": "candidates", "reason": "Later turns refer to the complete original group."}] if tid == 1 else [],
        "skip_reason": "Reuse the original complete group; no reusable new table is needed." if tid != 1 else "",
    })
    (turn / "plan.md").write_text(
        f"# Turn {tid}\n\n{REQUESTS[tid-1]}\n\nSeparate membership, measurement window and display limit.\n",
        encoding="utf-8",
    )
    (turn / "review.md").write_text(
        "# Independent checks\n\nThe source has January revenues 100, 80, 60 (total 240) and February\n"
        "120, 50, 90 (total 260). The original group has North, South, West.\n"
        "All three remain members in February, although South falls below 60.\n"
        "The two displayed leaders change from North/South to North/West.\n",
        encoding="utf-8",
    )
    shutil.copyfile(workspace.resources() / f"demo/turn{tid}.py", turn / "solve.py")


def run_demo(target):
    workspace.create_workspace(target, workspace.resources() / "demo/raw")
    root = Path(target).expanduser().resolve()
    answers = []
    for tid, request in enumerate(REQUESTS, 1):
        workspace.begin(root, request)
        prepare_turn(root, tid)
        for node in ("solve", "retain", "verify"):
            workspace.advance(root, node)
        (root / "memory.md").write_text(
            "# Analysis notes\n\nStanding month: January 2026. Original group: t001_candidates.\n"
            "Retain all three members; display two leaders. February in turn 2 is temporary.\n",
            encoding="utf-8",
        )
        workspace.advance(root, "handoff")
        workspace.complete(root)
        answers.append(data.read(root / "turns" / f"{tid:03}" / "answer.json"))
    if answers[0]["candidate_count"] != 3 or answers[2]["total_revenue"] != 240:
        raise ValueError("The example did not preserve the original group and standing window.")
    if answers[1]["membership"]["entered"] or answers[1]["membership"]["exited"]:
        raise ValueError("A measurement or display change altered the original membership.")
    return {"kind": "deterministic_worked_example", "model_calls": 0,
            "workspace": str(root), "turns": answers}
