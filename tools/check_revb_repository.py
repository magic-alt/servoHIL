#!/usr/bin/env python3
"""Prevent accidental revival of the archived dual-FPGA build/layout."""
from pathlib import Path
import json
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
# PR18 intentionally repaired the archived native drawings; freeze the exact
# already merged snapshot, not an arbitrary newly generated archive. Original
# snapshot 6ddd828a8b7ca289a4f2acfee7eb2e1f07569e2e remains in Git history.
# Source: main c29abb07e9fca5584235860dbe7f2bd1460141ca, 2026-09-24.
BASE_TREE='052a06c6e6e5b0ce23e94f75774a9f1cc7f3f167'

def check_archive_tree(actual):
    if actual != BASE_TREE:
        raise ValueError('reviewed PR18 archive snapshot bytes changed')

def check(root=ROOT):
    for old in ['hardware/fpga/revA','hardware/kicad/revA','docs/icd/j12-hil-link.csv']:
        if (root/old).exists(): raise ValueError('legacy active path must be archived: '+old)

    gates=json.loads((root/'hardware/revB/gates.json').read_text())
    contract=json.loads((root/'hardware/revB/layout_entry_contract.json').read_text())
    if gates.get('layout_allowed') is not True:
        raise ValueError('Rev.B source closure must authorize PCB Layout entry')
    if gates.get('fabrication_allowed') is not False or gates.get('release_allowed') is not False:
        raise ValueError('Layout entry must not authorize fabrication/release')
    if contract.get('status')!='READY_FOR_PCB_LAYOUT' or contract.get('layout_allowed') is not True:
        raise ValueError('layout-entry contract is not READY_FOR_PCB_LAYOUT')
    if contract.get('fabrication_allowed') is not False:
        raise ValueError('layout-entry contract must keep fabrication blocked')

    for pcb in root.rglob('*.kicad_pcb'):
        rel=pcb.relative_to(root)
        if 'archive' not in rel.parts and not gates.get('layout_allowed'):
            raise ValueError('active PCB layout exists without authorization: '+str(pcb))

    bom=(root/'bom/revb-common.csv').read_text()
    if re.search(r'XC7A|FGG484|W25Q128|ADP5054|ADM1186|1V0_FPGA',bom,re.I):
        raise ValueError('second-FPGA support component in active BOM')
    if any(v['status']!='SUPERSEDED' for v in gates['legacy'].values()):
        raise ValueError('legacy gates must be SUPERSEDED, never PASS')
    if (root/'.git').exists():
        result=subprocess.check_output(['git','rev-parse','HEAD:archive/revA/snapshot'],cwd=root,text=True).strip()
        check_archive_tree(result)
    else:
        print('Archive Git-tree verification not available outside a checkout')
    print('Rev.B repository guard PASS; Layout entry authorized, fabrication/release blocked; reviewed PR18 archive frozen')

if __name__=='__main__': check()
