# Image routing and individual transparent assets · 0.2.0

## Problem and correction

Version 0.1.1 checked only the optional official OAuth helper. This environment uses a custom Codex provider; absence of the helper's OAuth file was incorrectly generalized to image unavailability. Existing project records identified the same relay with a successful earlier `gpt-image-2` workflow. The new router selected the active custom provider without requiring an official auth file.

The earlier user-facing image was a white display board containing labels and multiple illustrations. The underlying PNGs did have actual alpha, but the handoff did not show the requested individual transparent material. Version 0.2.0 requires the actual single transparent PNG to be shown directly.

## Two decisions

| Decision | Rule |
| --- | --- |
| Drawing method | Native SVG when structure, silhouette, editability and palette already satisfy the brief; image exploration for complex form or an explicit request |
| Official image source | Exposed host image tool, otherwise optional existing OAuth helper; do not substitute API-key billing |
| Relay image source | Active config/profile base plus matching provider API credential; separate image base/key can be configured explicitly |
| Final format | Native transparent SVG and its actual transparent PNG; model reference remains separate |

The router does not assume that a Responses endpoint supports Images. It also does not switch to another provider or model after a failure. Bare hosts gain `/v1`; explicit API paths are preserved. Python 3.9–3.10 uses tomli rather than silently dropping TOML parsing.

## Actual evidence

- [Local source selection](image-backend-v020-preflight.json): selected relay, matching active-provider credential present; no generation at this step.
- [Models probe](image-backend-v020-probe.json): HTTP 200; source listed image models. This alone is not generation evidence.
- [Live image request](image-generation-v020-live.json): one authorized `gpt-image-2` generation returned HTTP 200 and a saved PNG. The response is RGB and opaque. No automatic retry, login or account/config change occurred.
- [Single transparent example](../assets/examples/blue-chromosome/asset.png): native rendered PNG, separate from the [opaque model reference](../assets/examples/blue-chromosome/reference.png). The accepted clean vector was retained after comparing the textured model reference; it is not claimed to be an automatic trace.
- [Unit checks](unit-tests.json): meaningful source, credential-binding, no-retry, payload, alpha, and existing vector-tool checks.

The live provider returned 1295 × 1214 pixels despite a 1024 × 1024 request. Actual dimensions are recorded instead of assuming the requested size. The generated reference adds textured shading; the final native asset keeps the user's restrained palette and precise editing controls.

## Credential and transport boundaries

Only the selected Codex config/auth files and named runtime environment variables are read. Keys stay in memory. Reports contain credential-source labels, never values, raw provider messages or account output. OAuth tokens never become relay keys. A changed origin requires an explicit image-only key. Downloads on the selected origin can retain authorization; cross-origin CDN downloads do not receive it, and authenticated redirects are not followed.

## Remaining evidence limits

Official host/OAuth live generation was not exercised because this environment uses a relay. Official selection behavior is covered by local tests, not a live official generation claim. Relay edits are covered by payload tests but have not been sent to the live provider. Native model alpha, human scientific review, and editor import/edit/reopen are not claimed. An opaque model reference plus a separately verified transparent native render is the demonstrated route.

The earlier Luban scores and English-package comparisons remain historical 0.1.1 evidence, not a new score for this routing implementation.
