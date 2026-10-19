import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("asset_tool", ROOT/"scripts/asset_tool.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
spec = importlib.util.spec_from_file_location("codex_reference", ROOT/"scripts/codex_reference.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
VALID = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><g id="body"><circle id="outline" cx="50" cy="50" r="25" fill="#D4B66C" data-fill-role="body" stroke="#AC8E4C" data-stroke-role="outline"/></g></svg>'''


class AssetToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)
        self.source = self.p/"asset.svg"
        self.source.write_text(VALID)
        self.palette = self.p/"palette.json"
        self.palette.write_text(json.dumps(tool.preset("teal")))

    def tearDown(self):
        self.tmp.cleanup()

    def invalid(self, svg):
        self.source.write_text(svg)
        self.assertFalse(tool.inspect_svg(self.source)["ok"])

    def test_native_shape_is_valid(self):
        result = tool.inspect_svg(self.source)
        self.assertTrue(result["ok"])
        self.assertEqual(result["palette_bindings"], 2)
        self.assertEqual(result["transparency"], "requires actual PNG render check")

    def test_embedded_png_is_rejected(self):
        self.invalid(VALID.replace('</g>', '<image href="data:image/png;base64,AAAA"/></g>'))

    def test_embedded_svg_is_rejected(self):
        self.invalid(VALID.replace('</g>', '<image href="data:image/svg+xml;base64,AAAA"/></g>'))

    def test_external_resource_is_rejected(self):
        self.invalid(VALID.replace('fill="#D4B66C"', 'fill="url(https://example.org/paint.svg)"'))

    def test_script_and_events_are_rejected(self):
        self.invalid(VALID.replace('</g>', '<script>void(0)</script></g>'))
        self.invalid(VALID.replace('<g id="body">', '<g id="body" onclick="void(0)">'))

    def test_duplicate_id_is_rejected(self):
        self.invalid(VALID.replace('id="outline"', 'id="body"'))

    def test_unresolved_gradient_is_rejected(self):
        self.invalid(VALID.replace('fill="#D4B66C"', 'fill="url(#missing)"'))

    def test_doctype_is_rejected(self):
        self.invalid('<!DOCTYPE svg [<!ENTITY sample "x">]>'+VALID)

    def test_xml_stylesheet_is_rejected_before_render(self):
        self.source.write_text('<?xml-stylesheet type="text/css" href="https://example.org/x.css"?>'+VALID)
        with mock.patch.object(tool.subprocess, 'run') as run:
            with self.assertRaises(ValueError): tool.render(self.source, self.p/'asset.png')
            run.assert_not_called()

    def test_motion_animation_is_rejected(self):
        self.invalid(VALID.replace('</g>', '<animateMotion dur="1s" path="M 0 0 L 10 10"/></g>'))

    def test_full_canvas_background_is_rejected(self):
        self.invalid(VALID.replace('<g id="body">', '<rect width="100%" height="100%" fill="white"/><g id="body">'))

    def test_invalid_viewbox_is_rejected(self):
        self.invalid(VALID.replace('0 0 100 100', '0 0 nan 100'))

    def test_recolor_preserves_geometry_and_source(self):
        before = self.source.read_bytes()
        output = self.p/"new.svg"
        result = tool.recolor(self.source,self.palette,output)
        self.assertTrue(result["geometry_preserved"])
        self.assertEqual(before,self.source.read_bytes())
        self.assertEqual(tool.geometry_digest(tool.parse_svg(self.source)),tool.geometry_digest(tool.parse_svg(output)))
        shape=next(n for n in tool.parse_svg(output).iter() if n.get('id')=='outline')
        self.assertEqual(shape.get('fill'),tool.preset('teal')['colors']['body'])
        self.assertEqual(shape.get('stroke'),tool.preset('teal')['colors']['outline'])

    def test_unknown_palette_role_fails_before_write(self):
        self.source.write_text(VALID.replace('data-fill-role="body"','data-fill-role="not-in-palette"'))
        output=self.p/"new.svg"
        with self.assertRaises(ValueError): tool.recolor(self.source,self.palette,output)
        self.assertFalse(output.exists())

    def test_inline_style_conflict_fails(self):
        self.source.write_text(VALID.replace('data-fill-role="body"','data-fill-role="body" style="fill:#000000"'))
        with self.assertRaises(ValueError): tool.recolor(self.source,self.palette,self.p/"new.svg")

    def test_output_cannot_overwrite_source_by_default(self):
        before=self.source.read_bytes()
        with self.assertRaises(FileExistsError): tool.recolor(self.source,self.palette,self.source)
        self.assertEqual(before,self.source.read_bytes())

    def test_brief_initialization_does_not_claim_artwork(self):
        directory=self.p/'new-asset'
        args=argparse.Namespace(slug='lab-pipette',subject='Generic pipette',outdir=str(directory),palette='warm-gold')
        result=tool.init_asset(args)
        self.assertFalse(result['artwork_generated'])
        self.assertFalse((directory/'asset.svg').exists())
        brief=json.loads((directory/'brief.json').read_text())
        self.assertFalse(brief['image_generation']['executed'])
        with self.assertRaises(FileExistsError): tool.init_asset(args)

    @unittest.skipUnless(shutil.which('rsvg-convert') and importlib.util.find_spec('PIL'),'requires local renderer and Pillow')
    def test_actual_render_has_transparent_edges_and_nonempty_foreground(self):
        output=self.p/'asset.png'
        result=tool.render(self.source,output,width=200,qa_path=self.p/'qa.json')
        self.assertTrue(result['ok'])
        self.assertTrue(result['png']['nonempty_foreground'])
        self.assertEqual(result['png']['corner_alpha'],[0,0,0,0])
        self.assertEqual(result['png']['edge_alpha_max'],[0,0,0,0])
        self.assertTrue((self.p/'qa.json').exists())

    def test_render_rejects_external_input_before_subprocess(self):
        self.source.write_text(VALID.replace('fill="#D4B66C"','fill="url(https://example.org/x.svg)"'))
        with mock.patch.object(tool.subprocess,'run') as run:
            with self.assertRaises(ValueError): tool.render(self.source,self.p/'asset.png')
            run.assert_not_called()

    @unittest.skipUnless(importlib.util.find_spec('PIL'),'requires Pillow')
    def test_opaque_png_is_not_reported_as_transparent(self):
        from PIL import Image
        path=self.p/'opaque.png'
        Image.new('RGB',(20,20),'white').save(path)
        self.assertFalse(tool.png_inspection(path)['ok'])

    def test_adapter_dry_run_makes_no_request_and_no_output(self):
        prompt=self.p/'prompt.txt'; prompt.write_text('an isolated generic mitochondrion')
        output=self.p/'reference.png'
        result=subprocess.run([sys.executable,str(ROOT/'scripts/codex_reference.py'),'--prompt-file',str(prompt),'--out',str(output),'--helper',str(self.p/'absent.py')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0)
        data=json.loads(result.stdout)
        self.assertEqual(data['mode'],'dry_run')
        self.assertFalse(data['generation_executed'])
        self.assertFalse(data['svg_generated'])
        self.assertFalse(output.exists())

    def test_adapter_does_not_forward_account_output(self):
        helper=self.p/'helper.py'; helper.write_text('# local fixture')
        completed=subprocess.CompletedProcess([],1,stdout='account-example-do-not-forward',stderr='private-account-example')
        with mock.patch.object(adapter.subprocess,'run',return_value=completed):
            data=adapter.doctor(str(helper))
        self.assertFalse(data['auth_ready'])
        self.assertNotIn('account-example',json.dumps(data))


if __name__=='__main__':
    unittest.main()
