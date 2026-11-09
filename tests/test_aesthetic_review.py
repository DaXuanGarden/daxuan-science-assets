"""Exercise review attribution, hard gates, arithmetic, and image binding."""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "aesthetic_review", ROOT / "scripts/aesthetic_review.py"
)
review_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review_tool)


def valid_review():
    """A complete review record, not evidence of an actually attractive image."""
    return {
        "schema_version": "1.0",
        "status": "pass",
        "reviewer": "independent fixture reviewer",
        "reviewer_type": "agent",
        "user_acceptance": "pending",
        "asset_sha256": "a" * 64,
        "reviewed_images": ["thumbnail.png", "placement.png"],
        "candidate_comparison": [
            {"candidate": "a", "note": "The selected scene has a clearer gesture."},
            {"candidate": "b", "note": "The chair competes with the subject."},
        ],
        "selection_reason": "The selected candidate reads clearly at the target size.",
        "review_scope": {
            "target_px": [1500, 1500],
            "thumbnail_px": [200, 200],
            "slot_px": [165, 165],
        },
        "criteria": {
            key: {"score": 4, "note": "Visual evidence checked in the named proof images."}
            for key in review_tool.WEIGHTS
        },
        "weighted_score": 80,
        "hard_gates": {key: True for key in review_tool.REQUIRED_GATES},
        "selected_candidate": "a",
        "science_boundary": "Aesthetic judgement does not establish scientific truth.",
    }


class AestheticReviewTests(unittest.TestCase):
    def test_complete_agent_review_does_not_claim_human_acceptance(self):
        result = review_tool.validate_review(valid_review())
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["weighted_score"], 80)
        self.assertEqual(result["reviewer_type"], "agent")
        self.assertEqual(result["user_acceptance"], "pending")
        self.assertIn("does not certify beauty", result["scope"])
        self.assertIn("scientific truth", result["scope"])

    def test_human_and_self_review_remain_explicitly_attributed(self):
        for reviewer_type, acceptance in (("human", "accepted"), ("self_review", "pending")):
            with self.subTest(reviewer_type=reviewer_type):
                review = valid_review()
                review.update(reviewer_type=reviewer_type, user_acceptance=acceptance)
                result = review_tool.validate_review(review)
                self.assertTrue(result["ok"], result["errors"])
                self.assertEqual(result["reviewer_type"], reviewer_type)
                self.assertEqual(result["user_acceptance"], acceptance)

    def test_reviewer_or_acceptance_cannot_be_unattributed(self):
        for field in ("reviewer", "reviewer_type", "user_acceptance"):
            with self.subTest(field=field):
                review = valid_review()
                del review[field]
                self.assertFalse(review_tool.validate_review(review)["ok"])

    def test_missing_required_gate_rejects_even_high_scores(self):
        review = valid_review()
        del review["hard_gates"]["single_anchor"]
        result = review_tool.validate_review(review)
        self.assertFalse(result["ok"])
        self.assertTrue(any("missing required gates" in error for error in result["errors"]))

    def test_high_score_cannot_override_failed_gate(self):
        review = valid_review()
        for criterion in review["criteria"].values():
            criterion["score"] = 5
        review["weighted_score"] = 100
        review["hard_gates"]["no_clipping"] = False
        result = review_tool.validate_review(review)
        self.assertFalse(result["ok"])
        self.assertFalse(result["hard_gates_passed"])
        self.assertIn("pass requires every hard gate to be true", result["errors"])

    def test_scores_and_totals_reject_nonfinite_numbers_and_booleans(self):
        for value in (float("nan"), float("inf"), -float("inf"), True):
            for field in ("criterion", "weighted_score"):
                with self.subTest(value=value, field=field):
                    review = valid_review()
                    if field == "criterion":
                        review["criteria"]["visual_hierarchy"]["score"] = value
                    else:
                        review["weighted_score"] = value
                    self.assertFalse(review_tool.validate_review(review)["ok"])

    def test_recorded_total_must_match_weighted_rubric(self):
        review = valid_review()
        review["weighted_score"] = 96
        result = review_tool.validate_review(review)
        self.assertFalse(result["ok"])
        self.assertEqual(result["weighted_score"], 80)
        self.assertTrue(any("weighted_score must equal 80.0" in error for error in result["errors"]))

    def test_pass_requires_each_dimension_to_be_usable(self):
        review = valid_review()
        for criterion in review["criteria"].values():
            criterion["score"] = 5
        review["criteria"]["detail_economy"]["score"] = 2
        review["weighted_score"] = 94
        result = review_tool.validate_review(review)
        self.assertFalse(result["ok"])
        self.assertIn("pass requires every criterion score >= 3", result["errors"])

    def test_revise_record_is_complete_but_not_a_pass_recommendation(self):
        review = valid_review()
        review["status"] = "revise"
        review["hard_gates"]["thumbnail_recognition"] = False
        result = review_tool.validate_review(review)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["review_status"], "revise")
        self.assertFalse(result["hard_gates_passed"])
        self.assertEqual(result["user_acceptance"], "pending")

    def test_behavior_gate_is_required_only_when_the_brief_locks_an_action(self):
        review = valid_review()
        contract = {"action": "Seated computer use at a desk, both feet grounded", "attention_target": "Computer screen in front of the person", "required_context": ["desk", "one monitor", "office task chair", "keyboard or mouse"]}
        legacy = review_tool.validate_review(review)
        self.assertTrue(legacy["ok"], legacy["errors"])
        self.assertFalse(legacy["required_behavior_reviewed"])
        locked = review_tool.validate_review(review, contract)
        self.assertFalse(locked["ok"])
        self.assertFalse(locked["hard_gates_passed"])
        self.assertTrue(any("required_behavior_match" in error for error in locked["errors"]))
        review["hard_gates"]["required_behavior_match"] = True
        complete = review_tool.validate_review(review, contract)
        self.assertTrue(complete["ok"], complete["errors"])
        self.assertTrue(complete["required_behavior_reviewed"])

    def test_high_aesthetic_score_does_not_override_wrong_required_behavior(self):
        review = valid_review()
        for criterion in review["criteria"].values():
            criterion["score"] = 5
        review["weighted_score"] = 100
        review["hard_gates"]["required_behavior_match"] = False
        result = review_tool.validate_review(review, {"action": "look at the screen"})
        self.assertFalse(result["ok"])
        self.assertFalse(result["recommendation_eligible"])
        review["status"] = "revise"
        revised = review_tool.validate_review(review, {"action": "look at the screen"})
        self.assertTrue(revised["ok"], revised["errors"])
        self.assertFalse(revised["recommendation_eligible"])

    def test_cli_rejects_review_for_a_different_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = root / "asset.png"
            # The standalone review CLI binds bytes; image decoding belongs to raster QA.
            asset.write_bytes(b"fixture image bytes")
            review = valid_review()
            review["asset_sha256"] = hashlib.sha256(asset.read_bytes()).hexdigest()
            (root / "aesthetic-review.json").write_text(json.dumps(review), encoding="utf-8")
            command = [sys.executable, str(ROOT / "scripts/aesthetic_review.py"), str(root)]
            initial = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
            (root / "brief.json").write_text(json.dumps({"action_contract": {"action": "look at the screen"}}), encoding="utf-8")
            missing_action_gate = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(missing_action_gate.returncode, 1)
            self.assertIn("required_behavior_match", missing_action_gate.stdout)
            review["hard_gates"]["required_behavior_match"] = True
            (root / "aesthetic-review.json").write_text(json.dumps(review), encoding="utf-8")
            restored = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(restored.returncode, 0, restored.stdout + restored.stderr)
            asset.write_bytes(b"a different selected image")
            changed = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(changed.returncode, 1)
            result = json.loads((root / "aesthetic-qa.json").read_text(encoding="utf-8"))
            self.assertFalse(result["ok"])
            self.assertIn("asset.png hash differs from the reviewed image", result["errors"])

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "requires Pillow for raster integration")
    def test_required_raster_review_rejects_revise_status_and_hash_drift(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = root / "asset.png"
            image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            image.putpixel((4, 4), (100, 140, 160, 255))
            image.save(asset)
            review = valid_review()
            review["asset_sha256"] = hashlib.sha256(asset.read_bytes()).hexdigest()
            documents = {
                "brief.json": {"aesthetic_review_required": True, "delivery_mode": "raster_generation", "target_size_px": [8, 8], "background": "transparent"},
                "text_manifest.json": {"no_extra_text": True, "texts": []},
                "relation_manifest.json": {"no_unlisted_arrows": True, "relations": []},
                "source_manifest.json": {"sources": [{"type": "fixture", "description": "Synthetic byte-binding integration case"}]},
                "generation-evidence.json": {"generation_verified": True},
            }
            for name, document in documents.items():
                (root / name).write_text(json.dumps(document), encoding="utf-8")
            command = [sys.executable, str(ROOT / "scripts/raster_asset_qa.py"), str(root)]
            # A locked behavior cannot be bypassed by omitting the conditional gate.
            brief = documents["brief.json"]
            brief["action_contract"] = {"action": "seated at a desk looking at the screen"}
            brief["aesthetic_review_required"] = False
            (root / "brief.json").write_text(json.dumps(brief), encoding="utf-8")
            missing_review = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(missing_review.returncode, 1)
            self.assertIn("visual review is required", missing_review.stdout)
            (root / "aesthetic-review.json").write_text(json.dumps(review), encoding="utf-8")
            missing = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(missing.returncode, 1)
            self.assertIn("required_behavior_match", missing.stdout)
            review["hard_gates"]["required_behavior_match"] = True
            for status, expected_code in (("pass", 0), ("revise", 1)):
                with self.subTest(status=status):
                    review["status"] = status
                    (root / "aesthetic-review.json").write_text(json.dumps(review), encoding="utf-8")
                    run = subprocess.run(command, capture_output=True, text=True, timeout=15)
                    self.assertEqual(run.returncode, expected_code, run.stdout + run.stderr)
                    result = json.loads((root / "qa.json").read_text(encoding="utf-8"))
                    if status == "revise":
                        self.assertTrue(result["aesthetic_review"]["ok"])
                        self.assertIn("aesthetic reviewer has not recommended this candidate", result["errors"])
            review["status"] = "pass"
            review["asset_sha256"] = "0" * 64
            (root / "aesthetic-review.json").write_text(json.dumps(review), encoding="utf-8")
            run = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 1)
            result = json.loads((root / "qa.json").read_text(encoding="utf-8"))
            self.assertIn("final asset hash differs from aesthetic-review.json", result["errors"])


if __name__ == "__main__":
    unittest.main()
