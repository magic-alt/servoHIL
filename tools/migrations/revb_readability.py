#!/usr/bin/env python3
"""One-shot native readability edits. Never part of normal schematic generation.

Each stage is graph/ERC checked by the migration workflow before its native
source is committed. Normal development edits the committed KiCad project.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from kicad_sexpr import Atom,parse,items,one,document
DST=ROOT/'hardware/kicad/revB/axu2cgb_expansion'
MARKER=DST/'READABILITY_PROGRESS.json'

def fingerprint(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def scope_labels():
    trees={p:parse(p.read_text()) for p in sorted(DST.glob('*.kicad_sch'))}
    owners=defaultdict(set)
    for path,tree in trees.items():
        for label in items(tree,'global_label')+items(tree,'label'):
            owners[str(label[1])].add(path.name)
    count=0
    for path,tree in trees.items():
        seen=set()
        for label in items(tree,'global_label'):
            name=str(label[1])
            if len(owners[name])<2 or name in seen:
                label[0]=Atom('label')
                label[:]=[v for v in label if not (isinstance(v,list) and v and v[0] in ('shape','property','fields_autoplaced'))]
                count+=1
            else:
                seen.add(name)
        path.write_text(document(tree))
    print('Converted redundant/page-only global labels:',count)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['scope'],required=True)
    args=parser.parse_args()
    progress=json.loads(MARKER.read_text()) if MARKER.exists() else {'baseline':'49cdeb395d31e2844b1f50189508aa9dbf940d40','completed':[],'source_hashes':{}}
    if args.stage in progress['completed']:
        raise ValueError('stage already applied; native edits must not be overwritten')
    for name,digest in progress['source_hashes'].items():
        if fingerprint(DST/name)!=digest: raise ValueError('native sheet edited since previous stage: '+name)
    scope_labels()
    progress['completed'].append(args.stage)
    progress['source_hashes']={p.name:fingerprint(p) for p in sorted(DST.glob('*.kicad_sch'))}
    MARKER.write_text(json.dumps(progress,sort_keys=True,indent=2)+'\n')

if __name__=='__main__':main()
