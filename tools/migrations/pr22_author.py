"""Explicit one-shot authoring record. Normal validation NEVER runs this file.

Run only with --author-native in a disposable checkout. Committed native KiCad
files are authoritative; this helper is removed after committing reviewed blobs.
It deliberately does not import the independent physical-pin oracle.
"""
from pathlib import Path
import sys, json, copy, uuid, math
ROOT=Path(__file__).resolve().parents[2]
if __name__!='__main__' or sys.argv[1:]!=['--author-native']:
    raise SystemExit('Explicit one-shot --author-native required')
sys.path.insert(0,str(ROOT/'tools'))
from kicad_sexpr import parse,document,one,items,Atom,number
P=ROOT/'hardware/kicad/revB/axu2cgb_expansion'
ROOT_ID='8ab18791-d5eb-50b1-a6c4-35f9e4c661f1'
NS=uuid.UUID('be785dd4-1052-4ab1-bfdc-f73177849d6c')
count=0

def uid():
    global count
    count+=1
    return str(uuid.uuid5(NS,str(count)))
def f(v):return str(number(v))
def e(sz=1.27,hide=False,j=''):
    return f'(effects (font (size {sz} {sz}))'+(' hide' if hide else '')+(f' (justify {j})' if j else '')+')'
def prop(k,v,x,y,hide=False,sz=1.27):
    return f'(property {json.dumps(k)} {json.dumps(v)} (at {f(x)} {f(y)} 0) {e(sz,hide)})'
def line(pts):return '(polyline (pts '+' '.join(f'(xy {f(x)} {f(y)})' for x,y in pts)+') (stroke (width .254) (type default)) (fill (type none)))'
LIB={};PINS={};META={}
def pin(n,name,kind,x,y,a,length=5.08):return(str(n),name,kind,x,y,a,length)
def symbol(name,pins,w=15.24,h=15.24,fp='',ds='',graphics=None,ref='U',power=False):
    if graphics is None:graphics=f'(rectangle (start {-w} {h}) (end {w} {-h}) (stroke (width .254) (type default)) (fill (type background)))'
    extra='(power global) (pin_names (offset 0) hide) (pin_numbers hide)' if power else '(pin_names (offset .635))'
    s=f'(symbol "{name}" {extra} (in_bom {"no" if power else "yes"}) (on_board {"no" if power else "yes"}) '
    s+=prop('Reference',ref,0,h+5.08,power)+prop('Value',name,0,h+8.89)
    s+=prop('Footprint',fp,0,0,True)+prop('Datasheet',ds,0,0,True)
    s+=f'(symbol "{name}_0_1" {graphics}) (symbol "{name}_1_1" '
    for n,nm,k,x,y,a,l in pins:
        s+=f'(pin {k} line (at {f(x)} {f(y)} {a}) (length {l}) (name "{nm}" {e(1.016)}) (number "{n}" {e(1.016)}))'
    s+='))'
    LIB[name]=parse(s);PINS[name]={n:(x,y) for n,_,_,x,y,_,_ in pins};META[name]=(fp,ds,h,power)
symbol('R',[pin(1,'','passive',-5.08,0,0,2.54),pin(2,'','passive',5.08,0,180,2.54)],2.54,1.27,fp='Resistor_SMD:R_0603_1608Metric',ref='R')
symbol('C',[pin(1,'','passive',-5.08,0,0,3.81),pin(2,'','passive',5.08,0,180,3.81)],1.27,2.54,fp='Capacitor_SMD:C_0603_1608Metric',ref='C',graphics=line([(-1.27,2.54),(-1.27,-2.54)])+line([(1.27,2.54),(1.27,-2.54)]))
for name in ('GND','3V3_D','1V8_D','+5V0_DAC'):
    g=line([(0,0),(0,-1.27),(-2.54,-1.27),(0,-3.81),(2.54,-1.27),(0,-1.27)]) if name=='GND' else line([(0,0),(0,2.54),(-1.27,1.27),(0,2.54),(1.27,1.27)])
    symbol(name,[pin(1,name,'power_in',0,0,90,0)],0,0,graphics=g,ref='#PWR',power=True)
symbol('TP',[pin(1,'','passive',0,0,90,0)],0,0,fp='TestPoint:TestPoint_Pad_D1.0mm',ref='TP',graphics='(circle (center 0 0) (radius 1.016) (stroke (width .254) (type default)) (fill (type none)))')
# Custom logical connector drawings retain explicit official physical pin IDs.
def connector(name,count,dy=10.16,side='right'):
    h=(count-1)*dy/2+5.08;x=10.16 if side=='right' else -10.16
    pins=[pin(i+1,str(i+1),'passive',x,(count-1)*dy/2-i*dy,180 if side=='right' else 0) for i in range(count)]
    symbol(name,pins,5.08,h,ref='J')
connector('J16',16,10.16);connector('J12',12,5.08);connector('J8',8,10.16)
connector('J4',4,10.16);connector('J3',3,10.16);connector('J6',6,10.16)
for sz in (3,4,6,8):connector('J'+str(sz)+'L',sz,10.16,'left')
# Inline unshunted 2-pin termination jumper, horizontal electrical drawing.
symbol('JP',[pin(1,'1','passive',-10.16,0,0),pin(2,'2','passive',10.16,0,180)],5.08,3.81,ref='JP')
TI='https://www.ti.com/lit/ds/symlink/'
symbol('THVD1450DR',[pin(1,'R','output',-25.4,15.24,0),pin(2,'RE_N','input',-25.4,5.08,0),pin(3,'DE','input',-25.4,-5.08,0),pin(4,'D','input',-25.4,-15.24,0),pin(6,'A','bidirectional',25.4,5.08,180),pin(7,'B','bidirectional',25.4,-5.08,180),pin(8,'VCC','power_in',0,30.48,270),pin(5,'GND','power_in',0,-30.48,90)],20.32,25.4,fp='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',ds=TI+'thvd1450.pdf')
symbol('SN74LVC1G08DBVR',[pin(1,'A','input',-15.24,5.08,0),pin(2,'B','input',-15.24,-5.08,0),pin(4,'Y','output',15.24,0,180),pin(5,'VCC','power_in',0,20.32,270),pin(3,'GND','power_in',0,-20.32,90)],10.16,15.24,fp='Package_TO_SOT_SMD:SOT-23-5',ds=TI+'sn74lvc1g08.pdf')
pwm_pins=[pin(i+2,'A'+str(i+1),'input',-25.4,35.56-10.16*i,0) for i in range(8)]
pwm_pins += [pin(18-i,'Y'+str(i+1),'output',25.4,35.56-10.16*i,180) for i in range(8)]
pwm_pins += [pin(1,'OE1_N','input',-10.16,-50.8,90),pin(19,'OE2_N','input',0,-50.8,90),pin(10,'GND','power_in',10.16,-50.8,90),pin(20,'VCC','power_in',0,50.8,270)]
symbol('SN74LVC541APWR',pwm_pins,20.32,45.72,fp='Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm',ds=TI+'sn74lvc541a.pdf')
# ADC separates analog inputs (left), serial/control/straps (right), supplies
# (top/bottom). All 64 physical pins are represented once, no hidden pins.
adc=[]
for ch in range(8):
    adc += [pin(49+2*ch,f'V{ch+1}+','input',-40.64,76.2-20.32*ch,0),pin(50+2*ch,f'V{ch+1}-','input',-40.64,66.04-20.32*ch,0)]
# Digital rows group traffic, then static mode straps below.
for n,nm,k,dy in [(12,'SCLK','input',96.52),(13,'CS_N','input',86.36),(29,'SDI','input',76.2),(9,'CONVST','input',66.04),(11,'RESET','input',55.88),(14,'BUSY','output',40.64),(15,'FRSTDATA','output',30.48)]:adc.append(pin(n,nm,k,40.64,dy,180))
for i,n in enumerate([24,25,27,28,19,20,21,22]):adc.append(pin(n,'DOUT'+chr(65+i),'output',40.64,15.24-10.16*i,180))
# Parallel pins are grounded in serial mode; os pins hard-high software mode.
for i,(n,nm) in enumerate([(3,'OS0'),(4,'OS1'),(5,'OS2'),(6,'SER_SEL'),(7,'STBY_N'),(8,'RANGE'),(10,'WR_N'),(34,'REFSELECT')]):
    adc.append(pin(n,nm,'input',-27.94+i*7.62,116.84,270))
for i,n in enumerate([16,17,18,30,31,32,33]):adc.append(pin(n,'DB_UNUSED','input',i*7.62,-116.84,90))
# Left-lower supply and regulator pins use an expanded bottom side.
for n,nm,x,y,a in [(1,'AVCC1',-78.74,116.84,270),(37,'AVCC2',-68.58,116.84,270),(38,'AVCC3',-58.42,116.84,270),(48,'AVCC4',-48.26,116.84,270),(23,'VDRIVE',50.8,116.84,270)]:
    # offset supplies are within drawn body expanded at top/bottom
    adc.append(pin(n,nm,'power_in',x,y,a))
for i,n in enumerate([2,26,35,40,41,47,43,46]):adc.append(pin(n,'AGND' if n not in [43,46] else 'REFGND','power_in',-88.9+i*10.16,-116.84,90))
# Supply and unused pin groups may share x at opposite ends, never same contact.
for n,nm,x in [(36,'REGCAP_A',-111.76),(39,'REGCAP_D',-96.52),(42,'REFIN_OUT',50.8),(44,'REFCAP_A',66.04),(45,'REFCAP_B',76.2)]:
    adc.append(pin(n,nm,'passive',x,-116.84,90))
assert len(adc)==64 and len({p[0] for p in adc})==64
# Main symbol body wide enough for supply contacts. Signal pins still meet
# inner body sides; cosmetic wing lines document grouping without hidden pins.
body=line([(-116.84,111.76),(81.28,111.76),(81.28,106.68),(35.56,106.68),(35.56,-101.6),(81.28,-101.6),(81.28,-111.76),(-116.84,-111.76),(-116.84,-101.6),(-35.56,-101.6),(-35.56,106.68),(-116.84,106.68),(-116.84,111.76)])
symbol('AD7606C-16BSTZ',adc,35.56,111.76,fp='Package_QFP:LQFP-64_10x10mm_P0.5mm',ds='https://www.analog.com/media/en/technical-documentation/data-sheets/ad7606c-16.pdf',graphics=body)

class Sheet:
    def __init__(self,name,sid,page,title):
        self.name=name;self.sid=sid;self.page=page;self.refs={};self.used=set();self.wires=[];self.extra=[];self.pwr=0
        self.t=parse(f'(kicad_sch (version 20231120) (generator eeschema) (uuid "{uid()}") (paper "A2") (title_block (title "{title}") (rev "B-IO-dev")) (lib_symbols))')
    def add(self,lib,ref,val,x,y,angle=0,fp=None,offset=None):
        self.used.add(lib);defaultfp,ds,h,power=META[lib];fp=defaultfp if fp is None else fp
        if offset is None:offset=(h+5.08,h+8.89)
        ry,vy=y-offset[0],y-offset[1]
        if power:ry=y;vy=y+(5.08 if lib=='GND' else -5.08)
        s=f'(symbol (lib_id "Periph:{lib}") (at {f(x)} {f(y)} {angle}) (unit 1) (in_bom {"no" if power else "yes"}) (on_board {"no" if power else "yes"}) (dnp no) (uuid "{uid()}") '
        s+=prop('Reference',ref,x,ry,power,1.016)+prop('Value',val,x,vy,False,1.016)+prop('Footprint',fp,x,y,True)+prop('Datasheet',ds,x,y,True)
        s+=f'(instances (project "servohil_io_revB" (path "/{ROOT_ID}/{self.sid}" (reference "{ref}") (unit 1)))))'
        self.t.append(parse(s))
        r=math.radians(angle);co,si=round(math.cos(r)),round(math.sin(r))
        pts={n:(round(x+dx*co-dy*si,4),round(y-(dx*si+dy*co),4)) for n,(dx,dy) in PINS[lib].items()}
        if ref in self.refs:raise ValueError(ref)
        self.refs[ref]=(lib,pts);return pts
    def pin(self,r,n):return self.refs[r][1][str(n)]
    def wire(self,*pts):
        for a,b in zip(pts,pts[1:]):
            a=tuple(round(v,4) for v in a);b=tuple(round(v,4) for v in b)
            if a==b:continue
            if a[0]!=b[0] and a[1]!=b[1]:raise ValueError(('diagonal',a,b))
            self.wires.append((a,b))
    def label(self,name,p,glob=False,angle=0):
        x,y=p;shape=' (shape input)' if glob else ''
        self.extra.append(parse(f'({"global_label" if glob else "label"} "{name}"{shape} (at {f(x)} {f(y)} {angle}) {e(1.016,j="left bottom" if angle==0 else "right bottom")} (uuid "{uid()}"))'))
    def power(self,name,p):
        self.pwr+=1;self.add(name,f'#PWR22{self.page:02d}{self.pwr:03d}',name,*p)
    def rail(self,ref,n,name,dx=0,dy=7.62):
        p=self.pin(ref,n);q=(p[0]+dx,p[1]+dy)
        if dx and dy:self.wire(p,(q[0],p[1]),q)
        else:self.wire(p,q)
        self.power(name,q)
    def named(self,ref,n,name,glob=False,dx=-15.24,dy=0):
        p=self.pin(ref,n);q=(p[0]+dx,p[1]+dy)
        if dx and dy:self.wire(p,(q[0],p[1]),q)
        else:self.wire(p,q)
        self.label(name,q,glob,0 if dx<=0 else 180)
    def nc(self,ref,n):
        x,y=self.pin(ref,n);self.extra.append(parse(f'(no_connect (at {f(x)} {f(y)}) (uuid "{uid()}"))'))
    def note(self,text,x,y,sz=1.27):self.extra.append(parse(f'(text {json.dumps(text)} (at {f(x)} {f(y)} 0) {e(sz,j="left bottom")} (uuid "{uid()}"))'))
    def resistor(self,ref,value,a,b,x,y,angle=0,fp=None):
        self.add('R',ref,value,x,y,angle,fp=fp)
        self.named(ref,1,a,dx=-7.62 if angle==0 else 0,dy=0 if angle==0 else 7.62)
        if b=='GND' or b in ('3V3_D','1V8_D','+5V0_DAC'):self.rail(ref,2,b,dy=7.62)
        else:self.named(ref,2,b,dx=7.62 if angle==0 else 0,dy=0 if angle==0 else -7.62)
    def decap(self,ref,value,net,x,y,fp=None):
        self.add('C',ref,value,x,y,fp=fp)
        if net in ('3V3_D','1V8_D','+5V0_DAC'):self.rail(ref,1,net,dy=-7.62)
        else:self.named(ref,1,net,dx=-5.08)
        self.rail(ref,2,'GND',dy=7.62)
    def save(self):
        for lib in sorted(self.used):
            v=copy.deepcopy(LIB[lib]);v[1]='Periph:'+lib;one(self.t,'lib_symbols').append(v)
        self.t.extend(self.extra)
        pts={p for w in self.wires for p in w}
        for _,v in self.refs.values():pts.update(v.values())
        for obj in self.extra:
            a=one(obj,'at')
            if a and obj[0] in ('label','global_label'):pts.add(tuple(float(v) for v in a[1:3]))
        segments=set()
        for a,b in self.wires:
            vertical=a[0]==b[0]
            candidates=[p for p in pts if p[0]==a[0] and min(a[1],b[1])<=p[1]<=max(a[1],b[1])] if vertical else [p for p in pts if p[1]==a[1] and min(a[0],b[0])<=p[0]<=max(a[0],b[0])]
            candidates.sort(key=lambda p:p[1] if vertical else p[0])
            segments.update((c,d) for c,d in zip(candidates,candidates[1:]) if c!=d)
        deg={}
        for a,b in sorted(segments):
            self.t.append(parse(f'(wire (pts (xy {f(a[0])} {f(a[1])}) (xy {f(b[0])} {f(b[1])})) (stroke (width 0) (type default)) (uuid "{uid()}"))'))
            for p in (a,b):deg[p]=deg.get(p,0)+1
        for (x,y),d in sorted(deg.items()):
            if d>=3:self.t.append(parse(f'(junction (at {f(x)} {f(y)}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))'))
        (P/(self.name+'.kicad_sch')).write_text(document(self.t))
HEADER='Connector_PinHeader_2.54mm:PinHeader_'
def hfp(shape):return HEADER+shape+'_P2.54mm_Vertical'
C0805='Capacitor_SMD:C_0805_2012Metric'
R1206='Resistor_SMD:R_1206_3216Metric'
SID70='22700000-0070-4000-8000-000000000001';SID80='22800000-0080-4000-8000-000000000001'

# ADC: source-side single-ended inputs with balanced series-R legs.
a=Sheet('70_adc_frontend',SID70,14,'ADC: eight low-energy analog inputs')
a.note('AD7606C-16 / 1.8V SERIAL / SOFTWARE MODE / INTERNAL REFERENCE. NOT AN INDUSTRIAL 24V INPUT.',20.32,20.32,1.524)
a.note('OS[2:0]=111. Host must program and read back CONFIG[4:3]=11 before eight-lane acquisition.',20.32,30.48)
a.note('RC networks are EMI/source networks, not complete anti-alias protection. Accuracy, clamp energy and partial-power qualification OPEN.',20.32,38.1)
a.add('AD7606C-16BSTZ','U801','AD7606C-16BSTZ',330.2,193.04,offset=(0,-5.08))
# Analog connectors stretched to match paired rows.
a.add('J16','J801','AI0..7 / GND - LOW ENERGY +/-10V',40.64,193.04,fp=hfp('2x08'),offset=(90.17,94.615))
for ch in range(8):
    for neg in (0,1):
        ref=f'R{850+2*ch+neg}';yp=116.84+ch*20.32+neg*10.16
        a.add('R',ref,'100',187.96,yp,offset=(3.175,6.985))
        a.wire(a.pin(ref,2),a.pin('U801',49+ch*2+neg))
        a.label(f'AI{ch}_{"N" if neg else "P"}',(264.16,yp))
        if not neg:
            a.wire(a.pin('J801',2*ch+1),a.pin(ref,1));a.label(f'AI{ch}_IN',(86.36,yp))
        else:
            a.rail('J801',2*ch+2,'GND',dx=10.16,dy=0)
            a.rail(ref,1,'GND',dx=-10.16,dy=0)
    a.add('C',f'C{850+ch}','1n',241.3,121.92+ch*20.32,angle=270,offset=(-1.27,-5.08))
for n in (3,4,5,6,7,8,10,34):a.rail('U801',n,'1V8_D',dy=-12.7)
for n in (1,37,38,48):a.rail('U801',n,'+5V0_DAC',dy=-7.62)
a.rail('U801',23,'1V8_D',dy=-12.7)
for n in (16,17,18,30,31,32,33,2,26,35,40,41,47,43,46):a.rail('U801',n,'GND',dy=7.62)
for n,name in [(36,'ADC_REGCAP_A'),(39,'ADC_REGCAP_D'),(42,'ADC_REFINT')]:a.named('U801',n,name,dx=0,dy=17.78)
p44,p45=a.pin('U801',44),a.pin('U801',45)
a.wire(p44,(p44[0],320.04),(p45[0],320.04),p45);a.label('ADC_REFBUF',(p44[0],320.04))
for i,(name,n) in enumerate([('SCLK',12),('CS_N',13),('SDI',29),('CONVST',9),('RESET',11)]):
    y=a.pin('U801',n)[1];ref=f'R{801+i}'
    a.add('R',ref,'33',424.18,y,angle=180,offset=(3.175,6.985))
    a.wire(a.pin('U801',n),a.pin(ref,2));a.label('ADC_'+name+'_IC',(393.7,y))
    a.named(ref,1,'ADC_'+name,True,dx=68.58)
for ch,n in enumerate([24,25,27,28,19,20,21,22]):
    y=a.pin('U801',n)[1];ref=f'R{820+ch}'
    a.add('R',ref,'33',424.18,y,offset=(3.175,6.985))
    a.wire(a.pin('U801',n),a.pin(ref,1));a.label(f'ADC_DOUT{ch}_RAW',(391.16,y))
    a.named(ref,2,f'ADC_DOUT{ch}',True,dx=68.58)
y=a.pin('U801',14)[1];a.add('R','R828','33',424.18,y,offset=(3.175,6.985));a.wire(a.pin('U801',14),a.pin('R828',1));a.label('ADC_BUSY_RAW',(391.16,y));a.named('R828',2,'ADC_BUSY',True,dx=68.58)
y=a.pin('U801',15)[1];a.wire(a.pin('U801',15),(469.9,y));a.add('TP','TP801','ADC_FRSTDATA',469.9,y,offset=(-3.81,-7.62));a.label('ADC_FRSTDATA',(398.78,y))
for i,(name,rail) in enumerate([('CS_N','1V8_D'),('RESET','1V8_D'),('CONVST','GND'),('SCLK','GND'),('SDI','GND')]):
    a.resistor(f'R{830+i}','10k','ADC_'+name+'_IC',rail,78.74+i*99.06,50.8)
for i,(ref,value,net) in enumerate([(f'C{801+j}','100n','+5V0_DAC') for j in range(4)]+[('C805','10u','+5V0_DAC'),('C806','100n','1V8_D'),('C807','1u','ADC_REGCAP_A'),('C808','1u','ADC_REGCAP_D'),('C809','100n','ADC_REFINT'),('C810','10u','ADC_REFBUF')]):
    x=50.8+(i%5)*106.68;y=350.52+(i//5)*30.48
    a.decap(ref,value,net,x,y,fp=C0805 if value in ('1u','10u') else None)
a.save()

def phy(s,u,gate,prefix,tx,rx,direction,x,y,rbase,cnum,gcap,term,jumper,term_x):
    tx_internal,rx_internal,de_internal=prefix+'_TX_IC',prefix+'_RX_RAW',prefix+'_DE_SAFE'
    s.add('THVD1450DR',u,'THVD1450DR',x,y,offset=(41.91,46.99))
    s.rail(u,8,'3V3_D',dy=-5.08);s.rail(u,5,'GND',dy=5.08)
    s.rail(u,2,'GND',dx=-5.08,dy=0)
    s.add('SN74LVC1G08DBVR',gate,'SN74LVC1G08DBVR',x-142.24,y+5.08,offset=(30.48,35.56))
    s.rail(gate,5,'3V3_D',dy=-5.08);s.rail(gate,3,'GND',dy=5.08)
    s.named(gate,1,'SAFE_ENABLE',True,dx=-15.24)
    s.named(gate,2,direction,True,dx=-15.24)
    s.wire(s.pin(gate,4),s.pin(u,3));s.label(de_internal,(x-63.5,y+5.08))
    s.add('R',f'R{rbase}','100',x-50.8,y+15.24,offset=(-3.175,-6.985))
    s.wire(s.pin(f'R{rbase}',2),s.pin(u,4));s.label(tx_internal,(x-38.1,y+15.24))
    s.named(f'R{rbase}',1,tx,True,dx=-22.86)
    s.add('R',f'R{rbase+1}','100',x-50.8,y-15.24,angle=180,offset=(3.175,6.985))
    s.wire(s.pin(f'R{rbase+1}',1),s.pin(u,1));s.label(rx_internal,(x-38.1,y-15.24))
    s.named(f'R{rbase+1}',2,rx,True,dx=-22.86)
    for j,(net,ref) in enumerate([(direction,rbase+2),(tx_internal,rbase+3),(de_internal,rbase+4)]):
        s.resistor(f'R{ref}','10k',net,'GND',43.18+j*71.12,y+53.34)
        if j==0:
            for obj in s.extra:
                if obj[0]=='label' and obj[1]==direction:obj[0]=Atom('global_label');obj.insert(2,parse('(shape input)'))
    pa,pb=s.pin(u,6),s.pin(u,7)
    s.wire(pa,(term_x,pa[1]));s.label(prefix+'_A',(term_x,pa[1]))
    s.wire(pb,(term_x,pb[1]));s.label(prefix+'_B',(term_x,pb[1]))
    s.add('R',term,'120',term_x+15.24,y+27.94,fp=R1206)
    s.named(term,1,prefix+'_A',dx=-5.08)
    s.add('JP',jumper,'TERM - SHUNT ABSENT',term_x+60.96,y+27.94,fp=hfp('1x02'),offset=(-5.08,-8.89))
    s.wire(s.pin(term,2),s.pin(jumper,1));s.label(prefix+'_TERM',(term_x+30.48,y+27.94))
    s.named(jumper,2,prefix+'_B',dx=5.08)
    s.decap(cnum,'100n','3V3_D',x+45.72,y+53.34)
    s.decap(gcap,'100n','3V3_D',x+96.52,y+53.34)

b=Sheet('80_encoder_phy',SID80,15,'Dual SSI / BiSS directional differential PHY')
b.note('TWO PORTS / CLOCK + DATA PER PORT. NON-ISOLATED. DIR=1 TRANSMITS ONLY WHEN SAFE_ENABLE=1.',20.32,20.32,1.524)
b.note('IO0/IO2 = TX data, IO1/IO3 = RX data. Receiver always on. SSI/BiSS only: not an ABZ or 4-wire SPI compatibility claim.',20.32,30.48)
for pair in range(4):
    port,lane=divmod(pair,2);pref=f'ENC{port}_P{lane}';y=86.36+pair*76.2;x=297.18
    u=f'U{901+pair}';g=f'U{911+pair}';r=901+pair*5
    b.add('THVD1450DR',u,'THVD1450DR',x,y,offset=(31.75,35.56))
    b.rail(u,8,'3V3_D',dy=-2.54);b.rail(u,5,'GND',dy=2.54);b.rail(u,2,'GND',dx=-7.62,dy=0)
    b.add('SN74LVC1G08DBVR',g,'SN74LVC1G08DBVR',116.84,y+5.08,offset=(21.59,25.4))
    b.rail(g,5,'3V3_D',dy=-5.08);b.rail(g,3,'GND',dy=5.08)
    b.named(g,1,'SAFE_ENABLE',True,dx=-35.56);b.named(g,2,f'ENC{port}_DIR{lane}',True,dx=-35.56)
    b.wire(b.pin(g,4),b.pin(u,3));b.label(pref+'_DE',(228.6,y+5.08))
    b.add('R',f'R{r}','100',220.98,y+15.24,offset=(-3.175,-6.985));b.wire(b.pin(f'R{r}',2),b.pin(u,4));b.label(pref+'_TX',(246.38,y+15.24));b.named(f'R{r}',1,f'ENC{port}_IO{lane*2}',True,dx=-35.56)
    b.add('R',f'R{r+1}','100',220.98,y-15.24,angle=180,offset=(3.175,6.985));b.wire(b.pin(f'R{r+1}',1),b.pin(u,1));b.label(pref+'_RX',(246.38,y-15.24));b.named(f'R{r+1}',2,f'ENC{port}_IO{lane*2+1}',True,dx=-35.56)
    for j,net in enumerate([f'ENC{port}_DIR{lane}',pref+'_TX',pref+'_DE']):
        ref=f'R{r+2+j}';xx=43.18+81.28*j;yy=y+35.56
        b.add('R',ref,'10k',xx,yy,offset=(3.175,6.985));b.named(ref,1,net,glob=(j==0),dx=-7.62);b.rail(ref,2,'GND',dy=0)
    for n,suffix in [(6,'A'),(7,'B')]:
        b.wire(b.pin(u,n),(365.76,b.pin(u,n)[1]));b.label(pref+'_'+suffix,(365.76,b.pin(u,n)[1]))
    b.add('R',f'R{950+pair}','120',398.78,y+10.16,fp=R1206,offset=(5.08,8.89));b.named(f'R{950+pair}',1,pref+'_A',dx=-7.62)
    b.add('JP',f'JP{901+pair}','TERM - SHUNT ABSENT',459.74,y+10.16,fp=hfp('1x02'),offset=(-5.08,-8.89));b.wire(b.pin(f'R{950+pair}',2),b.pin(f'JP{901+pair}',1));b.label(pref+'_TERM',(426.72,y+10.16));b.named(f'JP{901+pair}',2,pref+'_B',dx=10.16)
    b.decap(f'C{901+pair}','100n','3V3_D',345.44,y+33.02)
    b.decap(f'C{911+pair}','100n','3V3_D',408.94,y+33.02)
for port,y in enumerate([81.28,233.68]):
    ref=f'J{901+port}';b.add('J6L',ref,'SSI/BiSS CLK/DATA - NO POWER',546.1,y,fp=hfp('2x03'),offset=(40.64,44.45))
    for n,net in [(1,f'ENC{port}_P0_A'),(2,f'ENC{port}_P0_B'),(3,f'ENC{port}_P1_A'),(4,f'ENC{port}_P1_B')]:b.named(ref,n,net,dx=-17.78)
    b.rail(ref,5,'GND',dx=-12.7,dy=0);b.rail(ref,6,'GND',dx=-12.7,dy=0)
    b.decap(f'C{921+port}','1u','3V3_D',538.48,y+60.96,fp=C0805)
b.note('Termination shunts absent by default. Choose termination/role before ARM. No encoder power is supplied.',20.32,375.92)
b.note('External cable surge/ESD, IO contention, host-off backfeed and actual line timing remain physical acceptance items.',20.32,383.54)
b.save()

c=Sheet('03_peripheral_boundaries','73846c09-6306-5db3-9679-2686619beb33',7,'PWM, auxiliary logic and RS485 interfaces')
c.note('BUFFERED LOW-VOLTAGE LAB I/O / NO 24V PLC INPUTS / NO ISOLATION / NO ALLOCATED CAN OR ETHERCAT PORT.',20.32,20.32,1.524)
c.note('Reserved J3/J4 module headers removed. Existing carrier pin allocation is unchanged.',20.32,30.48)
c.add('SN74LVC541APWR','U1010','SN74LVC541APWR',223.52,132.08,offset=(60.96,64.77))
c.rail('U1010',20,'3V3_D',dy=-5.08)
for n in (1,19,10):c.rail('U1010',n,'GND',dy=5.08)
c.rail('U1010',8,'GND',dx=-10.16,dy=0);c.rail('U1010',9,'GND',dx=-10.16,dy=0);c.nc('U1010',12);c.nc('U1010',11)
c.add('J12','J1001','SIX PWM / GND - 3.3V LOGIC ONLY',40.64,124.46,fp=hfp('2x06'),offset=(66.04,69.85))
for ch,nm in enumerate(['UH','UL','VH','VL','WH','WL']):
    net='PWM_'+nm;yp=c.pin('U1010',ch+2)[1];r=f'R{1010+ch}'
    c.add('R',r,'100',139.7,yp,offset=(3.175,6.985));c.wire(c.pin(r,2),c.pin('U1010',ch+2));c.label(net+'_IC',(172.72,yp))
    start=c.pin('J1001',2*ch+1);dest=c.pin(r,1);xx=68.58+ch*7.62
    c.wire(start,(xx,start[1]),(xx,yp),dest);c.label(net+'_IN',(xx,start[1]))
    c.rail('J1001',2*ch+2,'GND',dx=5.08,dy=0)
    c.named('U1010',18-ch,net,True,dx=43.18)
    c.resistor(f'R{1020+ch}','10k',net+'_IC','GND',45.72+ch*48.26,210.82)
c.decap('C1010','100n','3V3_D',223.52,53.34);c.decap('C1011','1u','3V3_D',284.48,53.34,fp=C0805)
c.add('J8L','J1002','AUX 3.3V LOGIC / GND',548.64,116.84,fp=hfp('2x04'),offset=(45.72,49.53))
for ch in range(6):
    yp=c.pin('J1002',ch+1)[1];r=f'R{1030+ch}'
    c.add('R',r,'100',464.82,yp,offset=(3.175,6.985));c.named(r,1,f'AUX_IO{ch}',True,dx=-68.58)
    c.wire(c.pin(r,2),c.pin('J1002',ch+1));c.label(f'AUX{ch}_PORT',(518.16,yp))
    c.resistor(f'R{1040+ch}','100k',f'AUX{ch}_PORT','GND',378.46+(ch%3)*68.58,172.72+(ch//3)*25.4)
for n in (7,8):c.rail('J1002',n,'GND',dx=-10.16,dy=0)
phy(c,'U1001','U1002','RS485','RS485_TX','RS485_RX','RS485_DE',271.78,287.02,1001,'C1001','C1002','R1006','JP1001',350.52)
c.add('J3L','J1004','RS485 A/B/GND',505.46,284.48,fp=hfp('1x03'),offset=(22.86,26.67))
for n,net in [(1,'RS485_A'),(2,'RS485_B')]:c.named('J1004',n,net,dx=-20.32)
c.rail('J1004',3,'GND',dx=-20.32,dy=0)
c.add('J4L','J1003','I2C 3.3V / GND',543.56,353.06,fp=hfp('1x04'),offset=(30.48,34.29))
for n,nm in [(1,'MGMT_SCL'),(2,'MGMT_SDA')]:c.named('J1003',n,nm,True,dx=-17.78)
for n in (3,4):c.rail('J1003',n,'GND',dx=-10.16,dy=0)
for i,nm in enumerate(['MGMT_SCL','MGMT_SDA']):
    ref=f'R{1050+i}';c.add('R',ref,'4.7k',431.8,350.52+i*25.4);c.named(ref,1,nm,True,dx=-7.62);c.rail(ref,2,'3V3_D',dy=-7.62)
c.note('THVD1450 receivers stay enabled. All differential TX enable pins require SAFE_ENABLE AND the respective host DIR/DE.',20.32,368.3)
c.note('Port roles, line termination and cable/host-off behaviour must be reviewed before connecting a DUT. No board-level ESD rating claimed.',20.32,378.46)
c.save()

root=parse((P/'servohil_io_revB.kicad_sch').read_text())
for note in items(root,'text'):
    if str(note[1]).startswith('NATIVE SOURCE.'):
        note[1]='NATIVE SOURCE. ADC/PWM/encoder/RS485 populated; power EDV, physical DUT safety and production qualification OPEN.'
for name,sid,page,x in [('70_adc_frontend',SID70,14,25.4),('80_encoder_phy',SID80,15,203.2)]:
    for old in list(items(root,'sheet')):
        if any(p[1]=='Sheetfile' and p[2]==name+'.kicad_sch' for p in items(old,'property')):root.remove(old)
    root.append(parse(f'(sheet (at {x} 355.6) (size 139.7 30.48) (stroke (width .254) (type default)) (fill (color 0 0 0 0)) (uuid "{sid}") '+prop('Sheetname',name,x,353.06)+prop('Sheetfile',name+'.kicad_sch',x,389.89)+f'(instances (project "servohil_io_revB" (path "/{ROOT_ID}" (page "{page}")))))'))
(P/'servohil_io_revB.kicad_sch').write_text(document(root))
lib=parse('(kicad_symbol_lib (version 20231120) (generator kicad_symbol_editor))');lib.extend(LIB.values());(P/'peripherals.kicad_sym').write_text(document(lib))
table=parse((P/'sym-lib-table').read_text())
for old in list(items(table,'lib')):
    if one(old,'name')[1]=='Periph':table.remove(old)
table.append(parse('(lib (name "Periph") (type "KiCad") (uri "${KIPRJMOD}/peripherals.kicad_sym") (options "") (descr "Rev.B native peripherals"))'))
(P/'sym-lib-table').write_text(document(table))
table=parse((P/'fp-lib-table').read_text());names={one(o,'name')[1] for o in items(table,'lib')}
for name in ('Package_QFP','Connector_PinHeader_2.54mm'):
    if name not in names:table.append(parse(f'(lib (name "{name}") (type "KiCad") (uri "${{KIPRJMOD}}/footprints/{name}.pretty") (options "") (descr "Bundled KiCad footprints"))'))
(P/'fp-lib-table').write_text(document(table))
contract=json.loads((P/'expected_connections.json').read_text());contract={k:v for k,v in contract.items() if not k.startswith(('J3.','J4.'))}
(P/'expected_connections.json').write_text(json.dumps(contract,indent=2,sort_keys=True)+'\n')
print('One-shot native authoring done. Actual KiCad export/ERC still required.')
