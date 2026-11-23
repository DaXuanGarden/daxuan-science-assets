# Aesthetic Design Skill Review

Reviewed on 2026-11-23 for generated, small-format scientific raster illustrations. The goal was to find methods for deliberate art direction and visual finish while keeping a compact asset scientifically bounded. These are design references, not runtime dependencies or quality benchmarks.

## Most useful references

| Skill | What it contributes | What this package adopts | What stays out of scope |
| --- | --- | --- | --- |
| [Anthropic canvas-design](https://github.com/anthropics/skills/tree/main/skills/canvas-design) | Starts with a visual philosophy and reasons through form, space, material, rhythm, and balance before making the image. | Write a short, subject-specific art direction before prompting; make form and composition carry the idea. | Its art-object brief allows far more abstraction and interpretive freedom than a scientific figure inset. No abstract poster layout or implied science. |
| [Anthropic frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) | Plans a distinctive visual direction, checks it against the brief, and names common generated defaults. | Check whether a prompt falls back to generic flat vector, repeated camera angle, palette-only changes, or decorative clutter. | Website structure, web typography systems, CSS guidance, and hero conventions do not transfer to a small illustration. |
| OpenAI bundled `imagegen` skill (reviewed locally) | Structures image prompts, distinguishes generation from editing, directs one image per requested variant, and inspects saved outputs. | Keep each candidate as an independent prompt and image call; treat transparent background and reference-image roles explicitly. | This project's existing official/configured relay adapter remains the only execution route. The design work does not switch provider, model, account, credential, or billing path. |
| [K-Dense scientific-schematics](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/scientific-schematics) | Connects raster generation to critique and iteration, and emphasizes source-backed labels and relationships. | Keep science review independent from beauty review; preserve uncertainty and do not let the image model invent relationships. | Its OpenRouter/Gemini API configuration, complex-diagram focus, and numeric journal thresholds are not adopted. A heuristic score is not evidence of journal acceptance. |
| [imagegen-frontend-web](https://github.com/Leonxlnx/imagegen-skills/tree/main/skills/imagegen-frontend-web) | Explicitly counters repetitive image composition and requires separate prompts for separate outputs. | Give every candidate a different, visible design decision and keep each request to one image. | Landing-page sections, conversion framing, hero layouts, and marketing density are irrelevant to a scientific spot illustration. |

## Local skills reviewed

- `imagegen`: reinforces prompt specificity, role-labeled input images, one call per requested variant, actual output inspection, and a separate built-in/CLI decision. Its provider instructions do not replace the project's relay workflow.
- `frontend-design`: provides an anti-default checklist and a plan-then-critique process. Its web-specific layout and typography instructions are not reused.
- `character-design`: contributes silhouette-first reading, pose/gesture clarity, expression, and scale checks. Its bias toward exaggerated/iconic character shapes is constrained by natural anatomy and scientific context.
- `generate-scientific-graphical-abstract`: contributes a claim ledger, narrative-topology choice, and protection against turning associations into causal mechanisms. A graphical abstract's multi-node narrative is not a template for one small central asset.
- `paper-illustration-image2`: contributes the planner/generator/reviewer loop and targeted visual revisions. Its fixed conference-style visual rules and numeric score threshold are not treated as universal journal standards.
- `luban`: contributes peer inspection, explicit evidence boundaries, independent acceptance, release notes, and repeatable verification.

These locally installed skills are reference material only. They are not copied into this repository, fetched automatically, or required to install the public package.

## Design decision

No single reference covers the full need: a compact human-readable raster scene with strong craft, fixed scientific semantics, and traceable generation through the current relay. This package combines art-direction planning, candidate-specific image prompts, thumbnail/slot review, surface/light craft assessment, and scientific hard gates. It does not equate "academic" with faceless flat art, but it also does not allow expressive style to introduce unsupported anatomy or causality.

## Evidence boundary

The linked public skill documents were read from their repositories on the review date. The current update tests plan validation and review-record consistency locally. It did not generate images, compare model-rendered outputs, run a blinded preference study, or establish publisher acceptance. Visual scores and direction verdicts remain attributed human/agent judgments.
