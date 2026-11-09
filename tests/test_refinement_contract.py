"""Check selected-base provenance and edits that overall scores must not conceal."""
from argparse import Namespace
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


asset_tool = module("refine_asset_tool", ROOT / "scripts/asset_tool.py")
review_tool = module("refine_review_tool", ROOT / "scripts/aesthetic_review.py")
review_fixtures = module("refine_review_fixtures", ROOT / "tests/test_aesthetic_review.py")


class RefinementContractTests(unittest.TestCase):
    def args(self, output, base, **changes):
        fields = dict(slug="refined-scene", subject="Selected scientific scene", outdir=str(output), mode="raster_generation", palette="editorial-pastel", background="transparent", iteration_mode="refine", base_asset=str(base), edit_target=["Separate the visible fingers naturally"], preserve_feature=["Approved side-view composition"])
        fields.update(changes)
        return Namespace(**fields)

    def test_selected_base_is_bound_before_any_image_request(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "selected.svg"
            base.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 4"><circle cx="2" cy="2" r="1"/></svg>')
            output = Path(directory) / "refined"
            result = asset_tool.init_asset(self.args(output, base))
            brief = json.loads((output / "brief.json").read_text())
            contract = brief["refinement_contract"]
            self.assertEqual(brief["iteration_mode"], "refine")
            self.assertEqual(brief["aesthetic_spec"]["candidate_count"], 1)
            self.assertTrue(brief["aesthetic_review_required"])
            self.assertEqual(contract["base_asset"]["sha256"], hashlib.sha256(base.read_bytes()).hexdigest())
            self.assertEqual(contract["preserve_features"], ["Approved side-view composition"])
            prompt = (output / "image_prompt.txt").read_text()
            self.assertIn("Separate the visible fingers naturally", prompt)
            self.assertIn("supplied selected-base image", prompt)
            self.assertFalse(result["artwork_generated"])
            self.assertFalse((output / "asset.png").exists())

    def test_incomplete_refinement_and_wrong_count_fail_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "base.svg"
            base.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            cases = [{"base_asset": None}, {"base_asset": str(base.parent / "missing.png")}, {"edit_target": []}, {"preserve_feature": []}, {"edit_target": [" "]}, {"candidate_count": 3}, {"iteration_mode": "explore"}]
            for index, changes in enumerate(cases):
                output = Path(directory) / str(index)
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    asset_tool.init_asset(self.args(output, base, **changes))
                self.assertFalse(output.exists())
            two = Path(directory) / "two"
            asset_tool.init_asset(self.args(two, base, candidate_count=2))
            self.assertEqual(json.loads((two / "brief.json").read_text())["aesthetic_spec"]["candidate_count"], 2)

    def contract(self):
        return {"base_asset": {"path": "selected.png", "sha256": "b" * 64}, "edit_targets": ["Natural fingers", "Gentler sleeve folds"], "preserve_features": ["Approved side view"]}

    def complete_review(self, contract):
        review = review_fixtures.valid_review()
        review["base_asset_sha256"] = contract["base_asset"]["sha256"]
        review["hard_gates"].update(selected_base_preserved=True, requested_edits_addressed=True)
        review["edit_assessment"] = [{"target": target, "outcome": "improved", "note": "Compared named detail crops with the selected base."} for target in contract["edit_targets"]]
        return review

    def test_score_cannot_substitute_for_requested_edit_comparison(self):
        contract = self.contract()
        missing = review_fixtures.valid_review()
        self.assertFalse(review_tool.validate_review(missing, refinement_contract=contract)["ok"])
        review = self.complete_review(contract)
        self.assertTrue(review_tool.validate_review(review, refinement_contract=contract)["ok"])
        review["edit_assessment"].pop()
        self.assertFalse(review_tool.validate_review(review, refinement_contract=contract)["ok"])
        review = self.complete_review(contract)
        review["base_asset_sha256"] = "c" * 64
        self.assertFalse(review_tool.validate_review(review, refinement_contract=contract)["ok"])

    def test_unchanged_or_regressed_target_requires_a_revision_verdict(self):
        contract = self.contract()
        for outcome in ("unchanged", "regressed", "not_visible"):
            with self.subTest(outcome=outcome):
                review = self.complete_review(contract)
                review["edit_assessment"][0]["outcome"] = outcome
                self.assertFalse(review_tool.validate_review(review, refinement_contract=contract)["ok"])
                review["status"] = "revise"
                review["hard_gates"]["requested_edits_addressed"] = False
                result = review_tool.validate_review(review, refinement_contract=contract)
                self.assertTrue(result["ok"], result["errors"])
                self.assertFalse(result["recommendation_eligible"])
        review = self.complete_review(contract)
        review["hard_gates"]["selected_base_preserved"] = False
        self.assertFalse(review_tool.validate_review(review, refinement_contract=contract)["ok"])

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "requires Pillow for raster integration")
    def test_raster_refinement_cannot_bypass_review_or_base_hash(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "selected.png"
            image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            image.putpixel((4, 4), (100, 140, 160, 255))
            image.save(base)
            image.save(root / "asset.png")
            contract = self.contract()
            contract["base_asset"] = {"path": str(base), "sha256": hashlib.sha256(base.read_bytes()).hexdigest()}
            review = self.complete_review(contract)
            review["asset_sha256"] = hashlib.sha256((root / "asset.png").read_bytes()).hexdigest()
            docs = {"brief.json": {"delivery_mode": "raster_generation", "background": "transparent", "target_size_px": [8, 8], "refinement_contract": contract}, "text_manifest.json": {"no_extra_text": True, "texts": []}, "relation_manifest.json": {"no_unlisted_arrows": True, "relations": []}, "source_manifest.json": {"sources": [{"type": "fixture"}]}, "generation-evidence.json": {"generation_verified": True}}
            for name, document in docs.items():
                (root / name).write_text(json.dumps(document))
            command = [sys.executable, str(ROOT / "scripts/raster_asset_qa.py"), str(root)]
            missing = subprocess.run(command, text=True, capture_output=True, timeout=15)
            self.assertEqual(missing.returncode, 1)
            self.assertIn("visual review is required", missing.stdout)
            (root / "aesthetic-review.json").write_text(json.dumps(review))
            valid = subprocess.run(command, text=True, capture_output=True, timeout=15)
            self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
            brief = docs["brief.json"]
            brief["iteration_mode"] = "refine"
            del brief["refinement_contract"]
            (root / "brief.json").write_text(json.dumps(brief))
            unbound = subprocess.run(command, text=True, capture_output=True, timeout=15)
            self.assertEqual(unbound.returncode, 1)
            self.assertIn("refine mode requires a selected-base refinement_contract", unbound.stdout)
            brief["refinement_contract"] = contract
            (root / "brief.json").write_text(json.dumps(brief))
            image.putpixel((3, 3), (160, 140, 100, 255))
            image.save(base)
            drifted = subprocess.run(command, text=True, capture_output=True, timeout=15)
            self.assertEqual(drifted.returncode, 1)
            self.assertIn("selected refinement base hash has changed", drifted.stdout)


if __name__ == "__main__":
    unittest.main()
