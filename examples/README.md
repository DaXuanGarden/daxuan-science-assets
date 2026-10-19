# Reproduce the visible examples

Install the [dependencies](../requirements.txt) from the repository root, then choose a fresh output directory for each command. These runs use local native vectors and make no image-model request.

| Task | Source | Checked output |
| --- | --- | --- |
| Isolated scientific objects | [Chromosome, mitochondrion and pipette](../assets/examples/gallery.png) | Separate transparent SVG/PNG files under `assets/examples/` |
| Proposed method | [Original authored plan](../assets/examples/methodology-demo/diagram.json) | [Transparent method](../assets/examples/methodology-demo/asset.svg); no citation or result invented |
| Source-backed method | [Attributed DESeq2 plan](../assets/examples/deseq2-method/diagram.json) | [Editable dependency overview](../assets/examples/deseq2-method/asset.svg); original-model scope |
| Reference and destination colors | [Reproduction script](../scripts/build_color_example.py) | [Blue chromosome](../assets/examples/color-context/asset.svg) and local color-source/QA records |

```bash
python3 scripts/asset_tool.py render assets/examples/chromosome/asset.svg --out output/first-asset.png --qa output/first-asset-qa.json
python3 scripts/methodology_tool.py build assets/examples/deseq2-method/diagram.json --palette assets/examples/deseq2-method/palette.json --sources-dir assets/examples/deseq2-method --outdir output/deseq2-method --width 1600
python3 scripts/build_color_example.py --outdir output/color-context
python3 scripts/palette_context.py check output/color-context/color-context.json --root output/color-context --palette output/color-context/palette.json --svg output/color-context/asset.svg --out output/color-context/recheck.json
```

The blue recolor fixture uses only original bundled vectors. It demonstrates the conflict-resolution and checking mechanism; it is not evidence that a reference-paper author selected these colors. The DESeq2 excerpts retain their source attribution and CC BY 4.0 license. Private manuscript figures, screenshots and PDFs are not included.

Rebuild the gallery, mobile gallery and GIF with `python3 scripts/build_showcase.py`. The animation displays actually rendered fixtures and their QA counts; it is not a recording of image generation or a new model drawing session. Gallery/checkerboard backgrounds belong to the display, while individual assets remain transparent.

Rebuild the publication card from evidence: `python3 scripts/build_publication_card.py --review reports/publication-review.json --out output/publication-card.png`. Scores on this card are editorial estimates, not scientific or model benchmarks.
