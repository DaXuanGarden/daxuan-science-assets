#!/usr/bin/env python3
"""Prepare evidence or validate a review-only visual audit; never judges beauty."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil

from PIL import Image, ImageOps

DOMAINS = ("visual_appeal", "craft", "scientific_fit")
VIEW_NAMES = ("asset", "white", "dark", "thumbnail")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(asset_dir: Path, outdir: Path, figure: Path | None = None, slot=None):
    """Copy evidence and create a pending record. Figure is already composed."""
    asset_dir, outdir = asset_dir.resolve(), outdir.resolve()
    source = asset_dir / "asset.png"
    if bool(figure) != bool(slot):
        raise ValueError("figure and slot must be supplied together")
    if not source.is_file():
        raise ValueError("asset_dir must contain asset.png")
    if outdir.exists() and any(outdir.iterdir()):
        raise ValueError("audit output directory must be empty; choose a new version")
    image = Image.open(source).convert("RGBA")
    context = None
    if figure:
        figure = figure.resolve()
        context = Image.open(figure).convert("RGB")
        x, y, width, height = slot
        if min(x, y) < 0 or min(width, height) <= 0 or x + width > context.width or y + height > context.height:
            raise ValueError("slot must fit inside the already-composed figure")
    outdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, outdir / "asset.png")
    sources = [{"role": "asset", "path": str(source), "sha256": sha(source)}]
    files = [{"id": "asset", "path": "asset.png", "sha256": sha(outdir / "asset.png"), "kind": "view"}]
    for name, background, side in (("white", "#FFFFFF", 600), ("dark", "#223542", 600), ("thumbnail", "#FFFFFF", 200)):
        preview = Image.new("RGBA", (side, side), background)
        contained = ImageOps.contain(image, (side, side), Image.Resampling.LANCZOS)
        preview.alpha_composite(contained, ((side - contained.width) // 2, (side - contained.height) // 2))
        path = outdir / (name + ".png")
        preview.convert("RGB").save(path)
        files.append({"id": name, "path": path.name, "sha256": sha(path), "kind": "view"})
    brief = asset_dir / "brief.json"
    if brief.is_file():
        shutil.copy2(brief, outdir / "brief.json")
        sources.append({"role": "brief", "path": str(brief), "sha256": sha(brief)})
        files.append({"id": "brief", "path": "brief.json", "sha256": sha(outdir / "brief.json"), "kind": "context"})
    if context is not None:
        sources.append({"role": "composed_figure", "path": str(figure), "sha256": sha(figure)})
        for name, preview in (("destination_context", context), ("destination_slot", context.crop((x, y, x + width, y + height))), ("destination_crop", context.crop((max(0, x - 50), max(0, y - 50), min(context.width, x + width + 50), min(context.height, y + height + 50))))):
            path = outdir / (name + ".png")
            preview.save(path)
            files.append({"id": name, "path": path.name, "sha256": sha(path), "kind": "view"})
    evidence = {
        "schema_version": "1.0", "sources": sources, "files": files,
        "asset_size_px": list(image.size), "slot_xywh": list(slot) if slot else None,
        "destination_available": context is not None,
        "scope": "Copied source and display previews only; figure is already composed. No image request or source edit. Pixel sizes do not establish final physical print width."
    }
    dump(outdir / "evidence.json", evidence)
    review = {
        "schema_version": "1.0", "status": "pending", "reviewer": "", "reviewer_type": "agent",
        "user_acceptance": "pending", "asset_sha256": sha(source), "evidence_sha256": sha(outdir / "evidence.json"),
        "views_inspected": [],
        "domain_assessments": {name: {"status": "pending", "note": ""} for name in DOMAINS},
        "strengths": [], "findings": [], "top_actions": [], "verdict": "pending",
        "destination_assessment": {"status": "pending" if context else "not_supplied", "note": ""},
        "science_boundary": "", "limitations": [],
        "scope": "Attributed actual-image review; subjective observations, not an objective beauty score or publication acceptance."
    }
    dump(outdir / "review.json", review)
    return {"ok": True, "audit_dir": str(outdir), "review_status": "pending", "required_views": [item["id"] for item in files if item["kind"] == "view"], "scope": "Evidence prepared; visual review has not occurred."}


def validate(audit_dir: Path):
    errors = []
    try:
        evidence = json.loads((audit_dir / "evidence.json").read_text())
        review = json.loads((audit_dir / "review.json").read_text())
    except (OSError, ValueError) as exc:
        return {"ok": False, "errors": ["cannot read audit records: " + type(exc).__name__]}
    if review.get("schema_version") != "1.0" or review.get("status") != "complete":
        errors.append("review must be schema 1.0 and complete; pending templates are not reviews")
    if not str(review.get("reviewer", "")).strip() or review.get("reviewer_type") not in {"agent", "human", "self_review"}:
        errors.append("an attributed reviewer and valid reviewer_type are required")
    if review.get("user_acceptance") not in {"pending", "accepted", "rejected"}:
        errors.append("user_acceptance must be pending, accepted, or rejected")
    if review.get("evidence_sha256") != sha(audit_dir / "evidence.json"):
        errors.append("evidence.json hash differs from the reviewed evidence")
    sources = evidence.get("sources", [])
    if not sources or not isinstance(sources, list):
        errors.append("evidence needs source provenance")
        sources = []
    for item in sources:
        try:
            if sha(item["path"]) != item["sha256"]:
                errors.append("source hash changed: " + str(item.get("role")))
        except (OSError, KeyError, TypeError):
            errors.append("cannot verify source: " + str(item.get("role")))
    files = evidence.get("files", [])
    if not isinstance(files, list):
        errors.append("evidence files must be a list")
        files = []
    for item in files:
        try:
            path = (audit_dir / item["path"]).resolve()
            if audit_dir.resolve() not in path.parents or sha(path) != item["sha256"]:
                errors.append("snapshot path or hash mismatch: " + str(item.get("id")))
        except (OSError, KeyError, TypeError):
            errors.append("cannot verify snapshot: " + str(item.get("id")))
    asset = next((s for s in sources if s.get("role") == "asset"), {})
    if not asset or review.get("asset_sha256") != asset.get("sha256"):
        errors.append("asset_sha256 must bind the review to the copied source")
    required = {item["id"] for item in files if item.get("kind") == "view"}
    if not set(VIEW_NAMES).issubset(required):
        errors.append("evidence is missing required asset views")
    inspected = review.get("views_inspected")
    if not isinstance(inspected, list) or any(not isinstance(v, str) for v in inspected) or not required.issubset(inspected):
        errors.append("views_inspected must list every required view actually inspected")
    assessments = review.get("domain_assessments", {})
    for domain in DOMAINS:
        item = assessments.get(domain, {}) if isinstance(assessments, dict) else {}
        if item.get("status") not in {"reviewed", "not_observable"} or not item.get("note"):
            errors.append("domain_assessments." + domain + " needs an actual observation or explained not_observable")
    strengths = review.get("strengths")
    if not isinstance(strengths, list) or len(strengths) < 2 or any(not isinstance(s, str) or not s.strip() for s in strengths):
        errors.append("strengths must preserve at least two concrete observed features")
    findings = review.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be a list; an empty list is valid")
        findings = []
    ids = []
    for item in findings:
        if not isinstance(item, dict):
            errors.append("each finding must be an object")
            continue
        finding_id = item.get("id")
        if not isinstance(finding_id, str) or not finding_id or finding_id in ids:
            errors.append("finding IDs must be nonempty and unique")
        ids.append(finding_id)
        if item.get("domain") not in DOMAINS or item.get("severity") not in {"minor", "moderate", "major"} or item.get("confidence") not in {"low", "medium", "high"}:
            errors.append("finding needs a valid domain, severity, and confidence")
        region = item.get("region", {})
        box = region.get("box") if isinstance(region, dict) else None
        if not isinstance(region, dict) or region.get("space") not in {"asset", "context"} or not isinstance(box, list) or len(box) != 4 or any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or not 0 <= n <= 1 for n in box) or not (box[0] < box[2] and box[1] < box[3]):
            errors.append("finding region needs space asset|context and normalized [left, top, right, bottom]")
        elif region["space"] == "context" and not evidence.get("destination_available"):
            errors.append("context finding requires a supplied composed figure")
        visible = item.get("visible_at")
        if not isinstance(visible, list) or not visible or any(v not in {"detail", "thumbnail", "destination"} for v in visible):
            errors.append("finding visible_at must specify detail, thumbnail, or destination")
        elif "destination" in visible and not evidence.get("destination_available"):
            errors.append("destination visibility cannot be claimed without a supplied figure")
        for field in ("observation", "impact", "action", "acceptance"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append("finding needs concrete " + field)
    actions = review.get("top_actions")
    if not isinstance(actions, list) or len(actions) > 3 or len(set(str(x) for x in actions)) != len(actions) or any(a not in ids for a in actions):
        errors.append("top_actions must reference at most three unique finding IDs")
    verdict = review.get("verdict")
    if verdict not in {"keep", "refine", "revise"}:
        errors.append("verdict must be keep, refine, or revise")
    if verdict == "keep" and actions:
        errors.append("keep has no priority edits; optional observations can remain in findings")
    if verdict in {"refine", "revise"} and not actions:
        errors.append("refine or revise needs at least one priority edit")
    dest = review.get("destination_assessment", {})
    expected = "inspected" if evidence.get("destination_available") else "not_supplied"
    if not isinstance(dest, dict) or dest.get("status") != expected or not dest.get("note"):
        errors.append("destination_assessment must describe inspected placement or explicitly not_supplied")
    if not review.get("science_boundary"):
        errors.append("science_boundary is required")
    if not isinstance(review.get("limitations"), list):
        errors.append("limitations must be a list")
    return {"ok": not errors, "errors": errors, "review_status": review.get("status"), "verdict": verdict,
            "findings_checked": len(findings), "priority_edits": len(actions) if isinstance(actions, list) else None,
            "destination_reviewed": expected == "inspected" and dest.get("status") == "inspected",
            "reviewer_type": review.get("reviewer_type"), "user_acceptance": review.get("user_acceptance"),
            "scope": "Record completeness, provenance, and declared review coverage only. This checker does not see images or measure beauty, scientific truth, or publication acceptance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("prepare")
    create.add_argument("asset_dir", type=Path)
    create.add_argument("--outdir", type=Path, required=True)
    create.add_argument("--figure", type=Path, help="Already-composed destination PNG; copied, not overlaid")
    create.add_argument("--slot", nargs=4, type=int, metavar=("X", "Y", "WIDTH", "HEIGHT"))
    check = sub.add_parser("check")
    check.add_argument("audit_dir", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.asset_dir, args.outdir, args.figure, args.slot)
        else:
            result = validate(args.audit_dir)
            dump(args.audit_dir / "audit-qa.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
