"""Check skill frontmatter, local doc links and pinned source attribution."""

import hashlib
import json
from pathlib import Path
import re

import yaml

root = Path(__file__).resolve().parents[1]
skill = root / "src/codex_analysis_state/resources/skills/analysis-state/SKILL.md"
metadata = yaml.safe_load(skill.read_text(encoding="utf-8").split("---", 2)[1])
assert metadata["name"] == skill.parent.name
assert isinstance(metadata["description"], str) and metadata["description"].strip()
assert len(metadata["name"]) <= 64 and re.fullmatch(r"[a-z0-9-]+", metadata["name"])
for doc in [root / "README.md", root / "README.zh-CN.md", *sorted((root / "docs").glob("*.md")), *sorted(skill.parent.rglob("*.md"))]:
    for target in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
        if "://" in target or target.startswith("#"):
            continue
        path = (doc.parent / target.split("#", 1)[0]).resolve()
        assert path.exists(), f"Broken documentation link: {doc.relative_to(root)} -> {target}"
provenance = json.loads((root / "PROVENANCE.json").read_text())
assert len(provenance["source_commit"]) == 40
for entry in provenance["files"]:
    if entry["role"] == "unmodified StateM runtime":
        assert hashlib.sha256((root / entry["destination"]).read_bytes()).hexdigest() == entry["source_sha256"]
print("Release files: skill metadata, local links and vendored runtime hashes passed.")
