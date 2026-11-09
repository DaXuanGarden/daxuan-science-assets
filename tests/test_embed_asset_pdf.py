import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw

try:
    import fitz
except ImportError:
    fitz = None

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/embed_asset_pdf.py"
SPEC = importlib.util.spec_from_file_location("embed_asset_pdf", SCRIPT)
EMBED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EMBED)


@unittest.skipIf(fitz is None, "optional PDF embedding requires PyMuPDF")
class PDFEmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.pdf"
        with fitz.open() as pdf:
            page = pdf.new_page(width=300, height=300)
            page.insert_text((15, 25), "Scientific result", fontsize=10)
            page.draw_circle((150, 150), 72, color=(0.2, 0.5, 0.6))
            page.draw_line((10, 200), (280, 200), color=(0.8, 0.2, 0.1))
            page = pdf.new_page(width=200, height=240)
            page.insert_text((20, 30), "Unchanged second page")
            page.draw_rect((20, 50, 150, 180), color=(0.1, 0.3, 0.4))
            pdf.save(self.source)
        self.asset = self.root / "asset.png"
        image = Image.new("RGBA", (60, 120), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse((10, 10, 50, 110), fill=(40, 150, 130, 255))
        image.save(self.asset)
        self.output = self.root / "result"

    def run_embed(self, **kwargs):
        return EMBED.embed(self.source, self.asset, self.output, (100, 85, 200, 185), **kwargs)

    def test_vector_pdf_and_nonsquare_asset_roundtrip(self):
        hashes = [EMBED.sha(p) for p in (self.source, self.asset)]
        evidence = self.run_embed(label="LST", label_center_x=150, label_baseline_y=215)
        self.assertEqual(hashes, [EMBED.sha(p) for p in (self.source, self.asset)])
        self.assertTrue(evidence["label"]["native_text_verified"])
        rect = evidence["actual_asset_rect_pt"]
        self.assertAlmostEqual((rect[2] - rect[0]) / (rect[3] - rect[1]), 0.5)
        self.assertEqual(rect, [125, 85, 175, 185])
        self.assertAlmostEqual(evidence["effective_asset_dpi"], 86.4)
        self.assertEqual(evidence["page_count"], 2)
        self.assertTrue(evidence["pages"][0]["changed_pixels"] > 0)
        self.assertEqual(evidence["pages"][1]["changed_pixels"], 0)
        self.assertTrue(all(p["changed_pixels_outside_allowed_regions"] == 0 for p in evidence["pages"]))
        with Image.open(self.output / "figure.png") as preview:
            self.assertEqual(preview.size, (625, 625))
        with fitz.open(self.output / "figure.pdf") as pdf, fitz.open(self.source) as source:
            self.assertEqual(pdf[0].get_drawings(), source[0].get_drawings())
            self.assertEqual(pdf[0].get_text(), source[0].get_text() + "LST\n")
            self.assertEqual(pdf[1].get_text(), source[1].get_text())
        self.assertTrue(json.loads((self.output / "composition-evidence.json").read_text())["ok"])

    def test_invalid_placement_or_page_fails_before_output(self):
        for rect in [(-1, 20, 100, 100), (20, 20, 10, 50), (0, 0, 301, 50), (1, 2, float("nan"), 5)]:
            with self.subTest(rect=rect), self.assertRaises(ValueError):
                EMBED.embed(self.source, self.asset, self.output, rect)
        for page in [0, 3]:
            with self.subTest(page=page), self.assertRaises(ValueError):
                self.run_embed(page_number=page)
        self.assertFalse(self.output.exists())

    def test_opaque_or_invisible_asset_rejected(self):
        for color in [(30, 80, 50, 255), (30, 80, 50, 180), (0, 0, 0, 0)]:
            Image.new("RGBA", (60, 60), color).save(self.asset)
            with self.assertRaises(ValueError):
                self.run_embed()
        self.assertFalse(self.output.exists())

    def test_existing_outputs_and_symlink_refused(self):
        self.run_embed()
        before = EMBED.sha(self.output / "figure.pdf")
        with self.assertRaises(ValueError):
            self.run_embed()
        self.assertEqual(before, EMBED.sha(self.output / "figure.pdf"))
        target = self.root / "empty"
        target.mkdir()
        link = self.root / "linked"
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            EMBED.embed(self.source, self.asset, link, (50, 50, 100, 100))
        self.assertEqual(list(target.iterdir()), [])

    def test_label_font_and_bounds_constraints(self):
        for kwargs in [{"label": "LST"}, {"label": "LST", "label_center_x": 2, "label_baseline_y": 2},
                       {"label": "\u4e2d", "label_center_x": 150, "label_baseline_y": 215},
                       {"label_center_x": 150}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_embed(**kwargs)
        self.assertFalse(self.output.exists())

    def test_rotated_target_is_not_guessed(self):
        with fitz.open(self.source) as pdf:
            pdf[0].set_rotation(90)
            self.source.write_bytes(pdf.tobytes())
        with self.assertRaises(ValueError):
            self.run_embed()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
