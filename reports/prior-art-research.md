# Prior-art research

## Current review: 2026-10-19

Luban research covered live GitHub source and README files, skills.sh CLI discovery, and the ClawHub public catalog API. Separate research agents handled repository and catalog evidence; neither executed peer code. Exact URLs, inspected scope, timeouts, and metric semantics are recorded in [peer-research.json](peer-research.json).

| Peer | Category | Lesson adopted | Deliberate boundary |
| --- | --- | --- | --- |
| [ScanSci SVG](https://github.com/Rimagination/scansci-svg/blob/main/skill/SKILL.md) | Direct | Existing SVG first, semantic part editing, downloadable examples | No repository-wide license found; no prose or assets copied. Broader composition/animation is outside this skill. |
| [schematic-figure](https://github.com/lgwrightlab/schematic-figure/blob/main/.claude/skills/schematic-figure/SKILL.md) | Indirect | Editable-output promise, source constraints, actual renders | Complete figures and heavier engines are unnecessary for a single asset. |
| [scientific-schematics](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-schematics/SKILL.md) | Indirect | Bounded review and explicit missing evidence | Current source is PNG-only; do not adopt PNG as final SVG. |
| [Transparent Icons](https://skills.sh/neuromechanist/research-skills/transparent-icons) | Direct task, different format | Literal English name, shared palette, actual alpha checks | Its final output is PNG and needs sibling dependencies. |
| [SVG Figure](https://skills.sh/neuromechanist/research-skills/svg-figure) | Indirect | Named groups, reproducible example, separate editor handoff | Raster icon inserts are unsuitable for the native-only asset contract. |
| [Scientific Graphical Abstract Skill](https://clawhub.ai/jackkuo666/skills/scientific-graphical-abstract-skill) | Indirect, catalog only | Scenario-oriented English usage and concrete artifact names | Catalog claims were not treated as runtime evidence; full abstracts and charts widen the scope. |
| [Algorithmic Art](https://github.com/anthropics/skills/blob/main/skills/algorithmic-art/SKILL.md) | Craft | Explicit output list and reproducible adjustable parameters | Artistic philosophy and random generation do not establish scientific correctness. |
| [agent-browser](https://github.com/vercel-labs/agent-browser/blob/main/README.md) | Craft | Literal purpose, one install route, visible first result | Browser dependencies and unrelated actions are not adopted. |

Signals observed during this review include 31 repository stars for ScanSci, 44 for schematic-figure, and 52,745 for the entire K-Dense library. Transparent Icons and SVG Figure displayed 26 and 45 skills.sh installs respectively. ClawHub returned 1,427 downloads, 37 installs, and 1 catalog star for the graphical abstract candidate. These counters have different meanings, are date-sensitive, and are not ratings or quality measurements. No counters were added together.

Some raw GitHub requests timed out; API content retrieval succeeded. skills.sh and ClawHub channels succeeded. Tessl was not needed after sufficient coverage; it was not claimed as searched. Source review does not reproduce upstream benchmarks, model runs, or editor behavior.

## Earlier creation research

The first version queried `scientific svg assets`, `transparent scientific icons`, and `semantic svg editing` through the qiaomu prior-art runner. Both skills.sh and SkillsMP succeeded for all queries, yielding 26 deduplicated candidate families. The dated raw record remains in [prior-art-candidates.json](prior-art-candidates.json). Earlier snapshots can differ from the live counters above.

## Keep / adapt / reject / contribute

- **Keep:** vector-source-first editing, named parts, scoped scientific content, actual rendering.
- **Adapt:** a full-figure workflow becomes an isolated-asset workflow with optional image references. Package text is English; conversation follows the user.
- **Reject:** embedded-raster final SVG, PNG-only handoff, invented mechanisms, hidden retries, unsupported backend or editor claims.
- **Contribute:** one native asset contract across three input routes, role-bound recoloring with geometry checks, separate structure/alpha evidence, and a reproducible English package/showcase check.

These are implementation choices and semantic lessons, not claims of first invention or superior generated artwork. No peer code, artwork, or instruction prose was copied.
