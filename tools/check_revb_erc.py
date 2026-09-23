#!/usr/bin/env python3
"""Read native KiCad JSON ERC, fail closed on missing/invalid report."""
import json
import sys
from pathlib import Path

def check(path):
    r=json.loads(Path(path).read_text())
    if not isinstance(r.get('sheets'),list) or not r['sheets']:
        raise ValueError('missing KiCad sheets in ERC JSON')
    v=[x for s in r['sheets'] for x in s.get('violations',[])]
    if any(not isinstance(s.get('violations'),list) for s in r['sheets']):
        raise ValueError('incomplete ERC JSON')
    blocking=[x for x in v if x.get('severity') in ['error','warning']]
    if blocking:
        for x in blocking: print(x)
        raise ValueError(f'ERC has {len(blocking)} errors/warnings')
    return len(r['sheets'])

if __name__=='__main__': print('Native KiCad ERC clean for',check(sys.argv[1]),'sheets; not a hardware release')
