"""Described Parquet products, fixed input selections, and replay publication.

Adapted from longDS-codex for portable, standalone workspaces (2026-10-22).

Sources are checked declarations, not automatic Python data-flow provenance.
Use through the analysis-state CLI so the active turn environment is bound.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

PROTOCOL_VERSION = "analysis-state-v1"
SCHEMA_VERSION = 1
SOFT_TABLE_BUDGET = 2
_SAVED = set()


def rank_percentiles(values, *, singleton=None):
    """Return one-based average ranks / nonmissing count * 100, not midrank CDF.

    Preserve the Series index and missing values. Override a lone valid value
    only when the caller supplies its requested singleton convention.
    """
    import pandas as pd
    series = pd.Series(values)
    count = series.count()
    result = series.rank(method="average") / count * 100
    if count == 1 and singleton is not None:
        result.loc[series.notna()] = singleton
    return result


def unique_group_weights(groups):
    """Give each distinct group equal weight, preserving first occurrence order.

    Supply hashable labels already mapped according to the user's group rules;
    this function performs no mapping. Empty input produces an empty mapping.
    """
    unique = list(dict.fromkeys(groups))
    return {group: 1 / len(unique) for group in unique}


def membership_change(previous, current):
    """Compare complete ordered ID sets without mapping or display truncation.

    Deduplicate by first occurrence. Entered and retained follow current order;
    exited follows previous order. Counts refer to the complete distinct sets.
    """
    previous = list(dict.fromkeys(previous))
    current = list(dict.fromkeys(current))
    before, after = set(previous), set(current)
    return dict(entered=[item for item in current if item not in before],
                retained=[item for item in current if item in before],
                exited=[item for item in previous if item not in after],
                previous_count=len(previous), current_count=len(current))


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(path)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def object_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def required_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Required nonempty text: {label}")
    return value


def required_file(path):
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        raise ValueError(f"Required nonempty file: {path}")


def current_binding():
    return {"turn_id": int(os.environ["ANALYSIS_TURN_ID"]),
            "prompt_sha256": os.environ["ANALYSIS_PROMPT_SHA256"]}


def workspace_path(root, relative):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError(f"Expected workspace-relative path: {relative}")
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path escapes workspace: {relative}")
    return path


def protocol_metadata():
    return dict(version=PROTOCOL_VERSION, schema_version=SCHEMA_VERSION,
                soft_table_budget=SOFT_TABLE_BUDGET)


def check_protocol(root):
    marker = root / "data_catalog_version.json"
    if not marker.is_file() or read(marker) != protocol_metadata():
        raise ValueError("Incompatible Parquet workspace; open it with the version that created it")


def catalog(root):
    value = read(root / "data_index.json")
    if not isinstance(value, dict) or any(not isinstance(v, dict) or
            "metadata_file" not in v for v in value.values()):
        raise ValueError("Legacy data index; open it with the version that created it")
    return value


def output_paths(tid, name):
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name):
        raise ValueError("Dataset name must be a lowercase identifier, at most 64 characters")
    data_id = f"t{tid:03}_{name}"
    return data_id, f"data/t{tid:03}/{name}.parquet", f"data/t{tid:03}/{name}.meta.json"


def reference_key(ref):
    if not isinstance(ref, dict) or not ("data_id" in ref or "file" in ref):
        raise ValueError("A source needs a data_id or raw file")
    field = "data_id" if "data_id" in ref else "file"
    return field, required_text(ref[field], field)


def dataset_reference(root, data_id, tid, allow_current=False):
    index = catalog(root)
    if data_id in index:
        entry = index[data_id]
        metadata_file = entry["metadata_file"]
    else:
        match = re.fullmatch(r"t(\d{3,})_([a-z][a-z0-9_]{0,63})", data_id)
        if not allow_current or not match or int(match[1]) != tid:
            raise ValueError(f"Dataset is not published: {data_id}")
        keep = retention(root, tid)["keep"]
        if match[2] not in {x["name"] for x in keep}:
            raise ValueError(f"Source is not a retained current-turn dataset: {data_id}")
        _, _, metadata_file = output_paths(tid, match[2])
    path = workspace_path(root, metadata_file)
    meta = read(path)
    if meta.get("schema_version") != SCHEMA_VERSION or meta.get("data_id") != data_id:
        raise ValueError(f"Dataset metadata identity mismatch: {data_id}")
    if meta["created_turn"] > tid or (not allow_current and meta["created_turn"] >= tid):
        raise ValueError(f"Historical selection must come from an earlier turn: {data_id}")
    analysis_file = f"turns/{meta['created_turn']:03}/analysis_receipt.json"
    if (meta.get("analysis_receipt_file") != analysis_file
            or meta.get("analysis_receipt_sha256") != digest(workspace_path(root, analysis_file))):
        raise ValueError(f"Dataset analysis definitions changed: {data_id}")
    actual = digest(workspace_path(root, meta["file"]))
    if actual != meta["facts"]["sha256"]:
        raise ValueError(f"Dataset content changed: {data_id}")
    if data_id in index and index[data_id] != index_entry(meta, metadata_file):
        raise ValueError(f"Catalog differs from dataset description: {data_id}")
    return dict(kind="dataset", data_id=data_id, file=meta["file"], sha256=actual,
                metadata_file=metadata_file, metadata_sha256=digest(path),
                analysis_receipt_file=analysis_file, analysis_receipt_sha256=meta["analysis_receipt_sha256"])


def raw_reference(root, raw_root, file):
    if not file.startswith("raw/"):
        raise ValueError(f"Raw source must name a concrete raw/ file: {file}")
    relative = file[len("raw/"):]
    path = (raw_root / relative).resolve()
    if not path.is_relative_to(raw_root) or not path.is_file():
        raise ValueError(f"Unknown raw source: {file}")
    manifest = {"raw/" + item["path"]: item for item in read(root / "raw_input_manifest.json")}
    if file not in manifest or digest(path) != manifest[file]["sha256"]:
        raise ValueError(f"Raw source does not match the frozen input manifest: {file}")
    return dict(kind="raw", file=file, sha256=manifest[file]["sha256"])


def resolve_reference(root, raw_root, ref, tid, allow_current=False):
    kind, value = reference_key(ref)
    if kind == "data_id":
        actual = dataset_reference(root, value, tid, allow_current)
        if "file" in ref and ref["file"] != actual["file"]:
            raise ValueError(f"Source path differs from its dataset ID: {value}")
        return actual
    return raw_reference(root, raw_root, value)


def raw_path(file):
    """Resolve a selected raw/ input against the frozen workspace snapshot."""
    root = Path(os.environ["ANALYSIS_WORKSPACE"]).resolve()
    raw_root = Path(os.environ["ANALYSIS_RAW_DATA"]).resolve()
    binding = current_binding()
    check_protocol(root)
    pinned = check_selection(root, raw_root, binding)
    if file not in {ref["file"] for ref in pinned["inputs"] if ref["kind"] == "raw"}:
        raise ValueError(f"Raw input was not selected: {file}")
    raw_reference(root, raw_root, file)
    return raw_root / file[len("raw/"):]


def analysis_receipt(root, binding):
    """Resolve standing definitions plus this turn's explicitly temporary changes."""
    tid = binding["turn_id"]
    turn = root / "turns" / f"{tid:03}"
    changes = read(turn / "analysis.json")
    for group in ("updates", "temporary"):
        if not isinstance(changes.get(group), dict):
            raise ValueError(f"analysis.{group} must be a dictionary")
        for key, item in changes[group].items():
            required_text(key, "definition key")
            if not isinstance(item, dict) or "value" not in item:
                raise ValueError(f"analysis.{group}.{key} needs a value")
            required_text(item.get("reason"), f"analysis.{group}.{key}.reason")
    checks = changes.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("analysis.checks must be a nonempty list")
    for check in checks:
        required_text(check, "analysis check")
    base_turn = changes.get("restore_from_turn", tid - 1)
    if (type(base_turn) is not int or base_turn < 0 or base_turn >= tid
            or ("restore_from_turn" in changes and base_turn == 0)):
        raise ValueError("restore_from_turn must name an earlier published turn")
    base, standing = None, {}
    if base_turn:
        folder = root / "turns" / f"{base_turn:03}"
        publication = read(folder / "publication.json")
        prior = read(folder / "analysis_receipt.json")
        prior_hash = digest(folder / "analysis_receipt.json")
        if (publication.get("protocol") != PROTOCOL_VERSION or publication.get("turn_id") != base_turn
                or prior.get("protocol") != PROTOCOL_VERSION or prior.get("turn_id") != base_turn
                or publication.get("analysis_receipt_sha256") != prior_hash
                or publication["verification_sha256"] != digest(folder / "verification.json")
                or read(folder / "verification.json")["analysis_receipt_sha256"] != prior_hash):
            raise ValueError("Published analysis state changed")
        base = dict(turn_id=base_turn, analysis_receipt_sha256=prior_hash)
        standing = dict(prior["standing"])
    standing.update({key: item["value"] for key, item in changes["updates"].items()})
    effective = {**standing, **{key: item["value"] for key, item in changes["temporary"].items()}}
    return dict(protocol=PROTOCOL_VERSION, **binding, analysis_sha256=digest(turn / "analysis.json"),
                base=base, standing=standing, effective=effective, checks=checks)


def check_analysis(root, binding):
    turn = root / "turns" / f"{binding['turn_id']:03}"
    receipt = read(turn / "analysis_receipt.json")
    if receipt != analysis_receipt(root, binding):
        raise ValueError("Analysis definitions changed; return to inspect")
    return receipt


def analysis_context():
    """Return this turn's effective definitions; checks remain semantic obligations."""
    root = Path(os.environ["ANALYSIS_WORKSPACE"]).resolve()
    check_protocol(root)
    return check_analysis(root, current_binding())["effective"]


def pin_selection(root, raw_root, binding):
    tid = binding["turn_id"]
    turn = root / "turns" / f"{tid:03}"
    required_file(turn / "plan.md")
    selected = read(turn / "selection.json")
    if not isinstance(selected.get("inputs"), list):
        raise ValueError("selection.inputs must be a list")
    if not selected["inputs"]:
        required_text(selected.get("notes"), "selection.notes for no inputs")
    resolved, seen = [], set()
    for ref in selected["inputs"]:
        if ("data_id" in ref) == ("file" in ref):
            raise ValueError("Select exactly one of data_id or file for each input")
        required_text(ref.get("purpose"), "input purpose")
        required_text(ref.get("reason"), "input selection reason")
        actual = resolve_reference(root, raw_root, ref, tid)
        key = reference_key(ref)
        if key in seen:
            raise ValueError(f"Duplicate selected input: {key[1]}")
        seen.add(key)
        role = ref.get("role", "data")
        if role not in {"data", "historical_result", "context"}:
            raise ValueError(f"Unknown input role: {role}")
        resolved.append({**actual, "role": role, "purpose": ref["purpose"], "reason": ref["reason"]})
    pinned = dict(protocol=PROTOCOL_VERSION, **binding,
                  selection_sha256=digest(turn / "selection.json"), inputs=resolved,
                  analysis_receipt_sha256=digest(turn / "analysis_receipt.json"),
                  catalog_sha256=object_digest(catalog(root)),
                  raw_manifest_sha256=digest(root / "raw_input_manifest.json"))
    write(turn / "selection_receipt.json", pinned)
    return pinned


def check_selection(root, raw_root, binding):
    turn = root / "turns" / f"{binding['turn_id']:03}"
    pinned = read(turn / "selection_receipt.json")
    if any(pinned.get(k) != v for k, v in binding.items()) or pinned.get("protocol") != PROTOCOL_VERSION:
        raise ValueError("Selection belongs to another turn or prompt; return to inspect")
    if pinned["selection_sha256"] != digest(turn / "selection.json"):
        raise ValueError("Selection changed; return to inspect before replay")
    check_analysis(root, binding)
    if pinned["analysis_receipt_sha256"] != digest(turn / "analysis_receipt.json"):
        raise ValueError("Analysis receipt changed; return to inspect")
    if pinned["raw_manifest_sha256"] != digest(root / "raw_input_manifest.json"):
        raise ValueError("Frozen raw manifest changed")
    for ref in pinned["inputs"]:
        key = "data_id" if ref["kind"] == "dataset" else "file"
        actual = resolve_reference(root, raw_root, {key: ref[key]}, binding["turn_id"])
        if any(ref.get(k) != v for k, v in actual.items()):
            raise ValueError(f"Selected input changed: {ref[key]}")
    return pinned


def load_dataset(data_id):
    """Read one pinned Parquet input; log replay reads, not causal data lineage."""
    import pandas as pd
    root = Path(os.environ["ANALYSIS_WORKSPACE"]).resolve()
    raw_root = Path(os.environ["ANALYSIS_RAW_DATA"]).resolve()
    binding = current_binding()
    check_protocol(root)
    pinned = check_selection(root, raw_root, binding)
    selected = {ref["data_id"]: ref for ref in pinned["inputs"] if ref["kind"] == "dataset"}
    if data_id not in selected:
        raise ValueError(f"Dataset was not selected: {data_id}")
    actual = dataset_reference(root, data_id, binding["turn_id"])
    frame = pd.read_parquet(workspace_path(root, actual["file"]), engine="pyarrow")
    if os.environ.get("ANALYSIS_REPLAY") == "1":
        turn = root / "turns" / f"{binding['turn_id']:03}"
        reads = read(turn / "input_reads.json")
        if (any(reads.get(k) != v for k, v in binding.items())
                or reads.get("selection_receipt_sha256") != digest(turn / "selection_receipt.json")):
            raise ValueError("Input read log belongs to another replay selection")
        reads["reads"][data_id] = actual
        write(turn / "input_reads.json", reads)
    return frame


def check_input_reads(root, binding, pinned):
    turn = root / "turns" / f"{binding['turn_id']:03}"
    logged = read(turn / "input_reads.json")
    if (logged.get("protocol") != PROTOCOL_VERSION
            or any(logged.get(k) != v for k, v in binding.items())
            or logged.get("selection_receipt_sha256") != digest(turn / "selection_receipt.json")):
        raise ValueError("Wrong replay input read log")
    selected = {ref["data_id"]: ref for ref in pinned["inputs"] if ref["kind"] == "dataset"}
    required = {data_id for data_id, ref in selected.items() if ref["role"] != "context"}
    reads = logged["reads"]
    if required - reads.keys():
        raise ValueError(f"Selected datasets not loaded during replay: {sorted(required - reads.keys())}")
    for data_id, actual in reads.items():
        if data_id not in selected or actual != dataset_reference(root, data_id, binding["turn_id"]):
            raise ValueError(f"Replay read differs from pinned dataset: {data_id}")
    return reads


def retention(root, tid):
    value = read(root / "turns" / f"{tid:03}" / "retention.json")
    if not isinstance(value.get("keep"), list):
        raise ValueError("retention.keep must be a list")
    names = []
    for item in value["keep"]:
        output_paths(tid, item["name"])
        names.append(item["name"])
        required_text(item.get("reason"), "retention reason")
    if len(set(names)) != len(names):
        raise ValueError("Duplicate retained dataset name")
    if not names:
        required_text(value.get("skip_reason"), "skip_reason for zero retention")
    if tid > 1 and len(names) > SOFT_TABLE_BUDGET:
        required_text(value.get("exception_reason"), "exception_reason above the table budget")
        for item in value["keep"]:
            required_text(item.get("independent_reason"), f"independent_reason for {item['name']}")
    return value


def check_description(description):
    required_text(description.get("summary"), "summary")
    sources = description.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Description needs concrete sources")
    for source in sources:
        reference_key(source)
        required_text(source.get("usage"), "source usage")
    steps = description.get("processing_steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("processing_steps must be a nonempty ordered list")
    for step in steps:
        required_text(step, "processing step")
    semantics = description.get("semantics", {})
    for field in ("grain", "population", "filters"):
        required_text(semantics.get(field), f"semantics.{field}")
    if not isinstance(semantics.get("metrics"), dict):
        raise ValueError("semantics.metrics must be a dictionary (may be empty)")
    for definition in semantics["metrics"].values():
        required_text(definition, "metric definition")
    usage = description.get("usage", {})
    required_text(usage.get("purpose"), "usage.purpose")
    if usage.get("scope") not in {"standing", "temporary"}:
        raise ValueError("usage.scope must be standing or temporary")


def source_records(root, raw_root, description, binding, pinned):
    selected = {reference_key(x): x for x in pinned["inputs"]}
    tid = binding["turn_id"]
    current_ids = {output_paths(tid, item["name"])[0] for item in retention(root, tid)["keep"]}
    result = []
    for source in description["sources"]:
        key = reference_key(source)
        if key not in selected and not (key[0] == "data_id" and key[1] in current_ids):
            raise ValueError(f"Source was not selected or retained this turn: {key[1]}")
        if key[0] == "data_id" and key in selected and selected[key]["role"] == "context":
            raise ValueError(f"A context dataset cannot be a computational source: {key[1]}")
        actual = resolve_reference(root, raw_root, source, tid, allow_current=True)
        result.append({**actual, "usage": source["usage"]})
    return result


def table_facts(path):
    import pandas as pd
    frame = pd.read_parquet(path, engine="pyarrow")
    return dict(row_count=len(frame), columns=list(frame.columns),
                dtypes={str(k): str(v) for k, v in frame.dtypes.items()}, sha256=digest(path))


def save_dataset(df, name, description):
    """Save one selected product; return its description without publishing it."""
    root = Path(os.environ["ANALYSIS_WORKSPACE"]).resolve()
    raw_root = Path(os.environ["ANALYSIS_RAW_DATA"]).resolve()
    binding = current_binding()
    tid = binding["turn_id"]
    check_protocol(root)
    assert_unpublished(root, tid)
    pinned = check_selection(root, raw_root, binding)
    kept = {item["name"]: item for item in retention(root, tid)["keep"]}
    if name not in kept:
        raise ValueError(f"Dataset is not in retention.keep: {name}")
    identity = (str(root), tid, name)
    if identity in _SAVED:
        raise ValueError(f"Dataset name was saved twice in one execution: {name}")
    check_description(description)
    sources = source_records(root, raw_root, description, binding, pinned)
    data_id, file, metadata_file = output_paths(tid, name)
    if any(s.get("data_id") == data_id for s in sources):
        raise ValueError("Dataset cannot be its own source")
    path = workspace_path(root, file)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, engine="pyarrow", index=False)
    meta = dict(schema_version=SCHEMA_VERSION, data_id=data_id,
                name=description.get("name", name), file=file, created_turn=tid,
                summary=description["summary"], sources=sources,
                processing_steps=description["processing_steps"], semantics=description["semantics"],
                usage={**description["usage"], "retention_reason": kept[name]["reason"]},
                analysis_receipt_file=f"turns/{tid:03}/analysis_receipt.json",
                analysis_receipt_sha256=digest(root / "turns" / f"{tid:03}" / "analysis_receipt.json"),
                producer=f"turns/{tid:03}/solve.py", facts=table_facts(path))
    write(workspace_path(root, metadata_file), meta)
    _SAVED.add(identity)
    return meta


def index_entry(meta, metadata_file):
    return {key: meta[key] for key in ("name", "summary", "created_turn", "file")} | {"metadata_file": metadata_file}


def assert_unpublished(root, tid):
    if (root / "turns" / f"{tid:03}" / "publication.json").exists() or any(
            row["created_turn"] == tid for row in catalog(root).values()):
        raise ValueError("Turn is already published; do not replay or clear published data")


def validate_outputs(root, raw_root, binding, pinned, kept):
    tid = binding["turn_id"]
    expected = set()
    outputs = {}
    for item in kept["keep"]:
        data_id, file, metadata_file = output_paths(tid, item["name"])
        expected.update((file, metadata_file))
        meta = read(workspace_path(root, metadata_file))
        if (meta.get("data_id"), meta.get("created_turn"), meta.get("file"), meta.get("schema_version")) != (
                data_id, tid, file, SCHEMA_VERSION):
            raise ValueError(f"Wrong metadata identity: {data_id}")
        if meta.get("producer") != f"turns/{tid:03}/solve.py":
            raise ValueError(f"Wrong producer: {data_id}")
        analysis_file = f"turns/{tid:03}/analysis_receipt.json"
        if (meta.get("analysis_receipt_file") != analysis_file
                or meta.get("analysis_receipt_sha256") != digest(workspace_path(root, analysis_file))):
            raise ValueError(f"Wrong analysis definitions: {data_id}")
        required_text(meta.get("name"), "dataset name")
        check_description(meta)
        if meta["usage"].get("retention_reason") != item["reason"]:
            raise ValueError(f"Stale retention reason: {data_id}")
        if meta["facts"] != table_facts(workspace_path(root, file)):
            raise ValueError(f"Description facts differ from Parquet: {data_id}")
        if source_records(root, raw_root, meta, binding, pinned) != meta["sources"]:
            raise ValueError(f"Source identity changed: {data_id}")
        if any(s.get("data_id") == data_id for s in meta["sources"]):
            raise ValueError("Dataset cannot be its own source")
        outputs[data_id] = dict(file=file, metadata_file=metadata_file,
                                sha256=digest(workspace_path(root, file)),
                                metadata_sha256=digest(workspace_path(root, metadata_file)))
    folder = workspace_path(root, f"data/t{tid:03}")
    actual = {str(p.relative_to(root)).replace(os.sep, "/") for p in folder.rglob("*") if p.is_file()} if folder.exists() else set()
    if actual != expected:
        raise ValueError(f"Saved files differ from retention.keep: extra={sorted(actual-expected)}, missing={sorted(expected-actual)}")
    return outputs


def check_final(root, raw_root, binding):
    turn = root / "turns" / f"{binding['turn_id']:03}"
    required_file(turn / "review.md")
    required_file(root / "memory.md")
    receipt = read(turn / "verification.json")
    if receipt.get("protocol") != PROTOCOL_VERSION or any(receipt.get(k) != v for k, v in binding.items()):
        raise ValueError("Wrong verification turn, prompt, or protocol")
    if receipt.get("exit_code") != 0:
        raise ValueError("Replay was not successful")
    for key, name in (("script_sha256", "solve.py"), ("answer_sha256", "answer.json"),
                      ("selection_sha256", "selection.json"), ("selection_receipt_sha256", "selection_receipt.json"),
                      ("analysis_sha256", "analysis.json"), ("analysis_receipt_sha256", "analysis_receipt.json"),
                      ("input_reads_sha256", "input_reads.json"),
                      ("retention_sha256", "retention.json")):
        if digest(turn / name) != receipt[key]:
            raise ValueError(f"Stale verification: {name}; return and replay")
    for name, expected in receipt["code_sha256"].items():
        if digest(workspace_path(root, name)) != expected:
            raise ValueError(f"Stale code dependency: {name}")
    if digest(Path(__file__)) != receipt["helper_sha256"]:
        raise ValueError("Parquet helper changed after replay")
    pinned = check_selection(root, raw_root, binding)
    if check_input_reads(root, binding, pinned) != receipt["dataset_reads"]:
        raise ValueError("Dataset read evidence changed after replay")
    kept = retention(root, binding["turn_id"])
    actual = validate_outputs(root, raw_root, binding, pinned, kept)
    if actual != receipt["outputs"]:
        raise ValueError("Saved data or descriptions changed after replay")
    publication = turn / "publication.json"
    expected_catalog_hash = (read(publication)["catalog_after_sha256"] if publication.exists()
                             else pinned["catalog_sha256"])
    if object_digest(catalog(root)) != expected_catalog_hash:
        raise ValueError("Published catalog changed outside the accepted turn")
    return receipt


def publish(root, raw_root, binding):
    receipt = check_final(root, raw_root, binding)
    turn = root / "turns" / f"{binding['turn_id']:03}"
    marker = turn / "publication.json"
    receipt_hash = digest(turn / "verification.json")
    if marker.exists():
        prior = read(marker)
        if prior["verification_sha256"] != receipt_hash:
            raise ValueError("Published receipt differs from the accepted replay")
        return receipt["stats"]
    index = catalog(root)
    for data_id, entry in receipt["outputs"].items():
        if data_id in index:
            raise ValueError(f"Cannot replace published dataset: {data_id}")
        index[data_id] = index_entry(read(workspace_path(root, entry["metadata_file"])), entry["metadata_file"])
    write(root / "data_index.json", index)
    write(marker, dict(protocol=PROTOCOL_VERSION, **binding,
                       verification_sha256=receipt_hash, catalog_after_sha256=object_digest(index),
                       analysis_receipt_sha256=receipt["analysis_receipt_sha256"],
                       data_ids=list(receipt["outputs"]), stats=receipt["stats"]))
    return receipt["stats"]


def gate(stage, root, binding, raw_root):
    root, raw_root = Path(root).resolve(), Path(raw_root).resolve()
    binding = binding or current_binding()
    tid = binding["turn_id"]
    turn = root / "turns" / f"{tid:03}"
    check_protocol(root)
    result = dict(ok=True, stage=stage, turn_id=tid)
    if stage == "plan":
        assert_unpublished(root, tid)
        write(turn / "analysis_receipt.json", analysis_receipt(root, binding))
        pin_selection(root, raw_root, binding)
    elif stage == "ready":
        check_selection(root, raw_root, binding)
        required_file(turn / "solve.py")
        required_file(turn / "review.md")
    elif stage == "replay":
        required_file(turn / "solve.py")
        required_file(turn / "review.md")
        pinned = check_selection(root, raw_root, binding)
        kept = retention(root, tid)
        assert_unpublished(root, tid)
        if object_digest(catalog(root)) != pinned["catalog_sha256"]:
            raise ValueError("Catalog changed after input selection")
        folder = workspace_path(root, f"data/t{tid:03}")
        if folder.exists():
            shutil.rmtree(folder)
        (turn / "verification.json").unlink(missing_ok=True)
        (turn / "input_reads.json").unlink(missing_ok=True)
        write(turn / "input_reads.json", dict(protocol=PROTOCOL_VERSION, **binding,
              selection_receipt_sha256=digest(turn / "selection_receipt.json"), reads={}))
        fixed_files = {"script_sha256": "solve.py", "selection_sha256": "selection.json",
                       "selection_receipt_sha256": "selection_receipt.json", "retention_sha256": "retention.json",
                       "analysis_sha256": "analysis.json", "analysis_receipt_sha256": "analysis_receipt.json"}
        fixed_hashes = {key: digest(turn / name) for key, name in fixed_files.items()}
        env = {**os.environ, "ANALYSIS_TURN_ID": str(tid),
               "ANALYSIS_PROMPT_SHA256": binding["prompt_sha256"],
               "ANALYSIS_WORKSPACE": str(root), "ANALYSIS_RAW_DATA": str(raw_root), "ANALYSIS_REPLAY": "1"}
        started = time.monotonic()
        process = subprocess.run([sys.executable, str(turn / "solve.py")], cwd=root,
                                 text=True, capture_output=True, timeout=300, env=env)
        elapsed = time.monotonic() - started
        (turn / "replay.stderr.log").write_text(process.stderr, encoding="utf-8")
        if process.returncode:
            raise ValueError(f"solve.py exited {process.returncode}: {process.stderr[-3000:]}")
        for key, name in fixed_files.items():
            if digest(turn / name) != fixed_hashes[key]:
                raise ValueError(f"Replay changed fixed file {name}; prepare it before replay")
        answer = json.loads(process.stdout)
        if answer is None or answer == {} or answer == [] or answer == "":
            raise ValueError("Empty answer")
        write(turn / "answer.json", answer)
        pinned = check_selection(root, raw_root, binding)
        dataset_reads = check_input_reads(root, binding, pinned)
        if object_digest(catalog(root)) != pinned["catalog_sha256"]:
            raise ValueError("solve.py must not edit the published data index")
        outputs = validate_outputs(root, raw_root, binding, pinned, kept)
        hashes = {}
        for data_id, entry in {**catalog(root), **outputs}.items():
            meta = read(workspace_path(root, entry["metadata_file"]))
            hashes.setdefault(meta["facts"]["sha256"], []).append(data_id)
        duplicates = [ids for ids in hashes.values() if len(ids) > 1 and any(i in outputs for i in ids)]
        stats = dict(retained_count=len(outputs), over_budget=tid > 1 and len(outputs) > SOFT_TABLE_BUDGET,
                     initialization=tid == 1, soft_table_budget=SOFT_TABLE_BUDGET,
                     exception_reason=kept.get("exception_reason", ""),
                     duplicate_content_groups=duplicates, selected_input_count=len(pinned["inputs"]))
        receipt = dict(protocol=PROTOCOL_VERSION, schema_version=SCHEMA_VERSION, **binding,
                       verified_at=time.time(), exit_code=0, replay_seconds=elapsed,
                       **fixed_hashes, answer_sha256=digest(turn / "answer.json"),
                       input_reads_sha256=digest(turn / "input_reads.json"), dataset_reads=dataset_reads,
                       helper_sha256=digest(Path(__file__)),
                       selected_inputs=pinned["inputs"], outputs=outputs, stats=stats,
                       code_sha256={str(p.relative_to(root)).replace(os.sep, "/"): digest(p)
                                    for p in sorted(root.rglob("*.py")) if ".statem" not in p.relative_to(root).parts})
        write(turn / "verification.json", receipt)
        result["stats"] = stats
    elif stage == "final":
        result["stats"] = check_final(root, raw_root, binding)["stats"]
    elif stage == "publish":
        result["stats"] = publish(root, raw_root, binding)
    else:
        raise ValueError(stage)
    print(json.dumps(result, ensure_ascii=False))
    return result
