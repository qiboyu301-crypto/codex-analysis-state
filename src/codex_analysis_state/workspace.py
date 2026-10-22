"""Portable workspace lifecycle around the pinned StateM runtime."""

from contextlib import contextmanager, redirect_stdout
from importlib.resources import files
import io
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from . import __version__, data
from ._vendor.statem.core import RunOptions, StatemRuntime

MARKER = ".analysis-state/project.json"
NODES = {
    "inspect": "Read the request, standing definitions and relevant historical descriptions. Write analysis.json, selection.json and plan.md. Run next solve to pin them.",
    "solve": "Use the selected inputs and effective definitions in solve.py. Run the script and record independent checks in review.md. Advance to retain.",
    "retain": "Choose complete reusable tables in retention.json. Save them with data.save_dataset. Run next verify to replay solve.py in a fresh Python process.",
    "verify": "Inspect answer.json, retained data and receipts against the request. Update review.md and memory.md. Successful replay does not establish semantic correctness. Advance to handoff only after review.",
    "handoff": "Run complete to publish verified tables. Answer the user from the checked results. Before publication, return to inspect, solve or retain if a defect is found.",
}
TRANSITIONS = [
    ("inspect", "solve", "plan"), ("solve", "retain", "ready"),
    ("retain", "verify", "replay"), ("verify", "handoff", "final"),
    ("solve", "inspect", None), ("retain", "inspect", None),
    ("retain", "solve", None), ("verify", "inspect", None),
    ("verify", "solve", None), ("verify", "retain", None),
    ("handoff", "inspect", None), ("handoff", "solve", None),
    ("handoff", "retain", None),
]


def resources():
    return Path(str(files("codex_analysis_state").joinpath("resources")))


def find_workspace(start=None):
    start = Path(start or Path.cwd()).expanduser().resolve()
    for candidate in (start, *start.parents):
        if (candidate / MARKER).is_file():
            project = data.read(candidate / MARKER)
            if project["version"] != __version__:
                raise ValueError("Workspace/package versions differ; use the original package version.")
            data.check_protocol(candidate)
            return candidate
    raise ValueError("No analysis workspace found. Run analysis-state init first.")


def create_workspace(target, raw_directory):
    root = Path(target).expanduser().resolve()
    raw = Path(raw_directory).expanduser().resolve()
    if root.exists():
        raise ValueError(f"Workspace must be a new directory: {root}")
    if not raw.is_dir():
        raise ValueError(f"Data directory does not exist: {raw}")
    inputs = sorted(p for p in raw.rglob("*") if p.is_file())
    if not inputs:
        raise ValueError("The data directory has no files.")
    if root.is_relative_to(raw) or any(p.is_symlink() for p in raw.rglob("*")):
        raise ValueError("Use a separate output directory and ordinary input files, without symlinks.")
    root.mkdir(parents=True)
    shutil.copytree(raw, root / "raw")
    manifest = [{"path": p.relative_to(raw).as_posix(), "sha256": data.digest(p)} for p in inputs]
    data.write(root / MARKER, {"version": __version__, "raw_directory": "raw"})
    data.write(root / "raw_input_manifest.json", manifest)
    data.write(root / "data_catalog_version.json", data.protocol_metadata())
    data.write(root / "data_index.json", {})
    (root / "memory.md").write_text("# Analysis notes\n", encoding="utf-8")
    (root / "turns").mkdir()
    skill = resources() / "skills/analysis-state"
    shutil.copytree(skill, root / ".agents/skills/analysis-state")
    (root / "AGENTS.md").write_text(
        "# Analysis workspace\n\n"
        "Use the analysis-state skill for multi-turn analysis of the supplied raw/ data.\n"
        "Run `analysis-state status` to inspect the active turn. Preserve published data\n"
        "and descriptions. The skill and runtime do not grant extra tool permissions.\n",
        encoding="utf-8",
    )
    # The wrapper regenerates this file before each new turn so a relocated
    # completed workspace can use its new path and the active Python environment.
    write_workflow(root)
    return {"workspace": str(root), "input_files": len(inputs), "skill": ".agents/skills/analysis-state"}


def write_workflow(root):
    command = shlex.join([sys.executable, "-m", "codex_analysis_state._gate"])
    edges = []
    for source, target, stage in TRANSITIONS:
        edge = {"from": source, "to": target}
        if stage:
            edge["condition"] = {"type": "command", "run": f"{command} {stage}",
                                 "cwd": str(root), "timeout": 360}
        edges.append(edge)
    data.write(root / ".analysis-state/workflow.json", {
        "name": "analysis-state", "initial": "inspect",
        "nodes": {name: {"prompt": prompt} for name, prompt in NODES.items()}, "edges": edges,
    })


def runtime(root, active=None):
    return StatemRuntime(RunOptions(
        state_dir=root / ".analysis-state/statem", json_mode=True,
        run_id=active["run_id"] if active else None,
    ))


def active_turn(root, *, allow_completed=False):
    path = root / ".analysis-state/active.json"
    if not path.exists():
        raise ValueError("No active turn. Run analysis-state begin --request-file REQUEST.md.")
    active = data.read(path)
    if active["completed"] and not allow_completed:
        raise ValueError("Turn is already completed. Begin the next request.")
    request = root / "turns" / f"{active['turn_id']:03}" / "request.md"
    if data.digest(request) != active["prompt_sha256"]:
        raise ValueError("The recorded request changed after begin.")
    return active


def binding(active):
    return {key: active[key] for key in ("turn_id", "prompt_sha256")}


@contextmanager
def environment(root, active):
    settings = {
        "ANALYSIS_WORKSPACE": str(root), "ANALYSIS_RAW_DATA": str(root / "raw"),
        "ANALYSIS_TURN_ID": str(active["turn_id"]),
        "ANALYSIS_PROMPT_SHA256": active["prompt_sha256"],
    }
    previous = {key: os.environ.get(key) for key in settings}
    os.environ.update(settings)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def begin(root, request):
    if not request.strip():
        raise ValueError("The request must be nonempty.")
    active_path = root / ".analysis-state/active.json"
    tid = 1
    if active_path.exists():
        previous = active_turn(root, allow_completed=True)
        if not previous["completed"]:
            raise ValueError("Finish the active turn before starting another.")
        publication = root / "turns" / f"{previous['turn_id']:03}" / "publication.json"
        if not publication.is_file():
            raise ValueError("Previous turn has no publication receipt.")
        tid = previous["turn_id"] + 1
    turn = root / "turns" / f"{tid:03}"
    turn.mkdir()
    (turn / "request.md").write_text(request, encoding="utf-8")
    write_workflow(root)
    state = runtime(root).start(str(root / ".analysis-state/workflow.json"), fresh=True)
    active = {"turn_id": tid, "prompt_sha256": data.digest(turn / "request.md"),
              "run_id": state["run_id"], "completed": False}
    data.write(active_path, active)
    return {"turn_id": tid, "directory": f"turns/{tid:03}", **state}


def status(root):
    if not (root / ".analysis-state/active.json").exists():
        return {"workspace": str(root), "turn_id": None, "next": "begin"}
    active = active_turn(root, allow_completed=True)
    return {**active, **runtime(root, active).cur()}


def advance(root, target):
    active = active_turn(root)
    with environment(root, active):
        return {"turn_id": active["turn_id"], **runtime(root, active).goto(target)}


def run_script(root):
    active = active_turn(root)
    if runtime(root, active).cur()["current"] not in {"solve", "retain"}:
        raise ValueError("Run solve.py from solve or retain; return there before editing calculations.")
    script = root / "turns" / f"{active['turn_id']:03}" / "solve.py"
    with environment(root, active):
        return subprocess.run([sys.executable, str(script)], cwd=root, check=False).returncode


def complete(root):
    active = active_turn(root)
    if runtime(root, active).cur()["current"] != "handoff":
        raise ValueError("Reach handoff through next verify and next handoff before completing.")
    with environment(root, active), redirect_stdout(io.StringIO()):
        result = data.gate("publish", root, binding(active), root / "raw")
    active["completed"] = True
    data.write(root / ".analysis-state/active.json", active)
    result["answer_file"] = f"turns/{active['turn_id']:03}/answer.json"
    return result
