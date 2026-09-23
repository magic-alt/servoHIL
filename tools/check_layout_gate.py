#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
gate=root/'hardware/kicad/revA/layout_gate.yaml'
text=gate.read_text(encoding='utf-8')
allowed=any(line.strip()=='layout_allowed: true' for line in text.splitlines())
pcbs=list((root/'hardware/kicad/revA').glob('*.kicad_pcb'))
if pcbs and not allowed:
    print('ERROR: Rev.A PCB layout exists while layout_allowed is false:')
    for p in pcbs: print(' -', p.relative_to(root))
    sys.exit(1)
print('Rev.A layout gate OK; layout_allowed=', allowed, 'pcb_files=', len(pcbs))
