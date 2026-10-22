"""Small command-line adapter; model access remains with the user's Codex CLI."""

import argparse
import json
from pathlib import Path
import sys

from . import __version__, workspace
from ._vendor.statem.core import StatemError


def main(argv=None):
    parser = argparse.ArgumentParser(prog="analysis-state")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a workspace and install its project-scoped skill")
    init.add_argument("workspace", type=Path)
    init.add_argument("--data", type=Path, required=True, help="Directory of raw inputs to copy and fingerprint")
    begin = commands.add_parser("begin", help="Start the next user request")
    begin.add_argument("--request-file", type=Path, required=True)
    commands.add_parser("status", help="Show the active turn and workflow node")
    next_node = commands.add_parser("next", help="Advance or return through the workflow")
    next_node.add_argument("node", choices=list(workspace.NODES))
    commands.add_parser("run", help="Execute the current solve.py with its bound environment")
    commands.add_parser("complete", help="Publish verified data after reaching handoff")
    demo = commands.add_parser("demo", help="Run the deterministic three-turn example; no model calls")
    demo.add_argument("workspace", type=Path, help="New directory for example outputs")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = workspace.create_workspace(args.workspace, args.data)
        elif args.command == "demo":
            from .demo import run_demo
            result = run_demo(args.workspace)
        else:
            root = workspace.find_workspace()
            if args.command == "begin":
                result = workspace.begin(root, args.request_file.read_text(encoding="utf-8"))
            elif args.command == "status":
                result = workspace.status(root)
            elif args.command == "next":
                result = workspace.advance(root, args.node)
            elif args.command == "run":
                return workspace.run_script(root)
            else:
                result = workspace.complete(root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, StatemError) as exc:
        print(f"analysis-state: {exc}", file=sys.stderr)
        if isinstance(exc, StatemError) and exc.details:
            print(json.dumps(exc.details, ensure_ascii=False, indent=2), file=sys.stderr)
        return getattr(exc, "exit_code", 1)
