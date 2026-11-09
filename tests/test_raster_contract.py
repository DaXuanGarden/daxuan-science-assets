"""Validate literal text locks and brief-scoped aesthetic QA through the CLI."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("raster_contract_fixtures", ROOT / "tests/test_aesthetic_review.py")
FIXTURES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURES)


class RasterContractTests(unittest.TestCase):
    def prepare(self, root, background="opaque", composition="process_chain", review_required=False):
        image = Image.new("RGBA", (8, 8), (100, 140, 160, 255) if background == "opaque" else (0, 0, 0, 0))
        if background != "opaque":
            image.putpixel((4, 4), (100, 140, 160, 255))
        image.save(root / "asset.png")
        documents = {
            "brief.json": {"aesthetic_review_required": review_required, "delivery_mode": "raster_generation", "target_size_px": [8, 8], "background": background, "composition_mode": composition},
            "text_manifest.json": {"no_extra_text": True, "texts": []},
            "relation_manifest.json": {"no_unlisted_arrows": True, "relations": []},
            "source_manifest.json": {"sources": [{"type": "fixture"}]},
            "generation-evidence.json": {"generation_verified": True},
        }
        for name, value in documents.items():
            (root / name).write_text(json.dumps(value))

    def run_qa(self, root):
        run = subprocess.run([sys.executable, str(ROOT / "scripts/raster_asset_qa.py"), str(root)], capture_output=True, text=True, timeout=15)
        self.assertNotIn("Traceback", run.stderr, run.stderr)
        return run, json.loads((root / "qa.json").read_text())

    def test_text_items_require_objects_and_literal_true(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare(root)
            cases = (([{"id": "L1", "verbatim": True}], True),
                     ([{"id": "L1"}], False), ([{"id": "L1", "verbatim": None}], False),
                     ([{"id": "L1", "verbatim": False}], False), ([{"id": "L1", "verbatim": 1}], False),
                     ([{"id": "L1", "verbatim": "true"}], False), (["L1"], False),
                     ([{"id": " ", "verbatim": True}], False), ({"id": "L1", "verbatim": True}, False))
            for texts, accepted in cases:
                with self.subTest(texts=texts):
                    (root / "text_manifest.json").write_text(json.dumps({"no_extra_text": True, "texts": texts}))
                    run, result = self.run_qa(root)
                    self.assertEqual(run.returncode, 0 if accepted else 1, run.stdout + run.stderr)
                    self.assertEqual(result["ok"], accepted)

    def test_explicit_opaque_and_multiobject_briefs_reach_raster_review(self):
        cases = (("opaque", "scene_centered", {"verified_alpha"}),
                 ("transparent", "process_chain", {"single_anchor", "no_detached_objects"}),
                 ("opaque", "icon_composite", {"verified_alpha", "single_anchor", "no_detached_objects"}))
        for background, composition, excluded in cases:
            with self.subTest(background=background, composition=composition), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.prepare(root, background, composition, True)
                review = FIXTURES.valid_review()
                review["asset_sha256"] = hashlib.sha256((root / "asset.png").read_bytes()).hexdigest()
                for gate in excluded:
                    del review["hard_gates"][gate]
                (root / "aesthetic-review.json").write_text(json.dumps(review))
                run, result = self.run_qa(root)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertTrue(result["aesthetic_review"]["hard_gates_passed"])
                self.assertTrue(excluded.isdisjoint(result["aesthetic_review"]["required_gates"]))

    def test_transparent_scene_cannot_bypass_required_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare(root, "transparent", "scene_centered", True)
            review = FIXTURES.valid_review()
            review["asset_sha256"] = hashlib.sha256((root / "asset.png").read_bytes()).hexdigest()
            for gate in ("verified_alpha", "single_anchor", "no_detached_objects"):
                del review["hard_gates"][gate]
            (root / "aesthetic-review.json").write_text(json.dumps(review))
            run, result = self.run_qa(root)
            self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
            self.assertTrue(any("missing required gates" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
