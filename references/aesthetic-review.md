# Aesthetic review

For a standalone critique of one existing image, use [visual audit](visual-audit.md). It separates appeal, craft, and scientific/destination fit, can conclude `keep`, and does not require competing candidates or a numerical score. The contract below remains for selecting generated candidates and validating requested refinements.

Use this review for appearance-focused requests or after the user rejects a technically valid image as unattractive. Choose the iteration mode from context before choosing a count.

- `explore`: default to two candidates; honor a requested count of 2–10. Before generation, name each direction's visible design difference and user value. For larger sets, record a variation matrix. Camera mirroring, demographic swaps, and small recolors alone do not establish a new design direction. Inspect actual output pairs; a varied prompt list is not evidence of varied images. Label close variants honestly instead of claiming broad design diversity.
- `refine`: when the user selects an existing image, default to one focused revision; at most two treatments belong in this pass. Use the actual selected base as an edit reference, record its path and SHA-256 in `brief.refinement_contract.base_asset`, list `edit_targets`, and list `preserve_features`. Do not restart composition or replace approved features just to make a new image look different. Declare any second reference's limited role, such as hand anatomy or soft shading.

The CLI initializes these fields with `--iteration-mode`, `--base-asset`, repeated `--edit-target`, and repeated `--preserve-feature`. Initialization plans the work; it does not send image requests. Save each actual prompt and generation report.

## Review requested changes against the selected base

For `refine`, view the base and revised image together, inspect crops of each named detail, then inspect the final placement. Compare visible anatomy, edges, folds, shading transitions, or other requested properties; do not substitute generic praise such as "more polished." Exact labels added outside the image model need a deterministic typography check and a text-manifest entry.

The reviewer records `base_asset_sha256`, adds the hard gates `selected_base_preserved` and `requested_edits_addressed`, and supplies `edit_assessment`: one object per exact requested target with `target`, `outcome` (`improved|unchanged|regressed|not_visible`), and a concrete `note`. A `pass` requires every requested edit to be observed as `improved`, plus all gates. An unchanged or worse target requires `revise` or `fail`; do not let a high total score cover it. These remain attributed visual judgments, not automatic aesthetic measurements. The validator also checks that the saved base file has not changed.

One new version plus its selected base satisfies the comparison requirement; refinement does not require generating a second candidate. Preserve failed attempts as evidence and make at most one further focused correction to the highest-impact remaining defect in this pass.

## Lock required behavior before art direction

When behavior is part of the request, record `brief.action_contract` with `action`, `attention_target`, and `required_context`. A static object can leave this field empty. These fields describe what a viewer must be able to recognize, not hidden physiology. For a desk-screen scene, a desk, screen, seated person, and office chair can remain one coherent scene; an armchair alone does not preserve the requested behavior.

If the contract is nonempty, the reviewer must record `hard_gates.required_behavior_match`. It checks the action, gaze/attention target, and necessary contextual objects together. A failed behavior gate prevents a `pass` even when the image is attractive. The automated validator checks that the gate is recorded; actual behavior matching still requires looking at the image.

## Art direction before restrictions

Specify three positive visual aims such as natural facial expression, graceful seated silhouette, and a balanced seafoam/ivory/slate palette. Select one rendering language. Cartoon, painterly, flat editorial, and sculptural illustrations are valid options. Do not equate scientific rigor with a blank face, monochrome palette, or flatness. An avoidance list should protect meaning and remove known defects; it should not strip away all character and depth.

## Separate reviewer and actual evidence

A reviewer who did not write the prompt should inspect the baseline and candidates, a roughly 200 px thumbnail, and the destination placement. Use agent review when available; identify it as `reviewer_type: agent`. Never describe agent scores as a human vote or as user acceptance. If no separate reviewer is available, record `self_review` and that limitation. User acceptance remains `pending` until actual feedback.

Record `aesthetic-review.json` beside the selected image. Scores below are subjective review aids. They do not prove beauty, scientific truth, anatomy, diagnosis, causal evidence, or alpha transparency.

| Criterion | Weight | Review question |
|---|---:|---|
| `visual_hierarchy` | 20 | Does one subject and the intended cue lead attention? |
| `silhouette_readability` | 15 | Do pose and gesture read at 200 px? |
| `palette_harmony` | 15 | Are colors coordinated, lively enough, and sufficiently distinct? |
| `composition_balance` | 15 | Are proportions, visual weight, and whitespace balanced? |
| `style_coherence` | 15 | Are face, body, chair, lines, and shading part of the same style? |
| `detail_economy` | 10 | Does detail improve expression without introducing clutter? |
| `destination_slot_readability` | 10 | Does the asset work in the actual figure slot? |

Each criterion uses 1–5 with a concrete note. Convert to a score out of 100 using these weights. A reviewer `pass` requires at least 80 overall, every criterion at least 3, and all required gates true. The threshold is a selection rule, not a calibrated perception model. A high score cannot override a specific visible defect or negative user feedback.

## Sidecar contract

Required fields:

- `schema_version: "1.0"`; `status: pass|revise|fail`.
- `reviewer`, `reviewer_type: agent|human|self_review`, `user_acceptance: pending|accepted|rejected`.
- `asset_sha256`: binds the review to the actual selected file.
- `review_scope`: `target_px`, `thumbnail_px`, and `slot_px` as [width, height].
- `reviewed_images`: local image paths actually inspected, including the thumbnail and placement.
- `criteria`: each criterion contains `score` and `note`; `weighted_score` holds the rounded total.
- `hard_gates`: booleans for `no_extra_text_or_watermark`, `verified_alpha`, `single_anchor`, `no_detached_objects`, `thumbnail_recognition`, `no_clipping`, and `brief_style_match`. Add `required_behavior_match` when `brief.action_contract` is nonempty; leave legacy static-object reviews compatible when no contract exists.
- `defects`: concrete residual issues and their action; use an empty list when none are found.
- `candidate_comparison`: each candidate's path, strengths, defects, and verdict.
- `selected_candidate`, `selection_reason`, and `science_boundary`.

If any required gate fails, record `revise` or `fail`. After selection, permit at most one further focused correction to the highest-impact remaining defect. Keep failed candidates as evidence; do not present all of them as recommended finals. In exploration, explicitly record which outputs are genuinely different directions and which are close variants; do not infer diversity from the number of saved files.

Build repeatable previews with `python3 scripts/build_review_previews.py <asset-directory> --figure <figure.png> --slot <x> <y> <width> <height>`. Without a target figure, omit both figure and slot arguments; white/dark and 200 px previews are still produced. Use `--force` only to refresh existing preview files.

Run `python3 scripts/aesthetic_review.py <asset-directory>` for schema/arithmetic checks, then the normal raster QA. The validator does not inspect pixels, judge beauty, or replace scientific review. Review the individual transparent asset on white and a darker preview field to expose pale edges. Keep user assets and feedback outside the distributable Skill; only generic instructions and verification tools belong in the package.
