# Embed an approved asset in a PDF figure

Use this optional local assembly step when the user requests an existing PDF with an approved illustration placed in a specified empty region. It adds one raster PNG and optional exact native text to a copy of the PDF. It does not redraw statistical results, infer a safe central region, or turn the illustration into vector art.

Install the optional dependency only for this route:

```bash
python3 -m pip install -r requirements-pdf.txt
python3 scripts/embed_asset_pdf.py \
  --source input/figure.pdf --asset output/selected/asset.png \
  --outdir output/assembled-v1 --rect 240 210 320 290 \
  --label LST --label-center-x 280 --label-baseline-y 306 --label-size 8.5
```

Coordinates are PDF points (72 points per inch), measured from the visible page's top left. `--page` is one-based and defaults to 1. Rotated target pages are refused rather than guessing a coordinate transformation. Some annotation-bearing PDFs may fail the strict drawing-preservation check; refusal leaves the inputs intact. The tool does not remove annotations to force a pass. The rectangle and all label font bounds must fit the page. Supply all label coordinates with `--label`; omit all label flags when no label is requested. Native Helvetica-Bold labels support printable ASCII on one line. Keep label wording in the text manifest. Other scripts or alphabets need a deliberately selected embedded font and separate verification.

The PNG must include fully transparent pixels and visible content. Its original aspect ratio is preserved and centered within the rectangle. The tool refuses opaque assets, invisible assets, existing nonempty output directories and output symlinks. It never edits either input or overwrites an earlier result. Use a new output version for each assembly.

## Verification and deliverables

The tool serializes the assembled PDF, reopens it, and verifies:

- Source and asset hashes are unchanged.
- Page count, media/crop boxes, rotations, original text and drawing objects are preserved on every page.
- The exact added label is recovered as native PDF text at the requested location.
- Pixels outside the declared asset rectangle and label bounds match at the recorded verification DPI, allowing a two-pixel antialias margin around those regions. Unedited pages match everywhere.

Both sides of the pixel comparison use the same transparent render followed by white compositing. This avoids unrelated one-level antialias changes that MuPDF's direct opaque renderer can introduce when an image adds transparency. Equality at one verification DPI does not prove behavior in every PDF renderer.

The new/empty output folder receives `figure.pdf`, `figure.png` and `composition-evidence.json`. Evidence includes input/output hashes, actual placement bounds, image alpha facts, effective asset DPI, exact label information and per-page preservation checks. `--preview-dpi` controls the preview and pixel proof (72–600, default 150). The original PDF's text and vector drawings remain native; the inserted illustration remains raster.

## Visual acceptance still requires inspection

Before assembly, choose the rectangle from the actual figure and confirm it contains no data to be covered. After assembly, inspect the **reopened PDF preview**, the unscaled slot and the full figure. Verify breathing room, circle/branch clearance, label placement, gesture recognition and visual hierarchy. An overlay can preserve underlying objects yet visually cover them inside its allowed rectangle; structural checks do not establish safe whitespace or beauty. Use [visual audit](visual-audit.md) and [refinement review](aesthetic-review.md) for actual visual judgments.

When acting on an earlier audit, carry only the selected priority findings into the refinement prompt and preserve the accepted features. Compare the same crop and placement size before and after; save the final assembly evidence with the review. Do not claim a requested edit improved merely because a new file was generated, and do not re-embed a PDF that already contains the same asset or label. Start from the original clean figure whenever possible.
