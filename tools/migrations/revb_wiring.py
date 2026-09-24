"""Guarded one-time native drawing edits; preserves actual instances and electrical data.

Coordinates below use a 100 mil unit (2.54 mm). No electrical component is
invented or regenerated; original instances, values, pin identities, footprints
and UUIDs are reused. Exported KiCad pin partitions must remain identical.
"""
from __future__ import annotations
from collections import defaultdict
import copy
import json
import math
from pathlib import Path
import uuid
from kicad_sexpr import Atom,parse,dump,document,items,one,walk,number

NS=uuid.UUID('56b21598-8184-4b2e-a6ba-96f89f6ef998')
G=2.54

def prop(node,name):
    return next(p for p in items(node,'property') if p[1]==name)

def coord(p): return tuple(round(float(x)/G,6) for x in p)

def standard_ground():
    lib=parse(Path('/usr/share/kicad/symbols/power.kicad_sym').read_text())
    return copy.deepcopy(next(s for s in items(lib,'symbol') if s[1]=='GND'))

class Editor:
    def __init__(self,directory,name,title):
        self.directory=directory;self.path=directory/(name+'.kicad_sch');self.name=name
        self.tree=parse(self.path.read_text());self.seq=0;self.elements=[];self.placed={};self.lines=[];self.connected=set();self.named=set()
        self.lib=one(self.tree,'lib_symbols')
        self.defs={str(s[1]):s for s in items(self.lib,'symbol')}
        self.original={str(prop(s,'Reference')[2]):s for s in items(self.tree,'symbol')}
        self.expected=json.loads((directory/'expected_connections.json').read_text())
        owners=defaultdict(set)
        for path in directory.glob('*.kicad_sch'):
            t=parse(path.read_text())
            for label in items(t,'global_label')+items(t,'label'): owners[str(label[1])].add(path.name)
        self.cross={n for n,pages in owners.items() if len(pages)>1}
        self.ground=standard_ground();self.ground[1]='RevB:GND'
        if 'RevB:GND' not in self.defs:
            self.lib.append(self.ground);self.defs['RevB:GND']=self.ground
        self.path_instance=None
        for s in self.original.values():
            instances=one(s,'instances')
            if instances is not None:
                self.path_instance=copy.deepcopy(next(walk(instances,'path')))
                break
        if self.path_instance is None:raise ValueError('native instance path is missing')
        self.note(title,8,8,1.6)

    def uid(self):
        self.seq+=1;return str(uuid.uuid5(NS,self.name+':'+str(self.seq)))

    def definition(self,ref): return self.defs[str(one(self.original[ref],'lib_id')[1])]

    def pins(self,ref):
        result={}
        for pin in walk(self.definition(ref),'pin'):
            a=one(pin,'at');num=one(pin,'number')
            if a is not None and num is not None:result[str(num[1])]=(float(a[1])/G,float(a[2])/G)
        return result

    def place(self,ref,x,y,angle=0):
        if ref in self.placed:raise ValueError('duplicate placement '+ref)
        source=copy.deepcopy(self.original[ref]);at=one(source,'at');at[1:]=[number(x*G),number(y*G),number(angle)]
        source[:]=[v for v in source if not(isinstance(v,list) and v and v[0]=='mirror')]
        self.placed[ref]=(source,x,y,angle)
        pins=self.pins(ref);two=len(pins)==2;single=len(pins)==1
        for name in ('Reference','Value'):
            p=prop(source,name);a=one(p,'at');a[3]=number(0)
            effects=one(p,'effects');font=one(effects,'font');size=one(font,'size');size[1:]=[number(1.0),number(1.0)]
            effects[:]=[v for v in effects if not(isinstance(v,list) and v and v[0]=='justify') and v!='hide']
            if name=='Value':effects.append(Atom('hide'))
        r=prop(source,'Reference');a=one(r,'at')
        if two and angle in (90,270):
            a[1:3]=[number((x+2.8)*G),number((y-0.8)*G)];one(r,'effects').append([Atom('justify'),Atom('left')])
            vx,vy=x+2.8,y+0.8;justify='left'
        elif two or single:
            a[1:3]=[number(x*G),number((y-2.4)*G)]
            vx,vy=x,y+2.4;justify=None
        else:
            top=max(py for px,py in pins.values())
            bottom=min(py for px,py in pins.values())
            a[1:3]=[number(x*G),number((y-top-4)*G)]
            vx,vy=x,y-bottom+4;justify=None
        value=str(prop(source,'Value')[2]);short=value.split(' / ')[0].split(',')[0]
        if len(short)>27:short=short[:27]
        if not single:self.note(short,vx,vy,1.0,justify)
        self.elements.append(source)
        # Preserve true NC pins without silently terminating a functional pin.
        for pin in pins:
            if ref+'.'+pin not in self.expected:
                self.elements.append(parse(f'(no_connect (at {self.mm(self.pt(ref,pin))}) (uuid "{self.uid()}"))'))
        return ref

    def anchor(self,ref,pin,x,y,angle=0):
        px,py=self.pins(ref)[str(pin)];t=math.radians(angle)
        dx=px*math.cos(t)+py*math.sin(t);dy=-px*math.sin(t)+py*math.cos(t)
        return self.place(ref,x-dx,y-dy,angle)

    def pt(self,ref,pin):
        _,x,y,angle=self.placed[ref];px,py=self.pins(ref)[str(pin)];t=math.radians(angle)
        return (round(x+px*math.cos(t)+py*math.sin(t),6),round(y-px*math.sin(t)-py*math.cos(t),6))

    def net(self,ref,pin):return self.expected[ref+'.'+str(pin)]
    def mm(self,p):return f'{number(p[0]*G)} {number(p[1]*G)}'

    def wire(self,net,*points):
        pts=[self.pt(*p.split('.')) if isinstance(p,str) else p for p in points]
        for a,b in zip(pts,pts[1:]):
            if a==b:continue
            if a[0]!=b[0] and a[1]!=b[1]:raise ValueError(f'nonorthogonal route {net}: {a}->{b}')
            self.lines.append((net,a,b))
            self.elements.append(parse(f'(wire (pts (xy {self.mm(a)}) (xy {self.mm(b)})) (stroke (width 0) (type default)) (uuid "{self.uid()}"))'))

    def label(self,net,p,side='left'):
        glob=net in self.cross and net not in self.named
        self.named.add(net)
        tag='global_label' if glob else 'label'
        shape='(shape bidirectional)' if glob else ''
        angle=0 if side=='left' else 180
        self.elements.append(parse(f'({tag} {json.dumps(net)} {shape} (at {self.mm(p)} {angle}) (effects (font (size 1 1)) (justify {side})) (uuid "{self.uid()}"))'))

    def terminal(self,ref,pin,dx=-3):
        p=self.pt(ref,pin);q=(p[0]+dx,p[1]);net=self.net(ref,pin)
        self.wire(net,p,q);self.label(net,q,'left' if dx>0 else 'right')

    def ground_at(self,p):
        ref='#PWR'+str(50000+self.seq)
        path=copy.deepcopy(self.path_instance)
        one(path,'reference')[1]=ref;one(path,'unit')[1]=Atom('1')
        source=parse(f'''(symbol (lib_id "RevB:GND") (at {self.mm(p)} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid "{self.uid()}")
(property "Reference" "{ref}" (at {self.mm(p)} 0) (effects (font (size 1 1)) hide))
(property "Value" "GND" (at {self.mm((p[0],p[1]+3))} 0) (effects (font (size 1 1))))
(property "Footprint" "" (at {self.mm(p)} 0) (effects (font (size 1 1)) hide))
(property "Datasheet" "" (at {self.mm(p)} 0) (effects (font (size 1 1)) hide))
(pin "1" (uuid "{self.uid()}"))
(instances (project "servohil_io_revB" {dump(path)})))''')
        self.elements.append(source)

    def gnd(self,ref,pin,dy=2):
        if self.net(ref,pin)!='GND':raise ValueError('ground applied to non-ground pin '+ref+'.'+str(pin))
        p=self.pt(ref,pin);q=(p[0],p[1]+dy);self.wire('GND',p,q);self.ground_at(q)

    def note(self,text,x,y,size=1.27,justify='left'):
        j=f'(justify {justify})' if justify else ''
        self.elements.append(parse(f'(text {json.dumps(text)} (at {self.mm((x,y))} 0) (effects (font (size {size} {size})) {j}) (uuid "{self.uid()}"))'))

    def bus(self,net,y,refs,x1=None,x2=None,label=True):
        pts=[self.pt(*p.split('.')) for p in refs]
        left=min(p[0] for p in pts) if x1 is None else x1
        right=max(p[0] for p in pts) if x2 is None else x2
        self.wire(net,(left,y),(right,y))
        for p in pts:self.wire(net,p,(p[0],y))
        if label:self.label(net,(right,y))

    def finish(self):
        missing=set(self.original)-set(self.placed)
        if missing:raise ValueError('unplaced native components: '+str(sorted(missing)))
        # Junctions only connect identical nets. Crossings on other nets are not joined.
        junctions=set()
        for net,a,b in self.lines:
            for other,c,e in self.lines:
                if other!=net:continue
                for p in (a,b):
                    if p in (c,e):continue
                    if (c[0]==e[0]==p[0] and min(c[1],e[1])<p[1]<max(c[1],e[1])) or (c[1]==e[1]==p[1] and min(c[0],e[0])<p[0]<max(c[0],e[0])):
                        junctions.add(p)
        for p in sorted(junctions):self.elements.append(parse(f'(junction (at {self.mm(p)}) (diameter 0) (color 0 0 0 0) (uuid "{self.uid()}"))'))
        remove={'wire','global_label','label','no_connect','junction','text','symbol'}
        self.tree[:]=[v for v in self.tree if not(isinstance(v,list) and v and v[0] in remove)]
        one(self.tree,'generator')[1]=Atom('servohil_native_readability')
        self.tree.extend(self.elements)
        self.path.write_text(document(self.tree))
        libfile=self.directory/'revb.kicad_sym';library=parse(libfile.read_text())
        if not any(s[1]=='GND' for s in items(library,'symbol')):
            g=copy.deepcopy(self.ground);g[1]='GND';library.append(g)
            libfile.write_text(document(library))


def positive(directory):
    d=Editor(directory,'20_positive_rails','POSITIVE RAILS - direct power path, local feedback, cross-sheet interfaces only')
    for index,offset,rail in [(201,0,'6V2_PRE'),(202,76,'3V3_D'),(203,152,'1V8_D')]:
        def p(x,y):return (x+offset,y)
        def put(ref,x,y,a=0):return d.place(ref,x+offset,y,a)
        base=210+(index-201)*10;u=f'U{index}'
        d.note(f'{rail} / AP63201, 500 kHz',offset+9,16,1.5)
        put(u,30,30);put(f'L{index}',48,30)
        put(f'C{base}',44,23)
        put(f'C{base+1}',12,30,270);put(f'C{base+2}',18,30,270)
        put(f'C{base+3}',58,33,270);put(f'C{base+4}',66,33,270)
        put(f'R{base}',52,40,270);put(f'R{base+1}',52,50,270)
        put(f'R{base+2}',72,43,270)
        d.anchor(f'PF{index}',1,*p(64,21));d.anchor(f'TP{index}',1,*p(73,30))
        d.bus('VIN_PROT',24,[u+'.3',f'C{base+1}.1',f'C{base+2}.1'],offset+8,offset+22)
        d.terminal(u,2,-3)
        d.gnd(u,4)
        for ref in [f'C{base+1}',f'C{base+2}',f'C{base+3}',f'C{base+4}',f'R{base+1}',f'R{base+2}']:d.gnd(ref,2)
        d.wire(f'SW_{index}',u+'.5',f'L{index}.1')
        d.wire(f'BST_{index}',u+'.6',p(40,28),p(40,23),f'C{base}.1')
        d.label(f'BST_{index}',p(40,23))
        d.wire(f'SW_{index}',f'C{base}.2',p(46,26),p(43,26),p(43,30))
        d.label(f'SW_{index}',p(43,30))
        d.bus(rail,30,[f'L{index}.2',f'C{base+3}.1',f'C{base+4}.1',f'R{base}.1',f'R{base+2}.1',f'TP{index}.1'],offset+50,offset+73)
        d.wire(rail,f'PF{index}.1',p(64,30))
        d.wire(f'FB_{index}',f'R{base}.2',p(52,45),f'R{base+1}.1')
        d.wire(f'FB_{index}',u+'.1',p(40,32),p(40,45),p(52,45))
        d.label(f'FB_{index}',p(44,45))
        if index==201:
            put('R201',19,40,270)
            d.wire('INPUT_OK',u+'.2',p(19,30),'R201.1');d.gnd('R201',2)
        d.note('Cout effective capacitance >=20 uF; values/ratings unchanged.',offset+8,59,1.0)
    for index,offset,rail,pg in [(211,0,'+5V0_DAC','PG_5V0'),(212,116,'+5V2_PVDD','PG_PVDD')]:
        oy=76
        def p(x,y):return (x+offset,y+oy)
        def put(ref,x,y,a=0):return d.place(ref,x+offset,y+oy,a)
        base=240+(index-211)*20;u=f'U{index}'
        d.note(f'{rail} / LT3045 low-noise post-regulator',offset+10,oy+13,1.5)
        put(u,35,30)
        put(f'C{base+1}',14,27,270);put(f'C{base+2}',21,27,270)
        put(f'C{base+3}',59,28,270);put(f'C{base+4}',68,28,270)
        put(f'R{base}',50,38,270);put(f'C{base}',59,38,270)
        put(f'R{base+1}',20,38,270)
        put(f'R{base+2}',79,35,270);put(f'R{base+3}',79,47,270)
        put(f'R{base+4}',97,37,270)
        d.anchor(f'TP{index}',1,*p(87,24))
        d.bus('6V2_PRE',oy+22,[f'C{base+1}.1',f'C{base+2}.1'],offset+10,offset+23)
        d.wire('6V2_PRE',p(23,22),p(23,28))
        for pin,y in [(1,24),(2,26),(3,28)]:d.wire('6V2_PRE',u+'.'+str(pin),p(23,y))
        d.terminal(u,4,-3)
        d.wire('GND',u+'.9',u+'.13',p(27,39));d.ground_at(p(27,39))
        for ref in [f'C{base+1}',f'C{base+2}',f'C{base+3}',f'C{base+4}',f'R{base}',f'C{base}',f'R{base+1}',f'R{base+3}']:d.gnd(ref,2)
        d.wire(rail,u+'.12',p(47,24),p(47,28),u+'.10')
        d.wire(rail,u+'.11',p(47,26))
        d.bus(rail,oy+24,[f'C{base+3}.1',f'C{base+4}.1',f'R{base+2}.1',f'TP{index}.1'],offset+47,offset+87)
        d.wire(f'ILIM_{index}',u+'.6',p(20,32),f'R{base+1}.1');d.label(f'ILIM_{index}',p(20,32))
        d.wire(f'SET_{index}',u+'.8',p(50,30),f'R{base}.1')
        d.wire(f'SET_{index}',p(50,34),p(59,34),f'C{base}.1');d.label(f'SET_{index}',p(50,34))
        d.terminal(u,5,3)
        # PG is a genuine cross-sheet status; pull-up is shown as a named ancillary branch.
        d.terminal(f'R{base+4}',1,-3);d.terminal(f'R{base+4}',2,3)
        d.wire(f'PGFB_{index}',f'R{base+2}.2',p(79,41),f'R{base+3}.1')
        d.wire(f'PGFB_{index}',u+'.7',p(45,34),p(45,44),p(76,44),p(76,41),p(79,41))
        d.label(f'PGFB_{index}',p(65,44))
        d.note('OUTS / SET Kelvin layout required. PG pull-up uses always-on 3.3 V.',offset+10,oy+58,1.0)
    d.note('All parts, pin numbers, values and footprints match the previous native circuit. These drawings do not establish bench qualification.',8,151,1.05)
    d.note('No second FPGA. Output current, capacitor DC bias, startup, ripple, thermal and safety behavior remain hardware review gates.',8,156,1.05)
    d.finish()
