"""Keep the figure-slot plan explicit and reviewable."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FigureSlotIntegrationTests(unittest.TestCase):
    def test_plan_template_uses_one_coordinate_system_and_starts_unreviewed(self):
        plan = json.loads((ROOT / "assets/templates/figure-slot-plan.json").read_text())
        self.assertEqual(plan["schema_version"], "1.0")
        self.assertEqual(plan["coordinate_system"], "figure_normalized_0_1")
        self.assertEqual(len(plan["target_figure"]["physical_size_mm"]), 2)
        self.assertEqual(len(plan["target_figure"]["slot_xywh"]), 4)
        route = plan["route_record_template"]
        self.assertEqual(route["path"]["type"], "cubic_bezier")
        self.assertEqual(len(route["path"]["figure_xy"]), 4)
        self.assertEqual(route["layer"], "above_asset")
        self.assertEqual(plan["routes"], [])
        self.assertFalse(plan["review"]["reviewed_at_final_size"])

    def test_entrypoint_routes_composites_to_the_integration_contract(self):
        skill = (ROOT / "SKILL.md").read_text()
        self.assertIn("figure-slot-integration.md", skill)
        self.assertIn("image-model generation or edit", skill)
        self.assertIn("do not substitute an authored SVG for the requested image-model output", skill)
        self.assertIn("An illustration derivative accompanies, and never replaces, its generated raster original", skill)
        self.assertIn("fully assembled figure", skill)

    def test_guide_separates_relation_meaning_from_route_geometry(self):
        guide = (ROOT / "references/figure-slot-integration.md").read_text()
        self.assertIn("Keep scientific meaning in `relation_manifest.json`", guide)
        self.assertIn("the slot plan records coordinates and rendering order", guide)
        self.assertIn("Render the complete composition", guide)
        self.assertIn("Do not disguise prohibited content", guide)


if __name__ == "__main__":
    unittest.main()
