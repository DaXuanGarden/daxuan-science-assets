"""Guard explicit candidate plans and behavior fidelity without image requests."""
from argparse import Namespace
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("asset_tool", ROOT / "scripts/asset_tool.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class CandidateActionContractTests(unittest.TestCase):
    def make_args(self, output, **changes):
        fields = dict(slug="desk-scene", subject="Seated computer use", outdir=str(output), palette="editorial-pastel", mode="raster_generation", background="transparent", aesthetic_review=True)
        fields.update(changes)
        return Namespace(**fields)

    def test_explicit_eight_candidate_plan_still_requests_one_image(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "eight"
            result = tool.init_asset(self.make_args(output, candidate_count=8))
            brief = json.loads((output / "brief.json").read_text())
            self.assertEqual(brief["aesthetic_spec"]["candidate_count"], 8)
            self.assertIn("This prompt requests ONE image", (output / "image_prompt.txt").read_text())
            self.assertFalse(result["artwork_generated"])
            self.assertFalse((output / "asset.png").exists())

    def test_default_and_user_requested_upper_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            for count in (None, 10):
                with self.subTest(count=count):
                    output = Path(directory) / str(count)
                    args = self.make_args(output, **({"candidate_count": count} if count is not None else {}))
                    tool.init_asset(args)
                    brief = json.loads((output / "brief.json").read_text())
                    self.assertEqual(brief["aesthetic_spec"]["candidate_count"], 2 if count is None else count)
                    self.assertIsNone(brief["action_contract"])

    def test_invalid_count_is_rejected_before_any_files_are_written(self):
        with tempfile.TemporaryDirectory() as directory:
            for count in (1, 11, True, 2.5):
                with self.subTest(count=count):
                    output = Path(directory) / str(count)
                    with self.assertRaises(ValueError):
                        tool.init_asset(self.make_args(output, candidate_count=count))
                    self.assertFalse(output.exists())

    def test_action_and_required_context_remain_in_brief_and_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "desk"
            tool.init_asset(self.make_args(output, action="Seated computer use at a desk, both feet grounded", attention_target="Computer screen in front of the person", required_context=["desk", "one monitor", "office task chair", "keyboard or mouse"]))
            brief = json.loads((output / "brief.json").read_text())
            self.assertEqual(brief["action_contract"]["attention_target"], "Computer screen in front of the person")
            prompt = (output / "image_prompt.txt").read_text()
            for text in ("both feet grounded", "Computer screen", "office task chair", "keyboard or mouse"):
                self.assertIn(text, prompt)

    def test_attention_target_without_action_does_not_create_ambiguous_brief(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "ambiguous"
            with self.assertRaises(ValueError):
                tool.init_asset(self.make_args(output, attention_target="screen"))
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
