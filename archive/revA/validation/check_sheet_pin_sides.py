#!/usr/bin/env python3
"""Reject sheet pins which KiCad will clamp to a different edge on load.

Sheet-pin angles are NOT library-pin angles: 0=right, 90=top,
180=left, 270=bottom. See KiCad's SCH_IO_KICAD_SEXPR_PARSER.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools'))
from kicad_sexpr import parse, items, one

ROOT = Path(__file__).resolve().parents[1]/'snapshot/hardware/kicad/revA/servohil_io_revA.kicad_sch'

def check(tree):
    errors=[]; total=0
    vertices={tuple(map(float,p[1:3])) for wire in items(tree,'wire') for p in items(one(wire,'pts'),'xy')}
    for sheet in items(tree,'sheet'):
        x,y=map(float,one(sheet,'at')[1:3]);w,h=map(float,one(sheet,'size')[1:3])
        for pin in items(sheet,'pin'):
            total+=1;px,py,angle=map(float,one(pin,'at')[1:4])
            valid={0:abs(px-x-w)<1e-4,90:abs(py-y)<1e-4,180:abs(px-x)<1e-4,270:abs(py-y-h)<1e-4}
            if not valid.get(angle,False):errors.append(f'{pin[1]}: angle {angle} selects a different sheet edge')
            if not x-1e-4<=px<=x+w+1e-4 or not y-1e-4<=py<=y+h+1e-4:errors.append(f'{pin[1]}: pin outside sheet')
            if (px,py) not in vertices:errors.append(f'{pin[1]}: sheet pin is not an explicit wire vertex')
    return {'pins':total,'result':'FAIL' if errors else 'PASS','errors':errors}

if __name__=='__main__':
    result=check(parse(ROOT.read_text()))
    print(json.dumps(result,indent=2))
    sys.exit(bool(result['errors']))
