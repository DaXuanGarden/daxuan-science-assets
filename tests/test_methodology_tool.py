"""Meaningful failure cases for methodology evidence and SVG handoff."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import methodology_tool as tool

EXAMPLE = Path(__file__).resolve().parents[1] / "assets/examples/methodology-demo"


class MethodologyTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((EXAMPLE / "diagram.json").read_text())

    def check(self, svg=None):
        return tool.check(self.plan, svg)

    def paper_claim(self, access="full_text", level="method_detail"):
        self.plan["sources"].append({"id": "paper-1", "kind": "paper", "access": access,
                                     "citation": "Synthetic test record; not a real citation"})
        support = {"status": "source_supported", "claim_level": level,
                   "evidence": [{"source_id": "paper-1", "locator": "Synthetic methods excerpt"}]}
        self.plan["nodes"][0]["support"] = support
        return support

    def test_proposed_fixture_and_native_labels_match(self):
        self.assertTrue(self.check(EXAMPLE / "asset.svg")["ok"])

    def test_missing_edge_endpoint(self):
        self.plan["edges"][0]["to"] = "absent"
        self.assertFalse(self.check()["ok"])

    def test_duplicate_node_and_shared_svg_group(self):
        self.plan["nodes"].append(copy.deepcopy(self.plan["nodes"][0]))
        self.assertFalse(self.check()["ok"])
        self.plan["nodes"].pop()
        self.plan["edges"][0]["svg_id"] = self.plan["nodes"][0]["svg_id"]
        self.assertFalse(self.check()["ok"])

    def test_unknown_source_and_missing_locator(self):
        support = self.paper_claim()
        support["evidence"][0]["source_id"] = "absent"
        self.assertFalse(self.check()["ok"])
        support["evidence"][0] = {"source_id": "paper-1"}
        self.assertFalse(self.check()["ok"])

    def test_identifier_does_not_verify_a_method(self):
        self.paper_claim("identifier_only")
        self.assertFalse(self.check()["ok"])

    def test_abstract_can_support_overview_but_not_method_details(self):
        support = self.paper_claim("abstract", "overview")
        result = self.check()
        self.assertTrue(result["ok"])
        self.assertTrue(result["warnings"])
        support["claim_level"] = "method_detail"
        self.assertFalse(self.check()["ok"])

    def test_inspected_excerpt_accepts_method_details(self):
        self.paper_claim("excerpt")
        self.assertTrue(self.check()["ok"])

    def test_user_prompt_does_not_verify_published_method(self):
        support = self.plan["nodes"][0]["support"]
        support["status"] = "source_supported"
        self.assertFalse(self.check()["ok"])
        support["status"] = "user_specified"
        self.assertTrue(self.check()["ok"])

    def test_adaptation_needs_source_and_change_note(self):
        support = self.paper_claim()
        support["status"] = "adapted"
        self.assertFalse(self.check()["ok"])
        support["note"] = "Proposed adjustment to the source method."
        self.assertTrue(self.check()["ok"])

    def test_draft_uncertainty_cannot_be_final(self):
        self.plan["nodes"][0]["support"]["status"] = "unresolved"
        self.assertFalse(self.check()["ok"])
        self.plan["status"] = "draft"
        self.plan["open_questions"] = ["Which assay is intended?"]
        self.assertTrue(self.check()["ok"])
        self.plan["status"] = "final"
        self.assertFalse(self.check()["ok"])

    def test_meaningful_relation_requires_support(self):
        edge = self.plan["edges"][0]
        edge["relation"] = "activation"
        edge["support"] = {"status": "source_supported", "claim_level": "method_detail", "evidence": []}
        self.assertFalse(self.check()["ok"])

    def test_svg_endpoint_type_and_label_mismatches(self):
        raw = (EXAMPLE / "asset.svg").read_text()
        mutations = [raw.replace('data-to="assay"', 'data-to="compare"', 1),
                     raw.replace('data-relation="dataflow"', 'data-relation="causal"', 1),
                     raw.replace('>Sample</text>', '>Patient</text>', 1),
                     raw.replace('id="node-assay"', 'id="missing-assay"', 1),
                     raw.replace('data-node-id="sample"', 'data-node-id="unplanned"', 1)]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "asset.svg"
            for changed in mutations:
                with self.subTest(mutation=changed[:40]):
                    target.write_text(changed)
                    self.assertFalse(self.check(target)["ok"])

    def test_invalid_width_and_empty_plan(self):
        for invalid in (0, -1, float("nan"), True, "180"):
            self.plan["target_width_mm"] = invalid
            self.assertFalse(self.check()["ok"])
        self.assertFalse(tool.check({})["ok"])
        self.assertFalse(tool.check([])["ok"])

    def test_malformed_field_types_fail_without_traceback(self):
        self.plan["diagram_kind"] = []
        self.plan["sources"][0]["access"] = []
        self.plan["nodes"][0]["support"]["status"] = []
        self.plan["nodes"][0]["support"]["evidence"][0]["source_id"] = []
        self.plan["nodes"][0]["svg_id"] = []
        self.plan["edges"][0]["from"] = []
        self.assertFalse(self.check(EXAMPLE / "asset.svg")["ok"])


if __name__ == "__main__":
    unittest.main()
