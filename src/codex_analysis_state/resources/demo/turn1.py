import json
import pandas as pd
from codex_analysis_state import data

state = data.analysis_context()
sales = pd.read_csv(data.raw_path("raw/sales.csv"))
candidates = sales.loc[
    sales["month"].eq(state["window"]) & sales["revenue"].ge(state["minimum_revenue"]),
    ["region", "revenue"],
].sort_values(["revenue", "region"], ascending=[False, True])
assert candidates["region"].is_unique
assert candidates["revenue"].sum() == 240  # Hand sum of the three January rows.
data.save_dataset(candidates, "candidates", {
    "summary": "Complete January candidate membership with January revenue",
    "sources": [{"file": "raw/sales.csv", "usage": "January revenue and eligibility"}],
    "processing_steps": ["Select January", "Keep revenue >= 60", "Sort revenue descending, region ascending"],
    "semantics": {
        "grain": "One row per region", "population": "All January candidates",
        "filters": "month = 2026-01 and revenue >= 60",
        "metrics": {"revenue": "January revenue in whole currency units"},
    },
    "usage": {"purpose": "Preserve the complete original group for later measurement changes", "scope": "standing"},
})
print(json.dumps({
    "window": state["window"], "candidate_count": len(candidates),
    "candidate_members": candidates["region"].tolist(),
    "leaders": candidates.head(state["display_limit"]).to_dict("records"),
}))
