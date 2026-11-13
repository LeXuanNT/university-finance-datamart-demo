"""
Project conventions, checked from dbt's manifest (run `dbt parse` or `dbt build` first).

A dependency-free stand-in for the dbt_project_evaluator package: it fails CI when a model breaks the structure,
naming, documentation or testing rules this project follows (dbt Labs' "How we structure our dbt projects").
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "target" / "manifest.json"
PROJECT = "uni_finance"

# folder -> (allowed name pattern, allowed materializations)
LAYERS = {
    "staging": (r"^stg_[a-z0-9]+__[a-z0-9_]+$", {"view"}),
    "intermediate": (r"^int_[a-z0-9_]+$", {"view", "ephemeral"}),
    "marts": (r"^(dim|fct|rpt|obt)_[a-z0-9_]+$", {"table", "incremental"}),
    "audit": (r"^audit_[a-z0-9_]+$", {"table"}),
}
# Deliberate exceptions, each with its reason.
MAY_READ_SOURCES = {"audit_data_quality": "counts what staging removes or repairs, so it must read the raw rows"}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    nodes = {k: v for k, v in manifest["nodes"].items() if v["package_name"] == PROJECT}
    models = {k: v for k, v in nodes.items() if v["resource_type"] == "model"}
    layer_of = {k: v["path"].split("/")[0] for k, v in models.items()}
    errors = []

    # generic tests attached to each node: (test name, column, kwargs)
    tests = defaultdict(list)
    for node in nodes.values():
        meta = node.get("test_metadata")
        if node["resource_type"] == "test" and meta:
            for parent in node["depends_on"].get("nodes", []):
                tests[parent].append((meta["name"], node.get("column_name")))

    def has_primary_key_test(unique_id: str) -> bool:
        unique = {col for name, col in tests[unique_id] if name == "unique"}
        not_null = {col for name, col in tests[unique_id] if name == "not_null"}
        combination = any(name == "unique_combination_of_columns" for name, _ in tests[unique_id])
        return bool(unique & not_null) or combination

    for unique_id, model in sorted(models.items(), key=lambda kv: kv[1]["path"]):
        name, layer = model["name"], layer_of[unique_id]
        parents = model["depends_on"].get("nodes", [])
        sources = [p for p in parents if p.startswith("source.")]
        parent_layers = {layer_of[p] for p in parents if p in models}

        if layer not in LAYERS:
            errors.append(f"{name}: lives in an unknown folder '{layer}'")
            continue
        pattern, materializations = LAYERS[layer]
        if not re.match(pattern, name):
            errors.append(f"{name}: name does not follow the {layer} convention {pattern}")
        if model["config"]["materialized"] not in materializations:
            errors.append(f"{name}: {layer} models must be {' or '.join(sorted(materializations))}")
        if not model["description"].strip():
            errors.append(f"{name}: has no description")
        if not has_primary_key_test(unique_id):
            errors.append(f"{name}: has no primary-key test (unique + not_null, or unique_combination_of_columns)")
        if not Path(model.get("patch_path") or "").name.startswith("_"):
            errors.append(f"{name}: its properties file should be named _<folder>__models.yml")

        if layer == "staging":
            if len(sources) != 1 or len(parents) != 1:
                errors.append(f"{name}: a staging model reads exactly one source table and nothing else")
            elif not name.startswith(f"stg_{sources[0].split('.')[2]}__"):
                errors.append(f"{name}: name should start with stg_<source>__")
        elif sources and name not in MAY_READ_SOURCES:
            errors.append(f"{name}: only staging models may read sources")
        if layer == "intermediate" and "marts" in parent_layers:
            errors.append(f"{name}: an intermediate model must not depend on a mart")

    # one staging model per source table
    children = defaultdict(list)
    for unique_id, model in models.items():
        if layer_of[unique_id] == "staging":
            for parent in model["depends_on"].get("nodes", []):
                children[parent].append(model["name"])
    for unique_id, source in manifest["sources"].items():
        if source["package_name"] != PROJECT:
            continue
        label = f"source {source['source_name']}.{source['name']}"
        if len(children[unique_id]) != 1:
            errors.append(f"{label}: needs exactly one staging model, found {len(children[unique_id])}")
        if not source["description"].strip():
            errors.append(f"{label}: has no description")

    for node in nodes.values():
        if node["resource_type"] in ("seed", "snapshot") and not node["description"].strip():
            errors.append(f"{node['resource_type']} {node['name']}: has no description")

    # what leaves the warehouse (apps, BI) reads marts, the audit table or snapshots, never staging or intermediate
    for exposure in manifest["exposures"].values():
        for parent in exposure["depends_on"].get("nodes", []):
            if layer_of.get(parent) in ("staging", "intermediate"):
                errors.append(f"exposure {exposure['name']}: must not read {parent.split('.')[-1]} (not a mart)")

    if errors:
        print(f"{len(errors)} convention problem(s):")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Conventions OK: {len(models)} models named, placed, documented and key-tested; "
          f"{len(MAY_READ_SOURCES)} documented exception(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
