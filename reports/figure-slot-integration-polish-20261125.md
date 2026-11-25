# Daxuan Scientific Assets Skill Polish Report

**Review date:** 2026-11-25
**Baseline:** public `main`, commit `272b431`, version 0.9.0
**Scope:** the handoff from model-generated illustration artwork to editable overlays and final composite review.

## 1. Material assessment

- **Real problem:** valid. In a multi-panel scientific figure, a good isolated illustration can still obscure leader routes, hide their endpoints, or dominate the data when assembled.
- **Distinctive value:** the Skill already combines image-model artwork, scientific source boundaries, manuscript palette context, raster QA, vector derivatives, and PDF preservation. The missing part was a reusable geometry contract for the asset's final placement.
- **Reason to install:** it gives researchers a documented path from one generated component to a reviewed final composite, including route provenance and a clear rule for when layout code, rather than another image edit, should fix a defect.
- **Public hook:** generate the complex illustration; keep evidence, labels, and connector geometry inspectable.

The recent private Figure 8 work exposed the gap: the model-generated anatomy was refined repeatedly while panel-to-organ connectors changed between curves and elbows. The final review needs to check the illustration and its overlay together. Existing files already record connector geometry and a composite proof, so this update codifies a working pattern instead of introducing a new drawing backend. No private figure, prompt, result, or filesystem path is included here.

## 2. Peer study

| Project | Type | Useful practice | Boundary kept |
|---|---|---|---|
| [K-Dense Scientific Agent Skills: generate-image](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/generate-image/SKILL.md) | Direct | Keep model text out of scientific figures; treat generated art as illustration, not evidence; inspect errors and protect credentials. | Its hosted-provider setup and API are not imported. |
| [Scientific Illustrations Skill](https://github.com/fmschulz/scientific-illustrations-skill) | Direct | Generate and critique an image, then redraw as editable objects when that is the required deliverable. | Penpot is not added as a mandatory dependency. |
| [Craft Scientific Figure Prompts](https://github.com/kikixiong/craft-scientific-figure-prompts) | Direct | Separate scientific truth from visual style; validate a production prompt and inspect the actual rendered result. | Its whole-figure prompt workflow is not substituted for this asset package. |
| [Databricks Vital Skills: scientific-figures](https://github.com/databricks-industry-solutions/vital-skills/blob/main/skills/scientific-figures/SKILL.md) | Adjacent | Plan layout before rendering and require visual inspection after rendering. | It focuses on charts and Databricks rendering, outside this Skill's image backend. |
| [Scientific Figure Workflow](https://github.com/Yuhang-Xiao/scientific-figure/tree/scientific-figure/skill/scientific-figure-workflow) | Adjacent | Keep complex image assets separate from native editable labels, arrows, and frames. | Its full master-image reconstruction flow is not required here. |
| [Codex PaperFactory scientific-figure](https://github.com/happystander/codex-PaperFactory/tree/master/skills/scientific-figure) | Craft | Record figure plans, source mapping, and export QA as part of the work product. | Its broad paper-production scope is not copied. |

The common practice is separation of generated pixels from exact text and relationships, followed by visual review of the rendered composition. The update adds a narrow, reusable contract for that handoff.

## 3. Position

**Before:** a general scientific-asset generator with strong standalone raster and vector checks.
**After:** an image-model-first illustration workflow that also records how a generated asset fits into a composite figure and how external leader paths are reviewed.

The package remains an asset workflow. Statistical plotting, figure-wide scientific interpretation, and unsupported mechanism inference remain out of scope.

## 4. Quality score

Scores are rubric estimates, not a calibrated benchmark. The 0.9.0 baseline passed 148 unit tests and package checks. Historical project artifacts demonstrate that generation and assembly have been exercised, but there was no independent blind review. No live image request was made for 0.9.1, so measured-performance credit is unchanged.

| Dimension | Weight | 0.9.0 | 0.9.1 estimate | Evidence for change |
|---|---:|---:|---:|---|
| Frontmatter and triggers | 7 | 7 | 7 | Existing trigger contract retained. |
| Workflow clarity | 12 | 10 | 12 | Entrypoint now points to the integration workflow and marks its sequence. |
| Failure modes | 12 | 9 | 11 | Adds refusal handling, route visibility, clipping, and crossing checks. |
| Checkpoints | 6 | 4 | 6 | Adds an explicit plan template and final-composite review. |
| Actionable specificity | 17 | 15 | 17 | Defines coordinate systems, route choices, layers, endpoints, and review states. |
| Resource integration | 4 | 4 | 4 | Connects the new reference, template, README, and package manifest. |
| Architecture | 12 | 10 | 12 | Keeps relation semantics separate from placement geometry and preserves existing tools. |
| Measured performance | 23 | 17 | 17 | No new live-generation or independent perception study was run. |
| Counterexamples and boundaries | 7 | 6 | 7 | Covers hidden leaders, unnecessary regeneration, and refusal-retry behavior. |
| **Total** | **100** | **82** | **93 estimated** | **Structure improved; model quality not newly benchmarked.** |

## 5. Remaining gaps

### P0

None identified for the focused change.

### P1

- The package has no generic renderer that consumes the new placement plan. Projects still use their own plotting or composition code to draw connector paths.
- No human blind preference study or independent anatomical review was added.

### P2

- A public, synthetic multi-panel example could demonstrate the template without publishing a private manuscript figure.
- A later tool could validate connector geometry and rendered endpoint counts, once a stable cross-renderer contract is justified.

## 6. Three directions

| Direction | Scope | Benefit | Risk |
|---|---|---|---|
| A. Clarify | Add concise instructions for keeping labels and leaders outside generated pixels. | Smallest patch. | Does not give users a reusable geometry record. |
| B. Integrate (chosen) | Add a placement template, route and overlay guidance, composite QA, and focused tests. | Converts the repeated Figure 8 lesson into a portable workflow without adding a backend. | Route geometry remains project-renderer-specific. |
| C. Build a suite | Add a generic connector renderer, geometry collision checker, and demonstration composite. | More automation and an immediately visible demo. | Larger compatibility surface and premature layout API. |

Direction B was implemented under the user's explicit instruction to improve and push the Skill.

## 7. Candidate change and validation

The operative rule is:

> Generate the illustration as a clean image layer. Bind each external route to a named source and target in one coordinate system. Render exact labels and connectors in deterministic layout code, then review the complete assembled figure at publication size and thumbnail scale. Change only the layer responsible for a defect.

Changed files:

- `SKILL.md`: model-generated illustration is the primary creation output; composite integration is routed to a dedicated reference.
- `references/figure-slot-integration.md`: slot planning, image/overlay separation, route selection, final review, and restrained refusal handling.
- `assets/templates/figure-slot-plan.json`: reusable geometry and review-state template, initially unchecked.
- `tests/test_figure_slot_integration.py`: three focused tests for the template and entrypoint contract.
- `README.md`, `CHANGELOG.md`, and `manifest.json`: user-facing entry, version 0.9.1, scope, and release evidence.
- This report records the review and its limitations.

Two dry-run prompts were used to compare the instruction boundary against the 0.9.0 baseline:

1. “Generate a central anatomical illustration for a six-panel figure; each panel connects to a named organ.” The baseline said to estimate the slot and inspect occlusion, but had no route geometry record or explicit final composite gate. The new flow starts with a slot plan, keeps connectors out of model pixels, and requires review after the route layer is rendered.
2. “The artwork is approved; improve the organ leader curves without changing any plotted results.” The baseline did not explicitly tell the agent to fix a layout-only defect in the vector layer. The new flow preserves the image and data panels, updates only routes, and checks endpoints and crossings in the final composite.

These are instruction dry runs, not measured agent-routing accuracy. The package tests verify the template fields, reference links, and documented generation/composite requirements. They do not score beauty or scientific accuracy.

Verification on the release candidate: all 151 unit tests passed; package validation passed with the frozen 0.9.0 baseline; all 28 trigger smoke cases passed; existing bundled vector examples, palette files, and core image/vector tools were byte-identical to baseline; `git diff --check` passed. The installed Codex copy was also updated and its package validator passed. No live image request was made.

## 8. README and showcase

The README already includes generated outputs, an example gallery, installation commands, and a PDF assembly demonstration. This update adds the new workflow to the README's main usage explanation. No private Figure 8 artwork is suitable for the public showcase. A future showcase can use a synthetic panel layout and generated, non-project anatomy asset.

## 9. Execution plan

### Completed in this release

- [x] Record placement geometry separately from scientific relation meaning.
- [x] Keep exact labels and leader routes in deterministic layout layers.
- [x] Require full-composite review at print size and thumbnail scale.
- [x] Add package template, focused tests, release notes, and version metadata.
- [x] Push the validated change to GitHub `main`.

### Follow-up

- [ ] Gather feedback from future composite-figure use and keep project-specific route coordinates out of the public Skill.
- [ ] Add a synthetic showcase only if it can demonstrate the workflow without implying that generated art is empirical evidence.
- [ ] Consider a geometry validator after multiple projects share a stable placement schema.

## 10. Certificate

```text
Skill Workshop Certificate
Work: Daxuan Scientific Assets 0.9.1
Score: 82/100 baseline -> 93/100 estimated
Position: image-model illustration with traceable composite-figure integration
Signature: generated artwork stays separate from exact labels and connector geometry
Next check: evaluate the route contract on the next composite figure
Acceptance: package tests and static validation; no new live image run
```

## 11. Revisit list

- Watch the cited image-generation and scientific-figure skills for changes to refusal handling, model-text limitations, and separation of image assets from editable overlays.
- Keep the image backend and provider stable; a refusal is evidence to inspect, not a reason to switch providers or retry around a guardrail.
- If more than one project needs route geometry, compare their plans before adding a renderer or schema validator.
- Known boundary: the figure-slot plan documents and reviews routes but does not draw them.

## 12. User questions

None block this release. The image-generation backend was not called because this request was to improve the Skill, not to generate or revise an illustration.

## 13. Sources

- https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/generate-image/SKILL.md
- https://github.com/fmschulz/scientific-illustrations-skill
- https://github.com/kikixiong/craft-scientific-figure-prompts
- https://github.com/databricks-industry-solutions/vital-skills/blob/main/skills/scientific-figures/SKILL.md
- https://github.com/Yuhang-Xiao/scientific-figure/tree/scientific-figure/skill/scientific-figure-workflow
- https://github.com/happystander/codex-PaperFactory/tree/master/skills/scientific-figure
