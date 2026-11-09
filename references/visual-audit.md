# Review an existing scientific illustration

Use `review_only` when the user asks whether an existing asset is attractive, well crafted, or suitable for a scientific figure. A single image is enough. Do not generate a replacement, require fake competing candidates, or change an approved image merely to demonstrate activity. This route ends with a useful critique and bounded next actions. The existing [aesthetic review](aesthetic-review.md) remains the comparison record for generation and refinement.

## Prepare evidence, then actually inspect it

```bash
python3 scripts/visual_audit.py prepare output/selected \
  --outdir output/audit-v1 \
  --figure output/already-composed-figure.png --slot 240 180 160 160
```

`asset_dir` must contain `asset.png`; an optional brief is copied too. `--figure` is the **already-composed** destination PNG, including any exact labels. The script copies it and crops the slot; it does not overlay the asset again. Supply figure and slot together, or omit both. The output directory must be empty. Original artwork, figure, and brief remain unchanged. This local tool never invokes an image model.

The pack contains the original asset, white and dark previews, a 200 px thumbnail, and, when supplied, the unscaled destination slot, a wider context crop, and the full figure. Asset previews preserve the source aspect ratio and center it on a square display canvas; they do not stretch a non-square image. `evidence.json` binds sources and previews to hashes. `review.json` begins as `pending`; preparing it is not a completed review.

Open every required view. Inspect enlarged details for drawing defects, then return to the unscaled slot and whole figure. Distinguish a defect visible only in a magnified crop from one that matters at the destination. Do not infer physical publication width from preview DPI. If final print size, source support, or placement is missing, state that limit; use `not_observable` where appropriate.

## Three review lenses

1. **Visual appeal:** a clear focal point, balanced silhouette and whitespace, coordinated color/value, expressive but appropriate character, and a coherent rendering language. Beauty does not require faceless people, flat shapes, pale colors, or a particular age or body type. Preserve the user's accepted direction.
2. **Craft:** believable anatomy and gesture, object function, perspective, support/contact, clean overlaps, edges, shading, and detail economy. After simplification, recheck that a chair still supports the person or that a device remains plausible. Fewer lines are not automatically better.
3. **Scientific and destination fit:** what a viewer actually reads, whether it matches the brief, whether symptoms imply a stronger claim than the study supports, label accuracy, thumbnail/slot recognition, print-size limits, and visual competition with the surrounding results. A pleasing conceptual icon does not establish duration, diagnosis, causality, anatomy, or a quantitative result.

For each lens write a concrete observation, including strengths worth keeping. Avoid copying the previous round's score as a new inspection. An accepted image can be suitable already; `keep` is a successful review outcome.

## Findings that can guide an edit

Use at most three priority edits. Each finding must name an actual visible region and connect:

**Observation -> consequence -> exact action -> visible acceptance test.**

For example: "The chair base loses its support shape at slot size -> it can read as a stool rather than an office chair -> restore a small plausible rear support without restoring mechanical clutter -> the 200 px and actual-slot views show a stable office-chair silhouette while the person stays dominant."

Keep low-confidence interpretations conditional. Do not turn every stylistic preference into a defect, count larger files as a new aesthetic direction, or recommend extra rendering detail that disappears at final size. A refinement prompt should carry only selected priority findings plus the preserved features, not every observation in the report.

## Review record

Complete the prepared `review.json`:

- `status: complete`, attributed `reviewer`, `reviewer_type: agent|human|self_review`, and actual `user_acceptance`. Preserve the prepared asset and evidence hashes.
- `views_inspected`: evidence view IDs actually opened. All prepared views are required.
- `domain_assessments`: `visual_appeal`, `craft`, and `scientific_fit`, each with `status: reviewed|not_observable` and a specific `note`.
- `strengths`: at least two concrete features to preserve.
- `findings`: an empty list is valid. Each item has a unique `id`, `domain`, `severity: minor|moderate|major`, `confidence: low|medium|high`, `region: {space: asset|context, box: [left, top, right, bottom]}` with normalized coordinates, `visible_at: [detail|thumbnail|destination]`, and nonempty `observation`, `impact`, `action`, and `acceptance` text.
- `top_actions`: up to three finding IDs, ordered by value at the intended size. Other findings remain optional observations.
- `verdict: keep|refine|revise`. `keep` has no priority edits; `refine` identifies useful polish; `revise` identifies a material craft or communication problem. No aggregate beauty score is required.
- `destination_assessment`: `status: inspected` with a note when a figure is supplied, otherwise `status: not_supplied` with an explicit limitation. Add `science_boundary` and a `limitations` list.

```bash
python3 scripts/visual_audit.py check output/audit-v1
```

This checks completeness, declared coverage and provenance; it does not see the images or verify the truth of a visual judgment. A pending template, missing actual views, or changed evidence cannot pass. Agent review remains subjective. User acceptance is separate, and a record must not claim human preference experiments or journal acceptance.

Deliver the strongest observed conclusion first, a small annotated preview when useful, what should stay, and no more than three recommended changes. Keep engineering logs outside the artwork. Proceed to generation only when image creation or a concrete revision is authorized; reviewing an image by itself does not require an image request.
