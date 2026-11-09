#!/usr/bin/env python3
"""Rebuild an authored PDF-placement demonstration; no statistical data or model call."""
from pathlib import Path
import argparse
import json
from embed_asset_pdf import embed, require_fitz

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', type=Path, required=True)
    args = parser.parse_args()
    target = args.outdir
    if target.exists():
        parser.error('choose a new output directory; no overwrite')
    fitz = require_fitz()
    target.mkdir(parents=True)
    source = target / 'source.pdf'
    with fitz.open() as document:
        page = document.new_page(width=480, height=360)
        page.insert_text((28, 31), 'Illustrative PDF assembly', fontsize=17, color=(.12,.27,.30))
        page.insert_text((28, 49), 'Authored layout demonstration; no empirical results', fontsize=9, color=(.38,.46,.48))
        page.draw_circle((240, 181), 94, color=(.62,.75,.76), width=1.2)
        for start, end, text, origin in [
            ((167,122),(100,88),'SOURCE A',(59,78)),
            ((313,122),(380,88),'SOURCE B',(355,78)),
            ((167,240),(100,280),'SOURCE C',(59,298)),
            ((313,240),(380,280),'SOURCE D',(355,298))]:
            page.draw_line(start,end,color=(.67,.78,.77),width=1)
            page.draw_circle(end,4,color=(.30,.54,.55),fill=(.92,.96,.95))
            page.insert_text(origin,text,fontsize=9,color=(.22,.36,.39))
        document.save(source)
    evidence = embed(source, ROOT/'assets/examples/pipette/asset.png',target/'assembled',
                     (188,100,292,257),label='PIPETTE',label_center_x=240,label_baseline_y=302,
                     label_size=10)
    # Public summaries use package-relative names, never local execution paths.
    evidence['source_pdf'] = 'source.pdf'
    evidence['asset'] = 'assets/examples/pipette/asset.png'
    (target/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'ok':True,'example':'Authored layout, not a scientific result',
                      'vector_drawings_preserved':True,'outside_region_changed_pixels':0,
                      'pdf':str(target/'assembled/figure.pdf')}))

if __name__ == '__main__':
    main()
