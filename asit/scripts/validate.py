#!/usr/bin/env python3
"""Validate the ASIT taxonomy: schema, referential integrity, and ID stability.

Run from anywhere:

    python asit/scripts/validate.py            # validate (CI mode)
    python asit/scripts/validate.py --register-new-ids
                                               # adopt new category ids into
                                               # the id registry (a deliberate,
                                               # reviewable act)

Exit code 0 = clean, 1 = one or more errors. New, unregistered category ids are
an error in CI mode: ids are permanent, so adopting one is done on purpose.

Dependencies: PyYAML, jsonschema.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    sys.exit("jsonschema is required: pip install jsonschema")

ROOT = Path(__file__).resolve().parents[1]
TAX_DIR = ROOT / "taxonomy"
SCHEMA_PATH = TAX_DIR / "schema.json"
TAXONOMY_PATH = TAX_DIR / "taxonomy.yaml"
CONTROLS_PATH = TAX_DIR / "controls.yaml"
REGISTRY_PATH = TAX_DIR / "id_registry.yaml"
INCIDENTS_PATH = ROOT / "incidents" / "incidents.yaml"

VALID_SOURCE_TYPES = {
    "postmortem",
    "cve",
    "vendor_advisory",
    "vendor_report",
    "aiid",
    "research_paper",
    "reputable_reporting",
}


class Report:
    """Accumulates errors and warnings and prints a summary."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def dump(self) -> int:
        for w in self.warnings:
            print(f"  warning: {w}")
        for e in self.errors:
            print(f"  ERROR:   {e}")
        if self.errors:
            print(f"\nFAILED: {len(self.errors)} error(s), "
                  f"{len(self.warnings)} warning(s).")
            return 1
        print(f"\nOK: 0 errors, {len(self.warnings)} warning(s).")
        return 0


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_schema(taxonomy: dict, schema: dict, rep: Report) -> None:
    validator = Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(taxonomy), key=lambda e: e.path):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        rep.error(f"schema at {loc}: {err.message}")


def validate_controls(controls_doc: dict, rep: Report) -> set[str]:
    ids: set[str] = set()
    valid_stages = {"PLAN", "DESIGN", "BUILD", "TEST", "REL", "OPS", "FOUND"}
    for c in controls_doc.get("controls", []):
        cid = c.get("id")
        if not cid:
            rep.error("controls.yaml: a control has no id")
            continue
        if cid in ids:
            rep.error(f"controls.yaml: duplicate control id {cid}")
        ids.add(cid)
        if not c.get("name"):
            rep.error(f"controls.yaml: {cid} has no name")
        if c.get("stage") not in valid_stages:
            rep.error(f"controls.yaml: {cid} has invalid stage {c.get('stage')!r}")
    return ids


def validate_incidents(incidents_doc: dict, rep: Report) -> set[str]:
    ids: set[str] = set()
    for inc in incidents_doc.get("incidents", []):
        iid = inc.get("id")
        if not iid:
            rep.error("incidents.yaml: an incident has no id")
            continue
        if iid in ids:
            rep.error(f"incidents.yaml: duplicate incident id {iid}")
        ids.add(iid)
        for field in ("title", "date", "source_type", "url", "summary"):
            if not inc.get(field):
                rep.error(f"incidents.yaml: {iid} missing required field '{field}'")
        st = inc.get("source_type")
        if st and st not in VALID_SOURCE_TYPES:
            rep.error(f"incidents.yaml: {iid} has invalid source_type {st!r}")
        url = inc.get("url", "")
        if url and not str(url).startswith(("http://", "https://")):
            rep.error(f"incidents.yaml: {iid} url is not a URL: {url!r}")
    return ids


def validate_referential(
    taxonomy: dict,
    control_ids: set[str],
    incident_ids: set[str],
    rep: Report,
) -> None:
    categories = taxonomy.get("categories", [])
    cat_ids = [c["id"] for c in categories if "id" in c]
    seen: set[str] = set()
    for cid in cat_ids:
        if cid in seen:
            rep.error(f"taxonomy.yaml: duplicate category id {cid}")
        seen.add(cid)

    for cat in categories:
        cid = cat.get("id", "<no-id>")

        # id prefix must agree with lifecycle_stage
        stage = cat.get("lifecycle_stage")
        if stage and isinstance(cid, str) and cid.startswith("ASIT-"):
            id_stage = cid.split("-")[1]
            if id_stage != stage:
                rep.error(
                    f"{cid}: id stage '{id_stage}' disagrees with "
                    f"lifecycle_stage '{stage}'"
                )

        for ctrl in cat.get("mitigating_controls", []):
            if ctrl not in control_ids:
                rep.error(f"{cid}: mitigating_controls references unknown {ctrl}")

        for rel in cat.get("related", []):
            if rel not in seen and rel not in cat_ids:
                rep.error(f"{cid}: related references unknown category {rel}")
            if rel == cid:
                rep.error(f"{cid}: related references itself")

        for ref in cat.get("incident_refs", []):
            if ref not in incident_ids:
                rep.error(f"{cid}: incident_refs references unknown {ref}")

        # evidence_status vs incident_refs consistency
        status = cat.get("evidence_status")
        refs = cat.get("incident_refs", [])
        if status == "anticipated" and refs:
            rep.error(
                f"{cid}: evidence_status 'anticipated' must have empty "
                f"incident_refs (found {refs})"
            )
        if status == "documented" and not refs:
            rep.error(
                f"{cid}: evidence_status 'documented' requires at least one "
                f"incident_ref"
            )

        # deprecated hygiene
        if cat.get("status") == "deprecated" and not cat.get("deprecated_by"):
            rep.warn(f"{cid}: deprecated with no deprecated_by (allowed, but note it)")

        # coverage surfacing (not an error — gaps are a feature)
        if cat.get("status") != "deprecated" and not cat.get("mitigating_controls"):
            rep.warn(f"{cid}: no mitigating controls — coverage gap")


def validate_id_stability(
    taxonomy: dict, registry: dict, register_new: bool, rep: Report
) -> None:
    registered = {entry["id"] for entry in registry.get("ids", []) if "id" in entry}
    current = {c["id"] for c in taxonomy.get("categories", []) if "id" in c}

    # ids removed from the taxonomy without deprecation = renumber/reuse risk
    removed = registered - current
    for rid in sorted(removed):
        rep.error(
            f"id_registry: {rid} was registered but is absent from taxonomy.yaml. "
            f"Ids are permanent — deprecate it in place, do not delete."
        )

    # new ids must be deliberately adopted into the registry
    new = current - registered
    if new and not register_new:
        for nid in sorted(new):
            rep.error(
                f"id_registry: {nid} is new and unregistered. Run "
                f"`validate.py --register-new-ids` to adopt it (ids are permanent)."
            )
    elif new and register_new:
        version = taxonomy.get("version", "0.0.0")
        entries = list(registry.get("ids", []))
        for nid in sorted(new):
            entries.append({"id": nid, "first_seen_version": version, "status": "active"})
        registry["ids"] = sorted(entries, key=lambda e: e["id"])
        # Preserve the comment header, then dump the data.
        header_lines = []
        with REGISTRY_PATH.open(encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#") or line.strip() == "":
                    header_lines.append(line)
                else:
                    break
        with REGISTRY_PATH.open("w", encoding="utf-8") as fh:
            fh.write("".join(header_lines))
            yaml.safe_dump(registry, fh, sort_keys=False, default_flow_style=False)
        print(f"  registered {len(new)} new id(s): {', '.join(sorted(new))}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the ASIT taxonomy.")
    parser.add_argument(
        "--register-new-ids",
        action="store_true",
        help="Adopt new category ids into id_registry.yaml (deliberate action).",
    )
    args = parser.parse_args()

    rep = Report()

    for path in (SCHEMA_PATH, TAXONOMY_PATH, CONTROLS_PATH, REGISTRY_PATH, INCIDENTS_PATH):
        if not path.exists():
            rep.error(f"missing file: {path}")
    if rep.errors:
        return rep.dump()

    schema = load_json(SCHEMA_PATH)
    taxonomy = load_yaml(TAXONOMY_PATH)
    controls_doc = load_yaml(CONTROLS_PATH)
    incidents_doc = load_yaml(INCIDENTS_PATH)
    registry = load_yaml(REGISTRY_PATH)

    print(f"Validating {len(taxonomy.get('categories', []))} categories, "
          f"{len(controls_doc.get('controls', []))} controls, "
          f"{len(incidents_doc.get('incidents', []))} incidents.\n")

    validate_schema(taxonomy, schema, rep)
    control_ids = validate_controls(controls_doc, rep)
    incident_ids = validate_incidents(incidents_doc, rep)
    validate_referential(taxonomy, control_ids, incident_ids, rep)
    validate_id_stability(taxonomy, registry, args.register_new_ids, rep)

    return rep.dump()


if __name__ == "__main__":
    sys.exit(main())
