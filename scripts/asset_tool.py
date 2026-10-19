#!/usr/bin/env python3
"""Initialize, inspect, render, and recolor native scientific SVG assets."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from xml.etree import ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
ROLES = ("body", "body_light", "body_shadow", "outline", "detail", "highlight", "accent", "muted", "field", "guide")
PRESET_VALUES = {
    "warm-gold": ("#D4B66C", "#E3C98A", "#B39857", "#AC8E4C", "#BDA67B", "#F2E0AD", "#D6655B", "#C4B99F", "#EEE9DE", "#9C9D94"),
    "slate-blue": ("#719AB1", "#ADC9D7", "#4E758C", "#43657A", "#6E8D9C", "#D4E4EC", "#D2876F", "#ADBCC4", "#ECF1F4", "#8D9AA2"),
    "teal": ("#78A79A", "#AFCDC3", "#527D72", "#436E62", "#709288", "#DCECE6", "#CD8974", "#AFBFB8", "#EDF3EF", "#91A29B"),
    "neutral": ("#A8A69E", "#D0CEC6", "#85837B", "#706E67", "#96938A", "#E7E5DF", "#AD8074", "#C0BDB4", "#F0EFEA", "#9D9B93"),
}
PAINT = {"fill", "stroke", "stop-color", "color"}
ROLE_ATTRS = {"data-fill-role": "fill", "data-stroke-role": "stroke", "data-stop-role": "stop-color"}


def preset(name):
    return {"name": name, "colors": dict(zip(ROLES, PRESET_VALUES[name]))}


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def write_text(path, content, force=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w" if force else "x", encoding="utf-8") as stream:
        stream.write(content)


def write_json(path, value, force=False):
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2)+"\n", force)


def parse_svg(path):
    raw = Path(path).read_bytes()
    if len(raw) > 25_000_000:
        raise ValueError("SVG exceeds the 25 MB inspection limit")
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", raw, re.I):
        raise ValueError("DTD/entity declarations are not accepted")
    if re.search(br"<\?xml-stylesheet\b", raw, re.I):
        raise ValueError("XML stylesheet processing instructions are not accepted")
    root = ET.fromstring(raw)
    if root.tag != "{"+SVG+"}svg":
        raise ValueError("Expected an SVG root in the SVG namespace")
    return root


def numeric(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def inspect_svg(path):
    errors, warnings = [], []
    try:
        root = parse_svg(path)
    except (OSError, ET.ParseError, ValueError) as exc:
        return {"ok": False, "errors": [str(exc)], "warnings": [], "scientific_review": "not performed by this script"}
    try:
        view = [float(v) for v in re.split(r"[\s,]+", root.get("viewBox", "").strip())]
        if len(view) != 4 or not all(math.isfinite(v) for v in view) or view[2] <= 0 or view[3] <= 0:
            raise ValueError
    except ValueError:
        errors.append("viewBox must contain four finite numbers with positive width/height")
        view = None
    ids, references, groups, role_count = set(), [], 0, 0
    for node in root.iter():
        local = node.tag.split("}")[-1] if isinstance(node.tag, str) else ""
        if local.lower() in {"image", "script", "foreignobject", "iframe", "object", "embed", "animate", "animatetransform", "animatemotion", "animatecolor", "discard", "set"}:
            errors.append(f"Forbidden element for static native-vector assets: {local}")
        if local == "style":
            errors.append("Expand stylesheet rules to explicit SVG attributes before delivery")
        identifier = node.get("id")
        if identifier:
            if identifier in ids:
                errors.append(f"Duplicate ID: {identifier}")
            ids.add(identifier)
        if local == "g" and identifier:
            groups += 1
        if local == "use":
            warnings.append("Expand reusable instances if the user needs independent part editing")
        for key, value in node.attrib.items():
            key_local = key.split("}")[-1]
            if key_local.lower().startswith("on"):
                errors.append("Event handlers are not accepted")
            if key_local in {"href", "src"}:
                if value.startswith("#"):
                    references.append(value[1:])
                else:
                    errors.append("External or embedded href/src resource is not accepted")
            if "var(" in value.lower() or "@import" in value.lower() or "expression(" in value.lower():
                errors.append("Resolve CSS variables/imports/expressions before delivery")
            for match in re.findall(r"url\(\s*(['\"]?)(.*?)\1\s*\)", value, re.I):
                target = match[1].strip()
                if target.startswith("#"):
                    references.append(target[1:])
                else:
                    errors.append("External paint/filter resource is not accepted")
            if key in ROLE_ATTRS:
                role_count += 1
            if key_local == "style" and re.search(r"(?:^|;)\s*background(?:-color)?\s*:", value, re.I):
                errors.append("Remove CSS canvas backgrounds")
        if local == "rect" and view:
            vx, vy, vw, vh = view
            x, y = numeric(node.get("x", "0")), numeric(node.get("y", "0"))
            width = vw if node.get("width") == "100%" else numeric(node.get("width"))
            height = vh if node.get("height") == "100%" else numeric(node.get("height"))
            fill = node.get("fill", "black").lower()
            opacity = numeric(node.get("opacity", "1"))
            fill_opacity = numeric(node.get("fill-opacity", "1"))
            if None not in (x, y, width, height) and x <= vx and y <= vy and x+width >= vx+vw and y+height >= vy+vh and fill not in {"none", "transparent"} and opacity != 0 and fill_opacity != 0:
                errors.append("A filled rectangle covers the full canvas; remove the background")
    if not groups:
        errors.append("Provide at least one named editable group")
    unresolved = sorted(set(references)-ids)
    if unresolved:
        errors.append("Unresolved internal references: "+", ".join(unresolved))
    if not role_count:
        warnings.append("No palette-role tags; add them before using recolor")
    return {"ok": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings)), "named_groups": groups, "ids": len(ids), "palette_bindings": role_count, "native_vector_structure": not errors, "transparency": "requires actual PNG render check", "scientific_review": "not performed by this script"}


def load_palette(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    colors = value.get("colors")
    if not isinstance(colors, dict) or not colors:
        raise ValueError("Palette must contain a non-empty colors object")
    if any(not isinstance(v, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", v) for v in colors.values()):
        raise ValueError("Palette values must be explicit six-digit hex RGB colors")
    return colors


def geometry_digest(root):
    def record(node):
        return [node.tag, sorted((k, v) for k, v in node.attrib.items() if k not in PAINT), (node.text or "").strip(), [record(child) for child in node]]
    encoded = json.dumps(record(root), ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def recolor(source, palette, output, force=False):
    qa = inspect_svg(source)
    if not qa["ok"]:
        raise ValueError("Source SVG failed inspection: "+"; ".join(qa["errors"]))
    colors = load_palette(palette)
    root = parse_svg(source)
    before = geometry_digest(root)
    assignments = []
    for node in root.iter():
        for role_attr, paint_attr in ROLE_ATTRS.items():
            if node.get(role_attr):
                role = node.get(role_attr)
                if role not in colors:
                    raise ValueError(f"Palette has no value for role: {role}")
                if re.search(r"(?:^|;)\s*"+re.escape(paint_attr)+r"\s*:", node.get("style", "")):
                    raise ValueError(f"Inline style overrides {paint_attr}; expand it before recoloring")
                assignments.append((node, paint_attr, colors[role]))
    if not assignments:
        raise ValueError("Source has no palette-role bindings; annotate parts first")
    for node, attr, color in assignments:
        node.set(attr, color)
    if geometry_digest(root) != before:
        raise ValueError("Unexpected geometry change during recoloring")
    ET.indent(root, space="  ")
    write_text(output, ET.tostring(root, encoding="unicode", xml_declaration=False)+"\n", force)
    return {"ok": True, "updated_bindings": len(assignments), "geometry_preserved": True, "geometry_sha256": before}


def png_inspection(path):
    try:
        from PIL import Image
    except ImportError:
        return {"ok": False, "missing_evidence": "Install Pillow to inspect actual PNG alpha"}
    with Image.open(path) as image:
        if "A" not in image.getbands():
            return {"ok": False, "errors": ["PNG has no native alpha channel"]}
        alpha = image.getchannel("A")
        w, h = image.size
        corners = [alpha.getpixel(pos) for pos in ((0,0),(w-1,0),(0,h-1),(w-1,h-1))]
        edges = [alpha.crop(box).getextrema()[1] for box in ((0,0,w,1),(0,h-1,w,h),(0,0,1,h),(w-1,0,w,h))]
        box = alpha.getbbox()
        ok = box is not None and all(v == 0 for v in corners) and all(v == 0 for v in edges)
        return {"ok": ok, "mode": image.mode, "size": [w,h], "corner_alpha": corners, "edge_alpha_max": edges, "nonempty_foreground": box is not None, "content_bounds": list(box) if box else None, "errors": [] if ok else ["Foreground is empty, canvas is opaque, or artwork touches/clips a canvas edge; inspect the render"]}


def render(source, output, width=720, force=False, qa_path=None):
    qa = inspect_svg(source)
    if not qa["ok"]:
        raise ValueError("SVG failed inspection: "+"; ".join(qa["errors"]))
    output = Path(output)
    if not force and (output.exists() or (qa_path and Path(qa_path).exists())):
        raise FileExistsError("Output/QA already exists; choose a new version or use --force")
    output.parent.mkdir(parents=True, exist_ok=True)
    binary = shutil.which("rsvg-convert")
    if binary:
        subprocess.run([binary, "--width", str(width), "--output", str(output), str(source)], check=True, capture_output=True, timeout=45)
        renderer = "rsvg-convert"
    elif importlib.util.find_spec("cairosvg"):
        import cairosvg
        cairosvg.svg2png(url=str(source), write_to=str(output), output_width=width)
        renderer = "cairosvg"
    else:
        raise ValueError("No renderer available; install rsvg-convert or CairoSVG")
    raster = png_inspection(output)
    result = {"ok": qa["ok"] and raster["ok"], "renderer": renderer, "svg": qa, "png": raster, "image_generation": "not performed by the local renderer", "scientific_review": "agent/human inspection required"}
    if qa_path:
        write_json(qa_path, result, force)
    return result


def init_asset(args):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.slug):
        raise ValueError("Use a lowercase hyphenated asset slug")
    target = Path(args.outdir) if args.outdir else Path("figures/assets")/args.slug
    colors = preset(args.palette)
    brief = {"name": args.slug, "subject": args.subject, "use": "isolated asset for a scientific flowchart", "scientific_scope": "generic schematic unless the user supplied a more specific supported scope", "sources": [{"type":"user_brief", "description":args.subject}], "invariants": [], "allowed_simplifications": [], "editable_parts": [], "labels": [], "palette": args.palette, "route": "undecided", "image_generation": {"executed":False}, "status": "brief_only_not_artwork"}
    prompt = "\n".join(("Scientific illustration reference for ONE isolated research-flowchart asset.", "Subject: "+args.subject, "Style: clean original vector-like scientific illustration; restrained highlights; clear silhouette.", "Colors: "+", ".join(k+" "+v for k,v in colors["colors"].items()), "No text, watermark, logo, arrows, surrounding scene, or invented mechanisms unless specifically requested.", "Background: request native transparency only if the active image model supports it; otherwise use a plain white reference background. Final delivery will be rebuilt as transparent native SVG.", "This file is a prompt, not generated artwork. Preserve the supported structures in brief.json."))+"\n"
    outputs = {"brief.json": json.dumps(brief,ensure_ascii=False,indent=2)+"\n", "palette.json": json.dumps(colors,ensure_ascii=False,indent=2)+"\n", "image_prompt.txt": prompt}
    if any((target/name).exists() for name in outputs):
        raise FileExistsError("Asset brief already exists; use a new directory/version")
    for name, content in outputs.items():
        write_text(target/name, content)
    return {"ok":True, "directory":str(target), "created":list(outputs), "artwork_generated":False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init", help="Create a brief and palette; does not generate artwork")
    p.add_argument("slug"); p.add_argument("--subject", required=True); p.add_argument("--outdir")
    p.add_argument("--palette", choices=sorted(PRESET_VALUES), default="warm-gold")
    p = sub.add_parser("check", help="Inspect native SVG structure; not a scientific review")
    p.add_argument("svg"); p.add_argument("--output"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("render", help="Render a transparent PNG and inspect its alpha")
    p.add_argument("svg"); p.add_argument("--out", required=True); p.add_argument("--width", type=int, default=720)
    p.add_argument("--qa"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("recolor", help="Update tagged palette colors while preserving geometry")
    p.add_argument("svg"); p.add_argument("--palette", required=True); p.add_argument("--out", required=True)
    p.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "init": result = init_asset(args)
        elif args.command == "check":
            result = inspect_svg(args.svg)
            if args.output: write_json(args.output,result,args.force)
        elif args.command == "recolor": result = recolor(args.svg,args.palette,args.out,args.force)
        else:
            if args.width <= 0 or args.width > 8192: raise ValueError("width must be 1..8192")
            result = render(args.svg,args.out,args.width,args.force,args.qa)
        emit(result)
        return 0 if result["ok"] else 1
    except (ValueError, OSError, ET.ParseError, subprocess.SubprocessError) as exc:
        # Do not echo subprocess stdout/stderr: external helpers may contain account data.
        emit({"ok":False,"error":str(exc) if not isinstance(exc,subprocess.SubprocessError) else "Renderer failed; inspect the input and local renderer setup"})
        return 2


if __name__ == "__main__":
    sys.exit(main())
