#!/usr/bin/env python3
"""Prevent accidental revival of the archived dual-FPGA build/layout."""
from pathlib import Path
import json
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE_TREE='6ddd828a8b7ca289a4f2acfee7eb2e1f07569e2e'

def check(root=ROOT):
    for old in ['hardware/fpga/revA','hardware/kicad/revA','docs/icd/j12-hil-link.csv']:
        if (root/old).exists(): raise ValueError('legacy active path must be archived: '+old)
    for pcb in root.rglob('*.kicad_pcb'):
        if 'archive' not in pcb.relative_to(root).parts:
            raise ValueError('PCB layout is not authorized: '+str(pcb))
    bom=(root/'bom/revb-common.csv').read_text()
    if re.search(r'XC7A|FGG484|W25Q128|ADP5054|ADM1186|1V0_FPGA',bom,re.I):
        raise ValueError('second-FPGA support component in active BOM')
    gates=json.loads((root/'hardware/revB/gates.json').read_text())
    if gates['layout_allowed'] is not False: raise ValueError('migration must keep layout disabled')
    if any(v['status']!='SUPERSEDED' for v in gates['legacy'].values()):
        raise ValueError('legacy gates must be SUPERSEDED, never PASS')
    if (root/'.git').exists():
        result=subprocess.check_output(['git','rev-parse','HEAD:archive/revA/snapshot'],cwd=root,text=True).strip()
        if result!=BASE_TREE: raise ValueError('historical snapshot bytes changed')
    else:
        print('Archive Git-tree verification not available outside a checkout')
    print('Rev.B repository guard PASS; historical target is not active')

if __name__=='__main__': check()
