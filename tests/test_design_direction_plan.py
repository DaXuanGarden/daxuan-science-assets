"""Exercise art-direction planning without issuing image-generation requests."""

from argparse import Namespace
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("direction_asset_tool", ROOT / "scripts/asset_tool.py")
asset_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(asset_tool)
EXAMPLE_PLAN = ROOT / "assets/examples/aesthetic-directions/direction-plan.json"


class DesignDirectionPlanTests(unittest.TestCase):
    def args(self, output, **changes):
        fields = dict(
            slug="desk-asset",
            subject="One adult seated at a desk and looking at a monitor",
            outdir=str(output),
            palette="editorial-pastel",
            mode="raster_generation",
            background="transparent",
            aesthetic_review=True,
            iteration_mode="explore",
            candidate_count=3,
        )
        fields.update(changes)
        return Namespace(**fields)

    def test_aesthetic_raster_exploration_requires_a_direction_card(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "missing-plan"
            with self.assertRaisesRegex(ValueError, "requires --direction-plan"):
                asset_tool.init_asset(self.args(output))
            self.assertFalse(output.exists())

    def test_each_candidate_gets_its_own_prompt_and_recorded_card(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompts = []
            for direction_id in ("side-gouache", "oblique-pencil"):
                output = root / direction_id
                result = asset_tool.init_asset(self.args(
                    output,
                    direction_plan=str(EXAMPLE_PLAN),
                    candidate_id=direction_id,
                    candidate_count=None,
                ))
                brief = json.loads((output / "brief.json").read_text(encoding="utf-8"))
                selected = json.loads((output / "design-direction.json").read_text(encoding="utf-8"))
                prompts.append((output / "image_prompt.txt").read_text(encoding="utf-8"))
                self.assertEqual(brief["aesthetic_spec"]["selected_direction_id"], direction_id)
                self.assertEqual(brief["aesthetic_spec"]["candidate_count"], 3)
                self.assertEqual(selected["id"], direction_id)
                self.assertEqual(len(brief["aesthetic_spec"]["design_directions"]), 3)
                self.assertIn("This prompt requests ONE image", prompts[-1])
                self.assertIn("Keep the scientific subject, action, evidence boundary", prompts[-1])
                self.assertFalse(brief["image_generation"]["executed"])
                self.assertFalse((output / "asset.png").exists())
                self.assertFalse(result["artwork_generated"])
            self.assertNotEqual(prompts[0], prompts[1])
            self.assertIn("softly layered gouache", prompts[0])
            self.assertIn("colored-pencil contours", prompts[1])

    def test_direction_plan_rejects_cosmetic_only_pairwise_changes(self):
        plan = json.loads(EXAMPLE_PLAN.read_text(encoding="utf-8"))
        plan["directions"][1]["composition"] = plan["directions"][0]["composition"]
        plan["directions"][1]["rendering_language"] = plan["directions"][0]["rendering_language"]
        plan["directions"][1]["silhouette"] = plan["directions"][0]["silhouette"]
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "directions.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            output = Path(directory) / "rejected"
            with self.assertRaisesRegex(ValueError, "at least two changed design axes"):
                asset_tool.init_asset(self.args(
                    output,
                    direction_plan=str(plan_path),
                    candidate_id="side-gouache",
                ))
            self.assertFalse(output.exists())

    def test_punctuation_only_edits_do_not_count_as_new_axes(self):
        plan = json.loads(EXAMPLE_PLAN.read_text(encoding="utf-8"))
        first, second = plan["directions"][:2]
        for axis in ("composition", "rendering_language", "silhouette"):
            second[axis] = first[axis] + ","
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "directions.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            output = Path(directory) / "rejected"
            with self.assertRaisesRegex(ValueError, "at least two changed design axes"):
                asset_tool.init_asset(self.args(
                    output,
                    direction_plan=str(plan_path),
                    candidate_id="side-gouache",
                ))
            self.assertFalse(output.exists())

    def test_candidate_id_and_plan_size_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, (candidate_id, candidate_count, message) in enumerate((
                ("missing", 3, "must match a direction id"),
                ("side-gouache", 2, "exactly 2 directions"),
            )):
                with self.subTest(candidate_id=candidate_id, candidate_count=candidate_count):
                    output = Path(directory) / str(index)
                    with self.assertRaisesRegex(ValueError, message):
                        asset_tool.init_asset(self.args(
                            output,
                            direction_plan=str(EXAMPLE_PLAN),
                            candidate_id=candidate_id,
                            candidate_count=candidate_count,
                        ))
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
