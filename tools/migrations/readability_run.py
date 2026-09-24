#!/usr/bin/env python3
"""Run authorized native edits and commit each part only after real KiCad validation."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from check_native_readability import audit,compare,normalize,graph
NATIVE=ROOT/'hardware/kicad/revB/axu2cgb_expansion'
REVIEW=ROOT/'docs/review/revb-readability'
BUILD=ROOT/'build/readability-stage'


def run(*args,env=None):
    print('+',' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),check=True,cwd=ROOT,env=env)


def export_xml(path):run('kicad-cli','sch','export','netlist','--format','kicadxml','-o',path,NATIVE/'servohil_io_revB.kicad_sch')


def main():
    REVIEW.mkdir(parents=True,exist_ok=True);BUILD.mkdir(parents=True,exist_ok=True)
    stages=(ROOT/'tools/migrations/readability-stage.txt').read_text().split()
    allowed={'repair','scope','positive','input','negative','dac','status'}
    if not stages or not set(stages)<=allowed:raise ValueError('unrecognized edit stages')
    for stage in stages:
        dst=BUILD/stage;dst.mkdir(parents=True,exist_ok=True)
        export_xml(dst/'before.xml')
        (dst/'audit-before.json').write_text(json.dumps(audit(NATIVE,False),indent=2)+'\n')
        if stage=='repair':
            result=subprocess.run([sys.executable,'tools/verify_native_all.py',str(dst/'before.xml'),'--stage','supervision'],cwd=ROOT,text=True,capture_output=True)
            (dst/'baseline-regression.txt').write_text(result.stdout+result.stderr)
            if result.returncode==0 or 'U408.6' not in result.stderr:raise ValueError('baseline disarm regression not reproduced')
            print('RED: baseline U408.6 still connects INPUT_OK instead of HIL_ARM',flush=True)
            run(sys.executable,'tools/migrations/pr17_finalize.py')
        else:
            if stage=='scope':
                try:audit(NATIVE,True)
                except ValueError as error:
                    if 'page-only global' not in str(error):raise
                    print('RED: page-only/repeated global labels reproduced',flush=True)
                else:raise ValueError('scope regression not reproduced')
            run(sys.executable,'tools/migrations/revb_readability.py','--stage',stage)
        export_xml(dst/'netlist.xml')
        if stage!='repair':
            eq=compare(dst/'before.xml',dst/'netlist.xml')
            print('GRAPH:',json.dumps(eq),flush=True)
            (dst/'equivalence.json').write_text(json.dumps(eq,indent=2)+'\n')
            audit(NATIVE,True)
        else:
            a,b=graph(dst/'before.xml'),graph(dst/'netlist.xml')
            delta={'type':'EXPLICIT_INHERITED_SAFETY_REPAIR_NOT_STYLE_EQUIVALENCE',
                   'removed_components':sorted(set(a['components'])-set(b['components'])),
                   'added_components':sorted(set(b['components'])-set(a['components'])),
                   'changed_component_data':[r for r in set(a['components'])&set(b['components']) if a['components'][r]!=b['components'][r]],
                   'required_correction':'U408.6 -> HIL_ARM; replace U409 floating status with host-referenced Q401/Q402 circuit'}
            (dst/'intentional-delta.json').write_text(json.dumps(delta,indent=2)+'\n')
            print('REPAIR DELTA:',json.dumps(delta),flush=True)
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
        for name in ('audit-before.json','audit-after.json','equivalence.json','intentional-delta.json','erc.json','baseline-regression.txt'):
            if (dst/name).is_file():shutil.copyfile(dst/name,proof/name)
        if stage=='repair':shutil.copyfile(dst/'netlist.xml',proof/'corrected-baseline.xml')
        shutil.copyfile(dst/'schematic-review.pdf',REVIEW/'schematic-review.pdf')
        run('git','config','user.name','servoHIL schematic review')
        run('git','config','user.email','59996146+magic-alt@users.noreply.github.com')
        run('git','add',NATIVE,REVIEW)
        run('git','commit','-m',f'fix(schematic): verified {stage} native circuit and label repair')
        run('git','push','origin','HEAD:fix/revb-schematic-wiring-readability')
        sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        (dst/'source_commit.txt').write_text(sha+'\n')
        print('COMMITTED STAGE',stage,sha,flush=True)
    run('git','archive','--format=zip','--output='+str(BUILD/'native-source.zip'),'HEAD','hardware/kicad/revB/axu2cgb_expansion')


if __name__=='__main__':
    try:main()
    finally:
        for path in BUILD.glob('*/erc.json'):
            data=json.loads(path.read_text())
            for sheet in data.get('sheets',[]):
                for violation in sheet.get('violations',[]):
                    print(path,violation.get('type'),violation.get('severity'),violation.get('description'))
                    for item in violation.get('items',[]):print(item.get('description'))
        # Export the failed candidate for diagnosis, but never commit a failed edit.
        if NATIVE.exists():subprocess.run(['kicad-cli','sch','export','pdf','-o',str(BUILD/'latest-candidate.pdf'),str(NATIVE/'servohil_io_revB.kicad_sch')],cwd=ROOT)
