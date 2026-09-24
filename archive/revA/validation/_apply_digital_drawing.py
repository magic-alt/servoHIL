#!/usr/bin/env python3
"""One-shot reviewed PR18 edit. Never run by normal validation/opening KiCad.

Only drawing geometry changes: preserve every existing physical reference,
value, footprint, pin number/name/type and the frozen native pin partition.
Functional pre-layout ICs remain functional pre-layout ICs, not package models.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from kicad_sexpr import parse, items, one, walk, expr, dump
NATIVE = ROOT / 'archive/revA/snapshot/hardware/kicad/revA'
PREFIX = 'ServoHILDigitalReview'
GRID = 1.27


def mm(v): return round(v * GRID, 4)
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'servoHIL/revA/03-continuous/' + s))
def props(s): return {p[1]: p for p in items(s, 'property')}
def ref(s): return props(s)['Reference'][2]


def put(node, tag, value):
    old = one(node, tag)
    if old is None: node.append(value)
    else: node[node.index(old)] = value


def pretty(node, indent=0):
    text = dump(node)
    if len(text) < 150 or not isinstance(node, list): return ' ' * indent + text
    i = 1
    while i < len(node) and not isinstance(node[i], list): i += 1
    return (' ' * indent + '(' + ' '.join(dump(v) for v in node[:i]) + '\n'
            + '\n'.join(pretty(v, indent + 2) for v in node[i:])
            + '\n' + ' ' * indent + ')')


class Drawing:
    def __init__(self):
        self.path = NATIVE / '03_digital_power.kicad_sch'
        self.old = parse(self.path.read_text())
        self.originals = {ref(s): s for s in items(self.old, 'symbol')}
        keep = {'version', 'generator', 'generator_version', 'uuid', 'paper', 'title_block'}
        self.tree = [self.old[0]] + [copy.deepcopy(v) for v in self.old[1:] if v[0] in keep]
        self.lib = copy.deepcopy(one(self.old, 'lib_symbols'))
        self.defs = {}
        for definition in items(self.lib, 'symbol'):
            name = definition[1].split(':')[-1]
            definition[1] = PREFIX + ':' + name
            self.defs[name] = definition
        p = parse((NATIVE / '01_power_entry.kicad_sch').read_text())
        self.ground_template = copy.deepcopy(next(s for s in items(p, 'symbol') if one(s, 'lib_id')[1] == 'power:GND'))
        self.lib.append(copy.deepcopy(next(s for s in items(one(p, 'lib_symbols'), 'symbol') if s[1] == 'power:GND')))
        self.tree.append(self.lib)
        self.placed = {}
        self.routes = []
        self.labels = []
        self.ground_count = 0
        self._review_symbols()

    def reshape(self, name, cx, cy, bounds, pin_locations):
        d = self.defs[name]
        graphics = next(s for s in items(d, 'symbol') if s[1].endswith('_0_1'))
        x1, y1, x2, y2 = bounds
        graphics[:] = graphics[:2] + [expr(
            f'(rectangle (start {mm(x1-cx)} {mm(cy-y1)}) (end {mm(x2-cx)} {mm(cy-y2)}) '
            '(stroke (width 0.254) (type default)) (fill (type background)))')]
        pins = {str(one(p, 'number')[1]): p for p in walk(d, 'pin')}
        assert set(pins) == set(pin_locations), (name, set(pins) ^ set(pin_locations))
        for num, (x, y, angle) in pin_locations.items():
            put(pins[num], 'at', expr(f'(at {mm(x-cx)} {mm(cy-y)} {angle})'))
            put(pins[num], 'length', expr('(length 2.54)'))

    def _review_symbols(self):
        pins = {'36':(169,30,0), '22':(169,34,0), '6':(169,38,0), '7':(169,42,0),
                '45':(169,54,0), '43':(169,68,0), '17':(169,82,0),
                '39':(169,96,0), '48':(169,112,0), '14':(169,128,0), '21':(169,144,0),
                '42':(169,162,0), '18':(169,174,0), '13':(169,178,0),
                '44':(169,182,0), '49':(169,186,0), '30':(169,190,0)}
        for y, numbers in [(32,('32','33','31','41','40')),(74,('28','25','29','19','20')),
                           (116,('1','4',None,'46','47')),(158,('12','8',None,'16','15'))]:
            for n, dy in zip(numbers,(-8,0,8,20,25)):
                if n: pins[n] = (197,y+dy,180)
        self.reshape('ADP5054',183,103,(171,18,195,194),pins)
        self.reshape('ADM1186-1',104,130,(96,83,112,184),{
            '2':(94,87,0),'3':(94,103,0),'4':(94,119,0),'5':(94,135,0),
            '6':(94,152,0),'7':(94,170,0),'1':(104,186,90),'20':(104,81,270),
            '19':(114,96,180),'18':(114,112,180),'17':(114,128,180),'16':(114,144,180),
            '15':(114,160,180),'14':(114,176,180)})
        self.reshape('74LVC1G17',60,152,(54,146,66,158),{
            '2':(52,152,0),'4':(68,152,180),'5':(60,144,270),'3':(60,160,90)})
        self.reshape('NMOS_LS',220,42,(216,38,224,46),{
            '1':(214,42,0),'2':(220,48,90),'3':(220,36,270)})
        for name in ('R','C','L','D'):
            definition = self.defs[name]
            put(definition,'pin_names',expr('(pin_names (offset 0) hide)'))
            put(definition,'pin_numbers',expr('(pin_numbers hide)'))
        cap = next(s for s in items(self.defs['C'],'symbol') if s[1].endswith('_0_1'))
        cap[:] = cap[:2]
        for coords in [(-2.54,0,-0.762,0),(-0.762,-2.54,-0.762,2.54),
                       (0.762,-2.54,0.762,2.54),(0.762,0,2.54,0)]:
            x1,y1,x2,y2 = coords
            cap.append(expr(f'(polyline (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0.254) (type default)) (fill (type none)))'))
        coil = next(s for s in items(self.defs['L'],'symbol') if s[1].endswith('_0_1'))
        coil[:] = coil[:2]
        for i in range(4):
            a = round(-2.54+i*1.27,4); b = round(a+1.27,4); mid=round(a+0.635,4)
            coil.append(expr(f'(arc (start {a} 0) (mid {mid} 0.635) (end {b} 0) (stroke (width 0.254) (type default)) (fill (type none)))'))
        flag = self.defs['PWR_FLAG']
        graphics = next(s for s in items(flag,'symbol') if s[1].endswith('_0_1'))
        graphics[:] = graphics[:2] + [expr('(polyline (pts (xy 0 0) (xy 0 2.54) (xy -1.27 3.81) (xy 0 5.08) (xy 1.27 3.81) (xy 0 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))')]
        pin=next(walk(flag,'pin')); put(pin,'at',expr('(at 0 0 90)')); put(pin,'length',expr('(length 0)'))

    def place(self, reference, x, y, angle=0, fields=None):
        s = copy.deepcopy(self.originals[reference])
        name = one(s, 'lib_id')[1].split(':')[-1]
        put(s,'lib_id',expr(f'(lib_id "{PREFIX}:{name}")'))
        put(s,'at',expr(f'(at {mm(x)} {mm(y)} {angle})'))
        for p in items(s,'property'):
            put(p,'at',expr(f'(at {mm(x)} {mm(y)} 0)'))
        if fields is None:
            if angle in (90,270): fields = [(x+2,y-1,'left'),(x+2,y+2,'left')]
            else: fields = [(x,y-3,None),(x,y+3,None)]
        for key,(px,py,side) in zip(('Reference','Value'),fields):
            p=props(s)[key]
            put(p,'at',expr(f'(at {mm(px)} {mm(py)} {90 if angle in (90,270) else 0})'))
            put(p,'effects',expr('(effects (font (size 1.016 1.016))'+(f' (justify {side})' if side else '')+')'))
        self.tree.append(s); self.placed[reference]=s
        return s

    def wire(self, *points):
        for a,b in zip(points,points[1:]):
            if a==b: continue
            assert a[0]==b[0] or a[1]==b[1], (a,b)
            self.routes.append((a,b))

    def name(self, name, x, y, global_=False, angle=0):
        side = 'left' if angle==0 else 'right'
        kind='global_label' if global_ else 'label'
        shape=' (shape bidirectional)' if global_ else ''
        self.labels.append(expr(f'({kind} {json.dumps(name)}{shape} (at {mm(x)} {mm(y)} {angle}) '
                               f'(effects (font (size 1.016 1.016)) (justify {side}'+('' if global_ else ' bottom')+f')) (uuid "{uid("label/"+str(len(self.labels)))}"))'))

    def ground(self, x, y):
        self.ground_count+=1; r=f'#PWR3{self.ground_count:03d}'
        s=copy.deepcopy(self.ground_template)
        put(s,'uuid',expr(f'(uuid "{uid(r)}")'))
        put(s,'at',expr(f'(at {mm(x)} {mm(y)} 0)'))
        for p in items(s,'property'):
            put(p,'at',expr(f'(at {mm(x)} {mm(y+3)} 0)'))
            put(p,'effects',expr('(effects (font (size 1.016 1.016)) hide)'))
        props(s)['Reference'][2]=r
        for p in items(s,'pin'): one(p,'uuid')[1]=uid(r+'/pin/'+str(p[1]))
        inst=copy.deepcopy(one(self.originals['U9'],'instances'))
        for path in walk(inst,'path'): one(path,'reference')[1]=r
        put(s,'instances',inst); self.tree.append(s)

    def note(self, text,x,y,size=1.27):
        self.tree.append(expr(f'(text {json.dumps(text)} (at {mm(x)} {mm(y)} 0) (effects (font (size {size} {size})) (justify left)) (uuid "{uid("note/"+text)}"))'))

    def annotate(self, name,x,y): self.name(name,x,y)

    def draw(self):
        self.place('U9',44,29,fields=[(44,18,None),(44,41,None)])
        self.place('C40',22,33,270);self.place('C41',66,33,270)
        self.wire((14,25),(34,25)); self.name('12V_PROT',14,25,True,180)
        self.wire((30,25),(30,29),(34,29))
        self.wire((22,25),(22,29));self.wire((22,37),(22,39));self.ground(22,39)
        self.wire((34,33),(31,33),(31,39));self.ground(31,39)
        self.wire((54,25),(76,25));self.name('3V3_AON',76,25,True)
        self.wire((66,25),(66,29));self.wire((66,37),(66,39));self.ground(66,39)
        self.tree.append(expr(f'(no_connect (at {mm(54)} {mm(33)}) (uuid "{uid("U9.NC")}"))'))
        self.wire((26,25),(26,16),(163,16),(163,42))
        for reference,x in zip(('C151','C152','C153','C154'),(104,118,132,146)):
            self.place(reference,x,28,270)
            self.wire((x,16),(x,24));self.wire((x,32),(x,36))
        self.wire((104,36),(153,36),(153,38));self.ground(153,38)
        self.place('U2',183,103,fields=[(183,10,None),(183,14,None)])
        for y in (30,34,38,42):self.wire((163,y),(169,y))
        self.note('Protected input / PVIN1-4 bypass',102,12)
        for reference,x,ysignal in [('C141',156,54),('C140',146,68)]:
            self.place(reference,x,ysignal+5,270)
            self.wire((169,ysignal),(x,ysignal),(x,ysignal+1))
            self.wire((x,ysignal+9),(x,ysignal+11));self.ground(x,ysignal+11)
            self.annotate('VREG_ADP' if reference=='C141' else 'VDD_ADP',x+1,ysignal)
        self.place('R141',156,77,270)
        self.name('3V3_AON',156,71);self.wire((156,71),(156,73))
        self.wire((156,81),(156,82),(169,82));self.annotate('ADP_PWRGD',158,82)
        self.place('R140',162,168,270,fields=[(160,166,'right'),(160,169,'right')])
        self.wire((169,162),(162,162),(162,164));self.annotate('RT_ADP',162,162)
        self.wire((162,172),(162,174));self.ground(162,174)
        for y in (174,178,182,186,190):self.wire((169,y),(166,y))
        self.wire((166,174),(166,193));self.ground(166,193)
        self.place('U3',104,130,fields=[(104,74,None),(104,77,None)])
        self.wire((104,79),(104,81));self.name('3V3_AON',104,79)
        self.wire((104,186),(104,188));self.ground(104,188)
        rows=[(87,'1V0_FPGA','MON_1V0','R44','R45'),(103,'1V8_D','MON_1V8','R46','R47'),
              (119,'3V3_D','MON_3V3','R48','R49'),(135,'6V0_PRE','MON_6V0','R50','R51')]
        for y,rail,net,top,bottom in rows:
            self.place(top,34,y);self.place(bottom,54,y+6,270)
            self.name(rail,16,y);self.wire((16,y),(30,y))
            self.wire((38,y),(94,y));self.annotate(net,73,y)
            self.wire((54,y),(54,y+2));self.wire((54,y+10),(54,y+12));self.ground(54,y+12)
        self.note('Rail monitors / sequenced enables',14,68)
        for y,r,net in [(96,'R148','EN1_SEQ'),(112,'R149','EN3_SEQ'),(128,'R150','EN4_SEQ'),(144,'R151','EN2_SEQ')]:
            self.wire((114,y),(169,y));self.annotate(net,151,y)
            self.place(r,142,y-6,270);self.name('3V3_AON',142,y-11)
            self.wire((142,y-11),(142,y-10));self.wire((142,y-2),(142,y))
        for y,r,net in [(160,'R41','ANALOG_EN'),(176,'R42','SEQ_DONE')]:
            self.place(r,124,y-6,270);self.name('3V3_AON',124,y-11)
            self.wire((124,y-11),(124,y-10));self.wire((124,y-2),(124,y))
            self.wire((114,y),(129,y));self.name(net,129,y,True)
        self.place('R43',84,176,270)
        self.wire((94,170),(84,170),(84,172));self.annotate('SEQ_DOWN',84,170)
        self.wire((84,180),(84,182));self.ground(84,182)
        self.place('R40',32,152);self.place('D40',32,143,180,fields=[(32,140,None),(32,146,None)])
        self.place('C42',44,158,270);self.place('U12',60,152,fields=[(70,146,'left'),(70,159,'left')])
        self.name('EFUSE_PG',14,152,True,180);self.wire((14,152),(28,152))
        self.wire((24,152),(24,143),(28,143));self.wire((36,143),(44,143),(44,152))
        self.wire((36,152),(52,152));self.annotate('SEQ_RC',37,152)
        self.wire((44,152),(44,154));self.wire((44,162),(44,164));self.ground(44,164)
        self.wire((60,140),(60,144));self.name('3V3_AON',60,140)
        self.wire((60,160),(60,164));self.ground(60,164)
        self.wire((68,152),(94,152));self.annotate('SEQ_START',78,152)
        channels=[(1,32,'L41','C43','R70','R71','C142','R144','C146','1V0_FPGA','PWR301'),
                  (2,74,'L42','C44','R80','R81','C143','R145','C147','6V0_PRE',None),
                  (3,116,'L43','C45','R90','R91','C144','R146','C148','1V8_D','PWR302'),
                  (4,158,'L44','C46','R100','R101','C145','R147','C149','3V3_D','PWR303')]
        for ch,y,ind,cout,rtop,rbot,cbst,rcomp,ccomp,rail,pflag in channels:
            self.place(ind,237,y);self.wire((197,y),(233,y));self.annotate(f'SW{ch}',224,y)
            self.place(cout,252,y+8,270);self.place(rtop,280,y+7,270);self.place(rbot,280,y+19,270)
            self.wire((241,y),(296,y),(308,y));self.name(rail,308,y,True)
            self.wire((252,y),(252,y+4));self.wire((252,y+12),(252,y+16));self.ground(252,y+16)
            self.wire((280,y),(280,y+3));self.wire((280,y+11),(280,y+15))
            self.wire((280,y+23),(280,y+25));self.ground(280,y+25)
            self.wire((280,y+13),(268,y+13),(268,y+20),(197,y+20));self.annotate(f'FB{ch}',259,y+20)
            self.place(cbst,210,y-8);self.wire((197,y-8),(206,y-8));self.annotate(f'BST{ch}',198,y-8)
            self.wire((214,y-8),(220,y-8),(220,y))
            if pflag:
                s=self.place(pflag,296,y,fields=[(297,y-5,'left'),(297,y-2,'left')])
                put(props(s)['Value'],'effects',expr('(effects (font (size 1.016 1.016)) hide)'))
            self.place(rcomp,211,y+25);self.place(ccomp,237,y+25)
            self.wire((197,y+25),(207,y+25));self.annotate(f'COMP{ch}',198,y+25)
            self.wire((215,y+25),(233,y+25));self.annotate(f'COMP{ch}_RC',219,y+25)
            self.wire((241,y+25),(252,y+25),(252,y+29));self.ground(252,y+29)
            if ch <= 2:
                q=f'Q{ch}';r='R142' if ch==1 else 'R143'
                self.place(q,220,y+10,fields=[(226,y+6,'left'),(226,y+10,'left')])
                self.wire((220,y),(220,y+4));self.wire((220,y+16),(220,y+17));self.ground(220,y+17)
                self.wire((197,y+8),(205,y+8),(211,y+8),(211,y+10),(214,y+10));self.annotate(f'DL{ch}',198,y+8)
                self.place(r,205,y+12,270,fields=[(203,y+12,'right'),(203,y+15,'right')])
                self.wire((205,y+16),(205,y+17));self.ground(205,y+17)
            self.note(f'CH{ch}: {rail}  /  PRELIM',278,y-12,1.016)
        self.note('Sequence: CH1 (1.0 V) -> CH3 (1.8 V) -> CH4 (3.3 V) -> CH2 (6.0 V) -> ANALOG_EN.',14,199,1.016)
        self.note('U2/U3/Q1/Q2 are FUNCTIONAL PRELAYOUT symbols: package pins and device qualification remain open.',14,206,1.016)
        self.note('Magnetics, compensation, MOSFETs, MLCC derating, startup and thermal limits are NOT frozen. NO PCB RELEASE.',14,213,1.016)
        self.note('Same-sheet labels annotate real wires; only distant supply/monitor taps use local aliases.',14,220,1.016)
        self.finish()

    def finish(self):
        assert set(self.placed) == set(self.originals)
        for reference,s in self.placed.items():
            old=self.originals[reference]
            assert all(props(s)[k][2]==props(old)[k][2] for k in ('Reference','Value','Footprint','Datasheet'))
            old_d=next(d for d in items(one(self.old,'lib_symbols'),'symbol') if d[1]==one(old,'lib_id')[1])
            new_d=self.defs[one(s,'lib_id')[1].split(':')[-1]]
            signature=lambda d:sorted((one(p,'number')[1],one(p,'name')[1],p[1],p[2]) for p in walk(d,'pin'))
            assert signature(old_d)==signature(new_d), reference
        endpoints={p for pair in self.routes for p in pair}
        segments=set()
        def on(p,a,b):
            return ((a[0]==b[0]==p[0] and min(a[1],b[1])<=p[1]<=max(a[1],b[1])) or
                    (a[1]==b[1]==p[1] and min(a[0],b[0])<=p[0]<=max(a[0],b[0])))
        for a,b in self.routes:
            points=sorted(p for p in endpoints if on(p,a,b))
            for p,q in zip(points,points[1:]):segments.add(tuple(sorted((p,q))))
        degrees={}
        for i,(a,b) in enumerate(sorted(segments)):
            self.tree.append(expr(f'(wire (pts (xy {mm(a[0])} {mm(a[1])}) (xy {mm(b[0])} {mm(b[1])})) (stroke (width 0.1524) (type solid)) (uuid "{uid("wire/"+str(i))}"))'))
            for p in (a,b):degrees[p]=degrees.get(p,0)+1
        for (x,y),degree in sorted(degrees.items()):
            if degree>2:self.tree.append(expr(f'(junction (at {mm(x)} {mm(y)}) (diameter 0) (color 0 0 0 0) (uuid "{uid("junction/"+str((x,y)))}"))'))
        self.tree.extend(self.labels)
        self.path.write_text(pretty(self.tree)+'\n')
        library=expr('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor") (generator_version "8.0"))')
        for d in items(self.lib,'symbol'):
            if d[1]=='power:GND':continue
            d=copy.deepcopy(d);d[1]=d[1].split(':')[-1];library.append(d)
        (NATIVE/'servohil_digital_review.kicad_sym').write_text(pretty(library)+'\n')
        table=parse((NATIVE/'sym-lib-table').read_text())
        assert not any(one(l,'name')[1]==PREFIX for l in items(table,'lib'))
        table.append(expr(f'(lib (name "{PREFIX}") (type "KiCad") (uri "${{KIPRJMOD}}/servohil_digital_review.kicad_sym") (options "") (descr "Rev.A digital-power drawing variants; original electrical pin signatures retained"))'))
        (NATIVE/'sym-lib-table').write_text(pretty(table)+'\n')


if __name__=='__main__':
    Drawing().draw()
