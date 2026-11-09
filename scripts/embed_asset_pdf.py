#!/usr/bin/env python3
"""Embed one transparent asset in a PDF copy and verify bounded changes locally."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


def require_fitz():
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF embedding requires optional PyMuPDF: python3 -m pip install PyMuPDF") from exc
    return fitz


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(values):
    return all(not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v) for v in values)


def plain(value):
    """Normalize PDF geometry for equality and portable evidence."""
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return [plain(v) for v in value]


def snapshot(page):
    return {"text": page.get_text(), "drawings": plain(page.get_drawings()),
            "mediabox": list(page.mediabox), "cropbox": list(page.cropbox),
            "rect": list(page.rect), "rotation": page.rotation}


def rendered(page, scale):
    # Use the same transparent rendering/compositing path before and after.
    # Direct opaque rendering can shift unrelated antialiased pixels by one level
    # when the inserted PNG introduces a transparency group.
    pix = page.get_pixmap(matrix=require_fitz().Matrix(scale, scale), alpha=True)
    image = Image.frombytes("RGBa", (pix.width, pix.height), pix.samples).convert("RGBA")
    canvas = Image.new("RGBA", image.size, "white")
    canvas.alpha_composite(image)
    return canvas.convert("RGB")


def changed_pixels(before, after, allowed_rects, page_rect, scale):
    if before.size != after.size:
        raise ValueError("rendered page dimensions changed")
    channels = ImageChops.difference(before, after).split()
    difference = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    binary = difference.point(lambda x: 255 if x else 0)
    allowed = Image.new("L", before.size, 0)
    draw = ImageDraw.Draw(allowed)
    pixel_rects = []
    for rect in allowed_rects:
        box = [math.floor((rect[0] - page_rect[0]) * scale) - 2,
               math.floor((rect[1] - page_rect[1]) * scale) - 2,
               math.ceil((rect[2] - page_rect[0]) * scale) + 2,
               math.ceil((rect[3] - page_rect[1]) * scale) + 2]
        draw.rectangle(box, fill=255)
        pixel_rects.append(box)
    outside = ImageChops.subtract(binary, allowed)
    return {"changed_pixels": binary.histogram()[255],
            "changed_pixels_outside_allowed_regions": outside.histogram()[255],
            "allowed_pixel_rects_with_2px_margin": pixel_rects}


def embed(source, asset, outdir, rect, page_number=1, label=None,
          label_center_x=None, label_baseline_y=None, label_size=8.5,
          label_color=(0.17, 0.26, 0.29), preview_dpi=150):
    fitz = require_fitz()
    source, asset, outdir = Path(source), Path(asset), Path(outdir)
    if not source.is_file() or not asset.is_file():
        raise ValueError("source PDF and asset PNG must exist")
    if outdir.is_symlink() or (outdir.exists() and (not outdir.is_dir() or any(outdir.iterdir()))):
        raise ValueError("output directory must be new or empty, and not a symlink")
    source, asset, outdir = source.resolve(), asset.resolve(), outdir.resolve()
    if source == asset or outdir in source.parents or outdir in asset.parents:
        raise ValueError("output directory cannot contain either input")
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
        raise ValueError("page must be a positive one-based integer")
    if not finite(rect) or len(rect) != 4 or rect[0] >= rect[2] or rect[1] >= rect[3]:
        raise ValueError("rect needs finite X0 Y0 X1 Y1 with positive area")
    if not finite([preview_dpi]) or not 72 <= preview_dpi <= 600:
        raise ValueError("preview DPI must be finite and between 72 and 600")
    if not finite(label_color) or len(label_color) != 3 or any(not 0 <= v <= 1 for v in label_color):
        raise ValueError("label color must contain three values from 0 to 1")
    if label is None and (label_center_x is not None or label_baseline_y is not None):
        raise ValueError("label coordinates require a label")
    if label is not None:
        if not isinstance(label, str) or not label.strip() or any(not 32 <= ord(c) <= 126 for c in label):
            raise ValueError("native Helvetica label must contain printable ASCII text on one line")
        if not finite([label_center_x, label_baseline_y, label_size]) or label_size <= 0:
            raise ValueError("label requires finite center-x, baseline-y and positive size")
    with Image.open(asset) as im:
        if im.format != "PNG":
            raise ValueError("asset must be a PNG")
        if "A" not in im.getbands() and "transparency" not in im.info:
            raise ValueError("asset must have actual transparent pixels")
        rgba = im.convert("RGBA")
        histogram = rgba.getchannel("A").histogram()
        transparent = sum(histogram[:255])
        if not histogram[0] or histogram[0] == rgba.width * rgba.height:
            raise ValueError("asset must have fully transparent pixels and visible content")
        alpha = {"size_px": list(rgba.size), "alpha_extrema": list(rgba.getchannel("A").getextrema()),
                 "nonopaque_pixels": transparent, "fully_transparent_pixels": histogram[0]}
    source_hash, asset_hash = sha(source), sha(asset)
    with fitz.open(source) as document:
        if document.needs_pass:
            raise ValueError("encrypted PDFs requiring a password are unsupported")
        if page_number > len(document):
            raise ValueError("page exceeds source page count")
        page = document[page_number - 1]
        if page.rotation:
            raise ValueError("target page rotation must be zero; review coordinates before embedding")
        bounds = page.rect
        placement = fitz.Rect(rect)
        if not bounds.contains(placement):
            raise ValueError("asset rectangle must fit inside the selected page")
        originals = [snapshot(p) for p in document]
        before_renders = [rendered(p, preview_dpi / 72) for p in document]
        page.insert_image(placement, filename=str(asset), keep_proportion=True, overlay=True)
        factor = min(placement.width / rgba.width, placement.height / rgba.height)
        actual = fitz.Rect(placement.x0 + (placement.width - rgba.width * factor) / 2,
                           placement.y0 + (placement.height - rgba.height * factor) / 2,
                           placement.x0 + (placement.width + rgba.width * factor) / 2,
                           placement.y0 + (placement.height + rgba.height * factor) / 2)
        label_record = None
        if label is not None:
            font = fitz.Font("hebo")
            width = fitz.get_text_length(label, fontname="hebo", fontsize=label_size)
            origin = (label_center_x - width / 2, label_baseline_y)
            label_rect = fitz.Rect(origin[0], origin[1] - font.ascender * label_size,
                                   origin[0] + width, origin[1] - font.descender * label_size)
            if not bounds.contains(label_rect):
                raise ValueError("label including its font bounds must fit inside the selected page")
            page.insert_text(origin, label, fontname="hebo", fontsize=label_size, color=label_color, overlay=True)
            label_record = {"text": label, "font": "Helvetica-Bold", "size_pt": label_size,
                            "origin_pt": list(origin), "bbox_pt": list(label_rect), "color_rgb": list(label_color)}
        payload = document.tobytes(garbage=4, deflate=True)
    # Verify the serialized result, not merely the open document's current state.
    page_evidence = []
    with fitz.open(stream=payload, filetype="pdf") as result:
        if len(result) != len(originals):
            raise ValueError("page count changed")
        for i, original in enumerate(originals):
            current = snapshot(result[i])
            for field in ("mediabox", "cropbox", "rect", "rotation", "drawings"):
                if current[field] != original[field]:
                    raise ValueError("original PDF " + field + " changed on page " + str(i + 1))
            expected = original["text"] + (label + "\n" if i == page_number - 1 and label is not None else "")
            if current["text"] != expected:
                raise ValueError("original text or exact added label was not preserved on page " + str(i + 1))
            allowed = [list(placement)] if i == page_number - 1 else []
            if i == page_number - 1 and label_record:
                allowed.append(label_record["bbox_pt"])
            proof = changed_pixels(before_renders[i], rendered(result[i], preview_dpi / 72), allowed,
                                   current["rect"], preview_dpi / 72)
            if proof["changed_pixels_outside_allowed_regions"]:
                raise ValueError("pixels outside declared placement/label changed on page " + str(i + 1))
            proof.update(page=i + 1, original_text_preserved=True, original_drawings_preserved=True,
                         drawing_count=len(original["drawings"]), page_boxes_preserved=True)
            page_evidence.append(proof)
        if label_record:
            matches = [span for block in result[page_number - 1].get_text("dict")["blocks"] if "lines" in block
                       for line in block["lines"] for span in line["spans"]
                       if span["text"] == label and abs(span["origin"][0] - label_record["origin_pt"][0]) < 0.01
                       and abs(span["origin"][1] - label_baseline_y) < 0.01]
            if len(matches) != 1:
                raise ValueError("exact native PDF label was not recovered at the requested location")
            label_record["native_text_verified"] = True
        preview = rendered(result[page_number - 1], preview_dpi / 72)
    if sha(source) != source_hash or sha(asset) != asset_hash:
        raise ValueError("an input changed during composition")
    # All gates pass before creating deliverables. Never overwrite prior results.
    outdir.mkdir(parents=True, exist_ok=True)
    with (outdir / "figure.pdf").open("xb") as stream:
        stream.write(payload)
    with (outdir / "figure.png").open("xb") as stream:
        preview.save(stream, format="PNG")
    evidence = {"schema_version": "1.0", "ok": True, "source_pdf": str(source), "source_pdf_sha256": source_hash,
                "asset": str(asset), "asset_sha256": asset_hash, "source_hash_unchanged": True, "asset_hash_unchanged": True,
                "output_pdf_sha256": sha(outdir / "figure.pdf"), "preview_sha256": sha(outdir / "figure.png"),
                "page_count": len(originals), "page": page_number, "placement_rect_pt": list(placement),
                "actual_asset_rect_pt": list(actual), "image_alpha": alpha, "effective_asset_dpi": 72 / factor,
                "label": label_record, "verification_dpi": preview_dpi, "pages": page_evidence,
                "scope": "One raster PNG overlaid on the original PDF objects; existing text and vector drawings retained. The asset remains raster. Outside-region pixels match at the recorded verification DPI; this does not certify science, safe whitespace, beauty, or all renderer behavior."}
    with (outdir / "composition-evidence.json").open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--rect", nargs=4, type=float, required=True, metavar=("X0", "Y0", "X1", "Y1"))
    parser.add_argument("--page", type=int, default=1, help="One-based target page (default 1)")
    parser.add_argument("--label")
    parser.add_argument("--label-center-x", type=float)
    parser.add_argument("--label-baseline-y", type=float)
    parser.add_argument("--label-size", type=float, default=8.5)
    parser.add_argument("--label-color", nargs=3, type=float, default=(0.17, 0.26, 0.29))
    parser.add_argument("--preview-dpi", type=float, default=150)
    args = parser.parse_args()
    try:
        evidence = embed(args.source, args.asset, args.outdir, args.rect, args.page, args.label,
                         args.label_center_x, args.label_baseline_y, args.label_size,
                         args.label_color, args.preview_dpi)
        print(json.dumps({"ok": True, "pdf": str(args.outdir / "figure.pdf"), "preview": str(args.outdir / "figure.png"),
                          "pages_verified": evidence["page_count"], "native_label": bool(evidence["label"])}))
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
