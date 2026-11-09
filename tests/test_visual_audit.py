import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageChops

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/visual_audit.py"
SPEC = importlib.util.spec_from_file_location("visual_audit", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class VisualAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "selected"
        self.source.mkdir()
        Image.new("RGBA", (60, 60), (80, 150, 140, 200)).save(self.source / "asset.png")
        (self.source / "brief.json").write_text(json.dumps({"subject": "generic illustrative object"}))
        self.figure = self.root / "figure.png"
        Image.new("RGB", (160, 140), "white").save(self.figure)
        self.out = self.root / "audit"

    def prepare(self, with_destination=True):
        return AUDIT.prepare(self.source, self.out, self.figure if with_destination else None, (50, 30, 60, 60) if with_destination else None)

    def complete(self):
        evidence = json.loads((self.out / "evidence.json").read_text())
        review = json.loads((self.out / "review.json").read_text())
        review.update(status="complete", reviewer="independent reviewer", reviewer_type="agent",
                      views_inspected=[f["id"] for f in evidence["files"] if f["kind"] == "view"],
                      strengths=["The subject has a clear outer silhouette.", "The palette distinguishes the object from the canvas."],
                      verdict="keep", science_boundary="Conceptual object; no quantitative result or causal claim.")
        review["domain_assessments"] = {name: {"status": "reviewed", "note": "Observed at the available scales; no priority defect found."} for name in AUDIT.DOMAINS}
        review["destination_assessment"] = {"status": "inspected" if evidence["destination_available"] else "not_supplied", "note": "Placement inspected at native pixel size." if evidence["destination_available"] else "No target supplied; final placement remains unknown."}
        AUDIT.dump(self.out / "review.json", review)
        return review

    def test_pending_template_rejected_and_sources_unchanged(self):
        before = (self.source / "asset.png").read_bytes()
        self.prepare()
        self.assertFalse(AUDIT.validate(self.out)["ok"])
        self.assertEqual(before, (self.source / "asset.png").read_bytes())
        self.assertEqual(before, (self.out / "asset.png").read_bytes())
        with self.assertRaises(ValueError):
            self.prepare()

    def test_single_asset_keep_without_fake_comparison_or_score(self):
        self.prepare()
        self.complete()
        result = AUDIT.validate(self.out)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["findings_checked"], 0)
        self.assertTrue(result["destination_reviewed"])

    def test_nonsquare_asset_keeps_proportions_and_centers_in_each_preview(self):
        Image.new("RGBA", (40, 80), (80, 150, 140, 255)).save(self.source / "asset.png")
        before = (self.source / "asset.png").read_bytes()
        self.prepare(False)
        for name, side, background in (("white", 600, "#FFFFFF"), ("dark", 600, "#223542"), ("thumbnail", 200, "#FFFFFF")):
            with self.subTest(view=name):
                preview = Image.open(self.out / (name + ".png")).convert("RGB")
                self.assertEqual(preview.size, (side, side))
                bounds = ImageChops.difference(preview, Image.new("RGB", preview.size, background)).getbbox()
                self.assertEqual(bounds, (side // 4, 0, 3 * side // 4, side))
                self.assertEqual((bounds[2] - bounds[0]) / (bounds[3] - bounds[1]), 0.5)
        self.assertEqual(before, (self.out / "asset.png").read_bytes())
        self.assertEqual(before, (self.source / "asset.png").read_bytes())

    def test_missing_actual_slot_view_is_rejected(self):
        self.prepare()
        review = self.complete()
        review["views_inspected"].remove("destination_slot")
        AUDIT.dump(self.out / "review.json", review)
        self.assertFalse(AUDIT.validate(self.out)["ok"])

    def test_source_and_snapshot_hash_changes_are_detected(self):
        self.prepare()
        self.complete()
        with (self.source / "asset.png").open("ab") as stream:
            stream.write(b"changed source")
        self.assertTrue(any("source hash changed" in e for e in AUDIT.validate(self.out)["errors"]))
        with (self.out / "dark.png").open("ab") as stream:
            stream.write(b"changed snapshot")
        self.assertTrue(any("snapshot path or hash mismatch" in e for e in AUDIT.validate(self.out)["errors"]))

    def test_no_destination_remains_explicitly_unknown(self):
        self.prepare(False)
        review = self.complete()
        self.assertTrue(AUDIT.validate(self.out)["ok"])
        review["destination_assessment"]["status"] = "inspected"
        AUDIT.dump(self.out / "review.json", review)
        self.assertFalse(AUDIT.validate(self.out)["ok"])

    def test_findings_need_visible_acceptance_and_bounded_priorities(self):
        self.prepare()
        review = self.complete()
        finding = {"id": "F1", "domain": "craft", "severity": "minor", "confidence": "medium",
                   "region": {"space": "asset", "box": [0.1, 0.4, 0.3, 0.7]}, "visible_at": ["detail"],
                   "observation": "Two edges merge in the enlarged view.", "impact": "Object contacts become ambiguous.",
                   "action": "Separate the two edges without changing the silhouette.", "acceptance": "The detail crop shows two clear boundaries."}
        review.update(findings=[finding], top_actions=["F1"], verdict="refine")
        AUDIT.dump(self.out / "review.json", review)
        self.assertTrue(AUDIT.validate(self.out)["ok"])
        del finding["acceptance"]
        AUDIT.dump(self.out / "review.json", review)
        self.assertFalse(AUDIT.validate(self.out)["ok"])
        finding["acceptance"] = "The detail crop shows two clear boundaries."
        review["top_actions"] = ["F1", "F1", "F1", "F1"]
        AUDIT.dump(self.out / "review.json", review)
        self.assertFalse(AUDIT.validate(self.out)["ok"])


if __name__ == "__main__":
    unittest.main()
