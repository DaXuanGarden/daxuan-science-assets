# Image sources and vector reconstruction

Choose the drawing route separately from the image provider. Simple, supported shapes and edits can finish as native SVG without an image request. Complex organic form or an explicit generation request uses an image reference, followed by native reconstruction. A successful image call alone does not deliver an editable vector.

## Source selection

| Active setup | Image source | Credential boundary |
| --- | --- | --- |
| Official Codex login | Exposed host image tool; otherwise optional `codex-gpt-image` OAuth helper | Official session; no API-key billing substitution |
| Configured custom provider | Its OpenAI-compatible Images API | Matching active-provider key or bearer credential; never OAuth tokens |
| Explicit separate image base | That image provider | Paired `DAXUAN_SCIENCE_IMAGE_API_KEY` required when the origin differs |

`scripts/image_backend.py` reads the selected Codex config/profile and normalizes a bare host to `/v1`. It supports the active provider's `env_key`, `experimental_bearer_token`, Bearer Authorization header, and API-key auth-file/environment mode. An explicit image-only key/base can override the image source. It does not write accounts, credentials, provider settings, or environment files. Python 3.9–3.10 needs `tomli`; Python 3.11+ has `tomllib`.

Do not assume a working Responses provider supports Images. A config/key check, a model listing, a saved generated PNG, and actual alpha are different evidence levels. Report each separately. In particular, absence of the optional OAuth file does not make a configured relay unavailable.

```bash
python3 scripts/image_backend.py --doctor
python3 scripts/image_backend.py --doctor --probe
```

Doctor is local unless `--probe` is given; probe performs one models GET, never generation. `--config`, `--profile`, and `--auth-file` can select an existing setup. Parse errors are errors, not an excuse to guess the official route.

Use host session provider metadata when it is exposed. Otherwise the selected config/profile is the available source of truth; pass the actual session's config/profile when it differs from the default. For an exposed native image tool, add `--native-tool` to doctor. A helper-only failure does not override an available host tool.

## Execute one authorized image request

```bash
# Dry-run: source, model and files only; no request, secret or prompt is printed.
python3 scripts/image_backend.py --prompt-file output/chromosome/image_prompt.txt --out output/chromosome/reference.png
# The same plan, executed once:
python3 scripts/image_backend.py --prompt-file output/chromosome/image_prompt.txt --out output/chromosome/reference.png --execute --report output/chromosome/image-evidence.json
```

Default model is `gpt-image-2`, overridable by `--model` or `DAXUAN_SCIENCE_IMAGE_MODEL`. Use a model actually supported by the selected source. Size, quality and reference images are optional flags. `--image` sends an authorized local PNG/JPEG/WebP to the edits endpoint; text-only requests use generations. Do not switch models after a failure. Relay execution sends at most one generation/edit POST and never retries a billed request automatically.

For a separate image service, set `DAXUAN_SCIENCE_IMAGE_BASE_URL` and `DAXUAN_SCIENCE_IMAGE_API_KEY` in the calling environment. Do not put keys in prompts, examples, CLI arguments or reports. Same-origin image downloads can use the selected key; cross-origin CDN downloads do not receive it. Authenticated redirects are not followed.

For official sessions, invoke an exposed native image tool directly, following the host imagegen instructions. `--native-tool` only records a tool genuinely present in the current inventory; it does not create one. The optional OAuth helper is used only if its readiness check succeeds, with no automatic login. The older `codex_reference.py --doctor` checks **only this optional OAuth helper** and is retained for compatibility, not general source detection.

## Transparency and final files

This adapter defaults to an opaque **reference**, because the inspected `gpt-image-2` OAuth helper does not support transparent mode. Other sources/models may support `--background transparent`; verify actual pixels rather than inferring support from a model name. RGBA with every alpha value at 255 is opaque. A transparent request that returns opaque pixels fails without a regeneration retry.

For the SVG workflow, inspect the reference and reconstruct paths, named parts and palette roles. Render the resulting SVG to an actual transparent PNG. Keep three files/concepts distinct:

- `reference.png`: model output; may have a white background.
- `asset.svg` and `asset.png`: native vector and its verified transparent companion.
- Optional `preview_white.png` or checkerboard: display aids, never the delivered transparent asset.

Show the individual `asset.png` directly in the final response. A gallery or certificate is not a replacement for a single isolated material. Record the actual source/model, saved output, reconstruction decision and alpha checks. Inspect scientific structure independently; a generated chromosome, cell or organ does not certify anatomy or gene coordinates.
