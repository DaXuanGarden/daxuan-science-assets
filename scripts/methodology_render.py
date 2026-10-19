"""Build a bounded native methodology skeleton; scientific planning stays with the agent."""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import shutil
import tempfile
import unicodedata
import xml.etree.ElementTree as ET

import asset_tool
import methodology_tool

NS = "{" + asset_tool.SVG + "}"
ET.register_namespace("", asset_tool.SVG)


def wrap(text, width, font_size):
    """Conservative wrapping, including scripts without spaces; no silent truncation."""
    def measure(value):
        return sum(1.0 if unicodedata.east_asian_width(c) in {"W", "F"} else
                   0.38 if c.isspace() or c in "il.,:;!'|" else
                   0.9 if c in "MW@%" else 0.82 if c in "mw" else
                   0.68 if c.isupper() else 0.56 for c in value) * font_size
    lines, line = [], ""
    for character in text.strip():
        if character == "\n":
            lines.append(line + "\n")
            line = ""
            continue
        candidate = line + character
        if measure(candidate) > width and line:
            if character.isspace():
                lines.append(line + character)
                line = ""
            elif " " in line:
                before, after = line.rsplit(" ", 1)
                lines.append(before + " ")
                line = after + character
            elif any(unicodedata.east_asian_width(c) in {"W", "F"} for c in line + character):
                lines.append(line)
                line = character
            else:
                raise ValueError("A label token is too wide for this base layout; shorten it explicitly or author a custom SVG")
        else:
            line = candidate.lstrip()
    if line:
        lines.append(line)
    return lines or [""]


def svg_document(plan, colors):
    """Use declared columns and routes. Unsupported layouts fail rather than omit edges."""
    layout = plan.get("layout", {})
    if not isinstance(layout, dict):
        raise ValueError("layout must be an object with explicit columns")
    columns = layout.get("columns")
    if not isinstance(columns, list) or not columns or any(not isinstance(c, list) or not c for c in columns):
        raise ValueError("Build needs nonempty layout.columns; author a custom SVG for other layouts")
    flat = [identifier for column in columns for identifier in column]
    if any(not isinstance(i, str) for i in flat) or Counter(flat) != Counter(n["id"] for n in plan["nodes"]):
        raise ValueError("layout.columns must place every planned node exactly once")
    required = {"field", "body", "outline", "guide", "text"}
    if not required.issubset(colors):
        raise ValueError("Build palette needs field, body, outline, guide, and text roles")
    nodes = {node["id"]: node for node in plan["nodes"]}
    cw, ch, gap, row_gap, margin = 260, 200, 100, 70, 44
    width = 2 * margin + len(columns) * cw + (len(columns) - 1) * gap
    upper = sum(e.get("route") == "above" for e in plan["edges"])
    lower = sum(e.get("route") == "below" for e in plan["edges"])
    grid_top = 174 + 34 * upper
    grid_height = max(len(c) for c in columns) * (ch + row_gap) - row_gap
    positions = {}
    for col, identifiers in enumerate(columns):
        column_height = len(identifiers) * (ch + row_gap) - row_gap
        offset = (grid_height - column_height) / 2
        for row, identifier in enumerate(identifiers):
            positions[identifier] = (margin + col * (cw + gap), grid_top + offset + row * (ch + row_gap), col, row)
    caption = plan.get("caption", "")
    if not isinstance(caption, str):
        raise ValueError("caption must be text")
    footer = wrap(caption, width - 2 * margin, 30) if caption else []
    height = grid_top + grid_height + 60 + 34 * lower + 40 * len(footer)
    min_pt = 30 / width * plan["target_width_mm"] / 25.4 * 72
    minimum = plan.get("content_budget", {}).get("min_font_pt", 8)
    if isinstance(minimum, bool) or not isinstance(minimum, (int, float)) or not math.isfinite(minimum) or minimum <= 0:
        raise ValueError("min_font_pt must be finite and positive")
    if min_pt < minimum:
        raise ValueError("Labels would be smaller than min_font_pt at the target width; change layout or figure size explicitly")
    root = ET.Element(NS + "svg", {"viewBox": f"0 0 {width} {height}",
                                  "width": f"{plan['target_width_mm']}mm",
                                  "height": f"{height / width * plan['target_width_mm']:.3f}mm",
                                  "data-generator": "daxuan-methodology-build"})
    ET.SubElement(root, NS + "title").text = plan["title"]
    ET.SubElement(root, NS + "desc").text = plan["scope"] + " " + plan["provenance_summary"]

    def element(parent, tag, attrs=None, **kwargs):
        values = {key.replace("_", "-"): str(value) for key, value in kwargs.items()}
        values.update(attrs or {})
        return ET.SubElement(parent, NS + tag, values)

    def paint(role, attr="fill"):
        return {attr: colors[role], "data-" + attr + "-role": role}

    def label(parent, value, x, y, size=32, anchor="middle", weight="500"):
        text = element(parent, "text", paint("text"), x=x, y=y, font_size=size,
                       text_anchor=anchor, font_weight=weight, font_family="Arial, Helvetica, sans-serif")
        text.text = value
        return text

    heading = element(root, "g", id="method-heading")
    title_lines = wrap(plan["title"], width - 2 * margin, 42)
    if len(title_lines) > 1:
        raise ValueError("Title is too long for this base layout; shorten it or author a custom SVG")
    label(heading, plan["title"], margin, 64, 42, "start", "700")
    if plan["status"] == "draft":
        label(heading, "DRAFT — unresolved details", margin, 114, 30, "start")
    elif any(item["support"]["status"] in {"proposed", "adapted", "user_specified"} for item in plan["nodes"] + plan["edges"]):
        label(heading, "Includes proposed, adapted, or user-specified content", margin, 114, 30, "start")

    relations = element(root, "g", id="method-relations")
    direct = [e for e in plan["edges"] if e.get("route", "direct") == "direct"
              and positions[e["to"]][2] == positions[e["from"]][2] + 1]

    def port(edge, outgoing):
        key, other = ("from", "to") if outgoing else ("to", "from")
        peers = sorted((e for e in direct if e[key] == edge[key]),
                       key=lambda e: (positions[e[other]][1], e["id"]))
        # Separate incoming and outgoing arrows instead of drawing shared junctions.
        return (peers.index(edge) - (len(peers) - 1) / 2) * min(36, (ch - 70) / max(1, len(peers)))

    lanes = {"above": 0, "below": 0}
    for edge in plan["edges"]:
        sx, sy, sc, sr = positions[edge["from"]]
        tx, ty, tc, tr = positions[edge["to"]]
        route = edge.get("route", "direct")
        if edge["from"] == edge["to"]:
            raise ValueError("Self loops need an authored SVG")
        if route in lanes:
            lane = lanes[route]
            lanes[route] += 1
            if route == "above":
                if sr != 0 or tr != 0:
                    raise ValueError(edge["id"] + ": above route would cross a node; use a custom SVG or revise the declared layout")
                rail = grid_top - 35 - lane * 34
                points = [(sx + cw / 2, sy - 3), (sx + cw / 2, rail), (tx + cw / 2, rail), (tx + cw / 2, ty - 10)]
            else:
                if sr != len(columns[sc]) - 1 or tr != len(columns[tc]) - 1:
                    raise ValueError(edge["id"] + ": below route would cross a node; use a custom SVG or revise the declared layout")
                rail = grid_top + grid_height + 35 + lane * 34
                points = [(sx + cw / 2, sy + ch + 3), (sx + cw / 2, rail), (tx + cw / 2, rail), (tx + cw / 2, ty + ch + 10)]
        elif route == "direct" and tc == sc + 1:
            mid = (sx + cw + tx) / 2
            start_y, end_y = sy + ch / 2 + port(edge, True), ty + ch / 2 + port(edge, False)
            points = [(sx + cw + 3, start_y), (mid, start_y), (mid, end_y), (tx - 10, end_y)]
        elif route == "direct" and tc == sc and tr == sr + 1:
            points = [(sx + cw / 2, sy + ch + 3), (tx + cw / 2, ty - 10)]
        else:
            raise ValueError(edge["id"] + ": use an explicit above/below route for skips or feedback, or author a custom SVG")
        group = element(relations, "g", {"id": edge["svg_id"], "data-edge-id": edge["id"],
                        "data-from": edge["from"], "data-to": edge["to"], "data-relation": edge["relation"]})
        path_attrs = {"fill": "none", **paint("guide", "stroke")}
        if edge["relation"] == "uncertainty":
            path_attrs["stroke-dasharray"] = "9 7"
        path = "M " + " L ".join(f"{x:g} {y:g}" for x, y in points)
        element(group, "path", path_attrs, d=path, stroke_width=3.5, stroke_linejoin="round", stroke_linecap="round")
        end, previous = points[-1], next(p for p in reversed(points[:-1]) if p != points[-1])
        dx, dy = end[0] - previous[0], end[1] - previous[1]
        length = math.hypot(dx, dy)
        ux, uy, nx, ny = dx / length, dy / length, -dy / length, dx / length
        relation = edge["relation"]
        if relation == "inhibition":
            d = f"M {end[0]+nx*11:g} {end[1]+ny*11:g} L {end[0]-nx*11:g} {end[1]-ny*11:g}"
            element(group, "path", {"fill": "none", **paint("guide", "stroke"), "data-symbol": "bar"}, d=d, stroke_width=4)
        elif relation not in {"association", "uncertainty"}:
            p1 = (end[0] - ux * 13 + nx * 8, end[1] - uy * 13 + ny * 8)
            p2 = (end[0] - ux * 13 - nx * 8, end[1] - uy * 13 - ny * 8)
            d = f"M {p1[0]:g} {p1[1]:g} L {end[0]:g} {end[1]:g} L {p2[0]:g} {p2[1]:g}"
            element(group, "path", {"fill": "none", **paint("guide", "stroke"), "data-symbol": "arrow"}, d=d, stroke_width=3.5, stroke_linecap="round")
        if edge.get("label"):
            if len(wrap(edge["label"], gap - 12 if route == "direct" else width - 2 * margin, 30)) > 1:
                raise ValueError(edge["id"] + ": edge label needs a custom layout or a concise caption legend")
            middle = points[len(points) // 2]
            label(group, edge["label"], middle[0], middle[1] - 14, 30)

    parts = element(root, "g", id="method-nodes")
    for index, node in enumerate(plan["nodes"], 1):
        x, y, col, row = positions[node["id"]]
        group = element(parts, "g", {"id": node["svg_id"], "data-node-id": node["id"]})
        element(group, "rect", {**paint("field"), **paint("outline", "stroke")}, x=x, y=y, width=cw, height=ch, rx=18, stroke_width=2)
        element(group, "rect", paint("body"), x=x + 18, y=y + 18, width=42, height=7, rx=3)
        lines = wrap(node["label"], cw - 40, 32)
        status = node["support"]["status"]
        max_lines = 2 if status != "source_supported" else 3
        if len(lines) > max_lines:
            raise ValueError(node["id"] + ": label does not fit without shrinking; shorten it explicitly or author a custom SVG")
        text = label(group, "", x + cw / 2, y + ch / 2 - (len(lines) - 1) * 20 + (0 if status == "source_supported" else -12), 32, weight="600")
        for line_index, line in enumerate(lines):
            span = element(text, "tspan", x=x + cw / 2, dy=0 if line_index == 0 else 40)
            span.text = line
        if status != "source_supported":
            label(group, status.replace("_", " ").capitalize(), x + cw / 2, y + ch - 24, 30)
    if footer:
        caption_group = element(root, "g", id="method-caption")
        for line_index, line in enumerate(footer):
            label(caption_group, line, margin, grid_top + grid_height + 50 + 34 * lower + 40 * line_index, 30, "start")
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode") + "\n", {"viewbox": [width, height], "minimum_label_pt": round(min_pt, 2), "layout": "explicit columns; inspect connector overlaps visually"}


def build_diagram(plan_path, palette_path, outdir, sources_dir=None, width=1600):
    if not isinstance(width, int) or isinstance(width, bool) or not 1 <= width <= 8192:
        raise ValueError("width must be 1..8192")
    plan_path, outdir = Path(plan_path), Path(outdir)
    if outdir.exists():
        raise FileExistsError("Output directory exists; choose a new version")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    preflight = methodology_tool.check(plan, sources_dir=sources_dir)
    if not preflight["ok"]:
        raise ValueError("Plan failed: " + "; ".join(preflight["errors"]))
    published = any(item["support"]["status"] in {"source_supported", "adapted"}
                    for item in plan["nodes"] + plan["edges"])
    if (published or any(s.get("snapshot") for s in plan["sources"])) and sources_dir is None:
        raise ValueError("Supply --sources-dir to verify source extracts before building published-method claims")
    palette = asset_tool.load_palette(palette_path)
    svg, layout_qa = svg_document(plan, palette)
    outdir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".daxuan-method-build-", dir=str(outdir.parent)) as directory:
        stage = Path(directory) / "asset"
        stage.mkdir()
        asset_tool.write_text(stage / "asset.svg", svg)
        asset_tool.write_json(stage / "diagram.json", plan)
        shutil.copyfile(palette_path, stage / "palette.json")
        if sources_dir is not None:
            for source in plan["sources"]:
                if source.get("snapshot"):
                    target = stage / source["snapshot"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(Path(sources_dir) / source["snapshot"], target)
        semantic = methodology_tool.check(plan, stage / "asset.svg", stage if sources_dir is not None else None)
        if not semantic["ok"]:
            raise ValueError("SVG semantic check failed: " + "; ".join(semantic["errors"]))
        raster = asset_tool.render(stage / "asset.svg", stage / "asset.png", width=width)
        if not raster["ok"]:
            raise ValueError("PNG transparency check failed")
        qa = {**raster, "methodology": semantic, "layout": layout_qa}
        asset_tool.write_json(stage / "qa.json", qa)
        asset_tool.write_json(stage / "brief.json", {"mode": "methodology", "subject": plan["title"], "scope": plan["scope"],
                              "target_width_mm": plan["target_width_mm"], "content_budget": plan["content_budget"],
                              "sources": plan["sources"], "route": "native-base-layout", "image_generation": {"executed": False}})
        stage.rename(outdir)
    return {"ok": True, "directory": str(outdir), "files": sorted(str(p.relative_to(outdir)) for p in outdir.rglob("*") if p.is_file()),
            "image_generation_executed": False, "qa": qa}
