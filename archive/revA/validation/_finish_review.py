#!/usr/bin/env python3
"""One-shot reviewed geometry/library reconciliation; no electrical redesign."""
from __future__ import annotations
import argparse
import copy
from pathlib import Path
from _migrate_interfaces import NATIVE, spans
from _apply_digital_drawing import pretty, put, props, mm
from kicad_sexpr import parse, items, one, walk, expr, Atom

def save(path, tree):
    # Retain byte-for-byte all top-level records that did not change.
    before=path.read_text();old=parse(before);assert len(old)==len(tree)
    edits=[]
    for (a,b),o,n in zip(spans(before),old[1:],tree[1:]):
        if o!=n:edits.append((a,b,pretty(n)))
    for a,b,text in reversed(edits):before=before[:a]+text+before[b:]
    path.write_text(before)

def at(node,x,y):
    old=one(node,'at');old[1]=Atom(str(round(x,4)));old[2]=Atom(str(round(y,4)))

def run(power_library=None):
    root=NATIVE/'servohil_io_revA.kicad_sch';t=parse(root.read_text())
    for s in items(t,'sheet'):
        x,y=map(float,one(s,'at')[1:3])
        for pin in items(s,'pin'):
            angle=int(one(pin,'at')[3]);effect=one(pin,'effects')
            put(effect,'justify',expr('(justify '+('right' if angle==0 else 'left')+')'))
        if props(s)['Sheetfile'][2]=='07_dac_4_7.kicad_sch':
            one(s,'size')[2]=Atom(str(mm(52)))
            at(props(s)['Sheetfile'],x,mm(197))
    for label in items(t,'label'):
        lx,ly=map(float,one(label,'at')[1:3])
        for s in items(t,'sheet'):
            for pin in items(s,'pin'):
                px,py,angle=map(float,one(pin,'at')[1:4])
                if angle==0 and abs(lx-px-mm(1))<1e-4 and abs(ly-py)<1e-4:
                    before=(round(px+mm(5),4),py);after=(round(px+mm(12),4),py)
                    for wire in items(t,'wire'):
                        for xy in items(one(wire,'pts'),'xy'):
                            if tuple(map(float,xy[1:3]))==before:xy[1]=Atom(str(after[0]));xy[2]=Atom(str(after[1]))
                    at(label,*after);one(label,'at')[3]=Atom('180')
                    put(one(label,'effects'),'justify',expr('(justify right bottom)'))
    for n in items(t,'text'):
        if float(one(n,'at')[2])<mm(12):one(n,'at')[2]=Atom(str(mm(12)))
    save(root,t)
    p=NATIVE/'05_io_fpga.kicad_sch';t=parse(p.read_text())
    symbols={props(s)['Reference'][2]:s for s in items(t,'symbol')}
    for key,y in [('Reference',77),('Value',81)]:at(props(symbols['U10'])[key],mm(150),mm(y))
    for reference,y in [('R230',178),('R231',184)]:
        at(props(symbols[reference])['Reference'],mm(92),mm(y-2))
        at(props(symbols[reference])['Value'],mm(92),mm(y+2))
    pvalue=props(symbols['R234'])['Value'];at(pvalue,mm(298),mm(178))
    put(pvalue,'effects',expr('(effects (font (size 1.016 1.016)))'))
    for n in items(t,'text'):
        if float(one(n,'at')[2])<mm(12):one(n,'at')[2]=Atom(str(mm(12)))
    for n in items(t,'label'):
        if n[1]=='3V3_D' and abs(float(one(n,'at')[2])-mm(175))<1e-4:
            put(one(n,'effects'),'justify',expr('(justify left top)'))
    save(p,t)
    p=NATIVE/'03_digital_power.kicad_sch';t=parse(p.read_text())
    for n in items(t,'hierarchical_label'):
        if n[1] in ('12V_PROT','EFUSE_PG'):
            old=tuple(map(float,one(n,'at')[1:3]));new=(mm(20),old[1]);at(n,*new)
            for wire in items(t,'wire'):
                for xy in items(one(wire,'pts'),'xy'):
                    if tuple(map(float,xy[1:3]))==old:xy[1]=Atom(str(new[0]))
    save(p,t)
    changes={'01_power_entry.kicad_sch':{(230.0,80.01):(229.87,80.01)},
             '02_analog_power.kicad_sch':{(244.0,119.38):(243.84,119.38),(249.0,110.49):(248.92,110.49),(249.0,66.04):(248.92,66.04)}}
    for filename,mapping in changes.items():
        p=NATIVE/filename;t=parse(p.read_text())
        for n in t[1:]:
            if n[0] not in ('wire','junction','label','hierarchical_label'):continue
            for child in list(walk(n,'at')) + list(walk(n,'xy')):
                old=tuple(map(float,child[1:3]))
                if old in mapping:child[1:3]=[Atom(str(v)) for v in mapping[old]]
        save(p,t)
    sig=lambda d:sorted((one(pin,'number')[1],one(pin,'name')[1],pin[1],pin[2]) for pin in walk(d,'pin'))
    for filename,name,library in [('04_axu_hil_link.kicad_sch','ServoHILCore:J12_40','servohil_core.kicad_sym'),
                                   ('06_dac_0_3.kicad_sch','ServoHILCore:AD3542R','servohil_core.kicad_sym'),
                                   ('02_analog_power.kicad_sch','ServoHIL:LTC7149','servohil_power.kicad_sym')]:
        source=next(d for d in items(one(parse((NATIVE/filename).read_text()),'lib_symbols'),'symbol') if d[1]==name)
        path=NATIVE/library;t=parse(path.read_text());dest=next(d for d in items(t,'symbol') if d[1]==name.split(':')[-1])
        assert sig(source)==sig(dest),'Electrical pin signature differs: '+name
        replacement=copy.deepcopy(source);replacement[1]=dest[1];t[t.index(dest)]=replacement;save(path,t)
    if power_library:
        canonical=next(s for s in items(parse(Path(power_library).read_text()),'symbol') if s[1]=='GND')
        for path in NATIVE.glob('*.kicad_sch'):
            t=parse(path.read_text());lib=one(t,'lib_symbols')
            for d in items(lib,'symbol'):
                if d[1]!='power:GND':continue
                assert sig(d)==sig(canonical),'Unexpected standard ground pin signature'
                oldpin=next(walk(d,'pin'));newpin=next(walk(canonical,'pin'))
                assert one(oldpin,'at')==one(newpin,'at') and one(oldpin,'length')==one(newpin,'length')
                replacement=copy.deepcopy(canonical);replacement[1]='power:GND';lib[lib.index(d)]=replacement
            save(path,t)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--power-library');run(ap.parse_args().power_library)
