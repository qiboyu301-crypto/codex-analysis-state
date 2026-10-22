import json
from codex_analysis_state import data

state = data.analysis_context()
original = data.load_dataset("t001_candidates")
assert state["window"] == "2026-01"  # February was explicitly turn-only.
assert original["revenue"].sum() == 240
print(json.dumps({
    "window": state["window"], "candidate_count": len(original),
    "total_revenue": int(original["revenue"].sum()),
    "candidate_members": original["region"].tolist(),
}))
