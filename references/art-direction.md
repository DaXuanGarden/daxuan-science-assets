# Art direction for raster assets

Use this workflow when the user asks for a generated image to feel more polished, expressive, distinctive, or publication-ready. It applies to image-model raster output. It does not turn the request into SVG authoring or code-drawn artwork.

## Lock meaning before style

Write one short content lock before proposing directions:

- the subject and visible action;
- the intended scientific relationship and its evidence level;
- required anatomy, setting, labels, and palette meanings;
- the destination aspect ratio and approximate display size.

Keep these fixed across all candidates. If the source supports an association, do not make any direction read as proven causation. A style card may alter visual form; it may not add a diagnosis, mechanism, biomarker, statistic, anatomical feature, or causal arrow.

## Write one direction card per image

Before an aesthetic exploration, prepare a JSON file matching [`direction-plan.json`](../assets/examples/aesthetic-directions/direction-plan.json). Each card specifies:

- `composition`: camera/viewpoint, crop, grouping, and negative space;
- `rendering_language`: a concrete medium and its edge/texture treatment;
- `silhouette`: the pose, outer contour, and gesture that should read first;
- `lighting_material`: light quality and how important surfaces should feel;
- `signature_detail`: one small craft decision that improves recognition or finish;
- `design_intent`: what this route should communicate better than the others.

Use concrete visual instructions rather than adjectives such as “beautiful,” “professional,” or “more academic.” State what should appear in the image and why. Prefer three deliberate routes by default; use 5–10 when the user requests a broader search and the generation budget is clear. Planning does not make image requests. `asset_tool.py init` writes a prompt for one selected direction; the user or agent must explicitly execute each image request.

Every pair must differ on at least two of the five visual axes, and at least one difference must change composition, rendering language, or silhouette. Do not count palette hue, a mirrored view, demographic substitution, minor expression changes, or finer detail alone. Hold palette roles fixed unless color itself is an explicit part of the design question.

## Initialize independent prompts

Use the same direction file and candidate count, but a different `--candidate-id` and fresh `--outdir` for each image. For example, the bundled three-direction plan can be initialized without calling the image service:

```bash
python3 scripts/asset_tool.py init desk-scene --subject "One adult seated at a desk and looking at a monitor" --mode raster_generation --palette editorial-pastel --background transparent --aesthetic-review --direction-plan assets/examples/aesthetic-directions/direction-plan.json --candidate-id side-gouache --candidate-count 3 --outdir output/desk-scene/side-gouache
python3 scripts/asset_tool.py init desk-scene --subject "One adult seated at a desk and looking at a monitor" --mode raster_generation --palette editorial-pastel --background transparent --aesthetic-review --direction-plan assets/examples/aesthetic-directions/direction-plan.json --candidate-id oblique-pencil --candidate-count 3 --outdir output/desk-scene/oblique-pencil
python3 scripts/asset_tool.py init desk-scene --subject "One adult seated at a desk and looking at a monitor" --mode raster_generation --palette editorial-pastel --background transparent --aesthetic-review --direction-plan assets/examples/aesthetic-directions/direction-plan.json --candidate-id paper-relief --candidate-count 3 --outdir output/desk-scene/paper-relief
```

Add `--action`, `--attention-target`, and repeated `--required-context` arguments when the exact behavior must be preserved. Then inspect each `image_prompt.txt`; call the existing image backend once per approved prompt with `--execute`. Never ask the model to return a contact sheet in place of independent candidates. The backend, selected source, model, credential, and billing route are unchanged by this planning workflow.

```bash
python3 scripts/image_backend.py --prompt-file output/desk-scene/side-gouache/image_prompt.txt --out output/desk-scene/side-gouache/asset.png --execute --report output/desk-scene/side-gouache/generation-evidence.json
```

## Review the images, not just the prompts

Compare every candidate against the same brief and compare every pair side by side at native size, around 200 px, and in the actual figure slot. In `aesthetic-review.json`, `candidate_comparison` records each image's `content_match` and concrete `science_note`; `direction_comparison` records every visual pair:

```json
{
  "direction_a": "side-gouache",
  "direction_b": "oblique-pencil",
  "visible_axes": ["composition", "rendering_language", "silhouette"],
  "verdict": "distinct_direction",
  "note": "The camera view, surface finish, and outer body contour remain visibly different in the thumbnail."
}
```

For every candidate, state whether its visible action and scientific relationship still match the brief. In a post-GWAS association, check that the image does not introduce causal arrows, a specific mechanism, or a diagnosis unless the evidence supports it. A mismatch makes `candidate_content_fidelity` false and blocks recommendation.

Use `close_variant` when the actual results converge even if their prompts differed. This prevents prompt variety from being presented as visual variety. The `candidate_directions_distinct` hard gate must be false for any set containing a close variant; revise the direction cards before recommending that candidate set.

Review craft as well as layout: natural form and gesture, controlled edges, light/material consistency, a deliberate focal accent, balanced negative space, and readable expression at final size. Color harmony is one consideration, not a proxy for overall appeal. A high weighted score cannot override wrong science, a wrong action, clipping, or an unattractive visible defect. Scores remain attributed human/agent judgments, not an objective beauty metric or journal-acceptance claim.
