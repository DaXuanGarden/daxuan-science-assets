"""Source integrity, transparent native builds, and honest layout failure behavior."""

import copy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import asset_tool
import methodology_render as renderer
import methodology_tool as tool

EXAMPLES = Path(__file__).resolve().parents[1] / "assets/examples"
PAPER = EXAMPLES / "deseq2-method"
NS = "{" + asset_tool.SVG + "}"


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((EXAMPLES / "methodology-demo/diagram.json").read_text())
        self.plan["layout"] = {"columns": [["sample", "control"], ["assay"], ["compare"], ["readout"]]}
        self.colors = asset_tool.load_palette(EXAMPLES / "methodology-demo/palette.json")
        self.paper = json.loads((PAPER / "diagram.json").read_text())

    def svg(self):
        return renderer.svg_document(self.plan, self.colors)[0]

    def test_build_produces_matching_native_labels_and_actual_alpha(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "diagram.json"
            plan.write_text(json.dumps(self.plan))
            out = root / "output"
            result = renderer.build_diagram(plan, EXAMPLES / "methodology-demo/palette.json", out, width=1100)
            self.assertTrue(result["ok"])
            self.assertTrue(tool.check(self.plan, out / "asset.svg")["ok"])
            self.assertTrue(asset_tool.png_inspection(out / "asset.png")["ok"])
            self.assertFalse(result["image_generation_executed"])
            self.assertTrue(all((out / f).is_file() for f in result["files"]))

    def test_real_paper_excerpts_are_locally_verified(self):
        result = tool.check(self.paper, sources_dir=PAPER)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["source_snapshots"]["checked_claims"]), 20)

    def test_fabricated_excerpt_or_locator_fails(self):
        for field in ("excerpt", "locator"):
            plan = copy.deepcopy(self.paper)
            plan["nodes"][0]["support"]["evidence"][0][field] = "Invented material absent from this source"
            self.assertFalse(tool.check(plan, sources_dir=PAPER)["ok"])

    def test_changed_snapshot_fails_hash_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "sources/deseq2-methods.txt"
            path.parent.mkdir()
            path.write_text((PAPER / "sources/deseq2-methods.txt").read_text() + "Changed.")
            self.assertFalse(tool.check(self.paper, sources_dir=root)["ok"])

    def test_snapshot_cannot_escape_selected_directory(self):
        for unsafe in ("../outside.txt", "/tmp/outside.txt", "source.xml"):
            plan = copy.deepcopy(self.paper)
            plan["sources"][0]["snapshot"] = unsafe
            self.assertFalse(tool.check(plan, sources_dir=PAPER)["ok"])

    def test_hash_does_not_substitute_for_missing_snapshot(self):
        self.paper["sources"][0].pop("snapshot")
        self.assertFalse(tool.check(self.paper, sources_dir=PAPER)["ok"])

    def test_snapshot_checks_remain_explicit(self):
        result = tool.check(self.paper)
        self.assertTrue(result["ok"])
        self.assertIsNone(result["source_snapshots"])
        self.assertTrue(result["warnings"])

    def test_content_budget_is_enforced(self):
        self.plan["content_budget"]["max_nodes"] = 4
        self.assertFalse(tool.check(self.plan)["ok"])
        self.plan["content_budget"]["max_nodes"] = 5
        self.plan["content_budget"]["max_label_words"] = 1
        self.assertFalse(tool.check(self.plan)["ok"])

    def test_duplicate_semantic_binding_fails_even_with_distinct_svg_ids(self):
        svg = ET.fromstring(self.svg())
        group = next(n for n in svg.iter() if n.get("data-node-id") == "sample")
        extra = copy.deepcopy(group)
        extra.set("id", "extra-sample")
        svg.append(extra)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "asset.svg"
            path.write_text(ET.tostring(svg, encoding="unicode"))
            self.assertFalse(tool.check(self.plan, path)["ok"])

    def test_all_relation_symbols_have_distinct_semantics(self):
        for relation in sorted(tool.RELATIONS):
            self.plan["edges"][0]["relation"] = relation
            root = ET.fromstring(self.svg())
            group = next(n for n in root.iter() if n.get("data-edge-id") == "sample-assay")
            symbols = [n.get("data-symbol") for n in group if n.get("data-symbol")]
            self.assertEqual(symbols, ["bar"] if relation == "inhibition" else [] if relation in {"association", "uncertainty"} else ["arrow"])
            dashed = any(n.get("stroke-dasharray") for n in group)
            self.assertEqual(dashed, relation == "uncertainty")

    def test_wrapping_preserves_english_and_unspaced_label_text(self):
        for value in ("Compare sample signals", chr(0x7EC6) + chr(0x80DE) + chr(0x8F93) + chr(0x5165)):
            self.assertEqual("".join(renderer.wrap(value, 180, 30)), value)

    def test_overlong_token_and_small_print_do_not_silently_shrink(self):
        with self.assertRaises(ValueError):
            renderer.wrap("X" * 50, 200, 32)
        self.plan["target_width_mm"] = 40
        with self.assertRaises(ValueError):
            self.svg()

    def test_skipped_columns_need_an_explicit_route(self):
        self.plan["edges"][0]["to"] = "compare"
        with self.assertRaises(ValueError):
            self.svg()
        self.plan["edges"][0]["route"] = "above"
        self.assertIn('data-edge-id="sample-assay"', self.svg())

    def test_rail_crossing_another_node_is_rejected(self):
        self.plan["edges"][1]["to"] = "compare"
        self.plan["edges"][1]["route"] = "above"
        with self.assertRaises(ValueError):
            self.svg()

    def test_layout_must_include_every_node_exactly_once(self):
        for columns in ([["sample"]], [["sample", "sample"], ["assay", "compare", "readout"]]):
            self.plan["layout"]["columns"] = columns
            with self.assertRaises(ValueError):
                self.svg()

    def test_malformed_layout_and_edge_labels_fail_cleanly(self):
        self.plan["layout"] = []
        with self.assertRaises(ValueError):
            self.svg()
        self.plan["edges"][0]["label"] = {"unexpected": "object"}
        self.assertFalse(tool.check(self.plan)["ok"])

    def test_converging_edges_have_separate_target_ports(self):
        root = ET.fromstring(self.svg())
        groups = [n for n in root.iter() if n.get("data-edge-id") in {"sample-assay", "control-assay"}]
        endpoints = [re.findall(r"[-\d.]+", g.find(NS + "path").get("d"))[-2:] for g in groups]
        self.assertEqual(len(groups), 2)
        self.assertNotEqual(endpoints[0], endpoints[1])

    def test_build_refuses_overwrite_and_cleans_failed_staging(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "diagram.json"
            plan.write_text(json.dumps(self.plan))
            existing = root / "existing"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                renderer.build_diagram(plan, EXAMPLES / "methodology-demo/palette.json", existing)
            with patch.object(asset_tool, "render", side_effect=ValueError("Renderer unavailable")):
                with self.assertRaises(ValueError):
                    renderer.build_diagram(plan, EXAMPLES / "methodology-demo/palette.json", root / "failed")
            self.assertFalse((root / "failed").exists())
            self.assertFalse(list(root.glob(".daxuan-method-build-*")))

    def test_paper_build_cannot_skip_recorded_excerpt_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                renderer.build_diagram(PAPER / "diagram.json", PAPER / "palette.json", Path(directory) / "output")


if __name__ == "__main__":
    unittest.main()
