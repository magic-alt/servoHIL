"""One-shot PR21 native authoring record, NOT the source of truth.

Only run deliberately with --author-native in an isolated checkout. Normal
validation never imports or runs this file. Edit the committed KiCad files.
"""
from pathlib import Path
import sys, copy, math, json
REPO=Path(__file__).resolve().parents[2]
if __name__ != '__main__' or sys.argv[1:] != ['--author-native']:
 raise SystemExit('One-shot migration only: explicit --author-native required')
sys.path.insert(0,str(REPO/'tools'))
from kicad_sexpr import parse, dump, document, one, items, walk, Atom as A
P=REPO/'hardware/kicad/revB/axu2cgb_expansion'
ROOT='8ab18791-d5eb-50b1-a6c4-35f9e4c661f1'
seq=0

def uid():
 global seq
 seq+=1
 return f'50500000-0000-4000-8000-{seq:012x}'
def fmt(x):return f'{x:.4f}'.rstrip('0').rstrip('.') if x else '0'
def eff(size=1.27,hide=False,justify=''):
 return f'(effects (font (size {size} {size}))'+(' hide' if hide else '')+(f' (justify {justify})' if justify else '')+')'
def prop(k,v,x,y,hide=False,size=1.27):
 return f'(property {json.dumps(k)} {json.dumps(v)} (at {fmt(x)} {fmt(y)} 0) {eff(size,hide)})'
def poly(points,w=.254):
 return '(polyline (pts '+' '.join(f'(xy {fmt(x)} {fmt(y)})' for x,y in points)+f') (stroke (width {w}) (type default)) (fill (type none)))'
LIB={}
META={}
PIN={}
def sym(name,pins,box=(15.24,15.24),graphics=None,ref='U',fp='',ds='',power=False):
 h=box[1];w=box[0]
 if graphics is None: graphics=f'(rectangle (start {-w} {h}) (end {w} {-h}) (stroke (width .254) (type default)) (fill (type background)))'
 extra='(power global) (pin_numbers hide) (pin_names (offset 0) hide)' if power else '(pin_names (offset .635))'
 pre=f'(symbol "{name}" {extra} (in_bom {"no" if power else "yes"}) (on_board {"no" if power else "yes"}) '
 pre+=prop('Reference',ref,0,h+5.08,power)+prop('Value',name,0,-h-5.08)
 pre+=prop('Footprint',fp,0,0,True)+prop('Datasheet',ds,0,0,True)
 pre+=f'(symbol "{name}_0_1" {graphics}) (symbol "{name}_1_1" '
 for n,pn,t,x,y,a,l in pins:
  pre+=f'(pin {t} line (at {fmt(x)} {fmt(y)} {a}) (length {l}) (name "{pn}" {eff(1.016)}) (number "{n}" {eff(1.016)}))'
 pre+='))'
 LIB[name]=parse(pre);PIN[name]={str(p[0]):(p[3],p[4]) for p in pins};META[name]=(fp,ds,h,power)
def pin(n,name,t,x,y,a,l=5.08):return(str(n),name,t,x,y,a,l)
sym('R',[pin(1,'','passive',-5.08,0,0,2.54),pin(2,'','passive',5.08,0,180,2.54)],(2.54,1.27),ref='R',fp='Resistor_SMD:R_0603_1608Metric')
sym('C',[pin(1,'','passive',-5.08,0,0,3.81),pin(2,'','passive',5.08,0,180,3.81)],(1.27,2.54),poly([(-1.27,2.54),(-1.27,-2.54)])+poly([(1.27,2.54),(1.27,-2.54)]),ref='C',fp='Capacitor_SMD:C_0603_1608Metric')
for name in ['3V3_AON','+5V2_PVDD','-5V2_PVSS']:
 sym(name,[pin(1,name,'power_in',0,0,90,0)],(0,0),poly([(0,0),(0,2.54),(-1.27,1.27),(0,2.54),(1.27,1.27)]),ref='#PWR',power=True)
sym('GND',[pin(1,'GND','power_in',0,0,270,0)],(0,0),poly([(0,0),(0,-1.27),(-2.54,-1.27),(0,-3.81),(2.54,-1.27),(0,-1.27)]),ref='#PWR',power=True)
sym('TP',[pin(1,'','passive',0,0,90,0)],(0,0),'(circle (center 0 0) (radius 1.016) (stroke (width .254) (type default)) (fill (type none)))',ref='TP',fp='TestPoint:TestPoint_Pad_D1.0mm')
TI='https://www.ti.com/lit/ds/symlink/'
sym('TPS3430DRCR',[
 pin(1,'VDD1','power_in',-25.4,25.4,0),pin(10,'VDD2','power_in',-25.4,20.32,0),
 pin(3,'SET0','input',-25.4,15.24,0),pin(6,'SET1','input',-25.4,10.16,0),
 pin(2,'CWD','input',-25.4,5.08,0),pin(7,'WDI','input',-25.4,0,0),
 pin(4,'CRST','passive',-25.4,-5.08,0),pin(5,'GND','power_in',-25.4,-10.16,0),
 pin(11,'EP','power_in',-25.4,-15.24,0),pin(8,'WDO_N','open_collector',25.4,0,180),pin(9,'NC','no_connect',25.4,5.08,180)
],(20.32,30.48),ds=TI+'tps3430.pdf')
sym('TPS3808G33DBVR',[
 pin(6,'VDD','power_in',-20.32,10.16,0),pin(5,'SENSE','input',-20.32,5.08,0),pin(3,'MR_N','input',-20.32,0,0),
 pin(4,'CT','passive',-20.32,-5.08,0),pin(2,'GND','power_in',-20.32,-10.16,0),pin(1,'RESET_N','open_collector',20.32,0,180)
],(15.24,15.24),fp='Package_TO_SOT_SMD:SOT-23-6',ds=TI+'tps3808.pdf')
for name in ['SN74LVC1G17DBVR','SN74LVC1G14DBVR']:
 sym(name,[pin(2,'A','input',-12.7,0,0),pin(4,'Y','output',12.7,0,180),pin(5,'VCC','power_in',0,15.24,270),pin(3,'GND','power_in',0,-15.24,90),pin(1,'NC','no_connect',12.7,5.08,180)],(7.62,10.16),fp='Package_TO_SOT_SMD:SOT-23-5',ds=TI+name[:11].lower()+'.pdf')
sym('SN74LVC1G74DCTR',[
 pin(1,'CLK','input',-20.32,5.08,0),pin(2,'D','input',-20.32,-5.08,0),
 pin(5,'Q','output',20.32,-5.08,180),pin(3,'Q_N','output',20.32,5.08,180),
 pin(7,'PRE_N','input',-7.62,20.32,270),pin(8,'VCC','power_in',7.62,20.32,270),
 pin(6,'CLR_N','input',-7.62,-20.32,90),pin(4,'GND','power_in',7.62,-20.32,90)
],(15.24,15.24),ds=TI+'sn74lvc1g74.pdf')
sym('SN74LVC1G11DBVR',[
 pin(1,'A','input',-20.32,7.62,0),pin(3,'B','input',-20.32,0,0),pin(6,'C','input',-20.32,-7.62,0),
 pin(5,'VCC','power_in',0,20.32,270),pin(2,'GND','power_in',0,-20.32,90),pin(4,'Y','output',20.32,0,180)
],(15.24,15.24),fp='Package_TO_SOT_SMD:SOT-23-6',ds=TI+'sn74lvc1g11.pdf')
for suffix,side in [('',1),('_R',-1)]:
 pins=[]
 for n,dy in enumerate([22.86,7.62,-7.62,-22.86]):
  d=[2,15,10,7][n];s=[3,14,11,6][n]
  pins+=[pin(d,'D'+str(n+1),'passive',-25.4*side,dy,0 if side==1 else 180),pin(s,'S'+str(n+1),'passive',25.4*side,dy,180 if side==1 else 0)]
 for n,dx in enumerate([-12.7,-5.08,5.08,12.7]):pins.append(pin([1,16,9,8][n],'IN'+str(n+1),'input',dx,43.18,270))
 pins += [pin(13,'VDD','power_in',-20.32,43.18,270),pin(5,'GND','power_in',20.32,43.18,270),pin(4,'VSS','power_in',-10.16,-43.18,90),pin(12,'FF_N','output',10.16,-43.18,90)]
 sym('ADG5412FBRUZ'+suffix,pins,(20.32,38.1),fp='Package_SO:TSSOP-16_4.4x5mm_P0.65mm',ds='https://www.analog.com/media/en/technical-documentation/data-sheets/ADG5412F_5413F.pdf')
pins=[]
for n in range(4):
 pins.extend([pin(n+1,'AO'+str(n),'passive',-20.32,15.24-n*10.16,0),pin(n+5,'AO'+str(n+4),'passive',20.32,15.24-n*10.16,180)])
pins += [pin(9,'GND','passive',-10.16,-25.4,90),pin(10,'GND','passive',10.16,-25.4,90)]
sym('AO_PORT',pins,(15.24,20.32),ref='J')
sym('CONTACT_2',[pin(1,'1','passive',-10.16,5.08,0),pin(2,'2','passive',-10.16,-5.08,0)],(5.08,10.16),ref='J')
sym('AQY212GS',[pin(1,'LED_A','passive',-25.4,10.16,0),pin(2,'LED_K','passive',-25.4,-10.16,0),pin(3,'NO','passive',25.4,10.16,180),pin(4,'NO','passive',25.4,-10.16,180)],(20.32,20.32),ds='https://industry.panasonic.com/ap/en/products/control/relay/photomos/number/aqy212gs')
sym('MMBT3904',[pin(1,'B','input',-15.24,0,0),pin(2,'E','passive',10.16,-10.16,90),pin(3,'C','passive',10.16,10.16,270)],(10.16,10.16),
 poly([(-10.16,0),(-2.54,0)])+poly([(-2.54,7.62),(-2.54,-7.62)])+poly([(-2.54,5.08),(10.16,5.08)])+poly([(-2.54,-5.08),(10.16,-5.08)])+poly([(6.35,-2.54),(10.16,-5.08),(6.35,-7.62)]),ref='Q',fp='Package_TO_SOT_SMD:SOT-23',ds='https://assets.nexperia.com/documents/data-sheet/MMBT3904.pdf')

class Sheet:
 def __init__(self,name,sid,page,paper='A3',title=''):
  self.name=name;self.sid=sid;self.page=page;self.parts={};self.used=set();self.wires=[];self.extra=[];self.powerseq=0
  self.tree=parse(f'(kicad_sch (version 20231120) (generator eeschema) (uuid "{uid()}") (paper "{paper}") (title_block (title "{title}") (rev "B-safety-development")) (lib_symbols))')
 def component(self,lib,ref,value,x,y,fp=None,offset=None):
  self.used.add(lib);ds=META[lib][1];power=META[lib][3];h=META[lib][2];foot=META[lib][0] if fp is None else fp
  if offset is None: offset = (h+5.08,h+8.89) if not power else (0,-5.08 if lib!='GND' else 6.35)
  ry=y-offset[0] if not power else y
  vy=y-offset[1] if not power else y+offset[1]
  body=f'(symbol (lib_id "Safety:{lib}") (at {fmt(x)} {fmt(y)} 0) (unit 1) (in_bom {"no" if power else "yes"}) (on_board {"no" if power else "yes"}) (dnp no) (uuid "{uid()}") '
  body+=prop('Reference',ref,x,ry,power,1.016 if power else 1.27)+prop('Value',value,x,vy,False,1.016 if power else 1.27)
  body+=prop('Footprint',foot,x,y,True)+prop('Datasheet',ds,x,y,True)
  body+=f'(instances (project "servohil_io_revB" (path "/{ROOT}/{self.sid}" (reference "{ref}") (unit 1)))))'
  node=parse(body);self.tree.append(node)
  coords={n:(round(x+dx,4),round(y-dy,4)) for n,(dx,dy) in PIN[lib].items()}
  self.parts[ref]=(lib,coords,node);return coords
 def p(self,ref,n):return self.parts[ref][1][str(n)]
 def wire(self,*coords):
  for a,b in zip(coords,coords[1:]):
   if a==b:continue
   assert abs(a[0]-b[0])<.001 or abs(a[1]-b[1])<.001,('nonorthogonal',a,b)
   self.wires.append((tuple(round(v,4) for v in a),tuple(round(v,4) for v in b)))
 def label(self,name,at,global_=False,angle=0):
  x,y=at
  extra=' (shape input)' if global_ else ''
  self.extra.append(parse(f'({"global_label" if global_ else "label"} "{name}"{extra} (at {fmt(x)} {fmt(y)} {angle}) {eff(1.016,justify="left bottom" if angle==0 else "right bottom")} (uuid "{uid()}"))'))
 def nc(self,ref,n):
  x,y=self.p(ref,n);self.extra.append(parse(f'(no_connect (at {fmt(x)} {fmt(y)}) (uuid "{uid()}"))'))
 def power(self,name,at):
  ref=f'#PWR9{self.page}{self.powerseq:03d}';self.powerseq+=1;self.component(name,ref,name,*at)
 def power_pin(self,ref,n,name,dy=-7.62):
  x,y=self.p(ref,n);self.wire((x,y),(x,y+dy));self.power(name,(x,y+dy))
 def note(self,text,x,y,size=1.27):
  self.extra.append(parse(f'(text {json.dumps(text)} (at {fmt(x)} {fmt(y)} 0) {eff(size,justify="left bottom")} (uuid "{uid()}"))'))
 def signal(self,ref,n,name,glob=False,length=10.16):
  p=self.p(ref,n);q=(p[0]-length,p[1]);self.wire(q,p);self.label(name,q,glob)
 def buffer(self,ref,name,x,y):
  self.component(name,ref,name,x,y,offset=(33.02,36.83));self.power_pin(ref,5,'3V3_AON');self.power_pin(ref,3,'GND',5.08);self.nc(ref,1)
 def supervisor(self,ref,x,y):
  self.component('TPS3808G33DBVR',ref,'TPS3808G33DBVR',x,y)
  a=self.p(ref,6);b=self.p(ref,5);xx=a[0]-7.62
  self.wire(a,(xx,a[1]),(xx,b[1]),b);self.power('3V3_AON',(xx,a[1]-5.08));self.wire((xx,a[1]-5.08),(xx,a[1]));self.power_pin(ref,2,'GND',5.08);self.nc(ref,4)
 def save(self):
  cached=one(self.tree,'lib_symbols')
  for lib in sorted(self.used):
   d=copy.deepcopy(LIB[lib]);d[1]='Safety:'+lib;cached.append(d)
  self.tree.extend(self.extra)
  pts=set(p for w in self.wires for p in w)
  for _,coords,_ in self.parts.values():pts.update(coords.values())
  for e in self.extra:
   a=one(e,'at')
   if e[0] in ['label','global_label','junction'] and a:pts.add((float(a[1]),float(a[2])))
  segments=set()
  for a,b in self.wires:
   vertical=abs(a[0]-b[0])<.001
   candidates=[p for p in pts if (abs(p[0]-a[0])<.001 and min(a[1],b[1])<=p[1]<=max(a[1],b[1]))] if vertical else [p for p in pts if abs(p[1]-a[1])<.001 and min(a[0],b[0])<=p[0]<=max(a[0],b[0])]
   candidates.sort(key=lambda p:p[1] if vertical else p[0])
   for c,d in zip(candidates,candidates[1:]):
    if c!=d:segments.add((c,d))
  degree={}
  for a,b in sorted(segments):
   self.tree.append(parse(f'(wire (pts (xy {fmt(a[0])} {fmt(a[1])}) (xy {fmt(b[0])} {fmt(b[1])})) (stroke (width 0) (type default)) (uuid "{uid()}"))'))
   for p in (a,b):degree[p]=degree.get(p,0)+1
  for (x,y),d in sorted(degree.items()):
   if d>=3:self.tree.append(parse(f'(junction (at {fmt(x)} {fmt(y)}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))'))
  (P/(self.name+'.kicad_sch')).write_text(document(self.tree))

SID50='50500000-0050-4000-8000-000000000001';SID60='50500000-0060-4000-8000-000000000001'
s=Sheet('50_watchdog_interlock',SID50,12,'A2','Independent heartbeat watchdog and hardware enable')
s.note('FAIL-CLOSED LAB INTERLOCK / NOT A CERTIFIED SAFETY FUNCTION',20.32,20.32,1.778)
s.note('TPS3430: falling-edge heartbeat 5 ms (contract 4..6 ms); factory window and no software disable.',20.32,30.48)
s.note('Two received edges + U503 release delay, then a fresh HIL_ARM edge. Recovery alone never re-arms.',20.32,38.1)
s.buffer('U504','SN74LVC1G17DBVR',101.6,101.6)
s.component('R','R601','1k',50.8,101.6);s.wire((25.4,101.6),s.p('R601',1));s.label('HIL_WDI',(25.4,101.6),True)
s.wire(s.p('R601',2),(71.12,101.6),s.p('U504',2));s.label('WD_HOST',(71.12,101.6))
s.component('R','R602','10k',71.12,139.7);s.wire((71.12,101.6),(66.04,101.6),(66.04,139.7));s.power('GND',s.p('R602',2))
s.component('TPS3430DRCR','U501','TPS3430DRCR',254,101.6)
s.wire(s.p('U504',4),s.p('U501',7));s.label('WD_INPUT',(170.18,101.6))
for n in [1,10,3,6]:
 p=s.p('U501',n);s.wire(p,(215.9,p[1]))
s.wire((215.9,68.58),(215.9,91.44));s.power('3V3_AON',(215.9,68.58))
s.component('R','R604','10k',198.12,96.52);s.wire(s.p('R604',2),s.p('U501',2));s.power('3V3_AON',s.p('R604',1));s.label('WD_CWD',(208.28,96.52))
s.nc('U501',4);s.nc('U501',9)
s.wire(s.p('U501',5),(220.98,111.76),(220.98,124.46));s.wire(s.p('U501',11),(220.98,116.84));s.power('GND',(220.98,124.46))
s.buffer('U510','SN74LVC1G17DBVR',360.68,101.6)
s.wire(s.p('U501',8),s.p('U510',2));s.label('WD_CLEAR_N',(309.88,101.6))
s.component('R','R605','10k',309.88,73.66);s.power('3V3_AON',s.p('R605',1));s.wire(s.p('R605',2),(314.96,101.6))
s.wire(s.p('U510',4),(391.16,101.6));s.label('HB_CLR_N',(391.16,101.6))
s.note('WDO_N and U502 RESET_N are open drain. EP pad is pin 11 in this review symbol.',195.58,142.24)
s.component('CONTACT_2','J501','3.3V DRY CONTACT ONLY',60.96,177.8,offset=(15.24,20.32))
s.component('R','R606','1k',35.56,172.72);s.power('3V3_AON',s.p('R606',1));s.wire(s.p('R606',2),s.p('J501',1));s.label('INTERLOCK_FEED',(45.72,172.72))
s.wire(s.p('J501',2),(45.72,182.88),(45.72,213.36),(78.74,213.36),(78.74,177.8),(88.9,177.8));s.label('INTERLOCK_RAW',(78.74,198.12))
s.component('R','R607','10k',60.96,223.52);s.wire((45.72,213.36),(55.88,213.36),(55.88,223.52));s.power('GND',s.p('R607',2))
s.buffer('U509','SN74LVC1G17DBVR',101.6,177.8)
s.supervisor('U502',254,177.8);s.wire(s.p('U509',4),s.p('U502',3));s.label('INTERLOCK_OK',(177.8,177.8))
s.wire(s.p('U502',1),(314.96,177.8),(314.96,101.6))
s.note('Open J501 inhibits; 3.3V dry contact. ESD qualification OPEN.',20.32,236.22)
s.component('SN74LVC1G11DBVR','U508','SN74LVC1G11DBVR',480.06,177.8,offset=(38.1,41.91))
for n,name in [(1,'RAILS_OK'),(3,'ARM_LATCH'),(6,'HIL_ARM')]:s.signal('U508',n,name,True,20.32)
s.power_pin('U508',5,'3V3_AON');s.power_pin('U508',2,'GND',5.08)
s.wire(s.p('U508',4),(533.4,177.8));s.label('SAFE_ENABLE',(533.4,177.8),True)
s.component('R','R608','10k',541.02,215.9);s.wire((525.78,177.8),(525.78,215.9),s.p('R608',1));s.power('GND',s.p('R608',2))
s.buffer('U505','SN74LVC1G14DBVR',101.6,281.94);s.signal('U505',2,'WD_INPUT',False,17.78)
s.wire(s.p('U505',4),(132.08,281.94));s.label('WD_CLK',(132.08,281.94))
for ref,x in [('U506',233.68),('U507',350.52)]:
 s.component('SN74LVC1G74DCTR',ref,'SN74LVC1G74DCTR',x,279.4,offset=(40.64,44.45))
 s.power_pin(ref,7,'3V3_AON');s.power_pin(ref,8,'3V3_AON');s.power_pin(ref,4,'GND',5.08)
 s.signal(ref,1,'WD_CLK');s.nc(ref,3)
 p=s.p(ref,6);s.wire(p,(p[0],312.42));s.label('HB_CLR_N',(p[0],312.42))
s.power_pin('U506',2,'3V3_AON')
s.wire(s.p('U506',5),s.p('U507',2));s.label('HB_FIRST',(289.56,284.48))
s.supervisor('U503',480.06,284.48);s.wire(s.p('U507',5),s.p('U503',3));s.label('HB_VALID',(414.02,284.48))
s.component('R','R603','10k',406.4,322.58);s.wire((393.7,284.48),(393.7,322.58),s.p('R603',1));s.power('GND',s.p('R603',2))
s.wire(s.p('U503',1),(530.86,284.48));s.label('RAILS_OK',(530.86,284.48),True)
s.note('U503 adds a wired-OR inhibit to existing RAILS_OK; it does NOT feed back into the heartbeat clear path.',20.32,340.36)
s.note('CT open: 12..28 ms release, not an exact 20 ms. CRST open: 170..230 ms reset hold; startup/evaluation extra.',20.32,347.98)
for i in range(10):
 x=38.1+i*53.34;ref=f'C{601+i}'
 s.component('C',ref,'100n',x,375.92)
 s.power('3V3_AON',s.p(ref,1));s.power('GND',s.p(ref,2));s.note(f'U{501+i}',x-5.08,390.525,1.016)
s.save()
a=Sheet('06_analog_outputs','85913450-4763-5590-90b1-cdfc721368a4',10,'A3','Eight-channel protected AO disconnect - qualification open')
a.note('S TERMINALS FACE DUT / D TERMINALS FACE DAC. OFF = HIGH IMPEDANCE, NOT A DEFINED NEUTRAL.',15.24,17.78,1.27)
a.note('ADG5412F RON, settling, fault energy and power-off behaviour at selected rails require bench qualification.',15.24,25.4)
a.note('FF_N is a diagnostic test point only, NOT connected to the interlock (logic margin unresolved).',15.24,33.02)
for idx,(ref,x,lib) in enumerate([('U601',100.33,'ADG5412FBRUZ'),('U602',320.04,'ADG5412FBRUZ_R')]):
 a.component(lib,ref,'ADG5412FBRUZ',x,128.27,offset=(0,-3.81))
 a.power_pin(ref,13,'+5V2_PVDD');a.power_pin(ref,5,'GND',-7.62);a.power_pin(ref,4,'-5V2_PVSS',7.62)
 for n in [1,16,9,8]:
  p=a.p(ref,n);a.wire(p,(p[0],74.93))
 a.wire((x-12.7,74.93),(x+12.7,74.93))
 rseries=f'R{652+idx*2}';rpd=f'R{651+idx*2}'
 a.component('R',rseries,'100',x+2.54,52.07)
 a.wire((x-25.4,52.07),a.p(rseries,1));a.label('SAFE_ENABLE',(x-25.4,52.07),True)
 a.wire(a.p(rseries,2),(x+7.62,74.93));a.label(f'AO_EN{idx}',(x+7.62,74.93))
 a.component('R',rpd,'10k',x+43.18,74.93)
 a.wire((x+12.7,74.93),a.p(rpd,1));a.power('GND',a.p(rpd,2))
 for ch,n in enumerate([2,15,10,7]):
  p=a.p(ref,n);q=(p[0]-15.24 if idx==0 else p[0]+15.24,p[1]);a.wire(p,q);a.label('AO'+str(idx*4+ch),q,True,0 if idx==0 else 180)
 ff=a.p(ref,12);tp=f'TP{651+idx}';a.wire(ff,(ff[0],193.04));a.component('TP',tp,f'FF{idx}_N',ff[0],193.04,offset=(-5.08,-8.89));a.label(f'AO_FF{idx}_N',(ff[0],185.42))
 for k,rail in enumerate(['+5V2_PVDD','-5V2_PVSS']):
  c=f'C{651+idx*2+k}';cx=40.64 if idx==0 else 363.22;cy=208.28+k*30.48
  a.component('C',c,'100n',cx,cy);a.power(rail,a.p(c,1));a.power('GND',a.p(c,2))
a.component('AO_PORT','J5','AO0..AO7 - NOT MCU-safe without adapter',210.82,224.79,fp='',offset=(33.02,-38.1))
for idx,ref in enumerate(['U601','U602']):
 for ch,n in enumerate([3,14,11,6]):
  p=a.p(ref,n);dest=a.p('J5',idx*4+ch+1)
  xx=(175.26-ch*10.16) if idx==0 else (245.11+ch*10.16)
  a.wire(p,(xx,p[1]),(xx,dest[1]),dest);a.label('DUT_AO'+str(idx*4+ch),(xx,p[1]))
for n in [9,10]:a.power_pin('J5',n,'GND',5.08)
a.note('DUT adapter must provide application-specific neutral bias and use the separate permit contact.',15.24,279.4)
a.save()
d=Sheet('60_dut_permit',SID60,13,'A3','Normally-open DUT permit contact - not certified STO')
d.note('OPEN CONTACT = DUT INHIBITED (REQUIRES REVIEWED DUT ADAPTER). NOT MOTOR POWER SWITCHING / NOT STO.',20.32,20.32,1.27)
d.note('Lab interface envelope: SELV <=24 V, <=10 mA. No board-level isolation or reaction-time qualification claimed.',20.32,30.48)
d.component('AQY212GS','U701','AQY212GS',200.66,83.82)
d.component('R','R701','220 1%',99.06,73.66);d.power('3V3_AON',d.p('R701',1));d.wire(d.p('R701',2),d.p('U701',1));d.label('PERMIT_LED_A',(137.16,73.66))
d.component('MMBT3904','Q701','MMBT3904',124.46,162.56,offset=(22.86,26.67))
d.wire(d.p('U701',2),(134.62,93.98),d.p('Q701',3));d.label('PERMIT_LED_K',(134.62,129.54));d.power_pin('Q701',2,'GND',10.16)
d.component('R','R702','680 1%',66.04,162.56);d.wire((25.4,162.56),d.p('R702',1));d.label('SAFE_ENABLE',(25.4,162.56),True);d.wire(d.p('R702',2),d.p('Q701',1));d.label('PERMIT_BASE',(88.9,162.56))
d.component('R','R703','10k',91.44,205.74);d.wire((86.36,162.56),(86.36,205.74));d.power('GND',d.p('R703',2))
d.component('CONTACT_2','J701','DUT PERMIT - FLOATING NO',335.28,83.82,offset=(17.78,22.86))
for n,pn in [(1,3),(2,4)]:
 p=d.p('U701',pn);q=d.p('J701',n);d.wire(p,(299.72,p[1]),(299.72,q[1]),q);d.label('DUT_PERMIT_'+('A' if n==1 else 'B'),(254,p[1]))
d.note('No copper connection from J701 contact side to board supply or GND.',236.22,129.54)
d.note('U701 off-state leakage <=1 uA (component limit). Verify actual DUT input bias and cable-loss response.',20.32,231.14)
d.note('LED network is a candidate, not qualified: R701=220 ohm; R702=680 ohm; Q701 base pull-down=10k.',20.32,241.3)
d.note('Check AON load/thermal budget, LED current over temperature and measured contact release with the real DUT.',20.32,251.46)
d.save()
# Promote only this newly cross-sheet net; preserve the old physical circuit.
power=parse((P/'40_power_supervision.kicad_sch').read_text())
for label in items(power,'label'):
 if label[1]=='RAILS_OK':
  label[0]=A('global_label');label.insert(2,parse('(shape input)'))
(P/'40_power_supervision.kicad_sch').write_text(document(power))
root=parse((P/'servohil_io_revB.kicad_sch').read_text())
for e in items(root,'text'):
 if 'NATIVE SOURCE.' in str(e[1]):e[1]='NATIVE SOURCE. Watchdog/AO disconnect/DUT permit added; ADC/PHY, power EDV, PCB and bench qualification OPEN.'
for name,sid,page,x in [('50_watchdog_interlock',SID50,12,25.4),('60_dut_permit',SID60,13,203.2)]:
 existing=next((e for e in items(root,'sheet') if any(p[1]=='Sheetfile' and p[2]==name+'.kicad_sch' for p in items(e,'property'))),None)
 if existing:root.remove(existing)
 root.insert(-1,parse(f'(sheet (at {x} 304.8) (size 139.7 30.48) (stroke (width .254) (type default)) (fill (color 0 0 0 0)) (uuid "{sid}") '+prop('Sheetname',name,x,302.26)+prop('Sheetfile',name+'.kicad_sch',x,337.82)+f'(instances (project "servohil_io_revB" (path "/{ROOT}" (page "{page}")))))'))
(P/'servohil_io_revB.kicad_sch').write_text(document(root))
libroot=parse('(kicad_symbol_lib (version 20231120) (generator kicad_symbol_editor))');libroot.extend(LIB.values());(P/'safety.kicad_sym').write_text(document(libroot))
table=parse((P/'sym-lib-table').read_text());table[:]=[x for x in table if not (isinstance(x,list) and x and x[0]=='lib' and one(x,'name')[1]=='Safety')];table.append(parse('(lib (name "Safety") (type "KiCad") (uri "${KIPRJMOD}/safety.kicad_sym") (options "") (descr "Native Rev.B safety review - package qualification open"))'));(P/'sym-lib-table').write_text(document(table))
ex=json.loads((P/'expected_connections.json').read_text())
for n in range(8):ex[f'J5.{n+1}']=f'DUT_AO{n}'
(P/'expected_connections.json').write_text(json.dumps(ex,indent=2,sort_keys=True)+'\n')
print('Native sheets authored; actual KiCad export/ERC still required.')
