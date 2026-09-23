#!/usr/bin/env python3
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
proj=root/'hardware/kicad/revA/servohil_io_revA.kicad_pro'
json.loads(proj.read_text(encoding='utf-8'))
files=list((root/'hardware/kicad/revA').glob('*.kicad_sch'))
for p in files:
    s=p.read_text(encoding='utf-8'); depth=0; quoted=False; esc=False
    for ch in s:
        if quoted:
            if esc: esc=False
            elif ch=='\\': esc=True
            elif ch=='"': quoted=False
            continue
        if ch=='"': quoted=True
        elif ch=='(': depth+=1
        elif ch==')': depth-=1
        if depth<0: raise SystemExit(f'unbalanced parentheses: {p}')
    if depth: raise SystemExit(f'unbalanced parentheses: {p}: depth={depth}')
print(f'KiCad scaffold structural check PASS: {len(files)} schematic files')
