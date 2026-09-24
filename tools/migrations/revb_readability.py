#!/usr/bin/env python3
"""One-shot guarded native edits; never run during normal build or schematic generation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
DST=ROOT/'hardware/kicad/revB/axu2cgb_expansion'
MARKER=DST/'READABILITY_PROGRESS.json'

def fingerprint(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['scope','positive','input','negative','dac','supervision','status'],required=True)
    args=parser.parse_args()
    progress=json.loads(MARKER.read_text()) if MARKER.exists() else {'baseline':'49cdeb395d31e2844b1f50189508aa9dbf940d40','completed':[],'source_hashes':{}}
    if args.stage in progress['completed']:raise ValueError('stage already applied; native edits must not be overwritten')
    for name,digest in progress['source_hashes'].items():
        if fingerprint(DST/name)!=digest:raise ValueError('native sheet edited since previous stage: '+name)
    if args.stage=='scope':
        from revb_label_scope import apply
        apply(DST)
    else:
        import revb_wiring,revb_power_wiring,revb_supervision_wiring
        class PageScopedEditor(revb_wiring.Editor):
            def __init__(self,directory,name,title):
                super().__init__(directory,name,title)
                self.seq+=int(name.split('_')[0])*10000
                self.original={r:s for r,s in self.original.items() if not r.startswith('#')}
            def label(self,net,p,side='left'):
                # KiCad correctly warns if the SAME NAME is both local and global.
                # True cross-page signals keep global scope; internal nets are local.
                self.named.discard(net)
                return super().label(net,p,side)
        revb_wiring.Editor=PageScopedEditor
        revb_power_wiring.Editor=PageScopedEditor
        revb_supervision_wiring.Editor=PageScopedEditor
        funcs={'positive':revb_wiring.positive,'input':revb_power_wiring.input_power,
               'negative':revb_power_wiring.negative,'dac':revb_power_wiring.dac,
               'supervision':revb_supervision_wiring.supervision,'status':revb_supervision_wiring.status}
        funcs[args.stage](DST)
    progress['completed'].append(args.stage)
    progress['source_hashes']={p.name:fingerprint(p) for p in sorted(DST.glob('*.kicad_sch'))}
    MARKER.write_text(json.dumps(progress,sort_keys=True,indent=2)+'\n')

if __name__=='__main__':main()
