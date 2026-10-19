# Public distribution trust review

Scope: version 0.5.1, publication packaging review. This is an author/agent review, not a third-party security audit.

The existing vector, image-source and methodology tools remain byte-identical to the frozen 0.5.0 package. The added color-example builder reads original bundled vectors, writes a fresh local directory, recolors with the existing helper, renders a real PNG and checks the recorded source context. It performs no network call, credential read or deletion. Implicit overwrites are refused.

The optional image adapter selects the active official or relay source and binds credentials to its origin. It supports the implemented request paths documented in references/codex-image.md; the historical trust-review.md described only the older prompt-only adapter. No new image request is part of public installation or CI. Official live generation and relay reference-image edits remain untested.

GitHub Actions use read-only repository permissions and produce native-render artifacts. They do not receive or require image-provider secrets. Public examples contain original generic art and attributed CC BY extracts, without private manuscripts or screenshots. The locally configured relay hostname was replaced by a reserved example domain in three historical reports, with explicit redaction notes.

The SVG parser enforces a static-asset contract, not a complete hostile-file sandbox. Source and palette checks establish recorded consistency, not scientific validity. Editor import/edit/reopen, human blind review and equivalent behavior across runtimes remain untested.
