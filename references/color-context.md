# Color context from references and the destination figure

Read this when a scientific asset will join an existing figure, or when the user asks to coordinate author/reference colors with manuscript colors. Simple isolated objects without references can use an existing approved palette without creating extra paperwork.

## Resolve the sources separately

Inspect the sources actually supplied:

- **Explicit user/author rules:** A color report, approved element-to-color mapping, locked hex values, or stated exceptions.
- **Target figure:** The figure and neighboring modules where the asset will be placed. Inspect the full figure for overall balance and the local slot for contrast, scale, and visual weight.
- **Manuscript family:** Existing figures that establish recurring data-source, score, or cell-type colors.
- **Reference author:** The reference paper's relevant figures or graphical abstract. Learn its hierarchy, saturation, and emphasis strategy; record whether the full figure or only a small crop was available.

Resolve conflicts in that order: explicit user rules, target figure, manuscript family, then reference-author inspiration. Scientific meanings take precedence over decorative matching. A reference author's cell-type colors do not label the user's cell types. An author-supplied rule takes priority over an inferred screenshot sample. Ask a focused question only when an unresolved mapping changes interpretation; otherwise proceed with a disclosed visual inference. Record missing sources honestly rather than claiming to have inspected them.

Use exact vector paints when available. Raster screenshots provide approximate appearance; antialiasing, export, crop, and compression affect samples. Paint counts are not rendered area, semantic importance, or aesthetic quality. Do not copy every detected color into an asset. Select structural tones, local fills, guides, text, and an emphasis family that work in the target slot. Preserve the meaning and direction of continuous score legends. Richness may come from coordinated component roles while related objects share the same structural palette.

## Record and check the decision

For these context-dependent jobs, save `color-context.json` beside the user's assets. Its fields are:

- `schema_version`: `1.0`; `status`: `draft` or `final`.
- `precedence`: the ordered list `explicit_user_rules`, `target_figure`, `manuscript`, `reference_author`.
- `sources`: unique `id`, one `scope` from that list, `access`, a citation/description, and local `snapshot` plus `snapshot_sha256`. Supported access values are `inspected_vector`, `inspected_raster`, `author_report`, `source_snapshot`, and `user_statement`. A palette-extraction report can be the snapshot; record what was extracted and the original source hash. When unavailable, use `access: unavailable` and explain in `note`, without an inspection claim. Include both the reference-author and target-figure scope, even when one was not supplied. Snapshots stay within the selected output root.
- `assignments`: one object for each palette role, containing `hex`, `meaning`, `source_ids`, and `basis` (`explicit`, `exact_paint`, `approximate_sample`, `derived`, or `preserved`). Explain material color changes and conflict resolutions in a `note`.
- Optional `locked_colors`: role-to-hex rules that were explicitly fixed or deliberately retained for an approved revision. Do not invent locks that prevent the user's requested changes.
- Optional `score_scales`: `id`, ordered `roles`, `direction: low_to_high`, and `meaning`. Explicitly distinguish illustrative scores from observed results.
- Optional `contrast_pairs`: `foreground` role, `background` role or hex, and `min_ratio`. Choose an appropriate threshold for the actual use; this numeric check does not prove small labels or marks are legible.

Use the local helper without an image API:

```bash
python3 scripts/palette_context.py inspect reference.svg --out output/reference-colors.json
python3 scripts/palette_context.py inspect figure.png --crop 40 500 800 400 --out output/figure-slot-colors.json
python3 scripts/palette_context.py check output/asset/color-context.json --root output/asset --palette output/asset/palette.json --svg output/asset/asset.svg --out output/asset/color-qa.json
```

The inspector reads literal SVG paints or quantizes opaque raster samples; it does not assign scientific meanings. Raster inspection requires Pillow. The checker validates recorded snapshot hashes, role decisions, explicit color locks, actual tagged paints, inline-style conflicts, and declared text contrast. It does not establish source authorship, infer biological meaning, judge harmony, or prove score colors are perceptually monotonic. Existing SVG structure, alpha, methodology, and recolor checks still apply. Output files require a fresh name or explicit `--force`.

For final review, inspect the single transparent asset and a separate placement proof. Compare palette balance with the full target figure and readability in the local slot. Keep a short color report with original versus derived colors and any unresolved source limitations. Preserve all requested assets and their approved components during palette work. User-owned source images and palette reports belong with the user's output, outside the distributable skill.
