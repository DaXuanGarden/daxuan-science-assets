#!/usr/bin/env python3
"""Check a methodology plan's evidence links, topology, and optional SVG bindings."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET

import asset_tool

STATUSES = {"source_supported", "user_specified", "adapted", "proposed", "unresolved"}
RELATIONS = {"sequence", "dataflow", "causal", "activation", "inhibition", "association", "uncertainty"}
ACCESSES = {"full_text", "excerpt", "abstract", "identifier_only", "user_statement"}


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).split())


def source_snapshots(plan, directory):
    """Verify supplied local extracts, not the truth or provenance of publications."""
    base = Path(directory).resolve()
    errors, checked = [], []
    sources = {s["id"]: s for s in plan.get("sources", []) if isinstance(s, dict) and isinstance(s.get("id"), str)}
    content = {}
    for sid, source in sources.items():
        relative = source.get("snapshot")
        if relative is None:
            continue
        try:
            if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
                raise ValueError("snapshot must be a relative text path")
            path = (base / relative).resolve()
            if not path.is_relative_to(base) or path.suffix != ".txt":
                raise ValueError("snapshot must be a .txt file inside the selected sources directory")
            if path.stat().st_size > 5_000_000:
                raise ValueError("snapshot exceeds the 5 MB text limit")
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != source.get("snapshot_sha256"):
                raise ValueError("snapshot_sha256 does not match the local extract")
            content[sid] = normalized(raw.decode("utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(sid + ": " + str(exc))
    for item in plan.get("nodes", []) + plan.get("edges", []):
        if not isinstance(item, dict) or not isinstance(item.get("support"), dict):
            continue
        if item["support"].get("status") not in ("source_supported", "adapted"):
            continue
        for entry in item["support"].get("evidence", []):
            if not isinstance(entry, dict):
                continue
            sid = entry.get("source_id")
            if not isinstance(sid, str) or sid not in sources or sources[sid].get("kind") == "user_brief":
                continue
            prefix = str(item.get("id")) + "/" + sid + ": "
            if sid not in content:
                errors.append(prefix + "no verified local snapshot for this inspected source")
                continue
            for field in ("locator", "excerpt"):
                value = entry.get(field)
                if not isinstance(value, str) or not value.strip() or normalized(value) not in content[sid]:
                    errors.append(prefix + field + " not found in the recorded source extract")
            checked.append({"item": item.get("id"), "source_id": sid})
    return {"ok": not errors, "errors": sorted(set(errors)), "checked_claims": checked,
            "scope": "Recorded extract hash and locator/excerpt containment only; not source authenticity, entailment, completeness, or scientific validity."}


def check(plan, svg=None, sources_dir=None):
    """Check recorded consistency, never truth of a claim or a drawn arrow's geometry."""
    errors, warnings = [], []
    if not isinstance(plan, dict):
        return {"ok": False, "errors": ["Plan must be an object"], "warnings": []}

    def nonempty(value):
        return isinstance(value, str) and bool(value.strip())

    def member(value, choices):
        return isinstance(value, str) and value in choices

    def records(key):
        values = plan.get(key)
        if not isinstance(values, list):
            errors.append(key + " must be a list")
            return {}
        result = {}
        for item in values:
            if not isinstance(item, dict) or not nonempty(item.get("id")):
                errors.append(key + " entries require a nonempty id")
            elif item["id"] in result:
                errors.append("Duplicate " + key + " id: " + item["id"])
            else:
                result[item["id"]] = item
        return result

    if plan.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if not member(plan.get("status"), {"draft", "final"}):
        errors.append("status must be draft or final")
    if not member(plan.get("diagram_kind"), {"principle", "process", "hybrid"}):
        errors.append("diagram_kind must be principle, process, or hybrid")
    for field in ("title", "scope", "provenance_summary"):
        if not nonempty(plan.get(field)):
            errors.append(field + " must be a nonempty string")
    width = plan.get("target_width_mm")
    if isinstance(width, bool) or not isinstance(width, (int, float)) or not math.isfinite(width) or width <= 0:
        errors.append("target_width_mm must be finite and positive")
    if not isinstance(plan.get("content_budget"), dict) or not plan["content_budget"]:
        errors.append("content_budget must describe the selected detail budget")
    questions = plan.get("open_questions")
    if not isinstance(questions, list):
        errors.append("open_questions must be a list")
    elif questions and plan.get("status") == "final":
        errors.append("Final diagrams cannot have open questions")

    sources, nodes, edges = (records(key) for key in ("sources", "nodes", "edges"))
    if not nodes:
        errors.append("At least one node is required")
    budget = plan.get("content_budget")
    if isinstance(budget, dict):
        for field in ("max_nodes", "max_label_words"):
            value = budget.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value <= 0):
                errors.append(field + " must be a positive integer when specified")
        if isinstance(budget.get("max_nodes"), int) and len(nodes) > budget["max_nodes"]:
            errors.append("Node count exceeds the selected content budget; revise scope or budget explicitly")
        if isinstance(budget.get("max_label_words"), int):
            for identifier, node in nodes.items():
                if isinstance(node.get("label"), str) and len(node["label"].split()) > budget["max_label_words"]:
                    errors.append(identifier + ": label exceeds the selected word budget")
    for sid, source in sources.items():
        if not member(source.get("kind"), {"paper", "user_brief", "reference_manual"}):
            errors.append(sid + ": invalid source kind")
        if not member(source.get("access"), ACCESSES):
            errors.append(sid + ": invalid source access")
        if source.get("kind") == "paper" and source.get("access") == "user_statement":
            errors.append(sid + ": a user statement is not inspected paper content")
        if not nonempty(source.get("citation")):
            errors.append(sid + ": record the actual citation or prompt description")

    svg_ids = set()
    for category, items in (("nodes", nodes), ("edges", edges)):
        for identifier, item in items.items():
            prefix = category + "/" + identifier + ": "
            svg_id = item.get("svg_id")
            if not nonempty(svg_id):
                errors.append(prefix + "svg_id is required")
            elif svg_id in svg_ids:
                errors.append(prefix + "svg_id must be unique across nodes and edges")
            else:
                svg_ids.add(svg_id)
            if category == "nodes":
                if not nonempty(item.get("label")):
                    errors.append(prefix + "label is required")
                if not member(item.get("kind"), {"input", "process", "output", "principle", "annotation"}):
                    errors.append(prefix + "invalid node kind")
            else:
                if not member(item.get("from"), nodes) or not member(item.get("to"), nodes):
                    errors.append(prefix + "edge endpoints must reference existing nodes")
                if not member(item.get("relation"), RELATIONS):
                    errors.append(prefix + "invalid relation type")
                if "label" in item and not nonempty(item["label"]):
                    errors.append(prefix + "edge label must be nonempty text when specified")
            support = item.get("support")
            if not isinstance(support, dict):
                errors.append(prefix + "support is required")
                continue
            status = support.get("status") if isinstance(support.get("status"), str) else ""
            level = support.get("claim_level") if isinstance(support.get("claim_level"), str) else ""
            if status not in STATUSES:
                errors.append(prefix + "invalid support status")
            if level not in {"overview", "method_detail"}:
                errors.append(prefix + "claim_level must be overview or method_detail")
            if status in {"adapted", "proposed", "unresolved"} and not nonempty(support.get("note")):
                errors.append(prefix + "this status requires an explanatory note")
            if status == "unresolved":
                if plan.get("status") == "final":
                    errors.append(prefix + "unresolved item in a final diagram")
                else:
                    warnings.append(prefix + "unresolved draft item")
            evidence = support.get("evidence")
            if not isinstance(evidence, list):
                errors.append(prefix + "evidence must be a list")
                continue
            if status in {"source_supported", "user_specified", "adapted"} and not evidence:
                errors.append(prefix + "this status requires evidence")
            inspected = []
            user_evidence = False
            for entry in evidence:
                if not isinstance(entry, dict):
                    errors.append(prefix + "evidence entries must be objects")
                    continue
                source = sources.get(entry.get("source_id")) if nonempty(entry.get("source_id")) else None
                if source is None:
                    errors.append(prefix + "unknown evidence source")
                    continue
                if not nonempty(entry.get("locator")):
                    errors.append(prefix + "evidence requires a real locator")
                if source.get("kind") == "user_brief" and source.get("access") == "user_statement":
                    user_evidence = True
                if member(source.get("kind"), {"paper", "reference_manual"}) and member(source.get("access"), ACCESSES):
                    inspected.append(source.get("access"))
            if status in {"source_supported", "adapted"}:
                allowed = {"full_text", "excerpt"} if level == "method_detail" else {"full_text", "excerpt", "abstract"}
                if not any(access in allowed for access in inspected):
                    errors.append(prefix + "claim needs inspected source content at the claimed detail level")
                elif all(access == "abstract" for access in inspected):
                    warnings.append(prefix + "abstract-only overview; full methods not verified")
            if status == "user_specified" and not user_evidence:
                errors.append(prefix + "user_specified requires a user-statement source")

    snapshots = None
    if sources_dir is not None and not errors:
        snapshots = source_snapshots(plan, sources_dir)
        errors.extend(snapshots["errors"])
    elif any(s.get("snapshot") for s in sources.values()):
        warnings.append("Local source snapshots not checked; supply --sources-dir for excerpt verification")

    if svg is not None:
        try:
            root = asset_tool.parse_svg(svg)
            native = asset_tool.inspect_svg(svg)
            errors.extend(native["errors"])
            by_id = {item.get("id"): item for item in root.iter() if item.get("id")}
            mapped = {"data-node-id": set(nodes), "data-edge-id": set(edges)}
            for element in root.iter():
                for attribute, known in mapped.items():
                    if element.get(attribute) is not None and element.get(attribute) not in known:
                        errors.append("Unplanned semantic SVG item: " + element.get(attribute))
            for attribute, known in mapped.items():
                counts = Counter(element.get(attribute) for element in root.iter() if element.get(attribute) is not None)
                for identifier in known:
                    if counts[identifier] != 1:
                        errors.append(identifier + ": exactly one SVG semantic binding is required")
            for category, items in (("nodes", nodes), ("edges", edges)):
                for identifier, item in items.items():
                    element = by_id.get(item.get("svg_id")) if nonempty(item.get("svg_id")) else None
                    if element is None or element.tag != "{" + asset_tool.SVG + "}g":
                        errors.append(identifier + ": svg_id must resolve to a named group")
                        continue
                    attributes = {"data-node-id": identifier} if category == "nodes" else {
                        "data-edge-id": identifier, "data-from": item.get("from"),
                        "data-to": item.get("to"), "data-relation": item.get("relation")}
                    if any(element.get(key) != value for key, value in attributes.items()):
                        errors.append(identifier + ": SVG semantic attributes differ from the plan")
                    if category == "nodes":
                        labels = [" ".join("".join(label.itertext()).split())
                                  for label in element.iter("{" + asset_tool.SVG + "}text")]
                        if " ".join(str(item.get("label", "")).split()) not in labels:
                            errors.append(identifier + ": native editable label differs from the plan")
                    elif item.get("label"):
                        labels = [normalized("".join(label.itertext())) for label in element.iter("{" + asset_tool.SVG + "}text")]
                        if normalized(str(item["label"])) not in labels:
                            errors.append(identifier + ": native edge label differs from the plan")
        except (OSError, ValueError, ET.ParseError) as exc:
            errors.append("Cannot inspect SVG: " + str(exc))
    return {"ok": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings)),
            "status": plan.get("status"), "counts": {"sources": len(sources), "nodes": len(nodes), "edges": len(edges)},
            "svg_bindings_checked": svg is not None,
            "source_snapshots": snapshots,
            "evidence_scope": "Recorded links, detail/access consistency, topology, and declared SVG bindings only. Does not verify source truth, completeness, drawn arrow geometry, or scientific validity."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("check")
    command.add_argument("plan", type=Path)
    command.add_argument("--svg", type=Path)
    command.add_argument("--sources-dir", type=Path, help="Verify local extract hashes and evidence excerpts")
    command.add_argument("--out", type=Path)
    command.add_argument("--force", action="store_true")
    build = sub.add_parser("build", help="Build a native base diagram from an explicitly laid-out plan")
    build.add_argument("plan", type=Path)
    build.add_argument("--palette", required=True, type=Path)
    build.add_argument("--outdir", required=True, type=Path)
    build.add_argument("--sources-dir", type=Path)
    build.add_argument("--width", type=int, default=1600)
    args = parser.parse_args()
    try:
        if args.command == "build":
            from methodology_render import build_diagram
            result = build_diagram(args.plan, args.palette, args.outdir, args.sources_dir, args.width)
        else:
            result = check(json.loads(args.plan.read_text(encoding="utf-8")), args.svg, args.sources_dir)
        if args.command == "check" and args.out:
            asset_tool.write_json(args.out, result, args.force)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    except (OSError, ValueError, ET.ParseError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": "Local renderer failed" if isinstance(exc, subprocess.SubprocessError) else str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
