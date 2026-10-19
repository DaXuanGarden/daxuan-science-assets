import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import palette_context as pc

class ColorContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.snapshot=self.root/'source.txt';self.snapshot.write_text('Inspected local color notes')
        self.palette=self.root/'palette.json';self.colors={'body':'#91B2C8','text':'#39454B'}
        self.palette.write_text(json.dumps({'colors':self.colors}))
        self.svg=self.root/'asset.svg';self.svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><g id="body"><path fill="#91B2C8" data-fill-role="body"/></g></svg>')
        self.context={'schema_version':'1.0','status':'final','precedence':pc.ORDER,
          'sources':[{'id':scope,'scope':scope,'access':'source_snapshot','snapshot':'source.txt','snapshot_sha256':hashlib.sha256(self.snapshot.read_bytes()).hexdigest()} for scope in ['reference_author','target_figure']],
          'assignments':{role:{'hex':color,'basis':'preserved','source_ids':['target_figure'],'meaning':'Generic structure or text'} for role,color in self.colors.items()},
          'locked_colors':{'body':'#91B2C8'},'contrast_pairs':[{'foreground':'text','background':'#FFFFFF','min_ratio':4.5}]}
    def tearDown(self):self.tmp.cleanup()
    def check(self):return pc.check(self.context,self.root,self.palette,self.svg)
    def test_valid_context_and_paints(self):self.assertTrue(self.check()['ok'])
    def test_changed_snapshot_detected(self):
        self.snapshot.write_text('changed');self.assertFalse(self.check()['ok'])
    def test_svg_palette_mismatch_detected(self):
        self.svg.write_text(self.svg.read_text().replace('#91B2C8','#FFFFFF'));self.assertFalse(self.check()['ok'])
    def test_author_locked_color_protected(self):
        self.context['locked_colors']['body']='#000000';self.assertFalse(self.check()['ok'])
    def test_low_text_contrast_detected(self):
        self.colors['text']='#F8F8F8';self.palette.write_text(json.dumps({'colors':self.colors}));self.context['assignments']['text']['hex']='#F8F8F8';self.assertFalse(self.check()['ok'])
    def test_missing_target_context_detected(self):
        self.context['sources']=self.context['sources'][:1];self.assertFalse(self.check()['ok'])
    def test_unavailable_reference_is_honest_fallback(self):
        self.context['sources'][0]={'id':'reference_author','scope':'reference_author','access':'unavailable','note':'No reference paper provided'}
        result=self.check();self.assertTrue(result['ok']);self.assertTrue(result['warnings'])
    def test_source_cannot_escape_context_root(self):
        self.context['sources'][0]['snapshot']='../source.txt';self.assertFalse(self.check()['ok'])
    def test_inline_style_override_detected(self):
        self.svg.write_text(self.svg.read_text().replace('data-fill-role="body"','data-fill-role="body" style="fill:#FFFFFF"'));self.assertFalse(self.check()['ok'])
    def test_svg_literal_colors(self):
        self.svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><g><path fill="#abc" stroke="rgb(10, 20, 30)" style="fill:#91b2c8"/><stop stop-color="#BB748B"/></g></svg>')
        colors={r['hex'] for r in pc.inspect(self.svg)['chromatic_colors']};self.assertIn('#91B2C8',colors);self.assertIn('#BB748B',colors);self.assertNotIn('#AABBCC',colors)
    def test_raster_ignores_transparent_pixels_and_white(self):
        from PIL import Image
        p=self.root/'image.png';im=Image.new('RGBA',(4,1));im.putdata([(255,0,0,0),(255,255,255,255),(110,169,154,255),(110,169,154,255)]);im.save(p)
        result=pc.inspect(p);self.assertEqual(result['mode'],'approximate_raster_samples');self.assertEqual(result['chromatic_colors'][0]['hex'],'#6EA99A');self.assertEqual(result['chromatic_colors'][0]['count'],2)
    def test_unknown_score_role_detected(self):
        self.context['score_scales']=[{'roles':['body','unknown'],'direction':'low_to_high','meaning':'Illustrative score'}];self.assertFalse(self.check()['ok'])

if __name__=='__main__':unittest.main()
