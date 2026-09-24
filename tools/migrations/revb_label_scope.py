"""Scope-only native edit: internal labels local, real cross-page names global, GND symbolic."""
from collections import defaultdict
import copy
import json
from pathlib import Path
import uuid
from kicad_sexpr import Atom,parse,document,dump,items,one,walk,number

NS=uuid.UUID('f3998cb7-f5f5-44a7-8b06-1e3d3fb64c7a')

def apply(directory):
    trees={p:parse(p.read_text()) for p in sorted(directory.glob('*.kicad_sch'))}
    owners=defaultdict(set)
    for path,tree in trees.items():
        for label in items(tree,'global_label')+items(tree,'label'):owners[str(label[1])].add(path.name)
    library=parse(Path('/usr/share/kicad/symbols/power.kicad_sym').read_text())
    ground=copy.deepcopy(next(s for s in items(library,'symbol') if s[1]=='GND'))
    ground[1]='RevB:GND'
    converted=0;grounds=0
    for page_index,(path,tree) in enumerate(trees.items(),1):
        additions=[]
        for label in list(items(tree,'global_label')):
            name=str(label[1])
            if name=='GND':
                at=one(label,'at');x=float(at[1]);y=float(at[2]);reference=f'#PWR{page_index*10000+grounds}'
                old=str(one(label,'uuid')[1])
                def uid(s):return str(uuid.uuid5(NS,path.name+old+s))
                template=next(s for s in items(tree,'symbol') if one(s,'instances') is not None)
                instance_path=copy.deepcopy(next(walk(one(template,'instances'),'path')))
                one(instance_path,'reference')[1]=reference;one(instance_path,'unit')[1]=Atom('1')
                additions.append(parse(f'''(symbol (lib_id "RevB:GND") (at {number(x)} {number(y)} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid "{uid('symbol')}")
(property "Reference" "{reference}" (at {number(x)} {number(y)} 0) (effects (font (size 1 1)) hide))
(property "Value" "GND" (at {number(x)} {number(y+7.62)} 0) (effects (font (size 1 1))))
(property "Footprint" "" (at {number(x)} {number(y)} 0) (effects (font (size 1 1)) hide))
(property "Datasheet" "" (at {number(x)} {number(y)} 0) (effects (font (size 1 1)) hide))
(pin "1" (uuid "{uid('pin')}"))
(instances (project "servohil_io_revB" {dump(instance_path)})))'''))
                tree.remove(label);grounds+=1
            elif len(owners[name])<2:
                label[0]=Atom('label')
                label[:]=[v for v in label if not(isinstance(v,list) and v and v[0] in ('shape','property','fields_autoplaced'))]
                converted+=1
        if additions:
            cache=one(tree,'lib_symbols')
            if not any(s[1]=='RevB:GND' for s in items(cache,'symbol')):cache.append(copy.deepcopy(ground))
            tree.extend(additions)
        path.write_text(document(tree))
    libpath=directory/'revb.kicad_sym';lib=parse(libpath.read_text())
    if not any(s[1]=='GND' for s in items(lib,'symbol')):
        g=copy.deepcopy(ground);g[1]='GND';lib.append(g);libpath.write_text(document(lib))
    print('Page-only globals -> local:',converted,'GND globals -> standard ground:',grounds)
    print('True cross-sheet nets retain global scope. No mixed local/global same-name aliases are introduced.')
