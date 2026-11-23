# Server Relay Workflow

This guide runs the same image adapter on a Mac or Linux Codex host that already has the desired relay configured. The adapter reads that process user's active Codex config/profile and resolves the matching credential in memory. It does not provision a relay, copy a key from another computer, or change the model source.

## Install and update

Install the complete Skill package, including its scripts, for Codex:

```bash
npx skills add DaXuanGarden/daxuan-science-assets --skill daxuan-science-assets --agent codex --global --copy --yes
```

Update a Skills CLI installation with:

```bash
npx skills update daxuan-science-assets
```

Alternatively, use a Git-managed installation. Clone once into Codex's global skills directory, then fast-forward it when updating:

```bash
git clone https://github.com/DaXuanGarden/daxuan-science-assets.git "$HOME/.agents/skills/daxuan-science-assets"
git -C "$HOME/.agents/skills/daxuan-science-assets" pull --ff-only
```

Do not use both installation methods for the same Codex account. If the destination already exists, inspect it and update it with the method that originally installed it; do not delete or overwrite a local copy to make a clone command succeed. Reload the Codex session after an update so it discovers the current Skill instructions.

## Install local dependencies

The Skills CLI installs instructions and scripts; Python and optional system libraries are separate. From the installed package directory:

```bash
cd "$HOME/.agents/skills/daxuan-science-assets"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The PDF assembly route additionally needs PyMuPDF:

```bash
.venv/bin/python -m pip install -r requirements-pdf.txt
```

On Debian or Ubuntu, install the system SVG renderer when native SVG rendering is needed:

```bash
sudo apt-get install librsvg2-bin
```

The image adapter itself uses Python, Pillow, and the existing Codex configuration. It does not need a provider SDK, a second API account, or a separately installed image-generation Skill for the configured relay route.

## Verify the existing relay

Run the doctor from the server account that owns the relay configuration:

```bash
.venv/bin/python scripts/image_backend.py --doctor --probe
```

The adapter uses the active profile from the default Codex configuration. If the server uses a non-default config or a named profile, select those explicitly:

```bash
.venv/bin/python scripts/image_backend.py \
  --config /path/to/codex/config.toml --profile server-image \
  --doctor --probe
```

`--doctor` checks local route and credential readiness. `--probe` adds one `GET /models`; it does not generate an image or establish that every listed model supports Images. The report redacts the relay base URL and never returns credential values. Keep the config, auth file, environment, and probe report out of public commits if local account metadata is present.

For a relay using `env_key`, make the existing credential available to the same server process through its current secret manager or service environment. For a relay using a configured bearer token or authorization header, the adapter reads the selected active provider's setting. OAuth tokens are not forwarded to a relay. Do not paste credentials into chat, prompts, command-line arguments, this Skill, or its reports. If the selected route or matching credential is not ready, stop and fix the server's existing Codex setup; do not silently switch providers.

## Generate and review an asset

Prepare the brief, exact text and relation manifests, source notes, and `image_prompt.txt` using the normal [image-first workflow](codex-image.md). Choose a new output directory and make one explicit request:

```bash
mkdir -p output/relay-asset
.venv/bin/python scripts/image_backend.py \
  --prompt-file output/relay-asset/image_prompt.txt \
  --out output/relay-asset/asset.png \
  --report output/relay-asset/generation-evidence.json \
  --model gpt-image-2 --background transparent --execute
```

Use `gpt-image-2` only when that is the model selected for the work and supported by the active relay. Each execution sends one generation request; it does not retry a failed or opaque result. For image editing, pass only the user-approved local reference with `--image` and make sure its use with the provider is authorized.

Then run deterministic raster checks:

```bash
.venv/bin/python scripts/raster_asset_qa.py output/relay-asset
```

For an appearance-focused asset, create a preview at the actual figure slot, have a reviewer compare the isolated image and full composition, record the review, and validate it with `scripts/aesthetic_review.py`. A successful HTTP response, alpha channel, or QA pass does not certify scientific accuracy, attractive appearance, or fit in the destination.

## Place an asset in a multipage PDF

Start with the clean source PDF and an approved transparent PNG. Inspect the actual target page first and measure an empty placement rectangle in PDF points from the visible top-left corner. Do not infer a safe central region from page size alone. The PNG is centered without stretching inside the rectangle.

```bash
.venv/bin/python scripts/embed_asset_pdf.py \
  --source input/figures-1-7.pdf \
  --asset output/relay-asset/asset.png \
  --outdir output/figures-1-7-with-asset \
  --page 4 --rect LEFT TOP RIGHT BOTTOM --preview-dpi 300
```

Replace the four rectangle placeholders with measured numeric PDF-point coordinates. `--page` is one-based; use the page that contains the intended slot. If the original PDF already contains the exact native label, do not add it again. If a label is missing, add it with the optional `--label`, `--label-center-x`, `--label-baseline-y`, and `--label-size` arguments after measuring its location. Only printable ASCII labels are supported by the built-in Helvetica-Bold route.

The command writes a new `figure.pdf`, a rendered `figure.png`, and `composition-evidence.json` in an empty output directory. It reopens the serialized PDF and checks page geometry, original text and vector drawings, page count, requested label, image alpha, and pixels outside the declared placement and label regions. An image already embedded in a source PDF remains raster; surrounding original PDF text and vector content remain intact. Any validation failure stops delivery and preserves the inputs.

Inspect the reopened page preview, the placement crop at final size, and the complete multipage figure. Confirm circle/branch clearance, label position, line and label readability, and that no data are covered. Structural checks do not determine whether a placement is visually safe or aesthetically successful.

## Credential and evidence boundary

- Keep relay keys, private relay URLs, Codex auth files, and user-specific config outside the Skill repository and generated evidence.
- Do not upload private manuscript PDFs or generated research assets unless the user separately requests their publication.
- A local config check, a models probe, successful image generation, verified alpha, and successful PDF preservation are separate evidence levels.
- This workflow documents the existing Mac-to-server mechanism. It does not claim a live server run; validate the target account and relay before relying on it for a paper figure.
