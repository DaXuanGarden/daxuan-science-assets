#!/usr/bin/env python3
"""Build reproducible white/dark, thumbnail, and optional figure-slot previews."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageOps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_dir", type=Path)
    parser.add_argument("--figure", type=Path)
    parser.add_argument("--slot", nargs=4, type=int, metavar=("X", "Y", "WIDTH", "HEIGHT"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if bool(args.figure) != bool(args.slot):
        parser.error("--figure and --slot must be supplied together")
    source = args.asset_dir / "asset.png"
    asset = Image.open(source).convert("RGBA")
    planned = {"preview-white.png", "preview-dark.png", "thumbnail_200px.png", "preview-evidence.json"}
    if args.figure:
        planned.update({"placement.png", "placement-crop.png"})
    if not args.force and any((args.asset_dir / name).exists() for name in planned):
        parser.error("preview output exists; choose a new directory or use --force")
    evidence = {"asset_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "asset_size_px": list(asset.size), "fit_policy": "contain_centered_preserve_aspect", "rendered_boxes": {}, "outputs": sorted(planned - {"preview-evidence.json"}), "scope": "Display previews only; the transparent source asset is unchanged."}
    figure = None
    if args.figure:
        figure = Image.open(args.figure).convert("RGBA")
        x, y, width, height = args.slot
        if min(x, y) < 0 or min(width, height) <= 0 or x + width > figure.width or y + height > figure.height:
            parser.error("slot must fit inside the figure")
    for name, background, side in (("preview-white.png", "#FFFFFF", 600), ("preview-dark.png", "#223542", 600), ("thumbnail_200px.png", "#FFFFFF", 200)):
        preview = Image.new("RGBA", (side, side), background)
        contained = ImageOps.contain(asset, (side, side), Image.Resampling.LANCZOS)
        left, top = (side - contained.width) // 2, (side - contained.height) // 2
        preview.alpha_composite(contained, (left, top))
        evidence["rendered_boxes"][name] = [left, top, contained.width, contained.height]
        preview.convert("RGB").save(args.asset_dir / name)
    if figure is not None:
        x, y, width, height = args.slot
        contained = ImageOps.contain(asset, (width, height), Image.Resampling.LANCZOS)
        left, top = x + (width - contained.width) // 2, y + (height - contained.height) // 2
        figure.alpha_composite(contained, (left, top))
        evidence["rendered_boxes"]["placement.png"] = [left, top, contained.width, contained.height]
        figure.convert("RGB").save(args.asset_dir / "placement.png")
        margin = max(30, round(max(width, height) * .26))
        crop = (max(0, x-margin), max(0, y-margin), min(figure.width, x+width+margin), min(figure.height, y+height+margin))
        figure.crop(crop).convert("RGB").save(args.asset_dir / "placement-crop.png")
        evidence.update({"figure": str(args.figure), "figure_sha256": hashlib.sha256(args.figure.read_bytes()).hexdigest(), "slot_xywh": args.slot, "crop_ltrb": crop})
    (args.asset_dir / "preview-evidence.json").write_text(json.dumps(evidence, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
