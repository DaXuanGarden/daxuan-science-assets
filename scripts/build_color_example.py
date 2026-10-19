#!/usr/bin/env python3
"""Reproduce a transparent recolor example with separate reference/target color evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import asset_tool
import palette_context

ROOT = Path(__file__).resolve().parents[1]

def build(outdir):
    outdir = Path(outdir)
    if outdir.exists():
        raise FileExistsError('Choose a fresh output directory: '+str(outdir))
    outdir.mkdir(parents=True)
    reference = ROOT/'assets/examples/chromosome/asset.svg'
    target = ROOT/'assets/examples/methodology-demo/asset.svg'
    palette = json.loads((ROOT/'assets/examples/methodology-demo/palette.json').read_text())
    palette['name'] = 'blue-chromosome-for-methodology-example'
    asset_tool.write_json(outdir/'palette.json', palette)
    for name, path in [('reference',reference),('target',target)]:
        asset_tool.write_json(outdir/(name+'-colors.json'),palette_context.inspect(path))
    asset_tool.write_json(outdir/'rules.json', {
        'source':'Authored demonstration brief; not a user study or a third-party paper',
        'brief':'Recolor the bundled chromosome to match the bundled blue methodology example; preserve all paths, part names and opacity.',
        'locked_colors':{'body':'#91B2C8'},
        'scientific_meaning':'Generic structure only. No gene, disease, effect direction, coordinate or cell identity.'})
    sources = []
    for identifier,scope,file,description in [
        ('reference','reference_author','reference-colors.json','Daxuan bundled gold chromosome as a stand-in reference; no third-party author palette supplied'),
        ('target','target_figure','target-colors.json','Daxuan bundled proposed methodology example, used as the destination color context'),
        ('brief','explicit_user_rules','rules.json','Authored demonstration rule retaining a blue body')]:
        sources.append({'id':identifier,'scope':scope,'access':'source_snapshot','citation':description,
            'snapshot':file,'snapshot_sha256':hashlib.sha256((outdir/file).read_bytes()).hexdigest()})
    assignments = {role:{'hex':color,'basis':'explicit' if role=='body' else 'exact_paint',
        'meaning':'Generic structural or annotation role; no disease or result meaning',
        'source_ids':['brief'] if role=='body' else ['target'],
        'note':'Selected from the destination palette; the gold reference colors do not override the brief. Some roles are reserved.'}
        for role,color in palette['colors'].items()}
    context={'schema_version':'1.0','status':'final','precedence':palette_context.ORDER,
             'sources':sources,'assignments':assignments,'locked_colors':{'body':'#91B2C8'},
             'contrast_pairs':[{'foreground':'text','background':'#FFFFFF','min_ratio':4.5}]}
    asset_tool.write_json(outdir/'color-context.json',context)
    recolor=asset_tool.recolor(reference,outdir/'palette.json',outdir/'asset.svg')
    asset_tool.write_json(outdir/'recolor-qa.json',recolor)
    qa=asset_tool.render(outdir/'asset.svg',outdir/'asset.png',width=540,qa_path=outdir/'qa.json')
    color_qa=palette_context.check(context,outdir,outdir/'palette.json',outdir/'asset.svg')
    asset_tool.write_json(outdir/'color-qa.json',color_qa)
    if not qa['ok'] or not color_qa['ok']:
        raise ValueError('Example checks failed; inspect the saved QA files')
    return {'ok':True,'example':'Authored reference/destination demonstration; not a published biological result',
            'geometry_preserved':recolor['geometry_preserved'],'alpha_verified':qa['png']['ok'],
            'color_context_ok':color_qa['ok'],'model_generation':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir',type=Path,required=True)
    args=parser.parse_args()
    try:
        print(json.dumps(build(args.outdir),indent=2));return 0
    except (OSError,ValueError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)}));return 1
if __name__=='__main__':sys.exit(main())
