import json
import pandas as pd
from codex_analysis_state import data

state = data.analysis_context()
original = data.load_dataset("t001_candidates")
sales = pd.read_csv(data.raw_path("raw/sales.csv"))
measurements = sales.loc[sales["month"].eq(state["window"]), ["region", "revenue"]]
current = original[["region"]].merge(measurements, on="region", validate="one_to_one")
assert set(current["region"]) == set(original["region"])
current = current.sort_values(["revenue", "region"], ascending=[False, True])
assert current["revenue"].sum() == 260  # 120 + 50 + 90 from February's raw rows.
print(json.dumps({
    "window": state["window"], "candidate_count": len(current),
    "membership": data.membership_change(original["region"], current["region"]),
    "total_revenue": int(current["revenue"].sum()),
    "leaders": current.head(state["display_limit"]).to_dict("records"),
}))
