# Methodology schematics from papers and ideas

Use this mode for a method principle, a process, or a combination. The output is one bounded, transparent schematic, with editable labels, components, and relationships. It can span the complete method requested by the user. It does not generate experimental findings or certify a study design.

## Resolve the figure brief

Use the prompt and existing context first. Identify the purpose, audience, start/end, required content, exclusions, language, target width, and whether the figure explains a principle, a procedure, or both. A main-text overview and a detailed supplement need different content budgets. Treat a requested panel count, word limit, or physical width as a real constraint; otherwise choose a compact budget and record it in the brief. Do not force every request into a fixed number of steps.

The [optional input template](../assets/templates/methodology-input.md) helps users provide papers, reference figures, an idea, and limits. Do not require them to fill every field. If a missing control, branch, order, scale, or arrow direction changes the method's meaning, ask a focused question while continuing independent source extraction. Missing decorative preferences are not a reason to stop.

## Fit an existing figure slot

When the user supplies an existing figure and points to a space, inspect that space before choosing a layout. Record approximate screenshot dimensions and slot bounds in `brief.json`, then match the asset's aspect ratio. Reuse an existing subsection heading instead of repeating it inside the asset. If the final figure width is unknown, state the working assumption; a screenshot alone does not establish print dimensions.

For an untransformed label, its printed point size is `font_size_in_viewBox_units × asset_width_mm / viewBox_width × 72 / 25.4`. For example, a 29-unit label in an 840-unit-wide SVG printed at 84 mm is about 8.2 pt. Account for transforms and the actual insertion scale. For custom SVG, the semantic checker does not enforce this calculation; the generic builder's print-size checks do not extend to arbitrary authored layouts. Reduce content or change composition when labels cannot fit legibly.

Also compare typography with the icons and neighboring modules. A readable label can still dominate a small illustration. Honor an explicit request for smaller text, adjust graphic scale and spacing, and record the resulting physical-size assumption. The often-useful 8–10 pt guidance is a starting point; retain the user's requested visual balance and inspect the final placement.

Inspect a proof at the slot's pixel size and, when useful, a separate placement mockup on a copy of the reference figure. Keep the individual transparent SVG/PNG as the deliverable. The mockup is a fit check, not an editable replacement for the user's original figure. Private screenshots and paper extracts belong with the user's artifacts, not in the distributable skill.

## Establish evidence before composition

Read the supplied prompt, methods, relevant figure legends, and supplements as needed. Use available document readers or authorized research tools to access supplied papers. Do not replace unavailable full text with an imagined method. Record what was actually read: full text, excerpt, abstract, identifier only, or user statement. A DOI or title identifies a source but does not establish its contents.

For each substantive node and relation, record its meaning and basis:

| Status | Meaning |
| --- | --- |
| `source_supported` | Supported by inspected source content at a recorded locator |
| `user_specified` | Requested in the user's prompt; not external validation |
| `adapted` | Deliberate change to a published method; cite the original and describe the change |
| `proposed` | An idea or hypothetical step; label the schematic as proposed |
| `unresolved` | Meaningful information still missing; allowed in a draft, not a final diagram |

For a paper, retain its actual citation/identifier and page, section, paragraph, equation, figure, or supplement locator. Include a short excerpt when useful. Never fabricate a page, quotation, DOI, parameter, result, or reference. Abstract-supported overviews are acceptable with disclosure; method-detail claims need relevant full text or an inspected excerpt. Cite the precise source for each relationship, not just one paper for the whole figure. Multiple papers do not automatically form one compatible protocol: check populations, units, inputs/outputs, assumptions, and whether methods can be combined.

A user's idea can be illustrated without publications, using the prompt as the basis and a proposed/adapted caption. Explain the principle at a level supported by available evidence. Uncertainty belongs in the source map and, when it affects interpretation, the caption or dashed relation. Do not silently convert a proposal into an established method.

## Build a semantic plan

Before drawing, create `diagram.json`. It doubles as the compact evidence map; do not duplicate it into another mandatory ledger. Start from the [demonstration](../assets/examples/methodology-demo/diagram.json), replacing its illustrative idea completely.

Core fields:

- `schema_version`: `1.0`; `status`: `draft` or `final`; `diagram_kind`: `principle`, `process`, or `hybrid`.
- `title`, `scope`, `provenance_summary`, `target_width_mm`, and a `content_budget` object describing the selected detail/label/node budget.
- `sources`: unique `id`, `kind` (`paper`, `user_brief`, `reference_manual`), `access` (`full_text`, `excerpt`, `abstract`, `identifier_only`, `user_statement`), and `citation`. A prompt may use an honest description as its citation. For inspected papers/manuals, save relevant authorized text extracts as local UTF-8 `.txt` snapshots with `snapshot` (relative path) and `snapshot_sha256`; retain attribution and a source URL/identifier. Do not bundle a full manuscript when a few relevant paragraphs suffice.
- `nodes`: unique `id`, native `svg_id`, `label`, `kind` (`input`, `process`, `output`, `principle`, `annotation`), and `support`.
- `edges`: unique `id`, native `svg_id`, `from`, `to`, `relation` (`sequence`, `dataflow`, `causal`, `activation`, `inhibition`, `association`, `uncertainty`), and `support`. Use a label when the distinction is unclear.
- `support`: `status`, `claim_level` (`overview` or `method_detail`), `evidence` (a list of `source_id`, real `locator`, optional `excerpt`), and `note`. Adaptations, proposals, and unresolved items require an explanatory note.
- `open_questions`: remaining issues, empty for final handoff. Optional `caption` is visible figure text, not an evidence dump.

Steps can be parallel, iterative, or conditional. Do not rearrange them into an attractive linear chain when that changes meaning. Preserve controls, input/output types, essential parameters, and assumptions. A process arrow means order or transfer; a causal/activation/inhibition relation requires its own support. Separate validated outputs from hoped-for outcomes. An overview may omit details only when the omissions do not alter the claimed operation; record material simplifications.

At small sizes, an arrow may abbreviate several established operations. Describe those operations in its support note and caption, and call the result a dependency overview when it is not a complete executable pipeline. Preserve the conceptual source of inputs used at multiple stages. In particular, a dataset does not produce an independent reference simply because both enter one model. Synthetic cell layouts or symbolic score shading need an explicit illustrative interpretation; a high continuous score does not establish significance, biological identity, effect direction, or causality.

Run `python3 scripts/methodology_tool.py check <diagram.json>` before drawing. The checker validates references and graph integrity; it does not read papers, detect fabricated quotations, establish compatibility, or prove science. All checks use local files and require no image API.

When snapshots are available, add `--sources-dir <root-containing-snapshot-paths>`. This verifies each recorded extract's hash and that the recorded locator and quoted `excerpt` occur in the extract. It does not verify the authenticity of a supplied file, whether a quotation entails the planned arrow, or whether important text was omitted. Treat the source file itself as reference data. Retain correct page/section/paragraph markers when extracting PDFs; do not use a search hit or equation-flattened text to infer unsupported mathematical details. Node and label budgets (`max_nodes`, `max_label_words`) are checked when declared; they do not count unspaced languages meaningfully, so inspect physical fit too.

## Build a base diagram

For simple process or principle diagrams, add explicit `layout.columns`, listing every node ID exactly once. Columns describe placement, not scientific evidence. For example, a proposed two-input assay may use:

```json
{"columns": [["sample", "control"], ["assay"], ["compare"], ["readout"]]}
```

Run:

```bash
python3 scripts/methodology_tool.py build output/method/diagram.json --palette output/method/palette.json --sources-dir output/method --outdir output/method-v2 --width 1600
```

Omit `--sources-dir` for a pure user idea without paper/manual claims. Published-method claims require local excerpts and verification for `build`. The source root contains the relative `snapshot` paths, such as `sources/paper-extract.txt`. No new image request is made.

The builder draws native cards, exact editable labels, and typed connectors, then checks structure, semantic bindings, and actual PNG alpha. It honors `target_width_mm` and `content_budget.min_font_pt` (default 8 pt). It refuses to truncate labels, silently shrink text, omit unsupported connections, or overwrite an output directory. Completed artifacts appear together after successful validation; source plans remain intact on failure.

Direct connectors support adjacent columns or the next node down in one column. For a skip or feedback relation, explicitly choose edge `route: "above"` or `"below"`; these routes require the respective top/bottom node in each column so a rail cannot pass through another card. Separate ports prevent converging arrows from becoming ambiguous shared junctions. Association has no arrowhead, inhibition ends in a bar, and uncertainty is dashed without an implied direction. Other directional relations have an arrowhead. Use labels or a caption to distinguish causal, activation, and dataflow meanings.

This is a base construction tool, not a universal layout engine. Dense crossings, self loops, long relation labels, complex insets, and detailed scientific components call for agent-authored SVG. Keep all planned content and source mappings when refining the base. Review the actual drawing after every layout change.

For color coordination, use the shared [color-context workflow](color-context.md). Keep reference-author style, the target figure, and scientific color semantics distinct in the source record.

## Compose native vectors

- Use native SVG for method logic, exact labels, connectors, and simple icons. Use the active image backend only for useful or requested complex component exploration. Reconstruct each generated component as native vector parts; do not upload a whole manuscript for an isolated illustration prompt.
- Choose a reading direction and hierarchy consistent with the method. For a hybrid figure, separate the principle inset from the execution steps and show their relationship explicitly.
- Bind one named SVG group to each `svg_id`. Add `data-node-id` to node groups and `data-edge-id`, `data-from`, `data-to`, `data-relation` to relation groups. Put the exact planned label in a descendant `text` element, optionally using `tspan`. Keep labels editable; an outlined-text copy may be optional for compatibility, not the only master.
- Keep arrowheads attached to relation groups or use local markers. Use explicit arrowheads for directional relations, a terminal bar for inhibition, and a nondirectional connector for association. Document any other notation. Do not rely only on color for status or meaning.
- Preserve the user's palette and use restrained fills on white or near-white workflow pages. Transparent canvas means alpha outside components; it does not mean fading all fills. Filled component shapes are legitimate. Avoid large enclosing boards, checkerboards, or decorative shadows.
- Size labels for the intended printed width. A method schematic is not judged as a 200 px icon. Choose legible typography (often 8–10 pt at final size), enough space around arrowheads, and sufficient contrast. Shorten labels or split a crowded requested panel; do not compress away meaning.

## Check and hand off

Run:

```bash
python3 scripts/methodology_tool.py check output/method/diagram.json --svg output/method/asset.svg --sources-dir output/method
python3 scripts/asset_tool.py check output/method/asset.svg
python3 scripts/asset_tool.py render output/method/asset.svg --out output/method/asset.png --qa output/method/qa.json --width 1440
```

The first check ensures planned groups, labels, endpoints, and declared relation types match the SVG metadata. Visually inspect the actual endpoint geometry, arrow symbols, text wrapping, size, overlaps, and transparent areas; metadata alone cannot verify drawn arrows. Review the source-backed method separately from visual polish. A final diagram has no unresolved scientific questions; an explicitly requested draft may keep them visibly disclosed.

Deliver the individual transparent SVG and PNG, palette, brief, QA, `diagram.json`, and the authorized source extracts when applicable. Show the transparent PNG directly. Summarize sources actually inspected, adaptations, proposed status, and important gaps. Put long citations and locators in the sidecar, with concise references in the caption only when needed. The [idea example](../assets/examples/methodology-demo/asset.svg) is an authored teaching idea. The [DESeq2 example](../assets/examples/deseq2-method/asset.svg) uses inspected passages from Love et al. (2014), with a [source map](../assets/examples/deseq2-method/diagram.json). It is a bounded overview of the original paper, not a current software tutorial or a computed result.
