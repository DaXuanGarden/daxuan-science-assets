#!/usr/bin/env python3
"""Inspect reference colors and check an asset against its recorded color context."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import asset_tool

SCOPES = {'reference_author', 'manuscript', 'target_figure', 'explicit_user_rules'}
ORDER = ['explicit_user_rules', 'target_figure', 'manuscript', 'reference_author']
HEX = re.compile(r'#[0-9a-fA-F]{6}\Z')

def normalize_paint(value):
    value = value.strip().lower()
    if re.fullmatch(r'#[0-9a-f]{3}', value):
        return '#' + ''.join(c*2 for c in value[1:]).upper()
    if HEX.fullmatch(value):
        return value.upper()
    if value in {'white', 'black'}:
        return {'white': '#FFFFFF', 'black': '#000000'}[value]
    match = re.fullmatch(r'rgb\(\s*([^)]*)\)', value)
    if match:
        parts = [s.strip() for s in match[1].split(',')]
        if len(parts) == 3:
            try:
                nums = [float(s[:-1])*2.55 if s.endswith('%') else float(s) for s in parts]
                if all(math.isfinite(n) and 0 <= n <= 255.00001 for n in nums):
                    return '#' + ''.join(f'{min(255,round(n)):02X}' for n in nums)
            except ValueError:
                pass
    return None

def is_neutral(color):
    rgb = [int(color[i:i+2], 16) for i in (1,3,5)]
    return max(rgb)-min(rgb) < 12

def inspect(path, count=16, crop=None):
    path = Path(path)
    if not 2 <= count <= 32:
        raise ValueError('colors must be between 2 and 32')
    if path.suffix.lower() == '.svg':
        if crop:
            raise ValueError('crop is available for raster inputs; SVG inspection reads literal paints')
        root = asset_tool.parse_svg(path)
        values = Counter()
        for node in root.iter():
            paints = {k:node.get(k) for k in ('fill','stroke','stop-color') if node.get(k)}
            for key,value in re.findall(r'(?:^|;)\s*(fill|stroke|stop-color)\s*:\s*([^;]+)', node.get('style','')):
                paints[key] = value
            for value in paints.values():
                color = normalize_paint(value)
                if color:
                    values[color] += 1
        mode = 'literal_svg_paints'
        scope = 'Counts of explicit fill/stroke/stop-color paints, including inline styles; not rendered area, computed styles, or color meaning.'
    else:
        from PIL import Image
        image = Image.open(path).convert('RGBA')
        if crop:
            x,y,w,h = crop
            if min(x,y) < 0 or min(w,h) <= 0 or x+w > image.width or y+h > image.height:
                raise ValueError('crop must be inside the image with positive dimensions')
            image = image.crop((x,y,x+w,y+h))
        image.thumbnail((1200,1200))
        pixels = [p[:3] for p in image.getdata() if p[3] >= 250 and not min(p[:3]) >= 246]
        values = Counter()
        if pixels:
            # Quantization groups raster/antialias colors; it never establishes an author's exact hex values.
            strip = Image.new('RGB',(len(pixels),1));strip.putdata(pixels)
            quant = strip.quantize(colors=count)
            palette = quant.getpalette()
            for index,frequency in Counter(quant.getdata()).items():
                rgb = palette[index*3:index*3+3]
                values['#'+''.join(f'{n:02X}' for n in rgb)] += frequency
        mode = 'approximate_raster_samples'
        scope = 'Quantized opaque non-white pixels after optional crop and thumbnail; approximate appearance, not exact source paints or color meaning.'
    total = sum(values.values())
    chromatic = [(c,n) for c,n in values.most_common() if not is_neutral(c)][:count]
    neutral = [(c,n) for c,n in values.most_common() if is_neutral(c)][:count]
    records = lambda items: [{'hex':c,'count':n,'share_of_counted':round(n/total,6) if total else 0} for c,n in items]
    return {'ok':True,'source_name':path.name,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'mode':mode,'crop_xywh':list(crop) if crop else None,'chromatic_colors':records(chromatic),
            'neutral_colors':records(neutral),'scope':scope}

def contrast(a,b):
    def luminance(color):
        rgb = [int(color[i:i+2],16)/255 for i in (1,3,5)]
        linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
        return sum(v*w for v,w in zip(linear,[.2126,.7152,.0722]))
    x,y = sorted([luminance(a),luminance(b)])
    return (y+.05)/(x+.05)

def check(context, root, palette, svg=None):
    errors, warnings = [], []
    colors = {k:v.upper() for k,v in asset_tool.load_palette(palette).items()}
    if context.get('schema_version') != '1.0' or context.get('status') not in {'draft','final'}:
        errors.append('Expected schema_version 1.0 and draft/final status')
    if context.get('precedence') != ORDER:
        errors.append('Record precedence as explicit user rules, target figure, manuscript, reference author')
    source_ids, scopes = set(), set()
    source_list = context.get('sources', [])
    if not isinstance(source_list,list) or not source_list:
        errors.append('sources must be a nonempty list')
        source_list = []
    for source in source_list:
        if not isinstance(source,dict):
            errors.append('Source entries must be objects');continue
        identifier = source.get('id')
        if not isinstance(identifier,str) or not identifier or identifier in source_ids:
            errors.append('Source IDs must be nonempty and unique')
        else:source_ids.add(identifier)
        if source.get('scope') not in SCOPES:
            errors.append(str(identifier)+': unknown source scope')
        else:scopes.add(source['scope'])
        if source.get('access') == 'unavailable':
            if not source.get('note'):
                errors.append(str(identifier)+': unavailable sources need an honest note')
            warnings.append(str(identifier)+': source not available; no extraction claim')
            continue
        if source.get('access') not in {'inspected_vector','inspected_raster','author_report','source_snapshot','user_statement'}:
            errors.append(str(identifier)+': record how the source was inspected');continue
        try:
            rel = Path(source.get('snapshot',''))
            selected = (Path(root)/rel).resolve()
            if not str(rel) or str(rel)=='.' or rel.is_absolute() or not selected.is_relative_to(Path(root).resolve()):
                raise ValueError('snapshot must be a local relative file within the context root')
            if not selected.is_file() or selected.stat().st_size > 25_000_000:
                raise ValueError('snapshot missing or exceeds 25 MB')
            if hashlib.sha256(selected.read_bytes()).hexdigest() != source.get('snapshot_sha256'):
                raise ValueError('snapshot hash differs')
        except (OSError,TypeError,ValueError) as exc:
            errors.append(str(identifier)+': '+str(exc))
    for required in ('reference_author','target_figure'):
        if required not in scopes:
            errors.append('Record '+required+' as inspected or explicitly unavailable')
    assignments = context.get('assignments',{})
    if not isinstance(assignments,dict):
        errors.append('assignments must be an object');assignments={}
    for role,hex_value in colors.items():
        decision = assignments.get(role)
        if not isinstance(decision,dict):
            errors.append(role+': missing recorded color decision');continue
        if decision.get('hex','').upper() != hex_value:
            errors.append(role+': palette differs from the recorded decision')
        if decision.get('basis') not in {'explicit','exact_paint','approximate_sample','derived','preserved'}:
            errors.append(role+': unknown basis')
        evidence = decision.get('source_ids')
        if not isinstance(evidence,list) or not evidence or any(s not in source_ids for s in evidence):
            errors.append(role+': source_ids must resolve to recorded sources')
        elif any(s in {v.get('id') for v in source_list if isinstance(v,dict) and v.get('access')=='unavailable'} for s in evidence):
            errors.append(role+': unavailable source cannot support a color assignment')
        if not decision.get('meaning'):
            errors.append(role+': state the color meaning')
    locks = context.get('locked_colors',{})
    if not isinstance(locks,dict):
        errors.append('locked_colors must be an object');locks={}
    for role,color in locks.items():
        if not isinstance(color,str) or not HEX.fullmatch(color) or colors.get(role)!=color.upper():
            errors.append(str(role)+': explicit locked color changed')
    for scale in context.get('score_scales',[]):
        roles = scale.get('roles',[])
        if (not isinstance(roles,list) or len(roles)<2 or len(set(roles))!=len(roles)
            or any(role not in colors for role in roles) or scale.get('direction')!='low_to_high' or not scale.get('meaning')):
            errors.append('Score scale requires unique known roles, low_to_high order, and a meaning')
        elif len({colors[r] for r in roles})<2:
            errors.append('Score scale has no visible color range')
    contrast_results=[]
    for pair in context.get('contrast_pairs',[]):
        a = colors.get(pair.get('foreground'))
        b = colors.get(pair.get('background'),pair.get('background',''))
        minimum = pair.get('min_ratio',4.5)
        if not a or not isinstance(b,str) or not HEX.fullmatch(b) or not isinstance(minimum,(int,float)) or not math.isfinite(minimum) or minimum<1:
            errors.append('Contrast pair must resolve to explicit colors and a finite ratio');continue
        ratio = contrast(a,b)
        contrast_results.append({'foreground':pair['foreground'],'background':pair['background'],'ratio':round(ratio,2),'minimum':minimum})
        if ratio < minimum:errors.append('Insufficient declared contrast for '+pair['foreground'])
    bindings=0
    if svg:
        tree = asset_tool.parse_svg(svg)
        for node in tree.iter():
            for role_attr,paint_attr in asset_tool.ROLE_ATTRS.items():
                role = node.get(role_attr)
                if role:
                    bindings+=1
                    if role not in colors or normalize_paint(node.get(paint_attr,''))!=colors.get(role):
                        errors.append(str(role)+': SVG paint differs from palette')
            styles = dict(re.findall(r'(?:^|;)\s*(fill|stroke|stop-color)\s*:\s*([^;]+)',node.get('style','')))
            for role_attr,paint_attr in asset_tool.ROLE_ATTRS.items():
                if node.get(role_attr) and paint_attr in styles and normalize_paint(styles[paint_attr])!=colors.get(node.get(role_attr)):
                    errors.append('Inline style overrides '+node.get(role_attr))
        if not bindings:errors.append('No tagged SVG paints were checked')
    return {'ok':not errors,'errors':sorted(set(errors)),'warnings':warnings,'source_scopes':sorted(scopes),
            'roles_checked':len(colors),'svg_bindings_checked':bindings,'contrast':contrast_results,
            'scope':'Source-snapshot integrity, declared color decisions/locks, palette paints and numerical contrast only. Does not establish source authorship, scientific color meaning, perceptual harmony, monotonic score perception, or placement quality.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    inspect_cmd=sub.add_parser('inspect');inspect_cmd.add_argument('source',type=Path)
    inspect_cmd.add_argument('--colors',type=int,default=16);inspect_cmd.add_argument('--crop',nargs=4,type=int)
    check_cmd=sub.add_parser('check');check_cmd.add_argument('context',type=Path)
    check_cmd.add_argument('--root',type=Path,required=True);check_cmd.add_argument('--palette',type=Path,required=True)
    check_cmd.add_argument('--svg',type=Path)
    for command in (inspect_cmd,check_cmd):
        command.add_argument('--out',type=Path);command.add_argument('--force',action='store_true')
    args=parser.parse_args()
    try:
        result=inspect(args.source,args.colors,args.crop) if args.command=='inspect' else check(json.loads(args.context.read_text()),args.root,args.palette,args.svg)
        if args.out:asset_tool.write_json(args.out,result,args.force)
        print(json.dumps(result,indent=2));return 0 if result['ok'] else 1
    except (OSError,ValueError,TypeError,KeyError,ImportError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)}));return 2
if __name__=='__main__':sys.exit(main())
