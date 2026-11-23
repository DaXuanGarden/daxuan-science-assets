# Aesthetic Design Workflow Polish

Reviewed on 2026-11-23 for generated raster assets used as compact scientific illustrations. Version: 0.9.0 candidate. This pass improves art direction and aesthetic review; it does not claim that generated images are now more attractive without rendered-candidate evidence.

## 1. Premise challenge

- **Need:** researchers need small generated images that look intentional in a paper figure while preserving the claim and evidence boundary.
- **Distinct angle:** candidate-specific image prompts are joined to a fixed science brief, pairwise visual comparison, and candidate-level science review. The existing image backend and relay remain the execution path.
- **Installation reason:** the package makes design decisions, prompts, and review criteria reusable instead of relying on an unrecorded one-off prompt.
- **Visible outcome:** a direction plan, one prompt and evidence record per image, and a review that records what actually differs.

Conclusion: viable material. Improve the image-model art direction and review loop while retaining generated raster as the requested medium.

## 2. Design references

| Reference | Useful method | Adopted here | Kept out of scope |
|---|---|---|---|
| [Anthropic canvas-design](https://github.com/anthropics/skills/tree/main/skills/canvas-design) | Establish a visual philosophy before making an image | Subject-specific composition, form, material, and negative-space direction | Abstract poster freedom that could obscure the scientific subject |
| [Anthropic frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) | Choose a visual direction and challenge generated defaults | Check for generic rendering, repeated views, color-only variation, and clutter | Web layout, CSS, hero sections, and typography systems |
| Local `character-design` skill | Make silhouette, pose, gesture, and expression readable | Natural pose and silhouette checks at thumbnail size | Exaggerated character proportions or expression; local skill is not a package dependency |
| OpenAI bundled `imagegen` skill | Separate image requests and inspect saved output | One image prompt per candidate; inspect outputs rather than infer from prompts | A replacement provider, credential, or billing route; local skill is not a package dependency |
| [K-Dense scientific-schematics](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/scientific-schematics) | Iterate with source-aware scientific critique | Keep science fidelity separate from appearance review | Its API setup and fixed numeric journal thresholds |
| Local `generate-scientific-graphical-abstract` and `paper-illustration-image2` skills | Connect visual hierarchy to the study's claim and iterate from critique | Hold the claim and relationships fixed while exploring form | Multi-node abstract layouts and conference-specific style rules as a template for a small spot illustration; these local skills are not package dependencies |

The expanded comparison and limits are in [aesthetic-design-peers.md](aesthetic-design-peers.md). Locally installed skills were inspected as references only; they are not copied, downloaded, or required by this package.

## 3. Positioning

The skill began as a scientific asset authoring package and now also guides model-generated raster art direction. Its niche is **small, expressive scientific images whose visual design can vary while their scientific meaning stays fixed**.

## 4. Independent review

The 0.9.0 candidate received **76/100** in an independent, evidence-bounded editorial review using Luban's nine weights. This is a structural review of the candidate and available evidence, not a baseline comparison, blind aesthetic study, or measurement of improved model output.

| Dimension | Score | Evidence and limitation |
|---|---:|---|
| Frontmatter and triggers | 6/7 | [SKILL.md](../SKILL.md) defines generation, refinement, review, and output modes; description is somewhat long. |
| Workflow clarity | 11/12 | The workflow locks scientific meaning before choosing art direction, then generates and reviews each image separately. |
| Failure encoding | 10/12 | The CLI rejects missing plans, mismatched candidate counts, and cosmetic-only differences; text comparison cannot recognize semantic similarity. |
| Checkpoints | 5/6 | Review requires actual candidate pairs, thumbnail size, destination slot, and science fidelity; no model-rendered candidates were checked this pass. |
| Executable specificity | 15/17 | The JSON plan, three initialization commands, and review schema are provided; the prompt example references a bundled plan rather than duplicating it. |
| Resource integration | 3/4 | Public and local design references are compared, with adoption and exclusion boundaries; some local skills have no public URL. |
| Architecture | 10/12 | Planning, generation, science review, and aesthetic review are separated; duplicated guidance may add maintenance cost. |
| Runtime behavior | 10/23 | Existing evidence records 148/148 unit tests and 5/5 examples, but this pass did not rerun them or call the image model. |
| Negatives and boundaries | 6/7 | Unsupported causality, mechanisms, and superficial candidate variation are excluded; reviewer integrity remains necessary. |

The independent review found no content-level release blocker. The structural audit reported 13 PASS, 1 WARN, and 0 FAIL; the warning is that the showcase GIF has no recording script.

## 5. Remaining gaps

- **Highest priority:** generate separate images from several direction cards through the existing relay, then compare actual outputs at thumbnail size and in the intended figure slot.
- **Next:** record a human or independently attributed preference review; no blinded preference study exists.
- **Maintenance:** watch whether overlapping instructions between the entrypoint, README, and art-direction guide drift apart.
- **Showcase:** add a reproducible recording path for the existing demo when that work is in scope.

## 6. Three refinement directions

| Direction | Scope | Benefit | Cost or risk |
|---|---|---|---|
| A. Art-direction cards | Specify composition, medium, silhouette, light/material, a signature detail, and intent per image | Gives the model concrete visual decisions to follow | Prompts still cannot guarantee rendered differences |
| B. Rendered-candidate audit | Generate from each card, compare actual images pairwise, and review at final size | Tests whether the method changes the image users see | Uses the configured image service and may incur provider charges |
| C. Separate design/review skill kit | Package art direction and visual critique as separate reusable skills | Could support broader image workflows | Adds installation and routing overhead; not part of this release |

Recommendation: retain A and the review gates in this release; use B for the next authorized image-generation evaluation. Do not split into a skill suite without a separate scope decision.

## 7. Implemented rewrite

This pass changes the raster aesthetic workflow: one direction card and prompt per candidate, meaningful pairwise variation, and review of actual visible differences and scientific fidelity. The backend, model selection, credentials, and billing route are unchanged.

Core rule now in [art-direction.md](../references/art-direction.md):

> Keep the scientific subject, action, evidence boundary, relation semantics, text, and palette roles fixed across this candidate set. A direction card cannot add a diagnosis, mechanism, causal claim, anatomy, data, or label. Render only this candidate, not a contact sheet.

## 8. README and showcase

The README now introduces three deliberate directions by default and links to the reusable plan and commands. The bundled direction plan demonstrates profile gouache, three-quarter pencil and watercolor, and layered paper relief while holding the subject and palette roles fixed. Those are prompt examples, not generated-image evidence.

## 9. Verification and next steps

- Completed: implementation, reviewer-record checks, example direction plan, reference report, and structural audit.
- Previously recorded in [aesthetic-workflow-v090.json](aesthetic-workflow-v090.json): 148/148 tests, 5/5 examples, package and example checks passed. These checks were not rerun for this review.
- Not performed: image generation, rendered-candidate comparison, blind preference review, or journal acceptance assessment.
- Next evaluation: run one explicit image request per selected direction through the existing backend and record both visual and science review results.

## 10. Review card

```text
LUBAN REVIEW  |  Daxuan Scientific Assets  |  0.9.0 candidate
76/100 structural editorial review; not a measured aesthetic gain
Distinct prompt directions + pairwise image review + science-fidelity gates
Next proof: compare actual relay-generated candidates in the final figure slot
```

## 11. Follow-up discipline

Watch canvas-design for visual planning, character-design for pose readability, and scientific-schematics for evidence-aware iteration. The next review should start with actual rendered candidates and record when different prompts converge to visually similar results.

## 12. User decisions

No direction decision is required for this refinement. A future image-generation run should use the existing authorized relay route and make one request per candidate.

## 13. Sources

Public source URLs and design limits are listed above and in [aesthetic-design-peers.md](aesthetic-design-peers.md). Local validation evidence and its limitations are in [aesthetic-workflow-v090.json](aesthetic-workflow-v090.json).
