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
    "fresh-academic": ("#A9C7CB", "#DCEBED", "#7F9FA5", "#47636F", "#73939B", "#F1F7F7", "#E4867F", "#B3C4C9", "#F7FAFA", "#8DA2AA"),
    "editorial-pastel": ("#9BC4C1", "#DDEFEA", "#73989A", "#3F5963", "#6F8D91", "#F8FBF8", "#E98E7E", "#B9C8C7", "#FBFCF9", "#8FA6A8"),
}
COMPOSITION_MODES = ("scene_centered", "icon_composite", "process_chain")
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
    colors = preset(getattr(args, "palette", "warm-gold"))
    mode = getattr(args, "mode", "native_svg")
    route = {"native_svg": "native-svg", "raster_generation": "image-backend", "hybrid": "image-backend-plus-native-svg"}[mode]
    composition_mode = getattr(args, "composition_mode", "scene_centered")
    if composition_mode not in COMPOSITION_MODES:
        raise ValueError("composition_mode must be one of: "+", ".join(COMPOSITION_MODES))
    use = "generated raster asset for a scientific figure" if mode == "raster_generation" else "scientific asset with an explicit composition contract"
    background = getattr(args, "background", "auto")
    iteration_mode = getattr(args, "iteration_mode", "explore")
    if iteration_mode not in {"explore", "refine"}:
        raise ValueError("iteration_mode must be explore or refine")
    aesthetic_review_required = bool(getattr(args, "aesthetic_review", False) or iteration_mode == "refine")
    candidate_count = getattr(args, "candidate_count", None)
    if candidate_count is None:
        candidate_count = 1 if iteration_mode == "refine" else 2
    count_min, count_max = (1, 2) if iteration_mode == "refine" else (2, 10)
    if isinstance(candidate_count, bool) or not isinstance(candidate_count, int) or not count_min <= candidate_count <= count_max:
        raise ValueError(f"candidate_count must be an integer from {count_min} to {count_max} in {iteration_mode} mode")
    base_asset = getattr(args, "base_asset", None)
    edit_targets = getattr(args, "edit_target", None) or []
    preserve_features = getattr(args, "preserve_feature", None) or []
    refinement_contract = None
    if iteration_mode == "refine":
        if not base_asset or not edit_targets or not preserve_features:
            raise ValueError("refine needs --base-asset, at least one --edit-target, and at least one --preserve-feature")
        base = Path(base_asset).resolve()
        if not base.is_file():
            raise ValueError("base_asset must name an existing selected asset")
        if any(not isinstance(item, str) or not item.strip() for item in edit_targets + preserve_features):
            raise ValueError("Edit targets and preserved features must be non-empty descriptions")
        refinement_contract = {"base_asset": {"path": str(base), "sha256": hashlib.sha256(base.read_bytes()).hexdigest()}, "edit_targets": edit_targets, "preserve_features": preserve_features}
    elif base_asset or edit_targets or preserve_features:
        raise ValueError("Selected-base edit arguments require --iteration-mode refine")
    action = getattr(args, "action", None)
    attention_target = getattr(args, "attention_target", None)
    required_context = getattr(args, "required_context", None) or []
    if (attention_target or required_context) and not action:
        raise ValueError("An attention target or required context needs an explicit action")
    action_contract = {"action": action, "attention_target": attention_target, "required_context": required_context} if action else None
    brief = {"name": args.slug, "subject": args.subject, "use": use, "scientific_scope": "generic schematic unless the user supplied a more specific supported scope", "sources": [{"type":"user_brief", "description":args.subject}], "invariants": [], "allowed_simplifications": [], "editable_parts": [], "labels": [], "palette": getattr(args, "palette", "warm-gold"), "delivery_mode": mode, "background": background, "route": route, "composition_mode": composition_mode, "storyboard": {"visual_anchor": "single main subject", "environment": "minimal context that explains the subject", "state_cue": "one visible state or symptom cue", "integrated_secondary_cue": "one compact cue embedded in the scene", "relation_semantics": "conceptual association unless the brief explicitly supports causality", "avoid_list": ["isolated object chain", "detached icon satellites", "unlisted mechanism", "unlisted text"]}, "action_contract": action_contract, "aesthetic_review_required": aesthetic_review_required, "aesthetic_spec": {"candidate_count": candidate_count, "revision_round_limit": 1, "criteria": ["visual_hierarchy", "silhouette_readability", "palette_harmony", "composition_balance", "style_coherence", "detail_economy", "destination_slot_readability"], "science_boundary": "Aesthetic scores describe visual finish only; they do not certify scientific truth."}, "image_generation": {"executed":False, "requested": mode in {"raster_generation", "hybrid"}}, "status": "brief_only_not_artwork"}
    brief["iteration_mode"] = iteration_mode
    brief["refinement_contract"] = refinement_contract
    if mode == "raster_generation":
        style = "clean original scientific raster illustration; restrained highlights; clear silhouette; coherent art direction suited to the user and destination; natural proportions and intentional color contrast; preserve the requested composition without adding text"
        ending = "Final delivery is the generated PNG/JPEG. Do not reconstruct it as SVG unless the user separately requests a vector branch."
    elif mode == "hybrid":
        style = "clean original scientific illustration suitable for later native SVG reconstruction; restrained highlights; clear silhouette; coherent art direction suited to the user and destination"
        ending = "The generated PNG is a visual asset and may be accompanied by a separately authored editable SVG."
    else:
        style = "clean original vector-like scientific illustration; restrained highlights; clear silhouette; coherent art direction suited to the user and destination"
        ending = "Final delivery for this mode is a transparent native SVG with a rendered PNG companion."
    composition_instruction = {
        "scene_centered": "Build one coherent compact scene around a single visual anchor. Put the environment and state cue in the same scene; embed the secondary scientific cue into the subject or setting. Do not arrange detached icons as a chain.",
        "icon_composite": "Use a compact composite of a few explicitly requested objects, with clear grouping and no unlisted satellites.",
        "process_chain": "Use a deliberate process chain only when the brief explicitly requests ordered steps and relations."
    }[composition_mode]
    aesthetic_instruction = "Aesthetic goals: graceful composition, natural subject proportions, coherent rendering, harmonious colors with useful contrast, an appealing silhouette, and recognition at thumbnail size. This prompt requests ONE image. Candidate comparison and scientific review occur outside the image model." if aesthetic_review_required else "Aesthetic review is optional; preserve a coherent visual hierarchy and inspect the asset at the destination size."
    action_instruction = "Required behavior: "+json.dumps(action_contract, ensure_ascii=False)+". Preserve the action, attention target, and necessary context in this image; do not simplify away the behavior." if action_contract else "No additional behavior contract is specified."
    prompt = "\n".join(("Scientific illustration asset request with composition mode: "+composition_mode+".", "Subject: "+args.subject, "Style: "+style+".", "Composition contract: "+composition_instruction, "Storyboard fields: visual_anchor=single main subject; environment=minimal explanatory context; state_cue=one visible state or symptom cue; integrated_secondary_cue=one compact cue embedded in the scene; relation_semantics=conceptual association unless explicitly supported.", action_instruction, aesthetic_instruction, "Colors: "+", ".join(k+" "+v for k,v in colors["colors"].items()), "No watermark, logo, invented mechanisms, unsupported anatomy, genes, loci, numerical claims, or extra text/arrows unless specifically requested.", "Background request: "+background+"; use true alpha when supported and never draw a checkerboard to imitate transparency.", ending, "This file is a prompt. Preserve the supported structures, aesthetic contract, and evidence boundaries in brief.json."))+"\n"
    if refinement_contract:
        prompt += "Iteration mode: refine the supplied selected-base image; do not restart composition or replace the subject. Send that image as an edit reference through the existing backend. Additional references may guide specified detail or finish only.\n"
        prompt += "Preserve: "+json.dumps(preserve_features, ensure_ascii=False)+".\n"
        prompt += "Observable edit targets: "+json.dumps(edit_targets, ensure_ascii=False)+".\n"
        prompt += "Request ONE refined image. Compare its changed details directly with the selected base; a near-identical redraw does not prove that the requested edits improved.\n"
    else:
        prompt += "Iteration mode: explore. Candidate diversity is reviewed outside this one-image request; mirrored views, demographic swaps, or small recolors alone are not new design directions.\n"
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
    p.add_argument("--mode", choices=("native_svg", "raster_generation", "hybrid"), default="native_svg")
    p.add_argument("--composition-mode", choices=COMPOSITION_MODES, default="scene_centered")
    p.add_argument("--aesthetic-review", action="store_true", help="Require an attributed visual review sidecar and candidate comparison")
    p.add_argument("--iteration-mode", choices=("explore", "refine"), default="explore", help="Explore designs or refine one selected base")
    p.add_argument("--candidate-count", type=int, choices=range(1, 11), help="Explore: 2–10 (default 2); refine: 1–2 (default 1); does not execute requests")
    p.add_argument("--base-asset", help="Existing selected image/vector for refine mode; its hash is recorded")
    p.add_argument("--edit-target", action="append", default=[], help="Observable detail to improve in refine mode; repeat as needed")
    p.add_argument("--preserve-feature", action="append", default=[], help="Approved feature to retain in refine mode; repeat as needed")
    p.add_argument("--action", help="Behavior that must remain visible in every candidate")
    p.add_argument("--attention-target", help="Where the subject must look or direct attention")
    p.add_argument("--required-context", action="append", default=[], help="Necessary contextual object or setting; repeat as needed")
    p.add_argument("--background", choices=("opaque", "transparent", "auto"), default="auto")
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
