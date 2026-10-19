# SVG contract and tools

## Native structure

Use an SVG-namespace root with valid viewBox and dimensions. Native paths, shapes, gradients, clipPaths, and masks are available. Transparent canvases need no background rectangle.

Exclude `<image>` (including embedded SVG), external resources, scripts, event handlers, foreignObject, XML stylesheets, and animation. Expand stylesheets and CSS variables to explicit attributes for export.

Provide named groups and stable IDs for editable parts. Keep outlines, highlights, and shadows with their part. Expand `<use>` when independent editing matters. IDs must be unique and internal references resolved.

## Palette roles

Roles: `body`, `body_light`, `body_shadow`, `outline`, `detail`, `highlight`, `accent`, `muted`, `field`, `guide`. Extra roles may live in one asset's palette without becoming global rules.

```xml
<g id="outer-membrane">
  <path d="..." fill="#D4B66C" data-fill-role="body"
        stroke="#AC8E4C" data-stroke-role="outline"/>
</g>
<linearGradient id="body-lighting">
  <stop offset="0%" stop-color="#B39857" data-stop-role="body_shadow"/>
  <stop offset="100%" stop-color="#E3C98A" data-stop-role="body_light"/>
</linearGradient>
```

Write actual hex colors as well as role tags. Biological color encoding needs a user-approved meaning or legend.

The palette file uses a top-level `colors` object, not `roles`. For example:

```json
{"name": "custom", "colors": {"body": "#91B2C8", "outline": "#5F91AF", "accent": "#BB748B"}}
```

Include every role used in the SVG, with six-digit hex RGB values. Reuse the supplied palette's structure when extending it. Before handoff of a new custom palette, run `recolor` to a separate temporary SVG and verify that its geometry stays unchanged; structure and alpha checks alone do not validate palette-file compatibility.

## Commands

Resolve `scripts/` against the installed skill directory. Commands below assume that working directory.

```bash
python3 scripts/asset_tool.py init mitochondrion --subject "Generic mitochondrion with double membrane and cristae" --outdir output/mitochondrion --palette warm-gold
# After the agent draws output/mitochondrion/asset.svg:
python3 scripts/asset_tool.py check output/mitochondrion/asset.svg
python3 scripts/asset_tool.py render output/mitochondrion/asset.svg --out output/mitochondrion/asset.png --qa output/mitochondrion/qa.json --width 720
python3 scripts/asset_tool.py recolor output/mitochondrion/asset.svg --palette output/mitochondrion/palette.json --out output/mitochondrion/asset-v2.svg
```

`init` creates no artwork. `recolor` validates all bindings before writing; unknown roles and conflicting inline styles fail. A structure digest excludes paint values and detects unintended geometry changes.

`check` examines structure only. `render` uses rsvg-convert or CairoSVG; Pillow inspects actual PNG alpha, corners, edges, and nonempty foreground. Missing dependencies leave transparency unverified. Commands return nonzero on failure and reject implicit overwrites. `--force` permits writing selected outputs again.

## Visual and editor checks

Automatic inspection catches embedded bitmaps, canvas rectangles, broken references, and some clipping. It cannot identify every internal background shape or certify science. View the real PNG, including holes, edges, and part relationships.

Do not delete legitimate white or pale parts as background. Claim successful editor import, editing, saving, and reopening only after actually trying those actions.
