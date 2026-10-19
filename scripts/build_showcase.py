#!/usr/bin/env python3
"""Rebuild English gallery, actual-fixture animation, and optional Luban review card."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from PIL import Image, ImageDraw, ImageFont

import asset_tool as tool

ROOT = Path(__file__).resolve().parents[1]
INK = "#4D493F"
MUTED = "#8A806C"


def font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


def write(draw, xy, value, size=22, fill=INK):
    draw.text(xy, value, font=font(size), fill=fill)


def fit(image, size):
    result = image.copy()
    result.thumbnail(size, Image.Resampling.LANCZOS)
    return result


def build_gallery():
    gallery = Image.new("RGBA", (1200, 760), "white")
    draw = ImageDraw.Draw(gallery)
    write(draw, (42, 30), "Daxuan Scientific Assets", 34)
    write(draw, (42, 82), "Transparent SVG / Editable parts / Consistent warm gold", 21, MUTED)
    mobile = Image.new("RGBA", (390, 1360), "white")
    mobile_draw = ImageDraw.Draw(mobile)
    write(mobile_draw, (22, 24), "Daxuan Scientific Assets", 25)
    write(mobile_draw, (22, 66), "Transparent SVG / Editable parts", 17, MUTED)
    frames = []
    subjects = [("chromosome", "Replicated chromosome", "Genetics asset"),
                ("mitochondrion", "Mitochondrion", "Organelle asset"),
                ("pipette", "Single-channel pipette", "Laboratory asset")]
    with tempfile.TemporaryDirectory(prefix="daxuan-showcase-") as directory:
        for index, (slug, label, category) in enumerate(subjects):
            source = ROOT/"assets/examples"/slug/"asset.svg"
            rendered = Path(directory)/(slug+".png")
            qa = tool.render(source, rendered, width=540)
            if not qa["ok"]:
                raise ValueError("Example failed actual render: " + slug)
            with Image.open(rendered) as original:
                preview = fit(original.convert("RGBA"), (275, 450))
            left = 40+index*395
            gallery.alpha_composite(preview, (left+(310-preview.width)//2, 150+(450-preview.height)//2))
            write(draw, (left, 632), label, 24)
            write(draw, (left, 675), category, 19, MUTED)
            narrow_preview = fit(preview, (270, 270))
            row_top = 112+index*403
            mobile.alpha_composite(narrow_preview, ((390-narrow_preview.width)//2, row_top+(280-narrow_preview.height)//2))
            write(mobile_draw, (24, row_top+298), label, 23)
            write(mobile_draw, (24, row_top+338), category, 18, MUTED)
            frame = Image.new("RGBA", (900, 600), "#FAF9F6")
            fd = ImageDraw.Draw(frame)
            write(fd, (36, 28), "Daxuan Scientific Assets", 29)
            write(fd, (36, 76), "Recorded native SVG example / No image-model call", 17, MUTED)
            for y in range(120, 530, 20):
                for x in range(35, 400, 20):
                    fd.rectangle((x, y, min(x+19, 399), min(y+19, 529)), fill="#ECEAE4" if (x//20+y//20)%2 else "#F8F7F3")
            frame_preview = fit(preview, (300, 390))
            frame.alpha_composite(frame_preview, (35+(365-frame_preview.width)//2, 120+(410-frame_preview.height)//2))
            write(fd, (435, 155), label, 26)
            write(fd, (435, 215), "Native vector: checked", 21)
            write(fd, (435, 265), "Transparent alpha: checked", 21)
            write(fd, (435, 315), "Named groups: "+str(qa["svg"]["named_groups"]), 21)
            write(fd, (435, 365), "Color bindings: "+str(qa["svg"]["palette_bindings"]), 21)
            write(fd, (36, 558), "Display checkerboard only; individual asset files are transparent.", 17, MUTED)
            frames.append(frame.convert("RGB"))
    output = ROOT/"assets/showcase"; output.mkdir(parents=True, exist_ok=True)
    gallery.convert("RGB").save(ROOT/"assets/examples/gallery.png")
    mobile.convert("RGB").save(output/"gallery-mobile.png")
    frames[0].save(output/"demo.gif", save_all=True, append_images=frames[1:], duration=1800, loop=0)


def build_certificate(review_path):
    review = json.loads(review_path.read_text())
    canvas = Image.new("RGB", (1100, 670), "#F6F4EE")
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((28, 28, 1072, 642), radius=24, outline="#C4AC76", width=3)
    write(draw, (62, 60), "LUBAN / LOCAL REVIEW CARD", 22, MUTED)
    write(draw, (62, 120), "Daxuan Scientific Assets", 42)
    write(draw, (62, 185), "English package refinement / v0.1.1", 24, MUTED)
    write(draw, (62, 255), f"Editorial estimate: {review['baseline_total']} -> {review['candidate_total']} / 100", 32)
    write(draw, (62, 316), "Local runs + dry-run walkthroughs; not a model benchmark.", 20, MUTED)
    write(draw, (62, 380), "22 tool tests / 3 unchanged native SVG examples", 27)
    write(draw, (62, 429), "English docs, examples, metadata and previews", 27)
    write(draw, (62, 488), "Next: live image-reference and editor-import evidence", 22)
    write(draw, (62, 562), "Local runtime verified / No public release / No human blind review", 18, MUTED)
    canvas.save(ROOT/"assets/showcase/luban-review-card.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, help="Optional independent editorial audit JSON for a result card")
    args = parser.parse_args()
    build_gallery()
    if args.review:
        build_certificate(args.review)
    print(json.dumps({"ok": True, "gallery": "assets/examples/gallery.png", "animation": "assets/showcase/demo.gif", "model_generation": False, "certificate": bool(args.review)}))


if __name__ == "__main__":
    main()
