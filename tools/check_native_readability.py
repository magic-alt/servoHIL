#!/usr/bin/env python3
"""Scope audit and actual KiCad pin-partition equivalence, independent of placement."""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from kicad_sexpr import parse,items,one

ROOT=Path(__file__).resolve().parents[1]
NATIVE=ROOT/'hardware/kicad/revB/axu2cgb_expansion'

def audit(directory=NATIVE,strict=True):
    by_net=defaultdict(set);pages={};errors=[];global_names=set();local_names=set();repeated=[]
    trees={p:parse(p.read_text()) for p in sorted(directory.glob('*.kicad_sch'))}
    for path,tree in trees.items():
        globals_=items(tree,'global_label');local=items(tree,'label')
        global_names.update(str(x[1]) for x in globals_);local_names.update(str(x[1]) for x in local)
        pages[path.name]={'global':len(globals_),'local':len(local),'wires':len(items(tree,'wire')),
                         'ground_symbols':sum(one(s,'lib_id',['',''])[1]=='RevB:GND' for s in items(tree,'symbol'))}
        for label in globals_+local:by_net[str(label[1])].add(path.name)
    for path,tree in trees.items():
        counts=defaultdict(int)
        for label in items(tree,'global_label'):
            name=str(label[1]);counts[name]+=1
            if len(by_net[name])<2:errors.append(f'{path.name}: page-only global {name}')
            if name=='GND':errors.append(f'{path.name}: replace GND global text with a power symbol')
        # Multiple instances of a truly cross-sheet net are legal. They are
        # reported for review, not replaced with same-name local aliases (ERC warns).
        repeated.extend({'sheet':path.name,'net':name,'count':count} for name,count in counts.items() if count>1)
    for name in global_names&local_names:errors.append('mixed local/global same-name alias: '+name)
    result={'pages':pages,'global_total':sum(p['global'] for p in pages.values()),
            'local_total':sum(p['local'] for p in pages.values()),
            'repeated_cross_sheet_labels':repeated,'errors':errors}
    if errors and strict:raise ValueError('\n'.join(errors))
    return result

def graph(path):
    root=ET.parse(path).getroot()
    physical={c.attrib['ref']:c for c in root.findall('./components/comp') if not c.attrib['ref'].startswith('#')}
    components={ref:{'value':c.findtext('value',''),'footprint':c.findtext('footprint','')} for ref,c in physical.items()}
    connected=[];seen=set()
    for net in root.findall('./nets/net'):
        pins=[]
        for node in net.findall('node'):
            ref=node.attrib['ref'];pin=node.attrib['pin'];key=ref+'.'+pin
            if ref.startswith('#'):continue
            if key in seen:raise ValueError('duplicate pin in netlist: '+key)
            seen.add(key);pins.append(key)
        if pins:connected.append(sorted(pins))
    return {'components':components,'partition':sorted(connected)}

def compare(before,after):
    a,b=graph(before),graph(after)
    if a['components']!=b['components']:
        changed=[k for k in sorted(set(a['components'])|set(b['components'])) if a['components'].get(k)!=b['components'].get(k)]
        raise ValueError('physical component/value/footprint changed: '+str(changed))
    if a['partition']!=b['partition']:
        aa={tuple(p) for p in a['partition']};bb={tuple(p) for p in b['partition']}
        raise ValueError('electrical partition changed:\nREMOVED '+str(sorted(aa-bb))+'\nADDED '+str(sorted(bb-aa)))
    return {'components':len(a['components']),'nets':len(a['partition']),'pins':sum(len(p) for p in a['partition']),'result':'ELECTRICALLY_EQUIVALENT'}

def normalize(source,target):
    """Validation adapter only: preserve raw XML; reject ambiguous sheet-local basenames."""
    tree=ET.parse(source);seen={}
    for net in tree.getroot().findall('./nets/net'):
        name=net.attrib['name'];short=name.rsplit('/',1)[-1]
        if short in seen and seen[short]!=name:raise ValueError('cannot normalize two distinct nets: '+short)
        seen[short]=name;net.set('name',short)
    tree.write(target,encoding='utf-8',xml_declaration=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,default=NATIVE);p.add_argument('--audit-only',action='store_true')
    p.add_argument('--before',type=Path);p.add_argument('--after',type=Path)
    p.add_argument('--normalize',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.before and a.after:result=compare(a.before,a.after)
    elif a.normalize:
        normalize(a.normalize,a.output);result={'normalized_for_existing_checks':str(a.output)}
    else:result=audit(a.directory,not a.audit_only)
    print(json.dumps(result,indent=2))
