# Figure-slot integration and leader routes

Use this workflow when a generated illustration will occupy a measured region in a larger figure and connect to result panels, organs, or other named targets. It covers the handoff from model-generated artwork to the final composite; it does not replace the project's plotting or layout code.

## Plan the final composition first

Before writing the image prompt, record:

- the final figure size and the slot bounds in one declared coordinate system;
- the intended asset bounds and display scale, including any protected whitespace;
- each connector's semantic relation, source panel or object, target anchor, and route;
- the palette roles and any labels or result encodings that must remain unchanged.

Start from the actual target figure when available. If the full figure contains unpublished or sensitive material, inspect and measure it locally; do not upload it as an image reference without authorization. A verbal slot description or a non-sensitive mockup can provide model context. Use [`assets/templates/figure-slot-plan.json`](../assets/templates/figure-slot-plan.json) to track geometry and review state. Keep scientific meaning in `relation_manifest.json`; the slot plan records coordinates and rendering order.

## Separate the illustration from the overlays

Use the image model for the requested anatomy, character, or conceptual artwork. Unless the user asks for them in the raster, exclude panel frames, exact labels, organ badges, result markers, connector lines, stars, and decorative callouts from the image prompt. The model should not guess which panel maps to which structure or draw exact leader geometry.

Keep typography, data marks, endpoints, and connector paths in the deterministic figure renderer as editable vector or native plotting objects. For each route, bind a source to one named target anchor. Record anchor positions after the final crop, and route points in the declared figure coordinate system. Do not mix asset-local, panel-local, and page coordinates in one path.

## Choose one route style for the figure

Use the simplest path that remains readable in the final composition:

- For organic radial layouts, a shallow cubic Bézier with few control points can follow whitespace without looking mechanical.
- For a grid-aligned layout, use a small number of clean orthogonal segments.
- Avoid freeform loops, repeated bends, unnecessary waypoints, and mixing unrelated route styles in the same figure.

Keep source and target visible. Draw the vector overlay after the raster so the illustration cannot hide the path. Route through low-information space; do not cover data, labels, faces, or defining anatomy. If a path must cross the illustration, keep it short, use sufficient contrast against both light and dark regions, and terminate exactly at the named marker. Minimize route crossings. When a crossing cannot be avoided, identify it in the plan and inspect it at final size. Line color, dash, width, and any light casing must follow the figure's visual system and remain legible when reduced; do not use color alone to imply a scientific result.

## Review the assembled output

An asset preview placed in an empty slot does not test external leader paths. Render the complete composition with the final panels, labels, illustration, and overlays, then inspect:

1. At publication size: all expected connectors are present, begin and end at the intended anchors, and are neither clipped nor hidden.
2. At a 200 px thumbnail: the illustration does not dominate the results, route crossings remain understandable, and the figure's main message is still clear.
3. In the saved vector/raster output: count planned versus rendered routes, record intentional and unintended crossings, and note any protected feature obscured by a line.

Bind the visual review to the assembled file and record its output path and hash in the project evidence. If only scale, position, or routing is defective, adjust the layout layer; do not regenerate sound artwork. Regenerate or edit the image only for a visible artwork defect such as inaccurate anatomy, a wrong palette role, poor silhouette, or unwanted detail.

## Handle a generation refusal

Inspect the returned error and preserve a sanitized status in the generation evidence; do not assume the cause if the service did not identify it. Do not repeat the same rejected request or change providers to get around a refusal. When the intended content is permitted but the wording is ambiguous, make at most one focused rewrite in plain clinical or educational language, remove unnecessary appearance-focused phrasing, and retain the scientific content. Do not disguise prohibited content. If it is refused again, stop and report the blocker.
