#!/usr/bin/env python3
"""Recheck recorded SVG fixtures, small renders, and geometry-preserving recolors."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import asset_tool as tool
import methodology_tool
from methodology_render import build_diagram

ROOT = Path(__file__).resolve().parents[1]


def evaluate():
    results = []
    for name in ("chromosome", "mitochondrion", "pipette", "methodology-demo", "deseq2-method"):
        source = ROOT/"assets/examples"/name/"asset.svg"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory(prefix="daxuan-svg-eval-") as directory:
            target = Path(directory)
            palette = target/"palette.json"
            colors_for_test = tool.preset("teal")
            colors_for_test["colors"]["text"] = "#39454B"
            tool.write_json(palette, colors_for_test)
            native = tool.inspect_svg(source)
            supplied_preview = tool.png_inspection(source.with_suffix(".png"))
            preview_width = 1600 if name == "deseq2-method" else 1320 if name == "methodology-demo" else 200
            small_render = tool.render(source, target/"small.png", width=preview_width)
            changed = tool.recolor(source, palette, target/"recolored.svg")
            recolor_render = tool.render(target/"recolored.svg", target/"recolored.png", width=preview_width)
            colors = tool.load_palette(palette)
            bindings = [node.get(attr) == colors[node.get(role)]
                        for node in tool.parse_svg(target/"recolored.svg").iter()
                        for role, attr in tool.ROLE_ATTRS.items() if node.get(role)]
            geometry_match = tool.geometry_digest(tool.parse_svg(source)) == tool.geometry_digest(tool.parse_svg(target/"recolored.svg"))
            assertions = {
                "native_structure": native["ok"],
                "supplied_preview_alpha": supplied_preview["ok"],
                "preview_render_alpha": small_render["ok"],
                "recolor_geometry_unchanged": changed["geometry_preserved"] and geometry_match,
                "all_palette_bindings_updated": bool(bindings) and all(bindings),
                "recolored_render_alpha": recolor_render["ok"],
                "source_unchanged": source.read_bytes() == original,
            }
            if source.with_name("diagram.json").exists():
                plan = json.loads(source.with_name("diagram.json").read_text())
                sources_dir = source.parent if name == "deseq2-method" else None
                assertions["methodology_plan_and_svg_match"] = methodology_tool.check(plan, source, sources_dir)["ok"]
                assertions["recolored_methodology_still_matches"] = methodology_tool.check(plan, target/"recolored.svg", sources_dir)["ok"]
                if name == "deseq2-method":
                    rebuilt = build_diagram(source.with_name("diagram.json"), source.with_name("palette.json"), target/"rebuilt", sources_dir)
                    assertions["paper_source_excerpts_verified"] = rebuilt["qa"]["methodology"]["source_snapshots"]["ok"]
                    assertions["native_svg_reproduces_from_semantic_plan"] = (target/"rebuilt/asset.svg").read_bytes() == source.read_bytes()
            results.append({
                "case": name,
                "input": str(source.relative_to(ROOT)),
                "source_sha256": hashlib.sha256(original).hexdigest(),
                "ok": all(assertions.values()),
                "assertions": assertions,
                "named_groups": native["named_groups"],
                "palette_bindings": native["palette_bindings"],
                "preview_render": small_render["png"],
                "recolor_geometry_sha256": changed["geometry_sha256"],
            })
    return {
        "ok": all(item["ok"] for item in results),
        "evidence_kind": "recorded_fixture",
        "execution": "local_runtime",
        "image_generation_executed": False,
        "summary": {"passed": sum(item["ok"] for item in results), "total": len(results)},
        "cases": results,
        "baseline_output": "missing evidence: no matched model-generation comparison; fixture preservation is checked separately by validate_package.py",
        "human_blind_review": "missing evidence",
        "editor_application_import": "missing evidence",
        "scientific_validity": "generic schematic scope; automated tests do not certify scientific accuracy",
        "claim_scope": "Recorded examples and deterministic tools only; no provider quality or superiority claim.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Write a portable JSON evidence report")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        if args.output and Path(args.output).exists() and not args.force:
            raise FileExistsError("Report exists; choose a new path or use --force")
        result = evaluate()
        if args.output:
            tool.write_json(args.output, result, args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
