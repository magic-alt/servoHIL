#!/usr/bin/env python3
"""Final one-shot presentation repair, with actual graph/ERC verification before commit."""
from pathlib import Path
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from kicad_sexpr import Atom,parse,items,one,walk,document,number
from check_native_readability import compare,audit,normalize
NATIVE=ROOT/'hardware/kicad/revB/axu2cgb_expansion'
OUT=ROOT/'build/readability-stage/polish'
REVIEW=ROOT/'docs/review/revb-readability'
PAGES=('10_input_protection','20_positive_rails','30_negative_reference','40_power_supervision','41_power_status','04_dac_0_3','05_dac_4_7')

def run(*args,env=None):
    print('+',' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),check=True,cwd=ROOT,env=env)

def prop(symbol,name):return next(p for p in items(symbol,'property') if p[1]==name)
def hidden(effects):return 'hide' in effects or bool(items(effects,'hide'))

def polish():
    total=0
    for name in PAGES:
        path=NATIVE/(name+'.kicad_sch');tree=parse(path.read_text());definitions={s[1]:s for s in items(one(tree,'lib_symbols'),'symbol')}
        for symbol in items(tree,'symbol'):
            ref=str(prop(symbol,'Reference')[2])
            if ref.startswith(('#','PF','TP')):continue
            value=prop(symbol,'Value');effects=one(value,'effects')
            if not hidden(effects):raise ValueError('already polished or edited: '+ref)
            at=one(symbol,'at');x,y,angle=map(float,at[1:]);definition=definitions[one(symbol,'lib_id')[1]]
            pins=[p for p in walk(definition,'pin') if one(p,'at') is not None]
            if len(pins)==2 and angle in (90,270):vx,vy=x+2.8*2.54,y+0.8*2.54
            elif len(pins)<=2:vx,vy=x,y+2.4*2.54
            else:vx,vy=x,y-min(float(one(p,'at')[2]) for p in pins)+4*2.54
            short=str(value[2]).split(' / ')[0].split(',')[0][:27]
            matches=[]
            for text in items(tree,'text'):
                ta=one(text,'at')
                if str(text[1])==short and abs(float(ta[1])-vx)<0.001 and abs(float(ta[2])-vy)<0.001:matches.append(text)
            if len(matches)!=1:raise ValueError('static value anchor not uniquely found: '+ref)
            label=matches[0]
            value[:]=[value[0],value[1],value[2],copy.deepcopy(one(label,'at')),copy.deepcopy(one(label,'effects'))]
            font=one(one(value,'effects'),'font');size=one(font,'size');size[1:]=[number(0.95),number(0.95)]
            tree.remove(label);total+=1
        # Notes, not electrical objects, move clear of the bottom border/title area.
        for text in items(tree,'text'):
            at=one(text,'at');y=float(at[2])
            if name=='10_input_protection' and y>=266:at[2]=number(y-12.7)
            elif name=='40_power_supervision' and y>=400:at[2]=number(y-10.16)
        path.write_text(document(tree))
    marker=NATIVE/'READABILITY_PROGRESS.json';state=json.loads(marker.read_text())
    state['completed'].append('polish')
    state['source_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(NATIVE.glob('*.kicad_sch'))}
    marker.write_text(json.dumps(state,sort_keys=True,indent=2)+'\n')
    print('Restored live native Value fields without modifying values:',total,flush=True)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    run('kicad-cli','sch','export','netlist','--format','kicadxml','-o',OUT/'before.xml',NATIVE/'servohil_io_revB.kicad_sch')
    red=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_native_readability.py','-v'],cwd=ROOT,text=True,capture_output=True)
    (OUT/'red.txt').write_text(red.stdout+red.stderr)
    if red.returncode==0 or 'Hidden Value' not in red.stderr:raise ValueError('expected native-field regression not reproduced')
    print('RED: hidden Value/static text and bottom-frame margin regressions reproduced',flush=True)
    polish()
    run('kicad-cli','sch','export','netlist','--format','kicadxml','-o',OUT/'netlist.xml',NATIVE/'servohil_io_revB.kicad_sch')
    eq=compare(OUT/'before.xml',OUT/'netlist.xml');compare(REVIEW/'repair/corrected-baseline.xml',OUT/'netlist.xml')
    (OUT/'equivalence.json').write_text(json.dumps(eq,indent=2)+'\n');print(eq,flush=True)
    (OUT/'audit-after.json').write_text(json.dumps(audit(NATIVE),indent=2)+'\n')
    normalize(OUT/'netlist.xml',OUT/'canonical.xml')
    run(sys.executable,'tools/verify_native_all.py',OUT/'canonical.xml','--stage','supervision')
    run(sys.executable,'tools/check_revb_netlist.py',OUT/'canonical.xml',NATIVE/'expected_connections.json')
    env=dict(os.environ,NATIVE_NETLIST=str(OUT/'canonical.xml'))
    run(sys.executable,'-m','unittest','discover','-s','tests','-v',env=env)
    run('kicad-cli','sch','erc','--format','json','--exit-code-violations','-o',OUT/'erc.json',NATIVE/'servohil_io_revB.kicad_sch')
    run(sys.executable,'tools/check_revb_erc.py',OUT/'erc.json')
    run('kicad-cli','sch','export','pdf','-o',OUT/'schematic-review.pdf',NATIVE/'servohil_io_revB.kicad_sch')
    preview=REVIEW/'previews';preview.mkdir(parents=True,exist_ok=True)
    run('pdftoppm','-scale-to','2200','-png',OUT/'schematic-review.pdf',preview/'page')
    run('pdftotext','-bbox',OUT/'schematic-review.pdf',OUT/'text-bounds.xhtml')
    proof=REVIEW/'polish';proof.mkdir(parents=True,exist_ok=True)
    for name in ('equivalence.json','audit-after.json','erc.json'):shutil.copyfile(OUT/name,proof/name)
    shutil.copyfile(OUT/'schematic-review.pdf',REVIEW/'schematic-review.pdf')
    run('git','config','user.name','servoHIL schematic review')
    run('git','config','user.email','59996146+magic-alt@users.noreply.github.com')
    run('git','add',NATIVE,REVIEW)
    run('git','commit','-m','fix(schematic): preserve live value editing and finish native drawing margins')
    run('git','push','origin','HEAD:fix/revb-schematic-wiring-readability')
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    (OUT/'source_commit.txt').write_text(sha+'\n')
    run('git','archive','--format=zip','--output='+str(OUT/'native-source.zip'),'HEAD','hardware/kicad/revB/axu2cgb_expansion')
    print('COMMITTED POLISH',sha,flush=True)

if __name__=='__main__':main()
