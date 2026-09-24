#!/usr/bin/env python3
"""One-shot Rev.A drawing edit: preserve physical pin signatures and net intent.

The FPGA, watchdog and translator remain functional pre-layout abstractions.
This script is not used when opening KiCad or by normal read-only validation.
"""
from __future__ import annotations
import copy
import json
from collections import Counter
from _apply_digital_drawing import Drawing, pretty, uid, mm, put, props, ref
from _migrate_interfaces import NATIVE, HL, shape
from kicad_sexpr import parse, items, one, walk, expr

PREFIX='ServoHILFPGAReview'

class FPGADrawing(Drawing):
    def __init__(self):
        self.path=NATIVE/'05_io_fpga.kicad_sch';self.old=parse(self.path.read_text())
        self.originals={ref(s):s for s in items(self.old,'symbol') if not ref(s).startswith('#')}
        self.tree=[self.old[0]]+[copy.deepcopy(n) for n in self.old[1:] if n[0] in {'version','generator','generator_version','uuid','paper','title_block'}]
        self.lib=copy.deepcopy(one(self.old,'lib_symbols'));self.defs={}
        self.lib[:]=[self.lib[0]]+[d for d in self.lib[1:] if d[1]!='power:GND']
        for d in items(self.lib,'symbol'):
            name=d[1].split(':')[-1];d[1]=PREFIX+':'+name;self.defs[name]=d
        source=parse((NATIVE/'01_power_entry.kicad_sch').read_text())
        self.ground_template=copy.deepcopy(next(s for s in items(source,'symbol') if one(s,'lib_id')[1]=='power:GND'))
        self.lib.append(copy.deepcopy(next(s for s in items(one(source,'lib_symbols'),'symbol') if s[1]=='power:GND')))
        self.tree.append(self.lib);self.placed={};self.routes=[];self.labels=[];self.ground_count=0
        self.spec=json.loads((NATIVE.parents[3]/'validation/remaining_pages_pin_contract.json').read_text())['sheets']['05_io_fpga.kicad_sch']
        pins={'1':(120,38,270),'2':(150,38,270),'3':(180,38,270),'4':(150,190,90),
              '36':(192,124,180),'62':(192,150,180),'49':(108,174,0),'60':(108,178,0),'61':(108,184,0),
              '56':(108,156,0),'57':(108,152,0),'58':(108,160,0),'59':(108,164,0)}
        pins.update({str(n):(108,48+3*i,0) for i,n in enumerate(range(5,30))})
        self.dac_pins=list(range(30,36))+list(range(37,49))
        pins.update({str(n):(192,48+3*i,180) for i,n in enumerate(self.dac_pins)})
        pins.update({str(n):(108,126+3*i,0) for i,n in enumerate(range(50,56))})
        self.reshape('XC7A35T_FUNC',150,112,(110,40,190,188),pins)
        self.reshape('QSPI',42,134,(24,123,60,143),{
            '1':(62,126,180),'6':(62,129,180),'5':(62,132,180),'2':(62,135,180),'3':(62,138,180),'7':(62,141,180),
            '8':(42,121,270),'4':(22,140,0)})
        self.reshape('JTAG10',42,157,(24,147,60,165),{
            '1':(22,149,0),'2':(62,152,180),'4':(62,156,180),'8':(62,160,180),'6':(62,164,180),
            '3':(22,155,0),'5':(22,159,0),'9':(22,163,0),'7':(40,145,270),'10':(48,145,270)})
        self.reshape('XO',42,175,(24,170,60,180),{'1':(28,168,270),'4':(56,168,270),'3':(62,174,180),'2':(42,182,90)})
        self.reshape('WATCHDOG',226,124,(216,116,236,132),{
            '1':(226,114,270),'2':(214,124,0),'3':(226,134,90),'4':(238,124,180)})
        self.reshape('AND2',224,153,(216,145,232,160),{
            '1':(214,150,0),'2':(214,156,0),'4':(234,153,180),'5':(224,143,270),'3':(224,162,90)})
        self.reshape('LEVEL_SAFE',290,154,(282,143,298,168),{
            '1':(284,141,270),'5':(294,141,270),'2':(280,153,0),'6':(300,153,180),'3':(284,170,90),'4':(294,170,90)})
        for name in ('R','C'):
            put(self.defs[name],'pin_names',expr('(pin_names (offset 0) hide)'))
            put(self.defs[name],'pin_numbers',expr('(pin_numbers hide)'))
        cap=next(s for s in items(self.defs['C'],'symbol') if s[1].endswith('_0_1'));cap[:]=cap[:2]
        for x1,y1,x2,y2 in [(-2.54,0,-0.762,0),(-0.762,-2.54,-0.762,2.54),(0.762,-2.54,0.762,2.54),(0.762,0,2.54,0)]:
            cap.append(expr(f'(polyline (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0.254) (type default)) (fill (type none)))'))

    def place(self,*args,**kwargs):
        s=super().place(*args,**kwargs)
        one(s,'lib_id')[1]=PREFIX+':'+one(s,'lib_id')[1].split(':')[-1]
        return s

    def name(self,*args,**kwargs):
        super().name(*args,**kwargs)
        one(self.labels[-1],'uuid')[1]=uid('fpga/local/'+str(len(self.labels)))

    def note(self,*args,**kwargs):
        super().note(*args,**kwargs)
        one(self.tree[-1],'uuid')[1]=uid('fpga/note/'+str(len(self.tree)))

    def ground(self,x,y):
        self.ground_count+=1;r=f'#PWR5{self.ground_count:03d}'
        s=copy.deepcopy(self.ground_template)
        put(s,'at',expr(f'(at {mm(x)} {mm(y)} 0)'));put(s,'uuid',expr(f'(uuid "{uid("fpga/"+r)}")'))
        for p in items(s,'property'):
            put(p,'at',expr(f'(at {mm(x)} {mm(y+3)} 0)'))
            put(p,'effects',expr('(effects (font (size 1.016 1.016)) hide)'))
        props(s)['Reference'][2]=r
        for p in items(s,'pin'):put(p,'uuid',expr(f'(uuid "{uid("fpga/"+r+".1")}")'))
        inst=copy.deepcopy(one(self.originals['U10'],'instances'))
        for path in walk(inst,'path'):one(path,'reference')[1]=r
        put(s,'instances',inst);self.tree.append(s)

    def hier(self,name,x,y,angle=180):
        side='right' if angle==180 else 'left'
        self.labels.append(expr(f'(hierarchical_label "{name}" (shape {shape("05",name)}) (at {mm(x)} {mm(y)} {angle}) (effects (font (size 1.016 1.016)) (justify {side})) (uuid "{uid("fpga/hier/"+name)}"))'))

    def draw(self):
        self.place('U10',150,112,fields=[(150,32,None),(150,35,None)])
        for x,c,net in [(120,'C230','1V0_FPGA'),(150,'C231','1V8_D'),(180,'C232','3V3_D')]:
            self.hier(net,x-16,16);self.wire((x-16,16),(x,16),(x,38))
            self.place(c,x-8,24,270);self.wire((x-8,16),(x-8,20));self.wire((x-8,28),(x-8,30));self.ground(x-8,30)
        self.wire((150,190),(150,192));self.ground(150,192)
        for i,net in enumerate(HL):
            y=48+3*i;self.hier(net,80,y);self.wire((80,y),(108,y))
        for i,pin in enumerate(self.dac_pins):
            y=48+3*i;net=self.spec['U10'][str(pin)]
            self.wire((192,y),(254,y));self.hier(net,254,y,0)
        self.place('U11',42,134,fields=[(24,114,'left'),(24,117,'left')])
        self.name('3V3_D',42,119);self.wire((42,119),(42,121))
        self.wire((22,140),(18,140),(18,142));self.ground(18,142)
        for i,pin in enumerate(range(50,56)):
            y=126+3*i;self.wire((62,y),(108,y));self.name(self.spec['U10'][str(pin)],69,y)
        self.place('J11',42,157,fields=[(24,145,'left'),(62,148,'left')])
        self.name('3V3_D',14,149);self.wire((14,149),(22,149))
        for y in (155,159,163):self.wire((22,y),(18,y))
        self.wire((18,155),(18,166));self.ground(18,166)
        for x in (40,48):self.tree.append(expr(f'(no_connect (at {mm(x)} {mm(145)}) (uuid "{uid("fpga/NC/"+str(x))}"))'))
        for pin,y in [(57,152),(56,156),(58,160),(59,164)]:
            self.wire((62,y),(108,y));self.name(self.spec['U10'][str(pin)],69,y)
        self.place('Y1',42,175,fields=[(62,170,'left'),(62,181,'left')])
        self.wire((28,168),(28,167),(56,167),(56,168));self.name('1V8_D',30,167)
        self.wire((42,182),(42,184));self.ground(42,184)
        self.wire((62,174),(108,174));self.name('FPGA_CLK100',69,174)
        self.wire((78,175),(84,175),(84,184));self.name('3V3_D',78,175)
        for r,y,net in [('R230',178,'PROGRAM_B'),('R231',184,'INIT_B')]:
            self.place(r,92,y);self.wire((84,y),(88,y));self.wire((96,y),(108,y));self.name(net,98,y)
        self.place('U13',226,124,fields=[(220,112,'right'),(248,116,'left')])
        self.hier('3V3_AON',206,108);self.wire((206,108),(242,108))
        self.wire((226,108),(226,114));self.wire((242,108),(242,114))
        self.wire((226,134),(232,134),(232,135));self.ground(232,135)
        self.wire((192,124),(214,124));self.name('FPGA_WDI_3V3',193,124)
        self.place('R233',242,118,270);self.wire((242,122),(242,124))
        self.wire((238,124),(242,124),(244,124),(244,156),(246,156));self.name('LINK_WD_OK',239,124)
        self.place('U14',224,153,fields=[(216,143,'left'),(216,171,'left')])
        self.place('U15',256,153,fields=[(248,143,'left'),(248,171,'left')])
        self.place('U16',290,154,fields=[(286,137,None),(282,180,'left')])
        self.place('R232',202,144,270);self.name('3V3_D',202,136);self.wire((202,136),(202,140))
        self.wire((202,148),(202,150));self.wire((192,150),(214,150));self.name('FPGA_DONE',193,150)
        self.hier('SEQ_DONE',208,160);self.wire((208,160),(212,160),(212,156),(214,156))
        self.wire((234,153),(240,153),(240,150),(246,150));self.name('SAFE_STAGE1',235,153)
        self.wire((266,153),(280,153));self.name('SAFE_RELEASE_3V3',267,153)
        self.wire((224,139),(284,139),(284,141));self.name('3V3_AON',224,139)
        for x in (224,256):
            self.wire((x,139),(x,143));self.wire((x,162),(x,164));self.ground(x,164)
        self.name('1V8_D',294,136);self.wire((294,136),(294,141))
        self.wire((284,170),(284,174),(294,174),(294,170));self.ground(288,174)
        self.wire((300,153),(304,153),(306,153));self.hier('DAC_RESET_N',306,153,0)
        self.place('R234',304,162,270,fields=[(306,160,'left'),(274,185,'left')])
        self.wire((304,153),(304,158));self.wire((304,166),(304,172));self.ground(304,172)
        self.note('FPGA power entry / existing bulk capacitors',84,9,1.27)
        self.note('FROM / TO 04_AXU_HIL_LINK',18,42,1.27)
        self.note('TO / FROM 06_DAC_0_3 and 07_DAC_4_7',198,42,1.27)
        self.note('LOCAL CONFIGURATION / DEBUG',18,110,1.27)
        self.note('Hardware release: DONE & SEQ_DONE & watchdog OK',192,193,0.9)
        self.note('-> level translation -> DAC_RESET_N (active-low)',192,197,0.9)
        self.note('U10 is FUNCTIONAL PRELAYOUT; no FGG484 ball map or package completeness is asserted.',14,201,1.016)
        self.note('C230/C231/C232 are BULK only. Per-pin FPGA bypass and local IC decoupling remain OPEN.',14,207,1.016)
        self.note('Watchdog / translator are functional abstractions. Pin plan, power/safety qualification and PCB release remain BLOCKED.',14,213,1.016)
        self.save()

    def save(self):
        assert set(self.placed)==set(self.originals)
        sig=lambda d:sorted((one(p,'number')[1],one(p,'name')[1],p[1],p[2]) for p in walk(d,'pin'))
        for r,s in self.placed.items():
            old=self.originals[r]
            assert all(props(s)[k][2]==props(old)[k][2] for k in ('Reference','Value','Footprint','Datasheet'))
            old_d=next(d for d in items(one(self.old,'lib_symbols'),'symbol') if d[1]==one(old,'lib_id')[1])
            assert sig(old_d)==sig(self.defs[one(s,'lib_id')[1].split(':')[-1]])
        from test_digital_drawing import terminals
        points={p for pair in self.routes for p in pair}
        points.update(tuple(round(v/1.27,4) for v in p) for p in terminals(self.tree).values())
        points.update(tuple(round(float(v)/1.27,4) for v in one(n,'at')[1:3]) for n in self.labels)
        def on(p,a,b):return (p[0]==a[0]==b[0] and min(a[1],b[1])<=p[1]<=max(a[1],b[1])) or (p[1]==a[1]==b[1] and min(a[0],b[0])<=p[0]<=max(a[0],b[0]))
        segments=set()
        for a,b in self.routes:
            cuts=sorted(p for p in points if on(p,a,b));segments.update(tuple(sorted((p,q))) for p,q in zip(cuts,cuts[1:]) if p!=q)
        for a,b in sorted(segments):self.tree.append(expr(f'(wire (pts (xy {mm(a[0])} {mm(a[1])}) (xy {mm(b[0])} {mm(b[1])})) (stroke (width 0.1524) (type solid)) (uuid "{uid("fpga/wire/"+str((a,b)))}"))'))
        for (x,y),degree in Counter(p for pair in segments for p in pair).items():
            if degree>2:self.tree.append(expr(f'(junction (at {mm(x)} {mm(y)}) (diameter 0) (color 0 0 0 0) (uuid "{uid("fpga/junction/"+str((x,y)))}"))'))
        self.tree.extend(self.labels);self.path.write_text(pretty(self.tree)+'\n')
        lib=expr('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor") (generator_version "8.0"))')
        for d in items(self.lib,'symbol'):
            if d[1]=='power:GND':continue
            d=copy.deepcopy(d);d[1]=d[1].split(':')[-1];lib.append(d)
        (NATIVE/'servohil_fpga_review.kicad_sym').write_text(pretty(lib)+'\n')
        path=NATIVE/'sym-lib-table';table=parse(path.read_text())
        table[:]=[v for v in table if not(isinstance(v,list) and v and v[0]=='lib' and one(v,'name')[1]==PREFIX)]
        table.append(expr(f'(lib (name "{PREFIX}") (type "KiCad") (uri "${{KIPRJMOD}}/servohil_fpga_review.kicad_sym") (options "") (descr "Rev.A reviewed functional FPGA drawing; original pin signatures retained"))'))
        path.write_text(pretty(table)+'\n')

if __name__=='__main__':FPGADrawing().draw()
