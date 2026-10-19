#!/usr/bin/env python3
"""Render the publication review card from its recorded editorial evidence."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw
from build_showcase import font

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    evidence=json.loads(args.review.read_text())
    card=evidence['publication_card']
    image=Image.new('RGB',(1120,640),'#F4F6F5')
    draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((24,24,1096,616),radius=24,outline='#91B2C8',width=3)
    lines=[(60,'LUBAN / PUBLICATION REVIEW',22,'#5F91AF'),
           (115,'Daxuan Scientific Assets',40,'#39454B'),
           (178,'Transparent editable SVG / v'+card['version'],24,'#5C887C'),
           (250,card['score_line'],30,'#39454B'),
           (305,'Editorial estimate; not a scientific or model benchmark.',21,'#69777B'),
           (375,card['validation_line'],25,'#39454B'),
           (430,'Original art / Source records / Real alpha / Reproducible demos',22,'#39454B'),
           (505,card['next_step'],21,'#69777B'),
           (566,'Independent agent acceptance / No human blind-review claim',19,'#69777B')]
    for y,text,size,color in lines:draw.text((58,y),text,font=font(size),fill=color)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    image.save(args.out)
    print(json.dumps({'ok':True,'card':str(args.out),'score_scope':'Editorial estimate from the saved review'}))

if __name__=='__main__':main()
