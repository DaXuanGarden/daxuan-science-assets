#!/usr/bin/env python3
"""Validate an attributed visual review; this script does not judge image beauty."""
from __future__ import annotations

import argparse
import json
import math
import hashlib
import re
from pathlib import Path

WEIGHTS = {
    "visual_hierarchy": 18,
    "silhouette_readability": 14,
    "palette_harmony": 12,
    "composition_balance": 14,
    "style_coherence": 14,
    "surface_light_craft": 12,
    "detail_economy": 8,
    "destination_slot_readability": 8,
}
REQUIRED_GATES = {"no_extra_text_or_watermark", "verified_alpha", "single_anchor", "no_detached_objects", "thumbnail_recognition", "no_clipping", "brief_style_match"}
DIRECTION_AXES = {"composition", "rendering_language", "silhouette", "lighting_material", "signature_detail"}


def validate_direction_review(review: dict, aesthetic_spec: dict | None) -> tuple[bool, bool, list[str]]:
    directions = aesthetic_spec.get("design_directions") if isinstance(aesthetic_spec, dict) else None
    if not isinstance(directions, list) or len(directions) < 2:
        return False, False, []
    errors: list[str] = []
    expected_ids = [item.get("id") for item in directions if isinstance(item, dict)]
    if len(expected_ids) != len(directions) or any(not isinstance(item, str) or not item for item in expected_ids) or len(set(expected_ids)) != len(expected_ids):
        return False, False, ["brief design_directions must have unique non-empty ids"]
    candidates = review.get("candidate_comparison")
    candidate_rows = [item for item in candidates if isinstance(item, dict)] if isinstance(candidates, list) else []
    candidate_ids = [item.get("direction_id") for item in candidate_rows]
    candidate_map_valid = len(candidate_ids) == len(expected_ids) and not any(not isinstance(item, str) or not item for item in candidate_ids) and set(candidate_ids) == set(expected_ids)
    content_fidelity = candidate_map_valid
    if not candidate_map_valid:
        errors.append("candidate_comparison must include each planned direction_id exactly once")
    for item in candidate_rows:
        if not isinstance(item.get("content_match"), bool) or not isinstance(item.get("science_note"), str) or not item["science_note"].strip():
            errors.append("each candidate_comparison needs content_match and a concrete science_note")
            content_fidelity = False
        elif not item["content_match"]:
            content_fidelity = False
    expected_pairs = {tuple(sorted((left, right))) for index, left in enumerate(expected_ids) for right in expected_ids[index + 1:]}
    comparisons = review.get("direction_comparison")
    if not isinstance(comparisons, list):
        comparisons = []
        errors.append("direction_comparison must review every pair of planned candidates")
    seen_pairs: set[tuple[str, str]] = set()
    all_distinct = True
    for item in comparisons:
        if not isinstance(item, dict):
            errors.append("each direction_comparison needs two ids, visible_axes, verdict, and note")
            all_distinct = False
            continue
        left, right = item.get("direction_a"), item.get("direction_b")
        pair = tuple(sorted((left, right))) if isinstance(left, str) and isinstance(right, str) else None
        if pair not in expected_pairs or pair in seen_pairs:
            errors.append("direction_comparison pairs must match the plan exactly once")
            all_distinct = False
            continue
        seen_pairs.add(pair)
        axes = item.get("visible_axes")
        if not isinstance(axes, list) or any(not isinstance(axis, str) or axis not in DIRECTION_AXES for axis in axes) or len(set(axes)) != len(axes):
            errors.append("direction_comparison.visible_axes must list unique observed design axes")
            axes = []
            all_distinct = False
        verdict = item.get("verdict")
        if not isinstance(verdict, str) or verdict not in {"distinct_direction", "close_variant"} or not isinstance(item.get("note"), str) or not item["note"].strip():
            errors.append("direction_comparison needs a distinct_direction/close_variant verdict and visible note")
            all_distinct = False
        elif verdict == "distinct_direction" and len(axes) < 2:
            errors.append("distinct_direction requires at least two visibly different design axes")
            all_distinct = False
        elif verdict == "close_variant":
            all_distinct = False
    if seen_pairs != expected_pairs:
        errors.append("direction_comparison is missing planned candidate pairs")
        all_distinct = False
    return all_distinct and candidate_map_valid and seen_pairs == expected_pairs and not any("direction_comparison" in error for error in errors), content_fidelity, errors


def validate_review(review: dict, action_contract: dict | None = None, refinement_contract: dict | None = None, *, background: str | None = None, composition_mode: str | None = None, aesthetic_spec: dict | None = None, iteration_mode: str | None = None) -> dict:
    errors: list[str] = []
    required_gates = set(REQUIRED_GATES)
    # Missing options preserve the original transparent-scene caller contract.
    # Explicit brief values scope gates to the requested delivery/composition.
    if background is not None:
        if background not in {"transparent", "opaque", "auto"}:
            errors.append("background must be transparent, opaque, or auto")
        elif background != "transparent":
            required_gates.discard("verified_alpha")
    if composition_mode is not None:
        if composition_mode not in {"scene_centered", "icon_composite", "process_chain"}:
            errors.append("composition_mode must be scene_centered, icon_composite, or process_chain")
        elif composition_mode != "scene_centered":
            required_gates.difference_update({"single_anchor", "no_detached_objects"})
    if action_contract:
        required_gates.add("required_behavior_match")
    planned_directions = aesthetic_spec.get("design_directions") if isinstance(aesthetic_spec, dict) else None
    directions_required = iteration_mode == "explore" and isinstance(planned_directions, list) and len(planned_directions) >= 2
    if directions_required:
        required_gates.update({"candidate_directions_distinct", "candidate_content_fidelity"})
    if refinement_contract:
        if not isinstance(refinement_contract, dict):
            errors.append("refinement_contract must be an object")
            refinement_contract = {"invalid": True}
        required_gates.update({"selected_base_preserved", "requested_edits_addressed"})
        base = refinement_contract.get("base_asset", {})
        base_sha = base.get("sha256") if isinstance(base, dict) else None
        if not re.fullmatch(r"[0-9a-f]{64}", str(base_sha or "")):
            errors.append("refinement contract needs a base_asset sha256")
        if review.get("base_asset_sha256") != base_sha:
            errors.append("base_asset_sha256 must match the selected base in the refinement contract")
        targets = refinement_contract.get("edit_targets")
        if not isinstance(targets, list) or not targets or any(not isinstance(target, str) or not target.strip() for target in targets):
            errors.append("refinement contract needs non-empty edit_targets")
            targets = []
        assessments = review.get("edit_assessment")
        if not isinstance(assessments, list):
            errors.append("edit_assessment must compare each requested edit with the selected base")
            assessments = []
        seen = []
        for item in assessments:
            if not isinstance(item, dict):
                errors.append("each edit_assessment needs target, outcome, and note")
                continue
            target = item.get("target")
            if target not in targets or target in seen:
                errors.append("edit_assessment targets must match the requested edits exactly once")
            seen.append(target)
            if not isinstance(item.get("outcome"), str) or item.get("outcome") not in {"improved", "unchanged", "regressed", "not_visible"} or not item.get("note"):
                errors.append("each edit_assessment needs an observed outcome and concrete note")
            if review.get("status") == "pass" and item.get("outcome") != "improved":
                errors.append("pass requires each requested edit to be observed as improved")
        if any(target not in seen for target in targets):
            errors.append("edit_assessment is missing requested edits")
    if review.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if review.get("status") not in {"pass", "revise", "fail"}:
        errors.append("status must be pass, revise, or fail")
    if not review.get("reviewer"):
        errors.append("reviewer is required")
    if review.get("reviewer_type") not in {"agent", "human", "self_review"}:
        errors.append("reviewer_type must be agent, human, or self_review")
    if review.get("user_acceptance") not in {"pending", "accepted", "rejected"}:
        errors.append("user_acceptance must be pending, accepted, or rejected")
    if not re.fullmatch(r"[0-9a-f]{64}", str(review.get("asset_sha256", ""))):
        errors.append("asset_sha256 must bind the review to an image")
    if not isinstance(review.get("reviewed_images"), list) or len(review["reviewed_images"]) < 2:
        errors.append("reviewed_images must include actual thumbnail and placement images")
    if not isinstance(review.get("candidate_comparison"), list) or len(review["candidate_comparison"]) < 2:
        errors.append("candidate_comparison must include at least two candidates")
    if not review.get("selection_reason"):
        errors.append("selection_reason is required")
    scope = review.get("review_scope")
    if not isinstance(scope, dict):
        errors.append("review_scope must be an object")
    else:
        for key in ("target_px", "thumbnail_px", "slot_px"):
            value = scope.get(key)
            if not (isinstance(value, list) and len(value) == 2 and all(isinstance(v, int) and v > 0 for v in value)):
                errors.append(f"review_scope.{key} must be [width, height]")
    criteria = review.get("criteria")
    if not isinstance(criteria, dict):
        errors.append("criteria must be an object")
        criteria = {}
    scores: dict[str, float] = {}
    for key, weight in WEIGHTS.items():
        item = criteria.get(key)
        if not isinstance(item, dict):
            errors.append(f"criteria.{key} must include score and note")
            continue
        score = item.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 1 <= score <= 5:
            errors.append(f"criteria.{key}.score must be between 1 and 5")
        else:
            scores[key] = float(score)
        if not item.get("note"):
            errors.append(f"criteria.{key}.note is required")
    weighted = sum(scores[key] / 5 * WEIGHTS[key] for key in scores) if len(scores) == len(WEIGHTS) else None
    recorded = review.get("weighted_score")
    if weighted is not None:
        if isinstance(recorded, bool) or not isinstance(recorded, (int, float)) or not math.isfinite(recorded) or abs(float(recorded) - weighted) > 0.11:
            errors.append(f"weighted_score must equal {weighted:.1f} within rounding tolerance")
    gates = review.get("hard_gates")
    if not isinstance(gates, dict) or not gates:
        errors.append("hard_gates must be a non-empty object")
        gates = {}
    for key, value in gates.items():
        if not isinstance(value, bool):
            errors.append(f"hard_gates.{key} must be boolean")
    direction_distinct, content_fidelity, direction_errors = validate_direction_review(review, aesthetic_spec) if directions_required else (False, False, [])
    errors.extend(direction_errors)
    direction_gate_consistent = not directions_required or gates.get("candidate_directions_distinct") is direction_distinct
    if not direction_gate_consistent:
        errors.append("hard_gates.candidate_directions_distinct must match the observed pairwise direction review")
    content_gate_consistent = not directions_required or gates.get("candidate_content_fidelity") is content_fidelity
    if not content_gate_consistent:
        errors.append("hard_gates.candidate_content_fidelity must match the per-candidate science review")
    if not required_gates.issubset(gates):
        errors.append("hard_gates is missing required gates: " + ", ".join(sorted(required_gates - gates.keys())))
    scoped_gates = {"verified_alpha", "single_anchor", "no_detached_objects"}
    applicable_gates = {key: value for key, value in gates.items() if key not in scoped_gates or key in required_gates}
    if not review.get("selected_candidate"):
        errors.append("selected_candidate is required")
    if not review.get("science_boundary"):
        errors.append("science_boundary is required")
    if review.get("status") == "pass":
        if weighted is None or weighted < 80:
            errors.append("pass requires weighted_score >= 80")
        if any(score < 3 for score in scores.values()):
            errors.append("pass requires every criterion score >= 3")
        if applicable_gates and not all(applicable_gates.values()):
            errors.append("pass requires every hard gate to be true")
    return {
        "ok": not errors,
        "errors": errors,
        "weighted_score": round(weighted, 1) if weighted is not None else None,
        "criteria_checked": len(scores),
        "hard_gates_passed": required_gates.issubset(gates) and all(applicable_gates.values()) and direction_gate_consistent and content_gate_consistent and (not directions_required or direction_distinct and content_fidelity),
        "required_gates": sorted(required_gates),
        "nonapplicable_gates": sorted(set(gates) - set(applicable_gates)),
        "required_behavior_reviewed": bool(action_contract) and isinstance(gates.get("required_behavior_match"), bool),
        "selected_base_refinement_reviewed": bool(refinement_contract) and {"selected_base_preserved", "requested_edits_addressed"}.issubset(gates),
        "candidate_direction_diversity_reviewed": directions_required and not direction_errors and "candidate_directions_distinct" in gates,
        "candidate_content_fidelity_reviewed": directions_required and not direction_errors and "candidate_content_fidelity" in gates,
        "science_boundary_reviewed": bool(review.get("science_boundary")),
        "review_status": review.get("status"),
        "reviewer_type": review.get("reviewer_type"),
        "user_acceptance": review.get("user_acceptance"),
        "recommendation_eligible": not errors and review.get("status") == "pass" and review.get("user_acceptance") != "rejected",
        "scope": "Review record completeness and arithmetic only; does not certify beauty, scientific truth, anatomy, causality, or alpha."
    }


def refinement_source_errors(contract: dict | None, iteration_mode: str | None = None) -> list[str]:
    """Check byte provenance only; visual preservation requires actual comparison."""
    if not contract:
        return ["refine mode requires a selected-base refinement_contract"] if iteration_mode == "refine" else []
    if not isinstance(contract, dict):
        return ["refinement_contract must be an object"]
    base = contract.get("base_asset", {})
    if not isinstance(base, dict) or not base.get("path"):
        return ["refinement contract needs an existing base_asset path"]
    try:
        actual = hashlib.sha256(Path(base["path"]).read_bytes()).hexdigest()
    except (OSError, TypeError) as exc:
        return ["cannot read the selected refinement base: " + type(exc).__name__]
    return [] if actual == base.get("sha256") else ["selected refinement base hash has changed"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_dir", type=Path)
    args = parser.parse_args()
    path = args.asset_dir / "aesthetic-review.json"
    try:
        review = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "errors": [f"cannot read aesthetic-review.json: {exc}"]}, ensure_ascii=False, indent=2))
        return 1
    brief_path = args.asset_dir / "brief.json"
    try:
        brief = json.loads(brief_path.read_text(encoding="utf-8")) if brief_path.is_file() else {}
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "errors": [f"cannot read brief.json: {exc}"]}, ensure_ascii=False, indent=2))
        return 1
    result = validate_review(review, brief.get("action_contract"), brief.get("refinement_contract"), background=brief.get("background"), composition_mode=brief.get("composition_mode"), aesthetic_spec=brief.get("aesthetic_spec"), iteration_mode=brief.get("iteration_mode"))
    source_errors = refinement_source_errors(brief.get("refinement_contract"), brief.get("iteration_mode"))
    if source_errors:
        result["errors"].extend(source_errors)
        result["ok"] = False
        result["recommendation_eligible"] = False
    asset = args.asset_dir / "asset.png"
    if not asset.is_file() or hashlib.sha256(asset.read_bytes()).hexdigest() != review.get("asset_sha256"):
        result["errors"].append("asset.png hash differs from the reviewed image")
        result["ok"] = False
        result["recommendation_eligible"] = False
    (args.asset_dir / "aesthetic-qa.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
