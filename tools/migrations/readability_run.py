#!/usr/bin/env python3
"""Authorized one-shot native redraw; actual electrical checks precede every Git commit."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from check_native_readability import audit,compare,normalize
NATIVE=ROOT/'hardware/kicad/revB/axu2cgb_expansion'
REVIEW=ROOT/'docs/review/revb-readability'
BUILD=ROOT/'build/readability-stage'
BASELINE=REVIEW/'repair/corrected-baseline.xml'

def run(*args,env=None):
    print('+',' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),check=True,cwd=ROOT,env=env)

def export_xml(path):run('kicad-cli','sch','export','netlist','--format','kicadxml','-o',path,NATIVE/'servohil_io_revB.kicad_sch')

def diagnostics():
    for path in BUILD.glob('*/erc.json'):
        for sheet in json.loads(path.read_text()).get('sheets',[]):
            for violation in sheet.get('violations',[]):
                print('ERC DIAGNOSTIC',path,violation,flush=True)

def main():
    REVIEW.mkdir(parents=True,exist_ok=True);BUILD.mkdir(parents=True,exist_ok=True)
    if not BASELINE.is_file():raise ValueError('reviewed disarm/status baseline is missing')
    stages=(ROOT/'tools/migrations/readability-stage.txt').read_text().split()
    allowed={'scope','positive','input','negative','dac','supervision','status'}
    if not stages or not set(stages)<=allowed:raise ValueError('unrecognized edit stages')
    for stage in stages:
        dst=BUILD/stage;dst.mkdir(parents=True,exist_ok=True)
        export_xml(dst/'before.xml')
        (dst/'audit-before.json').write_text(json.dumps(audit(NATIVE,False),indent=2)+'\n')
        run(sys.executable,'tools/migrations/revb_readability.py','--stage',stage)
        export_xml(dst/'netlist.xml')
        eq=compare(dst/'before.xml',dst/'netlist.xml')
        compare(BASELINE,dst/'netlist.xml')
        print('GRAPH:',json.dumps(eq),flush=True)
        (dst/'equivalence.json').write_text(json.dumps(eq,indent=2)+'\n')
        audit(NATIVE,True)
        normalize(dst/'netlist.xml',dst/'canonical.xml')
        run(sys.executable,'tools/verify_native_all.py',dst/'canonical.xml','--stage','supervision')
        run(sys.executable,'tools/check_revb_netlist.py',dst/'canonical.xml',NATIVE/'expected_connections.json')
        env=dict(os.environ,NATIVE_NETLIST=str(dst/'canonical.xml'))
        run(sys.executable,'-m','unittest','discover','-s','tests','-p','test_native_power_netlist.py','-v',env=env)
        run('kicad-cli','sch','erc','--format','json','--exit-code-violations','-o',dst/'erc.json',NATIVE/'servohil_io_revB.kicad_sch')
        run(sys.executable,'tools/check_revb_erc.py',dst/'erc.json')
        run('kicad-cli','sch','export','pdf','-o',dst/'schematic-review.pdf',NATIVE/'servohil_io_revB.kicad_sch')
        (dst/'audit-after.json').write_text(json.dumps(audit(NATIVE,False),indent=2)+'\n')
        proof=REVIEW/stage;proof.mkdir(parents=True,exist_ok=True)
        for name in ('audit-before.json','audit-after.json','equivalence.json','erc.json'):
            shutil.copyfile(dst/name,proof/name)
        shutil.copyfile(dst/'schematic-review.pdf',REVIEW/'schematic-review.pdf')
        run('git','config','user.name','servoHIL schematic review')
        run('git','config','user.email','59996146+magic-alt@users.noreply.github.com')
        run('git','add',NATIVE,REVIEW)
        run('git','commit','-m',f'fix(schematic): verified {stage} native wiring and label repair')
        run('git','push','origin','HEAD:fix/revb-schematic-wiring-readability')
        sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        (dst/'source_commit.txt').write_text(sha+'\n')
        print('COMMITTED STAGE',stage,sha,flush=True)
    run('git','archive','--format=zip','--output='+str(BUILD/'native-source.zip'),'HEAD','hardware/kicad/revB/axu2cgb_expansion')

if __name__=='__main__':
    try:main()
    finally:
        diagnostics()
        if NATIVE.exists():subprocess.run(['kicad-cli','sch','export','pdf','-o',str(BUILD/'latest-candidate.pdf'),str(NATIVE/'servohil_io_revB.kicad_sch')],cwd=ROOT)
