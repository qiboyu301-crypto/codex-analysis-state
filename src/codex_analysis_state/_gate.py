"""Internal StateM transition checks; invoked by the generated runbook."""

import sys

from . import data
from .workspace import active_turn, binding, environment, find_workspace, runtime


def main():
    stage = sys.argv[1]
    expected = {"plan": "inspect", "ready": "solve", "replay": "retain", "final": "verify"}
    root = find_workspace()
    active = active_turn(root)
    if runtime(root, active).cur()["current"] != expected[stage]:
        raise ValueError("The gate does not match the active workflow node.")
    with environment(root, active):
        data.gate(stage, root, binding(active), root / "raw")


if __name__ == "__main__":
    main()
