"""Prevent aspect distortion in both aesthetic and destination previews."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageChops


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_review_previews.py"


class ReviewPreviewAspectTests(unittest.TestCase):
    def run_previews(self, root, size, figure=None, slot=None):
        asset_dir = root / "asset"
        asset_dir.mkdir()
        source = asset_dir / "asset.png"
        Image.new("RGBA", size, "#F00000").save(source)
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        argv = [sys.executable, str(SCRIPT), str(asset_dir)]
        if figure is not None:
            argv += ["--figure", str(figure), "--slot", *map(str, slot)]
        result = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_hash)
        return asset_dir, json.loads((asset_dir / "preview-evidence.json").read_text())

    def assert_foreground_box(self, path, background, expected):
        with Image.open(path) as actual:
            difference = ImageChops.difference(actual.convert("RGB"), Image.new("RGB", actual.size, background))
            self.assertEqual(difference.getbbox(), expected)

    def test_portrait_asset_retains_proportions_in_all_display_previews(self):
        with tempfile.TemporaryDirectory() as directory:
            asset_dir, evidence = self.run_previews(Path(directory), (40, 80))
            for name, background, side in (("preview-white.png", "#FFFFFF", 600), ("preview-dark.png", "#223542", 600), ("thumbnail_200px.png", "#FFFFFF", 200)):
                with self.subTest(name=name):
                    self.assert_foreground_box(asset_dir / name, background, (side // 4, 0, 3 * side // 4, side))
                    self.assertEqual(evidence["rendered_boxes"][name], [side // 4, 0, side // 2, side])
            self.assertEqual(evidence["asset_size_px"], [40, 80])
            self.assertEqual(evidence["fit_policy"], "contain_centered_preserve_aspect")

    def test_landscape_asset_is_centered_in_tall_slot_without_distortion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            figure = root / "figure.png"
            Image.new("RGB", (200, 150), "white").save(figure)
            figure_hash = hashlib.sha256(figure.read_bytes()).hexdigest()
            asset_dir, evidence = self.run_previews(root, (80, 40), figure, (20, 30, 60, 80))
            self.assert_foreground_box(asset_dir / "placement.png", "white", (20, 55, 80, 85))
            self.assertEqual(evidence["rendered_boxes"]["placement.png"], [20, 55, 60, 30])
            self.assertEqual(evidence["slot_xywh"], [20, 30, 60, 80])
            self.assertEqual(hashlib.sha256(figure.read_bytes()).hexdigest(), figure_hash)
            with Image.open(asset_dir / "placement-crop.png") as crop:
                self.assertEqual(crop.size, (110, 140))


if __name__ == "__main__":
    unittest.main()
