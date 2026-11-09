#!/usr/bin/env python3
"""Deterministic QA for an image-first scientific asset package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from aesthetic_review import validate_review, refinement_source_errors
except ImportError:  # pragma: no cover - allows direct reuse from another working directory
    validate_review = None


def load_json(root: Path, name: str, errors: list[str]):
    path = root / name
    if not path.is_file():
        errors.append(f"missing {name}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"invalid {name}: {exc}")
        return {}


def find_image(root: Path):
    for name in ("asset.png", "asset.jpg", "asset.jpeg"):
        path = root / name
        if path.is_file():
            return path
    return None


def image_facts(path: Path, errors: list[str], expected_size, background):
    try:
        from PIL import Image
    except ImportError:
        errors.append("Pillow is required for raster alpha and size QA")
        return {}
    try:
        with Image.open(path) as image:
            image.load()
            facts = {"mode": image.mode, "size": list(image.size)}
            if expected_size and list(image.size) != list(expected_size):
                errors.append(f"image size {list(image.size)} != brief target_size_px {list(expected_size)}")
            alpha = image.getchannel("A") if "A" in image.getbands() else None
            if background == "transparent":
                if alpha is None:
                    errors.append("transparent output has no alpha channel")
                else:
                    extrema = list(alpha.getextrema())
                    corners = [alpha.getpixel(pos) for pos in ((0, 0), (image.width - 1, 0), (0, image.height - 1), (image.width - 1, image.height - 1))]
                    edges = [
                        alpha.crop((0, 0, image.width, 1)).getextrema()[1],
                        alpha.crop((0, image.height - 1, image.width, image.height)).getextrema()[1],
                        alpha.crop((0, 0, 1, image.height)).getextrema()[1],
                        alpha.crop((image.width - 1, 0, image.width, image.height)).getextrema()[1],
                    ]
                    bounds = alpha.getbbox()
                    facts.update({"has_alpha": True, "alpha_extrema": extrema, "corner_alpha": corners, "edge_alpha_max": edges, "content_bounds": list(bounds) if bounds else None})
                    if extrema[0] != 0 or extrema[1] != 255:
                        errors.append("transparent output does not contain both transparent and opaque pixels")
                    if not bounds:
                        errors.append("transparent output has no foreground")
                    if any(edges):
                        errors.append("foreground touches an image edge")
            elif background == "opaque":
                if alpha is not None and alpha.getextrema() != (255, 255):
                    errors.append("opaque output contains transparent pixels")
                facts.update({"has_alpha": alpha is not None, "alpha_extrema": list(alpha.getextrema()) if alpha else None})
            return facts
    except (OSError, ValueError) as exc:
        errors.append(f"image read failed: {exc}")
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_dir")
    args = parser.parse_args()
    root = Path(args.asset_dir)
    errors: list[str] = []
    brief = load_json(root, "brief.json", errors)
    texts = load_json(root, "text_manifest.json", errors)
    relations = load_json(root, "relation_manifest.json", errors)
    source = load_json(root, "source_manifest.json", errors)
    generation = load_json(root, "generation-evidence.json", errors)
    aesthetic_path = root / "aesthetic-review.json"
    aesthetic = {}
    aesthetic_qa = None
    review_required = bool(brief.get("aesthetic_review_required") or brief.get("action_contract") or brief.get("refinement_contract") or brief.get("iteration_mode") == "refine")
    if review_required and not aesthetic_path.is_file():
        errors.append("visual review is required by the aesthetic or action contract but aesthetic-review.json is missing")
    if aesthetic_path.is_file():
        aesthetic = load_json(root, "aesthetic-review.json", errors)
        if validate_review is None:
            errors.append("aesthetic review validator is unavailable")
        else:
            aesthetic_qa = validate_review(aesthetic, brief.get("action_contract"), brief.get("refinement_contract"))
            errors.extend("aesthetic review: " + error for error in aesthetic_qa.get("errors", []))
            errors.extend(refinement_source_errors(brief.get("refinement_contract"), brief.get("iteration_mode")))
    image = find_image(root)
    if image is None:
        errors.append("missing asset.png/jpeg")
        facts = {}
    else:
        facts = image_facts(image, errors, brief.get("target_size_px"), brief.get("background"))
    if texts.get("no_extra_text") is not True:
        errors.append("text_manifest.no_extra_text must be true")
    for item in texts.get("texts", []):
        if not item.get("id") or item.get("verbatim") is False:
            errors.append("every listed visible text needs an id and verbatim=true")
    if relations.get("no_unlisted_arrows") is not True:
        errors.append("relation_manifest.no_unlisted_arrows must be true")
    allowed = {"physiology", "mechanism", "risk_association", "decision", "evidence_boundary"}
    for relation in relations.get("relations", []):
        if not all(relation.get(key) for key in ("from", "to", "relation_type", "direction", "source_locator")):
            errors.append("each relation needs from/to/relation_type/direction/source_locator")
        if relation.get("relation_type") not in allowed:
            errors.append(f"invalid relation_type: {relation.get('relation_type')}")
    if not source.get("sources"):
        errors.append("source_manifest.sources is required")
    if brief.get("delivery_mode") == "raster_generation" and generation.get("generation_verified") is not True:
        errors.append("generation-evidence.json does not confirm a verified generation")
    final_sha = generation.get("postprocess", {}).get("final_sha256")
    if image and final_sha:
        actual = hashlib.sha256(image.read_bytes()).hexdigest()
        if actual != final_sha:
            errors.append("final asset hash differs from generation-evidence.json")
    if image and aesthetic and hashlib.sha256(image.read_bytes()).hexdigest() != aesthetic.get("asset_sha256"):
        errors.append("final asset hash differs from aesthetic-review.json")
    if review_required and aesthetic.get("status") != "pass":
        errors.append("aesthetic reviewer has not recommended this candidate")
    if review_required and aesthetic.get("user_acceptance") == "rejected":
        errors.append("user rejected this candidate; an agent score cannot override that feedback")
    result = {
        "ok": not errors,
        "asset_dir": str(root),
        "image": str(image.name) if image else None,
        "image_facts": facts,
        "generation_verified": generation.get("generation_verified"),
        "aesthetic_review": aesthetic_qa,
        "errors": errors,
        "manual_review": [
            "Confirm the model did not add unlisted text, watermark, or unintended anatomy.",
            "Confirm the conceptual illustration is not presented as a quantitative GWAS result."
        ]
    }
    if brief.get("composition_mode") == "scene_centered":
        result["manual_review"].extend([
            "Confirm one visual anchor dominates a coherent scene with its environment and state cue.",
            "Confirm the secondary scientific cue is integrated into the scene rather than a detached icon.",
            "Confirm recognition and scene coherence at approximately 200 px and at the destination figure-slot size."
        ])
    if brief.get("action_contract"):
        result["manual_review"].append("Confirm the required action, attention target, and necessary context all remain visible; aesthetic appeal cannot replace behavioral fidelity.")
    else:
        result["manual_review"].append("Confirm declared composition mode and any listed relations match the rendered image.")
    if brief.get("refinement_contract"):
        result["manual_review"].append("Compare the selected base and refined image directly, including detail crops; verify preserved features and every requested edit rather than inferring improvement from an overall score.")
    if brief.get("palette") == "fresh-academic":
        result["manual_review"].extend([
            "Confirm the structural palette is cool and low-saturation, with coral reserved for the declared state cue.",
            "Confirm the rendering matches the user-approved art direction; flatness alone does not establish quality."
        ])
    (root / "qa.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
